"""Closed protocol purpose contracts. P1 admits no executable configuration."""
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator

from .analysis import PRIOR_REF, canonical, reference, sha
from .common import Identifier, Interval, Name, Sha256, StrictModel, VersionRef
from .estimands import MethodContext
from .protocol import LAW_REF, PROTOCOL_REFS
from .protocol_analysis import ProtocolHistory

Purpose = Literal['N0', 'N1', 'S1-WCLS', 'S2-refresh']
BOUNDARY_CONFIG = dict(executable=False, id='poc-protocol-boundary-only-v1',
                       purpose='schema-and-isolation-only', version='1.0.0')
BOUNDARY_CONFIG_REF = reference(BOUNDARY_CONFIG['id'], BOUNDARY_CONFIG)
WCLS_PRIOR_REF = reference('poc-wcls-prior-not-applicable-v1',
                          'not applicable: design-based S1 WCLS has no Bayesian prior')
# These describe the canonical existing assumptions, not active fit settings.
N_PRIOR_REF = reference('poc-nof1-prior-v1', dict(base=PRIOR_REF,
    medication_and_rebound_population='Normal(0,3)', patient_sd='HalfNormal(1)'))
S2_PRIOR_REF = reference('poc-support-policy-prior-v1', dict(
    effect_and_control='Normal(0,2)', intercept='Normal(5,3)',
    group_and_noise_sd='HalfNormal(2)', rho='Uniform(-.95,.95)'))
N_ESTIMAND = reference('EST-N1:poc-hstar-v1',
    'Expected next seven-night quality A minus B conditional on common reduced H*; integrate adherence/residual exposure/rebound/measurement')
S1_ESTIMAND = reference('EST-MRT:poc-support-v1',
    'S1 eligible two-action proximal quality excursion; q=.5; participant-clustered inference')
S2_ESTIMAND = reference('EST-POLICY:poc-support-refresh-v1',
    'Working action-centered quality policy refresh, separate from WCLS inference')
IDENTITIES = {
    'N0': dict(family='nof1_med', model=reference('poc-nof1-N0-v1',
        'Canonical N model; same H*/prior/rebound as N1; current taken indicator replaces medication carryover'), prior=N_PRIOR_REF, estimand=N_ESTIMAND),
    'N1': dict(family='nof1_med', model=reference('poc-nof1-N1-v1',
        'Canonical N model; .5 medication carryover; assignment-cessation rebound retained'), prior=N_PRIOR_REF, estimand=N_ESTIMAND),
    'S1-WCLS': dict(family='support', model=reference('poc-support-wcls-design-v1',
        'Canonical S1 WCLS control/treatment design; covariance/use-t/df/minimum clusters remain unadmitted'), prior=WCLS_PRIOR_REF, estimand=S1_ESTIMAND),
    'S2-refresh': dict(family='support', model=reference('poc-support-policy-working-v1',
        'Canonical hierarchical action-centered rounded-clipped quality working model; exact centering/prediction remains unadmitted'), prior=S2_PRIOR_REF, estimand=S2_ESTIMAND),
}
EXECUTABLE_CONFIGURATIONS: frozenset[str] = frozenset()


