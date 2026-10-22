"""TA-T1--4: independent expectations, finite cases, leakage and cap failures."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import math
import unittest

import numpy as np
from scipy.stats import norm

from contracts.domain.analysis import AnalysisHistory, PROTOCOL_REF, sha
from methods.truth import checks
from methods.truth.restricted import (Budget, Inconclusive, Law, Posterior, Problem, Settings,
    V1, burden, compile_history, condition, evaluate, expected_isi, future_pair, move,
    normal_bin_logmass, normalized_weights, prefix_loglikelihood, residuals, truth_seed)


def history_value():
    origin = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    patient = 'lawful-test-patient'
    records = []

    def add(kind, at, **values):
        rid = f'{kind}-{len(records)}'
        records.append(dict(record_id=rid, patient_id=patient, kind=kind,
            event_at=at.isoformat(), recorded_at=at.isoformat(), available_at=at.isoformat(),
            lineage_id=rid, revision=1, supersedes=None, duplicate_of=None,
            record_status='active', **values))

    add('isi', origin-timedelta(minutes=1), total=19, instrument_version='ISI-7-synthetic-14d-v1',
        recall_days=14, recall_start=(origin-timedelta(days=14, hours=1)).isoformat(),
        recall_end=(origin-timedelta(hours=1)).isoformat())
    add('assignment', origin, option='behavioral_continue', experimental=True)
    assignment = records[-1]['record_id']
    for day in range(1, 15):
        at = origin+timedelta(days=day, minutes=-1)
        observed = day != 5
        add('daily_report', at, sleep_quality=4.3 if observed else None,
            missingness='observed' if observed else 'missing')
        taken = day != 3
        add('delivery', origin+timedelta(days=day-1, hours=8), assignment_id=assignment,
            option='behavioral_continue', stage='taken' if taken else 'not_taken',
            adherence=float(taken), rescue=False, protocol_deviations=[])
    add('isi', origin+timedelta(days=14, minutes=-1), total=17,
        instrument_version='ISI-7-synthetic-14d-v1', recall_days=14,
        recall_start=(origin-timedelta(hours=1)).isoformat(),
        recall_end=(origin+timedelta(days=14, hours=-1)).isoformat())
    header_fields = set(records[0])-{'total', 'instrument_version', 'recall_days', 'recall_start', 'recall_end'}
    return dict(schema_version='1.0.0', synthetic=True, kind='poc_analysis_history',
        version='poc-analysis-history-v1', patient_id=patient,
        cutoff=(origin+timedelta(days=14)).isoformat(), origin=origin.isoformat(),
        protocol=PROTOCOL_REF, eligibility='uninterrupted-v1-behavioral-no-prompt', records=records,
        provenance=[{k: r[k] for k in header_fields} for r in records])


def typed(value=None):
    return AnalysisHistory.model_validate_json(json.dumps(history_value() if value is None else value))


def diagnostic_counts():
    return dict(mh_proposals=0, mh_accepts=0, mh_bounds_rejected=0,
                slice_evaluations=0, slice_accepts=0)


class MeasurementTests(unittest.TestCase):
    def test_bins_clipping_and_extreme_survival_tails(self):
        for value, mu, sd, step, high in [(0, .3, .45, .001, 10), (10, 9., .45, .001, 10),
                (3.456, 4., .45, .001, 10), (0, 2., 1., 1., 28), (28, 26., 1., 1., 28)]:
            lo = -np.inf if value == 0 else (value-step/2-mu)/sd
            hi = np.inf if value == high else (value+step/2-mu)/sd
            reference = norm.sf(lo)-norm.sf(hi) if lo >= 0 else norm.cdf(hi)-norm.cdf(lo)
            self.assertAlmostEqual(float(normal_bin_logmass(value, mu, sd, step, high)), math.log(reference), places=10)
        self.assertTrue(np.isfinite(normal_bin_logmass(0., 100., .45, .001, 10)))
        self.assertTrue(np.isfinite(normal_bin_logmass(10., -100., .45, .001, 10)))
        for mu in (0., 4., 10.):
            mass = np.exp(normal_bin_logmass(np.arange(10001)/1000, mu, .45, .001, 10)).sum()
            self.assertAlmostEqual(mass, 1., places=10)

    def test_single_total_shared_fourteen_night_recall(self):
        p = Problem(tuple(range(-13, 1)), (0.,)*14, (0.,)*14, isi=((13, 19, 14),))
        x = np.zeros((2, 14)); x[1, 0] = 2.
        z = burden(p, np.array([19., 19.]), np.ones(2), x)
        actual = prefix_loglikelihood(p, np.array([19., 19.]), np.ones(2), x)
        reference = norm.cdf(19.5-z.mean(axis=1))-norm.cdf(18.5-z.mean(axis=1))
        np.testing.assert_allclose(actual, np.log(reference), atol=1e-12)
        self.assertGreater(abs(actual[1]-actual[0]), .0001)
        self.assertGreater(abs(actual[0]-7*actual[0]), 1.)
        np.testing.assert_allclose(residuals(np.array([[1., 0.]])), [[.8, .44]])

    def test_analytic_rounded_clipped_expectation(self):
        for mu in (-2., .1, 13.4, 27.8, 30.):
            values = np.arange(29)
            probabilities = np.exp(normal_bin_logmass(values, mu, 1., 1., 28.))
            self.assertAlmostEqual(float(expected_isi(mu)), float(values@probabilities), places=12)


class InputTests(unittest.TestCase):
    def test_nonzero_history_keeps_missing_night_and_delivery_state(self):
        p = compile_history(typed())
        self.assertEqual(p.nights, tuple(range(-13, 15)))
        self.assertEqual(p.isi, ((13, 19, 14), (27, 17, 14)))
        self.assertEqual(len(p.quality), 13)
        c = 0.
        for day in range(1, 15):
            c = .65*c+.35*(day != 3)
        self.assertAlmostEqual(p.continue_state[-1], c)
        self.assertGreater(p.continue_state[5+13], p.continue_state[4+13])
        self.assertAlmostEqual(p.constant_log_probability, 13*math.log(.9)+math.log(.1)+13*math.log(.85)+math.log(.15))

    def test_private_and_excluded_public_fields_rejected(self):
        for field, value in [('seed', 17), ('generation_index', 0), ('baseline', 19),
                             ('residual_path', [0]), ('private_future', {}), ('name', 'excluded')]:
            candidate = history_value(); candidate[field] = value
            with self.assertRaises(ValueError):
                typed(candidate)
        for field in ('function', 'diary_sleep_minutes', 'raw_source'):
            candidate = history_value(); candidate['records'][2][field] = 3
            with self.assertRaises(ValueError):
                typed(candidate)
        with self.assertRaises(TypeError):
            compile_history(history_value())

    def test_cutoff_malformed_unresolved_and_patient_negatives(self):
        changes = [(2, 'available_at', '2026-01-15T12:00:00+00:00'),
                   (2, 'patient_id', 'another-patient'), (3, 'stage', 'unknown'),
                   (3, 'adherence', 0.), (0, 'recall_days', 7),
                   (0, 'recall_start', '2025-12-19T11:00:00+00:00')]
        for index, field, value in changes:
            candidate = history_value(); candidate['records'][index][field] = value
            with self.assertRaises(ValueError, msg=field):
                compile_history(typed(candidate))
        candidate = history_value(); candidate['records'].pop(3); candidate['provenance'].pop(3)
        with self.assertRaises(ValueError):
            typed(candidate)
        candidate = history_value(); candidate['records'].append(deepcopy(candidate['records'][2]))
        with self.assertRaises(ValueError):
            typed(candidate)

    def test_correction_head_authoritative_and_order_invariance(self):
        candidate = history_value()
        old = deepcopy(candidate['records'][0]); corrected = candidate['records'][0]
        corrected.update(record_id='baseline-correction', revision=2, supersedes=old['record_id'],
            available_at='2026-01-02T12:00:00+00:00', recorded_at='2026-01-02T12:00:00+00:00', total=21)
        fields = set(candidate['provenance'][0])
        candidate['provenance'].append({k: corrected[k] for k in fields})
        p = compile_history(typed(candidate))
        self.assertEqual(p.isi[0], (13, 21, 14))
        candidate['records'].reverse(); candidate['provenance'].reverse()
        self.assertEqual(p, compile_history(typed(candidate)))

    def test_day14_is_day56_not_day42_and_cap_is_inconclusive(self):
        h = typed()
        result = evaluate(h, Settings(seconds=1e-12), 'truth-ta1-test')
        self.assertEqual(result['endpoint_absolute_day'], 56)
        self.assertEqual(result['recall_absolute_nights'], [43, 56])
        self.assertEqual(result['retained_visits_absolute_days'], [28, 42])
        self.assertEqual(result['status'], 'inconclusive')
        self.assertEqual(result['reason'], 'wall_time_cap')
        self.assertIsNone(result['numerical_error_components']['between_filter_mcse'])
        self.assertFalse(result['production_truth'])
        self.assertNotIn('estimate', result)
        hs = sha(h.model_dump(mode='json'))
        self.assertNotEqual(truth_seed('truth-test', h.patient_id, hs, 0, 'future'),
                            truth_seed('truth-test', h.patient_id, hs, 0, 'conditioning'))
        with self.assertRaises(ValueError):
            truth_seed('generation', h.patient_id, hs, 0, 'future')


class NumericalTests(unittest.TestCase):
    def test_baseline_measurement_updates_random_baseline(self):
        p = Problem(tuple(range(-13, 1)), (0.,)*14, (0.,)*14, isi=((13, 16, 14),))
        posterior = condition(p, Settings(particles=4096), np.random.default_rng(1801))
        self.assertLess(posterior.diagnostics['baseline_mean'], 17.5)
        self.assertGreater(posterior.diagnostics['baseline_sd'], .1)
        self.assertGreater(posterior.diagnostics['response_sd'], .08)

    def test_independent_two_night_quadrature_refinement_and_filter(self):
        case = checks.ReducedCase((0, 1), (0., .7), quality=((0, 4.25),), isi=((1, 18, 2),))
        low, high = checks.quadrature(case, 16), checks.quadrature(case, 32)
        np.testing.assert_allclose(low['moments'], high['moments'], atol=.00002, rtol=0)
        p = Problem((0, 1), (0., .35), (0., 0.), case.quality, case.isi)
        posterior = condition(p, Settings(particles=16384, moves=3), np.random.default_rng(1802))
        last = residuals(posterior.innovations)[:, -1]
        actual = [posterior.weights@posterior.baseline, posterior.weights@posterior.response,
                  posterior.weights@last, posterior.weights@(last**2)]
        np.testing.assert_allclose(actual, high['moments'], atol=.045, rtol=0)
        print(json.dumps(dict(check='reduced-quadrature', order16=low, order32=high,
                              filter_moments=actual, diagnostics=posterior.diagnostics)), flush=True)

    def test_independent_gaussian_kalman_overlap(self):
        exact = checks.gaussian_overlap(observed_values=[20., 18.], observed_indices=[0, 1],
            observation_sds=[.7, .7], observed_nights=2, future_nights=3, recall=2)
        law = replace(V1, baseline=(19., 19.), response=(1., 1.), phase_amplitude=0.)
        p = Problem((0, 1), (0., 0.), (0., 0.), gaussian=((0, 20., .7), (1, 18., .7)))
        posterior = condition(p, Settings(particles=16384, moves=3), np.random.default_rng(1803), law)
        z = burden(p, posterior.baseline, posterior.response, posterior.innovations, law)
        means = posterior.weights@z
        np.testing.assert_allclose(means, exact['mean'][:2], atol=.025, rtol=0)
        means_future, _ = future_pair(p, posterior, np.random.default_rng(1804), 100000,
            replace(law, continue_effect=0., escalate_effect=0.), horizon=3, recall=2)
        self.assertAlmostEqual(float(means_future.mean()), exact['expected_rounded_isi'], delta=.012)
        print(json.dumps(dict(check='kalman-overlap', exact=exact, filter_means=means.tolist(),
                              future_mean=float(means_future.mean()))), flush=True)

    def test_prior_and_posterior_kernel_invariance(self):
        n = 20000; rng = np.random.default_rng(1805); settings = Settings(moves=4)
        b, r, x = rng.uniform(16, 22, n), rng.uniform(.8, 1.2, n), rng.standard_normal((n, 2))
        b, r, x, _ = move(b, r, x, lambda bb, rr, xx: np.zeros(len(bb)), rng, V1,
                           settings, Budget(60), diagnostic_counts())
        self.assertAlmostEqual(float(b.mean()), 19., delta=.05)
        self.assertAlmostEqual(float(r.mean()), 1., delta=.004)
        np.testing.assert_allclose(x.mean(axis=0), [0, 0], atol=.025)
        np.testing.assert_allclose(x.var(axis=0), [1, 1], atol=.035)
        law = replace(V1, baseline=(19., 19.), response=(1., 1.))
        mean = .8/(.8**2+.5**2); variance = .5**2/(.8**2+.5**2)
        x = rng.normal(mean, math.sqrt(variance), (n, 1))
        ll = lambda bb, rr, xx: -.5*((20-bb-.8*xx[:, 0])/.5)**2
        _, _, x, _ = move(np.full(n, 19.), np.ones(n), x, ll, rng, law,
                           settings, Budget(60), diagnostic_counts())
        self.assertAlmostEqual(float(x.mean()), mean, delta=.02)
        self.assertAlmostEqual(float(x.var()), variance, delta=.02)

    def test_weight_collapse_and_invalid_weights_remain_visible(self):
        # A deliberately extremely concentrated Gaussian overlap has effectively
        # one supported prior draw. Independently calculate this concentration
        # with scipy.stats, rather than changing the production collapse rule.
        p = Problem((0,), (0.,), (0.,), gaussian=((0, 1000., .001),))
        reference_rng = np.random.default_rng(1806)
        b = reference_rng.uniform(16, 22, 256)
        reference_rng.uniform(.8, 1.2, 256)
        z = b+.8*reference_rng.standard_normal(256)
        log_mass = norm.logpdf(1000., loc=z, scale=.001)
        reference_weights = np.exp(log_mass-log_mass.max())
        reference_weights /= reference_weights.sum()
        self.assertLess(1/np.sum(reference_weights**2), 2.)
        posterior = condition(p, Settings(particles=256), np.random.default_rng(1806))
        self.assertTrue(posterior.diagnostics['severe_weight_collapse'])
        self.assertTrue(any(s['severe_weight_collapse'] for s in posterior.diagnostics['stages']))
        with self.assertRaises(Inconclusive):
            normalized_weights(np.array([-np.inf, -np.inf]))
        with self.assertRaises(Inconclusive):
            normalized_weights(np.array([np.nan, 0.]))
        d = diagnostic_counts()
        with self.assertRaises(Inconclusive):
            move(np.full(64, 19.), np.ones(64), np.zeros((64, 1)),
                 lambda bb, rr, xx: -1e12*xx[:, 0]**2, np.random.default_rng(1807), V1,
                 Settings(slice_limit=1), Budget(60), d)

    def test_exact_short_tree_descendants_sign_swap_and_zero_effect(self):
        p = Problem((14,), (.4,), (.2,))
        law = replace(V1, baseline=(19., 19.), response=(1., 1.), innovation_sd=1e-12)
        posterior = Posterior(np.array([19.]), np.ones(1), np.zeros((1, 1)), np.ones(1), {})
        exact = checks.exact_adherence_tree(horizon=4, recall=2, initial_continue=.4, initial_escalate=.2)
        a, b = future_pair(p, posterior, np.random.default_rng(1808), 100000, law, horizon=4, recall=2)
        np.testing.assert_allclose([a.mean(), b.mean()], exact['arm_means'], atol=.004, rtol=0)
        self.assertLess(exact['contrast'], 0)
        swapped_b, swapped_a = future_pair(p, posterior, np.random.default_rng(1808), 100000, law,
            horizon=4, recall=2, arms=('behavioral_continue', 'behavioral_escalate'))
        np.testing.assert_array_equal(a, swapped_a); np.testing.assert_array_equal(b, swapped_b)
        a, b = future_pair(p, posterior, np.random.default_rng(1808), 10000,
            replace(law, continue_effect=0., escalate_effect=0.), horizon=4, recall=2)
        np.testing.assert_array_equal(a, b)
        reference = np.mean([19.+.55*math.sin(2*math.pi*s/21) for s in (17, 18)])
        self.assertAlmostEqual(float(a.mean()), float(expected_isi(reference)), places=9)
        # Omitting descendant exposure updates cannot reproduce the tree value.
        stale = float(expected_isi(reference-2*.4-4*.2))
        self.assertGreater(abs(stale-exact['arm_means'][0]), .3)
        print(json.dumps(dict(check='exact-adherence-tree', exact=exact)), flush=True)


if __name__ == '__main__':
    unittest.main()
