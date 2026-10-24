"""Evaluator-owned TA2-SE-DEFINITION-01 scalar preparation, never truth admission.

Only scalar summaries of previously admitted WHOLE cohort results cross here.
The required admission callable belongs to the separately reviewed isolated
result/artifact boundary; a content hash, callback return or this module's output
does not confer runtime authority or qualify an artifact. No posterior is loaded.
"""
import math
import re
from datetime import datetime
from statistics import fmean, stdev
from typing import Annotated, Literal

from pydantic import Field, model_validator
from contracts.domain.common import Identifier, Sha256, StrictModel, VersionRef
from contracts.domain.analysis import ESTIMAND_REF, canonical, reference, sha
from contracts.domain.cohort import (CohortInput, CohortResult, COHORT_CONFIG,
    COHORT_BORROW_CONFIG, COHORT_CONFIG_REF, COHORT_BORROW_CONFIG_REF)
from contracts.domain.borrowing import NumericalSeeds

DEFINITION = reference('TA2-SE-DEFINITION-01', dict(version=1,
    experiment='fixed implemented estimator; independent whole cohorts; paired success',
    scalar='member.effect.mean; accepted expected-effect chain/draw average',
    scale='sample SD(Y), ddof=1, never divided by sqrt(R)', minimum_pairs=3,
    target='individual reduced Hstar; not cohort-conditioned truth',
    tightening='min(pilot,confirmation,earlier smaller admitted exact matches)',
    absolute=.05, fraction=.1))
CONFIGS = (COHORT_CONFIG_REF, COHORT_BORROW_CONFIG_REF)
SETTINGS = (COHORT_CONFIG, COHORT_BORROW_CONFIG)
ALGORITHM_PATHS = {'services/learner/cohort_worker.py', 'methods/visit/cohort_model.py',
    'methods/visit/cohort_geometry.py', 'methods/visit/cohort_execution.py',
    'methods/visit/model.py', 'methods/visit/numerics.py', 'methods/visit/source_precision.py',
    'contracts/domain/cohort.py', 'contracts/domain/analysis.py', 'contracts/domain/borrowing.py'}


class PlannedCohort(StrictModel):
    replicate_id: Identifier
    phase: Literal['pilot', 'confirmation']
    cohort_id: Identifier
    panel_id: Identifier
    generation_key: VersionRef
    member_ids: Annotated[list[Identifier], Field(min_length=12, max_length=12)]
    fit_seeds: Annotated[list[NumericalSeeds], Field(min_length=2, max_length=2)]


class SamplingDesign(StrictModel):
    definition: VersionRef
    scenario: VersionRef
    behavior: VersionRef
    enrollment_activation: VersionRef
    external_source_policy: Literal['fixed_across_cohort_replications']
    source_set_sha256: Sha256
    member_ordinal: Annotated[int, Field(ge=1, le=12)]
    cutoff_day: Literal[14, 42, 84]
    estimand: VersionRef
    unit: Literal['ISI_points']
    configurations: Annotated[list[VersionRef], Field(min_length=2, max_length=2)]
    numerical_settings: Annotated[list[dict], Field(min_length=2, max_length=2)]
    algorithm_sources: dict[str, Sha256]
    source_commit: Annotated[str, Field(pattern=r'^[a-f0-9]{40}$')]
    learner_image: Annotated[str, Field(pattern=r'^sha256:[a-f0-9]{64}$')]
    numerical_runtime: VersionRef
    frozen_before_collection: VersionRef
    planned: list[PlannedCohort]

    @model_validator(mode='after')
    def closed_experiment(self):
        if (self.definition.model_dump()!=DEFINITION or self.estimand.model_dump()!=ESTIMAND_REF
                or [v.model_dump() for v in self.configurations]!=list(CONFIGS)
                or self.numerical_settings!=list(SETTINGS) or set(self.algorithm_sources)!=ALGORITHM_PATHS):
            raise ValueError('unsupported definition/target/algorithm/configuration/settings closure')
        if not 3<=sum(p.phase=='pilot' for p in self.planned)<=8 or not 30<=sum(p.phase=='confirmation' for p in self.planned)<=100:
            raise ValueError('freeze existing3-8 pilot and30-100 confirmation cohorts before collection')
        for name in ('replicate_id','cohort_id','panel_id'):
            values=[getattr(p,name) for p in self.planned]
            if len(set(values))!=len(values):raise ValueError('duplicate planned independent cohort '+name)
        keys=[canonical(p.generation_key.model_dump()) for p in self.planned]
        patients=[patient for p in self.planned for patient in p.member_ids]
        seeds=[getattr(s,k) for p in self.planned for s in p.fit_seeds
            for k in ('nuts','effect_rollout','prior_check','bridge_reference')]
        if len(set(keys))!=len(keys) or len(set(patients))!=len(patients) or len(set(seeds))!=len(seeds):
            raise ValueError('cohort/member/generation/fit-stream reuse is not independent replication')
        if any(p.member_ids!=sorted(set(p.member_ids)) for p in self.planned):
            raise ValueError('member ordinals must be distinct and frozen before outcomes')
        return self

    @property
    def reference(self):return reference('matched-estimator-sampling-experiment-v1',self.model_dump(mode='json'))


