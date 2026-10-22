"""Exact administrative follow-up amendments; no source resolution clears a latch."""
from dataclasses import replace
import json
from contracts.domain.evidence_v2 import exact_ref,validate_hold
from contracts.service.live_hold import InvalidationInput
from .live_hold import (LiveError,configured_archive,current_archive_history,current_reference,current_closure,
    object_hash,prepare_invalidation,patient_row)
from .live_tasks import binding_value
from .store import canonical,digest,timestamp


def validate_amendments(db,new_bundle,settings,at):
    amendments=new_bundle.authority.follow_up_amendments
    if not amendments:return []
    if settings is None:raise LiveError('cutover_archive_configuration_required')
    configured=replace(settings,installed=new_bundle)
    old=db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone()
    result=[]
    for amendment in amendments:
        row=db.execute("SELECT * FROM live_hold_episodes WHERE id=? AND generation=? AND patient_id=? AND status='active'",
            (amendment.episode_id,amendment.episode_generation,amendment.service_patient_id)).fetchone()
        if row is None:raise LiveError('followup_amendment_target_unavailable')
        e=json.loads(row['payload']);owner=amendment.owner_id;grant=amendment.grant
        patient_row(db,amendment.service_patient_id,owner)
        if (amendment.prior_authority_generation!=old['authority_generation']
                or amendment.prior_authority_sha256!=old['authority_sha256']
                or amendment.prior_review_rules_sha256!=old['review_rules_sha256']
                or amendment.prior_trigger_set_sha256!=e['trigger_set_sha256']
                or amendment.prior_obligation_set_sha256!=e['obligation_set_sha256']
                or list(amendment.source_key)!=json.loads(row['source_key'])
                or not any(g['source_id']==amendment.source_id and g['source_version']==amendment.source_version for g in e['grants'])):
            raise LiveError('stale_followup_amendment')
        namespace,run_id,partition,archive_episode=amendment.source_key
        if (grant not in new_bundle.authority.grants or 'invalidate' not in grant.allowed_operations
                or (grant.account_id,grant.service_patient_id,grant.archive_patient_id,grant.episode_namespace,
                    grant.run_id,grant.partition_id,grant.source_id,grant.source_version)!=
                   (owner,amendment.service_patient_id,amendment.service_patient_id,namespace,run_id,partition,amendment.source_id,amendment.source_version)):
            raise LiveError('followup_amendment_source_scope')
        stored,manifest,partitions,archive_authority=configured_archive(configured,db,grant.archive_id,owner)
        if (stored['export_sha256']!=grant.package_sha256 or object_hash(archive_authority.model_dump(mode='json'))!=grant.archive_authority_sha256
                or manifest.cutoff>at):raise LiveError('followup_amendment_package_mismatch')
        # Every partition's positive transitions have already traversed the
        # ordinary authenticated coordinator/invalidation admission.
        for part,history,*_ in partitions:
            patient_row(db,part.patient_id,owner)
            for bundle in history.records:
                if bundle.kind!='hold_transition_bundle' or bundle.transition_type not in ('enter','change_reason'):continue
                command=InvalidationInput.model_validate_json(canonical(dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,
                    archive_id=grant.archive_id,partition_id=part.id,bundle_ref=exact_ref(bundle).model_dump(mode='json'),trigger_refs=[r.model_dump(mode='json') for r in bundle.trigger_refs])))
                prepared=prepare_invalidation(configured,db,owner,part.patient_id,command,at)
                if not db.execute('SELECT 1 FROM live_hold_operations WHERE semantic_sha256=?',(prepared['semantic_sha256'],)).fetchone():
                    raise LiveError('followup_amendment_unadmitted_positive')
        h=current_archive_history(configured,db,grant.archive_id,partition,amendment.service_patient_id)
        bundle=current_reference(h,amendment.source_bundle_ref,at,{'hold_transition_bundle'})
        if ((bundle.run_id,bundle.partition_id,bundle.hold_episode_id,bundle.patient_id,bundle.source.id,bundle.source.version,bundle.owner_id,bundle.owner_role)!=
                (run_id,partition,archive_episode,amendment.service_patient_id,amendment.source_id,amendment.source_version,owner,'doctor')
                or bundle.ownership_ref!=grant.ownership_ref or amendment.follow_up.reference not in bundle.follow_up_refs):
            raise LiveError('followup_amendment_episode_scope')
        try:validate_hold(h,bundle)
        except ValueError as error:raise LiveError('hold_evidence_stale') from error
        current_closure(h,bundle,at)
        task=current_reference(h,amendment.follow_up.reference,at,{'follow_up'})
        follow=amendment.follow_up
        if ((task.owner,follow.owner_id,task.due_at,task.escalation_destination,task.source.id,task.source.version)!=
                (owner,owner,follow.due_at,follow.escalation_destination,amendment.source_id,amendment.source_version)):
            raise LiveError('hold_follow_up_mismatch')
        result.append(dict(episode_id=row['id'],generation=row['generation'],grant=grant.model_dump(mode='json'),
            binding=binding_value(grant,follow,archive_episode),amendment=amendment.model_dump(mode='json'),
            proof=dict(archive_id=grant.archive_id,archive_receipt_sha256=digest(stored['receipt']),manifest_sha256=grant.package_sha256,
                bundle_ref=amendment.source_bundle_ref.model_dump(mode='json'),follow_up_ref=follow.reference.model_dump(mode='json'),
                verified_visible_at=timestamp(at),prior_authority_generation=old['authority_generation'])))
    return result
