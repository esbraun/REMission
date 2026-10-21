"""Actual cookie routes and SQLite crash/restart/rollback for OBS2 archives."""
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'run_contracts'))
from observed_v2_fixtures import build, canonical
from contracts.runs.observed_v2 import ExportAuthorityV2
from services.foundation.app import Settings, create_app
from services.foundation.archive import archive_export
from services.foundation.cli import DEMO_PASSWORDS, seed
from services.foundation.replay import replay
from services.foundation.store import Store, digest
from services.foundation.workflow import history
from live_helpers import fresh_store

ORIGIN = 'http://127.0.0.1:8765'
NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = fresh_store(self.root / 'archive.sqlite')
        self.store.clock=lambda:NOW
        seed(self.store)
        with self.store.transaction() as db:
            self.owner = db.execute("SELECT owner_id FROM patients WHERE id='SYN-02'").fetchone()[0]
        self.fixture = build(self.root / 'staging', hold=True)
        self.authority = ExportAuthorityV2.model_validate_json(canonical(self.fixture['authority']))
        self.settings = Settings(self.store.path, self.store.installed, clock=lambda: NOW,
                                 observed_archives={'fixture-export': (self.fixture['raw'], self.root / 'staging', self.authority)})
        self.client = TestClient(create_app(self.settings), base_url=ORIGIN)

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def login(self, client=None, user='alice'):
        client = client or self.client
        bootstrap = client.get('/api/session').json()
        response = client.post('/api/login', json=dict(username=user, password=DEMO_PASSWORDS[user]), headers={'Origin': ORIGIN, 'X-CSRF-Token': bootstrap['csrf']})
        self.assertEqual(response.status_code, 200, response.text)

    def headers(self, client=None):
        client = client or self.client
        return {'Origin': ORIGIN, 'X-CSRF-Token': client.get('/api/session').json()['csrf']}

    def counts(self):
        with self.store.transaction() as db:
            return {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in ['observed_archives', 'observed_archive_entries', 'observed_archive_artifacts', 'events', 'replay_runs', 'decisions']}

    def test_authenticated_owned_read_only_archive_preserves_every_raw_byte(self):
        self.assertEqual(self.client.post('/api/observed-archives/fixture-export', json={'mode': 'archive_only'}).status_code, 401)
        self.login()
        self.assertEqual(self.client.post('/api/observed-archives/fixture-export', json={'mode': 'archive_only'}).status_code, 403)
        bob = TestClient(create_app(self.settings), base_url=ORIGIN)
        self.login(bob, 'bob')
        self.assertEqual(bob.post('/api/observed-archives/fixture-export', json={'mode': 'archive_only'}, headers=self.headers(bob)).status_code, 404)
        before = self.counts()
        response = self.client.post('/api/observed-archives/fixture-export', json={'mode': 'archive_only'}, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        receipt = response.json()
        self.assertEqual(receipt['status'], 'archived_read_only')
        self.assertFalse(receipt['live_authority_granted'])
        self.assertEqual(receipt['cursor'], len(self.fixture['entries']))
        after = self.counts()
        for table in ['events', 'decisions', 'replay_runs']:
            self.assertEqual(after[table], before[table])
        with self.store.transaction() as db:
            self.assertEqual(bytes(db.execute('SELECT manifest FROM observed_archives').fetchone()[0]), self.fixture['raw'])
            rows = db.execute('SELECT * FROM observed_archive_entries ORDER BY ordinal').fetchall()
            for row, entry in zip(rows, self.fixture['entries']):
                self.assertEqual(bytes(row['raw_source']), entry['raw_source'].encode())
                self.assertEqual(row['raw_sha256'], digest(entry['raw_source']))
                self.assertEqual(bytes(row['payload']), canonical(entry['record']))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('DELETE FROM observed_archive_entries')
        path = '/api/patients/SYN-02/observed-archives/' + receipt['archive_id']
        shown = self.client.get(path).json()
        self.assertTrue(shown['read_only'])
        self.assertEqual(shown['entries'], self.fixture['entries'])
        self.assertEqual(bob.get(path).status_code, 404)
        retry = self.client.post('/api/observed-archives/fixture-export', json={'mode': 'archive_only'}, headers=self.headers()).json()
        self.assertEqual(retry, receipt)
        self.assertEqual(self.counts(), after)
        bob.close()

    def test_entire_hold_partition_rejected_before_any_current_publication_including_v1(self):
        self.login()
        before = self.counts()
        response = self.client.post('/api/observed-archives/fixture-export', json={'mode': 'clinical_observation_import'}, headers=self.headers())
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()['code'], 'independent_hold_live_integration_required')
        self.assertEqual(self.counts(), before)
        hold_snapshot = next(e for e in self.fixture['entries'] if e['record']['kind'] == 'decision_snapshot' and e['record']['workflow']['clinical'] == 'clinical_hold')
        with self.assertRaisesRegex(ValueError, 'independent_hold_live_integration_required'):
            replay(self.store, 'v1-bypass', [self.fixture['entries'][0], hold_snapshot], NOW.isoformat())
        self.assertEqual(self.counts(), before)
        response = self.client.post('/api/patients/SYN-02/events', json=hold_snapshot, headers={**self.headers(), 'Idempotency-Key': 'v1-hold'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'independent_hold_live_integration_required')
        self.assertEqual(self.counts(), before)

    def test_real_sqlite_before_after_commit_crash_restart_cursor_and_conflict(self):
        before = self.counts()
        def crash(stage):
            if stage == 'before_archive_commit':
                raise RuntimeError('simulated process failure before commit')
        with self.assertRaises(RuntimeError):
            archive_export(self.store, self.fixture['raw'], self.root / 'staging', self.authority, owner_id=self.owner, received_at=NOW, fault=crash)
        self.assertEqual(self.counts(), before)
        def after(stage):
            if stage == 'after_archive_commit':
                raise RuntimeError('simulated lost response after commit')
        with self.assertRaises(RuntimeError):
            archive_export(Store(self.store.path,self.store.installed,clock=lambda:NOW), self.fixture['raw'], self.root / 'staging', self.authority, owner_id=self.owner, received_at=NOW, fault=after)
        receipt = archive_export(Store(self.store.path,self.store.installed,clock=lambda:NOW), self.fixture['raw'], self.root / 'staging', self.authority, owner_id=self.owner, received_at=NOW)
        self.assertEqual(receipt['cursor'], len(self.fixture['entries']))
        with self.assertRaisesRegex(ValueError, 'ownership'):
            archive_export(self.store, self.fixture['raw'], self.root / 'staging', self.authority, owner_id='doctor-bob', received_at=NOW)

    def test_clinical_subset_imports_signed_report_but_never_admin_authority(self):
        plain = build(self.root / 'plain', hold=False)
        authority = ExportAuthorityV2.model_validate_json(canonical(plain['authority']))
        before = self.counts()
        result = archive_export(self.store, plain['raw'], self.root / 'plain', authority, owner_id=self.owner, received_at=NOW, mode='clinical_observation_import')
        self.assertFalse(result['live_authority_granted'])
        with self.store.transaction() as db:
            imported = [r for r in history(db, 'SYN-02').records if r.record_id in {r.record_id for r in plain['history'].records}]
            self.assertEqual({r.kind for r in imported}, {'patient', 'daily_report'})
            self.assertEqual(next(r for r in imported if r.kind == 'daily_report').diary_sleep_minutes, -25.0)
            self.assertEqual(db.execute("SELECT count(*) FROM events WHERE kind IN ('consent','approval','assignment','hold_transition_bundle')").fetchone()[0], 0)
        self.assertEqual(self.counts()['events'], before['events'] + 2)


if __name__ == '__main__':
    unittest.main()
