"""Opt-in isolated learner graph-qualification SOURCE, not an operator/GO.

Never import/run on the host. Source checks inspect AST only. Future exact
operation review must freeze fixtures, coordinates, step/gates, compiler policy
and independent resource/deadline plan. No sampling or prediction-case rerun.
"""
import math
import os

DRAFT_SETTINGS=dict(density_atol=1e-8,normalizer_atol=1e-10,
    gradient_atol=1e-5,gradient_rtol=1e-5,steps=(1e-4,3e-5,1e-5,3e-6),
    operation_review=None,resource_plan_sha256=None)
CORRELATIONS=(-.949999,-.4,0.,.4,.949999)
STAGE='admission'
PRIOR_INPUT_FAILURE=None
PRIOR_INPUT_RVS=('mu_alpha','mu_tau','b','s_alpha','s_tau','s_e','s_Q','rho','z','u','epsilon_0','epsilon_1')
PRIOR_INPUT_DTYPES=('float16','float32','float64','float128')
PRIOR_INPUT_MAX_ORDINAL=7  # Diagnostic ceiling only; actual input count unknown.


def prior_input_metadata(rv,ordinal,dtype,is_constant,expected_names):
    if (type(expected_names) not in (list,tuple) or not 1<=len(expected_names)<=12
            or any(type(name) is not str or name not in PRIOR_INPUT_RVS for name in expected_names)
            or type(rv) is not str or rv not in expected_names or rv not in PRIOR_INPUT_RVS
            or type(ordinal) is not int or not 0<=ordinal<=PRIOR_INPUT_MAX_ORDINAL
            or type(dtype) is not str or dtype not in PRIOR_INPUT_DTYPES or type(is_constant) is not bool):
        return dict(status='unavailable',code='refused')
    return dict(status='available',rv=rv,input_ordinal=ordinal,dtype=dtype,is_constant=is_constant)


def prior_input_rejected(value,rv,ordinal,expected_names,constant_type):
    global PRIOR_INPUT_FAILURE
    # Same predicate and short-circuit order as R1; no value/array evaluation.
    rejected=getattr(value,'dtype','').startswith('float') and value.dtype!='float64'
    if rejected and PRIOR_INPUT_FAILURE is None:
        try:
            PRIOR_INPUT_FAILURE=prior_input_metadata(rv,ordinal,value.dtype,isinstance(value,constant_type),expected_names)
        except BaseException:
            PRIOR_INPUT_FAILURE=dict(status='unavailable',code='classification_failed')
    return rejected


def require_admitted(settings):
    if os.environ.get('S2_MODEL_SYMBOLIC_QUALIFY')!='1':
        raise PermissionError('separate isolated graph operation lease required')
    if (set(settings)!=set(DRAFT_SETTINGS) or not isinstance(settings['operation_review'],str)
            or len(settings['operation_review'])!=40 or any(c not in '0123456789abcdef' for c in settings['operation_review'])
            or not isinstance(settings['resource_plan_sha256'],str) or len(settings['resource_plan_sha256'])!=64
            or any(c not in '0123456789abcdef' for c in settings['resource_plan_sha256'])):
        raise PermissionError('exact reviewed graph/resource plan still pending')
    for name in ('density_atol','normalizer_atol','gradient_atol','gradient_rtol'):
        if type(settings[name]) is not float or not math.isfinite(settings[name]) or settings[name]<=0:
            raise ValueError('prespecified positive finite qualification gates required')
    steps=settings['steps']
    if (type(steps) is not tuple or len(steps)!=4 or len(set(steps))!=4
            or any(type(s) is not float or not math.isfinite(s) or not 0<s<.001 for s in steps)):
        raise ValueError('four prespecified finite-difference steps required')


