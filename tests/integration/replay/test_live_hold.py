"""Actual SQLite, cookie/CSRF and service safety workflow acceptance."""
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from fastapi.testclient import TestClient
from services.foundation.app import Settings, create_app
from services.foundation.cli import seed, DEMO_PASSWORDS
from services.foundation.store import Store
from services.foundation.admission import AdmissionError
from live_helpers import fresh_store

NOW=datetime(2026,10,21,12,tzinfo=timezone.utc)
ORIGIN='http://127.0.0.1:8765'


class ActivationTests(unittest.TestCase):
    def test_explicit_activation_normal_start_and_real_login(self):
        with tempfile.TemporaryDirectory() as directory:
            store=fresh_store(Path(directory)/'new.sqlite');seed(store)
            settings=Settings(store.path,store.installed,clock=lambda:NOW)
            with TestClient(create_app(settings),base_url=ORIGIN) as client:
                self.assertEqual(client.get('/health').status_code,200)
                bootstrap=client.get('/api/session').json()
                login=client.post('/api/login',json=dict(username='alice',password=DEMO_PASSWORDS['alice']),
                    headers={'Origin':ORIGIN,'X-CSRF-Token':bootstrap['csrf']})
                self.assertEqual(login.status_code,200,login.text)
                current=client.get('/api/patients/SYN-02')
                self.assertEqual(current.status_code,200,current.text)
                self.assertEqual(current.json()['live_safety_summary']['patient_sequence'],1)
                self.assertTrue(current.json()['permissions']['approve_ordinary'])
            stale=store.installed.model_copy(deep=True)
            stale.control.authority_generation+=1
            with self.assertRaisesRegex(AdmissionError,'service_generation_mismatch'):
                Store(store.path,stale)


if __name__=='__main__':
    unittest.main()
