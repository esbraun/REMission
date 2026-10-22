"""Observed export/replay wire contracts, safe to include in consumer images."""
import json
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator
from contracts.domain.boundaries import ObservedHistory
from contracts.domain.common import Identifier, Sha256, Source, StrictModel, Versioned, VersionRef
from contracts.domain.entities import ObservedRecord
from .common import Artifact, Bindings, Commit, Producer, RuntimeProfile, Token, canonical, sha256, unique, RESTRICTED, RESTRICTED_CELL, restricted_profile, restricted_producer

ADAPTER=TypeAdapter(ObservedRecord)
INGESTIBLE={'patient','consent','encounter','medication_order','medication_exposure','observation','intercurrent_event','oura_like','daily_report','isi'}


def validate_observation(record):
    covariates=record.covariates if record.kind=='patient' else [record.measure] if record.kind=='observation' else []
    if any(c.observed_at>record.event_at or c.available_at>record.available_at for c in covariates):
        raise ValueError('nested_future_covariate')
    if record.kind in ('patient','oura_like'):
        zone=ZoneInfo(record.timezone)
        if record.kind=='oura_like' and record.episode_end.astimezone(zone).date()!=record.local_date:
            raise ValueError('sleep_local_date_mismatch')
    return record


class ReplayEntry(StrictModel):
    record: ObservedRecord
    raw_source: str


class ReplayBatch(Versioned):
    kind: Literal['observed_replay_batch']
    contract_version: Literal['1.0.0']
    run_id: Token
    partition_id: Token
    patient_id: Identifier
    entries: list[ReplayEntry]

    @model_validator(mode='after')
    def raw_and_lineage(self):
        history=ObservedHistory(schema_version='1.0.0',synthetic=True,kind='observed_history',patient_id=self.patient_id,records=[e.record for e in self.entries])
        by_id={r.record_id:r for r in history.records}
        for entry in self.entries:
            record=validate_observation(entry.record)
            if record.kind not in INGESTIBLE:
                raise ValueError('administrative_record_route_required')
            raw=entry.raw_source.encode('utf-8')
            if sha256(raw)!=record.source.raw_sha256:
                raise ValueError('raw_source_hash_mismatch')
            original=by_id[record.duplicate_of] if record.duplicate_of else record
            payload=json.loads(raw)
            if not isinstance(payload,dict) or 'source' in payload:
                raise ValueError('raw source must be the observed envelope without its source header')
            payload['source']=original.source.model_dump(mode='json')
            parsed=ADAPTER.validate_json(canonical(payload))
            if parsed!=original:
                raise ValueError('raw source differs from its typed original observation')
        return self


class RecordBinding(StrictModel):
    record_id: Identifier
    payload_sha256: Sha256
    source: Source
    seed_key_sha256: Sha256 | None
    import_to_event_store: bool
    exclusion_reason: Literal['administrative_event_not_live_authority'] | None


class Partition(StrictModel):
    id: Token
    unit_id: Token
    cell_id: Identifier
    preset: Literal['catalog_cell','smoke','demonstration','evaluation']
    cohort_id: Token
    replicate: Annotated[int,Field(ge=0)]
    patient_id: Identifier
    history: Artifact
    replay: Artifact
    records: list[RecordBinding]

    @model_validator(mode='after')
    def files(self):
        if self.history.role!='observed' or self.replay.role!='replay' or self.history.media_type!='application/json' or self.replay.media_type!='application/json':
            raise ValueError('only observed/replay artifacts may enter a consumer export')
        unique([r.record_id for r in self.records],'partition record')
        for record in self.records:
            if record.import_to_event_store!=(record.exclusion_reason is None):
                raise ValueError('each omitted administrative record needs an explicit exclusion')
        return self


