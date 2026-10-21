"""LIB-03 strict manifests and three intentionally narrow offline formats."""
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Annotated, Callable, Literal, TypeVar

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator

from contracts.domain.boundaries import ContractViolation, validate_fit_request
from contracts.domain.common import (Identifier, Name, PositiveInt, Probability,
                                     SeedKey, Sha256, StrictModel, Versioned, VersionRef)
from contracts.domain.estimands import FitRequest


class FileRef(StrictModel):
    path: Name
    sha256: Sha256


class Runtime(StrictModel):
    image: Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
    platform: Literal["linux-x86_64"]
    runtime: Name
    packages: Annotated[dict[Identifier, Name], Field(min_length=1)]
    precision: Literal["float64"]
    device: Literal["cpu"]


class MixtureShape(StrictModel):
    kind: Literal["normal_mixture"]
    components: PositiveInt
    marginal_scale: Literal["ISI_points"]


class DrawShape(StrictModel):
    kind: Literal["mcmc_draws"]
    chains: Annotated[list[int], Field(min_length=1)]
    draws: PositiveInt
    quantities: Annotated[list[Identifier], Field(min_length=1)]

    @model_validator(mode="after")
    def coordinates(self):
        if len(set(self.chains)) != len(self.chains) or len(set(self.quantities)) != len(self.quantities):
            raise ValueError("chain/quantity coordinates must be unique")
        return self


class WCLSShape(StrictModel):
    kind: Literal["wcls_fixture"]
    rows: PositiveInt
    analysis: FileRef
    independent_unit: Literal["patient"]


class WCLSResultShape(StrictModel):
    kind: Literal["wcls_result"]
    input: FileRef
    analysis: FileRef


class WCLSResult(Versioned):
    kind: Literal["wcls_reference_result"]
    unit: Literal["quality_points"]
    input_sha256: Sha256
    analysis_sha256: Sha256
    coefficient_names: Literal["intercept,x,action_minus_numerator_probability"]
    coefficients: Annotated[list[float], Field(min_length=3, max_length=3)]
    variance: Literal["MRTAnalysis_hat_matrix_small_sample_not_Python_SE_parity"]
    n_rows: PositiveInt
    independent_unit: Literal["patient"]


Shape = Annotated[MixtureShape | DrawShape | WCLSShape | WCLSResultShape, Field(discriminator="kind")]
PATIENT_ID = TypeAdapter(Identifier)


class ArtifactManifest(Versioned):
    kind: Literal["offline_artifact"]
    artifact_id: Identifier
    payload: FileRef
    inputs: Annotated[list[FileRef], Field(min_length=1)]
    sources: Annotated[list[VersionRef], Field(min_length=1)]
    unit: Literal["ISI_points", "quality_points"]
    model: VersionRef
    prior: VersionRef
    transform: VersionRef
    seed: SeedKey
    observation_cutoff: AwareDatetime
    producer: Runtime
    producer_status: Literal["completed", "failed", "abstained"]
    failure_reason: Name | None
    shape: Shape

    @model_validator(mode="after")
    def consistency(self):
        if self.producer_status != "completed" and self.failure_reason is None:
            raise ValueError("failed/abstained production requires reason")
        if self.producer_status == "completed" and self.failure_reason is not None:
            raise ValueError("completed production cannot hide a failure")
        if self.shape.kind == "normal_mixture" and self.unit != self.shape.marginal_scale:
            raise ValueError("mixture named marginal scale must match manifest units")
        if self.shape.kind in ("wcls_fixture", "wcls_result") and self.unit != "quality_points":
            raise ValueError("reference WCLS reward uses quality points")
        return self


class NormalComponent(StrictModel):
    weight: Probability
    mean: float
    sd: Annotated[float, Field(gt=0)]
    role: Literal["informative", "weak"]


class NormalMixture(Versioned):
    kind: Literal["normal_mixture"]
    marginal_scale: Literal["ISI_points"]
    informative_weight: Probability
    weak_sd: Annotated[float, Field(gt=0)]
    components: Annotated[list[NormalComponent], Field(min_length=1)]

    @model_validator(mode="after")
    def weights(self):
        total = math.fsum(c.weight for c in self.components)
        informative = math.fsum(c.weight for c in self.components if c.role == "informative")
        if not math.isclose(total, 1.0, abs_tol=1e-12, rel_tol=0) or not math.isclose(informative, self.informative_weight, abs_tol=1e-12, rel_tol=0):
            raise ValueError("normalized weights and explicit informative fraction required")
        if any(c.role == "weak" and c.sd != self.weak_sd for c in self.components):
            raise ValueError("weak component scale must be explicit")
        return self


