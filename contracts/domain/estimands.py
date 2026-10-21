"""Semantic estimand and outcome contracts; no patient-specific potential outcomes."""
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .common import (Action, Estimate, Identifier, Name, Nonnegative, PositiveInt,
                     Probability, SeedKey, StrictModel, Versioned, VersionRef)

EstimandID = Literal["EST-VISIT", "EST-N1", "EST-ESC-STAGE", "EST-ESC-STRATEGY", "EST-MRT", "EST-POLICY", "EST-INT"]
EventType = Literal["death", "admission", "regimen_change", "steroid_change", "rescue", "discontinuation", "override"]


class EventStrategy(StrictModel):
    event: EventType
    strategy: Literal["separate_survival_and_conditional_symptoms", "separate_admission_and_conditional_symptoms", "treatment_policy"]
    explanation: Name

    @model_validator(mode="after")
    def terminal_outcomes(self):
        expected = ("separate_survival_and_conditional_symptoms" if self.event == "death" else
                    "separate_admission_and_conditional_symptoms" if self.event == "admission" else "treatment_policy")
        if self.strategy != expected:
            raise ValueError("demo event strategy must retain EST-INT/assignment outcomes")
        return self


class Horizon(StrictModel):
    amount: PositiveInt
    unit: Literal["days", "protocol_blocks", "protocol_stages", "cohorts"]
    endpoint_rule: Name
    protocol: VersionRef


class EstimandContract(Versioned):
    kind: Literal["estimand"]
    estimand_id: EstimandID
    estimand_version: Literal["1.0.0"]
    population: Name
    eligibility_rule: VersionRef
    history: Literal["available_observed_preassignment_only"]
    observation_cutoff: AwareDatetime
    time_zero: AwareDatetime
    intervention: Action
    comparator: Action
    contrast: Literal["assignment"]
    patient_blinded: bool
    clinician_blinded: bool
    outcome: Literal["ISI", "daily_sleep_quality", "function", "proximal_support_reward", "policy_value", "interruption_vector"]
    unit: Literal["ISI_points", "quality_points", "function_points", "probability_vector"]
    direction: Literal["lower_is_better", "higher_is_better", "no_overall_order"]
    horizon: Horizon
    continuation_policy: VersionRef
    support_policy: VersionRef
    intervention_strategy: VersionRef | None
    comparator_strategy: VersionRef | None
    intervention_policy: VersionRef | None
    comparator_policy: VersionRef | None
    policy_value_target: Literal["fixed_contextual", "complete_cohort_algorithm"] | None
    event_strategies: Annotated[list[EventStrategy], Field(min_length=7, max_length=7)]
    missing_data_assumptions: list[Name]
    identification_assumptions: Annotated[list[Name], Field(min_length=1)]
    comparator_information: Literal["same_permitted_history", "privileged_oracle_report_only"]
    source_ids: Annotated[list[Identifier], Field(min_length=1)]
    isi_instrument_version: Name | None
    isi_recall_days: Literal[14, 30] | None
    earliest_isi_days_after_assignment: PositiveInt | None
    limitations: Annotated[list[Name], Field(min_length=1)]

    @model_validator(mode="after")
    def coherence(self):
        if self.intervention == self.comparator or self.observation_cutoff > self.time_zero:
            raise ValueError("contrast requires distinct actions and no future cutoff")
        if {e.event for e in self.event_strategies} != {"death", "admission", "regimen_change", "steroid_change", "rescue", "discontinuation", "override"}:
            raise ValueError("exact per-event strategies required")
        if self.outcome in ("ISI", "interruption_vector"):
            if any(x is None for x in (self.isi_instrument_version, self.isi_recall_days, self.earliest_isi_days_after_assignment)):
                raise ValueError("ISI instrument/recall/first valid outcome must be explicit")
            if self.earliest_isi_days_after_assignment < self.isi_recall_days:
                raise ValueError("first postassignment ISI must not mix preassignment nights")
        elif any(x is not None for x in (self.isi_instrument_version, self.isi_recall_days, self.earliest_isi_days_after_assignment)):
            raise ValueError("non-ISI endpoint cannot borrow ISI metadata")
        if self.estimand_id in ("EST-VISIT", "EST-INT") and (self.horizon.amount != 42 or self.horizon.unit != "days"):
            raise ValueError("reference visit/interruptions require day-42 endpoint")
        if self.estimand_id == "EST-INT" and (self.outcome != "interruption_vector" or self.direction != "no_overall_order" or self.unit != "probability_vector"):
            raise ValueError("EST-INT must retain unordered separate outcomes")
        if self.estimand_id == "EST-MRT" and self.outcome != "proximal_support_reward":
            raise ValueError("MRT targets causal excursion, not distal treatment efficacy")
        actions = {self.intervention, self.comparator}
        if self.estimand_id == "EST-N1" and (actions != {"MED_A", "MED_B"} or self.outcome != "daily_sleep_quality"):
            raise ValueError("N-of-1 compares reversible fictional medication assignment on its daily endpoint")
        if self.estimand_id in ("EST-ESC-STAGE", "EST-ESC-STRATEGY") and (actions != {"behavioral_continue", "behavioral_escalate"} or self.outcome != "ISI"):
            raise ValueError("escalation preserves ongoing behavioral skills and its distal outcome")
        if self.estimand_id in ("EST-MRT", "EST-POLICY") and actions != {"support_prompt", "no_prompt"}:
            raise ValueError("support estimands cannot compare medication/treatment plans")
        if self.estimand_id == "EST-POLICY" and self.outcome != "policy_value":
            raise ValueError("policy value is separate from the MRT causal-excursion estimand")
        strategies = (self.intervention_strategy, self.comparator_strategy)
        if self.estimand_id == "EST-ESC-STRATEGY":
            if any(v is None for v in strategies) or strategies[0] == strategies[1]:
                raise ValueError("embedded strategy comparison requires distinct fully specified regime versions")
        elif any(v is not None for v in strategies):
            raise ValueError("stage/other effects cannot silently become embedded strategy values")
        policies = (self.intervention_policy, self.comparator_policy)
        if self.estimand_id == "EST-POLICY":
            if self.policy_value_target is None or any(v is None for v in policies) or policies[0] == policies[1]:
                raise ValueError("policy value requires distinct target-policy versions and contextual/cohort target")
        elif self.policy_value_target is not None or any(v is not None for v in policies):
            raise ValueError("policy value target is separate from the history-generating support policy")
        if self.estimand_id == "EST-VISIT" and self.outcome != "ISI":
            raise ValueError("uninterrupted reference visit targets ISI")
        if self.estimand_id in ("EST-VISIT", "EST-INT") and actions & {"support_prompt", "no_prompt"}:
            raise ValueError("visit plans and support actions are distinct")
        if self.outcome == "ISI" and (self.unit != "ISI_points" or self.direction != "lower_is_better"):
            raise ValueError("ISI units/direction mismatch")
        return self


