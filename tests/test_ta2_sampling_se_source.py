"""Hand-scalar/source controls with fabricated cohorts, never fit/study evidence."""
import ast
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from functools import lru_cache
import json
import math
from pathlib import Path
from unittest.mock import patch
import unittest

from contracts.domain.analysis import (AnalysisHistory,PROTOCOL_REF,ESTIMAND_REF,
    SCENARIO_REF,canonical,sha,reference,Effect)
from contracts.domain.borrowing import SourceBundle
from contracts.domain.cohort import CohortHistory,CohortManifest,CohortResult,COORDINATE_REF,make_cohort_input
from methods.truth import sampling_se as s

ROOT=Path(__file__).resolve().parents[1]
ORIGIN=datetime(2026,1,1,12,tzinfo=timezone.utc)


def header(patient,name,kind,at):
    return dict(record_id=patient+'-'+name,patient_id=patient,kind=kind,event_at=at.isoformat(),recorded_at=at.isoformat(),
        available_at=at.isoformat(),lineage_id=patient+'-'+name,revision=1,supersedes=None,duplicate_of=None,record_status='active')


def history(patient):
    # Complete typed inert grid, hand constants only. No generator/data/fit call.
    records=[dict(**header(patient,'plan','assignment',ORIGIN),option='behavioral_continue',experimental=True)]
    for day in range(1,15):
        records.append(dict(**header(patient,'q'+str(day),'daily_report',ORIGIN+timedelta(days=day,minutes=-1)),sleep_quality=7.,missingness='observed'))
        records.append(dict(**header(patient,'d'+str(day),'delivery',ORIGIN+timedelta(days=day-1,hours=8)),assignment_id=patient+'-plan',
            option='behavioral_continue',stage='taken',adherence=1.,rescue=False,protocol_deviations=[]))
    for day in (0,14):
        end=ORIGIN+timedelta(days=day,hours=-1)
        records.append(dict(**header(patient,'isi'+str(day),'isi',end+timedelta(minutes=59)),total=14,
            instrument_version='ISI-7-synthetic-14d-v1',recall_days=14,recall_start=(end-timedelta(days=14)).isoformat(),recall_end=end.isoformat()))
    return AnalysisHistory.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,kind='poc_analysis_history',
        version='poc-analysis-history-v1',patient_id=patient,cutoff=(ORIGIN+timedelta(days=14)).isoformat(),origin=ORIGIN.isoformat(),
        protocol=PROTOCOL_REF,eligibility='uninterrupted-v1-behavioral-no-prompt',records=records,
        provenance=[{k:v for k,v in r.items() if k in header(patient,'','',ORIGIN)} for r in records])))


