"""Expected versus predictive quality, independent references and seed controls."""
from itertools import product
from types import SimpleNamespace
import unittest

import numpy as np
import xarray as xr

from contracts.domain.nof1_config import CONFIG_REFS, PRIOR_REF, configuration
from contracts.domain.protocol_request import EXECUTABLE_CONFIGURATIONS, N_PRIOR_REF
from methods.nof1.observation import expected_quality
from methods.nof1.rollout import FIELDS, TargetDraws, paired_futures, predictive, target_draws
from methods.nof1.numerics import integrate, integration_bounds
from methods.nof1.data import prepare
from test_nof1_data import fixture


def theta(**changes):
    return dict(dict(b=18., a=.3, rho=.4, sigma_e=.3, sigma_quality=.45, current_error=.2,
        beta_C=2., beta_A=1.5, beta_B=2.5, gamma=1., p_C=.7, p_M=.6, q=.9), **changes)


def draws(*, shape=(2, 20), purpose="N1", **changes):
    return TargetDraws("N-PATIENT-A", purpose, 46, .7, (.1, .2), .25,
        {key: np.full(shape, value) for key, value in theta(**changes).items()})


def futures(parameters, *, purpose="N1", current=(0., (0., 0.), 0.), u=None, process=None, noise=None):
    if u is None:
        u = np.zeros((1, 7, 2))
    return paired_futures(parameters, purpose=purpose, day=46, current_c=current[0],
        current_medication=current[1], current_rebound=current[2], adherence_uniforms=u,
        process_normals=np.zeros(u.shape[:2]) if process is None else process,
        measurement_normals=np.zeros(u.shape[:2]) if noise is None else noise)


