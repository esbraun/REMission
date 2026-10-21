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
                'live_safety_facts','live_projection_receipts']
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
        for requirement in [*authority.grants[0].required_reviews,*rules.rules[0].requirements]:
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

    def install_next(self,authority=None,rules=None,*,fault=None):
        current=self.settings.installed
        bundle=bundle_for(authority or current.authority,rules or current.review_rules,
            generation=current.control.authority_generation+1,instance=current.control.database_instance_id)
        self.store.clock=lambda:NOW
        store=change_generation(self.store,bundle,NOW,fault=fault)
        self.store=store;self.settings=replace(self.settings,installed=bundle)
        return bundle

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
