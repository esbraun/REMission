"""Pure fail-closed LIVE-SAFETY admission. Authority must be selected out of band."""
from dataclasses import dataclass
import json
from pathlib import Path
from pydantic import TypeAdapter
from contracts.domain.boundaries import LearnerHistory
from contracts.domain.observed_v2 import LearnerHistoryV2
from contracts.runs.common import canonical, sha256
from .live_safety import LiveHoldFact, LiveSafetyExport, TrustedLiveSafetyAuthority

FACTS=TypeAdapter(list[LiveHoldFact])
EMPTY=sha256(b'')


def ordered(values):
    return sorted(values,key=canonical)


def obligation_hash(obligations):
    raw=[x.model_dump(mode='json') if hasattr(x,'model_dump') else x for x in obligations]
    if len({x['requirement_id'] for x in raw})!=len(raw) or raw!=sorted(raw,key=lambda x:x['requirement_id']):
        raise ValueError('invalid obligation set')
    return sha256(canonical(raw))


def fold(facts):
    active={};closed={};baseline=None;current_config=None
    for fact in facts:
        op=fact.operation
        config=(fact.authority_generation,fact.authority_sha256,fact.review_rules_sha256)
        if op.type=='baseline':
            if fact.patient_sequence!=1 or baseline is not None or op.active_episodes:
                raise ValueError('invalid independent baseline')
            baseline=fact.operation_id;current_config=config
            continue
        if baseline is None:
            raise ValueError('missing independent baseline')
        if op.type=='authority_changed':
            if ((op.old_generation,op.old_authority_sha256,op.old_review_rules_sha256)!=current_config
                    or op.new_generation<=op.old_generation or op.new_generation!=fact.authority_generation
                    or op.new_authority_sha256!=fact.authority_sha256 or op.new_review_rules_sha256!=fact.review_rules_sha256
                    or op.prior_journal_id!=fact.journal_id or len(op.active_episodes)!=len(active)
                    or {x.episode_id for x in op.active_episodes}!=set(active)):
                raise ValueError('invalid authority change')
            for item in op.active_episodes:
                current=active[item.episode_id]
                if item.generation!=current['generation'] or obligation_hash(item.obligations)!=item.obligation_set_sha256:
                    raise ValueError('invalid changed obligations')
                previous={x['requirement_id']:x for x in current['obligations']}
                resulting={x.requirement_id:x.model_dump(mode='json') for x in item.obligations}
                if any(resulting.get(k)!=v for k,v in previous.items()):
                    raise ValueError('authority weakened obligation')
                current.update(obligations=list(resulting.values()),obligation_set_sha256=item.obligation_set_sha256,review=None)
            current_config=config
            continue
        if config!=current_config:
            # Cutovers append patient authority facts only for active episodes.
            # An inactive journal may next open under a later generation, but
            # an existing latch/review cannot cross authority without its fact.
            if active or op.type!='invalidate' or op.action!='open' or config[0]<=current_config[0]:
                raise ValueError('missing active authority change')
            current_config=config
        key=op.episode_id
        if op.type=='invalidate':
            triggers=[x.model_dump(mode='json') for x in op.active_trigger_refs]
            if (not op.trigger_refs or not op.reason_codes or not op.obligations or triggers!=ordered(triggers)
                    or len({canonical(x) for x in triggers})!=len(triggers)
                    or sha256(canonical([op.generation,triggers]))!=op.trigger_set_sha256
                    or obligation_hash(op.obligations)!=op.obligation_set_sha256
                    or any(x.model_dump(mode='json') not in triggers for x in op.trigger_refs)):
                raise ValueError('invalid invalidation set')
            if op.action=='open':
                if key in active or op.generation!=closed.get(key,0)+1:
                    raise ValueError('invalid generation open')
            else:
                if key not in active or op.generation!=active[key]['generation']:
                    raise ValueError('invalid generation strengthen')
                old=active[key]
                if any(x not in triggers for x in old['triggers']):
                    raise ValueError('removed active trigger')
                if not set(old['reason_codes']).issubset(op.reason_codes):
                    raise ValueError('removed active reason')
                resulting={x.requirement_id:x.model_dump(mode='json') for x in op.obligations}
                if any(resulting.get(x['requirement_id'])!=x for x in old['obligations']):
                    raise ValueError('weakened active obligation')
            active[key]=dict(episode_id=key,generation=op.generation,triggers=triggers,trigger_set_sha256=op.trigger_set_sha256,
                obligations=[x.model_dump(mode='json') for x in op.obligations],obligation_set_sha256=op.obligation_set_sha256,
                reason_codes=list(op.reason_codes),review=None)
            continue
        if key not in active or op.generation!=active[key]['generation']:
            raise ValueError('operation targets inactive generation')
        current=active[key]
        if op.type=='evidence_disputed':
            if (op.reason=='current_context_changed') != (op.changed_context_sha256 is not None):
                raise ValueError('invalid context dispute')
            if not op.affected_refs and op.reason!='current_context_changed':
                raise ValueError('empty evidence dispute')
            current['review']=None
            continue
        if op.trigger_set_sha256!=current['trigger_set_sha256'] or op.obligation_set_sha256!=current['obligation_set_sha256']:
            raise ValueError('review/clearance stale facts')
        if not op.rule_refs or len({canonical(x.model_dump(mode='json')) for x in op.rule_refs})!=len(op.rule_refs):
            raise ValueError('invalid review rule set')
        if op.type=='review_recorded':
            if op.current_review_at!=fact.recorded_at:
                raise ValueError('review current clock mismatch')
            current['review']=dict(id=op.review_id,sha256=op.review_sha256,config=config,
                rules=[x.model_dump(mode='json') for x in op.rule_refs],result=op.result)
        elif op.type=='clearance':
            review=current['review']
            if (review is None or review['result']!='satisfied' or review['config']!=config
                    or review['id']!=op.review_id or review['sha256']!=op.review_sha256
                    or ordered(review['rules'])!=ordered([x.model_dump(mode='json') for x in op.rule_refs])):
                raise ValueError('clearance lacks prior satisfied current review')
            closed[key]=op.generation
            del active[key]
        else:
            raise ValueError('unsupported safety operation')
    summary=[{k:e[k] for k in ['episode_id','generation','trigger_set_sha256','obligation_set_sha256']} for _,e in sorted(active.items())]
    return baseline,summary,'unknown' if baseline is None else 'held' if active else 'not_held'


