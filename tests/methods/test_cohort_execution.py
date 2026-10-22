"""Lightweight callable doubles; no graph, compiler, sampler or actual-mode proof."""
from functools import wraps
from contextlib import contextmanager
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

import numpy as np
from pytensor.compile.mode import Mode, get_default_mode
from contracts.domain.borrow_runtime import POLICY, NATIVE_OPTIMIZER
from methods.visit import cohort_execution as execution

LAYOUT = [dict(name='theta', shape=[2], dtype='float64', start=0, stop=2)]
VM = dict(vm_type=POLICY['actual_vm'], linker='VMLinker', use_cloop=True, c_thunks=True,
    callback_empty=True, callback_input_empty=True)


class Function:
    def __init__(self, mode, calls):
        self.maker = SimpleNamespace(mode=mode)
        self.vm = object()
        self.calls = calls

    def __call__(self, *args, **kwargs):
        self.calls.append(('evaluate', args, kwargs))
        return [np.array([.2, -.3], dtype='float64')]


class Model:
    def __init__(self, calls, dtype='float64'):
        self.calls, self.dtype = calls, dtype
        self.continuous_value_vars = [SimpleNamespace(name='theta', dtype='float64')]

    def _make_initial_point(self, **kwargs):
        self.calls.append(('make', kwargs))
        function = execution.initial_point.compile(inputs=[], outputs=['original-expression'], mode=execution.FAST_COMPILE)
        @wraps(function)
        def seeded(seed):
            self.calls.append(('original-reseed', seed))
            return {'theta': function()[0].astype(self.dtype)}
        return seeded

    def compile_fn(self, *args, **kwargs):
        self.calls.append(('compile_fn', args, kwargs))
        mode = Mode(linker='cvm', optimizer=kwargs['mode'].provided_optimizer.including(
            'random_make_inplace', 'local_check_parameter_to_ninf_switch'))
        return Function(mode, self.calls)

    def check_start_vals(self, *args, **kwargs):
        raise AssertionError('unqualified diagnostic must not run')

    def __enter__(self):return self
    def __exit__(self,*args):return False


