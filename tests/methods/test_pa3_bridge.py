"""PA3-B independent filter, rounding, mixture and gradient checks."""
import math
import os
import unittest
import numpy as np
from scipy.stats import norm
import pytensor
import pytensor.tensor as pt
from methods.visit.borrowing import (BASE, FIELDS, WC, WE, filter_weights, fixed_vectors,
    marginal, mixture_logp, tensor_marginal, tensor_mixture)
from methods.visit.numerics import rounded_isi_mean


class BridgeTests(unittest.TestCase):
    def test_filter_by_single_innovation_forward_recurrence(self):
        for rho in (-.94, 0, .3, .94):
            expected=[]
            for impulse in range(-13,43):
                state=0.; recall=[]
                for day in range(-13,43):
                    state=rho*state+int(day==impulse)
                    if day>=29:recall.append(state)
                expected.append(sum(recall)/14)
            np.testing.assert_allclose(filter_weights(rho),expected,atol=1e-15,rtol=1e-14)
        for decay, scale, observed in ((.65,.35,WC),(.8,.2,WE)):
            self.assertAlmostEqual(sum(observed),sum(1-decay**t for t in range(29,43))/14,places=14)

    def test_rounded_mean_against_category_probabilities_and_limits(self):
        for mu,sd in [(-8,.1),(0,2),(19,1),(28,4),(35,.5)]:
            expected=0.
            for y in range(29):
                lo=-np.inf if y==0 else y-.5
                hi=np.inf if y==28 else y+.5
                expected+=y*(norm.cdf(hi,mu,sd)-norm.cdf(lo,mu,sd))
            self.assertAlmostEqual(float(rounded_isi_mean(mu,sd)),expected,places=12)
        np.testing.assert_equal(rounded_isi_mean(np.array([-10,0,3.49,3.51,29]),0),[0,0,3,4,28])

    def test_no_treatment_and_deterministic_adherence_independent_normal_collapse(self):
        theta=dict(zip(FIELDS,BASE))
        self.assertEqual(marginal(dict(theta,p=0)),0)
        # Deterministic adherence makes each arm an exactly normal latent
        # endpoint; collapse b/beta analytically as an independent reference.
        theta.update(mu_b=14,sd_b=.1,sd_beta_c=.1,sd_beta_e=.1,p=1)
        h=filter_weights(theta['rho'])
        means=[]
        for arm,w in [('c',WC),('e',WE)]:
            mu=theta['mu_b']+theta['a']*np.sin(2*np.pi*np.arange(29,43)/21).mean()-theta['beta_'+arm]*w.sum()
            variance=theta['sd_b']**2+(theta['sd_beta_'+arm]*w.sum())**2+theta['sigma_e']**2*sum(h**2)+theta['sigma_isi']**2
            means.append(float(rounded_isi_mean(mu,variance**.5)))
        self.assertAlmostEqual(marginal(theta),means[1]-means[0],places=11)
        self.assertAlmostEqual(marginal(dict(theta,beta_c=0,beta_e=0,sd_beta_c=0,sd_beta_e=0)),0,places=14)

    def test_tensor_values_gradients_and_normalized_mixture_scalar_reference(self):
        order=int(os.environ.get('PA3_TEST_QUADRATURE_ORDER','16'))
        vector=pt.dvector('theta')
        theta={name:vector[i] for i,name in enumerate(FIELDS)}
        g=tensor_marginal(theta,order)
        total,responsibility=tensor_mixture(-1.4,.4,g,.2,.8)
        f=pytensor.function([vector],[g,total,responsibility,pt.grad(total,vector)])
        direction=np.array([.4,-.3,.2,.1,.1,-.1,.03,.04,.1,.1,-.2])
        for values in fixed_vectors():
            x=np.array([values[k] for k in FIELDS],dtype=float)
            vg,vl,vr,gradient=f(x)
            self.assertAlmostEqual(vg,marginal(values,order),places=11)
            variance=.4**2+.8**2
            informative=.5*math.exp(-.5*(-1.4-vg-.2)**2/variance)/math.sqrt(2*math.pi*variance)
            weak=.5*math.exp(-.5*(-1.4)**2/(.4**2+100))/math.sqrt(2*math.pi*(.4**2+100))
            self.assertAlmostEqual(vl,math.log(informative+weak),delta=1e-10)
            self.assertAlmostEqual(vr,informative/(informative+weak),delta=1e-10)
            step=1e-5
            finite=(f(x+step*direction)[1]-f(x-step*direction)[1])/(2*step)
            autodiff=float(gradient@direction)
            self.assertTrue(np.isfinite(gradient).all(),values)
            self.assertLessEqual(abs(autodiff-finite),1e-5+1e-4*abs(finite))
        for weight in (0.,1.):
            with np.errstate(divide='ignore'):
                total,_=mixture_logp(-1.4,.4,-2,.2,.8,weight=weight)
            expected=norm.logpdf(-1.4,-1.8,math.sqrt(.4**2+.8**2)) if weight else norm.logpdf(-1.4,0,math.sqrt(.4**2+100))
            self.assertAlmostEqual(total,expected,places=13)


if __name__=='__main__':unittest.main()
