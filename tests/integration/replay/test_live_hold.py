"""Actual SQLite, cookie/CSRF and service safety workflow acceptance."""
from dataclasses import replace
import copy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import unittest
from fastapi.testclient import TestClient
from services.foundation.app import Settings, create_app
from services.foundation.cli import seed, DEMO_PASSWORDS
from services.foundation.store import Store
from services.foundation.admission import AdmissionError
from live_helpers import fresh_store,live_fixture,ref
from services.foundation.cutover import bundle_for,change_generation
from live_process_helpers import CONTEXT,service_process

NOW=datetime(2026,10,21,12,tzinfo=timezone.utc)
ORIGIN='http://127.0.0.1:8765'


class ActivationTests(unittest.TestCase):
    def test_explicit_activation_normal_start_and_real_login(self):
        with tempfile.TemporaryDirectory() as directory:
            store=fresh_store(Path(directory)/'new.sqlite');seed(store)
            settings=Settings(store.path,store.installed,clock=lambda:NOW)
            with TestClient(create_app(settings),base_url=ORIGIN) as client:
                self.assertEqual(client.get('/health').status_code,200)
                bootstrap=client.get('/api/session').json()
                login=client.post('/api/login',json=dict(username='alice',password=DEMO_PASSWORDS['alice']),
                    headers={'Origin':ORIGIN,'X-CSRF-Token':bootstrap['csrf']})
                self.assertEqual(login.status_code,200,login.text)
                current=client.get('/api/patients/SYN-02')
                self.assertEqual(current.status_code,200,current.text)
                self.assertEqual(current.json()['live_safety_summary']['patient_sequence'],1)
                self.assertTrue(current.json()['permissions']['approve_ordinary'])
            stale=store.installed.model_copy(deep=True)
            stale.control.authority_generation+=1
            with self.assertRaisesRegex(AdmissionError,'service_generation_mismatch'):
                Store(store.path,stale)


class LiveWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.root=Path(self.directory.name)
        fixture,authority,installed,self.command=live_fixture(self.root)
        self.store=fresh_store(self.root/'service.sqlite',installed);seed(self.store)
        self.settings=Settings(self.store.path,installed,clock=lambda:NOW,
            observed_archives={'fixture-export':(fixture['raw'],self.root/'staging',authority)},
            live_export_root=self.root/'exports',source_commit='a'*40,runtime_ref=ref('qualified-test-runtime'))
        self.client=TestClient(create_app(self.settings),base_url=ORIGIN)
        self.login()
        response=self.client.post('/api/observed-archives/fixture-export',json={'mode':'archive_only'},headers=self.headers())
        self.assertEqual(response.status_code,200,response.text)

    def tearDown(self):
        self.client.close();self.directory.cleanup()

    def login(self,client=None,user='alice'):
        client=client or self.client
        bootstrap=client.get('/api/session').json()
        result=client.post('/api/login',json=dict(username=user,password=DEMO_PASSWORDS[user]),headers={'Origin':ORIGIN,'X-CSRF-Token':bootstrap['csrf']})
        self.assertEqual(result.status_code,200,result.text)

    def headers(self,key='test-key',client=None):
        client=client or self.client
        return {'Origin':ORIGIN,'X-CSRF-Token':client.get('/api/session').json()['csrf'],'Idempotency-Key':key}

    def enter(self,key='entry'):
        response=self.client.post('/api/patients/SYN-02/live-holds',json=self.command,headers=self.headers(key))
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def review_input(self,episode):
        workspace=self.client.get('/api/patients/SYN-02').json();s=workspace['snapshot']
        return dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,mode='current',decision_id=s['record_id'],
            expected_patient_version=s['patient_version'],expected_state_version=s['state_version'],expected_consent_version=s['consent_version'],
            expected_eligibility_version=s['eligibility_version'],expected_episode_generation=episode['generation'],trigger_set_sha256=episode['trigger_set_sha256'],
            review_rules=episode['review_rules'],rationale='Explicit synthetic structural assessment; changed facts reviewed',current_assessment_attested=True,
            items=[dict(requirement_id=r['requirement_id'],definition=r['definition'],evidence_refs=episode['trigger_refs'],finding='Synthetic concern and changed facts reviewed',result='satisfied') for r in episode['obligations']])

    def test_independent_entry_is_atomic_and_retry_cross_session(self):
        before=self.client.get('/api/patients/SYN-02').json()
        result=self.enter()
        after=self.client.get('/api/patients/SYN-02').json()
        self.assertEqual(after['snapshot']['patient_version'],before['snapshot']['patient_version']+1)
        self.assertEqual(after['snapshot']['consent_version'],before['snapshot']['consent_version'])
        self.assertEqual(after['snapshot']['workflow']['data_readiness'],'stale')
        self.assertFalse(after['permissions']['approve_ordinary'])
        self.assertEqual(result,self.enter('another-key'))
        self.client.close();self.client=TestClient(create_app(self.settings),base_url=ORIGIN);self.login()
        self.assertEqual(result,self.enter())
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM live_hold_operations').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM live_hold_tasks').fetchone()[0],1)

    def test_owned_review_separate_clearance_returns_assessment_only(self):
        result=self.enter();episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        request=self.review_input(episode)
        response=self.client.post('/api/patients/SYN-02/live-holds/'+result['episode_id']+'/reviews',json=request,headers=self.headers('review'))
        self.assertEqual(response.status_code,200,response.text);review=response.json()
        held=self.client.get('/api/patients/SYN-02').json();self.assertEqual(held['stage'],'ASSIGN-09')
        clear=self.review_input(episode)
        for key in ['items','rationale','current_assessment_attested']:clear.pop(key)
        clear.update(review_id=review['review_id'],review_sha256=review['review_sha256'])
        response=self.client.post('/api/patients/SYN-02/live-holds/'+result['episode_id']+'/clearance',json=clear,headers=self.headers('clear'))
        self.assertEqual(response.status_code,200,response.text)
        current=self.client.get('/api/patients/SYN-02').json()
        self.assertEqual(current['stage'],'ASSIGN-01');self.assertEqual(current['snapshot']['workflow']['support_mode'],'paused')
        self.assertEqual(current['snapshot']['workflow']['data_readiness'],'incomplete');self.assertFalse(current['permissions']['approve_ordinary'])

    def test_actual_service_export_and_new_consumer_strict_equality(self):
        self.enter()
        from contracts.service.live_safety import TrustedLiveSafetyAuthority
        from services.learner.worker import read_live_safety_export,dispatch_product
        for cutoff,status in [('2026-10-21T12:00:00+00:00','not_held'),('2026-10-21T12:00:00.000001+00:00','held')]:
            settings=replace(self.settings,clock=lambda:datetime(2026,10,21,13,tzinfo=timezone.utc))
            with TestClient(create_app(settings),base_url=ORIGIN) as client:
                self.login(client)
                response=client.post('/api/patients/SYN-02/live-safety-exports',json=dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,cutoff=cutoff),headers=self.headers('export-'+status,client))
                self.assertEqual(response.status_code,200,response.text)
            with self.store.transaction() as db:
                row=db.execute('SELECT authority FROM live_export_receipts WHERE key=?',('export-'+status,)).fetchone()
                authority=TrustedLiveSafetyAuthority.model_validate_json(row[0])
            root=self.root/'exports'/response.json()['export_id']
            context=read_live_safety_export(root,authority)
            self.assertEqual(context.independent_hold_status,status)
            with self.assertRaisesRegex(ValueError,'capability'):
                dispatch_product(required_product=('LIVE-SAFETY-EXPORT','1.0.0'),worker_capabilities=[],root=root,authority=authority)

    def safety_state(self):
        with self.store.transaction() as db:
            tables=['observed_archives','observed_archive_entries','observed_archive_artifacts','events','decisions','state_changes',
                'live_hold_operations','live_hold_episodes','live_hold_reviews','live_hold_tasks','live_hold_task_events','live_hold_keys',
                'live_safety_facts','live_projection_receipts','live_hold_additional_tasks','live_hold_task_bindings',
                'live_hold_additional_task_events','service_control','live_authority_history','live_activation_receipts','drafts']
            return {table:[tuple(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY rowid')] for table in tables}|{
                'patient':tuple(db.execute("SELECT * FROM patients WHERE id='SYN-02'").fetchone())}

    def test_real_auth_csrf_foreign_owner_and_exact_reference_denials(self):
        before=self.safety_state();url='/api/patients/SYN-02/live-holds'
        with TestClient(create_app(self.settings),base_url=ORIGIN) as other:
            self.assertEqual(other.post(url,json=self.command,headers=self.headers()).status_code,401)
            self.login(other,'bob')
            self.assertEqual(other.post(url,json=self.command,headers=self.headers('foreign',other)).status_code,404)
        self.assertEqual(self.client.post(url,json=self.command,headers={'Idempotency-Key':'missing-csrf'}).status_code,403)
        bad=self.headers();bad['Origin']='https://foreign.invalid'
        self.assertEqual(self.client.post(url,json=self.command,headers=bad).status_code,403)
        for field,value in [('partition_id','foreign'),('archive_id','foreign')]:
            command=copy.deepcopy(self.command);command[field]=value
            self.assertEqual(self.client.post(url,json=command,headers=self.headers()).status_code,409)
        command=copy.deepcopy(self.command);command['bundle_ref']['payload_sha256']='f'*64
        self.assertEqual(self.client.post(url,json=command,headers=self.headers()).status_code,409)
        self.assertEqual(before,self.safety_state())
        self.enter('same')
        command=copy.deepcopy(self.command);command['trigger_refs']=[]
        self.assertEqual(self.client.post(url,json=command,headers=self.headers('same')).status_code,422)

    def test_precommit_faults_rollback_every_unit_and_response_loss_recovers_once(self):
        before=self.safety_state()
        for point in ['after_hold_episode','after_hold_task_audit','after_hold_version_decision','before_hold_commit']:
            def fault(name):
                if name==point:raise RuntimeError('deliberate '+point)
            with TestClient(create_app(replace(self.settings,fault=fault)),base_url=ORIGIN,raise_server_exceptions=False) as client:
                self.login(client)
                response=client.post('/api/patients/SYN-02/live-holds',json=self.command,headers=self.headers('retry-after-rejection',client))
                self.assertEqual(response.status_code,500,response.text)
            self.assertEqual(before,self.safety_state(),point)
        def loss(name):
            if name=='after_hold_commit':raise RuntimeError('deliberate response loss')
        with TestClient(create_app(replace(self.settings,fault=loss)),base_url=ORIGIN,raise_server_exceptions=False) as client:
            self.login(client)
            response=client.post('/api/patients/SYN-02/live-holds',json=self.command,headers=self.headers('retry-after-rejection',client))
            self.assertEqual(response.status_code,500)
        committed=self.safety_state();self.enter('retry-after-rejection')
        self.assertEqual(committed,self.safety_state())

    def test_generic_state_and_reports_cannot_clear_latch_or_restore_draft(self):
        self.enter()
        for stage in ['ASSIGN-01','ASSIGN-02','ASSIGN-10']:
            workspace=self.client.get('/api/patients/SYN-02').json()
            response=self.client.post('/api/patients/SYN-02/state',json=dict(expected_version=workspace['snapshot']['patient_version'],stage=stage,reason='Attempt ordinary path'),headers=self.headers())
            self.assertEqual(response.status_code,409,response.text)
            self.assertEqual(response.json()['code'],'active_live_hold')
        response=self.client.post('/api/patients/SYN-02/reports',json=dict(event_at='2026-10-21T11:00:00+00:00',sleep_quality=7.0,function=7.0,diary_sleep_minutes=420.0,note=''),headers=self.headers('report'))
        self.assertEqual(response.status_code,200,response.text)
        workspace=self.client.get('/api/patients/SYN-02').json()
        self.assertEqual(workspace['snapshot']['workflow']['data_readiness'],'stale')
        self.assertEqual(workspace['stage'],'ASSIGN-09')
        self.assertFalse(workspace['permissions']['approve_ordinary'])

    def test_current_review_rejects_caller_clock_and_stales_on_context_change(self):
        result=self.enter();episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        request=self.review_input(episode);request['assessed_at']='2026-01-01T08:00:00+00:00'
        response=self.client.post('/api/patients/SYN-02/live-holds/'+result['episode_id']+'/reviews',json=request,headers=self.headers('review'))
        self.assertEqual(response.status_code,422)
        request.pop('assessed_at')
        response=self.client.post('/api/patients/SYN-02/live-holds/'+result['episode_id']+'/reviews',json=request,headers=self.headers('review'))
        self.assertEqual(response.status_code,200,response.text);review=response.json()
        with self.store.transaction() as db:
            saved=__import__('json').loads(db.execute('SELECT payload FROM live_hold_reviews WHERE id=?',(review['review_id'],)).fetchone()[0])
            self.assertEqual(saved['current_review_at'],'2026-10-21T12:00:00+00:00')
            self.assertEqual(saved['proofs'][0]['verified_visible_at'],saved['current_review_at'])
        clear=self.review_input(episode)
        for k in ['items','rationale','current_assessment_attested']:clear.pop(k)
        clear.update(review_id=review['review_id'],review_sha256=review['review_sha256'])
        self.client.post('/api/patients/SYN-02/reports',json=dict(event_at='2026-10-21T11:00:00+00:00',sleep_quality=7.0,function=7.0,diary_sleep_minutes=420.0,note=''),headers=self.headers('change'))
        response=self.client.post('/api/patients/SYN-02/live-holds/'+result['episode_id']+'/clearance',json=clear,headers=self.headers('clear'))
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(self.client.get('/api/patients/SYN-02').json()['stage'],'ASSIGN-09')

    def test_whole_archive_coordinator_atomic_aggregate_and_retry(self):
        before=self.client.get('/api/patients/SYN-02').json()['snapshot']
        response=self.client.post('/api/observed-archives/fixture-export',json={'mode':'clinical_observation_import'},headers=self.headers('project'))
        self.assertEqual(response.status_code,200,response.text);receipt=response.json()
        row=receipt['patients']['SYN-02'];total=row['clinical_insertions']+row['novel_hold_transitions']
        self.assertEqual(row['after_versions']['version'],before['patient_version']+total)
        self.assertEqual(row['after_versions']['consent_version'],before['consent_version'])
        self.assertEqual(self.client.get('/api/patients/SYN-02').json()['stage'],'ASSIGN-09')
        state=self.safety_state()
        retry=self.client.post('/api/observed-archives/fixture-export',json={'mode':'clinical_observation_import'},headers=self.headers('project'))
        self.assertEqual(retry.status_code,200,retry.text);self.assertEqual(receipt,retry.json());self.assertEqual(state,self.safety_state())

    def http_login(self,client):
        response=client.get('/api/session');self.assertEqual(response.status_code,200,response.text)
        response=client.post('/api/login',json=dict(username='alice',password=DEMO_PASSWORDS['alice']),headers={'Origin':ORIGIN,'X-CSRF-Token':response.json()['csrf']})
        self.assertEqual(response.status_code,200,response.text)
        return {'Origin':ORIGIN,'X-CSRF-Token':response.json()['csrf']}

    def approval_request(self):
        s=self.client.get('/api/patients/SYN-02').json()['snapshot']
        return dict(decision_id=s['record_id'],expected_patient_version=s['patient_version'],expected_state_version=s['state_version'],
            expected_consent_version=s['consent_version'],expected_eligibility_version=s['eligibility_version'],mode='current',option='usual_care',
            rationale='Explicit ordinary synthetic choice',follow_up_at='2026-10-22T12:00:00+00:00',purpose='ordinary_treatment')

    def test_LH13_real_two_process_received_writer_blocked_gate_prevents_ready_or_approval(self):
        import httpx
        admitted=CONTEXT.Event()
        def boundary(point):
            if point=='after_hold_admission':admitted.set()
        first=replace(self.settings,fault=boundary);second=replace(self.settings,admission_timeout=.25)
        approval=self.approval_request()
        with service_process(first) as (url_a,_),service_process(second) as (url_b,_),httpx.Client(base_url=url_a,timeout=15) as a,httpx.Client(base_url=url_b,timeout=15) as b:
            headers_a=self.http_login(a);headers_b=self.http_login(b)
            headers_a['Idempotency-Key']='process-entry';headers_b['Idempotency-Key']='process-approval'
            writer=sqlite3.connect(self.store.path,isolation_level=None);writer.execute('BEGIN IMMEDIATE')
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future=executor.submit(a.post,'/api/patients/SYN-02/live-holds',json=self.command,headers=headers_a)
                    self.assertTrue(admitted.wait(10),'hold never crossed authenticated R barrier')
                    current=b.get('/api/patients/SYN-02');self.assertEqual(current.status_code,503,current.text)
                    self.assertEqual(current.json()['code'],'safety_admission_busy')
                    response=b.post('/api/patients/SYN-02/approve',json=approval,headers=headers_b)
                    self.assertEqual(response.status_code,503,response.text)
                    self.assertEqual(writer.execute('SELECT count(*) FROM live_hold_operations').fetchone()[0],0)
                    writer.rollback()
                    held=future.result(15);self.assertEqual(held.status_code,200,held.text)
                    response=b.post('/api/patients/SYN-02/approve',json=approval,headers=headers_b)
                    self.assertEqual(response.status_code,409,response.text)
            finally:
                writer.rollback();writer.close()
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM bundles').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM live_hold_operations').fetchone()[0],1)

    def test_actual_process_death_precommit_and_aftercommit_release_os_gate(self):
        import httpx
        for point,expected in [('after_hold_episode',0),('after_hold_commit',1)]:
            def crash(name):
                if name==point:os._exit(77)
            with service_process(replace(self.settings,fault=crash)) as (url,process),httpx.Client(base_url=url,timeout=15) as client:
                headers=self.http_login(client);headers['Idempotency-Key']='crash-entry'
                with self.assertRaises(httpx.RemoteProtocolError):
                    client.post('/api/patients/SYN-02/live-holds',json=self.command,headers=headers)
                process.join(10);self.assertEqual(process.exitcode,77)
            with self.store.transaction() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM live_hold_operations').fetchone()[0],expected)
                self.assertEqual(db.execute('SELECT count(*) FROM live_hold_tasks').fetchone()[0],expected)
        result=self.enter('crash-entry')
        self.assertEqual(result['live_received_at'],'2026-10-21T12:00:00+00:00')

    def test_missing_archive_then_same_key_succeeds_after_exact_dependencies_commit(self):
        fixture,archive_authority,addition,command=live_fixture(self.root/'pending',run_name='pending-live-run')
        authority=self.settings.installed.authority.model_copy(update={'grants':self.settings.installed.authority.grants+addition.authority.grants})
        self.install_next(authority)
        self.settings=replace(self.settings,observed_archives={**self.settings.observed_archives,'pending':(fixture['raw'],self.root/'pending/staging',archive_authority)})
        self.restart_client();before=self.safety_state();headers=self.headers('exact-after-rejection')
        response=self.client.post('/api/patients/SYN-02/live-holds',json=command,headers=headers)
        self.assertEqual(response.status_code,409,response.text);self.assertEqual(response.json()['code'],'hold_dependencies_unavailable')
        self.assertEqual(before,self.safety_state())
        response=self.client.post('/api/observed-archives/pending',json={'mode':'archive_only'},headers=self.headers())
        self.assertEqual(response.status_code,200,response.text)
        response=self.client.post('/api/patients/SYN-02/live-holds',json=command,headers=headers)
        self.assertEqual(response.status_code,200,response.text)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM live_hold_keys WHERE key='exact-after-rejection'").fetchone()[0],1)

    def allow_event_review(self):
        installed=self.settings.installed;authority=installed.authority.model_copy(deep=True);rules=installed.review_rules.model_copy(deep=True)
        for requirement in [*authority.grants[0].trigger_bindings[0].required_reviews,*rules.rules[0].requirements]:
            requirement.evidence_kinds.append('daily_report');requirement.source_ids.append('foundation-synthetic')
        self.install_next(authority,rules);self.restart_client()

    def test_review_missing_stale_future_and_equal_committed_event_proofs(self):
        from test_foundation import observed
        from services.foundation.replay import append_event,parse_observed
        from services.foundation.store import canonical,digest
        self.allow_event_review();entry=self.enter();episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        url='/api/patients/SYN-02/live-holds/'+entry['episode_id']+'/reviews'
        for name,reference,code in [('missing',dict(store='event',namespace_id='SYN-02',partition_id=None,record_id='missing-record',payload_sha256='f'*64),'hold_dependencies_unavailable'),
                ('stale',{**episode['trigger_refs'][0],'payload_sha256':'f'*64},'hold_evidence_stale')]:
            request=self.review_input(episode);request['items'][0]['evidence_refs']=[reference]
            response=self.client.post(url,json=request,headers=self.headers(name))
            self.assertEqual(response.status_code,409,response.text);self.assertEqual(response.json()['code'],code)
        future='2026-10-21T12:00:00.000001+00:00'
        item=observed(identifier='future-review-evidence',available=future)
        record=parse_observed(canonical(item['record']).encode())
        self.store.clock=lambda:NOW
        with self.store.transaction(write=True) as db:append_event(db,record,item['raw_source'].encode(),received_at=NOW)
        reference=dict(store='event',namespace_id='SYN-02',partition_id=None,record_id=record.record_id,payload_sha256=digest(canonical(record.model_dump(mode='json'))))
        request=self.review_input(episode);request['items'][0]['evidence_refs']=[reference]
        headers=self.headers('future-then-equal')
        response=self.client.post(url,json=request,headers=headers)
        self.assertEqual(response.status_code,422,response.text);self.assertEqual(response.json()['code'],'future_hold_evidence')
        self.settings=replace(self.settings,clock=lambda:datetime.fromisoformat(future));self.restart_client()
        response=self.client.post(url,json=request,headers=self.headers('future-then-equal'))
        self.assertEqual(response.status_code,200,response.text)
        with self.store.transaction() as db:
            saved=__import__('json').loads(db.execute('SELECT payload FROM live_hold_reviews WHERE id=?',(response.json()['review_id'],)).fetchone()[0])
            self.assertEqual(saved['current_review_at'],future);self.assertEqual(saved['proofs'][0]['verified_visible_at'],future)

    def test_uncommitted_event_is_not_review_evidence_then_same_key_can_retry(self):
        from test_foundation import observed
        from services.foundation.replay import append_event,parse_observed
        from services.foundation.store import canonical,digest
        self.allow_event_review();entry=self.enter();episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        item=observed(identifier='uncommitted-review-evidence',available=NOW.isoformat());record=parse_observed(canonical(item['record']).encode())
        reference=dict(store='event',namespace_id='SYN-02',partition_id=None,record_id=record.record_id,payload_sha256=digest(canonical(record.model_dump(mode='json'))))
        request=self.review_input(episode);request['items'][0]['evidence_refs']=[reference]
        headers=self.headers('uncommitted-then-committed');url='/api/patients/SYN-02/live-holds/'+entry['episode_id']+'/reviews'
        writer=self.store.connect();writer.execute('BEGIN IMMEDIATE')
        try:
            append_event(writer,record,item['raw_source'].encode(),received_at=NOW)
            response=self.client.post(url,json=request,headers=headers)
            self.assertEqual(response.status_code,409,response.text);self.assertEqual(response.json()['code'],'hold_dependencies_unavailable')
        finally:writer.rollback();writer.close()
        self.store.clock=lambda:NOW
        with self.store.transaction(write=True) as db:append_event(db,record,item['raw_source'].encode(),received_at=NOW)
        response=self.client.post(url,json=request,headers=headers)
        self.assertEqual(response.status_code,200,response.text)

    def test_reverse_equal_clock_two_process_approval_commits_then_hold_preserves_history(self):
        import httpx
        approval_inside=CONTEXT.Event();allow_approval=CONTEXT.Event();hold_received=CONTEXT.Event()
        def approval_barrier(point):
            if point=='after_follow_up':
                approval_inside.set()
                if not allow_approval.wait(10):raise RuntimeError('approval release barrier missing')
        def hold_barrier(point):
            if point=='before_hold_gate':hold_received.set()
        approval=self.approval_request()
        with service_process(replace(self.settings,fault=approval_barrier)) as (url_a,_),service_process(replace(self.settings,fault=hold_barrier)) as (url_b,_),httpx.Client(base_url=url_a,timeout=20) as a,httpx.Client(base_url=url_b,timeout=20) as b:
            ha=self.http_login(a);hb=self.http_login(b);ha['Idempotency-Key']='approval-first';hb['Idempotency-Key']='hold-second'
            with ThreadPoolExecutor(max_workers=2) as executor:
                fa=executor.submit(a.post,'/api/patients/SYN-02/approve',json=approval,headers=ha)
                self.assertTrue(approval_inside.wait(10))
                fb=executor.submit(b.post,'/api/patients/SYN-02/live-holds',json=self.command,headers=hb)
                self.assertTrue(hold_received.wait(10));allow_approval.set()
                approved=fa.result(20);held=fb.result(20)
            self.assertEqual(approved.status_code,200,approved.text);self.assertEqual(held.status_code,200,held.text)
            before=self.safety_state()
            retry=a.post('/api/patients/SYN-02/approve',json=approval,headers=ha)
            self.assertEqual(retry.status_code,200,retry.text);self.assertEqual(retry.json(),approved.json())
            self.assertEqual(before,self.safety_state())
            current=b.get('/api/patients/SYN-02').json();self.assertEqual(current['stage'],'ASSIGN-09');self.assertFalse(current['permissions']['approve_ordinary'])
        with self.store.transaction() as db:
            row=db.execute('SELECT * FROM bundles').fetchone()
            self.assertEqual(row['approved_at'],held.json()['live_received_at'])
            self.assertEqual(row['display_sha256'],approved.json()['display_sha256'])
            self.assertEqual(db.execute('SELECT count(*) FROM bundles').fetchone()[0],1)

    def test_authentication_rechecked_after_unrelated_sqlite_writer_wait(self):
        import httpx
        admitted=CONTEXT.Event()
        def boundary(point):
            if point=='after_hold_admission':admitted.set()
        before=self.safety_state()
        with service_process(replace(self.settings,fault=boundary)) as (url,_),httpx.Client(base_url=url,timeout=20) as client:
            headers=self.http_login(client);headers['Idempotency-Key']='revoked-during-wait'
            writer=self.store.connect();writer.execute('BEGIN IMMEDIATE')
            try:
                writer.execute("UPDATE sessions SET revoked=1 WHERE account_id='alice'")
                with ThreadPoolExecutor(max_workers=1) as executor:
                    pending=executor.submit(client.post,'/api/patients/SYN-02/live-holds',json=self.command,headers=headers)
                    self.assertTrue(admitted.wait(10),'authenticated receipt barrier not reached')
                    writer.commit()
                    response=pending.result(20)
                self.assertEqual(response.status_code,401,response.text)
            finally:writer.rollback();writer.close()
        self.assertEqual(before,self.safety_state())
        self.login();self.enter('revoked-during-wait')

    def test_actual_generation_cutover_process_death_before_and_after_commit(self):
        self.enter();self.store.clock=lambda:NOW
        original=self.settings.installed;before=self.safety_state()
        next_bundle=bundle_for(original.authority,original.review_rules,generation=2,instance=original.control.database_instance_id)
        for point in ['before_generation_commit','after_generation_commit']:
            def cutover_child():
                child_store=Store(self.store.path,original,clock=lambda:NOW)
                def crash(name):
                    if name==point:os._exit(79)
                change_generation(child_store,next_bundle,fault=crash)
            process=CONTEXT.Process(target=cutover_child);process.start();process.join(15)
            self.assertFalse(process.is_alive());self.assertEqual(process.exitcode,79)
            if point=='before_generation_commit':self.assertEqual(before,self.safety_state())
        with self.assertRaisesRegex(AdmissionError,'service_generation_mismatch'):Store(self.store.path,original)
        self.store=Store(self.store.path,next_bundle,clock=lambda:NOW);self.settings=replace(self.settings,installed=next_bundle);self.restart_client()
        current=self.client.get('/api/patients/SYN-02').json()
        self.assertEqual(current['stage'],'ASSIGN-09')
        self.assertEqual(current['snapshot']['patient_version'],before['patient'][3]+1)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM live_hold_operations WHERE family='authority_changed'").fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM live_hold_tasks').fetchone()[0],1)

    def test_database_leaf_alias_hardlink_and_copied_identity_refuse_startup(self):
        alias=self.root/'alias.sqlite';alias.symlink_to(self.store.path)
        with self.assertRaisesRegex(AdmissionError,'unsupported_database_alias'):Store(alias,self.settings.installed)
        alias.unlink();os.link(self.store.path,alias)
        with self.assertRaisesRegex(AdmissionError,'unsupported_database_alias'):Store(self.store.path,self.settings.installed)
        alias.unlink()
        copy_path=self.root/'copied.sqlite'
        source=sqlite3.connect(self.store.path);destination=sqlite3.connect(copy_path)
        try:source.backup(destination)
        finally:source.close();destination.close()
        Path(str(copy_path)+'.admission.lock').touch()
        with self.assertRaisesRegex(AdmissionError,'service_generation_mismatch'):Store(copy_path,self.settings.installed)

    def install_extra_transition_fixture(self,*,multi_followup=False,mixed=False):
        from contracts.domain.evidence_v2 import exact_ref
        fixture,archive_authority,addition,command=live_fixture(self.root/'extra',run_name='extra-concern-run',extra_hold=not multi_followup,extra_threshold=mixed,multi_followup=multi_followup)
        authority=self.settings.installed.authority.model_copy(update={'grants':self.settings.installed.authority.grants+addition.authority.grants})
        rules=self.settings.installed.review_rules.model_copy(deep=True)
        rules.rules.extend(r for r in addition.review_rules.rules if all(r.trigger_rule!=old.trigger_rule for old in rules.rules))
        self.install_next(authority,rules)
        self.settings=replace(self.settings,observed_archives={**self.settings.observed_archives,'extra':(fixture['raw'],self.root/'extra/staging',archive_authority)})
        self.restart_client();self.command=command
        response=self.client.post('/api/observed-archives/extra',json={'mode':'archive_only'},headers=self.headers())
        self.assertEqual(response.status_code,200,response.text)
        bundle=next(r for r in fixture['history'].records if r.kind=='hold_transition_bundle' and r.transition_type==('enter' if multi_followup else 'change_reason'))
        return {**command,'bundle_ref':exact_ref(bundle).model_dump(mode='json'),'trigger_refs':[r.model_dump(mode='json') for r in bundle.trigger_refs]}

    def test_configured_mandatory_followup_subset_refuses_without_any_commit(self):
        self.install_extra_transition_fixture()
        authority=self.settings.installed.authority.model_copy(deep=True)
        grant=authority.grants[-1]
        grant.trigger_bindings[0].follow_ups.append(grant.trigger_bindings[1].follow_ups[0])
        self.install_next(authority);self.restart_client();before=self.safety_state()
        response=self.client.post('/api/patients/SYN-02/live-holds',json=self.command,headers=self.headers('mandatory-subset'))
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(response.json()['code'],'hold_follow_up_mismatch')
        self.assertEqual(self.safety_state(),before)

    def test_complete_two_followup_binding_creates_distinct_deadlines_and_closes_both(self):
        self.install_extra_transition_fixture(multi_followup=True)
        first=self.enter();self.assertEqual(len(first['task_ids']),2)
        self.assertEqual(first,self.enter('full-two-retry'))
        with self.store.transaction() as db:
            from services.foundation.live_tasks import all_tasks
            tasks=all_tasks(db,'SYN-02')
            self.assertEqual(len(tasks),2);self.assertEqual(len({t['due_at'] for t in tasks}),2)
        episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        response=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/reviews',json=self.review_input(episode),headers=self.headers('full-two-review'))
        self.assertEqual(response.status_code,200,response.text);review=response.json()
        clear=self.review_input(episode)
        for key in ['items','rationale','current_assessment_attested']:clear.pop(key)
        clear.update(review_id=review['review_id'],review_sha256=review['review_sha256'])
        response=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/clearance',json=clear,headers=self.headers('full-two-clear'))
        self.assertEqual(response.status_code,200,response.text)
        with self.store.transaction() as db:
            for table in ['live_hold_task_events','live_hold_additional_task_events']:
                self.assertEqual(__import__('json').loads(db.execute('SELECT payload FROM '+table+' ORDER BY rowid DESC LIMIT 1').fetchone()[0])['status'],'closed')

    def test_distinct_same_episode_transition_strengthens_and_stales_review(self):
        addition=self.install_extra_transition_fixture();first=self.enter()
        episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        response=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/reviews',json=self.review_input(episode),headers=self.headers('before-strengthen-review'))
        self.assertEqual(response.status_code,200,response.text);review=response.json()
        clear=self.review_input(episode)
        for key in ['items','rationale','current_assessment_attested']:clear.pop(key)
        clear.update(review_id=review['review_id'],review_sha256=review['review_sha256'])
        before=self.client.get('/api/patients/SYN-02').json()['snapshot']
        response=self.client.post('/api/patients/SYN-02/live-holds',json=addition,headers=self.headers('strengthen'))
        self.assertEqual(response.status_code,200,response.text)
        episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        self.assertEqual(episode['generation'],1);self.assertEqual(len(episode['trigger_refs']),2);self.assertIsNone(episode['current_review'])
        self.assertEqual(self.client.get('/api/patients/SYN-02').json()['snapshot']['patient_version'],before['patient_version']+1)
        response=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/clearance',json=clear,headers=self.headers('obsolete-clear'))
        self.assertEqual(response.status_code,409,response.text)
        with self.store.transaction() as db:self.assertEqual(db.execute("SELECT count(*) FROM live_hold_task_bindings WHERE episode_id=?",(first['episode_id'],)).fetchone()[0],2)

    def test_first_seen_distinct_old_trigger_reopens_after_clear_but_old_retry_does_not(self):
        addition=self.install_extra_transition_fixture();first=self.enter();episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        response=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/reviews',json=self.review_input(episode),headers=self.headers('first-review'))
        self.assertEqual(response.status_code,200,response.text);review=response.json()
        clear=self.review_input(episode)
        for key in ['items','rationale','current_assessment_attested']:clear.pop(key)
        clear.update(review_id=review['review_id'],review_sha256=review['review_sha256'])
        response=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/clearance',json=clear,headers=self.headers('first-clear'))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(first,self.enter('old-distinct-key'))
        self.assertEqual(self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'],[])
        response=self.client.post('/api/patients/SYN-02/live-holds',json=addition,headers=self.headers('new-generation'))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['episode_id'],first['episode_id']);self.assertEqual(response.json()['episode_generation'],2)
        # Identical old semantic intent returns historical success only.
        response=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/clearance',json=clear,headers=self.headers('old-clearance-alias'))
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['episode_generation'],1)
        current_episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        invalid=self.review_input(current_episode)
        for key in ['items','rationale','current_assessment_attested']:invalid.pop(key)
        invalid.update(review_id=review['review_id'],review_sha256=review['review_sha256'])
        response=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/clearance',json=invalid,headers=self.headers('cannot-reuse-old-review'))
        self.assertEqual(response.status_code,409,response.text)
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM live_hold_tasks').fetchone()[0],2)
            statuses=[r[0] for r in db.execute('SELECT status FROM live_hold_episodes ORDER BY generation')]
            self.assertEqual(statuses,['closed','active'])

    def test_whole_archive_multiple_transitions_commit_one_final_decision(self):
        self.install_extra_transition_fixture()
        with self.store.transaction() as db:before=db.execute('SELECT count(*) FROM decisions').fetchone()[0]
        response=self.client.post('/api/observed-archives/extra',json={'mode':'clinical_observation_import'},headers=self.headers('multiple-projection'))
        self.assertEqual(response.status_code,200,response.text);receipt=response.json()
        self.assertEqual([r['ordinal'] for r in receipt['transitions']],[0,1])
        final=receipt['patients']['SYN-02']['decision_id']
        self.assertTrue(all(r['receipt']['decision_id']==final for r in receipt['transitions']))
        self.assertEqual(receipt['patients']['SYN-02']['novel_hold_transitions'],2)
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM decisions').fetchone()[0],before+1)
            self.assertEqual(db.execute('SELECT count(*) FROM live_hold_task_bindings').fetchone()[0],2)

    def install_next(self,authority=None,rules=None,*,fault=None):
        current=self.settings.installed
        bundle=bundle_for(authority or current.authority,rules or current.review_rules,
            generation=current.control.authority_generation+1,instance=current.control.database_instance_id)
        self.store.clock=lambda:NOW
        store=change_generation(self.store,bundle,fault=fault,settings=self.settings)
        self.store=store;self.settings=replace(self.settings,installed=bundle)
        return bundle

    def prepare_exact_amendment(self,*,unadmitted_positive=False):
        from contracts.domain.evidence_v2 import exact_ref
        from contracts.service.live_hold import FollowUpAmendment,FollowUpBinding
        first=self.enter()
        fixture,archive_authority,addition,_=live_fixture(self.root/'amendment',archive_resolution=not unadmitted_positive,
            extra_hold=unadmitted_positive,export_name='amendment-export')
        authority=self.settings.installed.authority.model_copy(update={'grants':self.settings.installed.authority.grants+addition.authority.grants})
        self.install_next(authority)
        self.settings=replace(self.settings,observed_archives={**self.settings.observed_archives,'amendment':(fixture['raw'],self.root/'amendment/staging',archive_authority)})
        self.restart_client()
        response=self.client.post('/api/observed-archives/amendment',json={'mode':'archive_only'},headers=self.headers('amendment-archive'))
        self.assertEqual(response.status_code,200,response.text)
        bundle=next(r for r in reversed(fixture['history'].records) if r.kind=='hold_transition_bundle')
        follow=next(r for r in fixture['history'].records if r.record_id==bundle.follow_up_refs[0].record_id)
        with self.store.transaction() as db:
            row=db.execute('SELECT * FROM live_hold_episodes WHERE id=?',(first['episode_id'],)).fetchone();e=__import__('json').loads(row['payload'])
        old=self.settings.installed.control;grant=addition.authority.grants[0]
        amendment=FollowUpAmendment(service_patient_id='SYN-02',episode_id=row['id'],episode_generation=row['generation'],
            prior_authority_generation=old.authority_generation,prior_authority_sha256=old.authority_sha256,prior_review_rules_sha256=old.review_rules_sha256,
            prior_trigger_set_sha256=e['trigger_set_sha256'],prior_obligation_set_sha256=e['obligation_set_sha256'],source_key=tuple(__import__('json').loads(row['source_key'])),
            source_id=grant.source_id,source_version=grant.source_version,owner_id='alice',grant=grant,source_bundle_ref=exact_ref(bundle),
            follow_up=FollowUpBinding(reference=exact_ref(follow),owner_id='alice',policy=ref('explicit-cutover-followup'),due_at=follow.due_at,escalation_destination=follow.escalation_destination),authorization=ref('explicit-installed-offline-amendment'))
        return amendment,first

    def test_exact_archived_resolution_amendment_adds_task_without_clearance_and_rejects_scope_substitution(self):
        from services.foundation.live_hold import LiveError
        amendment,first=self.prepare_exact_amendment()
        original=self.safety_state()
        def install(value,*,fault=None):
            authority=self.settings.installed.authority.model_copy(update={'follow_up_amendments':[value]})
            return self.install_next(authority,fault=fault)
        cases=[dict(prior_trigger_set_sha256='f'*64),dict(prior_obligation_set_sha256='f'*64),dict(prior_authority_generation=1),
            dict(episode_generation=2),dict(source_key=[*amendment.source_key[:3],'foreign-episode']),dict(source_id='foreign-source'),dict(owner_id='bob'),
            dict(source_bundle_ref=__import__('contracts.domain.observed_v2',fromlist=['ExactRef']).ExactRef.model_validate(self.command['bundle_ref'])),
            dict(follow_up=amendment.follow_up.model_copy(update={'due_at':NOW})),dict(follow_up=amendment.follow_up.model_copy(update={'owner_id':'bob'}))]
        for changes in cases:
            with self.assertRaises((LiveError,ValueError),msg=str(changes)):install(amendment.model_copy(update=changes))
            self.assertEqual(self.safety_state(),original)
        def fail(point):
            if point=='before_generation_commit':raise RuntimeError('amendment rollback beforecommit')
        with self.assertRaises(RuntimeError):install(amendment,fault=fail)
        self.assertEqual(self.safety_state(),original)
        prior_versions=self.client.get('/api/patients/SYN-02').json()['snapshot']
        install(amendment);self.restart_client()
        current=self.client.get('/api/patients/SYN-02').json();self.assertEqual(current['stage'],'ASSIGN-09')
        self.assertEqual(current['snapshot']['patient_version'],prior_versions['patient_version']+1)
        episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        self.assertEqual(episode['generation'],1);self.assertEqual(len(episode['task_ids']),2);self.assertIsNone(episode['current_review'])
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM live_hold_task_bindings').fetchone()[0],2)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            response=__import__('json').loads(db.execute("SELECT response FROM live_hold_operations WHERE family='authority_changed' ORDER BY sequence DESC LIMIT 1").fetchone()[0])
            self.assertEqual(response['task_sets'][0]['amendments'][0]['amendment'],amendment.model_dump(mode='json'))
        # Original retry remains byte-exact, with its original one-task roster.
        self.assertEqual(first,self.enter('old-receipt-after-amendment'))

    def test_amendment_cannot_consume_an_unadmitted_positive_transition(self):
        from services.foundation.live_hold import LiveError
        amendment,_=self.prepare_exact_amendment(unadmitted_positive=True);before=self.safety_state()
        authority=self.settings.installed.authority.model_copy(update={'follow_up_amendments':[amendment]})
        with self.assertRaisesRegex(LiveError,'followup_amendment_unadmitted_positive'):self.install_next(authority)
        self.assertEqual(before,self.safety_state())

    def test_actual_amendment_process_death_rolls_back_or_recovers_complete_task_set(self):
        amendment,first=self.prepare_exact_amendment();current=self.settings.installed
        authority=current.authority.model_copy(update={'follow_up_amendments':[amendment]})
        next_bundle=bundle_for(authority,current.review_rules,generation=current.control.authority_generation+1,instance=current.control.database_instance_id)
        before=self.safety_state()
        def child(point):
            child_store=Store(self.store.path,current,clock=lambda:NOW)
            def crash(name):
                if name==point:os._exit(89)
            change_generation(child_store,next_bundle,fault=crash,settings=self.settings)
        for point in ['before_generation_commit','after_generation_commit']:
            process=CONTEXT.Process(target=child,args=(point,));process.start();process.join(15);self.assertEqual(process.exitcode,89)
            if point=='before_generation_commit':self.assertEqual(self.safety_state(),before)
        self.assertEqual(self.client.get('/api/patients/SYN-02').status_code,503)
        self.store=Store(self.store.path,next_bundle,clock=lambda:NOW);self.settings=replace(self.settings,installed=next_bundle);self.restart_client()
        episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        self.assertEqual(len(episode['task_ids']),2);self.assertEqual(first,self.enter('crash-original-retry'))
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM live_hold_task_bindings').fetchone()[0],2)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_mixed_one_episode_requires_all_obligations_and_named_threshold_block(self):
        addition=self.install_extra_transition_fixture(mixed=True);first=self.enter()
        result=self.client.post('/api/patients/SYN-02/live-holds',json=addition,headers=self.headers('mixed-strengthen'));self.assertEqual(result.status_code,200,result.text)
        episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0]
        self.assertEqual(len(episode['obligations']),2);self.assertEqual(len(episode['task_ids']),2)
        self.assertFalse(episode['clearance_supported']);self.assertEqual(episode['blocker'],'T-OBS2-CLEARANCE-POLICY')
        request=self.review_input(episode);request['items']=[i for i in request['items'] if i['requirement_id']=='review-concern']
        result=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/reviews',json=request,headers=self.headers('omit-threshold'));self.assertEqual(result.status_code,409,result.text);self.assertEqual(result.json()['code'],'all_active_obligations_required')
        request=self.review_input(episode)
        for item in request['items']:
            item['evidence_refs']=[r for r in episode['trigger_refs'] if r['record_id'] in ({self.command['trigger_refs'][0]['record_id']} if item['requirement_id']=='review-concern' else {addition['trigger_refs'][0]['record_id']})]
            if item['requirement_id']=='review-threshold':item.update(result='pending',evidence_refs=[],finding='Named scientific clearance policy is unavailable')
        result=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/reviews',json=request,headers=self.headers('complete-mixed-review'));self.assertEqual(result.status_code,200,result.text)
        with self.store.transaction() as db:
            review=__import__('json').loads(db.execute('SELECT payload FROM live_hold_reviews WHERE id=?',(result.json()['review_id'],)).fetchone()[0]);self.assertEqual(review['result'],'pending')
            self.assertEqual({r[0] for r in db.execute('SELECT status FROM live_hold_episodes')},{'active'})
        self.assertEqual(self.client.get('/api/patients/SYN-02').json()['stage'],'ASSIGN-09')

    def test_owned_foreign_episode_archive_review_fact_cannot_satisfy_current_episode(self):
        first=self.enter();fixture,archive_authority,addition,command=live_fixture(self.root/'foreign',run_name='foreign-episode-run')
        authority=self.settings.installed.authority.model_copy(update={'grants':self.settings.installed.authority.grants+addition.authority.grants})
        self.install_next(authority);self.settings=replace(self.settings,observed_archives={**self.settings.observed_archives,'foreign':(fixture['raw'],self.root/'foreign/staging',archive_authority)})
        self.restart_client();result=self.client.post('/api/observed-archives/foreign',json={'mode':'archive_only'},headers=self.headers('foreign-archive'));self.assertEqual(result.status_code,200,result.text)
        episode=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0];request=self.review_input(episode)
        request['items'][0]['evidence_refs']=[dict(store='archive',namespace_id=command['archive_id'],partition_id=command['partition_id'],**command['trigger_refs'][0])]
        before=self.safety_state();result=self.client.post('/api/patients/SYN-02/live-holds/'+first['episode_id']+'/reviews',json=request,headers=self.headers('foreign-episode-review'))
        self.assertEqual(result.status_code,409,result.text);self.assertEqual(result.json()['code'],'hold_requirement_evidence_mismatch');self.assertEqual(before,self.safety_state())

    def restart_client(self):
        self.client.close();self.client=TestClient(create_app(self.settings),base_url=ORIGIN);self.login()

    def test_generation_cutover_revocation_disable_rollback_to_old_bytes_and_stale_worker(self):
        original=self.settings.installed;receipt=self.enter();old_client=self.client
        before=self.safety_state()
        def fail(point):
            if point=='before_generation_commit':raise RuntimeError('cutover beforecommit')
        with self.assertRaises(RuntimeError):self.install_next(fault=fail)
        self.assertEqual(before,self.safety_state())
        bundle=self.install_next()
        self.assertEqual(old_client.get('/api/patients/SYN-02').status_code,503)
        self.assertEqual(old_client.get('/health').status_code,503)
        self.restart_client()
        held=self.client.get('/api/patients/SYN-02/live-holds').json()
        self.assertEqual(len(held['episodes']),1)
        self.assertEqual(held['summary']['authority_generation'],2)
        # Reverting exact old bytes still increments generation, so G1 never returns.
        self.install_next(original.authority,original.review_rules);self.restart_client()
        self.assertEqual(self.client.get('/api/patients/SYN-02/live-holds').json()['summary']['authority_generation'],3)
        revoked=self.settings.installed.authority.model_copy(update={'grants':[]})
        self.install_next(revoked);self.restart_client()
        response=self.client.post('/api/patients/SYN-02/live-holds',json=self.command,headers=self.headers('entry'))
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(response.json()['code'],'live_source_grant_unavailable')
        held=self.client.get('/api/patients/SYN-02/live-holds').json()
        self.assertEqual(len(held['episodes']),1);self.assertFalse(held['episodes'][0]['clearance_supported'])
        disabled=revoked.model_copy(update={'enabled':False})
        self.install_next(disabled);self.restart_client()
        self.assertEqual(self.client.get('/api/patients/SYN-02').json()['stage'],'ASSIGN-09')
        self.assertFalse(self.client.get('/api/patients/SYN-02').json()['permissions']['approve_ordinary'])

    def test_two_independent_episodes_clear_one_and_threshold_rule_remains_named_blocked(self):
        fixture,archive_authority,addition,command=live_fixture(self.root/'second',run_name='second-threshold-run',threshold=True)
        authority=self.settings.installed.authority.model_copy(update={'grants':self.settings.installed.authority.grants+addition.authority.grants})
        self.install_next(authority)
        self.settings=replace(self.settings,observed_archives={**self.settings.observed_archives,'second':(fixture['raw'],self.root/'second/staging',archive_authority)})
        self.restart_client()
        response=self.client.post('/api/observed-archives/second',json={'mode':'archive_only'},headers=self.headers())
        self.assertEqual(response.status_code,200,response.text)
        first=self.enter()
        response=self.client.post('/api/patients/SYN-02/live-holds',json=command,headers=self.headers('second-entry'))
        self.assertEqual(response.status_code,200,response.text)
        episodes=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes']
        self.assertEqual(len(episodes),2)
        concern=next(e for e in episodes if e['episode_id']==first['episode_id'])
        threshold=next(e for e in episodes if e['episode_id']!=first['episode_id'])
        self.assertFalse(threshold['clearance_supported']);self.assertEqual(threshold['blocker'],'T-OBS2-CLEARANCE-POLICY')
        response=self.client.post('/api/patients/SYN-02/live-holds/'+concern['episode_id']+'/reviews',json=self.review_input(concern),headers=self.headers('review'))
        self.assertEqual(response.status_code,200,response.text);review=response.json()
        clear=self.review_input(concern)
        for k in ['rationale','items','current_assessment_attested']:clear.pop(k)
        clear.update(review_id=review['review_id'],review_sha256=review['review_sha256'])
        response=self.client.post('/api/patients/SYN-02/live-holds/'+concern['episode_id']+'/clearance',json=clear,headers=self.headers('clear'))
        self.assertEqual(response.status_code,200,response.text)
        left=self.client.get('/api/patients/SYN-02/live-holds').json()['episodes']
        self.assertEqual([e['episode_id'] for e in left],[threshold['episode_id']])
        self.assertEqual(self.client.get('/api/patients/SYN-02').json()['stage'],'ASSIGN-09')


if __name__=='__main__':
    unittest.main()
