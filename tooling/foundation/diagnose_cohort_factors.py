"""Same original graph/physical point factor diagnostic; no inference or repair."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.special import expit, log_ndtr
from scipy.stats import norm, halfnorm, beta as beta_law

sys.path.insert(0,str(Path(__file__).resolve().parent))
from qualify_cohort_symbolic import database, export, cohort_inputs, build_cohort, original_point, density, MODE
from methods.visit.borrow_execution import compilation_options, verify_cvm, optimizer_identity
from contracts.domain.borrow_runtime import OPTIMIZER
from pytensor.compile.mode import get_default_mode


def independent_factors(data,p):
    sb=np.exp(p['sd_b_log__']);bt=np.exp(p['sd_beta_log__']);rho=1.9*expit(p['rho_interval__'])-.95
    se,si,sq=[np.exp(p[k+'_log__']) for k in ('sigma_e','sigma_isi','sigma_quality')]
    result=dict(sd_b=halfnorm.logpdf(sb,scale=3),sd_beta=halfnorm.logpdf(bt,scale=1),rho=-np.log(1.9),
        sigma_e=halfnorm.logpdf(se,scale=2),sigma_isi=halfnorm.logpdf(si,scale=2),sigma_quality=halfnorm.logpdf(sq,scale=1),
        mu_b=norm.logpdf(p['mu_b'],19,5),population_beta=norm.logpdf(p['population_beta'],0,4),a=norm.logpdf(p['a']))
    for name in ('b_raw','beta_raw','innovation'):result[name]=norm.logpdf(p[name])
    result['p_adherence']=beta_law.logpdf(expit(p['p_adherence_logodds__']),1+sum(d['taken'] for _,d in data),1+sum(d['deliveries']-d['taken'] for _,d in data))
    result['observation_rate']=beta_law.logpdf(expit(p['observation_rate_logodds__']),1+sum(len(d['quality']) for _,d in data),1+sum(d['day']-len(d['quality']) for _,d in data))
    def logbin(v,m,s,step,maximum):
        lo=(v-step/2-m)/s;hi=(v+step/2-m)/s
        if v==0:return log_ndtr(hi)
        if v==maximum:return log_ndtr(-lo)
        a,b=(log_ndtr(-lo),log_ndtr(-hi)) if lo>0 else (log_ndtr(hi),log_ndtr(lo))
        return a+np.log(-np.expm1(b-a))
    for i,(_,d) in enumerate(data):
        state=0.;errors=[]
        for v in p['innovation'][i]:state=rho*state+se*v;errors.append(state)
        beta=p['population_beta']+bt*p['beta_raw'][i]
        z=p['mu_b']+sb*p['b_raw'][i]+p['a']*np.sin(2*np.pi*d['nights']/21)+errors-beta[0]*d['c']-beta[1]*d['e']
        result['isi_likelihood_'+str(i)]=sum(logbin(v,float(z[w].mean()),si,1.,28.) for v,w in zip(d['isi'],d['recall'],strict=True))
        if len(d['quality']):result['quality_likelihood_'+str(i)]=sum(logbin(v,float(10-z[j]/3),sq,.001,10.) for v,j in zip(d['quality'],d['qindex'],strict=True))
    return result


def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,np.ndarray):return clean(value.tolist())
    if isinstance(value,(float,np.floating)):
        return float(value) if np.isfinite(value) else ('+inf' if value>0 else '-inf' if value<0 else 'nan')
    return value


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    started=time.monotonic()
    # Check known public configuration before any model graph is built. The
    # pinned image's defaults are inherited, not overridden by launcher mode.
    baseline=compilation_options()
    actual_optimizer=optimizer_identity(get_default_mode().provided_optimizer)
    assert actual_optimizer==OPTIMIZER
    preflight=dict(guard_pass=True,optimizer=actual_optimizer,linker=type(baseline['mode'].linker).__name__)
    db=database();cohort=export(db);db.close();data=cohort_inputs(cohort)
    model=build_cohort(data,guide=False);point=original_point(model,12,len(data[0][1]['nights']))
    expected=independent_factors(data,point)
    result=dict(source='Original12-member graph and exact interior physical point from r2, unchanged fixture/model/settings',
        no_fit=True,preflight=preflight,independent_density=density(data,point),independent_factors=expected,point=point,modes={})
    assert abs(sum(np.sum(v) for v in expected.values())-result['independent_density'])<1e-9
    def save():args.output.write_text(json.dumps(clean(result),indent=2,allow_nan=False)+'\n')
    args.output.parent.mkdir(parents=True,exist_ok=True);save()
    labels=[rv.name for rv in model.free_RVs]+[rv.name for rv in model.observed_RVs]+[rv.name for rv in model.potentials]
    for name in ['diagnostic_fast_compile_cvm','production_unchanged_cvm']:
        mode=MODE if name=='diagnostic_fast_compile_cvm' else compilation_options()['mode']
        began=time.monotonic();values=copy.deepcopy(point)
        factors=model.compile_logp(sum=False,jacobian=False,mode=mode)
        actual=factors(values)
        metadata=dict(actual_vm=verify_cvm(factors.f),factors=[],point_unchanged=all(np.array_equal(values[k],point[k]) for k in point))
        assert len(labels)==len(actual)
        for label,array in zip(labels,actual,strict=True):
            array=np.asarray(array)
            metadata['factors'].append(dict(name=label,shape=list(array.shape),sum=float(np.sum(array)),
                finite=bool(np.isfinite(array).all()),values=array,independent=expected[label],
                max_absolute_difference=float(np.max(np.abs(array-expected[label])))))
        metadata['factor_sum']=float(sum(np.sum(x) for x in actual));result['modes'][name]=metadata;save()
        fn=model.compile_logp(jacobian=False,mode=mode)
        value=float(fn(copy.deepcopy(point)))
        metadata.update(compiled_sum=value,difference_from_independent=value-result['independent_density'],
            seconds=time.monotonic()-began,point_unchanged_after_sum=all(np.array_equal(values[k],point[k]) for k in point))
        save();print(json.dumps(clean(dict(mode=name,compiled_sum=value,factor_sum=metadata['factor_sum'],seconds=metadata['seconds']))),flush=True)
    result['seconds']=time.monotonic()-started;save()


if __name__=='__main__':main()
