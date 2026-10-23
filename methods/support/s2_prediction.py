"""Unqualified S2 reference predictor. Learner-only; never import on CORE/host.

No model fitting, filtering, observation sampling, allocation or authority here.
All arrays are joint float64 arrays retaining original chain/draw/member axes.
"""
import time

import numpy as np
from contracts.domain.analysis import sha
from contracts.domain.support_s2 import CELLS, S2Request, S2Result, precision_status
from methods.nof1.observation import expected_quality, rounded_quality

EPSILON = 1e-8
FIELDS = {'alpha','tau','e_T','b','rho','s_e','s_Q'}


def checked_arrays(arrays,patient_ids,request):
    if set(arrays)!=FIELDS:raise ValueError('exact S2 joint array names required')
    if patient_ids!=[m.patient_id for m in request.members]:
        raise ValueError('joint member axis differs from fitted complete cohort')
    if any(not isinstance(a,np.ndarray) or a.dtype!=np.dtype('float64')
            or not np.all(np.isfinite(a)) for a in arrays.values()):
        raise ValueError('finite native float64 joint arrays required')
    shape=arrays['alpha'].shape
    if len(shape)!=3 or shape[0]!=4 or shape[1] not in (1000,2000) or shape[2]!=12:
        raise ValueError('S2 requires chain4/draw1000-or2000/member12 axes')
    for key in ('alpha','tau','e_T'):
        if arrays[key].shape!=shape:raise ValueError('joint target axes mismatch')
    if arrays['b'].shape!=shape[:2]+(4,):raise ValueError('joint four-feature axes mismatch')
    for key in ('rho','s_e','s_Q'):
        if arrays[key].shape!=shape[:2]:raise ValueError('joint scalar draw axes mismatch')
    if (np.any(np.abs(arrays['rho'])>.95) or np.any(arrays['s_e']<0)
            or np.any(arrays['s_Q']<0)):raise ValueError('S2 parameter support mismatch')
    return patient_ids.index(request.target_id)


def action_moments(alpha,tau,b,rho,e_T,s_e,s_Q,x,h):
    """Joint conditional mean/SD; no recentering or postfit state update."""
    if (type(h) is not int or not 1<=h<=14 or np.any(np.abs(rho)>.95)
            or np.any(s_e<0) or np.any(s_Q<0)):
        raise ValueError('S2 horizon/parameter support mismatch')
    base=alpha+np.sum(b*np.asarray(x,dtype=np.float64),axis=-1)+(rho**h)*e_T
    variance=s_Q*s_Q+s_e*s_e*sum(rho**(2*j) for j in range(h))
    sd=np.sqrt(variance)
    positive=(s_Q>0)|(s_e>0)
    if (not np.all(np.isfinite(base)) or not np.all(np.isfinite(sd))
            or np.any(positive&(sd==0))):raise ValueError('nonfinite/underflow S2 arithmetic')
    return base-.5*tau,base+.5*tau,sd


def blend(mean,rate,delta):
    return (1-rate)*mean+rate*np.clip(mean+delta,0.,10.)


