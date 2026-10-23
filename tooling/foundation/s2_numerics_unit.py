"""Fixed S2 numerical/API/cost qualification SOURCE. Never run on the host.

Public structural arrays, not fits or genuine data. No Store/API/model worker.
The companion fixed-path carrier hashes all new source before importing it.
"""
import base64
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import resource
import time

import numpy as np
from scipy.special import ndtr
from contracts.domain.analysis import sha
from contracts.domain.support_s2 import CONFIG_REF,DEFINITIONS,HSTAR_REF,S2Request
from methods.support.s2_prediction import action_moments,blend,checked_arrays,indicator_diagnostics,predict
from methods.nof1.observation import expected_quality
from s2_numerics_oracle import cdf,full_case

ROOT=Path('/qualification')
SEED=91740323
DEADLINE=None


def deadline():
    if DEADLINE is None or time.monotonic()>=DEADLINE:raise TimeoutError('S2 work lease expired')


def scalar_cases(value):
    results=[]
    for case in value:
        deadline()
        values=[case[k] for k in ('alpha','tau','rho','e_T','s_e','s_Q','r0','r1')]+case['b']+case['x']
        scalar_support=(len(case['b'])==4 and len(case['x'])==4
            and all(type(v) in (int,float) and math.isfinite(v) for v in values)
            and type(case['h']) is int and 1<=case['h']<=14
            and -.95<case['rho']<.95 and case['s_e']>=0 and case['s_Q']>=0
            and 0<=case['r0']<=1 and 0<=case['r1']<=1)
        if not scalar_support:
            if case['expected_domain']!='reject':raise ValueError('scalar support mismatch')
            results.append(dict(id=case['id'],domain='rejected'));continue
        a={k:np.asarray(case[k],dtype=np.float64) for k in ('alpha','tau','rho','e_T','s_e','s_Q')}
        a['b']=np.asarray(case['b'],dtype=np.float64)
        try:
            m0,m1,sd=action_moments(**a,x=case['x'],h=case['h'])
            admitted=(all(-40<=float(v)<=50 for v in (m0,m1))
                      and (float(sd)==0 or 1e-6<=float(sd)<=40))
        except ValueError:admitted=False
        if admitted!=(case['expected_domain']=='admit'):raise ValueError('scalar domain admission mismatch: '+case['id'])
        if not admitted:
            results.append(dict(id=case['id'],domain='rejected'));continue
        oracle=full_case(case)
        q=[float(expected_quality(m0,sd)),float(expected_quality(m1,sd))]
        discrepancies=[]
        for action,mean in enumerate((m0,m1)):
            ref=oracle['actions'][action]
            # Compare full independently formed mean/variance as well as g.
            if max(abs(float(mean)-ref['mean']),abs(float(sd)-ref['sd']))>1e-10:
                raise ValueError('full AR arithmetic differs from oracle')
            discrepancies.append(abs(q[action]-ref['quality']))
        for cell in oracle['cells']:
            for arm in (0,1):
                v=float(blend(np.asarray(q[arm]),case['r'+str(arm)],cell['delta'+str(arm)]))
                discrepancies.append(abs(v-cell['action'+str(arm)]))
        if max(discrepancies)>1e-9:raise ValueError('S2 full-action/blend discrepancy exceeds epsilon/10')
        results.append(dict(id=case['id'],domain='admitted',oracle=oracle,
                            maximum_discrepancy=max(discrepancies)))
    return results


def request(target,draws):
    ids=[f'UNIT-S2-{i:02}' for i in range(12)]
    return S2Request.model_validate(dict(schema_version='s2-prediction-candidate-1.0.0',
        owner_id='UNIT-owner',store_id='UNIT-store',generation_id='UNIT-generation',cohort_id='UNIT-cohort',
        fit_id='UNIT-structural-NOT-fit',fit_artifact_sha256='0'*64,fitted_hstar=HSTAR_REF,
        fitted_snapshot_sha256='1'*64,configuration=CONFIG_REF,definitions=DEFINITIONS,
        members=tuple(dict(patient_id=id,patient_version=1,history_sha256='2'*64,
            revisions_sha256='3'*64,observed=(5,4),missing=(1,2)) for id in ids),
        cutoff=14,target_id=target,context_id=f'UNIT-context-{draws}-{target}',context_version=1,
        current_snapshot_sha256='4'*64,decision_day=20,reward_day=21,h=7,
        expires_before_decision=28,x_current=(7.,0.,2.,.25)))


