"""Independent public-law controls; no posterior fit or config admission."""
import unittest

import numpy as np
from scipy.stats import norm

from methods.nof1.dynamics import exposure_path, medication_design
from methods.nof1.observation import expected_quality, rounded_quality


class DynamicsTests(unittest.TestCase):
    def test_impulse_and_washout_geometric_values(self):
        path = exposure_path(["MED_A", "MED_A", None, None],
                             ["MED_A", "MED_A", None, None])
        np.testing.assert_array_equal(path.medication, [[.5, 0], [.75, 0], [.375, 0], [.1875, 0]])
        np.testing.assert_array_equal(path.rebound, np.zeros(4))

    def test_assignment_cessation_distinct_from_missed_dose(self):
        path = exposure_path(["MED_B", "MED_B", None, None, "MED_A"],
                             ["MED_B", None, None, None, "MED_A"])
        np.testing.assert_array_equal(path.medication[:, 1], [.5, .25, .125, .0625, .03125])
        np.testing.assert_array_equal(path.rebound, [0, 0, 1, .5, .25])
        direct = exposure_path(["MED_A"], [None], previous_assigned="MED_B")
        np.testing.assert_array_equal(direct.rebound, [1])

    def test_convolution_reference_and_state_continuation(self):
        assigned = ["MED_B"] * 7 + [None] * 2 + ["MED_A"] * 7 + [None] * 2
        taken = [x if i % 3 else None for i, x in enumerate(assigned)]
        path = exposure_path(assigned, taken)
        for arm, column in [("MED_A", 0), ("MED_B", 1)]:
            expected = [sum(.5 ** (t - j + 1) for j in range(t + 1) if taken[j] == arm)
                        for t in range(len(taken))]
            np.testing.assert_allclose(path.medication[:, column], expected, rtol=0, atol=0)
        second = exposure_path(assigned[8:], taken[8:], initial_medication=path.medication[7],
                               initial_rebound=path.rebound[7], previous_assigned=assigned[7])
        np.testing.assert_array_equal(second.medication, path.medication[8:])
        np.testing.assert_array_equal(second.rebound, path.rebound[8:])

    def test_n0_n1_only_medication_design_differs(self):
        path = exposure_path(["MED_B", None], ["MED_B", None])
        np.testing.assert_array_equal(medication_design(path, "N0"), [[0, 1], [0, 0]])
        np.testing.assert_array_equal(medication_design(path, "N1"), [[0, .5], [0, .25]])
        np.testing.assert_array_equal(path.rebound, [0, 1])
        with self.assertRaises(ValueError):
            medication_design(path, "V0")

    def test_unknown_mismatched_or_malformed_inputs_rejected(self):
        for assigned, taken in [(["MED_A"], ["MED_B"]), ([None], ["unknown"]), ([], [None])]:
            with self.assertRaises(ValueError):
                exposure_path(assigned, taken)
        with self.assertRaises(ValueError):
            exposure_path([], [], initial_medication=[np.nan, 0])


class ObservationTests(unittest.TestCase):
    def test_full_category_mass_reference_including_tails(self):
        categories = np.arange(10001) * .001
        edges = np.r_[-np.inf, (np.arange(10000) + .5) * .001, np.inf]
        for mu, sd in [(-3, .2), (0, 1), (3.1234, .45), (10, 2), (14, 4)]:
            # Explicit category probability dot product, independent of tail sum.
            probabilities = np.diff(norm.cdf(edges, loc=mu, scale=sd))
            expected = probabilities @ categories
            self.assertAlmostEqual(float(expected_quality(mu, sd)), expected, places=12)

    def test_no_noise_clipping_and_input_axes(self):
        means = np.array([[-2., 0., 3.1234], [3.1236, 10., 20.]])
        np.testing.assert_array_equal(expected_quality(means, 0), [[0, 0, 3.123], [3.124, 10, 10]])
        np.testing.assert_allclose(expected_quality(np.array([[0, 10], [5, 5]]), .4),
                                   [[float(expected_quality(0, .4)), float(expected_quality(10, .4))], [5, 5]])
        self.assertEqual(rounded_quality(20), 10)
        with self.assertRaises(ValueError):
            expected_quality(5, -1)

    def test_expected_reported_quality_not_latent_or_coefficient(self):
        # Equal latent differences give different expected quality at a boundary.
        middle = expected_quality(6, .5) - expected_quality(5, .5)
        ceiling = expected_quality(11, .5) - expected_quality(10, .5)
        self.assertAlmostEqual(float(middle), 1., places=10)
        self.assertGreater(float(ceiling), 0)
        self.assertLess(float(ceiling), .2)


if __name__ == "__main__":
    unittest.main()
