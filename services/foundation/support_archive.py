"""Configured, immutable historical support intake; no live event replay.

All public proof stays in the existing archive tables. This module never
initializes a journal/decision, imports a generator, or grants current consent.
"""
from dataclasses import dataclass
from datetime import timedelta
import json
from pathlib import Path
import stat

from contracts.domain.protocol import ObservedHistoryV21
from contracts.runs.common import Artifact,canonical as canonical_bytes, sha256
from contracts.runs.coverage_v2 import StageLedgerV2
from contracts.runs.support_research import (SupportArchiveAuthority, SupportCompletion,
    SupportResearchIndex, StageVerifier, read_artifact)
from .protocol import project_protocol
from .store import canonical, digest, timestamp
from .workflow import state_for
from .support_diagnostics import observe


MODE='restricted_support_historical'


def marker_key(patient):return 'support-historical-'+digest(patient)


def historical_marker(db, patient):
    row=db.execute('SELECT payload FROM state_changes WHERE id=? AND patient_id=?',
        (marker_key(patient),patient)).fetchone()
    return json.loads(row[0]) if row else None


def _index(raw, authority):
    if type(authority) is not SupportArchiveAuthority:
        raise ValueError('independent_restricted_support_authority_required')
    if sha256(raw)!=authority.manifest_sha256:
        raise ValueError('support_manifest_hash_mismatch')
    index=SupportResearchIndex.model_validate_json(raw)
    if index!=authority.descriptor:
        raise ValueError('support_source_runtime_descriptor_mismatch')
    return index


def _trajectory(index, trajectory, reader, *, cuts=None, verify_all=True, diagnostic=None, trajectory_ordinal=0):
    observe(diagnostic,'trajectory_before',trajectory=trajectory_ordinal)
    full=ObservedHistoryV21.model_validate_json(reader(trajectory.history))
    if full.patient_id!=trajectory.member_id:
        raise ValueError('support_history_member_mismatch')
    observe(diagnostic,'history_after',trajectory=trajectory_ordinal)
    ledgers=[StageLedgerV2.model_validate_json(canonical_bytes(r)) for r in json.loads(reader(trajectory.stage_ledgers))]
    observe(diagnostic,'ledgers_after',trajectory=trajectory_ordinal)
    completions=[SupportCompletion.model_validate_json(canonical_bytes(r)) for r in json.loads(reader(trajectory.completions))]
    observe(diagnostic,'completions_after',trajectory=trajectory_ordinal)
    verifier=StageVerifier(full,ledgers,completions,None,run_id=index.run_id,partition_id=trajectory.partition_id,
        source_commit=index.source_commit,runtime=index.runtime,frozen_plan_sha256=index.frozen_plan_sha256,
        artifact_reader=reader)
    closures=[r for r in full.records if r.kind=='support_stage_closure']
    if (not closures or {c.stage_ledger.id for c in closures}!={r.id for r in ledgers}
            or {c.completion_receipt.id for c in closures if c.completion_receipt}!={r.id for r in completions}):
        raise ValueError('complete_support_stage_proof_required')
    for completion in completions:
        for artifact in completion.output_artifacts:reader(artifact)
    projections={}
    for cut_ordinal,day in enumerate((index.cuts if cuts is None else cuts),1):
        observe(diagnostic,'cut_before',trajectory=trajectory_ordinal,cut=cut_ordinal)
        cutoff=index.origin+timedelta(days=day)
        projected=project_protocol(full,cutoff,family='support',origin=index.origin,verify_closure=verifier)
        if trajectory_ordinal==1:observe(diagnostic,'cut_projection_return',trajectory=trajectory_ordinal,cut=cut_ordinal)
        original=reader(trajectory.projections[str(day)])
        if trajectory_ordinal==1:observe(diagnostic,'cut_reader_return',trajectory=trajectory_ordinal,cut=cut_ordinal)
        if json.loads(original)!=projected.model_dump(mode='json'):
            raise ValueError('support_projection_replay_mismatch')
        projections[day]=projected
        observe(diagnostic,'cut_after',trajectory=trajectory_ordinal,cut=cut_ordinal)
    # Every closure, including any not consumed by a reduction, must be proven.
    if verify_all:
        observe(diagnostic,'closures_before',trajectory=trajectory_ordinal)
        for closure in closures:verifier(closure,index.origin+timedelta(days=index.horizon))
        observe(diagnostic,'closures_after',trajectory=trajectory_ordinal)
    decisions=[r for r in full.records if r.kind=='support_decision']
    if (not decisions or any(r.mode!=('fixed' if trajectory.mode=='S0' else 'mrt') for r in decisions)
            or (trajectory.mode=='S0' and any(r.availability=='randomized' for r in decisions))):
        raise ValueError('support_mode_identity_mismatch')
    return full,projections


