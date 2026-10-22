"""Appointment envelopes with typed synthetic fixtures, NOT real fit evidence."""
import copy
import json
from datetime import timedelta
import unittest
from unittest.mock import patch

from contracts.domain.analysis import CONFIG_REF, ESTIMAND_REF, canonical
from services.foundation.analysis import claim, fail
from test_analysis import AnalysisRoutesTests, ORIGIN


class AppointmentRoutes(unittest.TestCase):
    setUp = AnalysisRoutesTests.setUp
    tearDown = AnalysisRoutesTests.tearDown
    login = AnalysisRoutesTests.login
    headers = AnalysisRoutesTests.headers
    submit = AnalysisRoutesTests.submit

    def saved_fixture(self, transform=None, *, borrowed=False):
        """Persist envelope-only values, never invoke or claim posterior fitting."""
        self.fixture_count=getattr(self,'fixture_count',0)+1
        response=self.client.post('/api/patients/POC-TEST/analyses',
            json=dict(expected_version=1,previous_attempt=None,mode='borrow' if borrowed else 'v0',
                source_bundle_id='source-7c97862d' if borrowed else None),
            headers=self.headers('envelope-fixture-'+str(self.fixture_count)))
        self.assertEqual(response.status_code,202,response.text);job=response.json()
        result=dict(schema_version='1.0.0',synthetic=True,kind='poc_visit_result',
            attempt_id=job['id'],input_sha256=job['input_sha256'],history_sha256=job['history_sha256'],
            cutoff=job['cutoff'],configuration=copy.deepcopy(job['configuration']),estimand=ESTIMAND_REF,status='completed',reason=None,
            effect=dict(mean=-1.23456789,sd=.5,lower=-2.3,upper=.2,unit='ISI_points',kind='conditional_expected_assignment_contrast'),
            diagnostics=dict(fits=[dict(seed=123,diagnostics=dict(accepted=True))],effect_mcmc=dict(accepted=True),
                integration=dict(status='accepted'),predictive_endpoint=dict(continue_interval=[5.25,24.75],escalate_interval=[4.5,23.125])),
            artifacts=[dict(path='expected-effect.npz',sha256='a'*64)],
            limitations=['HAND AUTHORED ENVELOPE FIXTURE, NOT FIT OR CLINICAL EVIDENCE'])
        progress={}
        if borrowed:
            from contracts.domain.borrowing import parse_input,BRIDGE_REF
            from contracts.domain.borrow_runtime import execution_binding,coordinate_layout,NATIVE_OPTIMIZER
            with self.store.transaction() as db:
                product=parse_input(db.execute('SELECT request_json FROM analysis_attempts WHERE job_id=?',(job['id'],)).fetchone()[0])
            binding=execution_binding(product,dict(learner_image='sha256:'+'a'*64,source_commit='b'*40))
            progress=dict(trusted_launch=binding)
            result.update(schema_version='1.1.0',kind='poc_visit_borrow_result',
                bridge=BRIDGE_REF,source_set_sha256=product.source_set_sha256)
            result['diagnostics'].update(bridge_precision=dict(status='accepted'),
                execution=dict(binding,prior_released_before_posterior=True,native_compilations=[
                    dict(index=1,seconds=.1,coordinate_map=coordinate_layout(product.history),compiled_optimizer=NATIVE_OPTIMIZER,
                        actual_vm=dict(vm_type='pytensor.link.c.cvm.CVM',linker='VMLinker',use_cloop=True,c_thunks=True,callback_empty=True,callback_input_empty=True))]))
            result['artifacts'].extend(dict(path=name,sha256='a'*64) for name in ['bridge-precision.json','bridge-marginals.npz'])
        if transform:transform(result)
        with self.store.transaction(write=True) as db:
            db.execute("UPDATE analysis_attempts SET status='completed',stage='complete',result_json=?,finished_at=?,progress_json=? WHERE job_id=?",
                (canonical(result),self.store.clock().isoformat(),canonical(progress),job['id']))
            db.execute("UPDATE pending_work SET status='completed' WHERE id=?",(job['id'],))
        return job,result

    def test_comparison_receipt_recomputes_freshness_without_rewriting_saved_bytes(self):
        """Typed envelopes only: these are NOT actual fits or runtime qualification."""
        from fastapi.testclient import TestClient
        from services.foundation.app import Settings,create_app
        from test_analysis import URL
        self.client.close()
        self.app=create_app(Settings(self.store.path,self.store.installed,clock=self.store.clock,live_export_root=self.root/'exports'))
        self.client=TestClient(self.app,base_url=URL);self.login(self.client,'alice')
        left,_=self.saved_fixture();right,_=self.saved_fixture(borrowed=True)
        url='/api/patients/POC-TEST/analysis-comparisons';payload=dict(left=left['id'],right=right['id'])
        response=self.client.post(url,json=payload,headers=self.headers('comparison-freshness'))
        self.assertEqual(response.status_code,201,response.text);initial=response.json()
        self.assertEqual(initial['appointment']['status'],'current')
        artifact=next((self.root/'exports/comparisons').rglob('comparison-*.json'));artifact_before=artifact.read_bytes()
        with self.store.transaction(write=True) as db:
            receipt_before=db.execute("SELECT response FROM receipts WHERE key='comparison-freshness'").fetchone()[0]
            original=json.loads(db.execute("SELECT payload FROM events WHERE id='POC-TEST-daily_report-1'").fetchone()[0])
            record=dict(original,record_id='comparison-correction',revision=2,supersedes=original['record_id'],record_status='corrected',sleep_quality=6.)
            record['available_at']=(ORIGIN+timedelta(days=14,minutes=-1)).isoformat();record['recorded_at']=record['available_at'];encoded=canonical(record)
            db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (record['record_id'],'POC-TEST',record['kind'],record['lineage_id'],2,record['supersedes'],encoded,'0'*64,encoded.encode(),'0'*64,
                 record['event_at'],record['recorded_at'],record['available_at'],5,self.store.clock().isoformat()))
        replay=self.client.post(url,json=payload,headers=self.headers('comparison-freshness'))
        self.assertEqual(replay.status_code,200,replay.text);dated=replay.json()
        self.assertEqual(dated['appointment']['status'],'dated')
        self.assertEqual(dated,self.client.get(url).json()['comparisons'][0])
        self.assertEqual({k:v for k,v in initial.items() if k!='appointment'},{k:v for k,v in dated.items() if k!='appointment'})
        self.assertEqual(artifact_before,artifact.read_bytes())
        with self.store.transaction() as db:
            self.assertEqual(receipt_before,db.execute("SELECT response FROM receipts WHERE key='comparison-freshness'").fetchone()[0])

    def get(self,job):
        response=self.client.get('/api/patients/POC-TEST/analyses/'+job['id'])
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def test_exact_stored_pair_publication_and_no_foreground_work(self):
        job,result=self.saved_fixture()
        with patch('services.foundation.analysis.submit',side_effect=AssertionError('GET queued a job')), \
                patch('services.foundation.analysis.claim',side_effect=AssertionError('GET claimed a job')), \
                patch('methods.visit.model.build',side_effect=AssertionError('GET built a model')):
            value=self.get(job)
            listed=self.client.get('/api/patients/POC-TEST/analyses').json()['attempts'][0]
            workspace=self.client.get('/api/patients/POC-TEST')
            self.assertEqual(workspace.status_code,200)
        self.assertEqual(value,listed)
        self.assertFalse(value['stale']);self.assertEqual(value['serving']['status'],'current')
        self.assertEqual(value['result']['effect'],result['effect'])
        self.assertEqual(value['serving']['predictive_endpoint'],dict(continue_interval=[5.25,24.75],escalate_interval=[4.5,23.125]))
        self.assertEqual(value['serving']['published_at'],self.store.clock().isoformat())
        self.assertIsNone(value['serving']['artifact_generated_at'])
        self.assertNotIn('"seed"',canonical(value))
        self.assertNotIn('artifact_root',canonical(value))

    def test_pending_refresh_does_not_gate_ordinary_approval_or_run_fit(self):
        job=self.submit().json()
        workspace=self.client.get('/api/patients/POC-TEST').json();snapshot=workspace['snapshot']
        payload=dict(decision_id=snapshot['record_id'],mode='current',option='behavioral_continue',
            rationale='Explicit synthetic ordinary choice while background analysis is queued',
            follow_up_at=(ORIGIN+timedelta(days=21)).isoformat(),purpose='ordinary_treatment',
            **{key:snapshot[key.removeprefix('expected_')] for key in
                ['expected_patient_version','expected_state_version','expected_consent_version','expected_eligibility_version']})
        with patch('services.foundation.analysis.submit',side_effect=AssertionError('approval submitted fit')), \
                patch('services.foundation.analysis.claim',side_effect=AssertionError('approval claimed fit')), \
                patch('methods.visit.model.build',side_effect=AssertionError('approval built model')):
            response=self.client.post('/api/patients/POC-TEST/approve',json=payload,headers=self.headers('ordinary-approval'))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.get(job)['serving']['status'],'pending')

    def test_same_cutoff_correction_stales_but_future_unavailable_does_not(self):
        job,result=self.saved_fixture()
        with self.store.transaction(write=True) as db:
            row=db.execute("SELECT payload FROM events WHERE id='POC-TEST-daily_report-1'").fetchone()
            original=json.loads(row[0]);record=copy.deepcopy(original)
            record.update(record_id='future-unavailable',lineage_id='future-unavailable',sleep_quality=6.)
            # Not available before the strict cutoff: it must have no influence.
            record['available_at']=job['cutoff'];record['recorded_at']=job['cutoff']
            encoded=canonical(record)
            db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (record['record_id'],'POC-TEST',record['kind'],record['lineage_id'],1,None,
                 encoded,'0'*64,encoded.encode(),'0'*64,record['event_at'],record['recorded_at'],record['available_at'],5,self.store.clock().isoformat()))
        self.assertEqual(self.get(job)['serving']['status'],'current')
        with self.store.transaction(write=True) as db:
            record=copy.deepcopy(original)
            record.update(record_id='same-cutoff-correction',revision=2,supersedes=original['record_id'],
                record_status='corrected',sleep_quality=6.)
            record['available_at']=(ORIGIN+timedelta(days=14,minutes=-1)).isoformat()
            record['recorded_at']=record['available_at'];encoded=canonical(record)
            db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (record['record_id'],'POC-TEST',record['kind'],record['lineage_id'],2,record['supersedes'],
                 encoded,'0'*64,encoded.encode(),'0'*64,record['event_at'],record['recorded_at'],record['available_at'],5,self.store.clock().isoformat()))
        value=self.get(job)
        self.assertTrue(value['stale']);self.assertEqual(value['serving']['status'],'dated')
        self.assertEqual(value['staleness_reason'],'same_cutoff_history_or_lineage_changed')
        self.assertEqual(value['cutoff'],job['cutoff']);self.assertEqual(value['forecast_endpoint_day'],56)
        self.assertEqual(value['result']['effect'],result['effect'])

    def test_later_failed_refresh_preserves_prior_summary_and_forecast(self):
        job,result=self.saved_fixture()
        newer=self.submit('new-refresh').json();work=claim(self.store)
        self.assertEqual(work['attempt_id'],newer['id'])
        fail(self.store,newer['id'],work['claim_token'],'bounded refresh failure at /tmp/private/posterior.nc')
        attempts=self.client.get('/api/patients/POC-TEST/analyses').json()['attempts']
        self.assertEqual(attempts[0]['serving']['status'],'failed')
        self.assertNotIn('/tmp/private',canonical(attempts[0]))
        with self.store.transaction() as db:
            self.assertIn('/tmp/private',db.execute('SELECT failure_reason FROM analysis_attempts WHERE job_id=?',(newer['id'],)).fetchone()[0])
        prior=next(a for a in attempts if a['id']==job['id'])
        self.assertEqual(prior['result']['effect'],result['effect']);self.assertEqual(prior['forecast_endpoint_day'],56)
        self.assertEqual(prior['serving']['status'],'current')

    def test_changed_current_support_policy_cannot_reuse_summary_as_current(self):
        job,result=self.saved_fixture()
        with self.store.transaction(write=True) as db:
            state=json.loads(db.execute("SELECT state_json FROM patients WHERE id='POC-TEST'").fetchone()[0])
            state['workflow']['support_policy']['version']='2.0.0'
            db.execute("UPDATE patients SET state_json=? WHERE id='POC-TEST'",(canonical(state),))
        value=self.get(job)
        self.assertEqual(value['serving']['status'],'dated');self.assertEqual(value['serving']['reason'],'current_history_unsupported')
        self.assertEqual(value['result']['effect'],result['effect'])

    def test_corrupt_summary_hash_config_and_rejected_diagnostics_fail_closed(self):
        variants=[lambda r:r.update(input_sha256='f'*64),
            lambda r:r['configuration'].update(version='99.0.0'),
            lambda r:r['diagnostics']['effect_mcmc'].update(accepted=False),
            lambda r:r['diagnostics'].update(fits=[dict(diagnostics='invalid-diagnostic-shape')]),
            lambda r:r.update(artifacts=[])]
        for index,transform in enumerate(variants):
            with self.subTest(variant=index):
                job,_=self.saved_fixture(transform)
                value=self.get(job)
                self.assertEqual(value['serving']['status'],'unavailable');self.assertIsNone(value['result'])
                self.assertFalse(value['serving']['summary_available'])


if __name__=='__main__':unittest.main()
