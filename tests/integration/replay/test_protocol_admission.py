"""Actual P1 dispatch/worker/ingestion vetoes; never executes a model."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'contracts'))
from test_protocol_boundary import product
from contracts.domain.analysis import canonical,sha
from contracts.domain.protocol_request import BOUNDARY_CONFIG_REF
from services.foundation.analysis import claim,ingest
from services.foundation.cli import seed
from live_helpers import fresh_store


class ProtocolAdmissionTests(unittest.TestCase):
    def test_boundary_claim_is_rejected_before_any_claim_or_token_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            store=fresh_store(Path(directory)/'authority.sqlite');seed(store)
            value=product('N1');payload=canonical(value.model_dump(mode='json'))
            with store.transaction(write=True) as db:
                # Explicitly malformed scheduling fixture: normal app endpoints
                # cannot enqueue an unadmitted protocol fit in P1.
                db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(value.attempt_id,'SYN-02','queued','P1 admission negative'))
                db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                    (value.attempt_id,'SYN-02','alice',payload,sha(value.model_dump(mode='json')),value.history_sha256,value.cutoff.isoformat(),canonical(BOUNDARY_CONFIG_REF),canonical(['SYN-02']),'queued','queued','2026-10-21T09:00:00Z'))
            with patch('services.foundation.analysis.secrets.token_hex',side_effect=AssertionError('claim token must not be generated')):
                with self.assertRaisesRegex(ValueError,'not executable'):claim(store)
            with store.transaction() as db:
                row=db.execute('SELECT status,claim_token,started_at,result_json FROM analysis_attempts WHERE job_id=?',(value.attempt_id,)).fetchone()
                self.assertEqual(tuple(row),('queued',None,None,None))

    def test_actual_worker_and_result_ingestion_reject_boundary_fixture(self):
        from services.learner.analysis_worker import run
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);value=product();source=root/'input.json'
            source.write_text(canonical(value.model_dump(mode='json')))
            with patch('services.learner.analysis_worker.pm.sample_prior_predictive',side_effect=AssertionError('no model execution')) as prior:
                with self.assertRaisesRegex(ValueError,'not executable'):run(source,root/'output')
                prior.assert_not_called()
            context=value.request.context
            result=dict(schema_version='2.0.0',synthetic=True,kind='poc_protocol_result',purpose=value.purpose,attempt_id=value.attempt_id,
                input_sha256=sha(value.model_dump(mode='json')),history_sha256=value.history_sha256,cohort=[m.model_dump() for m in value.cohort],
                cutoff=value.cutoff.isoformat(),run=value.run.model_dump(),protocol=context.protocol.model_dump(),configuration=BOUNDARY_CONFIG_REF,
                model=context.model.model_dump(),prior=context.prior.model_dump(),estimand=context.estimand.model_dump(),status='failed',
                reason='Non-executable boundary fixture',consumed_record_ids=[],diagnostics={},artifacts=[],output=None)
            output=root/'result-output';output.mkdir();(output/'result.json').write_text(canonical(result))
            # Veto precedes Store access/artifact admission and works regardless
            # of a caller label. No accepted estimate or marker result exists.
            with self.assertRaisesRegex(ValueError,'not executable'):ingest(None,value.attempt_id,'fixture-not-a-live-token',output)


if __name__=='__main__':unittest.main()
