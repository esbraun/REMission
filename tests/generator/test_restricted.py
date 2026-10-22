"""Behavioral-law checks independent of service/runtime admission."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from contracts.domain.boundaries import ObservedHistory
from services.generator.restricted import generate


class RestrictedGeneratorTests(unittest.TestCase):
    def request(self, **changes):
        return dict(seed=20261021, index=0, patient_id='POC-test-01', through_day=84, actions=[], **changes)

    def test_reproduction_variation_cutoff_and_no_private_fields(self):
        request = self.request()
        first = generate(request)
        self.assertEqual(first, generate(copy.deepcopy(request)))
        other = dict(request, seed=request['seed'] + 1)
        self.assertNotEqual(first, generate(other))
        ObservedHistory.model_validate_json(json.dumps(dict(schema_version='1.0.0', synthetic=True,
            kind='observed_history', patient_id=request['patient_id'], records=[r['record'] for r in first['records']])))
        encoded = json.dumps(first)
        for private in ('baseline_severity', 'response_multiplier', 'latent', 'truth', 'parameters'):
            self.assertNotIn(private, encoded)
        for entry in first['records']:
            self.assertEqual(hashlib.sha256(entry['raw_source'].encode()).hexdigest(), entry['record']['source']['raw_sha256'])
        early = generate(dict(request, through_day=14))
        self.assertEqual(early['records'], first['records'][:len(early['records'])])

    def test_action_path_and_missingness_are_paired_across_branches(self):
        base = self.request()
        branches = [generate(dict(base, actions=[dict(day=0, option=option, assignment_id='assignment-1')]))
                    for option in ('behavioral_continue', 'behavioral_escalate')]
        reports = [[e['record'] for e in b['records'] if e['record']['kind'] == 'daily_report'] for b in branches]
        self.assertEqual([r['missingness'] for r in reports[0]], [r['missingness'] for r in reports[1]])
        self.assertTrue(any(r['missingness'] == 'missing' for r in reports[0]))
        differences = [b['sleep_quality'] - a['sleep_quality'] for a, b in zip(*reports) if a['sleep_quality'] is not None]
        self.assertGreater(sum(differences[-28:]) / 28, .2)
        # Durability/carryover is exercised by switching after a fortnight.
        switched = generate(dict(base, actions=[dict(day=0, option='behavioral_escalate', assignment_id='a'),
                                               dict(day=14, option='behavioral_continue', assignment_id='b')]))
        day15 = [e['record'] for e in switched['records'] if e['record']['kind'] == 'delivery'][14]
        self.assertEqual(day15['assignment_id'], 'b')
        deliveries = [[e['record'] for e in b['records'] if e['record']['kind'] == 'delivery'] for b in branches]
        self.assertEqual([r['adherence'] for r in deliveries[0]], [r['adherence'] for r in deliveries[1]])
        self.assertTrue(any(r['stage'] == 'not_taken' for r in deliveries[0]))

    def test_complete_recall_windows_and_input_bounds(self):
        product = generate(self.request())
        assessments = [e['record'] for e in product['records'] if e['record']['kind'] == 'isi']
        self.assertEqual(len(assessments), 7)
        for r in assessments:
            self.assertEqual(datetime.fromisoformat(r['recall_end']) - datetime.fromisoformat(r['recall_start']), timedelta(days=14))
            self.assertEqual(len(r['items']), 7)
            self.assertTrue(all(0 <= item <= 4 for item in r['items']))
        for changes in ({'seed': True}, {'through_day': 85}, {'index': 24}, {'patient_id': '../escape'},
                        {'actions': [dict(day=84, option='behavioral_continue', assignment_id='a')]},
                        {'actions': [dict(day=0, option='MED_A', assignment_id='a')]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                generate(dict(self.request(), **changes))

    def test_zero_noise_first_night_and_persistent_exposure_analytic_case(self):
        import math
        with patch('services.generator.restricted.uniform', return_value=.5), patch('services.generator.restricted.normal', return_value=0):
            product = generate(dict(self.request(), actions=[dict(day=0, option='behavioral_continue', assignment_id='a')]))
        reports = [e['record'] for e in product['records'] if e['record']['kind'] == 'daily_report']
        for day in (1, 14, 84):
            # A unit constant input to C=.65C+.35 has closed form 1-.65^t.
            expected_burden = 19 + .55 * math.sin(2 * math.pi * day / 21) - 2 * (1 - .65 ** day)
            self.assertAlmostEqual(reports[day - 1]['sleep_quality'], round(10 - expected_burden / 3, 3), places=3)

    def test_delivery_precedes_overnight_response_and_next_morning_report(self):
        from services.generator.restricted import START
        product = generate(dict(self.request(), actions=[dict(day=0, option='behavioral_continue', assignment_id='a')]))
        deliveries = [e['record'] for e in product['records'] if e['record']['kind'] == 'delivery']
        reports = [e['record'] for e in product['records'] if e['record']['kind'] == 'daily_report']
        for day, (delivery, report) in enumerate(zip(deliveries, reports), 1):
            delivered = datetime.fromisoformat(delivery['event_at'])
            reported = datetime.fromisoformat(report['event_at'])
            self.assertEqual(delivered, START + timedelta(days=day - 1, hours=8))
            self.assertLess(delivered, reported)
            self.assertLess(reported, START + timedelta(days=day))


if __name__ == '__main__':
    unittest.main()
