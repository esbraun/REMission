"""Versioned structural ordering and observed-only reporting boundaries."""
from datetime import timedelta
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .common import Identifier, Name, PositiveInt, StrictModel, Versioned
from .estimands import EstimandID
from .boundaries import LearnerHistory


class ReportingRules(StrictModel):
    pain_source: Literal["independent_observed_clinical_record_before_report_decision"]
    pre_report_history: Literal["strictly_available_before_decision_excluding_current_report"]
    previous_quality: Literal["latest_active_observed_report_event_before_current_event"]
    absent_quality: Literal["baseline_7_with_missing_history_indicator"]
    mar_predictors: Literal["previous_observed_quality_missing_indicator_and_current_observed_pain_only"]
    recording: Literal["report_decision_time_not_morning_outcome_event_time"]
    upload: Literal["recording_plus_independently_keyed_0_1_3_day_delay"]
    wearable: Literal["separate_stream_no_report_or_current_pain_parent"]
    equal_time: Literal["strict_before_excludes_all_equal_time_arrivals_phase_then_record_id_for_replay"]


class ReportingDecision(Versioned):
    """Observed MAR inputs only; MNAR truth stays outside this contract."""
    kind: Literal["reporting_decision"]
    temporal_version: Literal["2.0.0"]
    patient_id: Identifier
    report_event_at: AwareDatetime
    decision_at: AwareDatetime
    recorded_at: AwareDatetime
    available_at: AwareDatetime
    upload_delay_days: Literal[0, 1, 3]
    pain_record_id: Identifier
    pre_report_history: LearnerHistory

    @model_validator(mode="after")
    def observed_pain_and_clock(self):
        history = self.pre_report_history
        if self.patient_id != history.patient_id or history.cutoff != self.decision_at:
            raise ValueError("pre-report history must belong to this patient and exact decision cutoff")
        if self.recorded_at != self.decision_at or self.available_at != self.recorded_at + timedelta(days=self.upload_delay_days):
            raise ValueError("record at reporting decision; upload delay starts at recording, not outcome event")
        if not self.report_event_at < self.decision_at:
            raise ValueError("morning outcome event must precede reporting decision")
        if any(r.kind == "intercurrent_event" and r.event_type == "death" and r.event_at <= self.decision_at
               for r in history.records):
            raise ValueError("no new reporting decision after known death; earlier uploads retain their original decision time")
        if any(r.kind == "daily_report" and r.event_at >= self.report_event_at for r in history.records):
            raise ValueError("current/future report cannot be a pre-report MAR input")
        pain = next((r for r in history.records if r.record_id == self.pain_record_id), None)
        if (pain is None or pain.kind != "observation" or pain.measure.concept != "pain"
                or pain.duplicate_of is not None or pain.record_status == "retracted"
                or not self.report_event_at < pain.event_at < self.decision_at
                or pain.event_at - self.report_event_at >= timedelta(days=1)
                or pain.measure.available_at >= self.decision_at):
            raise ValueError("independent current observed pain must be available before report decision")
        return self

    def mar_predictors(self) -> dict[str, float | bool]:
        """No current quality, latent L, wearable proxy or post-decision field is used."""
        pain = next(r for r in self.pre_report_history.records if r.record_id == self.pain_record_id)
        previous = max((r for r in self.pre_report_history.records
                        if r.kind == "daily_report" and r.missingness == "observed" and r.sleep_quality is not None),
                       key=lambda r: (r.event_at, r.available_at, r.recorded_at, r.record_id), default=None)
        return {"previous_observed_quality": 7.0 if previous is None else previous.sleep_quality,
                "missing_quality_history": previous is None, "current_observed_pain": pain.measure.value}


class Parent(StrictModel):
    variable: Identifier
    day_offset: Annotated[int, Field(le=0)]


