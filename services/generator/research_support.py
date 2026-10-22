"""One bounded historical S0/S1 producer and frozen public projections.

This command grants no archive admission, live authority or statistical accuracy
claim. Qualify its exact source/runtime/invocation separately before execution.
"""
import time
IMPORT_STARTED=time.perf_counter()
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import resource
from typing import Annotated, Literal

from pydantic import Field, model_validator
from contracts.domain.analysis import FIXED_SUPPORT_REF, canonical, reference, sha
from contracts.domain.boundaries import lineage_heads, visible_records
from contracts.domain.common import StrictModel
from contracts.domain.evidence_v2 import exact_ref, projection_hash
from contracts.domain.protocol import LAW_REF, SUPPORT_REF, ObservedHistoryV21, RECORD_ADAPTER_V21
from contracts.domain.protocol_request import IDENTITIES, S1_ESTIMAND
from contracts.runs.common import Artifact, Token, unique
from contracts.runs.coverage_v2 import StageLedgerV2
from contracts.runs.support_research import (StageVerifier, SupportCompletion, SupportResearchIndex,
                                           SupportRuntime, version_ref)
from services.foundation.protocol import project_protocol
from .restricted import START
from .restricted_v2 import generate

IMPORT_SECONDS=time.perf_counter()-IMPORT_STARTED

MAPPING='poc-support-research-map-v1'
DESIGN=reference('poc-support-research-design-v1',
    'Historical synthetic research only; never imported as live physician authority')
CONTEXT=reference('poc-support-public-context-v1','Latest available quality and preceding six nights delivered prompts')
STAGE_RULE=reference('poc-support-stage-rule-v1','Explicit offered/delivered transitions; exhaustive active stage events per noon window')
ENDPOINT=reference('poc-support-quality-window-v1','Noon through next day11:59; exact next-morning reported quality')
S1_POLICY=SUPPORT_REF


class ResearchSupportPlan(StrictModel):
    version: Literal['poc-support-research-plan-v1']
    namespace: Annotated[str, Field(min_length=1,max_length=256)]
    run_id: Token
    cohort_id: Token
    patients: Annotated[list[Token], Field(min_length=12,max_length=12)]

    @model_validator(mode='after')
    def members(self):
        unique(self.patients,'support research member')
        if any(len(p)>60 or not all(c.isalnum() or c in '-_' for c in p) for p in self.patients):
            raise ValueError('opaque_restricted_support_member_required')
        return self


def _now():
    return datetime.now(timezone.utc)


def _write(root, identifier, path, value, role='observed'):
    raw=canonical(value).encode()
    descriptor=Artifact.model_validate(dict(id=identifier,path=path,sha256=sha(value),
        bytes=len(raw),role=role,media_type='application/json'))
    target=Path(root)/path
    if any(p.is_symlink() for p in (target,*target.parents) if p.is_relative_to(root)):
        raise ValueError('symlink_support_artifact_denied')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.read_bytes()!=raw:raise ValueError('immutable_support_artifact_conflict')
    else:
        with target.open('xb') as handle:handle.write(raw)
    return descriptor


def _record(patient, name, at, kind, *, schema='1.0.0', published=None, **fields):
    value=dict(schema_version=schema,synthetic=True,record_id=name,patient_id=patient,
        event_at=at.isoformat(),recorded_at=(published or at).isoformat(),available_at=(published or at).isoformat(),
        lineage_id=name,revision=1,supersedes=None,duplicate_of=None,record_status='active',kind=kind,**fields)
    value['source']=dict(id=LAW_REF['id'] if kind=='delivery' else DESIGN['id'],
        version='2.0.0' if kind=='delivery' else '1.0.0',adapter='simulation' if kind=='delivery' else 'research_configuration',raw_sha256=sha(value))
    return RECORD_ADAPTER_V21.validate_json(canonical(value))


def _history(patient, records):
    return ObservedHistoryV21(schema_version='2.1.0',synthetic=True,kind='observed_history',patient_id=patient,records=records)


