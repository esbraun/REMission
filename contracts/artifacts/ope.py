"""DR-EXCEPTION-R1 v1: fixed-policy current-action qualification contracts."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from contracts.domain.common import Identifier, Sha256, StrictModel, Versioned, VersionRef
from .manifest import FileRef

Pair = Annotated[list[float], Field(min_length=2, max_length=2)]
Action = Annotated[int, Field(strict=True, ge=0, le=1)]
Quality = Annotated[float, Field(ge=0, le=10)]


class Feature(StrictModel):
    row_id: Identifier
    patient_id: Identifier
    window_id: Identifier
    decision_at: AwareDatetime
    x: float
    x_available_at: AwareDatetime

    @model_validator(mode="after")
    def predecision(self):
        if self.x_available_at >= self.decision_at:
            raise ValueError("feature must be strictly available before assignment")
        return self


class TrainingRow(Feature):
    action: Action
    reward: Quality
    reward_available_at: AwareDatetime


class TrainingPlan(Versioned):
    version: Literal["DR-EXCEPTION-R1/1.0.0"]
    cutoff: AwareDatetime
    evaluation_start: AwareDatetime
    evaluation_patients: list[Identifier]
    basis: Literal["x,action,x_times_action;StandardScaler;Ridge_intercept"]
    alpha: Literal[1.0]
    solver: Literal["svd"]
    seed: int
    protocol_sha256: Sha256

    @model_validator(mode="after")
    def earlier(self):
        if self.cutoff >= self.evaluation_start or len(set(self.evaluation_patients)) != len(self.evaluation_patients):
            raise ValueError("seal earlier cutoff and unique evaluation patients")
        return self


class TrainingStamp(StrictModel):
    row_id: Identifier
    patient_id: Identifier
    action: Action
    decision_at: AwareDatetime
    x_available_at: AwareDatetime
    reward_available_at: AwareDatetime


class TrainingReceipt(Versioned):
    version: Literal["DR-EXCEPTION-R1/1.0.0"]
    plan: TrainingPlan
    plan_sha256: Sha256
    training_sha256: Sha256
    model_sha256: Sha256
    trainer_sha256: Sha256
    fit_at: AwareDatetime
    rows: list[TrainingStamp]

    @model_validator(mode="after")
    def held_out(self):
        if (self.fit_at > self.plan.cutoff or len({r.row_id for r in self.rows}) != len(self.rows)
                or len({(r.patient_id,r.decision_at.date()) for r in self.rows}) != len(self.rows)):
            raise ValueError("fit must precede seal; unique training rows")
        if any(r.patient_id in self.plan.evaluation_patients or r.x_available_at >= r.decision_at
               or r.decision_at >= r.reward_available_at or r.reward_available_at >= self.plan.cutoff for r in self.rows):
            raise ValueError("patient-held-out and forward-time training provenance required")
        if any(len({r.patient_id for r in self.rows if r.action == a}) < 10 for a in [0, 1]):
            raise ValueError("warm-up needs at least ten distinct training patients per action")
        return self


class Decision(Feature):
    available_actions: list[Action]
    logging_probabilities: Pair
    action: Action | None


class Reward(StrictModel):
    row_id: Identifier
    status: Literal["observed", "missing", "pending", "undefined"]
    value: Quality | None

    @model_validator(mode="after")
    def no_imputation(self):
        if (self.status == "observed") != (self.value is not None):
            raise ValueError("reward status/value must agree; missing is not zero")
        return self


class Policy(Versioned):
    policy_id: Identifier
    version: Literal["1.0.0"]
    sealed_at: AwareDatetime
    action_order: Literal["0=no_prompt,1=approved_prompt"]
    definition_sha256: Sha256
    availability_rule: Literal["singleton_deterministic_empty_unavailable"]


class TargetRow(StrictModel):
    row_id: Identifier
    probabilities: Pair


class Targets(Versioned):
    policy: Policy
    roster_sha256: Sha256
    rows: list[TargetRow]


class QRow(StrictModel):
    row_id: Identifier
    values: Pair


class Predictions(Versioned):
    version: Literal["DR-EXCEPTION-R1/1.0.0"]
    action_order: Literal["0=no_prompt,1=approved_prompt"]
    roster_sha256: Sha256
    receipt_sha256: Sha256
    model_sha256: Sha256
    predictor_sha256: Sha256
    predicted_at: AwareDatetime
    rows: list[QRow]


class Bindings(StrictModel):
    receipt_sha256: Sha256
    training_sha256: Sha256
    plan_sha256: Sha256
    model_sha256: Sha256
    trainer_sha256: Sha256
    predictor_sha256: Sha256
    q_sha256: Sha256
    target_sha256: list[Sha256]
    policy_sha256: list[Sha256]


class EvaluationProtocol(Versioned):
    protocol_id: Identifier
    version: Literal["1.0.0"]
    population_id: Identifier
    behavior: VersionRef
    reward_horizon: Literal["next_morning_quality"]
    outcome_window_rule: Literal["one_decision_per_patient_next_morning"]
    unit: Literal["quality_points"]
    target_policy_ids: list[Identifier]
    sealed_at: AwareDatetime


class OPERequest(Versioned):
    version: Literal["DR-EXCEPTION-R1/1.0.0"]
    estimand: Literal["current_action_value_over_behavior_history_eligible_windows"]
    unit: Literal["quality_points"]
    aggregation: Literal["pooled_eligible_decision_mean"]
    logging_regime: Literal["fixed_independent_patients", "pooled_adaptive"]
    protocol: FileRef
    roster: FileRef
    rewards: FileRef
    predictions: FileRef
    targets: Annotated[list[FileRef], Field(min_length=1)]
    receipt: FileRef | None
    bindings: Bindings
    inference: bool
    bootstrap_seed: Annotated[int, Field(ge=0)]
    bootstrap_replicates: Literal[2000]
    minimum_patients: Literal[30]


class OPEOutput(Versioned):
    version: Literal["DR-EXCEPTION-R1/1.0.0"]
    status: Literal["computed_conditional", "diagnostic_only", "abstained", "undefined"]
    reason: str | None
    unit: Literal["quality_points"]
    eligible_windows: int
    unavailable_windows: int
    independent_patients: int
    policies: list[Identifier]
    dr: list[float]
    ips: list[float]
    intervals: list[list[float]]
    paired_intervals: list[list[float]]
    bootstrap_values: list[list[float]]
    patient_order: list[Identifier]
    patient_counts: list[int]
    patient_score_sums: list[list[float]]
    bootstrap_indices_sha256: Sha256 | None
    metadata: dict[str, str | int | bool]