@lru_cache(maxsize=1)
def prepared():
    # Existing PUBLIC frozen source-summary JSON is parsed only to construct
    # lawful typed V1 input identity, not analyzed or treated as a genuine fit.
    source=SourceBundle.model_validate_json((ROOT/'services/foundation/studies/source-7c97862d.json').read_bytes())
    planned=[];inputs={}
    for index in range(33):
        rid=f'TEST-INERT-cohort-{index:02}';members=[f'{rid}-patient-{j:02}' for j in range(12)]
        histories=[history(patient) for patient in members]
        manifest=dict(schema='poc-cohort-manifest-v1/1.0.0',cohort_id=rid,owner_id='TEST-INERT-owner',panel_id=rid+'-panel',
            scope='research',research_run_id=rid+'-run',research_execution='engine_run',cutoff=histories[0].cutoff.isoformat(),
            origin=ORIGIN.isoformat(),protocol=PROTOCOL_REF,coordinates=COORDINATE_REF,
            members=[dict(patient_id=h.patient_id,patient_version=1,history_sha256=sha(h.model_dump(mode='json')),
                provenance_sha256=sha([r.model_dump(mode='json') for r in h.provenance])) for h in histories])
        manifest=CohortManifest.model_validate_json(canonical(manifest)).model_dump(mode='json')
        cohort=CohortHistory.model_validate_json(canonical(dict(schema='poc-cohort-history-v1/1.0.0',manifest=manifest,
            manifest_sha256=sha(manifest),histories=[h.model_dump(mode='json') for h in histories])))
        products=[make_cohort_input(cohort,rid+'-V0'),make_cohort_input(cohort,rid+'-V1',source)]
        planned.append(dict(replicate_id=rid,phase='pilot' if index<3 else 'confirmation',cohort_id=rid,panel_id=rid+'-panel',
            generation_key=reference('TEST-INERT-independent-generation',index),member_ids=members,
            fit_seeds=[p.numerical_seeds.model_dump() for p in products]))
        inputs[rid]=products
    design=s.SamplingDesign.model_validate_json(canonical(dict(definition=s.DEFINITION,scenario=SCENARIO_REF,
        behavior=reference('TEST-INERT-retained-behavior','frozen before outcomes'),enrollment_activation=reference('TEST-INERT-enrollment','t0'),
        external_source_policy='fixed_across_cohort_replications',source_set_sha256=source.source_set_sha256,
        member_ordinal=1,cutoff_day=14,estimand=ESTIMAND_REF,unit='ISI_points',configurations=list(s.CONFIGS),numerical_settings=list(s.SETTINGS),
        algorithm_sources={path:'1'*64 for path in s.ALGORITHM_PATHS},source_commit='1'*40,learner_image='sha256:'+'2'*64,
        numerical_runtime=reference('TEST-INERT-runtime','not installed/qualified'),
        frozen_before_collection=reference('TEST-INERT-preregistration','before any cohort outcome'),planned=planned)))
    return design,inputs


def diagnostics():
    return dict(accepted=True,rhat={'effect':1.},ess_bulk={'effect':500.},ess_tail={'effect':500.},mcse={'effect':.001})


def sensitivity(y0,y1,truth,epsilon,intervals=None):
    ids=[f'TEST-INERT-pair-{i}' for i in range(len(truth))]
    return s.truth_sensitivity(y0,y1,truth,epsilon,intervals,pair_ids=(ids,ids,ids))


def result(product,mean,*,status='completed',sd=100.):
    pd=dict(integration=dict(status='accepted',attempted=[dict(K=2048,U=.00001,L=.1,mean_integration_se=.001,
        variance_pass=True,mean_pass=True,stability_pass=True)]),effect_mcmc=diagnostics())
    patients=[dict(patient_id=m.patient_id,history_sha256=m.history_sha256,status=status,reason=None if status=='completed' else 'TEST-INERT-joint-failure',
        effect=dict(mean=mean,sd=sd,lower=mean-sd,upper=mean+sd,unit='ISI_points',kind='conditional_expected_assignment_contrast') if status=='completed' else None,
        diagnostics=deepcopy(pd)) for m in product.cohort.manifest.members]
    names=['patient-'+sha(m.patient_id)[:16]+'-expected-effect.npz' for m in product.cohort.manifest.members]
    if product.sources:names+=['bridge-precision.json','bridge-marginals.npz']
    return CohortResult.model_validate_json(canonical(dict(schema_version='3.0.0',synthetic=True,kind='poc_visit_cohort_result',
        attempt_id=product.attempt_id,input_sha256=sha(product.model_dump(mode='json')),cohort_sha256=product.cohort_sha256,
        manifest=product.cohort.manifest.model_dump(mode='json'),manifest_sha256=product.cohort.manifest_sha256,
        source_set_sha256=product.source_set_sha256,configuration=product.request.configuration.model_dump(),estimand=ESTIMAND_REF,
        status=status,reason=None if status=='completed' else 'TEST-INERT-joint-failure',patients=patients,
        diagnostics=dict(fits=[dict(extension=False,seed=product.numerical_seeds.nuts,diagnostics=diagnostics())],
            patients={m['patient_id']:deepcopy(pd) for m in patients},bridge_precision=dict(status='accepted'),
            execution=dict(source_commit='1'*40,learner_image='sha256:'+'2'*64)),
        artifacts=[dict(path=name,sha256='3'*64) for name in names],limitations=['TEST INERT; no artifact/fit admission'])))