class CohortCallableControls(unittest.TestCase):
    def setUp(self):
        self.calls, self.compiled = [], []
        def compiler(*args, **kwargs):
            self.calls.append(('compile', args, kwargs))
            mode = Mode(linker='cvm', optimizer=kwargs['mode'].provided_optimizer.including(
                'random_make_inplace', 'local_check_parameter_to_ninf_switch'))
            function = Function(mode, self.calls);self.compiled.append(function)
            return function
        self.compiler = compiler
        self.patches = [patch.object(execution.initial_point, 'compile', compiler),
            patch.object(execution.pytensorf, 'compile', compiler),
            patch.object(execution, 'verify_cvm', side_effect=lambda fn: dict(VM))]
        for item in self.patches:item.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    def context(self, model, events):
        return execution.owned_callables(model, fit='initial', binding_sha256='a'*64,
            on_event=events.append, expected_layout=LAYOUT)

    def test_original_seeded_algorithm_raw_points_mode_and_callable_preserved(self):
        model=Model(self.calls);events=[]
        before=execution.optimizer_identity(execution.FAST_COMPILE.provided_optimizer)
        overrides={'theta': np.array([1., 2.])};jitter={object()}
        with self.context(model, events):
            seeded=model._make_initial_point(overrides=overrides,jitter_rvs=jitter,return_transformed=True)
            self.assertIs(seeded.maker, self.compiled[0].maker)
            point=seeded(739)
            self.assertEqual(point['theta'].dtype, np.dtype('float64'))
            self.assertEqual(self.calls[0], ('make', dict(overrides=overrides,jitter_rvs=jitter,return_transformed=True)))
            self.assertEqual([c[1] for c in self.calls if c[0]=='original-reseed'], [739])
            self.assertEqual(sum(c[0]=='evaluate' for c in self.calls), 1)
        self.assertEqual(execution.optimizer_identity(execution.FAST_COMPILE.provided_optimizer), before)
        self.assertIs(execution.initial_point.compile, self.compiler)
        self.assertEqual(events[0]['stage'], 'jitter_initializer')
        self.assertEqual(events[1]['coordinate_map'], LAYOUT)
        self.assertNotIn('_make_initial_point', model.__dict__)

    def test_cleanup_observer_compile_failures_and_unrelated_following_use(self):
        for observer_failure in (False, True):
            model=Model(self.calls);before=dict(model.__dict__)
            with self.subTest(observer=observer_failure):
                def observer(value):raise RuntimeError('observer')
                with self.assertRaises(RuntimeError):
                    with execution.owned_callables(model,fit='initial',binding_sha256='a'*64,
                            on_event=observer if observer_failure else lambda value:None):
                        if observer_failure:model._make_initial_point()
                        else:
                            with patch.object(execution,'Mode',side_effect=RuntimeError('compile')):
                                model._make_initial_point()
                self.assertEqual(model.__dict__, before)
                self.assertIs(execution.initial_point.compile, self.compiler)
                self.compiler(mode=execution.FAST_COMPILE)  # Subsequent unrelated compiler works.

    def test_owner_nested_concurrent_and_exhausted_jitter_reject(self):
        model=Model(self.calls);events=[];errors=[]
        with self.context(model, events):
            with self.assertRaisesRegex(ValueError,'reentrant'):
                with self.context(model,events):pass
            with self.assertRaisesRegex(ValueError,'outside owned model'):
                execution.initial_point.compile(mode=execution.FAST_COMPILE)
            def foreign():
                try:model._make_initial_point()
                except ValueError as error:errors.append(str(error))
            thread=threading.Thread(target=foreign);thread.start();thread.join()
            self.assertEqual(len(errors),1);self.assertIn('owner thread',errors[0])
            with self.assertRaisesRegex(ValueError,'exhausted-jitter'):
                model.check_start_vals({})
        self.assertFalse(execution._OWNER.locked())

    def test_raw_float32_nonfinite_shape_order_reject_before_cast(self):
        for value in [np.array([1.,2.],dtype='float32'), np.array([np.nan,2.]), np.array([1.])]:
            with self.subTest(dtype=value.dtype,shape=value.shape),self.assertRaises(ValueError):
                execution.raw_point({'theta':value},Model([]).continuous_value_vars,LAYOUT)
        model=Model(self.calls,dtype='float32')
        with self.context(model,[]),self.assertRaisesRegex(ValueError,'original finite float64'):
            model._make_initial_point()(13)

    def test_recording_checked_before_shape_evaluation_and_exact_returned_function(self):
        model=Model(self.calls);events=[]
        with self.context(model,events):
            with patch.object(execution,'compilation_options',return_value={'mode':Mode(linker='cvm',optimizer=get_default_mode().provided_optimizer)}):
                function=model.compile_fn(outs=['deterministic'],point_fn=False,trust_input=True)
            self.assertFalse(any(c[0]=='evaluate' for c in self.calls))
            self.assertEqual(events[0]['stage'],'recording')
            self.assertEqual(events[0]['function_identity'],id(function))
            function(theta=np.array([.1,.2]))
            forwarded=next(c for c in self.calls if c[0]=='compile_fn')[2]
            self.assertTrue(forwarded['trust_input']);self.assertFalse(forwarded['point_fn'])

    def test_original_compiler_identity_and_unexpected_mode_reject(self):
        model=Model(self.calls)
        with patch.object(execution.pytensorf,'compile',object()),self.assertRaisesRegex(ValueError,'compiler identity'):
            with self.context(model,[]):pass
        self.assertFalse(execution._OWNER.locked())
        with self.context(model,[]) as custody:
            custody.compiling=True;custody.initializer_stage='support_initializer'
            with self.assertRaisesRegex(ValueError,'incoming mode'):
                execution.initial_point.compile(mode=Mode(linker='cvm',optimizer='fast_run'))

    def test_fit_identity_indices_duplicate_order_and_failed_initial(self):
        records=[];saved=[]
        initial=execution.fit_callback(records,extension=False,seed=37,on_record=lambda:saved.append(1))
        initial(dict(index=1,actual_vm=VM))
        with self.assertRaisesRegex(ValueError,'duplicate'):initial(dict(index=1))
        extension=execution.fit_callback(records,extension=True,seed=38,on_record=lambda:saved.append(2))
        extension(dict(index=1,actual_vm=VM))
        self.assertEqual([(x['index'],x['fit'],x['fit_seed']) for x in records],[(1,'initial',37),(2,'extension',38)])
        for extension,existing in [(True,[]),(False,records)]:
            with self.assertRaisesRegex(ValueError,'missing or reordered'):
                execution.fit_callback(existing,extension=extension,seed=37,on_record=lambda:None)

    def test_cohort_sampler_keeps_original_profile_and_seed_without_point_injection(self):
        @contextmanager
        def custody(*args,**kwargs):yield SimpleNamespace(support_point=lambda:None)
        @contextmanager
        def guarded(*args,**kwargs):yield
        for extended in (False,True):
            with patch.object(execution,'owned_callables',custody),patch.object(execution,'guarded_native',guarded), \
                    patch.object(execution,'compilation_options',return_value={'mode':'CVM-MODE'}), \
                    patch.object(execution.pm,'sample',return_value='trace') as sample:
                self.assertEqual(execution.sample(Model([]),739,extended=extended,on_compile=lambda value:None,
                    expected_layout=LAYOUT,binding_sha256='a'*64,on_event=lambda value:None),'trace')
                kwargs=sample.call_args.kwargs
                self.assertEqual((kwargs['chains'],kwargs['cores'],kwargs['blas_cores']),(4,1,1))
                self.assertEqual((kwargs['draws'],kwargs['tune']),(2000,2000) if extended else (1000,1000))
                self.assertEqual((kwargs['random_seed'],kwargs['target_accept'],kwargs['nuts']),(739,.995,{'max_treedepth':12}))
                self.assertNotIn('initvals',kwargs);self.assertNotIn('step',kwargs)


if __name__=='__main__':unittest.main()