def _snapshot(patient,name,at,policy,mode,eligibility,*,held=False,paused=False):
    return _record(patient,name,at,'decision_snapshot',cutoff=at.isoformat(),patient_version=1,state_version=1,
        consent_version=1,eligibility_version=1,workflow=dict(clinical='clinical_hold' if held else 'treatment_active',
        learning='support_active',data_readiness='ready',hold_reasons=['synthetic_hold'] if held else [],
        support_policy=policy,support_mode='paused' if paused else mode),view=dict(patient_id=patient,mode='current',snapshot_id=None),
        eligibility=eligibility,outcome='quality',horizon_days=1,estimand=S1_ESTIMAND,model=IDENTITIES['S1-WCLS']['model'],
        posterior=None,evidence=[DESIGN],policy=DESIGN)


def _approval(patient,name,at,snapshot,option=None):
    return _record(patient,name,at,'approval',decision_id=snapshot.record_id,option=option,
        permitted_options=[] if option else ['support_prompt','no_prompt'],clinician_id='historical-synthetic-research-design',
        purpose='ordinary_treatment' if option else 'randomization_protocol',expected_patient_version=1,
        expected_state_version=1,expected_consent_version=1,expected_eligibility_version=1)


def _assignment(patient,name,at,snapshot,approval,option,policy,*,randomized=False,day=0):
    seed=dict(namespace='assignment',protocol=SUPPORT_REF['id'],scenario='poc-support-reference',replicate=0,
        patient=patient,time_index=day,process='historical-support-draw') if randomized else None
    return _record(patient,name,at,'assignment',decision_id=snapshot.record_id,approval_id=approval.record_id,option=option,
        experimental=randomized,component='mrt_bandit' if randomized else None,probability=.5 if randomized else None,
        seed=seed,support_policy=policy,patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None)


def _initial(patient,mode):
    policy=FIXED_SUPPORT_REF if mode=='S0' else S1_POLICY
    consent=_record(patient,patient+'-consent',START-timedelta(seconds=50),'consent',component='mrt_bandit',
        consent_version=DESIGN['id'],oversight_version=DESIGN['id'],consent_status='active',oversight_status='approved_synthetic',
        effective_at=(START-timedelta(seconds=50)).isoformat(),expires_at=None,withdrawn_at=None)
    eligibility=[dict(action=a,status='eligible',reasons=[]) for a in ('support_prompt','no_prompt','behavioral_continue')]
    initial=_snapshot(patient,patient+'-background-context',START-timedelta(seconds=40),FIXED_SUPPORT_REF,'fixed',eligibility)
    binary=_approval(patient,patient+'-binary-design',START-timedelta(seconds=39),initial)
    approval=_approval(patient,patient+'-background-approval',START-timedelta(seconds=39),initial,'behavioral_continue')
    background=_assignment(patient,patient+'-background',START-timedelta(seconds=38),initial,approval,'behavioral_continue',FIXED_SUPPORT_REF)
    records=[consent,initial,binary,approval,background]
    frozen=None
    if mode=='S0':
        frozen=_record(patient,patient+'-fixed-snapshot',START-timedelta(seconds=30),'protocol_snapshot',schema='2.1.0',
            family='support',protocol=SUPPORT_REF,template=SUPPORT_REF,consent_refs=[exact_ref(consent).model_dump()],
            approval_refs=[exact_ref(binary).model_dump()],background_ref=exact_ref(background).model_dump(),support_refs=[],
            activation_at=(START-timedelta(seconds=30)).isoformat())
        records.append(frozen)
    return records,background,frozen,policy


