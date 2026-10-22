"""Actual auth/CSRF/owned cohort routes; no fit result or executable bypass."""
import unittest
import json
from datetime import timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from services.foundation.app import Settings,create_app
from services.foundation.cli import DEMO_PASSWORDS
from services.foundation.store import canonical,instant
from services.foundation.workflow import state_for
import test_cohort_service as service_cases

URL='http://127.0.0.1:8765'


class CohortRoutes(unittest.TestCase):
    owned=service_cases.CohortStoreTests.owned
    insert_attempt=service_cases.CohortStoreTests.insert_attempt

    def setUp(self):
        service_cases.CohortStoreTests.setUp(self)
        # Export-only contract fixtures omit workflow. Route freshness also
        # verifies the actual current state's supported no-prompt policy.
        with self.store.transaction(write=True) as db:
            for row in db.execute("SELECT id,state_json FROM patients WHERE id LIKE 'COHORT-%'").fetchall():
                state=json.loads(row['state_json']);state['workflow']=state_for('ASSIGN-02')['workflow']
                db.execute('UPDATE patients SET state_json=? WHERE id=?',(canonical(state),row['id']))
        self.app=create_app(Settings(self.store.path,self.store.installed,clock=self.store.clock,live_export_root=self.root/'exports'))
        self.client=TestClient(self.app,base_url=URL);self.addCleanup(self.client.close)
        self.login(self.client,'alice')
        self.selection=dict(cohort_id='cohort-a',patient_versions=self.versions,cutoff=self.cutoff,
            source_bundle_id=None,research_run_id=None)

    def login(self,client,user):
        csrf=client.get('/api/session').json()['csrf']
        response=client.post('/api/login',json=dict(username=user,password=DEMO_PASSWORDS[user]),
            headers={'Origin':URL,'X-CSRF-Token':csrf})
        self.assertEqual(response.status_code,200)

    def headers(self,key='cohort-route'):
        return {'Origin':URL,'X-CSRF-Token':self.client.get('/api/session').json()['csrf'],'Idempotency-Key':key}

    def test_preview_auth_owner_versions_and_real_closed_submission(self):
        self.assertEqual(self.client.post('/api/cohort-analyses/preview',json=self.selection).status_code,403)
        response=self.client.post('/api/cohort-analyses/preview',json=self.selection,headers=self.headers())
        self.assertEqual(response.status_code,200,response.text)
        preview=response.json();self.assertFalse(preview['executable']);self.assertEqual(len(preview['manifest']['members']),12)
        payload=dict(self.selection,approved_manifest_sha256=preview['manifest_sha256'])
        closed=self.client.post('/api/cohort-analyses',json=payload,headers=self.headers())
        self.assertEqual(closed.status_code,409);self.assertIn('qualification',closed.json()['detail'])
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM analysis_attempts').fetchone()[0],0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM receipts WHERE scope LIKE 'cohort-analysis:%'").fetchone()[0],0)
        bob=TestClient(self.app,base_url=URL);self.addCleanup(bob.close);self.login(bob,'bob')
        csrf=bob.get('/api/session').json()['csrf']
        self.assertEqual(bob.post('/api/cohort-analyses/preview',json=self.selection,
            headers={'Origin':URL,'X-CSRF-Token':csrf}).status_code,404)
        with self.store.transaction(write=True) as db:db.execute("UPDATE patients SET version=4 WHERE id='COHORT-11'")
        stale=self.client.post('/api/cohort-analyses/preview',json=self.selection,headers=self.headers('stale'))
        self.assertEqual(stale.status_code,409)

    def test_actual_nonanchor_listing_status_and_whole_member_staleness(self):
        from contracts.domain.cohort import make_cohort_input
        with self.store.transaction(write=True) as db:
            product=make_cohort_input(self.owned(db),'boundary-routes-only')
            self.insert_attempt(db,product,status='failed')
        path='/api/patients/COHORT-07/analyses'
        response=self.client.get(path);self.assertEqual(response.status_code,200,response.text)
        value=response.json()['attempts'][0];self.assertEqual(value['kind'],'cohort_visit_analysis');self.assertFalse(value['stale'])
        self.assertEqual(self.client.get(path+'/'+product.attempt_id).json()['id'],product.attempt_id)
        with self.store.transaction(write=True) as db:
            row=db.execute("SELECT payload FROM events WHERE patient_id='COHORT-11' AND kind='daily_report' ORDER BY available_at LIMIT 1").fetchone()
            original=json.loads(row[0]);record=dict(original)
            record.update(record_id='cohort-same-cutoff-correction',revision=original['revision']+1,
                supersedes=original['record_id'],record_status='corrected',sleep_quality=6.)
            record['available_at']=(instant(self.cutoff)-timedelta(minutes=1)).isoformat()
            record['recorded_at']=record['available_at'];encoded=canonical(record)
            db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (record['record_id'],'COHORT-11',record['kind'],record['lineage_id'],record['revision'],record['supersedes'],
                 encoded,'0'*64,encoded.encode(),'0'*64,record['event_at'],record['recorded_at'],record['available_at'],3,self.store.clock().isoformat()))
        corrected=self.client.get(path+'/'+product.attempt_id).json()
        self.assertTrue(corrected['stale'])
        statuses={m['patient_id']:m['status'] for m in corrected['member_information']}
        self.assertEqual(statuses['COHORT-11'],'dated');self.assertEqual(statuses['COHORT-07'],'current')
        self.assertEqual(corrected['manifest_sha256'],value['manifest_sha256'])
        with self.store.transaction(write=True) as db:db.execute("UPDATE patients SET version=4 WHERE id='COHORT-11'")
        self.assertTrue(self.client.get(path+'/'+product.attempt_id).json()['stale'])
        with self.store.transaction(write=True) as db:db.execute("UPDATE patients SET owner_id='bob' WHERE id='COHORT-11'")
        self.assertEqual(self.client.get(path).status_code,404)

    def test_receipt_replay_and_changed_intent_use_actual_routes_core_only(self):
        """Test-local qualification stub only queues CORE rows, never a learner."""
        preview=self.client.post('/api/cohort-analyses/preview',json=self.selection,headers=self.headers()).json()
        payload=dict(self.selection,approved_manifest_sha256=preview['manifest_sha256'])
        with patch('services.foundation.cohort_analysis.require_executable'):
            first=self.client.post('/api/cohort-analyses',json=payload,headers=self.headers())
            self.assertEqual(first.status_code,202,first.text)
            replay=self.client.post('/api/cohort-analyses',json=payload,headers=self.headers())
            self.assertEqual(first.json(),replay.json())
            changed=dict(payload,previous_attempt='different-intent')
            self.assertEqual(self.client.post('/api/cohort-analyses',json=changed,headers=self.headers()).status_code,409)
            self.assertEqual(self.client.post('/api/cohort-analyses',json=payload,headers=self.headers('overlap')).status_code,409)
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM analysis_attempts').fetchone()[0],1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM receipts WHERE scope LIKE 'cohort-analysis:%'").fetchone()[0],1)


if __name__=='__main__':unittest.main()