def reference(point,members,*,wrong_centering=False,omit_last=False,duplicate_first=False):
    """Independent ORIGINAL noncentered coordinates, zero transform Jacobian.

    Direct scalar AR recurrence and SciPy density/bin reference. No PyTensor
    expression/helper, symbolic AR convolution or log_bin is reused here.
    """
    import numpy as np
    from scipy.stats import norm,halfnorm,uniform
    from methods.nof1.observation import bin_logprob
    get=lambda name:np.asarray(point[name],dtype=np.float64)
    factors=dict(mu_alpha=float(norm.logpdf(get('mu_alpha'),loc=5,scale=3)),
        mu_tau=float(norm.logpdf(get('mu_tau'),loc=0,scale=2)),
        b=float(norm.logpdf(get('b'),loc=0,scale=2).sum()),
        rho=float(uniform.logpdf(get('rho'),loc=-.95,scale=1.9)),
        z=float(norm.logpdf(get('z')).sum()),u=float(norm.logpdf(get('u')).sum()))
    for name in ('s_alpha','s_tau','s_e','s_Q'):factors[name]=float(halfnorm.logpdf(get(name),scale=2))
    likelihood=[]
    for i,member in enumerate(members):
        innovations=get('epsilon_'+str(i));factors['epsilon_'+str(i)]=float(norm.logpdf(innovations).sum())
        current=0.;errors=[]
        for innovation in innovations:
            current=float(get('rho'))*current+float(get('s_e'))*float(innovation);errors.append(current)
        alpha=float(get('mu_alpha')+get('s_alpha')*get('z')[i])
        tau=float(get('mu_tau')+get('s_tau')*get('u')[i])
        for row in member.observed:
            mean=alpha+math.fsum(float(v)*float(w) for v,w in zip(row.x,get('b')))
            mean+=(row.action-(.5 if wrong_centering else row.probability))*tau+errors[row.index]
            likelihood.append(float(bin_logprob(np.asarray([row.quality]),np.asarray([mean]),float(get('s_Q')),.001,10.)[0]))
    if omit_last and likelihood:likelihood=likelihood[:-1]
    if duplicate_first and likelihood:likelihood=[*likelihood,likelihood[0]]
    prior=math.fsum(factors.values());observed=math.fsum(likelihood)
    return dict(total=prior+observed,prior=prior,likelihood=observed,factors=factors)


def point_for(members,rho,*,tail=False):
    import numpy as np
    count=len(members);scalar=lambda value:np.asarray(value,dtype=np.float64)
    point=dict(mu_alpha=scalar(14. if tail else 5.3),mu_tau=scalar(.4),
        b=np.asarray([.13,-.2,.05,.1],dtype=np.float64),s_alpha=scalar(.8),s_tau=scalar(.9),
        s_e=scalar(.6),s_Q=scalar(1.3),rho=scalar(rho),
        z=np.linspace(-.2,.2,count,dtype=np.float64),u=np.linspace(.1,-.1,count,dtype=np.float64))
    for i,member in enumerate(members):
        point['epsilon_'+str(i)]=np.linspace(-.1,.15,len(member.nights),dtype=np.float64)*(1. if i%2==0 else -1.)
    return point


