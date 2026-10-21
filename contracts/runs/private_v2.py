"""Private v2 provenance qualification. Never copy this module to consumers.

No generator/evaluator engine is implemented here. Real completion attestations
must come from separately qualified execution evidence, supplied out of band.
"""
import json
from typing import Literal

from pydantic import model_validator
from contracts.domain.common import Identifier, Sha256, StrictModel, VersionRef
from contracts.domain.observed_v2 import LearnerHistoryV2
from .common import Authority, Artifact, canonical, read_artifact, sha256, unique
from .private import RunManifest, RunResult, SeedLedger, StreamKey, TruthRequest, TruthResponse
from .observed_v2 import BindingsV2, ExportAuthorityV2, ObservedExportV2, TrustedPartitionV2
from .coverage_v2 import ScheduleInputV2, derive_slots
from .admission_v2 import verify_export_v2


class RunManifestV2(RunManifest):
    schema_version: Literal['2.0.0']
    contract_version: Literal['2.0.0']
    bindings: BindingsV2
    schedule_inputs: list[Artifact]
    source_registry: VersionRef
    transformation_registry: VersionRef

    @model_validator(mode='after')
    def schedule_files(self):
        unique([a.id for a in self.schedule_inputs], 'schedule input')
        if any(a not in self.inputs or a.role != 'configuration' for a in self.schedule_inputs):
            raise ValueError('schedule must be a predeclared immutable run input')
        return self


class RunResultV2(RunResult):
    schema_version: Literal['2.0.0']
    contract_version: Literal['2.0.0']
    bindings: BindingsV2
    completion_receipts: list[Artifact]


class SeedLedgerV2(SeedLedger):
    schema_version: Literal['2.0.0']
    contract_version: Literal['2.0.0']


class TruthRequestV2(TruthRequest):
    schema_version: Literal['2.0.0']
    contract_version: Literal['2.0.0']
    bindings: BindingsV2


class TruthResponseV2(TruthResponse):
    schema_version: Literal['2.0.0']
    contract_version: Literal['2.0.0']
    bindings: BindingsV2


class AuthorityV2(Authority):
    contract_version: Literal['2.0.0']
    bindings: BindingsV2
    producer_qualification: VersionRef | None


def verify_run_v2(raw, root, authority):
    if not isinstance(authority, AuthorityV2) or sha256(raw) != authority.manifest_sha256:
        raise ValueError('untrusted v2 run authority/digest')
    run = RunManifestV2.model_validate_json(raw)
    if (run.run_id, run.producer, run.source_commit, run.runtime, run.bindings) != (authority.run_id, authority.producer, authority.source_commit, authority.runtime, authority.bindings):
        raise ValueError('v2 run changed trusted identity/configuration')
    if run.execution == 'contract_fixture' and not authority.allow_contract_fixture:
        raise ValueError('fixture cannot authorize production')
    if run.execution == 'engine_run' and authority.producer_qualification is None:
        raise ValueError('real producer qualification pending')
    by_id = {a.id: a for a in run.inputs}
    for name, ref in run.bindings:
        if name in ('dgp', 'domain_schema_set', 'run_schema_set'):
            continue
        artifact = by_id.get(ref.id)
        if artifact is None or artifact.role != 'configuration':
            raise ValueError('missing exact accepted v2 configuration input')
        if sha256(read_artifact(root, artifact, 'configuration').replace(b'\r\n', b'\n')) != ref.sha256:
            raise ValueError('changed accepted v2 configuration bytes')
    for artifact in run.inputs:
        read_artifact(root, artifact, artifact.role)
    for ref in [run.source_registry, run.transformation_registry]:
        artifact = by_id.get(ref.id)
        if artifact is None or artifact.role != 'configuration' or artifact.sha256 != ref.sha256:
            raise ValueError('source/transformation registry must bind exact immutable run input')
    slots = {p.id: (u, c, p) for u in run.units for c in u.cohorts for p in c.patients}
    schedules = {}
    for artifact in run.schedule_inputs:
        schedule = ScheduleInputV2.model_validate_json(read_artifact(root, artifact, 'configuration'))
        if schedule.patient_id not in slots or schedule.patient_id in schedules:
            raise ValueError('schedule patient outside complete roster')
        unit, cohort, patient = slots[schedule.patient_id]
        if (schedule.run_id, schedule.unit_id, schedule.cell_id, schedule.cohort_id, schedule.replicate, schedule.preset) != (run.run_id, unit.id, unit.cell_id, cohort.id, patient.replicate, unit.preset):
            raise ValueError('schedule differs from accepted run cohort/replicate')
        if (schedule.protocol, schedule.timing, schedule.temporal, schedule.representation) != (run.bindings.protocol, run.bindings.timing, run.bindings.temporal, run.bindings.observed_representation):
            raise ValueError('schedule changed accepted time grid/profile')
        schedules[patient.id] = schedule
    if set(schedules) != set(slots):
        raise ValueError('run omitted patient schedule inputs')
    return run, schedules


