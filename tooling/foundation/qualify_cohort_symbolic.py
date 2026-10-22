"""Bounded symbolic qualification only: no NUTS, fit, or accepted result."""
import argparse
import gc
import json
from pathlib import Path
import sys
import time

import numpy as np
import pymc as pm
import pytensor
from pytensor.compile.mode import Mode
from scipy.special import expit, logit, log_ndtr, logsumexp
from scipy.stats import beta as beta_law, halfnorm, norm

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from contracts.domain.borrowing import SourceBundle
from contracts.domain.borrow_runtime import cohort_coordinate_layout
from methods.visit.cohort_model import build_cohort, build_cohort_borrow, cohort_inputs
from methods.visit.model import build
from methods.visit.borrow_execution import compilation_options, verify_cvm, native_call, optimizer_identity
from tests.contracts.test_cohort import database, export


MODE=Mode(linker='cvm',optimizer='fast_compile')


def density(data, p):
    """Independent scalar original-coordinate joint density, without Jacobians."""
    sd_b=np.exp(p['sd_b_log__']);sd_beta=np.exp(p['sd_beta_log__'])
    rho=1.9*expit(p['rho_interval__'])-.95
    se,si,sq=[np.exp(p[k+'_log__']) for k in ('sigma_e','sigma_isi','sigma_quality')]
    result=float(halfnorm.logpdf(sd_b,scale=3)+halfnorm.logpdf(sd_beta,scale=1).sum()
        -np.log(1.9)+halfnorm.logpdf(se,scale=2)+halfnorm.logpdf(si,scale=2)
        +halfnorm.logpdf(sq,scale=1)+norm.logpdf(p['mu_b'],19,5)
        +norm.logpdf(p['population_beta'],0,4).sum()+norm.logpdf(p['a']))
    for name in ('b_raw','beta_raw','innovation'):result+=float(norm.logpdf(p[name]).sum())
    def bin_log(value,mean,sd,step,maximum):
        lo=(value-step/2-mean)/sd;hi=(value+step/2-mean)/sd
        if value==0:return log_ndtr(hi)
        if value==maximum:return log_ndtr(-lo)
        a,b=(log_ndtr(-lo),log_ndtr(-hi)) if lo>0 else (log_ndtr(hi),log_ndtr(lo))
        return a+np.log(-np.expm1(b-a))
    for i,(_,d) in enumerate(data):
        error=[];last=0.
        for innovation in p['innovation'][i]:last=rho*last+se*innovation;error.append(last)
        burden=p['mu_b']+sd_b*p['b_raw'][i]+p['a']*np.sin(2*np.pi*d['nights']/21)+np.array(error)
        effect=p['population_beta']+sd_beta*p['beta_raw'][i]
        burden-=effect[0]*d['c']+effect[1]*d['e']
        result+=sum(bin_log(v,float(burden[window].mean()),si,1.,28.) for v,window in zip(d['isi'],d['recall'],strict=True))
        result+=sum(bin_log(v,float(10-burden[index]/3),sq,.001,10.) for v,index in zip(d['quality'],d['qindex'],strict=True))
    taken=sum(d['taken'] for _,d in data);deliveries=sum(d['deliveries'] for _,d in data)
    observed=sum(len(d['quality']) for _,d in data);reports=sum(d['day'] for _,d in data)
    result+=beta_law.logpdf(expit(p['p_adherence_logodds__']),1+taken,1+deliveries-taken)
    result+=beta_law.logpdf(expit(p['observation_rate_logodds__']),1+observed,1+reports-observed)
    return float(result)


