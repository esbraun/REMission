"""Analytic seams and real owned routes; no fitted output is fabricated here."""
import copy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import ndtr
from scipy.stats import norm
from fastapi.testclient import TestClient
from contracts.domain.analysis import AnalysisHistory, AnalysisInput, AnalysisResult, CONFIG_REF, ESTIMAND_REF, project_history, sha
from contracts.domain.boundaries import ObservedHistory
from methods.visit.model import inputs, build
from methods.visit.numerics import (endpoint_weights, conditional_endpoint, rounded_isi_mean,
    bin_logprob, integration_bounds, integrate)
from services.foundation.app import Settings,create_app
from services.foundation.cli import seed,DEMO_PASSWORDS
from services.foundation.store import canonical,instant
from services.foundation.workflow import record_header,history,create_decision,state_for,SUPPORT
from services.foundation.analysis import claim,progress,interrupt,ingest,AnalysisError
from live_helpers import fresh_store

ORIGIN=instant('2026-01-01T12:00:00+00:00')
URL='http://127.0.0.1:8765'


def fixture_records(patient='POC-TEST',day=14):
    records=[]
    def add(kind,t,values,at=None):
        value=dict(**record_header(f'{patient}-{kind}-{t}',patient,at or ORIGIN+timedelta(days=t,minutes=-1)),kind=kind,**values)
        if kind!='assignment':
            value['source'].update(id='poc-longitudinal-v1',adapter='simulation')
        records.append(value)
    add('assignment',0,dict(decision_id='decision-fixture',approval_id='approval-fixture',option='behavioral_continue',experimental=False,
        component=None,probability=None,seed=None,support_policy=SUPPORT,patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None),ORIGIN)
    for t in range(day+1):
        if t>0:
            add('delivery',t,dict(assignment_id=patient+'-assignment-0',option='behavioral_continue',stage='taken',adherence=1.,rescue=False,protocol_deviations=[]),ORIGIN+timedelta(days=t-1,hours=8))
            add('daily_report',t,dict(sleep_quality=4. if t!=3 else None,function=7. if t!=3 else None,diary_sleep_minutes=400. if t!=3 else None,
                adverse_symptoms=[],goals=[],burden=0. if t!=3 else None,missingness='observed' if t!=3 else 'missing'))
        if t%14==0:
            end=ORIGIN+timedelta(days=t,hours=-1)
            add('isi',t,dict(instrument_version='ISI-7-synthetic-14d-v1',recall_days=14,recall_start=(end-timedelta(days=14)).isoformat(),recall_end=end.isoformat(),items=[3,3,3,3,3,2,2]))
    return records


def reduced():
    full=ObservedHistory.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,kind='observed_history',patient_id='POC-TEST',records=fixture_records())))
    return project_history(full.project(ORIGIN+timedelta(days=14)))


