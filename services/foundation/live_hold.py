"""Authenticated, transactional independent hold workflow; archive resolution never clears."""
from datetime import datetime
import json
import uuid
from contracts.domain.evidence_v2 import exact_ref, resolve, validate_hold
from contracts.domain.observed_v2 import ObservedHistoryV2
from contracts.service.live_hold import EvidenceRef
from .live_journal import active_episodes, append_fact, control, receive
from .store import canonical, digest, instant, timestamp

VERSION_FIELDS=('version','state_version','consent_version','eligibility_version')


class LiveError(ValueError):
    def __init__(self, code, status=409):
        super().__init__(code)
        self.code,self.status=code,status


def object_hash(value):
    return digest(canonical(value))


def refs(values):
    values=[v.model_dump(mode='json') if hasattr(v,'model_dump') else v for v in values]
    encoded=[canonical(v) for v in values]
    if len(set(encoded)) != len(encoded):
        raise LiveError('duplicate_evidence_reference',422)
    return sorted(values,key=canonical)


def versions(patient):
    return {k:patient[k] for k in VERSION_FIELDS}


def patient_row(db, patient_id, owner):
    row=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(patient_id,owner)).fetchone()
    if row is None:
        raise LiveError('not_found',404)
    return row


def archive_history(db, archive_id, partition_id, patient_id):
    rows=db.execute('SELECT payload FROM observed_archive_entries WHERE archive_id=? AND partition_id=? AND patient_id=? ORDER BY ordinal',
        (archive_id,partition_id,patient_id)).fetchall()
    if not rows:
        raise LiveError('hold_dependencies_unavailable')
    return ObservedHistoryV2.model_validate_json(canonical(dict(schema_version='2.0.0',synthetic=True,
        kind='observed_history',patient_id=patient_id,records=[json.loads(r[0]) for r in rows])))


def configured_archive(settings, db, archive_id, owner):
    stored=db.execute('SELECT * FROM observed_archives WHERE id=? AND owner_id=?',(archive_id,owner)).fetchone()
    if stored is None:
        raise LiveError('hold_dependencies_unavailable')
    for raw,root,authority in (settings.observed_archives or {}).values():
        if digest(raw)==stored['export_sha256'] and raw==bytes(stored['manifest']):
            from contracts.runs.admission_v2 import verify_export_v2
            manifest,partitions=verify_export_v2(raw,root,authority)
            if manifest.run_id+':'+manifest.id != archive_id:
                continue
            return stored,manifest,partitions,authority
    raise LiveError('live_source_grant_unavailable')


