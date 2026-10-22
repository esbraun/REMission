"""Non-fitting controls: actual tiny CVM and real worker graph-lifetime seam."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import weakref

import numpy as np
import pymc as pm
from contracts.domain.borrow_runtime import OPTIMIZER, runtime_origin
from methods.visit import borrow_execution as execution
from methods.visit.model import sample as v0_sample


class BorrowExecutionTests(unittest.TestCase):
    def test_native_sampler_forwarding_actual_tiny_cvm_and_v0_no_override(self):
        with pm.Model() as model:
            pm.Normal('theta', 0, 1, shape=2)
        captures, guarded = [], []
        sentinel = object()

        def sample(**kwargs):
            captures.append(kwargs)
            if 'compile_kwargs' in kwargs:
                fn = model.logp_dlogp_function(ravel_inputs=True, initial_point=model.initial_point(), **kwargs['compile_kwargs'])
                value, gradient, mapping = execution.native_call(fn, {'theta':np.array([.2,-.3])}, model.continuous_value_vars)
                np.testing.assert_allclose(gradient, [-.2,.3], atol=1e-12)
                self.assertTrue(np.isfinite(value))
                self.assertEqual(mapping, [dict(name='theta', shape=[2], dtype='float64', start=0, stop=2)])
                with patch.object(fn._pytensor_function, 'vm', object()):
                    with self.assertRaisesRegex(ValueError, 'actual native VM'):
                        execution.verify_cvm(fn._pytensor_function)
            return sentinel

        original = model.logp_dlogp_function
        with patch.object(pm, 'sample', side_effect=sample):
            expected=[dict(name='theta',shape=[2],dtype='float64',start=0,stop=2)]
            self.assertIs(execution.sample(model, 739, on_compile=guarded.append,expected_layout=expected), sentinel)
            self.assertIs(v0_sample(model, 739), sentinel)
        self.assertEqual(model.logp_dlogp_function, original)
        with execution.guarded_native(model, lambda value:None):
            with self.assertRaisesRegex(ValueError, 'forwarded native grad_vars'):
                model.logp_dlogp_function(grad_vars=[], **execution.compilation_options())
            # Satisfy the mandatory real compile/evidence control after the
            # rejected subset, keeping the wrapper's no-call veto meaningful.
            model.logp_dlogp_function(ravel_inputs=True, **execution.compilation_options())
        self.assertEqual(captures[0].keys()-captures[1].keys(), {'compile_kwargs'})
        self.assertEqual({k:v for k,v in captures[0].items() if k != 'compile_kwargs'}, captures[1])
        self.assertEqual(execution.optimizer_identity(captures[0]['compile_kwargs']['mode'].provided_optimizer), OPTIMIZER)
        self.assertEqual(len(guarded), 1)
        self.assertEqual(guarded[0]['actual_vm']['vm_type'], 'pytensor.link.c.cvm.CVM')

    def test_guard_must_be_used_and_restores_on_failure(self):
        with pm.Model() as model:
            pm.Normal('theta')
        original = model.logp_dlogp_function
        with self.assertRaisesRegex(ValueError, 'did not expose'):
            with execution.guarded_native(model, lambda value:None):
                pass
        self.assertEqual(model.logp_dlogp_function, original)
        with self.assertRaisesRegex(RuntimeError, 'failure-control'):
            with execution.guarded_native(model, lambda value:None):
                raise RuntimeError('failure-control')
        self.assertEqual(model.logp_dlogp_function, original)

    def test_prior_predictive_compile_keyword_is_supported_on_tiny_model(self):
        with pm.Model():
            pm.Beta('unconditioned_adherence', 1, 1)
            prior = pm.sample_prior_predictive(draws=4, random_seed=723, compile_kwargs=execution.compilation_options())
        self.assertEqual(prior['prior']['unconditioned_adherence'].size, 4)

    def test_origin_rejects_mutable_missing_identity(self):
        for image, source in [('candidate','a'*40), ('sha256:'+'a'*64,'not-recorded')]:
            with self.assertRaises(ValueError):
                runtime_origin(image, source)

    def test_worker_saves_and_releases_prior_before_posterior_graph(self):
        from services.learner import analysis_worker as worker
        from methods.visit import borrow_model
        from contracts.domain.borrowing import make_borrow_input
        from services.foundation.analysis_sources import load_source
        source = Path('tests/integration/replay/fixtures/pa3-legacy-v0-input.json')
        legacy = worker.parse_input(source.read_bytes())
        # A named unit-control intent, not the actual queued4ff attempt/profile.
        product = make_borrow_input(legacy.history, 'analysis-prior-lifetime-control', load_source('source-7c97862d', legacy.history.cutoff))
        data = worker.inputs(product.history)
        n = len(data['nights'])
        group = {name:SimpleNamespace(values=value) for name,value in dict(
            burden=np.full((1,64,n), 19.), sigma_isi=np.ones((1,64)), sigma_quality=np.ones((1,64)),
            source_g=np.linspace(-2,2,64)[None,:], p_adherence=np.linspace(.01,.99,64)[None,:]).items()}
        references, calls = [], []

        class Prior:
            def __enter__(self):return self
            def __exit__(self,*args):pass

        def build(*args, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                self.assertEqual(kwargs, dict(guide=False, prior_predictive=True))
                model = Prior()
                references.append(weakref.ref(model))
                return model
            self.assertIsNone(references[0](), 'prior graph must be dead before posterior construction')
            raise RuntimeError('after-prior-release-control')

        with tempfile.TemporaryDirectory() as directory, patch.object(borrow_model, 'build_joint', side_effect=build), \
                patch.object(pm, 'sample_prior_predictive', return_value={'prior':group}) as prior, \
                patch.object(execution, 'compilation_options', return_value={}), \
                patch.dict('os.environ', dict(REMISSION_LEARNER_IMAGE='sha256:'+'a'*64, REMISSION_SOURCE_COMMIT='b'*40)):
            source = Path(directory)/'input.json'
            source.write_text(product.model_dump_json())
            result = worker.run(source, Path(directory)/'output')
            self.assertEqual(result['status'], 'failed')
            self.assertIn('after-prior-release-control', result['reason'])
            self.assertTrue(result['diagnostics']['execution']['prior_released_before_posterior'])
            self.assertEqual(prior.call_args.kwargs['random_seed'], product.numerical_seeds.prior_check)
            self.assertTrue((Path(directory)/'output/source-prior-predictive.npz').is_file())
            self.assertTrue((Path(directory)/'output/prior-predictive.npz').is_file())
            self.assertTrue((Path(directory)/'output/failure.log').is_file())
            self.assertEqual(len(calls), 2)


if __name__ == '__main__':unittest.main()
