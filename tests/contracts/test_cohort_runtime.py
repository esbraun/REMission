"""Mocked structural provenance controls, NOT actual VM/COPY qualification."""
import copy
import unittest
from contracts.domain.cohort import make_cohort_input
from contracts.domain.cohort_runtime import execution_binding,validate_execution
from contracts.domain.borrow_runtime import POLICY,NATIVE_OPTIMIZER
from tests.contracts.test_cohort import database,export


class CohortRuntimeControls(unittest.TestCase):
    def test_exact_joint_binding_and_negative_map_seed_origin_prior_controls(self):
        db=database()
        try:product=make_cohort_input(export(db),'mocked-structural-control')
        finally:db.close()
        trusted=execution_binding(product,dict(learner_image='sha256:'+'1'*64,source_commit='2'*40))
        execution=copy.deepcopy(trusted)
        execution.update(kind='cohort_native_execution_v1',prior_released_before_posterior=True,
            native_compilations=[dict(index=1,seconds=1.,coordinate_map=trusted['layout']['layout'],compiled_optimizer=NATIVE_OPTIMIZER,
                actual_vm=dict(vm_type=POLICY['actual_vm'],linker='VMLinker',use_cloop=True,c_thunks=True,callback_empty=True,callback_input_empty=True))])
        validate_execution(execution,product,trusted)
        for mutate in [lambda x:x.update(source_commit='3'*40),lambda x:x.update(manifest_sha256='0'*64),
                lambda x:x['numerical_seeds'].update(nuts=x['numerical_seeds']['nuts']+1),
                lambda x:x.update(prior_released_before_posterior=False),
                lambda x:x['native_compilations'][0]['coordinate_map'][6].update(shape=[35]),
                lambda x:x['native_compilations'][0]['actual_vm'].update(vm_type='PythonVM'),
                lambda x:x['native_compilations'][0].update(compiled_optimizer={}),
                lambda x:x['native_compilations'][0].update(seconds=float('nan'))]:
            changed=copy.deepcopy(execution);mutate(changed)
            with self.assertRaises(ValueError):validate_execution(changed,product,trusted)
        with self.assertRaises(ValueError):validate_execution(execution,product,None)


if __name__=='__main__':unittest.main()