class CohortAttempt(StrictModel):
    replicate_id: Identifier
    # None denotes planned but not attempted; no successful peer supplies it.
    inputs: Annotated[list[CohortInput], Field(min_length=2, max_length=2)] | None
    results: Annotated[list[CohortResult | None], Field(min_length=2, max_length=2)] | None
    reason: str | None


class AdmittedWholeCohort(StrictModel):
    """Binding returned by the isolated adapter, not self-authenticating proof."""
    experiment: VersionRef
    planned_cohort: VersionRef
    input: VersionRef
    result: VersionRef
    artifact_manifest: VersionRef
    scalar_semantics: Literal['accepted_chain_draw_expected_effect_mean']
    admission_reference: VersionRef


class MemberTarget(StrictModel):
    patient_id: Identifier
    history_sha256: Sha256
    provenance_sha256: Sha256
    cutoff: str
    ordinal: Annotated[int, Field(ge=1, le=12)]
    estimand: VersionRef
    unit: Literal['ISI_points']
    input_refs: Annotated[list[VersionRef],Field(min_length=2,max_length=2)]
    result_refs: Annotated[list[VersionRef],Field(min_length=2,max_length=2)]
    expected_effect_artifacts: Annotated[list[dict],Field(min_length=2,max_length=2)]


class ReductionRow(StrictModel):
    replicate_id: Identifier
    phase: Literal['pilot','confirmation']
    status: Literal['not_attempted','incomplete','paired_failure','paired_success']
    reason: str | None
    configuration_statuses: list[Literal['completed','abstained','failed'] | None] | None = None
    configuration_reasons: list[str | None] | None = None
    input_refs: list[VersionRef] | None = None
    result_refs: list[VersionRef | None] | None = None
    admissions: list[AdmittedWholeCohort] | None = None
    cohort_sha256: Sha256 | None = None
    manifest_sha256: Sha256 | None = None
    means: Annotated[list[float],Field(min_length=2,max_length=2)] | None = None
    target: MemberTarget | None = None
    artifacts: list[list[dict]] | None = None
    numerical_diagnostics: list[dict] | None = None


class SamplingSEBinding(StrictModel):
    schema_version: Literal['matched_estimator_sampling_se-v1']
    definition: VersionRef
    experiment: VersionRef
    design: SamplingDesign
    rows: list[ReductionRow]
    counts: dict
    scales: dict
    earlier: list[VersionRef]
    earlier_scales: list[Annotated[float,Field(gt=0)]]
    status: Literal['provisional','final','unresolved']
    used_se: Annotated[float,Field(gt=0)] | None
    epsilon: Annotated[float,Field(gt=0,le=.05)] | None
    zero_se_requires_analytic_truth: bool
    unit: Literal['ISI_points']
    conditional_population: Literal['prespecified paired-success fixed finite algorithm; not unconditional performance']
    production_truth: Literal[False]
    actual_admission: Literal['separately reviewed isolated result/artifact and calibration admission required']


def fresh(model, cls):
    if type(model) is not cls:raise ValueError('exact typed '+cls.__name__+' required')
    return cls.model_validate_json(model.model_dump_json())


