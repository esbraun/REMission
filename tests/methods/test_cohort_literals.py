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
        x=pt.dscalar('x')
        cases=[('sd_b',1.4,halfnorm.logpdf(1.4,scale=3),-1.4/9),
               ('mu_b',18.2,norm.logpdf(18.2,19,5),-(18.2-19)/25)]
        for name,point,expected,gradient in cases:
            with self.subTest(name=name):
                rv=model[name]
                parameters=rv.owner.inputs[-2:] if name=='mu_b' else rv.owner.inputs[-1:]
                self.assertTrue(all(v.dtype=='float64' for v in parameters))
                expression=pm.logp(rv,x)
                fn=pytensor.function([x],[expression,pt.grad(expression,x)],**compilation_options())
                verify_cvm(fn)
                actual,derivative=fn(point)
                self.assertAlmostEqual(float(actual),expected,delta=1e-12)
                self.assertAlmostEqual(float(derivative),gradient,delta=1e-12)


if __name__=='__main__':unittest.main()
