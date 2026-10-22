"""Full original-byte observed archive and qualified public export profile."""
import json
from typing import Annotated, Literal
from pathlib import Path

from pydantic import AwareDatetime, Field, model_validator
from contracts.domain.common import Identifier, Record, Sha256, Source, StrictModel, VersionRef
from contracts.domain.observed_v2 import ObservedHistoryV2, ObservedRecordV2, RECORD_ADAPTER_V2, VersionedV2
from .common import Artifact, Bindings, Commit, ExportAuthority, Producer, Runtime, Token, canonical, sha256, unique
from .observed import validate_observation
from .coverage_v2 import CompletionReceiptV2, ScheduleInputV2, StageLedgerV2, SupportCoverageV2, DecisionSlotV2

CLINICAL_KINDS = frozenset({'patient', 'encounter', 'medication_order', 'medication_exposure', 'observation', 'intercurrent_event', 'oura_like', 'daily_report', 'isi'})


class BindingsV2(Bindings):
    observed_representation: VersionRef
    domain_schema_set: VersionRef
    run_schema_set: VersionRef

    @model_validator(mode='after')
    def accepted_source(self):
        expected = json.loads(Path(__file__).with_name('bindings-v2.json').read_text(encoding='utf-8'))
        if self.model_dump(mode='json') != expected:
            raise ValueError('unaccepted v2 representation/schema/scientific bindings')
        return self


class ReplayEntryV2(StrictModel):
    record: ObservedRecordV2
    raw_source: str


class ReplayBatchV2(VersionedV2):
    kind: Literal['observed_replay_batch']
    contract_version: Literal['2.0.0']
    run_id: Token
    partition_id: Token
    patient_id: Identifier
    entries: list[ReplayEntryV2]

    @model_validator(mode='after')
    def originals(self):
        history = ObservedHistoryV2(schema_version='2.0.0', synthetic=True, kind='observed_history', patient_id=self.patient_id, records=[e.record for e in self.entries])
        by_id = {r.record_id: r for r in history.records}
        for entry in self.entries:
            record = validate_observation(entry.record)
            if sha256(entry.raw_source.encode('utf-8')) != record.source.raw_sha256:
                raise ValueError('raw_source_hash_mismatch')
            original = by_id[record.duplicate_of] if record.duplicate_of else record
            if record.duplicate_of:
                header = set(Record.model_fields)
                if record.model_dump(exclude=header) != original.model_dump(exclude=header):
                    raise ValueError('duplicate must retain original clinical payload')
            payload = json.loads(entry.raw_source)
            if not isinstance(payload, dict) or 'source' in payload:
                raise ValueError('raw source must omit only original source header')
            payload['source'] = original.source.model_dump(mode='json')
            if RECORD_ADAPTER_V2.validate_json(canonical(payload)) != original:
                raise ValueError('raw source differs from exact typed original')
        return self


class RecordIdentityV2(StrictModel):
    protocol: Identifier
    phase: Literal['fixture', 'calibration', 'pilot', 'smoke', 'development', 'confirmation']
    run_id: Token
    cell_id: Identifier
    cohort_id: Token
    replicate: Annotated[int, Field(ge=0)]
    patient_id: Identifier
    time_index: int
    process: Identifier
    substream: Identifier
    namespace: Literal['generation', 'assignment', 'measurement', 'missingness', 'fitting', 'posterior_rollout', 'truth']
    source_registry: VersionRef
    transformation: VersionRef
    input_refs: list[VersionRef]
    draw_consumed: bool


class RecordBindingV2(StrictModel):
    record_id: Identifier
    payload_sha256: Sha256
    source: Source
    seed_key_sha256: Sha256
    identity: RecordIdentityV2
    import_to_event_store: bool
    exclusion_reason: Literal['administrative_event_not_live_authority'] | None


