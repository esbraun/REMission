"""Shared wire primitives, provenance and explicit numerical result states."""
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Name = Annotated[str, Field(min_length=1, max_length=256)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Probability = Annotated[float, Field(ge=0, le=1)]
Nonnegative = Annotated[float, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
Component = Literal["nof1", "escalation", "mrt_bandit"]
Action = Literal["MED_A", "MED_B", "behavioral_continue", "behavioral_escalate", "support_prompt", "no_prompt", "usual_care"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False,
                              validate_assignment=True, revalidate_instances="always")


class Versioned(StrictModel):
    schema_version: Literal["1.0.0"]
    synthetic: Literal[True]


class VersionRef(StrictModel):
    id: Identifier
    version: Name
    sha256: Sha256


class SeedKey(StrictModel):
    namespace: Literal["fixture", "development", "confirmation", "truth", "fit", "assignment"]
    protocol: Identifier
    scenario: Identifier
    replicate: Annotated[int, Field(ge=0)]
    patient: Identifier
    time_index: int
    process: Identifier


class Source(StrictModel):
    id: Identifier
    version: Name
    adapter: Literal["synthetic_fhir_shaped", "synthetic_oura_like", "patient_report", "synthetic_trial", "simulation", "research_configuration"]
    raw_sha256: Sha256


class Record(Versioned):
    record_id: Identifier
    patient_id: Identifier
    event_at: AwareDatetime
    recorded_at: AwareDatetime
    available_at: AwareDatetime
    source: Source
    lineage_id: Identifier
    revision: PositiveInt
    supersedes: Identifier | None
    duplicate_of: Identifier | None
    record_status: Literal["active", "corrected", "retracted"]

    @model_validator(mode="after")
    def chronology(self):
        if not self.event_at <= self.recorded_at <= self.available_at:
            raise ValueError("event <= recorded <= available is required; source times must be normalized before ingestion")
        if (self.revision == 1) != (self.supersedes is None):
            raise ValueError("a correction must reference the previous revision")
        if self.record_id in (self.supersedes, self.duplicate_of):
            raise ValueError("self-referencing lineage")
        return self


class Interval(StrictModel):
    lower: float
    upper: float
    level: Annotated[float, Field(gt=0, lt=1)]
    interval_type: Literal["credible", "confidence", "prediction", "monte_carlo"]

    @model_validator(mode="after")
    def ordered(self):
        if self.lower > self.upper:
            raise ValueError("reversed interval")
        return self


class Estimated(StrictModel):
    status: Literal["estimated"]
    value: float
    unit: Literal["ISI_points", "quality_points", "function_points", "probability", "minutes", "count"]
    standard_error: Nonnegative | None
    interval: Interval | None

    @model_validator(mode="after")
    def probability_range(self):
        if self.unit == "probability" and not 0 <= self.value <= 1:
            raise ValueError("probability estimate outside [0,1]")
        return self


class Unavailable(StrictModel):
    status: Literal["undefined", "failed", "abstained", "pending", "inconclusive", "prior_only"]
    reason: Name


Estimate = Annotated[Estimated | Unavailable, Field(discriminator="status")]


class FitMetadata(StrictModel):
    backend: Literal["pymc"]
    backend_version: Name
    sampler: Literal["native_nuts"]
    sampler_version: Name
    packages: dict[Identifier, Name]
    precision: Literal["float64"]
    status: Literal["accepted", "failed", "abstained", "pending"]
    diagnostics_artifacts: list[VersionRef]
    failure_reason: Name | None

    @model_validator(mode="after")
    def status_reason(self):
        if self.status in ("failed", "abstained") and self.failure_reason is None:
            raise ValueError("failed/abstained fit requires a reason")
        if self.status == "accepted" and (self.failure_reason or not self.diagnostics_artifacts):
            raise ValueError("accepted fit requires diagnostics and no failure reason")
        return self