@dataclass(frozen=True)
class VerifiedSupportArchive:
    raw: bytes
    authority: SupportArchiveAuthority
    index: SupportResearchIndex
    artifacts: dict
    histories: dict


def verify_support_archive(raw, root, authority, *, diagnostic=None):
    observe(diagnostic,'verify_before')
    index=_index(raw,authority)
    observe(diagnostic,'index_after')
    artifacts={};descriptors={};identifiers={};histories={};path_partitions={};partition=None
    reads=read_bytes=hits=visits=0
    def reader(artifact):
        nonlocal reads,read_bytes,hits
        old=descriptors.get(artifact.path)
        if old is not None:
            if old!=artifact or path_partitions[artifact.path]!=partition:raise ValueError('conflicting_support_artifact_path')
            if diagnostic is not None:hits+=1
            return artifacts[artifact.path]
        key=(partition,artifact.id)
        if key in identifiers:raise ValueError('duplicate_support_artifact_id_in_partition')
        if artifact.role not in ('observed','configuration'):
            raise ValueError('support_public_proof_role_required')
        payload=read_artifact(root,artifact)
        if diagnostic is not None:reads+=1;read_bytes+=len(payload)
        descriptors[artifact.path]=artifact;identifiers[key]=artifact.path;artifacts[artifact.path]=payload;path_partitions[artifact.path]=partition
        return payload
    direct=[a for t in index.trajectories for a in (t.history,t.stage_ledgers,t.completions,*t.projections.values())]
    if len({a.path for a in direct})!=len(direct) or len({a.id for a in direct})!=len(direct):
        raise ValueError('duplicate_support_artifact_path_or_id')
    for trajectory_ordinal,trajectory in enumerate(index.trajectories,1):
        partition=trajectory.partition_id
        histories[trajectory.partition_id]=_trajectory(index,trajectory,reader,diagnostic=diagnostic,trajectory_ordinal=trajectory_ordinal)[0]
        observe(diagnostic,'trajectory_after',trajectory=trajectory_ordinal,reads=reads,bytes=read_bytes,hits=hits)
    observe(diagnostic,'supplement_before')
    for supplemental in authority.supplemental_public_artifacts:
        if supplemental.artifact.path in artifacts:raise ValueError('duplicate_supplemental_public_path')
        partition=supplemental.partition_id
        reader(supplemental.artifact)
    observe(diagnostic,'supplement_after')
    # The original index stays byte-identical. The trusted supplemental list
    # binds independently persisted predecision/timing proof omitted by it.
    manifest=Artifact(id='support-original-index',path='manifest.json',sha256=sha256(raw),bytes=len(raw),
        role='observed_manifest',media_type='application/json')
    if 'manifest.json' in artifacts:raise ValueError('reserved_original_support_manifest_path')
    observe(diagnostic,'manifest_before')
    read_artifact(root,manifest)
    if diagnostic is not None:reads+=1;read_bytes+=len(raw)
    observe(diagnostic,'manifest_after')
    observed=set();directory=Path(root)
    observe(diagnostic,'inventory_before',reads=reads,bytes=read_bytes,hits=hits)
    for path in directory.rglob('*'):
        if diagnostic is not None:visits+=1
        if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError('linked_support_public_inventory')
        if path.is_file():observed.add(path.relative_to(directory).as_posix())
    if observed!=set(artifacts)|{'manifest.json'}:
        raise ValueError('exact_qualified_support_public_inventory_required')
    observe(diagnostic,'inventory_after',visits=visits,files=len(observed))
    observe(diagnostic,'verify_after',reads=reads,bytes=read_bytes,hits=hits)
    return VerifiedSupportArchive(raw,authority,index,artifacts,histories)


def _identity(package, owner, patient):
    index=package.index
    return dict(kind=MODE,owner_id=owner,patient_id=patient,archive_id=index.run_id+':'+index.cohort_id,
        run_id=index.run_id,cohort_id=index.cohort_id,manifest_sha256=sha256(package.raw),
        admission_sha256=package.authority.admission_sha256,synthetic=True,read_only=True,
        live_authority_granted=False)