def mcmc_gate(value, *, effect=False):
    """Check current numeric gates as well as labels; no relaxed SE-driven gate."""
    if value.get('accepted') is not True:raise ValueError('MCMC diagnostics not accepted')
    for name, predicate in (('rhat',lambda x:x<1.01),('ess_bulk',lambda x:x>=400),('ess_tail',lambda x:x>=400)):
        numbers=value.get(name,{})
        if not numbers or (effect and set(numbers)!={'effect'}) or any(type(x) not in (int,float) or not math.isfinite(x) or not predicate(x) for x in numbers.values()):
            raise ValueError('missing/nonfinite/failed MCMC '+name)
    mcse=value.get('mcse',{})
    if not mcse or (effect and set(mcse)!={'effect'}) or any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in mcse.values()):
        raise ValueError('separate finite fit numerical-error report required')
    if (value.get('divergences',0)!=0 or value.get('maximum_tree_depth',0)>=12
            or any(type(x) not in (int,float) or not math.isfinite(x) or x<=.3 for x in value.get('energy_bfmi',[1.]))):
        raise ValueError('MCMC divergence/depth/energy gate')


def completed_gates(product, result):
    d=result.diagnostics;fits=d.get('fits',[])
    if not 1<=len(fits)<=2:raise ValueError('whole cohort fit/extension diagnostics required')
    for i,fit in enumerate(fits):
        if fit.get('extension') is not bool(i) or fit.get('seed')!=product.numerical_seeds.nuts+i:
            raise ValueError('frozen initial/extension algorithm mismatch')
    mcmc_gate(fits[-1]['diagnostics'])
    names={a.get('path') for a in result.artifacts}
    if len(names)!=len(result.artifacts) or any(set(a)!={'path','sha256'} for a in result.artifacts):
        raise ValueError('duplicate/malformed whole result artifacts')
    if any(not re.fullmatch(r'[A-Za-z0-9_.-]+',a['path']) or not re.fullmatch(r'[a-f0-9]{64}',a['sha256']) for a in result.artifacts):
        raise ValueError('noncanonical artifact name/hash')
    for member in result.patients:
        if member.status!='completed' or member.effect is None:raise ValueError('every member must complete')
        pd=d.get('patients',{}).get(member.patient_id,{})
        if pd!=member.diagnostics:raise ValueError('member/whole diagnostic binding mismatch')
        mcmc_gate(pd.get('effect_mcmc',{}),effect=True)
        integration=pd.get('integration',{});attempts=integration.get('attempted',[])
        if integration.get('status')!='accepted' or not attempts:raise ValueError('expected-effect integration required')
        final=attempts[-1]
        required=('U','L','mean_integration_se','K')
        if any(type(final.get(k)) not in (int,float) or not math.isfinite(final[k]) or final[k]<0 for k in required):
            raise ValueError('nonfinite/missing integration diagnostics')
        if (final['K'] not in (1024,2048,4096,8192,16384,32768,65536)
                or any(final.get(k) is not True for k in ('variance_pass','mean_pass','stability_pass'))
                or final['U']>.01*max(final['L'],.1**2)
                or final['mean_integration_se']>min(.05,.1*max(math.sqrt(final['L']),.1))):
            raise ValueError('existing expected-effect numerical gates failed')
        expected='patient-'+sha(member.patient_id)[:16]+'-expected-effect.npz'
        if expected not in names:raise ValueError('whole cohort expected-effect artifact missing')
        canonical(member.effect.model_dump())  # rejects nonfinite mean/sd/limits
    if product.sources and (d.get('bridge_precision',{}).get('status')!='accepted'
            or not {'bridge-precision.json','bridge-marginals.npz'}<=names):
        raise ValueError('existing shared source bridge gate failed')


