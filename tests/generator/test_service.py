"""Actual cookie/CSRF/SQLite/HTTP producer loop on the pinned runtime."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.error
from unittest.mock import patch
from fastapi.testclient import TestClient
from services.foundation.app import Settings, create_app
from services.foundation.cli import seed, DEMO_PASSWORDS
from services.foundation.store import canonical, instant
from services.foundation.workflow import history, record_header
from services.foundation.replay import append_event, parse_observed, apply_current_state
from services.foundation.store import digest
from services.generator.server import Handler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integration/replay'))
from live_helpers import fresh_store

NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
ORIGIN = 'http://127.0.0.1:8765'


class SimulationServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = fresh_store(Path(self.directory.name) / 'service.sqlite')
        seed(self.store)
        self.store.clock = lambda: NOW
        self.settings = Settings(self.store.path, self.store.installed, clock=lambda: NOW,
                                 generator_url=f'http://127.0.0.1:{self.server.server_port}')
        self.client = TestClient(create_app(self.settings), base_url=ORIGIN)
        self.login(self.client)
        self.sequence = 0

    def tearDown(self):
        self.client.close(); self.directory.cleanup()

    def login(self, client, user='alice'):
        csrf = client.get('/api/session').json()['csrf']
        result = client.post('/api/login', json=dict(username=user, password=DEMO_PASSWORDS[user]),
                             headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf})
        self.assertEqual(result.status_code, 200, result.text)

    def headers(self, key=None, client=None):
        self.sequence += 1
        client = client or self.client
        return {'Origin': ORIGIN, 'X-CSRF-Token': client.get('/api/session').json()['csrf'],
                'Idempotency-Key': key or f'operation-{self.sequence}'}

    def panel(self, seed_value=20261021, count=2):
        result = self.client.post('/api/panels/generate', json=dict(seed=seed_value, count=count), headers=self.headers())
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()['patient_ids']

    def workspace(self, identifier):
        response = self.client.get('/api/patients/' + identifier)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def approve_payload(self, identifier, option='behavioral_continue'):
        snapshot = self.workspace(identifier)['snapshot']
        return dict(decision_id=snapshot['record_id'], expected_patient_version=snapshot['patient_version'],
            expected_state_version=snapshot['state_version'], expected_consent_version=snapshot['consent_version'],
            expected_eligibility_version=snapshot['eligibility_version'], mode='current', option=option,
            rationale='Explore synthetic treatment response', purpose='ordinary_treatment',
            follow_up_at=(instant(snapshot['cutoff']) + timedelta(days=14)).isoformat())

    def approve(self, identifier, option='behavioral_continue'):
        response = self.client.post(f'/api/patients/{identifier}/approve', json=self.approve_payload(identifier, option), headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def step(self, identifier, mode='visit', expected=None, key=None):
        version = self.workspace(identifier)['snapshot']['patient_version'] if expected is None else expected
        return self.client.post(f'/api/patients/{identifier}/advance', json=dict(expected_version=version, mode=mode), headers=self.headers(key))

    def outcomes(self, identifier):
        return [{k: r[k] for k in ('kind', 'event_at', 'available_at', 'sleep_quality', 'function', 'missingness', 'items') if k in r}
                for r in self.workspace(identifier)['projection']['records'] if r['kind'] in ('daily_report', 'isi')]

    def test_panel_bounds_default_ownership_reproduction_and_loading(self):
        for invalid in ({'seed': -1, 'count': 2}, {'seed': 1, 'count': 25}, {'seed': 1, 'count': 1}, {'seed': True, 'count': 2}):
            self.assertEqual(self.client.post('/api/panels/generate', json=invalid, headers=self.headers()).status_code, 422)
        response = self.client.post('/api/panels/generate', json={'seed': 40}, headers=self.headers('default'))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['count'], 12)
        self.assertEqual(self.client.get('/api/patients').json()['generated']['count'], 12)
        self.assertEqual(self.client.get('/api/patients').json()['denominator'], 22)
        first = self.panel()
        baseline = self.outcomes(first[0])
        repeat = self.panel()
        self.assertEqual(baseline, self.outcomes(repeat[0]))
        different = self.panel(seed_value=20261022)
        self.assertNotEqual(baseline, self.outcomes(different[0]))
        all_owned = self.client.get('/api/patients').json()
        self.assertEqual(all_owned['generated']['count'], 2)
        self.assertTrue(set(first).issubset({p['id'] for p in all_owned['patients']}))
        self.assertIn('SYN-02', {p['id'] for p in all_owned['patients']})
        self.assertEqual(self.workspace(first[0])['simulation']['day'], 0)  # Old generation retained.
        with TestClient(create_app(self.settings), base_url=ORIGIN) as bob:
            self.login(bob, 'bob')
            self.assertEqual(bob.get('/api/patients/' + first[0]).status_code, 404)
            self.assertEqual(bob.post(f'/api/patients/{first[0]}/advance', json={'expected_version': 1, 'mode': 'day'}, headers=self.headers(client=bob)).status_code, 404)
        self.assertEqual(self.client.post('/api/panels/generate', json={'seed': 5, 'count': 2}).status_code, 403)

    def test_decide_advance_persist_history_and_matched_branches(self):
        first = self.panel()[0]
        initial = self.workspace(first)
        self.assertEqual([x['action'] for x in initial['options']], ['behavioral_continue', 'behavioral_escalate'])
        self.assertEqual(initial['simulation']['actions'], [])
        self.assertEqual(self.client.post(f'/api/patients/{first}/approve', json=self.approve_payload(first, 'MED_A'), headers=self.headers()).status_code, 409)
        approved = self.approve(first)
        self.assertEqual(self.workspace(first)['simulation']['day'], 0)
        self.assertEqual(self.workspace(first)['plan']['effective_at'], '2026-01-01T20:00:00+00:00')
        saved = self.client.get(f'/api/patients/{first}/history/{approved["bundle_id"]}').json()
        for _ in range(14):
            response = self.step(first, 'day')
            self.assertEqual(response.status_code, 200, response.text)
        first_outcomes = self.outcomes(first)
        repeat = self.panel()[0]
        self.approve(repeat)
        self.assertEqual(self.step(repeat).status_code, 200)
        self.assertEqual(first_outcomes, self.outcomes(repeat))
        changed = self.panel()[0]
        self.approve(changed, 'behavioral_escalate')
        self.assertEqual(self.step(changed).status_code, 200)
        self.assertNotEqual(first_outcomes, self.outcomes(changed))
        restored = TestClient(create_app(self.settings), base_url=ORIGIN)
        self.login(restored)
        self.assertEqual(restored.get('/api/patients/' + first).json()['simulation']['day'], 14)
        restored.close()
        self.assertEqual(saved, self.client.get(f'/api/patients/{first}/history/{approved["bundle_id"]}').json())
        later = self.client.get(f'/api/patients/{first}/history/{approved["bundle_id"]}/later-outcomes')
        self.assertEqual(later.status_code, 200, later.text)
        self.assertEqual(len(later.json()['records']), 15)
        projected = self.workspace(first)['projection']
        self.assertTrue(all(r.get('seed') is None for r in projected['records']))
        self.assertNotIn('simulation', projected)
        self.assertNotIn('20261021', json.dumps(projected))
        self.assertTrue(all(instant(r['available_at']) < instant(self.workspace(first)['snapshot']['cutoff']) for r in projected['records']))

    def test_stale_same_day_hold_death_and_historical_write_guards(self):
        identifier = self.panel()[0]
        stale = self.approve_payload(identifier)
        self.approve(identifier)
        self.assertEqual(self.client.post(f'/api/patients/{identifier}/approve', json=stale, headers=self.headers()).status_code, 409)
        before = self.workspace(identifier)
        changed = self.client.post(f'/api/patients/{identifier}/state', json=dict(expected_version=before['snapshot']['patient_version'], stage='ASSIGN-02', reason='Reviewed prerequisites'), headers=self.headers())
        self.assertEqual(changed.status_code, 200)
        again = self.client.post(f'/api/patients/{identifier}/approve', json=self.approve_payload(identifier), headers=self.headers())
        self.assertEqual(again.status_code, 409, again.text)
        self.assertEqual(again.json()['code'], 'plan_already_chosen')
        historical = self.approve_payload(identifier); historical['mode'] = 'historical'
        self.assertEqual(self.client.post(f'/api/patients/{identifier}/approve', json=historical, headers=self.headers()).json()['code'], 'historical_write')
        held = self.client.post(f'/api/patients/{identifier}/state', json=dict(expected_version=1, stage='ASSIGN-09', reason='Synthetic hold'), headers=self.headers())
        self.assertEqual(held.status_code, 200)
        self.assertEqual(self.step(identifier).json()['code'], 'clinical_hold')
        self.assertEqual(self.workspace(identifier)['simulation']['actions'], before['simulation']['actions'])
        # A real operational receipt can carry a simulated death fact; it blocks all later generation.
        at = instant('2026-01-02T07:00:00+00:00')
        record = dict(**record_header('death-test', identifier, at), kind='intercurrent_event', event_type='death', detail='Synthetic terminal event')
        raw = canonical({k: v for k, v in record.items() if k != 'source'}).encode(); record['source']['raw_sha256'] = digest(raw)
        with self.store.transaction(write=True) as db:
            append_event(db, parse_observed(canonical(record).encode()), raw)
            apply_current_state(db, identifier, NOW)
        self.assertEqual(self.step(identifier).status_code, 409)
        self.assertEqual(self.workspace(identifier)['simulation']['day'], 0)

    def test_rollback_retry_stale_version_and_horizon(self):
        identifier = self.panel()[0]
        self.approve(identifier)
        before = self.workspace(identifier)
        def fail(stage):
            if stage == 'after_simulation_events': raise RuntimeError('injected rollback')
        with TestClient(create_app(replace(self.settings, fault=fail)), base_url=ORIGIN, raise_server_exceptions=False) as broken:
            self.login(broken)
            response = broken.post(f'/api/patients/{identifier}/advance', json={'expected_version': before['snapshot']['patient_version'], 'mode': 'visit'}, headers=self.headers('retry', broken))
            self.assertEqual(response.status_code, 500)
        self.assertEqual(before, self.workspace(identifier))
        with patch('services.generator.server.generate', return_value={'name': 'Broken', 'records': []}):
            self.assertEqual(self.step(identifier).status_code, 503)
        self.assertEqual(before, self.workspace(identifier))
        with patch('services.foundation.simulation.urllib.request.urlopen', side_effect=urllib.error.URLError('producer down')):
            self.assertEqual(self.step(identifier).json()['code'], 'generator_failed')
        self.assertEqual(before, self.workspace(identifier))
        response = self.step(identifier, expected=before['snapshot']['patient_version'], key='retry')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), self.step(identifier, expected=before['snapshot']['patient_version'], key='retry').json())
        self.assertEqual(self.step(identifier, expected=before['snapshot']['patient_version']).json()['code'], 'stale_simulation')
        for _ in range(5): self.assertEqual(self.step(identifier).status_code, 200)
        self.assertEqual(self.workspace(identifier)['simulation']['day'], 84)
        self.assertEqual(self.step(identifier).json()['code'], 'simulation_complete')


if __name__ == '__main__': unittest.main()