def prepare_invalidation(settings, db, owner, patient_id, data, at):
    patient_row(db,patient_id,owner)
    installed=settings.installed
    if not installed.control.enabled or not installed.authority.enabled:
        raise LiveError('independent_hold_live_integration_required')
    stored,manifest,partitions,archive_authority=configured_archive(settings,db,data.archive_id,owner)
    if manifest.cutoff>at:
        raise LiveError('future_hold_evidence',422)
    history=archive_history(db,data.archive_id,data.partition_id,patient_id)
    try:
        bundle=resolve(history,data.bundle_ref,{'hold_transition_bundle'},cutoff=at,inclusive=True)
        validate_hold(history,bundle,cutoff=at)
    except ValueError as error:
        code='hold_dependencies_unavailable' if 'missing' in str(error) else 'hold_evidence_stale'
        raise LiveError(code) from error
    if bundle.transition_type not in ('enter','change_reason') or not bundle.reason_codes:
        raise LiveError('positive_hold_trigger_required')
    if refs(data.trigger_refs)!=refs(bundle.trigger_refs):
        raise LiveError('hold_evidence_stale')
    grant=next((g for g in installed.authority.grants if
        (g.account_id,g.service_patient_id,g.archive_patient_id,g.run_id,g.partition_id,g.archive_id,g.package_sha256,
         g.source_id,g.source_version,g.archive_authority_sha256)==
        (owner,patient_id,patient_id,bundle.run_id,data.partition_id,data.archive_id,stored['export_sha256'],
         bundle.source.id,bundle.source.version,object_hash(archive_authority.model_dump(mode='json')))),None)
    if grant is None or 'invalidate' not in grant.allowed_operations:
        raise LiveError('live_source_grant_unavailable')
    if grant.ownership_ref!=bundle.ownership_ref or grant.follow_up_owner_id!=owner:
        raise LiveError('live_source_grant_unavailable')
    for follow in bundle.follow_up_refs:
        task=resolve(history,follow,{'follow_up'},cutoff=at,inclusive=True)
        if task.owner!=owner or task.due_at!=grant.due_at or task.escalation_destination!=grant.escalation_destination:
            raise LiveError('hold_follow_up_mismatch')
    requirements={r.requirement_id:r for r in grant.required_reviews}
    if {r.requirement_id for r in bundle.required_reviews} != set(requirements):
        raise LiveError('hold_requirement_mismatch')
    for r in bundle.required_reviews:
        required=requirements[r.requirement_id]
        if r.definition!=required.definition or r.responsible_role!=required.responsible_role:
            raise LiveError('hold_requirement_mismatch')
    triggers=[]
    for ref in bundle.trigger_refs:
        trigger=resolve(history,ref,{'hold_review_evidence'},cutoff=at,inclusive=True)
        if (trigger.review_result!='requires_hold' or trigger.evidence_type!='trigger_observation'
                or trigger.rule not in grant.trigger_rules
                or trigger.source.id!=grant.source_id or trigger.source.version!=grant.source_version):
            raise LiveError('positive_hold_trigger_required')
        triggers.append(trigger)
    closure=[bundle,*[resolve(history,e.ref,cutoff=at,inclusive=True) for e in bundle.evidence_roles],
             *[resolve(history,r,cutoff=at,inclusive=True) for r in [bundle.snapshot_ref,bundle.ownership_ref,*bundle.follow_up_refs]]]
    if any(max(r.event_at,r.recorded_at,r.available_at)>at for r in closure):
        raise LiveError('future_hold_evidence',422)
    source_key=[grant.episode_namespace,bundle.run_id,data.partition_id,bundle.hold_episode_id]
    semantic=[patient_id,*source_key,bundle.lineage_id,bundle.revision,exact_ref(bundle).payload_sha256]
    return dict(bundle=bundle,grant=grant,history=history,source_key=source_key,
        semantic_sha256=object_hash(semantic),triggers=triggers,archive_id=data.archive_id,partition_id=data.partition_id)


def committed_key(db, owner, patient_id, family, key, request_sha256):
    row=db.execute('SELECT k.request_sha256,o.response FROM live_hold_keys k JOIN live_hold_operations o ON k.operation_id=o.id WHERE k.owner_id=? AND k.patient_id=? AND k.family=? AND k.key=?',
        (owner,patient_id,family,key)).fetchone()
    if row:
        if row[0]!=request_sha256:
            raise LiveError('idempotency_conflict')
        return json.loads(row[1])


def alias(db, owner, patient_id, family, key, request_sha256, operation_id):
    db.execute('INSERT INTO live_hold_keys VALUES(?,?,?,?,?,?)',(owner,patient_id,family,key,request_sha256,operation_id))


def semantic_retry(db, semantic, owner, patient_id, family, key, request_sha256):
    row=db.execute('SELECT id,response FROM live_hold_operations WHERE semantic_sha256=?',(semantic,)).fetchone()
    if row:
        alias(db,owner,patient_id,family,key,request_sha256,row[0])
        return json.loads(row[1])