def _owners(db, package, owner):
    for patient in package.index.members:
        row=db.execute('SELECT * FROM patients WHERE id=?',(patient,)).fetchone()
        marker=db.execute('SELECT * FROM state_changes WHERE id=?',(marker_key(patient),)).fetchone()
        if (row is None or row['owner_id']!=owner or marker is None or marker['actor_id']!=owner
                or marker['patient_id']!=patient or json.loads(marker['payload'])!=_identity(package,owner,patient)
                or json.loads(row['state_json'])!=state_for('ASSIGN-01') or row['current_decision'] is not None):
            raise ValueError('support_historical_owner_or_identity_conflict')


def _receipt_bindings(index,authority,raw):
    return dict(status='archived_read_only',archive_id=index.run_id+':'+index.cohort_id,mode=MODE,
        synthetic=True,read_only=True,live_authority_granted=False,manifest_sha256=sha256(raw),
        admission_sha256=authority.admission_sha256,source_commit=index.source_commit,
        runtime=authority.descriptor.runtime.model_dump(mode='json'),qualification_scope=authority.qualification_scope,
        producer_qualification=authority.producer_qualification.model_dump(mode='json'),
        outcome_qualification=authority.outcome_qualification.model_dump(mode='json'),members=12,partitions=24,projections=72)


def _check_receipt(db,archive,index,authority,raw):
    receipt=json.loads(archive['receipt'])
    expected=_receipt_bindings(index,authority,raw)
    entries=db.execute('SELECT count(*) FROM observed_archive_entries WHERE archive_id=?',(archive['id'],)).fetchone()[0]
    artifacts=db.execute('SELECT count(*) FROM observed_archive_artifacts WHERE archive_id=?',(archive['id'],)).fetchone()[0]
    expected.update(received_at=archive['received_at'],records=entries,cursor=entries,artifacts=artifacts)
    if (archive['export_sha256']!=sha256(raw) or archive['mode']!=MODE or archive['cursor']!=entries
            or archive['record_count']!=entries or canonical(receipt)!=canonical(expected)):
        raise ValueError('stored_support_admission_mismatch')
    return receipt


def _check_entries(db,archive_id,trajectory,full):
    rows=db.execute('SELECT * FROM observed_archive_entries WHERE archive_id=? AND partition_id=? ORDER BY ordinal',
        (archive_id,trajectory.partition_id)).fetchall()
    if len(rows)!=len(full.records):raise ValueError('stored_support_entries_changed')
    for row,record in zip(rows,full.records):
        payload=canonical_bytes(record.model_dump(mode='json'))
        if (bytes(row['payload'])!=payload or row['payload_sha256']!=sha256(payload)
                or bytes(row['raw_source'])!=payload or row['raw_sha256']!=sha256(payload)
                or (row['patient_id'],row['record_id'],row['schema_version'],row['kind'])!=
                   (record.patient_id,record.record_id,record.schema_version,record.kind)):
            raise ValueError('stored_support_entries_changed')


