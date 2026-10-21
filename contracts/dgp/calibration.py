"""Required derived calibration bindings; absent/inconclusive is not a default."""
from hashlib import sha256
import json
from typing import Annotated, Literal
from pydantic import Field, model_validator
from contracts.domain.common import Nonnegative, StrictModel, VersionRef
from .parameters import VERSION, reference_parameters
from .scenarios import resolve_cell, scenario_manifest


class ExternalTargetEvidence(StrictModel):
    """Independently frozen inputs, verified against their artifacts by G1.

    The consumer supplies these trusted artifacts, never the binding's own
    copies. Targets are derived here from the registered scenario operation.
    """
    source_reference: VersionRef
    source_pilot: VersionRef
    reference_contrast: float
    source_se: Annotated[float, Field(gt=0)]
    source_se_mcse: Nonnegative
    smallest_estimator_se: Annotated[float, Field(gt=0)]


def calibration_request(*, cell_id: str, dgp: VersionRef,
                        external: ExternalTargetEvidence | None = None) -> dict:
    """Derive purpose/target from the authoritative catalog; no free target API."""
    if dgp.version != VERSION:
        raise ValueError("calibration request requires current DGP version")
    resolved = resolve_cell(reference_parameters(), scenario_manifest(), cell_id)
    values = {k: row["value"] for k, row in resolved["parameters"].items()}
    expected = {"cell_id": cell_id, "dgp": dgp.model_dump(mode="json"),
                "source_reference": None, "source_pilot": None,
                "source_se": None, "source_se_mcse": None, "smallest_estimator_se": None}
    if values["report_mode"] in (2, 3, 4):
        if external is not None:
            raise ValueError("report request cannot use external target evidence")
        expected.update(purpose="report_rate", target=1 - values["missing_fraction"])
    elif values["external_shift_SE"] or values["external_reverse_sign"]:
        if external is None:
            raise ValueError("external target requires independently frozen reference and pilot evidence")
        target = (-external.reference_contrast if values["external_reverse_sign"] else
                  external.reference_contrast + values["external_shift_SE"] * external.source_se)
        expected.update(purpose="external_contrast", target=target,
                        **{k: v for k, v in external.model_dump(mode="json").items() if k != "reference_contrast"})
    else:
        raise ValueError("cell has no registered derived calibration; exact MCAR/event defaults are not solved coefficients")
    # Includes the operation, resolved cell, upstream identities and numeric pilot
    # inputs. Changing even an upstream artifact with equal numbers invalidates it.
    specification = {"dgp_version": VERSION, "cell": resolved["cell"], "expected": expected,
                     "external": external.model_dump(mode="json") if external else None}
    digest = sha256(json.dumps(specification, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    expected["target_spec"] = {"id": "dgp-calibration-target", "version": VERSION, "sha256": digest}
    return expected


class CalibrationBinding(StrictModel):
    schema_version: Literal["1.1.0"]
    synthetic: Literal[True]
    purpose: Literal["report_rate", "event_rate", "external_contrast"]
    status: Literal["solved", "infeasible", "inconclusive"]
    dgp: VersionRef
    cell_id: str
    target_spec: VersionRef
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
    source_reference: VersionRef | None
    smallest_estimator_se: Nonnegative | None
    frozen_before: Literal["development_and_confirmation"]

    @model_validator(mode="after")
    def precision_and_provenance(self):
        if self.purpose in ("report_rate", "event_rate") and not 0 <= self.target <= 1:
            raise ValueError("rate target outside [0,1]")
        if self.purpose == "external_contrast":
            if self.source_reference is None or self.source_pilot is None or self.source_se is None or self.source_se <= 0 or self.source_se_mcse is None:
                raise ValueError("external calibration requires independently frozen source-SE pilot and uncertainty")
            if self.smallest_estimator_se is None or self.smallest_estimator_se <= 0:
                raise ValueError("external numerical truth requires positive independently piloted estimator SE")
        elif any(v is not None for v in (self.source_se, self.source_se_mcse, self.source_pilot, self.source_reference)):
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


def require_solved(binding: CalibrationBinding, *, cell_id: str, dgp: VersionRef,
                   external: ExternalTargetEvidence | None = None) -> float:
    expected = calibration_request(cell_id=cell_id, dgp=dgp, external=external)
    actual = binding.model_dump(mode="json")
    if (binding.status != "solved" or binding.coefficient is None or
            any(actual[key] != value for key, value in expected.items())):
        raise ValueError("calibration unresolved or mismatched cell/DGP/purpose/target specification or upstream evidence")
    return binding.coefficient
