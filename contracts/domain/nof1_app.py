"""Distinct schema4 N application contract; scalar validation only.

The schema2 fixtures and inactive scientific proposal remain unchanged. Runtime
operations still require a separately reviewed immutable source/image binding.
"""
from datetime import timedelta
import math
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .analysis import canonical, reference, sha
from .common import Identifier, Sha256, StrictModel, VersionRef
from .estimands import MethodContext
from .nof1_config import (ARTIFACT_REF, CONFIG_REFS as PROPOSAL_REFS,
    DIAGNOSTIC_REF, MODEL_REFS, PRIOR_REF, configuration as proposal)
from .protocol import LAW_REF, NOF1_REF
from .protocol_analysis import ProtocolHistory
from .protocol_request import N_ESTIMAND

Purpose = Literal['N0', 'N1']
CONFIGS = {p: dict(id='poc-nof1-app-'+p+'-v1', version='1.0.0', executable=True,
    purpose=p, scientific_proposal=PROPOSAL_REFS[p], settings=proposal(p),
    artifact_schema=ARTIFACT_REF, diagnostic_schema=DIAGNOSTIC_REF,
    admission='schema4-explicit-owned-target-cohort-v1') for p in ('N0', 'N1')}
CONFIG_REFS = {p: reference(c['id'], c) for p,c in CONFIGS.items()}
MONITORED = ('mu_b','sd_b','b','population_amplitude','sd_amplitude',
    'patient_amplitude','a','rho','sigma_e','sigma_isi','sigma_quality',
    'current_error','p_C','p_M','q')
ARTIFACT_NAMES = frozenset(('posterior.nc','expected-contrast.npz','predictive.npz',
    'ownership.json','diagnostics.json'))
LIMITATIONS = [
    'Synthetic fixed kinetics; unblinded randomized blocks and restricted observed history.',
    'Limited arm information and prior sensitivity may leave wide intervals.',
    'Expected next-seven-night quality assigned MED_A minus MED_B; predictive trajectories are separate.',
    'Saved analysis is read-only and grants no treatment approval or clinical superiority.']


class NSubmission(StrictModel):
    purpose: Purpose
    target_id: Identifier
    cohort_id: Identifier
    patient_versions: dict[Identifier, Annotated[int, Field(ge=1)]]
    cutoff: AwareDatetime
    configuration: VersionRef
    previous_attempt: Identifier | None = None

    @model_validator(mode='after')
    def declared(self):
        if (not self.patient_versions or self.target_id not in self.patient_versions
                or self.configuration.model_dump()!=CONFIG_REFS[self.purpose]):
            raise ValueError('explicit N target, nonempty declared cohort and admitted configuration required')
        return self


class NMember(StrictModel):
    patient_id: Identifier
    patient_version: Annotated[int, Field(ge=1)]
    history_sha256: Sha256
    provenance_sha256: Sha256


class NRequest(StrictModel):
    schema_version: Literal['4.0.0']
    synthetic: Literal[True]
    kind: Literal['nof1_fit_request']
    purpose: Purpose
    context: MethodContext
    backend: Literal['pymc']
    sampler: Literal['native_nuts']
    precision: Literal['float64']
    configuration: VersionRef

    @model_validator(mode='after')
    def identity(self):
        expected=dict(model=MODEL_REFS[self.purpose],prior=PRIOR_REF,
            estimand=N_ESTIMAND,comparator_estimand=N_ESTIMAND,protocol=NOF1_REF,dgp=LAW_REF)
        if (self.configuration.model_dump()!=CONFIG_REFS[self.purpose]
                or any(getattr(self.context,k).model_dump()!=v for k,v in expected.items())
                or self.context.seed.namespace!='fit'
                or self.context.seed.process!=self.purpose+'-fit'):
            raise ValueError('N purpose/scientific configuration/independent fit seed mismatch')
        return self


def _day(at, origin):
    value=(at-origin).total_seconds()/86400
    if value!=int(value):raise ValueError('N public noon grid required')
    return int(value)


