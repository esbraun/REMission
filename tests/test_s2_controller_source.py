"""Labeled inert SOURCE records and DB doubles; never actual app/fit/browser evidence."""
import ast
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from contracts.domain.analysis import canonical,sha,reference
from contracts.domain.entities import DecisionSnapshot
from contracts.domain.evidence_v2 import exact_ref
from contracts.domain.protocol import ObservedHistoryV21,RECORD_ADAPTER_V21,SUPPORT_REF
from contracts.domain.support_s2_controller import CONFIG_REF,ControllerCommand

ROOT=Path(__file__).resolve().parents[1]
FILE='services/foundation/support_s2_controller.py'
AT=datetime(2026,1,15,12,tzinfo=timezone.utc)
BEFORE=AT-timedelta(days=14)


def load(path, **bindings):
    """Execute actual source; ONLY service-relative imports are replaced seams."""
    tree=ast.parse((ROOT/path).read_text(encoding='utf-8'))
    class ReplaceServiceImports(ast.NodeTransformer):
        def visit_ImportFrom(self,node):return None if node.level or (node.module or '').startswith('services') else node
    tree=ReplaceServiceImports().visit(tree)
    ns=dict(__name__='UNIT_actual_source',**bindings)
    exec(compile(ast.fix_missing_locations(tree),str(ROOT/path),'exec'),ns)
    return ns


def header(name,patient,at):
    return dict(schema_version='1.0.0',synthetic=True,record_id=name,patient_id=patient,event_at=at.isoformat(),
        recorded_at=at.isoformat(),available_at=at.isoformat(),source=dict(id='UNIT-INERT',version='1.0.0',
        adapter='research_configuration',raw_sha256=sha(name)),lineage_id=name,revision=1,supersedes=None,
        duplicate_of=None,record_status='active')


def typed(value):return RECORD_ADAPTER_V21.validate_json(canonical(value))
def history(records):return ObservedHistoryV21.model_validate_json(canonical(dict(schema_version='2.1.0',synthetic=True,
    kind='observed_history',patient_id='UNIT-patient',records=[r.model_dump(mode='json') for r in records])))


def snapshot(name,at,eligibility=None):
    return typed(dict(**header(name,'UNIT-patient',at),kind='decision_snapshot',cutoff=at.isoformat(),
        patient_version=1,state_version=1,consent_version=1,eligibility_version=1,
        workflow=dict(clinical='treatment_active',learning='support_active',data_readiness='ready',hold_reasons=[],
            support_mode='adaptive',support_policy=CONFIG_REF),view=dict(patient_id='UNIT-patient',mode='current',snapshot_id=None),
        eligibility=eligibility or [dict(action=a,status='eligible',reasons=[]) for a in ('support_prompt','no_prompt','behavioral_continue')],
        outcome='UNIT quality',horizon_days=1,estimand=reference('UNIT-estimand','inert'),model=reference('UNIT-model','inert'),posterior=None,evidence=[],policy=CONFIG_REF))


def consent(at=BEFORE-timedelta(seconds=1),status='active'):
    return typed(dict(**header('UNIT-consent','UNIT-patient',at),kind='consent',component='mrt_bandit',consent_version='UNIT',
        oversight_version='UNIT',consent_status=status,oversight_status='approved_synthetic' if status=='active' else 'withdrawn',
        effective_at=at.isoformat(),expires_at=None,withdrawn_at=None if status=='active' else at.isoformat()))


class Cursor:
    def __init__(self,rows=()):self.rows=list(rows)
    def fetchone(self):return self.rows[0] if self.rows else None
    def fetchall(self):return self.rows


class InertDB:
    """Explicit SQL double. Unknown access fails, never opens SQLite."""
    def __init__(self,records,snapshot):
        self.records=records;self.snapshot=snapshot;self.writes=[];self.audit=[]
    def execute(self,sql,args=()):
        if sql=='SELECT snapshot FROM decisions WHERE id=?':return Cursor([(self.snapshot.model_dump_json(),)])
        if sql=='INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)':
            record=RECORD_ADAPTER_V21.validate_json(args[6]);self.records.append(record);self.writes.append(record.kind);return Cursor()
        if sql=='INSERT INTO state_changes VALUES(?,?,?,?,?)':self.audit.append(args);self.writes.append('basis');return Cursor()
        raise AssertionError('Unmodeled UNIT SQL: '+sql)


