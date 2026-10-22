"""Float64 rounded/clipped Normal likelihood for the new protocol/cohort models.

Retain the pinned PyMC log-CDF expression, including its tail algorithm. Its
exact scalar 2/-1 constants must be float64 before constant folding: float32
folding otherwise changes the Normal normalizer at the strict density gate.
The legacy visit likelihood remains unchanged for its frozen fitted artifacts.
"""
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt
from pytensor.graph.basic import Constant
from pytensor.graph.replace import clone_replace
from pytensor.graph.traversal import graph_inputs


def normal_logcdf(value):
    """Pinned library standard-Normal CDF with exact-valued constants promoted."""
    if pytensor.config.floatX != 'float64':
        raise ValueError('float64 required')
    value=pt.cast(pt.as_tensor_variable(value),'float64')
    # Inspect just the library CDF template, never ancestors of a caller's
    # model expression. Upstream constants belong to that model's own policy.
    placeholder=value.type()
    expression=pm.logcdf(pm.Normal.dist(np.float64(0),np.float64(1)),placeholder)
    replacements={placeholder:value}
    for variable in graph_inputs([expression]):
        if isinstance(variable,Constant) and getattr(variable,'dtype',None)=='float32':
            scalar=np.asarray(variable.data)
            if scalar.ndim!=0 or float(scalar) not in (2.,-1.):
                raise ValueError('Unexpected float32 constant in pinned Normal log-CDF')
            replacements[variable]=pt.as_tensor_variable(np.float64(scalar))
    return clone_replace(expression,replace=replacements,rebuild_strict=False)


def log_bin(value,mean,sd,step,maximum):
    """Rounded interval mass with clipping atoms at zero and maximum.

    Positive-tail intervals use survival differences, exactly as the existing
    visit likelihood. Boundary atoms include the complete clipped tail.
    """
    value=pt.cast(pt.as_tensor_variable(value),'float64')
    mean=pt.cast(pt.as_tensor_variable(mean),'float64')
    sd=pt.cast(pt.as_tensor_variable(sd),'float64')
    lo=(value-np.float64(step)/np.float64(2)-mean)/sd
    hi=(value+np.float64(step)/np.float64(2)-mean)/sd
    a=pt.switch(lo>np.float64(0),normal_logcdf(-lo),normal_logcdf(hi))
    b=pt.switch(lo>np.float64(0),normal_logcdf(-hi),normal_logcdf(lo))
    interior=a+pt.log(-pt.expm1(b-a))
    return pt.switch(pt.eq(value,np.float64(0)),normal_logcdf(hi),
        pt.switch(pt.eq(value,np.float64(maximum)),normal_logcdf(-lo),interior))
