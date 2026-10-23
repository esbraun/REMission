"""Real ingestion transaction tail with controlled validation time, no fit/DB job."""
from contextlib import contextmanager, nullcontext, closing
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock,patch
import sqlite3

from services.foundation import analysis
from services.foundation.store import Store


class CompletionDeadlineControls(unittest.TestCase):
    def test_host_deadline_after_journal_rolls_back_completion_and_receipt(self):
        # Real Store.transaction/SQLite commit path with explicit isolated gate
        # and scientific result doubles; never an admitted service or fit.
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'result.json').write_text('{}')
            database=root/'isolated.sqlite';db=sqlite3.connect(database)
            start=datetime(2026,1,1,tzinfo=timezone.utc);clock=[start+timedelta(seconds=100)]
            db.executescript("CREATE TABLE service_control(singleton INTEGER,last_receipt_at TEXT);"
                "CREATE TABLE analysis_attempts(job_id TEXT,status TEXT,stage TEXT,failure_reason TEXT,result_json TEXT,artifact_root TEXT,finished_at TEXT);"
                "CREATE TABLE pending_work(id TEXT,status TEXT,reason TEXT);")
            db.execute('INSERT INTO service_control VALUES(1,?)',(start.isoformat(),))
            db.execute("INSERT INTO analysis_attempts(job_id,status) VALUES('job','running')")
            db.execute("INSERT INTO pending_work(id,status) VALUES('job','running')");db.commit();db.close()
            store=Store.__new__(Store);store.path=database;store.clock=lambda:clock[0]
            store.gate=SimpleNamespace(hold=nullcontext);store.validate_control=lambda db:dict(last_receipt_at=start.isoformat())
            row=dict(started_at=start.isoformat(),request_json='{}')
            result=SimpleNamespace(kind='poc_visit_cohort_result',status='completed',artifacts=[],reason=None,model_dump_json=lambda:'{}')
            from services.foundation.live_journal import receive
            def journal_then_expire(db,at):
                receive(db,at);clock[0]=start+timedelta(seconds=200)
            with patch.object(analysis,'parse_result',return_value=result),patch.object(analysis,'running',return_value=row), \
                    patch('contracts.domain.cohort.CohortInput.model_validate_json',return_value=object()),patch('contracts.domain.cohort.require_executable'), \
                    patch('services.foundation.cohort_analysis.validate_result'),patch('services.foundation.live_journal.receive',side_effect=journal_then_expire):
                with self.assertRaisesRegex(analysis.AnalysisError,'before commit'):
                    analysis.ingest(store,'job','token',root,accept_before=(start+timedelta(seconds=200)).isoformat())
            with closing(sqlite3.connect(database)) as db:
                self.assertEqual(db.execute('SELECT status,result_json FROM analysis_attempts').fetchone(),('running',None))
                self.assertEqual(db.execute('SELECT last_receipt_at FROM service_control').fetchone()[0],start.isoformat())

    def test_validation_crosses_persisted_claim_deadline_inside_transaction(self):
        for elapsed in (7199,7200,7201):
            with self.subTest(elapsed=elapsed),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'result.json').write_text('{}')
                start=datetime(2026,1,1,tzinfo=timezone.utc);clock=[start+timedelta(seconds=7100)]
                db=Mock();row=dict(started_at=start.isoformat(),request_json='{}')
                @contextmanager
                def transaction(**kwargs):yield db
                store=SimpleNamespace(transaction=transaction,clock=lambda:clock[0])
                result=SimpleNamespace(kind='poc_visit_cohort_result',status='completed',artifacts=[],reason=None,
                    model_dump_json=lambda:'{}')
                def validate(*args):clock[0]=start+timedelta(seconds=elapsed)
                with patch.object(analysis,'parse_result',return_value=result), \
                        patch.object(analysis,'running',return_value=row), \
                        patch('contracts.domain.cohort.CohortInput.model_validate_json',return_value=object()), \
                        patch('contracts.domain.cohort.require_executable'), \
                        patch('services.foundation.cohort_analysis.validate_result',side_effect=validate):
                    if elapsed>=7200:
                        with self.assertRaisesRegex(analysis.AnalysisError,'persisted claim deadline'):
                            analysis.ingest(store,'job','token',root)
                        db.execute.assert_not_called()
                    else:
                        self.assertEqual(analysis.ingest(store,'job','token',root),dict(id='job',status='completed'))
                        self.assertEqual(db.execute.call_count,2)


if __name__=='__main__':unittest.main()
