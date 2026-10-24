"""S2 app SOURCE contracts. No executable/serving authority is admitted here.

The old schema2/candidate definitions remain separate and unchanged. These
references hash complete typed content, rather than a label or document hash.
"""
from datetime import timedelta
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from .analysis import reference, sha
from .common import Identifier, SeedKey, Sha256, StrictModel, VersionRef
from .protocol import SUPPORT_REF
from .protocol_analysis import ProtocolHistory
from .support_s2 import S2Request, S2Result
from .support_s2_fit import DEFINITIONS, S2FitProvenance

Positive = Annotated[int, Field(ge=1)]
Count = Annotated[int, Field(ge=0, le=84)]
Version = Literal['s2-app-source-1.0.0']
FIT_PURPOSE = 'EST-POLICY:poc-support-refresh-v1'
INITIAL_PROCESS = 'S2-refresh-fit-initial'
EXTENSION_PROCESS = 'S2-refresh-fit-extension'


class SamplerSettings(StrictModel):
    backend: Literal['pymc_native_nuts'] = 'pymc_native_nuts'
    chains: Literal[4] = 4
    tune: Literal[1000] = 1000
    draws: Literal[1000] = 1000
    extension_tune: Literal[2000] = 2000
    extension_draws: Literal[2000] = 2000
    target_accept: Literal[.995] = .995
    max_treedepth: Literal[12] = 12
    precision: Literal['float64'] = 'float64'
    thinning: Literal[1] = 1
    original_prior_each_attempt: Literal[True] = True
    settings_status: Literal['PROPOSED_S2_APPLICABILITY_NOT_EXECUTABLE'] = 'PROPOSED_S2_APPLICABILITY_NOT_EXECUTABLE'
    candidate_controls_source: Literal['methods/nof1/model.py; contracts/domain/analysis.py'] = 'methods/nof1/model.py; contracts/domain/analysis.py'


class DiagnosticSettings(StrictModel):
    rhat_strict_upper: Literal[1.01] = 1.01
    bulk_ess_min: Literal[400] = 400
    tail_ess_min: Literal[400] = 400
    unresolved_divergences: Literal[0] = 0
    bfmi_strict_lower: Literal[.3] = .3
    tree_depth_hits: Literal[0] = 0
    unresolved_warnings: Literal[0] = 0
    require_finite_energy_mcse_all_chains: Literal[True] = True
    inventory: Literal['all_sampled_and_reported:mu_alpha,mu_tau,b,s_alpha,s_tau,s_e,s_Q,rho,z,u,alpha,tau,e_T,epsilon_0..11,error_0..11'] = 'all_sampled_and_reported:mu_alpha,mu_tau,b,s_alpha,s_tau,s_e,s_Q,rho,z,u,alpha,tau,e_T,epsilon_0..11,error_0..11'
    missing_fields: Literal['fail_closed'] = 'fail_closed'
    status: Literal['PROPOSED_S2_APPLICABILITY'] = 'PROPOSED_S2_APPLICABILITY'


class ExtensionPolicy(StrictModel):
    maximum: Literal[1] = 1
    automatic_retry: Literal[False] = False
    trigger: Literal['canonical_fit_diagnostics_or_required_indicator_precision_failed_only'] = 'canonical_fit_diagnostics_or_required_indicator_precision_failed_only'
    linkage: Literal['new_attempt_and_distinct_purpose_SeedKey; same_original_prior_data_cutoff; retain_initial_artifacts'] = 'new_attempt_and_distinct_purpose_SeedKey; same_original_prior_data_cutoff; retain_initial_artifacts'
    selection: Literal['extension_all_four_original_chains_only_if_all_gates_pass; never_concatenate_or_select_chains'] = 'extension_all_four_original_chains_only_if_all_gates_pass; never_concatenate_or_select_chains'
    budget: Literal['must_fit_single_predeclared_operation; unknown_budget_refuses_dispatch'] = 'must_fit_single_predeclared_operation; unknown_budget_refuses_dispatch'


