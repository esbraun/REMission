"""Opt-in model-density/gradient qualification; requires exclusive heavy lease.

Default discovery skips this class before importing PyMC or building a graph.
Choose one N purpose and J at a time to keep each qualification bounded.
"""
import os
import json
from pathlib import Path
import unittest

import numpy as np
from scipy.special import expit
from scipy.stats import beta, halfnorm, norm, uniform

from methods.nof1.data import prepare
from methods.nof1.observation import bin_logprob
from test_nof1_data import fixture


def frozen_point(data):
    """Explicit finite point from the failed f941 J1/N0 causal qualification.

    No initial-point or default-linker compilation is needed to define it.
    J>1 repeats the same independent patient coordinates without changing the
    hierarchy or priors. Each probability is at its own conjugate mean.
    """
    count = len(data.patients)
    scalar = lambda x: np.asarray(x, dtype=np.float64)
    point = dict(mu_b=scalar(19.), sd_b_log__=scalar(np.log(3.)), b_raw=np.zeros(count),
        population_amplitude=np.array([1., -.2, 1.5, 2.5, .7]), sd_amplitude_log__=np.zeros(5),
        amplitude_raw=np.zeros((count, 5)), a=scalar(0.), rho_interval__=scalar(.4),
        sigma_e_log__=scalar(np.log(2.)), sigma_isi_log__=scalar(np.log(2.)), sigma_quality_log__=scalar(0.))
    for i, patient in enumerate(data.patients):
        point["innovation_" + str(i)] = np.zeros(len(patient.nights), dtype=np.float64)
    for name, success, total in (("p_C", "C_success", "C_total"), ("p_M", "M_success", "M_total"),
                                  ("q", "observed", None)):
        alpha = np.array([1. + p.counts[success] for p in data.patients], dtype=np.float64)
        beta_shape = np.array([1. + (p.counts[total] - p.counts[success] if total else p.counts["missing"])
                               for p in data.patients], dtype=np.float64)
        point[name + "_logodds__"] = np.log(alpha / beta_shape)
    return point


def compile_options():
    """Diagnostic-only CVM, preserving the pinned default optimizer query."""
    from tooling.foundation.pa3_monitor import compilation_options
    policy = json.loads((Path(__file__).resolve().parents[2] / "tooling/foundation/pa3-cvm-policy.json").read_bytes())
    options, _ = compilation_options(policy)
    return options


def independent_logp(point, data):
    """Original-coordinate density, excluding transform Jacobians explicitly."""
    get = lambda name: np.asarray(point[name], dtype=np.float64)
    mu_b, sd_b = get("mu_b"), np.exp(get("sd_b_log__"))
    b_raw, population = get("b_raw"), get("population_amplitude")
    sd, raw = np.exp(get("sd_amplitude_log__")), get("amplitude_raw")
    a, rho = get("a"), -.95 + 1.9 * expit(get("rho_interval__"))
    se, si, sq = [np.exp(get(name + "_log__")) for name in ("sigma_e", "sigma_isi", "sigma_quality")]
    total = (norm.logpdf(mu_b, 19, 5).sum() + halfnorm.logpdf(sd_b, scale=3).sum()
        + norm.logpdf(b_raw).sum() + norm.logpdf(population, scale=[4, 4, 3, 3, 3]).sum()
        + halfnorm.logpdf(sd).sum() + norm.logpdf(raw).sum() + norm.logpdf(a).sum()
        + uniform.logpdf(rho, -.95, 1.9).sum() + halfnorm.logpdf(se, scale=2).sum()
        + halfnorm.logpdf(si, scale=2).sum() + halfnorm.logpdf(sq).sum())
    amplitude, baseline = population + sd * raw, mu_b + sd_b * b_raw
    for i, patient in enumerate(data.patients):
        innovation = get("innovation_" + str(i))
        total += norm.logpdf(innovation).sum()
        error, current = [], 0.
        for value in innovation:
            current = rho * current + se * value
            error.append(current)
        z = (baseline[i] + a * np.sin(2 * np.pi * patient.nights / 21) + error
            - amplitude[i, 0] * patient.c - amplitude[i, 2] * patient.medication[:, 0]
            - amplitude[i, 3] * patient.medication[:, 1] + amplitude[i, 4] * patient.path.rebound)
        total += bin_logprob(patient.isi, z[patient.recall].mean(axis=1), si, 1., 28.).sum()
        total += bin_logprob(patient.quality, 10 - z[patient.qindex] / 3, sq, .001, 10.).sum()
        counts = patient.counts
        for name, success, failure in [
            ("p_C", counts["C_success"], counts["C_total"] - counts["C_success"]),
            ("p_M", counts["M_success"], counts["M_total"] - counts["M_success"]),
            ("q", counts["observed"], counts["missing"])]:
            total += beta.logpdf(expit(get(name + "_logodds__")[i]), 1. + success, 1. + failure)
    return float(total)


