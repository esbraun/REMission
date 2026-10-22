"""Joint-cohort lifecycle behind scientific and reviewed runtime admission.

One prior graph is saved/released before one shared posterior is constructed.
All members retain their chain/draw axes and gates; no averaged target exists.
Host claim-to-completion stop/late-ingest veto remains an admission prerequisite.
"""
import gc
import hashlib
import os
from pathlib import Path
import resource
import time
import traceback
from types import SimpleNamespace

import numpy as np
import pymc as pm
import xarray as xr
from contracts.domain.analysis import CONFIG, ESTIMAND_REF, sha
from contracts.domain.cohort import CohortResult, admitted_configuration, require_executable
from contracts.domain.borrow_runtime import cohort_coordinate_layout, runtime_origin
from contracts.domain.cohort_runtime import execution_binding
from methods.visit.cohort_model import cohort_inputs, build_cohort, build_cohort_borrow
from methods.visit.cohort_geometry import patient_parameters
from methods.visit.model import diagnostics
from methods.visit.borrow_execution import compilation_options
from methods.visit.cohort_execution import owned_callables, fit_callback, sample
from methods.visit.numerics import integrate, predictive


def _observed(group, patient, data, seed):
    values=group.sel(patient=patient)
    burden=values['burden'].transpose('chain','draw','night').values
    rng=np.random.default_rng(seed)
    mu=burden[...,data['recall']].mean(axis=-1)
    isi=np.clip(np.floor(mu+rng.normal(size=mu.shape)*values['sigma_isi'].values[...,None]+.5),0,28)
    mu=10-burden[...,data['qindex']]/3
    quality=np.round(np.clip(mu+rng.normal(size=mu.shape)*values['sigma_quality'].values[...,None],0,10),3)
    return isi,quality


