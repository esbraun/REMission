"""Evaluator-only types. Do not import these into learner request schemas."""
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .common import (Estimate, FitMetadata, Identifier, Name, Nonnegative,
                     PositiveInt, Probability, SeedKey, StrictModel,
                     Versioned, VersionRef)


class ParameterSpec(StrictModel):
    symbol: Identifier
    unit: Name
    value: float | list[float]
    distribution: Name
    provenance: Literal["synthetic_engineering"]
    rationale: Name


class DGPConfig(Versioned):
    kind: Literal["dgp_config"]
    dgp: VersionRef
    layer: Literal["analytic", "reference", "adversarial"]
    scenario: VersionRef
    patients: PositiveInt
    external_study_sizes: list[PositiveInt]
    start_day: int
    end_day: int
    initialized_day: int
    time_grid_unit: Literal["days"]
    temporal_contract: VersionRef
    equations: VersionRef
    parameter_table: Annotated[list[ParameterSpec], Field(min_length=1)]
    initial_distribution: VersionRef
    irregular_visit_process: VersionRef
    observation_rules: VersionRef
    learner_export_schema: VersionRef
    seed_namespaces: Annotated[list[SeedKey], Field(min_length=1)]
    clinical_interpretation: Literal["synthetic_not_clinically_calibrated"]

    @model_validator(mode="after")
    def time_grid(self):
        if not self.initialized_day < self.start_day < self.end_day:
            raise ValueError("initial states must precede generated time grid")
        if len({p.symbol for p in self.parameter_table}) != len(self.parameter_table):
            raise ValueError("duplicate parameter symbol")
        return self


class TruthResult(Versioned):
    kind: Literal["truth_result"]
    estimand: VersionRef
    method: Literal["analytic", "enumerated", "numerical"]
    estimate: Estimate
    numerical_standard_error: Nonnegative
    information_set: Literal["evaluator_only_structural_system"]
    privileged_information: Literal[True]
    dgp: VersionRef
    seed: SeedKey
    draws: Annotated[int, Field(ge=0)]
    independent_implementation: VersionRef

    @model_validator(mode="after")
    def method_precision(self):
        if self.method == "numerical" and self.draws == 0:
            raise ValueError("numerical truth requires actual draws")
        if self.method in ("analytic", "enumerated") and self.numerical_standard_error != 0:
            raise ValueError("analytic/enumerated truth has no numerical sampling SE")
        return self


class SimulatorTruth(Versioned):
    kind: Literal["simulator_truth"]
    access: Literal["evaluator_only"]
    patient_id: Identifier
    day: int
    latent_states: dict[Identifier, float]
    structural_parameters: list[ParameterSpec]
    counterfactuals: list[TruthResult]


class EvaluationCell(StrictModel):
    id: Identifier
    scenario: VersionRef
    estimand: VersionRef
    patients: PositiveInt
    tier: Literal["deterministic", "smoke", "development", "sbc", "recovery", "decision_null", "integrated_policy"]
    repetitions: PositiveInt

    @model_validator(mode="after")
    def mandatory_budget(self):
        minimum = {"deterministic": 1, "smoke": 5, "development": 200, "sbc": 1000, "recovery": 1000, "decision_null": 2000, "integrated_policy": 1000}
        if self.repetitions < minimum[self.tier]:
            raise ValueError("required evaluation repetitions may not be silently reduced")
        return self


class EvaluationProtocol(Versioned):
    kind: Literal["evaluation_protocol"]
    protocol: VersionRef
    locked_at: AwareDatetime
    cells: Annotated[list[EvaluationCell], Field(min_length=1)]
    metrics: Annotated[list[Name], Field(min_length=1)]
    thresholds: Annotated[list[VersionRef], Field(min_length=1)]
    development_namespace: Identifier
    confirmation_namespace: Identifier
    model: VersionRef
    prior: VersionRef
    decision: VersionRef
    failure_handling: Literal["retain_all_attempted_completed_failed_abstained_undefined_pending_counts"]
    checkpoint_commands: Annotated[list[Name], Field(min_length=1)]

    @model_validator(mode="after")
    def independent_confirmation(self):
        if self.development_namespace == self.confirmation_namespace:
            raise ValueError("development and confirmation seeds must be separate")
        if len({c.id for c in self.cells}) != len(self.cells):
            raise ValueError("duplicate evaluation cell")
        return self


class ReplicateResult(Versioned):
    kind: Literal["replicate_result"]
    run_id: Identifier
    replicate_id: Identifier
    input_versions: Annotated[list[VersionRef], Field(min_length=1)]
    seeds: Annotated[list[SeedKey], Field(min_length=1)]
    attempted_fit: bool
    fit: FitMetadata | None
    estimate: Estimate
    truth_ref: VersionRef | None
    assignment_refs: list[Identifier]
    executed_propensities: list[Probability]
    outcome_refs: list[Identifier]
    violations: list[Name]
    execution_seconds: Nonnegative
    peak_memory_bytes: Annotated[int, Field(ge=0)]
    failure_reason: Name | None

    @model_validator(mode="after")
    def retain_failed_attempt(self):
        if self.attempted_fit != (self.fit is not None):
            raise ValueError("attempted fit must retain metadata")
        if self.fit is not None and self.fit.status != "accepted" and self.estimate.status == "estimated":
            raise ValueError("unsuccessful fit cannot supply accepted estimate")
        if len(self.assignment_refs) != len(self.executed_propensities):
            raise ValueError("every assignment retains its executed propensity")
        return self


class GateEvidence(Versioned):
    kind: Literal["gate_evidence"]
    requirement_ids: Annotated[list[Identifier], Field(min_length=1)]
    input_versions: Annotated[list[VersionRef], Field(min_length=1)]
    executed_checks: Annotated[list[Name], Field(min_length=1)]
    commands: Annotated[list[Name], Field(min_length=1)]
    manifests: Annotated[list[VersionRef], Field(min_length=1)]
    attempted: Annotated[int, Field(ge=0)]
    completed: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]
    abstained: Annotated[int, Field(ge=0)]
    undefined: Annotated[int, Field(ge=0)]
    pending: Annotated[int, Field(ge=0)]
    failures: list[Name]
    reviewer_disposition: Literal["pending", "changes_requested", "ready_to_ship"]
    claim_limits: Annotated[list[Name], Field(min_length=1)]

    @model_validator(mode="after")
    def accounting(self):
        if self.attempted != self.completed + self.failed + self.abstained + self.undefined + self.pending:
            raise ValueError("all attempts require one mutually exclusive outcome")
        return self


class EvidenceRecord(Versioned):
    kind: Literal["evidence_record"]
    source_id: Identifier
    bibliography: Name
    year: Annotated[int, Field(ge=1800, le=2200)]
    url: Name
    doi: Name | None
    evidence_type: Literal["real_literature_rationale", "synthetic_quantitative_study", "software_documentation"]
    source_version: Name
    supported_claim: Name
    limitations: Annotated[list[Name], Field(min_length=1)]
    locator: Name
    verified_at: AwareDatetime | None
    verification_status: Literal["unverified", "verified", "unavailable"]
    consuming_requirements: Annotated[list[Identifier], Field(min_length=1)]
    role: Literal["rationale_only", "synthetic_likelihood", "software_api"]

    @model_validator(mode="after")
    def source_separation(self):
        if self.evidence_type == "real_literature_rationale" and self.role != "rationale_only":
            raise ValueError("real references are not synthetic quantitative study inputs")
        if self.verification_status == "verified" and self.verified_at is None:
            raise ValueError("verification requires observed date")
        return self
