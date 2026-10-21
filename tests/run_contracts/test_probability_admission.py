"""Complete pure-IO qualification fixture, not a generated pilot/truth result."""
import copy
import json
import unittest

import numpy as np
from scipy.stats import binom

import test_evaluator as evaluator
from fixtures import artifact, full_key, load, wire_investigation
from contracts.runs.common import canonical, sha256
from contracts.runs.private import CELLS, TruthRequest, TruthResponse
from contracts.runs.private_admission import verify_truth
from contracts.runs.probability import COMPONENTS, ProbabilityEvidence, qualify_probability, qualify_symptom_pilot


class ProbabilityAdmission(unittest.TestCase):
    def test_authenticated_complete_paired_fixture_roundtrip_and_binding_faults(self):
        helper=evaluator.EvaluatorContracts();helper.setUp()
        try:
            root=helper.root;cell=next(k for k,v in CELLS.items() if v['estimand']=='EST-INT' and k.endswith('.n60'))
            data=helper.request(cell=cell)
            plan=artifact(root,'probability-pilot-plan','probability/plan.json',dict(kind='probability_pilot_plan',rule=data['bindings']['probability_precision'],conditional=False,configurations=[dict(id='fixture-config',trial_size=60)]),'evaluator_result')
            data['comparator_pilot']=plan;request=load(TruthRequest,data)
            request_hash=sha256(canonical(request.model_dump(mode='json')))
            trials=[];configuration='fixture-config'
            for j in range(1000):
                # Deterministic binomial quantiles are explicitly hand fixtures.
                count=int(binom.ppf((j+.5)/1000,30,.5));rows=[]
                for i in range(60):
                    flag=i%30<count
                    rows.append(dict(id='env-'+str(i),arm='intervention' if i<30 else 'comparator',outcome=dict(survival_day42=flag,admission_by_day42=flag,alive_outpatient_day42=flag,death_day=None if flag else 20.,admission_day=10. if flag else None,conditional_isi=(12.+4.*(i%2)) if flag else None),filter_execution=None))
                stream='p'+sha256(canonical(dict(configuration=configuration,level=0,target_sha256=request_hash)))[:48]
                key=full_key(protocol=request.bindings.protocol.id,phase='pilot',namespace='assignment',scenario=cell,replicate=j,patient=configuration,time_index=0,process='probability_allocation',stream=stream)
                trials.append(artifact(root,'trial-'+str(j),'probability/trials/'+str(j)+'.json',dict(trial=j,allocation_key=key,environments=rows),'evaluator_result'))
            diagnostic=artifact(root,'fixture-diagnostic','probability/diagnostic.json',dict(kind='hand_authored_contract_fixture',actual_producer_execution=False,claim='No simulation or independence qualification; only artifact admission exercised'),'evaluator_result')
            path_artifacts={}
            for count in (4999,5001):
                paths=[]
                for i in range(10000):
                    flag=i<count;outcome=dict(survival_day42=flag,admission_by_day42=flag,alive_outpatient_day42=flag,death_day=None if flag else 20.,admission_day=10. if flag else None,conditional_isi=14. if flag else None)
                    paths.append(dict(id='pair-'+str(i),intervention=outcome,comparator=outcome))
                path_artifacts[count]=artifact(root,'paths-'+str(count),'probability/paths-'+str(count)+'.json',paths,'evaluator_result')
            batches=[]
            for b in range(32):
                key=full_key(protocol=request.bindings.protocol.id,phase='confirmation',namespace='truth',scenario=cell,replicate=b,patient='population',time_index=42,process='probability_truth_batch',stream='p'+request_hash[:48])
                batches.append(dict(id='batch-'+str(b),independent_outer_key=key,paths=path_artifacts[4999 if b%2 else 5001],conditional_filter_receipts=None))
            counts=np.repeat(np.array([5001 if b%2==0 else 4999 for b in range(32)])[:,None],6,axis=1)
            truth_hash=sha256(canonical(batches));investigation=wire_investigation(counts,request_hash=request_hash,truth_hash=truth_hash)
            investigation_ref=artifact(root,'wire-only-investigation','probability/fixture-investigation.json',investigation[0],'evaluator_result')
            authorities={investigation_ref['sha256']:investigation[1]}
            evidence=dict(rule=data['bindings']['probability_precision'],request_sha256=request_hash,unit='probability',component_order=list(COMPONENTS),conditional=False,required_configurations=[configuration],pilots=[dict(configuration=configuration,conditional=False,n_arm=30,history_sha256=None,levels=[dict(particles=0,trials=trials)],dispersion_review='consistent',independent_iid_check=diagnostic,producer_execution_qualification=diagnostic)],batches=batches,structural_proofs=[],actual_matched_estimator_se=None,conditional_accuracy=None,diagnostic_filters_per_level=32,iid_investigation=investigation_ref)
            qualified=qualify_probability(load(ProbabilityEvidence,evidence),root,request,investigation_authorities=authorities)
            with self.assertRaisesRegex(ValueError,'out-of-band'):
                qualify_probability(load(ProbabilityEvidence,evidence),root,request)
            self.assertEqual(qualified['mean'].tolist(),[.5]*6)
            # All eight original estimand components remain separate.
            def arm(which,action):return dict(action=action,survival_day42=.5,admission_by_day42=.5,alive_outpatient_day42=.5,conditional_isi=dict(numerator_count=160000,denominator_count=320000,conditioning_probability=.5,isi=dict(status='estimated',value=14.,unit='ISI_points',standard_error=0.,interval=None)),**qualified['event_times'][which])
            result=dict(schema_version='1.0.0',synthetic=True,kind='interruption_result',estimand_id='EST-INT',estimand_version='1.0.0',horizon_days=42,intervention=arm('intervention',request.target.estimand.intervention),comparator=arm('comparator',request.target.estimand.comparator),interpretation='intervention_specific_conditional_populations_not_common_survivors',overall_ranking='suppressed')
            response=helper.response(request,result=result);response['batches']=32
            evidence_artifact=artifact(root,'probability-evidence','probability/evidence.json',evidence,'evaluator_result')
            from contracts.runs.common import Artifact
            evidence_ref=load(Artifact,evidence_artifact)
            symptom_refs={};symptom_bounds={}
            for which in ('intervention','comparator'):
                component=which+'.conditional_isi'
                symptom_refs[which]=artifact(root,'symptom-'+which,'probability/symptom-'+which+'.json',dict(kind='interruption_symptom_pilot_binding',request_sha256=request_hash,component=component,comparison='own_arm_alive_outpatient_ISI_mean',unit='ISI_points',probability_evidence=evidence_artifact,trial_refs_sha256=qualified['pilot_trial_refs_sha256']),'evaluator_result')
                symptom_bounds[which]=qualify_symptom_pilot(load(Artifact,symptom_refs[which]),root,request,evidence_ref,qualified,component)
            response['interruption_precision']=[]
            for which in ('intervention','comparator'):
                for name in ('survival_day42','admission_by_day42','alive_outpatient_day42','conditional_isi'):
                    component=which+'.'+name;index=COMPONENTS.index(component) if name!='conditional_isi' else None
                    response['interruption_precision'].append(dict(component=component,status='computed',numerical_standard_error=float(qualified['mcse'][index]) if index is not None else 0.,smallest_estimator_se=float(qualified['matched_se'][index]) if index is not None else symptom_bounds[which],matched_pilot=plan if index is not None else symptom_refs[which],probability_evidence=evidence_artifact if index is not None else None))
            def verify(reqraw,resraw,root,**kwargs):return verify_truth(reqraw,resraw,root,investigation_authorities=authorities,**kwargs)
            raw_request=canonical(request.model_dump(mode='json'));raw_response=canonical(load(TruthResponse,response).model_dump(mode='json'))
            verify(raw_request,raw_response,root,request_sha256=sha256(raw_request),response_sha256=sha256(raw_response),evaluator=helper.authority)
            partial=copy.deepcopy(response);partial.update(status='undefined',reason='Retained interruption vector has an undefined component')
            partial['interruption_precision'][3]['status']='undefined'
            rawpartial=canonical(partial)
            verify(raw_request,rawpartial,root,request_sha256=sha256(raw_request),response_sha256=sha256(rawpartial),evaluator=helper.authority)
            partial['result']['intervention']['survival_day42']=.51
            rawpartial=canonical(partial)
            with self.assertRaises(ValueError):verify(raw_request,rawpartial,root,request_sha256=sha256(raw_request),response_sha256=sha256(rawpartial),evaluator=helper.authority)
            for name,value in [('request_sha256','b'*64),('unit','ISI_points'),('required_configurations',['missing-config'])]:
                bad=copy.deepcopy(evidence);bad[name]=value
                with self.subTest(field=name),self.assertRaises(ValueError):qualify_probability(load(ProbabilityEvidence,bad),root,request,investigation_authorities=authorities)
            bad=copy.deepcopy(evidence);bad['actual_matched_estimator_se']=[0.]*6
            with self.assertRaises(ValueError):qualify_probability(load(ProbabilityEvidence,bad),root,request,investigation_authorities=authorities)
            bad=copy.deepcopy(evidence);bad['batches'][1]['independent_outer_key']=bad['batches'][0]['independent_outer_key']
            with self.assertRaises(ValueError):qualify_probability(load(ProbabilityEvidence,bad),root,request,investigation_authorities=authorities)
            bad=copy.deepcopy(response);bad['result']['intervention']['survival_day42']=.51
            raw=canonical(bad)
            with self.assertRaises(ValueError):verify(raw_request,raw,root,request_sha256=sha256(raw_request),response_sha256=sha256(raw),evaluator=helper.authority)
            for label in ('missing_symptom_pilot','probability_pilot_substitution','inflated_symptom_se','wrong_death_times','omitted_admission_times','wrong_nested_se','unqualified_interval'):
                bad=copy.deepcopy(response)
                if label=='missing_symptom_pilot':bad['interruption_precision'][3]['matched_pilot'].update(path='missing/pilot.json',sha256='f'*64)
                elif label=='probability_pilot_substitution':bad['interruption_precision'][3]['matched_pilot']=plan
                elif label=='inflated_symptom_se':bad['interruption_precision'][3]['smallest_estimator_se']=1000000.
                elif label=='wrong_death_times':bad['result']['intervention']['death_times_days']=[999.]
                elif label=='omitted_admission_times':bad['result']['intervention']['admission_times_days']=[]
                elif label=='wrong_nested_se':bad['result']['intervention']['conditional_isi']['isi']['standard_error']=999.
                else:bad['result']['intervention']['conditional_isi']['isi']['interval']=dict(lower=0.,upper=28.,level=.95,interval_type='confidence')
                raw=canonical(bad)
                with self.subTest(label=label),self.assertRaises((ValueError,FileNotFoundError)):verify(raw_request,raw,root,request_sha256=sha256(raw_request),response_sha256=sha256(raw),evaluator=helper.authority)
        finally:helper.tearDown()


if __name__=='__main__':unittest.main()
