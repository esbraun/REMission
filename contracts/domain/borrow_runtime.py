"""Consumer-safe execution identity; numerical configuration/target is unchanged."""
import re
import math
from .analysis import reference, sha

OPTIMIZER = dict(type='RewriteDatabaseQuery', name='OPT_FAST_RUN', include=['fast_run'], exclude=[], require=[],
                 subquery={}, position_cutoff='inf', extra_rewrites=[])
POLICY = dict(id='poc-borrow-native-cvm-v1', version='1.0.0', optimizer=OPTIMIZER,
    requested_linker='VMLinker', actual_vm='pytensor.link.c.cvm.CVM', use_cloop=True, c_thunks=True,
    callbacks_empty=True, whole_vm_fallback_allowed=False, floatX='float64',
    scope='Borrow-only compile kwargs; original target/priors/Q64/nativeNUTS/settings; V0 unchanged')
POLICY_REF = reference(POLICY['id'], POLICY)
NATIVE_OPTIMIZER = dict(OPTIMIZER, name=None, include=['fast_run', 'local_check_parameter_to_ninf_switch', 'random_make_inplace'])


def runtime_origin(image, source):
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image) or not re.fullmatch(r'[a-f0-9]{40}', source):
        raise ValueError('borrow execution requires actual immutable image/source provenance')
    return dict(learner_image=image, source_commit=source)


def execution_binding(product, origin):
    runtime_origin(origin['learner_image'],origin['source_commit'])
    return dict(kind='borrow_host_launch_v1',attempt_id=product.attempt_id,policy=POLICY_REF,
        input_sha256=sha(product.model_dump(mode='json')),history_sha256=product.history_sha256,
        source_set_sha256=product.source_set_sha256,cutoff=product.history.cutoff.isoformat(),
        configuration=product.request.configuration.model_dump(),numerical_seeds=product.numerical_seeds.model_dump(),**origin)


def coordinate_layout(history):
    shapes=[('sd_b_log__',[]),('sd_beta_log__',[2]),('rho_interval__',[]),('sigma_e_log__',[]),
        ('sigma_isi_log__',[]),('sigma_quality_log__',[]),('guide_innovation',[(history.cutoff-history.origin).days+21]),
        ('p_adherence_logodds__',[]),('observation_rate_logodds__',[]),('source_bias',[2]),('source_tau_log__',[])]
    layout=[];offset=0
    for name,shape in shapes:
        size=math.prod(shape)
        layout.append(dict(name=name,shape=shape,dtype='float64',start=offset,stop=offset+size));offset+=size
    return layout


def validate_execution(execution, product, trusted):
    # trusted is loaded from the service-owned attempt, NEVER from result.json.
    if not isinstance(execution,dict) or not isinstance(trusted,dict) or not trusted:
        raise ValueError('missing trusted host launch binding')
    if trusted!=execution_binding(product,runtime_origin(trusted.get('learner_image',''),trusted.get('source_commit',''))):
        raise ValueError('missing or invalid trusted host launch binding')
    expected = dict(policy=POLICY_REF, input_sha256=sha(product.model_dump(mode='json')),
        history_sha256=product.history_sha256, source_set_sha256=product.source_set_sha256,
        configuration=product.request.configuration.model_dump(), numerical_seeds=product.numerical_seeds.model_dump())
    if any(execution.get(k) != v for k,v in expected.items()) or execution.get('cutoff') != product.history.cutoff.isoformat():
        raise ValueError('borrow execution input/policy binding mismatch')
    runtime_origin(execution.get('learner_image', ''), execution.get('source_commit', ''))
    if any(execution.get(k)!=trusted[k] for k in ('learner_image','source_commit')):
        raise ValueError('worker origin differs from trusted host launch')
    if execution.get('prior_released_before_posterior') is not True or not isinstance(execution.get('native_compilations'),list) or not execution['native_compilations']:
        raise ValueError('borrow execution lacks prior lifetime/native compile evidence')
    for compilation in execution['native_compilations']:
        if not isinstance(compilation,dict):raise ValueError('invalid native compile evidence')
        vm = compilation.get('actual_vm', {})
        if not isinstance(vm,dict):raise ValueError('invalid native VM evidence')
        if (vm.get('vm_type') != POLICY['actual_vm'] or vm.get('linker') != 'VMLinker' or vm.get('use_cloop') is not True
                or vm.get('c_thunks') is not True or vm.get('callback_empty') is not True or vm.get('callback_input_empty') is not True):
            raise ValueError('borrow execution actual VM mismatch')
        from .analysis import canonical
        if (canonical(compilation.get('coordinate_map'))!=canonical(coordinate_layout(product.history))
                or compilation.get('compiled_optimizer')!=NATIVE_OPTIMIZER
                or type(compilation.get('index')) is not int or compilation['index']<1
                or type(compilation.get('seconds')) not in (int,float) or not math.isfinite(compilation['seconds']) or compilation['seconds']<0):
            raise ValueError('borrow execution native coordinate map/optimizer/compile evidence mismatch')
