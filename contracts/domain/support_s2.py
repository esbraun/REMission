"""Scalar S2 candidate boundaries. No executable dispatch or serving authority.

The joint arrays and numerical libraries live in methods.support.s2_prediction.
References describe the accepted method, not evidence of its qualification.
"""
from typing import Annotated, Literal

from pydantic import Field, model_validator
from .analysis import reference
from .common import Identifier, Sha256, StrictModel, VersionRef

MODEL = dict(id='poc-support-s2-joint-ar-v1', version='1.0.0',
    mean='alpha_i+x_current@b+(a-.5)*tau_i+rho**h*e_iT',
    variance='s_Q**2+s_e**2*sum(rho**(2*j),j=0..h-1)',
    observation='round(clip(quality,0,10),.001); ties-to-even',
    fit='one observed-only joint12 hierarchy; original prior at each cumulative cutoff',
    initial_state='e_i0=0; latent AR states across missing reward nights')
PRIOR = dict(id='poc-support-s2-prior-v1', version='1.0.0',
    mu_alpha='Normal(5,3)', mu_tau='Normal(0,2)', b='four independent Normal(0,2)',
    s_alpha='HalfNormal(2)', s_tau='HalfNormal(2)', s_e='HalfNormal(2)',
    s_Q='HalfNormal(2)', rho='Uniform(-.95,.95)',
    alpha='mu_alpha+s_alpha*z_i; z_i~Normal(0,1)',
    tau='mu_tau+s_tau*u_i; u_i~Normal(0,1)')
FEATURES = dict(id='poc-support-s2-features-v1', version='1.0.0',
    ordered=['prior_available_quality_default7', 'no_prior_available_quality',
             'previous_six_nights_delivered_prompts', 'reward_night/84'],
    original_probability='persisted predecision p; never substituted .5 in likelihood',
    prediction_probability=.5, intercept='separate alpha_i',
    outcome='completed available quality only; original unique resolved revisions',
    current='predecision plug-in x; no posterior/e_iT filtering after fit')
BATCH = dict(id='poc-support-s2-batches-v1', version='1.0.0',
    cutoffs=[14,28,42,56,70,84], chains=4, tune=1000, draws=1000,
    extension_tune=2000, extension_draws=2000, cohort_members=12,
    decision='T..T+13', h='d+1-T', expiry='before decision T+14',
    last_reward=84, frozen='all member H*/revisions/e_iT/action missing counts at T')
SELECTOR = dict(id='poc-support-s2-selector-v1', version='1.0.0',
    deltas=[-.5,0.,.5], blend='(1-r_a)*m_a+r_a*clip(m_a+delta_a,0,10)',
    primary='joint target tau sign for positive common variance; exact Q for zero',
    ties=.5, unready=.5, probability='mean Z; no sampled noisy outcome win',
    allocation='eligible set then .1-.9 clipping then normalize then one keyed draw')
NUMERICS = dict(id='poc-support-s2-numerics-candidate-v1', version='1.0.0',
    reference='unchanged methods.nof1.observation.expected_quality 10000-CDF sum',
    means=[-40.,50.], positive_sd=[1e-6,40.], zero_sd='exact separate Q branch',
    epsilon_quality=1e-8, action_comparison=1e-9, reference_convergence=1e-10,
    sensitivity_allowance=2e-8, qualification='finite empirical; not uniform enclosure',
    unresolved='any required draw makes complete context numerical_unready',
    precision=dict(rhat_exclusive=1.01, ess_bulk_min=400., ess_tail_min=400.,
                   mcse_exclusive_zero=True, mcse_max=.02, half_full_max=.02,
                   guard='p +/- 2*MCSE strictly one side .5',
                   constant_chain='any chain with fewer than two distinct Z values unready',
                   reuse='exact ordered indicator array equality only'))
DEFINITIONS = {name: reference(value['id'], value) for name,value in
    [('model',MODEL),('prior',PRIOR),('features',FEATURES),('batch',BATCH),
     ('selector',SELECTOR),('numerics',NUMERICS)]}
CONFIG = dict(id='poc-support-s2-source-candidate-v1', version='1.0.0',
              definitions=DEFINITIONS, executable=False, serving_authority=False)
CONFIG_REF = reference(CONFIG['id'],CONFIG)
HSTAR_REF = reference('poc-support-s2-hstar-v1',
    'ProtocolHistory support; complete owned ordered12; unique resolved observed revisions as of T; no private truth')
CELLS = tuple((a,b) for a in (-.5,0.,.5) for b in (-.5,0.,.5))


class FrozenMember(StrictModel):
    patient_id: Identifier
    patient_version: Annotated[int,Field(ge=1)]
    history_sha256: Sha256
    revisions_sha256: Sha256
    observed: tuple[Annotated[int,Field(ge=0)],Annotated[int,Field(ge=0)]]
    missing: tuple[Annotated[int,Field(ge=0)],Annotated[int,Field(ge=0)]]