def distribution(history,at,mode,*,held=False,paused=False):
    """Eligibility consumes only active public predecision records."""
    known=history.as_known_at(at)
    state=max((r for r in known if r.kind=='decision_snapshot'),
        key=lambda r:(r.event_at,r.available_at,r.record_id),default=None)
    if state is not None:
        held=held or state.workflow.clinical=='clinical_hold' or bool(state.workflow.hold_reasons)
        paused=paused or state.workflow.support_mode=='paused'
    consents=lineage_heads(visible_records([r for r in history.records if r.kind=='consent' and r.component=='mrt_bandit'],at))
    consent=max(consents,key=lambda r:(r.available_at,r.recorded_at,r.revision,r.record_id),default=None)
    denied=['clinical_hold'] if held else ['patient_pause'] if paused else []
    if state is not None and state.workflow.data_readiness!='ready':denied.append('data_unready')
    if consent is None or not consent.permits('mrt_bandit',at):denied.append('consent_or_oversight_unavailable')
    delivered=[r for r in known if r.kind=='delivery' and r.stage=='delivered' and r.option=='support_prompt'
               and at-timedelta(days=6) <= r.event_at < at]
    prompt_reasons=[]
    if any(at-timedelta(days=1) <= r.event_at < at for r in delivered):prompt_reasons.append('no_consecutive_nights')
    if len(delivered)>=3:prompt_reasons.append('max_three_in_seven')
    if mode=='S0':prompt_reasons.append('fixed_no_prompt')
    eligibility=[dict(action=a,status='excluded' if denied or (a=='support_prompt' and prompt_reasons) else 'eligible',
        reasons=denied or (prompt_reasons if a=='support_prompt' else [])) for a in ('support_prompt','no_prompt')]
    if denied:return eligibility,'unavailable',dict(support_prompt=0.,no_prompt=0.),denied
    if prompt_reasons:return eligibility,'deterministic',dict(support_prompt=0.,no_prompt=1.),[]
    return eligibility,'randomized',dict(support_prompt=.5,no_prompt=.5),[]


def _draw(seed,patient,day):
    # Independent keyed assignment namespace never consumes generator streams.
    raw=hashlib.sha256(canonical([MAPPING,'assignment',seed,patient,day]).encode()).digest()
    return ((int.from_bytes(raw[:8],'big') >> 11)+.5)/2**53


def _generated(seed,index,patient,through,background,support):
    product=generate(dict(law_version=LAW_REF['id'],family='support',seed=seed,index=index,patient_id=patient,
        through_day=through,actions=[dict(day=0,option='behavioral_continue',assignment_id=background.record_id)] if through else [],
        medications=[],support=support))
    return [RECORD_ADAPTER_V21.validate_json(canonical(e['record'])) for e in product['records']]