def readiness(histories, target_id):
    """Check observed design without importing the scientific worker.

    The worker independently revalidates through methods.nof1.data.prepare.
    Pending quality is retained but never classified as resolved missingness.
    """
    reviews=[];arms={}
    for h in histories:
        records=h.records;active={r.record_id:r for r in records}
        snapshots=[r for r in records if r.kind=='protocol_snapshot']
        if len(snapshots)!=1:raise ValueError('one uninterrupted N snapshot required')
        snapshot=snapshots[0];start=_day(snapshot.activation_at,h.origin)
        review=_day(h.cutoff,h.origin)-start;reviews.append(review)
        if start<0 or start+72>84:raise ValueError('N activation must leave72 nights inside84')
        if any(r.kind=='intercurrent_event' for r in records):raise ValueError('interrupted N history')
        for r in records:
            if r.kind=='consent' and r.component=='nof1' and (
                    r.consent_status!='active' or r.oversight_status!='approved_synthetic'
                    or r.withdrawn_at is not None or (r.expires_at is not None and r.expires_at<=h.cutoff)):
                raise ValueError('uninterrupted active N consent required')
            if r.kind=='decision_snapshot' and (r.workflow.clinical=='clinical_hold' or r.workflow.hold_reasons):
                raise ValueError('held N history')
            if r.kind=='support_decision' and r.probabilities.get('support_prompt',0)!=0:
                raise ValueError('frozen no-prompt N support required')
        assignments=[r for r in records if r.kind=='assignment']
        if any(r.option not in ('behavioral_continue','MED_A','MED_B','no_prompt')
                or r.clinician_override is not None or r.override_reason is not None for r in assignments):
            raise ValueError('unsupported or overridden N assignment')
        background=sorted((r for r in assignments if r.option=='behavioral_continue'),key=lambda r:r.event_at)
        frozen=active.get(snapshot.background_ref.record_id)
        if (not background or frozen!=background[-1] or frozen.experimental
                or any(r.experimental or r.component is not None or r.event_at>snapshot.activation_at for r in background)):
            raise ValueError('unchanged ordinary continuation background required')
        if not snapshot.support_refs:raise ValueError('explicit frozen no-prompt evidence required')
        for ref in snapshot.support_refs:
            support=active[ref.record_id]
            if ((support.kind=='assignment' and support.option!='no_prompt')
                    or (support.kind=='support_decision' and support.probabilities.get('support_prompt',0)!=0)):
                raise ValueError('frozen no-prompt evidence mismatch')
        medication=sorted((r for r in assignments if r.option in ('MED_A','MED_B')),key=lambda r:r.event_at)
        expected=[h.origin+timedelta(days=start+offset) for offset in range(0,max(review,0),9)]
        if [r.event_at for r in medication]!=expected:raise ValueError('complete unique N blocks required')
        approvals={r.record_id for r in snapshot.approval_refs}
        if any(not r.experimental or r.component!='nof1' or r.probability!=.5
                or r.approval_id not in approvals or r.patient_blinded or r.clinician_blinded for r in medication):
            raise ValueError('canonical independent unblinded N block randomization required')
        deliveries={}
        for r in records:
            if r.kind!='delivery':continue
            night=_day(r.event_at-timedelta(hours=8),h.origin)+1
            if not 1<=night<=_day(h.cutoff,h.origin) or r.rescue or r.protocol_deviations:
                raise ValueError('invalid N exposure')
            if r.option=='no_prompt':continue
            if r.stage not in ('taken','not_taken') or r.adherence!=float(r.stage=='taken'):
                raise ValueError('resolved binary N exposure required')
            key=(night,'C' if r.option=='behavioral_continue' else 'M')
            if key in deliveries:raise ValueError('duplicate N component exposure')
            deliveries[key]=r
        used=set()
        for t in range(1,_day(h.cutoff,h.origin)+1):
            at=h.origin+timedelta(days=t-1,hours=8)
            current=[r for r in background if r.event_at<=at]
            block=next((r for r in medication if 1<=t-_day(r.event_at,h.origin)<=7),None)
            for component,assignment in (('C',current[-1] if current else None),('M',block)):
                r=deliveries.get((t,component))
                if assignment is None:
                    if r is not None:raise ValueError('unassigned N component exposure')
                elif r is None or r.assignment_id!=assignment.record_id or r.option!=assignment.option:
                    raise ValueError('missing or mismatched N component exposure')
                else:used.add((t,component))
        if used!=deliveries.keys():raise ValueError('unconsumed N component exposure')
        arms[h.patient_id]={arm:sum(r.option==arm for r in medication) for arm in ('MED_A','MED_B')}
    if len(set(reviews))!=1:raise ValueError('common protocol-relative N review required')
    if reviews[0] not in (36,72):return dict(status='unavailable',reason='N requires relative review36 or72',review_day=reviews[0],arm_blocks=arms)
    status='eligible' if min(arms[target_id].values())>=2 else 'inconclusive'
    return dict(status=status,reason=None if status=='eligible' else 'Target needs two completed blocks per arm',review_day=reviews[0],arm_blocks=arms)