def correlated(rng,shape,mean,scale):
    value=rng.normal(0,scale,shape)
    # Original chains retained. Deliberately correlated structural fixtures.
    for draw in range(1,shape[1]):value[:,draw]=.6*value[:,draw-1]+value[:,draw]
    return value+mean


def fixture(draws):
    rng=np.random.default_rng(SEED+draws);shape=(4,draws)
    return dict(alpha=correlated(rng,shape+(12,),5.,.08),
        tau=correlated(rng,shape+(12,),.65,.6),e_T=correlated(rng,shape+(12,),0.,.1),
        b=correlated(rng,shape+(4,),0.,.003),rho=np.full(shape,.6),
        s_e=np.full(shape,.3),s_Q=np.full(shape,.4))


def diagnostic_controls():
    rng=np.random.default_rng(SEED)
    z=(correlated(rng,(4,1000),.4,1.)>0).astype(np.float64)
    report={'correlated':indicator_diagnostics(z)}
    constant=z.copy();constant[2]=1.
    report['constant_chain']=indicator_diagnostics(constant)
    if report['constant_chain']['status']!='probability_unready_constant_chain':
        raise ValueError('constant chain was accepted')
    # Half/full drift and separated chains remain original, not thinned.
    drift=z.copy();drift[:,:500]=0.;drift[:,500:]=1.
    report['drift']=indicator_diagnostics(drift)
    separated=z.copy();separated[0]=1.-z[0]
    report['separated']=indicator_diagnostics(separated)
    if report['drift']['status']=='candidate_ready':raise ValueError('drifting indicator was accepted')
    return report


def boundary_controls():
    ids=[f'UNIT-S2-{i:02}' for i in range(12)];context=request(ids[7],1000);arrays=fixture(1000)
    if checked_arrays(arrays,ids,context)!=7:raise ValueError('explicit nonfirst target was not selected')
    rejected=[]
    for name in ('chain-axis','feature-axis','float32','nonfinite','rho-support','member-order'):
        changed=dict(arrays);order=list(ids)
        if name=='chain-axis':changed['alpha']=changed['alpha'][:3]
        elif name=='feature-axis':changed['b']=changed['b'][:,:,:3]
        elif name=='float32':changed['tau']=changed['tau'].astype('float32')
        elif name=='nonfinite':changed['e_T']=changed['e_T'].copy();changed['e_T'][0,0,7]=np.nan
        elif name=='rho-support':changed['rho']=np.full((4,1000),.95)
        else:order.reverse()
        try:checked_arrays(changed,order,context)
        except ValueError:rejected.append(name)
        else:raise ValueError('joint-array counterexample accepted')
    for name in ('domain','positive-underflow','unresolved-sign','zero-constant-chain','missing-arm'):
        changed=copy.deepcopy(arrays);wire=context.model_dump();wire['members']=tuple(wire['members'])
        if name=='domain':changed['alpha'][:]=200.
        elif name=='positive-underflow':changed['s_e'][:]=0.;changed['s_Q'][:]=1e-200
        elif name=='unresolved-sign':
            changed['tau'][:]=1e-12
            for member in wire['members']:member.update(observed=(5,5),missing=(1,1))
        elif name=='zero-constant-chain':
            for key in ('tau','b','e_T','s_e','s_Q'):changed[key][:]=0.
            changed['alpha'][:]=5.
            for member in wire['members']:member.update(observed=(6,6),missing=(0,0))
        else:
            wire['members'][7].update(observed=(0,6),missing=(0,1))
        result,indicators,_=predict(S2Request.model_validate(wire),changed,ids)
        expected=('arm_unavailable' if name=='missing-arm' else
                  'probability_unready' if name=='zero-constant-chain' else 'numerical_unready')
        if result.status!=expected or len(result.cells)!=9:raise ValueError('S2 failure guard changed')
        if name=='zero-constant-chain' and any(cell.precision.status!='probability_unready_constant_chain' for cell in result.cells):
            raise ValueError('zero-noise constant indicator accepted')
        rejected.append(name)
    return rejected


