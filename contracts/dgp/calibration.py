"""Required derived calibration bindings; absent/inconclusive is not a default."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from contracts.domain.common import Nonnegative, StrictModel, VersionRef


class CalibrationBinding(StrictModel):
    schema_version: Literal["1.0.0"]
    synthetic: Literal[True]
    purpose: Literal["report_rate", "event_rate", "external_contrast"]
    status: Literal["solved", "infeasible", "inconclusive"]
    dgp: VersionRef
    cell_id: str
    calibration_sample_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    seed_key_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    sample_size: Annotated[int, Field(gt=0)]
    target: float
    achieved: float | None
    achieved_mcse: Nonnegative | None
    coefficient: float | None
    iterations: Annotated[int, Field(ge=0, le=100)]
    source_se: Nonnegative | None
    source_se_mcse: Nonnegative | None
    source_pilot: VersionRef | None
    smallest_estimator_se: Nonnegative | None
    frozen_before: Literal["development_and_confirmation"]

    @model_validator(mode="after")
    def precision_and_provenance(self):
        if self.purpose in ("report_rate", "event_rate") and not 0 <= self.target <= 1:
            raise ValueError("rate target outside [0,1]")
        if self.purpose == "external_contrast":
            if self.source_pilot is None or self.source_se is None or self.source_se <= 0 or self.source_se_mcse is None:
                raise ValueError("external calibration requires independently frozen source-SE pilot and uncertainty")
            if self.smallest_estimator_se is None or self.smallest_estimator_se <= 0:
                raise ValueError("external numerical truth requires positive independently piloted estimator SE")
        elif any(v is not None for v in (self.source_se, self.source_se_mcse, self.source_pilot)):
            raise ValueError("rate calibration cannot borrow unrelated external-SE metadata")
        elif self.smallest_estimator_se is not None:
            raise ValueError("rate calibration does not use an estimator-effect SE")
        if self.status == "solved":
            if any(v is None for v in (self.achieved, self.achieved_mcse, self.coefficient)) or self.iterations == 0:
                raise ValueError("solved calibration requires actual achieved target, MCSE, coefficient and iterations")
            tolerance = 0.005 if self.purpose == "external_contrast" else 0.0001
            if abs(self.achieved - self.target) > tolerance:
                raise ValueError("numerical calibration tolerance not achieved")
            if self.purpose in ("report_rate", "event_rate") and not 0 <= self.achieved <= 1:
                raise ValueError("achieved rate outside [0,1]")
            if self.purpose == "external_contrast" and self.achieved_mcse > min(0.05, 0.1 * self.smallest_estimator_se):
                raise ValueError("external contrast truth precision not achieved")
        elif self.coefficient is not None:
            raise ValueError("unresolved calibration must not expose an executable coefficient")
        return self


def require_solved(binding: CalibrationBinding, *, cell_id: str, dgp: VersionRef) -> float:
    if binding.status != "solved" or binding.cell_id != cell_id or binding.dgp != dgp or binding.coefficient is None:
        raise ValueError("calibration missing, unresolved or bound to another cell/version")
    return binding.coefficient
