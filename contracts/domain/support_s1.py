"""One executable historical S1 application product; schema2 remains closed.

Only scalar admission lives here. Numerical libraries belong to the file worker.
"""
from typing import Annotated, Literal
import math
from datetime import datetime

from pydantic import AwareDatetime, Field, model_validator
from .analysis import reference, sha
from .common import Identifier, Sha256, StrictModel, VersionRef
from .protocol import LAW_REF, SUPPORT_REF
from .protocol_analysis import ProtocolHistory
from .protocol_request import S1_ESTIMAND, WCLS_PRIOR_REF

# Frozen copy of the accepted offline settings, checked against the source AST.
OFFLINE_SETTINGS = dict(id='poc-support-s1-offline-r1', version='1.0.0', q=.5,
    controls=['intercept', 'prior_available_quality_default7', 'no_prior_available_quality',
              'previous_six_nights_delivered_prompts', 'night/84'], effect='A-.5',
    reporting='complete-observed-reward; independent MCAR .1', min_clusters=8,
    columns=6, weighted_rank='max(N,K)*float64_epsilon*s_max',
    covariance=dict(type='cluster', use_correction=True, df_correction=True, use_t=True),
    interval='beta +/- t(.975,G-1)*SE', missing_rate=.1, deltas=[-.5, 0., .5],
    baseline='clip(controls@gamma+(a-.5)*beta,0,10)',
    sensitivity='beta + mean_context(.1*(d1-d0)); equal decision weights; point estimates only',
    statsmodels='0.15.0', precision='float64', production_activation=False)
OFFLINE_REF = reference(OFFLINE_SETTINGS['id'], OFFLINE_SETTINGS)
CONFIG = dict(id='poc-support-s1-app-v1', version='1.0.0', executable=True,
    offline=OFFLINE_REF, purpose='owned-admitted-historical-S1-cohort', precision='float64')
CONFIG_REF = reference(CONFIG['id'], CONFIG)
MODEL_REF = reference('poc-support-s1-app-wcls-v1', dict(settings=OFFLINE_REF,
    design='six columns; no dropped columns', covariance='participant cluster corrected use_t G-1',
    sensitivity='nine R1 clipped point cells; no sensitivity interval'))


class S1Submission(StrictModel):
    archive_id: Identifier
    mode: Literal['S1']
    cutoff_day: Literal[14, 42, 84]
    configuration: VersionRef
    previous_attempt: Identifier | None = None

    @model_validator(mode='after')
    def identity(self):
        if self.configuration.model_dump() != CONFIG_REF:
            raise ValueError('unadmitted S1 application configuration')
        return self


class S1Member(StrictModel):
    patient_id: Identifier
    patient_version: Annotated[int, Field(ge=1)]
    partition_id: Identifier
    projection_sha256: Sha256
    history_sha256: Sha256


class S1Archive(StrictModel):
    owner_id: Identifier
    archive_id: Identifier
    run_id: Identifier
    cohort_id: Identifier
    manifest_sha256: Sha256
    admission_sha256: Sha256
    source_commit: Annotated[str, Field(pattern='^[a-f0-9]{40}$')]
    producer_runtime: dict
    producer_qualification: dict
    outcome_qualification: dict


class S1Input(StrictModel):
    schema_version: Literal['3.0.0']
    synthetic: Literal[True]
    kind: Literal['poc_support_s1_input']
    purpose: Literal['S1-WCLS']
    attempt_id: Identifier
    archive: S1Archive
    mode: Literal['S1']
    cutoff_day: Literal[14, 42, 84]
    cutoff: AwareDatetime
    cohort: Annotated[list[S1Member], Field(min_length=12, max_length=12)]
    histories: Annotated[list[ProtocolHistory], Field(min_length=12, max_length=12)]
    history_sha256: Sha256
    configuration: VersionRef
    model: VersionRef
    prior: VersionRef
    estimand: VersionRef
    law: VersionRef
    protocol: VersionRef
    provenance_seed: str

    @model_validator(mode='after')
    def frozen(self):
        require_executable(self)
        for key, expected in dict(model=MODEL_REF, prior=WCLS_PRIOR_REF,
                estimand=S1_ESTIMAND, law=LAW_REF, protocol=SUPPORT_REF).items():
            if getattr(self,key).model_dump()!=expected:raise ValueError('S1 '+key+' mismatch')
        ids=[h.patient_id for h in self.histories]
        if ids!=sorted(set(ids)) or ids!=[m.patient_id for m in self.cohort]:
            raise ValueError('canonical twelve-member S1 roster required')
        if len({m.partition_id for m in self.cohort})!=12:
            raise ValueError('unique S1 partitions required')
        for member,h in zip(self.cohort,self.histories):
            if (h.family!='support' or h.protocol!=self.protocol or h.cutoff!=self.cutoff
                    or (h.cutoff-h.origin).total_seconds()!=self.cutoff_day*86400
                    or sha(h.model_dump(mode='json'))!=member.history_sha256
                    or any(r.mode!='mrt' for r in h.records if r.kind=='support_decision')):
                raise ValueError('same-cutoff canonical S1 member history required')
        if self.history_sha256!=sha([h.model_dump(mode='json') for h in self.histories]):
            raise ValueError('S1 Hstar hash mismatch')
        if not self.provenance_seed.startswith('fit/wcls-unused-provenance/'):
            raise ValueError('S1 unused fit provenance namespace required')
        consumed_ids(self)  # No ambiguity across member likelihood ownership.
        return self