class NInput(StrictModel):
    schema_version: Literal['4.0.0']
    synthetic: Literal[True]
    kind: Literal['poc_nof1_input']
    purpose: Purpose
    attempt_id: Identifier
    owner_id: Identifier
    cohort_id: Identifier
    generation_id: Identifier
    run: VersionRef
    target_id: Identifier
    cutoff: AwareDatetime
    cohort: Annotated[list[NMember], Field(min_length=1)]
    histories: Annotated[list[ProtocolHistory], Field(min_length=1)]
    history_sha256: Sha256
    request: NRequest

    @model_validator(mode='after')
    def frozen(self):
        ids=[h.patient_id for h in self.histories]
        if ids!=sorted(set(ids)) or ids!=[m.patient_id for m in self.cohort] or self.target_id not in ids:
            raise ValueError('sorted explicit N cohort and target membership required')
        for m,h in zip(self.cohort,self.histories):
            if (h.family!='nof1_med' or h.cutoff!=self.cutoff
                    or sha(h.model_dump(mode='json'))!=m.history_sha256
                    or sha([r.model_dump(mode='json') for r in h.provenance])!=m.provenance_sha256):
                raise ValueError('N member reduced history/cutoff/lineage mismatch')
        if self.history_sha256!=sha([h.model_dump(mode='json') for h in self.histories]):
            raise ValueError('N joint Hstar hash mismatch')
        ctx=self.request.context
        if (self.request.purpose!=self.purpose or ctx.observation_cutoff!=self.cutoff
                or ctx.scenario!=self.run or ctx.seed.patient!=self.target_id
                or ctx.seed.scenario!=self.run.id or ctx.seed.protocol!=NOF1_REF['id']
                or ctx.seed.time_index!=_day(self.cutoff,self.histories[ids.index(self.target_id)].origin)
                or ctx.input_data.model_dump()!=reference('poc-nof1-app-observed-v1',[m.model_dump() for m in self.cohort])):
            raise ValueError('N request target/run/cutoff/seed/input binding mismatch')
        consumed_ids(self)
        readiness(self.histories,self.target_id)
        return self


def consumed_ids(product):
    ids=[r.record_id for h in product.histories for r in h.records]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate cross-member N record ownership')
    return sorted(ids)


def ownership_manifest(product):
    patients=[]
    for h in product.histories:
        records=h.records
        patients.append(dict(patient_id=h.patient_id,record_ids=sorted(r.record_id for r in records),
            likelihood=dict(quality=sorted(r.record_id for r in records if r.kind=='daily_report' and r.missingness=='observed'),
                isi=sorted(r.record_id for r in records if r.kind=='isi'),
                adherence_C=sorted(r.record_id for r in records if r.kind=='delivery' and r.option=='behavioral_continue'),
                adherence_M=sorted(r.record_id for r in records if r.kind=='delivery' and r.option in ('MED_A','MED_B')),
                observation_indicators=sorted(r.record_id for r in records if r.kind=='daily_report' and r.missingness!='pending'))))
    return dict(schema='poc-nof1-ownership-v1',history_sha256=product.history_sha256,
        ordered_cohort=[m.patient_id for m in product.cohort],target_id=product.target_id,patients=patients)


