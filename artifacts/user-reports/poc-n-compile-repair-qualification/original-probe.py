"""Reviewer-only frozen e6d5 symbolic qualification; no fitting/admission."""
import hashlib,json,os,signal,sys,time,traceback
from pathlib import Path
import numpy as np
from scipy.special import expit
from scipy.stats import beta,halfnorm,norm,uniform
ROOT=Path('/source'); PREP=ROOT/'artifacts/user-reports/poc-n-symbolic-e6d5-prep'; OUT=Path('/output')
sys.path[:0]=[str(ROOT/'tests/methods'),str(ROOT/'tooling/foundation')]
from contracts.domain.analysis import canonical
from contracts.domain.protocol_analysis import ProtocolHistory
from contracts.domain.borrow_runtime import NATIVE_OPTIMIZER
from methods.nof1.data import prepare
from methods.nof1.observation import bin_logprob
from test_nof1_symbolic import independent_logp
from pa3_monitor import compilation_options,optimizer_identity,verify_cvm
START=time.monotonic()
def emit(kind,**value):
    record=dict(kind=kind,elapsed=time.monotonic()-START,**value)
    encoded=canonical(record)
    print(encoded,flush=True)
    with (OUT/'events.jsonl').open('a') as f:f.write(encoded+'\n');f.flush()
def timeout(*_):raise TimeoutError('whole-stage-1800-second-cap')
signal.signal(signal.SIGALRM,timeout);signal.alarm(int(os.environ['NOF1_STAGE_SECONDS']))
def filehash(path):return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((PREP/'input-manifest.json').read_text())
for name,want in manifest['files'].items():
    if filehash(ROOT/name)!=want:raise ValueError('frozen source/input mismatch: '+name)
emit('frozen-inputs-verified',manifest_sha256=filehash(PREP/'input-manifest.json'),source=manifest['source'],no_fit=True)
import pymc as pm
import pytensor
import pytensor.tensor as pt
from pytensor.compile.mode import get_default_mode
from methods.nof1.model import build,log_bin
policy=json.loads((ROOT/'tooling/foundation/pa3-cvm-policy.json').read_text())
def options():
    opts,binding=compilation_options(policy)
    return opts,binding
def verified(fn,label,pymc=True):
    actual=fn.f if hasattr(fn,'f') else fn
    vm=verify_cvm(actual)
    opt=optimizer_identity(actual.maker.mode.provided_optimizer)
    if opt!=(NATIVE_OPTIMIZER if pymc else policy['candidate_optimizer']):raise ValueError('compiled optimizer identity differs')
    emit('actual-compiled',label=label,actual_vm=vm,optimizer=opt)
    return fn
