"""LIVE-HOLD-01 command/configuration types, separate from observed records."""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from contracts.domain.common import Identifier, Name, Sha256, StrictModel, VersionRef
from contracts.domain.observed_v2 import ExactRef

CAPABILITY = 'LIVE-HOLD-01/1.0.0'


class Header(StrictModel):
    schema_version: Literal['1.0.0']
    contract: Literal['LIVE-HOLD-01']
    synthetic: Literal[True]


class EvidenceRef(StrictModel):
    store: Literal['archive', 'event', 'live_review']
    namespace_id: Identifier
    partition_id: Identifier | None
    record_id: Identifier
    payload_sha256: Sha256

    @model_validator(mode='after')
    def namespace(self):
        if (self.store == 'archive') != (self.partition_id is not None):
            raise ValueError('only archive refs have a partition')
        return self


class InvalidationInput(Header):
    archive_id: Identifier
    partition_id: Identifier
    bundle_ref: ExactRef
    trigger_refs: Annotated[list[ExactRef], Field(min_length=1)]


class CurrentInput(Header):
    mode: Literal['current']
    decision_id: Identifier
    expected_patient_version: Annotated[int, Field(gt=0)]
    expected_state_version: Annotated[int, Field(gt=0)]
    expected_consent_version: Annotated[int, Field(gt=0)]
    expected_eligibility_version: Annotated[int, Field(gt=0)]
    expected_episode_generation: Annotated[int, Field(gt=0)]
    trigger_set_sha256: Sha256
    review_rules: Annotated[list[VersionRef], Field(min_length=1)]


class ReviewItem(StrictModel):
    requirement_id: Identifier
    definition: VersionRef
    evidence_refs: list[EvidenceRef]
    finding: Name
    result: Literal['pending', 'satisfied']


class ReviewInput(CurrentInput):
    rationale: Annotated[str, Field(min_length=1, max_length=1000)]
    items: Annotated[list[ReviewItem], Field(min_length=1)]
    current_assessment_attested: Literal[True]


class ClearanceInput(CurrentInput):
    review_id: Identifier
    review_sha256: Sha256


class ExportInput(Header):
    cutoff: AwareDatetime


class Requirement(StrictModel):
    requirement_id: Identifier
    definition: VersionRef
    responsible_role: Literal['doctor']
    evidence_kinds: Annotated[list[Identifier], Field(min_length=1)]
    source_ids: Annotated[list[Identifier], Field(min_length=1)]


class ManualReviewRule(StrictModel):
    ref: VersionRef
    trigger_rule: VersionRef
    requirements: Annotated[list[Requirement], Field(min_length=1)]


class SourceGrant(StrictModel):
    account_id: Identifier
    service_patient_id: Identifier
    archive_patient_id: Identifier
    source_id: Identifier
    source_version: Name
    run_id: Identifier
    partition_id: Identifier
    archive_id: Identifier
    package_sha256: Sha256
    archive_authority_sha256: Sha256
    ownership_ref: ExactRef
    episode_namespace: Identifier
    allowed_operations: list[Literal['invalidate']]
    trigger_rules: Annotated[list[VersionRef], Field(min_length=1)]
    required_reviews: Annotated[list[Requirement], Field(min_length=1)]
    follow_up_owner_id: Identifier
    follow_up_policy: VersionRef
    due_at: AwareDatetime
    escalation_destination: Name


class LiveHoldAuthority(Header):
    authority_id: Identifier
    version: VersionRef
    enabled: bool
    observed_binding: VersionRef
    archive_verifier: VersionRef
    producer: VersionRef
    source_registry: VersionRef
    execution: Literal['synthetic_service', 'contract_fixture']
    grants: list[SourceGrant]


class ReviewRules(Header):
    rules: list[ManualReviewRule]


class ControlBinding(StrictModel):
    database_instance_id: Identifier
    capability: Literal['LIVE-HOLD-01/1.0.0']
    minimum_reader_writer_capability: Literal['LIVE-HOLD-01/1.0.0']
    authority_generation: Annotated[int, Field(gt=0)]
    authority_sha256: Sha256
    review_rules_sha256: Sha256
    enabled: bool
    activation_id: Identifier


class InstalledBundle(StrictModel):
    control: ControlBinding
    authority: LiveHoldAuthority
    review_rules: ReviewRules
