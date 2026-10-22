"""Authenticated caller's complete original-byte archive, with one atomic receipt."""
from contracts.runs.admission_v2 import verify_export_v2
from contracts.runs.common import read_artifact
from contracts.runs.observed_v2 import CLINICAL_KINDS
from .replay import append_event, apply_current_state, preflight_current
from .store import canonical, digest, timestamp
from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedArchive:
    raw: bytes
    root: object
    authority: object
    manifest: object
    partitions: tuple


def verify_archive(raw,root,authority):
    manifest,partitions=verify_export_v2(raw,root,authority)
    return VerifiedArchive(raw,root,authority,manifest,tuple(partitions))


def persist_archive(db,package,*,owner_id,received_at):
    """Private coordinator staging, always an unchanged read-only archive receipt."""
    from contracts.runs.common import read_artifact
    manifest,partitions=package.manifest,package.partitions
    identifier=manifest.run_id+':'+manifest.id
    prior=db.execute('SELECT * FROM observed_archives WHERE id=?',(identifier,)).fetchone()
    if prior:
        if prior['export_sha256']!=digest(package.raw) or prior['owner_id']!=owner_id:
            raise ValueError('immutable_archive_idempotency_conflict')
        return identifier
    entries=[(partition,entry) for partition,_,batch,*_ in partitions for entry in batch.entries]
    receipt=dict(status='archived_read_only',archive_id=identifier,export_sha256=digest(package.raw),records=len(entries),cursor=len(entries),
        mode='archive_only',live_authority_granted=False,received_at=timestamp(received_at),hold_intervals={})
    from contracts.domain.evidence_v2 import reconstruct_hold
    from datetime import timedelta
    for partition,history,*_ in partitions:
        if any(r.kind=='hold_transition_bundle' for r in history.records):
            intervals=reconstruct_hold(history,manifest.cutoff+timedelta(microseconds=1))
            receipt['hold_intervals'][partition.patient_id]=[{k:timestamp(v) if k in ('starts_at','ends_at') and v is not None else v for k,v in interval.items()} for interval in intervals]
    db.execute('INSERT INTO observed_archives VALUES(?,?,?,?,?,?,?,?,?)',(identifier,owner_id,digest(package.raw),package.raw,'archive_only',timestamp(received_at),len(entries),len(entries),canonical(receipt)))
    for ordinal,(partition,entry) in enumerate(entries):
        r=entry.record;payload=canonical(r.model_dump(mode='json')).encode();source=entry.raw_source.encode()
        db.execute('INSERT INTO observed_archive_entries VALUES(?,?,?,?,?,?,?,?,?,?,?)',(identifier,partition.id,ordinal,r.patient_id,r.record_id,r.schema_version,r.kind,payload,digest(payload),source,digest(source)))
    for partition,*_ in partitions:
        for artifact in [partition.history,partition.replay,partition.coverage,*partition.stage_ledgers,*partition.completion_receipts,*partition.mechanisms]:
            payload=read_artifact(package.root,artifact,artifact.role)
            db.execute('INSERT INTO observed_archive_artifacts VALUES(?,?,?,?)',(identifier,artifact.path,payload,digest(payload)))
    return identifier


def archive_export(store, raw, artifact_root, authority, *, owner_id, received_at, mode='archive_only', fault=None, authorize=None):
    if mode not in ('archive_only', 'clinical_observation_import'):
        raise ValueError('unsupported_archive_mode')
    manifest, partitions = verify_export_v2(raw, artifact_root, authority)
    if manifest.cutoff > received_at:
        raise ValueError('archive receipt cannot precede declared source cutoff')
    entries = [(partition, entry) for partition, _, batch, *_ in partitions for entry in batch.entries]
    # Entire partition preflight precedes even an archive cursor in current mode.
    if mode == 'clinical_observation_import':
        preflight_current([entry.record for _, entry in entries])
    identifier = manifest.run_id + ':' + manifest.id
    with store.transaction(write=True) as db:
        if authorize:
            authorize(db)
        for partition, *_ in partitions:
            if db.execute('SELECT 1 FROM patients WHERE id=? AND owner_id=?', (partition.patient_id, owner_id)).fetchone() is None:
                raise ValueError('archive_patient_ownership_required')
        prior = db.execute('SELECT * FROM observed_archives WHERE id=?', (identifier,)).fetchone()
        if prior:
            if prior['export_sha256'] != digest(raw) or prior['owner_id'] != owner_id or prior['mode'] != mode:
                raise ValueError('immutable_archive_idempotency_conflict')
            import json
            return json.loads(prior['receipt'])
        receipt = dict(status='archived_read_only' if mode == 'archive_only' else 'clinical_subset_imported', archive_id=identifier,
                       export_sha256=digest(raw), records=len(entries), cursor=len(entries), mode=mode,
                       live_authority_granted=False, received_at=timestamp(received_at))
        from contracts.domain.evidence_v2 import reconstruct_hold
        from datetime import timedelta
        receipt['hold_intervals'] = {}
        for partition, history, *_ in partitions:
            if any(r.kind == 'hold_transition_bundle' for r in history.records):
                intervals = reconstruct_hold(history, manifest.cutoff + timedelta(microseconds=1))
                receipt['hold_intervals'][partition.patient_id] = [{k: timestamp(v) if k in ('starts_at', 'ends_at') and v is not None else v for k, v in interval.items()} for interval in intervals]
        db.execute('INSERT INTO observed_archives VALUES(?,?,?,?,?,?,?,?,?)',
                   (identifier, owner_id, digest(raw), raw, mode, timestamp(received_at), len(entries), len(entries), canonical(receipt)))
        changed = {}
        # Original archive order is retained. Clinical dependency order is separate.
        for ordinal, (partition, entry) in enumerate(entries):
            record = entry.record
            payload = canonical(record.model_dump(mode='json')).encode()
            source = entry.raw_source.encode('utf-8')
            db.execute('INSERT INTO observed_archive_entries VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (identifier, partition.id, ordinal, record.patient_id, record.record_id, record.schema_version, record.kind,
                        payload, digest(payload), source, digest(source)))
        for partition, *_ in partitions:
            for artifact in [partition.history, partition.replay, partition.coverage, *partition.stage_ledgers, *partition.completion_receipts, *partition.mechanisms]:
                payload = read_artifact(artifact_root, artifact, artifact.role)
                db.execute('INSERT INTO observed_archive_artifacts VALUES(?,?,?,?)', (identifier, artifact.path, payload, digest(payload)))
        if mode == 'clinical_observation_import':
            remaining = [entry for _, entry in entries if entry.record.kind in CLINICAL_KINDS]
            remaining.sort(key=lambda e: (e.record.available_at, e.record.recorded_at, e.record.record_id))
            while remaining:
                ids = {e.record.record_id for e in remaining}
                ready = next((e for e in remaining if not ({e.record.supersedes, e.record.duplicate_of} - {None}) & ids), None)
                if ready is None:
                    raise ValueError('clinical_lineage_dependency_cycle')
                if append_event(db, ready.record, ready.raw_source.encode('utf-8'), received_at=received_at):
                    changed[ready.record.patient_id] = changed.get(ready.record.patient_id, 0) + 1
                remaining.remove(ready)
            for patient_id, count in sorted(changed.items()):
                apply_current_state(db, patient_id, received_at, advance_by=count)
        if fault:
            fault('before_archive_commit')
    if fault:
        fault('after_archive_commit')
    return receipt