opts,binding=options()
default=get_default_mode()
emit('runtime-before-build',pymc=pm.__version__,pytensor=pytensor.__version__,floatX=pytensor.config.floatX,default_linker=type(default.linker).__name__,binding=binding)
assert pytensor.config.floatX=='float64'
def reference_factors(point,data):
    g=lambda k:np.asarray(point[k],dtype=np.float64)
    mu,sb=g('mu_b'),np.exp(g('sd_b_log__')); raw,pop=g('b_raw'),g('population_amplitude')
    sd,araw=np.exp(g('sd_amplitude_log__')),g('amplitude_raw')
    a,rho=g('a'),-.95+1.9*expit(g('rho_interval__'))
    se,si,sq=[np.exp(g(n+'_log__')) for n in ('sigma_e','sigma_isi','sigma_quality')]
    refs=dict(mu_b=norm.logpdf(mu,19,5).sum(),sd_b=halfnorm.logpdf(sb,scale=3).sum(),b_raw=norm.logpdf(raw).sum(),population_amplitude=norm.logpdf(pop,scale=[4,4,3,3,3]).sum(),sd_amplitude=halfnorm.logpdf(sd).sum(),amplitude_raw=norm.logpdf(araw).sum(),a=norm.logpdf(a).sum(),rho=uniform.logpdf(rho,-.95,1.9).sum(),sigma_e=halfnorm.logpdf(se,scale=2).sum(),sigma_isi=halfnorm.logpdf(si,scale=2).sum(),sigma_quality=halfnorm.logpdf(sq).sum())
    means=[]
    for i,p in enumerate(data.patients):
        innovation=g('innovation_'+str(i));refs['innovation_'+str(i)]=norm.logpdf(innovation).sum()
        e=[];cur=0.
        for value in innovation:cur=rho*cur+se*value;e.append(cur)
        amp=pop+sd*araw[i]
        z=mu+sb*raw[i]+a*np.sin(2*np.pi*p.nights/21)+e-amp[0]*p.c-amp[2]*p.medication[:,0]-amp[3]*p.medication[:,1]+amp[4]*p.path.rebound
        im=z[p.recall].mean(axis=1);qm=10-z[p.qindex]/3
        refs['isi_likelihood_'+str(i)]=bin_logprob(p.isi,im,si,1.,28.).sum()
        refs['quality_likelihood_'+str(i)]=bin_logprob(p.quality,qm,sq,.001,10.).sum()
        means.append((im,qm,float(si),float(sq)))
    for name in ('p_C','p_M','q'):
        refs[name]=0.
        for i,p in enumerate(data.patients):
            c=p.counts;s,f=(c['C_success'],c['C_total']-c['C_success']) if name=='p_C' else (c['M_success'],c['M_total']-c['M_success']) if name=='p_M' else (c['observed'],c['missing'])
            refs[name]+=beta.logpdf(expit(g(name+'_logodds__')[i]),1.+s,1.+f)
    return refs,means


