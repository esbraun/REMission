"""Bounded interactive controller interface; no scientific or execution authority."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field
from .analysis import reference
from .common import Identifier, StrictModel, VersionRef

CONFIGURATION = dict(schema='s2-controller-source-1.0.0',
    order=['current_authority', 'mask', 'saved_scalar_or_fallback', 'bounds_normalize_feasibility',
           'persist_final_distribution', 'keyed_assignment', 'delivery_outcome_clock'],
    actions=['support_prompt', 'no_prompt'], bounds=[.1, .9], fallback=.5,
    max_prompts_rolling_seven=3, no_consecutive=True,
    rng=dict(namespace='assignment', process='s2-support-assignment-v1',
             algorithm='sha256 first53 bits midpoint; independent from generator outcomes'),
    reentry='new explicit envelope after N stop/completion; never automatic',
    saved='exact current scalar only; no fit/predict launch/wait on appointment paths')
CONFIG_REF = reference('poc-support-s2-controller-source-v1', CONFIGURATION)


class ControllerCommand(StrictModel):
    schema_version: Literal['s2-controller-source-1.0.0']
    mode: Literal['current']
    action: Literal['consent', 'withdraw', 'approve', 'pause']
    decision_id: Identifier
    expected_version: Annotated[int, Field(gt=0)]
    expected_state_version: Annotated[int, Field(gt=0)]
    expected_consent_version: Annotated[int, Field(gt=0)]
    expected_eligibility_version: Annotated[int, Field(gt=0)]
    rationale: Annotated[str, Field(min_length=1, max_length=1000)]
    consent_expires_at: AwareDatetime | None = None


class SavedScalar(StrictModel):
    """Service-owned scalar view, never accepted from an HTTP command."""
    summary_available: bool
    serving_authority: bool
    status: str | None = None
    reason: str | None = None
    probability: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    context_reference: VersionRef | None = None
    fit_collection_reference: VersionRef | None = None


class ExecutionBasis(StrictModel):
    schema_version: Literal['s2-controller-execution-v1']
    configuration: VersionRef
    envelope_id: Identifier
    decision_id: Identifier
    patient_versions: dict[str, int]
    context_sha256: str
    fallback_reason: str | None
    saved: SavedScalar
    probabilities: dict[Literal['support_prompt', 'no_prompt'], float]
