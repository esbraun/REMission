"""OBS-REP-02: observed facts and exact, append-only administrative evidence.

This module is consumer safe. It neither imports DGP code nor confers live
consent, approval or hold clearance authority.
"""
from datetime import date
from typing import Annotated, Literal, Union

from pydantic import AwareDatetime, Discriminator, Field, Tag, TypeAdapter, model_validator

from .common import Identifier, Name, Record, Sha256, StrictModel, VersionRef, Versioned
from .entities import (Approval, Assignment, AuditRun, Consent, DailyReport,
                       DecisionSnapshot, Delivery, Eligibility, Encounter, FollowUpTask,
                       IntercurrentEvent, ISIAssessment, MedicationExposure,
                       MedicationOrder, Observation, Patient, Recommendation,
                       WearableObservation)
from .boundaries import lineage_heads, no_postdeath_outcomes, validate_lineage, visible_records

Index = Annotated[int, Field(ge=0)]
Count = Annotated[int, Field(ge=0)]
PROBABILITY_TOLERANCE = 1e-12


class VersionedV2(Versioned):
    schema_version: Literal['2.0.0']


class RecordV2(Record):
    schema_version: Literal['2.0.0']


class ExactRef(StrictModel):
    record_id: Identifier
    payload_sha256: Sha256


class DailyReportV2(DailyReport):
    schema_version: Literal['2.0.0']
    diary_sleep_minutes: float | None

    @model_validator(mode='after')
    def diary_channel(self):
        if self.source.adapter != 'patient_report':
            raise ValueError('v2 diary requires the registered patient-report channel')
        return self


class OutcomeWindow(StrictModel):
    id: Identifier
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    assessment_at: AwareDatetime
    timezone: Name
    local_date: date
    endpoint_definition: VersionRef

    @model_validator(mode='after')
    def clock(self):
        if not self.starts_at < self.ends_at == self.assessment_at:
            raise ValueError('half-open next-morning outcome window required')
        return self


class SupportDecision(RecordV2):
    kind: Literal['support_decision']
    decision_snapshot: ExactRef
    decision_index: Index
    cutoff: AwareDatetime
    context: list[ExactRef]
    context_projection_sha256: Sha256
    context_mapping: VersionRef
    policy: VersionRef
    mechanism: VersionRef
    mode: Literal['fixed', 'mrt', 'adaptive', 'frozen', 'paused']
    eligibility: list[Eligibility]
    availability: Literal['unavailable', 'deterministic', 'randomized']
    unavailable_reasons: list[Name]
    probabilities: dict[Literal['support_prompt', 'no_prompt'], Annotated[float, Field(ge=0, le=1)]]
    probability_tolerance: Literal[1e-12]
    assignment_id: Identifier | None
    distribution_persisted_at: AwareDatetime
    execution_receipt: VersionRef
    outcome_window: OutcomeWindow
    outcome_link_id: Identifier

    @model_validator(mode='after')
    def executed_vector(self):
        actions = {'support_prompt', 'no_prompt'}
        if set(self.probabilities) != actions or {e.action for e in self.eligibility} != actions or len(self.eligibility) != 2:
            raise ValueError('complete two-action distribution and eligibility required')
        eligible = {e.action for e in self.eligibility if e.status == 'eligible'}
        if any(e.status != 'eligible' and not e.reasons for e in self.eligibility):
            raise ValueError('every excluded support action requires its reasons')
        p = self.probabilities
        if self.event_at != self.cutoff or self.outcome_window.starts_at != self.cutoff:
            raise ValueError('support event, cutoff and window start must agree')
        if not self.event_at <= self.distribution_persisted_at <= self.recorded_at:
            raise ValueError('distribution persistence clock required')
        if self.availability == 'unavailable':
            if eligible or any(p.values()) or self.assignment_id is not None or not self.unavailable_reasons:
                raise ValueError('unavailable requires zero vector, no assignment and reasons')
        else:
            if self.unavailable_reasons or self.assignment_id is None or abs(sum(p.values()) - 1) > PROBABILITY_TOLERANCE:
                raise ValueError('available distribution must normalize and bind assignment')
            if self.availability == 'deterministic':
                if len(eligible) != 1 or any(p[a] != float(a in eligible) for a in actions):
                    raise ValueError('deterministic requires exactly one eligible action')
            elif eligible != actions or any(not 0.1 <= p[a] <= 0.9 for a in actions):
                raise ValueError('randomized final masses must both be within [0.1,0.9]')
        return self


