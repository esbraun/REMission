"""PA3 full-target and actual authenticated admission/old-reader seams."""
import copy
from datetime import timedelta
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pymc as pm
from scipy.stats import norm,halfnorm
from contracts.domain.analysis import AnalysisInput,AnalysisResult,CONFIG_REF,canonical,sha
from contracts.domain.borrowing import (BORROW_CONFIG,BORROW_CONFIG_REF,BRIDGE_REF,BORROW_MODEL_REF,
    BorrowAnalysisInput,make_borrow_input,parse_input,parse_result,APPROVED_BUNDLES)
from methods.visit.borrow_model import build_joint
from methods.visit.borrowing import marginal
from methods.visit.model import build,inputs
from methods.visit.source_precision import select_indices
from services.foundation.analysis_sources import load_source
from services.foundation.analysis import claim,interrupt,ingest,AnalysisError
from test_analysis import reduced,ORIGIN
import test_analysis as analysis_cases


class JointTargetTests(unittest.TestCase):
    def test_real_frozen_pre_v1_input_result_canonical_identity(self):
        import hashlib
        root=Path(__file__).with_name('fixtures')
        raw=(root/'pa3-legacy-v0-input.json').read_bytes();output=(root/'pa3-legacy-v0-result.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'74139ac2dfdc945dd1eb0be1e176f2ec66386dee39a09717c1f5a0b8da8551ac')
        self.assertEqual(hashlib.sha256(output).hexdigest(),'9f4bc1ce5ddf921fea3de714b86bb9d8c8826f2b8b1109365190d6d5a6434efd')
        product=parse_input(raw);result=parse_result(output)
        self.assertEqual(product.model_dump(mode='json'),json.loads(raw))
        self.assertEqual(result.model_dump(mode='json'),json.loads(output))
        self.assertEqual(sha(product.model_dump(mode='json')),result.input_sha256)
        self.assertEqual(result.configuration.model_dump(),CONFIG_REF)
        self.assertEqual(result.status,'completed');self.assertIsNotNone(result.effect)
        self.assertEqual(result.attempt_id,'analysis-5746f0fea4964d77b5a1cf5aeb552f01')

    def test_joint_minus_original_exact_normalized_terms_and_new_priors(self):
        data=inputs(reduced());sources=load_source('source-7c97862d',reduced().cutoff)
        original=build(data,guide=False);joint=build_joint(data,sources,BORROW_CONFIG,guide=False)
        old=original.initial_point();new=joint.initial_point()
        old.update(mu_b=np.array(19.),population_beta=np.array([1.,3.]),a=np.array(.4),
            sd_b_log__=np.array(np.log(2.)),sd_beta_log__=np.log([.8,.8]),
            p_adherence_logodds__=np.array(np.log(.7/.3)),rho_interval__=np.array(np.log((.3+.95)/(.95-.3))),
            sigma_e_log__=np.array(0.),sigma_isi_log__=np.array(np.log(1.2)))
        new.update(old);bias=np.array([.2,-.3]);tau=.8
        new.update(source_bias=bias,source_tau_log__=np.array(np.log(tau)))
        theta=dict(mu_b=19,beta_c=1,beta_e=3,sd_b=2,sd_beta_c=.8,sd_beta_e=.8,p=.7,rho=.3,sigma_e=1,sigma_isi=1.2,a=.4)
        g=marginal(theta,64)
        terms=[np.log(.5*norm.pdf(s.d,g+b, np.sqrt(s.se*s.se+tau*tau))+.5*norm.pdf(s.d,0,np.sqrt(s.se*s.se+100))) for s,b in zip(sources.studies,bias)]
        priors=norm.logpdf(bias,0,.5).sum()+halfnorm.logpdf(tau,scale=1)+np.log(tau)
        observed=float(joint.compile_logp()(new)-original.compile_logp()(old))
        self.assertAlmostEqual(observed,sum(terms)+priors,places=8)
        self.assertNotAlmostEqual(observed,2*sum(terms)+priors,places=6)
        self.assertNotAlmostEqual(observed,terms[0]+priors,places=6)
        reversed_terms=[np.log(.5*norm.pdf(-s.d,g+b,np.sqrt(s.se*s.se+tau*tau))+.5*norm.pdf(-s.d,0,np.sqrt(s.se*s.se+100))) for s,b in zip(sources.studies,bias)]
        self.assertNotAlmostEqual(observed,sum(reversed_terms)+priors,places=6)
        changed=copy.deepcopy(sources);changed.studies[0].__dict__['d']+=.7
        altered=build_joint(data,changed,BORROW_CONFIG,guide=False)
        self.assertNotAlmostEqual(float(altered.compile_logp()(new)),float(joint.compile_logp()(new)),places=6)
        self.assertTrue(np.isfinite(joint.compile_dlogp()(new)).all())

    def test_joint_exact_guide_identity_and_original_prior_parameterization(self):
        data=inputs(reduced());sources=load_source('source-7c97862d',reduced().cutoff)
        guided=build_joint(data,sources,BORROW_CONFIG);original=build_joint(data,sources,BORROW_CONFIG,guide=False)
        gp=guided.initial_point();base=original.initial_point()
        converted=guided.compile_fn(guided.replace_rvs_by_values([guided['prior_normal_coordinates'],guided['guide_log_jacobian']]),inputs=guided.value_vars,on_unused_input='ignore')
        glog=guided.compile_logp();olog=original.compile_logp();gradient=guided.compile_dlogp()
        for rho in (0.,-.94,.94):
            point=copy.deepcopy(gp);point['rho_interval__']=np.log((rho+.95)/(.95-rho))
            point['guide_innovation']=np.linspace(-.2,.2,len(data['nights'])+7)
            u,jac=converted(point);op=copy.deepcopy(base);op.update({k:v for k,v in point.items() if k in op})
            op.update(mu_b=19+5*u[0],b_raw=u[1],population_beta=4*u[2:4],beta_raw=u[4:6],a=u[6],innovation=u[7:])
            self.assertAlmostEqual(float(glog(point)),float(olog(op))+np.log(80)+float(jac),places=7)
            self.assertTrue(np.isfinite(gradient(point)).all())
        self.assertNotIn('guide_innovation',original.named_vars)
        with build_joint(data,sources,BORROW_CONFIG,guide=False,prior_predictive=True):
            prior=pm.sample_prior_predictive(draws=32,random_seed=37198,var_names=['mu_b','population_beta','source_g'])
        self.assertEqual(prior['prior']['source_g'].shape,(1,32))
        self.assertTrue(np.isfinite(prior['prior']['source_g']).all())

    def test_unconditioned_source_prior_is_invariant_to_local_adherence_counts(self):
        data=inputs(reduced());sources=load_source('source-7c97862d',reduced().cutoff)
        values=[]
        for taken,deliveries in [(0,0),(0,28),(28,28)]:
            with build_joint(dict(data,taken=taken,deliveries=deliveries),sources,BORROW_CONFIG,guide=False,prior_predictive=True):
                prior=pm.sample_prior_predictive(draws=64,random_seed=317482,var_names=['p_adherence','source_g'])
            values.append((prior['prior']['p_adherence'].values,prior['prior']['source_g'].values))
        for observed in values[1:]:
            np.testing.assert_array_equal(observed[0],values[0][0]);np.testing.assert_array_equal(observed[1],values[0][1])
        self.assertGreater(float(values[0][0].std()),.2)

    def test_frozen_source_identity_old_reader_and_seed_intents(self):
        h=reduced();sources=load_source('source-7c97862d',h.cutoff)
        first=make_borrow_input(h,'analysis-one',sources);second=make_borrow_input(h,'analysis-two',sources)
        self.assertNotEqual(first.numerical_seeds.nuts,second.numerical_seeds.nuts)
        self.assertEqual(first.model_dump(),parse_input(first.model_dump_json()).model_dump())
        with self.assertRaises(ValueError):AnalysisInput.model_validate_json(first.model_dump_json())
        bad=first.model_dump(mode='json');bad['source_set_sha256']='0'*64
        with self.assertRaises(ValueError):BorrowAnalysisInput.model_validate_json(canonical(bad))
        bad=first.model_dump(mode='json');bad['sources']['map_prior']={}
        with self.assertRaises(ValueError):BorrowAnalysisInput.model_validate_json(canonical(bad))
        for key in ('participant_rows','seed','private_parameters','ipd'):
            bad=first.model_dump(mode='json');bad['sources']['studies'][0][key]=[]
            with self.assertRaises(ValueError):BorrowAnalysisInput.model_validate_json(canonical(bad))
        from contracts.domain.analysis import make_input
        old=make_input(h,'analysis-old',123)
        self.assertEqual(parse_input(old.model_dump_json()).model_dump(),old.model_dump())
        bad=old.model_dump(mode='json');bad['sources']=sources.model_dump(mode='json')
        with self.assertRaises(ValueError):parse_input(canonical(bad))

    def test_selection_extrema_ties_and_chain_balance(self):
        g=np.tile(np.arange(20.),(4,1));v=np.ones((4,20));g[:,3]=-100;g[:,17]=100
        selected=select_indices(g,v)
        self.assertEqual(len(selected),32)
        for chain in range(4):
            observed=[r['draw'] for r in selected if r['chain']==chain]
            self.assertEqual(observed,[2,7,11,16,3,17,0,1])
        with self.assertRaises(ValueError):select_indices(g[:,:7],v[:,:7])


class BorrowingRoutesTests(unittest.TestCase):
    tearDown=analysis_cases.AnalysisRoutesTests.tearDown
    login=analysis_cases.AnalysisRoutesTests.login
    headers=analysis_cases.AnalysisRoutesTests.headers
    def setUp(self):
        analysis_cases.AnalysisRoutesTests.setUp(self)
        self.client.close()
        self.app=analysis_cases.create_app(analysis_cases.Settings(self.store.path,self.store.installed,clock=self.store.clock,live_export_root=self.root/'exports'))
        self.client=analysis_cases.TestClient(self.app,base_url=analysis_cases.URL);self.login(self.client,'alice')

    def test_genuine_pre_v1_stored_receipt_replays_with_optional_defaults(self):
        import hashlib
        root=Path(__file__).with_name('fixtures')
        raw=(root/'pa3-legacy-v0-receipt.json').read_bytes()
        self.assertEqual(len(raw),758)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'bb1f9b9ef8d3707114d1bed85a355467cad8d22c201de070f6507c5914b057ec')
        payload=json.loads((root/'pa3-legacy-v0-payload.json').read_bytes())
        payload_hash=sha(payload)
        self.assertEqual(payload_hash,'009dd2e72debc0623fa62118a06e23a81dd09469a2cbf3c16a8842f5ecf7dc46')
        stored=json.loads(raw);patient=stored['patient_id']
        self.assertEqual(stored['configuration'],CONFIG_REF)
        self.assertEqual(stored['status'],'queued');self.assertIsNone(stored['result'])
        session=self.client.get('/api/session').json()['auth_generation']
        # The original session was not captured. Only the fresh test-session
        # association and owned stub are synthetic; receipt bytes are genuine.
        with self.store.transaction(write=True) as db:
            db.execute('INSERT INTO patients SELECT ?,owner_id,name,version,state_version,consent_version,eligibility_version,state_json,NULL,cutoff FROM patients WHERE id=?',(patient,'POC-TEST'))
            db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',('alice',session,'9877f6c1-c994-418a-a2ec-3141afba90b8',patient+':analysis',payload_hash,raw.decode()))
            before=db.execute('SELECT count(*) FROM analysis_attempts').fetchone()[0]
        for body in (payload,dict(payload,mode='v0',source_bundle_id=None)):
            response=self.client.post('/api/patients/'+patient+'/analyses',json=body,headers=self.headers('9877f6c1-c994-418a-a2ec-3141afba90b8'))
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json(),stored)
            self.assertEqual(sha(response.json()),hashlib.sha256(raw).hexdigest())
        changed=self.client.post('/api/patients/'+patient+'/analyses',json=dict(payload,mode='borrow',source_bundle_id='source-7c97862d'),headers=self.headers('9877f6c1-c994-418a-a2ec-3141afba90b8'))
        self.assertEqual(changed.status_code,409,changed.text)
        with self.store.transaction() as db:self.assertEqual(db.execute('SELECT count(*) FROM analysis_attempts').fetchone()[0],before)

    def test_legacy_v0_receipt_retry_with_new_default_fields_and_immutable_failed_comparison(self):
        legacy=dict(expected_version=1,previous_attempt=None)
        first=self.client.post('/api/patients/POC-TEST/analyses',json=legacy,headers=self.headers('old-shape'))
        self.assertEqual(first.status_code,202,first.text)
        modern=dict(legacy,mode='v0',source_bundle_id=None)
        replay=self.client.post('/api/patients/POC-TEST/analyses',json=modern,headers=self.headers('old-shape'))
        self.assertEqual(replay.json()['id'],first.json()['id'])
        claim(self.store);interrupt(self.store)
        second=self.client.post('/api/patients/POC-TEST/analyses',json=dict(legacy,mode='borrow',source_bundle_id='source-7c97862d'),headers=self.headers('borrow-pair'))
        self.assertEqual(second.status_code,202,second.text);claim(self.store);interrupt(self.store)
        pair=dict(left=first.json()['id'],right=second.json()['id'])
        with patch('services.foundation.analysis.os.link',side_effect=OSError('injected-before-publication')):
            with self.assertRaisesRegex(OSError,'injected-before-publication'):
                self.client.post('/api/patients/POC-TEST/analysis-comparisons',json=pair,headers=self.headers('comparison-1'))
        self.assertEqual(self.client.get('/api/patients/POC-TEST/analysis-comparisons').json()['comparisons'],[])
        destination=next((self.root/'exports/comparisons').iterdir())
        self.assertEqual(list(destination.glob('comparison-*.json')),[])
        # A process killed before its finally block can leave a partial temp.
        # Such bytes have no final identity and never enter the saved list.
        (destination/'.comparison-interrupted.partial').write_text('{')
        saved=self.client.post('/api/patients/POC-TEST/analysis-comparisons',json=pair,headers=self.headers('comparison-1'))
        self.assertEqual(saved.status_code,201,saved.text)
        self.assertTrue(all(v['effect'] is None for v in saved.json()['attempts']))
        repeated=self.client.post('/api/patients/POC-TEST/analysis-comparisons',json=pair,headers=self.headers('comparison-1'))
        self.assertEqual(repeated.json(),saved.json())
        self.assertEqual(self.client.get('/api/patients/POC-TEST/analysis-comparisons').json()['comparisons'],[saved.json()])
        with self.store.transaction(write=True) as db:
            db.execute('UPDATE patients SET cutoff=? WHERE id=?',((ORIGIN+timedelta(days=42)).isoformat(),'POC-TEST'))
        self.assertEqual(self.client.get('/api/patients/POC-TEST/analysis-comparisons').json()['comparisons'],[saved.json()])
        self.assertEqual(self.client.post('/api/patients/POC-TEST/analysis-comparisons',json=dict(left=pair['left'],right=pair['left']),headers=self.headers('same-attempt')).status_code,409)

    def test_source_admission_receipt_intents_and_guarded_result_sources(self):
        available=self.client.get('/api/patients/POC-TEST/analysis-sources')
        self.assertEqual(available.status_code,200,available.text)
        self.assertEqual(len(available.json()['bundles']),3)
        base=dict(expected_version=1,previous_attempt=None,mode='borrow',source_bundle_id='source-7c97862d')
        for bad in [dict(base,source_bundle_id='../private'),dict(base,mode='v0'),dict(base,source_bundle_id=None)]:
            response=self.client.post('/api/patients/POC-TEST/analyses',json=bad,headers=self.headers('bad-'+sha(bad)[:8]))
            self.assertEqual(response.status_code,409,response.text)
        response=self.client.post('/api/patients/POC-TEST/analyses',json=base,headers=self.headers('borrow-intent'))
        self.assertEqual(response.status_code,202,response.text);created=response.json()
        self.assertEqual(created['configuration'],BORROW_CONFIG_REF)
        self.assertEqual(created['forecast_endpoint_day'],56)
        self.assertEqual(created['recall_first_night'],43)
        self.assertEqual(self.client.post('/api/patients/POC-TEST/analyses',json=base,headers=self.headers('borrow-intent')).json()['id'],created['id'])
        self.assertEqual(self.client.post('/api/patients/POC-TEST/analyses',json=dict(base,mode='tau2'),headers=self.headers('borrow-intent')).status_code,409)
        job=claim(self.store);product=parse_input(canonical(job['input']))
        self.assertEqual(product.source_set_sha256,created['source_set_sha256'])
        result=dict(schema_version='1.1.0',synthetic=True,kind='poc_visit_borrow_result',attempt_id=created['id'],
            input_sha256=created['input_sha256'],history_sha256=created['history_sha256'],source_set_sha256='f'*64,
            cutoff=created['cutoff'],configuration=BORROW_CONFIG_REF,estimand=product.request.context.estimand.model_dump(),
            bridge=BRIDGE_REF,status='abstained',reason='test-bridge-precision-unmet',effect=None,diagnostics={},artifacts=[],limitations=['Synthetic boundary test only'])
        directory=self.root/'borrow-result';directory.mkdir();(directory/'result.json').write_text(canonical(result))
        with self.assertRaisesRegex(AnalysisError,'source hash'):ingest(self.store,created['id'],job['claim_token'],directory)
        result['source_set_sha256']=created['source_set_sha256'];(directory/'result.json').write_text(canonical(result))
        ingest(self.store,created['id'],job['claim_token'],directory)
        saved=self.client.get('/api/jobs/'+created['id']).json()
        self.assertIsNone(saved['result']['effect']);self.assertEqual(saved['status'],'abstained')


if __name__=='__main__':unittest.main()
