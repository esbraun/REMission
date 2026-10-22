"""Original-wire and paired exogenous law checks, without model fitting."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from services.generator.restricted import generate as v1
from services.generator.restricted_v2 import Extension, generate as v2
from services.generator.server import generate as dispatch


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class ProtocolGeneratorTests(unittest.TestCase):
    def request(self):
        return dict(seed=1245, index=1, patient_id='p1-prefix', through_day=14,
                    actions=[dict(day=0, option='behavioral_continue', assignment_id='p1-background')])

    def extended(self, **changes):
        return self.request() | dict(law_version='poc-longitudinal-v2', family='support', medications=[], support=[]) | changes

    def test_original_v1_wire_and_no_intervention_v2_base_prefix(self):
        expected=json.loads(Path('tests/generator/p1-v1-prefix-origin.json').read_text())
        original=v1(self.request())
        self.assertEqual(hashlib.sha256(canonical(original).encode()).hexdigest(), expected['product_sha256'])
        self.assertEqual(dispatch(self.request()), original)
        extended=v2(self.extended())
        self.assertEqual(original['name'], extended['name'])
        self.assertEqual(len(original['records']), len(extended['records']))
        for old,new in zip(original['records'],extended['records']):
            # Exact outcomes/measurement/missingness/times/lineage; explicit
            # source/minor-version metadata intentionally differs.
            self.assertEqual({k:v for k,v in old['record'].items() if k not in ('source','schema_version')},
                             {k:v for k,v in new['record'].items() if k not in ('source','schema_version')})
        self.assertEqual(dispatch(self.extended()), extended)
        for bad in [self.request() | dict(law_version='unknown'), self.extended() | dict(unexpected=True)]:
            with self.assertRaises(ValueError):dispatch(bad)

    def test_medication_rebound_follows_assignment_cessation_not_missed_dose(self):
        request=self.extended(family='nof1_med', medications=[dict(day=0, option='MED_B', assignment_id='med-B'),dict(day=2, option=None, assignment_id=None)])
        extension=Extension(request)
        with patch('services.generator.restricted_v2.medication_taken', return_value=True):
            self.assertAlmostEqual(extension.medication_burden(1,1.), -1.25)
            self.assertAlmostEqual(extension.medication_burden(2,1.), -1.875)
        self.assertAlmostEqual(extension.medication_burden(3,1.), -.9375+1.)
        self.assertAlmostEqual(extension.medication_burden(4,1.), -.46875+.5)
        extension=Extension(request)
        with patch('services.generator.restricted_v2.medication_taken', side_effect=[True,False]):
            extension.medication_burden(1,1.)
            self.assertAlmostEqual(extension.medication_burden(2,1.), -.625)
            self.assertEqual(extension.rebound,0.)

    def test_support_quality_has_no_direct_isi_effect_and_burden_is_bounded(self):
        baseline=v2(self.extended())
        intervention=v2(self.extended(support=[dict(day=0, option='support_prompt', assignment_id='support-1')]))
        old=[r['record'] for r in baseline['records'] if r['record']['kind']=='isi']
        new=[r['record'] for r in intervention['records'] if r['record']['kind']=='isi']
        self.assertEqual(old,new)
        for days in ([0,1],[0,2,4,6]):
            with self.assertRaisesRegex(ValueError,'burden'):
                v2(self.extended(support=[dict(day=d,option='support_prompt',assignment_id='s'+str(d)) for d in days]))
        with self.assertRaises(ValueError):
            v2(self.extended(family='nof1_med',support=[dict(day=0,option='support_prompt',assignment_id='s')]))
        with self.assertRaises(ValueError):
            v2(self.extended(medications=[dict(day=0,option='MED_A',assignment_id='m')]))


if __name__=='__main__':unittest.main()