def fixture(allowed=('support_prompt','no_prompt'),saved=None):
    c=consent();old=snapshot('UNIT-original',BEFORE)
    def approve(name,option=None):
        return typed(dict(**header(name,'UNIT-patient',BEFORE),kind='approval',decision_id=old.record_id,
            option=option,permitted_options=[] if option else ['support_prompt','no_prompt'],clinician_id='UNIT-owner',
            purpose='ordinary_treatment' if option else 'randomization_protocol',expected_patient_version=1,
            expected_state_version=1,expected_consent_version=1,expected_eligibility_version=1))
    ap=approve('UNIT-envelope');background_approval=approve('UNIT-background-approval','behavioral_continue')
    background=typed(dict(**header('UNIT-background','UNIT-patient',BEFORE),kind='assignment',decision_id=old.record_id,
        approval_id=background_approval.record_id,option='behavioral_continue',experimental=False,component=None,
        probability=None,seed=None,support_policy=CONFIG_REF,patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None))
    envelope=typed(dict(**(header('UNIT-envelope-snapshot','UNIT-patient',BEFORE)|dict(schema_version='2.1.0')),
        kind='protocol_snapshot',family='support',protocol=SUPPORT_REF,template=SUPPORT_REF,
        consent_refs=[exact_ref(c).model_dump()],approval_refs=[exact_ref(ap).model_dump()],background_ref=exact_ref(background).model_dump(),
        support_refs=[],activation_at=BEFORE.isoformat()))
    eligibility=[dict(action=a,status='eligible' if a in allowed else 'excluded',reasons=[] if a in allowed else ['UNIT mask']) for a in ('support_prompt','no_prompt')]
    current=snapshot('UNIT-current',AT,eligibility)
    records=[c,old,ap,background_approval,background,envelope]
    db=InertDB(records,current)
    state=dict(workflow=current.workflow.model_dump(mode='json'),simulation=dict(day=14,seed=7,index=1,support=[],
        support_controller=dict(status='active',snapshot_id=envelope.record_id,approval_id=ap.record_id,actor='UNIT-owner')))
    patient=dict(id='UNIT-patient',owner_id='UNIT-owner',current_decision=current.record_id,
        version=1,state_version=1,consent_version=1,eligibility_version=1)
    # Run real persist and snapshot validator against typed records; only Store I/O is inert.
    from contracts.domain.evidence_v2 import projection_hash
    persist_source=ast.parse((ROOT/'services/foundation/nof1.py').read_text())
    fn=next(n for n in persist_source.body if isinstance(n,ast.FunctionDef) and n.name=='persist')
    ns=dict(RECORD_ADAPTER_V21=RECORD_ADAPTER_V21,canonical=canonical,digest=lambda x:hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest(),timestamp=lambda x:x.isoformat())
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual_nof1_persist','exec'),ns)
    protocol=load('services/foundation/protocol.py')
    code=load(FILE,history=lambda db,p:history(db.records),patient_clock=lambda p,n:AT,record_header=header,persist=ns['persist'],
        active_episodes=lambda db,p:[],validate_snapshot=protocol['validate_snapshot'])
    code['mask']=lambda full,state,at,received_at,**kw:(allowed,[] if len(allowed)==2 else ['UNIT mask'])
    code['saved_status']=lambda *args:dict(saved=saved or dict(summary_available=False,serving_authority=False,reason='UNIT unavailable'))
    code['require_executable']=lambda *args:None
    return code,db,patient,state


class ScalarTests(unittest.TestCase):
    def setUp(self):self.code=load(FILE)
    def test_contract_denies_history_and_extra_keys(self):
        base=dict(schema_version='s2-controller-source-1.0.0',mode='current',action='approve',decision_id='UNIT-current',expected_version=1,
            expected_state_version=1,expected_consent_version=1,expected_eligibility_version=1,rationale='UNIT explicit review')
        self.assertEqual(ControllerCommand.model_validate(base).action,'approve')
        for change in (dict(mode='historical'),dict(serving_authority=True),dict(expected_version=0)):
            with self.assertRaises(ValueError):ControllerCommand.model_validate(base|change)
    def test_saved_authority_and_finite_bounds(self):
        for p,expected in ((0.,.1),(.4,.4),(1.,.9)):
            result=self.code['final_distribution'](('support_prompt','no_prompt'),dict(summary_available=True,serving_authority=True,status='candidate_ready',probability=p))
            self.assertAlmostEqual(result[1]['support_prompt'],expected)
        for change in (dict(serving_authority=False),dict(status='fallback'),dict(summary_available=False)):
            result=self.code['final_distribution'](('support_prompt','no_prompt'),dict(summary_available=True,serving_authority=True,status='candidate_ready',probability=.8)|change)
            self.assertEqual(result[1],dict(support_prompt=.5,no_prompt=.5));self.assertIsNotNone(result[2])
        with self.assertRaises(ValueError):self.code['final_distribution'](('support_prompt','no_prompt'),dict(summary_available=True,serving_authority=True,probability=float('nan')))
    def test_one_none_and_invalid_masks(self):
        saved=dict(summary_available=False,serving_authority=False)
        self.assertEqual(self.code['final_distribution'](('no_prompt',),saved)[1],dict(support_prompt=0.,no_prompt=1.))
        self.assertEqual(self.code['final_distribution']((),saved)[0],'unavailable')
        for allowed in (('no_prompt','no_prompt'),('support_prompt',),('MED_A',)):
            with self.assertRaises(ValueError):self.code['final_distribution'](allowed,saved)
    def test_gate_still_closed(self):
        with self.assertRaisesRegex(ValueError,'unqualified'):self.code['require_executable']()


