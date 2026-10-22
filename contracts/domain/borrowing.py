"""Public PA3 summary-only source contract. Replay and participant keys are absent."""
import hashlib
import json
import math
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from .common import Identifier, Sha256, StrictModel, VersionRef
from .estimands import FitRequest
from .analysis import (sha, canonical, reference, CONFIG, MODEL_REF, PRIOR_REF, AnalysisHistory,
    Effect, ESTIMAND_REF, PROTOCOL_REF, DGP_REF, SCENARIO_REF)

BRIDGE_SPEC = dict(id='poc-source-marginal-v1', version='1.0.0',
    algorithm_source_sha256='dd9138677c56b4f5a66508287a3e23916fa41272878a158b7ab4393867ac9fb2',
    rounding_source_sha256='fd0d64d7ee9e29ed3f7d24c05d4526e09cf5357ae0e96a8c577e4b09d4deab14',
    population='independent normal baseline/active beta under sampled population hyperparameters',
    adherence='iid Bernoulli; weighted adherence only Gaussian moment approximated',
    ar='exact zero-initialized innovations nights-13..42, recurrence including rho0',
    endpoint='rounded/clipped normal expectation; source-relative42 recall29..42')
BRIDGE_REF=reference('poc-source-marginal-v1',BRIDGE_SPEC)
BORROW_MODEL_REF=reference('rounded-clipped-state-space-borrow-v1',dict(local=MODEL_REF,source_marginal=BRIDGE_REF))
BORROW_PRIOR_REF=reference('poc-visit-joint-mixture-v1',dict(local=PRIOR_REF,bias_sd=.5,tau_halfnormal_scale=1,
    informative_weight=.5,weak_mean=0,weak_sd=10,normalization='full normal constants; logaddexp; one contribution per distinct source'))
TAU2_PRIOR_REF=reference('poc-visit-joint-mixture-tau2-v1',dict(primary=BORROW_PRIOR_REF,tau_halfnormal_scale=2))
NODE_HASHES={64:'07c193f1d9cfa97f56d3576503734db8807f133185a90cac05109a572cda92ba',
    128:'cb19875caa91ccb71fe82a7b5c91fbacc4e0d120093839fd35e5373206cd6188'}


def borrowing_config(identifier,order,tau,*,diagnostic=False):
    value=dict(CONFIG,id=identifier,model=BORROW_MODEL_REF,prior=TAU2_PRIOR_REF if tau==2 else BORROW_PRIOR_REF,
        source_bridge=BRIDGE_REF,quadrature_order=order,node_weight_sha256=NODE_HASHES[order],tau_prior_scale=tau,
        diagnostic_only=diagnostic,bridge_prefit_manifest_sha256='cbd93ee9da9435d5bcbf73b6615d829cc2ef8242d0365b7d6602f509e0754eac',
        bridge_postfit_seconds=900,dispatcher_seconds=7200,bridge_alpha=.01,bridge_tests=4320,
        bridge_reference_batches=8,bridge_reference_looks=[4096,8192,16384,32768,65536,131072],
        bridge_resolution_fraction=.25,bridge_absolute_error=.05,bridge_se_fraction=.1,
        reference_family='separate-q128-diagnostic' if diagnostic else 'primary-16-32-64',
        seed_recipe='poc-pa3-seeds-v1')
    return value,reference(identifier,value)


BORROW_CONFIG,BORROW_CONFIG_REF=borrowing_config('poc-visit-borrow-v1',64,1)
TAU2_CONFIG,TAU2_CONFIG_REF=borrowing_config('poc-visit-borrow-tau2-v1',64,2)
Q128_CONFIG,Q128_CONFIG_REF=borrowing_config('poc-visit-borrow-q128-check-v1',128,1,diagnostic=True)
CONFIGURATIONS={v['id']:(v,r) for v,r in [(BORROW_CONFIG,BORROW_CONFIG_REF),(TAU2_CONFIG,TAU2_CONFIG_REF),(Q128_CONFIG,Q128_CONFIG_REF)]}
APPROVED_BUNDLES={
    'source-7c97862d':'29354228baea86c3d86a75ff3f9bce357e2f3dc6797075d87c242c42d8cdefdd',
    'source-d48331f8':'04227ff1a95d69faa72b37d4025b86aa039f775fe88ec784490b1695f85bc17f',
    'source-28814e65':'a45c24f9b106e61896a146c54463a6e5334ef11d55f5cc9fbed8cd089d18f48e'}


