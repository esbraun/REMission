"""Declared tiny pinned-API regression; one Normal, no cohort or NUTS."""
import unittest
from unittest.mock import patch

import numpy as np
import pymc as pm

from methods.visit import cohort_execution as execution


class PinnedInitializerAPI(unittest.TestCase):
    def test_original_reseeding_wrapper_uses_captured_actual_cvm(self):
        events = []
        original_compile = execution.initial_point.compile
        with pm.Model() as model:
            theta = pm.Normal('theta', 0., 1., initval='prior')
        before = dict(model.__dict__)
        layout = [dict(name='theta', shape=[], dtype='float64', start=0, stop=1)]
        with patch.object(pm, 'sample', side_effect=AssertionError('No sampling in tiny regression')), \
                patch.object(pm.NUTS, 'astep', side_effect=AssertionError('No NUTS transition')):
            with execution.owned_callables(model, fit='initial', binding_sha256='a'*64,
                    on_event=events.append, expected_layout=layout):
                seeded = model._make_initial_point(overrides={'theta': 'prior'}, jitter_rvs={theta})
                original_seeded = seeded.__wrapped__
                actual = original_seeded.__wrapped__
                self.assertFalse(hasattr(original_seeded, 'maker'))
                self.assertTrue(hasattr(actual, 'maker'))
                first, repeated = seeded(739), seeded(739)
                np.testing.assert_array_equal(first['theta'], repeated['theta'])
                self.assertEqual(first['theta'].dtype, np.dtype('float64'))
                self.assertTrue(np.isfinite(first['theta']).all())
                self.assertEqual([e['function_identity'] for e in events], [id(actual)]*3)
                self.assertTrue(all(e['actual_vm']['vm_type'] == 'pytensor.link.c.cvm.CVM' for e in events))
                self.assertEqual([e['stage'] for e in events],
                    ['jitter_initializer', 'jitter_initializer_point', 'jitter_initializer_point'])
                self.assertEqual(events[-1]['coordinate_map'], layout)
        self.assertEqual(set(model.__dict__), set(before))
        for name, value in before.items():self.assertIs(model.__dict__[name], value)
        self.assertIs(execution.initial_point.compile, original_compile)
        self.assertFalse(execution._OWNER.locked())


if __name__ == '__main__':unittest.main()
