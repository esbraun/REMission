"""Native S2 fitting in the isolated learner only; accepted model unchanged.

Runtime admission remains closed in the scalar contract and worker entry.
No alternative sampler, initializer, likelihood, prior or retry lives here.
"""
from contextlib import contextmanager
import time
import warnings
import numpy as np
import pymc as pm
import pytensor
from pytensor.compile.mode import Mode, get_default_mode
from pytensor.graph.basic import Constant
from pytensor.graph.traversal import ancestors, graph_inputs
from pytensor.tensor.random.op import RandomVariable
from contracts.domain.borrow_runtime import OPTIMIZER, NATIVE_OPTIMIZER
from contracts.domain.support_s2_native import MONITORED, FitDiagnostics, coordinate_layout
from methods.visit.borrow_execution import optimizer_identity, verify_cvm, native_call
from .s2_model import build


def actual_policy():
    if (pm.__version__!='6.3.2' or pytensor.__version__!='3.3.4'
            or pytensor.config.floatX!='float64' or pytensor.config.cast_policy!='numpy+floatX'
            or pytensor.config.base_compiledir!='/tmp/pytensor-s2'):
        raise ValueError('S2_actual_pinned_construction_policy_mismatch')
    default=get_default_mode()
    if optimizer_identity(default.provided_optimizer)!=OPTIMIZER:
        raise ValueError('S2_default_optimizer_mismatch')
    mode=Mode(linker='cvm',optimizer=default.provided_optimizer)
    if optimizer_identity(mode.provided_optimizer)!=OPTIMIZER:
        raise ValueError('S2_requested_optimizer_mismatch')
    return dict(mode=mode)


def construction_guards(model):
    expected=['mu_alpha','mu_tau','b','s_alpha','s_tau','s_e','s_Q','rho','z','u']+['epsilon_'+str(i) for i in range(12)]
    if [v.name for v in model.free_RVs]!=expected:
        raise ValueError('S2_exact_registered_free_RV_inventory_required')
    registered=set(model.free_RVs)
    if any(v.dtype!='float64' for v in [*model.free_RVs,*model.value_vars]):
        raise ValueError('S2_RV_value_dtype_mismatch')
    for rv in model.free_RVs:
        for operand in rv.owner.inputs:
            if getattr(operand,'dtype','').startswith('float') and operand.dtype!='float64':
                raise ValueError('S2_strict_prior_operand_float64_required')
    for name in ('s_alpha','s_tau','s_e','s_Q'):
        inputs=model.named_vars[name].owner.inputs
        if (len(inputs)!=4 or any(not isinstance(inputs[i],Constant) or inputs[i].dtype!='float64' for i in (2,3))):
            raise ValueError('S2_strict_HalfNormal_location_and_scale_required')
    for output in [*model.potentials,*model.deterministics]:
        rvs={v for v in ancestors([output]) if v.owner is not None and isinstance(v.owner.op,RandomVariable)}
        if not rvs<=registered:raise ValueError('S2_unregistered_RV_ancestor')
    reject_f32(graph_inputs([model.logp(),model.dlogp()]))


def reject_f32(values):
    if any(isinstance(v,Constant) and getattr(v,'dtype',None)=='float32' for v in values):
        raise ValueError('S2_float32_graph_Constant_refused')


@contextmanager
def sampling_graph(model, *, cutoff, stage):
    """Inspect/evaluate the actual callable returned to native BaseHMC.

    Forwards untouched arguments/result; checks actual post-rewrite graph,
    optimizer, CVM and coordinate ownership before the sampler gets it.
    """
    original=model.logp_dlogp_function
    previous=model.__dict__.get('logp_dlogp_function')
    records=[]
    def checked(*args,**kwargs):
        stage(dict(stage='fitting',event='compiling'))
        supplied=kwargs.get('grad_vars',args[0] if args else None)
        expected=list(model.continuous_value_vars)
        if supplied is not None and (len(supplied)!=len(expected) or any(a is not b for a,b in zip(supplied,expected))):
            raise ValueError('S2_sampler_must_own_all_value_coordinates')
        function=original(*args,**kwargs)
        actual_policy()
        fn=function._pytensor_function
        vm=verify_cvm(fn)
        optimizer=optimizer_identity(fn.maker.mode.provided_optimizer)
        if optimizer!=NATIVE_OPTIMIZER:raise ValueError('S2_actual_sampler_optimizer_changed')
        graph=fn.maker.fgraph
        reject_f32([*graph.variables,*graph_inputs(graph.outputs)])
        if any(isinstance(node.op,RandomVariable) for node in graph.toposort()):
            raise ValueError('S2_unowned_RV_in_compiled_sampler_graph')
        point=kwargs.get('initial_point')
        if point is None:point=model.initial_point()
        _,_,mapping=native_call(function,point,model.continuous_value_vars)
        if mapping!=coordinate_layout(cutoff):raise ValueError('S2_actual_sampler_coordinate_layout_changed')
        records.append(dict(index=len(records)+1,actual_vm=vm,compiled_optimizer=optimizer,
            coordinate_map=mapping,compiled_graph_float32_constants=0,unowned_random_variables=0,
            strict_prior_operands=True,finite_logp_dlogp=True))
        stage(dict(stage='fitting',event='compiled'))
        return function
    model.logp_dlogp_function=checked
    try:
        yield records
        if not records:raise ValueError('S2_native_sampler_no_guarded_combined_callable')
    finally:
        if previous is None:del model.logp_dlogp_function
        else:model.logp_dlogp_function=previous


