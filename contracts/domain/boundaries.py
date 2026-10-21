"""Pure boundary checks. Storage, transactions and worker execution belong to G1/G5."""
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .common import Component, Identifier, Name, Versioned, VersionRef
from .entities import (Approval, Assignment, Consent, DecisionSnapshot,
                       ISIAssessment, ObservedRecord, ViewContext)
from .estimands import EstimandContract, FitRequest


class ContractViolation(ValueError):
    """Stable machine-readable reason with a display-safe explanation."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class ObservedHistory(Versioned):
    kind: Literal["observed_history"]
    patient_id: Identifier
    records: list[ObservedRecord]

    @model_validator(mode="after")
    def lineage_and_outcomes(self):
        ids = {r.record_id: r for r in self.records}
        if len(ids) != len(self.records) or any(r.patient_id != self.patient_id for r in self.records):
            raise ValueError("history must have unique record IDs and one patient")
        if len({(r.lineage_id, r.revision) for r in self.records if r.duplicate_of is None}) != sum(r.duplicate_of is None for r in self.records):
            raise ValueError("lineage revision must be unique")
        successors = set()
        for record in self.records:
            if record.supersedes is not None:
                prior = ids.get(record.supersedes)
                if (prior is None or prior.lineage_id != record.lineage_id or prior.kind != record.kind
                        or prior.event_at != record.event_at or prior.revision + 1 != record.revision
                        or prior.available_at > record.available_at or record.supersedes in successors):
                    raise ValueError("correction must extend exactly one same-event lineage")
                successors.add(record.supersedes)
            if record.duplicate_of is not None:
                prior = ids.get(record.duplicate_of)
                if (prior is None or prior.kind != record.kind or prior.event_at != record.event_at
                        or prior.source.raw_sha256 != record.source.raw_sha256
                        or prior.available_at > record.available_at or prior.duplicate_of is not None):
                    raise ValueError("duplicate must identify an earlier original payload")
        latest = [r for r in self.records if r.record_id not in successors and r.record_status != "retracted" and r.duplicate_of is None]
        deaths = [r.event_at for r in latest if r.kind == "intercurrent_event" and r.event_type == "death"]
        if deaths and any(r.kind in ("isi", "daily_report") and r.event_at >= min(deaths) for r in latest):
            raise ValueError("no symptom outcome exists after death")
        return self

    def as_known_at(self, cutoff: AwareDatetime) -> list[ObservedRecord]:
        visible = [r for r in self.records if r.event_at <= cutoff and r.recorded_at < cutoff and r.available_at < cutoff and r.duplicate_of is None]
        superseded = {r.supersedes for r in visible if r.supersedes is not None}
        return sorted([r for r in visible if r.record_id not in superseded and r.record_status != "retracted"],
                      key=lambda r: (r.available_at, r.recorded_at, r.record_id))


class LearnerInput(Versioned):
    kind: Literal["learner_input"]
    request: FitRequest
    history: ObservedHistory

    @model_validator(mode="after")
    def only_available(self):
        cutoff = self.request.context.observation_cutoff
        if {r.record_id for r in self.history.records} != {r.record_id for r in self.history.as_known_at(cutoff)}:
            raise ValueError("learner payload must contain only active records available before cutoff")
        for record in self.history.records:
            covariates = record.covariates if record.kind == "patient" else [record.measure] if record.kind == "observation" else []
            if any(c.observed_at > cutoff or c.available_at >= cutoff for c in covariates):
                raise ValueError("nested future/unavailable covariate denied")
        return self


def validate_fit_request(request: FitRequest, accepted: list[VersionRef]) -> None:
    """Call before scheduling a costly worker. No default/fallback configuration."""
    allowed = {(ref.id, ref.version, ref.sha256) for ref in accepted}
    context = request.context
    required = [context.estimand, context.dgp, context.scenario, context.input_data,
                context.prior, context.model, context.protocol,
                context.comparator_estimand, request.configuration]
    if any((ref.id, ref.version, ref.sha256) not in allowed for ref in required):
        raise ContractViolation("unsupported_input_version", "Every input/version/hash must be independently accepted before fit dispatch")


def ensure_isi_comparable(records: Annotated[list[ISIAssessment], Field(min_length=1)]) -> None:
    if not records:
        raise ContractViolation("no_isi", "No ISI observations to compare")
    if len({(r.instrument_version, r.recall_days) for r in records}) > 1:
        raise ContractViolation("incompatible_isi", "Different instrument versions/recall intervals cannot be trended together")


def validate_isi_endpoint(assessment: ISIAssessment, estimand: EstimandContract) -> None:
    if (assessment.instrument_version != estimand.isi_instrument_version
            or assessment.recall_days != estimand.isi_recall_days):
        raise ContractViolation("incompatible_isi", "Endpoint instrument and recall must match the estimand")
    if assessment.recall_start < estimand.time_zero:
        raise ContractViolation("mixed_recall", "Outcome window must be wholly postassignment")


def validate_approval(approval: Approval, current: DecisionSnapshot, view: ViewContext,
                      actor_role: Literal["doctor", "nurse", "behavioral_clinician", "researcher"],
                      at: AwareDatetime, component: Component | None,
                      consents: list[Consent]) -> None:
    if view.mode != "current" or current.view.mode != "current":
        raise ContractViolation("historical_write", "Historical and retrospective views are read-only")
    if view.patient_id != current.patient_id or approval.patient_id != current.patient_id:
        raise ContractViolation("patient_mismatch", "Patient switch invalidates approval draft")
    if actor_role != "doctor":
        raise ContractViolation("permission_denied", "Treatment/protocol approval requires clinician authority")
    expected = (approval.expected_patient_version, approval.expected_state_version,
                approval.expected_consent_version, approval.expected_eligibility_version)
    actual = (current.patient_version, current.state_version, current.consent_version,
              current.eligibility_version)
    if approval.decision_id != current.record_id or expected != actual:
        raise ContractViolation("stale_approval", "Refresh state, consent and eligibility before approving")
    if current.available_at > at or approval.event_at > at:
        raise ContractViolation("future_approval", "Approval/current context must exist before assignment")
    if current.workflow.clinical == "clinical_hold" or current.workflow.hold_reasons:
        raise ContractViolation("clinical_hold", "Clinical hold blocks assignment")
    if current.workflow.data_readiness != "ready":
        raise ContractViolation("data_unready", "Data readiness blocks approval")
    options = [approval.option] if approval.purpose == "ordinary_treatment" else approval.permitted_options
    if not all(any(e.action == action and e.status == "eligible" for e in current.eligibility) for action in options):
        raise ContractViolation("ineligible_action", "Action excluded or requires prescriber review")
    if component is not None:
        if approval.purpose != "randomization_protocol":
            raise ContractViolation("wrong_approval_purpose", "Ordinary treatment approval cannot authorize randomization")
        candidates = [c for c in consents if c.patient_id == current.patient_id and c.component == component and c.available_at <= at]
        latest = max(candidates, key=lambda c: (c.available_at, c.revision, c.record_id), default=None)
        if latest is None or not latest.permits(component, at):
            raise ContractViolation("consent_unavailable", "Missing, expired or withdrawn component consent/oversight blocks draw")
    elif approval.purpose != "ordinary_treatment":
        raise ContractViolation("wrong_approval_purpose", "Randomization approval is separate from ordinary treatment choice")


def validate_assignment(assignment: Assignment, approval: Approval,
                        current: DecisionSnapshot, view: ViewContext,
                        actor_role: Literal["doctor", "nurse", "behavioral_clinician", "researcher"],
                        consents: list[Consent]) -> None:
    validate_approval(approval, current, view, actor_role, assignment.event_at,
                      assignment.component, consents)
    approved_options = [approval.option] if approval.purpose == "ordinary_treatment" else approval.permitted_options
    if (assignment.patient_id != approval.patient_id or assignment.approval_id != approval.record_id
            or assignment.decision_id != current.record_id or assignment.option not in approved_options):
        raise ContractViolation("assignment_mismatch", "Assignment must retain its exact approved option and context")
    if assignment.support_policy != current.workflow.support_policy:
        raise ContractViolation("support_version_mismatch", "Assignment must retain the support policy in force")
    if assignment.clinician_override is not None and not any(e.action == assignment.clinician_override and e.status == "eligible" for e in current.eligibility):
        raise ContractViolation("ineligible_override", "Clinician override must remain inside current eligibility")
