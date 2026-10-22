"""Mocked structural provenance controls, NOT actual VM/COPY qualification."""
import copy
import os
import unittest
from unittest.mock import patch
from contracts.domain.cohort import make_cohort_input
from contracts.domain.cohort_runtime import execution_binding,validate_execution,INITIALIZER_NATIVE_OPTIMIZER
from contracts.domain.analysis import sha
from contracts.domain.borrow_runtime import POLICY,NATIVE_OPTIMIZER
from tests.contracts.test_cohort import database,export
from tests.contracts.test_cohort_qualification import qualified_input


class CohortRuntimeControls(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,dict(REMISSION_COHORT_REVIEWED_LEARNER_IMAGE='sha256:'+'1'*64,
            REMISSION_COHORT_REVIEWED_SOURCE_COMMIT='2'*40))
        self.env.start();self.addCleanup(self.env.stop)

    def test_exact_joint_binding_and_negative_map_seed_origin_prior_controls(self):
        product=make_cohort_input(qualified_input().cohort,'mocked-structural-control')
        trusted=execution_binding(product,dict(learner_image='sha256:'+'1'*64,source_commit='2'*40))
        execution=copy.deepcopy(trusted)
        execution.update(kind='cohort_native_execution_v1',prior_released_before_posterior=True,
            native_compilations=[dict(index=1,fit='initial',fit_seed=product.numerical_seeds.nuts,seconds=1.,coordinate_map=trusted['layout']['layout'],compiled_optimizer=NATIVE_OPTIMIZER,
                actual_vm=dict(vm_type=POLICY['actual_vm'],linker='VMLinker',use_cloop=True,c_thunks=True,callback_empty=True,callback_input_empty=True))])
        execution['callable_custody']=[dict(stage=stage,fit=fit,invocation=1,function_identity=123,
            binding_sha256=sha(trusted),actual_vm=copy.deepcopy(execution['native_compilations'][0]['actual_vm']),
            compiled_optimizer=INITIALIZER_NATIVE_OPTIMIZER if 'initializer' in stage else NATIVE_OPTIMIZER,
            **({'coordinate_map':trusted['layout']['layout']} if stage.endswith('_point') else {}))
            for fit,stage in [('prior','prior_forward'),*[('initial',s) for s in
                ('support_initializer','jitter_initializer','support_initializer_point','jitter_initializer_point','recording')]]]
        validate_execution(execution,product,trusted)
        for mutate in [lambda x:x.update(source_commit='3'*40),lambda x:x.update(manifest_sha256='0'*64),
                lambda x:x['numerical_seeds'].update(nuts=x['numerical_seeds']['nuts']+1),
                lambda x:x.update(prior_released_before_posterior=False),
                lambda x:x['native_compilations'][0]['coordinate_map'][6].update(shape=[35]),
                lambda x:x['native_compilations'][0]['actual_vm'].update(vm_type='PythonVM'),
                lambda x:x['native_compilations'][0].update(compiled_optimizer={}),
                lambda x:x['native_compilations'][0].update(seconds=float('nan')),
                lambda x:x['native_compilations'][0].update(fit='extension'),
                lambda x:x['native_compilations'][0].update(fit_seed=0),
                lambda x:x['callable_custody'].pop(),
                lambda x:x['callable_custody'][0].update(binding_sha256='0'*64),
                lambda x:x['callable_custody'][1].update(compiled_optimizer=NATIVE_OPTIMIZER)]:
            changed=copy.deepcopy(execution);mutate(changed)
            with self.assertRaises(ValueError):validate_execution(changed,product,trusted)
        with patch.dict(os.environ,dict(REMISSION_COHORT_REVIEWED_LEARNER_IMAGE='sha256:'+'3'*64)):
            with self.assertRaises(ValueError):validate_execution(execution,product,trusted)
        with self.assertRaises(ValueError):validate_execution(execution,product,None)
        extended=copy.deepcopy(execution)
        extended['native_compilations'].append(dict(extended['native_compilations'][0],
            index=2,fit='extension',fit_seed=product.numerical_seeds.nuts+1))
        extended['callable_custody'].extend([dict(copy.deepcopy(r),fit='extension')
            for r in execution['callable_custody'] if r['fit']=='initial'])
        validate_execution(extended,product,trusted)
        for mutate in [lambda x:x['native_compilations'].reverse(),
                lambda x:x['native_compilations'].append(copy.deepcopy(x['native_compilations'][0])),
                lambda x:x['native_compilations'][1].update(fit='initial'),
                lambda x:x['callable_custody'][1].update(invocation=9)]:
            changed=copy.deepcopy(extended);mutate(changed)
            with self.assertRaises(ValueError):validate_execution(changed,product,trusted)

    def test_runtime_configuration_is_lazy_deny_default_and_exact(self):
        from contracts.domain.cohort_runtime import reviewed_runtime
        origin=dict(learner_image='sha256:'+'1'*64,source_commit='2'*40)
        product=qualified_input()
        for config in ({},dict(REMISSION_COHORT_REVIEWED_LEARNER_IMAGE=origin['learner_image']),
                dict(REMISSION_COHORT_REVIEWED_SOURCE_COMMIT=origin['source_commit']),
                dict(REMISSION_COHORT_REVIEWED_LEARNER_IMAGE='bad',REMISSION_COHORT_REVIEWED_SOURCE_COMMIT='bad')):
            with self.subTest(config=config),patch.dict(os.environ,config,clear=True):
                with self.assertRaises(ValueError):execution_binding(product,origin)
                # Shared legacy modules remain usable with absent/invalid cohort config.
                from contracts.domain.borrow_runtime import runtime_origin
                self.assertEqual(runtime_origin(**dict(image=origin['learner_image'],source=origin['source_commit'])),origin)
        for changed in [dict(origin,learner_image='sha256:'+'3'*64),dict(origin,source_commit='3'*40),
                dict(origin,extra='untrusted'),{},None]:
            with self.assertRaises(ValueError):reviewed_runtime(changed)
        db=database()
        try:fixture=make_cohort_input(export(db),'structural-unqualified')
        finally:db.close()
        with self.assertRaises(ValueError):execution_binding(fixture,origin)


if __name__=='__main__':unittest.main()