def indicator_diagnostics(z):
    """Installed API qualification remains a separate actual operation."""
    import xarray as xr
    import arviz_stats as azs
    probability=float(np.mean(z))
    half=float(np.mean(z[:,:z.shape[1]//2]))
    constant=any(np.unique(chain).size<2 for chain in z)
    values=dict(rhat=None,ess_bulk=None,ess_tail=None,mcse=None)
    if not constant:
        tree=xr.DataTree.from_dict({'posterior':xr.Dataset({'Z':(('chain','draw'),z)})})
        for name,fn,kwargs in (('rhat',azs.rhat,dict(method='rank')),
                ('ess_bulk',azs.ess,dict(method='bulk')),('ess_tail',azs.ess,dict(method='tail')),
                ('mcse',azs.mcse,dict(method='mean'))):
            value=np.asarray(fn(tree,var_names=['Z'],**kwargs)['Z'].values)
            if value.size!=1:raise ValueError('S2 diagnostic scalar axes changed')
            values[name]=float(value.item()) if np.all(np.isfinite(value)) else None
    return dict(probability=probability,half_probability=half,constant_chain=constant,
        status=precision_status(probability,half,constant,**values),**values)


def predict(request,arrays,patient_ids):
    """Candidate reference result plus all ten indicators, never serving authority.

    Empirical epsilon bounds below are proposed engineering guards. They must be
    qualified on the frozen domain before any caller can consider allocation.
    A malformed array/identity raises; an admissible but unready context abstains.
    """
    if not isinstance(request,S2Request):raise ValueError('validated S2Request required')
    target=checked_arrays(arrays,patient_ids,request)
    result=dict(schema_version=request.schema_version,
        request_sha256=sha(request.model_dump(mode='json')),target_id=request.target_id,
        context_id=request.context_id,context_version=request.context_version,
        status='numerical_unready',reason='',primary=None,
        cells=[dict(delta0=a,delta1=b,precision=None) for a,b in CELLS],
        probability=.5,serving_authority=False,empirical_domain_only=True)
    timing=dict(expected_quality_seconds=0.,diagnostics_seconds=0.,distinct_diagnostic_arrays=0)
    member=request.members[target]
    totals=[member.observed[a]+member.missing[a] for a in (0,1)]
    if not all(totals):
        result.update(status='arm_unavailable',reason='no complete two-action opportunity in an arm')
        return S2Result.model_validate(result),{},timing
    rates=[member.missing[a]/totals[a] for a in (0,1)]
    tau=arrays['tau'][:,:,target]
    try:
        mu0,mu1,sd=action_moments(arrays['alpha'][:,:,target],tau,arrays['b'],
            arrays['rho'],arrays['e_T'][:,:,target],arrays['s_e'],arrays['s_Q'],
            request.x_current,request.h)
    except ValueError as error:
        result['reason']=str(error);return S2Result.model_validate(result),{},timing
    positive=sd>0
    if (np.any(mu0< -40) or np.any(mu0>50) or np.any(mu1< -40) or np.any(mu1>50)
            or np.any(positive&((sd<1e-6)|(sd>40)))):
        result['reason']='draw outside candidate empirical domain'
        return S2Result.model_validate(result),{},timing
    # Exactly two complete g calls feed the primary and every sensitivity cell.
    before=time.perf_counter()
    m0=expected_quality(mu0,sd);m1=expected_quality(mu1,sd)
    timing['expected_quality_seconds']=time.perf_counter()-before
    if (not np.all(np.isfinite(m0)) or not np.all(np.isfinite(m1))
            or np.any(m0<0) or np.any(m0>10) or np.any(m1<0) or np.any(m1>10)):
        result['reason']='invalid reference quality expectation'
        return S2Result.model_validate(result),{},timing
    zero=~positive
    if any(np.any(zero&(rounded_quality(mu-EPSILON)!=rounded_quality(mu+EPSILON)))
           for mu in (mu0,mu1)):
        result['reason']='exact-zero rounding threshold arithmetic ambiguous'
        return S2Result.model_validate(result),{},timing
    primary=np.where(positive,np.where(tau>0,1.,np.where(tau<0,0.,.5)),
                     np.where(m1>m0,1.,np.where(m1<m0,0.,.5)))
    indicators={'primary':primary}
    for index,(d0,d1) in enumerate(CELLS):
        # Exact algebraic simplification, not a numerically equal probability.
        if (d0==0 and d1==0) or rates==[0.,0.]:
            z=primary.copy()
        else:
            lower0=blend(np.clip(m0-EPSILON,0,10),rates[0],d0)-EPSILON
            upper0=blend(np.clip(m0+EPSILON,0,10),rates[0],d0)+EPSILON
            lower1=blend(np.clip(m1-EPSILON,0,10),rates[1],d1)-EPSILON
            upper1=blend(np.clip(m1+EPSILON,0,10),rates[1],d1)+EPSILON
            # Only proven same-m/same-function equalities are exact ties.
            same_function=(rates[0]==rates[1] and d0==d1) or (
                (rates[0]==0 or d0==0) and (rates[1]==0 or d1==0))
            exact_tie=((positive&(tau==0))|(zero&(m0==m1)))&same_function
            up=lower1>upper0;down=upper1<lower0
            if np.any(~(up|down|exact_tie)):
                result['reason']='at least one required sensitivity sign is unresolved'
                return S2Result.model_validate(result),{},timing
            z=np.where(exact_tie,.5,np.where(up,1.,0.))
        indicators[str(index)]=z
    before=time.perf_counter();cache=[];summaries={}
    for name,z in indicators.items():
        previous=next((summary for old,summary in cache if np.array_equal(old,z)),None)
        if previous is None:
            previous=indicator_diagnostics(z);cache.append((z,previous))
        summaries[name]=dict(previous)
    timing['diagnostics_seconds']=time.perf_counter()-before
    timing['distinct_diagnostic_arrays']=len(cache)
    result['primary']=summaries['primary']
    for index,cell in enumerate(result['cells']):cell['precision']=summaries[str(index)]
    ready=all(s['status']=='candidate_ready' for s in summaries.values())
    same_side=all((s['probability']>.5)==(summaries['primary']['probability']>.5)
                  for s in summaries.values())
    result.update(status='candidate_ready' if ready and same_side else 'probability_unready',
        reason='candidate empirical guards only; no serving authority' if ready and same_side
               else 'primary/cell precision, neutrality or sensitivity reversal',
        probability=summaries['primary']['probability'] if ready and same_side else .5)
    return S2Result.model_validate(result),indicators,timing
