"""Closed saved-posterior S2 SOURCE contracts; no execution/serving authority.

Deterministic inference has no RNG or sampler SeedKey. Fit/assignment purposes
remain separate. Scientific arrays and binary reads belong only to learner.
"""
from datetime import timedelta
from typing import Annotated, Literal
from pydantic import ConfigDict, Field, model_validator
from .analysis import canonical, reference, sha
from .common import Identifier, Sha256, StrictModel, VersionRef
from .entities import DecisionSnapshot
from .protocol_analysis import ProtocolHistory, ReducedRef, Consent
from .support_s2 import (CONFIG_REF as CANDIDATE_REF, DEFINITIONS, HSTAR_REF,
    NUMERICS, CELLS, S2Request, S2Result)
from .support_s2_native import (NativeInput, NativeResult, TrustedLaunch, Artifact,
    BinarySemantics, CONFIG_REF as FIT_REF, SCHEMA_REF, validate_result as validate_fit)

MIB=1024**2
INPUT_CAP=10*MIB  # native input<=8MiB + native result<=1MiB + context/envelope<=1MiB
CONTEXT_CAP=768*1024
RESULT_CAP=64*1024
JOINT_ARRAY_CAP=4*MIB  # 43 float64 values/draw *4chains*2000draws =2,752,000B
CONFIG=dict(schema='s2-saved-prediction-source-1.0.0',fit_configuration=FIT_REF,
    posterior_schema=SCHEMA_REF,candidate=CANDIDATE_REF,definitions=DEFINITIONS,numerics=NUMERICS,
    algorithm='unchanged methods.support.s2_prediction.predict; all joint draws/all nine cells',
    purpose='EST-POLICY:poc-support-prediction-v1',seed='none: deterministic inference, no RNG',
    counts='frozen fitted two-action observed/missing counts; never current-context counts',
    context='owned current predecision row/protocol projection/current consent/explicit approval/hold/Nfreeze/burden',
    expiry='original T+14 before draw; reward<=84; completion cannot renew',
    bounds=dict(input_bytes=INPUT_CAP,context_bytes=CONTEXT_CAP,result_bytes=RESULT_CAP,joint_array_bytes=JOINT_ARRAY_CAP),
    operation=dict(status='PROSPECTIVE_UNQUALIFIED',outer=600,work=570,segment=300,
        origin='one absolute operation origin; segment starts once before reference prediction',
        blocked_native='existing independent supervisor/watchdog required; no syscall preemption claim'),
    qualification=dict(image=None,source_closure=None,installed_API=None,genuine_fit=None,operation=None),
    executable=False,serving_authority=False)
CONFIG_REF=reference('poc-support-s2-saved-prediction-source-v1',CONFIG)


class FitCollection(StrictModel):
    model_config=ConfigDict(serialize_by_alias=True,validate_by_name=True)
    schema_name: Literal['s2-native-owned-collection-v1'] = Field(alias='schema')
    attempt_id: Identifier
    input_sha256: Sha256
    claim_sha256: Sha256
    terminal: Literal['reaped_exit_0_no_oom_no_restart']
    files: Annotated[tuple[Artifact,...],Field(min_length=1,max_length=1)]
    result_sha256: Sha256


class SavedFit(StrictModel):
    product: NativeInput
    result: NativeResult
    launch: TrustedLaunch
    collection: FitCollection
    collection_reference: VersionRef

    @model_validator(mode='after')
    def admitted_identity(self):
        validate_fit(self.result,self.product,self.launch.model_dump(mode='json'))
        if self.result.status!='completed':raise ValueError('S2_saved_fit_not_completed')
        expected=dict(schema='s2-native-owned-collection-v1',attempt_id=self.product.attempt_id,
            input_sha256=sha(self.product.model_dump(mode='json')),claim_sha256=self.launch.claim_sha256,
            terminal='reaped_exit_0_no_oom_no_restart',files=[self.result.semantics.artifact.model_dump(mode='json')],
            result_sha256=sha(self.result.model_dump(mode='json')))
        if self.collection.model_dump(mode='json',by_alias=True)!=expected or self.collection_reference.model_dump()!=reference('poc-support-s2-saved-fit-collection-v1',expected):
            raise ValueError('S2_saved_fit_complete_owned_collection_mismatch')
        return self