def finish(db, settings, owner, patient_id, family, key, request_sha256, semantic, at, before, payload, operation, *, event_at=None, decision=True):
    from .workflow import create_decision
    receive(db,at)
    operation_id=payload['operation_id']
    fact=append_fact(db,patient_id,operation_id,at,operation,event_at=event_at)
    audit_id='audit-'+uuid.uuid4().hex
    db.execute('INSERT INTO state_changes VALUES(?,?,?,?,?)',(audit_id,patient_id,owner,timestamp(at),canonical(dict(family=family,operation_id=operation_id))))
    db.execute('DELETE FROM drafts WHERE patient_id=?',(patient_id,))
    if settings.fault:
        settings.fault('after_hold_task_audit')
    decision_id=create_decision(db,patient_id,at) if decision else None
    after=patient_row(db,patient_id,owner)
    c=control(db)
    next_sequence=db.execute('SELECT COALESCE(max(sequence),0)+1 FROM live_hold_operations').fetchone()[0]
    response=dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,status='committed',
        operation_id=operation_id,operation_type=family,semantic_sha256=semantic,patient_id=patient_id,owner_id=owner,
        actor_id=owner,authority_generation=c['authority_generation'],authority_sha256=c['authority_sha256'],
        review_rules_sha256=c['review_rules_sha256'],live_received_at=timestamp(at),operation_sequence=next_sequence,
        patient_sequence=fact.patient_sequence,before_versions=before,after_versions=versions(after),decision_id=decision_id,
        audit_id=audit_id,**{k:v for k,v in payload.items() if k!='operation_id'})
    db.execute('INSERT INTO live_hold_operations(id,patient_id,family,semantic_sha256,received_at,payload,response) VALUES(?,?,?,?,?,?,?)',
        (operation_id,patient_id,family,semantic,timestamp(at),canonical(payload),canonical(response)))
    alias(db,owner,patient_id,family,key,request_sha256,operation_id)
    if settings.fault:
        settings.fault('after_hold_version_decision')
        settings.fault('before_hold_commit')
    return response


def advance(db, patient_id, state=None):
    if state is None:
        db.execute('UPDATE patients SET version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1 WHERE id=?',(patient_id,))
    else:
        db.execute('UPDATE patients SET version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1,state_json=? WHERE id=?',(canonical(state),patient_id))