class NumericalTests(unittest.TestCase):
    def test_gaussian_recall_impulse_and_measurement(self):
        for rho in [-1.,-.95,0.,.55,.95,1.]:
            independent=[]
            for j in range(1,43):
                error=0.;values=[]
                for t in range(1,43):
                    error=rho*error+float(t==j)
                    if t>=29:values.append(error)
                independent.append(np.mean(values))
            np.testing.assert_allclose(endpoint_weights(rho),independent,atol=2e-15)
        m,s=conditional_endpoint(19.,.6,0.,2.,3.,.7,2.,4.,.8,.9,14)
        self.assertAlmostEqual(s*s,4/14+9)
        # Independently recur both existing carries and absolute sine phase.
        c,e,error=.8,.9,.7;z=[]
        for h in range(1,43):
            c*=.65;e*=.8;error=0.*error
            if h>=29:z.append(19+.6*np.sin(2*np.pi*(14+h)/21)+error-2*c-4*e)
        self.assertAlmostEqual(m,np.mean(z))

    def test_measurement_bins_and_clipped_expectation(self):
        values=np.arange(29,dtype=float)
        probabilities=np.exp(bin_logprob(values,13.2,2.1))
        self.assertAlmostEqual(probabilities.sum(),1.)
        self.assertAlmostEqual(values@probabilities,rounded_isi_mean(13.2,2.1))
        self.assertAlmostEqual(rounded_isi_mean(.2,1.)+rounded_isi_mean(27.8,1.),28.)
        np.testing.assert_array_equal(rounded_isi_mean(np.array([-.2,.5,27.5,29.]),0.),[0,1,28,28])
        for mu in [-50.,0.,5.,10.,50.]:
            p=np.exp(bin_logprob(np.arange(0,10001)/1000,mu,1.,.001,10.))
            self.assertAlmostEqual(p.sum(),1.,places=10)
        # Positive-tail narrow bins must not disappear through1-CDF cancellation.
        self.assertTrue(np.isfinite(bin_logprob(9.5,0.,.5,.001,10.)))

    def test_uninflated_variance_rejects_noise_and_null_passes(self):
        rng=np.random.default_rng(82)
        inflated=.1*rng.normal(size=(4,1000,1))+np.sqrt(8)*rng.normal(size=(4,1000,8))
        bound=integration_bounds(inflated)
        self.assertFalse(bound['variance_pass'])
        p={k:np.ones((4,20)) for k in ['b','a','rho','sigma_e','sigma_isi','p_adherence','current_e','beta_c','beta_e']}
        p['b']*=19;p['rho']*=.5;p['p_adherence']*=.8
        p['beta_c']*=0;p['beta_e']*=0
        effect,checks=integrate(p,day=14,current_c=.8,current_e=.3,seed=89)
        np.testing.assert_array_equal(effect,0.)
        self.assertEqual([r['K'] for r in checks['attempted']],[1024,2048])
        self.assertEqual(checks['attempted'][-1]['U'],0.)
        # Crossing the whole-stage deadline during checks must never accept.
        calls=[0]
        def clock():
            calls[0]+=1
            return 0. if calls[0]<200 else 1801.
        with patch('methods.visit.numerics.time.monotonic',side_effect=clock):
            failed,report=integrate(p,day=14,current_c=.8,current_e=.3,seed=89)
        self.assertIsNone(failed);self.assertEqual(report['status'],'numerical-precision-unmet')
        self.assertGreater(report['seconds'],1800)

    def test_hstar_data_ownership_and_actual_likelihood_changes(self):
        h=reduced();d=inputs(h)
        self.assertEqual(d['recall'].tolist(),[list(range(14)),list(range(14,28))])
        self.assertEqual(d['qindex'],[t+13 for t in range(1,15) if t!=3])
        self.assertEqual(d['deliveries'],14)
        self.assertAlmostEqual(d['c'][-1],1-.65**14)
        model=build(d,guide=False)
        point=model.initial_point();logp=model.compile_logp()(point)
        gradient=model.compile_dlogp()
        for rho in [0.,-.94,.94]:
            checked=copy.deepcopy(point)
            checked['rho_interval__']=np.log((rho+.95)/(.95-rho))
            self.assertTrue(np.isfinite(gradient(checked)).all())
        changed=copy.deepcopy(d);changed['quality']=d['quality']+1
        self.assertNotAlmostEqual(logp,build(changed,guide=False).compile_logp()(point))
        changed=copy.deepcopy(d);changed['isi']=d['isi']-3
        self.assertNotAlmostEqual(logp,build(changed,guide=False).compile_logp()(point))

    def test_exact_guide_density_and_valid_gradients(self):
        data=inputs(reduced())
        guided=build(data);original=build(data,guide=False)
        gp=guided.initial_point();base=original.initial_point()
        transformed=guided.compile_fn(guided.replace_rvs_by_values([guided['prior_normal_coordinates'],guided['guide_log_jacobian']]),
            inputs=guided.value_vars,on_unused_input='ignore')
        glog=guided.compile_logp();olog=original.compile_logp();gradient=guided.compile_dlogp()
        for rho in [0.,-.94,.94]:
            point=copy.deepcopy(gp);point['rho_interval__']=np.log((rho+.95)/(.95-rho))
            point['guide_innovation']=np.linspace(-.2,.2,len(data['nights'])+7)
            u,logjac=transformed(point)
            op=copy.deepcopy(base)
            op.update({k:v for k,v in point.items() if k in op})
            op.update(mu_b=19+5*u[0],b_raw=u[1],population_beta=4*u[2:4],beta_raw=u[4:6],a=u[6],innovation=u[7:])
            self.assertAlmostEqual(float(glog(point)),float(olog(op))+np.log(80)+float(logjac),places=7)
            self.assertTrue(np.isfinite(gradient(point)).all())

    def test_hstar_exclusion_tamper_duplicate_future_and_delivery(self):
        h=reduced().model_dump(mode='json')
        text=canonical(h)
        for forbidden in ['function','diary','raw_sha256','source','state_json','seed','index']:
            self.assertNotIn('"'+forbidden+'"',text)
        for field in ['function','raw_sha256','state_json','seed']:
            bad=copy.deepcopy(h);bad['records'][0][field]=1
            with self.assertRaises(ValueError):AnalysisHistory.model_validate_json(canonical(bad))
        bad=copy.deepcopy(h);bad['records'].append(bad['records'][0])
        with self.assertRaises(ValueError):AnalysisHistory.model_validate_json(canonical(bad))
        bad=copy.deepcopy(h);bad['records'][0]['available_at']=bad['cutoff']
        with self.assertRaises(ValueError):AnalysisHistory.model_validate_json(canonical(bad))
        bad=copy.deepcopy(h);bad['records']=[r for r in bad['records'] if r['record_id']!='POC-TEST-delivery-5'];bad['provenance']=[r for r in bad['provenance'] if r['record_id']!='POC-TEST-delivery-5']
        with self.assertRaisesRegex(ValueError,'missing is not zero'):AnalysisHistory.model_validate_json(canonical(bad))
        full=fixture_records();full[1]['source']['id']='unqualified-other-law'
        observed=ObservedHistory.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,kind='observed_history',patient_id='POC-TEST',records=full)))
        with self.assertRaisesRegex(ValueError,'unqualified'):project_history(observed.project(ORIGIN+timedelta(days=14)))
        for field,value in [('version','99.0.0'),('sha256','f'*64)]:
            full=fixture_records();full[0]['support_policy'][field]=value
            observed=ObservedHistory.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,kind='observed_history',patient_id='POC-TEST',records=full)))
            with self.assertRaisesRegex(ValueError,'support'):project_history(observed.project(ORIGIN+timedelta(days=14)))


class AnalysisRoutesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=fresh_store(self.root/'db.sqlite');seed(self.store)
        with self.store.transaction(write=True) as db:
            state=state_for('ASSIGN-02');state['simulation']=dict(law_version='poc-longitudinal-v1',day=14,origin=ORIGIN.isoformat(),seed=999,index=0,actions=[])
            db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',('POC-TEST','alice','Synthetic analysis fixture',1,1,1,1,canonical(state),None,(ORIGIN+timedelta(days=14)).isoformat()))
            for r in fixture_records():
                encoded=canonical(r)
                db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(r['record_id'],'POC-TEST',r['kind'],r['lineage_id'],1,None,encoded,'0'*64,encoded.encode(),'0'*64,r['event_at'],r['recorded_at'],r['available_at'],5,self.store.clock().isoformat()))
            create_decision(db,'POC-TEST',self.store.clock())
        self.app=create_app(Settings(self.store.path,self.store.installed,clock=self.store.clock))
        self.client=TestClient(self.app,base_url=URL);self.login(self.client,'alice')

    def tearDown(self):
        self.client.close();self.temp.cleanup()

    def login(self,client,user):
        csrf=client.get('/api/session').json()['csrf']
        response=client.post('/api/login',json=dict(username=user,password=DEMO_PASSWORDS[user]),headers={'Origin':URL,'X-CSRF-Token':csrf})
        self.assertEqual(response.status_code,200)

    def headers(self,key='analysis-1'):
        return {'Origin':URL,'X-CSRF-Token':self.client.get('/api/session').json()['csrf'],'Idempotency-Key':key}

    def submit(self,key='analysis-1',previous=None):
        return self.client.post('/api/patients/POC-TEST/analyses',json=dict(expected_version=1,previous_attempt=previous),headers=self.headers(key))

    def test_receipt_owner_csrf_atomic_freeze_restart_and_retry(self):
        self.assertEqual(self.client.post('/api/patients/POC-TEST/analyses',json=dict(expected_version=1)).status_code,403)
        created=self.submit();self.assertEqual(created.status_code,202,created.text);job=created.json()['id']
        self.assertEqual(self.submit().json()['id'],job)
        self.assertEqual(self.submit('another-key').status_code,409)
        bob=TestClient(self.app,base_url=URL);self.login(bob,'bob')
        self.assertEqual(bob.get('/api/jobs/'+job).status_code,404)
        self.assertEqual(bob.get('/api/patients/POC-TEST/analyses/'+job).status_code,404)
        bob.close()
        work=claim(self.store);self.assertEqual(work['attempt_id'],job)
        product=AnalysisInput.model_validate_json(canonical(work['input']))
        self.assertEqual(sha(product.model_dump(mode='json')),created.json()['input_sha256'])
        self.assertIsNone(claim(self.store))
        self.assertEqual(interrupt(self.store),1)
        with self.assertRaises(AnalysisError):progress(self.store,job,work['claim_token'],dict(stage='fitting',attempt_id=job,input_sha256=created.json()['input_sha256']))
        newer=self.submit('retry-2',job);self.assertEqual(newer.status_code,202,newer.text)
        self.assertEqual(newer.json()['previous_attempt'],job)
        old=self.client.get('/api/jobs/'+job).json();self.assertEqual(old['status'],'failed')

    def test_ingestion_identity_staleness_and_terminal_immutability(self):
        job=self.submit().json();work=claim(self.store)
        result=dict(schema_version='1.0.0',synthetic=True,kind='poc_visit_result',attempt_id=job['id'],input_sha256=job['input_sha256'],history_sha256=job['history_sha256'],
            cutoff=job['cutoff'],configuration=CONFIG_REF,estimand=ESTIMAND_REF,status='abstained',reason='test-numerical-precision-unmet',effect=None,diagnostics={},artifacts=[],limitations=['Synthetic seam test only'])
        directory=self.root/'out';directory.mkdir();(directory/'result.json').write_text(canonical(result))
        wrong=copy.deepcopy(result);wrong['input_sha256']='f'*64;(directory/'result.json').write_text(canonical(wrong))
        with self.assertRaisesRegex(AnalysisError,'identity'):ingest(self.store,job['id'],work['claim_token'],directory)
        (directory/'result.json').write_text(canonical(result))
        with self.store.transaction(write=True) as db:
            db.execute('UPDATE patients SET cutoff=? WHERE id=?',((ORIGIN+timedelta(days=28)).isoformat(),'POC-TEST'))
        ingest(self.store,job['id'],work['claim_token'],directory)
        saved=self.client.get('/api/jobs/'+job['id']).json()
        self.assertTrue(saved['stale']);self.assertEqual(saved['cutoff'],job['cutoff'])
        with self.assertRaises(AnalysisError):ingest(self.store,job['id'],work['claim_token'],directory)
        with self.store.transaction() as db:
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
