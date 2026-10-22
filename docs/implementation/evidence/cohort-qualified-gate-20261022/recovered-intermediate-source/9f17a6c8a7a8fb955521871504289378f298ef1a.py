"""Isolated SQLite binding/ingest controls. No producer, fit or app activation."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from contracts.domain.analysis import canonical, sha
from contracts.domain.cohort import make_cohort_input
from services.foundation import analysis
from tests.contracts.test_cohort_qualification import qualified_input, changed_cohort, failure_result


class QualifiedBindingControls(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
        # Exact attempt schema/immutability triggers, with irrelevant FKs disabled.
        self.db.executescript('CREATE TABLE schema_migrations(version INTEGER);'
            'CREATE TABLE pending_work(id TEXT PRIMARY KEY,patient_id TEXT,status TEXT,reason TEXT);'+
            (Path(__file__).resolve().parents[3]/'services/foundation/migrations/005_analysis.sql').read_text())
        @contextmanager
        def transaction(**kwargs):
            with self.db:yield self.db
        self.store=SimpleNamespace(transaction=transaction,clock=lambda:datetime(2026,10,22,tzinfo=timezone.utc))
        self.origin=dict(learner_image='sha256:'+'1'*64,source_commit='2'*40)
        env=patch.dict(os.environ,dict(REMISSION_COHORT_REVIEWED_LEARNER_IMAGE=self.origin['learner_image'],
            REMISSION_COHORT_REVIEWED_SOURCE_COMMIT=self.origin['source_commit']))
        env.start();self.addCleanup(env.stop)

    def insert(self, product):
        manifest=product.cohort.manifest;job=product.attempt_id;anchor=manifest.members[0].patient_id
        self.db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(job,anchor,'queued','STRUCTURAL-NO-FIT'))
        self.db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (job,anchor,manifest.owner_id,product.model_dump_json(),sha(product.model_dump(mode='json')),product.cohort_sha256,
             manifest.cutoff.isoformat(),canonical(product.request.configuration.model_dump()),
             canonical([m.patient_id for m in manifest.members]),'queued','queued',self.store.clock().isoformat()))
        self.db.commit()

    def test_ordinary_claim_immutable_rebind_progress_and_replay(self):
        product=make_cohort_input(qualified_input().cohort,'analysis-'+uuid.uuid4().hex);self.insert(product)
        claimed=analysis.claim(self.store);job=claimed['attempt_id'];token=claimed['claim_token']
        self.assertEqual(claimed['input'],product.model_dump(mode='json'))
        binding=analysis.bind_execution(self.store,job,token,self.origin)
        self.assertEqual(analysis.bind_execution(self.store,job,token,self.origin),binding)
        for wrong_job,wrong_token in [('other',token),(job,'stale-token')]:
            with self.assertRaises(analysis.AnalysisError):analysis.bind_execution(self.store,wrong_job,wrong_token,self.origin)
        with self.assertRaises(ValueError):analysis.bind_execution(self.store,job,token,dict(self.origin,source_commit='3'*40))
        analysis.progress(self.store,job,token,dict(attempt_id=job,input_sha256=binding['input_sha256'],stage='fitting'))
        row=self.db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone()
        self.assertEqual(json.loads(row['progress_json'])['trusted_launch'],binding)
        with self.assertRaises(analysis.AnalysisError):analysis.progress(self.store,job,token,dict(stage='fitting',trusted_launch={}))
        with patch.dict(os.environ,dict(REMISSION_COHORT_REVIEWED_LEARNER_IMAGE='sha256:'+'4'*64)):
            with self.assertRaises(ValueError):analysis.bind_execution(self.store,job,token,self.origin)
        # A self-consistent learner-forged pair cannot configure the service.
        with self.assertRaises(ValueError):analysis.bind_execution(self.store,job,token,
            dict(learner_image='sha256:'+'4'*64,source_commit='3'*40))
        analysis.fail(self.store,job,token,'STRUCTURAL-NO-FIT')
        second=make_cohort_input(product.cohort,'analysis-'+uuid.uuid4().hex);self.insert(second)
        next_claim=analysis.claim(self.store)
        next_binding=analysis.bind_execution(self.store,second.attempt_id,next_claim['claim_token'],self.origin)
        self.assertNotEqual(binding['input_sha256'],next_binding['input_sha256'])
        self.assertNotEqual(binding['numerical_seeds'],next_binding['numerical_seeds'])
        with self.assertRaises(analysis.AnalysisError):analysis.bind_execution(self.store,job,token,self.origin)

    def test_ingest_qualifies_persisted_original_not_result_envelope(self):
        for qualified in (True,False):
            with self.subTest(qualified=qualified),tempfile.TemporaryDirectory() as directory:
                product=qualified_input() if qualified else changed_cohort(lambda v:v['manifest'].update(research_run_id='other-run'))
                self.insert(product)
                # Test-only running row permits reaching ingest for a denied original.
                self.db.execute("UPDATE analysis_attempts SET status='running',stage='preparing',claim_token='STRUCTURAL' WHERE job_id=?",(product.attempt_id,));self.db.commit()
                result=failure_result(product)
                Path(directory,'result.json').write_text(result.model_dump_json())
                if qualified:
                    self.assertEqual(analysis.ingest(self.store,product.attempt_id,'STRUCTURAL',directory)['status'],'failed')
                else:
                    with self.assertRaisesRegex(ValueError,'qualification'):analysis.ingest(self.store,product.attempt_id,'STRUCTURAL',directory)
                    row=self.db.execute('SELECT result_json,status FROM analysis_attempts WHERE job_id=?',(product.attempt_id,)).fetchone()
                    self.assertIsNone(row['result_json']);self.assertEqual(row['status'],'running')


if __name__=='__main__':unittest.main()