def admitted_configuration(ref):
    pair=CONFIGURATIONS.get(ref.id)
    if pair is None or ref.model_dump()!=pair[1]:raise ValueError('unsupported borrowing configuration')
    return pair[0]


def seed_value(namespace,scenario,study,panel,patient,cutoff,purpose):
    return int.from_bytes(hashlib.sha256(canonical([namespace,scenario,study,panel,patient,cutoff,purpose]).encode()).digest()[:4],'big')


DESIGN = dict(endpoint_day=42, recall_first_night=29, recall_last_night=42,
    instrument='ISI-7-synthetic-14d-v1', unit='ISI_points', sign='escalate-minus-continue',
    assignment='random-permutation-60-per-arm-retained-at-14-28', support='fixed-no-prompt',
    baseline='untreated-nights-minus13-through0', population='shared-normal-independent-hierarchy-v1',
    source_target_assumption='common-population-adherence-process-measurement-law',
    protocol='poc-visit-retain-v1', producer='poc-pa3-study-producer-v1')


class StudySummary(StrictModel):
    schema: Literal['poc-study-summary-v1/1.0.0']
    study_id: Identifier
    dataset_id: Identifier
    synthetic: Literal[True]
    provenance: Literal['fictional-randomized-study']
    n_continue: Literal[60]
    n_escalate: Literal[60]
    d: float
    se: Annotated[float, Field(gt=0)]
    available_at: AwareDatetime
    design: dict[str, str | int]
    checksum: Sha256

    @model_validator(mode='after')
    def admitted(self):
        if not math.isfinite(self.d) or not math.isfinite(self.se) or self.design != DESIGN:
            raise ValueError('nonfinite or unsupported source summary/design')
        if self.checksum != sha(self.model_dump(mode='json', exclude={'checksum'})):
            raise ValueError('summary checksum mismatch')
        return self


class SourceBundle(StrictModel):
    schema: Literal['poc-source-bundle-v1/1.0.0']
    bundle_id: Identifier
    studies: Annotated[list[StudySummary], Field(min_length=2, max_length=2)]
    source_set_sha256: Sha256

    @model_validator(mode='after')
    def unique(self):
        if len({s.study_id for s in self.studies}) != 2 or len({s.dataset_id for s in self.studies}) != 2:
            raise ValueError('duplicate study or underlying dataset')
        if self.source_set_sha256 != sha([s.model_dump(mode='json') for s in self.studies]):
            raise ValueError('source set checksum mismatch')
        return self

    def at_cutoff(self, cutoff):
        if any(s.available_at >= cutoff for s in self.studies):
            raise ValueError('source unavailable at requested cutoff')
        return self


class NumericalSeeds(StrictModel):
    recipe: Literal['poc-pa3-seeds-v1']
    namespace: Literal['pa3-fit-20261021-v1']
    nuts: Annotated[int,Field(ge=0,le=4294967295)]
    effect_rollout: Annotated[int,Field(ge=0,le=4294967295)]
    prior_check: Annotated[int,Field(ge=0,le=4294967295)]
    bridge_reference: Annotated[int,Field(ge=0,le=4294967295)]

    @model_validator(mode='after')
    def distinct(self):
        if len({self.nuts,self.effect_rollout,self.prior_check,self.bridge_reference})!=4:
            raise ValueError('numerical seed collision')
        return self


