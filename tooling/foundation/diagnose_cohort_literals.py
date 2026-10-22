"""Same published point: scalar prior/CDF constants, no joint graph or fit."""
import argparse,json
from pathlib import Path
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt
from pytensor.graph.traversal import graph_inputs
from pytensor.graph.basic import Constant
from scipy.special import log_ndtr
from scipy.stats import norm,halfnorm
from methods.visit.model import log_bin
from methods.visit.borrow_execution import compilation_options,verify_cvm
from tests.contracts.test_cohort import database,export
from methods.visit.cohort_model import cohort_inputs
from diagnose_cohort_factors import clean


def typed_bin(value,mean,sd,step,maximum):
    lo=(value-np.float64(step)/np.float64(2)-mean)/sd
    hi=(value+np.float64(step)/np.float64(2)-mean)/sd
    normal=pm.Normal.dist(np.float64(0),np.float64(1))
    a=pt.switch(lo>np.float64(0),pm.logcdf(normal,-lo),pm.logcdf(normal,hi))
    b=pt.switch(lo>np.float64(0),pm.logcdf(normal,-hi),pm.logcdf(normal,lo))
    interior=a+pt.log(-pt.expm1(b-a))
    return pt.switch(pt.eq(value,np.float64(0)),pm.logcdf(normal,hi),
        pt.switch(pt.eq(value,np.float64(maximum)),pm.logcdf(normal,-lo),interior))


def scalar_bin(v,m,s,step,maximum):
    lo=(v-step/2-m)/s;hi=(v+step/2-m)/s
    if v==0:return log_ndtr(hi)
    if v==maximum:return log_ndtr(-lo)
    a,b=(log_ndtr(-lo),log_ndtr(-hi)) if lo>0 else (log_ndtr(hi),log_ndtr(lo))
    return a+np.log(-np.expm1(b-a))


def constants(expr):
    return [dict(dtype=v.dtype,value=np.asarray(v.data).tolist()) for v in graph_inputs([expr])
        if isinstance(v,Constant) and hasattr(v,'dtype') and np.asarray(v.data).size<=4]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--point',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    options=compilation_options();p={k:np.asarray(v,dtype=np.float64) for k,v in json.loads(args.point.read_bytes()).items()}
    results=dict(no_fit=True,no_joint_model=True,priors=[],measurement=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(clean(results),indent=2,allow_nan=False)+'\n')
    x=pt.dscalar('x')
    for name,value,original,typed,reference in [
        ('sd_b',1.4,pm.HalfNormal.dist(3),pm.HalfNormal.dist(np.float64(3)),halfnorm.logpdf(1.4,scale=3)),
        ('mu_b',18.2,pm.Normal.dist(19,5),pm.Normal.dist(np.float64(19),np.float64(5)),norm.logpdf(18.2,19,5))]:
        case=dict(name=name,reference=float(reference),constructions={})
        for label,rv in [('original',original),('float64',typed)]:
            expression=pm.logp(rv,x);fn=pytensor.function([x],expression,**options);actual=float(fn(value))
            case['constructions'][label]=dict(logp=actual,error=actual-float(reference),constants=constants(expression),actual_vm=verify_cvm(fn))
        results['priors'].append(case);save()
    db=database();data=cohort_inputs(export(db));db.close()
    values={'isi':[],'quality':[]};means={'isi':[],'quality':[]}
    sb=np.exp(p['sd_b_log__']);bt=np.exp(p['sd_beta_log__']);rho=1.9/(1+np.exp(-p['rho_interval__']))-.95;se=np.exp(p['sigma_e_log__'])
    for i,(_,d) in enumerate(data):
        state=0.;errors=[]
        for innovation in p['innovation'][i]:state=rho*state+se*innovation;errors.append(state)
        beta=p['population_beta']+bt*p['beta_raw'][i]
        z=p['mu_b']+sb*p['b_raw'][i]+p['a']*np.sin(2*np.pi*d['nights']/21)+errors-beta[0]*d['c']-beta[1]*d['e']
        values['isi'].extend(d['isi']);means['isi'].extend(z[d['recall']].mean(axis=1))
        values['quality'].extend(d['quality']);means['quality'].extend(10-z[d['qindex']]/3)
    mean=pt.dvector('mean');sd=pt.dscalar('sd')
    for name,step,maximum,sigma in [('isi',1.,28.,float(np.exp(p['sigma_isi_log__']))),('quality',.001,10.,float(np.exp(p['sigma_quality_log__'])))]:
        observations=np.asarray(values[name]);mu=np.asarray(means[name]);ref=np.array([scalar_bin(v,m,sigma,step,maximum) for v,m in zip(observations,mu,strict=True)])
        case=dict(name=name,count=len(mu),constructions={})
        for label,builder in [('original',log_bin),('float64',typed_bin)]:
            expression=builder(observations,mean,sd,step,maximum);fn=pytensor.function([mean,sd],expression,**options)
            actual=np.asarray(fn(mu,sigma));case['constructions'][label]=dict(sum=float(actual.sum()),reference_sum=float(ref.sum()),
                sum_error=float((actual-ref).sum()),max_error=float(np.abs(actual-ref).max()),constants=constants(expression),actual_vm=verify_cvm(fn))
        results['measurement'].append(case);save()
    save();print(json.dumps(clean(results),indent=2))


if __name__=='__main__':main()
