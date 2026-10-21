"""ESTINT-PRECISION-01/1.0.0-r1: private IO and pure qualification.

No filter, generator, pilot or truth engine lives here. Provenance is checked
against producer output bytes; this does not independently establish that an
unqualified producer actually executed its claimed independent filters.
"""
from math import isfinite, sqrt
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator
from scipy.stats import beta

from contracts.domain.common import Nonnegative, Sha256, StrictModel, VersionRef
from .common import Artifact, Token, canonical, read_artifact, sha256, unique
from .private import ConditionalAccuracy, StreamKey

COMPONENTS=tuple(arm+'.'+event for arm in ('intervention','comparator')
                 for event in ('survival_day42','admission_by_day42','alive_outpatient_day42'))
LEVELS=(1024,4096,16384,65536)
Probability=Annotated[float,Field(ge=0,le=1,allow_inf_nan=False)]


def array(values, *, dimensions=2):
    x=np.asarray(values,dtype=np.float64)
    if x.ndim!=dimensions or not np.isfinite(x).all() or ((x<0)|(x>1)).any():
        raise ValueError('finite probability arrays required')
    return x


def pilot_statistics(values, counts, n_arm, *, proofs=None):
    """All 1000 trial means, including zero trials. CP is an IID cross-check."""
    x=array(values)
    if x.shape!=(1000,6) or n_arm<1:raise ValueError('1000 complete six-component trials required')
    k=np.asarray(counts)
    if k.shape!=x.shape or not np.issubdtype(k.dtype,np.integer) or ((k<0)|(k>n_arm)).any() or not np.allclose(x,k/n_arm,rtol=0,atol=1e-15):
        raise ValueError('pilot means/counts/assigned arm denominators disagree')
    m=x.mean(axis=0);s=x.std(axis=0,ddof=1)
    structural=np.array([COMPONENTS[i] in (proofs or {}) and np.all(x[:,i]==proofs[COMPONENTS[i]]) for i in range(6)])
    if ((s<=0)&~structural).any():raise ValueError('zero empirical trial dispersion is unresolved, without an artificial floor')
    safe=np.where(structural,1.,s)
    u=(x-m)**2;mcse=u.std(axis=0,ddof=1)/(2*safe*sqrt(1000));lower=s-1.645*mcse
    total=k.sum(axis=0);n=1000*n_arm
    lo=np.array([0. if v==0 else beta.ppf(.025,v,n-v+1) for v in total])
    hi=np.array([1. if v==n else beta.ppf(.975,v+1,n-v) for v in total])
    analytic=np.sqrt(np.minimum(lo*(1-lo),hi*(1-hi))/n_arm)
    bound=np.minimum(lower,analytic)
    bound=np.where(structural,np.inf,bound)
    if ((~np.isfinite(bound)|(bound<=0))&~structural).any():raise ValueError('nonpositive empirical/CP lower binding remains unresolved')
    p=total/n;z=1.96;den=1+z*z/n
    centre=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return dict(mean=m,sd=s,sd_mcse=mcse,lower=lower,cp_lower=lo,cp_upper=hi,
                analytic_lower=analytic,binding=bound,wilson_lower=centre-half,wilson_upper=centre+half,
                covariance=np.cov(x,rowvar=False,ddof=1),influence=(u-s*s)/(2*safe),structural=structural)


def require_refinement(level_values, level_statistics, epsilon):
    if len(level_values) not in (3,4) or len(level_values)!=len(level_statistics):raise ValueError('last two adjacent approved refinements required')
    for index in range(len(level_values)-2,len(level_values)):
        before,after=level_statistics[index-1:index+1]
        delta=level_values[index]-level_values[index-1]
        mean_bound=np.abs(after['mean']-before['mean'])+1.96*delta.std(axis=0,ddof=1)/sqrt(1000)
        dh=after['influence']-before['influence']
        sd_bound=.1*(np.abs(after['sd']-before['sd'])+1.96*dh.std(axis=0,ddof=1)/sqrt(1000))
        binding_change=.1*np.abs(np.where(after['structural'],0.,after['binding'])-np.where(before['structural'],0.,before['binding']))
        if any((v>epsilon/4).any() for v in (mean_bound,sd_bound,binding_change)):
            raise ValueError('mean/variance/lower-binding refinement unresolved at final epsilon')