class DecisionTests(unittest.TestCase):
    def test_distribution_before_one_keyed_draw_and_assignment(self):
        code,db,patient,state=fixture(saved=dict(summary_available=True,serving_authority=True,status='candidate_ready',probability=.8))
        calls=[]
        def draw(seed):
            self.assertIn('support_decision',db.writes);self.assertNotIn('assignment',db.writes)
            calls.append(seed);return .7
        code['keyed_uniform']=draw
        decision,assignment=code['decide'](db,NS(fault=None),patient,state,AT)
        self.assertEqual(len(calls),1);self.assertEqual(assignment.option,'support_prompt')
        self.assertEqual(assignment.probability,decision.probabilities[assignment.option]);self.assertEqual(assignment.seed.process,'s2-support-assignment-v1')
        self.assertEqual(json.loads(db.audit[0][4])['probabilities'],decision.probabilities)
    def test_unavailable_and_deterministic_consume_no_draw(self):
        for allowed in ((),('no_prompt',)):
            code,db,patient,state=fixture(allowed)
            code['keyed_uniform']=lambda seed:(_ for _ in ()).throw(AssertionError('RNG forbidden'))
            decision,assignment=code['decide'](db,NS(fault=None),patient,state,AT)
            self.assertEqual(assignment is None,not allowed)
            if assignment:self.assertIsNone(assignment.seed)
    def test_fallback_is_frozen_against_late_result(self):
        code,db,patient,state=fixture();code['keyed_uniform']=lambda seed:.6
        decision,_=code['decide'](db,NS(fault=None),patient,state,AT);original=decision.model_dump_json()
        code['saved_status']=lambda *args:dict(saved=dict(summary_available=True,serving_authority=True,status='candidate_ready',probability=.9))
        self.assertEqual(decision.model_dump_json(),original)
        with self.assertRaisesRegex(ValueError,'already_persisted'):code['decide'](db,NS(fault=None),patient,state,AT)
    def test_fault_after_distribution_can_roll_back_whole_inert_transaction(self):
        code,db,patient,state=fixture();before=copy.deepcopy(db.__dict__)
        def fault(stage):raise RuntimeError(stage)
        try:code['decide'](db,NS(fault=fault),patient,state,AT)
        except RuntimeError:db.__dict__=before  # LABELED transaction rollback double
        self.assertEqual(db.writes,[]);self.assertEqual(db.audit,[])
    def test_stale_versions_fail_before_draw(self):
        code,db,patient,state=fixture();patient['version']=2
        with self.assertRaisesRegex(ValueError,'exact_current'):code['decide'](db,NS(fault=None),patient,state,AT)
        self.assertEqual(db.writes,[])


