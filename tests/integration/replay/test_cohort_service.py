"""Real Store boundaries; hand-authored contract artifacts, never fit evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import sqlite3
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(ROOT/'tests/run_contracts'))
from live_helpers import fresh_store
from contracts.domain.analysis import canonical, sha
from contracts.domain.cohort import make_cohort_input, CohortResult, COHORT_CONFIG_REF
from contracts.domain.boundaries import ObservedHistory
from contracts.runs.common import ExportAuthority, sha256
from contracts.runs.observed import ObservedExport, ReplayBatch, INGESTIBLE
from services.foundation.store import timestamp
from services.foundation.cli import seed
from services.foundation.analysis import (export_cohort, prepare_cohort, claim, AnalysisError, submit as submit_single,
    compare, comparisons, bind_execution, ingest)
from services.foundation.cohort_analysis import submit_receipted, active_overlap, view, comparison, validate_result
from services.foundation.cohort_registration import register, registration
from tests.contracts.test_cohort import database, histories
import fixtures as run_fixtures


def research_fixture(root, fixture_db):
    """Explicit contract_fixture authority, no engine/randomization claim."""
    prepared=run_fixtures.setup(root);value=prepared['export'].model_dump(mode='json')
    value.update(status='complete',cutoff=histories()[0].cutoff.isoformat(),partitions=[])
    for index,h in enumerate(histories()):
        records=[];entries=[];links=[]
        for row in fixture_db.execute('SELECT payload FROM events WHERE patient_id=? ORDER BY available_at,phase,id',(h.patient_id,)):
            record=json.loads(row[0]);raw_record={k:v for k,v in record.items() if k!='source'}
            raw=canonical(raw_record);record['source']['raw_sha256']=sha256(raw.encode())
            records.append(record);admit=record['kind'] in INGESTIBLE
            if admit:entries.append(dict(record=record,raw_source=raw))
            links.append(dict(record_id=record['record_id'],payload_sha256=sha256(canonical(record).encode()),
                source=record['source'],seed_key_sha256=None,import_to_event_store=admit,
                exclusion_reason=None if admit else 'administrative_event_not_live_authority'))
        observed=ObservedHistory.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,
            kind='observed_history',patient_id=h.patient_id,records=records)))
        partition='cohort-partition-'+str(index)
        batch=ReplayBatch.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,
            kind='observed_replay_batch',contract_version='1.0.0',run_id=value['run_id'],partition_id=partition,
            patient_id=h.patient_id,entries=entries)))
        value['partitions'].append(dict(id=partition,unit_id='unit-one',cell_id=value['partitions'][0]['cell_id'] if value['partitions'] else 'S01.reference.n60',
            preset='catalog_cell',cohort_id='cohort-a',replicate=0,patient_id=h.patient_id,
            history=run_fixtures.artifact(root,'h-'+str(index),'observed/'+value['run_id']+'/'+partition+'.json',observed.model_dump(mode='json'),'observed'),
            replay=run_fixtures.artifact(root,'r-'+str(index),'replay/'+value['run_id']+'/'+partition+'.json',batch.model_dump(mode='json'),'replay'),records=links))
    product=ObservedExport.model_validate_json(canonical(value));raw=canonical(product.model_dump(mode='json')).encode()
    authority=prepared['export_authority'].model_dump(mode='json');authority['export_sha256']=sha256(raw)
    return raw,ExportAuthority.model_validate_json(canonical(authority))


class CohortStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.store=fresh_store(self.root/'service.sqlite');seed(self.store)
        self.fixture=database();self.addCleanup(self.fixture.close)
        with self.store.transaction(write=True) as db:
            for row in self.fixture.execute('SELECT * FROM patients'):
                state=json.loads(row['state_json']);state['simulation']['day']=14
                db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',(row['id'],'alice',row['id'],3,1,1,1,canonical(state),None,row['cutoff']))
            for row in self.fixture.execute('SELECT * FROM events'):
                value=json.loads(row['payload']);encoded=canonical(value)
                db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(row['id'],row['patient_id'],value['kind'],
                    value['lineage_id'],value['revision'],value['supersedes'],encoded,'0'*64,encoded.encode(),'0'*64,
                    value['event_at'],value['recorded_at'],value['available_at'],3,timestamp(self.store.clock())))
        self.versions={h.patient_id:3 for h in histories()};self.cutoff=histories()[0].cutoff.isoformat()

    def owned(self,db):return export_cohort(db,'alice',self.versions,self.cutoff,cohort_id='cohort-a')

    def insert_attempt(self,db,product,status='queued'):
        value=product.model_dump(mode='json');anchor=min(self.versions);job=product.attempt_id
        db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(job,anchor,status,'CONTRACT BOUNDARY ONLY'))
        db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (job,anchor,'alice',canonical(value),sha(value),product.cohort_sha256,self.cutoff,canonical(product.request.configuration.model_dump()),canonical(sorted(self.versions)),status,'queued' if status=='queued' else 'failed',timestamp(self.store.clock())))
        return db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone()

    def test_owned_manifest_and_failclosed_submission_claim_rollback(self):
        with self.store.transaction() as db:cohort=self.owned(db)
        payload=dict(cohort_id='cohort-a',patient_versions=self.versions,cutoff=self.cutoff,approved_manifest_sha256=cohort.manifest_sha256)
        current=dict(account_id='alice',token_hash='BOUNDARY-NOT-A-SESSION')
        with self.assertRaisesRegex(ValueError,'qualification'):
            with self.store.transaction(write=True) as db:submit_receipted(db,current,'one',payload,now=self.store.clock())
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM analysis_attempts').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM receipts WHERE key=?',('one',)).fetchone()[0],0)
        with self.store.transaction(write=True) as db:self.insert_attempt(db,make_cohort_input(cohort,'boundary-queued'))
        with self.assertRaisesRegex(ValueError,'qualification'):claim(self.store)
        with self.store.transaction() as db:
            row=db.execute('SELECT * FROM analysis_attempts').fetchone()
            self.assertEqual(row['status'],'queued');self.assertIsNone(row['claim_token'])
            self.assertEqual(active_overlap(db,['COHORT-11']),'boundary-queued')
            value=view(row,self.cutoff);self.assertEqual(len(value['patient_ids']),12)
            self.assertEqual(value['manifest_sha256'],cohort.manifest_sha256)

    def test_research_requires_trusted_artifact_membership_and_owner(self):
        artifact_root=self.root/'producer';artifact_root.mkdir()
        raw,authority=research_fixture(artifact_root,self.fixture)
        with self.assertRaisesRegex(ValueError,'Interactive'):
            register(self.store,'alice',raw,artifact_root,authority,cohort_id='cohort-a',patient_versions=self.versions)
        with self.store.transaction(write=True) as db:
            for p in self.versions:db.execute('UPDATE patients SET state_json=? WHERE id=?',('{}',p))
        bad=authority.model_dump(mode='json');bad['export_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'untrusted'):
            register(self.store,'alice',raw,artifact_root,ExportAuthority.model_validate_json(canonical(bad)),cohort_id='cohort-a',patient_versions=self.versions)
        # Fault after earlier membership rows were inserted: the actual Store
        # transaction must roll back the anchor and every link together.
        with self.store.transaction(write=True) as db:
            db.execute("CREATE TRIGGER cohort_fault BEFORE INSERT ON state_changes WHEN NEW.patient_id='COHORT-11' AND NEW.id LIKE 'cohort-run-%' BEGIN SELECT RAISE(ABORT,'cohort-registration-test-fault'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'cohort-registration-test-fault'):
            register(self.store,'alice',raw,artifact_root,authority,cohort_id='cohort-a',patient_versions=self.versions)
        with self.store.transaction(write=True) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM state_changes WHERE id LIKE 'cohort-run-%'").fetchone()[0],0)
            db.execute('DROP TRIGGER cohort_fault')
        first=register(self.store,'alice',raw,artifact_root,authority,cohort_id='cohort-a',patient_versions=self.versions)
        self.assertEqual(first['execution'],'contract_fixture');self.assertFalse(first['executable'])
        self.assertEqual(register(self.store,'alice',raw,artifact_root,authority,cohort_id='cohort-a',patient_versions=self.versions),first)
        with self.store.transaction() as db:
            cohort=export_cohort(db,'alice',self.versions,self.cutoff,cohort_id='cohort-a',research_run_id=authority.run_id)
            self.assertEqual(cohort.manifest.scope,'research')
            from contracts.domain.cohort import require_executable
            with self.assertRaisesRegex(ValueError,'contract fixture'):
                require_executable(make_cohort_input(cohort,'never-executable'))
            with self.assertRaises(ValueError):registration(db,'bob',authority.run_id,'cohort-a',self.cutoff)
            with self.assertRaises(AnalysisError):export_cohort(db,'alice',self.versions,self.cutoff,cohort_id='cohort-a',research_run_id='caller-string')
        with self.store.transaction(write=True) as db:db.execute('UPDATE patients SET version=version+1 WHERE id=?',('COHORT-11',))
        with self.store.transaction() as db:
            with self.assertRaisesRegex(AnalysisError,'changed'):
                export_cohort(db,'alice',self.versions,self.cutoff,cohort_id='cohort-a',research_run_id=authority.run_id)

    def test_atomic_receipt_rollback_retry_and_nonanchor_overlap_core_only(self):
        """Stub ONLY closed qualification for CORE storage, never run a worker.

        Actual production admission/claim rejection is checked separately above.
        This is not a qualified queue, posterior or accepted-result fixture.
        """
        with self.store.transaction() as db:cohort=self.owned(db)
        payload=dict(cohort_id='cohort-a',patient_versions=self.versions,cutoff=self.cutoff,
            approved_manifest_sha256=cohort.manifest_sha256)
        current=dict(account_id='alice',token_hash='BOUNDARY-NOT-A-SESSION')
        with self.store.transaction(write=True) as db:
            db.execute("CREATE TRIGGER receipt_fault BEFORE INSERT ON receipts WHEN NEW.key='fault' BEGIN SELECT RAISE(ABORT,'receipt-test-fault'); END")
        with patch('services.foundation.cohort_analysis.require_executable'):
            with self.assertRaisesRegex(sqlite3.IntegrityError,'receipt-test-fault'):
                with self.store.transaction(write=True) as db:submit_receipted(db,current,'fault',payload,now=self.store.clock())
            with self.store.transaction(write=True) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM analysis_attempts').fetchone()[0],0)
                db.execute('DROP TRIGGER receipt_fault')
                first=submit_receipted(db,current,'one',payload,now=self.store.clock())
            with self.store.transaction(write=True) as db:
                self.assertEqual(submit_receipted(db,current,'one',payload,now=self.store.clock()),first)
                with self.assertRaisesRegex(AnalysisError,'different content'):
                    submit_receipted(db,current,'one',dict(payload,source_bundle_id='source-7c97862d'),now=self.store.clock())
                patient=db.execute('SELECT * FROM patients WHERE id=?',('COHORT-11',)).fetchone()
                with self.assertRaisesRegex(AnalysisError,'already pending'):
                    submit_single(db,patient,'alice',3,None,self.store.clock())
            with self.store.transaction(write=True) as db:
                db.execute("UPDATE analysis_attempts SET status='failed',stage='failed' WHERE job_id=?",(first['id'],))
                db.execute("UPDATE pending_work SET status='failed' WHERE id=?",(first['id'],))
                retry=submit_receipted(db,current,'retry',dict(payload,previous_attempt=first['id']),now=self.store.clock())
                self.assertEqual(retry['previous_attempt'],first['id']);self.assertNotEqual(retry['id'],first['id'])
        with self.assertRaisesRegex(ValueError,'qualification'):claim(self.store)

    def test_concurrent_core_submissions_serialize_whole_member_set(self):
        """Qualification stub is test-local; no production bypass or fit."""
        barrier=threading.Barrier(2);results=[];errors=[]
        with self.store.transaction() as db:cohort=self.owned(db)
        payload=dict(cohort_id='cohort-a',patient_versions=self.versions,cutoff=self.cutoff,
            approved_manifest_sha256=cohort.manifest_sha256)
        def submitter(key):
            try:
                barrier.wait()
                with self.store.transaction(write=True) as db:
                    results.append(submit_receipted(db,dict(account_id='alice',token_hash='BOUNDARY'),key,payload,now=self.store.clock()))
            except Exception as error:errors.append(error)
        with patch('services.foundation.cohort_analysis.require_executable'):
            threads=[threading.Thread(target=submitter,args=(key,)) for key in ('concurrent-a','concurrent-b')]
            for thread in threads:thread.start()
            for thread in threads:thread.join(10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(results),1);self.assertEqual(len(errors),1)
        self.assertIsInstance(errors[0],AnalysisError);self.assertIn('one or more cohort members',str(errors[0]))
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM analysis_attempts').fetchone()[0],1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM receipts WHERE key LIKE 'concurrent-%'").fetchone()[0],1)

    def test_failed_result_identity_and_immutable_whole_cohort_comparison(self):
        """Failure envelopes only: no fabricated posterior or accepted interval."""
        from services.foundation.analysis_sources import load_source
        with self.store.transaction(write=True) as db:
            cohort=self.owned(db);source=load_source('source-7c97862d',cohort.manifest.cutoff)
            products=[make_cohort_input(cohort,'boundary-v0'),make_cohort_input(cohort,'boundary-v1',source)]
            for product in products:
                row=self.insert_attempt(db,product)
                value=dict(schema_version='3.0.0',synthetic=True,kind='poc_visit_cohort_result',
                    attempt_id=product.attempt_id,input_sha256=sha(product.model_dump(mode='json')),
                    cohort_sha256=product.cohort_sha256,manifest=cohort.manifest.model_dump(mode='json'),
                    manifest_sha256=cohort.manifest_sha256,source_set_sha256=product.source_set_sha256,
                    configuration=product.request.configuration.model_dump(),estimand=product.request.context.estimand.model_dump(),
                    status='failed',reason='CONTRACT-BOUNDARY-UNQUALIFIED-NO-FIT',diagnostics={},artifacts=[],limitations=['No fit ran.'],
                    patients=[dict(patient_id=m.patient_id,history_sha256=m.history_sha256,status='failed',
                        reason='CONTRACT-BOUNDARY-UNQUALIFIED-NO-FIT',effect=None,diagnostics={}) for m in cohort.manifest.members])
                result=CohortResult.model_validate_json(canonical(value));validate_result(result,row,set())
                wrong=copy.deepcopy(value);wrong['input_sha256']='0'*64
                with self.assertRaisesRegex(AnalysisError,'Frozen cohort'):
                    validate_result(CohortResult.model_validate_json(canonical(wrong)),row,set())
                db.execute("UPDATE analysis_attempts SET status='failed',stage='failed',result_json=? WHERE job_id=?",(result.model_dump_json(),product.attempt_id))
                db.execute("UPDATE pending_work SET status='failed' WHERE id=?",(product.attempt_id,))
            public=compare(db,min(self.versions),'alice',products[0].attempt_id,products[1].attempt_id,self.root/'artifacts')
            self.assertEqual(public['kind'],'poc_cohort_v0_v1_comparison')
            self.assertEqual(len(public['attempts'][0]['patients']),12)
            self.assertTrue(all(p['effect'] is None for a in public['attempts'] for p in a['patients']))
            self.assertNotEqual(public['attempts'][0]['fit_seed'],public['attempts'][1]['fit_seed'])
            with self.assertRaises(AnalysisError):compare(db,min(self.versions),'bob',products[0].attempt_id,products[1].attempt_id,self.root/'artifacts')
        self.assertEqual(comparisons(self.root/'artifacts','alice',min(self.versions)),[public])

    def test_host_binding_worker_and_ingest_remain_closed_without_compilation(self):
        """Real entry points reject before building a model or accepting output."""
        with self.store.transaction(write=True) as db:
            product=make_cohort_input(self.owned(db),'boundary-never-executable')
            self.insert_attempt(db,product)
            db.execute("UPDATE analysis_attempts SET status='running',stage='preparing',claim_token='BOUNDARY-ONLY' WHERE job_id=?",(product.attempt_id,))
        origin=dict(learner_image='sha256:'+'1'*64,source_commit='2'*40)
        with self.assertRaisesRegex(ValueError,'qualification'):
            bind_execution(self.store,product.attempt_id,'BOUNDARY-ONLY',origin)
        source=self.root/'input.json';source.write_text(product.model_dump_json())
        from services.learner.analysis_worker import run
        with patch('methods.visit.cohort_model.build_cohort',side_effect=AssertionError('No model may be built')):
            with self.assertRaisesRegex(ValueError,'qualification'):run(source,self.root/'worker-output')
        output=self.root/'failed-output';output.mkdir()
        value=dict(schema_version='3.0.0',synthetic=True,kind='poc_visit_cohort_result',attempt_id=product.attempt_id,
            input_sha256=sha(product.model_dump(mode='json')),cohort_sha256=product.cohort_sha256,
            manifest=product.cohort.manifest.model_dump(mode='json'),manifest_sha256=product.cohort.manifest_sha256,
            source_set_sha256=None,configuration=product.request.configuration.model_dump(),estimand=product.request.context.estimand.model_dump(),
            status='failed',reason='NO-FIT-BOUNDARY-CONTROL',diagnostics={},artifacts=[],limitations=['No fit ran.'],
            patients=[dict(patient_id=m.patient_id,history_sha256=m.history_sha256,status='failed',reason='NO-FIT-BOUNDARY-CONTROL',
                effect=None,diagnostics={}) for m in product.cohort.manifest.members])
        (output/'result.json').write_text(CohortResult.model_validate_json(canonical(value)).model_dump_json())
        with self.assertRaisesRegex(ValueError,'qualification'):
            ingest(self.store,product.attempt_id,'BOUNDARY-ONLY',output)
        with self.store.transaction() as db:
            row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(product.attempt_id,)).fetchone()
            self.assertEqual(row['progress_json'],'{}');self.assertIsNone(row['result_json'])
            self.assertEqual(row['status'],'running')


if __name__=='__main__':unittest.main()