class PathOutcome(StrictModel):
    """One complete path, including death and admission before death."""
    survival_day42: bool
    admission_by_day42: bool
    alive_outpatient_day42: bool
    death_day: Annotated[float,Field(ge=0,allow_inf_nan=False)] | None
    admission_day: Annotated[float,Field(ge=0,allow_inf_nan=False)] | None
    conditional_isi: Annotated[float,Field(ge=0,le=28,allow_inf_nan=False)] | None = None

    @model_validator(mode='after')
    def events(self):
        if self.survival_day42!=(self.death_day is None or self.death_day>42):raise ValueError('death/survival disagreement')
        if self.admission_by_day42!=(self.admission_day is not None and self.admission_day<=42):raise ValueError('admission/time disagreement')
        if self.death_day is not None and self.admission_day is not None and self.admission_day>self.death_day:raise ValueError('admission cannot first occur after death')
        if self.alive_outpatient_day42 and not self.survival_day42:raise ValueError('outpatient indicator exceeds survival')
        if not self.alive_outpatient_day42 and self.conditional_isi is not None:raise ValueError('conditional ISI cannot be supplied for a noneligible path')
        return self

    def vector(self):return [int(self.survival_day42),int(self.admission_by_day42),int(self.alive_outpatient_day42)]


class FilterExecution(StrictModel):
    """Producer execution receipts, not arbitrary relabelled environment IDs."""
    producer_run: Token
    environment: Token
    realization_sha256: Sha256
    ancestry_sha256: Sha256
    innovations_sha256: Sha256
    posterior_selection_sha256: Sha256
    rollout_sha256: Sha256
    # Full canonical StreamKey material is checked lazily to keep consumer imports safe.
    keys: list[StreamKey]

    def require_execution(self, *, protocol, cell, config, trial, environment, level, target_sha256):
        keys=self.keys
        processes={'probability_filter','probability_selection','probability_rollout'}
        if len(keys)!=3 or {k.process for k in keys}!=processes:raise ValueError('filter/selection/one-rollout keys required')
        for key in keys:
            expected_stream='p'+sha256(canonical(dict(configuration=config,environment=environment,level=level,target_sha256=target_sha256)))[:48]
            if (key.protocol,key.phase,key.namespace,key.scenario,key.replicate,key.patient,key.time_index,key.stream)!=(protocol,'pilot','truth',cell,trial,environment,level,expected_stream):
                raise ValueError('conditional unit full key changed target/configuration/trial/environment/level')
        return keys


class PilotEnvironment(StrictModel):
    id: Token
    arm: Literal['intervention','comparator']
    outcome: PathOutcome
    filter_execution: FilterExecution | None


class PilotTrial(StrictModel):
    trial: Annotated[int,Field(ge=0,lt=1000)]
    allocation_key: StreamKey
    environments: list[PilotEnvironment]


