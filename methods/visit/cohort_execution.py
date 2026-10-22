"""Owned cohort callable custody; no admission, alternate initializer or sampler."""
from contextlib import contextmanager
from functools import wraps
import threading

import numpy as np
import pymc as pm
import pymc.initial_point as initial_point
import pymc.pytensorf as pytensorf
from pytensor.compile.mode import FAST_COMPILE, Mode

from contracts.domain.analysis import CONFIG
from contracts.domain.borrow_runtime import OPTIMIZER, NATIVE_OPTIMIZER
from contracts.domain.cohort_runtime import INITIALIZER_OPTIMIZER, INITIALIZER_NATIVE_OPTIMIZER
from .borrow_execution import compilation_options, coordinate_map, guarded_native, optimizer_identity, verify_cvm

_OWNER = threading.Lock()


def raw_point(point, variables, expected_layout):
    """Check original arrays before Point/coordinate_map can cast their dtype."""
    if not isinstance(point, dict) or list(point) != [v.name for v in variables]:
        raise ValueError('cohort initializer original coordinate order differs')
    if any(not isinstance(v, np.ndarray) or v.dtype != np.dtype('float64') or not np.isfinite(v).all()
           for v in point.values()):
        raise ValueError('cohort initializer requires original finite float64 arrays')
    _, layout = coordinate_map(point, variables)
    if expected_layout is not None and layout != expected_layout:
        raise ValueError('cohort initializer original shapes/layout differ')
    return layout


class CallableCustody:
    def __init__(self, model, *, fit, binding_sha256, on_event, expected_layout=None):
        self.model = model
        self.fit, self.binding_sha256, self.on_event = fit, binding_sha256, on_event
        self.expected_layout = expected_layout
        self.thread = threading.get_ident()
        self.compiling = False
        self.support = None
        self.counts = {}

    def owned(self):
        if threading.get_ident() != self.thread:
            raise ValueError('cohort callable invoked outside owner thread')

    def observe(self, function, stage, optimizer, **extra):
        self.owned()
        actual = verify_cvm(function)
        if optimizer_identity(function.maker.mode.provided_optimizer) != optimizer:
            raise ValueError('cohort callable optimizer differs from stage policy')
        self.counts[stage] = self.counts.get(stage, 0) + 1
        self.on_event(dict(stage=stage, fit=self.fit, invocation=self.counts[stage],
            function_identity=id(function), binding_sha256=self.binding_sha256,
            actual_vm=actual, compiled_optimizer=optimizer, **extra))

    def support_point(self):
        self.owned()
        if self.support is None:
            raise ValueError('cohort combined callable did not capture original support point')
        return self.support