def invalidate(db, settings, owner, patient_id, data, key, at, prepared):
    family='invalidate';request_sha256=object_hash(data.model_dump(mode='json'))
    prior=committed_key(db,owner,patient_id,family,key,request_sha256)
    if prior:
        return prior
    semantic=prepared['semantic_sha256']
    prior=semantic_retry(db,semantic,owner,patient_id,family,key,request_sha256)
    if prior:
        return prior
    patient=patient_row(db,patient_id,owner);before=versions(patient)
    bundle,grant=prepared['bundle'],prepared['grant']
    episode_id='episode-'+object_hash([patient_id,*prepared['source_key']])[:40]
    row=db.execute('SELECT * FROM live_hold_episodes WHERE id=? ORDER BY generation DESC LIMIT 1',(episode_id,)).fetchone()
    active=row and row['status']=='active';generation=row['generation'] if active else row['generation']+1 if row else 1
    e=json.loads(row['payload']) if active else dict(trigger_refs=[],obligations=[],reason_codes=[],trigger_rules=[],grants=[],bundle_refs=[],current_review_id=None)
    # A different hash at the same source lineage/revision is never a new fact.
    for prior_op in db.execute("SELECT payload FROM live_hold_operations WHERE patient_id=? AND family='invalidate'",(patient_id,)):
        p=json.loads(prior_op[0])
        if p['source_key']==prepared['source_key'] and p['bundle_lineage']==bundle.lineage_id and p['bundle_revision']==bundle.revision:
            raise LiveError('hold_evidence_stale')
    trigger_refs=[dict(store='archive',namespace_id=data.archive_id,partition_id=data.partition_id,**r) for r in refs(data.trigger_refs)]
    e['trigger_refs']=sorted({canonical(r):r for r in [*e['trigger_refs'],*trigger_refs]}.values(),key=canonical)
    obligations={r['requirement_id']:r for r in e['obligations']}
    for r in grant.required_reviews:
        value=r.model_dump(mode='json')
        if r.requirement_id in obligations and obligations[r.requirement_id]!=value:
            raise LiveError('hold_requirement_substitution_forbidden')
        obligations[r.requirement_id]=value
    e['obligations']=sorted(obligations.values(),key=lambda r:r['requirement_id'])
    public_obligations=[{k:r[k] for k in ['requirement_id','definition']} for r in e['obligations']]
    e['trigger_set_sha256']=object_hash([generation,e['trigger_refs']])
    e['obligation_set_sha256']=object_hash(public_obligations)
    e['reason_codes']=sorted(set(e['reason_codes'])|set(bundle.reason_codes))
    e['trigger_rules']=sorted({canonical(r):r for r in [*e['trigger_rules'],*[r.rule.model_dump(mode='json') for r in prepared['triggers']]]}.values(),key=canonical)
    e['grants']=sorted({canonical(g):g for g in [*e['grants'],grant.model_dump(mode='json')]}.values(),key=canonical)
    e['bundle_refs'].append(dict(archive_id=data.archive_id,partition_id=data.partition_id,bundle_ref=data.bundle_ref.model_dump(mode='json')))
    e['current_review_id']=None
    operation_id='hold-'+uuid.uuid4().hex
    if not active:
        task_id='hold-review-'+uuid.uuid4().hex;e['task_id']=task_id
        db.execute('INSERT INTO live_hold_tasks VALUES(?,?,?,?,?,?,?)',(task_id,patient_id,episode_id,generation,owner,timestamp(grant.due_at),
            canonical(dict(policy=grant.follow_up_policy.model_dump(mode='json'),escalation_destination=grant.escalation_destination,requirements=e['obligations']))))
        db.execute('INSERT INTO live_hold_episodes VALUES(?,?,?,?,?,?,?,?)',(episode_id,generation,patient_id,canonical(prepared['source_key']),'active',timestamp(at),operation_id,canonical(e)))
    else:
        db.execute('UPDATE live_hold_episodes SET payload=?,last_operation=? WHERE id=? AND generation=?',(canonical(e),operation_id,episode_id,generation))
    if settings.fault:
        settings.fault('after_hold_episode')
    db.execute('INSERT INTO live_hold_task_events VALUES(?,?,?,?)',('task-event-'+uuid.uuid4().hex,e['task_id'],operation_id,canonical(dict(status='pending',trigger_set_sha256=e['trigger_set_sha256'],obligations=e['obligations']))))
    advance(db,patient_id)
    operation=dict(type='invalidate',action='strengthen' if active else 'open',episode_id=episode_id,generation=generation,
        trigger_refs=trigger_refs,active_trigger_refs=e['trigger_refs'],trigger_set_sha256=e['trigger_set_sha256'],reason_codes=e['reason_codes'],
        obligations=public_obligations,obligation_set_sha256=e['obligation_set_sha256'])
    return finish(db,settings,owner,patient_id,family,key,request_sha256,semantic,at,before,
        dict(operation_id=operation_id,episode_id=episode_id,episode_generation=generation,task_ids=[e['task_id']],
            source_key=prepared['source_key'],bundle_lineage=bundle.lineage_id,bundle_revision=bundle.revision,
            package_sha256=grant.package_sha256,archive_id=data.archive_id,partition_id=data.partition_id,
            bundle_ref=data.bundle_ref.model_dump(mode='json'),trigger_refs=trigger_refs),operation,event_at=bundle.event_at)


def episode(db, patient_id, episode_id):
    row=db.execute("SELECT * FROM live_hold_episodes WHERE id=? AND patient_id=? AND status='active'",(episode_id,patient_id)).fetchone()
    if row is None:
        raise LiveError('active_episode_unavailable')
    return row,json.loads(row['payload'])


