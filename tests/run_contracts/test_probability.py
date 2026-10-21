"""Analytical and hand-authored wire fixtures; no producer or pilot executions."""
import copy
from math import sqrt
import unittest

import numpy as np

from fixtures import full_key, load
from contracts.runs.common import canonical, sha256
from contracts.runs.probability import (COMPONENTS, PathOutcome, PilotTrial, ProbabilityEvidence, TruthFilterReceipt,
    StructuralDerivation, pilot_statistics, require_refinement, require_trial, truth_statistics)


class ProbabilityContracts(unittest.TestCase):
    def test_analytic_bernoulli_variance_mixture_and_zero_trials_are_distinct(self):
        self.assertAlmostEqual(sqrt(.02*.98/30),.025560386016907754)
        self.assertAlmostEqual(.98**30,.5454843193824369)
        p=.001;var_q=.0001;n=30
        independent=sqrt(p*(1-p)/n)
        shared=sqrt(p*(1-p)/n+(1-1/n)*var_q)
        self.assertAlmostEqual(independent,.005770615218501403)
        self.assertAlmostEqual(shared,.011400292393911078)
        # Exact three-point shared-filter mixture moments; no random pilot run.
        from scipy.stats import binom
        values=np.arange(31)/30;weights=(p/.101)*binom.pmf(np.arange(31),30,.101)
        weights[0]+=1-p/.101
        variance=np.sum(weights*(values-p)**2)
        fourth=np.sum(weights*(values-p)**4)
        delta=sqrt(fourth-variance**2)/(2*sqrt(variance)*sqrt(1000))
        self.assertAlmostEqual(delta,.002548819940811536)
        self.assertAlmostEqual(shared-1.645*delta,.007207483591276102)
        for probability in (.5,.02):
            self.assertAlmostEqual(binom.var(30,probability)/30**2,probability*(1-probability)/30)

    def fixture_counts(self):
        # Deliberately deterministic many-zero contract fixture, not calibration.
        column=np.zeros(1000,dtype=np.int64);column[::2]=1
        return np.repeat(column[:,None],6,axis=1)

    def test_empirical_lower_binding_retains_zero_trials_and_cp_not_wilson_acceptance(self):
        counts=self.fixture_counts();stats=pilot_statistics(counts/30,counts,30)
        self.assertTrue((stats['binding']>0).all())
        self.assertTrue((stats['binding']<=stats['lower']).all())
        self.assertTrue((stats['binding']<=stats['analytic_lower']).all())
        with self.assertRaises(ValueError):pilot_statistics(np.zeros((1000,6)),np.zeros((1000,6),dtype=int),30)
        with self.assertRaises(ValueError):pilot_statistics(counts[:500]/30,counts[:500],30)
        bad=counts/30;bad[0,0]=float('nan')
        with self.assertRaises(ValueError):pilot_statistics(bad,counts,30)
        with self.assertRaises(ValueError):pilot_statistics(counts/30,counts+1,30)

    def test_final_epsilon_and_paired_variance_binding_refinement(self):
        counts=self.fixture_counts();x=counts/30;s=pilot_statistics(x,counts,30)
        epsilon=np.minimum(.001,.1*s['binding'])
        require_refinement([x,x,x],[s,s,s],epsilon)
        altered=x.copy();altered[::4]=2/30
        changed=pilot_statistics(altered,(altered*30).astype(int),30)
        with self.assertRaises(ValueError):require_refinement([x,x,altered],[s,s,changed],epsilon)
        # Same marginal means/SD can still have paired stochastic disagreement.
        shifted=np.roll(x,1,axis=0);other=pilot_statistics(shifted,(shifted*30).astype(int),30)
        with self.assertRaises(ValueError):require_refinement([x,x,shifted],[s,s,other],epsilon)
        tighter=np.minimum(epsilon,.1*np.repeat(.00001,6))
        self.assertTrue((tighter<epsilon).all())

    def trial(self,*,shared=False,relabel=False):
        target='a'*64;config='conditional-H';level=1024;cell='S01.reference.n60';protocol='remission-g1-v1'
        def key(process,environment,namespace='truth'):
            stream='p'+sha256(canonical(dict(configuration=config,level=level,target_sha256=target,**({} if process=='probability_allocation' else dict(environment=environment)))))[:48]
            return full_key(protocol=protocol,phase='pilot',namespace=namespace,scenario=cell,replicate=0,patient=environment,time_index=level,process=process,stream=stream)
        rows=[]
        for i in range(60):
            env='env-'+str(i);identity='shared' if shared else str(i)
            receipt=dict(producer_run='fixture-no-engine',environment=env,keys=[key(p,env) for p in ('probability_filter','probability_selection','probability_rollout')])
            for name in ('realization_sha256','ancestry_sha256','innovations_sha256','posterior_selection_sha256','rollout_sha256'):
                receipt[name]=sha256((name+identity).encode())
            if relabel:receipt['realization_sha256']=sha256(b'underlying-replayed-filter')
            rows.append(dict(id=env,arm='intervention' if i<30 else 'comparator',outcome=dict(survival_day42=True,admission_by_day42=False,alive_outpatient_day42=True,death_day=None,admission_day=None),filter_execution=receipt))
        return load(PilotTrial,dict(trial=0,allocation_key=key('probability_allocation',config,'assignment'),environments=rows)),dict(conditional=True,n_arm=30,protocol=protocol,cell=cell,config=config,level=level,target_sha256=target,producer_run='fixture-no-engine')

    def test_correct_environment_unit_shared_filter_and_relabelled_realization_faults(self):
        trial,args=self.trial();counts=require_trial(trial,seen=set(),**args)
        self.assertEqual(counts,[30,0,30,30,0,30])
        for shared,relabel in [(True,False),(False,True)]:
            trial,args=self.trial(shared=shared,relabel=relabel)
            with self.assertRaises(ValueError):require_trial(trial,seen=set(),**args)
        trial,args=self.trial();bad=trial.model_dump(mode='json');bad['environments'].pop()
        with self.assertRaises(ValueError):require_trial(load(PilotTrial,bad),seen=set(),**args)
        trial,args=self.trial();args['target_sha256']='b'*64
        with self.assertRaises(ValueError):require_trial(trial,seen=set(),**args)
        trial,args=self.trial();args['producer_run']='another-run'
        with self.assertRaises(ValueError):require_trial(trial,seen=set(),**args)

    def test_complete_death_admission_outpatient_and_paired_covariance(self):
        path=load(PathOutcome,dict(survival_day42=False,admission_by_day42=True,alive_outpatient_day42=False,death_day=20.,admission_day=10.))
        self.assertEqual(path.vector(),[0,1,0])
        bad=path.model_dump();bad['alive_outpatient_day42']=True
        with self.assertRaises(ValueError):load(PathOutcome,bad)
        bad=path.model_dump();bad['admission_day']=21.
        with self.assertRaises(ValueError):load(PathOutcome,bad)
        counts=np.repeat((5000+np.tile([-1,1],16))[:,None],6,axis=1)
        stats=truth_statistics(counts,conditional=False,epsilon=np.repeat(.001,6))
        self.assertAlmostEqual(stats['covariance'][0,3],stats['mcse'][0]**2)
        self.assertIsNotNone(stats['pooled_iid_mcse'])

    def test_iid_and_conditional_zero_boundary_caps_structural_proof_scope(self):
        zeros=np.zeros((1000,6),dtype=int);epsilon=np.repeat(.001,6)
        iid=truth_statistics(zeros,conditional=False,epsilon=epsilon)
        self.assertLess(iid['boundary_error'][0],.001)
        self.assertAlmostEqual(1-.05**(1/1000),.0029912495450953314)
        with self.assertRaises(ValueError):truth_statistics(zeros,conditional=True,epsilon=epsilon)
        proofs=dict.fromkeys(COMPONENTS,0)
        structural=truth_statistics(zeros,conditional=True,epsilon=epsilon,proofs=proofs)
        self.assertEqual(structural['boundary_error'].tolist(),[0.]*6)
        with self.assertRaises(ValueError):truth_statistics(np.zeros((1001,6),dtype=int),conditional=False,epsilon=epsilon)
        with self.assertRaises(ValueError):truth_statistics(np.repeat([[5000]*6],32,axis=0),conditional=True,epsilon=epsilon)
        raw=dict(request_sha256='a'*64,component='intervention.admission_by_day42',value=0,method='analytic',implementation=dict(id='independent-fixture',version='1.0',sha256='b'*64),proof_kind='known_death',no_hidden_numerical_integration=True,derivation='Known death cannot remove an earlier hospital admission.')
        with self.assertRaises(ValueError):load(StructuralDerivation,raw)

    def test_structural_zero_is_distinct_from_zero_sample_pilot(self):
        zero=np.zeros((1000,6),dtype=int)
        with self.assertRaises(ValueError):pilot_statistics(zero/30,zero,30)
        stats=pilot_statistics(zero/30,zero,30,proofs=dict.fromkeys(COMPONENTS,0))
        self.assertTrue(stats['structural'].all())
        require_refinement([zero/30]*3,[stats]*3,np.repeat(.001,6))

    def test_truth_diagnostic_receipts_bind_actual_run_target_batch_and_final_level(self):
        from types import SimpleNamespace
        request=SimpleNamespace(run_id='fixture-run',cell_id='S01.reference.n60',bindings=SimpleNamespace(protocol=SimpleNamespace(id='remission-g1-v1')))
        key=full_key(phase='confirmation',namespace='truth',scenario=request.cell_id,replicate=0,patient='truth-filter-0',time_index=16384,process='probability_truth_filter',stream='p'+'a'*48)
        data=dict(producer_run='fixture-run',filter_index=0,particles=16384,key=key,realization_sha256='b'*64,ancestry_sha256='c'*64,innovations_sha256='d'*64)
        receipt=load(TruthFilterReceipt,data)
        receipt.require_binding(request,batch_index=0,target_sha256='a'*64,particles=16384)
        for name,value in [('producer_run','different-run'),('particles',4096),('realization_sha256','not-a-hash')]:
            bad=copy.deepcopy(data);bad[name]=value
            with self.subTest(field=name),self.assertRaises(ValueError):load(TruthFilterReceipt,bad).require_binding(request,batch_index=0,target_sha256='a'*64,particles=16384)
        with self.assertRaises(ValueError):receipt.require_binding(request,batch_index=1,target_sha256='a'*64,particles=16384)
        with self.assertRaises(ValueError):receipt.require_binding(request,batch_index=0,target_sha256='e'*64,particles=16384)


if __name__=='__main__':unittest.main()