def require_trial(trial, *, conditional, n_arm, protocol, cell, config, level, seen, target_sha256, producer_run):
    if len(trial.environments)!=2*n_arm:raise ValueError('complete assigned arm rosters required; failures cannot be dropped')
    unique([v.id for v in trial.environments],'pilot environment')
    if any(sum(v.arm==arm for v in trial.environments)!=n_arm for arm in ('intervention','comparator')):raise ValueError('fixed balanced randomized allocation required')
    key=trial.allocation_key
    expected_stream='p'+sha256(canonical(dict(configuration=config,level=level,target_sha256=target_sha256)))[:48]
    if (key.protocol,key.phase,key.namespace,key.scenario,key.replicate,key.patient,key.time_index,key.process,key.stream)!=(protocol,'pilot','assignment',cell,trial.trial,config,level,'probability_allocation',expected_stream):raise ValueError('allocation key is not independent and target-bound')
    counts=[]
    for arm in ('intervention','comparator'):
        counts.extend(np.sum([v.outcome.vector() for v in trial.environments if v.arm==arm],axis=0).tolist())
    for v in trial.environments:
        receipt=v.filter_execution
        if conditional:
            if n_arm!=30 or receipt is None or receipt.environment!=v.id or receipt.producer_run!=producer_run:raise ValueError('conditional pilot requires 60 fresh per-environment filters, 30 per arm, bound to the actual producer run')
            keys=receipt.require_execution(protocol=protocol,cell=cell,config=config,trial=trial.trial,environment=v.id,level=level,target_sha256=target_sha256)
            # Cross-level coupling for the same (trial, environment) is allowed;
            # within a level no execution, ancestry or random innovation reuse is.
            identities=[('key',k.key_sha256) for k in keys]+[(name,getattr(receipt,name)) for name in ('realization_sha256','ancestry_sha256','innovations_sha256','posterior_selection_sha256','rollout_sha256')]
            if any(identity in seen for identity in identities):raise ValueError('shared/relabelled filter realization, ancestry, innovations, selection or rollout')
            seen.update(identities)
        elif receipt is not None:raise ValueError('unconditional IID trial cannot borrow conditional filter receipts')
    return counts


class PilotLevel(StrictModel):
    particles: Literal[0,1024,4096,16384,65536]
    trials: Annotated[list[Artifact],Field(min_length=1000,max_length=1000)]


class ProbabilityPilot(StrictModel):
    configuration: Token
    conditional: bool
    n_arm: Annotated[int,Field(gt=0)]
    history_sha256: Sha256 | None
    levels: list[PilotLevel]
    dispersion_review: Literal['consistent','unresolved']
    independent_iid_check: Artifact
    # Required even when empirical and binomial summaries happen to agree.
    producer_execution_qualification: Artifact


class PilotConfiguration(StrictModel):
    id: Token
    trial_size: Literal[60,240]


class ProbabilityPilotPlan(StrictModel):
    """Frozen required configurations in the authenticated request pilot file."""
    kind: Literal['probability_pilot_plan']
    rule: VersionRef
    conditional: bool
    configurations: Annotated[list[PilotConfiguration],Field(min_length=1)]

    @model_validator(mode='after')
    def complete_design(self):
        unique([c.id for c in self.configurations],'matched pilot configuration')
        if self.conditional and any(c.trial_size!=60 for c in self.configurations):raise ValueError('conditional trials retain 60 environments, 30 per arm')
        return self


class PairedPath(StrictModel):
    id: Token
    intervention: PathOutcome
    comparator: PathOutcome


class TruthBatch(StrictModel):
    id: Token
    independent_outer_key: StreamKey
    paths: Artifact
    conditional_filter_receipts: Artifact | None


class TruthFilterReceipt(StrictModel):
    producer_run: Token
    filter_index: Annotated[int,Field(ge=0,lt=32)]
    particles: Literal[1024,4096,16384,65536]
    key: StreamKey
    realization_sha256: Sha256
    ancestry_sha256: Sha256
    innovations_sha256: Sha256

    def require_binding(self, request, *, batch_index, target_sha256, particles):
        key=self.key
        if self.producer_run!=request.run_id or self.particles!=particles:raise ValueError('truth diagnostic filter producer/final level changed')
        if (key.protocol,key.phase,key.namespace,key.scenario,key.replicate,key.patient,key.time_index,key.process,key.stream)!=(request.bindings.protocol.id,'confirmation','truth',request.cell_id,batch_index,'truth-filter-'+str(self.filter_index),particles,'probability_truth_filter','p'+target_sha256[:48]):raise ValueError('truth diagnostic filter full key/target/batch identity mismatch')


class StructuralProof(StrictModel):
    component: Literal[COMPONENTS]
    value: Literal[0,1]
    method: Literal['analytic','enumerated']
    no_hidden_numerical_integration: Literal[True]
    independent_derivation: Artifact


