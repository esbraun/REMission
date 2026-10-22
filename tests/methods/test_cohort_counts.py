"""Actual model count scalars; no fit/12-member graph compilation."""
import unittest
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt
from scipy.stats import beta as beta_law
from tests.contracts.test_cohort import database, export
from methods.visit.cohort_model import cohort_inputs, build_cohort
from methods.visit.borrow_execution import compilation_options, verify_cvm


class CohortCountControls(unittest.TestCase):
    def test_actual_pooled_counts_and_unconditioned_prior_remain_float64(self):
        db=database()
        try:data=cohort_inputs(export(db))
        finally:db.close()
        options=compilation_options()
        for prior in (False,True):
            model=build_cohort(data,guide=False,prior_predictive=prior)
            cases=[('observation_rate',121.,49.,.8),('p_adherence',157.,13.,.7)]
            for name,a,b,probability in cases:
                if prior:a=b=1.
                with self.subTest(prior=prior,name=name):
                    rv=model[name];alpha,beta=rv.owner.inputs[-2:]
                    self.assertEqual(alpha.dtype,'float64');self.assertEqual(beta.dtype,'float64')
                    p=pt.dscalar('p');logp=pm.logp(rv,p)
                    fn=pytensor.function([p],[alpha,beta,alpha+beta,logp,pt.grad(logp,p)],**options)
                    self.assertEqual(verify_cvm(fn)['vm_type'],'pytensor.link.c.cvm.CVM')
                    aa,bb,total,value,gradient=fn(probability)
                    self.assertEqual(float(aa),a);self.assertEqual(float(bb),b);self.assertEqual(float(total),a+b)
                    self.assertTrue(np.isfinite(value));self.assertAlmostEqual(float(value),float(beta_law.logpdf(probability,a,b)),delta=1e-10)
                    self.assertAlmostEqual(float(gradient),(a-1)/probability-(b-1)/(1-probability),delta=1e-10)


if __name__=='__main__':unittest.main()
