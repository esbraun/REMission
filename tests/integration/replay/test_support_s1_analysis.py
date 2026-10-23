"""Disposable scalar SQLite/TestClient seams; never genuine P2 admission.

The archive preparation seam is explicitly injected. These tests accept no
producer authority and perform no worker execution or statistical computation.
Linux Store/admission and genuine data remain separate required verification.
"""
from contextlib import contextmanager
import copy
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:
    TestClient=None
from contracts.domain.analysis import canonical,sha
from contracts.domain.support_s1 import S1Input,CONFIG_REF,execution_binding
if TestClient is not None:
    from services.foundation.app import Settings,create_app,HASHER
from services.foundation.store import digest,timestamp
from services.foundation import support_analysis as support
from services.foundation.analysis import claim,bind_execution,ingest,export_queued_request,AnalysisError
from services.foundation.appointment import checked_result
from support_s1_fixtures import product,abstention,HOST,WALL

URL='http://127.0.0.1:8765'


class ScalarSQLite:
    """Explicit test-only transaction adapter; not production Store emulation."""
    def __init__(self,path):
        self.path=path;self.clock=lambda:WALL;self.gate=SimpleNamespace(timeout=5)
        with self.transaction(write=True) as db:
            for name in ('001_foundation.sql','002_observed_archive.sql','005_analysis.sql'):
                db.executescript(Path('services/foundation/migrations',name).read_text())

    @contextmanager
    def transaction(self,write=False,before_commit=None,**kwargs):
        db=sqlite3.connect(self.path,isolation_level=None);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON');db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        try:
            yield db
            if before_commit:before_commit(db)
            db.commit()
        except BaseException:db.rollback();raise
        finally:db.close()