class ExecutionPreparation(StrictModel):
    # Slice2 must replace these with a separately reviewed, versioned contract.
    # Unknown caps/source/image/installed API cannot reach dispatch/private I/O.
    qualified_production_image: Literal[None] = None
    production_source_closure: Literal[None] = None
    resource_caps: Literal[None] = None
    artifact_caps: Literal[None] = None
    installed_diagnostic_api: Literal[None] = None
    executable: Literal[False] = False
    serving_authority: Literal[False] = False


class AppConfiguration(StrictModel):
    schema_version: Version = 's2-app-source-1.0.0'
    sampler: SamplerSettings = SamplerSettings()
    diagnostics: DiagnosticSettings = DiagnosticSettings()
    extension: ExtensionPolicy = ExtensionPolicy()
    execution: ExecutionPreparation = ExecutionPreparation()
    model: VersionRef
    prior: VersionRef
    features: VersionRef
    batch: VersionRef


CONFIG = AppConfiguration.model_validate(dict(**DEFINITIONS)).model_dump(mode='json')
CONFIG_REF = reference('poc-support-s2-app-source-v1', CONFIG)
SEED_POLICY = dict(namespace='fit', protocol=SUPPORT_REF, initial_process=INITIAL_PROCESS,
    extension_process=EXTENSION_PROCESS, scenario='attempt_id', patient='predeclared_real_target',
    time_index='cutoff_day', replicate='app_created_entropy_recorded_once_with_attempt',
    sampler_seed='int(canonical_sha256(complete_SeedKey)[:8],16) % 2147483647',
    forbidden='generator/UNIT/target-index/copied-job seeds; assignment RNG is independent')
SEED_POLICY_REF = reference('poc-support-s2-app-fit-seed-v1', SEED_POLICY)
POSTERIOR_SCHEMA = dict(name='posterior.nc', groups=['posterior','sample_stats'],
    chain_labels=[0,1,2,3], draw_labels='0..999 initial OR 0..1999 extension; no tuning draws',
    patient_labels='exact ordered twelve input IDs', feature_labels='exact four s2_model.FEATURES',
    joint=['alpha:patient','tau:patient','b:feature','rho:scalar','s_e:scalar','s_Q:scalar','e_T:patient'],
    diagnostic_variables=DiagnosticSettings().inventory, sample_stats=['energy','diverging','tree_depth','lp'],
    dtype='float64 continuous; bool diverging; int tree_depth',
    units='quality_points alpha/tau/s_e/s_Q/e_T; declared feature units b; dimensionless rho',
    binary_semantics='learner_only_validation_required', size_caps='UNRESOLVED_NON_EXECUTABLE')
POSTERIOR_SCHEMA_REF = reference('poc-support-s2-app-posterior-source-v1', POSTERIOR_SCHEMA)


class MemberVersion(StrictModel):
    patient_id: Identifier
    patient_version: Positive


class S2Selection(StrictModel):
    schema_version: Version
    target_id: Identifier
    cohort_id: Identifier
    members: Annotated[tuple[MemberVersion, ...], Field(min_length=12, max_length=12)]
    configuration: VersionRef

    @model_validator(mode='after')
    def selected(self):
        ids = [m.patient_id for m in self.members]
        if ids != sorted(set(ids)) or self.target_id not in ids:
            raise ValueError('explicit_real_target_and_ordered_unique_twelve_required')
        if self.configuration.model_dump() != CONFIG_REF:
            raise ValueError('unadmitted_S2_app_configuration')
        return self


class SelectionIdentity(StrictModel):
    schema_version: Version
    owner_id: Identifier
    store_id: Identifier
    authority_generation: Positive
    generation_id: Identifier
    origin: AwareDatetime
    selected_at: AwareDatetime
    recorded_at: AwareDatetime
    selection: S2Selection


class SelectionReceipt(SelectionIdentity):
    reference: VersionRef

    @model_validator(mode='after')
    def immutable(self):
        content = self.model_dump(mode='json', exclude={'reference'})
        if self.reference.model_dump() != reference('poc-support-s2-preoutcome-selection-v1', content):
            raise ValueError('selection_receipt_content_changed')
        if self.selected_at > self.origin:
            raise ValueError('selection_must_precede_first_support_outcome')
        return self