class ObservedExport(Versioned):
    kind: Literal['observed_export']
    contract_version: Literal['1.0.0']
    id: Token
    run_id: Token
    run_manifest: VersionRef
    producer: Producer
    execution: Literal['contract_fixture','engine_run']
    source_commit: Commit
    runtime: RuntimeProfile
    bindings: Bindings
    evaluation_configuration: VersionRef | None = None
    cutoff: AwareDatetime
    created_at: AwareDatetime
    status: Literal['partial','complete']
    partitions: Annotated[list[Partition], Field(min_length=1)]

    @model_validator(mode='after')
    def safe_export(self):
        restricted=restricted_profile(self.bindings,self.runtime)
        if restricted:
            restricted_producer(self.producer,self.execution)
            if (self.evaluation_configuration is None or self.evaluation_configuration.model_dump(mode='json')!=RESTRICTED['evaluation_configuration']['reference']
                    or len(self.partitions)!=12 or len({(p.unit_id,p.cohort_id,p.replicate) for p in self.partitions})!=1
                    or any(p.cell_id!=RESTRICTED_CELL or p.preset!='evaluation' or p.replicate!=0 for p in self.partitions)):
                raise ValueError('restricted export requires exact twelve-member evaluation association')
            sources=[*RESTRICTED['source'],RESTRICTED['historical_assignment_source']]
            if any(r.source.model_dump(exclude={'raw_sha256'}) not in sources or r.seed_key_sha256 is not None for p in self.partitions for r in p.records):
                raise ValueError('restricted export source mismatch or private seed key')
        elif self.evaluation_configuration is not None or any(p.cell_id==RESTRICTED_CELL for p in self.partitions):
            raise ValueError('restricted evaluation association requires restricted profile')
        if self.producer.role not in ('generator','contract_fixture') or (self.execution=='contract_fixture')!=(self.producer.role=='contract_fixture'):
            raise ValueError('observed export must have a matching generator/fixture producer')
        if self.created_at<self.cutoff or self.run_manifest.id!=self.run_id or self.run_manifest.version!='1.0.0':
            raise ValueError('run identity/version/cutoff mismatch')
        unique([p.id for p in self.partitions],'partition')
        unique([p.patient_id for p in self.partitions],'patient partition')
        unique([r.record_id for p in self.partitions for r in p.records],'run record')
        artifacts=[a for p in self.partitions for a in (p.history,p.replay)]
        unique([a.id for a in artifacts],'artifact ID');unique([a.path for a in artifacts],'artifact path')
        for partition in self.partitions:
            for artifact,role in [(partition.history,'observed'),(partition.replay,'replay')]:
                if artifact.path!=f'{role}/{self.run_id}/{partition.id}.json':
                    raise ValueError('artifact path must match its role/run/partition')
        return self


def verify_partition(manifest: ObservedExport, partition: Partition, history: ObservedHistory, batch: ReplayBatch):
    if history.patient_id!=partition.patient_id or batch.patient_id!=partition.patient_id or batch.run_id!=manifest.run_id or batch.partition_id!=partition.id:
        raise ValueError('patient/run/partition identity mismatch')
    by_id={r.record_id:r for r in history.records}
    if set(by_id)!={r.record_id for r in partition.records}:
        raise ValueError('export record mapping is incomplete or fabricated')
    replay_ids=set()
    for link in partition.records:
        record=validate_observation(by_id[link.record_id])
        if restricted_profile(manifest.bindings,manifest.runtime):
            expected=RESTRICTED['historical_assignment_source'] if record.kind=='assignment' else RESTRICTED['source'][0]
            if record.source.model_dump(exclude={'raw_sha256'})!=expected or record.kind not in {'patient','daily_report','isi','delivery','assignment'}:
                raise ValueError('restricted record/source role mismatch')
            if max(record.event_at,record.recorded_at,record.available_at)>=manifest.cutoff:
                raise ValueError('restricted export requires strict three-clock cutoff')
        if sha256(canonical(record.model_dump(mode='json')))!=link.payload_sha256 or record.source!=link.source:
            raise ValueError('record payload/source provenance mismatch')
        if record.available_at>manifest.cutoff or record.recorded_at>manifest.cutoff or record.event_at>manifest.cutoff:
            raise ValueError('export cannot include data beyond its declared receipt cutoff')
        expected=record.kind in INGESTIBLE
        if link.import_to_event_store!=expected:
            raise ValueError('administrative records cannot acquire clinical authority by import')
        if expected:replay_ids.add(record.record_id)
    if replay_ids!={entry.record.record_id for entry in batch.entries}:
        raise ValueError('replay mapping omitted or added observed records')
    for entry in batch.entries:
        if entry.record!=by_id[entry.record.record_id]:
            raise ValueError('replay/history record disagreement')
    # A replay partition must retain its own complete correction/duplicate lineage.
    projection=history.project(manifest.cutoff)
    if restricted_profile(manifest.bindings,manifest.runtime):
        from contracts.domain.analysis import project_history
        reduced=project_history(projection)
        from datetime import datetime, timedelta
        origin=datetime.fromisoformat(RESTRICTED['binding_descriptors']['timing']['origin'])
        if reduced.origin!=origin or manifest.cutoff not in (origin+timedelta(days=14),origin+timedelta(days=42)):
            raise ValueError('restricted research origin/cutoff mismatch')
        expected=[origin+timedelta(days=d) for d in (0,14,28) if origin+timedelta(days=d)<manifest.cutoff]
        if sorted(r.event_at for r in reduced.records if r.kind=='assignment')!=expected:
            raise ValueError('restricted research requires complete initial/retention assignment history')
    return projection