class S2Request(StrictModel):
    schema_version: Literal['s2-prediction-candidate-1.0.0']
    owner_id: Identifier
    store_id: Identifier
    generation_id: Identifier
    cohort_id: Identifier
    fit_id: Identifier
    fit_artifact_sha256: Sha256
    fitted_hstar: VersionRef
    fitted_snapshot_sha256: Sha256
    configuration: VersionRef
    definitions: dict[str,VersionRef]
    members: Annotated[tuple[FrozenMember,...],Field(min_length=12,max_length=12)]
    cutoff: Literal[14,28,42,56,70,84]
    target_id: Identifier
    context_id: Identifier
    context_version: Annotated[int,Field(ge=1)]
    current_snapshot_sha256: Sha256
    decision_day: Annotated[int,Field(ge=14,le=83)]
    reward_day: Annotated[int,Field(ge=15,le=84)]
    h: Annotated[int,Field(ge=1,le=14)]
    expires_before_decision: Annotated[int,Field(ge=28,le=98)]
    x_current: tuple[float,float,float,float]

    @model_validator(mode='after')
    def identity(self):
        if self.configuration.model_dump()!=CONFIG_REF or {
                k:v.model_dump() for k,v in self.definitions.items()}!=DEFINITIONS:
            raise ValueError('unadmitted S2 definitions')
        if self.fitted_hstar.model_dump()!=HSTAR_REF:raise ValueError('unadmitted S2 H*')
        ids=[m.patient_id for m in self.members]
        if ids!=sorted(set(ids)) or self.target_id not in ids:
            raise ValueError('ordered unique complete cohort and explicit target required')
        if any(sum(m.observed)+sum(m.missing)>self.cutoff for m in self.members):
            raise ValueError('frozen opportunity counts exceed fitted cutoff')
        if (not self.cutoff<=self.decision_day<self.cutoff+14
                or self.reward_day!=self.decision_day+1 or self.h!=self.reward_day-self.cutoff
                or self.expires_before_decision!=self.cutoff+14):
            raise ValueError('S2 cutoff/horizon/expiry mismatch')
        quality,missing,delivered,night=self.x_current
        if not (0<=quality<=10 and missing in (0.,1.) and 0<=delivered<=6
                and delivered.is_integer() and night==self.reward_day/84
                and (missing==0. or quality==7.)):
            raise ValueError('invalid predecision feature snapshot')
        return self


class PrecisionSummary(StrictModel):
    probability: Annotated[float,Field(ge=0,le=1)]
    rhat: float | None
    ess_bulk: float | None
    ess_tail: float | None
    mcse: float | None
    half_probability: Annotated[float,Field(ge=0,le=1)]
    constant_chain: bool
    status: Literal['candidate_ready','probability_unready_constant_chain','probability_unready']

    @model_validator(mode='after')
    def consistent_gate(self):
        if self.status!=precision_status(self.probability,self.half_probability,
                self.constant_chain,self.rhat,self.ess_bulk,self.ess_tail,self.mcse):
            raise ValueError('S2 precision status differs from scalar gate')
        return self


def precision_status(probability,half_probability,constant_chain,rhat,ess_bulk,ess_tail,mcse):
    """Scalar gate shared with validation; no numerical runtime or IID substitute."""
    import math
    if constant_chain:return 'probability_unready_constant_chain'
    values=(probability,half_probability,rhat,ess_bulk,ess_tail,mcse)
    if any(type(v) not in (float,int) or not math.isfinite(v) for v in values):
        return 'probability_unready'
    if not (0<=probability<=1 and 0<=half_probability<=1 and 0<rhat<1.01
            and ess_bulk>=400 and ess_tail>=400 and 0<mcse<=.02
            and abs(probability-half_probability)<=.02):return 'probability_unready'
    if not (probability-2*mcse>.5 or probability+2*mcse<.5):return 'probability_unready'
    return 'candidate_ready'


class CellSummary(StrictModel):
    delta0: Literal[-.5,0.,.5]
    delta1: Literal[-.5,0.,.5]
    precision: PrecisionSummary | None


class S2Result(StrictModel):
    schema_version: Literal['s2-prediction-candidate-1.0.0']
    request_sha256: Sha256
    target_id: Identifier
    context_id: Identifier
    context_version: Annotated[int,Field(ge=1)]
    status: Literal['candidate_ready','numerical_unready','probability_unready','arm_unavailable']
    reason: str
    primary: PrecisionSummary | None
    cells: Annotated[tuple[CellSummary,...],Field(min_length=9,max_length=9)]
    probability: Annotated[float,Field(ge=0,le=1)]
    serving_authority: Literal[False]
    empirical_domain_only: Literal[True]

    @model_validator(mode='after')
    def retained_cells(self):
        if tuple((v.delta0,v.delta1) for v in self.cells)!=CELLS:
            raise ValueError('all nine ordered cell identities required')
        if self.status=='candidate_ready':
            summaries=[self.primary]+[v.precision for v in self.cells]
            if any(v is None or v.status!='candidate_ready' for v in summaries):
                raise ValueError('candidate ready requires every precision gate')
            side=self.primary.probability>.5
            if any((v.probability>.5)!=side for v in summaries):
                raise ValueError('sensitivity reversal')
            if self.probability!=self.primary.probability:raise ValueError('primary probability mismatch')
        elif self.probability!=.5:raise ValueError('unready probability must be .5')
        return self