class MemberCounts(StrictModel):
    patient_id: Identifier
    observed: tuple[Count, Count]
    missing: tuple[Count, Count]
    prior_hierarchy_only: bool


class S2Export(StrictModel):
    schema_version: Version
    selection: SelectionReceipt
    provenance: S2FitProvenance
    histories: Annotated[tuple[ProtocolHistory, ...], Field(min_length=12, max_length=12)]
    counts: Annotated[tuple[MemberCounts, ...], Field(min_length=12, max_length=12)]
    contribution_sha256: Sha256
    configuration: VersionRef
    reference: VersionRef

    @model_validator(mode='after')
    def bound(self):
        p = self.provenance
        s = self.selection
        ids = [m.patient_id for m in s.selection.members]
        if (p.owner_id != s.owner_id or p.store_id != s.store_id or p.generation_id != s.generation_id
                or p.cohort_id != s.selection.cohort_id or p.target_id != s.selection.target_id
                or p.origin != s.origin or [h.patient_id for h in self.histories] != ids
                or [m.patient_id for m in p.members] != ids or [m.patient_id for m in self.counts] != ids):
            raise ValueError('selection_export_identity_mismatch')
        if self.configuration.model_dump() != CONFIG_REF:
            raise ValueError('export_configuration_mismatch')
        if self.reference.model_dump() != reference('poc-support-s2-trusted-export-v1', self.model_dump(mode='json', exclude={'reference'})):
            raise ValueError('complete_typed_export_reference_mismatch')
        # Reuse the actual scalar adapter, never duplicate its row resolution.
        from methods.support.s2_data import prepare
        data = prepare(self.histories, p)
        if data.contribution_sha256 != self.contribution_sha256:
            raise ValueError('resolved_contributions_changed')
        for count, member in zip(self.counts, data.members):
            if (count.observed != member.observed_counts or count.missing != member.missing_counts
                    or count.prior_hierarchy_only != member.prior_hierarchy_only):
                raise ValueError('frozen_opportunity_counts_changed')
        for history, binding in zip(self.histories, p.members):
            if binding.source_projection_sha256 != source_projection_sha256(history):
                raise ValueError('reduced_source_projection_content_changed')
        return self


def source_projection_sha256(history: ProtocolHistory):
    return sha(dict(records=[r.model_dump(mode='json') for r in history.records],
        provenance=[r.model_dump(mode='json') for r in history.provenance]))


class S2ExportSelection(StrictModel):
    schema_version: Version
    selection_key: Annotated[str, Field(min_length=1, max_length=128)]
    members: Annotated[tuple[MemberVersion, ...], Field(min_length=12, max_length=12)]
    cutoff: AwareDatetime
    configuration: VersionRef

    @model_validator(mode='after')
    def configured(self):
        ids = [m.patient_id for m in self.members]
        if ids != sorted(set(ids)) or self.configuration.model_dump() != CONFIG_REF:
            raise ValueError('ordered_unique_members_and_exact_app_config_required')
        return self


class S2Submission(S2ExportSelection):
    kind: Literal['support_s2_fit_submission']
    approved_export: VersionRef


class FitSeedRecord(StrictModel):
    record_id: Identifier
    attempt_id: Identifier
    owner_id: Identifier
    created_at: AwareDatetime
    policy: VersionRef
    key: SeedKey
    sampler_seed: Annotated[int, Field(ge=0, lt=2147483647)]

    @model_validator(mode='after')
    def derived(self):
        if (self.policy.model_dump() != SEED_POLICY_REF or self.key.namespace != 'fit'
                or self.key.protocol != SUPPORT_REF['id'] or self.key.scenario != self.attempt_id
                or self.key.process not in (INITIAL_PROCESS, EXTENSION_PROCESS)
                or self.sampler_seed != int(sha(self.key.model_dump(mode='json'))[:8], 16) % 2147483647):
            raise ValueError('registered_app_fit_seed_purpose_and_derivation_required')
        return self