def current_input(db, patient_id, owner, episode_id, data):
    patient=patient_row(db,patient_id,owner);row,e=episode(db,patient_id,episode_id)
    expected=dict(zip(VERSION_FIELDS,[data.expected_patient_version,data.expected_state_version,data.expected_consent_version,data.expected_eligibility_version]))
    if data.decision_id!=patient['current_decision'] or versions(patient)!=expected:
        raise LiveError('stale_live_hold_review')
    if data.expected_episode_generation!=row['generation'] or data.trigger_set_sha256!=e['trigger_set_sha256']:
        raise LiveError('stale_live_hold_review')
    return patient,row,e


def installed_rules(settings,e):
    selected=[r for r in settings.installed.review_rules.rules if r.trigger_rule.model_dump(mode='json') in e['trigger_rules']]
    complete=all(any(r.trigger_rule.model_dump(mode='json')==t for r in selected) for t in e['trigger_rules'])
    return selected,complete


def evidence_access(db, settings, patient_id, owner, episode_id, ref, at):
    if ref.store=='archive':
        stored,_,_,_=configured_archive(settings,db,ref.namespace_id,owner)
        h=archive_history(db,ref.namespace_id,ref.partition_id,patient_id)
        from contracts.domain.observed_v2 import ExactRef
        value=resolve(h,ExactRef(record_id=ref.record_id,payload_sha256=ref.payload_sha256),cutoff=at,inclusive=True)
        receipt_id=ref.namespace_id;receipt_sha256=digest(stored['receipt'])
        grant=next((g for g in settings.installed.authority.grants if g.archive_id==ref.namespace_id and g.partition_id==ref.partition_id and g.service_patient_id==patient_id and g.account_id==owner and g.package_sha256==stored['export_sha256']),None)
        if grant is None:
            raise LiveError('live_source_grant_unavailable')
        source=value.model_dump(mode='json')
    elif ref.store=='event':
        if ref.namespace_id!=patient_id:
            raise LiveError('not_found',404)
        from .workflow import history
        from contracts.domain.observed_v2 import ExactRef
        value=resolve(history(db,patient_id),ExactRef(record_id=ref.record_id,payload_sha256=ref.payload_sha256),cutoff=at,inclusive=True)
        source=value.model_dump(mode='json');receipt_id=ref.record_id;receipt_sha256=ref.payload_sha256
    else:
        if ref.namespace_id!=patient_id:
            raise LiveError('not_found',404)
        review=db.execute('SELECT * FROM live_hold_reviews WHERE id=? AND patient_id=? AND episode_id=?',(ref.record_id,patient_id,episode_id)).fetchone()
        if review is None or review['payload_sha256']!=ref.payload_sha256:
            raise LiveError('hold_evidence_stale')
        value=json.loads(review['payload']);source=dict(kind='live_review',source=dict(id='authenticated-owning-doctor'),
            event_at=value['current_review_at'],recorded_at=value['current_review_at'],available_at=value['current_review_at'])
        receipt=db.execute('SELECT sequence,id FROM live_hold_operations WHERE id=?',(review['operation_id'],)).fetchone()
        if receipt is None:
            raise LiveError('hold_dependencies_unavailable')
        receipt_id=receipt['id'];receipt_sha256=ref.payload_sha256
    if any(instant(source[k])>at for k in ['event_at','recorded_at','available_at']):
        raise LiveError('future_hold_evidence',422)
    return dict(reference=ref.model_dump(mode='json'),kind=source['kind'],source_id=source['source']['id'],
        event_at=source['event_at'],recorded_at=source['recorded_at'],available_at=source['available_at'],
        committed_object_id=receipt_id,committed_receipt_sha256=receipt_sha256,verified_visible_at=timestamp(at),
        authority_generation=control(db)['authority_generation'])


