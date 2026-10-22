"""Real ingestion transaction tail with controlled validation time, no fit/DB job."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock,patch

from services.foundation import analysis


class CompletionDeadlineControls(unittest.TestCase):
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
