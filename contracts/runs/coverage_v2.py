"""Consumer-safe trusted schedule and observation-completion attestations.

Trusted authorities are caller configuration, never taken from uploads. Real
producer qualification remains required; contract fixtures cannot attest it.
"""
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, model_validator
from contracts.domain.common import Identifier, Name, Sha256, StrictModel, VersionRef
from contracts.domain.observed_v2 import ExactRef, VersionedV2
from .common import Artifact, Producer, Runtime, Token, canonical, sha256, unique


class ScheduleInputV2(VersionedV2):
    kind: Literal['support_schedule_input']
    id: Token
    run_id: Token
    partition_id: Token
    protocol: VersionRef
    timing: VersionRef
    temporal: VersionRef
    representation: VersionRef
    dgp: VersionRef
    catalog: VersionRef
    cell_id: Identifier
    preset: Literal['catalog_cell', 'smoke', 'demonstration', 'evaluation']
    unit_id: Token
    cohort_id: Token
    replicate: Annotated[int, Field(ge=0)]
    patient_id: Identifier
    patient_ref: ExactRef
    timezone: Name
    time_zero_local_date: date
    time_zero_utc: AwareDatetime
    timezone_database: VersionRef
    derivation: VersionRef
    planned_horizon: Literal[84]

    @model_validator(mode='after')
    def origin(self):
        expected = datetime.combine(self.time_zero_local_date, time(), ZoneInfo(self.timezone)).astimezone(timezone.utc)
        if self.time_zero_utc != expected:
            raise ValueError('time-zero local/UTC mapping mismatch')
        return self


class DecisionSlotV2(StrictModel):
    decision_index: Annotated[int, Field(ge=0, le=84)]
    decision_at: AwareDatetime
    window_id: Identifier
    assessment_at: AwareDatetime
    outcome_link_id: Identifier


class SupportMechanismV2(VersionedV2):
    kind: Literal['support_mechanism']
    id: Token
    policy: VersionRef
    mode: Literal['fixed', 'mrt', 'adaptive', 'frozen', 'paused']
    parameter_refs: Annotated[list[VersionRef], Field(min_length=1)]
    action_versions: dict[Literal['support_prompt', 'no_prompt'], VersionRef]
    probability_rule: VersionRef
    context_mapping: VersionRef
    burden_behavior: VersionRef
    constraints: VersionRef
    frozen_origin: VersionRef | None
    approximation_settings: VersionRef | None
    approximation_error: Annotated[float, Field(ge=0)] | None

    @model_validator(mode='after')
    def full_mechanism(self):
        if set(self.action_versions) != {'support_prompt', 'no_prompt'}:
            raise ValueError('both versioned support actions required')
        if self.mode == 'frozen' and self.frozen_origin is None:
            raise ValueError('frozen mechanism requires exact origin snapshot')
        if self.mode == 'adaptive' and (self.approximation_settings is None or self.approximation_error is None):
            raise ValueError('adaptive approximation contract must be supplied before execution')
        return self


def derive_slots(schedule: ScheduleInputV2, *, death_at=None):
    """TIME-01 daily calendar schedule, derived from trusted bound inputs.

    Holds/caps/consent never remove a roster row. Only qualified terminal
    evidence supplied by the caller can truncate at its safety phase.
    """
    zone = ZoneInfo(schedule.timezone)
    result = []
    for day in range(85):
        local_date = schedule.time_zero_local_date + timedelta(days=day)
        at = datetime.combine(local_date, time(9), zone).astimezone(timezone.utc)
        if death_at is not None and death_at <= at:
            break
        identity = sha256(canonical([schedule.run_id, schedule.partition_id, schedule.patient_id, day]))[:32]
        result.append(DecisionSlotV2(decision_index=day, decision_at=at, window_id='window-' + identity,
                                    assessment_at=datetime.combine(local_date + timedelta(days=1), time(7), zone).astimezone(timezone.utc),
                                    outcome_link_id='outcome-' + identity))
    return result


class CoverageSlotV2(StrictModel):
    slot: DecisionSlotV2
    decision_ref: ExactRef | None
    status: Literal['planned', 'pending', 'available']
    endpoint_status: Literal['not_yet_due', 'pending', 'available']
    outcome_ref: ExactRef | None

    @model_validator(mode='after')
    def references(self):
        if (self.status == 'available') != (self.decision_ref is not None) or (self.endpoint_status == 'available') != (self.outcome_ref is not None):
            raise ValueError('coverage slot state/reference mismatch')
        return self


