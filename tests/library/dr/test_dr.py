"""Independent algebra/reference and adversarial checks of the approved functional."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from pydantic import TypeAdapter, ValidationError
from contracts.artifacts.ope import Decision, Reward, QRow, Targets, OPERequest
from contracts.domain.boundaries import ContractViolation
from methods.ope.functional import score_rows, patient_bootstrap, evaluate_files

ROOT=Path(__file__).resolve().parents[3]
E=ROOT/'docs/implementation/evidence/G0-LIB/DR'
NOW=datetime(2026,10,1,tzinfo=timezone.utc)


def decision(row,patient,action,p,available=None):
    return Decision(row_id=row,patient_id=patient,window_id=row,decision_at=NOW,
        x=0.,x_available_at=NOW-timedelta(seconds=1),available_actions=[0,1] if available is None else available,
        logging_probabilities=p,action=action)


def targets(ids,probabilities):
    return Targets(schema_version='1.0.0',synthetic=True,policy=dict(schema_version='1.0.0',synthetic=True,
        policy_id='fixed',version='1.0.0',sealed_at=NOW,action_order='0=no_prompt,1=approved_prompt',
        definition_sha256='a'*64,availability_rule='singleton_deterministic_empty_unavailable'),roster_sha256='b'*64,
        rows=[dict(row_id=i,probabilities=p) for i,p in zip(ids,probabilities)])


class Algebra(unittest.TestCase):
    def test_wire_action_identity_is_integer_and_versioned(self):
        d=decision('row','patient',1,[.5,.5]).model_dump(mode='json')
        for bad in [True,1.,'1',2,-1]:
            d['action']=bad
            with self.subTest(action=bad):
                with self.assertRaises(ValidationError):Decision.model_validate_json(json.dumps(d))
        wire=json.loads((E/'exchange/request.json').read_bytes());wire['version']='2.0.0'
        with self.assertRaises(ValidationError):OPERequest.model_validate_json(json.dumps(wire))

    def fixture(self):
        ds=[decision('r1','P1',0,[.25,.75]),decision('r2','P2',1,[.25,.75])]
        rs=[Reward(row_id='r1',status='observed',value=2.),Reward(row_id='r2',status='observed',value=1.)]
        qs=[QRow(row_id='r1',values=[1.,3.]),QRow(row_id='r2',values=[2.,4.])]
        ts=[targets(['r1','r2'],[[1/3,2/3],[.5,.5]])]
        return ds,rs,ts,qs

    def test_reviewer_independent_rational_and_unequal_patient_denominator(self):
        ds,rs,ts,qs=self.fixture()
        _,v,ips=score_rows(ds,rs,ts,qs)
        expected=[F(1,3)*1+F(2,3)*3+F(1,3)/F(1,4)*(2-1),
                  F(1,2)*2+F(1,2)*4+F(1,2)/F(3,4)*(1-4)]
        self.assertEqual(expected,[F(11,3),F(1)])
        np.testing.assert_allclose(v[:,0],list(map(float,expected)),atol=1e-12,rtol=0)
        np.testing.assert_allclose(ips[:,0],[float(F(8,3)),float(F(2,3))],atol=1e-12,rtol=0)
        ds.insert(1,decision('r1-copy','P1',0,[.25,.75]));rs.insert(1,Reward(row_id='r1-copy',status='observed',value=2.))
        ds[1].decision_at+=timedelta(days=1)
        qs.insert(1,QRow(row_id='r1-copy',values=[1.,3.]));ts=[targets([d.row_id for d in ds],[[1/3,2/3],[1/3,2/3],[.5,.5]])]
        _,v,_=score_rows(ds,rs,ts,qs)
        self.assertAlmostEqual(v.mean(),float(F(25,9)),places=12)
        self.assertNotAlmostEqual(v.mean(),float(F(7,3)),places=8)

    def test_zero_Q_residual_factual_target_and_singleton(self):
        ds,rs,ts,qs=self.fixture()
        for q in qs:q.values=[0.,0.]
        _,v,ips=score_rows(ds,rs,ts,qs);np.testing.assert_array_equal(v,ips)
        qs[0].values=[2.,3.];qs[1].values=[2.,1.]
        _,v,_=score_rows(ds,rs,ts,qs);np.testing.assert_allclose(v[:,0],[8/3,1.5],atol=1e-12)
        ts[0].rows[0].probabilities=[0.,1.]
        _,v,ips=score_rows(ds,rs,ts,qs);self.assertEqual(v[0,0],3.);self.assertEqual(ips[0,0],0.)
        ds=[decision('only','P',1,[0.,1.],[1])];rs=[Reward(row_id='only',status='observed',value=4.)]
        _,v,ips=score_rows(ds,rs,[targets(['only'],[[0.,1.]])],[QRow(row_id='only',values=[2.,3.])])
        self.assertEqual(v[0,0],4.);self.assertEqual(ips[0,0],4.)

    def test_probability_support_availability_and_identity_failures(self):
        mutations=[lambda d,r,t,q:setattr(d[0],'logging_probabilities',[.2,.2]),
            lambda d,r,t,q:setattr(d[0],'logging_probabilities',[1.,0.]),
            lambda d,r,t,q:setattr(d[0],'available_actions',[0]),
            lambda d,r,t,q:setattr(d[0],'action',None),
            lambda d,r,t,q:setattr(t[0].rows[0],'probabilities',[-.1,1.1]),
            lambda d,r,t,q:setattr(t[0].rows[0],'probabilities',[.2,.7]),
            lambda d,r,t,q:q.reverse(),lambda d,r,t,q:setattr(d[1],'window_id',d[0].window_id) or setattr(d[1],'patient_id',d[0].patient_id)]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                args=self.fixture();mutate(*args)
                with self.assertRaises(ContractViolation):score_rows(*args)
        args=self.fixture();args[1][0]=Reward(row_id='r1',status='missing',value=None)
        with self.assertRaises(ContractViolation):score_rows(*args)

    def test_independent_patient_ratio_bootstrap_and_shared_pair_reference(self):
        patients=[];values=[]
        for p in range(30):
            for j in range(1+p%3):patients.append(f'P{p:02}');values.append([p/3+j,2-p/7+j*j])
        values=np.asarray(values,dtype=np.float64)
        order,draws,ci,paired,checksum=patient_bootstrap(patients,values,518)
        # Reference explicitly loops sampled patients/rows and sums scalar values/counts.
        indices=np.random.Generator(np.random.PCG64DXSM(518)).integers(0,30,(2000,30),dtype=np.int64)
        ref=[]
        for sample in indices:
            rows=[i for k in sample for i,p in enumerate(patients) if p==f'P{k:02}']
            ref.append([sum(float(values[i,j]) for i in rows)/len(rows) for j in [0,1]])
        np.testing.assert_allclose(draws,ref,atol=1e-12,rtol=0)
        def percentile(xs,p):
            x=sorted(xs);at=(len(x)-1)*p;lo=int(at);return x[lo]+(at-lo)*(x[min(lo+1,len(x)-1)]-x[lo])
        independent_ci=[[percentile([r[j] for r in ref],p) for p in [.025,.975]] for j in [0,1]]
        independent_paired=[[percentile([r[1]-r[0] for r in ref],p) for p in [.025,.975]]]
        np.testing.assert_allclose(ci,independent_ci,atol=1e-12,rtol=0)
        np.testing.assert_allclose(paired,independent_paired,atol=1e-12,rtol=0)
        self.assertEqual(checksum,hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest())
        np.testing.assert_array_equal(draws,patient_bootstrap(patients,values,518)[1])
        self.assertFalse(np.array_equal(draws,patient_bootstrap(patients,values,519)[1]))
        self.assertNotAlmostEqual(values[:,0].mean(),np.mean([values[np.array(patients)==p,0].mean() for p in order]))
        with self.assertRaises(ContractViolation):patient_bootstrap(patients[:20],values[:20],518)


class Provenance(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for path in (E/'exchange').iterdir():shutil.copyfile(path,self.root/path.name)
        self.req=json.loads((self.root/'request.json').read_bytes())

    def read(self,name):return json.loads((self.root/name).read_bytes())
    def write(self,name,value):
        path=self.root/name;path.write_bytes((json.dumps(value,indent=2)+'\n').encode());return hashlib.sha256(path.read_bytes()).hexdigest()
    def run_request(self):return evaluate_files(self.root,OPERequest.model_validate_json(json.dumps(self.req)))
    def rewrite(self,field,name,value):self.req[field]['sha256']=self.write(name,value)

    def reseal(self):
        # An independently authorized fixture producer can reseal to test deeper guards.
        roster=self.req['roster']['sha256']
        for field,name in [('predictions','q.json')]:
            data=self.read(name);data['roster_sha256']=roster;self.rewrite(field,name,data)
        for n,r in enumerate(self.req['targets']):
            data=self.read(r['path']);data['roster_sha256']=roster;r['sha256']=self.write(r['path'],data)
        self.req['bindings']['q_sha256']=self.req['predictions']['sha256']
        self.req['bindings']['target_sha256']=[r['sha256'] for r in self.req['targets']]
        if self.req['receipt']:
            self.req['bindings']['receipt_sha256']=self.req['receipt']['sha256']
            q=self.read('q.json');q['receipt_sha256']=self.req['receipt']['sha256'];self.rewrite('predictions','q.json',q)
            self.req['bindings']['q_sha256']=self.req['predictions']['sha256']

    def assert_reject_before_score(self):
        with patch('methods.ope.functional.score_rows',side_effect=AssertionError('costly work invoked')) as worker:
            with self.assertRaises((ContractViolation,ValidationError)):self.run_request()
            self.assertEqual(worker.call_count,0)

    def test_real_Ridge_artifacts_access_and_reward_mutation(self):
        result=self.run_request();self.assertEqual(result.status,'computed_conditional');self.assertEqual(result.eligible_windows,60)
        self.assertEqual(len(result.bootstrap_values),2000);self.assertEqual(result.independent_patients,30)
        receipt=self.read('receipt.json')
        for a in [0,1]:self.assertGreaterEqual(len({r['patient_id'] for r in receipt['rows'] if r['action']==a}),10)
        for stage in ['train','predict','score','mutated-score']:
            access=json.loads((E/(stage+'-access.json')).read_bytes());self.assertEqual(len(access['denied_actual_reads']),2)
            if 'score' in stage:
                self.assertFalse(access['sklearn_imported']);self.assertEqual(access['fit_learn_predict_choice_calls'],[])
        self.assertIn('fit',json.loads((E/'train-access.json').read_bytes())['fit_learn_predict_choice_calls'])
        self.assertIn('predict',json.loads((E/'predict-access.json').read_bytes())['fit_learn_predict_choice_calls'])
        hashes={p:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for p in ['q.json','policy-a.json','receipt.json','training.json']}
        r=self.read('rewards.json');r[0]['value']+=.1;self.rewrite('rewards','rewards.json',r)
        changed=self.run_request();self.assertNotEqual(result.dr,changed.dr)
        self.assertEqual(hashes,{p:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for p in hashes})

    def test_actual_training_guards_reject_before_Ridge_fit(self):
        from methods.ope.nuisance import train
        plan=self.read('plan.json');now=datetime.now(timezone.utc)
        plan.update(cutoff=(now+timedelta(minutes=5)).isoformat(),evaluation_start=(now+timedelta(days=2)).isoformat())
        self.write('plan.json',plan);original=self.read('training.json')
        mutations=[lambda r:r[0].update(patient_id='E00'),
            lambda r:r[0].update(x_available_at=r[0]['decision_at']),
            lambda r:r[0].update(reward_available_at=plan['cutoff']),
            lambda r:r.__delitem__(slice(4,None)),lambda r:r[0].update(x=float('nan')),
            lambda r:r[0].update(reward=11.)]
        for mutate in mutations:
            rows=deepcopy(original);mutate(rows);self.write('training.json',rows)
            with patch('sklearn.linear_model.Ridge.fit') as fit:
                with self.assertRaises(ValidationError):train(self.root,self.root)
                fit.assert_not_called()
        self.write('training.json',original)
        with patch('sklearn.linear_model.Ridge.fit',side_effect=RuntimeError('valid fixture reaches actual fit')) as fit:
            with self.assertRaisesRegex(RuntimeError,'valid fixture reaches actual fit'):train(self.root,self.root)
            self.assertEqual(fit.call_count,1)

    def test_raw_byte_hash_and_source_binding_rejection(self):
        for field in ['protocol','roster','rewards','predictions','receipt']:
            with self.subTest(field=field):
                path=self.root/self.req[field]['path'];raw=path.read_bytes();path.write_bytes(raw+b' ')
                self.assert_reject_before_score();path.write_bytes(raw)
        for name in ['training_sha256','plan_sha256','model_sha256','trainer_sha256','predictor_sha256','q_sha256']:
            old=self.req['bindings'][name];self.req['bindings'][name]='0'*64
            with self.subTest(binding=name):self.assert_reject_before_score()
            self.req['bindings'][name]=old

    def test_patient_time_row_action_and_training_mutations_before_score(self):
        original=deepcopy(self.req);files={p.name:p.read_bytes() for p in self.root.iterdir()}
        cases=[('patient',lambda r:r[0].update(patient_id='T0')),
            ('future_x',lambda r:r[0].update(x_available_at=r[0]['decision_at'])),
            ('before_cutoff',lambda r:r[0].update(decision_at=self.read('receipt.json')['plan']['cutoff'])),
            ('wrong_action',lambda r:r[0].update(action=2)),('duplicate_window',lambda r:r[1].update(patient_id=r[0]['patient_id'],window_id=r[0]['window_id']))]
        for name,mutate in cases:
            self.req=deepcopy(original)
            for n,raw in files.items():(self.root/n).write_bytes(raw)
            roster=self.read('roster.json');mutate(roster);self.rewrite('roster','roster.json',roster);self.reseal()
            with self.subTest(case=name):self.assert_reject_before_score()
        self.req=deepcopy(original)
        for n,raw in files.items():(self.root/n).write_bytes(raw)
        q=self.read('q.json');q['rows'].reverse();self.rewrite('predictions','q.json',q);self.req['bindings']['q_sha256']=self.req['predictions']['sha256']
        self.assert_reject_before_score()
        for mutate in [lambda r:r['rows'][0].update(patient_id='E00'),
                       lambda r:r['rows'][0].update(reward_available_at=r['plan']['cutoff']),
                       lambda r:r.update(rows=r['rows'][:4]),lambda r:r['plan'].update(basis='future_reward')]:
            self.req=deepcopy(original)
            for n,raw in files.items():(self.root/n).write_bytes(raw)
            receipt=self.read('receipt.json');mutate(receipt);self.rewrite('receipt','receipt.json',receipt);self.reseal();self.assert_reject_before_score()

    def test_missing_absent_training_insufficient_units_and_pooled_dependence(self):
        for state in ['missing','pending','undefined']:
            rs=self.read('rewards.json');rs[0].update(status=state,value=None);self.rewrite('rewards','rewards.json',rs)
            with patch('methods.ope.functional.score_rows') as worker:
                self.assertEqual(self.run_request().status,'abstained');worker.assert_not_called()
        self.req['receipt']=None
        with patch('methods.ope.functional.score_rows') as worker:
            self.assertEqual(self.run_request().reason,'no_valid_earlier_training');worker.assert_not_called()
        self.req=json.loads((self.root/'request.json').read_bytes())
        self.req['logging_regime']='pooled_adaptive';self.assert_reject_before_score()

    def test_unavailable_denominator_no_eligible_and_unit_guard(self):
        for all_unavailable in [False,True]:
            roster=self.read('roster.json')
            for row in roster:
                if all_unavailable or row['patient_id']=='E00':row.update(available_actions=[],logging_probabilities=[0.,0.],action=None)
            self.rewrite('roster','roster.json',roster)
            for target in self.req['targets']:
                data=self.read(target['path'])
                for i,row in enumerate(roster):
                    if not row['available_actions']:data['rows'][i]['probabilities']=[0.,0.]
                target['sha256']=self.write(target['path'],data)
            self.reseal()
            with patch('methods.ope.functional.score_rows') as worker:
                result=self.run_request();worker.assert_not_called()
                self.assertEqual(result.status,'undefined' if all_unavailable else 'abstained')
                self.assertEqual(result.reason,'no_eligible_windows' if all_unavailable else 'fewer_than_30_independent_evaluation_patients')
        self.req['unit']='ISI_points'
        with self.assertRaises(ValidationError):self.run_request()


if __name__=='__main__':unittest.main()
