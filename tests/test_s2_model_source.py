"""Actual observed scalar adapter, strict provenance and AST only; no science."""
import ast
import copy
import os
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import unittest
from pydantic import ValidationError
from unittest.mock import patch
from contracts.domain.analysis import reference,sha
from contracts.domain.protocol_request import EXECUTABLE_CONFIGURATIONS
from contracts.domain.support_s2 import DEFINITIONS as PREDICTION_DEFINITIONS
from contracts.domain.support_s2_fit import CONFIG,MODEL,MODEL_REF,PRIOR,PRIOR_REF,S2FitProvenance
from methods.support.s2_data import prepare,InvalidInput,UnsupportedInput,Unavailable,CohortData
from s2_model_fixtures import cohort,provenance,history

ROOT=Path(__file__).resolve().parents[1]


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.histories=cohort();cls.source=provenance(cls.histories);cls.data=prepare(cls.histories,cls.source)

    def test_distinct_canonical_v2_fit_definitions_never_activate_prediction(self):
        self.assertEqual((MODEL['id'],MODEL['version']),('poc-support-policy-working-v2','2.0.0'))
        self.assertEqual((PRIOR['id'],PRIOR['version']),('poc-support-policy-prior-v2','2.0.0'))
        self.assertEqual(MODEL_REF,reference(MODEL['id'],MODEL)|dict(version='2.0.0'))
        self.assertEqual(PRIOR_REF,reference(PRIOR['id'],PRIOR)|dict(version='2.0.0'))
        self.assertNotEqual(MODEL_REF,PREDICTION_DEFINITIONS['model']);self.assertNotEqual(PRIOR_REF,PREDICTION_DEFINITIONS['prior'])
        self.assertFalse(CONFIG['executable']);self.assertFalse(CONFIG['serving_authority']);self.assertFalse(EXECUTABLE_CONFIGURATIONS)

    def test_full_grid_explicit_nonfirst_target_and_original_predecision_four_features(self):
        data=self.data;self.assertEqual(data.target_index,7);self.assertEqual(len(data.members),12)
        p=data.members[0];self.assertEqual(p.nights,tuple(range(1,15)))
        self.assertEqual([r.index for r in p.rows],list(range(14)))
        self.assertEqual(p.rows[0].x,(7.,1.,0.,1/84))
        # Night2 missing does not erase the older observed night1 quality0.
        self.assertEqual(p.rows[2].x,(0.,0.,1.,3/84))
        self.assertEqual(p.rows[0].quality,0.);self.assertEqual(p.rows[2].quality,10.)
        self.assertEqual(p.rows[6].x[2],2.)
        self.assertEqual(p.rows[7].x[2],1.)
        self.assertTrue(all(len(r.x)==4 for r in p.rows if r.x is not None))

    def test_persisted_final_probability_and_deterministic_zero_centering_not_s1_filter(self):
        p=self.data.members[0]
        self.assertEqual((p.rows[0].action,p.rows[0].probability),(1,.25))
        self.assertEqual((p.rows[1].action,p.rows[1].probability),(0,.25))
        deterministic=p.rows[3];self.assertEqual(deterministic.action-deterministic.probability,0.)
        self.assertIsNotNone(deterministic.quality);self.assertFalse(deterministic.two_action)
        self.assertEqual(p.observed_counts,(4,5));self.assertEqual(p.missing_counts,(2,0))

    def test_missing_pending_undefined_unavailable_and_missing_final_latent_state_distinct(self):
        p=self.data.members[0]
        self.assertEqual((p.rows[1].status,p.rows[4].status,p.rows[5].status),('missing','pending','undefined'))
        self.assertIsNone(p.rows[5].action);self.assertEqual(p.night_status[5],'unavailable:undefined')
        self.assertEqual(p.night_status[-1],'missing');self.assertEqual(p.nights[-1],14)
        self.assertTrue(all(r.quality is None for r in (p.rows[1],p.rows[4],p.rows[5],p.rows[-1])))
        self.assertEqual(len(p.observed),10)

    def test_prior_only_target_with_two_arm_missing_opportunities_stays_in_joint12(self):
        h=cohort(target_missing=True);data=prepare(h,provenance(h));target=data.members[data.target_index]
        self.assertTrue(target.prior_hierarchy_only);self.assertEqual(target.observed,())
        self.assertEqual(target.missing_counts,(7,6));self.assertEqual(len(data.members),12)
        empty=cohort(all_missing=True)
        with self.assertRaisesRegex(Unavailable,'observation-free'):prepare(empty,provenance(empty))

    def test_cumulative_day28_retains_previous_row_identities_and_original_fit_definitions(self):
        h=cohort(day=28);data=prepare(h,provenance(h));self.assertEqual(data.members[0].nights,tuple(range(1,29)))
        self.assertEqual(data.members[0].rows[:14],self.data.members[0].rows)
        self.assertEqual(data.provenance.definitions['prior'].model_dump(),PRIOR_REF)
        self.assertFalse(hasattr(data,'previous_posterior'))

    def test_changed_assignment_probability_duplicate_outcome_or_missing_feature_fail_closed(self):
        for change in (dict(bad_probability=2),dict(bad_probability=4),dict(duplicate_outcome=3),dict(missing_feature=3),
                       dict(bad_window=3),dict(bad_approval=3),dict(held=3),dict(bad_snapshot=3)):
            h=cohort(member_change=change)
            with self.subTest(change=change),self.assertRaises(InvalidInput):prepare(h,provenance(h))

    def test_order_target_member_cutoff_digest_private_or_configuration_corruption_rejected(self):
        with self.assertRaises(InvalidInput):prepare(tuple(reversed(self.histories)),self.source)
        with self.assertRaises(InvalidInput):prepare(self.histories[:-1],self.source)
        for change in ('target','membership','history','config','private','owner','clock'):
            p=self.source.model_dump()
            if change=='target':p['target_id']='UNIT-foreign'
            elif change=='membership':p['membership_sha256']='f'*64
            elif change=='history':p['histories_sha256']='f'*64
            elif change=='config':p['configuration']['sha256']='f'*64
            elif change=='private':p['private_truth']={}
            elif change=='owner':p['owner_id']=''
            else:p['cutoff']+=timedelta(seconds=1)
            with self.subTest(change=change),self.assertRaises((ValueError,ValidationError)):
                prepare(self.histories,p)

    def test_unvalidated_instance_future_record_or_changed_ref_cannot_bypass_revalidation(self):
        h=list(self.histories);records=list(h[0].records);i=next(i for i,r in enumerate(records) if r.kind=='daily_report')
        records[i]=records[i].model_copy(update=dict(available_at=h[0].cutoff))
        h[0]=h[0].model_copy(update=dict(records=records))
        with self.assertRaises(ValidationError):prepare(h,self.source)
        h=list(self.histories);records=list(h[0].records)
        records[i]=records[i].model_copy(update=dict(sleep_quality=9.111))
        h[0]=h[0].model_copy(update=dict(records=records))
        with self.assertRaises(ValidationError):prepare(h,self.source)

    def test_late_available_original_quality_does_not_leak_then_becomes_available(self):
        h=cohort(member_change=dict(late_report=1));data=prepare(h,provenance(h))
        self.assertEqual(data.members[0].rows[1].x[:2],(7.,1.))
        self.assertEqual(data.members[0].rows[2].x[:2],(0.,0.))

    def test_current_reward_revision_once_and_temporary_context_activation_gaps_explicit(self):
        h=cohort(member_change=dict(correction=14,statuses={14:'observed'}));data=prepare(h,provenance(h))
        row=data.members[0].rows[-1]
        self.assertEqual(row.reward_revision[1],2);self.assertEqual(row.quality,4.321)
        self.assertEqual(sum(r.night==14 for r in data.members[0].observed),1)
        for change,reason in ((dict(correction=1),'corrected original-context'),(dict(activation_day=1),'delayed-activation')):
            h=cohort(member_change=change)
            with self.subTest(change=change),self.assertRaisesRegex(UnsupportedInput,reason):prepare(h,provenance(h))


