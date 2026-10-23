"""Opt-in Linux fixture qualification; never part of host structural discovery.

Run only under the separately authorized frozen image/network/mount proposal.
Actual app/SQLite/Argon2 and private generator HTTP; no training or analytics.
"""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import secrets
import socket
import tempfile
import time
import unittest
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from contracts.service.live_hold import InstalledBundle
from services.foundation.app import HASHER, Settings, create_app
from services.foundation.cli import reset_password
from services.foundation.store import Store
import admin

# TestClient-only documentation address: no external connection or certificate
# claim. Exercises IP-origin cookies/CSRF before the actual allocated-IP ingress.
ORIGIN = 'https://192.0.2.10'


class IsolatedSimulationQualification(unittest.TestCase):
    def test_new_accounts_auth_generator_decision_restart_and_revocation(self):
        generator = os.environ['REMISSION_GENERATOR_URL']
        if generator != 'http://generator:8780':
            raise ValueError('use only the frozen task-private generator endpoint')
        deadline = time.monotonic() + 30
        while True:
            try:
                with socket.create_connection(('generator', 8780), timeout=1):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('private_generator_readiness_timeout') from None
                time.sleep(0.1)
        deployment = {key: os.environ['QUALIFICATION_' + key.upper()]
                      for key in ('source_commit', 'service_image', 'generator_image')}
        with tempfile.TemporaryDirectory(prefix='cloud-simulation-') as directory:
            root = Path(directory)
            bootstrap = root / 'bootstrap'
            bootstrap.mkdir()
            database = root / 'remission.sqlite'
            admin.initialize(database, bootstrap, deployment)
            installed = InstalledBundle.model_validate_json((bootstrap / 'bundle.json').read_bytes())
            self.assertFalse(installed.control.enabled)
            self.assertEqual(installed.authority.grants, [])
            at = [datetime.now(timezone.utc)]
            store = Store(database, installed, clock=lambda: at[0])
            passwords = {name: secrets.token_urlsafe(32) for name in ('physician-one', 'physician-two')}
            for name, password in passwords.items():
                admin.create_account(store, name, 'Synthetic ' + name, password, HASHER)
            settings = Settings(database, installed, origin=ORIGIN, generator_url=generator,
                                source_commit=deployment['source_commit'], clock=lambda: at[0])
            first = TestClient(create_app(settings), base_url=ORIGIN)
            second = TestClient(create_app(settings), base_url=ORIGIN)
            anonymous = TestClient(create_app(settings), base_url=ORIGIN)
            clients = [first, second, anonymous]
            sequence = 0

            def headers(client):
                nonlocal sequence
                sequence += 1
                return {'Origin': ORIGIN, 'X-CSRF-Token': client.get('/api/session').json()['csrf'],
                        'Idempotency-Key': 'fixture-' + str(sequence)}

            def login(client, name, password):
                result = client.post('/api/login', json={'username': name, 'password': password}, headers=headers(client))
                self.assertEqual(result.status_code, 200)

            try:
                response = anonymous.get('/api/session')
                cookie = response.headers['set-cookie']
                for attribute in ('Secure', 'HttpOnly', 'SameSite=lax'):
                    self.assertTrue(attribute in cookie, 'missing cookie attribute: ' + attribute)
                self.assertEqual(anonymous.get('/api/patients').status_code, 401)
                self.assertEqual(anonymous.post('/api/panels/generate', json={'seed': 1, 'count': 12}, headers=headers(anonymous)).status_code, 401)
                for name in ('physician-one', 'unknown-physician'):
                    self.assertEqual(anonymous.post('/api/login', json={'username': name, 'password': 'wrong'}, headers=headers(anonymous)).status_code, 401)
                login(first, 'physician-one', passwords['physician-one'])
                login(second, 'physician-two', passwords['physician-two'])
                self.assertEqual(first.post('/api/panels/generate', json={'seed': 20261023, 'count': 12}, headers={'Origin': ORIGIN}).status_code, 403)
                forged = headers(first)
                forged['Origin'] = 'https://other.example.org'
                self.assertEqual(first.post('/api/panels/generate', json={'seed': 20261023, 'count': 12}, headers=forged).status_code, 403)
                generated = first.post('/api/panels/generate', json={'seed': 20261023, 'count': 12}, headers=headers(first))
                self.assertEqual(generated.status_code, 200)
                ids = generated.json()['patient_ids']
                self.assertEqual(len(ids), 12)
                self.assertEqual(second.get('/api/patients').json()['denominator'], 0)
                identifier = ids[0]
                path = '/api/patients/' + identifier
                self.assertEqual(second.get(path).status_code, 404)
                workspace = first.get(path).json()
                snapshot = workspace['snapshot']
                choice = dict(decision_id=snapshot['record_id'], mode='current', option='behavioral_continue',
                              rationale='Explicit isolated physician simulation qualification', purpose='ordinary_treatment',
                              follow_up_at=(datetime.fromisoformat(snapshot['cutoff']) + timedelta(days=14)).isoformat(),
                              **{'expected_' + key: snapshot[key] for key in
                                 ('patient_version', 'state_version', 'consent_version', 'eligibility_version')})
                self.assertEqual(second.post(path + '/approve', json=choice, headers=headers(second)).status_code, 404)
                approved = first.post(path + '/approve', json=choice, headers=headers(first))
                self.assertEqual(approved.status_code, 200)
                historical = path + '/history/' + approved.json()['bundle_id']
                old_history = first.get(historical).json()
                self.assertEqual(first.get(path + '/analyses').json(), {'attempts': []})
                current = first.get(path).json()
                version = current['snapshot']['patient_version']
                advance = {'expected_version': version, 'mode': 'visit'}
                self.assertEqual(second.post(path + '/advance', json=advance, headers=headers(second)).status_code, 404)
                self.assertEqual(first.post(path + '/advance', json=advance, headers=headers(first)).status_code, 200)
                self.assertEqual(first.get(path).json()['simulation']['day'], 14)
                self.assertEqual(first.get(historical).json(), old_history)
                self.assertEqual(first.post(path + '/advance', json=advance, headers=headers(first)).status_code, 409)
                self.assertEqual(first.post(path + '/approve', json=choice, headers=headers(first)).status_code, 409)
                def persisted():
                    value = first.get(path).json()
                    return {key: value[key] for key in ('snapshot', 'simulation', 'projection', 'history')}
                saved = persisted()
                first.close()
                first = TestClient(create_app(settings), base_url=ORIGIN)
                clients.append(first)
                login(first, 'physician-one', passwords['physician-one'])
                self.assertEqual(persisted(), saved)
                old_cookie = first.cookies.get('remission_session')
                self.assertEqual(first.post('/api/logout', headers=headers(first)).status_code, 200)
                first.cookies.set('remission_session', old_cookie, domain=urlsplit(ORIGIN).hostname, path='/')
                self.assertEqual(first.get('/api/patients').status_code, 401)
                first.cookies.clear()
                login(first, 'physician-one', passwords['physician-one'])
                reset_password(store, 'physician-one', secrets.token_urlsafe(32))
                self.assertEqual(first.get('/api/patients').status_code, 401)
                at[0] += timedelta(seconds=1801)
                self.assertEqual(second.get('/api/patients').status_code, 401)
            finally:
                for client in clients:
                    client.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
