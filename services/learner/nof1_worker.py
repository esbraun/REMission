"""Lazy file-only N0/N1 learner; no Store, generator, service or network API."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata as metadata
import math
import os
from pathlib import Path
import time

from contracts.domain.analysis import canonical,sha
from contracts.domain.nof1_app import (NInput,NResult,LIMITATIONS,consumed_ids,
    ownership_manifest,execution_binding,readiness,validate_fit)


def publish(path,value):
    temporary=path.with_suffix('.partial')
    temporary.write_text(canonical(value)+'\n',encoding='utf-8');temporary.replace(path)


def finite_report(value):
    if isinstance(value,dict):return {k:finite_report(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [finite_report(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):return None
    return value


def effect_diagnostics(effect):
    import numpy as np
    import xarray as xr
    import arviz_stats as azs
    tree=xr.DataTree.from_dict({'posterior':xr.Dataset({'expected_contrast':
        (('chain','draw','target'),effect)})})
    result={}
    for name,fn,kwargs in (('rhat',azs.rhat,dict(method='rank')),
            ('ess_bulk',azs.ess,dict(method='bulk')),('ess_tail',azs.ess,dict(method='tail')),
            ('mcse',azs.mcse,dict(method='mean'))):
        array=np.asarray(fn(tree,var_names=['expected_contrast'],**kwargs)['expected_contrast'].values)
        value=np.max(array) if name in ('rhat','mcse') else np.min(array)
        result[name]=dict(expected_contrast=float(value) if np.all(np.isfinite(array)) else None)
    result['accepted']=True
    try:validate_fit(result,effect=True)
    except ValueError:result['accepted']=False
    return result


def run(source,out,*,seconds=7200):
    if not 0<seconds<=7200:raise ValueError('N worker ceiling must be positive and at most7200 seconds')
    started=time.monotonic();deadline=started+seconds
    product=NInput.model_validate_json(source.read_bytes());out.mkdir(parents=True,exist_ok=True)
    ready=readiness(product.histories,product.target_id);ctx=product.request.context
    origin={k:os.environ[v] for k,v in dict(learner_image='REMISSION_LEARNER_IMAGE',
        source_commit='REMISSION_SOURCE_COMMIT').items()}
    base=dict(schema_version='4.0.0',synthetic=True,kind='poc_nof1_result',purpose=product.purpose,
        attempt_id=product.attempt_id,target_id=product.target_id,input_sha256=sha(product.model_dump(mode='json')),
        history_sha256=product.history_sha256,cohort=[m.model_dump() for m in product.cohort],
        cutoff=product.cutoff.isoformat(),run=product.run.model_dump(),configuration=product.request.configuration.model_dump(),
        model=ctx.model.model_dump(),prior=ctx.prior.model_dump(),estimand=ctx.estimand.model_dump(),
        protocol=ctx.protocol.model_dump(),status='failed',readiness=ready['status'],reason='worker-incomplete',
        generated_at=datetime.now(timezone.utc).isoformat(),consumed_record_ids=consumed_ids(product),
        effect=None,diagnostics=dict(execution=execution_binding(product,origin),fits=[]),artifacts=[],limitations=LIMITATIONS)
    progress_state=dict(sequence=0,extension=False,rollouts_started_elapsed_seconds=None,integration_finished_elapsed_seconds=None)
    def check_deadline():
        if time.monotonic()>=deadline:raise TimeoutError('whole-N-worker-deadline')
        if (progress_state['rollouts_started_elapsed_seconds'] is not None
                and progress_state['integration_finished_elapsed_seconds'] is None
                and time.monotonic()-started>=progress_state['rollouts_started_elapsed_seconds']+1800):
            raise TimeoutError('whole-N-integration-deadline')
    def stage(value):
        check_deadline();elapsed=time.monotonic()-started
        if value['stage']=='rollouts' and progress_state['rollouts_started_elapsed_seconds'] is None:
            progress_state['rollouts_started_elapsed_seconds']=elapsed
        if value.get('integration_finished') is True:progress_state['integration_finished_elapsed_seconds']=elapsed
        if 'extension' in value:progress_state['extension']=value['extension']
        progress_state['sequence']+=1
        publish(out/'progress.json',dict(schema='n-fit04-progress-v1',attempt_id=product.attempt_id,
            input_sha256=base['input_sha256'],stage=value['stage'],elapsed_seconds=elapsed,K=value.get('K'),**progress_state))
    try:
        stage(dict(stage='preparing'))
        if ready['status']!='eligible':
            base.update(status='abstained',reason=ready['reason'])
        else:
            imports=time.monotonic()
            import numpy as np
            from methods.nof1.data import prepare
            from methods.nof1.model import build,sample,diagnostics
            from methods.nof1.rollout import target_draws,predictive
            from methods.nof1.numerics import integrate
            imported=time.monotonic()
            base['diagnostics']['packages']={name:metadata.version(name) for name in
                ('numpy','pymc','pytensor','arviz-stats','xarray','netCDF4')}
            data=prepare(product.histories,purpose=product.purpose,target_id=product.target_id,seed_patient=ctx.seed.patient)
            if data.history_sha256!=product.history_sha256:raise ValueError('scientific reader Hstar identity mismatch')
            manifest=ownership_manifest(product)
            for patient,owned in zip(data.patients,manifest['patients']):
                if ({k:sorted(v) for k,v in patient.ownership.items()}!=owned['likelihood']
                        or sorted(patient.record_ids)!=owned['record_ids']):
                    raise ValueError('scientific reader likelihood ownership mismatch')
            check_deadline();model=build(data)
            seed=int(sha(ctx.seed.model_dump())[:8],16)
            for extended in (False,True):
                stage(dict(stage='fitting',extension=extended));fit_start=time.monotonic()
                trace=sample(model,seed+int(extended),purpose=product.purpose,extended=extended)
                stage(dict(stage='diagnostics'));fit=diagnostics(trace,purpose=product.purpose)
                base['diagnostics']['fits'].append(dict(extended=extended,seconds=time.monotonic()-fit_start,diagnostics=fit))
                publish(out/'diagnostics.json',finite_report(base['diagnostics']))
                if fit['accepted']:break
                del trace
            if not fit['accepted']:
                base.update(status='abstained',reason='nuts-diagnostics-unmet')
            else:
                check_deadline();draws=target_draws(trace,data)
                shape=draws.parameters['b'].shape
                base['diagnostics']['axes']=dict(chains=shape[0],draws=shape[1],
                    target_ids=[product.target_id],patients=[m.patient_id for m in product.cohort])
                stage(dict(stage='rollouts'))
                remaining=min(1800.,deadline-time.monotonic())
                if remaining<=0:raise TimeoutError('N integration has no remaining host budget')
                effect,integration=integrate(draws,seed=seed,stage=stage,seconds=remaining)
                stage(dict(stage='rollouts',integration_finished=True))
                base['diagnostics']['integration']=integration
                if effect is None:base.update(status='abstained',reason='numerical-precision-unmet')
                else:
                    effect_fit=effect_diagnostics(effect);base['diagnostics']['effect_mcmc']=effect_fit
                    if not effect_fit['accepted']:base.update(status='abstained',reason='expected-effect-diagnostics-unmet')
                    else:
                        check_deadline();future=predictive(draws,seed=seed)
                        base['effect']=dict(kind='conditional_expected_assignment_contrast',unit='quality_points',
                            mean=float(effect.mean()),sd=float(effect.std(ddof=1)),
                            lower=float(np.quantile(effect,.025)),upper=float(np.quantile(effect,.975)),
                            horizon=7,target_id=product.target_id)
                        trace.to_netcdf(out/'posterior.nc',engine='netcdf4')
                        axes=dict(chain=np.arange(shape[0]),draw=np.arange(shape[1]),target=np.array([product.target_id]),
                            history_sha256=np.array(product.history_sha256))
                        np.savez_compressed(out/'expected-contrast.npz',effect=effect,**axes,
                            axes=np.array(['chain','draw','target']),unit=np.array('quality_points'),
                            kind=np.array('conditional_expected_assignment_contrast'))
                        np.savez_compressed(out/'predictive.npz',quality=future['quality'],available=future['available'],
                            **axes,arm=np.array(future['arms']),night=future['nights'],axes=np.array(future['axes']),
                            unit=np.array(future['unit']),kind=np.array(future['kind']))
                        check_deadline()
                        from .nof1_artifacts import validate
                        base['diagnostics']['artifact_semantics']=validate(out,product,base['effect'])
                        check_deadline();base.update(status='completed',reason=None)
            base['diagnostics'].setdefault('timings',{}).update(import_seconds=imported-imports)
    except Exception as error:
        base.update(status='failed',reason=type(error).__name__+': '+str(error),effect=None)
    base['diagnostics'].setdefault('timings',{})['worker_seconds']=time.monotonic()-started
    base['diagnostics']=finite_report(base['diagnostics'])
    base['generated_at']=datetime.now(timezone.utc).isoformat()
    publish(out/'ownership.json',ownership_manifest(product));publish(out/'diagnostics.json',base['diagnostics'])
    names=['diagnostics.json','ownership.json']
    if base['status']=='completed':names+=['posterior.nc','expected-contrast.npz','predictive.npz']
    base['artifacts']=[dict(path=name,sha256=hashlib.sha256((out/name).read_bytes()).hexdigest()) for name in names]
    try:checked=NResult.model_validate_json(canonical(base))
    except ValueError as error:
        base.update(status='failed',reason='ResultValidation: '+str(error),effect=None)
        base['artifacts']=[a for a in base['artifacts'] if a['path'] in ('diagnostics.json','ownership.json')]
        checked=NResult.model_validate_json(canonical(base))
    check_deadline()
    publish(out/'result.json',checked.model_dump(mode='json'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();run(args.input,args.output)


if __name__=='__main__':main()