def fixture(values=((1.,3.,5.),(2.,4.,6.)),confirmation=None,failed=()):
    design,inputs=prepared();design=s.fresh(design,s.SamplingDesign);attempts=[]
    for index,planned in enumerate(design.planned):
        if index<3 or confirmation is not None:
            means=[v[index] for v in values] if index<3 else [v[index-3] for v in confirmation]
            products=deepcopy(inputs[planned.replicate_id]);rs=[result(p,means[i],status='failed' if (index,i) in failed else 'completed') for i,p in enumerate(products)]
            attempts.append(s.CohortAttempt(replicate_id=planned.replicate_id,inputs=products,results=rs,reason=None))
        else:attempts.append(s.CohortAttempt(replicate_id=planned.replicate_id,inputs=None,results=None,reason='planned_not_collected'))
    admissions=[]
    def admit(product,r):
        planned=next(p for p in design.planned if p.cohort_id==product.cohort.manifest.cohort_id)
        admissions.append((product.attempt_id,r.status))
        return dict(experiment=design.reference,planned_cohort=reference('planned-independent-cohort',planned.model_dump(mode='json')),
            input=reference('cohort-input',product.model_dump(mode='json')),result=reference('cohort-result',r.model_dump(mode='json')),
            artifact_manifest=reference('cohort-artifact-manifest',r.artifacts),scalar_semantics='accepted_chain_draw_expected_effect_mean',
            admission_reference=reference('TEST-INERT-admission','fabricated SOURCE double, not actual acceptance'))
    def reduce(**kw):return s.reduce_sampling_se(design,attempts,expected_design=design.reference,admit_whole_cohort=admit,**kw)
    return design,attempts,admit,admissions,reduce


