"""Container-only UNIT API/file seam. Never import or execute on the host."""
def main():
    import os
    import sys
    if sys.platform!='linux' or os.environ.get('REMISSION_N_API_UNIT')!='UNIT-API02-91740203':
        raise RuntimeError('isolated reviewed UNIT container required')
    from datetime import date
    import hashlib
    import json
    from pathlib import Path
    from types import SimpleNamespace
    sys.path.insert(0,'/app')
    import numpy as np
    import xarray as xr
    from contracts.domain.nof1_app import MONITORED
    from services.learner.nof1_worker import effect_diagnostics
    from services.learner.nof1_artifacts import validate

    out=Path('/tmp/n-api02-unit');out.mkdir(exist_ok=False)
    seed,domain=91740203,9202
    rng=np.random.default_rng(np.random.SeedSequence([seed,domain]))
    patients=['UNIT-API02-A','UNIT-API02-B'];target=patients[1]
    chains,draws=4,1000;shape=(chains,draws)
    history=hashlib.sha256(b'UNIT-API02-no-patient-data').hexdigest()
    product=SimpleNamespace(cohort=[SimpleNamespace(patient_id=p) for p in patients],target_id=target,
        histories=[SimpleNamespace(patient_id=p,origin=date(2026,1,1),cutoff=date(2026,1,15)) for p in patients],
        history_sha256=history)
    variables={name:(('chain','draw'),rng.normal(size=shape)) for name in MONITORED}
    for name in ('b','current_error','p_C','p_M','q'):
        variables[name]=(('chain','draw','patient'),rng.normal(size=(*shape,2)))
    variables['patient_amplitude']=(('chain','draw','patient','coefficient'),rng.normal(size=(*shape,2,5)))
    posterior=xr.Dataset(variables,coords=dict(chain=np.arange(chains),draw=np.arange(draws),
        patient=patients,coefficient=['C','E','A','B','R'],night_0=np.arange(-13,15),night_1=np.arange(-13,15)))
    stats=xr.Dataset(dict(energy=(('chain','draw'),rng.normal(size=shape)),
        diverging=(('chain','draw'),np.zeros(shape,dtype=bool)),tree_depth=(('chain','draw'),np.ones(shape,dtype=np.int64))))
    tree=xr.DataTree.from_dict({'posterior':posterior,'sample_stats':stats})
    tree.to_netcdf(out/'posterior.nc',engine='netcdf4')
    effect=np.clip(rng.normal(.15,.2,size=(*shape,1)),-1,1).astype(np.float64)
    diagnostics=effect_diagnostics(effect)
    for name in ('rhat','ess_bulk','ess_tail','mcse'):
        value=diagnostics[name]['expected_contrast']
        if value is None or not np.isfinite(value):raise ValueError('UNIT nonfinite actual diagnostics')
    summary=dict(mean=float(effect.mean()),sd=float(effect.std(ddof=1)),
        lower=float(np.quantile(effect,.025)),upper=float(np.quantile(effect,.975)))
    axes=dict(chain=np.arange(chains),draw=np.arange(draws),target=np.array([target]),history_sha256=np.array(history))
    expected=dict(effect=effect,**axes,axes=np.array(['chain','draw','target']),unit=np.array('quality_points'),
        kind=np.array('conditional_expected_assignment_contrast'))
    quality=np.round(rng.uniform(0,10,size=(*shape,1,2,7)),3).astype(np.float64)
    available=rng.random((*shape,1,7))>.25
    if available.all() or not available.any():raise ValueError('UNIT mask must exercise available and unavailable')
    predictive=dict(quality=quality,available=available,**axes,arm=np.array(['MED_A','MED_B']),night=np.arange(15,22),
        axes=np.array(['chain','draw','target','arm','night']),unit=np.array('reported_quality_points'),kind=np.array('predictive_trajectory'))
    def save(name,value):np.savez_compressed(out/name,**value)
    save('expected-contrast.npz',expected);save('predictive.npz',predictive)
    semantics=validate(out,product,summary)
    controls=[]
    for name,field,value in [('target','target',np.array([patients[0]])),('dtype','effect',effect.astype(np.float32)),
            ('axes','axes',np.array(['draw','chain','target'])),('unit','unit',np.array('unknown'))]:
        changed={**expected,field:value};save('expected-contrast.npz',changed)
        digest=hashlib.sha256((out/'expected-contrast.npz').read_bytes()).hexdigest()
        try:validate(out,product,summary)
        except ValueError:controls.append(dict(control=name,rehashed_sha256=digest,rejected=True))
        else:raise AssertionError('UNIT corrupt artifact accepted: '+name)
        save('expected-contrast.npz',expected)
    save('predictive.npz',{**predictive,'available':available.astype(np.int64)})
    try:validate(out,product,summary)
    except ValueError:controls.append(dict(control='predictive-mask-dtype',rejected=True))
    else:raise AssertionError('UNIT nonboolean availability accepted')
    save('predictive.npz',predictive)
    try:validate(out,product,{**summary,'sd':summary['sd']+.01})
    except ValueError:controls.append(dict(control='summary-sd',rejected=True))
    else:raise AssertionError('UNIT serialized summary disagreement accepted')
    validate(out,product,summary)
    print(json.dumps(dict(kind='N-API02-UNIT-ONLY',seed=seed,domain=domain,target=target,patients=patients,
        diagnostics=diagnostics,summary=summary,semantics=semantics,controls=controls,
        artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir())},
        model_fitted=False,genuine_data=False,Store_opened=False),sort_keys=True,allow_nan=False))

if __name__=='__main__':main()
