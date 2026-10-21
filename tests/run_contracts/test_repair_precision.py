"""Rejected2a regressions; deterministic wire fixtures grant no producer claims."""
import copy
import json
import unittest

import numpy as np
from scipy.stats import binom

from fixtures import CUTOFF, artifact, canonical, load, sha256, wire_investigation
from contracts.runs.probability import (COMPONENTS, IIDInvestigationAuthority,
    qualify_symptom_pilot, symptom_pilot_statistics, truth_statistics)


class RepairPrecision(unittest.TestCase):
    def test_iid_both_uncertainties_and_every_investigation_is_trusted_and_bound(self):
        counts=np.repeat((5000+np.tile([-1,1],16))[:,None],6,axis=1)
        proof=wire_investigation(counts)
        with self.assertRaisesRegex(ValueError,'pooled IID'):
            truth_statistics(counts,conditional=False,epsilon=np.repeat(.0001,6),investigation=proof)
        with self.assertRaisesRegex(ValueError,'separately trusted'):
            truth_statistics(counts,conditional=False,epsilon=np.repeat(.001,6))
        # Wire-only investigation may bind this deliberately underdispersed
        # diagnostic fixture; it does not certify an actual IID producer.
        truth_statistics(counts,conditional=False,epsilon=np.repeat(.001,6),investigation=proof)
        for field,value in [('disposition','unresolved'),('raw_counts_sha256','c'*64),('request_sha256','d'*64),('truth_evidence_sha256','e'*64),('independent_unit','conditional_descendant'),('independent_units',640000),('batch_mcse',[0.]*6),('pooled_iid_mcse',[0.]*6),('batch_covariance',[[0.]*6]*6)]:
            report=json.loads(proof[0]);report[field]=value;raw=canonical(report)
            authority=proof[1].model_dump(mode='json');authority['sha256']=sha256(raw)
            with self.subTest(field=field),self.assertRaises(ValueError):
                truth_statistics(counts,conditional=False,epsilon=np.repeat(.001,6),investigation=(raw,load(IIDInvestigationAuthority,authority),proof[2],proof[3]))
        authority=proof[1].model_dump(mode='json');authority['sha256']='f'*64
        with self.assertRaises(ValueError):truth_statistics(counts,conditional=False,epsilon=np.repeat(.001,6),investigation=(proof[0],load(IIDInvestigationAuthority,authority),proof[2],proof[3]))
        with self.assertRaises(ValueError):truth_statistics(counts,conditional=False,epsilon=np.repeat(.001,6),investigation=(b'{"consistent":true}',proof[1],proof[2],proof[3]))
        authority=proof[1].model_dump(mode='json');authority['sha256']=sha256(b'{"consistent":true}')
        with self.assertRaises(ValueError):truth_statistics(counts,conditional=False,epsilon=np.repeat(.001,6),investigation=(b'{"consistent":true}',load(IIDInvestigationAuthority,authority),proof[2],proof[3]))
        authority=proof[1].model_dump(mode='json');authority['allow_contract_fixture']=False
        with self.assertRaises(ValueError):truth_statistics(counts,conditional=False,epsilon=np.repeat(.001,6),investigation=(proof[0],load(IIDInvestigationAuthority,authority),proof[2],proof[3]))

    def test_ordinary_iid_quantile_control_and_conditional_units_do_not_pool_descendants(self):
        column=binom.ppf((np.arange(32)+.5)/32,10000,.5).astype(int)
        counts=np.repeat(column[:,None],6,axis=1)
        stats=truth_statistics(counts,conditional=False,epsilon=np.repeat(.001,6),investigation=wire_investigation(counts))
        self.assertLess(stats['mcse'][0],.001);self.assertLess(stats['pooled_iid_mcse'][0],.001)
        with self.assertRaises(ValueError):truth_statistics(counts,conditional=True,epsilon=np.repeat(.001,6),investigation=wire_investigation(counts))
        conditional=truth_statistics(counts,conditional=True,epsilon=np.repeat(.001,6))
        self.assertIsNone(conditional['pooled_iid_mcse'])

    def test_symptom_policy_recomputes_realized_trial_se_and_rms_lower_limit(self):
        values=[[12.,16.] for _ in range(1000)]
        stats=symptom_pilot_statistics(values)
        self.assertEqual(stats['binding'],2.)
        self.assertEqual(stats['rms_se'],2.)
        self.assertEqual(stats['rms_mcse'],0.)
        self.assertEqual(stats['rms_lower'],2.)
        for invalid in (values[:999],[[14.,14.] for _ in range(1000)],[[14.] for _ in range(1000)],[[None,14.] for _ in range(1000)]):
            with self.assertRaises(ValueError):symptom_pilot_statistics(invalid)
        varying=[[10.,14.,18.] if j%2 else [12.,16.] for j in range(1000)]
        result=symptom_pilot_statistics(varying)
        ses=np.array([np.std(row,ddof=1)/np.sqrt(len(row)) for row in varying]);rms=np.sqrt(np.mean(ses**2))
        lower=rms-1.645*np.std(ses**2,ddof=1)/(2*rms*np.sqrt(1000))
        self.assertAlmostEqual(result['binding'],min(ses.min(),lower))

    def test_conditional_symptom_accuracy_and_later_actual_se_use_isi_epsilon(self):
        # Controlled post-authentication validator fixture; full raw IO is
        # separately exercised in ProbabilityAdmission, not asserted here.
        import test_evaluator as evaluator
        from contracts.domain.boundaries import ObservedHistory
        from contracts.runs.common import Artifact
        from contracts.runs.private import CELLS, TruthRequest, TruthResponse, validate_truth_response
        from services.foundation.store import instant
        helper=evaluator.EvaluatorContracts();helper.setUp()
        try:
            cell=next(k for k,v in CELLS.items() if v['estimand']=='EST-INT' and k.endswith('.n60'))
            data=helper.request(cell=cell,truth_kind='observed_history_conditional_average')
            history_ref=helper.data['export'].partitions[0].history
            history=ObservedHistory.model_validate_json((helper.root/history_ref.path).read_bytes()).project(instant(CUTOFF))
            data.update(patient_id=history.patient_id,information_set='available_observed_history',observed_history=artifact(helper.root,'H','repair/H.json',history.model_dump(mode='json'),'observed'),smallest_estimator_se=.001)
            request=load(TruthRequest,data);dummy=artifact(helper.root,'private-evidence','repair/post-auth-fixture.json',dict(kind='post_auth_validator_fixture_not_a_producer_result'),'evaluator_result');evidence_ref=load(Artifact,dummy)
            stats=symptom_pilot_statistics([[12.,16.] for _ in range(1000)])
            qualified=dict(mean=np.array([.9,.2,.7,.9,.2,.7]),mcse=np.repeat(.00001,6),matched_se=np.repeat(.1,6),batches=32,structural_proofs={},conditional_isi=[dict(status='computed',count=224000,value=14.,mcse=.000005)]*2,event_times={arm:dict(death_times_days=[20.],admission_times_days=[10.]) for arm in ('intervention','comparator')},symptom_pilots={arm:[[stats,stats,stats]] for arm in ('intervention','comparator')},pilot_trial_refs_sha256='a'*64,symptom_matched_se={})
            bindings={}
            for arm in ('intervention','comparator'):
                component=arm+'.conditional_isi';bindings[arm]=artifact(helper.root,'pilot-'+arm,'repair/pilot-'+arm+'.json',dict(kind='interruption_symptom_pilot_binding',request_sha256=sha256(canonical(request.model_dump(mode='json'))),component=component,comparison='own_arm_alive_outpatient_ISI_mean',unit='ISI_points',probability_evidence=dummy,trial_refs_sha256='a'*64),'evaluator_result')
                qualified['symptom_matched_se'][component]=qualify_symptom_pilot(load(Artifact,bindings[arm]),helper.root,request,evidence_ref,qualified,component)
                self.assertEqual(qualified['symptom_matched_se'][component],.001)
            def arm(action):return dict(action=action,survival_day42=.9,admission_by_day42=.2,alive_outpatient_day42=.7,conditional_isi=dict(numerator_count=224000,denominator_count=320000,conditioning_probability=.7,isi=dict(status='estimated',value=14.,unit='ISI_points',standard_error=.000005,interval=None)),death_times_days=[20.],admission_times_days=[10.])
            vector=dict(schema_version='1.0.0',synthetic=True,kind='interruption_result',estimand_id='EST-INT',estimand_version='1.0.0',horizon_days=42,intervention=arm(request.target.estimand.intervention),comparator=arm(request.target.estimand.comparator),interpretation='intervention_specific_conditional_populations_not_common_survivors',overall_ranking='suppressed')
            response=helper.response(request,result=vector);response['batches']=32;response['interruption_precision']=[]
            for which in ('intervention','comparator'):
                for event in ('survival_day42','admission_by_day42','alive_outpatient_day42','conditional_isi'):
                    symptom=event=='conditional_isi'
                    response['interruption_precision'].append(dict(component=which+'.'+event,status='computed',numerical_standard_error=.000005 if symptom else .00001,smallest_estimator_se=.001 if symptom else .1,matched_pilot=bindings[which] if symptom else helper.pilot,probability_evidence=None if symptom else dummy))
            with self.assertRaisesRegex(ValueError,'separate symptom accuracy'):validate_truth_response(request,load(TruthResponse,response),qualified_probability=qualified)
            response['conditional_accuracy']=dict(particle_levels=[1024,4096,16384],filters_per_level=32,successive_differences=[.0001,.0001],paired_standard_errors=[0.,0.],quadrature_change=.0001,within_filter_mcse=.0001,between_filter_mcse=.0001,independent_reduced_checks=[helper.pilot])
            with self.assertRaisesRegex(ValueError,'budget unresolved'):validate_truth_response(request,load(TruthResponse,response),qualified_probability=qualified)
            for name in ('quadrature_change','within_filter_mcse','between_filter_mcse'):response['conditional_accuracy'][name]=.000001
            response['conditional_accuracy']['successive_differences']=[.000001,.000001]
            validate_truth_response(request,load(TruthResponse,response),qualified_probability=qualified)
            partial=copy.deepcopy(response);partial.update(status='pending',reason='Symptom precision remains pending')
            partial['interruption_precision'][3]['status']='pending'
            partial['result']['intervention']['conditional_isi'].update(numerator_count=7,denominator_count=10)
            with self.assertRaisesRegex(ValueError,'actual eligible count'):
                validate_truth_response(request,load(TruthResponse,partial),qualified_probability=qualified)
            # A tighter actual comparison changes the recomputed minimum. It
            # cannot be ignored while retaining the older generous bound.
            smaller=data|dict(smallest_estimator_se=.000001);new_request=load(TruthRequest,smaller)
            binding=json.loads((helper.root/bindings['intervention']['path']).read_bytes());binding['request_sha256']=sha256(canonical(new_request.model_dump(mode='json')))
            ref=artifact(helper.root,'pilot-new','repair/pilot-new.json',binding,'evaluator_result')
            new_bound=qualify_symptom_pilot(load(Artifact,ref),helper.root,new_request,evidence_ref,qualified,'intervention.conditional_isi')
            self.assertEqual(new_bound,.000001)
            bad=copy.deepcopy(response);bad['interruption_precision'][3]['smallest_estimator_se']=new_bound
            with self.assertRaises(ValueError):load(TruthResponse,bad)
        finally:helper.tearDown()


if __name__=='__main__':unittest.main()
