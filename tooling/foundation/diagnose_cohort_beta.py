"""Tiny same-count scalar Beta diagnostic; no cohort graph or inference."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt
from scipy.special import betaln, logit
from scipy.stats import beta as beta_law

sys.path.insert(0,str(Path(__file__).resolve().parent))
from qualify_cohort_symbolic import database, export, cohort_inputs
from diagnose_cohort_factors import clean
from methods.visit.borrow_execution import compilation_options, verify_cvm


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    started=time.monotonic();options=compilation_options();db=database();cohort=export(db);db.close();data=cohort_inputs(cohort)
    observed=sum(len(d['quality']) for _,d in data);reports=sum(d['day'] for _,d in data)
    taken=sum(d['taken'] for _,d in data);deliveries=sum(d['deliveries'] for _,d in data)
    result=dict(no_fit=True,no_cohort_model=True,pooled_counts=dict(observed=observed,reports=reports,taken=taken,deliveries=deliveries),cases=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(clean(result),indent=2,allow_nan=False)+'\n')
    for name,a,b,probability in [('observation_rate',1+observed,1+reports-observed,.8),('p_adherence',1+taken,1+deliveries-taken,.7)]:
        reference=float(beta_law.logpdf(probability,a,b))
        for construction in ('original_python_int','explicit_float64'):
            aa,bb=(a,b) if construction=='original_python_int' else (np.float64(a),np.float64(b))
            rv=pm.Beta.dist(alpha=aa,beta=bb);alpha,beta=rv.owner.inputs[-2:]
            p=pt.dscalar('probability');logp=pm.logp(rv,p)
            normalization=pt.gammaln(alpha+beta)-pt.gammaln(alpha)-pt.gammaln(beta)
            fn=pytensor.function([p],[alpha,beta,alpha+beta,normalization,logp,pt.grad(logp,p)],**options)
            av,bv,total,norm,value,gradient=fn(probability)
            case=dict(name=name,construction=construction,probability=probability,actual_vm=verify_cvm(fn),
                alpha_dtype=alpha.dtype,beta_dtype=beta.dtype,sum_dtype=(alpha+beta).dtype,
                alpha=float(av),beta=float(bv),alpha_plus_beta=float(total),normalizer=float(norm),
                scipy_normalizer=float(-betaln(a,b)),logp=float(value),scipy_logp=reference,
                difference=float(value)-reference,gradient=float(gradient),
                scipy_gradient=(a-1)/probability-(b-1)/(1-probability))
            # Also inspect the ordinary model's unchanged logodds transform at
            # the exact physical probability; no NUTS initialization or fit.
            with pm.Model() as model:pm.Beta('rate',alpha=aa,beta=bb)
            transformed=model.compile_logp(jacobian=False,**options)
            case['transformed_logp']=float(transformed({'rate_logodds__':np.array(logit(probability))}))
            result['cases'].append(case);save();print(json.dumps(clean(case)),flush=True)
    result['seconds']=time.monotonic()-started;save()


if __name__=='__main__':main()
