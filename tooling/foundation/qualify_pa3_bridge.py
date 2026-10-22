"""Frozen PA3 prefit reference family. Writes each inspected scheduled look."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy.stats import norm
from methods.visit.borrowing import (ALPHA, FAMILY_TESTS, FIELDS, LOOKS, REFERENCE_ORDERS,
    QUALIFICATION_SECONDS, fixed_vectors, marginal, quadrature)
from tests.methods.pa3_reference import forward


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def key_seed(scenario, point, batch, purpose):
    key=['pa3-bridge-20261021-v1',scenario,-1,batch,point,42,purpose]
    return int.from_bytes(hashlib.sha256(canonical(key).encode()).digest()[:4], 'big')


def freeze(studies):
    rng=np.random.default_rng(key_seed(-1,-1,-1,'prior-check'))
    prior=[]
    for _ in range(64):
        prior.append(dict(mu_b=float(rng.normal(19,5)), beta_c=float(rng.normal(0,4)), beta_e=float(rng.normal(0,4)),
            sd_b=float(abs(rng.normal(0,3))), sd_beta_c=float(abs(rng.normal())), sd_beta_e=float(abs(rng.normal())),
            p=float(rng.beta(1,1)), rho=float(rng.uniform(-.95,.95)), sigma_e=float(abs(rng.normal(0,2))),
            sigma_isi=float(abs(rng.normal(0,2))), a=float(rng.normal())))
    vectors=prior+fixed_vectors()
    epsilons=[min(.05,.1*s['se']) for s in studies]
    nodes={str(order):dict(nodes=quadrature(order)[0].tolist(),weights=quadrature(order)[1].tolist()) for order in (16,32,64,128)}
    return dict(schema='pa3-bridge-qualification-v1', family_id='pa3-prefit-reference-20261022-v1',
        information_set='public-fitted-model; original-prior theta; independent exact-adherence/AR forward reference',
        truth_scope='source-population marginal reference, not PA6 private H*-conditional truth',
        production_orders=list(REFERENCE_ORDERS), quadrature=nodes, prior_vectors=64, stress_vectors=24,
        vectors=vectors, reference_seed_keys=[[key_seed(0,i,b,'bridge-reference') for b in range(8)] for i in range(88)],
        batches=8, looks=list(LOOKS), epsilon_per_study=epsilons, studies=studies,
        alpha=ALPHA, family_tests=FAMILY_TESTS, z=float(norm.isf(ALPHA/(2*FAMILY_TESTS))),
        seconds_cap=QUALIFICATION_SECONDS, posterior_reference_points=32,
        multiplicity_scope='approximate normal-mean Bonferroni bound conditional on fixed points; six scheduled looks; no alpha reuse')


def diagnosis(reference_pass, significant_discrepancy, resolution_pass):
    if not resolution_pass:
        return 'quadrature-resolution-unmet'
    if significant_discrepancy:
        return 'moment-approximation-failure'
    return 'accepted' if reference_pass else 'reference-precision-unmet'


def run(manifest, out, order):
    out.mkdir(parents=True,exist_ok=False)
    manifest=dict(manifest,production_order=order,qualification_version='pa3-prefit-v1.0.1',
        deadline_rule='check before/after each batch, point publication and final acceptance; external watchdog cap+60 seconds')
    (out/'frozen-manifest.json').write_text(canonical(manifest)+'\n')
    started=time.monotonic(); points=[]; cap=manifest['seconds_cap']; timed_out=False
    def expired():return time.monotonic()-started>cap
    for i, theta in enumerate(manifest['vectors']):
        if expired():timed_out=True;break
        g=marginal(theta,order); doubled=marginal(theta,2*order)
        resolution=abs(doubled-g)
        streams=[np.random.default_rng(s) for s in manifest['reference_seed_keys'][i]]
        count=0; total=0.; square=0.; looks=[]
        epsilon=min(manifest['epsilon_per_study'])
        for size in manifest['looks']:
            if expired():timed_out=True;break
            completed_batches=0
            for rng in streams:
                if expired():timed_out=True;break
                values=forward(theta,size-count,rng)
                total+=float(values.sum()); square+=float(values@values)
                completed_batches+=1
                if expired():timed_out=True;break
            if timed_out:
                looks.append(dict(per_batch=size,status='interrupted',completed_batches=completed_batches))
                break
            count=size
            n=8*count; mean=total/n; variance=max(0.,(square-total**2/n)/(n-1)); se=(variance/n)**.5
            bound=abs(g-mean)+manifest['z']*se
            lower=max(0.,abs(g-mean)-manifest['z']*se)
            looks.append(dict(per_batch=size, trajectories=n, mean=mean, paired_se=se,
                absolute_discrepancy=abs(g-mean), upper_error_bound=bound, lower_error_bound=lower,
                reference_pass=bound<=epsilon, moment_failure=lower>epsilon))
            if bound <= epsilon:
                break
        last=looks[-1] if looks else {}
        if expired():timed_out=True
        point=dict(index=i, theta=theta, order=order, g=g, doubled_g=doubled,
            resolution_difference=resolution, resolution_tolerance=epsilon/4,
            resolution_pass=resolution<=epsilon/4, looks=looks,
            accepted=bool(not timed_out and last.get('reference_pass') and resolution<=epsilon/4),
            diagnosis='qualification-timeout' if timed_out else diagnosis(last.get('reference_pass',False),last.get('moment_failure',False),resolution<=epsilon/4))
        points.append(point)
        (out/'points.json').write_text(canonical(points)+'\n')
        print(canonical(dict(index=i, diagnosis=point['diagnosis'], g=g, resolution=resolution,
            last=last, seconds=time.monotonic()-started)),flush=True)
        if timed_out:
            break
    peak=Path('/sys/fs/cgroup/memory.peak')
    if expired():timed_out=True
    result=dict(status='accepted' if not timed_out and len(points)==88 and all(p['accepted'] for p in points) else 'not-qualified',
        seconds=time.monotonic()-started, points_completed=len(points), order=order,
        timed_out=timed_out,
        cgroup_peak_memory_bytes=int(peak.read_text()) if peak.exists() else None,
        diagnoses={name:sum(p['diagnosis']==name for p in points) for name in sorted({p['diagnosis'] for p in points})},
        manifest_sha256=hashlib.sha256((out/'frozen-manifest.json').read_bytes()).hexdigest(),
        points_sha256=hashlib.sha256((out/'points.json').read_bytes()).hexdigest())
    (out/'result.json').write_text(canonical(result)+'\n'); print(canonical(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sources',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--order',type=int,choices=REFERENCE_ORDERS,default=16)
    args=parser.parse_args(); studies=json.loads(args.sources.read_text())['studies']
    run(freeze(studies),args.output,args.order)