def prospective_features(projection,refs):
    """Actual pure feature producer, without an executed decision or outcome."""
    from methods.support.s2_data import predecision_features
    return predecision_features(projection,cutoff=projection.cutoff,context=refs,
        context_projection_sha256=sha([r.model_dump(mode='json') for r in refs]),
        active={r.record_id:r for r in projection.records})


def current_mask(decision,projection,consents,activation_ref,approval_ref,refs):
    """Current policy inputs only; never use fitted missingness counts as a mask.

    Generic physician eligibility cannot supply missing support actions. The
    explicit support envelope grants its binary set; current safety/N/burden
    restrict it before any future controller draw. This function never draws.
    """
    from methods.support.s2_data import resolve
    active={r.record_id:r for r in projection.records}
    activation=resolve(active,activation_ref,'protocol_snapshot')
    approval=resolve(active,approval_ref,'approval')
    if (activation.family!='support' or activation.protocol!=projection.protocol
            or approval_ref not in activation.approval_refs or approval.purpose!='randomization_protocol'
            or approval.option is not None or len(approval.permitted_options)!=2
            or set(approval.permitted_options)!={'support_prompt','no_prompt'}):
        raise ValueError('S2_explicit_current_support_envelope_required')
    at=decision.cutoff
    if any(c.patient_id!=decision.patient_id or c.component!='mrt_bandit' or c.available_at>at for c in consents):
        raise ValueError('S2_current_consent_projection_mismatch')
    consent=max(consents,key=lambda c:(c.available_at,c.recorded_at,c.revision,c.record_id),default=None)
    active_consent=(consent is not None and consent.record_status!='retracted'
        and consent.consent_status=='active' and consent.oversight_status=='approved_synthetic'
        and consent.effective_at<=at and (consent.expires_at is None or at<consent.expires_at)
        and (consent.withdrawn_at is None or at<consent.withdrawn_at))
    workflow=decision.workflow
    if (not active_consent or workflow.clinical=='clinical_hold' or workflow.hold_reasons or workflow.data_readiness!='ready'
            or workflow.support_mode=='paused'):return (), 'current_support_unavailable'
    if (workflow.support_mode in ('fixed','frozen') or workflow.learning in ('nof1_block','nof1_washout')):
        return ('no_prompt',), 'fixed_or_N_snapshot'
    if workflow.support_mode not in ('mrt','adaptive'):
        raise ValueError('S2_current_support_mode_unavailable')
    x,_=prospective_features(projection,refs)
    recent=[r for r in active.values() if r.kind=='delivery' and r.option=='support_prompt'
        and r.stage=='delivered' and at-timedelta(days=1)<=r.event_at<at]
    if x[2]>=3 or recent:return ('no_prompt',), 'current_burden_constraint'
    return ('support_prompt','no_prompt'), 'binary_support_envelope'