def validate_record_keys(run, partition, history, ledger, schedule):
    """Check full verified key material, process, time, namespace and source."""
    keys = {k.key_sha256: k for k in ledger.keys}
    records = {r.record_id: r for r in history.records}
    processes = {'support_decision': ('support_assignment', 'assignment'), 'support_outcome_link': ('support_outcome', 'generation'),
                 'support_stage_closure': ('support_stage_closure', 'generation'), 'hold_transition_bundle': ('hold_transition', 'generation'),
                 'hold_review_evidence': ('hold_review', 'generation'), 'daily_report': ('diary_report', 'measurement')}
    for binding in partition.records:
        record = records[binding.record_id]
        identity = binding.identity
        key = keys.get(binding.seed_key_sha256)
        if key is None or (key.protocol, key.phase, key.namespace, key.scenario, key.replicate, key.patient, key.time_index, key.process, key.stream) != (identity.protocol, identity.phase, identity.namespace, identity.cell_id, identity.replicate, identity.patient_id, identity.time_index, identity.process, identity.substream):
            raise ValueError('full record key/process/time/namespace mismatch')
        if key.protocol != run.bindings.protocol.id or key.phase != run.phase or key.patient != partition.patient_id or key.scenario != partition.cell_id or key.replicate != partition.replicate:
            raise ValueError('key outside accepted protocol/phase/run/cell/patient')
        if identity.source_registry != run.source_registry or identity.transformation != run.transformation_registry:
            raise ValueError('record source/transformation registry mismatch')
        if record.source.model_dump(exclude={'raw_sha256'}) not in run.sources:
            raise ValueError('undeclared generated source')
        expected_day = (record.event_at.astimezone(__import__('zoneinfo').ZoneInfo(schedule.timezone)).date() - schedule.time_zero_local_date).days
        if record.kind == 'support_outcome_link':
            expected_day -= 1
        if record.kind == 'support_stage_closure':
            expected_day = record.decision_index
        if identity.time_index != expected_day:
            raise ValueError('record key has wrong protocol day')
        if record.schema_version == '2.0.0' and (identity.process, identity.namespace) != processes[record.kind]:
            raise ValueError('record has wrong accepted process/namespace')
        if record.kind == 'assignment' and record.option in ('support_prompt', 'no_prompt') and (identity.process, identity.namespace) != ('support_assignment', 'assignment'):
            raise ValueError('deterministic or randomized support assignment has wrong process/namespace')
        randomized = record.kind == 'support_decision' and record.availability == 'randomized' or record.kind == 'assignment' and record.experimental
        if identity.draw_consumed != randomized and record.kind in ('support_decision', 'assignment', 'support_outcome_link', 'support_stage_closure', 'hold_transition_bundle', 'hold_review_evidence'):
            raise ValueError('deterministic provenance cannot imply a random draw')
        if record.kind == 'assignment' and record.component == 'mrt_bandit':
            if (key.namespace, key.process) != ('assignment', 'support_assignment') or record.seed is None:
                raise ValueError('MRT requires exact assignment key')
            seed = record.seed
            if (seed.namespace, seed.protocol, seed.scenario, seed.replicate, seed.patient, seed.time_index, seed.process) != ('assignment', key.protocol, key.scenario, key.replicate, key.patient, key.time_index, key.process):
                raise ValueError('MRT public seed differs from full assignment key')
        if record.kind == 'support_decision' and record.assignment_id:
            assignment_binding = next((b for b in partition.records if b.record_id == record.assignment_id), None)
            if assignment_binding is None or assignment_binding.seed_key_sha256 != binding.seed_key_sha256:
                raise ValueError('support decision and assignment must bind the same full assignment key')
    return True