class PartitionV2(StrictModel):
    id: Token
    unit_id: Token
    cell_id: Identifier
    preset: Literal['catalog_cell', 'smoke', 'demonstration', 'evaluation']
    cohort_id: Token
    replicate: Annotated[int, Field(ge=0)]
    patient_id: Identifier
    history: Artifact
    replay: Artifact
    coverage: Artifact
    stage_ledgers: list[Artifact]
    completion_receipts: list[Artifact]
    mechanisms: list[Artifact]
    records: list[RecordBindingV2]

    @model_validator(mode='after')
    def files(self):
        for artifact, role in [(self.history, 'observed'), (self.replay, 'replay'), (self.coverage, 'configuration'),
                               *[(a, 'configuration') for a in [*self.stage_ledgers, *self.completion_receipts, *self.mechanisms]]]:
            if artifact.role != role or artifact.media_type != 'application/json':
                raise ValueError('v2 observed archive artifact role/media mismatch')
        unique([r.record_id for r in self.records], 'partition record')
        for record in self.records:
            if record.import_to_event_store != (record.exclusion_reason is None):
                raise ValueError('omitted administrative record needs explicit exclusion')
        return self


class ObservedExportV2(VersionedV2):
    kind: Literal['observed_export']
    contract_version: Literal['2.0.0']
    id: Token
    run_id: Token
    run_manifest: VersionRef
    producer: Producer
    execution: Literal['contract_fixture', 'engine_run']
    source_commit: Commit
    runtime: Runtime
    bindings: BindingsV2
    cutoff: AwareDatetime
    created_at: AwareDatetime
    status: Literal['partial', 'complete']
    partitions: Annotated[list[PartitionV2], Field(min_length=1)]

    @model_validator(mode='after')
    def export(self):
        if self.producer.role not in ('generator', 'contract_fixture') or (self.execution == 'contract_fixture') != (self.producer.role == 'contract_fixture'):
            raise ValueError('v2 export producer/execution mismatch')
        if self.created_at < self.cutoff or self.run_manifest.id != self.run_id or self.run_manifest.version != '2.0.0':
            raise ValueError('v2 run identity/version/cutoff mismatch')
        unique([p.id for p in self.partitions], 'partition')
        unique([p.patient_id for p in self.partitions], 'patient partition')
        unique([r.record_id for p in self.partitions for r in p.records], 'run record')
        artifacts = [a for p in self.partitions for a in (p.history, p.replay, p.coverage, *p.stage_ledgers, *p.completion_receipts, *p.mechanisms)]
        unique([a.id for a in artifacts], 'artifact ID')
        unique([a.path for a in artifacts], 'artifact path')
        for p in self.partitions:
            for a, role in [(p.history, 'observed'), (p.replay, 'replay')]:
                if a.path != f'{role}/{self.run_id}/{p.id}.json':
                    raise ValueError('artifact path must bind role/run/partition')
        return self


class TrustedPartitionV2(StrictModel):
    """Derived/qualified externally; an upload cannot redefine these facts."""
    partition_id: Token
    schedule: ScheduleInputV2
    expected_decisions: list[DecisionSlotV2]
    coverage_sha256: Sha256
    terminal_evidence_sha256: Sha256 | None
    stage_ledger_hashes: dict[Token, Sha256]
    completion_receipt_hashes: dict[Token, Sha256]
    mechanism_hashes: dict[Token, Sha256]
    record_identities: dict[Identifier, RecordIdentityV2]
    record_key_hashes: dict[Identifier, Sha256]


class ExportAuthorityV2(ExportAuthority):
    runtime: Runtime
    contract_version: Literal['2.0.0']
    bindings: BindingsV2
    producer_qualification: VersionRef | None
    partitions: list[TrustedPartitionV2]

    @model_validator(mode='after')
    def authority(self):
        unique([p.partition_id for p in self.partitions], 'trusted partition')
        if not self.allow_contract_fixture and self.producer_qualification is None:
            raise ValueError('real producer qualification is required')
        return self