class BorrowAnalysisInput(StrictModel):
    schema_version: Literal['1.1.0']
    synthetic: Literal[True]
    kind: Literal['poc_visit_borrow_input']
    attempt_id: Identifier
    request: FitRequest
    history: AnalysisHistory
    history_sha256: Sha256
    sources: SourceBundle
    source_set_sha256: Sha256
    numerical_seeds: NumericalSeeds

    @model_validator(mode='after')
    def frozen(self):
        config=admitted_configuration(self.request.configuration)
        ctx=self.request.context
        expected=[(ctx.estimand,ESTIMAND_REF),(ctx.comparator_estimand,ESTIMAND_REF),
            (ctx.model,BORROW_MODEL_REF),(ctx.prior,config['prior']),(ctx.protocol,PROTOCOL_REF),
            (ctx.dgp,DGP_REF),(ctx.scenario,SCENARIO_REF)]
        combined=dict(history=self.history.model_dump(mode='json'),sources=self.sources.model_dump(mode='json'))
        if any(a.model_dump()!=b for a,b in expected) or ctx.input_data.model_dump()!=reference('poc-borrow-observed-input-v1',combined):
            raise ValueError('unsupported borrowing target/prior/input identity')
        if ctx.observation_cutoff!=self.history.cutoff or self.history_sha256!=sha(combined['history']):
            raise ValueError('borrowing history hash/cutoff mismatch')
        if self.source_set_sha256!=self.sources.source_set_sha256:
            raise ValueError('source set hash mismatch')
        self.sources.at_cutoff(self.history.cutoff)
        if APPROVED_BUNDLES.get(self.sources.bundle_id)!=sha(combined['sources']):
            raise ValueError('source bundle is not an approved immutable artifact')
        if ctx.seed.namespace!='fit' or ctx.seed.patient!=self.history.patient_id or ctx.seed.replicate!=self.numerical_seeds.nuts:
            raise ValueError('independent numerical seed identity mismatch')
        if any(min(.05,.1*s.se)<.03287180487219337 for s in self.sources.studies):
            raise ValueError('source SE outside qualified bridge precision')
        return self


def make_borrow_input(history,attempt_id,sources,configuration=BORROW_CONFIG_REF):
    from .analysis import make_input
    config=CONFIGURATIONS.get(configuration['id'])
    if config is None or config[1]!=configuration:raise ValueError('unsupported borrowing intent')
    value=history.model_dump(mode='json');source=sources.model_dump(mode='json')
    day=(history.cutoff-history.origin).days
    index=int(sha(history.patient_id)[:8],16)
    seeds=dict(recipe='poc-pa3-seeds-v1',namespace='pa3-fit-20261021-v1')
    for field,purpose in [('nuts','nuts'),('effect_rollout','effect-rollout'),('prior_check','prior-check'),('bridge_reference','bridge-reference')]:
        seeds[field]=seed_value(seeds['namespace'],-1,-1,0,index,day,purpose+':'+configuration['sha256']+':'+attempt_id)
    base=make_input(history,attempt_id,seeds['nuts']).model_dump(mode='json')
    ctx=base['request']['context']
    ctx.update(model=BORROW_MODEL_REF,prior=config[0]['prior'],input_data=reference('poc-borrow-observed-input-v1',dict(history=value,sources=source)),
               source_ids=['BAYES-02','BORROW-01','EST-VISIT','POC-4',*[s.study_id for s in sources.studies]])
    ctx['seed'].update(protocol=configuration['id'],scenario=sources.bundle_id)
    base['request']['configuration']=configuration
    base.update(schema_version='1.1.0',kind='poc_visit_borrow_input',sources=source,
                source_set_sha256=sources.source_set_sha256,numerical_seeds=seeds)
    return BorrowAnalysisInput.model_validate_json(canonical(base))


class BorrowAnalysisResult(StrictModel):
    schema_version: Literal['1.1.0']
    synthetic: Literal[True]
    kind: Literal['poc_visit_borrow_result']
    attempt_id: Identifier
    input_sha256: Sha256
    history_sha256: Sha256
    source_set_sha256: Sha256
    cutoff: AwareDatetime
    configuration: VersionRef
    estimand: VersionRef
    bridge: VersionRef
    status: Literal['completed','abstained','failed']
    reason: str | None
    effect: Effect | None
    diagnostics: dict
    artifacts: list[dict]
    limitations: list[str]

    @model_validator(mode='after')
    def accepted(self):
        admitted_configuration(self.configuration)
        if self.estimand.model_dump()!=ESTIMAND_REF or self.bridge.model_dump()!=BRIDGE_REF:
            raise ValueError('borrowing result target/bridge mismatch')
        if (self.status=='completed')!=(self.effect is not None) or (self.status=='completed')!=(self.reason is None):
            raise ValueError('failed/abstained borrowing result cannot expose accepted interval')
        canonical(self.model_dump(mode='json'))
        return self


def parse_input(raw):
    from .analysis import AnalysisInput
    value=json.loads(raw)
    return (BorrowAnalysisInput if value.get('kind')=='poc_visit_borrow_input' else AnalysisInput).model_validate_json(raw)


def parse_result(raw):
    from .analysis import AnalysisResult
    value=json.loads(raw)
    return (BorrowAnalysisResult if value.get('kind')=='poc_visit_borrow_result' else AnalysisResult).model_validate_json(raw)