class Variable(StrictModel):
    id: Identifier
    phase: Annotated[int, Field(ge=0)]
    unit: Name
    visibility: Literal["observed", "evaluator_only", "administrative"]
    parents: list[Parent]
    role_by_estimand: dict[EstimandID, Literal["covariate", "treatment", "mediator", "outcome", "observation_indicator", "intercurrent_event", "administrative"]]
    postassignment_role_by_estimand: dict[EstimandID, Literal["covariate", "treatment", "mediator", "outcome", "observation_indicator", "intercurrent_event", "administrative"]]
    source_locator: Name


class TemporalContract(Versioned):
    kind: Literal["temporal_contract"]
    id: Literal["TIME-01"]
    version: Literal["1.0.0", "2.0.0"]
    timestamp_rule: Literal["timezone_aware_utc_order_local_calendar_preserved"]
    learner_cutoff_rule: Literal["event_at_lte_cutoff_recorded_and_available_strictly_before"]
    tie_rule: Literal["phase_then_stable_record_id_known_holds_and_withdrawals_before_draw"]
    daily_factorization: Annotated[list[Name], Field(min_length=1)]
    initial_distribution: Literal["must_be_versioned_by_G0_DGP_before_generation"]
    irregular_visit_process: Literal["must_be_versioned_by_G0_DGP_before_generation"]
    variables: Annotated[list[Variable], Field(min_length=1)]
    pending_numerical_decisions: Annotated[list[Name], Field(min_length=1)]
    reporting: ReportingRules | None = None

    @model_validator(mode="after")
    def no_future_or_same_phase_cycle(self):
        variables = {v.id: v for v in self.variables}
        if len(variables) != len(self.variables):
            raise ValueError("duplicate structural variable")
        for variable in self.variables:
            if not variable.role_by_estimand or variable.role_by_estimand.keys() != variable.postassignment_role_by_estimand.keys():
                raise ValueError("each variable requires estimand-specific role declarations")
            for parent in variable.parents:
                if parent.variable not in variables:
                    raise ValueError("unknown structural parent")
                if parent.day_offset == 0 and variables[parent.variable].phase >= variable.phase:
                    raise ValueError("same-day parent must precede child, preventing cycles/future leakage")
        if self.version == "1.0.0" and self.reporting is not None:
            raise ValueError("reporting-v2 rules cannot be attached to historical temporal-v1")
        if self.version == "2.0.0":
            if self.reporting is None:
                raise ValueError("temporal-v2 requires explicit reporting boundaries")
            required = {"observed_pain": {("clinical_L", 0)},
                        "pre_report_history": {("observed_pain", 0), ("available_history", -1)},
                        "report_observation": {("observed_pain", 0), ("pre_report_history", 0)},
                        "report_availability": {("report_observation", 0), ("morning_measurements", 0)},
                        "wearable_availability": {("morning_measurements", 0)},
                        "available_history": {("report_availability", 0), ("wearable_availability", 0)}}
            for name, parents in required.items():
                if name not in variables or not parents <= {(p.variable, p.day_offset) for p in variables[name].parents}:
                    raise ValueError("temporal-v2 missing required reporting variable/parent")
            if variables["observed_pain"].visibility != "observed":
                raise ValueError("MAR pain cannot be evaluator-only")
            exact = {"observed_pain": {("clinical_L", 0)},
                     "pre_report_history": {("available_history", -1), ("wearable_availability", 0), ("observed_pain", 0)}}
            for name, parents in exact.items():
                if {(p.variable, p.day_offset) for p in variables[name].parents} != parents:
                    raise ValueError("independent pain/pre-report history cannot acquire hidden or current-report parents")
            # Only the observed pain record and prior available history may
            # inform MAR; no direct current quality/severity/truth parent.
            if {p.variable for p in variables["report_observation"].parents} != {"observed_pain", "pre_report_history", "innovations"}:
                raise ValueError("MAR observation parents exclude hidden/current-outcome predictors")
            if {p.variable for p in variables["wearable_availability"].parents} != {"morning_measurements", "innovations"}:
                raise ValueError("wearable stream must be independent of report/current pain")
        return self