def read_attempt(design, planned, attempt, *, admit_whole_cohort):
    """Required isolated admission FIRST, then exact bindings/gates, then means.

    admit_whole_cohort(product,result) must authenticate result bytes, complete
    artifacts, trusted launch and chain/draw expected-effect semantics using the
    normal reviewed result admission plus isolated semantic artifact checks.
    No implementation of that actual boundary or permission is supplied here.
    Source tests use inert callbacks; callback identity hashes are not authority.
    """
    if attempt.inputs is None:
        if attempt.results is not None or not attempt.reason:raise ValueError('unattempted ledger needs reason and no results')
        return dict(replicate_id=planned.replicate_id,phase=planned.phase,status='not_attempted',reason=attempt.reason)
    products=attempt.inputs;results=attempt.results or [None,None];admissions=[]
    for index,(product,result) in enumerate(zip(products,results,strict=True)):
        manifest=product.cohort.manifest
        if (product.cohort.manifest.scope!='research' or manifest.research_execution!='engine_run'
                or (manifest.cohort_id,manifest.panel_id)!=(planned.cohort_id,planned.panel_id)
                or [m.patient_id for m in manifest.members]!=planned.member_ids
                or product.numerical_seeds!=planned.fit_seeds[index]
                or (manifest.cutoff-manifest.origin).total_seconds()!=design.cutoff_day*86400
                or product.request.configuration!=design.configurations[index]
                or product.request.context.scenario!=design.scenario
                or product.source_set_sha256!=(None if index==0 else design.source_set_sha256)):
            raise ValueError('planned cohort/ordinal/cutoff/config/source/stream mismatch')
        if result is None:continue
        # Mandatory even when a failed result retains earlier member files.
        admitted=AdmittedWholeCohort.model_validate(admit_whole_cohort(product,result))
        if any(getattr(admitted,k).model_dump()!=v for k,v in dict(experiment=design.reference,
                planned_cohort=reference('planned-independent-cohort',planned.model_dump(mode='json')),
                input=reference('cohort-input',product.model_dump(mode='json')),
                result=reference('cohort-result',result.model_dump(mode='json')),
                artifact_manifest=reference('cohort-artifact-manifest',result.artifacts)).items()):
            raise ValueError('isolated admission adapter returned mismatched binding')
        admissions.append(admitted.model_dump(mode='json'))
        if (result.attempt_id!=product.attempt_id or result.input_sha256!=sha(product.model_dump(mode='json'))
                or result.cohort_sha256!=product.cohort_sha256 or result.manifest!=manifest
                or result.manifest_sha256!=product.cohort.manifest_sha256
                or result.configuration!=product.request.configuration or result.source_set_sha256!=product.source_set_sha256):
            raise ValueError('exact whole result/input/artifact context mismatch')
    if products[0].cohort!=products[1].cohort:raise ValueError('paired V0/V1 must receive identical whole reduced cohort')
    if any(result is None for result in results):
        if not attempt.reason:raise ValueError('incomplete attempt requires retained reason')
        return dict(replicate_id=planned.replicate_id,phase=planned.phase,status='incomplete',reason=attempt.reason,
            input_refs=[reference('cohort-input',p.model_dump(mode='json')) for p in products],
            result_refs=[reference('cohort-result',r.model_dump(mode='json')) if r else None for r in results],
            configuration_statuses=[r.status if r else None for r in results],configuration_reasons=[r.reason if r else 'not_completed' for r in results])
    row=dict(replicate_id=planned.replicate_id,phase=planned.phase,status='paired_failure',
        reason=attempt.reason or '; '.join(r.reason for r in results if r.reason),configuration_statuses=[r.status for r in results],
        configuration_reasons=[r.reason for r in results],
        input_refs=[reference('cohort-input',p.model_dump(mode='json')) for p in products],
        result_refs=[reference('cohort-result',r.model_dump(mode='json')) for r in results],admissions=admissions,
        cohort_sha256=products[0].cohort_sha256,manifest_sha256=products[0].cohort.manifest_sha256)
    if any(r.status!='completed' for r in results):return row
    for product,result in zip(products,results,strict=True):
        completed_gates(product,result)
        execution=result.diagnostics.get('execution',{})
        if (execution.get('source_commit'),execution.get('learner_image'))!=(design.source_commit,design.learner_image):
            raise ValueError('fixed algorithm source/image execution identity mismatch')
    ordinal=design.member_ordinal-1;member=products[0].cohort.manifest.members[ordinal]
    row.update(status='paired_success',reason=None,means=[r.patients[ordinal].effect.mean for r in results],
        target=dict(patient_id=member.patient_id,history_sha256=member.history_sha256,
            provenance_sha256=member.provenance_sha256,cutoff=products[0].cohort.manifest.cutoff.isoformat(),
            ordinal=design.member_ordinal,estimand=design.estimand.model_dump(),unit=design.unit,
            input_refs=row['input_refs'],result_refs=row['result_refs'],expected_effect_artifacts=[
                next(a for a in r.artifacts if a['path']=='patient-'+sha(member.patient_id)[:16]+'-expected-effect.npz') for r in results]),
        artifacts=[r.artifacts for r in results],numerical_diagnostics=[r.patients[ordinal].diagnostics for r in results])
    return row


