"""Whole verified package -> atomic archive/clinical/latch projection."""
import json
import uuid
from contracts.domain.evidence_v2 import exact_ref
from contracts.runs.observed_v2 import CLINICAL_KINDS
from contracts.service.live_hold import InvalidationInput
from .archive import persist_archive,verify_archive
from .live_hold import LiveError,alias,committed_key,invalidate,object_hash,patient_row,prepare_invalidation,versions,authorized_invalidation_retry
from .live_journal import receive
from .replay import append_event
from .store import canonical,digest,instant,timestamp


def project_archive(store,settings,raw,root,authority,*,owner_id,key,authorize):
    package=verify_archive(raw,root,authority)
    archive_id=package.manifest.run_id+':'+package.manifest.id
    intent=object_hash(dict(archive_id=archive_id,manifest_sha256=digest(raw),mode='clinical_observation_import'))
    patients=sorted({p.patient_id for p,*_ in package.partitions})
    if not patients:
        raise LiveError('hold_dependencies_unavailable')
    prepared={}
    def historical(db):
        for patient_id in patients:patient_row(db,patient_id,owner_id)
        prior=committed_key(db,owner_id,patients[0],'import',key,intent)
        saved=db.execute('SELECT payload FROM live_projection_receipts WHERE archive_id=? AND manifest_sha256=? AND projection_version=?',(archive_id,digest(raw),'LIVE-HOLD-01/1.0.0')).fetchone()
        response=prior or (json.loads(saved[0]) if saved else None)
        if response is None:return None
        if not settings.installed.control.enabled or not settings.installed.authority.enabled:raise LiveError('independent_hold_live_integration_required')
        for partition,history,*_ in package.partitions:
            for bundle in history.records:
                if bundle.kind!='hold_transition_bundle' or bundle.transition_type not in ('enter','change_reason'):continue
                command=InvalidationInput.model_validate_json(canonical(dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,
                    archive_id=archive_id,partition_id=partition.id,bundle_ref=exact_ref(bundle).model_dump(mode='json'),trigger_refs=[r.model_dump(mode='json') for r in bundle.trigger_refs])))
                if authorized_invalidation_retry(db,settings,owner_id,partition.patient_id,command) is None:raise LiveError('live_source_grant_unavailable')
        return response,bool(prior)
    def discover(db,at):
        if package.manifest.cutoff>at:
            raise LiveError('future_hold_evidence',422)
        commands=[]
        for partition,history,*_ in package.partitions:
            patient_row(db,partition.patient_id,owner_id)
            bundles=[r for r in history.records if r.kind=='hold_transition_bundle' and r.transition_type in ('enter','change_reason')]
            covered_triggers={r.record_id for b in bundles for r in b.trigger_refs}
            covered_snapshots={b.snapshot_ref.record_id for b in bundles}
            for r in history.records:
                if (r.kind=='hold_review_evidence' and r.review_result=='requires_hold' and r.record_id not in covered_triggers
                        or r.kind=='decision_snapshot' and (r.workflow.clinical=='clinical_hold' or r.workflow.hold_reasons) and r.record_id not in covered_snapshots):
                    raise LiveError('hold_dependencies_unavailable')
            for bundle in sorted(bundles,key=lambda b:(b.transition_sequence,b.run_id,partition.id,b.hold_episode_id,b.record_id)):
                command=InvalidationInput.model_validate_json(canonical(dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,
                    archive_id=archive_id,partition_id=partition.id,bundle_ref=exact_ref(bundle).model_dump(mode='json'),trigger_refs=[r.model_dump(mode='json') for r in bundle.trigger_refs])))
                value=prepare_invalidation(settings,db,owner_id,partition.patient_id,command,at,_verified_package=package)
                commands.append((partition.patient_id,command,value))
        return commands
    def prepare(db):
        authorize(db)
        prepared['history']=historical(db)
        prepared['commands']=[] if prepared['history'] else discover(db,settings.clock())
        prepared['at']=settings.clock()
        if prepared['at']<instant(store.validate_control(db)['last_receipt_at']):
            raise LiveError('service_clock_regression')
    with store.transaction(write=True,prepare=prepare,authorize=authorize) as db:
        at=prepared['at'];prior=historical(db)
        if prior:
            response,key_exists=prior
            if not key_exists:
                for patient_id in patients:alias(db,owner_id,patient_id,'import',key,intent,response['operation_id'])
            return response
        commands=discover(db,at)
        before={pid:versions(patient_row(db,pid,owner_id)) for pid in patients}
        persist_archive(db,package,owner_id=owner_id,received_at=at,installed=settings.installed)
        clinical_counts={pid:0 for pid in patients}
        remaining=[e for _,_,batch,*_ in package.partitions for e in batch.entries if e.record.kind in CLINICAL_KINDS]
        remaining.sort(key=lambda e:(e.record.available_at,e.record.recorded_at,e.record.record_id))
        while remaining:
            ids={e.record.record_id for e in remaining}
            entry=next((e for e in remaining if not ({e.record.supersedes,e.record.duplicate_of}-{None})&ids),None)
            if entry is None:
                raise LiveError('clinical_lineage_dependency_cycle')
            if append_event(db,entry.record,entry.raw_source.encode(),received_at=at):
                clinical_counts[entry.record.patient_id]+=1
            remaining.remove(entry)
        novel={pid:0 for pid in patients}
        for pid,_,value in commands:
            if not db.execute('SELECT 1 FROM live_hold_operations WHERE semantic_sha256=?',(value['semantic_sha256'],)).fetchone():
                novel[pid]+=1
        final_ids={pid:'decision-'+digest(canonical([pid,before[pid]['version']+clinical_counts[pid]+novel[pid],timestamp(at)]))[:32] for pid in patients}
        transitions=[]
        for ordinal,(pid,command,value) in enumerate(commands):
            transitions.append(dict(ordinal=ordinal,receipt=invalidate(db,settings,owner_id,pid,command,
                'projection-'+digest(canonical([archive_id,ordinal]))[:48],at,value,_final_decision_id=final_ids[pid])))
        from .workflow import create_decision,state_for,current_safety
        for pid in patients:
            count=clinical_counts[pid]
            if count:
                row=patient_row(db,pid,owner_id)
                state=json.loads(row['state_json'])
                if any(r.kind=='intercurrent_event' and r.event_type in ('death','admission','regimen_change','steroid_change','fever_suspected_infection','confusion','fall') for r in current_safety(db,pid,at)):
                    state=state_for('ASSIGN-09','Known safety event requires clinical review');state['plan']=json.loads(row['state_json'])['plan']
                db.execute('UPDATE patients SET version=version+?,state_version=state_version+?,eligibility_version=eligibility_version+?,state_json=? WHERE id=?',(count,count,count,canonical(state),pid))
            if count or novel[pid]:
                actual=create_decision(db,pid,at)
                if actual!=final_ids[pid]:raise LiveError('projection_final_decision_mismatch')
        receive(db,at)
        operation_id='projection-'+uuid.uuid4().hex
        response=dict(status='live_projection_committed',operation_id=operation_id,archive_id=archive_id,manifest_sha256=digest(raw),
            live_received_at=timestamp(at),patients={pid:dict(before_versions=before[pid],after_versions=versions(patient_row(db,pid,owner_id)),
                clinical_insertions=clinical_counts[pid],novel_hold_transitions=novel[pid],decision_id=patient_row(db,pid,owner_id)['current_decision']) for pid in patients},transitions=transitions)
        db.execute('INSERT INTO live_hold_operations(id,patient_id,family,semantic_sha256,received_at,payload,response) VALUES(?,?,?,?,?,?,?)',
            (operation_id,patients[0],'import',object_hash(['projection',archive_id,digest(raw)]),timestamp(at),canonical(dict(archive_id=archive_id)),canonical(response)))
        for pid in patients:alias(db,owner_id,pid,'import',key,intent,operation_id)
        db.execute('INSERT INTO live_projection_receipts VALUES(?,?,?,?,?)',(operation_id,archive_id,digest(raw),'LIVE-HOLD-01/1.0.0',canonical(response)))
        if settings.fault:
            settings.fault('before_archive_commit');settings.fault('before_projection_commit')
    if settings.fault:settings.fault('after_projection_commit')
    return response
