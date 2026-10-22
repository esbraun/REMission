"""Host-only genuine research enrollment, resumable replay and registration.

No public route, generated consent, live approval, executable grant or new store.
The independently configured ExportAuthority is never taken from the upload.
"""
import json

from contracts.runs.admission import verify_export
from contracts.runs.common import ExportAuthority, restricted_profile
from .cohort_registration import _key, register, registration
from .live_journal import initialize_journal
from .replay import replay_export
from .store import canonical, digest, instant, timestamp
from .workflow import create_decision, state_for


def _selection(raw, root, authority, cohort_id):
    if type(authority) is not ExportAuthority or authority.allow_contract_fixture:
        raise ValueError('Independent engine-only v1 authority required for research enrollment')
    public,partitions=verify_export(raw,root,authority)
    if public.status!='complete' or public.execution!='engine_run' or not restricted_profile(public.bindings,public.runtime):
        raise ValueError('Complete genuine restricted research export required')
    selected=[p for p in partitions if p[0].cohort_id==cohort_id]
    if len(selected)!=12 or len(selected)!=len(partitions):raise ValueError('Exact research cohort required')
    return public,selected


def _identity(public, partition, owner):
    return dict(kind='trusted_research_enrollment',owner_id=owner,run_id=public.run_id,unit_id=partition.unit_id,
        cohort_id=partition.cohort_id,replicate=partition.replicate,patient_id=partition.patient_id,
        run_manifest_sha256=public.run_manifest.sha256)


def _enrollment_key(patient):return 'research-enrollment-'+digest(patient)


def _check_row(db, owner, public, partition):
    row=db.execute('SELECT * FROM patients WHERE id=?',(partition.patient_id,)).fetchone()
    marker=db.execute('SELECT patient_id,actor_id,payload FROM state_changes WHERE id=?',(_enrollment_key(partition.patient_id),)).fetchone()
    if (row is None or row['owner_id']!=owner or 'simulation' in json.loads(row['state_json']) or marker is None
            or marker['patient_id']!=partition.patient_id or marker['actor_id']!=owner
            or json.loads(marker['payload'])!=_identity(public,partition,owner)):
        raise ValueError('Research enrollment owner/identity conflict; interactive or unrelated row rejected')
    return row


def enroll_replay_register(store, owner, manifest_bytes, artifact_root, authority, *, cohort_id, batch_size=100, fault=None):
    public,selected=_selection(manifest_bytes,artifact_root,authority,cohort_id)
    # Verification above completes before the first database mutation.
    with store.transaction(write=True) as db:
        if db.execute('SELECT 1 FROM accounts WHERE id=?',(owner,)).fetchone() is None:raise ValueError('Existing administrative owner required')
        for partition,_,_,projection,*_ in selected:
            if db.execute('SELECT 1 FROM patients WHERE id=?',(partition.patient_id,)).fetchone() is None:
                # Ordinary incomplete workflow: historical study allocation
                # cannot grant live readiness, consent or physician approval.
                origin=min(r.recall_end for r in projection.records if r.kind=='isi')
                from datetime import timedelta
                origin+=timedelta(hours=1)
                db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',(partition.patient_id,owner,
                    'Synthetic research member',1,1,1,1,canonical(state_for('ASSIGN-01')),None,timestamp(origin)))
                initialize_journal(db,partition.patient_id,store.clock())
                create_decision(db,partition.patient_id,origin)
                db.execute('INSERT INTO state_changes VALUES(?,?,?,?,?)',(_enrollment_key(partition.patient_id),
                    partition.patient_id,owner,timestamp(store.clock()),canonical(_identity(public,partition,owner))))
            _check_row(db,owner,public,partition)
        key=_key(owner,public.run_id,cohort_id,timestamp(public.cutoff))
        prior=db.execute('SELECT payload FROM state_changes WHERE id=?',(key+'-00',)).fetchone()
        if prior:
            value=json.loads(prior['payload'])
            if value['authority']!=authority.model_dump(mode='json'):raise ValueError('Research registration is immutable')
            registration(db,owner,public.run_id,cohort_id,timestamp(public.cutoff))
            return dict(run_id=public.run_id,cohort_id=cohort_id,manifest_sha256=value['cohort']['manifest_sha256'],
                members=12,execution=public.execution,executable=False)
    if fault:fault('after_enrollment')
    replay_export(store,manifest_bytes,artifact_root,authority,batch_size=batch_size,fault=fault,preserve_cutoff=True)
    # Replay owns its own batch transactions. Only a completed verified replay
    # may advance the reached cutoff; the version bump and marker are atomic.
    with store.transaction(write=True) as db:
        replay=db.execute('SELECT * FROM replay_runs WHERE id=?',(f'{public.run_id}:{public.id}',)).fetchone()
        if replay is None or replay['cursor']!=replay['record_count'] or instant(replay['cutoff'])!=public.cutoff:
            raise ValueError('Complete verified replay required before cutoff advance')
        for partition,*_ in selected:
            row=_check_row(db,owner,public,partition)
            marker='research-cutoff-'+digest(canonical([owner,public.run_id,public.id,partition.patient_id]))
            payload=dict(kind='trusted_research_cutoff',export_sha256=authority.export_sha256,cutoff=timestamp(public.cutoff))
            old=db.execute('SELECT payload FROM state_changes WHERE id=?',(marker,)).fetchone()
            if old:
                if json.loads(old['payload'])!=payload or instant(row['cutoff'])<public.cutoff:raise ValueError('Research cutoff receipt conflict')
            else:
                if instant(row['cutoff'])>public.cutoff:raise ValueError('Research cutoff cannot regress')
                if instant(row['cutoff'])<public.cutoff:
                    db.execute('UPDATE patients SET cutoff=?,version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1 WHERE id=?',
                        (timestamp(public.cutoff),partition.patient_id))
                    create_decision(db,partition.patient_id,public.cutoff)
                db.execute('INSERT INTO state_changes VALUES(?,?,?,?,?)',(marker,partition.patient_id,owner,timestamp(store.clock()),canonical(payload)))
        if fault:fault('before_cutoff_commit')
        versions={p[0].patient_id:db.execute('SELECT version FROM patients WHERE id=?',(p[0].patient_id,)).fetchone()[0] for p in selected}
    if fault:fault('before_registration')
    return register(store,owner,manifest_bytes,artifact_root,authority,cohort_id=cohort_id,patient_versions=versions)