def prepare_review(db, settings, owner, patient_id, episode_id, data, at):
    patient,row,e=current_input(db,patient_id,owner,episode_id,data)
    latest=db.execute('SELECT received_at FROM live_safety_facts WHERE patient_id=? ORDER BY patient_sequence DESC LIMIT 1',(patient_id,)).fetchone()
    if at<instant(row['opened_at']) or (latest and at<instant(latest[0])):
        raise LiveError('service_clock_regression')
    rules,complete=installed_rules(settings,e)
    if refs(data.review_rules)!=refs([r.ref for r in rules]):
        raise LiveError('clearance_rule_unavailable')
    required={r['requirement_id']:r for r in e['obligations']}
    if len(data.items)!=len(required) or {i.requirement_id for i in data.items}!=set(required):
        raise LiveError('all_active_obligations_required')
    proofs=[];all_satisfied=complete
    for item in data.items:
        requirement=required[item.requirement_id]
        if item.definition.model_dump(mode='json')!=requirement['definition']:
            raise LiveError('hold_requirement_mismatch')
        supported=any(any(r.requirement_id==item.requirement_id and r.definition==item.definition for r in rule.requirements) for rule in rules)
        if item.result=='satisfied' and (not supported or not item.evidence_refs):
            raise LiveError('clearance_rule_unavailable')
        all_satisfied &= item.result=='satisfied' and supported
        for reference in refs(item.evidence_refs):
            proof=evidence_access(db,settings,patient_id,owner,episode_id,EvidenceRef.model_validate(reference),at)
            if proof['kind'] not in requirement['evidence_kinds'] or proof['source_id'] not in requirement['source_ids']:
                raise LiveError('hold_requirement_evidence_mismatch')
            proofs.append(proof)
    return dict(proofs=proofs,result='satisfied' if all_satisfied else 'pending',rules=[r.ref.model_dump(mode='json') for r in rules],
        evidence_head_sha256=object_hash(proofs),input_versions=versions(patient))


def record_review(db,settings,owner,patient_id,episode_id,data,key,at,prepared):
    family='review';request_sha256=object_hash(data.model_dump(mode='json'))
    prior=committed_key(db,owner,patient_id,family,key,request_sha256)
    if prior:
        return prior
    semantic=object_hash([family,patient_id,episode_id,data.model_dump(mode='json')])
    prior=semantic_retry(db,semantic,owner,patient_id,family,key,request_sha256)
    if prior:
        return prior
    patient,row,e=current_input(db,patient_id,owner,episode_id,data)
    review_id='review-'+uuid.uuid4().hex;operation_id='review-op-'+uuid.uuid4().hex
    review=dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,review_id=review_id,episode_id=episode_id,
        generation=row['generation'],actor_id=owner,current_review_at=timestamp(at),recorded_at=timestamp(at),available_at=timestamp(at),
        authority_generation=control(db)['authority_generation'],authority_sha256=control(db)['authority_sha256'],review_rules_sha256=control(db)['review_rules_sha256'],
        trigger_set_sha256=e['trigger_set_sha256'],obligation_set_sha256=e['obligation_set_sha256'],**prepared,
        rationale=data.rationale,current_assessment_attested=True,items=[i.model_dump(mode='json') for i in data.items])
    encoded=canonical(review);review_sha256=digest(encoded)
    db.execute('INSERT INTO live_hold_reviews VALUES(?,?,?,?,?,?,?)',(review_id,patient_id,episode_id,row['generation'],operation_id,encoded,review_sha256))
    e['current_review_id']=review_id
    db.execute('UPDATE live_hold_episodes SET payload=?,last_operation=? WHERE id=? AND generation=?',(canonical(e),operation_id,episode_id,row['generation']))
    advance(db,patient_id)
    return finish(db,settings,owner,patient_id,family,key,request_sha256,semantic,at,versions(patient),
        dict(operation_id=operation_id,review_id=review_id,review_sha256=review_sha256,episode_id=episode_id,episode_generation=row['generation'],task_ids=[e['task_id']]),
        dict(type='review_recorded',episode_id=episode_id,generation=row['generation'],review_id=review_id,review_sha256=review_sha256,
            current_review_at=timestamp(at),trigger_set_sha256=e['trigger_set_sha256'],obligation_set_sha256=e['obligation_set_sha256'],
            rule_refs=prepared['rules'],result=prepared['result']))