class Reward(StrictModel):
    status: Literal['observed', 'pending', 'missing', 'undefined']
    report_ref: ExactRef | None
    field: Literal['sleep_quality']
    unit: Literal['quality_points']
    reason: Name | None
    evidence_refs: list[ExactRef]
    definition_refs: list[VersionRef]

    @model_validator(mode='after')
    def status_evidence(self):
        if self.status == 'observed':
            if self.report_ref is None or self.reason is not None:
                raise ValueError('observed reward requires report and no copied value')
        elif self.report_ref is not None or self.reason is None:
            raise ValueError('non-observed reward requires reason and no report value')
        if self.status == 'missing' and not self.evidence_refs or self.status == 'undefined' and not (self.evidence_refs or self.definition_refs):
            raise ValueError('missing/undefined requires explicit reporting or terminal evidence')
        return self


class OperationalBurden(StrictModel):
    definition: VersionRef
    type: Literal['offered_prompt_count', 'delivered_prompt_count']
    unit: Literal['count']
    status: Literal['observed', 'pending', 'missing']
    value: Count | None
    source_refs: list[ExactRef]

    @model_validator(mode='after')
    def no_missing_zero(self):
        if (self.status == 'observed') != (self.value is not None):
            raise ValueError('only verified observed counts may have a value')
        return self


class SupportOutcomeLink(RecordV2):
    kind: Literal['support_outcome_link']
    support_decision: ExactRef
    assignment_ref: ExactRef | None
    window_id: Identifier
    assessment_at: AwareDatetime
    evaluated_as_of: AwareDatetime
    reward: Reward
    burden: list[OperationalBurden]
    offered_closure_ref: ExactRef | None
    delivered_closure_ref: ExactRef | None

    @model_validator(mode='after')
    def clocks(self):
        if not self.event_at == self.assessment_at <= self.evaluated_as_of <= self.recorded_at:
            raise ValueError('assessment <= knowledge <= publication required')
        if {b.type for b in self.burden} != {'offered_prompt_count', 'delivered_prompt_count'} or len(self.burden) != 2:
            raise ValueError('separate offered and delivered count states required')
        return self


class SupportStageClosureV2(RecordV2):
    kind: Literal['support_stage_closure']
    run_id: Identifier
    partition_id: Identifier
    support_decision: ExactRef
    assignment_ref: ExactRef | None
    window_id: Identifier
    decision_index: Index
    stage: Literal['offered', 'delivered']
    rule: VersionRef
    stage_completed_at: AwareDatetime
    status: Literal['complete', 'pending', 'missing']
    stage_event_refs: list[ExactRef]
    stage_ledger: VersionRef
    row_count: Count
    reason: Name
    completion_receipt: VersionRef | None

    @model_validator(mode='after')
    def completion(self):
        if self.stage_completed_at != self.event_at or self.row_count != len(self.stage_event_refs):
            raise ValueError('stage completion/event/count mismatch')
        if (self.status == 'complete') != (self.completion_receipt is not None):
            raise ValueError('complete stage requires exact completion receipt')
        if self.status != 'complete' and self.stage_event_refs:
            raise ValueError('pending/missing stage cannot claim an exhaustive event list')
        return self


class EvidenceRole(StrictModel):
    ref: ExactRef
    role: Literal['causal_context', 'transition_trigger', 'later_review']


class RequiredReview(StrictModel):
    requirement_id: Identifier
    definition: VersionRef
    responsible_role: Name
    status: Literal['pending', 'satisfied']
    evidence_refs: list[ExactRef]

    @model_validator(mode='after')
    def satisfied(self):
        if self.status == 'satisfied' and not self.evidence_refs:
            raise ValueError('satisfied review requires evidence')
        return self


class Clearance(StrictModel):
    status: Literal['not_applicable', 'pending', 'documented']
    rule: VersionRef | None
    evidence_refs: list[ExactRef]
    assessment_snapshot_ref: ExactRef | None