class SamplingTests(unittest.TestCase):
    def test_hand_sample_SD_and_jackknife_not_mean_SE_or_posterior_SD(self):
        design,attempts,admit,calls,reduce=fixture();b=reduce();s.validate_binding(b.model_dump(mode='json'))
        self.assertEqual(b.scales['pilot'][0]['sd'],2.);self.assertEqual(b.used_se,2.);self.assertEqual(b.epsilon,.05)
        self.assertAlmostEqual(b.scales['pilot'][0]['jackknife'],math.sqrt(8/9));self.assertTrue(b.scales['pilot'][0]['unreliable'])
        self.assertEqual(b.status,'provisional');self.assertEqual(b.counts['pilot']['attempted'],3);self.assertEqual(len(calls),6)
        self.assertEqual(b.counts['confirmation']['not_attempted'],30);self.assertFalse(b.production_truth)

    def test_constant_estimator_diffuse_posterior_and_min_pair_zero_remain_unresolved(self):
        for values in (((5.,5.,5.),(5.,5.,5.)),((5.,5.,5.),(1.,3.,5.))):
            *_,reduce=fixture(values);b=reduce()
            self.assertEqual(b.status,'unresolved');self.assertIsNone(b.used_se);self.assertIsNone(b.epsilon);self.assertTrue(b.zero_se_requires_analytic_truth)

    def test_varying_truth_tiny_errors_sampling_SD_is_distinct_and_absolute_ceiling_remains(self):
        truth=[-10.,0.,10.];means=tuple(t+.0001 for t in truth)
        *_,reduce=fixture((means,means));b=reduce()
        self.assertGreater(b.used_se,9.);self.assertEqual(b.epsilon,.05)
        report=sensitivity(list(means),list(means),truth,[.05]*3)
        self.assertAlmostEqual(report['rmse'][0],.0001);self.assertEqual(report['scope'],'engineering_allowance')
        self.assertGreater(report['rmse_allowance'],report['rmse'][0])

    def test_two_successes_failure_and_partial_artifacts_stay_in_denominators(self):
        design,attempts,admit,calls,reduce=fixture(failed=((2,1),));b=reduce()
        self.assertEqual(b.counts['pilot']['attempted'],3);self.assertEqual(b.counts['pilot']['paired_failure'],1)
        self.assertEqual(b.counts['pilot']['paired_success'],2);self.assertEqual(b.counts['pilot']['configurations'][0]['completed'],3)
        self.assertEqual(b.counts['pilot']['configurations'][1]['failed'],1)
        self.assertIsNone(b.rows[2].means);self.assertIsNone(b.used_se);self.assertEqual(len(calls),6)
        self.assertTrue(attempts[2].results[1].artifacts)  # retained earlier files are not eligible estimates
        forged=attempts[2].results[1].model_dump(mode='json');forged['patients'][0].update(status='completed',reason=None,effect=attempts[2].results[0].patients[0].effect.model_dump())
        with self.assertRaisesRegex(ValueError,'unaccepted joint fit'):CohortResult.model_validate_json(canonical(forged))

    def test_full_ledger_and_independent_cohorts_required_not_nights_or_seed_reruns(self):
        design,attempts,admit,calls,reduce=fixture()
        for changed in (attempts[:-1],attempts+[attempts[0]],attempts[1:]+[attempts[1]]):
            with self.assertRaisesRegex(ValueError,'full planned attempt ledger'):s.reduce_sampling_se(design,changed,expected_design=design.reference,admit_whole_cohort=admit)
        for field in ('replicate_id','cohort_id','panel_id','generation_key','member_ids','fit_seeds'):
            value=design.model_dump(mode='json');value['planned'][1][field]=value['planned'][0][field]
            with self.subTest(field=field),self.assertRaises(ValueError):s.SamplingDesign.model_validate_json(canonical(value))

    def test_malformed_stratum_settings_input_result_and_nonfinite_refuse(self):
        for field,new in (('unit','quality'),('cutoff_day',15),('member_ordinal',0),('definition',reference('wrong','wrong')),
                          ('numerical_settings',[{},{}]),('configurations',list(reversed(s.CONFIGS)))):
            design,*_=fixture();value=design.model_dump(mode='json');value[field]=new
            with self.subTest(field=field),self.assertRaises(ValueError):s.SamplingDesign.model_validate_json(canonical(value))
        for mutate in ('result_hash','wrong_patient','wrong_config','diagnostic','integration','nonfinite','partial_member','artifact'):
            design,attempts,admit,calls,reduce=fixture();raw=attempts[0].results[0].model_dump(mode='json')
            if mutate=='result_hash':raw['input_sha256']='9'*64
            elif mutate=='wrong_patient':raw['patients'][0]['patient_id']='wrong'
            elif mutate=='wrong_config':raw['configuration']=s.CONFIGS[1];raw['source_set_sha256']='9'*64
            elif mutate=='nonfinite':raw['patients'][0]['effect']['mean']=float('nan')
            elif mutate=='partial_member':raw['patients'][-1].update(status='failed',effect=None,reason='failed-late')
            elif mutate=='artifact':raw['artifacts'].pop(1)
            else:
                pd=raw['patients'][0]['diagnostics']
                if mutate=='diagnostic':pd['effect_mcmc']['rhat']['effect']=1.02
                else:pd['integration']['attempted'][-1]['mean_integration_se']=1.
                raw['diagnostics']['patients'][raw['patients'][0]['patient_id']]=deepcopy(pd)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):
                attempts[0].results[0]=CohortResult.model_validate_json(json.dumps(raw));reduce()

    def test_admission_mandatory_and_precedes_scalar_gate_selection(self):
        design,attempts,admit,calls,reduce=fixture()
        def refuse(*args):raise ValueError('TEST-INERT artifact admission refused')
        with patch.object(s,'sample_scale',side_effect=AssertionError('no scalar reduction before admission')):
            with self.assertRaisesRegex(ValueError,'artifact admission refused'):
                s.reduce_sampling_se(design,attempts,expected_design=design.reference,admit_whole_cohort=refuse)
        def wrong(p,r):return admit(p,r)|dict(result=reference('wrong-result','wrong'))
        with self.assertRaisesRegex(ValueError,'mismatched binding'):s.reduce_sampling_se(design,attempts,expected_design=design.reference,admit_whole_cohort=wrong)
        b=reduce();self.assertIn('separately reviewed isolated',b.actual_admission)

    def test_incomplete_pair_preserved_without_peer_scalar_or_invented_success(self):
        design,attempts,admit,calls,reduce=fixture();attempts[2].results[1]=None;attempts[2].reason='TEST-INERT interrupted'
        b=reduce();self.assertEqual(b.counts['pilot']['incomplete'],1);self.assertEqual(b.counts['pilot']['attempted'],3)
        self.assertEqual(b.counts['pilot']['paired_success'],2);self.assertIsNone(b.rows[2].means);self.assertIsNone(b.used_se)

    def test_final_minimum_tightens_never_relaxes_and_does_not_rewrite_pilot(self):
        *_,pilot_reduce=fixture(((.1,.2,.3),(.2,.4,.6)));pilot=pilot_reduce();frozen=pilot.model_dump_json()
        for spread in (.01,1.):
            values=tuple(spread*(i-15) for i in range(30))
            *_,reduce=fixture(((.1,.2,.3),(.2,.4,.6)),confirmation=(values,values));final=reduce()
            self.assertEqual(final.status,'final');self.assertEqual(final.counts['confirmation']['attempted'],30)
            if spread==.01:self.assertLess(final.used_se,pilot.used_se)
            else:self.assertEqual(final.used_se,pilot.used_se)
            self.assertAlmostEqual(final.used_se,min(.1,spread*math.sqrt(77.5)))
            self.assertLessEqual(final.epsilon,pilot.epsilon);self.assertEqual(pilot.model_dump_json(),frozen)
        *_,reduce=fixture(((.1,.2,.3),(.2,.4,.6)),confirmation=((0.,)*30,(1.,)*30));b=reduce()
        self.assertEqual(b.status,'unresolved');self.assertTrue(b.zero_se_requires_analytic_truth)

    def test_earlier_smaller_matching_scale_requires_separate_admission(self):
        *_,small=fixture(((.01,.02,.03),(.02,.04,.06)));prior=small()
        *_,reduce=fixture();
        with self.assertRaisesRegex(ValueError,'separate isolated admission'):reduce(earlier=[prior])
        b=reduce(earlier=[prior],admit_earlier_binding=lambda value:None)
        self.assertEqual(b.used_se,prior.used_se);self.assertEqual(b.epsilon,prior.epsilon)

    def test_closed_binding_reader_exact_target_final_status_and_counts_cannot_be_forged(self):
        *_,reduce=fixture();b=reduce();ref=reference('matched-estimator-sampling-SE',b.model_dump(mode='json'));target=b.rows[0].target.model_dump(mode='json')
        self.assertEqual(s.matched_estimator_sampling_se(b,expected_binding=ref,target=target),2.)
        for change in (dict(patient_id='wrong'),dict(ordinal=2),dict(history_sha256='0'*64),dict(cutoff='2026-01-16T12:00:00+00:00')):
            with self.assertRaisesRegex(ValueError,'unmatched'):s.matched_estimator_sampling_se(b,expected_binding=ref,target=target|change)
        with self.assertRaises(ValueError):s.matched_estimator_sampling_se(b,expected_binding=reference('self','wrong'),target=target)
        changed=deepcopy(target);changed['expected_effect_artifacts'][0]['sha256']='8'*64
        with self.assertRaisesRegex(ValueError,'unmatched'):s.matched_estimator_sampling_se(b,expected_binding=ref,target=changed)
        for field in ('status','counts','epsilon','extra'):
            value=b.model_dump(mode='json')
            if field=='status':value['status']='final'
            elif field=='counts':value['counts']['pilot']['attempted']=36
            elif field=='epsilon':value['epsilon']=.01
            else:value['authority']=True
            with self.subTest(field=field),self.assertRaises(ValueError):s.validate_binding(value)

    def test_wrong_planned_cohort_and_reused_integration_stream_cannot_pool(self):
        design,attempts,admit,calls,reduce=fixture()
        attempts[0].inputs=attempts[1].inputs
        with self.assertRaisesRegex(ValueError,'planned cohort'):reduce()
        value=design.model_dump(mode='json')
        value['planned'][1]['fit_seeds'][1]['effect_rollout']=value['planned'][0]['fit_seeds'][0]['effect_rollout']
        with self.assertRaisesRegex(ValueError,'stream reuse'):s.SamplingDesign.model_validate_json(canonical(value))

    def test_initial_extension_seed_collisions_in_both_directions_and_configurations_refuse(self):
        design,*_=fixture()
        for source,destination,offset in (((0,0),(1,0),1),((1,0),(0,0),-1),((0,0),(0,1),1)):
            raw=design.model_dump(mode='json');a,b=source;c,d=destination
            raw['planned'][c]['fit_seeds'][d]['nuts']=raw['planned'][a]['fit_seeds'][b]['nuts']+offset
            with self.subTest(source=source,destination=destination,offset=offset),self.assertRaisesRegex(ValueError,'fit-stream reuse'):
                s.SamplingDesign.model_validate_json(canonical(raw))

    def test_extension_reservation_includes_all_other_declared_streams(self):
        design,*_=fixture()
        for destination in ((0,0),(0,1),(1,0)):
            for stream in ('effect_rollout','prior_check','bridge_reference'):
                raw=design.model_dump(mode='json');i,j=destination
                raw['planned'][i]['fit_seeds'][j][stream]=raw['planned'][0]['fit_seeds'][0]['nuts']+1
                with self.subTest(destination=destination,stream=stream),self.assertRaisesRegex(ValueError,'fit-stream reuse'):
                    s.SamplingDesign.model_validate_json(canonical(raw))

    def test_derived_seed_range_boundaries_and_noncolliding_design(self):
        design,*_=fixture();raw=design.model_dump(mode='json')
        # Hand-spaced SOURCE fixture, not a production seed allocator or search.
        for i,planned in enumerate(raw['planned']):
            for j,seeds in enumerate(planned['fit_seeds']):
                base=10*(2*i+j)
                seeds.update(nuts=base,effect_rollout=base+2,prior_check=base+3,bridge_reference=base+4)
        self.assertEqual(s.SamplingDesign.model_validate_json(canonical(raw)).planned[0].fit_seeds[0].nuts,0)
        maximum=4294967295
        upper=deepcopy(raw);upper['planned'][0]['fit_seeds'][0]['nuts']=maximum-1
        self.assertEqual(s.SamplingDesign.model_validate_json(canonical(upper)).planned[0].fit_seeds[0].nuts,maximum-1)
        for value in (-1,maximum,maximum+1):
            bad=deepcopy(raw);bad['planned'][0]['fit_seeds'][0]['nuts']=value
            with self.subTest(value=value),self.assertRaises(ValueError):s.SamplingDesign.model_validate_json(canonical(bad))
        lower=deepcopy(raw);lower['planned'][1]['fit_seeds'][0]['nuts']=1
        with self.assertRaisesRegex(ValueError,'fit-stream reuse'):s.SamplingDesign.model_validate_json(canonical(lower))
        upper['planned'][1]['fit_seeds'][0]['bridge_reference']=maximum
        with self.assertRaisesRegex(ValueError,'fit-stream reuse'):s.SamplingDesign.model_validate_json(canonical(upper))

    def test_sparse_final_failures_remain_unresolved_not_infinite_precision_scale(self):
        confirmation=(tuple(float(i) for i in range(30)),tuple(float(i) for i in range(30)))
        *_,reduce=fixture(confirmation=confirmation,failed=tuple((i,1) for i in range(5,33)))
        b=reduce();self.assertEqual(b.counts['confirmation']['attempted'],30)
        self.assertEqual(b.counts['confirmation']['paired_success'],2);self.assertEqual(b.counts['confirmation']['paired_failure'],28)
        self.assertIsNone(b.used_se);self.assertEqual(b.status,'unresolved')

    def test_refinement_wrapper_passes_only_exact_scalar_and_keeps_other_gates_unresolved(self):
        from methods.truth import refinement
        *_,reduce=fixture(((.1,.2,.3),(.2,.4,.6)));b=reduce();target=b.rows[0].target.model_dump(mode='json')
        binding=dict(patient_id=target['patient_id'],history_sha256=target['history_sha256'],target=dict(cutoff=target['cutoff']))
        calls=[]
        def inert_rows(*args,**kw):calls.append(kw);return dict(status='unresolved',production_truth=False,finite_grid_discrepancy_bound=None)
        ref=reference('matched-estimator-sampling-SE',b.model_dump(mode='json'))
        with patch.object(refinement,'reduce_rows',inert_rows):
            report=s.reduce_refinement_with_sampling_se([],[],binding,b,expected_sampling_binding=ref,target=target)
        self.assertAlmostEqual(calls[0]['matched_se'],.1);self.assertEqual(report['status'],'unresolved');self.assertIsNone(report['finite_grid_discrepancy_bound'])
        binding['history_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'exact scored Hstar'):s.reduce_refinement_with_sampling_se([],[],binding,b,expected_sampling_binding=ref,target=target)

    def test_active_import_process_network_and_private_filesystem_guards(self):
        import subprocess,socket
        for module in ('numpy','scipy','pymc','sqlite3','services.foundation.store'):
            with self.subTest(module=module),self.assertRaises(AssertionError):__import__(module)
        with self.assertRaises(AssertionError):subprocess.run(['TEST-INERT-NEVER-START'])
        with self.assertRaises(AssertionError):socket.create_connection(('TEST-INERT-NEVER-CONNECT',1))
        with self.assertRaises(AssertionError):Path('C:/TEST-INERT-NEVER-TOUCH/private.txt').read_bytes()


class SensitivityTests(unittest.TestCase):
    def test_bias_RMSE_common_truth_cancellation_and_no_RMSE_cancellation(self):
        a=sensitivity([1.,4.],[0.,2.],[0.,2.],[.1,.2])
        b=sensitivity([1.,4.],[0.,2.],[.1,1.8],[.1,.2])
        self.assertAlmostEqual(a['bias_allowance'],.15);self.assertAlmostEqual(a['rmse_allowance'],math.sqrt(.025))
        self.assertEqual(a['paired_mean_error_difference'],1.5);self.assertEqual(a['paired_mean_error_difference'],b['paired_mean_error_difference'])
        self.assertFalse(a['truth_cancels_for_squared_error_or_RMSE_difference']);self.assertNotEqual(a['rmse'],b['rmse'])
        self.assertEqual(a['scope'],'engineering_allowance')

    def test_coverage_sign_ranking_boundary_equality_is_ambiguous(self):
        report=sensitivity([0.,0.,0.],[0.,0.,0.],[0.,1.,1.1],[.1,.1,.1],[[-1.,1.],[.9,2.],[.5,2.]])
        self.assertEqual(report['coverage'],dict(lower_count=2,upper_count=3,denominator=3,ambiguous=1))
        self.assertTrue(report['sign_ambiguous'][0]);self.assertIn((1,2),report['ranking_ambiguous'])
        for bad in (float('nan'),float('inf'),-.1):
            with self.assertRaises(ValueError):sensitivity([0.],[0.],[0.],[bad])

    def test_common_truth_cancellation_refuses_reordered_unequal_or_duplicated_pairs(self):
        for ids in ((['a','b'],['b','a'],['a','b']),(['a','b'],['a','b'],['a','c']),(['a','a'],['a','a'],['a','a'])):
            with self.assertRaisesRegex(ValueError,'same distinct ordered'):
                s.truth_sensitivity([1.,2.],[2.,3.],[0.,1.],[.1,.1],pair_ids=ids)

    def test_source_semantics_and_existing_science_contracts_are_not_reinterpreted(self):
        worker=(ROOT/'services/learner/cohort_worker.py').read_text()
        self.assertIn('mean=float(effect.mean())',worker);self.assertIn('for member in members:member.update(status=status,reason=reason,effect=None)',worker)
        self.assertEqual(Effect.model_fields['sd'].annotation,float)
        tree=ast.parse((ROOT/'methods/truth/sampling_se.py').read_text())
        modules=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith(('numpy','pymc','scipy','services')) for name in modules))