class SupportCoverageV2(VersionedV2):
    kind: Literal['support_coverage']
    id: Token
    run_manifest: VersionRef
    schedule_input: VersionRef
    schedule: ScheduleInputV2
    expected_decisions: list[DecisionSlotV2]
    first_decision_index: int | None
    last_decision_index: int | None
    first_decision_at: AwareDatetime | None
    last_decision_at: AwareDatetime | None
    receipt_cutoff: AwareDatetime
    coverage_through: AwareDatetime
    status: Literal['partial', 'complete']
    execution_status: Literal['partial', 'complete']
    endpoint_status: Literal['pending', 'complete']
    slots: list[CoverageSlotV2]
    death_ref: ExactRef | None
    death_effective_at: AwareDatetime | None
    terminal_phase: Literal['safety_before_decision'] | None
    terminal_reconciliation: VersionRef | None
    no_terminal_event_evidence: VersionRef | None
    completion_receipt: VersionRef | None

    @model_validator(mode='after')
    def coverage(self):
        expected = derive_slots(self.schedule, death_at=self.death_effective_at)
        if self.expected_decisions != expected or [row.slot for row in self.slots] != expected:
            raise ValueError('coverage differs from canonical independently derived roster')
        ends = (expected[0].decision_index, expected[-1].decision_index, expected[0].decision_at, expected[-1].decision_at) if expected else (None, None, None, None)
        if (self.first_decision_index, self.last_decision_index, self.first_decision_at, self.last_decision_at) != ends:
            raise ValueError('first/last canonical schedule mismatch')
        if self.coverage_through > self.receipt_cutoff:
            raise ValueError('coverage cannot establish future receipts')
        if (self.death_ref is None) != (self.death_effective_at is None) or (self.death_ref is not None and (self.terminal_phase is None or self.terminal_reconciliation is None)):
            raise ValueError('terminal truncation needs exact evidence and reconciliation')
        if self.status == 'complete' and (self.execution_status != 'complete' or self.endpoint_status != 'complete' or self.completion_receipt is None):
            raise ValueError('complete coverage needs execution and endpoint completion receipt')
        if self.execution_status == 'complete' and self.death_ref is None and self.no_terminal_event_evidence is None:
            raise ValueError('complete alive roster needs qualified no-terminal evidence')
        for row in self.slots:
            if row.slot.decision_at > self.receipt_cutoff and row.status != 'planned':
                raise ValueError('future decision is planned, never unavailable')
            if row.slot.decision_at <= self.receipt_cutoff and row.status == 'planned':
                raise ValueError('due decision needs available or pending slot')
            if row.slot.assessment_at > self.receipt_cutoff and row.endpoint_status != 'not_yet_due':
                raise ValueError('future assessment must remain a reservation')
            if row.slot.assessment_at <= self.receipt_cutoff and row.endpoint_status == 'not_yet_due':
                raise ValueError('due assessment needs pending or available endpoint')
            if self.status == 'complete' and (row.status != 'available' or row.endpoint_status != 'available'):
                raise ValueError('complete coverage omitted a decision or endpoint')
        return self


class StageLedgerV2(VersionedV2):
    kind: Literal['support_stage_ledger']
    id: Token
    run_id: Token
    partition_id: Token
    patient_id: Identifier
    decision_index: Annotated[int, Field(ge=0, le=84)]
    window_id: Identifier
    stage: Literal['offered', 'delivered']
    rule: VersionRef
    event_refs: list[ExactRef]

    @model_validator(mode='after')
    def exhaustive(self):
        unique([r.record_id for r in self.event_refs], 'stage event')
        return self


class CompletionReceiptV2(VersionedV2):
    kind: Literal['completion_receipt']
    id: Token
    run_id: Token
    partition_id: Token
    patient_id: Identifier
    producer: Producer
    source_commit: Annotated[str, Field(pattern=r'^[a-f0-9]{40}$')]
    runtime: Runtime
    accepted_configuration: list[VersionRef]
    schedule_input: VersionRef
    stage_ledgers: list[VersionRef]
    process: Identifier
    time_start: AwareDatetime
    time_end: AwareDatetime
    completed_at: AwareDatetime
    recorded_at: AwareDatetime
    published_at: AwareDatetime
    available_at: AwareDatetime
    output_artifacts: list[Artifact]
    output_counts: dict[Identifier, Annotated[int, Field(ge=0)]]
    dependency_manifests: list[VersionRef]
    status: Literal['partial', 'complete', 'failed']
    failure_reason: Name | None
    checkpoint_id: Identifier
    resume_from: Identifier | None

    @model_validator(mode='after')
    def completion(self):
        if not self.time_start <= self.time_end <= self.completed_at <= self.recorded_at <= self.published_at <= self.available_at:
            raise ValueError('actual execution/publication chronology required')
        if (self.status == 'complete') != (self.failure_reason is None):
            raise ValueError('incomplete/failed receipt needs reason')
        unique([r.id for r in self.stage_ledgers], 'receipt stage ledger')
        # Receipt outputs exclude final coverage/closures/archive to avoid cycles.
        if any(a.role not in ('observed', 'configuration') for a in self.output_artifacts):
            raise ValueError('receipt may bind only independent pre-closure outputs')
        return self