def trajectory(patient,mode,*,seed,index,assignment_seed,run_id,partition_id,runtime,source_commit,plan_sha,
               root,horizon=84,now=_now,on_persist=None):
    """Sequential prefix regeneration; horizon is a UNIT seam, production is84."""
    records,background,frozen,policy=_initial(patient,mode)
    generated={r.record_id:r for r in _generated(seed,index,patient,0,background,[])}
    records.extend(generated.values());support=[];ledgers=[];receipts=[];timings=[]
    for day in range(horizon):
        started=now();tick=time.perf_counter();at=START+timedelta(days=day);assessment=at+timedelta(days=1,minutes=-1)
        before=_history(patient,records)
        eligibility,availability,probabilities,reasons=distribution(before,at,mode)
        snapshot=_snapshot(patient,f'{patient}-context-{day}',at,policy,'fixed' if mode=='S0' else 'mrt',eligibility)
        records.append(snapshot)
        approval=None
        if availability!='unavailable':
            approval=_approval(patient,f'{patient}-approval-{day}',at,snapshot,
                'no_prompt' if availability=='deterministic' else None)
            records.append(approval)
        known=before.as_known_at(at)
        prior=max((r for r in known if r.kind=='daily_report' and r.missingness=='observed'),
            key=lambda r:(r.event_at,r.available_at,r.recorded_at,r.record_id),default=None)
        context=([prior] if prior else [])+[r for r in known if r.kind=='delivery' and r.stage=='delivered'
            and r.option=='support_prompt' and at-timedelta(days=6)<=r.event_at<at]
        # All reports remain in the complete frozen projection. Only canonical
        # feature sources belong in the declared predecision context refs.
        name=f'{patient}-support-{day}';assignment_id=f'{patient}-support-assignment-{day}' if approval else None
        decision=_record(patient,name,at,'support_decision',schema='2.1.0',
            decision_snapshot=exact_ref(snapshot).model_dump(),decision_index=day,cutoff=at.isoformat(),
            context=[exact_ref(r).model_dump() for r in context],context_projection_sha256=projection_hash(before,at),
            context_mapping=CONTEXT,policy=policy,mechanism=SUPPORT_REF,mode='fixed' if mode=='S0' else 'mrt',
            eligibility=eligibility,policy_constraint=dict(allowed_actions=['no_prompt'] if frozen else ['support_prompt','no_prompt'],
                reason='fixed_no_prompt' if frozen else 'unrestricted',snapshot_ref=exact_ref(frozen).model_dump() if frozen else None),
            availability=availability,unavailable_reasons=reasons,probabilities=probabilities,probability_tolerance=1e-12,
            assignment_id=assignment_id,distribution_persisted_at=at.isoformat(),execution_receipt=DESIGN,
            outcome_window=dict(id=name+'-window',starts_at=at.isoformat(),ends_at=assessment.isoformat(),assessment_at=assessment.isoformat(),
                timezone='UTC',local_date=at.date().isoformat(),endpoint_definition=ENDPOINT),outcome_link_id=name+'-outcome')
        records.append(decision)
        _write(root,name+'-predecision',f'{partition_id}/decisions/{day}.json',
            dict(support_decision=decision.model_dump(mode='json'),decision_snapshot=snapshot.model_dump(mode='json'),
                approval=approval.model_dump(mode='json') if approval else None,
                context=[r.model_dump(mode='json') for r in context]))
        if on_persist:on_persist(decision)
        assignment=None
        if approval:
            option='support_prompt' if availability=='randomized' and _draw(assignment_seed,patient,day)<probabilities['support_prompt'] else 'no_prompt'
            # All noon substeps share the canonical simulated instant. The final
            # vector is already appended above before this draw, independently
            # of actual execution timing. WCLS owns this exact noon clock.
            assignment=_assignment(patient,assignment_id,at,snapshot,approval,option,policy,
                randomized=availability=='randomized',day=day)
            records.append(assignment);support.append(dict(day=day,option=option,assignment_id=assignment.record_id))
        regenerated={r.record_id:r for r in _generated(seed,index,patient,day+1,background,support)}
        if any(regenerated.get(k)!=v for k,v in generated.items()):raise ValueError('generator_prefix_changed')
        fresh=[v for k,v in regenerated.items() if k not in generated];records.extend(fresh);generated=regenerated
        delivery_at=at+timedelta(hours=8)
        events=[r for r in fresh if r.kind=='delivery' and r.assignment_id==assignment_id and r.stage=='delivered']
        if assignment and assignment.option=='support_prompt':
            # The restricted law supplies delivery; the producer explicitly logs
            # the preceding offer transition under immediate/perfect response.
            offered=_record(patient,name+'-offered',delivery_at,'delivery',assignment_id=assignment_id,option='support_prompt',
                stage='offered',adherence=None,rescue=False,protocol_deviations=[])
            records.append(offered);events.append(offered)
        event_artifact=_write(root,name+'-events',f'{partition_id}/events/{day}.json',[r.model_dump(mode='json') for r in events])
        local=[]
        for stage in ('offered','delivered'):
            local.append(StageLedgerV2.model_validate_json(canonical(dict(schema_version='2.0.0',synthetic=True,kind='support_stage_ledger',
                id=name+'-'+stage+'-ledger',run_id=run_id,partition_id=partition_id,patient_id=patient,decision_index=day,
                window_id=decision.outcome_window.id,stage=stage,rule=STAGE_RULE,
                event_refs=[exact_ref(r).model_dump() for r in events if r.stage==stage]))))
        completed=delivery_at+timedelta(seconds=1);available=completed+timedelta(seconds=1)
        receipt=SupportCompletion.model_validate_json(canonical(dict(version='poc-support-stage-completion-v1',id=name+'-completion',
            run_id=run_id,partition_id=partition_id,patient_id=patient,source_commit=source_commit,runtime=runtime.model_dump(mode='json'),
            frozen_plan_sha256=plan_sha,status='complete',reason=None,stage_ledgers=[version_ref(r).model_dump() for r in local],
            output_artifacts=[event_artifact.model_dump(mode='json')],output_counts=dict(stage_events=len(events)),
            simulated_completed_through=completed.isoformat(),simulated_available_at=available.isoformat(),
            execution_started_at=started.isoformat(),execution_ended_at=now().isoformat(),published_at=now().isoformat())))
        closures=[]
        for ledger in local:
            closure=_record(patient,name+'-'+ledger.stage+'-closure',completed,'support_stage_closure',schema='2.0.0',published=available,
                run_id=run_id,partition_id=partition_id,support_decision=exact_ref(decision).model_dump(),
                assignment_ref=exact_ref(assignment).model_dump() if assignment else None,window_id=decision.outcome_window.id,
                decision_index=day,stage=ledger.stage,rule=STAGE_RULE,stage_completed_at=completed.isoformat(),status='complete',
                stage_event_refs=[r.model_dump() for r in ledger.event_refs],stage_ledger=version_ref(ledger).model_dump(),row_count=len(ledger.event_refs),
                reason='Historical restricted producer completed exhaustive stage',completion_receipt=version_ref(receipt).model_dump())
            records.append(closure);closures.append(closure)
        report=next(r for r in fresh if r.kind=='daily_report' and r.event_at==assessment)
        observed=report.missingness=='observed'
        outcome=_record(patient,decision.outcome_link_id,assessment,'support_outcome_link',schema='2.0.0',published=assessment+timedelta(seconds=20),
            support_decision=exact_ref(decision).model_dump(),assignment_ref=exact_ref(assignment).model_dump() if assignment else None,
            window_id=decision.outcome_window.id,assessment_at=assessment.isoformat(),evaluated_as_of=(assessment+timedelta(seconds=10)).isoformat(),
            reward=dict(status='observed' if observed else 'missing',report_ref=exact_ref(report).model_dump() if observed else None,
                field='sleep_quality',unit='quality_points',reason=None if observed else 'independent_MCAR_report_missing',
                evidence_refs=[exact_ref(report).model_dump()],definition_refs=[]),
            burden=[dict(definition=STAGE_RULE,type=stage+'_prompt_count',unit='count',status='observed',
                value=sum(r.option=='support_prompt' and r.stage==stage for r in events),
                source_refs=[exact_ref(r).model_dump() for r in events if r.stage==stage]) for stage in ('offered','delivered')],
            offered_closure_ref=exact_ref(closures[0]).model_dump(),delivered_closure_ref=exact_ref(closures[1]).model_dump())
        records.append(outcome);ledgers.extend(local);receipts.append(receipt)
        timings.append(dict(day=day,wall_seconds=time.perf_counter()-tick))
    return _history(patient,records),ledgers,receipts,timings


