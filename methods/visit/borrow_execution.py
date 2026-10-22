"""Borrow-only native PyMC compilation. V0 never imports or selects this policy."""
from contextlib import contextmanager
import time

import numpy as np
import pymc as pm
from pytensor.compile.mode import Mode, get_default_mode
from pytensor.link.c.cvm import CVM
from contracts.domain.analysis import CONFIG
from contracts.domain.borrow_runtime import OPTIMIZER, POLICY, POLICY_REF


def optimizer_identity(query):
    if query.subquery or query.extra_rewrites:
        raise ValueError('unqualified optimizer subquery/extra rewrites')
    return dict(type=type(query).__name__, name=query.name, include=sorted(query.include), exclude=sorted(query.exclude),
                require=sorted(query.require), subquery={}, position_cutoff=str(query.position_cutoff), extra_rewrites=[])


def compilation_options():
    import pytensor
    default = get_default_mode()
    if pytensor.config.floatX != 'float64' or type(default.linker).__name__ != 'NumbaLinker' or optimizer_identity(default.provided_optimizer) != OPTIMIZER:
        raise ValueError('borrow compile default/optimizer/float64 differs from qualification')
    mode = Mode(linker='cvm', optimizer=default.provided_optimizer)
    if optimizer_identity(mode.provided_optimizer) != OPTIMIZER:
        raise ValueError('borrow compile optimizer changed')
    return dict(mode=mode)


def verify_cvm(function):
    linker = function.maker.mode.linker
    identity = dict(vm_type=type(function.vm).__module__+'.'+type(function.vm).__qualname__, linker=type(linker).__name__,
        use_cloop=getattr(linker, 'use_cloop', None), c_thunks=getattr(linker, 'c_thunks', None),
        callback_empty=getattr(linker, 'callback', None) is None, callback_input_empty=getattr(linker, 'callback_input', None) is None,
        limitation='Whole VM checked; individual operations may use ordinary Python thunks.')
    if (type(function.vm) is not CVM or identity['linker'] != 'VMLinker' or identity['use_cloop'] is not True
            or identity['c_thunks'] is not True or not identity['callback_empty'] or not identity['callback_input_empty']):
        raise ValueError('borrow actual native VM/linker/callback guard failed')
    return identity


def coordinate_map(point, variables):
    from pymc.blocking import DictToArrayBijection
    ordered = {v.name: np.asarray(point[v.name], dtype=v.dtype) for v in variables}
    if set(ordered) != set(point):
        raise ValueError('native continuous variables must cover all value coordinates')
    raveled = DictToArrayBijection.map(ordered)
    mapping, offset = [], 0
    for name, shape, size, dtype in raveled.point_map_info:
        if str(dtype) != 'float64':
            raise ValueError('native float64 coordinates required')
        mapping.append(dict(name=name, shape=list(shape), dtype=str(dtype), start=offset, stop=offset+int(size)))
        offset += int(size)
    if offset != len(raveled.data) or offset < 1:
        raise ValueError('native coordinate offset mismatch')
    return raveled, mapping


def native_call(function, point, variables):
    raveled, mapping = coordinate_map(point, variables)
    function.set_extra_values(point)
    value, gradient = function(raveled)
    if np.asarray(gradient).shape != raveled.data.shape or not np.isfinite(value) or not np.isfinite(gradient).all():
        raise ValueError('native combined value/gradient shape or finiteness')
    return value, gradient, mapping


@contextmanager
def guarded_native(model, on_compile):
    """Inspect the actual function returned to unchanged PyMC init_nuts/BaseHMC.

    This temporary instance wrapper forwards every argument and returns the
    exact original ValueGradFunction. It neither supplies a step method nor
    changes initialization, RNGs, gradients, callbacks or sampler options.
    """
    original = model.logp_dlogp_function
    previous = model.__dict__.get('logp_dlogp_function')
    calls = 0

    def checked(*args, **kwargs):
        nonlocal calls
        before = time.monotonic()
        function = original(*args, **kwargs)
        actual = verify_cvm(function._pytensor_function)
        point = kwargs.get('initial_point')
        if point is None:
            point = model.initial_point()
        _, mapping = coordinate_map(point, model.continuous_value_vars)
        calls += 1
        on_compile(dict(index=calls, seconds=time.monotonic()-before, actual_vm=actual, coordinate_map=mapping,
                        compiled_optimizer=optimizer_identity(function._pytensor_function.maker.mode.provided_optimizer)))
        return function

    model.logp_dlogp_function = checked
    try:
        yield
        if calls == 0:
            raise ValueError('native PyMC did not expose a guarded combined function')
    finally:
        if previous is None:
            del model.logp_dlogp_function
        else:
            model.logp_dlogp_function = previous


def sample(model, seed, *, extended=False, on_compile):
    # Same original native PyMC call/settings/seeding/initialization as V0;
    # compile_kwargs is the only added sampler argument. No provided step.
    kwargs = compilation_options()
    with model, guarded_native(model, on_compile):
        return pm.sample(draws=CONFIG['extension_draws'] if extended else CONFIG['draws'],
            tune=CONFIG['extension_tune'] if extended else CONFIG['tune'], chains=4, cores=1,
            random_seed=seed, nuts_sampler='pymc', target_accept=CONFIG['target_accept'],
            nuts={'max_treedepth':CONFIG['max_treedepth']}, blas_cores=1, progressbar=False,
            return_inferencedata=True, compile_kwargs=kwargs)