class S2FitInput(StrictModel):
    schema_version: Version
    kind: Literal['poc_support_s2_app_fit_input']
    purpose: Literal['EST-POLICY:poc-support-refresh-v1']
    attempt_id: Identifier
    export: S2Export
    seed_record: FitSeedRecord
    configuration: VersionRef
    posterior_schema: VersionRef
    executable: Literal[False]

    @model_validator(mode='after')
    def identity(self):
        p = self.export.provenance
        if (self.seed_record.attempt_id != self.attempt_id or self.seed_record.owner_id != p.owner_id
                or self.seed_record.key.patient != p.target_id or self.seed_record.key.time_index != p.cutoff_day
                or self.seed_record.key.process != INITIAL_PROCESS or self.configuration.model_dump() != CONFIG_REF
                or self.posterior_schema.model_dump() != POSTERIOR_SCHEMA_REF):
            raise ValueError('fit_attempt_export_seed_configuration_binding_mismatch')
        return self


class S2FitResult(StrictModel):
    schema_version: Version
    kind: Literal['poc_support_s2_app_fit_result']
    attempt_id: Identifier
    input_reference: VersionRef
    configuration: VersionRef
    status: Literal['unavailable_source_preparation']
    reason: Literal['production_worker_artifact_and_diagnostics_unqualified']
    serving_authority: Literal[False]

    @model_validator(mode='after')
    def configured(self):
        if self.configuration.model_dump() != CONFIG_REF:
            raise ValueError('fit_result_configuration_mismatch')
        return self


class S2ExtensionRequest(StrictModel):
    schema_version: Version
    attempt_id: Identifier
    parent_attempt_id: Identifier
    parent_input_reference: VersionRef
    original_export_reference: VersionRef
    seed_record: FitSeedRecord
    number: Literal[1]
    trigger: Literal['canonical_fit_diagnostics_failed', 'required_indicator_precision_failed']
    tune: Literal[2000]
    draws: Literal[2000]
    chains: Literal[4]
    retain_initial_artifacts: Literal[True]
    concatenate_attempts: Literal[False]
    executable: Literal[False]

    @model_validator(mode='after')
    def linked(self):
        if (self.attempt_id == self.parent_attempt_id or self.seed_record.attempt_id != self.attempt_id
                or self.seed_record.key.process != EXTENSION_PROCESS):
            raise ValueError('distinct_linked_extension_attempt_and_seed_purpose_required')
        return self


def validate_extension(extension: S2ExtensionRequest, initial: S2FitInput):
    if (extension.parent_attempt_id != initial.attempt_id
            or extension.parent_input_reference.model_dump() != reference('poc-support-s2-app-fit-input-v1', initial.model_dump(mode='json'))
            or extension.original_export_reference != initial.export.reference
            or extension.seed_record.owner_id != initial.seed_record.owner_id
            or extension.seed_record.key.patient != initial.seed_record.key.patient
            or extension.seed_record.key.time_index != initial.seed_record.key.time_index
            or extension.seed_record.key.replicate == initial.seed_record.key.replicate):
        raise ValueError('extension_requires_same_original_prior_data_cutoff_and_distinct_recorded_seed')
    return extension


class S2PredictionInput(StrictModel):
    schema_version: Version
    kind: Literal['poc_support_s2_app_prediction_input']
    purpose: Literal['EST-POLICY:poc-support-prediction-v1']
    attempt_id: Identifier
    fit_input_reference: VersionRef
    fit_result_reference: VersionRef
    request: S2Request
    patient_version: Positive
    state_version: Positive
    consent_version: Positive
    eligibility_version: Positive
    allowed_actions: tuple[Literal['support_prompt', 'no_prompt'], ...]
    context_cutoff: AwareDatetime
    origin: AwareDatetime
    expires_at: AwareDatetime
    configuration: VersionRef
    executable: Literal[False]

    @model_validator(mode='after')
    def exact_context(self):
        if (len(set(self.allowed_actions)) != len(self.allowed_actions)
                or self.context_cutoff != self.origin + timedelta(days=self.request.decision_day)
                or self.expires_at != self.origin + timedelta(days=self.request.cutoff + 14)
                or not self.context_cutoff < self.expires_at or self.configuration.model_dump() != CONFIG_REF):
            raise ValueError('exact_context_mask_configuration_or_original_expiry_mismatch')
        return self


