"""Bounded interactive controller interface; no scientific or execution authority."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, ConfigDict, model_validator
from .analysis import reference, sha
from .common import Identifier, Sha256, StrictModel, VersionRef
from .observed_v2 import ExactRef
from contracts.runs.coverage_v2 import StageLedgerV2

CONFIGURATION = dict(schema='s2-controller-source-1.0.0',
    order=['current_authority', 'mask', 'saved_scalar_or_fallback', 'bounds_normalize_feasibility',
           'persist_final_distribution', 'keyed_assignment', 'delivery_outcome_clock'],
    actions=['support_prompt', 'no_prompt'], bounds=[.1, .9], fallback=.5,
    max_prompts_rolling_seven=3, no_consecutive=True,
    rng=dict(namespace='assignment', process='s2-support-assignment-v1',
             algorithm='sha256 first53 bits midpoint; independent from generator outcomes'),
    reentry='new explicit envelope after N stop/completion; never automatic',
    saved='exact current scalar only; no fit/predict launch/wait on appointment paths')
CONFIGURATION['qualification']=dict(contexts=['installed_ACTUAL','untrusted_once_SOURCE_OP'],
    candidate='external nonHTTP invocation only; never LIVE history/export/fit/serving',
    clocks='synthetic stage clocks distinct from actual receipt/publication')
CONFIG_REF = reference('poc-support-s2-controller-source-v1', CONFIGURATION)
REQUIRED_APP_SOURCES={'services/foundation/'+name+'.py' for name in
    ('app','store','protocol','workflow','simulation','support_s2_controller','support_s2_authority','support_s2_invocation','support_s2_prediction')}
REQUIRED_APP_SOURCES.add('contracts/domain/support_s2_controller.py')
REQUIRED_GENERATOR_SOURCES={'services/generator/'+name+'.py' for name in ('server','restricted','restricted_v2')}


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


class QualificationPacket(StrictModel):
    """Frozen BEFORE qualification execution/actual acceptance; no self reference."""
    schema_version: Literal['poc-support-interactive-packet-v1']
    app_commit: Annotated[str, Field(pattern=r'^[a-f0-9]{40}$')]
    app_source_closure: dict[str, Sha256]
    generator_source_closure: dict[str, Sha256]
    app_image: Annotated[str, Field(pattern=r'^sha256:[a-f0-9]{64}$')]
    generator_image: Annotated[str, Field(pattern=r'^sha256:[a-f0-9]{64}$')]
    runtime: VersionRef
    configuration: VersionRef
    invocation_class: Literal['owned-interactive-support-v1']
    store_id: Identifier
    authority_generation: Annotated[int, Field(ge=1)]
    installed_bundle_sha256: Sha256

    @model_validator(mode='after')
    def complete(self):
        if (self.configuration.model_dump()!=CONFIG_REF or not REQUIRED_APP_SOURCES<=self.app_source_closure.keys()
                or not REQUIRED_GENERATOR_SOURCES<=self.generator_source_closure.keys()):
            raise ValueError('complete_exact_interactive_packet_required')
        return self


class UntrustedInteractiveInvocation(StrictModel):
    """Untrusted candidate scope. External SOURCE/OP authority is supplied separately."""
    model_config = ConfigDict(frozen=True)
    schema_version: Literal['poc-support-untrusted-invocation-v1']
    invocation_id: Identifier
    packet: QualificationPacket
    packet_sha256: Sha256
    source_acceptance: VersionRef
    operation_go: VersionRef
    owner_id: Identifier
    cases: dict[Identifier, Identifier]  # patient -> exact generation
    operations_sha256: Sha256
    not_before: AwareDatetime
    expires_at: AwareDatetime
    receipt_path: Annotated[str, Field(min_length=1,max_length=1024)]
    output_cap: Annotated[int,Field(ge=1,le=524288)]

    @model_validator(mode='after')
    def exact_scope(self):
        if self.packet_sha256!=sha(self.packet.model_dump(mode='json')) or not self.cases or self.not_before>=self.expires_at:
            raise ValueError('exact_finite_candidate_invocation_required')
        return self

    @property
    def authority_body(self):
        # The external GO hashes this upstream scope, never its own reference.
        return dict(scope='UNTRUSTED_interactive_candidate_once',**self.model_dump(mode='json',exclude={'operation_go'}))

    @property
    def reference(self):
        return reference('candidate-s2-invocation-v1',self.model_dump(mode='json'))


class InteractiveSupportQualification(StrictModel):
    """Trusted installation input ONLY, after DIFFERENT ACTUAL evidence acceptance.

    SOURCE/OP review, a worker/product object or a Settings label cannot install
    this binding. The future operator installation supplies the accepted value.
    """
    model_config = ConfigDict(frozen=True)
    schema_version: Literal['poc-support-interactive-qualification-v1']
    packet: QualificationPacket
    packet_sha256: Sha256
    actual_acceptance: VersionRef
    acceptance_scope: Literal['ACTUAL_interactive_producer_accepted']

    @model_validator(mode='after')
    def frozen_packet(self):
        if self.packet_sha256!=sha(self.packet.model_dump(mode='json')):
            raise ValueError('interactive_packet_digest_mismatch')
        return self

    @property
    def reference(self):
        return reference('poc-support-interactive-qualified-installation-v1',self.model_dump(mode='json'))


class AuthorizationBasis(StrictModel):
    schema_version: Literal['s2-controller-authorization-v1']
    configuration: VersionRef
    qualification: VersionRef
    owner_id: Identifier
    patient_id: Identifier
    generation_id: Identifier
    store_id: Identifier
    authority_generation: Annotated[int,Field(ge=1)]
    envelope: ExactRef
    original_approval: ExactRef
    original_command_id: Identifier
    actor_id: Identifier
    assignment_unit: Identifier
    current_snapshot: ExactRef
    versions: dict[str,int]
    known_refs: Annotated[list[ExactRef],Field(max_length=4096)]
    consent_heads: Annotated[list[ExactRef],Field(max_length=32)]
    frozen_state: dict
    at: AwareDatetime
    received_at: AwareDatetime
    allowed_actions: list[Literal['support_prompt','no_prompt']]
    probabilities: dict[Literal['support_prompt','no_prompt'],float]
    saved: SavedScalar
    fallback_reason: str | None


class InteractiveStageCompletion(StrictModel):
    schema_version: Literal['poc-support-interactive-completion-v1']
    qualification: VersionRef
    authorization: VersionRef
    owner_id: Identifier
    patient_id: Identifier
    generation_id: Identifier
    store_id: Identifier
    authority_generation: Annotated[int,Field(ge=1)]
    decision: ExactRef
    assignment: ExactRef | None
    output_ref: VersionRef
    output_bytes: Annotated[int,Field(ge=2,le=524288)]
    output_sha256: Sha256
    output_count: Annotated[int,Field(ge=0,le=4)]
    ledgers: list[StageLedgerV2]
    simulated_completed_at: AwareDatetime
    simulated_available_at: AwareDatetime
    received_at: AwareDatetime
    published_at: AwareDatetime

    @model_validator(mode='after')
    def clocks(self):
        if not self.simulated_completed_at < self.simulated_available_at or self.received_at>self.published_at:
            raise ValueError('separate_interactive_completion_clocks_required')
        return self