class HoldReviewEvidenceV2(RecordV2):
    kind: Literal['hold_review_evidence']
    run_id: Identifier
    partition_id: Identifier
    hold_episode_id: Identifier
    evidence_type: Literal['trigger_observation', 'review', 'clearance']
    rule: VersionRef
    requirement: VersionRef
    actor_id: Identifier
    actor_role: Name
    origin: Literal['simulation']
    ownership_ref: ExactRef
    assessed_at: AwareDatetime
    facts_refs: list[ExactRef]
    finding: Name
    review_result: Literal['pending', 'requires_hold', 'requirements_satisfied']
    follow_up_refs: list[ExactRef]

    @model_validator(mode='after')
    def clock(self):
        if self.assessed_at != self.event_at:
            raise ValueError('review assessment event mismatch')
        return self


class HoldTransitionBundleV2(RecordV2):
    kind: Literal['hold_transition_bundle']
    run_id: Identifier
    partition_id: Identifier
    hold_episode_id: Identifier
    transition_sequence: Index
    transition_type: Literal['baseline', 'enter', 'change_reason', 'resolve_to_assessment']
    effective_at: AwareDatetime
    snapshot_ref: ExactRef
    predecessor_bundle_ref: ExactRef | None
    predecessor_snapshot_ref: ExactRef | None
    reason_codes: list[Name]
    reason: Name
    trigger_refs: list[ExactRef]
    changed_fact_refs: list[ExactRef]
    blocked_actions: list[Identifier]
    context_cutoff: AwareDatetime
    causal_context_refs: list[ExactRef]
    context_projection_sha256: Sha256
    policy: VersionRef
    model: VersionRef
    eligibility_configuration: VersionRef
    owner_id: Identifier
    owner_role: Name
    ownership_ref: ExactRef
    follow_up_refs: Annotated[list[ExactRef], Field(min_length=1)]
    required_reviews: list[RequiredReview]
    review_refs: list[ExactRef]
    clearance: Clearance
    evidence_roles: list[EvidenceRole]

    @model_validator(mode='after')
    def transition(self):
        if self.effective_at != self.event_at or self.context_cutoff > self.event_at:
            raise ValueError('transition effective/context clock mismatch')
        baseline = self.transition_type == 'baseline'
        if baseline != (self.predecessor_bundle_ref is None and self.predecessor_snapshot_ref is None):
            raise ValueError('only baseline has no predecessor')
        if not baseline and (self.predecessor_bundle_ref is None or self.predecessor_snapshot_ref is None):
            raise ValueError('both exact predecessor references required')
        if baseline and self.transition_sequence != 0:
            raise ValueError('baseline sequence must be zero')
        if self.transition_type in ('enter', 'change_reason'):
            if not self.reason_codes or not self.trigger_refs or self.clearance.status != 'pending':
                raise ValueError('hold entry/change requires trigger/reasons and pending clearance')
        if self.transition_type == 'resolve_to_assessment':
            c = self.clearance
            if not self.required_reviews or any(r.status != 'satisfied' for r in self.required_reviews) or not self.review_refs:
                raise ValueError('resolution requires satisfied explicit reviews')
            if c.status != 'documented' or c.rule is None or not c.evidence_refs or c.assessment_snapshot_ref != self.snapshot_ref:
                raise ValueError('resolution requires documented rule/evidence and assessment')
        expected = {r.record_id for r in [*self.causal_context_refs, *self.trigger_refs, *self.changed_fact_refs, *self.review_refs, *self.clearance.evidence_refs,
                                         *[r for review in self.required_reviews for r in review.evidence_refs]]}
        if len({e.ref.record_id for e in self.evidence_roles}) != len(self.evidence_roles) or expected != {e.ref.record_id for e in self.evidence_roles}:
            raise ValueError('each evidence reference requires exactly one clock role')
        roles = {e.ref.record_id: e.role for e in self.evidence_roles}
        exact_roles = {e.ref.record_id: e.ref for e in self.evidence_roles}
        if any(exact_roles[r.record_id] != r for r in [*self.causal_context_refs, *self.trigger_refs, *self.changed_fact_refs, *self.review_refs, *self.clearance.evidence_refs,
                                                      *[r for review in self.required_reviews for r in review.evidence_refs]]):
            raise ValueError('evidence role must bind the same exact hash')
        if len({r.requirement_id for r in self.required_reviews}) != len(self.required_reviews):
            raise ValueError('duplicate required review')
        if any(roles[r.record_id] != 'causal_context' for r in self.causal_context_refs):
            raise ValueError('causal facts must have causal clock role')
        if any(roles[r.record_id] != 'later_review' for r in [*self.review_refs, *self.clearance.evidence_refs]):
            raise ValueError('review and clearance must retain later-review clock role')
        return self


