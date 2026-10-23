"""Authenticated scalar SQLite lifecycle controls; no genuine N fit/data claim.

Only the already-qualified observed projection and current protocol authority
seams are injected. Cookies, CSRF, ownership, transactions, queue receipts,
claims, host binding, ingestion and saved reads execute their real source.
"""
from contextlib import contextmanager
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from contracts.domain.analysis import canonical,sha
from contracts.domain.nof1_app import (NInput,NResult,CONFIG_REFS,ownership_manifest,
    consumed_ids,execution_binding,MONITORED,ARTIFACT_NAMES)
from contracts.domain.protocol import LAW_REF,NOF1_REF
from services.foundation.app import Settings,create_app,HASHER
from services.foundation import nof1_analysis as nof1
from services.foundation.analysis import (claim,bind_execution,ingest,export_queued_request,
    fail,AnalysisError)
from services.foundation.appointment import checked_result as visit_result
from tests.contracts.test_nof1_app import scalar_fixture

WALL=datetime(2026,10,23,12,tzinfo=timezone.utc)
HOST=dict(source_commit='a'*40,learner_image='sha256:'+'b'*64)
URL='http://127.0.0.1:8765'


class ScalarSQLite:
    def __init__(self,path):
        self.path=path;self.clock=lambda:WALL;self.gate=SimpleNamespace(timeout=5)
        with self.transaction(write=True) as db:
            for path in sorted(Path('services/foundation/migrations').glob('*.sql')):
                db.executescript(path.read_text())

    @contextmanager
    def transaction(self,write=False,before_commit=None,**kwargs):
        db=sqlite3.connect(self.path,isolation_level=None);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON');db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        try:
            yield db
            if before_commit:before_commit(db)
            db.commit()
        except BaseException:db.rollback();raise
        finally:db.close()


def abstention(product):
    ctx=product.request.context
    return dict(schema_version='4.0.0',synthetic=True,kind='poc_nof1_result',purpose=product.purpose,
        attempt_id=product.attempt_id,target_id=product.target_id,input_sha256=sha(product.model_dump(mode='json')),
        history_sha256=product.history_sha256,cohort=[m.model_dump() for m in product.cohort],
        cutoff=product.cutoff.isoformat(),run=product.run.model_dump(),
        configuration=product.request.configuration.model_dump(),model=ctx.model.model_dump(),
        prior=ctx.prior.model_dump(),estimand=ctx.estimand.model_dump(),protocol=ctx.protocol.model_dump(),
        status='abstained',readiness='eligible',reason='structural diagnostic failure',generated_at=WALL.isoformat(),
        consumed_record_ids=consumed_ids(product),effect=None,artifacts=[],
        diagnostics=dict(execution=execution_binding(product,HOST),timings=dict(worker_seconds=.1)),
        limitations=['Scalar lifecycle fixture; no fitted estimate.'])


def completed_counterexample(product):
    """Gate-shaped scalar data solely for negative semantic-corruption tests."""
    value=abstention(product);effect=dict(kind='conditional_expected_assignment_contrast',unit='quality_points',
        mean=.25,sd=.5,lower=-.75,upper=1.25,horizon=7,target_id=product.target_id)
    fit={key:{name:number for name in MONITORED} for key,number in
        (('rhat',1.),('ess_bulk',500.),('ess_tail',500.),('mcse',.01))}
    fit.update(accepted=True,divergences=0,maximum_tree_depth=9,energy_bfmi=[.8]*4)
    effect_d={key:{'expected_contrast':number} for key,number in
        (('rhat',1.),('ess_bulk',500.),('ess_tail',500.),('mcse',.01))};effect_d['accepted']=True
    final=dict(K=2048,U=.0001,L=.2,residual_variance=.00001,raw_effect_variance=.25,
        uninflated_effect_variance=.24999,mean_integration_se=(.0001/4000)**.5,
        sd=.5,interval=[-.75,1.25],changes=[.001]*3,stability_tolerance=.02*(.2**.5),
        seconds=.1,peak_rss_mib=12.,variance_pass=True,mean_pass=True,stability_pass=True)
    value['diagnostics'].update(fits=[dict(extended=False,diagnostics=fit)],effect_mcmc=effect_d,
        axes=dict(chains=4,draws=1000,target_ids=[product.target_id],patients=[m.patient_id for m in product.cohort]),
        integration=dict(status='accepted',axes=['chain','draw','target'],target_ids=[product.target_id],
            unit='quality_points',kind='conditional_expected_assignment_contrast',
            bootstrap=dict(resamples=1000,block=20,seed=731981),seconds=.1,
            attempted=[dict(final,K=1024,changes=None,stability_pass=False),final]))
    value.update(status='completed',reason=None,effect=effect,
        artifacts=[dict(path=name,sha256='d'*64) for name in sorted(ARTIFACT_NAMES)])
    return value