def clear_episode(db,settings,owner,patient_id,episode_id,data,key,at):
    family='clearance';request_sha256=object_hash(data.model_dump(mode='json'))
    prior=committed_key(db,owner,patient_id,family,key,request_sha256)
    if prior:
        return prior
    semantic=object_hash([family,patient_id,episode_id,data.expected_episode_generation,data.review_sha256,refs(data.review_rules)])
    prior=semantic_retry(db,semantic,owner,patient_id,family,key,request_sha256)
    if prior:
        return prior
    patient,row,e=current_input(db,patient_id,owner,episode_id,data)
    rules,complete=installed_rules(settings,e)
    if not complete or refs(data.review_rules)!=refs([r.ref for r in rules]):
        raise LiveError('clearance_rule_unavailable')
    saved=db.execute('SELECT * FROM live_hold_reviews WHERE id=? AND patient_id=? AND episode_id=?',(data.review_id,patient_id,episode_id)).fetchone()
    if saved is None or saved['payload_sha256']!=data.review_sha256 or e['current_review_id']!=data.review_id:
        raise LiveError('stale_live_hold_review')
    review=json.loads(saved['payload']);c=control(db)
    operation=db.execute('SELECT response FROM live_hold_operations WHERE id=?',(saved['operation_id'],)).fetchone()
    response=json.loads(operation[0])
    if (review['result']!='satisfied' or review['actor_id']!=owner or review['generation']!=row['generation']
            or any(review[k]!=c[k] for k in ['authority_generation','authority_sha256','review_rules_sha256'])
            or response['after_versions']!=versions(patient) or response['decision_id']!=patient['current_decision']
            or review['trigger_set_sha256']!=e['trigger_set_sha256'] or review['obligation_set_sha256']!=e['obligation_set_sha256']):
        raise LiveError('stale_live_hold_review')
    if instant(review['current_review_at'])>at:
        raise LiveError('service_clock_regression')
    for proof in review['proofs']:
        # Exact heads must still resolve; present access time does not backdate review.
        evidence_access(db,settings,patient_id,owner,episode_id,EvidenceRef.model_validate(proof['reference']),at)
    operation_id='clear-'+uuid.uuid4().hex
    db.execute("UPDATE live_hold_episodes SET status='closed',last_operation=? WHERE id=? AND generation=?",(operation_id,episode_id,row['generation']))
    db.execute('INSERT INTO live_hold_task_events VALUES(?,?,?,?)',('task-event-'+uuid.uuid4().hex,e['task_id'],operation_id,canonical(dict(status='closed',review_id=data.review_id))))
    from .workflow import state_for,current_safety
    held=any(r.kind=='intercurrent_event' and r.event_type in ('death','admission','regimen_change','steroid_change','fever_suspected_infection','confusion','fall') for r in current_safety(db,patient_id,at))
    state=state_for('ASSIGN-09' if held else 'ASSIGN-01','Known safety event requires clinical review')
    state['workflow'].update(data_readiness='stale' if held else 'incomplete',support_mode='paused')
    state['plan']=json.loads(patient['state_json'])['plan']
    advance(db,patient_id,state)
    return finish(db,settings,owner,patient_id,family,key,request_sha256,semantic,at,versions(patient),
        dict(operation_id=operation_id,episode_id=episode_id,episode_generation=row['generation'],task_ids=[e['task_id']],review_id=data.review_id),
        dict(type='clearance',episode_id=episode_id,generation=row['generation'],review_id=data.review_id,review_sha256=data.review_sha256,
            trigger_set_sha256=e['trigger_set_sha256'],obligation_set_sha256=e['obligation_set_sha256'],rule_refs=refs(data.review_rules)))