def original_point(model, count, nights):
    p=model.initial_point()
    p.update(sd_b_log__=np.array(np.log(1.4)),sd_beta_log__=np.log([.8,1.1]),rho_interval__=np.array(logit((.2+.95)/1.9)),
        sigma_e_log__=np.array(np.log(1.1)),sigma_isi_log__=np.array(np.log(1.3)),sigma_quality_log__=np.array(np.log(.6)),
        mu_b=np.array(18.2),population_beta=np.array([1.,2.]),a=np.array(.4),
        b_raw=np.linspace(-.2,.3,count),beta_raw=np.linspace(-.3,.2,count*2).reshape(count,2),
        innovation=.1*np.sin(np.arange(count*nights)).reshape(count,nights),
        p_adherence_logodds__=np.array(logit(.7)),observation_rate_logodds__=np.array(logit(.8)))
    return p


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--native',action='store_true')
    args=parser.parse_args();started=time.monotonic();results={}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(results,indent=2)+'\n')
    # Preserve every completed gate if a subsequent gate fails or the external
    # whole-run watchdog terminates compilation. Qualification thresholds stay
    # unchanged; a partial record never denotes full acceptance.
    options=compilation_options()
    results['preflight']=dict(guard_pass=True,optimizer=optimizer_identity(options['mode'].provided_optimizer),
        linker=type(options['mode'].linker).__name__,full_qualification=False)
    save()
    db=database();cohort=export(db);db.close();data=cohort_inputs(cohort);n=len(data[0][1]['nights'])
    original=build_cohort(data,guide=False);point=original_point(original,12,n)
    lp=original.compile_logp(jacobian=False,mode=MODE);grad=original.compile_dlogp(jacobian=False,mode=MODE)
    actual=float(lp(point));expected=density(data,point);assert abs(actual-expected)<1e-8,(actual,expected)
    rng=np.random.default_rng(8129);direction={k:rng.normal(size=np.asarray(v).shape) for k,v in point.items()}
    epsilon=1e-5
    finite=(density(data,{k:v+epsilon*direction[k] for k,v in point.items()})-density(data,{k:v-epsilon*direction[k] for k,v in point.items()}))/(2*epsilon)
    flat=np.concatenate([np.asarray(direction[v.name]).reshape(-1) for v in original.continuous_value_vars])
    autodiff=float(np.dot(grad(point),flat));assert abs(autodiff-finite)<1e-5+1e-4*abs(finite),(autodiff,finite)
    results['independent_joint_density_gradient']=dict(logp=actual,scalar_logp=expected,directional_autodiff=autodiff,directional_finite_difference=finite,patients=12)
    save()
    swapped=[(p,data[-1-i][1]) for i,(p,_) in enumerate(data)]
    reverse={k:(v[::-1] if k in ('b_raw','beta_raw','innovation') else v) for k,v in point.items()}
    reverse_model=build_cohort(swapped,guide=False);reverse_lp=reverse_model.compile_logp(jacobian=False,mode=MODE)
    assert abs(float(reverse_lp(reverse))-actual)<1e-8
    results['patient_permutation']=True
    save()
    del reverse_model,reverse_lp;gc.collect()
    singleton=build_cohort(data[:1],guide=False);single=build(data[0][1],guide=False)
    sp=original_point(singleton,1,n);op=dict(sp,b_raw=sp['b_raw'][0],beta_raw=sp['beta_raw'][0],innovation=sp['innovation'][0])
    sl=float(singleton.compile_logp(jacobian=False,mode=MODE)(sp));ol=float(single.compile_logp(jacobian=False,mode=MODE)(op))
    assert abs(sl-ol)<1e-8,(sl,ol);results['singleton_equivalence']=dict(cohort=sl,legacy=ol)
    save()
    del singleton,single;gc.collect()
    guided=build_cohort(data);gp=guided.initial_point()
    for key in gp:
        if key in point:gp[key]=point[key]
    gp['guide_innovation']=rng.normal(size=4+12*(n+3))*.1
    expression=guided.replace_rvs_by_values([guided['prior_normal_coordinates'],guided['guide_log_jacobian']])
    values=guided.compile_fn(expression,inputs=guided.value_vars,mode=MODE,on_unused_input='ignore')
    u,jac=values(gp);mapped=dict(point,mu_b=np.array(19+5*u[0]),population_beta=4*u[1:3],a=np.array(u[3]))
    local=u[4:].reshape(12,n+3);mapped.update(b_raw=local[:,0],beta_raw=local[:,1:3],innovation=local[:,3:])
    guide_lp=float(guided.compile_logp(jacobian=False,mode=MODE)(gp))
    mapped_lp=float(lp(mapped));difference=guide_lp-(mapped_lp+float(jac)+np.log(80.))
    assert abs(difference)<1e-7,difference
    results['guide_original_jacobian']=dict(difference=difference,shared_natural_scale_jacobian=float(np.log(80.)),guide_log_jacobian=float(jac))
    save()
    del values,guided,original,lp,grad;gc.collect()
    root=Path(__file__).resolve().parents[2]
    sources=SourceBundle.model_validate_json((root/'services/foundation/studies/source-7c97862d.json').read_bytes())
    from contracts.domain.cohort import COHORT_BORROW_CONFIG
    borrowed=build_cohort_borrow(data,sources,COHORT_BORROW_CONFIG,guide=False)
    bp=dict(point,source_bias=np.array([.1,-.2]),source_tau_log__=np.array(np.log(.7)))
    marginal_fn=borrowed.compile_fn(borrowed.replace_rvs_by_values([borrowed['source_g'],borrowed['source_logp']]),
        inputs=borrowed.value_vars,mode=MODE,on_unused_input='ignore')
    g,terms=marginal_fn(bp)
    scalar=[logsumexp([np.log(.5)+norm.logpdf(s.d,g+bp['source_bias'][i],np.sqrt(s.se**2+.7**2)),
        np.log(.5)+norm.logpdf(s.d,0,np.sqrt(s.se**2+100))]) for i,s in enumerate(sources.studies)]
    np.testing.assert_allclose(terms,scalar,rtol=1e-11,atol=1e-11)
    joint=float(borrowed.compile_logp(jacobian=False,mode=MODE)(bp))
    extra=float(np.sum(scalar)+norm.logpdf(bp['source_bias'],0,.5).sum()+halfnorm.logpdf(.7,scale=1))
    assert abs(joint-density(data,point)-extra)<1e-7
    results['external_terms_once']=dict(terms=np.asarray(terms).tolist(),count=len(terms),density_difference=joint-density(data,point),independent_terms_plus_new_priors=extra)
    save()
    del borrowed,marginal_fn;gc.collect()
    # Original unconditioned prior must not acquire local adherence/report counts.
    prior=build_cohort(data,guide=False,prior_predictive=True)
    with prior:draws=pm.sample_prior_predictive(draws=64,random_seed=9173,var_names=['b_raw','beta_raw','innovation','p_adherence','observation_rate'],compile_kwargs={'mode':MODE})
    p=np.asarray(draws['prior']['p_adherence']);obs=np.asarray(draws['prior']['observation_rate'])
    assert np.any(p<.5) and np.any(obs<.5)
    assert draws['prior']['b_raw'].shape==(1,64,12)
    results['original_prior_simulation']=dict(draws=64,patient_shape=list(draws['prior']['b_raw'].shape),p_range=[float(p.min()),float(p.max())],observation_range=[float(obs.min()),float(obs.max())])
    del draws,prior;gc.collect()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(dict(stage='symbolic-passed',seconds=time.monotonic()-started)),flush=True)
    if args.native:
        model=build_cohort_borrow(data,sources,COHORT_BORROW_CONFIG)
        point=model.initial_point();before=time.monotonic()
        fn=model.logp_dlogp_function(ravel_inputs=True,initial_point=point,**compilation_options())
        vm=verify_cvm(fn._pytensor_function)
        value,gradient,mapping=native_call(fn,point,model.continuous_value_vars)
        expected=cohort_coordinate_layout(cohort,borrowed=True)['layout'];assert mapping==expected
        results['native_combined']=dict(seconds=time.monotonic()-before,actual_vm=vm,coordinate_map=mapping,
            logp=float(value),gradient_finite=bool(np.isfinite(gradient).all()),dimension=len(gradient))
    results.update(seconds=time.monotonic()-started,no_fit=True,fixture='12 renamed observed contract histories, not independently generated/qualified job input')
    args.output.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2),flush=True)


if __name__=='__main__':main()