class ProtocolRequest(StrictModel):
    schema_version: Literal['2.0.0']
    synthetic: Literal[True]
    kind: Literal['protocol_fit_request']
    purpose: Purpose
    context: MethodContext
    backend: Literal['pymc', 'statsmodels']
    sampler: Literal['native_nuts', 'not_applicable']
    precision: Literal['float64']
    configuration: VersionRef

    @model_validator(mode='after')
    def purpose_identity(self):
        expected = IDENTITIES[self.purpose]
        backend = ('statsmodels', 'not_applicable') if self.purpose == 'S1-WCLS' else ('pymc', 'native_nuts')
        if (self.backend, self.sampler) != backend:
            raise ValueError('purpose/backend/sampler mismatch')
        for field in ['model', 'prior', 'estimand']:
            if getattr(self.context, field).model_dump() != expected[field]:
                raise ValueError('purpose-bound '+field+' identity mismatch')
        if self.context.comparator_estimand != self.context.estimand:
            raise ValueError('protocol comparator must share the declared estimand')
        if self.context.protocol.model_dump() != PROTOCOL_REFS[expected['family']] or self.context.dgp.model_dump() != LAW_REF:
            raise ValueError('purpose/family protocol or observed law mismatch')
        process = 'wcls-unused-provenance' if self.purpose == 'S1-WCLS' else self.purpose+'-fit'
        if self.context.seed.namespace != 'fit' or self.context.seed.process != process:
            raise ValueError('independent purpose fit seed required; WCLS seed is unused provenance')
        if self.configuration.model_dump() != BOUNDARY_CONFIG_REF:
            raise ValueError('P1 accepts only the non-executable boundary fixture configuration')
        return self


class N0Request(ProtocolRequest):
    purpose: Literal['N0']
    backend: Literal['pymc']
    sampler: Literal['native_nuts']


class N1Request(ProtocolRequest):
    purpose: Literal['N1']
    backend: Literal['pymc']
    sampler: Literal['native_nuts']


class WCLSRequest(ProtocolRequest):
    purpose: Literal['S1-WCLS']
    backend: Literal['statsmodels']
    sampler: Literal['not_applicable']


class PolicyRequest(ProtocolRequest):
    purpose: Literal['S2-refresh']
    backend: Literal['pymc']
    sampler: Literal['native_nuts']


PurposeRequest = Annotated[N0Request | N1Request | WCLSRequest | PolicyRequest, Field(discriminator='purpose')]


class CohortMember(StrictModel):
    patient_id: Identifier
    history_sha256: Sha256


class ProtocolInput(StrictModel):
    schema_version: Literal['2.0.0']
    synthetic: Literal[True]
    kind: Literal['poc_protocol_input']
    attempt_id: Identifier
    purpose: Purpose
    family: Literal['nof1_med', 'support']
    run: VersionRef
    cutoff: AwareDatetime
    cohort: Annotated[list[CohortMember], Field(min_length=1)]
    histories: Annotated[list[ProtocolHistory], Field(min_length=1)]
    history_sha256: Sha256
    request: PurposeRequest

    @model_validator(mode='after')
    def frozen_input(self):
        expected = IDENTITIES[self.purpose]
        if self.request.purpose != self.purpose or expected['family'] != self.family:
            raise ValueError('input/request purpose/family mismatch')
        ids = [h.patient_id for h in self.histories]
        if ids != sorted(set(ids)) or len(ids) != len(self.cohort):
            raise ValueError('unique sorted protocol cohort required')
        members = [dict(patient_id=h.patient_id, history_sha256=sha(h.model_dump(mode='json'))) for h in self.histories]
        if [m.model_dump() for m in self.cohort] != members:
            raise ValueError('cohort/history identity mismatch')
        if any(h.family != self.family or h.cutoff != self.cutoff for h in self.histories):
            raise ValueError('owned common-cutoff same-family histories required')
        if self.history_sha256 != sha([h.model_dump(mode='json') for h in self.histories]):
            raise ValueError('protocol reduced-history hash mismatch')
        context = self.request.context
        if context.observation_cutoff != self.cutoff or context.scenario != self.run:
            raise ValueError('protocol request cutoff/run mismatch')
        if context.input_data.model_dump() != reference('poc-protocol-observed-input-v2', members):
            raise ValueError('request cohort input-data identity mismatch')
        if context.seed.protocol != self.histories[0].protocol.id or context.seed.scenario != self.run.id or context.seed.patient not in ids:
            raise ValueError('protocol numerical seed binding mismatch')
        return self


class NContrast(StrictModel):
    kind: Literal['expected_nof1_assignment_contrast']
    unit: Literal['quality_points']
    mean: float
    interval: Interval