@contextmanager
def owned_callables(model, *, fit, binding_sha256, on_event, expected_layout=None):
    """Dedicated one-job process only; all references restore even on observers' errors.

    Only the initializer module's compile alias is temporarily intercepted.
    Its original seeded callable retains maker/RNG discovery/reseeding. Every
    other model/thread invocation during the owned operation is rejected.
    """
    if threading.current_thread() is not threading.main_thread() or threading.active_count() != 1:
        raise ValueError('cohort custody requires a dedicated single-job process')
    if not _OWNER.acquire(blocking=False):
        raise ValueError('cohort callable custody is not reentrant or concurrent')
    original_compile = initial_point.compile
    previous = {name: (name in model.__dict__, model.__dict__.get(name))
                for name in ('_make_initial_point', 'compile_fn', 'check_start_vals')}
    original_make, original_fn = model._make_initial_point, model.compile_fn
    custody = CallableCustody(model, fit=fit, binding_sha256=binding_sha256,
        on_event=on_event, expected_layout=expected_layout)
    try:
        if original_compile is not pytensorf.compile:
            raise ValueError('cohort initializer compiler identity differs')

        def compile_initializer(*args, **kwargs):
            custody.owned()
            if not custody.compiling or initial_point.compile is not compile_initializer:
                raise ValueError('cohort initializer compiler invoked outside owned model')
            mode = kwargs.get('mode')
            if mode is not FAST_COMPILE or optimizer_identity(mode.provided_optimizer) != INITIALIZER_OPTIMIZER:
                raise ValueError('cohort initializer incoming mode/query differs')
            before = optimizer_identity(mode.provided_optimizer)
            replacement = Mode(linker='cvm', optimizer=mode.provided_optimizer)
            if optimizer_identity(replacement.provided_optimizer) != before:
                raise ValueError('cohort initializer optimizer changed')
            forwarded = dict(kwargs, mode=replacement)
            function = original_compile(*args, **forwarded)
            if optimizer_identity(mode.provided_optimizer) != before:
                raise ValueError('cohort initializer shared optimizer mutated')
            custody.observe(function, custody.initializer_stage, INITIALIZER_NATIVE_OPTIMIZER)
            return function  # Exact PyTensor Function; never a maker-less wrapper.

        def make_initializer(*args, **kwargs):
            custody.owned()
            if custody.compiling:
                raise ValueError('cohort initializer compilation is not reentrant')
            if kwargs.get('return_transformed', True) is not True:
                raise ValueError('cohort requires transformed initial coordinates')
            stage = 'jitter_initializer' if kwargs.get('jitter_rvs') else 'support_initializer'
            custody.initializer_stage, custody.compiling = stage, True
            try:
                seeded = original_make(*args, **kwargs)
            finally:
                custody.compiling = False

            @wraps(seeded)
            def checked_point(*point_args, **point_kwargs):
                custody.owned()
                # Check the inherited actual function before original reseed/evaluation.
                verify_cvm(seeded)
                optimizer = optimizer_identity(seeded.maker.mode.provided_optimizer)
                if optimizer != INITIALIZER_NATIVE_OPTIMIZER:
                    raise ValueError('cohort seeded initializer optimizer changed')
                point = seeded(*point_args, **point_kwargs)
                layout = raw_point(point, model.continuous_value_vars, expected_layout)
                if stage == 'support_initializer':
                    custody.support = point
                custody.observe(seeded, stage+'_point', optimizer, coordinate_map=layout)
                return point
            return checked_point

        def compile_function(*args, **kwargs):
            custody.owned()
            if kwargs.get('point_fn') is not False:
                raise ValueError('cohort unexpected point-wrapped callable compilation')
            forwarded = dict(kwargs)
            mode = forwarded.get('mode')
            if mode is None:
                forwarded.update(compilation_options())
            elif optimizer_identity(mode.provided_optimizer) != OPTIMIZER:
                raise ValueError('cohort forward/recording incoming optimizer differs')
            before = optimizer_identity(forwarded['mode'].provided_optimizer)
            function = original_fn(*args, **forwarded)
            if optimizer_identity(forwarded['mode'].provided_optimizer) != before:
                raise ValueError('cohort forward/recording shared optimizer mutated')
            custody.observe(function, 'prior_forward' if fit == 'prior' else 'recording', NATIVE_OPTIMIZER)
            return function

        def failed_jitter(*args, **kwargs):
            custody.owned()
            raise ValueError('cohort exhausted-jitter diagnostic compilation is unqualified')

        initial_point.compile = compile_initializer
        model._make_initial_point = make_initializer
        model.compile_fn = compile_function
        model.check_start_vals = failed_jitter
        yield custody
    finally:
        initial_point.compile = original_compile
        for name, (present, value) in previous.items():
            if present:
                setattr(model, name, value)
            else:
                model.__dict__.pop(name, None)
        _OWNER.release()


def fit_callback(records, *, extension, seed, on_record):
    """One combined callable per actual fit; lifecycle indices never reset."""
    index = 2 if extension else 1
    fit = 'extension' if extension else 'initial'
    if len(records) != index-1:
        raise ValueError('cohort fit compilation lifecycle is missing or reordered')
    seen = False

    def record(value):
        nonlocal seen
        if seen or value.get('index') != 1 or len(records) != index-1:
            raise ValueError('cohort duplicate combined callable within fit')
        seen = True
        records.append(dict(value, index=index, fit=fit, fit_seed=seed))
        on_record()
    return record


def sample(model, seed, *, extended=False, on_compile, expected_layout, binding_sha256, on_event):
    options = compilation_options()
    with model, owned_callables(model, fit='extension' if extended else 'initial',
            binding_sha256=binding_sha256, on_event=on_event, expected_layout=expected_layout) as custody, \
            guarded_native(model, on_compile, expected_layout, point_provider=custody.support_point):
        return pm.sample(draws=CONFIG['extension_draws'] if extended else CONFIG['draws'],
            tune=CONFIG['extension_tune'] if extended else CONFIG['tune'], chains=4, cores=1,
            random_seed=seed, nuts_sampler='pymc', target_accept=CONFIG['target_accept'],
            nuts={'max_treedepth':CONFIG['max_treedepth']}, blas_cores=1, progressbar=False,
            return_inferencedata=True, compile_kwargs=options)