def make_input(histories, *, purpose, attempt_id, owner_id, cohort_id, generation_id,
               run, target_id, patient_versions, fit_seed):
    """Freeze already owned/projected observations; never select a target here."""
    histories=sorted(histories,key=lambda h:h.patient_id)
    members=[dict(patient_id=h.patient_id,patient_version=patient_versions[h.patient_id],
        history_sha256=sha(h.model_dump(mode='json')),
        provenance_sha256=sha([r.model_dump(mode='json') for r in h.provenance])) for h in histories]
    if not histories or target_id not in patient_versions:
        raise ValueError('declared nonempty N cohort and explicit target required')
    context=dict(estimand=N_ESTIMAND,dgp=LAW_REF,scenario=run,
        input_data=reference('poc-nof1-app-observed-v1',members),prior=PRIOR_REF,
        model=MODEL_REFS[purpose],protocol=NOF1_REF,observation_cutoff=histories[0].cutoff.isoformat(),
        seed=dict(namespace='fit',protocol=NOF1_REF['id'],scenario=run['id'],replicate=fit_seed,
            patient=target_id,time_index=_day(histories[0].cutoff,
                next(h.origin for h in histories if h.patient_id==target_id)),process=purpose+'-fit'),
        allowed_information='available_observed_history_only',truth_access='denied',
        comparator_estimand=N_ESTIMAND,comparator_information='same_permitted_history',
        source_ids=['EST-N1','BAYES-02','POC-4'],
        failure_policy='retain_all_attempts_fail_or_abstain_never_fabricate')
    return NInput.model_validate_json(canonical(dict(schema_version='4.0.0',synthetic=True,
        kind='poc_nof1_input',purpose=purpose,attempt_id=attempt_id,owner_id=owner_id,
        cohort_id=cohort_id,generation_id=generation_id,run=run,target_id=target_id,
        cutoff=histories[0].cutoff.isoformat(),cohort=members,
        histories=[h.model_dump(mode='json') for h in histories],
        history_sha256=sha([h.model_dump(mode='json') for h in histories]),
        request=dict(schema_version='4.0.0',synthetic=True,kind='nof1_fit_request',purpose=purpose,
            context=context,backend='pymc',sampler='native_nuts',precision='float64',
            configuration=CONFIG_REFS[purpose]))))


class NEffect(StrictModel):
    kind: Literal['conditional_expected_assignment_contrast']
    unit: Literal['quality_points']
    mean: float
    sd: Annotated[float, Field(gt=0)]
    lower: float
    upper: float
    horizon: Literal[7]
    target_id: Identifier

    @model_validator(mode='after')
    def interval(self):
        if not -10<=self.lower<=self.upper<=10 or not -10<=self.mean<=10:
            raise ValueError('ordered bounded expected quality contrast required')
        return self