class ContextBody(StrictModel):
    schema_version: Literal['s2-saved-context-v1']
    owner_id: Identifier
    store_id: Identifier
    authority_generation: Annotated[int,Field(ge=1)]
    generation_id: Identifier
    decision: DecisionSnapshot
    projection: ProtocolHistory
    current_consents: Annotated[tuple[Consent,...],Field(max_length=32)]
    activation_ref: ReducedRef
    approval_ref: ReducedRef
    feature_refs: Annotated[tuple[ReducedRef,...],Field(max_length=4096)]
    x_current: tuple[float,float,float,float]
    allowed_actions: tuple[Literal['support_prompt','no_prompt'],...]
    mask_reason: Literal['current_support_unavailable','fixed_or_N_snapshot','current_burden_constraint','binary_support_envelope']

    @model_validator(mode='after')
    def genuine_predecision(self):
        d=self.decision;h=self.projection
        if (d.patient_id!=h.patient_id or d.view.mode!='current' or h.family!='support'
                or h.cutoff!=d.cutoff or d.available_at!=d.cutoff or d.event_at!=d.cutoff):
            raise ValueError('S2_exact_current_predecision_snapshot_required')
        expected=tuple(dict(record_id=r.record_id,projection_sha256=sha(r.model_dump(mode='json')))
            for r in sorted(h.records,key=lambda r:r.record_id))
        if tuple(r.model_dump(mode='json') for r in self.feature_refs)!=expected:
            raise ValueError('S2_complete_strict_predecision_projection_refs_required')
        x,_=prospective_features(h,self.feature_refs)
        if self.x_current!=x:raise ValueError('S2_original_predecision_feature_formula_changed')
        mask,reason=current_mask(d,h,self.current_consents,self.activation_ref,self.approval_ref,self.feature_refs)
        if self.allowed_actions!=mask or self.mask_reason!=reason:
            raise ValueError('S2_current_mask_must_match_current_safety_and_burden')
        if len(canonical(self.model_dump(mode='json')).encode())>CONTEXT_CAP:
            raise ValueError('S2_current_context_byte_cap')
        return self


class CurrentContext(ContextBody):
    reference: VersionRef

    @model_validator(mode='after')
    def content_identity(self):
        if self.reference.model_dump()!=reference('poc-support-s2-current-context-v1',self.model_dump(mode='json',exclude={'reference'})):
            raise ValueError('S2_current_context_reference_changed')
        return self


def make_request(fit,context):
    p=fit.product.initial.export.provenance;d=context.decision
    day=int((d.cutoff-p.origin).total_seconds()/86400)
    return S2Request.model_validate_json(canonical(dict(schema_version='s2-prediction-candidate-1.0.0',
        owner_id=p.owner_id,store_id=p.store_id,generation_id=p.generation_id,cohort_id=p.cohort_id,
        fit_id=fit.product.attempt_id,fit_artifact_sha256=fit.result.semantics.artifact.sha256,
        fitted_hstar=HSTAR_REF,fitted_snapshot_sha256=p.histories_sha256,configuration=CANDIDATE_REF,
        definitions=DEFINITIONS,members=[dict(patient_id=m.patient_id,patient_version=m.patient_version,
            history_sha256=m.history_sha256,revisions_sha256=m.revisions_sha256,observed=c.observed,missing=c.missing)
            for m,c in zip(p.members,fit.product.initial.export.counts)],cutoff=p.cutoff_day,target_id=d.patient_id,
        context_id=d.record_id,context_version=d.state_version,current_snapshot_sha256=sha(d.model_dump(mode='json')),
        decision_day=day,reward_day=day+1,h=day+1-p.cutoff_day,expires_before_decision=p.cutoff_day+14,x_current=context.x_current)))


class SavedPredictionInput(StrictModel):
    schema_version: Literal['s2-saved-prediction-source-1.0.0']
    kind: Literal['poc_support_s2_saved_prediction_input']
    purpose: Literal['EST-POLICY:poc-support-prediction-v1']
    attempt_id: Identifier
    fit: SavedFit
    context: CurrentContext
    request: S2Request
    configuration: VersionRef
    executable: Literal[False]

    @model_validator(mode='after')
    def exact_frozen_fit_context(self):
        p=self.fit.product.initial.export.provenance;c=self.context;d=c.decision
        if (self.configuration.model_dump()!=CONFIG_REF or self.request!=make_request(self.fit,c)
                or (c.owner_id,c.store_id,c.generation_id,c.authority_generation)!=
                (p.owner_id,p.store_id,p.generation_id,self.fit.product.initial.export.selection.authority_generation)
                or d.patient_id not in [m.patient_id for m in p.members]
                or c.projection.origin!=p.origin or (d.cutoff-p.origin).total_seconds()!=self.request.decision_day*86400):
            raise ValueError('S2_saved_fit_current_context_complete_identity_mismatch')
        if self.attempt_id==self.fit.product.attempt_id:
            raise ValueError('S2_prediction_is_distinct_from_fit_attempt')
        if len(canonical(self.model_dump(mode='json')).encode())>INPUT_CAP:
            raise ValueError('S2_saved_prediction_input_byte_cap')
        return self


