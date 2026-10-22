"""LIGHT NumPy geometry/extraction checks, never PyTensor compilation."""
import unittest
import numpy as np
import xarray as xr
from methods.visit.cohort_geometry import coordinate_slices, embed_basis, patient_parameters


class Geometry(unittest.TestCase):
    def test_shared_coordinates_once_and_disjoint_patient_likelihood_blocks(self):
        layout = coordinate_slices(['p0', 'p1'], 14)
        self.assertEqual(layout['dimension'], 38)
        shared = np.ones((2, 4)); local = np.ones((2, 17))
        left = embed_basis(shared, local, 0, 2)
        right = embed_basis(shared*2, local*3, 1, 2)
        np.testing.assert_array_equal(left[:, layout['patients']['p1']], 0.)
        np.testing.assert_array_equal(right[:, layout['patients']['p0']], 0.)
        np.testing.assert_array_equal(left[:, :4], shared)
        design = np.concatenate([left, right])
        precision = np.eye(38)+design.T@design
        covariance = np.linalg.inv(precision)
        self.assertGreater(abs(covariance[layout['patients']['p0'].start, layout['patients']['p1'].start]), 1e-6)
        # Integrating shared population coordinates creates dependence; twelve
        # independent fits could not produce this local cross-covariance.
        with self.assertRaises(ValueError):
            coordinate_slices(['p1', 'p0'], 14)

    def test_gaussian_change_of_variables_matches_independent_marginal_identity(self):
        rng = np.random.default_rng(819)
        design = rng.normal(size=(6, 9)); variance = np.linspace(.4, 2., 6)
        y = rng.normal(size=6); eta = rng.normal(size=9)
        precision = np.eye(9)+design.T@(design/variance[:, None])
        cholesky = np.linalg.cholesky(precision)
        mean = np.linalg.solve(precision, design.T@(y/variance))
        u = mean+np.linalg.solve(cholesky.T, eta)
        correction = -.5*(u@u-eta@eta)-np.log(np.diag(cholesky)).sum()
        marginal = np.diag(variance)+design@design.T
        log_z = -.5*(6*np.log(2*np.pi)+np.linalg.slogdet(marginal)[1]+y@np.linalg.solve(marginal, y))
        residual = y-design@u
        log_guide = -.5*(6*np.log(2*np.pi)+np.log(variance).sum()+(residual**2/variance).sum())
        self.assertAlmostEqual(correction, log_z-log_guide, places=11)

    def test_extraction_preserves_patient_chain_draw_and_current_state(self):
        dataset = xr.Dataset(coords=dict(chain=[0, 1], draw=[0, 1, 2], patient=['a', 'b'], arm=['continue', 'escalate'], night=[13, 14]))
        for name in ('a', 'rho', 'sigma_e', 'sigma_isi', 'p_adherence'):
            dataset[name] = (('chain', 'draw'), np.ones((2, 3)))
        dataset['b'] = (('chain', 'draw', 'patient'), np.arange(12).reshape(2, 3, 2))
        dataset['patient_beta'] = (('chain', 'draw', 'patient', 'arm'), np.arange(24).reshape(2, 3, 2, 2))
        dataset['error'] = (('chain', 'draw', 'patient', 'night'), np.arange(24).reshape(2, 3, 2, 2))
        result = patient_parameters(dataset, 'b')
        np.testing.assert_array_equal(result['b'], [[1, 3, 5], [7, 9, 11]])
        np.testing.assert_array_equal(result['beta_c'], [[2, 6, 10], [14, 18, 22]])
        np.testing.assert_array_equal(result['current_e'], [[3, 7, 11], [15, 19, 23]])
        self.assertTrue(all(v.shape == (2, 3) for v in result.values()))


if __name__ == '__main__':
    unittest.main()
