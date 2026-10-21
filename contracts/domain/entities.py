"""Observed records and decision contracts; no evaluator truth is accepted here."""
from datetime import date, timedelta
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .common import (Action, Component, FitMetadata, Identifier, Name, Nonnegative,
                     PositiveInt, Probability, Record, SeedKey, StrictModel,
                     Versioned, VersionRef)

ClinicalState = Literal["assessment", "initial_assignment", "treatment_active", "scheduled_reassessment", "maintenance_closeout", "clinical_hold"]
LearningState = Literal["none", "nof1_design", "nof1_block", "nof1_washout", "nof1_review", "escalation_decision", "support_active", "support_frozen", "support_unavailable"]
Measure = Literal["pain", "nausea", "distress", "fatigue", "sleep_quality", "function", "adverse_symptom", "sleep_minutes", "wake_minutes", "age_years", "X", "M", "U", "site", "phase", "steroid_indicator"]


class ObservedCovariate(StrictModel):
    concept: Measure
    value: float
    unit: Literal["dimensionless", "quality_points", "function_points", "minutes", "years", "indicator"]
    observed_at: AwareDatetime
    available_at: AwareDatetime

    @model_validator(mode="after")
    def observed_first(self):
        if self.observed_at > self.available_at:
            raise ValueError("covariate unavailable before observation")
        expected_unit = {"sleep_quality": "quality_points", "function": "function_points", "fatigue": "function_points",
                         "sleep_minutes": "minutes", "wake_minutes": "minutes", "age_years": "years",
                         "M": "indicator", "steroid_indicator": "indicator"}.get(self.concept, "dimensionless")
        if self.unit != expected_unit:
            raise ValueError("observed measure unit does not match the versioned dictionary")
        return self


class Patient(Record):
    kind: Literal["patient"]
    covariates: list[ObservedCovariate]
    diagnosis_context: Name
    clinical_context: Name
    preferences: list[Name]
    goals: list[Name]
    baseline_eligibility: list[Name]
    care_team: list[Identifier]
    timezone: Name


class Consent(Record):
    kind: Literal["consent"]
    component: Component
    consent_version: Name
    oversight_version: Name
    consent_status: Literal["active", "missing", "expired", "withdrawn"]
    oversight_status: Literal["approved_synthetic", "pending", "expired", "withdrawn"]
    effective_at: AwareDatetime
    expires_at: AwareDatetime | None
    withdrawn_at: AwareDatetime | None

    @model_validator(mode="after")
    def consistency(self):
        if self.expires_at is not None and self.expires_at <= self.effective_at:
            raise ValueError("consent expiry precedes effective time")
        if self.consent_status == "withdrawn" and self.withdrawn_at is None:
            raise ValueError("withdrawal requires time")
        if self.withdrawn_at is not None and self.withdrawn_at < self.effective_at:
            raise ValueError("withdrawal precedes consent")
        return self

    def permits(self, component: Component, at: AwareDatetime) -> bool:
        return (component == self.component and self.consent_status == "active"
                and self.record_status != "retracted"
                and self.oversight_status == "approved_synthetic"
                and self.available_at <= at and self.effective_at <= at
                and (self.expires_at is None or at < self.expires_at)
                and (self.withdrawn_at is None or at < self.withdrawn_at))


class Encounter(Record):
    kind: Literal["encounter"]
    scheduled_at: AwareDatetime
    actual_at: AwareDatetime | None
    care_setting: Literal["outpatient", "inpatient", "remote"]
    chemotherapy_phase: Name
    cycle: PositiveInt
    review_status: Literal["pending", "reviewed", "hold"]


class MedicationOrder(Record):
    kind: Literal["medication_order"]
    drug: Literal["MED_A", "MED_B"]
    intended_schedule: Name
    starts_at: AwareDatetime
    changed_at: AwareDatetime | None
    stopped_at: AwareDatetime | None
    ordering_clinician: Identifier


class MedicationExposure(Record):
    kind: Literal["medication_exposure"]
    drug: Literal["MED_A", "MED_B"]
    order_ref: Identifier | None
    administration_at: AwareDatetime
    report_status: Literal["taken", "not_taken", "uncertain"]
    adherence: Probability | None
    rescue: bool
    uncertainty: Name


class Observation(Record):
    kind: Literal["observation"]
    measure: ObservedCovariate
    lab_reference_context: Name | None

    @model_validator(mode="after")
    def observation_clock(self):
        if self.measure.observed_at != self.event_at or self.measure.available_at > self.available_at:
            raise ValueError("nested observation must retain its event/availability chronology")
        return self


