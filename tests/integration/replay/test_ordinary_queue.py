"""Real isolated SQLite attempt/receipt controls; no fit, service or live Store.

Only current public projection is doubled; typed frozen input, receipt selection,
queue cardinality and transaction rollback use production code/schema.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contracts.domain.analysis import canonical, sha
from contracts.domain.cohort import make_cohort_input, CohortSubmission
from services.foundation import analysis
from tests.contracts.test_cohort_qualification import qualified_input


class QueuedRequestControls(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
        self.db.executescript('CREATE TABLE schema_migrations(version INTEGER);'
            'CREATE TABLE pending_work(id TEXT PRIMARY KEY,patient_id TEXT,status TEXT,reason TEXT);'
            'CREATE TABLE receipts(owner_id TEXT,session_id TEXT,key TEXT,scope TEXT,payload_sha256 TEXT,response TEXT);'+
            (Path(__file__).resolve().parents[3]/'services/foundation/migrations/005_analysis.sql').read_text())
        @contextmanager
        def transaction(**kwargs):
            with self.db:yield self.db
        self.store=SimpleNamespace(transaction=transaction,clock=lambda:datetime(2026,10,22,tzinfo=timezone.utc))
        self.product=make_cohort_input(qualified_input().cohort,'analysis-'+'1'*32)
        p=self.product;m=p.cohort.manifest;job=p.attempt_id
        self.db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(job,m.members[0].patient_id,'queued','STRUCTURAL ONLY'))
        self.db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (job,m.members[0].patient_id,m.owner_id,p.model_dump_json(),sha(p.model_dump(mode='json')),p.cohort_sha256,m.cutoff.isoformat(),
             canonical(p.request.configuration.model_dump()),canonical([member.patient_id for member in m.members]),'queued','queued',self.store.clock().isoformat()))
        self.submission=dict(cohort_id=m.cohort_id,patient_versions={v.patient_id:v.patient_version for v in m.members},
            cutoff=m.cutoff.isoformat(),source_bundle_id=None,research_run_id=m.research_run_id,
            approved_manifest_sha256=p.cohort.manifest_sha256,previous_attempt=None)
        self.submission=CohortSubmission.model_validate_json(canonical(self.submission)).model_dump(mode='json')
        self.selection=dict(owner=m.owner_id,job=job,key='same-original-key',submission=self.submission)
        self.db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',(m.owner_id,'PRIVATE-SESSION-HASH',self.selection['key'],
            'cohort-analysis:'+m.cohort_id,sha(self.submission),canonical(dict(id=job,status='queued'))));self.db.commit()
        self.project=patch.object(analysis,'prepare_cohort',return_value=p);self.project.start();self.addCleanup(self.project.stop)

    def test_readonly_export_then_exact_claim_no_secret_export_or_replay(self):
        before=self.db.total_changes
        proof=analysis.export_queued_request(self.store,**self.selection)
        self.assertEqual(self.db.total_changes,before)
        self.assertEqual(proof['input'],self.product.model_dump(mode='json'))
        self.assertNotIn('PRIVATE-SESSION-HASH',canonical(proof));self.assertNotIn('claim_token',canonical(proof))
        expected=dict(selection=self.selection,export_sha256=sha(proof))
        claimed=analysis.claim(self.store,expected=expected)
        self.assertEqual(claimed['attempt_id'],self.product.attempt_id);self.assertEqual(claimed['input'],proof['input'])
        with self.assertRaises(analysis.AnalysisError):analysis.claim(self.store,expected=expected)

    def test_missing_foreign_stale_or_ambiguous_receipt_denied_without_claim(self):
        for column,value in [('key','unknown'),('owner','foreign'),('job','analysis-'+'2'*32)]:
            selection=dict(self.selection,**{column:value})
            with self.subTest(column=column),self.assertRaises(analysis.AnalysisError):analysis.export_queued_request(self.store,**selection)
        changed=copy.deepcopy(self.selection);changed['submission']['approved_manifest_sha256']='f'*64
        with self.assertRaises(analysis.AnalysisError):analysis.export_queued_request(self.store,**changed)
        self.db.execute("INSERT INTO receipts SELECT owner_id,'OTHER-SESSION',key,scope,payload_sha256,response FROM receipts");self.db.commit()
        with self.assertRaisesRegex(analysis.AnalysisError,'ambiguous'):analysis.export_queued_request(self.store,**self.selection)
        self.assertEqual(self.db.execute('SELECT status FROM analysis_attempts').fetchone()[0],'queued')

    def test_changed_export_or_current_projection_denies_atomic_claim(self):
        proof=analysis.export_queued_request(self.store,**self.selection)
        with self.assertRaises(analysis.AnalysisError):analysis.claim(self.store,expected=dict(selection=self.selection,export_sha256='f'*64))
        with patch.object(analysis,'prepare_cohort',return_value=SimpleNamespace(cohort_sha256='f'*64)):
            with self.assertRaisesRegex(analysis.AnalysisError,'Current owned cohort'):analysis.claim(self.store,expected=dict(selection=self.selection,export_sha256=sha(proof)))
        self.assertEqual(self.db.execute('SELECT status,claim_token FROM analysis_attempts').fetchone()[:],('queued',None))

    def test_queue_change_denies_original_claim(self):
        self.db.execute("INSERT INTO pending_work VALUES('foreign','foreign','queued','STRUCTURAL')")
        self.db.execute("INSERT INTO analysis_attempts(job_id,patient_id,owner_id,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) SELECT 'foreign','foreign','foreign',request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,'queued','queued',created_at FROM analysis_attempts")
        self.db.commit()
        with self.assertRaisesRegex(analysis.AnalysisError,'exactly the one'):analysis.export_queued_request(self.store,**self.selection)


if __name__=='__main__':unittest.main()