class StructuralDerivation(StrictModel):
    request_sha256: Sha256
    component: Literal[COMPONENTS]
    value: Literal[0,1]
    method: Literal['analytic','enumerated']
    implementation: VersionRef
    proof_kind: Literal['known_death','independent_analytic','independent_enumeration']
    no_hidden_numerical_integration: Literal[True]
    derivation: Annotated[str,Field(min_length=20)]

    @model_validator(mode='after')
    def death_scope(self):
        if self.proof_kind=='known_death' and (self.value!=0 or self.component.endswith('admission_by_day42')):raise ValueError('known death does not establish past admission absence')
        return self


class ProbabilityEvidence(StrictModel):
    """Evaluator-owned evidence for all six probabilities, never observed export."""
    rule: VersionRef
    request_sha256: Sha256
    unit: Literal['probability']
    component_order: list[str]
    conditional: bool
    required_configurations: Annotated[list[Token],Field(min_length=1)]
    pilots: Annotated[list[ProbabilityPilot],Field(min_length=1)]
    batches: Annotated[list[TruthBatch],Field(min_length=32,max_length=1000)]
    structural_proofs: list[StructuralProof]
    actual_matched_estimator_se: Annotated[list[Nonnegative],Field(min_length=6,max_length=6)] | None
    conditional_accuracy: ConditionalAccuracy | None
    diagnostic_filters_per_level: Literal[32]

    @model_validator(mode='after')
    def exact_vector(self):
        if self.component_order!=list(COMPONENTS):raise ValueError('full fixed six-component probability vector required')
        unique(self.required_configurations,'required pilot configuration')
        if sorted(p.configuration for p in self.pilots)!=sorted(self.required_configurations):raise ValueError('every required matched configuration must be retained')
        unique([p.component for p in self.structural_proofs],'structural proof component')
        unique([b.id for b in self.batches],'independent truth batch')
        return self


def truth_statistics(counts, *, conditional, epsilon, proofs=None):
    """Batch means, not descendants, are independent conditional units."""
    k=np.asarray(counts)
    if k.ndim!=2 or k.shape[1]!=6 or not 32<=len(k)<=1000 or not np.issubdtype(k.dtype,np.integer) or ((k<0)|(k>10000)).any():raise ValueError('32..1000 complete paired batches of 10000 required')
    q=k/10000;mean=q.mean(axis=0);se=q.std(axis=0,ddof=1)/sqrt(len(q));cov=np.cov(q,rowvar=False,ddof=1)/len(q)
    n=len(q) if conditional else len(q)*10000
    boundary=1-.05**(1/n)
    boundary_error=np.where((mean==0)|(mean==1),boundary,0.)
    for index in range(6):
        if mean[index] in (0.,1.) and (proofs or {}).get(COMPONENTS[index])==mean[index]:boundary_error[index]=0.
        if se[index]==0 and mean[index] not in (0.,1.):raise ValueError('constant nonboundary numerical batches have no reviewed independent bound')
    pooled=np.sqrt(mean*(1-mean)/(len(q)*10000))
    z=1.96;total=len(q)*10000;den=1+z*z/total
    centre=(mean+z*z/(2*total))/den;half=z*np.sqrt(mean*(1-mean)/total+z*z/(4*total*total))/den
    if (se>epsilon).any() or (boundary_error>epsilon).any():raise ValueError('truth MCSE/boundary precision unresolved; cap cannot be extended')
    return dict(mean=mean,mcse=se,covariance=cov,boundary_error=boundary_error,
                pooled_iid_mcse=None if conditional else pooled,wilson_lower=None if conditional else centre-half,wilson_upper=None if conditional else centre+half)