class IntercurrentEvent(Record):
    kind: Literal["intercurrent_event"]
    event_type: Literal["death", "admission", "discharge", "regimen_change", "steroid_change", "discontinuation", "override", "rescue", "fever_suspected_infection", "confusion", "fall"]
    detail: Name


class WearableObservation(Record):
    kind: Literal["oura_like"]
    record_type: Literal["sleep_episode"]
    local_date: date
    timezone: Name
    episode_start: AwareDatetime
    episode_end: AwareDatetime
    sync_at: AwareDatetime
    estimated_sleep_minutes: Nonnegative | None
    estimated_wake_minutes: Nonnegative | None
    device_version: Name
    quality_flags: list[Name]
    missingness: Literal["observed", "missing", "quality_rejected"]

    @model_validator(mode="after")
    def episode(self):
        if not self.episode_start < self.episode_end <= self.event_at <= self.sync_at <= self.available_at:
            raise ValueError("sleep episode/event/sync chronology")
        measures = (self.estimated_sleep_minutes, self.estimated_wake_minutes)
        if self.missingness != "observed" and any(v is not None for v in measures):
            raise ValueError("missing/rejected wearable cannot masquerade as measured sleep")
        return self


class DailyReport(Record):
    kind: Literal["daily_report"]
    sleep_quality: Annotated[float, Field(ge=0, le=10)] | None
    function: Annotated[float, Field(ge=0, le=10)] | None
    adverse_symptoms: list[Name]
    diary_sleep_minutes: Nonnegative | None
    goals: list[Name]
    burden: Nonnegative | None
    missingness: Literal["observed", "missing", "pending"]

    @model_validator(mode="after")
    def missing_is_not_zero(self):
        if self.missingness != "observed" and any(v is not None for v in (self.sleep_quality, self.function, self.diary_sleep_minutes, self.burden)):
            raise ValueError("missing/pending reports cannot contain fabricated values")
        return self


class ISIAssessment(Record):
    kind: Literal["isi"]
    instrument_version: Name
    recall_days: Literal[14, 30]
    recall_start: AwareDatetime
    recall_end: AwareDatetime
    items: Annotated[list[Annotated[int, Field(ge=0, le=4)]], Field(min_length=7, max_length=7)]

    @model_validator(mode="after")
    def recall(self):
        if self.recall_end - self.recall_start != timedelta(days=self.recall_days) or self.recall_end > self.event_at:
            raise ValueError("ISI recall interval/version must be explicit and complete before assessment")
        return self

    @property
    def total(self) -> int:
        return sum(self.items)


class ExternalStudy(Versioned):
    kind: Literal["external_study"]
    study: VersionRef
    population: Name
    intervention: Name
    comparator: Name
    outcome: Name
    scale: Literal["ISI_points"]
    follow_up_days: PositiveInt
    likelihood_input: Literal["summary", "ipd"]
    effect: float | None
    standard_error: Annotated[float, Field(gt=0)] | None
    ipd: VersionRef | None
    covariate_distribution: list[ObservedCovariate]
    blinding: Literal["open_label", "patient_blinded", "double_blinded"]
    bias_transport_notes: list[Name]
    rationale_source_ids: list[Identifier]

    @model_validator(mode="after")
    def one_likelihood(self):
        if self.likelihood_input == "summary":
            if self.effect is None or self.standard_error is None or self.ipd is not None:
                raise ValueError("summary requires effect/SE and excludes IPD")
        elif self.ipd is None or self.effect is not None or self.standard_error is not None:
            raise ValueError("IPD likelihood excludes the same study summary")
        return self


class ViewContext(StrictModel):
    patient_id: Identifier
    mode: Literal["current", "historical", "retrospective_evaluation"]
    snapshot_id: Identifier | None

    @model_validator(mode="after")
    def historical_reference(self):
        if self.mode != "current" and self.snapshot_id is None:
            raise ValueError("historical/evaluation view requires snapshot")
        return self


class Workflow(StrictModel):
    clinical: ClinicalState
    learning: LearningState
    data_readiness: Literal["ready", "incomplete", "stale", "failed"]
    hold_reasons: list[Name]
    support_policy: VersionRef
    support_mode: Literal["fixed", "mrt", "adaptive", "frozen", "paused"]

    @model_validator(mode="after")
    def hold_and_freeze(self):
        if self.clinical == "clinical_hold" and not self.hold_reasons:
            raise ValueError("hold requires reasons")
        if self.learning in ("nof1_block", "nof1_washout") and self.support_mode not in ("frozen", "fixed", "paused"):
            raise ValueError("N-of-1 active/washout forbids drifting support")
        return self


