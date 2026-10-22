"""Model's same scientific prior parameters retain float64 normalizers."""
import unittest
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt
from scipy.stats import norm,halfnorm
from tests.contracts.test_cohort import database,export
from methods.visit.cohort_model import cohort_inputs,build_cohort
from methods.visit.borrow_execution import compilation_options,verify_cvm


class CohortLiteralControls(unittest.TestCase):
    def test_actual_model_prior_density_and_gradient(self):
        db=database()
        try:data=cohort_inputs(export(db))
        finally:db.close()
        model=build_cohort(data,guide=False)
        cases=[]
        for name,point,scale in [('sd_b',1.4,3),('sd_beta',np.array([.8,1.1]),1),
                ('sigma_e',1.1,2),('sigma_isi',1.3,2),('sigma_quality',.6,1)]:
            cases.append((name,point,halfnorm.logpdf(point,scale=scale),-np.asarray(point)/scale**2,1))
        for name,point,location,scale in [('mu_b',18.2,19,5),('population_beta',np.array([1.,2.]),0,4),
                ('a',.4,0,1),('b_raw',np.linspace(-.2,.3,12),0,1),
                ('beta_raw',np.linspace(-.3,.2,24).reshape(12,2),0,1),
                ('innovation',np.sin(np.arange(12*28)).reshape(12,28)/10,0,1)]:
            cases.append((name,point,norm.logpdf(point,location,scale),-(np.asarray(point)-location)/scale**2,2))
        cases.append(('rho',.2,-np.log(1.9),0.,2))
        for name,point,expected,gradient,count in cases:
            with self.subTest(name=name):
                rv=model[name]
                parameters=rv.owner.inputs[-count:]
                self.assertTrue(all(v.dtype=='float64' for v in parameters))
                x=rv.type()
                expression=pm.logp(rv,x)
                fn=pytensor.function([x],[expression,pt.grad(expression.sum(),x)],**compilation_options())
                verify_cvm(fn)
                actual,derivative=fn(point)
                np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-12)
                np.testing.assert_allclose(derivative,gradient,rtol=0,atol=1e-12)


if __name__=='__main__':unittest.main()
