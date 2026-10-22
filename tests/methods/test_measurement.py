"""Independent scalar Normal CDF/bin densities and derivatives; no model fit."""
import unittest
import numpy as np
import pytensor
import pytensor.tensor as pt
from pytensor.graph.basic import Constant
from pytensor.graph.traversal import graph_inputs
from scipy.special import log_ndtr
from scipy.stats import norm
from methods.measurement import normal_logcdf,log_bin
from methods.visit.borrow_execution import compilation_options,verify_cvm


def reference(value,mean,sd,step,maximum):
    lo=(value-step/2-mean)/sd;hi=(value+step/2-mean)/sd
    if value==0:
        mass=log_ndtr(hi);ratio=np.exp(norm.logpdf(hi)-mass)
        return mass,-ratio/sd,-hi*ratio/sd
    if value==maximum:
        mass=log_ndtr(-lo);ratio=np.exp(norm.logpdf(lo)-mass)
        return mass,ratio/sd,lo*ratio/sd
    a,b=(log_ndtr(-lo),log_ndtr(-hi)) if lo>0 else (log_ndtr(hi),log_ndtr(lo))
    mass=a+np.log(-np.expm1(b-a))
    l=np.exp(norm.logpdf(lo)-mass);h=np.exp(norm.logpdf(hi)-mass)
    return mass,(l-h)/sd,(lo*l-hi*h)/sd


class MeasurementControls(unittest.TestCase):
    def test_library_cdf_float64_density_gradient_and_graph_constants(self):
        x=pt.dvector('x');expression=normal_logcdf(x)
        floats=[v for v in graph_inputs([expression]) if isinstance(v,Constant)
                and getattr(v,'dtype','').startswith('float')]
        self.assertTrue(floats)
        self.assertTrue(all(v.dtype=='float64' for v in floats))
        fn=pytensor.function([x],[expression,pt.grad(expression.sum(),x)],**compilation_options())
        verify_cvm(fn)
        values=np.array([-35.,-12.,-3.,-.01,0.,.7,2.,9.,35.])
        actual,gradient=fn(values);expected=log_ndtr(values)
        np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-10)
        np.testing.assert_allclose(gradient,np.exp(norm.logpdf(values)-expected),rtol=1e-10,atol=1e-10)

    def test_clipped_atoms_interior_tails_and_mean_scale_gradients(self):
        mean=pt.dscalar('mean');sd=pt.dscalar('sd');value=pt.dscalar('value')
        for step,maximum in [(1.,28.),(.001,10.)]:
            expression=log_bin(value,mean,sd,step,maximum)
            fn=pytensor.function([value,mean,sd],[expression,pt.grad(expression,mean),pt.grad(expression,sd)],
                **compilation_options())
            verify_cvm(fn)
            middle=maximum/2
            cases=[(0.,-.7,.8),(0.,9.,.8),(maximum,maximum+.7,.8),(maximum,maximum-9.,.8),
                (middle,middle-.4,.6),(middle,middle+2.,1.3),
                (middle,middle-25.,1.),(middle,middle+25.,1.)]
            for v,m,s in cases:
                with self.subTest(step=step,value=v,mean=m,sd=s):
                    actual=np.asarray(fn(v,m,s));expected=np.asarray(reference(v,m,s,step,maximum))
                    self.assertTrue(np.isfinite(actual).all())
                    self.assertAlmostEqual(actual[0],expected[0],delta=1e-10)
                    np.testing.assert_allclose(actual[1:],expected[1:],rtol=1e-8,atol=1e-8)


if __name__=='__main__':unittest.main()