class Eligibility(StrictModel):
    action: Action
    status: Literal["eligible", "excluded", "requires_prescriber_review"]
    reasons: list[Name]


class DecisionSnapshot(Record):
    kind: Literal["decision_snapshot"]
    cutoff: AwareDatetime
    patient_version: PositiveInt
    state_version: PositiveInt
    consent_version: PositiveInt
    eligibility_version: PositiveInt
    workflow: Workflow
    view: ViewContext
    eligibility: list[Eligibility]
    outcome: Name
    horizon_days: PositiveInt
    estimand: VersionRef
    model: VersionRef
    posterior: VersionRef | None
    evidence: list[VersionRef]
    policy: VersionRef

    @model_validator(mode="after")
    def snapshot(self):
        if self.view.patient_id != self.patient_id or self.cutoff > self.event_at:
            raise ValueError("snapshot patient/cutoff mismatch")
        if len({x.action for x in self.eligibility}) != len(self.eligibility):
            raise ValueError("duplicate eligibility action")
        return self


class Recommendation(Record):
    kind: Literal["recommendation"]
    decision_id: Identifier
    option: Action | None
    reason: Name


class Approval(Record):
    kind: Literal["approval"]
    decision_id: Identifier
    option: Action | None
    permitted_options: list[Action]
    clinician_id: Identifier
    purpose: Literal["ordinary_treatment", "randomization_protocol"]
    expected_patient_version: PositiveInt
    expected_state_version: PositiveInt
    expected_consent_version: PositiveInt
    expected_eligibility_version: PositiveInt

    @model_validator(mode="after")
    def ordinary_vs_protocol(self):
        if self.purpose == "ordinary_treatment":
            if self.option is None or self.permitted_options:
                raise ValueError("ordinary choice requires one explicit option")
        elif self.option is not None or not self.permitted_options or len(set(self.permitted_options)) != len(self.permitted_options):
            raise ValueError("protocol approval authorizes a set, never preselects a randomized winner")
        return self


class Assignment(Record):
    kind: Literal["assignment"]
    decision_id: Identifier
    approval_id: Identifier
    option: Action
    experimental: bool
    component: Component | None
    probability: Annotated[float, Field(gt=0, le=1)] | None
    seed: SeedKey | None
    support_policy: VersionRef
    patient_blinded: bool
    clinician_blinded: bool
    clinician_override: Action | None
    override_reason: Name | None

    @model_validator(mode="after")
    def randomization_metadata(self):
        if self.experimental and any(x is None for x in (self.component, self.probability, self.seed)):
            raise ValueError("randomized assignment requires component, known probability and seed")
        if not self.experimental and any(x is not None for x in (self.component, self.probability, self.seed)):
            raise ValueError("ordinary choice is not a randomized assignment")
        if self.clinician_override is not None and self.override_reason is None:
            raise ValueError("override requires reason; original assignment retained")
        if self.component == "mrt_bandit" and self.option not in ("support_prompt", "no_prompt"):
            raise ValueError("support randomization cannot assign medication")
        return self


class Delivery(Record):
    kind: Literal["delivery"]
    assignment_id: Identifier
    option: Action
    stage: Literal["offered", "delivered", "taken", "not_taken", "unknown"]
    adherence: Probability | None
    rescue: bool
    protocol_deviations: list[Name]


class FollowUpTask(Record):
    kind: Literal["follow_up"]
    owner: Identifier
    due_at: AwareDatetime
    trigger: Name
    status: Literal["pending", "active", "completed", "cancelled"]
    escalation_destination: Identifier


class AuditRun(Record):
    kind: Literal["audit_run"]
    actor: Identifier
    change: Name
    input_versions: list[VersionRef]
    seed: SeedKey
    fit: FitMetadata | None
    execution_seconds: Nonnegative
    lineage_refs: list[Identifier]


ObservedRecord = Annotated[Patient | Consent | Encounter | MedicationOrder | MedicationExposure | Observation | IntercurrentEvent | WearableObservation | DailyReport | ISIAssessment | DecisionSnapshot | Recommendation | Approval | Assignment | Delivery | FollowUpTask | AuditRun, Field(discriminator="kind")]
