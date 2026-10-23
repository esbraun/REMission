"""Fixed S2 numerical/API/cost qualification SOURCE. Never run on the host.

Public structural arrays, not fits or genuine data. No Store/API/model worker.
The companion fixed-path carrier hashes all new source before importing it.
"""
import base64
import hashlib
import io
import json
from pathlib import Path
import resource
import time

import numpy as np
from scipy.special import ndtr
from contracts.domain.analysis import sha
from contracts.domain.support_s2 import CONFIG_REF,DEFINITIONS,HSTAR_REF,S2Request
from methods.support.s2_prediction import action_moments,blend,indicator_diagnostics,predict
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
            revisions_sha256='3'*64,observed=(8,7),missing=(2,3)) for id in ids),
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


def main():
    global DEADLINE
    started=time.monotonic();DEADLINE=started+600
    fixed=json.loads((ROOT/'fixed.json').read_text(encoding='utf-8'))
    held=json.loads((ROOT/'held-out.json').read_text(encoding='utf-8'))
    if (len(fixed['scalar'])!=64 or len(fixed['cdf'])!=16
            or len(held['scalar'])!=32 or len(held['cdf'])!=16):raise ValueError('frozen96/32 case counts required')
    phase=time.monotonic();scalar=scalar_cases(fixed['scalar']+held['scalar']);cdf_report=[]
    for case in fixed['cdf']+held['cdf']:
        discrepancy=abs(float(ndtr(case['z']))-cdf(case['z']))
        if discrepancy>1e-10:raise ValueError('CDF independent erfc discrepancy')
        cdf_report.append(dict(id=case['id'],absolute_error=discrepancy))
    scalar_seconds=time.monotonic()-phase
    if scalar_seconds>300:raise TimeoutError('proposed scalar segment300s exceeded')
    diagnostic=diagnostic_controls();cost=[];saved={};ids=[f'UNIT-S2-{i:02}' for i in range(12)]
    for draws in (1000,2000):
        arrays=fixture(draws)
        saved.update({f'draw{draws}_{key}':v for key,v in arrays.items()})
        previous={}
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
                rows.append(dict(target=target,result=result.model_dump(mode='json'),timing=timing))
            elapsed=time.monotonic()-phase
            if elapsed>300:raise TimeoutError('proposed full-context segment300s exceeded')
            cost.append(dict(draws=draws,chains=4,targets=12,run=run,seconds=elapsed,contexts=rows))
    if not any(row['result']['status']=='candidate_ready' for run in cost for row in run['contexts']):
        raise ValueError('all-fallback fixture cannot pass functional numerical qualification')
    deadline()
    buffer=io.BytesIO();np.savez_compressed(buffer,**saved);raw=buffer.getvalue()
    # New exact workload transport proposal, not ordinary CLI capture expansion.
    if not 0<len(raw)<=8*1024*1024:raise ValueError('structural artifact8MiB ceiling exceeded')
    output=dict(kind='S2-NUMERICS-STRUCTURAL-ONLY',seed=SEED,model_fitted=False,genuine_data=False,
        serving_authority=False,empirical_not_uniform=True,scalar=scalar,cdf=cdf_report,
        diagnostics=diagnostic,cost=cost,elapsed_seconds=time.monotonic()-started,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        artifact=dict(name='structural.npz',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                      base64=base64.b64encode(raw).decode('ascii')))
    encoded=json.dumps(output,separators=(',',':'),allow_nan=False)
    if len(encoded.encode())+1>12*1024*1024:raise ValueError('S2 complete JSON stdout12MiB ceiling exceeded')
    print(encoded)


if __name__=='__main__':main()