def prepare(plan,private_root,output_root,*,runtime,source_commit):
    started=_now();tick=time.perf_counter()
    plan=ResearchSupportPlan.model_validate_json(canonical(plan));runtime=SupportRuntime.model_validate_json(canonical(runtime))
    private_root,output_root=Path(private_root).resolve(),Path(output_root).resolve()
    if private_root==output_root or private_root.is_relative_to(output_root) or output_root.is_relative_to(private_root):
        raise ValueError('private_recipe_must_be_separate_from_public_output')
    if output_root.exists() and any(output_root.iterdir()):raise ValueError('fresh_support_output_required_no_success_retries')
    private_root.mkdir(parents=True,exist_ok=True);output_root.mkdir(parents=True,exist_ok=True)
    plan_sha=sha(plan.model_dump(mode='json'));mapping=[]
    for index,patient in enumerate(plan.patients):
        mapping.append(dict(patient_id=patient,index=index,
            generation_seed=int(sha([MAPPING,plan.namespace,plan.run_id,patient,'generation']),16)%2**31,
            assignment_seed=sha([MAPPING,plan.namespace,plan.run_id,patient,'independent-assignment']),
            paired_member_id='pair-'+sha([MAPPING,plan.namespace,patient,'paired-member'])[:24]))
    unique([r['generation_seed'] for r in mapping],'generation seed')
    shared_pair_sha=sha([dict(paired_member_id=r['paired_member_id'],index=r['index'],generation_seed=r['generation_seed']) for r in mapping])
    recipe=dict(plan=plan.model_dump(mode='json'),mapping=mapping,derivation=MAPPING,
        shared_pair_sha256=shared_pair_sha,source_commit=source_commit,runtime=runtime.model_dump(mode='json'))
    recipe_artifact=_write(private_root,'support-private-recipe','recipe.json',recipe,'configuration')
    sources={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
             for name in ('restricted.py','restricted_v2.py','research_support.py')}
    trajectories=[];timings=[]
    for member in mapping:
        for mode in ('S0','S1'):
            patient=member['patient_id'];partition='partition-'+sha([plan.run_id,patient,mode])[:24]
            trajectory_tick=time.perf_counter()
            full,ledgers,receipts,stage_times=trajectory(patient,mode,seed=member['generation_seed'],index=member['index'],
                assignment_seed=member['assignment_seed'],run_id=plan.run_id,partition_id=partition,runtime=runtime,
                source_commit=source_commit,plan_sha=plan_sha,root=output_root)
            generated_at=time.perf_counter()
            verifier=StageVerifier(full,ledgers,receipts,output_root,run_id=plan.run_id,partition_id=partition,
                source_commit=source_commit,runtime=runtime,frozen_plan_sha256=plan_sha)
            history=_write(output_root,partition+'-history',f'{partition}/history.json',full.model_dump(mode='json'))
            ledger_artifact=_write(output_root,partition+'-ledgers',f'{partition}/ledgers.json',[r.model_dump(mode='json') for r in ledgers],'configuration')
            receipt_artifact=_write(output_root,partition+'-completions',f'{partition}/completions.json',[r.model_dump(mode='json') for r in receipts],'configuration')
            projections={}
            projection_times={}
            for day in (14,42,84):
                projection_tick=time.perf_counter()
                projection=project_protocol(full,START+timedelta(days=day),family='support',origin=START,verify_closure=verifier)
                projections[str(day)]=_write(output_root,partition+'-day-'+str(day),f'{partition}/day-{day}.json',projection.model_dump(mode='json')).model_dump(mode='json')
                projection_times[str(day)]=time.perf_counter()-projection_tick
            trajectories.append(dict(member_id=patient,paired_member_id=member['paired_member_id'],mode=mode,partition_id=partition,
                history=history.model_dump(mode='json'),projections=projections,stage_ledgers=ledger_artifact.model_dump(mode='json'),
                completions=receipt_artifact.model_dump(mode='json')))
            timings.append(dict(member_id=patient,mode=mode,stages=stage_times,generation_wall_seconds=generated_at-trajectory_tick,
                projection_and_publication_wall_seconds=projection_times,total_wall_seconds=time.perf_counter()-trajectory_tick,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    index=SupportResearchIndex.model_validate_json(canonical(dict(version='poc-support-research-v1',synthetic=True,
        execution='historical-research-only',run_id=plan.run_id,cohort_id=plan.cohort_id,members=plan.patients,origin=START.isoformat(),
        horizon=84,cuts=[14,42,84],law=LAW_REF,protocol=SUPPORT_REF,estimand=S1_ESTIMAND,source_commit=source_commit,
        generator_sources=sources,runtime=runtime.model_dump(mode='json'),frozen_plan_sha256=plan_sha,
        private_recipe_sha256=recipe_artifact.sha256,shared_pair_sha256=shared_pair_sha,trajectories=trajectories)))
    # The complete marker is last. Interrupted work cannot masquerade as a run.
    _write(output_root,'support-generation-timing','generation-timing.json',dict(started_at=started.isoformat(),ended_at=_now().isoformat(),
        cold_import_wall_seconds=IMPORT_SECONDS,total_wall_seconds=time.perf_counter()-tick,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,trajectories=timings),'configuration')
    return _write(output_root,plan.run_id,'manifest.json',index.model_dump(mode='json'),'observed_manifest').model_dump(mode='json')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','runtime','private-root','output-root'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--source-commit',required=True);args=parser.parse_args()
    print(json.dumps(prepare(json.loads(args.plan.read_bytes()),args.private_root,args.output_root,
        runtime=json.loads(args.runtime.read_bytes()),source_commit=args.source_commit),sort_keys=True))


if __name__=='__main__':main()