class Nof1AnalysisService(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=ScalarSQLite(self.root/'disposable.sqlite')
        self.histories=[scalar_fixture('N-PATIENT-A'),scalar_fixture('N-PATIENT-B')]
        self.cutoff=self.histories[0].cutoff
        self.state=dict(workflow=dict(hold_reasons=[]),simulation=dict(panel_id='panel-structural',
            law_version=LAW_REF['id'],law=LAW_REF,protocol=NOF1_REF,family='nof1_med',
            nof1=dict(status='active',uninterrupted=True)))
        with self.store.transaction(write=True) as db:
            for owner in ('alice','bob'):
                db.execute('INSERT INTO accounts VALUES(?,?,?,?,?)',(owner,owner,owner,HASHER.hash('StructuralPassword!'),1))
            for h in self.histories:
                db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',(h.patient_id,'alice',
                    'Structural N member',1,1,1,1,canonical(self.state),None,self.cutoff.isoformat()))
        self.projector=patch('services.foundation.protocol.export_histories',side_effect=self.projections)
        self.authority=patch('services.foundation.nof1.guard',return_value=[])
        self.projector.start();self.guard=self.authority.start()
        with patch('services.foundation.app.Store',return_value=self.store):
            self.app=create_app(Settings(self.store.path,None,clock=lambda:WALL))
        self.client=TestClient(self.app,base_url=URL);self.login(self.client)

    def tearDown(self):
        self.client.close();self.projector.stop();self.authority.stop();self.temp.cleanup()

    def projections(self,db,owner,patients,cutoff):
        return [h for h in self.histories if h.patient_id in patients]

    def login(self,client,owner='alice'):
        csrf=client.get('/api/session').json()['csrf']
        response=client.post('/api/login',json=dict(username=owner,password='StructuralPassword!'),
            headers={'Origin':URL,'X-CSRF-Token':csrf})
        self.assertEqual(response.status_code,200,response.text)

    def headers(self,key='N-structural-command'):
        return {'Origin':URL,'X-CSRF-Token':self.client.get('/api/session').json()['csrf'],'Idempotency-Key':key}

    def payload(self,**changes):
        return dict(purpose='N1',target_id='N-PATIENT-B',cohort_id='declared-N-cohort',
            patient_versions={h.patient_id:1 for h in self.histories},cutoff=self.cutoff.isoformat(),
            configuration=CONFIG_REFS['N1'],**changes)

    def queue(self,payload=None,key='N-structural-command'):
        response=self.client.post('/api/nof1-analyses',json=payload or self.payload(),headers=self.headers(key))
        self.assertEqual(response.status_code,202,response.text);return response.json()

    def output(self,p,value=None):
        directory=self.root/'output';directory.mkdir(exist_ok=True);value=value or abstention(p)
        artifacts=dict(diagnostics=value['diagnostics'],ownership=ownership_manifest(p))
        refs=[]
        for name,data in artifacts.items():
            raw=canonical(data).encode();path=name+'.json';(directory/path).write_bytes(raw)
            refs.append(dict(path=path,sha256=hashlib.sha256(raw).hexdigest()))
        value['artifacts']=refs;(directory/'result.json').write_text(canonical(value),encoding='utf-8')
        return directory,value

    def test_authenticated_cookie_csrf_receipt_target_fk_and_owned_saved_reads(self):
        with TestClient(self.app,base_url=URL) as anonymous:
            self.assertEqual(anonymous.post('/api/nof1-analyses',json=self.payload()).status_code,401)
        self.assertEqual(self.client.post('/api/nof1-analyses',json=self.payload()).status_code,403)
        queued=self.queue();self.assertEqual(self.queue()['id'],queued['id']);job=queued['id']
        self.assertEqual(queued['target_id'],'N-PATIENT-B');self.assertFalse(queued['stale'])
        for url in (f'/api/jobs/{job}',f'/api/patients/N-PATIENT-A/analyses',
                f'/api/patients/N-PATIENT-B/analyses/{job}'):
            response=self.client.get(url);self.assertEqual(response.status_code,200,response.text)
            self.assertIn('nof1_analysis',response.text)
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT patient_id FROM pending_work').fetchone()[0],'N-PATIENT-B')
            self.assertEqual(db.execute('SELECT count(*) FROM analysis_attempts').fetchone()[0],1)
        with TestClient(self.app,base_url=URL) as foreign:
            self.login(foreign,'bob');self.assertEqual(foreign.get('/api/jobs/'+job).status_code,404)
            self.assertEqual(foreign.get('/api/nof1-analyses/receipt',params=dict(target_id='N-PATIENT-B',key='N-structural-command')).status_code,404)

    def test_unknown_submission_reconciles_persisted_identity_after_reauthentication(self):
        queued=self.queue()
        with TestClient(self.app,base_url=URL) as reauth:
            self.login(reauth)
            found=reauth.get('/api/nof1-analyses/receipt',params=dict(target_id='N-PATIENT-B',key='N-structural-command')).json()
            self.assertEqual(found['status'],'found');self.assertEqual(found['attempt']['id'],queued['id'])
            unknown=reauth.get('/api/nof1-analyses/receipt',params=dict(target_id='N-PATIENT-B',key='unknown-key')).json()
            self.assertEqual(unknown,dict(status='unknown',attempt=None))
        with self.store.transaction() as db:self.assertEqual(db.execute('SELECT count(*) FROM analysis_attempts').fetchone()[0],1)

    def test_overlap_covers_nonanchor_member_and_claim_export_binding(self):
        queued=self.queue();job=queued['id']
        overlap=self.payload();overlap.update(target_id='N-PATIENT-A',patient_versions={'N-PATIENT-A':1})
        response=self.client.post('/api/nof1-analyses',json=overlap,headers=self.headers('overlap'))
        self.assertEqual(response.status_code,409,response.text)
        selection=dict(owner='alice',job=job,key='N-structural-command',submission=self.payload())
        proof=export_queued_request(self.store,**selection)
        with self.assertRaises(ValueError):claim(self.store,expected=dict(selection=selection,export_sha256='0'*64))
        claimed=claim(self.store,expected=dict(selection=selection,export_sha256=sha(proof)))
        self.assertEqual(claimed['attempt_id'],job);self.assertIsNone(claim(self.store))
        binding=bind_execution(self.store,job,claimed['claim_token'],HOST)
        self.assertEqual(binding,bind_execution(self.store,job,claimed['claim_token'],HOST))
        with self.assertRaises(AnalysisError):bind_execution(self.store,job,'stale',HOST)
        with self.assertRaises(AnalysisError):bind_execution(self.store,job,claimed['claim_token'],dict(HOST,source_commit='c'*40))

    def test_every_member_owner_version_cutoff_generation_rechecked_at_queue(self):
        for field,value in (('owner_id','bob'),('version',2),('cutoff',(self.cutoff+timedelta(days=1)).isoformat())):
            with self.subTest(field=field),self.store.transaction(write=True) as db:
                db.execute('UPDATE patients SET '+field+'=? WHERE id=?',(value,'N-PATIENT-A'))
            response=self.client.post('/api/nof1-analyses',json=self.payload(),headers=self.headers(field))
            self.assertEqual(response.status_code,409,response.text)
            with self.store.transaction(write=True) as db:
                db.execute('UPDATE patients SET owner_id=?,version=?,cutoff=? WHERE id=?',('alice',1,self.cutoff.isoformat(),'N-PATIENT-A'))
        state=copy.deepcopy(self.state);state['simulation']['panel_id']='different-generation'
        with self.store.transaction(write=True) as db:db.execute('UPDATE patients SET state_json=? WHERE id=?',(canonical(state),'N-PATIENT-A'))
        self.assertEqual(self.client.post('/api/nof1-analyses',json=self.payload(),headers=self.headers('generation')).status_code,409)

    def test_current_authority_hold_withdrawal_background_and_same_cutoff_correction(self):
        queued=self.queue()
        for reason in ('Clinical hold','Component consent withdrawn','Frozen behavioral background changed','Frozen exact protocol authority changed'):
            self.guard.return_value=[reason]
            with self.assertRaisesRegex(ValueError,reason):claim(self.store)
            read=self.client.get('/api/jobs/'+queued['id']).json()
            self.assertTrue(read['stale']);self.assertFalse(read['serving']['summary_available'])
        self.guard.return_value=[]
        changed=self.histories[0].model_dump(mode='python')
        next(r for r in changed['records'] if r['kind']=='daily_report' and r['missingness']=='observed')['sleep_quality']=4.
        from contracts.domain.protocol_analysis import ProtocolHistory
        self.histories[0]=ProtocolHistory.model_validate(changed)
        with self.assertRaisesRegex(ValueError,'same_cutoff_history'):claim(self.store)

    def test_rejected_receipt_is_atomic_and_conflicting_key_cannot_resubmit(self):
        queued=self.queue();different=self.payload();different['purpose']='N0';different['configuration']=CONFIG_REFS['N0']
        response=self.client.post('/api/nof1-analyses',json=different,headers=self.headers())
        self.assertEqual(response.status_code,409,response.text)
        with self.store.transaction() as db:
            for table in ('pending_work','analysis_attempts','receipts'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],1)

    def test_abstention_late_ingest_corrupt_artifact_and_saved_immutability(self):
        job=self.queue()['id'];claimed=claim(self.store);token=claimed['claim_token'];bind_execution(self.store,job,token,HOST)
        p=NInput.model_validate_json(canonical(claimed['input']));directory,value=self.output(p)
        with self.assertRaises(AnalysisError):ingest(self.store,job,'stale',directory)
        with self.assertRaises(AnalysisError):ingest(self.store,job,token,directory,accept_before=WALL.isoformat())
        original=(directory/'ownership.json').read_bytes();(directory/'ownership.json').write_bytes(b'{}')
        with self.assertRaises(AnalysisError):ingest(self.store,job,token,directory)
        (directory/'ownership.json').write_bytes(original)
        self.assertEqual(ingest(self.store,job,token,directory)['status'],'abstained')
        read=self.client.get('/api/jobs/'+job).json();self.assertIsNone(read['result']['effect'])
        with self.store.transaction() as db:
            row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone()
            self.assertEqual(visit_result(row),(None,'nof1_is_not_an_individual_visit_effect'))
        with self.assertRaises(AnalysisError):ingest(self.store,job,token,directory)
        with self.assertRaises(sqlite3.IntegrityError),self.store.transaction(write=True) as db:
            db.execute("UPDATE analysis_attempts SET failure_reason='rewrite' WHERE job_id=?",(job,))

    def test_rehashed_semantically_invalid_completed_results_and_corrupt_saved_read(self):
        job=self.queue()['id'];claimed=claim(self.store);token=claimed['claim_token'];bind_execution(self.store,job,token,HOST)
        p=NInput.model_validate_json(canonical(claimed['input']))
        for mutation in ('effect-target','fit-ess','integration-se','interval','ownership','host'):
            value=completed_counterexample(p)
            if mutation=='effect-target':value['effect']['target_id']='N-PATIENT-A'
            elif mutation=='fit-ess':value['diagnostics']['fits'][-1]['diagnostics']['ess_bulk']['p_M']=399.
            elif mutation=='integration-se':value['diagnostics']['integration']['attempted'][-1]['mean_integration_se']=0.
            elif mutation=='interval':value['effect']['upper']=.9
            elif mutation=='ownership':value['consumed_record_ids']=value['consumed_record_ids'][1:]
            else:value['diagnostics']['execution']['source_commit']='c'*40
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                checked=NResult.model_validate_json(canonical(value))
                from contracts.domain.nof1_app import validate_result
                validate_result(checked,p,execution_binding(p,HOST))
        # Direct corruption simulates a damaged DB summary, not accepted output.
        value=completed_counterexample(p);value['effect']['lower']=7.
        with self.store.transaction(write=True) as db:
            db.execute("UPDATE analysis_attempts SET status='completed',stage='complete',result_json=? WHERE job_id=?",(canonical(value),job))
            db.execute("UPDATE pending_work SET status='completed' WHERE id=?",(job,))
        read=self.client.get('/api/jobs/'+job).json()
        self.assertIsNone(read['result']);self.assertFalse(read['serving']['summary_available'])

    def test_no_science_imported_by_authenticated_host_lifecycle(self):
        self.queue()
        self.assertFalse({'numpy','pymc','pytensor','arviz','arviz_stats','scipy','statsmodels'}.intersection(sys.modules))


if __name__=='__main__':unittest.main()
