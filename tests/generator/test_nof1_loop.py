"""Actual existing HTTP generator/auth/SQLite loop; no analysis execution."""
import json
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from fastapi.testclient import TestClient
from contracts.domain.protocol import LAW_REF,NOF1_REF
from services.foundation.app import create_app
from services.foundation.store import canonical,digest
from services.foundation.store import instant
from services.foundation.workflow import record_header
import test_service as prior

ASSERTIONS=['both_options_acceptable','stable_regimen_reviewed','interactions_reviewed','fall_risk_reviewed','rescue_stop_plan_reviewed','patient_agrees']


class Nof1LoopTests(prior.SimulationServiceTests):
    def patient(self):
        r=self.client.post('/api/panels/generate',json=dict(schema_version='2.0.0',kind='poc_protocol_panel',
            seed=1245,count=2,family='nof1_med',law=LAW_REF,protocol=NOF1_REF),headers=self.headers())
        self.assertEqual(r.status_code,200,r.text)
        return r.json()['patient_ids'][0]

    def payload(self,patient,action):
        s=self.workspace(patient)['snapshot']
        value=dict(mode='current',action=action,decision_id=s['record_id'],expected_version=s['patient_version'],
            expected_state_version=s['state_version'],expected_consent_version=s['consent_version'],
            expected_eligibility_version=s['eligibility_version'],rationale='Explicit fictional engineering review')
        if action=='review':value['assertions']=ASSERTIONS
        if action=='approve':value.update(permitted_options=['MED_A','MED_B'],template=NOF1_REF)
        return value

    def command(self,patient,action,*,key=None,payload=None,expected=200):
        r=self.client.post(f'/api/patients/{patient}/nof1',json=payload or self.payload(patient,action),headers=self.headers(key))
        self.assertEqual(r.status_code,expected,r.text)
        return r

    def prepare(self,patient):
        ordinary=self.approve(patient)
        self.command(patient,'consent');self.command(patient,'review');self.command(patient,'approve')
        return ordinary

    def test_explicit_authorization_start_draw_and72_day_law(self):
        p=self.patient()
        self.command(p,'start',expected=409)
        self.command(p,'review');self.command(p,'approve',expected=409)
        ordinary=self.prepare(p)
        before=self.workspace(p)
        self.assertIsNone(before['nof1']['loop'].get('draws') and before['nof1']['loop']['draws'][0] or None)
        payload=self.payload(p,'start');r=self.command(p,'start',key='stable-start',payload=payload)
        self.assertEqual(self.command(p,'start',key='stable-start',payload=payload).json(),r.json())
        w=self.workspace(p);draw=w['nof1']['loop']['draws'][0]
        self.assertEqual(draw['probabilities'],dict(MED_A=.5,MED_B=.5))
        self.assertEqual(draw['seed']['namespace'],'assignment')
        self.assertFalse(any(r['kind']=='delivery' for r in w['projection']['records']))
        self.assertEqual(len(w['nof1']['loop']['draws']),1)
        for _ in range(6):
            response=self.step(p)
            self.assertEqual(response.status_code,200,response.text)
        w=self.workspace(p);loop=w['nof1']['loop']
        self.assertEqual(loop['status'],'completed')
        self.assertEqual([r['day'] for r in loop['draws']],[0,9,18,27,36,45,54,63])
        self.assertEqual([r['day'] for r in loop['reviews']],[36,72])
        self.assertTrue(all(r['analysis_status'] in ('unavailable_methods_pending','inconclusive_insufficient_arm_blocks') for r in loop['reviews']))
        deliveries=[r for r in w['projection']['records'] if r['kind']=='delivery' and r['option'].startswith('MED_')]
        self.assertEqual(len(deliveries),56)
        self.assertTrue(any(r['stage']=='not_taken' for r in deliveries))
        self.assertEqual(len({r['assignment_id'] for r in deliveries}),8)
        with self.store.transaction() as db:
            for draw in loop['draws']:
                assignment=db.execute('SELECT rowid FROM events WHERE id=?',(draw['assignment_id'],)).fetchone()[0]
                later=list(db.execute("SELECT rowid,payload FROM events WHERE patient_id=? AND kind='delivery'",(p,)))
                self.assertTrue(all(assignment<row['rowid'] for row in later if json.loads(row['payload'])['assignment_id']==draw['assignment_id']))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM state_changes WHERE patient_id=? AND payload LIKE '%nof1_block_draw%'",(p,)).fetchone()[0],8)
        saved=self.client.get(f'/api/patients/{p}/history/'+ordinary['bundle_id']).json()
        self.assertEqual(saved['display']['approval']['permitted_options'],[]) # original ordinary approval retained
        self.assertEqual(self.workspace(p)['nof1']['loop'],loop)
        self.command(p,'start',expected=409)

    def test_missing_review_partial_envelope_stale_and_rollback(self):
        p=self.patient();self.approve(p);self.command(p,'consent')
        self.command(p,'approve',expected=409)
        body=self.payload(p,'review');body['assertions']=ASSERTIONS[:-1]
        self.command(p,'review',payload=body,expected=422)
        self.command(p,'review')
        body=self.payload(p,'approve');body['permitted_options']=['MED_A']
        self.command(p,'approve',payload=body,expected=422)
        self.command(p,'approve');stale=self.payload(p,'start')
        self.command(p,'review');self.command(p,'start',payload=stale,expected=409)
        self.command(p,'approve')
        before=self.workspace(p)
        def fault(stage):
            if stage=='after_nof1_draw':raise RuntimeError('deliberate protocol rollback')
        broken=TestClient(create_app(replace(self.settings,fault=fault)),base_url=prior.ORIGIN)
        self.login(broken)
        with self.assertRaisesRegex(RuntimeError,'deliberate protocol rollback'):
            broken.post(f'/api/patients/{p}/nof1',json=self.payload(p,'start'),headers=self.headers(client=broken))
        broken.close()
        self.assertEqual(self.workspace(p)['simulation'],before['simulation'])
        self.command(p,'start')
        self.assertEqual(len(self.workspace(p)['nof1']['loop']['draws']),1)
        self.command(p,'withdraw')
        self.assertEqual(self.workspace(p)['nof1']['loop']['status'],'stopped')
        self.assertEqual(self.step(p).status_code,200)
        self.assertEqual(len(self.workspace(p)['nof1']['loop']['draws']),1)
        self.command(p,'consent',expected=409)

    def test_current_consent_expiry_and_material_state_changes_stop_draws(self):
        for scenario in ('expiry','hold','rescue','review_changed'):
            with self.subTest(scenario=scenario):
                p=self.patient();self.approve(p)
                payload=self.payload(p,'consent')
                if scenario=='expiry':payload['consent_expires_at']=(instant(self.workspace(p)['snapshot']['cutoff'])+timedelta(days=8)).isoformat()
                self.command(p,'consent',payload=payload);self.command(p,'review');self.command(p,'approve');self.command(p,'start')
                if scenario in ('hold','review_changed'):
                    response=self.client.post(f'/api/patients/{p}/state',json=dict(expected_version=self.workspace(p)['snapshot']['patient_version'],
                        stage='ASSIGN-09' if scenario=='hold' else 'ASSIGN-02',reason='Material synthetic state review'),headers=self.headers())
                    self.assertEqual(response.status_code,200,response.text)
                elif scenario=='rescue':
                    # A live observation is not a hidden controller command.
                    value=dict(**record_header('rescue-'+p,p,prior.NOW),kind='intercurrent_event',event_type='rescue',detail='Fictional rescue used')
                    raw=canonical({k:v for k,v in value.items() if k!='source'});value['source']['raw_sha256']=digest(raw)
                    response=self.client.post(f'/api/patients/{p}/events',json=dict(record=value,raw_source=raw),headers=self.headers())
                    self.assertEqual(response.status_code,200,response.text)
                if scenario!='hold':self.assertEqual(self.step(p).status_code,200)
                else:self.assertEqual(self.step(p).status_code,409)
                loop=self.workspace(p)['nof1']['loop']
                self.assertEqual(loop['status'],'stopped');self.assertFalse(loop['uninterrupted'])
                self.assertEqual(len(loop['draws']),1)

    def test_owner_concurrent_advance_retry_and_immutable_checkpoint(self):
        p=self.patient();self.prepare(p);self.command(p,'start')
        before=self.workspace(p)
        saved={r['id']:self.client.get(f'/api/patients/{p}/history/'+r['id']).json()['display_sha256'] for r in before['history']}
        bob=TestClient(create_app(self.settings),base_url=prior.ORIGIN);self.login(bob,'bob')
        result=bob.post(f'/api/patients/{p}/nof1',json=self.payload(p,'start'),headers=self.headers(client=bob))
        self.assertEqual(result.status_code,404);bob.close()
        second=TestClient(create_app(self.settings),base_url=prior.ORIGIN);self.login(second)
        payload=dict(expected_version=before['snapshot']['patient_version'],mode='visit')
        headers=[self.headers('advance-left'),self.headers('advance-right',client=second)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(client.post,f'/api/patients/{p}/advance',json=payload,headers=h) for client,h in zip((self.client,second),headers)]
            responses=[f.result() for f in futures]
        self.assertEqual(sorted(r.status_code for r in responses),[200,409],[r.text for r in responses])
        winner=next(i for i,r in enumerate(responses) if r.status_code==200)
        retry=(self.client,second)[winner].post(f'/api/patients/{p}/advance',json=payload,headers=headers[winner])
        self.assertEqual(retry.json(),responses[winner].json());second.close()
        after=self.workspace(p)
        self.assertEqual(after['simulation']['day'],14);self.assertEqual(len(after['nof1']['loop']['draws']),2)
        for identifier,sha in saved.items():
            self.assertEqual(self.client.get(f'/api/patients/{p}/history/'+identifier).json()['display_sha256'],sha)