_V1 = [Patient, Consent, Encounter, MedicationOrder, MedicationExposure, Observation, IntercurrentEvent,
       WearableObservation, DailyReport, ISIAssessment, DecisionSnapshot, Recommendation, Approval, Assignment,
       Delivery, FollowUpTask, AuditRun]
_V2 = [DailyReportV2, SupportDecision, SupportOutcomeLink, SupportStageClosureV2, HoldReviewEvidenceV2, HoldTransitionBundleV2]


def record_tag(value):
    if isinstance(value, dict):
        return f"{value.get('schema_version')}:{value.get('kind')}"
    return f'{value.schema_version}:{value.kind}'


ObservedRecordV2 = Annotated[Union[tuple(Annotated[model, Tag(f'{"2.0.0" if model in _V2 else "1.0.0"}:{model.model_fields["kind"].annotation.__args__[0]}')] for model in [*_V1, *_V2])], Discriminator(record_tag)]
RECORD_ADAPTER_V2 = TypeAdapter(ObservedRecordV2)


class RecordProvenanceV2(RecordV2):
    schema_version: Literal['1.0.0', '2.0.0']
    kind: Identifier


def provenance_v2(record):
    return RecordProvenanceV2.model_validate(record.model_dump(include=set(Record.model_fields) | {'kind'}))


def validate_lineage_v2(records):
    validate_lineage(records)
    by_id = {r.record_id: r for r in records}
    for r in records:
        for dependency in (r.supersedes, r.duplicate_of):
            if dependency and by_id[dependency].schema_version != r.schema_version:
                raise ValueError('cross-version correction/duplicate forbidden')


class LearnerHistoryV2(VersionedV2):
    kind: Literal['learner_history']
    patient_id: Identifier
    cutoff: AwareDatetime
    records: list[ObservedRecordV2]
    provenance: list[RecordProvenanceV2]

    @model_validator(mode='after')
    def projection(self):
        all_records = [*self.records, *self.provenance]
        if any(r.patient_id != self.patient_id for r in all_records):
            raise ValueError('projection patient mismatch')
        validate_lineage_v2(self.provenance)
        if len(visible_records(self.provenance, self.cutoff)) != len(self.provenance):
            raise ValueError('strict-before cutoff required')
        expected = {r.record_id: r for r in lineage_heads(self.provenance) if r.record_status != 'retracted'}
        if len({r.record_id for r in self.records}) != len(self.records) or {r.record_id for r in self.records} != set(expected):
            raise ValueError('values must exactly match active visible heads')
        if any(provenance_v2(r) != expected[r.record_id] for r in self.records):
            raise ValueError('projection provenance mismatch')
        no_postdeath_outcomes(self.records)
        return self


class ObservedHistoryV2(VersionedV2):
    kind: Literal['observed_history']
    patient_id: Identifier
    records: list[ObservedRecordV2]

    @model_validator(mode='after')
    def lineage(self):
        if any(r.patient_id != self.patient_id for r in self.records):
            raise ValueError('history patient mismatch')
        validate_lineage_v2(self.records)
        no_postdeath_outcomes([r for r in lineage_heads(self.records) if r.record_status != 'retracted'])
        return self

    def as_known_at(self, cutoff):
        return [r for r in lineage_heads(visible_records(self.records, cutoff)) if r.record_status != 'retracted']

    def project(self, cutoff):
        return LearnerHistoryV2(schema_version='2.0.0', synthetic=True, kind='learner_history', patient_id=self.patient_id,
                                cutoff=cutoff, records=self.as_known_at(cutoff),
                                provenance=[provenance_v2(r) for r in visible_records(self.records, cutoff)])


from .estimands import FitRequest


class LearnerInputV2(VersionedV2):
    kind: Literal['learner_input']
    request: FitRequest
    history: LearnerHistoryV2

    @model_validator(mode='after')
    def cutoff(self):
        cutoff = self.request.context.observation_cutoff
        if self.history.cutoff != cutoff:
            raise ValueError('learner request/projection cutoff mismatch')
        for record in self.history.records:
            measures = record.covariates if record.kind == 'patient' else [record.measure] if record.kind == 'observation' else []
            if any(m.observed_at > cutoff or m.available_at >= cutoff for m in measures):
                raise ValueError('nested future/unavailable covariate')
        return self