def sample_scale(values):
    if len(values)<3:return dict(count=len(values),sd=None,jackknife=None,unreliable=True)
    value=stdev(values)
    leave=[stdev(values[:i]+values[i+1:]) for i in range(len(values))]
    center=fmean(leave)
    return dict(count=len(values),sd=value,jackknife=math.sqrt((len(values)-1)/len(values)*math.fsum((x-center)**2 for x in leave)),
        unreliable=len(values)<=8,diagnostic='delete-one-cohort SD variability; not estimator SE or confidence bound')


def phase_statistics(rows):
    scales={};counts={}
    for phase in ('pilot','confirmation'):
        group=[r for r in rows if r['phase']==phase];pairs=[r for r in group if r['status']=='paired_success']
        counts[phase]=dict(planned=len(group),attempted=sum(r['status']!='not_attempted' for r in group),paired_success=len(pairs),
            paired_failure=sum(r['status']=='paired_failure' for r in group),incomplete=sum(r['status']=='incomplete' for r in group),
            not_attempted=sum(r['status']=='not_attempted' for r in group),configurations=[
                {label:sum((r.get('configuration_statuses') or [None,None])[i]==status for r in group)
                    for label,status in (('completed','completed'),('abstained','abstained'),('failed','failed'),('not_completed',None))} for i in (0,1)])
        scales[phase]=[sample_scale([r['means'][index] for r in pairs]) for index in (0,1)]
    return scales,counts


def precision(scales,counts,earlier):
    pilot=[s['sd'] for s in scales['pilot']];final=[s['sd'] for s in scales['confirmation']]
    candidates=pilot
    done=all(counts[p]['not_attempted']==counts[p]['incomplete']==0 for p in ('pilot','confirmation'))
    if done:candidates=pilot+final
    usable=all(s is not None and math.isfinite(s) and s>0 for s in candidates)
    used=min(candidates+list(earlier)) if usable else None
    status=('final' if done else 'provisional') if usable else 'unresolved'
    return status,used,(min(.05,.1*used) if used is not None else None),not usable and 0. in candidates


def reduce_sampling_se(design, attempts, *, expected_design, admit_whole_cohort, earlier=(), admit_earlier_binding=None):
    """Content-bound candidate only. Actual admission/collection remain external."""
    design=fresh(design,SamplingDesign)
    if design.reference!=expected_design:raise ValueError('independently frozen exact design reference required')
    attempts=[fresh(a,CohortAttempt) for a in attempts]
    by_id={a.replicate_id:a for a in attempts}
    if len(by_id)!=len(attempts) or set(by_id)!={p.replicate_id for p in design.planned}:
        raise ValueError('immutable full planned attempt ledger required; no dropped/replaced/duplicate cohorts')
    rows=[read_attempt(design,p,by_id[p.replicate_id],admit_whole_cohort=admit_whole_cohort) for p in design.planned]
    cohorts=[r['cohort_sha256'] for r in rows if 'cohort_sha256' in r]
    if len(set(cohorts))!=len(cohorts):raise ValueError('duplicate realized cohort is not another replication')
    scales,counts=phase_statistics(rows)
    for prior in earlier:
        prior=fresh(prior,SamplingSEBinding).model_dump(mode='json')
        if prior['experiment']!=design.reference:raise ValueError('earlier scale must exactly match this frozen experiment')
        # Reader recomputes prior scalar arithmetic; caller must separately admit
        # the prior binding just as the current artifact boundary is external.
        validate_binding(prior)
        if admit_earlier_binding is None:raise ValueError('earlier calibration requires separate isolated admission')
        admit_earlier_binding(prior)
        if prior['used_se'] is None or prior['used_se']<=0:raise ValueError('earlier missing/zero scale cannot resolve precision')
    phase,used,epsilon,zero=precision(scales,counts,[p.used_se for p in earlier])
    value=dict(schema_version='matched_estimator_sampling_se-v1',definition=DEFINITION,experiment=design.reference,
        design=design.model_dump(mode='json'),rows=rows,counts=counts,scales=scales,
        earlier=[reference('earlier-matched-sampling-SE',p.model_dump(mode='json')) for p in earlier],earlier_scales=[p.used_se for p in earlier],
        status=phase,used_se=used,epsilon=epsilon,zero_se_requires_analytic_truth=zero,
        unit='ISI_points',conditional_population='prespecified paired-success fixed finite algorithm; not unconditional performance',
        production_truth=False,actual_admission='separately reviewed isolated result/artifact and calibration admission required')
    return SamplingSEBinding.model_validate(value)