class MethodContext(StrictModel):
    estimand: VersionRef
    dgp: VersionRef
    scenario: VersionRef
    input_data: VersionRef
    prior: VersionRef
    model: VersionRef
    protocol: VersionRef
    observation_cutoff: AwareDatetime
    seed: SeedKey
    allowed_information: Literal["available_observed_history_only"]
    truth_access: Literal["denied"]
    comparator_estimand: VersionRef
    comparator_information: Literal["same_permitted_history"]
    source_ids: Annotated[list[Identifier], Field(min_length=1)]
    failure_policy: Literal["retain_all_attempts_fail_or_abstain_never_fabricate"]


class FitRequest(Versioned):
    kind: Literal["fit_request"]
    context: MethodContext
    backend: Literal["pymc"]
    sampler: Literal["native_nuts"]
    precision: Literal["float64"]
    configuration: VersionRef


class NamedThreshold(Versioned):
    kind: Literal["threshold"]
    id: Identifier
    parameter_version: Name
    value: float
    unit: Literal["ISI_points", "quality_points", "probability", "dimensionless"]
    provenance: Literal["provisional_synthetic_engineering"]
    clinical_review: Literal["deferred"]
    rationale: Name


class ConditionalSymptom(StrictModel):
    numerator_count: Annotated[int, Field(ge=0)]
    denominator_count: Annotated[int, Field(ge=0)]
    conditioning_probability: Probability
    isi: Estimate

    @model_validator(mode="after")
    def denominator(self):
        if self.numerator_count > self.denominator_count:
            raise ValueError("conditioning count exceeds total")
        zero = self.numerator_count == 0 or self.conditioning_probability == 0
        if zero and self.isi.status != "undefined":
            raise ValueError("zero conditional denominator/probability requires undefined ISI")
        if self.isi.status == "estimated" and (self.isi.unit != "ISI_points" or not 0 <= self.isi.value <= 28):
            raise ValueError("conditional ISI unit/range")
        if self.denominator_count == 0 and self.conditioning_probability != 0:
            raise ValueError("empty Monte Carlo denominator cannot imply positive probability")
        if self.denominator_count and abs(self.conditioning_probability - self.numerator_count / self.denominator_count) > 1e-12:
            raise ValueError("conditional probability must retain its Monte Carlo denominator")
        return self


class InterventionOutcomes(StrictModel):
    action: Action
    survival_day42: Probability
    admission_by_day42: Probability
    alive_outpatient_day42: Probability
    conditional_isi: ConditionalSymptom
    death_times_days: list[Nonnegative]
    admission_times_days: list[Nonnegative]

    @model_validator(mode="after")
    def separate_outcomes(self):
        if self.alive_outpatient_day42 > self.survival_day42:
            raise ValueError("alive-outpatient probability exceeds survival")
        if self.conditional_isi.conditioning_probability != self.alive_outpatient_day42:
            raise ValueError("conditional ISI must use its own intervention's alive-outpatient probability")
        return self


class InterruptionResult(Versioned):
    kind: Literal["interruption_result"]
    estimand_id: Literal["EST-INT"]
    estimand_version: Literal["1.0.0"]
    horizon_days: Literal[42]
    intervention: InterventionOutcomes
    comparator: InterventionOutcomes
    interpretation: Literal["intervention_specific_conditional_populations_not_common_survivors"]
    overall_ranking: Literal["suppressed"]

    @model_validator(mode="after")
    def distinct_interventions(self):
        if self.intervention.action == self.comparator.action:
            raise ValueError("interruption comparison requires distinct interventions")
        return self