class RolloutTests(unittest.TestCase):
    def test_no_noise_sign_scale_carryover_and_null(self):
        t = theta(a=0., current_error=0., beta_C=0., beta_A=3., beta_B=6., p_M=1., sigma_e=0., sigma_quality=0.)
        n0, n1 = futures(t, purpose="N0"), futures(t)
        np.testing.assert_allclose(n0[0, 0], 5.)
        np.testing.assert_allclose(n0[0, 1], 6.)
        # Independent deterministic recurrence: first A exposure .5 -> quality4.5.
        self.assertEqual(n1[0, 0, 0], 4.5)
        self.assertLess((n1[:, 0] - n1[:, 1]).mean(), 0)
        null = futures(dict(t, beta_A=0., beta_B=0.))
        np.testing.assert_array_equal(null[:, 0], null[:, 1])

    def test_future_is_origin_T_plus_one_and_residual_states_retained(self):
        t = theta(beta_C=0., beta_A=0., beta_B=0., gamma=0., sigma_e=0., sigma_quality=0.)
        q = futures(t)
        expected = np.round(10 - (18 + .3 * np.sin(2 * np.pi * np.arange(47, 54) / 21)
                                  + .2 * .4 ** np.arange(1, 8)) / 3, 3)
        np.testing.assert_array_equal(q[0, 0], expected)
        state = futures(theta(a=0., current_error=0., sigma_e=0., sigma_quality=0.), current=(.7, (.5, .25), 1.))
        reset = futures(theta(a=0., current_error=0., sigma_e=0., sigma_quality=0.))
        self.assertFalse(np.array_equal(state, reset))

    def test_stochastic_mean_against_exhaustive_medication_and_normal_reference(self):
        t = theta(a=0., beta_C=0., current_error=0., sigma_e=0., p_C=0., gamma=0.)
        expected = 0.
        for bits in product((0, 1), repeat=7):
            weight = .6 ** sum(bits) * .4 ** (7 - sum(bits))
            ma = mb = 0.
            for bit in bits:
                ma, mb = .5 * ma + .5 * bit, .5 * mb + .5 * bit
                expected += weight * float(expected_quality(4 + t["beta_A"] * ma / 3, .45)
                    - expected_quality(4 + t["beta_B"] * mb / 3, .45)) / 7
        rng = np.random.default_rng(731)
        q = futures(t, u=rng.random((30000, 7, 2)), noise=rng.normal(size=(30000, 7)))
        effects = (q[:, 0] - q[:, 1]).mean(axis=-1)
        self.assertLess(abs(effects.mean() - expected), 4 * effects.std(ddof=1) / np.sqrt(len(effects)) + .0002)

    def test_integrated_draw_axes_seed_replay_q_not_endpoint_and_predictive_separate(self):
        d = draws(beta_A=0., beta_B=0.)
        result, report = integrate(d, seed=719)
        replay, again = integrate(d, seed=719)
        self.assertEqual(result.shape, (2, 20, 1))
        np.testing.assert_array_equal(result, np.zeros_like(result))
        np.testing.assert_array_equal(result, replay)
        self.assertEqual([x["K"] for x in report["attempted"]], [1024, 2048])
        self.assertEqual(report["axes"], ["chain", "draw", "target"])
        self.assertEqual(report["kind"], "conditional_expected_assignment_contrast")
        self.assertEqual(report["status"], again["status"])
        pred = predictive(draws(q=0.), seed=721)
        np.testing.assert_array_equal(pred["quality"], predictive(draws(q=0.), seed=721)["quality"])
        self.assertEqual(pred["quality"].shape, (2, 20, 1, 2, 7))
        self.assertFalse(pred["available"].any())
        self.assertGreater(pred["quality"].min(), 0)
        np.testing.assert_array_equal(pred["quality"], predictive(draws(q=1.), seed=721)["quality"])
        with self.assertRaises(ValueError):
            integrate(draws(shape=(2, 21)), seed=1)
        abstained, failure = integrate(d, seed=719, seconds=1e-9)
        self.assertIsNone(abstained)
        self.assertEqual(failure["reason"], "whole-integration-deadline")

    def test_bootstrap_carries_eight_batch_rows_and_uninflates_variance(self):
        settings = configuration("N1")
        outer = np.arange(80).reshape(2, 40) / 80
        offsets = np.arange(8) / 1000
        batches = outer[..., None] + offsets
        result = integration_bounds(batches, settings=settings)
        self.assertAlmostEqual(result["residual_variance"], offsets.var(ddof=1) / 8, places=15)
        self.assertAlmostEqual(result["uninflated_effect_variance"],
            outer.var(ddof=1) - offsets.var(ddof=1) / 8, places=15)
        self.assertEqual(result, integration_bounds(batches, settings=settings))
        with self.assertRaises(ValueError):
            integration_bounds(batches[..., :7], settings=settings)

    def test_posterior_target_selection_checks_axes_and_shared_state(self):
        data = prepare([fixture(), fixture("N-PATIENT-B")], purpose="N1", target_id="N-PATIENT-B", seed_patient="N-PATIENT-B")
        coords = dict(chain=[0, 1], draw=np.arange(20), patient=["N-PATIENT-A", "N-PATIENT-B"], coefficient=["C", "E", "A", "B", "R"])
        values = {}
        shared = {"a", "rho", "sigma_e", "sigma_quality"}
        for key, value in theta().items():
            if key.startswith("beta_") or key == "gamma":
                continue
            dims = ("chain", "draw") if key in shared else ("patient", "draw", "chain")
            shape = (2, 20) if key in shared else (2, 20, 2)
            values[key] = (dims, np.full(shape, value))
        values["b"][1][1, :, :] = 21.
        values["patient_amplitude"] = (("chain", "draw", "patient", "coefficient"), np.ones((2, 20, 2, 5)))
        trace = SimpleNamespace(posterior=xr.Dataset(values, coords=coords))
        selected = target_draws(trace, data)
        self.assertEqual(selected.target_id, "N-PATIENT-B")
        self.assertEqual(set(selected.parameters), set(FIELDS))
        np.testing.assert_array_equal(selected.parameters["b"], np.full((2, 20), 21.))

    def test_config_identity_proposal_distinct_and_boundary_not_admitted(self):
        self.assertEqual(EXECUTABLE_CONFIGURATIONS, frozenset())
        self.assertNotEqual(PRIOR_REF, N_PRIOR_REF)
        self.assertNotEqual(CONFIG_REFS["N0"]["sha256"], CONFIG_REFS["N1"]["sha256"])
        a, b = configuration("N0"), configuration("N1")
        for key in set(a) - {"id", "model", "purpose"}:
            self.assertEqual(a[key], b[key])
        self.assertFalse(a["executable"])


if __name__ == "__main__":
    unittest.main()