@unittest.skipUnless(os.environ.get("NOF1_SYMBOLIC_QUALIFY") == "1", "requires explicit exclusive heavy-resource lease")
class SymbolicTests(unittest.TestCase):
    def test_ar_convolution_and_pullback_at_zero_and_negative_rho(self):
        import pytensor
        import pytensor.tensor as pt
        from methods.nof1.model import _ar_error
        from tooling.foundation.pa3_monitor import verify_cvm

        rng = np.random.default_rng(20261022)
        # The public -13..84 grid has 98 nights. Retain the original 96-night
        # qualification size too, plus the one-night boundary.
        for n in (1, 96, 98):
            innovation, rho, sigma = pt.dvector("innovation"), pt.dscalar("rho"), pt.dscalar("sigma")
            eps, weights = rng.normal(size=n), rng.normal(size=n)
            error = _ar_error(innovation, rho, sigma, n)
            pullback = pt.grad(pt.dot(error, weights), [rho, sigma, innovation])
            fn = pytensor.function([innovation, rho, sigma], [error, *pullback], **compile_options())
            verify_cvm(fn)
            for correlation in (-.949999, -.4, 0., .4, .949999):
                with self.subTest(n=n, rho=correlation):
                    expected, dr, ds = [], [], []
                    previous = previous_rho = previous_sigma = 0.
                    for value in eps:
                        current = correlation * previous + 2.2 * value
                        current_rho = previous + correlation * previous_rho
                        current_sigma = value + correlation * previous_sigma
                        expected.append(current)
                        dr.append(current_rho)
                        ds.append(current_sigma)
                        previous, previous_rho, previous_sigma = current, current_rho, current_sigma
                    reverse = np.empty(n)
                    following = 0.
                    for index in range(n - 1, -1, -1):
                        following = weights[index] + correlation * following
                        reverse[index] = 2.2 * following
                    actual, actual_rho, actual_sigma, actual_innovation = fn(eps, correlation, 2.2)
                    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-10)
                    np.testing.assert_allclose(actual_rho, weights @ dr, rtol=0, atol=1e-10)
                    np.testing.assert_allclose(actual_sigma, weights @ ds, rtol=0, atol=1e-10)
                    np.testing.assert_allclose(actual_innovation, reverse, rtol=0, atol=1e-10)

    def test_frozen_point_measurement_factors_against_reference(self):
        import pytensor
        import pytensor.tensor as pt
        from tooling.foundation.pa3_monitor import verify_cvm
        from methods.nof1.model import log_bin

        purpose = os.environ.get("NOF1_SYMBOLIC_PURPOSE", "N1")
        h = fixture("N-PATIENT-0", start=10, review=72)
        data = prepare([h], purpose=purpose, target_id=h.patient_id, seed_patient=h.patient_id)
        patient, point = data.patients[0], frozen_point(data)
        # All innovations/deviations and phase are zero at the fixed causal
        # point. This independent forward mean uses the public fixed designs.
        amp = point["population_amplitude"]
        z = (19. - amp[0] * patient.c - amp[2] * patient.medication[:, 0]
             - amp[3] * patient.medication[:, 1] + amp[4] * patient.path.rebound)
        total_difference = 0.
        for values, means, sigma, step, maximum in [
            (patient.isi, z[patient.recall].mean(axis=1), 2., 1., 28.),
            (patient.quality, 10. - z[patient.qindex] / 3., 1., .001, 10.)]:
            mean, sd = pt.dvector("mean"), pt.dscalar("sd")
            graph = log_bin(values, mean, sd, step, maximum).sum()
            function = pytensor.function([mean, sd], graph, **compile_options())
            verify_cvm(function)
            observed = float(function(means, sigma))
            expected = float(bin_logprob(values, means, sigma, step, maximum).sum())
            self.assertTrue(np.isfinite(observed))
            self.assertAlmostEqual(observed, expected, delta=1e-8)
            total_difference += observed - expected
        self.assertLessEqual(abs(total_difference), 1e-8)

    def test_original_density_and_directional_gradient_independent_reference(self):
        from methods.nof1.model import build
        from tooling.foundation.pa3_monitor import verify_cvm

        count = int(os.environ.get("NOF1_SYMBOLIC_PATIENTS", "1"))
        purpose = os.environ.get("NOF1_SYMBOLIC_PURPOSE", "N1")
        self.assertIn(count, (1, 2))
        histories = [fixture("N-PATIENT-" + str(i), start=10, review=72) for i in range(count)]
        data = prepare(histories, purpose=purpose, target_id=histories[-1].patient_id, seed_patient=histories[-1].patient_id)
        model = build(data)
        point = frozen_point(data)
        logp = model.compile_logp(jacobian=False, **compile_options())
        verify_cvm(logp.f)
        observed, expected = float(logp(point)), independent_logp(point, data)
        self.assertTrue(np.isfinite(observed))
        self.assertAlmostEqual(observed, expected, delta=1e-8)
        gradient = model.compile_dlogp(jacobian=False, **compile_options())
        verify_cvm(gradient.f)
        names = [value.name for value in model.value_vars]
        rng = np.random.default_rng(761)
        direction = {name: rng.normal(size=point[name].shape) * .1 for name in names}
        analytic = np.asarray(gradient(point))
        vector = np.concatenate([np.ravel(direction[name]) for name in names])
        self.assertTrue(np.isfinite(analytic).all())
        step = 1e-5
        plus = {name: point[name] + step * direction[name] for name in names}
        minus = {name: point[name] - step * direction[name] for name in names}
        finite = (independent_logp(plus, data) - independent_logp(minus, data)) / (2 * step)
        self.assertAlmostEqual(float(analytic @ vector), finite, delta=1e-5 + 1e-5 * abs(finite))
        # Scalar conjugate factors are checked separately so a count dtype
        # normalizer failure cannot hide inside a large total likelihood.
        for name in ("p_C", "p_M", "q"):
            value = model[name]
            for argument in value.owner.inputs[-2:]:
                self.assertEqual(argument.dtype, "float64")
            factor = model.compile_logp(vars=[value], jacobian=False, **compile_options())
            verify_cvm(factor.f)
            reference = 0.
            for i, patient in enumerate(data.patients):
                c = patient.counts
                successes, failures = ((c["C_success"], c["C_total"] - c["C_success"]) if name == "p_C" else
                    (c["M_success"], c["M_total"] - c["M_success"]) if name == "p_M" else
                    (c["observed"], c["missing"]))
                reference += beta.logpdf(expit(point[name + "_logodds__"][i]), 1. + successes, 1. + failures)
            self.assertAlmostEqual(float(factor({name + "_logodds__": point[name + "_logodds__"]})), reference, delta=1e-10)


if __name__ == "__main__":
    unittest.main()
