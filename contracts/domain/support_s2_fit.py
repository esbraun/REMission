"""S2 canonical fit definitions and scalar export custody; no activation/API.

Ownership/projection assertions originate at the trusted export boundary. This
contract checks their exact identities; it cannot independently query a Store.
Prediction-context descriptors retain their existing, distinct identities.
"""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from .analysis import reference, sha
from .common import Identifier, Sha256, StrictModel, VersionRef
from .protocol import LAW_REF, SUPPORT_REF
from .protocol_analysis import ReducedRef
from .support_s2 import DEFINITIONS as PREDICTION_DEFINITIONS, HSTAR_REF

MODEL = dict(id='poc-support-policy-working-v2',version='2.0.0',
    eta="alpha_i+x_it'b+(A_it-p_it)*tau_i+e_it",
    alpha='mu_alpha+s_alpha*z_i',tau='mu_tau+s_tau*u_i',
    features=PREDICTION_DEFINITIONS['features'],batch=PREDICTION_DEFINITIONS['batch'],
    initial='e_i0=0 at public support activation',
    latent='e_it=rho*e_i,t-1+s_e*epsilon_it on every latent support night',
    quality='Q(eta_it+s_Q*noise); Q(y)=round(clip(y,0,10),.001); ties-to-even',
    conditioning='unique resolved observed public rewards only; persisted final A,p and original predecision x',
    refresh='cumulative original prior at T=14,28,42,56,70,84; never previous posterior plus old likelihood',
    saved_joint=['alpha','tau','b','rho','s_e','s_Q','e_T'],
    prediction_descriptor=PREDICTION_DEFINITIONS['model'])
PRIOR = dict(id='poc-support-policy-prior-v2',version='2.0.0',
    mu_alpha='Normal(5,3)',mu_tau='Normal(0,2)',b='four independent Normal(0,2)',
    s_alpha='HalfNormal(2)',s_tau='HalfNormal(2)',s_e='HalfNormal(2)',s_Q='HalfNormal(2)',
    rho='Uniform(-.95,.95)',z='independent standard Normal per member',
    u='independent standard Normal per member',epsilon='independent standard Normal per member/night',
    independence='all displayed priors independent except deterministic hierarchy',
    prediction_descriptor=PREDICTION_DEFINITIONS['prior'])
MODEL_REF=reference(MODEL['id'],MODEL)|dict(version=MODEL['version'])
PRIOR_REF=reference(PRIOR['id'],PRIOR)|dict(version=PRIOR['version'])
DEFINITIONS=dict(model=MODEL_REF,prior=PRIOR_REF,features=PREDICTION_DEFINITIONS['features'],batch=PREDICTION_DEFINITIONS['batch'])
CONFIG=dict(id='poc-support-fit-source-v2',version='2.0.0',purpose='EST-POLICY:poc-support-refresh-v1',
    definitions=DEFINITIONS,executable=False,serving_authority=False)
CONFIG_REF=reference(CONFIG['id'],CONFIG)|dict(version=CONFIG['version'])


class FitMember(StrictModel):
    patient_id: Identifier
    patient_version: Annotated[int,Field(ge=1)]
    history_sha256: Sha256
    revisions_sha256: Sha256
    source_projection_sha256: Sha256
    activation_ref: ReducedRef


class S2FitProvenance(StrictModel):
    schema_version: Literal['s2-fit-source-1.0.0']
    purpose: Literal['EST-POLICY:poc-support-refresh-v1']
    synthetic: Literal[True]
    owner_id: Identifier
    store_id: Identifier
    generation_id: Identifier
    cohort_id: Identifier
    export_id: Identifier
    source_commit: Annotated[str,Field(pattern=r'^[a-f0-9]{40}$')]
    target_id: Identifier
    origin: AwareDatetime
    cutoff: AwareDatetime
    cutoff_day: Literal[14,28,42,56,70,84]
    members: Annotated[tuple[FitMember,...],Field(min_length=12,max_length=12)]
    histories_sha256: Sha256
    membership_sha256: Sha256
    law: VersionRef
    protocol: VersionRef
    hstar: VersionRef
    configuration: VersionRef
    definitions: dict[str,VersionRef]
    serving_authority: Literal[False]

    @model_validator(mode='after')
    def frozen(self):
        ids=[m.patient_id for m in self.members]
        if ids!=sorted(set(ids)) or self.target_id not in ids:
            raise ValueError('complete ordered unique12 and explicit target required')
        if self.membership_sha256!=sha([m.model_dump(mode='json') for m in self.members]):
            raise ValueError('frozen membership digest mismatch')
        if (self.cutoff-self.origin).total_seconds()!=self.cutoff_day*86400:
            raise ValueError('common public origin/cutoff mismatch')
        if self.law.model_dump()!=LAW_REF or self.protocol.model_dump()!=SUPPORT_REF or self.hstar.model_dump()!=HSTAR_REF:
            raise ValueError('unadmitted observed law/protocol/H*')
        if (self.configuration.model_dump()!=CONFIG_REF
                or {k:v.model_dump() for k,v in self.definitions.items()}!=DEFINITIONS):
            raise ValueError('unadmitted canonical S2 fit definitions')
        return self