def main(draws,work_seconds):
    global DEADLINE
    started=time.monotonic();DEADLINE=started+work_seconds
    if draws not in (1000,2000) or not 0<work_seconds<=300:raise ValueError('fixed child size/lease required')
    cost=[];saved={};ids=[f'UNIT-S2-{i:02}' for i in range(12)]
    arrays=fixture(draws);saved.update({f'draw{draws}_{key}':v for key,v in arrays.items()})
    previous={}
    # First pass precedes scalar/CDF work, so its reference calls are genuinely
    # first use in this fresh Python process. OS/image caches are not reset.
    for run in ('cold','warm'):
        phase=time.monotonic();rows=[]
        for target in ids:
            deadline();context=request(target,draws)
            result,indicators,timing=predict(context,arrays,ids)
            if set(indicators)!={'primary',*(str(i) for i in range(9))}:
                raise ValueError('complete target context produced no complete indicator set')
            if run=='cold':
                previous[target]=result.model_dump(mode='json')
                saved.update({f'draw{draws}_{target}_{key}':z for key,z in indicators.items()})
            elif previous[target]!=result.model_dump(mode='json'):
                raise ValueError('cold/warm scalar result changed')
            else:
                for key,z in indicators.items():
                    if not np.array_equal(saved[f'draw{draws}_{target}_{key}'],z):
                        raise ValueError('warm recomputed indicator arrays changed')
            rows.append(dict(target=target,result=result.model_dump(mode='json'),timing=timing))
        elapsed=time.monotonic()-phase
        cost.append(dict(draws=draws,chains=4,targets=12,run=run,seconds=elapsed,contexts=rows))
    if not any(row['result']['status']=='candidate_ready' for run in cost for row in run['contexts']):
        raise ValueError('all-fallback fixture cannot pass functional numerical qualification')
    scalar=[];cdf_report=[];diagnostic={};scalar_seconds=0.
    if draws==1000:
        fixed=json.loads((ROOT/'fixed.json').read_text(encoding='utf-8'))
        held=json.loads((ROOT/'held-out.json').read_text(encoding='utf-8'))
        if (len(fixed['scalar'])!=64 or len(fixed['cdf'])!=16
                or len(held['scalar_cases'])!=32 or len(held['cdf_cases'])!=16):raise ValueError('frozen96/32 case counts required')
        phase=time.monotonic();scalar=scalar_cases(fixed['scalar']+held['scalar_cases'])
        for case in fixed['cdf']+held['cdf_cases']:
            discrepancy=abs(float(ndtr(case['z']))-cdf(case['z']))
            if discrepancy>1e-10:raise ValueError('CDF independent erfc discrepancy')
            cdf_report.append(dict(id=case['id'],absolute_error=discrepancy))
        scalar_seconds=time.monotonic()-phase;diagnostic=diagnostic_controls()
        diagnostic['boundary_rejections']=boundary_controls()
    deadline()
    buffer=io.BytesIO();np.savez_compressed(buffer,**saved);raw=buffer.getvalue()
    # New exact workload transport proposal, not ordinary CLI capture expansion.
    if not 0<len(raw)<=8*1024*1024:raise ValueError('structural artifact8MiB ceiling exceeded')
    output=dict(kind='S2-NUMERICS-STRUCTURAL-ONLY',draws=draws,seed=SEED,model_fitted=False,genuine_data=False,
        serving_authority=False,empirical_not_uniform=True,scalar=scalar,cdf=cdf_report,
        diagnostics=diagnostic,cost=cost,scalar_seconds=scalar_seconds,elapsed_seconds=time.monotonic()-started,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        artifact=dict(name=f'structural-{draws}.npz',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                      base64=base64.b64encode(raw).decode('ascii')))
    encoded=json.dumps(output,separators=(',',':'),allow_nan=False)
    if len(encoded.encode())+1>12*1024*1024:raise ValueError('S2 complete JSON stdout12MiB ceiling exceeded')
    return encoded