class NResult(StrictModel):
    schema_version: Literal['4.0.0']
    synthetic: Literal[True]
    kind: Literal['poc_nof1_result']
    purpose: Purpose
    attempt_id: Identifier
    target_id: Identifier
    input_sha256: Sha256
    history_sha256: Sha256
    cohort: Annotated[list[NMember], Field(min_length=1)]
    cutoff: AwareDatetime
    run: VersionRef
    configuration: VersionRef
    model: VersionRef
    prior: VersionRef
    estimand: VersionRef
    protocol: VersionRef
    status: Literal['completed','abstained','failed']
    readiness: Literal['eligible','unavailable','inconclusive']
    reason: Annotated[str, Field(min_length=1)] | None
    generated_at: AwareDatetime
    consumed_record_ids: list[Identifier]
    effect: NEffect | None
    diagnostics: dict
    artifacts: list[dict]
    limitations: Annotated[list[str], Field(min_length=1)]

    @model_validator(mode='after')
    def accepted(self):
        for k,v in dict(configuration=CONFIG_REFS[self.purpose],model=MODEL_REFS[self.purpose],
                prior=PRIOR_REF,estimand=N_ESTIMAND,protocol=NOF1_REF).items():
            if getattr(self,k).model_dump()!=v:raise ValueError('N result '+k+' mismatch')
        ids=[m.patient_id for m in self.cohort]
        if ids!=sorted(set(ids)) or self.target_id not in ids:
            raise ValueError('N result target/cohort mismatch')
        if self.consumed_record_ids!=sorted(set(self.consumed_record_ids)):
            raise ValueError('unique sorted N consumed IDs required')
        if (self.status=='completed')!=(self.effect is not None) or (self.status=='completed')!=(self.reason is None):
            raise ValueError('failed/abstained N result cannot expose accepted effect')
        if self.status=='completed':
            if self.readiness!='eligible' or self.effect.target_id!=self.target_id:
                raise ValueError('eligible bound N effect target required')
            validate_summary(self)
        canonical(self.model_dump(mode='json'))
        return self


def _finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def validate_fit(d, *, effect=False):
    names=('expected_contrast',) if effect else MONITORED
    for key in ('rhat','ess_bulk','ess_tail','mcse'):
        values=d.get(key,{})
        if set(values)!=set(names) or any(not _finite(v) or v<0 for v in values.values()):
            raise ValueError('complete finite N '+key+' diagnostics required')
    if (d.get('accepted') is not True or max(d['rhat'].values())>=1.01
            or min(d['ess_bulk'].values())<400 or min(d['ess_tail'].values())<400):
        raise ValueError('N posterior diagnostics failed')
    if not effect:
        bfmi=d.get('energy_bfmi',[])
        if (d.get('divergences')!=0 or type(d.get('maximum_tree_depth')) is not int
                or not 0<=d['maximum_tree_depth']<12 or len(bfmi)!=4
                or any(not _finite(v) or v<=.3 for v in bfmi)):
            raise ValueError('N sampler diagnostics failed')