def validate_binding(value):
    """Recompute serialized scalar arithmetic; integrity does not confer authority."""
    value=SamplingSEBinding.model_validate_json(canonical(value)).model_dump(mode='json')
    if value['definition']!=DEFINITION or value['production_truth'] is not False:
        raise ValueError('unsupported sampling binding')
    design=SamplingDesign.model_validate_json(canonical(value['design']))
    if value['experiment']!=design.reference:raise ValueError('exact frozen experiment identity changed')
    if [(r['replicate_id'],r['phase']) for r in value['rows']]!=[(p.replicate_id,p.phase) for p in design.planned]:
        raise ValueError('complete immutable ordered cohort ledger changed')
    for row,planned in zip(value['rows'],design.planned,strict=True):
        if row['status']=='not_attempted':
            if not row['reason'] or any(row[k] is not None for k in ('means','target','input_refs','result_refs','admissions','configuration_statuses')):
                raise ValueError('unattempted row cannot expose results or scalar')
            continue
        if row['input_refs'] is None or len(row['input_refs'])!=2 or row['result_refs'] is None or len(row['result_refs'])!=2:
            raise ValueError('paired exact input/result references required')
        if row['status']!='paired_success':
            if not row['reason'] or any(row[k] is not None for k in ('means','target','artifacts','numerical_diagnostics')):
                raise ValueError('failed/incomplete whole cohort cannot expose a member scalar')
            statuses=row['configuration_statuses']
            if statuses is None or len(statuses)!=2 or (row['status']=='incomplete')!=(None in statuses):
                raise ValueError('incomplete and failed configuration statuses must remain distinct')
            if row['status']=='paired_failure' and statuses==['completed','completed']:
                raise ValueError('cannot select successful cohorts out of the prespecified pair set')
        else:
            target=row['target']
            if (row['configuration_statuses']!=['completed','completed'] or row['means'] is None
                    or row['admissions'] is None or len(row['admissions'])!=2 or target is None
                    or (target['patient_id'],target['ordinal'])!=(planned.member_ids[design.member_ordinal-1],design.member_ordinal)
                    or target['estimand']!=design.estimand.model_dump() or target['unit']!='ISI_points'):
                raise ValueError('whole paired-success target/admission binding changed')
            if target['input_refs']!=row['input_refs'] or target['result_refs']!=row['result_refs']:
                raise ValueError('scored target input/result identity changed')
            for index,artifact in enumerate(target['expected_effect_artifacts']):
                if artifact not in row['artifacts'][index] or artifact['path']!='patient-'+sha(target['patient_id'])[:16]+'-expected-effect.npz':
                    raise ValueError('scored expected-effect artifact identity changed')
        if row['status'] in ('paired_success','paired_failure'):
            if row['admissions'] is None or len(row['admissions'])!=2:raise ValueError('both whole-result admission bindings required')
            for i,admission in enumerate(row['admissions']):
                if (admission['experiment']!=design.reference
                        or admission['planned_cohort']!=reference('planned-independent-cohort',planned.model_dump(mode='json'))
                        or admission['input']!=row['input_refs'][i] or admission['result']!=row['result_refs'][i]):
                    raise ValueError('whole-cohort admission/scored result references changed')
                if row['status']=='paired_success' and admission['artifact_manifest']!=reference('cohort-artifact-manifest',row['artifacts'][i]):
                    raise ValueError('whole result artifact manifest changed')
    cohort_ids=[r['cohort_sha256'] for r in value['rows'] if r['cohort_sha256'] is not None]
    if len(set(cohort_ids))!=len(cohort_ids):raise ValueError('duplicated cohort is not independent evidence')
    scales,counts=phase_statistics(value['rows'])
    if value['scales']!=scales or value['counts']!=counts:raise ValueError('sampling scale/count/denominator arithmetic changed')
    if len(value['earlier'])!=len(value['earlier_scales']):raise ValueError('earlier exact scale references missing')
    status,used,epsilon,zero=precision(scales,counts,value['earlier_scales'])
    if (value['status'],value['used_se'],value['epsilon'],value['zero_se_requires_analytic_truth'])!=(status,used,epsilon,zero):
        raise ValueError('precision scale/tightening arithmetic changed')


