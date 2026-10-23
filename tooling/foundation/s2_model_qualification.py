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
    import numpy as np
    from pytensor.graph.basic import Constant
    from pytensor.graph.traversal import graph_inputs
    from methods.support.s2_model import build,_graph
    from tooling.foundation.pa3_monitor import verify_cvm
    report=dict(kind='S2-ORIGINAL-COORDINATE-DENSITY-GRADIENT-STRUCTURAL-ONLY',
        settings=settings,coordinates='mu_alpha,mu_tau,b,s_alpha,s_tau,s_e,s_Q,rho,z,u,epsilon; all original/untransformed; jacobian=False',
        qualification_fixture_only=True,model_fitted=False,genuine_data=False,serving_authority=False,shapes=[],density=[])
    # Full production shape/input checks stay12; small graph fixtures below do
    # not introduce a shortened production adapter or live API.
    for data,cutoff in ((data14,14),(data28,28)):
        if data.provenance.cutoff_day!=cutoff:raise ValueError('fixed structural14/28 inputs required')
        model=build(data)
        if len(model.coords['patient'])!=12 or len(model.coords['feature'])!=4:raise AssertionError('complete12/four-feature graph required')
        for name in ('alpha','tau','e_T'):
            if model.named_vars_to_dims[name]!=('patient',):raise AssertionError('joint target member axes changed')
        if model.named_vars_to_dims['b']!=('feature',):raise AssertionError('shared four-feature b axes changed')
        report['shapes'].append(dict(cutoff=cutoff,members=list(model.coords['patient']),features=list(model.coords['feature']),
            latent_nights=[len(model.coords['night_'+str(i)]) for i in range(12)]))
    for count in (1,2):
        members=data14.members[:count];model=_graph(members,original_coordinates=True)
        names=[v.name for v in model.value_vars]
        if any('__' in name for name in names):raise AssertionError('qualification must use untransformed original coordinates')
        for value in graph_inputs([model.logp(jacobian=False)]):
            if isinstance(value,Constant) and getattr(value,'dtype',None)=='float32':raise AssertionError('float32 graph constant')
        logp=model.compile_logp(jacobian=False,**compile_options);verify_cvm(logp.f)
        gradient=model.compile_dlogp(jacobian=False,**compile_options);verify_cvm(gradient.f)
        likelihood=model.compile_logp(vars=list(model.potentials),jacobian=False,**compile_options);verify_cvm(likelihood.f)
        factor_functions={}
        for rv in model.free_RVs:
            fn=model.compile_logp(vars=[rv],jacobian=False,**compile_options);verify_cvm(fn.f);factor_functions[rv.name]=fn
        for correlation in CORRELATIONS:
            # The last positive near-boundary point also exercises distant
            # clipped tails, without changing observations or accepting ties.
            point=point_for(members,correlation,tail=correlation==CORRELATIONS[-1])
            expected=reference(point,members);actual=float(logp(point))
            actual_like=float(likelihood(point))
            if not np.isfinite(actual) or abs(actual-expected['total'])>settings['density_atol']:raise AssertionError('complete S2 joint density mismatch')
            if abs(actual_like-expected['likelihood'])>settings['density_atol']:raise AssertionError('S2 observed-only likelihood mismatch')
            factor_errors={}
            for name,fn in factor_functions.items():
                value=float(fn({name:point[name]}));factor_errors[name]=value-expected['factors'][name]
                if not math.isfinite(value) or abs(factor_errors[name])>settings['normalizer_atol']:raise AssertionError('S2 independent prior factor/normalizer mismatch')
            observed_gradient=np.asarray(gradient(point),dtype=np.float64)
            if not np.all(np.isfinite(observed_gradient)):raise AssertionError('nonfinite S2 gradient')
            sweeps=[]
            for direction_id in (0,1):
                direction={name:np.asarray((.01*((np.arange(point[name].size).reshape(point[name].shape)+j+direction_id)%7-3)),dtype=np.float64)
                           for j,name in enumerate(names)}
                direction['rho']=np.asarray(.001 if direction_id==0 else -.001,dtype=np.float64)
                vector=np.concatenate([np.ravel(direction[name]) for name in names]);analytic=float(observed_gradient@vector)
                for step in settings['steps']:
                    plus={n:point[n]+step*direction[n] for n in names};minus={n:point[n]-step*direction[n] for n in names}
                    finite=(reference(plus,members)['total']-reference(minus,members)['total'])/(2*step)
                    error=abs(analytic-finite);bound=settings['gradient_atol']+settings['gradient_rtol']*abs(finite)
                    if not math.isfinite(finite) or error>bound:raise AssertionError('S2 directional gradient step-sweep mismatch')
                    sweeps.append(dict(direction=direction_id,step=step,analytic=analytic,finite_difference=finite,error=error,bound=bound))
            negative={name:reference(point,members,**flag)['total'] for name,flag in (
                ('wrong_A_minus_half',dict(wrong_centering=True)),('omitted_reward',dict(omit_last=True)),('duplicate_reward',dict(duplicate_first=True)))}
            if any(abs(actual-v)<=settings['density_atol'] for v in negative.values()):raise AssertionError('fixture fails to distinguish incorrect likelihood/centering')
            report['density'].append(dict(members=count,rho=correlation,tail_point=correlation==CORRELATIONS[-1],
                actual=actual,reference=expected,total_error=actual-expected['total'],likelihood_actual=actual_like,
                factor_errors=factor_errors,negative_controls=negative,gradient_sweeps=sweeps,value_variable_order=names))
    return report
