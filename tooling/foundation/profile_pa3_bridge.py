"""Measured cold compile and repeated source logp/gradient cost at frozen Q64."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pytensor
import pytensor.tensor as pt
from contracts.domain.borrowing import SourceBundle
from methods.visit.borrowing import BASE,FIELDS,tensor_marginal,tensor_mixture


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sources',type=Path,required=True);args=parser.parse_args()
    bundle=SourceBundle.model_validate_json(args.sources.read_bytes())
    vector=pt.dvector('theta-and-source-nuisance')
    theta={name:vector[i] for i,name in enumerate(FIELDS)}
    g=tensor_marginal(theta,64)
    logp=sum(tensor_mixture(study.d,study.se,g,vector[11+i],vector[13])[0] for i,study in enumerate(bundle.studies))
    start=time.monotonic();value=pytensor.function([vector],logp);value_compile=time.monotonic()-start
    start=time.monotonic();gradient=pytensor.function([vector],pt.grad(logp,vector));gradient_compile=time.monotonic()-start
    point=np.array([*BASE,0.,0.,1.]);expected=float(value(point));grad=gradient(point)
    measurements={}
    for name,fn in [('logp',value),('gradient',gradient)]:
        times=[]
        for _ in range(100):
            start=time.perf_counter();computed=fn(point);times.append(time.perf_counter()-start)
            if not np.isfinite(computed).all():raise ValueError('nonfinite profile result')
        measurements[name]=dict(repeats=100,median_seconds=float(np.median(times)),p95_seconds=float(np.quantile(times,.95)))
    peak=Path('/sys/fs/cgroup/memory.peak')
    print(json.dumps(dict(scope='two summary likelihood terms only; not full local model/NUTS or accepted inference',
        order=64,source_set_sha256=bundle.source_set_sha256,logp=expected,gradient=grad.tolist(),
        compile_seconds=dict(logp=value_compile,gradient=gradient_compile),timing=measurements,
        cgroup_peak_memory_bytes=int(peak.read_text()) if peak.exists() else None,
        source_sha256=hashlib.sha256(Path('/app/methods/visit/borrowing.py').read_bytes()).hexdigest())))


if __name__=='__main__':main()