def validate_summary(result):
    d=result.diagnostics;fits=d.get('fits',[]);integration=d.get('integration',{})
    if not 1<=len(fits)<=2:raise ValueError('one fit and at most one extension required')
    if (fits[0].get('extended') is not False
            or (len(fits)==2 and (fits[1].get('extended') is not True
                or fits[0].get('diagnostics',{}).get('accepted') is not False))):
        raise ValueError('N extension is permitted once only after failed initial diagnostics')
    validate_fit(fits[-1].get('diagnostics',{}))
    validate_fit(d.get('effect_mcmc',{}),effect=True)
    if (integration.get('status')!='accepted' or integration.get('axes')!=['chain','draw','target']
            or integration.get('target_ids')!=[result.target_id] or integration.get('unit')!='quality_points'
            or integration.get('kind')!='conditional_expected_assignment_contrast'
            or integration.get('bootstrap')!=dict(resamples=1000,block=20,seed=731981)
            or not _finite(integration.get('seconds')) or not 0<=integration['seconds']<=1800):
        raise ValueError('complete bounded N integration diagnostics required')
    attempted=integration.get('attempted',[])
    if len(attempted)<2 or [r.get('K') for r in attempted]!=[1024*2**i for i in range(len(attempted))] or attempted[-1]['K']>65536:
        raise ValueError('N doubled K/2 integration history required')
    final=attempted[-1]
    keys=('U','L','residual_variance','raw_effect_variance','uninflated_effect_variance',
        'mean_integration_se','sd','stability_tolerance','seconds','peak_rss_mib')
    if any(not _finite(final.get(k)) or final[k]<0 for k in keys):
        raise ValueError('finite N integration bounds required')
    U,L=final['U'],final['L'];floor=max(L,.05**2)
    changes=final.get('changes',[]);interval=final.get('interval',[])
    if (U>.01*floor or final['mean_integration_se']>min(.02,.1*max(math.sqrt(L),.05))
            or any(final.get(k) is not True for k in ('variance_pass','mean_pass','stability_pass'))
            or len(changes)!=3 or any(not _finite(v) or v<0 or v>max(.005,.02*math.sqrt(L)) for v in changes)
            or not math.isclose(final['stability_tolerance'],max(.005,.02*math.sqrt(L)),rel_tol=1e-12)
            or interval!=[result.effect.lower,result.effect.upper] or final['sd']!=result.effect.sd):
        raise ValueError('N integration precision or effect interval mismatch')
    axes=d.get('axes',{})
    if (axes.get('chains')!=4 or axes.get('draws') not in (1000,2000)
            or axes.get('draws')!=(1000 if len(fits)==1 else 2000)
            or axes.get('target_ids')!=[result.target_id]
            or axes.get('patients')!=[m.patient_id for m in result.cohort]):
        raise ValueError('explicit N chain/draw/patient/target axes required')
    if (not math.isclose(final['raw_effect_variance'],result.effect.sd**2,rel_tol=1e-10,abs_tol=1e-12)
            or not math.isclose(final['uninflated_effect_variance'],
                max(0.,final['raw_effect_variance']-final['residual_variance']),rel_tol=1e-10,abs_tol=1e-12)
            or not math.isclose(final['mean_integration_se'],math.sqrt(U/(4*axes['draws'])),rel_tol=1e-10,abs_tol=1e-12)):
        raise ValueError('N residual-variance/mean-SE arithmetic mismatch')
    expected_semantics=dict(schema='poc-nof1-file-semantics-v1',status='accepted',
        chains=axes['chains'],draws=axes['draws'],patients=axes['patients'],target_ids=[result.target_id],
        expected_axes=['chain','draw','target'],predictive_axes=['chain','draw','target','arm','night'],
        expected_unit='quality_points',predictive_unit='reported_quality_points')
    if d.get('artifact_semantics')!=expected_semantics:
        raise ValueError('N scientific file semantic validation receipt required')
    names=[a.get('path') for a in result.artifacts]
    if len(names)!=len(ARTIFACT_NAMES) or set(names)!=ARTIFACT_NAMES:
        raise ValueError('complete separate N posterior/effect/predictive/ownership artifacts required')
    for artifact in result.artifacts:
        if set(artifact)!={'path','sha256'} or len(artifact['sha256'])!=64 or any(c not in '0123456789abcdef' for c in artifact['sha256']):
            raise ValueError('hashed N artifact required')


def execution_binding(product,origin):
    from .borrow_runtime import runtime_origin
    runtime_origin(origin['learner_image'],origin['source_commit'])
    return dict(kind='nof1-host-binding-v1',input_sha256=sha(product.model_dump(mode='json')),
        configuration=CONFIG_REFS[product.purpose],**origin)


def validate_result(result,product,trusted):
    if (result.attempt_id!=product.attempt_id or result.purpose!=product.purpose
            or result.target_id!=product.target_id or result.input_sha256!=sha(product.model_dump(mode='json'))
            or result.history_sha256!=product.history_sha256 or result.cohort!=product.cohort
            or result.cutoff!=product.cutoff or result.run!=product.run
            or result.configuration!=product.request.configuration or result.consumed_record_ids!=consumed_ids(product)):
        raise ValueError('frozen N result/input/target/cohort identity mismatch')
    if not trusted or result.diagnostics.get('execution')!=trusted or execution_binding(product,
            {k:trusted[k] for k in ('learner_image','source_commit')})!=trusted:
        raise ValueError('N trusted host source/image binding mismatch')
    ready=readiness(product.histories,product.target_id)
    if result.readiness!=ready['status']:raise ValueError('N result readiness mismatch')
    timings=result.diagnostics.get('timings',{})
    if not _finite(timings.get('worker_seconds')) or timings['worker_seconds']<0:
        raise ValueError('finite measured N worker timing required')
    if result.status=='completed' and ready['status']!='eligible':
        raise ValueError('N target not ready for accepted effect')