class WCLSInference(StrictModel):
    kind: Literal['wcls_excursion_inference']
    unit: Literal['quality_points']
    coefficient: float
    standard_error: Annotated[float, Field(ge=0)]
    interval: Interval


class PolicyRefresh(StrictModel):
    kind: Literal['support_policy_refresh']
    unit: Literal['quality_points']
    policy: VersionRef
    fit_cutoff: AwareDatetime


class ProtocolResult(StrictModel):
    schema_version: Literal['2.0.0']
    synthetic: Literal[True]
    kind: Literal['poc_protocol_result']
    purpose: Purpose
    attempt_id: Identifier
    input_sha256: Sha256
    history_sha256: Sha256
    cohort: Annotated[list[CohortMember], Field(min_length=1)]
    cutoff: AwareDatetime
    run: VersionRef
    protocol: VersionRef
    configuration: VersionRef
    model: VersionRef
    prior: VersionRef
    estimand: VersionRef
    status: Literal['failed', 'abstained', 'completed']
    reason: Name | None
    consumed_record_ids: list[Identifier]
    diagnostics: dict
    artifacts: list[dict]
    output: NContrast | WCLSInference | PolicyRefresh | None

    @model_validator(mode='after')
    def purpose_output(self):
        identity = IDENTITIES[self.purpose]
        for field in ['model', 'prior', 'estimand']:
            if getattr(self, field).model_dump() != identity[field]:
                raise ValueError('result purpose-bound '+field+' mismatch')
        if self.protocol.model_dump() != PROTOCOL_REFS[identity['family']] or self.configuration.model_dump() != BOUNDARY_CONFIG_REF:
            raise ValueError('unadmitted protocol result identity')
        if len(set(self.consumed_record_ids)) != len(self.consumed_record_ids):
            raise ValueError('duplicate likelihood ownership')
        if self.status == 'completed' or self.output is not None or self.reason is None:
            raise ValueError('P1 boundary fixture cannot supply an accepted estimate')
        return self


def require_executable(value):
    """Shared admission veto, also applied independently by host dispatch."""
    configuration = value.request.configuration if isinstance(value, ProtocolInput) else value.configuration
    if configuration.sha256 not in EXECUTABLE_CONFIGURATIONS:
        raise ValueError('protocol configuration is not executable in P1')


def make_boundary_input(histories, purpose, attempt_id, run, seed):
    """Schema/isolation fixture from genuine owned observations; never a fit."""
    histories = sorted(histories, key=lambda h: h.patient_id)
    members = [dict(patient_id=h.patient_id, history_sha256=sha(h.model_dump(mode='json'))) for h in histories]
    identity = IDENTITIES[purpose]
    context = dict(estimand=identity['estimand'], dgp=LAW_REF, scenario=run,
        input_data=reference('poc-protocol-observed-input-v2', members), prior=identity['prior'], model=identity['model'],
        protocol=PROTOCOL_REFS[identity['family']], observation_cutoff=histories[0].cutoff.isoformat(), seed=seed,
        allowed_information='available_observed_history_only', truth_access='denied', comparator_estimand=identity['estimand'],
        comparator_information='same_permitted_history', source_ids=[LAW_REF['id']], failure_policy='retain_all_attempts_fail_or_abstain_never_fabricate')
    request = dict(schema_version='2.0.0', synthetic=True, kind='protocol_fit_request', purpose=purpose, context=context,
        backend='statsmodels' if purpose == 'S1-WCLS' else 'pymc', sampler='not_applicable' if purpose == 'S1-WCLS' else 'native_nuts',
        precision='float64', configuration=BOUNDARY_CONFIG_REF)
    return ProtocolInput.model_validate_json(canonical(dict(schema_version='2.0.0', synthetic=True, kind='poc_protocol_input',
        attempt_id=attempt_id, purpose=purpose, family=identity['family'], run=run, cutoff=histories[0].cutoff.isoformat(), cohort=members,
        histories=[h.model_dump(mode='json') for h in histories], history_sha256=sha([h.model_dump(mode='json') for h in histories]), request=request)))
