"""Short deterministic scalar SOURCE fixtures, not generated cohorts or science evidence."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import ast
from fractions import Fraction
import io
import json
import os
import socket
import subprocess
import unittest
from unittest.mock import patch

from contracts.domain import breadth as b
from contracts.domain.boundaries import LearnerHistory
from services.generator import breadth as g

ORIGIN=datetime(2026,1,1,tzinfo=timezone.utc)


def record(kind,day,*,hour=None,**values):
    hour=hour if hour is not None else {'demographic':0,'steroid_schedule':0,'clinical':8,'steroid_exposure':8,
        'device_sleep':7,'daily_report':7,'isi':11,'assignment':12,'delivery':20}[kind]
    at=ORIGIN+timedelta(days=day,hours=hour);identifier='fixture-'+kind+'-'+str(day)
    if kind=='daily_report':recorded=at+timedelta(hours=1,minutes=1)
    elif kind=='device_sleep':recorded=at+timedelta(minutes=30)
    elif kind=='isi':recorded=at+timedelta(minutes=59)
    else:recorded=at
    return dict(schema_version='3.0.0',synthetic=True,kind=kind,record_id=identifier,patient_id='fixture-member',
        event_at=at.isoformat(),recorded_at=recorded.isoformat(),available_at=recorded.isoformat(),lineage_id=identifier,
        revision=1,supersedes=None,duplicate_of=None,record_status='active',
        source=dict(id=b.SOURCE_IDS[kind],version='3.0.0',adapter=b.ADAPTERS[kind],raw_sha256='a'*64),**values)


def fixture_records():
    return [record('demographic',-15,age_years=52.5,age_unit='years',synthetic_sex_code=1,
                sex_concept='fictional-two-code-scenario-variable-not-general-sex-gender-ontology'),
        record('steroid_schedule',-15,period_days=21,active_residues=[0,1,2],unit='binary_contextual_exposure_not_dose'),
        record('clinical',14,value=6.,unit='synthetic_clinical_score_0_10',missingness='observed'),
        record('device_sleep',14,episode_start=(ORIGIN+timedelta(days=13,hours=23)).isoformat(),episode_end=(ORIGIN+timedelta(days=14,hours=7)).isoformat(),
            time_in_bed=480.,sleep_minutes=420.,estimated_wake_minutes=60.,status='observed',unit='minutes'),
        record('daily_report',14,value=8.,unit='quality_points_0_10',missingness='observed')]


def history(records=None):
    return b.BreadthHistory.model_validate_json(b.canonical(dict(version=b.HISTORY_VERSION,synthetic=True,law=b.LAW_REF,
        patient_id='fixture-member',origin=ORIGIN.isoformat(),records=fixture_records() if records is None else records)))


class ContractTests(unittest.TestCase):
    def test_four_source_types_and_exact_compact_features(self):
        projection=history().project(ORIGIN+timedelta(days=14,hours=12));f=b.support_features(projection)
        self.assertEqual(f.prognostic(),(1.,8.,0.,0.,14/84,.25,1.,1.))
        self.assertEqual(f.effect_interactions(),(0.,0.));self.assertEqual(f.clinical_record,'fixture-clinical-14')
        self.assertEqual(f.device_record,'fixture-device_sleep-14');self.assertAlmostEqual(f.clinical_age_days,4/24)
        self.assertAlmostEqual(f.device_age_days,5/24)
        self.assertEqual(f.demographic_record,'fixture-demographic--15')
        self.assertEqual(b.SupportFeatures.model_validate_json(f.model_dump_json()),f)
        with self.assertRaises(ValueError):LearnerHistory.model_validate_json(projection.model_dump_json())

    def test_unavailable_sync_and_equal_cutoff_refused(self):
        rows=fixture_records();rows[3]['available_at']=(ORIGIN+timedelta(days=15,hours=7,minutes=30)).isoformat()
        projection=history(rows).project(ORIGIN+timedelta(days=14,hours=12))
        self.assertNotIn('fixture-device_sleep-14',projection.active_record_ids)
        self.assertEqual(b.support_features(projection).device_control,0.)
        rows=fixture_records();rows[2]['available_at']=(ORIGIN+timedelta(days=14,hours=12)).isoformat()
        projection=history(rows).project(ORIGIN+timedelta(days=14,hours=12))
        self.assertNotIn('fixture-clinical-14',projection.active_record_ids)
        raw=projection.model_dump(mode='json');raw['lineage'].append(rows[2]);raw['active_record_ids'].append(rows[2]['record_id'])
        with self.assertRaises(ValueError):b.BreadthProjection.model_validate_json(b.canonical(raw))

    def test_correction_selected_after_visibility_not_before(self):
        rows=fixture_records();correction=deepcopy(rows[2]);correction.update(record_id='correction',revision=2,supersedes=rows[2]['record_id'],
            record_status='corrected',value=4.,recorded_at=(ORIGIN+timedelta(days=15,hours=8)).isoformat(),available_at=(ORIGIN+timedelta(days=15,hours=8)).isoformat())
        h=history(rows+[correction]);earlier=h.project(ORIGIN+timedelta(days=14,hours=12));later=h.project(ORIGIN+timedelta(days=15,hours=12))
        self.assertEqual(b.support_features(earlier).clinical_control,1.)
        self.assertEqual(b.support_features(later).clinical_control,0.)
        self.assertIn('fixture-clinical-14',[x.record_id for x in later.lineage]);self.assertNotIn('fixture-clinical-14',later.active_record_ids)
        bad=deepcopy(correction);bad['event_at']=(ORIGIN+timedelta(days=13,hours=8)).isoformat()
        with self.assertRaises(ValueError):history(rows+[bad])

    def test_missing_not_zero_stale_not_recent_and_no_device_imputation(self):
        rows=fixture_records();rows[2].update(value=None,missingness='missing');rows[3].update(sleep_minutes=None,estimated_wake_minutes=None,status='nonwear')
        rows[4].update(value=None,missingness='missing');f=b.support_features(history(rows).project(ORIGIN+timedelta(days=14,hours=12)))
        self.assertEqual(f.prognostic()[1:3],(7.,1.));self.assertEqual((f.clinical_control,f.device_control),(0.,0.))
        rows=fixture_records();projection=history(rows).project(ORIGIN+timedelta(days=22,hours=12));f=b.support_features(projection)
        self.assertIsNone(f.clinical_record);self.assertIsNone(f.device_record);self.assertEqual(f.clinical_control,.5)
        for index,field,value in [(2,'value',0.),(3,'sleep_minutes',0.)]:
            raw=deepcopy(rows);raw[index][field]=value
            if index==3:raw[index]['estimated_wake_minutes']=480.
            self.assertIsNotNone(history(raw).records[index])

    def test_units_source_clock_oracle_and_unknown_fields_reject(self):
        for index,field,value in [(0,'age_unit','months'),(2,'unit','ISI_points'),(3,'estimated_wake_minutes',59.),(4,'value',8.0001),
                                  (0,'synthetic_sex_code',True),(0,'latent_b',20.)]:
            rows=fixture_records();rows[index][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):history(rows)
        for field in ('id','version','adapter'):
            rows=fixture_records();rows[2]['source'][field]='wrong'
            with self.assertRaises(ValueError):history(rows)
        for field in ('seed','X','response','truth','future_outcome'):
            raw=history().model_dump(mode='json');raw[field]=1
            with self.assertRaises(ValueError):b.BreadthHistory.model_validate_json(b.canonical(raw))

    def test_perturbations_reach_only_lawful_declared_features(self):
        original=b.support_features(history().project(ORIGIN+timedelta(days=14,hours=12)))
        for index,field,value,expected in [(0,'age_years',75.,'age_control'),(2,'value',8.,'clinical_control'),(3,'sleep_minutes',360.,'device_control')]:
            rows=fixture_records();rows[index][field]=value
            if index==3:rows[index]['estimated_wake_minutes']=480-value
            changed=b.support_features(history(rows).project(ORIGIN+timedelta(days=14,hours=12)))
            self.assertNotEqual(getattr(changed,expected),getattr(original,expected))
            for other in ('age_control','clinical_control','device_control'):
                if other!=expected:self.assertEqual(getattr(changed,other),getattr(original,other))

    def test_actual_logged_prompt_counts_and_source_lineage(self):
        rows=fixture_records()
        for day in (8,10,12):
            rows.append(record('assignment',day,component='support',option='support_prompt',policy=b.reference('fixture-MRT','1.0.0','q=.5'),
                chosen_probability=.5,support_available=[True,True],support_probabilities=[.5,.5],unit='assigned_action'))
        f=b.support_features(history(rows).project(ORIGIN+timedelta(days=14,hours=12)))
        self.assertEqual(f.previous_six_prompts,3);self.assertEqual(f.prognostic()[3],1.);self.assertEqual(len(f.prompt_records),3)
        bad=deepcopy(rows[-1]);bad['support_available']=[True,False]
        with self.assertRaises(ValueError):history(rows[:-1]+[bad])

    def test_ambiguous_baseline_or_delivery_cannot_claim_provenance(self):
        rows=fixture_records();other=deepcopy(rows[2]);other.update(record_id='other',lineage_id='other')
        with self.assertRaises(ValueError):history(rows+[other])
        rows=fixture_records();rows[0]['event_at']=rows[0]['recorded_at']=rows[0]['available_at']=ORIGIN.isoformat()
        with self.assertRaises(ValueError):history(rows)
        delivery=record('delivery',13,component='medication',assignment_id='unknown',option='MED_A',taken=True,unit='actual_delivery_taking')
        with self.assertRaises(ValueError):history(fixture_records()+[delivery])

    def test_candidate_export_requires_complete_roster_and_exact_features(self):
        # Twelve INERT copies of hand-authored scalar records, not a generated
        # cohort. This tests the whole-export wire/transform guard only.
        histories=[];features=[]
        for index in range(12):
            h=history().model_dump(mode='json');patient='inert-member-'+str(index);h['patient_id']=patient
            for row in h['records']:row['patient_id']=patient
            projected=b.BreadthHistory.model_validate_json(b.canonical(h)).project(ORIGIN+timedelta(days=14,hours=12))
            histories.append(projected);features.append(b.support_features(projected))
        value=dict(version='poc-breadth-observed-export-v1',synthetic=True,run_id='inert-run',cohort_id='inert-cohort',replicate=0,role='prospective',
            law=b.LAW_REF,history_definition=b.HISTORY_REF,feature_definition=b.FEATURE_REF,source_commit='a'*40,runtime=b.reference('inert-runtime','1.0.0','NOTQUALIFIED'),
            cutoff=histories[0].cutoff.isoformat(),origin=ORIGIN.isoformat(),member_order=[h.patient_id for h in histories],histories=[h.model_dump(mode='json') for h in histories],
            support=[f.model_dump(mode='json') for f in features],publication_status='candidate_requires_independent_source_runtime_export_admission')
        b.BreadthExport.model_validate_json(b.canonical(value))
        for field in ('histories','support','member_order'):
            changed=deepcopy(value);changed[field]=changed[field][:-1]
            with self.assertRaises(ValueError):b.BreadthExport.model_validate_json(b.canonical(changed))
        changed=deepcopy(value);changed['support'][0]['device_control']=999.
        with self.assertRaises(ValueError):b.BreadthExport.model_validate_json(b.canonical(changed))
        changed=deepcopy(value);changed['publication_status']='accepted'
        with self.assertRaises(ValueError):b.BreadthExport.model_validate_json(b.canonical(changed))


class ScalarLawTests(unittest.TestCase):
    def person(self):return dict(a=0.,s=0.,b=19.,response=1.,device_bias=15.)
    def initial(self):return dict(x_previous=0.,z=19.,e=0.,c=0.,escalate=0.,ma=0.,mb=0.,rebound=0.,previous_assigned_drug=None)

    def test_baseline_independent_named_draws_hand_constants(self):
        calls=[]
        def uniform(name):calls.append(name);return .5
        value=g.baseline(uniform,lambda name:0.)
        self.assertEqual(calls,['age','sex','baseline','response']);self.assertEqual(value['age'],52.5)
        self.assertEqual(value['b'],18.5);self.assertEqual(value['response'],1.);self.assertEqual(value['device_bias'],15.)

    def test_two_step_feedback_and_assigned_rebound_not_missed_dose(self):
        zero={k:False for k in ('behavioral_continue','behavioral_escalate','MED_A','MED_B')}
        one=g.step(self.initial(),self.person(),0,eta=0.,xi=0.,taken=zero,assigned_drug='MED_B')
        self.assertAlmostEqual(one['x_previous'],.5);self.assertEqual(one['rebound'],0.)
        # Day1 keeps assigned B despite no dose: no cessation term.
        missed=g.step(one,self.person(),1,eta=0.,xi=0.,taken=zero,assigned_drug='MED_B')
        ceased=g.step(one,self.person(),1,eta=0.,xi=0.,taken=zero,assigned_drug=None)
        self.assertEqual(missed['rebound'],0.);self.assertEqual(ceased['rebound'],1.)
        self.assertAlmostEqual(ceased['z']-missed['z'],1.)
        self.assertAlmostEqual(missed['x_previous'],.6*.5+.12*(one['z']-19)+.5)

    def test_carryover_adherence_and_null_coefficients(self):
        zero={k:False for k in ('behavioral_continue','behavioral_escalate','MED_A','MED_B')};taken=zero|{'behavioral_escalate':True,'MED_A':True}
        active=g.step(self.initial(),self.person(),3,eta=0.,xi=0.,taken=taken,assigned_drug='MED_A')
        null=g.step(self.initial(),self.person(),3,eta=0.,xi=0.,taken=taken,assigned_drug='MED_A',coefficients=(0.,0.))
        self.assertEqual(active['escalate'],.2);self.assertEqual(active['ma'],.5);self.assertAlmostEqual(null['z']-active['z'],.8)
        next_state=g.step(active,self.person(),4,eta=0.,xi=0.,taken=zero,assigned_drug='MED_A')
        self.assertAlmostEqual(next_state['escalate'],.16);self.assertEqual(next_state['ma'],.25)

    def test_measurement_separation_clipping_missing_and_support(self):
        args=dict(x=0.,z=19.,steroid=0,previous_support=0,prompt_count=0,clinical_noise=0.,device_noise=0.,report_noise=0.,
            clinical_missing=False,device_status='observed',report_missing=False,round_value=round)
        base=g.measurements(self.person(),**args);self.assertEqual(base['clinical'],4.);self.assertEqual(base['device'],343.)
        self.assertEqual(base['estimated_wake'],137.);self.assertEqual(base['quality'],3.667)
        support=g.measurements(self.person(),**(args|dict(previous_support=1,prompt_count=2,steroid=1)))
        self.assertEqual(support['quality'],3.867);self.assertEqual(support['device'],base['device'])
        missing=g.measurements(self.person(),**(args|dict(clinical_missing=True,device_status='quality_rejected',report_missing=True)))
        self.assertEqual(missing,dict(clinical=None,device=None,estimated_wake=None,quality=None))


class PrivateWireTests(unittest.TestCase):
    def action(self,day,component,option,probability=1.,mask=None):
        return dict(day=day,component=component,option=option,assignment_id='fixture-'+component+'-'+str(day),policy=b.reference('fixture-policy','1.0.0','NOTACTUAL'),
            chosen_probability=probability,support_available=mask,
            support_probabilities=None if mask is None else ([1-probability,probability] if option=='support_prompt' else [probability,1-probability]))

    def request(self):
        return dict(law_version=b.LAW_VERSION,namespace='SOURCE-inert-no-generation',seed=1,index=0,patient_id='fixture-member',origin=ORIGIN.isoformat(),
            family='V',population='target',scenario='reference',through_day=2,support_mode=None,actions=[self.action(0,'behavioral','behavioral_continue')])

    def test_new_private_shape_family_and_old_fields_do_not_mix(self):
        value=self.request();g.BreadthRequest.model_validate_json(b.canonical(value))
        for key,value2 in [('law_version','poc-longitudinal-v1'),('seed',True),('index',12),('through_day',127),('family','other'),('support_mode','S1'),('truth',1)]:
            changed=deepcopy(value);changed[key]=value2
            with self.subTest(key=key),self.assertRaises(ValueError):g.BreadthRequest.model_validate_json(b.canonical(changed))
        changed=deepcopy(value);changed['actions'].append(self.action(0,'medication','MED_A'))
        with self.assertRaises(ValueError):g.BreadthRequest.model_validate_json(b.canonical(changed))
        changed=deepcopy(value);changed['actions']*=2
        with self.assertRaises(ValueError):g.BreadthRequest.model_validate_json(b.canonical(changed))

    def test_actual_support_probability_mask_and_hard_constraints(self):
        value=self.request();value.update(family='S',support_mode='S1',actions=[self.action(0,'behavioral','behavioral_continue'),
            self.action(0,'support','support_prompt',.5,[True,True]),self.action(1,'support','no_prompt',1.,[True,False])])
        g.BreadthRequest.model_validate_json(b.canonical(value))
        for mutate in ('missing','probability','unavailable','consecutive'):
            changed=deepcopy(value)
            if mutate=='missing':changed['actions'].pop()
            if mutate=='probability':changed['actions'][1]['chosen_probability']=.7
            if mutate=='unavailable':changed['actions'][1]['support_available']=[True,False]
            if mutate=='consecutive':changed['actions'][2].update(option='support_prompt',support_available=[True,True])
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):g.BreadthRequest.model_validate_json(b.canonical(changed))
        changed=deepcopy(value);changed['support_mode']='S0'
        with self.assertRaises(ValueError):g.BreadthRequest.model_validate_json(b.canonical(changed))
        changed=deepcopy(value);changed['support_mode']='S2';changed['actions'][1]['chosen_probability']=.09
        with self.assertRaises(ValueError):g.BreadthRequest.model_validate_json(b.canonical(changed))

    def test_observed_source_bytes_verified_before_history_projection(self):
        at=ORIGIN-timedelta(days=15)
        entry=g.observed_entry('fixture-member','demographic','fixture-demo',at,at,at,age_years=52.5,age_unit='years',synthetic_sex_code=1,
            sex_concept='fictional-two-code-scenario-variable-not-general-sex-gender-ontology')
        h=g.history_from_entries('fixture-member',ORIGIN,[entry]);self.assertEqual(h.records[0].age_years,52.5)
        for change in ('hash','raw','value','extra'):
            changed=deepcopy(entry)
            if change=='hash':changed['record']['source']['raw_sha256']='0'*64
            if change=='raw':changed['raw_source']+=' '
            if change=='value':changed['record']['age_years']=60.
            if change=='extra':changed['private_seed']=1
            with self.subTest(change=change),self.assertRaises(ValueError):g.history_from_entries('fixture-member',ORIGIN,[changed])


class ProducerSourceTests(unittest.TestCase):
    """Single-patient short CONSTANT-draw fixtures; no cohort generation."""
    def request(self):
        value=PrivateWireTests().request();value.update(through_day=1,namespace='DO-NOT-EXPORT-KEY')
        return value

    def short(self,request=None,draw=None):
        # Replace all exogenous draws with inert named constants. This tests
        # source plumbing, not a realization/qualification of the random law.
        with patch.object(g,'uniform',side_effect=draw or (lambda *args:.5)),patch.object(g,'normal',return_value=0.):
            return g.generate(self.request() if request is None else request)

    def test_short_fixed_source_has_four_families_no_latent_seed_and_original_delivery(self):
        result=self.short();h=g.history_from_entries(result['patient_id'],ORIGIN,result['records'])
        self.assertEqual(set(result),{'law_version','patient_id','records'})
        self.assertEqual({r.source.id for r in h.records},set(b.SOURCE_IDS.values()))
        self.assertEqual(sum(r.kind=='device_sleep' for r in h.records),15) # -13..1
        self.assertFalse(any(r.event_at.date()<(ORIGIN-timedelta(days=13)).date() for r in h.records if r.kind=='device_sleep'))
        assignment=next(r for r in h.records if r.kind=='assignment')
        delivery=next(r for r in h.records if r.kind=='delivery')
        self.assertEqual((assignment.record_id,delivery.assignment_id),('fixture-behavioral-0','fixture-behavioral-0'))
        self.assertTrue(delivery.taken);self.assertEqual(delivery.event_at,ORIGIN+timedelta(hours=20))
        isi=next(r for r in h.records if r.kind=='isi')
        self.assertEqual(isi.recall_start,ORIGIN-timedelta(days=14)+timedelta(hours=7))
        self.assertEqual(isi.recall_end,ORIGIN+timedelta(hours=7))
        for forbidden in ('DO-NOT-EXPORT-KEY','"seed"','"x_previous"','"response"','"device_bias"','"coefficients"','"scenario"'):
            self.assertNotIn(forbidden,b.canonical(result).decode())
        self.assertEqual(self.short(),result) # constant fixture determinism only

    def test_terminal_observation_calls_no_next_transition_and_cannot_backdate_delayed_values(self):
        calls=[];original=g.step
        def step(*args,**kwargs):calls.append(args[2]);return original(*args,**kwargs)
        def draw(*args):return .05 if args[-1]=='clinical-delay' else .95 if args[-1]=='device-sync' else .5
        with patch.object(g,'step',side_effect=step):result=self.short(draw=draw)
        self.assertEqual(calls,list(range(-14,1))) # terminal1 is X-only, no Z2
        h=g.history_from_entries(result['patient_id'],ORIGIN,result['records'])
        terminal=next(r for r in h.records if r.kind=='clinical' and r.event_at==ORIGIN+timedelta(days=1,hours=8))
        self.assertEqual(terminal.available_at,ORIGIN+timedelta(days=2,hours=8))
        projected=h.project(ORIGIN+timedelta(hours=12))
        self.assertNotIn('fixture-member-clinical-0',projected.active_record_ids)
        self.assertNotIn('fixture-member-device_sleep-0',projected.active_record_ids)
        self.assertNotIn(terminal.record_id,projected.active_record_ids)
        source=ast.parse(Path(g.__file__).read_text(encoding='utf-8'))
        function=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='generate')
        terminal_branch=next(n for n in ast.walk(function) if isinstance(n,ast.If) and ast.unparse(n.test)=='day < request.through_day' and n.orelse)
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='step' for statement in terminal_branch.orelse for n in ast.walk(statement)))

    def test_short_prefix_and_later_action_leave_original_available_observations_identical(self):
        full=self.short();request=self.request();request.update(through_day=0,actions=[])
        prefix=self.short(request)
        def projection(result):
            return g.history_from_entries(result['patient_id'],ORIGIN,result['records']).project(ORIGIN+timedelta(hours=12)).model_dump(mode='json')
        self.assertEqual(projection(prefix),projection(full))
        by_id={e['record']['record_id']:e for e in full['records']}
        for original in prefix['records']:self.assertEqual(original,by_id[original['record']['record_id']])

    def test_initial_nonwear_rejection_independence_and_absent_status_cutoff(self):
        calls=[]
        def rejected(name):calls.append(name);return .01
        worn,status=g.device_state(-13,False,rejected)
        self.assertEqual((worn,status),(True,'quality_rejected'));self.assertEqual(calls,['device-rejection'])
        worn,status=g.device_state(-12,worn,lambda name:.01)
        self.assertEqual((worn,status),(False,'nonwear'))
        worn,status=g.device_state(-11,worn,lambda name:.7)
        self.assertEqual((worn,status),(True,'observed'))
        def draw(*args):return .01 if args[-1]=='device-rejection' else .5
        result=self.short(draw=draw);h=g.history_from_entries(result['patient_id'],ORIGIN,result['records'])
        device=next(r for r in h.records if r.kind=='device_sleep' and r.event_at==ORIGIN+timedelta(hours=7))
        self.assertEqual((device.status,device.sleep_minutes),('quality_rejected',None))
        self.assertEqual(device.available_at,ORIGIN+timedelta(hours=7,minutes=30))
        self.assertNotIn(device.record_id,h.project(device.available_at).active_record_ids)
        self.assertIn(device.record_id,h.project(device.available_at+timedelta(microseconds=1)).active_record_ids)

    def test_real_grid_ties_distinct_from_literal_and_isi_half_up(self):
        # Independent exact rational expected REAL quantizer, no float bridge.
        def real_grid(value,grid):return grid*round(value/grid)
        for value,grid,expected in [(Fraction(5,100),Fraction(1,10),Fraction(0)),(Fraction(15,100),Fraction(1,10),Fraction(2,10)),
                (Fraction(12345,10000),Fraction(1,1000),Fraction(1234,1000)),(Fraction(12355,10000),Fraction(1,1000),Fraction(1236,1000))]:
            self.assertEqual(real_grid(value,grid),expected)
        self.assertEqual(round(.05,1),.1);self.assertEqual(round(.15,1),.1)
        self.assertNotEqual(Fraction(str(round(.05,1))),real_grid(Fraction(5,100),Fraction(1,10)))
        self.assertEqual(g.isi_total([2.5]*14,0.),3);self.assertEqual(g.isi_total([-.5]*14,0.),0)
        with self.assertRaises(ValueError):g.isi_total([1.]*13,0.)
        self.assertEqual((b.LAW_DEFINITION['literal_equivalence'],b.LAW_DEFINITION['finite_grid_discrepancy_bound']),(False,None))

    def test_scenario_coefficients_and_midnight_identity_are_explicit_private_inputs(self):
        self.assertEqual(g.treatment_coefficients('target','external_conflict'),(2.,4.))
        self.assertEqual(g.treatment_coefficients('external','external_conflict'),(2.,1.))
        self.assertEqual(g.treatment_coefficients('target','sharp_null'),(0.,0.))
        value=self.request();value['origin']=(ORIGIN+timedelta(hours=12)).isoformat()
        with self.assertRaises(ValueError):g.BreadthRequest.model_validate_json(b.canonical(value))
        value=self.request();value['patient_id']='a'*81
        with self.assertRaises(ValueError):g.BreadthRequest.model_validate_json(b.canonical(value))

    def test_explicit_lazy_dispatch_preserves_historical_branch_and_unknown_refusal(self):
        path=Path(g.__file__).with_name('server.py');module=ast.parse(path.read_text(encoding='utf-8'))
        function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='generate')
        old=ast.parse("def generate(request):\n return generate_v2(request) if request.get('law_version') == 'poc-longitudinal-v2' else generate_v1(request)").body[0]
        self.assertEqual(ast.dump(function,include_attributes=False),ast.dump(old,include_attributes=False))
        self.assertFalse(any(isinstance(n,ast.ImportFrom) and n.module=='breadth' for n in module.body))
        # Historical dispatch body is completely unchanged; new profile lives
        # exclusively behind the distinct /generate/breadth method.
        calls=[]
        def named(name):
            def run(value):calls.append(name);return name
            return run
        env=dict(generate_v1=named('v1'),generate_v2=named('v2'))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(function)],type_ignores=[])),'<inert-dispatch>','exec'),env)
        for version,expected in [('poc-longitudinal-v2','v2'),(b.LAW_VERSION,'v1'),('unknown','v1')]:
            self.assertEqual(env['generate']({'law_version':version}),expected)
        self.assertEqual(calls,['v2','v1','v1'])

    def test_short_support_effect_is_next_report_only_and_original_full_probability_retained(self):
        value=self.request();value.update(family='S',support_mode='S1')
        value['actions'].append(PrivateWireTests().action(0,'support','support_prompt',.5,[True,True]))
        prompted=self.short(value);value['actions'][-1]=PrivateWireTests().action(0,'support','no_prompt',.5,[True,True])
        no_prompt=self.short(value)
        def selected(result,kind,day):
            return next(e['record'] for e in result['records'] if e['record']['kind']==kind and e['record']['event_at'].startswith((ORIGIN+timedelta(days=day)).date().isoformat()))
        self.assertEqual(selected(prompted,'daily_report',0)['value'],selected(no_prompt,'daily_report',0)['value'])
        self.assertAlmostEqual(selected(prompted,'daily_report',1)['value']-selected(no_prompt,'daily_report',1)['value'],.4)
        self.assertEqual(selected(prompted,'clinical',1)['value'],selected(no_prompt,'clinical',1)['value'])
        self.assertEqual(selected(prompted,'device_sleep',1)['sleep_minutes'],selected(no_prompt,'device_sleep',1)['sleep_minutes'])
        assigned=next(e['record'] for e in prompted['records'] if e['record']['kind']=='assignment' and e['record']['component']=='support')
        self.assertEqual((assigned['chosen_probability'],assigned['support_probabilities'],assigned['support_available']),(.5,(.5,.5),(True,True)))

    def test_new_transport_full126_logged_request_sizing_and_old_handler_inverse(self):
        value=PrivateWireTests().request();value.update(family='S',support_mode='S2',through_day=126,actions=[])
        for day in range(126):
            for component,option,probability,mask in [('behavioral','behavioral_continue',1.,None),('support','no_prompt',.5,[True,True])]:
                action=PrivateWireTests().action(day,component,option,probability,mask)
                action['assignment_id']=('b' if component=='behavioral' else 's')+'a'*123+str(day)
                action['policy']=dict(id='p'*128,version='v'*256,sha256='a'*64)
                value['actions'].append(action)
        g.BreadthRequest.model_validate_json(b.canonical(value))
        self.assertGreater(len(b.canonical(value)),32768);self.assertLessEqual(len(b.canonical(value)),262144)
        module=ast.parse(Path(g.__file__).with_name('server.py').read_text(encoding='utf-8'))
        handler=next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='Handler')
        body=next(n for n in handler.body if isinstance(n,ast.FunctionDef) and n.name=='do_POST')
        # Legacy endpoint's body is retained after the explicit new-path branch.
        legacy=deepcopy(body);legacy.body=legacy.body[1:]
        self.assertEqual(ast.unparse(legacy.body[0]),"length = int(self.headers.get('Content-Length', '0'))")
        self.assertIn("not 0 < length <= 32768",ast.unparse(legacy))
        self.assertEqual(ast.unparse(body.body[0].test),"self.path == '/generate/breadth'")

    def test_actual_new_transport_method_bytebound_short_duplicate_nonfinite_and_exact_profile(self):
        module=ast.parse(Path(g.__file__).with_name('server.py').read_text(encoding='utf-8'))
        handler=next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='Handler')
        method=deepcopy(next(n for n in handler.body if isinstance(n,ast.FunctionDef) and n.name=='breadth_POST'))
        # Inert producer substitution only; actual decoder/read/length/status body.
        for node in ast.walk(method):
            if isinstance(node,ast.Try):node.body=[n for n in node.body if not isinstance(n,ast.ImportFrom)]
        called=[]
        def producer(value):called.append(value);return {'source_only':True}
        env=dict(json=json,generate_breadth=producer)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'<inert-http-method>','exec'),env)
        class Peer:
            def __init__(self,raw,length):self.headers={'Content-Length':length};self.rfile=io.BytesIO(raw);self.wfile=io.BytesIO();self.status=None
            def send_error(self,status,*args):self.status=status
            def send_response(self,status):self.status=status
            def send_header(self,*args):pass
            def end_headers(self):pass
        valid=b.canonical({'law_version':b.LAW_VERSION});padded=valid+b' '*(262144-len(valid))
        for raw,length,status in [(valid,str(len(valid)),200),(padded,'262144',200),(padded+b' ','262145',400),
                (valid,'-1',400),(valid,'+3',400),(valid,'',400),(valid,'0000001',400),(valid,'１２',400),
                (valid,str(len(valid)+1),422),(b'{"law_version":"poc-breadth-longitudinal-v3","x":NaN}','56',422),
                (b'{"law_version":"poc-breadth-longitudinal-v3","x":1,"x":2}',None,422),
                (b'{"law_version":"poc-longitudinal-v2"}',None,422),(b'[]','2',422),
                (b'{"law_version":"poc-breadth-longitudinal-v3","x":'+b'['*10000+b'0'+b']'*10000+b'}',None,422)]:
            peer=Peer(raw,str(len(raw)) if length is None else length)
            with self.subTest(length=length,status=status):env['breadth_POST'](peer);self.assertEqual(peer.status,status)
        self.assertEqual(len(called),2)

    def test_source_guards_are_active_before_any_runtime_access(self):
        self.assertEqual(os.environ,{}) # literal fixture, never real env copied
        import sys
        original=sys.modules['__main__'].ORIGINAL_ENVIRON
        for call in (lambda:original['SOURCE_ONLY_NEVER_FETCHED'],lambda:original.get('SOURCE_ONLY_NEVER_FETCHED'),
                lambda:iter(original),lambda:len(original),lambda:original.copy(),lambda:'SOURCE_ONLY_NEVER_FETCHED' in original):
            with self.assertRaises(AssertionError):call()
        for module in ('numpy','pymc','sqlite3','ctypes','services.foundation.store','apps.foundation.app'):
            with self.subTest(module=module),self.assertRaises(AssertionError):__import__(module)
        for call in (lambda:subprocess.Popen(['not-executed']),lambda:socket.socket(),lambda:Path('artifacts/private-never-open/auth.json').read_bytes()):
            with self.assertRaises(AssertionError):call()


if __name__=='__main__':unittest.main()