def matched_estimator_sampling_se(value, *, expected_binding, target):
    """Read only an independently admitted exact binding for a scored pair.

    expected_binding must come from evaluator-owned admission, never from the
    payload being read. Hash equality supplies identity only, not actual custody.
    """
    value=fresh(value,SamplingSEBinding).model_dump(mode='json')
    target=MemberTarget.model_validate(target).model_dump(mode='json')
    if reference('matched-estimator-sampling-SE',value)!=expected_binding:raise ValueError('independent exact admitted binding required')
    validate_binding(value)
    if not any(r.get('target')==target and r['status']=='paired_success' for r in value['rows']):
        raise ValueError('missing/failed/unmatched per-member Hstar/cutoff/ordinal target')
    return value['used_se']


def reduce_refinement_with_sampling_se(rows, inventory, truth_binding, sampling, *, expected_sampling_binding, target):
    from .refinement import reduce_rows
    if (target['patient_id']!=truth_binding['patient_id'] or target['history_sha256']!=truth_binding['history_sha256']
            or datetime.fromisoformat(target['cutoff'])!=datetime.fromisoformat(truth_binding['target']['cutoff']) or target['unit']!='ISI_points'):
        raise ValueError('refinement must match exact scored Hstar/cutoff/ISI target')
    matched=matched_estimator_sampling_se(sampling,expected_binding=expected_sampling_binding,target=target)
    report=reduce_rows(rows,inventory,truth_binding,matched_se=matched)
    report.update(matched_estimator_sampling_se=expected_sampling_binding,matched_precision_status=sampling.status,
        matched_precision_epsilon=sampling.epsilon,zero_se_requires_analytic_truth=sampling.zero_se_requires_analytic_truth)
    return report


def truth_sensitivity(y0,y1,truth,epsilon,intervals=None,*,pair_ids,envelope='engineering_allowance'):
    """Equal scored pairs/weights/common truth only; no oracle bound is invented."""
    n=len(truth)
    if not n or any(len(values)!=n for values in (y0,y1,epsilon)):raise ValueError('identical nonempty scored pairs required')
    if (len(pair_ids)!=3 or any(len(ids)!=n for ids in pair_ids) or pair_ids[0]!=pair_ids[1] or pair_ids[0]!=pair_ids[2]
            or len(set(pair_ids[0]))!=n):
        raise ValueError('same distinct ordered scored-pair IDs for both methods and common truth required')
    if any(type(x) not in (int,float) or not math.isfinite(x) for values in (y0,y1,truth,epsilon) for x in values) or min(epsilon)<0:
        raise ValueError('finite scalar effects and nonnegative truth allowances required')
    if envelope not in ('engineering_allowance','independently_justified_bound'):raise ValueError('explicit envelope scope required')
    errors=[[y-t for y,t in zip(values,truth)] for values in (y0,y1)]
    out=dict(scope=envelope,bias_allowance=fmean(epsilon),rmse_allowance=math.sqrt(fmean([x*x for x in epsilon])),
        bias=[fmean(e) for e in errors],rmse=[math.sqrt(fmean([x*x for x in e])) for e in errors],
        paired_mean_error_difference=fmean([a-b for a,b in zip(y0,y1)]),common_truth_cancels_for_mean_error_difference=True,
        truth_cancels_for_squared_error_or_RMSE_difference=False,
        rmse_difference_allowance=2*math.sqrt(fmean([x*x for x in epsilon])),
        sign_ambiguous=[abs(t)<=e for t,e in zip(truth,epsilon)],
        ranking_ambiguous=[(i,j) for i in range(n) for j in range(i+1,n) if abs(truth[i]-truth[j])<=epsilon[i]+epsilon[j]])
    if intervals is not None:
        if len(intervals)!=n or any(len(pair)!=2 or not all(math.isfinite(x) for x in pair) or pair[0]>pair[1] for pair in intervals):raise ValueError('valid matched intervals required')
        certain=sum(lo<t-e and t+e<hi for (lo,hi),t,e in zip(intervals,truth,epsilon))
        possible=sum(not(t+e<lo or t-e>hi) for (lo,hi),t,e in zip(intervals,truth,epsilon))
        out['coverage']=dict(lower_count=certain,upper_count=possible,denominator=n,ambiguous=possible-certain)
    return out
