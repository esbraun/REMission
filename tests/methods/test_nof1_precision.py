"""Light frozen-point/source controls; never import or execute PyMC."""
import ast
from pathlib import Path
import unittest

import numpy as np

from contracts.domain.nof1_config import configuration
from methods.nof1.data import prepare
from test_nof1_data import fixture
from test_nof1_symbolic import frozen_point, independent_logp


class PrecisionSourceTests(unittest.TestCase):
    def test_fixed_causal_density_reference_and_explicit_float64_point(self):
        h = fixture("N-PATIENT-0", start=10, review=72)
        data = prepare([h], purpose="N0", target_id=h.patient_id, seed_patient=h.patient_id)
        point = frozen_point(data)
        self.assertEqual((data.patients[0].day, len(point["innovation_0"])), (82, 96))
        self.assertTrue(all(value.dtype == np.dtype("float64") and np.isfinite(value).all()
                            for value in point.values()))
        # Independently reported original-coordinate SciPy density in numerical
        # review bbc5d212; the pre-fix source differs by3.8454e-7 at this point.
        self.assertAlmostEqual(independent_logp(point, data), -777.2208826453802, delta=1e-10)

    def test_n_source_delegates_both_measurements_to_one_pinned_helper(self):
        root = Path(__file__).resolve().parents[2]
        tree = ast.parse((root / "methods/nof1/model.py").read_text())
        imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == "methods.measurement"]
        self.assertEqual(len(imports), 1)
        self.assertEqual([(name.name, name.asname) for name in imports[0].names], [("log_bin", None)])
        self.assertFalse(any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "log_bin"
                             for node in ast.walk(tree)))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                 and node.func.id == "log_bin"]
        self.assertEqual(len(calls), 2)  # one ISI block and one quality block
        for purpose in ("N0", "N1"):
            settings = configuration(purpose)
            self.assertEqual(settings["measurement_kernel"]["source_git_blob"], "595eabdb2260b3318effe405fd93d44ab427069e")
            self.assertFalse(settings["executable"])


if __name__ == "__main__":
    unittest.main()