class S1Estimate(StrictModel):
    kind: Literal['wcls_excursion_inference']
    unit: Literal['quality_points']
    coefficient: float
    standard_error: Annotated[float, Field(gt=0)]
    interval: tuple[float, float]
    df: Annotated[int, Field(ge=7)]

    @model_validator(mode='after')
    def interval_order(self):
        if not self.interval[0]<=self.coefficient<=self.interval[1]:
            raise ValueError('invalid WCLS interval')
        return self


class S1Result(StrictModel):
    schema_version: Literal['3.0.0']
    synthetic: Literal[True]
    kind: Literal['poc_support_s1_result']
    purpose: Literal['S1-WCLS']
    attempt_id: Identifier
    input_sha256: Sha256
    history_sha256: Sha256
    feature_history_sha256: Sha256 | None
    archive: S1Archive
    cohort: Annotated[list[S1Member], Field(min_length=12,max_length=12)]
    cutoff: AwareDatetime
    configuration: VersionRef
    model: VersionRef
    prior: VersionRef
    estimand: VersionRef
    protocol: VersionRef
    status: Literal['completed','abstained','failed']
    reason: str | None
    consumed_record_ids: list[Identifier]
    generated_at: AwareDatetime
    diagnostics: dict
    artifacts: list[dict]
    output: S1Estimate | None
    limitations: list[str]

    @model_validator(mode='after')
    def accepted(self):
        require_executable(self)
        for key, expected in dict(model=MODEL_REF,prior=WCLS_PRIOR_REF,
                estimand=S1_ESTIMAND,protocol=SUPPORT_REF).items():
            if getattr(self,key).model_dump()!=expected:raise ValueError('S1 result '+key+' mismatch')
        if (self.status=='completed')!=(self.output is not None) or (self.status=='completed')!=(self.reason is None):
            raise ValueError('only estimated WCLS exposes interval')
        if self.consumed_record_ids!=sorted(set(self.consumed_record_ids)):
            raise ValueError('unique sorted consumed S1 IDs required')
        if self.status=='completed':validate_summary(self)
        return self


def require_executable(value):
    if type(value) not in (S1Input,S1Result) or value.configuration.model_dump()!=CONFIG_REF:
        raise ValueError('unadmitted S1 application product')


def consumed_ids(product):
    # build_features parses and validates every active record, even excluded rows.
    ids=[r.record_id for h in product.histories for r in h.records]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate cross-member record ownership')
    return sorted(ids)


def feature_history_sha(product):
    """Exact scalar identity used by build_features, distinct from full H*."""
    return sha([dict(patient_id=h.patient_id,origin=h.origin.isoformat(),
        records=[r.model_dump(mode='json') for r in sorted(h.records,key=lambda r:r.record_id)])
        for h in sorted(product.histories,key=lambda h:h.patient_id)])