def digest(path: Path) -> str:
    """Hash exact file bytes, including newlines; never normalize artifact content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_file(root: Path, reference: FileRef) -> Path:
    base = root.resolve()
    path = (base / reference.path).resolve()
    if Path(reference.path).is_absolute() or not path.is_relative_to(base) or path == base:
        raise ContractViolation("artifact_path", "Artifact files must remain inside the declared artifact directory")
    if not path.is_file() or digest(path) != reference.sha256:
        raise ContractViolation("artifact_checksum", "Missing or modified offline file")
    return path


def _validate_artifact(root: Path, manifest: ArtifactManifest) -> NormalMixture | WCLSResult | list[dict[str, str]]:
    if manifest.producer_status != "completed":
        raise ContractViolation("artifact_failed", "Failed/abstained production is not a usable prior or reference")
    for source in manifest.inputs:
        checked_file(root, source)
    path = checked_file(root, manifest.payload)
    shape = manifest.shape
    if shape.kind == "normal_mixture":
        mixture = NormalMixture.model_validate_json(path.read_bytes())
        if len(mixture.components) != shape.components or mixture.marginal_scale != manifest.unit:
            raise ContractViolation("artifact_shape", "Mixture component count/scale mismatch")
        return mixture
    if shape.kind == "wcls_result":
        input_path = checked_file(root, shape.input)
        analysis_path = checked_file(root, shape.analysis)
        result = WCLSResult.model_validate_json(path.read_bytes())
        if result.input_sha256 != digest(input_path) or result.analysis_sha256 != digest(analysis_path):
            raise ContractViolation("artifact_lineage", "WCLS result must retain exact input and analysis checksums")
        return result
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        rows = list(reader)
    if any(set(row) != set(columns or []) or any(value is None for value in row.values()) for row in rows):
        raise ContractViolation("artifact_shape", "CSV rows must have exactly the declared fields; extra/missing values are rejected")
    if shape.kind == "mcmc_draws":
        if columns != ["chain", "draw", "quantity", "value"]:
            raise ContractViolation("artifact_shape", "SBC exchange must preserve named chain/draw/quantity/value columns")
        seen = set()
        for row in rows:
            key = (int(row["chain"]), int(row["draw"]), row["quantity"])
            if key in seen or key[0] not in shape.chains or not 0 <= key[1] < shape.draws or key[2] not in shape.quantities or not math.isfinite(float(row["value"])):
                raise ContractViolation("artifact_shape", "Duplicate, nonfinite or out-of-range draw coordinate")
            seen.add(key)
        if len(seen) != len(shape.chains) * shape.draws * len(shape.quantities):
            raise ContractViolation("artifact_shape", "Missing chain/draw/quantity coordinates")
    else:
        analysis = json.loads(checked_file(root, shape.analysis).read_text(encoding="utf-8"))
        if analysis != {"schema_version": "1.0.0", "unit": "quality_points", "centering": 0.5, "independent_unit": "patient", "r_se": "hat_matrix_small_sample", "python_se": "cluster_correction_not_identical"}:
            raise ContractViolation("artifact_analysis", "Unsupported WCLS analysis/variance contract")
        if columns != ["id", "time", "y", "action", "logging_probability", "numerator_probability", "availability", "x"] or len(rows) != shape.rows:
            raise ContractViolation("artifact_shape", "WCLS column/row mismatch")
        seen = set()
        for row in rows:
            PATIENT_ID.validate_python(row["id"])
            key = (row["id"], int(row["time"]))
            if key in seen or int(row["action"]) not in (0, 1) or int(row["availability"]) not in (0, 1) or not 0 < float(row["logging_probability"]) < 1 or float(row["numerator_probability"]) != 0.5 or not all(math.isfinite(float(row[f])) for f in ["y", "x"]):
                raise ContractViolation("artifact_shape", "Invalid WCLS row/probability or duplicated decision")
            seen.add(key)
    return rows


def validate_artifact(root: Path, manifest: ArtifactManifest) -> NormalMixture | WCLSResult | list[dict[str, str]]:
    try:
        return _validate_artifact(root, manifest)
    except ContractViolation:
        raise
    except (ValueError, TypeError, KeyError, csv.Error) as error:
        raise ContractViolation("artifact_encoding", "Malformed or incompatible artifact payload") from error


Result = TypeVar("Result")


def dispatch_checked(request: FitRequest, accepted_versions: list[VersionRef],
                     artifacts: list[tuple[Path, ArtifactManifest]], worker: Callable[[FitRequest], Result]) -> Result:
    """All validation finishes before invoking the separate expensive worker."""
    validate_fit_request(request, accepted_versions)
    allowed = {(v.id, v.version, v.sha256) for v in accepted_versions}
    for root, manifest in artifacts:
        if any((v.id, v.version, v.sha256) not in allowed for v in
               [manifest.model, manifest.prior, manifest.transform, *manifest.sources]):
            raise ContractViolation("unsupported_artifact_version", "Artifact version/hash must be independently accepted")
        if (manifest.model != request.context.model or manifest.prior != request.context.prior
                or manifest.observation_cutoff > request.context.observation_cutoff):
            raise ContractViolation("artifact_context", "Artifact model/prior/cutoff is incompatible with fit request")
        validate_artifact(root, manifest)
    return worker(request)