class PredictionLaunch(StrictModel):
    schema_version: Literal['s2-saved-prediction-launch-v1']
    attempt_id: Identifier
    input_sha256: Sha256
    configuration: VersionRef
    source_commit: Annotated[str,Field(pattern=r'^[a-f0-9]{40}$')]
    learner_image: Annotated[str,Field(pattern=r'^sha256:[a-f0-9]{64}$')]
    installed_closure_sha256: Sha256
    claim_sha256: Sha256


class SavedPredictionResult(StrictModel):
    schema_version: Literal['s2-saved-prediction-source-1.0.0']
    kind: Literal['poc_support_s2_saved_prediction_result']
    attempt_id: Identifier
    input_sha256: Sha256
    context_reference: VersionRef
    fit_collection_reference: VersionRef
    configuration: VersionRef
    launch: PredictionLaunch
    binary: BinarySemantics | None
    candidate: S2Result | None
    status: Literal['candidate_ready','fallback','failed']
    reason: Literal['candidate_evidence_only','current_mask_not_binary','numerical_or_precision_unready','worker_refused','deadline_exceeded']
    probability: Annotated[float,Field(ge=0,le=1)]
    serving_authority: Literal[False]

    @model_validator(mode='after')
    def closed(self):
        if self.configuration.model_dump()!=CONFIG_REF or self.launch.configuration.model_dump()!=CONFIG_REF:
            raise ValueError('S2_saved_result_configuration_changed')
        if self.status=='candidate_ready':
            if (self.reason!='candidate_evidence_only' or self.binary is None or self.candidate is None
                    or self.candidate.status!='candidate_ready' or self.probability!=self.candidate.probability):
                raise ValueError('S2_saved_ready_requires_all_candidate_and_binary_gates')
        elif self.probability!=.5:raise ValueError('S2_saved_unready_requires_point5')
        if self.status!='candidate_ready' and self.candidate is not None and self.candidate.status=='candidate_ready':
            raise ValueError('S2_saved_status_candidate_contradiction')
        expected={'candidate_ready':{'candidate_evidence_only'},'fallback':{'current_mask_not_binary','numerical_or_precision_unready'},
            'failed':{'worker_refused','deadline_exceeded'}}
        if self.reason not in expected[self.status]:raise ValueError('S2_saved_status_reason_contradiction')
        return self


def validate_saved_result(result,product,trusted,*,at):
    result=SavedPredictionResult.model_validate(result)
    p=product.fit.product.initial.export.provenance
    if (result.attempt_id!=product.attempt_id or result.input_sha256!=sha(product.model_dump(mode='json'))
            or result.context_reference!=product.context.reference or result.fit_collection_reference!=product.fit.collection_reference
            or result.launch.model_dump(mode='json')!=trusted or result.launch.attempt_id!=product.attempt_id
            or result.launch.input_sha256!=result.input_sha256
            or not product.context.decision.cutoff<=at<p.origin+timedelta(days=p.cutoff_day+14)):
        raise ValueError('S2_saved_result_context_fit_launch_or_original_expiry_mismatch')
    if result.binary is not None and result.binary!=product.fit.result.semantics:
        raise ValueError('S2_saved_result_posterior_bytes_or_semantics_changed')
    if result.candidate is not None:
        r=result.candidate;q=product.request
        if (r.request_sha256!=sha(q.model_dump(mode='json')) or
                (r.target_id,r.context_id,r.context_version)!=(q.target_id,q.context_id,q.context_version)):
            raise ValueError('S2_saved_candidate_exact_context_mismatch')
    if result.status=='candidate_ready' and product.context.allowed_actions!=('support_prompt','no_prompt'):
        raise ValueError('S2_saved_ready_requires_current_binary_mask')
    if len(canonical(result.model_dump(mode='json')).encode())>RESULT_CAP:
        raise ValueError('S2_saved_summary_byte_cap')
    return result


def require_executable(product=None):
    raise ValueError('S2_saved_prediction_source_fit_image_API_OP_and_serving_unqualified')
