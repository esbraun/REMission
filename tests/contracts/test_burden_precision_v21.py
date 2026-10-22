"""Independent finite algebra, not stochastic trials or a calibration pilot."""
import copy
from fractions import Fraction
from itertools import product
import math
import unittest

import numpy as np

from contracts.runs import burden_precision as b


def finite125():
    # Five equally likely elementary outcomes, including three undefined ones.
    # This enumeration is independent of the implementation's binomial sum.
    rows=[];ratios=[];scores=[];inverse=[]
    for outcomes in product((-1,-1,-1,0,4),repeat=3):
        counts=[outcomes.count(-1),outcomes.count(0),0,0,0,outcomes.count(4)]
        rows.append(counts);m=3-counts[0]
        if m:
            ratios.append(Fraction(counts[1],m));scores.append(Fraction(4*counts[5],m));inverse.append(Fraction(1,m))
    return rows,ratios,scores,inverse


def variance(values):
    mean=sum(values,Fraction(0))/len(values)
    return sum(((x-mean)**2 for x in values),Fraction(0))/len(values)


class BurdenPrecisionV21Tests(unittest.TestCase):
    def test_literal125_exact_oracle_random_denominator_and_null_roster(self):
        rows,ratios,scores,inverse=finite125()
        self.assertEqual(len(rows),125);self.assertEqual(len(ratios),98)
        self.assertEqual(sum(inverse,Fraction(0))/len(inverse),Fraction(16,21))
        self.assertEqual(variance(ratios),Fraction(4,21));self.assertEqual(variance(scores),Fraction(64,21))
        self.assertEqual(Fraction(125-len(ratios),125),Fraction(27,125))
        self.assertAlmostEqual(b.ratio_factor(3,.4),float(Fraction(16,21)))
        self.assertNotAlmostEqual(b.ratio_factor(3,.4),1/(3*.4))
        values=b.sampling_variances(3,.4,[.5,0.,0.,0.,.5])
        self.assertAlmostEqual(values['theta'][0],float(Fraction(4,21)))
        self.assertAlmostEqual(values['mu'],float(Fraction(64,21)))
        self.assertAlmostEqual(values['undefined_probability'],27/125)
        # Eight copies are exactly 1000 deterministic algebra rows, not pilot
        # execution or an assertion of 1000 independent simulated trials.
        counts=np.array(rows*8);stats=b.empirical_statistics(counts,3,'theta0')
        self.assertEqual(stats['undefined_trials'],216)
        self.assertEqual(stats['values'].count(None),216)
        self.assertTrue(np.all(stats['sd_influence'][~stats['defined']]==0))
        self.assertTrue(np.isfinite(stats['sd_influence']).all())

    def test_n1_q1_and_small_q_not_inverse_expected_denominator(self):
        for q in [.4,1e-7,1e-30]:self.assertAlmostEqual(b.ratio_factor(1,q),1.,places=12)
        self.assertAlmostEqual(b.ratio_factor(30,1.),1/30)
        self.assertAlmostEqual(b.ratio_factor(30,1e-20),1.,places=12)
        for q in [0.,-1.,float('nan'),True]:
            with self.assertRaises(ValueError):b.ratio_factor(30,q)
        for n in [0,True,3.5]:
            with self.assertRaises(ValueError):b.ratio_factor(n,.4)

    def test_pooled_exact_box_positive_despite_empty_individual_trials(self):
        counts=np.array(finite125()[0]*8)
        self.assertTrue((counts[:,1]==0).any())
        result=b.numerical_binding(counts,3,'theta0')
        self.assertGreater(result['binding'],0);self.assertGreater(result['variance_lower'],0)
        self.assertEqual(result['box']['interval_alpha'],.05/6)
        for component in ['theta1','theta2','theta3']:
            with self.assertRaises(b.UnresolvedPrecision):b.numerical_binding(counts,3,component)
        empty=np.tile([3,0,0,0,0,0],(1000,1))
        with self.assertRaises(b.UnresolvedPrecision):b.pooled_box(empty,3)
        allzero=np.tile([0,3,0,0,0,0],(1000,1))
        with self.assertRaises(b.UnresolvedPrecision):b.numerical_binding(allzero,3,'theta0')
        for malformed in [counts[:-1],counts.astype(float),counts+1]:
            with self.assertRaises(ValueError):b.empirical_statistics(malformed,3,'theta0')

    def test_accepted_derivatives_against_independent_centered_finite_differences(self):
        theta=np.array([.1,.15,.25,.2,.3]);q=.6;n=30
        p=np.r_[1-q,q*theta];step=1e-6
        for component in b.COMPONENTS:
            sd,gradient=b.analytic_sd_gradient(n,p,component)
            def independent_sd(v):
                defined=v[1:].sum();marks=v[1:]/defined
                # Direct finite sums, not implementation's log-PMF path.
                rho=1-(1-defined)**n
                r=sum(math.comb(n,m)*defined**m*(1-defined)**(n-m)/m for m in range(1,n+1))/rho
                var=defined*(1-defined)/n if component=='q' else marks[int(component[-1])]*(1-marks[int(component[-1])])*r if component.startswith('theta') else sum(marks[k]*marks[l]*(k-l)**2 for k in range(5) for l in range(k+1,5))*r
                return math.sqrt(var)
            self.assertAlmostEqual(sd,independent_sd(p),places=12)
            for coordinate in range(1,6):
                delta=np.zeros(6);delta[coordinate]=step;delta[0]=-step
                numeric=(independent_sd(p+delta)-independent_sd(p-delta))/(2*step)
                self.assertAlmostEqual(gradient[coordinate]-gradient[0],numeric,places=7)
        rdiff=(b.ratio_factor(n,q+step)-b.ratio_factor(n,q-step))/(2*step)
        self.assertAlmostEqual(b.ratio_factor_derivative(n,q),rdiff,places=7)
        with self.assertRaises(b.UnresolvedPrecision):b.analytic_sd_gradient(n,np.r_[0.,theta],'mu')
        fixed,gradient=b.fixed_defined_sd_gradient(n,theta,'mu')
        self.assertAlmostEqual(fixed,math.sqrt(b.sampling_variances(n,1.,theta)['mu']))
        self.assertTrue(np.isfinite(gradient).all())

    def test_truth_pools_numerators_not_batch_ratios_or_descendant_units(self):
        rows=np.array([[9999,0,0,0,0,1],[0,10000,0,0,0,0]]*16)
        result=b.pooled_truth_statistics(rows,'mu')
        self.assertAlmostEqual(result['value'],4/10001)
        self.assertNotAlmostEqual(result['value'],2.)
        self.assertEqual(result['independent_units'],32)
        self.assertGreater(result['mcse'],0)
        self.assertGreater(b.all_batch_absent_upper(32),b.all_batch_absent_upper(1000))
        self.assertGreater(b.all_batch_absent_upper(32,definition_lower=.5),b.all_batch_absent_upper(32))
        for bad in [rows[:31],rows*2]:
            with self.assertRaises(ValueError):b.pooled_truth_statistics(bad,'mu')
        with self.assertRaises(ValueError):b.all_batch_absent_upper(1000,definition_lower=0.)

    def test_two_adjacent_refinements_use_paired_all_trial_influences_and_final_limit(self):
        stats=b.numerical_binding(np.array(finite125()[0]*8),3,'theta0')
        levels=[copy.deepcopy(stats) for _ in range(3)]
        self.assertEqual(b.require_refinement(b.LEVELS[:3],levels),stats['epsilon'])
        for change in ['mean','sd','binding','influence']:
            bad=copy.deepcopy(levels)
            if change=='influence':bad[1]['mean_influence'][0]+=100.
            else:bad[1][change]+=.1
            with self.subTest(change=change),self.assertRaises(b.UnresolvedPrecision):b.require_refinement(b.LEVELS[:3],bad)
        with self.assertRaises(ValueError):b.require_refinement([1024,16384,65536],levels)


if __name__=='__main__':unittest.main()
