"""LIVE-SAFETY-EXPORT 1.0.0, an independent operational product."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from contracts.domain.common import Identifier, Sha256, StrictModel, VersionRef
from .live_hold import EvidenceRef


class Obligation(StrictModel):
    requirement_id: Identifier
    definition: VersionRef


class Baseline(StrictModel):
    type: Literal['baseline']
    scope: Literal['independent_live_holds']
    active_episodes: list[Identifier]


class Invalidate(StrictModel):
    type: Literal['invalidate']
    action: Literal['open', 'strengthen']
    episode_id: Identifier
    generation: Annotated[int, Field(gt=0)]
    trigger_refs: list[EvidenceRef]
    active_trigger_refs: list[EvidenceRef]
    trigger_set_sha256: Sha256
    reason_codes: list[Identifier]
    obligations: list[Obligation]
    obligation_set_sha256: Sha256


class ReviewRecorded(StrictModel):
    type: Literal['review_recorded']
    episode_id: Identifier
    generation: Annotated[int, Field(gt=0)]
    review_id: Identifier
    review_sha256: Sha256
    current_review_at: AwareDatetime
    trigger_set_sha256: Sha256
    obligation_set_sha256: Sha256
    rule_refs: list[VersionRef]
    result: Literal['pending', 'satisfied']


class Clearance(StrictModel):
    type: Literal['clearance']
    episode_id: Identifier
    generation: Annotated[int, Field(gt=0)]
    review_id: Identifier
    review_sha256: Sha256
    trigger_set_sha256: Sha256
    obligation_set_sha256: Sha256
    rule_refs: list[VersionRef]


class EpisodeObligations(StrictModel):
    episode_id: Identifier
    generation: Annotated[int, Field(gt=0)]
    obligations: list[Obligation]
    obligation_set_sha256: Sha256


class AuthorityChanged(StrictModel):
    type: Literal['authority_changed']
    old_generation: Annotated[int, Field(gt=0)]
    new_generation: Annotated[int, Field(gt=0)]
    old_authority_sha256: Sha256
    new_authority_sha256: Sha256
    old_review_rules_sha256: Sha256
    new_review_rules_sha256: Sha256
    prior_journal_id: Identifier
    active_episodes: list[EpisodeObligations]


class EvidenceDisputed(StrictModel):
    type: Literal['evidence_disputed']
    episode_id: Identifier
    generation: Annotated[int, Field(gt=0)]
    reason: Literal['corrected','retracted','superseded','unresolved','current_context_changed']
    affected_refs: list[EvidenceRef]
    changed_context_sha256: Sha256 | None


Operation = Annotated[Baseline | Invalidate | ReviewRecorded | Clearance | AuthorityChanged | EvidenceDisputed, Field(discriminator='type')]


class LiveHoldFact(StrictModel):
    schema_version: Literal['1.0.0']
    kind: Literal['live_hold_fact']
    synthetic: Literal[True]
    patient_id: Identifier
    journal_id: Identifier
    operation_id: Identifier
    patient_sequence: Annotated[int, Field(gt=0)]
    previous_fact_sha256: Sha256 | None
    authority_generation: Annotated[int, Field(gt=0)]
    authority_sha256: Sha256
    review_rules_sha256: Sha256
    event_at: AwareDatetime
    recorded_at: AwareDatetime
    available_at: AwareDatetime
    operation: Operation

    @model_validator(mode='after')
    def chronology(self):
        if self.event_at > self.recorded_at or self.available_at != self.recorded_at:
            raise ValueError('invalid live fact chronology')
        if self.operation.type != 'invalidate' and self.event_at != self.recorded_at:
            raise ValueError('service operation event must equal receipt')
        if (self.patient_sequence == 1) != (self.previous_fact_sha256 is None):
            raise ValueError('invalid predecessor')
        return self


class Artifact(StrictModel):
    path: Literal['observed-projection.json', 'live-hold-facts.json']
    sha256: Sha256
    bytes: Annotated[int, Field(ge=0)]


class ObservedArtifact(Artifact):
    kind: Literal['learner_history']
    schema_version: Literal['1.0.0','2.0.0']


class FactsArtifact(Artifact):
    count: Annotated[int, Field(ge=0)]


class ActiveEpisode(StrictModel):
    episode_id: Identifier
    generation: Annotated[int, Field(gt=0)]
    trigger_set_sha256: Sha256
    obligation_set_sha256: Sha256


class ReceiptRef(StrictModel):
    receipt_id: Identifier
    payload_sha256: Sha256


class LiveSafetyExport(StrictModel):
    schema_version: Literal['1.0.0']
    kind: Literal['live_safety_export']
    synthetic: Literal[True]
    scope: Literal['independent_live_holds']
    export_id: Identifier
    service_contract: VersionRef
    schema_binding: VersionRef
    observed_binding: VersionRef
    service_instance_id: Identifier
    service_producer: VersionRef
    source_commit: Annotated[str, Field(pattern=r'^[a-f0-9]{40}$')]
    runtime: VersionRef
    execution: Literal['synthetic_service','contract_fixture']
    authority_generation: Annotated[int, Field(gt=0)]
    authority_sha256: Sha256
    review_rules_sha256: Sha256
    patient_id: Identifier
    cutoff: AwareDatetime
    captured_at: AwareDatetime
    snapshot_id: Identifier
    snapshot_sha256: Sha256
    observed_source_sha256: Sha256
    observed_projection: ObservedArtifact
    facts: FactsArtifact
    journal_id: Identifier
    baseline_operation_id: Identifier | None
    through_patient_sequence: Annotated[int, Field(ge=0)]
    prefix_chain_sha256: Sha256
    completeness: Literal['complete_visible_prefix','uninitialized']
    independent_hold_status: Literal['held','not_held','unknown']
    active_episodes: list[ActiveEpisode]
    publication_receipt_ref: ReceiptRef

    @model_validator(mode='after')
    def capture(self):
        if self.captured_at < self.cutoff:
            raise ValueError('future export cutoff')
        if self.observed_projection.path != 'observed-projection.json' or self.facts.path != 'live-hold-facts.json':
            raise ValueError('wrong artifact names')
        return self


class AuthorityGeneration(StrictModel):
    generation: Annotated[int, Field(gt=0)]
    authority_sha256: Sha256
    review_rules_sha256: Sha256


class TrustedLiveSafetyAuthority(StrictModel):
    schema_version: Literal['1.0.0']
    kind: Literal['trusted_live_safety_authority']
    synthetic: Literal[True]
    service_instance_id: Identifier
    service_producer: VersionRef
    source_commit: Annotated[str, Field(pattern=r'^[a-f0-9]{40}$')]
    runtime: VersionRef
    export_id: Identifier
    manifest_sha256: Sha256
    patient_id: Identifier
    cutoff: AwareDatetime
    snapshot_id: Identifier
    snapshot_sha256: Sha256
    authority_generation: Annotated[int, Field(gt=0)]
    authority_sha256: Sha256
    review_rules_sha256: Sha256
    generations: list[AuthorityGeneration]
    observed_sha256: Sha256
    prefix_count: Annotated[int, Field(ge=0)]
    through_patient_sequence: Annotated[int, Field(ge=0)]
    prefix_chain_sha256: Sha256
    baseline_operation_id: Identifier | None
    allow_contract_fixture: bool = False