def qualify_probability(evidence, root: Path, request):
    """Recompute from hashed evaluator files; caller has authenticated producer."""
    if evidence.rule!=request.bindings.probability_precision or evidence.request_sha256!=sha256(canonical(request.model_dump(mode='json'))):raise ValueError('probability rule/request hash mismatch')
    conditional=request.target.truth_kind=='observed_history_conditional_average'
    if evidence.conditional!=conditional:raise ValueError('probability information set mismatch')
    history=request.observed_history.sha256 if conditional else None
    if request.comparator_pilot is None:raise ValueError('frozen probability pilot plan required')
    plan=ProbabilityPilotPlan.model_validate_json(read_artifact(root,request.comparator_pilot,'evaluator_result'))
    if plan.rule!=evidence.rule or plan.conditional!=conditional or sorted(c.id for c in plan.configurations)!=sorted(evidence.required_configurations):raise ValueError('producer omitted or changed a predeclared matched configuration')
    sizes={c.id:c.trial_size for c in plan.configurations}
    if not conditional and int(request.cell_id.rsplit('.n',1)[1]) not in sizes.values():raise ValueError('catalog trial size absent from matched pilot plan')
    proofs={}
    for proof in evidence.structural_proofs:
        derivation=StructuralDerivation.model_validate_json(read_artifact(root,proof.independent_derivation,'evaluator_result'))
        if (derivation.request_sha256,derivation.component,derivation.value,derivation.method)!=(evidence.request_sha256,proof.component,proof.value,proof.method):raise ValueError('structural proof target/provenance mismatch')
        proofs[proof.component]=proof.value
    all_values=[];all_stats=[];bindings=[]
    for pilot in evidence.pilots:
        if pilot.conditional!=conditional or pilot.history_sha256!=history or pilot.dispersion_review!='consistent':raise ValueError('pilot history/dispersion remains unresolved')
        expected_levels=list(LEVELS[:len(pilot.levels)]) if conditional else [0]
        if [l.particles for l in pilot.levels]!=expected_levels or (conditional and len(pilot.levels) not in (3,4)) or (not conditional and len(pilot.levels)!=1):raise ValueError('approved pilot particle levels required')
        expected_n=sizes[pilot.configuration]//2
        if pilot.n_arm!=expected_n:raise ValueError('matched randomized pilot arm size changed')
        read_artifact(root,pilot.independent_iid_check,'evaluator_result')
        read_artifact(root,pilot.producer_execution_qualification,'evaluator_result')
        values=[];statistics=[]
        for level in pilot.levels:
            seen=set();counts=[]
            for index,artifact in enumerate(level.trials):
                trial=PilotTrial.model_validate_json(read_artifact(root,artifact,'evaluator_result'))
                if trial.trial!=index:raise ValueError('all 1000 paired trial IDs must align across levels')
                counts.append(require_trial(trial,conditional=conditional,n_arm=pilot.n_arm,protocol=request.bindings.protocol.id,cell=request.cell_id,config=pilot.configuration,level=level.particles,seen=seen,target_sha256=evidence.request_sha256,producer_run=request.run_id))
            x=np.asarray(counts)/pilot.n_arm;stats=pilot_statistics(x,counts,pilot.n_arm,proofs=proofs)
            values.append(x);statistics.append(stats)
        bindings.append(statistics[-1]['binding']);all_values.append(values);all_stats.append(statistics)
    matched=np.min(bindings,axis=0)
    if evidence.actual_matched_estimator_se is not None:
        actual=np.asarray(evidence.actual_matched_estimator_se)
        structural=np.array([c in proofs for c in COMPONENTS])
        if not np.isfinite(actual).all() or ((actual<=0)&~structural).any():raise ValueError('zero/nonfinite matched actual SE requires analytic proof or unresolved status')
        matched=np.minimum(matched,np.where(structural,np.inf,actual))
    epsilon=np.minimum(.001,.1*matched)
    if conditional:
        for values,stats in zip(all_values,all_stats):require_refinement(values,stats,epsilon)
    counts=[];outer=set();paired_ids=None;isi_numerators=[];isi_denominators=[]
    for batch_index,batch in enumerate(evidence.batches):
        key=batch.independent_outer_key
        if (key.protocol,key.phase,key.namespace,key.scenario,key.replicate,key.patient,key.time_index,key.process)!=(request.bindings.protocol.id,'confirmation','truth',request.cell_id,batch_index,request.patient_id or 'population',42,'probability_truth_batch'):raise ValueError('outer truth batch key changed target/run/cutoff')
        if key.stream!='p'+evidence.request_sha256[:48]:raise ValueError('outer truth seed missing full target/history/action/support binding')
        if key.key_sha256 in outer:raise ValueError('reused truth outer batch key')
        outer.add(key.key_sha256)
        import json
        paths=[PairedPath.model_validate(p) for p in json.loads(read_artifact(root,batch.paths,'evaluator_result'))]
        if len(paths)!=10000:raise ValueError('incomplete paired paths cannot be dropped')
        unique([p.id for p in paths],'paired path')
        ids=[p.id for p in paths]
        if paired_ids is None:paired_ids=ids
        elif ids!=paired_ids:raise ValueError('paired ID roster changed across truth batches')
        if conditional:
            if batch.conditional_filter_receipts is None:raise ValueError('each conditional outer batch must regenerate independent filters')
            receipts=[TruthFilterReceipt.model_validate(v) for v in json.loads(read_artifact(root,batch.conditional_filter_receipts,'evaluator_result'))]
            if len(receipts)!=32 or {r.filter_index for r in receipts}!=set(range(32)):raise ValueError('32 exact independent truth diagnostic filter receipts required')
            for receipt in receipts:
                receipt.require_binding(request,batch_index=batch_index,target_sha256=evidence.request_sha256,particles=evidence.pilots[0].levels[-1].particles)
                for field in ('realization_sha256','ancestry_sha256','innovations_sha256'):
                    identity=(field,getattr(receipt,field))
                    if identity in outer:raise ValueError('conditional truth outer batches reused filters')
                    outer.add(identity)
        elif batch.conditional_filter_receipts is not None:raise ValueError('IID truth cannot borrow conditional receipt claims')
        counts.append(np.sum([p.intervention.vector()+p.comparator.vector() for p in paths],axis=0).tolist())
        sums=[];eligible=[]
        for arm in ('intervention','comparator'):
            outcomes=[getattr(p,arm) for p in paths];values=[p.conditional_isi for p in outcomes if p.alive_outpatient_day42]
            if any(value is None for value in values):raise ValueError('complete eligible conditional ISI values required; no silent loss after death/admission')
            sums.append(sum(values));eligible.append(len(values))
        isi_numerators.append(sums);isi_denominators.append(eligible)
    stats=truth_statistics(counts,conditional=conditional,epsilon=epsilon,proofs=proofs)
    if conditional:
        if evidence.conditional_accuracy is None:raise ValueError('conditional truth requires quadrature/refinement/within/between budget')
        accuracy=evidence.conditional_accuracy;accuracy.require_accuracy(float(min(epsilon)))
        if accuracy.particle_levels!=[l.particles for l in evidence.pilots[0].levels]:raise ValueError('final pilot/truth particle levels differ')
        if any([l.particles for l in pilot.levels]!=accuracy.particle_levels for pilot in evidence.pilots):raise ValueError('every matched pilot and truth must share the final particle level')
        for artifact in accuracy.independent_reduced_checks:read_artifact(root,artifact,'evaluator_result')
    elif evidence.conditional_accuracy is not None:raise ValueError('unconditional truth has no conditional accuracy allowance')
    matched=np.where([c in proofs for c in COMPONENTS],0.,matched)
    a=np.asarray(isi_numerators)/10000;d=np.asarray(isi_denominators)/10000
    isi=[]
    for i in range(2):
        count=int(np.asarray(isi_denominators)[:,i].sum())
        if count<2:isi.append(dict(status='undefined',reason='no_sampled_eligible_paths' if count==0 else 'fewer_than_two_eligible_paths',count=count,value=None,mcse=None))
        else:
            mean=float(a[:,i].mean()/d[:,i].mean());mcse=float((a[:,i]-mean*d[:,i]).std(ddof=1)/(d[:,i].mean()*sqrt(len(d))))
            isi.append(dict(status='computed',count=count,value=mean,mcse=mcse))
    return dict(**stats,epsilon=epsilon,matched_se=matched,batches=len(counts),structural_proofs=proofs,conditional_isi=isi)
