"""Opt-in model-density/gradient qualification; requires exclusive heavy lease.

Default discovery skips this class before importing PyMC or building a graph.
Choose one N purpose and J at a time to keep each qualification bounded.
"""
import os
import unittest

import numpy as np
from scipy.special import expit
from scipy.stats import beta, halfnorm, norm, uniform

from methods.nof1.data import prepare
from methods.nof1.observation import bin_logprob
from test_nof1_data import fixture


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
    def test_original_density_and_directional_gradient_independent_reference(self):
        from methods.nof1.model import build

        count = int(os.environ.get("NOF1_SYMBOLIC_PATIENTS", "1"))
        purpose = os.environ.get("NOF1_SYMBOLIC_PURPOSE", "N1")
        self.assertIn(count, (1, 2))
        histories = [fixture("N-PATIENT-" + str(i), start=10, review=72) for i in range(count)]
        data = prepare(histories, purpose=purpose, target_id=histories[-1].patient_id, seed_patient=histories[-1].patient_id)
        model = build(data)
        point = model.initial_point()
        point["population_amplitude"] = np.array([1., -.2, 1.5, 2.5, .7])
        point["rho_interval__"] = np.array(.4)
        logp, gradient = model.compile_logp(jacobian=False), model.compile_dlogp(jacobian=False)
        observed, expected = float(logp(point)), independent_logp(point, data)
        self.assertTrue(np.isfinite(observed))
        self.assertAlmostEqual(observed, expected, delta=1e-8)
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
            factor = model.compile_logp(vars=[value], jacobian=False)
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
