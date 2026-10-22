"""Same original graph/physical point factor diagnostic; no inference or repair."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from qualify_cohort_symbolic import database, export, cohort_inputs, build_cohort, original_point, density, MODE
from methods.visit.borrow_execution import compilation_options, verify_cvm


def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,np.ndarray):return clean(value.tolist())
    if isinstance(value,(float,np.floating)):
        return float(value) if np.isfinite(value) else ('+inf' if value>0 else '-inf' if value<0 else 'nan')
    return value


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    started=time.monotonic();db=database();cohort=export(db);db.close();data=cohort_inputs(cohort)
    model=build_cohort(data,guide=False);point=original_point(model,12,len(data[0][1]['nights']))
    result=dict(source='Original12-member graph and exact interior physical point from r2, unchanged fixture/model/settings',
        no_fit=True,independent_density=density(data,point),point=point,modes={})
    def save():args.output.write_text(json.dumps(clean(result),indent=2,allow_nan=False)+'\n')
    args.output.parent.mkdir(parents=True,exist_ok=True);save()
    labels=[rv.name for rv in model.free_RVs]+[rv.name for rv in model.observed_RVs]+[rv.name for rv in model.potentials]
    for name,mode in [('diagnostic_fast_compile_cvm',MODE),('production_unchanged_cvm',compilation_options()['mode'])]:
        began=time.monotonic();values=copy.deepcopy(point)
        factors=model.compile_logp(sum=False,jacobian=False,mode=mode)
        actual=factors(values)
        metadata=dict(actual_vm=verify_cvm(factors.f),factors=[],point_unchanged=all(np.array_equal(values[k],point[k]) for k in point))
        assert len(labels)==len(actual)
        for label,array in zip(labels,actual,strict=True):
            array=np.asarray(array)
            metadata['factors'].append(dict(name=label,shape=list(array.shape),sum=float(np.sum(array)),
                finite=bool(np.isfinite(array).all()),values=array))
        metadata['factor_sum']=float(sum(np.sum(x) for x in actual));result['modes'][name]=metadata;save()
        fn=model.compile_logp(jacobian=False,mode=mode)
        value=float(fn(copy.deepcopy(point)))
        metadata.update(compiled_sum=value,difference_from_independent=value-result['independent_density'],
            seconds=time.monotonic()-began,point_unchanged_after_sum=all(np.array_equal(values[k],point[k]) for k in point))
        save();print(json.dumps(clean(dict(mode=name,compiled_sum=value,factor_sum=metadata['factor_sum'],seconds=metadata['seconds']))),flush=True)
    result['seconds']=time.monotonic()-started;save()


if __name__=='__main__':main()