def sample(data,product, *, stage, check):
    """One explicitly selected attempt, with blocked-sampler progress veto.

    The caller owns the single absolute deadline. The PyMC callback runs on
    each actual tuning/saved draw, including during the blocked sample call.
    External existing supervision remains necessary during a blocked compile
    or individual native leapfrog; this callback cannot preempt C code.
    """
    check();options=actual_policy();model=build(data);construction_guards(model)
    cutoff=product.initial.export.provenance.cutoff_day
    last=-1;callback_calls=0
    def callback(trace,draw):
        nonlocal last,callback_calls
        check()
        if type(draw.chain) not in (int,np.int64) or not 0<=int(draw.chain)<4:
            raise ValueError('S2_sampler_callback_chain_mismatch')
        callback_calls+=1
        # Bounded stage writes (at most 240 for a 2000+2000, four-chain fit).
        ordinal=int(draw.chain)*2*product.draws+int(draw.draw_idx)
        if ordinal//100!=last:
            last=ordinal//100
            stage(dict(stage='fitting',event='sampling',chain=int(draw.chain),draw=int(draw.draw_idx),tuning=bool(draw.tuning)))
        check()
    check();stage(dict(stage='fitting',event='starting'))
    warning_count=0
    def count_warning(*args,**kwargs):
        nonlocal warning_count
        warning_count+=1
        if warning_count>1000:raise ValueError('S2_python_warning_count_cap')
    with warnings.catch_warnings(), model, sampling_graph(model,cutoff=cutoff,stage=stage) as compiled:
        warnings.simplefilter('always')
        warnings.showwarning=count_warning
        trace=pm.sample(draws=product.draws,tune=product.draws,chains=4,cores=1,
            random_seed=product.seed_record.sampler_seed,nuts_sampler='pymc',target_accept=.995,
            nuts={'max_treedepth':12},blas_cores=1,progressbar=False,
            return_inferencedata=True,compile_kwargs=options,callback=callback,
            keep_warning_stat=True,discard_tuned_samples=True,
            idata_kwargs={'log_likelihood':False})
    check()
    if callback_calls!=4*2*product.draws:
        raise ValueError('S2_native_callback_did_not_observe_all_tuning_and_saved_draws')
    return trace,dict(native_compilations=compiled,callback_calls=callback_calls,python_warnings=warning_count)


def diagnostics(trace, *, python_warnings):
    import arviz_stats as azs
    posterior=trace['posterior'];stats=trace['sample_stats']
    if set(posterior.data_vars)!=set(MONITORED):raise ValueError('S2_full_sampled_reported_inventory_required')
    summaries={name:{} for name in MONITORED}
    for field,fn,kwargs in (('rhat',azs.rhat,dict(method='rank')),('ess_bulk',azs.ess,dict(method='bulk')),
            ('ess_tail',azs.ess,dict(method='tail')),('mcse',azs.mcse,dict(method='mean'))):
        values=fn(trace,var_names=list(MONITORED),**kwargs)
        if set(values.data_vars)!=set(MONITORED):raise ValueError('S2_missing_required_diagnostic_field')
        for name,value in values.data_vars.items():
            array=np.asarray(value.values)
            if not np.all(np.isfinite(array)):raise ValueError('S2_nonfinite_required_diagnostic')
            summaries[name][field]=float(np.max(array) if field in ('rhat','mcse') else np.min(array))
    for name in ('energy','lp','diverging','tree_depth','sampler_warning'):
        if name not in stats:raise ValueError('S2_missing_native_sampler_statistic')
    energy=np.asarray(stats['energy'].transpose('chain','draw').values)
    if (energy.shape[0]!=4 or energy.shape[1] not in (1000,2000) or not np.all(np.isfinite(energy))):
        raise ValueError('S2_all_chain_finite_energy_required')
    bfmi=np.mean(np.diff(energy,axis=1)**2,axis=1)/np.var(energy,axis=1)
    result=dict(variables=summaries,energy_min=np.min(energy,axis=1).tolist(),energy_max=np.max(energy,axis=1).tolist(),
        bfmi=bfmi.tolist(),divergences=int(stats['diverging'].sum()),
        tree_depth_hits=int((stats['tree_depth']>=12).sum()),maximum_tree_depth=int(stats['tree_depth'].max()),
        sampler_warnings=int(stats['sampler_warning'].sum()),
        python_warnings=python_warnings)
    result['accepted']=bool(all(v['rhat']<1.01 and v['ess_bulk']>=400 and v['ess_tail']>=400 for v in summaries.values())
        and np.all(np.isfinite(bfmi)) and np.all(bfmi>.3) and not result['divergences']
        and not result['tree_depth_hits'] and not result['sampler_warnings'] and not python_warnings)
    return FitDiagnostics.model_validate_json(__import__('json').dumps(result))