class GraphSourceTests(unittest.TestCase):
    def test_opt_in_qualification_draft_hardblocks_before_scientific_imports(self):
        tree=ast.parse((ROOT/'tooling/foundation/s2_model_qualification.py').read_text(encoding='utf-8'))
        guard=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='require_admitted')
        draft=next(n for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='DRAFT_SETTINGS')
        namespace=dict(os=os)
        import math
        namespace['math']=math
        exec(compile(ast.Module(body=[draft,guard],type_ignores=[]),'isolated_actual_opt_in_guard','exec'),namespace)
        with patch.dict(os.environ,{},clear=True),self.assertRaises(PermissionError):namespace['require_admitted'](namespace['DRAFT_SETTINGS'])
        with patch.dict(os.environ,dict(S2_MODEL_SYMBOLIC_QUALIFY='1')),self.assertRaises(PermissionError):namespace['require_admitted'](namespace['DRAFT_SETTINGS'])
        qualify=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='qualify')
        self.assertEqual(qualify.body[0].value.func.id,'require_admitted')
        self.assertGreater(next(i for i,n in enumerate(qualify.body) if isinstance(n,ast.Import)),0)
        self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) and (getattr(n,'module','') or '').startswith('methods') for n in tree.body))
        self.assertNotIn('600',(ROOT/'tooling/foundation/s2_model_qualification.py').read_text(encoding='utf-8'))

    def test_native_model_has_only_canonical_prior_hierarchy_centering_and_observed_rounded_likelihood(self):
        tree=ast.parse((ROOT/'methods/support/s2_model.py').read_text(encoding='utf-8'))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='pm']
        distributions={n.args[0].value:n.func.attr for n in calls if n.func.attr in ('Normal','HalfNormal','Uniform') and isinstance(n.args[0],ast.Constant)}
        self.assertEqual(distributions,dict(mu_alpha='Normal',mu_tau='Normal',b='Normal',s_alpha='HalfNormal',s_tau='HalfNormal',s_e='HalfNormal',s_Q='HalfNormal',rho='Uniform',z='Normal',u='Normal'))
        expected=dict(mu_alpha=(5.,3.),mu_tau=(0.,2.),b=(0.,2.),s_alpha=(2.,),s_tau=(2.,),
                      s_e=(2.,),s_Q=(2.,),rho=(-.95,.95),z=(0.,1.),u=(0.,1.))
        for call in calls:
            if call.func.attr not in ('Normal','HalfNormal','Uniform') or not isinstance(call.args[0],ast.Constant):continue
            parameters=[]
            for value in call.args[1:]:
                self.assertIsInstance(value,ast.Call);self.assertEqual(value.func.id,'F')
                parameters.append(ast.literal_eval(value.args[0]))
            self.assertEqual(tuple(parameters),expected[call.args[0].value])
        source=ast.unparse(tree)
        self.assertIn('r.action - r.probability',source);self.assertNotIn('r.action - 0.5',source)
        self.assertIn('_ar_error(epsilon, rho, s_e, len(patient.nights))',source)
        self.assertIn("log_bin(quality, eta, s_Q, F(0.001), F(10.0))",source)
        self.assertIn("pm.Deterministic('e_T', pt.stack(final), dims='patient')",source)
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='sample' for n in ast.walk(tree)))
        self.assertFalse(any(isinstance(n,ast.ImportFrom) and 'truth' in n.module for n in tree.body))

    def test_actual_production_build_guards_complete12_grid_without_prior_only_target_veto(self):
        tree=ast.parse((ROOT/'methods/support/s2_model.py').read_text(encoding='utf-8'))
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build')
        calls=[];namespace=dict(CohortData=CohortData,S2FitProvenance=S2FitProvenance,_graph=lambda members:calls.append(members) or 'GRAPH_NOT_BUILT')
        exec(compile(ast.Module(body=[function],type_ignores=[]),'isolated_actual_build_scalar_guards','exec'),namespace)
        h=cohort(target_missing=True);data=prepare(h,provenance(h));self.assertEqual(namespace['build'](data),'GRAPH_NOT_BUILT')
        with self.assertRaises(ValueError):namespace['build'](replace(data,members=data.members[:-1]))
        p=replace(data.members[0],nights=tuple(t for t in data.members[0].nights if t!=2))
        with self.assertRaises(ValueError):namespace['build'](replace(data,members=(p,*data.members[1:])))
        self.assertEqual(len(calls),1)
