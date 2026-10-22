"""Proposed nominal-law singleton criterion; execution needs reviewed amendment."""
import argparse,copy,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qualify_cohort_symbolic import database,export,cohort_inputs,build_cohort,build,original_point,density
from diagnose_cohort_factors import independent_factors,clean
from methods.visit.borrow_execution import compilation_options,verify_cvm,optimizer_identity


def reshape_to_legacy(point):
    result=copy.deepcopy(point)
    assert result['b_raw'].shape==(1,) and result['beta_raw'].shape==(1,2)
    assert result['innovation'].ndim==2 and result['innovation'].shape[0]==1
    for name in ('b_raw','beta_raw','innovation'):
        result[name]=result[name][0]
        np.testing.assert_array_equal(np.asarray(result[name])[None],point[name])
    return result


def stress_design(data,history):
    """Algebraic basis only, never an observed-input export or stored history."""
    d=copy.deepcopy(data);c=[];e=[];previous_c=previous_e=0.
    deliveries={int((r.event_at-history.origin).total_seconds()//86400)+1:r
                for r in history.records if r.kind=='delivery'}
    for night in d['nights']:
        record=deliveries.get(int(night));taken=record is not None and record.stage=='taken'
        previous_c=.65*previous_c+.35*int(taken and night<=7)
        previous_e=.8*previous_e+.2*int(taken and night>7)
        c.append(previous_c);e.append(previous_e)
    assert len(deliveries)==d['deliveries'] and sum(r.stage=='taken' for r in deliveries.values())==d['taken']
    d.update(c=np.array(c),e=np.array(e))
    assert d['c'].max()>0 and d['e'].max()>0
    return d


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    options=compilation_options()
    result=dict(kind='proposed_nominal_singleton_qualification',no_fit=True,
        preflight=dict(optimizer=optimizer_identity(options['mode'].provided_optimizer),guard_pass=True),cases=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(clean(result),indent=2,allow_nan=False)+'\n')
    save();db=database()
    try:cohort=export(db)
    finally:db.close()
    patient,observed=cohort_inputs(cohort)[0]
    designs=[('archived_observed_contract_fixture',observed),
             ('algebraic_both_arm_exposure_stress_NOT_observed_job',stress_design(observed,cohort.histories[0]))]
    for design,d in designs:
        data=[(patient,d)];model=build_cohort(data,guide=False);legacy=build(d,guide=False)
        factors=model.compile_logp(sum=False,jacobian=False,**options)
        joint=model.compile_logp(jacobian=False,**options);gradient=model.compile_dlogp(jacobian=False,**options)
        raw_factors=legacy.compile_logp(sum=False,jacobian=False,**options)
        raw_joint=legacy.compile_logp(jacobian=False,**options)
        for fn in (factors,joint,gradient,raw_factors,raw_joint):verify_cvm(fn.f)
        labels=[r.name for r in model.free_RVs]+[r.name for r in model.potentials]
        raw_labels=[r.name for r in legacy.free_RVs]+[r.name for r in legacy.potentials]
        for index in (0,1):
            point=original_point(model,1,len(d['nights']))
            if index:
                point.update(mu_b=np.array(17.4),population_beta=np.array([1.3,2.4]),a=np.array(-.3),
                    b_raw=np.array([.4]),beta_raw=np.array([[-.25,.35]]),
                    innovation=(.13*np.cos(np.arange(len(d['nights'])))+.03)[None],
                    rho_interval__=np.array(np.log((-.31+.95)/(.95-(-.31)))))
            old=reshape_to_legacy(point);assert set(old)==set(legacy.initial_point())
            reference=independent_factors(data,point);expected=density(data,point)
            actual=float(joint(copy.deepcopy(point)));parts=factors(copy.deepcopy(point))
            residuals={name:float(np.max(np.abs(np.asarray(value)-reference[name]))) for name,value in zip(labels,parts,strict=True)}
            rng=np.random.default_rng(8129+index)
            direction={k:rng.normal(size=np.asarray(v).shape) for k,v in point.items()}
            epsilon=1e-5
            finite=(density(data,{k:v+epsilon*direction[k] for k,v in point.items()})-
                    density(data,{k:v-epsilon*direction[k] for k,v in point.items()}))/(2*epsilon)
            flat=np.concatenate([np.asarray(direction[v.name]).ravel() for v in model.continuous_value_vars])
            autodiff=float(np.dot(gradient(copy.deepcopy(point)),flat))
            raw=float(raw_joint(copy.deepcopy(old)));raw_parts=raw_factors(copy.deepcopy(old))
            raw_residuals={name:float(np.max(np.abs(np.asarray(value)-np.asarray(reference[name+'_0' if name in ('isi_likelihood','quality_likelihood') else name]).reshape(np.asarray(value).shape))))
                           for name,value in zip(raw_labels,raw_parts,strict=True)}
            wrong=copy.deepcopy(point);wrong['population_beta']=wrong['population_beta'][::-1]
            gates=dict(nominal_density_absolute_1e_8=bool(abs(actual-expected)<=1e-8),
                nominal_factors_absolute_1e_8=all(v<=1e-8 for v in residuals.values()),
                mapped_directional_gradient=bool(abs(autodiff-finite)<=1e-5+1e-4*abs(finite)),
                wrong_arm_mapping_detected=bool(abs(density(data,wrong)-expected)>1e-7))
            result['cases'].append(dict(design=design,point_index=index,point=point,gates=gates,
                nominal_joint=actual,independent_joint=expected,nominal_factor_residuals=residuals,
                gradient=dict(autodiff=autodiff,independent_finite_difference=finite,epsilon=epsilon),
                raw_legacy=dict(joint=raw,delta_to_cohort=actual-raw,absolute_tolerance=1e-8,
                    passed=bool(abs(actual-raw)<=1e-8),factor_residuals=raw_residuals)))
            save()
    result['nominal_singleton_passed']=all(all(case['gates'].values()) for case in result['cases'])
    result['raw_legacy_compatibility_passed']=all(case['raw_legacy']['passed'] for case in result['cases'])
    result['production_executable']=False;save()
    if not result['nominal_singleton_passed']:raise SystemExit(1)


if __name__=='__main__':main()
