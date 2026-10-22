"""Consumer-safe execution identity; numerical configuration/target is unchanged."""
import re
from .analysis import reference, sha

OPTIMIZER = dict(type='RewriteDatabaseQuery', name='OPT_FAST_RUN', include=['fast_run'], exclude=[], require=[],
                 subquery={}, position_cutoff='inf', extra_rewrites=[])
POLICY = dict(id='poc-borrow-native-cvm-v1', version='1.0.0', optimizer=OPTIMIZER,
    requested_linker='VMLinker', actual_vm='pytensor.link.c.cvm.CVM', use_cloop=True, c_thunks=True,
    callbacks_empty=True, whole_vm_fallback_allowed=False, floatX='float64',
    scope='Borrow-only compile kwargs; original target/priors/Q64/nativeNUTS/settings; V0 unchanged')
POLICY_REF = reference(POLICY['id'], POLICY)


def runtime_origin(image, source):
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image) or not re.fullmatch(r'[a-f0-9]{40}', source):
        raise ValueError('borrow execution requires actual immutable image/source provenance')
    return dict(learner_image=image, source_commit=source)


def validate_execution(execution, product):
    expected = dict(policy=POLICY_REF, input_sha256=sha(product.model_dump(mode='json')),
        history_sha256=product.history_sha256, source_set_sha256=product.source_set_sha256,
        configuration=product.request.configuration.model_dump(), numerical_seeds=product.numerical_seeds.model_dump())
    if any(execution.get(k) != v for k,v in expected.items()) or execution.get('cutoff') != product.history.cutoff.isoformat():
        raise ValueError('borrow execution input/policy binding mismatch')
    runtime_origin(execution.get('learner_image', ''), execution.get('source_commit', ''))
    if execution.get('prior_released_before_posterior') is not True or not execution.get('native_compilations'):
        raise ValueError('borrow execution lacks prior lifetime/native compile evidence')
    for compilation in execution['native_compilations']:
        vm = compilation.get('actual_vm', {})
        if (vm.get('vm_type') != POLICY['actual_vm'] or vm.get('linker') != 'VMLinker' or vm.get('use_cloop') is not True
                or vm.get('c_thunks') is not True or vm.get('callback_empty') is not True or vm.get('callback_input_empty') is not True):
            raise ValueError('borrow execution actual VM mismatch')