try:
    for j,purpose in [(1,'N0'),(1,'N1'),(2,'N0'),(2,'N1')]:
        label=f'J{j}-{purpose}';emit('model-start',label=label)
        histories=[ProtocolHistory.model_validate_json(canonical(h)) for h in json.loads((PREP/f'frozen/J{j}-histories.json').read_text())]
        data=prepare(histories,purpose=purpose,target_id=histories[-1].patient_id,seed_patient=histories[-1].patient_id)
        point={k:np.asarray(v,dtype=np.float64) for k,v in json.loads((PREP/f'frozen/J{j}-point.json').read_text()).items()}
        physical={k.removesuffix('_log__'):np.exp(v).tolist() if k.endswith('_log__') else v.tolist() for k,v in point.items() if not k.endswith('_logodds__') and k!='rho_interval__'}
        physical.update({k.removesuffix('_logodds__'):expit(v).tolist() for k,v in point.items() if k.endswith('_logodds__')})
        physical['rho']=float(-.95+1.9*expit(point['rho_interval__']))
        (OUT/(label+'-physical-point.json')).write_text(canonical(physical)+'\n')
        refs,means=reference_factors(point,data)
        model=build(data)
        names=[v.name for v in model.value_vars]
        assert set(names)==set(point)
        dtype_rows={rv.name:[dict(dtype=getattr(v,'dtype',None),shape=str(getattr(v.type,'shape',None)),constant=np.asarray(v.data).tolist() if hasattr(v,'data') and str(getattr(v,'dtype','')).startswith(('float','int')) else None) for v in rv.owner.inputs] for rv in model.free_RVs}
        for variable in model.value_vars:assert variable.dtype=='float64',(variable.name,variable.dtype)
        for rv in model.free_RVs:
            parameter_inputs=rv.owner.inputs[-2:] if rv.name in ('p_C','p_M','q','rho') or not rv.name.startswith(('sd_','sigma_')) else rv.owner.inputs[-1:]
            for value in parameter_inputs:assert value.dtype=='float64',(rv.name,value.dtype)
        emit('model-built',label=label,history_sha256=data.history_sha256,point_sha256=filehash(PREP/f'frozen/J{j}-point.json'),coordinates=[dict(name=n,shape=list(point[n].shape),dtype=str(point[n].dtype)) for n in names],rv_input_dtypes=dtype_rows)
        from pytensor.graph.traversal import ancestors
        from pytensor.tensor.random.op import RandomVariable
        for potential in model.potentials:
            rvs={v for v in ancestors([potential]) if v.owner is not None and isinstance(v.owner.op,RandomVariable)}
            assert rvs <= set(model.free_RVs),(potential.name,'unregistered RV ancestor')
        emit('registered-RV-ownership',label=label,passed=True)
        variables=[*model.free_RVs,*model.potentials]
        expressions=[model.logp(vars=[v],jacobian=False) for v in variables]+[model.logp(jacobian=False)]
        opts,_=options();emit('factor-compile-start',label=label)
        fn=verified(model.compile_fn(expressions,inputs=model.value_vars,**opts),label+'-factors')
        evaluated=np.asarray(fn(point),dtype=np.float64)
        repeated=np.asarray(fn(point),dtype=np.float64)
        assert np.array_equal(evaluated,repeated),'repeated density changed at fixed point'
        observed=evaluated[:-1]
        rows=[dict(name=v.name,actual=float(x),reference=float(refs[v.name]),difference=float(x-refs[v.name]),tolerance=1e-10 if v.name in ('p_C','p_M','q') else 1e-8) for v,x in zip(variables,observed)]
        total=float(evaluated[-1]);reference=independent_logp(point,data)
        assert abs(total-float(observed.sum()))<=1e-8,'factor sum/full density mismatch'
        assert abs(sum(refs.values())-reference)<1e-10
        passed=bool(np.isfinite(observed).all() and abs(total-reference)<=1e-8 and all(abs(r['difference'])<=r['tolerance'] for r in rows))
        emit('density-gate',label=label,passed=passed,total=total,reference=reference,difference=total-reference,tolerance=1e-8,factors=rows)
        if not passed:
            emit('first-source-failure-stop-models',label=label,gradient_run=False)
            # Stop immediately: no patched graph or later model after failure.
            raise AssertionError(label+' original density gate failed; no later model/control allowed')
        opts,_=options();emit('gradient-compile-start',label=label)
        grad=verified(model.compile_dlogp(jacobian=False,**opts),label+'-gradient')
        rng=np.random.default_rng(761);direction={n:rng.normal(size=point[n].shape)*.1 for n in names}
        vector=np.concatenate([np.ravel(direction[n]) for n in names]);analytic=np.asarray(grad(point))
        eps=1e-5
        finite=(independent_logp({n:point[n]+eps*direction[n] for n in names},data)-independent_logp({n:point[n]-eps*direction[n] for n in names},data))/(2*eps)
        projected=float(analytic@vector);tol=1e-5+1e-5*abs(finite)
        passed=bool(np.isfinite(analytic).all() and abs(projected-finite)<=tol)
        emit('gradient-gate',label=label,passed=passed,analytic=projected,independent_fd=finite,difference=projected-finite,tolerance=tol)
        if not passed:raise AssertionError(label+' gradient gate failed')
        emit('model-pass',label=label)
    emit('helper-controls-start',source='tests/methods/test_measurement.py')
    import unittest
    import test_measurement
    from unittest.mock import patch
    original_lp,original_grad=pm.Model.compile_logp,pm.Model.compile_dlogp
    test_measurement.verify_cvm=lambda fn:verified(fn,'helper-raw',pymc=False)
    with patch.object(pm.Model,'compile_logp',lambda self,*a,**k:verified(original_lp(self,*a,**k),'helper-model-logp')), patch.object(pm.Model,'compile_dlogp',lambda self,*a,**k:verified(original_grad(self,*a,**k),'helper-model-gradient')), (OUT/'helper-tests.log').open('w') as stream:
        outcome=unittest.TextTestRunner(stream=stream,verbosity=2,failfast=True).run(unittest.defaultTestLoader.loadTestsFromModule(test_measurement))
    emit('helper-controls-complete',tests=outcome.testsRun,failures=len(outcome.failures),errors=len(outcome.errors),skipped=len(outcome.skipped))
    if not outcome.wasSuccessful():raise AssertionError('helper source controls failed')
    emit('terminal',status='passed-bounded-symbolic-controls',fit=False)
except BaseException as exc:
    emit('terminal',status='failed',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),fit=False)
    raise
