"""Separate source-only cohort execution identity; legacy guards unchanged."""
import math
from .analysis import reference, sha, canonical
from .borrow_runtime import (POLICY, POLICY_REF, NATIVE_OPTIMIZER, runtime_origin, cohort_coordinate_layout)
from .cohort import COORDINATE_REF

COHORT_POLICY_REF=reference('poc-cohort-native-cvm-v1',dict(compile_policy=POLICY_REF,
    coordinates=COORDINATE_REF,scope='One joint cohort V0/V1 model; original native initialization/settings; qualification required'))


def execution_binding(product, origin):
    runtime_origin(origin['learner_image'],origin['source_commit'])
    return dict(kind='cohort_host_launch_v1',attempt_id=product.attempt_id,policy=COHORT_POLICY_REF,
        input_sha256=sha(product.model_dump(mode='json')),cohort_sha256=product.cohort_sha256,
        manifest_sha256=product.cohort.manifest_sha256,source_set_sha256=product.source_set_sha256,
        cutoff=product.cohort.manifest.cutoff.isoformat(),configuration=product.request.configuration.model_dump(),
        numerical_seeds=product.numerical_seeds.model_dump(),
        layout=cohort_coordinate_layout(product.cohort,borrowed=product.sources is not None),**origin)


def validate_execution(execution, product, trusted):
    if not isinstance(execution,dict) or not isinstance(trusted,dict) or not trusted:
        raise ValueError('Cohort requires a trusted host launch binding.')
    expected=execution_binding(product,runtime_origin(trusted.get('learner_image',''),trusted.get('source_commit','')))
    if trusted!=expected or execution.get('kind')!='cohort_native_execution_v1':
        raise ValueError('Cohort trusted host launch mismatch.')
    if any(execution.get(k)!=v for k,v in expected.items() if k!='kind'):
        raise ValueError('Cohort worker input/layout/origin differs from trusted launch.')
    records=execution.get('native_compilations')
    if execution.get('prior_released_before_posterior') is not True or not isinstance(records,list) or not 1<=len(records)<=2:
        raise ValueError('Cohort requires original prior lifetime and native compilation proof.')
    for index,compilation in enumerate(records,1):
        vm=compilation.get('actual_vm',{})
        if (vm.get('vm_type')!=POLICY['actual_vm'] or vm.get('linker')!='VMLinker'
                or any(vm.get(k) is not True for k in ('use_cloop','c_thunks','callback_empty','callback_input_empty'))
                or canonical(compilation.get('coordinate_map'))!=canonical(expected['layout']['layout'])
                or compilation.get('compiled_optimizer')!=NATIVE_OPTIMIZER
                or type(compilation.get('index')) is not int or compilation['index']!=index
                or type(compilation.get('seconds')) not in (int,float) or not math.isfinite(compilation['seconds']) or compilation['seconds']<0):
            raise ValueError('Cohort actual native VM/order/optimizer compilation mismatch.')