def run(product, out):
    require_executable(product)  # No diagnostic helper can turn on production.
    from .analysis_worker import publish
    from contracts.domain.borrowing import seed_value
    started=time.monotonic();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    configuration=admitted_configuration(product.request.configuration)
    borrowed=product.sources is not None
    input_hash=sha(product.model_dump(mode='json'));manifest=product.cohort.manifest
    seed=product.numerical_seeds.nuts
    members=[dict(patient_id=m.patient_id,history_sha256=m.history_sha256,status='failed',
        reason='joint-worker-incomplete',effect=None,diagnostics={}) for m in manifest.members]
    result=dict(schema_version='3.0.0',synthetic=True,kind='poc_visit_cohort_result',attempt_id=product.attempt_id,
        input_sha256=input_hash,cohort_sha256=product.cohort_sha256,manifest=manifest.model_dump(mode='json'),
        manifest_sha256=product.cohort.manifest_sha256,source_set_sha256=product.source_set_sha256,
        configuration=product.request.configuration.model_dump(),estimand=ESTIMAND_REF,
        status='failed',reason='joint-worker-incomplete',patients=members,diagnostics={'patients':{}},artifacts=[],
        limitations=['One joint population posterior with distinct patient expected assignment contrasts; no averaged-effect target.',
            'Fictional synthetic model; no clinical validation, private truth, causal recovery or calibrated superiority claim.',
            'Restricted quality/ISI H* only; MCAR observation and declared transport/exchangeability assumptions.'])
    d=result['diagnostics']
    def stage(value):
        if time.monotonic()-started>=7200:raise TimeoutError('whole-cohort-worker-deadline')
        publish(out/'progress.json',dict(attempt_id=product.attempt_id,input_sha256=input_hash,**value))
    def save():publish(out/'diagnostics.json',d)
    try:
        # Deny before model/prior construction. This learner-side check cannot
        # configure or replace the service's independently fixed reviewed pair.
        origin=runtime_origin(os.environ.get('REMISSION_LEARNER_IMAGE',''),os.environ.get('REMISSION_SOURCE_COMMIT',''))
        d['execution']=execution_binding(product,origin)
        custody_binding=sha(d['execution'])
        d['execution'].update(kind='cohort_native_execution_v1',native_compilations=[],callable_custody=[])
        data=cohort_inputs(product.cohort)
        d['data']={patient:dict(day=x['day'],consumed_ids=x['record_ids'],likelihood_blocks=x['likelihood_blocks'],
            deliveries=x['deliveries'],taken=x['taken'],local_arm_support=x['arms']) for patient,x in data}
        layout=cohort_coordinate_layout(product.cohort,borrowed=borrowed)
        def observed_callable(value):
            d['execution']['callable_custody'].append(value);save()
        stage(dict(stage='fitting'));save()
        prior_model=(build_cohort_borrow(data,product.sources,configuration,guide=False,prior_predictive=True)
            if borrowed else build_cohort(data,guide=False,prior_predictive=True))
        variables=['burden','sigma_isi','sigma_quality','p_adherence']+(['source_g'] if borrowed else [])
        with prior_model, owned_callables(prior_model,fit='prior',binding_sha256=custody_binding,on_event=observed_callable):
            prior=pm.sample_prior_predictive(draws=64,random_seed=product.numerical_seeds.prior_check,
                var_names=variables,compile_kwargs=compilation_options())
        for index,(patient,x) in enumerate(data):
            isi,quality=_observed(prior['prior'],patient,x,np.random.SeedSequence([product.numerical_seeds.prior_check,index,314]))
            np.savez_compressed(out/('patient-'+sha(patient)[:16]+'-prior-predictive.npz'),isi=isi,quality=quality)
        if borrowed:
            np.savez_compressed(out/'source-prior-predictive.npz',g=prior['prior']['source_g'].values,
                p_adherence=prior['prior']['p_adherence'].values)
        d['prior_predictive']=dict(draws=64,coordinates='original/unconditioned',shared_graphs=1,
            note='No guide-conditioned pseudo-prior; adherence/observation prior counts reset to zero.')
        del prior_model,prior,isi,quality;gc.collect()
        d['execution']['prior_released_before_posterior']=True;save()
        model=build_cohort_borrow(data,product.sources,configuration) if borrowed else build_cohort(data)
        d['fits']=[]
        for extension in (False,True):
            stage(dict(stage='fitting',extension=extension));fit_start=time.monotonic()
            compiled=fit_callback(d['execution']['native_compilations'],extension=extension,
                seed=seed+int(extension),on_record=save)
            trace=sample(model,seed+int(extension),extended=extension,on_compile=compiled,expected_layout=layout['layout'],
                binding_sha256=custody_binding,on_event=observed_callable)
            stage(dict(stage='diagnostics'));checks=diagnostics(trace)
            name='posterior-extension.nc' if extension else 'posterior.nc';trace.to_netcdf(out/name,engine='netcdf4')
            d['fits'].append(dict(extension=extension,seed=seed+int(extension),seconds=time.monotonic()-fit_start,
                diagnostics=checks,artifact=name));save()
            if checks['accepted']:break
        if not checks['accepted']:raise ArithmeticError('nuts-diagnostics-unmet')
        posterior=trace['posterior']
        if borrowed:
            from methods.visit.source_precision import validate
            # Reuse canonical bridge with the common clock, once for the shared
            # population posterior. No patient-specific baseline is substituted.
            context=SimpleNamespace(history=manifest,sources=product.sources,attempt_id=product.attempt_id,
                numerical_seeds=product.numerical_seeds)
            d['bridge_precision']=validate(posterior,context,configuration,out,stage);save()
            if d['bridge_precision']['status']!='accepted':raise ArithmeticError('bridge-precision-unmet')
        # A shared30-minute effect-stage budget covers all twelve members, within
        # the original7200s total cap; no new per-member budget multiplication.
        effect_deadline=min(started+7200,time.monotonic()+CONFIG['integration_seconds'])
        for index,((patient,x),member) in enumerate(zip(data,members,strict=True)):
            stage(dict(stage='rollouts'));p=patient_parameters(posterior,patient)
            prefix='patient-'+sha(patient)[:16]
            isi,quality=_observed(posterior,patient,x,np.random.SeedSequence([seed,index,315]))
            np.savez_compressed(out/(prefix+'-observed-posterior-predictive.npz'),isi=isi,quality=quality)
            effect_seed=seed_value('pa3-fit-20261021-v1',-1,-1,index,manifest.cohort_id,
                timestamp_cutoff(manifest),'cohort-effect:'+patient+':'+str(product.numerical_seeds.effect_rollout))
            remaining=effect_deadline-time.monotonic()
            if remaining<=0:raise ArithmeticError('whole-cohort-effect-deadline')
            effect,precision=integrate(p,day=x['day'],current_c=x['c'][-1],current_e=x['e'][-1],
                seed=effect_seed,seconds=remaining,stage=stage)
            pd=d['patients'][patient]=dict(integration=precision,effect_seed=effect_seed)
            if effect is None:raise ArithmeticError('patient-numerical-precision-unmet:'+patient)
            effect_trace=xr.DataTree.from_dict({'posterior':xr.Dataset({'effect':(('chain','draw'),effect)})})
            pd['effect_mcmc']=diagnostics(effect_trace,variables=['effect']);save()
            np.savez_compressed(out/(prefix+'-expected-effect.npz'),effect=effect,chain=np.arange(effect.shape[0]),draw=np.arange(effect.shape[1]))
            if not pd['effect_mcmc']['accepted']:raise ArithmeticError('patient-effect-mcmc-unmet:'+patient)
            endpoint=predictive(p,day=x['day'],current_c=x['c'][-1],current_e=x['e'][-1],seed=effect_seed)
            np.savez_compressed(out/(prefix+'-predictive-endpoint.npz'),endpoint=endpoint,arm=np.array(['continue','escalate']))
            member.update(status='completed',reason=None,effect=dict(mean=float(effect.mean()),sd=float(effect.std(ddof=1)),
                lower=float(np.quantile(effect,.025)),upper=float(np.quantile(effect,.975)),unit='ISI_points',
                kind='conditional_expected_assignment_contrast'),diagnostics=pd)
        stage(dict(stage='diagnostics'));result.update(status='completed',reason=None)
    except Exception as error:
        (out/'failure.log').write_text(traceback.format_exc(),encoding='utf-8')
        status='abstained' if isinstance(error,(ArithmeticError,TimeoutError)) else 'failed'
        reason=f'{type(error).__name__}: {str(error)[:180]}'
        result.update(status=status,reason=reason)
        # Partial computational artifacts remain, but no interval escapes a
        # failed joint/applicable gate, even for an earlier passing member.
        for member in members:member.update(status=status,reason=reason,effect=None)
    d.update(seconds=time.monotonic()-started,peak_memory_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    save()
    result['artifacts']=[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.iterdir())
        if p.is_file() and p.name not in ('result.json','progress.json') and p.suffix!='.partial']
    parsed=CohortResult.model_validate_json(__import__('json').dumps(result))
    publish(out/'result.json',parsed.model_dump(mode='json'))
    return result


def timestamp_cutoff(manifest):
    return manifest.cutoff.isoformat()