def validate_summary(result):
    d=result.diagnostics;w=d.get('wcls',{});counts=w.get('counts',{})
    identity=w.get('identity',{})
    if (w.get('status')!='estimated' or identity.get('configuration')!=OFFLINE_REF
            or identity.get('settings_sha256')!=sha(OFFLINE_SETTINGS)
            or identity.get('package_versions',{}).get('statsmodels')!='0.15.0'
            or identity.get('expected_public_law')!=LAW_REF or identity.get('expected_protocol')!=SUPPORT_REF
            or identity.get('estimand')!=S1_ESTIMAND or identity.get('prior')!=WCLS_PRIOR_REF
            or identity.get('seed_used') is not False
            or w.get('identity',{}).get('history_sha256')!=result.feature_history_sha256
            or counts.get('participants',0)<8 or counts.get('participants',0)>12
            or counts.get('observed',0)<=6 or w.get('df')!=counts['participants']-1
            or w.get('df')!=result.output.df or len(w.get('coefficients',[]))!=6
            or len(w.get('covariance',[]))!=6 or len(w.get('singular_values',[]))!=6
            or d.get('weighted_rank')!=6):
        raise ValueError('S1 WCLS inference gates missing')
    coefficients=w['coefficients'];cov=w['covariance'];singular=w['singular_values']
    values=coefficients+singular+[w.get('condition_number')]
    if any(len(r)!=6 for r in cov):raise ValueError('full WCLS covariance required')
    values += [v for row in cov for v in row]
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('finite WCLS diagnostics required')
    if min(singular)<=max(counts['observed'],6)*2.220446049250313e-16*max(singular):
        raise ValueError('full weighted rank required')
    if (counts.get('missing',-1)<0 or counts.get('eligible_completed')!=counts['observed']+counts['missing']
            or any(not math.isclose(cov[i][j],cov[j][i],rel_tol=1e-12,abs_tol=1e-14) for i in range(6) for j in range(6))):
        raise ValueError('WCLS count/covariance symmetry mismatch')
    output=result.output
    if (coefficients[-1]!=output.coefficient or w.get('estimate')!=output.coefficient
            or w.get('standard_error')!=output.standard_error
            or w.get('interval')!=list(output.interval)
            or not math.isclose(cov[-1][-1],output.standard_error**2,rel_tol=1e-12,abs_tol=1e-14)):
        raise ValueError('WCLS summary/coefficient/covariance mismatch')
    cells=w.get('sensitivity',[])
    if w.get('sensitivity_status')=='available':
        if (len(cells)!=9 or {(c['delta0'],c['delta1']) for c in cells}!=
                {(a,b) for a in (-.5,0.,.5) for b in (-.5,0.,.5)} or w.get('sensitivity_reason') is not None):
            raise ValueError('nine R1 point sensitivity cells required')
        if any(not all(type(c.get(k)) in (int,float) and math.isfinite(c[k]) for k in ('estimate','shift'))
                or not math.isclose(c['estimate'],output.coefficient+c['shift'],rel_tol=1e-12,abs_tol=1e-14)
                for c in cells):raise ValueError('finite coherent R1 point cells required')
    elif w.get('sensitivity_status')!='unavailable' or not w.get('sensitivity_reason') or cells:
        raise ValueError('missing sensitivity must be withheld explicitly')


def execution_binding(product,origin):
    from .borrow_runtime import runtime_origin
    runtime_origin(origin['learner_image'],origin['source_commit'])
    return dict(kind='support-s1-host-binding-v1',input_sha256=sha(product.model_dump(mode='json')),
        configuration=CONFIG_REF,**origin)


def validate_result(result,product,trusted):
    require_executable(product)
    if (result.attempt_id!=product.attempt_id or result.input_sha256!=sha(product.model_dump(mode='json'))
            or result.history_sha256!=product.history_sha256 or result.archive!=product.archive
            or result.cohort!=product.cohort or result.cutoff!=product.cutoff
            or result.consumed_record_ids!=consumed_ids(product)):
        raise ValueError('frozen S1 result input/archive/roster/consumed identity mismatch')
    execution=result.diagnostics.get('execution')
    if not trusted or execution!=trusted or execution_binding(product,
            {k:trusted[k] for k in ('learner_image','source_commit')})!=trusted:
        raise ValueError('S1 trusted host launch mismatch')
    if result.status=='completed' and result.feature_history_sha256 is None:
        raise ValueError('S1 feature identity required')
    if result.feature_history_sha256 is not None and result.feature_history_sha256!=feature_history_sha(product):
        raise ValueError('S1 feature adapter history identity mismatch')
    if result.status=='completed':
        w=result.diagnostics['wcls'];identity=w['identity']
        if identity.get('seed')!=product.provenance_seed:
            raise ValueError('S1 fit provenance mismatch')
        if datetime.fromisoformat(identity['observation_cutoff'])!=product.cutoff:
            raise ValueError('S1 inference cutoff mismatch')
        records={r.record_id:r for h in product.histories for r in h.records}
        selected=result.diagnostics.get('decision_ids',[])
        observed=set();missing=set()
        for r in records.values():
            if (r.kind=='support_decision' and r.mode=='mrt' and r.availability=='randomized'
                    and r.outcome_window.assessment_at<product.cutoff):
                outcome=records[r.outcome_link_id]
                if outcome.reward.status=='observed':observed.add(r.record_id)
                elif outcome.reward.status=='missing':missing.add(r.record_id)
        if (selected!=sorted(set(selected)) or not observed<=set(selected)<=observed|missing
                or (w['counts']['eligible_counts_complete'] and set(selected)!=observed|missing)
                or w['counts']['observed']!=len(observed) or w['counts']['eligible_completed']!=len(selected)
                or w['counts']['participants']!=len({records[k].patient_id for k in observed})):
            raise ValueError('S1 consumed completed decision/count identity mismatch')
        source_ids=result.diagnostics.get('feature_source_ids',[])
        if source_ids!=sorted(set(source_ids)) or not set(source_ids)<=set(records):
            raise ValueError('S1 feature source IDs outside frozen input')
    timings=result.diagnostics.get('timings',{})
    required=('import_seconds','feature_seconds','estimator_seconds','worker_seconds') if result.status!='failed' else ('worker_seconds',)
    if any(type(timings.get(k)) not in (int,float) or not math.isfinite(timings[k]) or timings[k]<0 for k in required):
        raise ValueError('S1 measured worker timings required')