class S2PredictionResult(StrictModel):
    schema_version: Version
    kind: Literal['poc_support_s2_app_prediction_result']
    attempt_id: Identifier
    input_reference: VersionRef
    candidate: S2Result
    serving_authority: Literal[False]


def validate_fit_result(result: S2FitResult, product: S2FitInput):
    if (result.attempt_id != product.attempt_id
            or result.input_reference.model_dump() != reference('poc-support-s2-app-fit-input-v1', product.model_dump(mode='json'))):
        raise ValueError('fit_result_complete_input_identity_mismatch')
    return result


def validate_prediction_input(product: S2PredictionInput, fit: S2FitInput, result: S2FitResult):
    validate_fit_result(result, fit)
    p = fit.export.provenance
    request = product.request
    if (product.fit_input_reference.model_dump() != reference('poc-support-s2-app-fit-input-v1', fit.model_dump(mode='json'))
            or product.fit_result_reference.model_dump() != reference('poc-support-s2-app-fit-result-v1', result.model_dump(mode='json'))
            or request.fit_id != fit.attempt_id or request.fitted_snapshot_sha256 != p.histories_sha256
            or request.owner_id != p.owner_id or request.store_id != p.store_id
            or request.generation_id != p.generation_id or request.cohort_id != p.cohort_id
            or request.target_id != p.target_id or request.cutoff != p.cutoff_day or product.origin != p.origin):
        raise ValueError('prediction_frozen_fit_owner_cohort_target_cutoff_identity_mismatch')
    for frozen, member, count in zip(request.members, p.members, fit.export.counts):
        if (frozen.patient_id != member.patient_id or frozen.patient_version != member.patient_version
                or frozen.history_sha256 != member.history_sha256 or frozen.revisions_sha256 != member.revisions_sha256
                or frozen.observed != count.observed or frozen.missing != count.missing):
            raise ValueError('prediction_all_member_fitted_evidence_or_counts_changed')
    return product


def validate_prediction_result(result: S2PredictionResult, product: S2PredictionInput, *, at):
    candidate = result.candidate
    if (result.attempt_id != product.attempt_id
            or result.input_reference.model_dump() != reference('poc-support-s2-app-prediction-input-v1', product.model_dump(mode='json'))
            or candidate.request_sha256 != sha(product.request.model_dump(mode='json'))
            or (candidate.target_id, candidate.context_id, candidate.context_version) !=
                (product.request.target_id, product.request.context_id, product.request.context_version)
            or not product.context_cutoff <= at < product.expires_at):
        raise ValueError('prediction_result_context_identity_or_original_expiry_mismatch')
    # SOURCE contracts can describe candidate evidence, never admit serving.
    return result


def validate_current_context(product: S2PredictionInput, *, owner, store, generation,
        target, patient_version, state_version, consent_version, eligibility_version,
        context_id, context_version, snapshot_sha256, allowed_actions, at):
    request = product.request
    if ((owner, store, generation, target) != (request.owner_id, request.store_id, request.generation_id, request.target_id)
            or (patient_version, state_version, consent_version, eligibility_version) !=
                (product.patient_version, product.state_version, product.consent_version, product.eligibility_version)
            or (context_id, context_version, snapshot_sha256) !=
                (request.context_id, request.context_version, request.current_snapshot_sha256)
            or tuple(allowed_actions) != product.allowed_actions or not product.context_cutoff <= at < product.expires_at):
        raise ValueError('current_S2_prediction_context_authority_mask_or_expiry_changed')
    # Matching scalar identities still do not grant source/runtime authority.
    return product


def require_executable(product=None):
    # No string/config mutation can enable a partially implemented S2 worker.
    raise ValueError('S2_production_execution_and_serving_not_qualified')