def qualify(data14,data28,*,settings,compile_options):
    require_admitted(settings)  # MUST precede every scientific import/build.
    global STAGE,PRIOR_INPUT_FAILURE
    PRIOR_INPUT_FAILURE=None
    import numpy as np
    from dataclasses import replace
    from pytensor.graph.basic import Constant
    from pytensor.graph.traversal import graph_inputs,ancestors
    from pytensor.tensor.random.op import RandomVariable
    from methods.support.s2_model import build,_graph
    from tooling.foundation.pa3_monitor import verify_cvm,optimizer_identity
    from contracts.domain.borrow_runtime import NATIVE_OPTIMIZER
    report=dict(kind='S2-ORIGINAL-COORDINATE-DENSITY-GRADIENT-STRUCTURAL-ONLY',
        settings=settings,coordinates='mu_alpha,mu_tau,b,s_alpha,s_tau,s_e,s_Q,rho,z,u,epsilon; all original/untransformed; jacobian=False',
        qualification_fixture_only=True,model_fitted=False,genuine_data=False,serving_authority=False,shapes=[],density=[])
    # Full production shape/input checks stay12; small graph fixtures below do
    # not introduce a shortened production adapter or live API.
    STAGE='shape'
    for data,cutoff in ((data14,14),(data28,28)):
        if data.provenance.cutoff_day!=cutoff:raise ValueError('fixed structural14/28 inputs required')
        model=build(data)
        if len(model.coords['patient'])!=12 or len(model.coords['feature'])!=4:raise AssertionError('complete12/four-feature graph required')
        for name in ('alpha','tau','e_T'):
            if model.named_vars_to_dims[name]!=('patient',):raise AssertionError('joint target member axes changed')
        if model.named_vars_to_dims['b']!=('feature',):raise AssertionError('shared four-feature b axes changed')
        report['shapes'].append(dict(cutoff=cutoff,members=list(model.coords['patient']),target=data.provenance.target_id,
            compiled=False,features=list(model.coords['feature']),
            latent_nights=[len(model.coords['night_'+str(i)]) for i in range(12)]))
    cases=[('observed',data14.members[:count],CORRELATIONS) for count in (1,2)]
    cases.append(('prior_only_empty_rows',(replace(data14.members[0],rows=()),),(0.,)))
    for fixture,members,correlations in cases:
        STAGE='graph';count=len(members);model=_graph(members,original_coordinates=True)
        expected_names=['mu_alpha','mu_tau','b','s_alpha','s_tau','s_e','s_Q','rho','z','u']+['epsilon_'+str(i) for i in range(count)]
        expected_shapes={name:() for name in expected_names}
        expected_shapes.update(b=(4,),z=(count,),u=(count,))
        expected_shapes.update({'epsilon_'+str(i):(len(p.nights),) for i,p in enumerate(members)})
        if [v.name for v in model.free_RVs]!=expected_names:raise AssertionError('exact registered free-RV set/order changed')
        names=[v.name for v in model.value_vars]
        if names!=expected_names or any(v.dtype!='float64' for v in [*model.free_RVs,*model.value_vars]):
            raise AssertionError('original value-variable order/dtype changed')
        registered=set(model.free_RVs);ownership=[]
        for output in [*model.potentials,*model.deterministics]:
            rvs={v for v in ancestors([output]) if v.owner is not None and isinstance(v.owner.op,RandomVariable)}
            if not rvs<=registered:raise AssertionError('unregistered RV ancestor in S2 output')
            ownership.append(dict(output=output.name,registered_ancestors=sorted(v.name for v in rvs)))
        for rv in model.free_RVs:
            if any(prior_input_rejected(v,rv.name,ordinal,expected_names,Constant) for ordinal,v in enumerate(rv.owner.inputs)):
                raise AssertionError('prior parameter input not float64')
        for value in graph_inputs([model.logp(jacobian=False)]):
            if isinstance(value,Constant) and getattr(value,'dtype',None)=='float32':raise AssertionError('float32 graph constant')
        STAGE='compile';compiled=[]
        def checked(fn,label):
            optimizer=optimizer_identity(fn.f.maker.mode.provided_optimizer)
            if optimizer!=NATIVE_OPTIMIZER:raise AssertionError('actual post-PyMC optimizer changed')
            compiled.append(dict(label=label,optimizer=optimizer,vm=verify_cvm(fn.f)))
            return fn
        logp=checked(model.compile_logp(jacobian=False,**compile_options),'full')
        gradient=checked(model.compile_dlogp(jacobian=False,**compile_options),'gradient')
        likelihood=checked(model.compile_logp(vars=list(model.potentials),jacobian=False,**compile_options),'likelihood')
        factor_functions={}
        for rv in model.free_RVs:
            factor_functions[rv.name]=checked(model.compile_logp(vars=[rv],jacobian=False,**compile_options),'prior:'+rv.name)
        if set(factor_functions)!=set(expected_names):raise AssertionError('prior factor inventory changed')
        for correlation in correlations:
            STAGE='density'
            # The last positive near-boundary point also exercises distant
            # clipped tails, without changing observations or accepting ties.
            point=point_for(members,correlation,tail=fixture=='observed' and correlation==CORRELATIONS[-1])
            def valid_point(value):
                if set(value)!=set(expected_names):raise AssertionError('point coordinate set changed')
                for name,array in value.items():
                    if array.dtype!=np.dtype('float64') or array.shape!=expected_shapes[name] or not np.all(np.isfinite(array)):
                        raise AssertionError('point shape/dtype/nonfinite')
                if not -.95<float(value['rho'])<.95 or any(float(value[n])<=0 for n in ('s_alpha','s_tau','s_e','s_Q')):
                    raise AssertionError('point/perturbation outside prior support')
            valid_point(point)
            expected=reference(point,members);actual=float(logp(point))
            actual_like=float(likelihood(point))
            if set(expected['factors'])!=set(expected_names):raise AssertionError('reference factor inventory changed')
            finite_values=[actual,actual_like,expected['total'],expected['prior'],expected['likelihood'],*expected['factors'].values()]
            if not all(math.isfinite(v) for v in finite_values):raise AssertionError('nonfinite full/factor/likelihood/reference')
            if abs(actual-expected['total'])>settings['density_atol']:raise AssertionError('complete S2 joint density mismatch')
            if abs(actual_like-expected['likelihood'])>settings['density_atol']:raise AssertionError('S2 observed-only likelihood mismatch')
            factor_errors={};factor_values={}
            for name,fn in factor_functions.items():
                value=float(fn({name:point[name]}));factor_errors[name]=value-expected['factors'][name]
                factor_values[name]=value
                if not math.isfinite(value) or abs(factor_errors[name])>settings['normalizer_atol']:raise AssertionError('S2 independent prior factor/normalizer mismatch')
            summed=math.fsum(factor_values.values())+actual_like;repeated=float(logp(point))
            if not math.isfinite(summed) or not math.isfinite(repeated) or abs(summed-actual)>settings['density_atol'] or abs(repeated-actual)>settings['density_atol']:
                raise AssertionError('factor/full sum or repeated density mismatch')
            if fixture=='prior_only_empty_rows' and (actual_like!=0. or expected['likelihood']!=0. or abs(actual-expected['prior'])>settings['density_atol']):
                raise AssertionError('prior-only graph likelihood must be exactly zero')
            STAGE='gradient';observed_gradient=np.asarray(gradient(point),dtype=np.float64)
            if observed_gradient.shape!=(sum(point[n].size for n in names),) or not np.all(np.isfinite(observed_gradient)):raise AssertionError('nonfinite/wrong shape S2 gradient')
            sweeps=[];directions=[]
            for direction_id in (0,1):
                direction={name:np.asarray((.01*((np.arange(point[name].size).reshape(point[name].shape)+j+direction_id)%7-3)),dtype=np.float64)
                           for j,name in enumerate(names)}
                direction['rho']=np.asarray(.001 if direction_id==0 else -.001,dtype=np.float64)
                vector=np.concatenate([np.ravel(direction[name]) for name in names]);analytic=float(observed_gradient@vector)
                if not math.isfinite(analytic) or not np.all(np.isfinite(vector)):raise AssertionError('nonfinite analytic direction')
                directions.append(dict(direction=direction_id,arrays={n:direction[n].tolist() for n in names}))
                for step in settings['steps']:
                    plus={n:point[n]+step*direction[n] for n in names};minus={n:point[n]-step*direction[n] for n in names}
                    valid_point(plus);valid_point(minus)
                    plus_value=reference(plus,members)['total'];minus_value=reference(minus,members)['total']
                    if not math.isfinite(plus_value) or not math.isfinite(minus_value):raise AssertionError('nonfinite finite-difference reference')
                    finite=(plus_value-minus_value)/(2*step)
                    error=abs(analytic-finite);bound=settings['gradient_atol']+settings['gradient_rtol']*abs(finite)
                    if not math.isfinite(finite) or error>bound:raise AssertionError('S2 directional gradient step-sweep mismatch')
                    sweeps.append(dict(direction=direction_id,step=step,analytic=analytic,finite_difference=finite,error=error,bound=bound))
            negative={} if fixture=='prior_only_empty_rows' else {name:reference(point,members,**flag)['total'] for name,flag in (
                ('wrong_A_minus_half',dict(wrong_centering=True)),('omitted_reward',dict(omit_last=True)),('duplicate_reward',dict(duplicate_first=True)))}
            if fixture=='observed' and any(not math.isfinite(v) or abs(actual-v)<=settings['density_atol'] for v in negative.values()):raise AssertionError('fixture fails to distinguish incorrect likelihood/centering')
            report['density'].append(dict(fixture=fixture,members=count,rho=correlation,tail_point=fixture=='observed' and correlation==CORRELATIONS[-1],
                actual=actual,reference=expected,total_error=actual-expected['total'],likelihood_actual=actual_like,
                factor_values=factor_values,factor_errors=factor_errors,factor_full_sum=summed,repeated_full=repeated,
                negative_controls=negative,gradient_sweeps=sweeps,directions=directions,value_variable_order=names,
                point={n:point[n].tolist() for n in names},coordinate_shapes={n:list(expected_shapes[n]) for n in names},
                compiled=compiled,ownership=ownership,prior_only_fixture_not_policy_input=fixture=='prior_only_empty_rows'))
    STAGE='serialization'
    return report