@dataclass(frozen=True)
class LiveSafetyContext:
    observed_projection: LearnerHistory | LearnerHistoryV2
    visible_operations: tuple[LiveHoldFact,...]
    independent_hold_status: str
    active_episodes: tuple[dict,...]
    cutoff: object
    provenance: LiveSafetyExport


def verify_live_safety(raw_manifest: bytes, root: Path, authority: TrustedLiveSafetyAuthority):
    authority=TrustedLiveSafetyAuthority.model_validate_json(authority.model_dump_json())
    manifest=LiveSafetyExport.model_validate_json(raw_manifest)
    if sha256(raw_manifest)!=authority.manifest_sha256 or canonical(manifest.model_dump(mode='json'))!=raw_manifest:
        raise ValueError('untrusted live manifest bytes')
    if manifest.execution=='contract_fixture' and not authority.allow_contract_fixture:
        raise ValueError('contract fixture is not a qualified service producer')
    for field in ['service_instance_id','service_producer','source_commit','runtime','export_id','patient_id','cutoff',
                  'snapshot_id','snapshot_sha256','authority_generation','authority_sha256','review_rules_sha256',
                  'through_patient_sequence','prefix_chain_sha256','baseline_operation_id']:
        if getattr(manifest,field)!=getattr(authority,field):
            raise ValueError('live authority binding mismatch: '+field)
    bindings=json.loads(Path(__file__).with_name('bindings-v1.json').read_bytes())
    if (manifest.service_contract.model_dump()!=bindings['live_hold'] or manifest.schema_binding.model_dump()!=bindings['service_schema_set']
            or manifest.observed_binding.model_dump()!=bindings['observed_domain'][manifest.observed_projection.schema_version]):
        raise ValueError('live schema/spec binding mismatch')
    root=Path(root)
    if root.is_symlink() or {p.name for p in root.iterdir()}!={'manifest.json','observed-projection.json','live-hold-facts.json'}:
        raise ValueError('live product must contain exactly three files')
    if any(p.is_symlink() or not p.is_file() for p in root.iterdir()):
        raise ValueError('unsafe live artifact')
    if (root/'manifest.json').read_bytes()!=raw_manifest:
        raise ValueError('manifest artifact mismatch')
    artifacts=[]
    for ref in [manifest.observed_projection,manifest.facts]:
        raw=(root/ref.path).read_bytes()
        if len(raw)!=ref.bytes or sha256(raw)!=ref.sha256:
            raise ValueError('live artifact bytes mismatch')
        artifacts.append(raw)
    observed_raw,facts_raw=artifacts
    if sha256(observed_raw)!=authority.observed_sha256:
        raise ValueError('untrusted observed projection')
    model=LearnerHistoryV2 if manifest.observed_projection.schema_version=='2.0.0' else LearnerHistory
    observed=model.model_validate_json(observed_raw)
    if observed.patient_id!=manifest.patient_id or observed.cutoff!=manifest.cutoff:
        raise ValueError('nested patient/cutoff mismatch')
    facts=FACTS.validate_json(facts_raw)
    if facts_raw!=canonical([f.model_dump(mode='json') for f in facts]):
        raise ValueError('noncanonical safety facts')
    if len(facts)!=manifest.facts.count or len(facts)!=authority.prefix_count or manifest.through_patient_sequence!=len(facts):
        raise ValueError('incomplete trusted patient prefix')
    roster={(r.generation,r.authority_sha256,r.review_rules_sha256) for r in authority.generations}
    generations=[r.generation for r in authority.generations]
    if generations!=sorted(set(generations)) or any(g>manifest.authority_generation for g in generations):
        raise ValueError('invalid trusted authority roster')
    previous=None;last_time=None;operations=set()
    for sequence,fact in enumerate(facts,1):
        if (fact.patient_id!=manifest.patient_id or fact.journal_id!=manifest.journal_id or fact.patient_sequence!=sequence
                or fact.previous_fact_sha256!=previous or fact.operation_id in operations
                or fact.event_at>manifest.cutoff or fact.recorded_at>=manifest.cutoff or fact.available_at>=manifest.cutoff
                or (last_time is not None and fact.recorded_at<last_time)
                or (fact.authority_generation,fact.authority_sha256,fact.review_rules_sha256) not in roster):
            raise ValueError('invalid visible patient prefix')
        operations.add(fact.operation_id);last_time=fact.recorded_at
        previous=sha256(canonical(fact.model_dump(mode='json')))
    if (previous or EMPTY)!=manifest.prefix_chain_sha256:
        raise ValueError('wrong prefix head')
    baseline,active,status=fold(facts)
    if (baseline!=manifest.baseline_operation_id or status!=manifest.independent_hold_status
            or active!=[x.model_dump(mode='json') for x in manifest.active_episodes]
            or manifest.completeness!=('complete_visible_prefix' if baseline else 'uninitialized')):
        raise ValueError('incorrect live safety fold')
    return LiveSafetyContext(observed,tuple(facts),status,tuple(active),manifest.cutoff,manifest)