@unittest.skipUnless(TestClient is not None,'FastAPI unavailable in scalar host; pinned isolated authenticated checks pending')
class SupportS1Service(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=ScalarSQLite(self.root/'disposable.sqlite');self.p=product()
        with self.store.transaction(write=True) as db:
            for owner in ('alice','bob'):
                db.execute('INSERT INTO accounts VALUES(?,?,?,?,?)',(owner,owner,owner,HASHER.hash('StructuralPassword!'),1))
            for m in self.p.cohort:
                db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',(m.patient_id,'alice','Structural historical member',1,1,1,1,'{}',None,'2026-03-26T12:00:00+00:00'))
            db.execute('INSERT INTO observed_archives VALUES(?,?,?,?,?,?,?,?,?)',
                (self.p.archive.archive_id,'alice','d'*64,b'{}','restricted_support_historical',timestamp(WALL),0,0,'{}'))
        self.original_prepare=support.prepare
        self.preparer=patch.object(support,'prepare',side_effect=self.prepared);self.preparer.start()
        with patch('services.foundation.app.Store',return_value=self.store):
            self.app=create_app(Settings(self.store.path,None,clock=lambda:WALL))
        self.client=TestClient(self.app,base_url=URL);self.login(self.client)

    def tearDown(self):self.client.close();self.preparer.stop();self.temp.cleanup()

    def prepared(self,db,owner,submission,configured,*,attempt_id):
        # One explicit structural seam, never a fabricated accepted producer.
        if owner!='alice' or submission['archive_id']!=self.p.archive.archive_id:
            raise ValueError('structural fixture ownership/archive mismatch')
        value=self.p.model_dump(mode='json');value['attempt_id']=attempt_id
        return S1Input.model_validate_json(canonical(value))

    def login(self,client,owner='alice'):
        pre=client.get('/api/session').json()
        response=client.post('/api/login',json=dict(username=owner,password='StructuralPassword!'),
            headers={'Origin':URL,'X-CSRF-Token':pre['csrf']})
        self.assertEqual(response.status_code,200,response.text)

    def headers(self,key='shape-command'):
        return {'Origin':URL,'X-CSRF-Token':self.client.get('/api/session').json()['csrf'],'Idempotency-Key':key}

    def payload(self):return support.submission_for(self.p)

    def queue(self):
        response=self.client.post('/api/support-s1-analyses',json=self.payload(),headers=self.headers())
        self.assertEqual(response.status_code,202,response.text);return response.json()

    def test_cookie_csrf_and_owned_command_receipt_and_generic_reads(self):
        with TestClient(self.app,base_url=URL) as anonymous:
            self.assertEqual(anonymous.post('/api/support-s1-analyses',json=self.payload()).status_code,401)
        self.assertEqual(self.client.post('/api/support-s1-analyses',json=self.payload()).status_code,403)
        response=self.queue();self.assertFalse(response['stale'])
        self.assertEqual(response,self.queue())
        job=response['id']
        for url in (f'/api/jobs/{job}',f'/api/patients/{self.p.cohort[-1].patient_id}/analyses',
                f'/api/patients/{self.p.cohort[0].patient_id}/analyses/{job}',
                f'/api/support-s1-analyses?archive_id={self.p.archive.archive_id}&cutoff_day=14'):
            read=self.client.get(url);self.assertEqual(read.status_code,200,read.text)
            self.assertIn('support_s1_analysis',read.text);self.assertNotIn('observation_cutoff_changed',read.text)
        with TestClient(self.app,base_url=URL) as foreign:
            self.login(foreign,'bob');self.assertEqual(foreign.get(f'/api/jobs/{job}').status_code,404)
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM analysis_attempts').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM patients WHERE current_decision IS NOT NULL').fetchone()[0],0)
        different=self.payload();different['cutoff_day']=42
        self.assertEqual(self.client.post('/api/support-s1-analyses',json=different,headers=self.headers()).status_code,409)

    def test_rollback_overlap_claim_tokens_exact_export_and_host_binding(self):
        original=self.queue();job=original['id']
        self.assertEqual(self.client.post('/api/support-s1-analyses',json=self.payload(),headers=self.headers('new-command')).status_code,409)
        selection=dict(owner='alice',job=job,key='shape-command',submission=self.payload())
        proof=export_queued_request(self.store,**selection)
        wrong=copy.deepcopy(selection);wrong['submission']['archive_id']='foreign'
        with self.assertRaises(ValueError):export_queued_request(self.store,**wrong)
        with self.assertRaises(ValueError):claim(self.store,expected=dict(selection=selection,export_sha256='0'*64))
        claimed=claim(self.store,expected=dict(selection=selection,export_sha256=sha(proof)))
        self.assertEqual(claimed['attempt_id'],job);self.assertIsNone(claim(self.store))
        binding=bind_execution(self.store,job,claimed['claim_token'],HOST)
        self.assertEqual(binding,bind_execution(self.store,job,claimed['claim_token'],HOST))
        with self.assertRaises(AnalysisError):bind_execution(self.store,job,'stale',HOST)
        with self.assertRaises(AnalysisError):bind_execution(self.store,job,claimed['claim_token'],dict(HOST,source_commit='0'*40))
        # The failed overlap command created neither a receipt nor pending row.
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM pending_work').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM receipts').fetchone()[0],1)

    def test_same_version_history_and_member_version_revalidated_before_claim_and_read(self):
        queued=self.queue()
        for change in ('quality','member-version','owner','run'):
            value=self.p.model_dump(mode='json')
            if change=='quality':
                value['histories'][0]['records'][0]['sleep_quality']=5.
                value['cohort'][0]['history_sha256']=sha(value['histories'][0])
                value['history_sha256']=sha(value['histories'])
            elif change=='member-version':value['cohort'][-1]['patient_version']=2
            elif change=='owner':value['archive']['owner_id']='bob'
            else:value['archive']['run_id']='other-run'
            altered=S1Input.model_validate_json(canonical(value))
            with patch.object(self,'p',altered):
                with self.assertRaises(ValueError):claim(self.store)
                read=self.client.get('/api/jobs/'+queued['id']).json()
                self.assertTrue(read['stale']);self.assertIsNone(read['result'])

    def test_abstained_artifact_ingestion_is_bound_and_never_a_visit_effect(self):
        queued=self.queue();job=queued['id'];claimed=claim(self.store);token=claimed['claim_token']
        bind_execution(self.store,job,token,HOST)
        p=S1Input.model_validate_json(canonical(claimed['input']));result=abstention(p).model_dump(mode='json')
        directory=self.root/'output';directory.mkdir();artifact=canonical(result['diagnostics']).encode()
        (directory/'wcls.json').write_bytes(artifact)
        result['artifacts']=[dict(path='wcls.json',sha256=hashlib.sha256(artifact).hexdigest())]
        (directory/'result.json').write_text(canonical(result))
        with self.assertRaises(AnalysisError):ingest(self.store,job,'stale',directory)
        with self.assertRaises(AnalysisError):ingest(self.store,job,token,directory,accept_before=timestamp(WALL-timedelta(seconds=1)))
        tampered=copy.deepcopy(result);tampered['consumed_record_ids']=tampered['consumed_record_ids'][1:]
        (directory/'result.json').write_text(canonical(tampered))
        with self.assertRaises(ValueError):ingest(self.store,job,token,directory)
        (directory/'result.json').write_text(canonical(result))
        self.assertEqual(ingest(self.store,job,token,directory)['status'],'abstained')
        read=self.client.get('/api/jobs/'+job).json()
        self.assertEqual(read['status'],'abstained');self.assertIsNone(read['result']['output'])
        with self.store.transaction() as db:
            row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone()
            self.assertEqual(checked_result(row),(None,'cohort_support_is_not_an_individual_visit_effect'))
        with self.assertRaises(AnalysisError):ingest(self.store,job,token,directory)

    def test_late_receipt_failure_rolls_back_attempt_pending_and_receipt(self):
        with self.store.transaction(write=True) as db:
            db.execute("CREATE TRIGGER structural_receipt_fault BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT,'structural injected receipt fault'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.queue()
        with self.store.transaction() as db:
            for table in ('receipts','pending_work','analysis_attempts'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0)

    def test_untrusted_real_preparation_seam_rejects_foreign_missing_and_structural_authority(self):
        # Exercise the unmocked negative path; no accepted authority is invented.
        original=self.original_prepare
        with self.store.transaction() as db:
            for owner,archive in [('bob',self.p.archive.archive_id),('alice','absent')]:
                with self.assertRaises(ValueError):original(db,owner,dict(self.payload(),archive_id=archive),{},attempt_id=self.p.attempt_id)
            authority=SimpleNamespace(qualification_scope='structural_fixture')
            with patch.object(support,'authority_for',return_value=authority),self.assertRaisesRegex(ValueError,'accepted_saved'):
                original(db,'alice',self.payload(),{},attempt_id=self.p.attempt_id)


if __name__=='__main__':unittest.main()