class MaskTests(unittest.TestCase):
    def setUp(self):
        self.code=load(FILE);self.state=dict(workflow=dict(clinical='treatment_active',learning='support_active',data_readiness='ready',hold_reasons=[],support_mode='adaptive'),
            simulation=dict(support_controller=dict(status='active',snapshot_id='UNIT-approved')))
    def mask(self,records):return self.code['mask'](history(records),self.state,AT,AT)[0]
    def test_consent_withdrawal_exact_cutoff_and_retraction(self):
        self.assertEqual(set(self.mask([consent()])),{'support_prompt','no_prompt'})
        c=consent(AT,'withdrawn');self.assertEqual(self.mask([c]),())
        c=consent().model_copy(update=dict(record_status='retracted'));self.assertEqual(self.mask([c]),())
    def test_hold_and_readiness(self):
        for key,value in (('hold_reasons',['review']),('data_readiness','stale')):
            self.state['workflow'][key]=value;self.assertEqual(self.mask([consent()]),())
    def test_N_block_washout_and_no_automatic_reentry(self):
        for learning in ('nof1_block','nof1_washout'):
            self.state['workflow']['learning']=learning;self.assertEqual(self.mask([consent()]),('no_prompt',))
        self.state['workflow']['learning']='support_active'
        for status in ('stopped','completed'):
            self.state['simulation']['nof1']=dict(status=status);self.assertEqual(self.mask([consent()]),())
            self.state['simulation']['support_controller']['nof1_review_identity']=sha(self.state['simulation']['nof1'])
            self.assertEqual(set(self.mask([consent()])),{'support_prompt','no_prompt'})
    def test_expiry_is_exclusive_and_future_consent_does_not_authorize(self):
        c=consent().model_copy(update=dict(expires_at=AT));self.assertEqual(self.mask([c]),())
        self.assertEqual(self.mask([consent(AT+timedelta(microseconds=1))]),())
    def test_delivered_burden_includes_tonight_and_consecutive_boundary(self):
        def delivered(name,at):
            return typed(dict(**header(name,'UNIT-patient',at),kind='delivery',assignment_id=name+'-assignment',option='support_prompt',
                stage='delivered',adherence=1.,rescue=False,protocol_deviations=[]))
        c=consent()
        self.assertEqual(self.mask([c,delivered('yesterday',AT-timedelta(days=1)+timedelta(hours=8))]),('no_prompt',))
        three=[delivered('prompt-'+str(day),AT-timedelta(days=day)+timedelta(hours=8)) for day in (2,4,6)]
        self.assertEqual(self.mask([c,*three]),('no_prompt',))
        # Oldest delivery just outside the previous-six-night window frees tonight's third slot.
        three[-1]=delivered('outside',AT-timedelta(days=6,microseconds=1))
        self.assertEqual(set(self.mask([c,*three])),{'support_prompt','no_prompt'})


class SavedReadTests(unittest.TestCase):
    """Exact control flow, metadata-only parser double; never a saved fit admission."""
    def setUp(self):
        self.calls=[];self.context=NS(reference=NS())
        self.product=NS(context=self.context,fit=NS(product=NS(initial=NS(export=NS(provenance=NS(origin=BEFORE,cutoff_day=14))))))
        self.context.decision=NS(cutoff=AT)
        self.row=dict(job_id='UNIT-prediction',status='completed',cutoff=AT.isoformat(),finished_at=AT.isoformat(),failure_reason=None,request_json='UNIT-parser-double')
        self.db=NS(execute=lambda sql,args:Cursor([self.row]))
        tree=ast.parse((ROOT/FILE).read_text())
        fn=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='saved_status'))
        fn.body=[n for n in fn.body if not isinstance(n,ast.ImportFrom)]
        from contracts.domain.support_s2_controller import SavedScalar
        self.ns=dict(SavedScalar=SavedScalar,timedelta=timedelta,INPUT_CAP=10485760,
            SavedPredictionInput=NS(model_validate_json=lambda raw:self.product),
            current_context=lambda *args:self.context,read_summary=lambda *args,**kwargs:self.read(**kwargs))
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual_saved_status','exec'),self.ns)
    def read(self,**kwargs):
        self.calls.append(kwargs)
        return dict(summary_available=False,serving_authority=False,reason='UNIT existing admission off')
    def test_expiry_before_day28_avoids_scalar_read_and_never_renews(self):
        result=self.ns['saved_status'](self.db,'UNIT-owner',dict(id='UNIT-patient'),BEFORE+timedelta(days=28))
        self.assertEqual(result['saved']['reason'],'saved_prediction_expired');self.assertEqual(self.calls,[])
    def test_stale_context_avoids_scalar_read(self):
        self.ns['current_context']=lambda *args:NS(reference='UNIT changed')
        result=self.ns['saved_status'](self.db,'UNIT-owner',dict(id='UNIT-patient'),AT)
        self.assertEqual(result['saved']['reason'],'saved_prediction_stale_current_context');self.assertEqual(self.calls,[])
    def test_read_passes_current_context_fit_and_original_at_without_launch(self):
        result=self.ns['saved_status'](self.db,'UNIT-owner',dict(id='UNIT-patient'),AT)
        self.assertEqual(len(self.calls),1);self.assertIs(self.calls[0]['current_context'],self.context)
        self.assertIs(self.calls[0]['current_fit'],self.product.fit);self.assertEqual(self.calls[0]['at'],AT)
        self.assertFalse(result['saved']['summary_available'])
    def test_pending_and_failed_do_not_attempt_current_projection(self):
        self.ns['current_context']=lambda *args:(_ for _ in ()).throw(AssertionError('pending projection'))
        for status in ('queued','running','failed'):
            self.row['status']=status
            result=self.ns['saved_status'](self.db,'UNIT-owner',dict(id='UNIT-patient'),AT)
            self.assertEqual(result['saved']['reason'],'saved_prediction_'+status)
        self.assertEqual(self.calls,[])