def verify_result_v2(raw, root, run, authority, expected_result_sha256, *, export_authorities):
    if sha256(raw) != expected_result_sha256:
        raise ValueError('untrusted v2 result digest')
    result = RunResultV2.model_validate_json(raw)
    if (result.run_id, result.run_manifest.sha256, result.run_manifest.version, result.producer, result.source_commit, result.runtime, result.bindings) != (run.run_id, authority.manifest_sha256, '2.0.0', run.producer, run.source_commit, run.runtime, run.bindings):
        raise ValueError('v2 result changed accepted run provenance')
    if result.seed_ledger is None:
        raise ValueError('v2 output qualification needs complete seed ledger')
    ledger = SeedLedgerV2.model_validate_json(read_artifact(root, result.seed_ledger, 'seed_ledger'))
    if ledger.run_id != run.run_id:
        raise ValueError('seed ledger run mismatch')
    schedules = {s.patient_id: s for a in run.schedule_inputs for s in [ScheduleInputV2.model_validate_json(read_artifact(root, a, 'configuration'))]}
    admitted = []
    seen = set()
    for artifact in result.observed_exports:
        public = export_authorities.get(artifact.id)
        if public is None or public.export_sha256 != artifact.sha256:
            raise ValueError('separately qualified export authority required')
        manifest, partitions = verify_export_v2(read_artifact(root, artifact, 'observed_manifest'), root, public)
        if manifest.bindings != run.bindings or manifest.cutoff != run.cutoff:
            raise ValueError('export changed run bindings/cutoff')
        for partition, history, batch, projection, *_ in partitions:
            if partition.patient_id in seen or partition.patient_id not in schedules:
                raise ValueError('unknown/repeated run patient')
            seen.add(partition.patient_id)
            public_schedule = next(t.schedule for t in public.partitions if t.partition_id == partition.id)
            if public_schedule != schedules[partition.patient_id]:
                raise ValueError('public authority schedule differs from independently accepted run origin')
            validate_record_keys(run, partition, history, ledger, schedules[partition.patient_id])
            admitted.append((manifest, partition, history, batch, projection))
    if result.status == 'complete' and seen != set(schedules):
        raise ValueError('complete v2 result omitted roster patient')
    # Existing private truth/calibration artifacts keep their original schemas.
    for artifact in [*result.private_truth, *result.calibration, *result.reports, *result.completion_receipts]:
        read_artifact(root, artifact, artifact.role)
    return result, admitted


def verify_truth_v2_history(request, raw):
    history = LearnerHistoryV2.model_validate_json(raw)
    if history.patient_id != request.patient_id or history.cutoff != request.cutoff:
        raise ValueError('v2 conditional history patient/cutoff mismatch')
    return history


def parse_private_artifact(raw):
    """No kind-only discriminator or silent cross-version promotion."""
    value = json.loads(raw)
    models = {('1.0.0', 'generator_run_manifest'): RunManifest, ('1.0.0', 'generator_run_result'): RunResult,
              ('1.0.0', 'seed_ledger'): SeedLedger, ('1.0.0', 'evaluator_request'): TruthRequest, ('1.0.0', 'evaluator_response'): TruthResponse,
              ('2.0.0', 'generator_run_manifest'): RunManifestV2, ('2.0.0', 'generator_run_result'): RunResultV2,
              ('2.0.0', 'seed_ledger'): SeedLedgerV2, ('2.0.0', 'evaluator_request'): TruthRequestV2, ('2.0.0', 'evaluator_response'): TruthResponseV2}
    model = models.get((value.get('schema_version'), value.get('kind')))
    if model is None:
        raise ValueError('unsupported private artifact version/kind')
    return model.model_validate_json(raw)