def admit_support_archive(store, raw, root, authority, *, owner_id, received_at, authorize=None, fault=None, diagnostic=None):
    observe(diagnostic,'admit_before')
    package=verify_support_archive(raw,root,authority,diagnostic=diagnostic)
    index=package.index;identifier=index.run_id+':'+index.cohort_id
    # Receipt time is real wall time; never substitute the simulated cutoff.
    observe(diagnostic,'publication_before')
    completions=[SupportCompletion.model_validate_json(canonical_bytes(r)) for t in index.trajectories
        for r in json.loads(package.artifacts[t.completions.path])]
    if any(r.published_at>received_at for r in completions):raise ValueError('support_receipt_precedes_publication')
    observe(diagnostic,'publication_after')
    observe(diagnostic,'transaction_acquire')
    with store.transaction(write=True,authorize=authorize) as db:
        observe(diagnostic,'transaction_enter')
        if db.execute('SELECT 1 FROM accounts WHERE id=?',(owner_id,)).fetchone() is None:
            raise ValueError('support_existing_owner_required')
        for patient in index.members:
            existing=db.execute('SELECT 1 FROM patients WHERE id=?',(patient,)).fetchone()
            orphan=db.execute('SELECT 1 FROM state_changes WHERE id=?',(marker_key(patient),)).fetchone()
            if existing is None:
                if orphan:raise ValueError('support_orphan_enrollment_marker')
                db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',(patient,owner_id,
                    'Synthetic historical support member',1,1,1,1,canonical(state_for('ASSIGN-01')),None,
                    timestamp(index.origin+timedelta(days=index.horizon))))
                db.execute('INSERT INTO state_changes VALUES(?,?,?,?,?)',(marker_key(patient),patient,owner_id,
                    timestamp(received_at),canonical(_identity(package,owner_id,patient))))
        _owners(db,package,owner_id)
        observe(diagnostic,'owners_after')
        prior=db.execute('SELECT * FROM observed_archives WHERE id=?',(identifier,)).fetchone()
        if prior:
            if (prior['owner_id']!=owner_id or prior['export_sha256']!=sha256(raw) or bytes(prior['manifest'])!=raw
                    or prior['mode']!=MODE or json.loads(prior['receipt'])['admission_sha256']!=authority.admission_sha256):
                raise ValueError('immutable_support_archive_conflict')
            stored={r['path']:(bytes(r['payload']),r['sha256']) for r in db.execute('SELECT * FROM observed_archive_artifacts WHERE archive_id=?',(identifier,))}
            if stored!={p:(raw,sha256(raw)) for p,raw in package.artifacts.items()}:raise ValueError('stored_support_artifact_conflict')
            for trajectory in index.trajectories:_check_entries(db,identifier,trajectory,package.histories[trajectory.partition_id])
            observe(diagnostic,'idempotent_pending')
            return _check_receipt(db,prior,index,authority,raw)
        count=sum(len(h.records) for h in package.histories.values())
        receipt=_receipt_bindings(index,authority,raw)
        receipt.update(received_at=timestamp(received_at),artifacts=len(package.artifacts),records=count,cursor=count)
        db.execute('INSERT INTO observed_archives VALUES(?,?,?,?,?,?,?,?,?)',(identifier,owner_id,sha256(raw),raw,MODE,
            timestamp(received_at),count,count,canonical(receipt)))
        observe(diagnostic,'receipt_after')
        ordinal=0
        for trajectory in index.trajectories:
            for record in package.histories[trajectory.partition_id].records:
                payload=canonical_bytes(record.model_dump(mode='json'))
                db.execute('INSERT INTO observed_archive_entries VALUES(?,?,?,?,?,?,?,?,?,?,?)',(identifier,trajectory.partition_id,
                    ordinal,record.patient_id,record.record_id,record.schema_version,record.kind,payload,sha256(payload),payload,sha256(payload)))
                ordinal+=1
        observe(diagnostic,'entries_after')
        for path,payload in package.artifacts.items():
            db.execute('INSERT INTO observed_archive_artifacts VALUES(?,?,?,?)',(identifier,path,payload,sha256(payload)))
        observe(diagnostic,'artifacts_after')
        observe(diagnostic,'precommit')
        if fault:fault('before_support_archive_commit')
    observe(diagnostic,'commit_returned')
    return receipt


def read_support_history(db, owner, patient, archive_id, mode, cutoff_day, authority):
    if mode not in ('S0','S1') or cutoff_day not in (14,42,84):
        raise ValueError('explicit_support_mode_and_supported_cutoff_required')
    archive=db.execute('SELECT * FROM observed_archives WHERE id=? AND owner_id=? AND mode=?',(archive_id,owner,MODE)).fetchone()
    if archive is None:raise ValueError('owned_support_archive_required')
    raw=bytes(archive['manifest']);index=_index(raw,authority)
    package=VerifiedSupportArchive(raw,authority,index,{},{});_owners(db,package,owner)
    receipt=_check_receipt(db,archive,index,authority,raw)
    trajectory=next((t for t in index.trajectories if t.member_id==patient and t.mode==mode),None)
    if trajectory is None:raise ValueError('support_member_partition_required')
    def reader(artifact):
        row=db.execute('SELECT payload,sha256 FROM observed_archive_artifacts WHERE archive_id=? AND path=?',(archive_id,artifact.path)).fetchone()
        if row is None:raise ValueError('stored_support_proof_missing')
        payload=bytes(row['payload'])
        if row['sha256']!=sha256(payload) or artifact.sha256!=sha256(payload) or artifact.bytes!=len(payload):
            raise ValueError('stored_support_proof_changed')
        return payload
    full,projections=_trajectory(index,trajectory,reader,cuts=(cutoff_day,),verify_all=False)
    _check_entries(db,archive_id,trajectory,full)
    return dict(kind=MODE,synthetic=True,read_only=True,live_authority_granted=False,archive_id=archive_id,
        patient_id=patient,cohort_id=index.cohort_id,member_count=12,mode=mode,cutoff_day=cutoff_day,
        partition_id=trajectory.partition_id,paired_member_id=trajectory.paired_member_id,receipt=receipt,
        projection=projections[cutoff_day].model_dump(mode='json'),
        projection_sha256=trajectory.projections[str(cutoff_day)].sha256)
