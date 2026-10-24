"""Labeled inert SOURCE records and DB doubles; never actual app/fit/browser evidence."""
import ast
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import json
import io
from pathlib import Path
from types import SimpleNamespace as NS
from contextlib import contextmanager,nullcontext
from unittest.mock import patch
import unittest
from contracts.domain.analysis import canonical,sha,reference,FIXED_SUPPORT_REF
from contracts.domain.entities import DecisionSnapshot
from contracts.domain.evidence_v2 import exact_ref
from contracts.domain.protocol import ObservedHistoryV21,RECORD_ADAPTER_V21,SUPPORT_REF
from contracts.domain.support_s2_controller import CONFIG_REF,ControllerCommand,InteractiveSupportQualification,REQUIRED_APP_SOURCES,REQUIRED_GENERATOR_SOURCES

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
    ns=dict(__name__='UNIT_actual_source',candidate_context=lambda db:None,reject_candidate=lambda full:None);ns.update(bindings)
    exec(compile(ast.fix_missing_locations(tree),str(ROOT/path),'exec'),ns)
    return ns


INSTALLED_CONTEXT=load('services/foundation/support_s2_invocation.py')['InstalledInteractiveContext']


def header(name,patient,at):
    return dict(schema_version='1.0.0',synthetic=True,record_id=name,patient_id=patient,event_at=at.isoformat(),
        recorded_at=at.isoformat(),available_at=at.isoformat(),source=dict(id='UNIT-INERT',version='1.0.0',
        adapter='research_configuration',raw_sha256=sha(name)),lineage_id=name,revision=1,supersedes=None,
        duplicate_of=None,record_status='active')


def typed(value):
    value=copy.deepcopy(value);value['source']['raw_sha256']=sha({k:v for k,v in value.items() if k!='source'})
    return RECORD_ADAPTER_V21.validate_json(canonical(value))
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
    def __iter__(self):return iter(self.rows)


class InertSupportConnection:
    """Inert stand-in for the optional Store-owned sqlite connection subclass."""
    pass


class InertDB(InertSupportConnection):
    """Explicit SQL double. Unknown access fails, never opens SQLite."""
    def __init__(self,records,snapshot):
        self.records=records;self.snapshot=snapshot;self.writes=[];self.audit=[];self.proofs={};self.receipts={}
        self.raw_sources={};self.tasks={}
        self.in_transaction=False;self.closed=False;self.decisions={snapshot.record_id:snapshot}
        self.control=dict(database_instance_id='UNIT-store',authority_generation=1,enabled=True)
        packet=dict(schema_version='poc-support-interactive-packet-v1',app_commit='0'*40,app_source_closure={p:'0'*64 for p in REQUIRED_APP_SOURCES},
            generator_source_closure={p:'1'*64 for p in REQUIRED_GENERATOR_SOURCES},app_image='sha256:'+'2'*64,generator_image='sha256:'+'3'*64,
            runtime=reference('UNIT-runtime','fabricated metadata only'),configuration=CONFIG_REF,invocation_class='owned-interactive-support-v1',
            store_id='UNIT-store',authority_generation=1,installed_bundle_sha256='4'*64)
        self.q=InteractiveSupportQualification.model_validate_json(canonical(dict(schema_version='poc-support-interactive-qualification-v1',
            packet=packet,packet_sha256=sha(packet),actual_acceptance=reference('UNIT-FAKE-actual','fabricated SOURCE metadata; NO actual acceptance'),
            acceptance_scope='ACTUAL_interactive_producer_accepted')))
        self.expected_control=canonical(self.control)
    def _read_support_binding(self):
        return INSTALLED_CONTEXT(self.q.model_dump_json()),'4'*64,'0'*40,canonical(self.q.packet.runtime.model_dump()),self.expected_control
    def execute(self,sql,args=()):
        if sql=='SELECT snapshot FROM decisions WHERE id=?':return Cursor([(self.decisions.get(args[0],self.snapshot).model_dump_json(),)])
        if sql=='SELECT * FROM patients WHERE id=?':return Cursor([self.patient] if args[0]==self.patient['id'] else [])
        if sql=='SELECT 1 FROM events WHERE id=?':return Cursor([(1,)] if any(r.record_id==args[0] for r in self.records) else [])
        if sql.startswith('SELECT job_id,cutoff,result_json,input_sha256 FROM analysis_attempts'):return Cursor()
        if sql.startswith('SELECT id,patient_id,actor_id,created_at,payload FROM state_changes WHERE patient_id IN'):
            return Cursor([dict(v,id=k,created_at=AT.isoformat()) for k,v in self.proofs.items()])
        if sql=='SELECT id,payload FROM state_changes WHERE patient_id=?':
            return Cursor([dict(id=k,payload=v['payload']) for k,v in self.proofs.items() if v['patient_id']==args[0]])
        if sql=='UPDATE patients SET state_json=? WHERE id=?':self.patient['state_json']=args[0];return Cursor()
        if sql=='INSERT INTO decisions VALUES (?,?,?,?,?)':
            self.snapshot=DecisionSnapshot.model_validate_json(args[2]);self.decisions[args[0]]=self.snapshot;return Cursor()
        if sql=='UPDATE patients SET current_decision=?,cutoff=? WHERE id=?':
            self.patient.update(current_decision=args[0],cutoff=args[1]);return Cursor()
        if sql=='SELECT payload FROM events WHERE patient_id=? ORDER BY available_at,phase,id':
            return Cursor([(r.model_dump_json(),) for r in self.records if r.patient_id==args[0]])
        if sql=='SELECT * FROM receipts WHERE owner_id=? AND session_id=? AND key=?':return Cursor([self.receipts[args]] if args in self.receipts else [])
        if sql=='INSERT INTO receipts VALUES(?,?,?,?,?,?)':
            self.receipts[args[:3]]=dict(scope=args[3],payload_sha256=args[4],response=args[5]);return Cursor()
        if sql=='INSERT INTO tasks VALUES(?,?,?,?,?,?)':
            if args[0] in self.tasks:raise AssertionError('duplicate inert task')
            self.tasks[args[0]]=dict(zip(('id','patient_id','bundle_id','owner_id','due_at','payload'),args));return Cursor()
        if sql=='SELECT * FROM tasks WHERE patient_id=?':
            return Cursor([r for r in self.tasks.values() if r['patient_id']==args[0]])
        if sql=='SELECT t.payload FROM tasks t JOIN patients p ON t.patient_id=p.id WHERE t.id=? AND p.owner_id=?':
            row=self.tasks.get(args[0])
            return Cursor([(row['payload'],)] if row and row['patient_id']==self.patient['id'] and args[1]==self.patient['owner_id'] else [])
        if sql=='SELECT payload FROM events WHERE id=? AND patient_id=? AND kind=?':
            return Cursor([(r.model_dump_json(),) for r in self.records if (r.record_id,r.patient_id,r.kind)==args])
        if sql=='SELECT * FROM service_control WHERE singleton=1':return Cursor([self.control])
        if sql.startswith('PRAGMA '):return Cursor([(1 if 'foreign_keys' in sql else 2,)])
        if sql=='SELECT * FROM patients WHERE id=? AND owner_id=?':
            return Cursor([self.patient] if args==(self.patient['id'],self.patient['owner_id']) else [])
        if sql=='SELECT 1 FROM state_changes WHERE id=?':return Cursor([(1,)] if args[0] in self.proofs else [])
        if sql=='SELECT patient_id,actor_id,payload FROM state_changes WHERE id=?':return Cursor([self.proofs[args[0]]] if args[0] in self.proofs else [])
        if sql=='INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)':
            record=RECORD_ADAPTER_V21.validate_json(args[6]);self.records.append(record);self.raw_sources[record.record_id]=args[8]
            self.writes.append(record.kind);return Cursor()
        if sql=='INSERT INTO state_changes VALUES(?,?,?,?,?)':
            if args[0] in self.proofs:raise AssertionError('duplicate inert insert')
            self.audit.append(args);self.proofs[args[0]]=dict(patient_id=args[1],actor_id=args[2],payload=args[4]);self.writes.append('basis');return Cursor()
        if sql=='UPDATE patients SET state_json=?,version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1 WHERE id=?':
            self.patient['state_json']=args[0]
            for k in ('version','state_version','eligibility_version'):self.patient[k]+=1
            self.writes.append('clock');return Cursor()
        if sql=='UPDATE patients SET state_json=?,version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1,consent_version=consent_version+? WHERE id=?':
            self.patient['state_json']=args[0]
            for k in ('version','state_version','eligibility_version'):self.patient[k]+=1
            self.patient['consent_version']+=args[1];return Cursor()
        if sql in ('BEGIN IMMEDIATE','BEGIN'):
            self.saved=copy.deepcopy({k:v for k,v in self.__dict__.items() if k!='saved' and not k.startswith('_candidate')});self.in_transaction=True;return Cursor()
        raise AssertionError('Unmodeled UNIT SQL: '+sql)
    def commit(self):self.committed=True;self.in_transaction=False
    def rollback(self):
        bindings={k:v for k,v in self.__dict__.items() if k.startswith('_candidate')}
        self.__dict__=self.saved;self.__dict__.update(bindings);self.in_transaction=False
    def close(self):self.closed=True;self.in_transaction=False


def fixture(allowed=('support_prompt','no_prompt'),saved=None,actual_mask=False):
    c=consent();old=snapshot('UNIT-original',BEFORE)
    old=typed(old.model_dump(mode='json')|dict(workflow=old.workflow.model_dump(mode='json')|dict(support_policy=FIXED_SUPPORT_REF),policy=FIXED_SUPPORT_REF))
    def approve(name,option=None):
        return typed(dict(**header(name,'UNIT-patient',BEFORE),kind='approval',decision_id=old.record_id,
            option=option,permitted_options=[] if option else ['support_prompt','no_prompt'],clinician_id='UNIT-owner',
            purpose='ordinary_treatment' if option else 'randomization_protocol',expected_patient_version=1,
            expected_state_version=1,expected_consent_version=1,expected_eligibility_version=1))
    ap=approve('UNIT-envelope');background_approval=approve('UNIT-background-approval','behavioral_continue')
    background=typed(dict(**header('UNIT-background','UNIT-patient',BEFORE),kind='assignment',decision_id=old.record_id,
        approval_id=background_approval.record_id,option='behavioral_continue',experimental=False,component=None,
        probability=None,seed=None,support_policy=FIXED_SUPPORT_REF,patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None))
    envelope=typed(dict(**(header('UNIT-envelope-snapshot','UNIT-patient',BEFORE)|dict(schema_version='2.1.0')),
        kind='protocol_snapshot',family='support',protocol=SUPPORT_REF,template=SUPPORT_REF,
        consent_refs=[exact_ref(c).model_dump()],approval_refs=[exact_ref(ap).model_dump()],background_ref=exact_ref(background).model_dump(),
        support_refs=[],activation_at=BEFORE.isoformat()))
    eligibility=[dict(action=a,status='eligible' if a in allowed else 'excluded',reasons=[] if a in allowed else ['UNIT mask']) for a in ('support_prompt','no_prompt')]
    current=snapshot('UNIT-current',AT,eligibility)
    records=[c,old,ap,background_approval,background,envelope]
    for day in range(1,15):
        value=dict(**(header('UNIT-prior-report-'+str(day),'UNIT-patient',BEFORE+timedelta(days=day,minutes=-1))|dict(schema_version='2.0.0')),
            kind='daily_report',sleep_quality=None,function=None,adverse_symptoms=[],diary_sleep_minutes=None,goals=[],burden=None,missingness='missing')
        value['source'].update(id='poc-longitudinal-v2',version='2.0.0',adapter='patient_report')
        records.append(typed(value))
    db=InertDB(records,current)
    state=dict(stage='ASSIGN-03',workflow=current.workflow.model_dump(mode='json'),simulation=dict(day=14,seed=7,index=1,support=[],panel_id='UNIT-generation',
        origin=BEFORE.isoformat(),law_version='poc-longitudinal-v2',family='support',medications=[],actions=[dict(day=0,option='behavioral_continue',assignment_id=background.record_id)],
        support_controller=dict(status='active',snapshot_id=envelope.record_id,approval_id=ap.record_id,actor='UNIT-owner',command_id='UNIT-command')))
    patient=dict(id='UNIT-patient',owner_id='UNIT-owner',current_decision=current.record_id,
        version=1,state_version=1,consent_version=1,eligibility_version=1,state_json=canonical(state),cutoff=AT.isoformat())
    db.patient=patient
    db.proofs['UNIT-command']=dict(patient_id=patient['id'],actor_id='UNIT-owner',payload=canonical(dict(kind='support_envelope_command',
        command=dict(action='approve',decision_id=old.record_id),envelope_id=envelope.record_id)))
    # Run real persist and snapshot validator against typed records; only Store I/O is inert.
    from contracts.domain.evidence_v2 import projection_hash
    persist_source=ast.parse((ROOT/'services/foundation/nof1.py').read_text())
    fn=next(n for n in persist_source.body if isinstance(n,ast.FunctionDef) and n.name=='persist')
    ns=dict(RECORD_ADAPTER_V21=RECORD_ADAPTER_V21,canonical=canonical,digest=lambda x:hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest(),timestamp=lambda x:x.isoformat())
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual_nof1_persist','exec'),ns)
    protocol=load('services/foundation/protocol.py')
    code=load(FILE,history=lambda db,p:history(db.records),patient_clock=lambda p,n:AT,record_header=header,persist=ns['persist'],
        active_episodes=lambda db,p:[],validate_snapshot=protocol['validate_snapshot'])
    if not actual_mask:code['mask']=lambda full,state,at,received_at,**kw:(allowed,[] if len(allowed)==2 else ['UNIT mask'])
    code['saved_status']=lambda *args:dict(saved=saved or dict(summary_available=False,serving_authority=False,reason='UNIT unavailable'))
    code['require_executable']=lambda *args:None
    authority=load('services/foundation/support_s2_authority.py',SupportConnection=InertSupportConnection,
        InstalledInteractiveContext=INSTALLED_CONTEXT,validate_snapshot=protocol['validate_snapshot'],_validate_support_v21=protocol['_validate_support_v21'],mask=code['mask'],final_distribution=code['final_distribution'])
    code['derive_execution_authorization']=authority['derive_execution_authorization']
    authority['require_executable']=lambda:None  # Explicit SOURCE-only deployment-gate double.
    code['producer_gate']=authority['producer_gate'];code['producer_id']=authority['producer_id']
    protocol['reject_candidate']=authority['reject_candidate']
    code['UNIT_authority']=authority
    authority.update(history=code['history'],record_header=header,persist=ns['persist'])
    code['qualification']=authority['producer_qualification'];code['put']=authority['put']
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


class ProducerConsumerTests(unittest.TestCase):
    def prepared(self,prompt=True):
        code,db,patient,state=fixture(actual_mask=True);code['keyed_uniform']=lambda seed:0. if prompt else .99
        decision,assignment=code['decide'](db,NS(fault=None),patient,state,AT)
        return code,db,patient,state,decision,assignment
    def finish(self,prompt=True,missing=False):
        code,db,patient,state,decision,assignment=self.prepared(prompt)
        offered,canceled=code['dispatch'](db,NS(fault=None),patient,state,decision,assignment,AT)
        delivery=dict(**header('UNIT-delivery','UNIT-patient',AT+timedelta(hours=8)),kind='delivery',assignment_id=assignment.record_id,
            option=assignment.option,stage='delivered',adherence=1.,rescue=False,protocol_deviations=[])
        delivery['source'].update(id='poc-longitudinal-v2',version='2.0.0',adapter='simulation')
        report=dict(**(header('UNIT-report','UNIT-patient',AT+timedelta(days=1,minutes=-1))|dict(schema_version='2.0.0')),
            kind='daily_report',sleep_quality=None if missing else 7.,function=None if missing else 6.,adverse_symptoms=[],
            diary_sleep_minutes=None if missing else 420.,goals=[],burden=None,missingness='missing' if missing else 'observed')
        report['source'].update(id='poc-longitudinal-v2',version='2.0.0',adapter='patient_report')
        db.records.extend([typed(delivery),typed(report)])
        a=code['UNIT_authority']
        link=a['close_stages'](db,NS(fault=None,clock=lambda:AT),patient,decision,assignment,offered,AT,canceled=canceled)
        return code,db,patient,state,decision,assignment,link
    def test_real_authorization_required_in_live_and_protocol_consumers(self):
        code,db,p,state,d,a=self.prepared();authority=code['UNIT_authority'];full=history(db.records)
        authority['validate_live_history'](db,full)
        protocol=load('services/foundation/protocol.py')
        with self.assertRaisesRegex(ValueError,'interactive_authorization'):
            protocol['validate_support_v21'](full,d,AT+timedelta(days=1))
        protocol['validate_support_v21'](full,d,AT+timedelta(days=1),verify_authorization=authority['authorization_verifier'](db,full))
        # A forged apparent admin Approval satisfying ordinary shape still lacks its binding.
        orphan=typed(next(r for r in full.records if r.kind=='approval' and r.record_id.startswith('s2-admin-')).model_dump(mode='json')|
            dict(record_id='s2-admin-forged',lineage_id='s2-admin-forged'))
        with self.assertRaisesRegex(ValueError,'unbound'):authority['validate_live_history'](db,history([*db.records,orphan]))
    def test_closed_prompt_and_no_prompt_stages_project_through_real_consumer(self):
        for prompt in (True,False):
            code,db,p,state,d,a,link=self.finish(prompt)
            authority=code['UNIT_authority'];full=history(db.records);cutoff=AT+timedelta(days=1)
            verify=authority['interactive_stage_verifier'](db,full)
            for closure in (r for r in full.records if r.kind=='support_stage_closure'):verify(closure,cutoff)
            from contracts.domain.evidence_v2 import validate_outcome_link
            validate_outcome_link(full,link,verify_closure=verify)
            reduced=load('services/foundation/protocol.py')['project_protocol'](full,cutoff,family='support',origin=BEFORE,
                verify_closure=verify,verify_authorization=authority['authorization_verifier'](db,full))
            self.assertTrue(any(r.kind=='support_outcome_link' for r in reduced.records))
            self.assertEqual([b.value for b in link.burden],[int(prompt),int(prompt)])
    def test_missing_reward_remains_missing(self):
        *_,link=self.finish(missing=True)
        self.assertEqual(link.reward.status,'missing');self.assertIsNone(link.reward.report_ref)
    def test_forged_settings_or_changed_generation_cannot_supply_qualification(self):
        code,db,p,state,d,a=self.prepared();authority=code['UNIT_authority']
        with self.assertRaisesRegex(ValueError,'qualification_required'):
            authority['qualification'](NS(_read_support_binding=db._read_support_binding))
        db.control['authority_generation']=2
        with self.assertRaisesRegex(ValueError,'generation_mismatch'):authority['qualification'](db)
    def test_changed_basis_actor_owner_versions_and_vector_refuse(self):
        for change in (dict(actor_id='UNIT-foreign'),dict(owner_id='UNIT-foreign'),dict(versions={'version':99}),
                       dict(probabilities={'support_prompt':.9,'no_prompt':.1})):
            code,db,p,state,d,a=self.prepared();authority=code['UNIT_authority']
            basis=authority['get'](db,p['id'],d.execution_receipt)
            basis.update(change)
            from contracts.domain.support_s2_controller import AuthorizationBasis
            with self.assertRaises(ValueError):authority['validate_basis'](db,history(db.records),AuthorizationBasis.model_validate_json(canonical(basis)))
    def test_unknown_offer_and_corrupted_output_are_not_observed_zero(self):
        code,db,p,state,d,a,link=self.finish();authority=code['UNIT_authority'];full=history(db.records)
        closure=next(r for r in full.records if r.kind=='support_stage_closure')
        receipt=authority['get'](db,p['id'],closure.completion_receipt)
        output_id='s2-proof-'+receipt['output_ref']['sha256']
        db.proofs[output_id]['payload']='[]'
        with self.assertRaisesRegex(ValueError,'content_identity'):authority['interactive_stage_verifier'](db,full)(closure,AT+timedelta(days=1))
    def test_actual_offer_precedes_product_and_cancellation_preserves_distribution(self):
        code,db,p,state,d,a=self.prepared();before=d.model_dump_json()
        code['mask']=lambda *args,**kwargs:((),['withdrawn before offer'])
        offered,canceled=code['dispatch'](db,NS(fault=None),p,state,d,a,AT)
        self.assertTrue(canceled);self.assertIsNone(offered);self.assertEqual(d.model_dump_json(),before)
        self.assertFalse(any(r.kind=='delivery' for r in db.records))
    def test_rehashed_missing_extra_duplicate_foreign_and_wrong_stage_outputs_refuse(self):
        from contracts.domain.common import VersionRef
        for case in ('missing_offer','duplicate','foreign_patient','wrong_stage','extra'):
            code,db,p,state,d,a,link=self.finish();authority=code['UNIT_authority']
            closure=next(r for r in db.records if r.kind=='support_stage_closure')
            completion=authority['get'](db,p['id'],closure.completion_receipt)
            output=authority['get'](db,p['id'],VersionRef.model_validate(completion['output_ref']))
            if case=='missing_offer':output=[r for r in output if r['stage']!='offered']
            elif case=='duplicate':output.append(copy.deepcopy(output[0]))
            elif case=='foreign_patient':output[0]['patient_id']='UNIT-foreign'
            elif case=='wrong_stage':output[0]['stage']='taken'
            else:
                extra=copy.deepcopy(output[0]);extra['record_id']='UNIT-extra';extra['lineage_id']='UNIT-extra';output.append(extra)
            ref=reference('poc-support-interactive-stage-output-v1',output)
            db.proofs['s2-proof-'+ref['sha256']]=dict(patient_id=p['id'],actor_id=p['owner_id'],payload=canonical(output))
            completion.update(output_ref=ref,output_bytes=len(canonical(output).encode()),output_sha256=sha(output),output_count=len(output))
            cref=reference('poc-support-interactive-completion-v1',completion)
            db.proofs['s2-proof-'+cref['sha256']]=dict(patient_id=p['id'],actor_id=p['owner_id'],payload=canonical(completion))
            changed=typed(closure.model_dump(mode='json')|dict(completion_receipt=cref))
            db.records=[changed if r.record_id==closure.record_id else r for r in db.records]
            with self.subTest(case=case),self.assertRaises(ValueError):
                authority['interactive_stage_verifier'](db,history(db.records))(changed,AT+timedelta(days=1))
    def test_active_revision_and_completion_clock_substitutions_refuse(self):
        code,db,p,state,d,a,link=self.finish();authority=code['UNIT_authority']
        closure=next(r for r in db.records if r.kind=='support_stage_closure')
        delivery=next(r for r in db.records if r.kind=='delivery' and r.stage=='delivered')
        value=delivery.model_dump(mode='json');value.update(record_id='UNIT-corrected-delivery',revision=2,supersedes=delivery.record_id,
            recorded_at=(AT+timedelta(hours=9)).isoformat(),available_at=(AT+timedelta(hours=9)).isoformat())
        db.records.append(typed(value))
        with self.assertRaises(ValueError):authority['interactive_stage_verifier'](db,history(db.records))(closure,AT+timedelta(days=1))
        code,db,p,state,d,a,link=self.finish();authority=code['UNIT_authority'];closure=next(r for r in db.records if r.kind=='support_stage_closure')
        with self.assertRaises(ValueError):authority['interactive_stage_verifier'](db,history(db.records))(closure,closure.available_at)
    def test_unavailable_outcome_never_claims_observed_zero_burden(self):
        code,db,p,state=fixture(())
        d,a=code['decide'](db,NS(fault=None),p,state,AT)
        value=dict(**(header('UNIT-unavailable-report',p['id'],AT+timedelta(days=1,minutes=-1))|dict(schema_version='2.0.0')),
            kind='daily_report',sleep_quality=7.,function=6.,adverse_symptoms=[],diary_sleep_minutes=420.,goals=[],burden=None,missingness='observed')
        value['source'].update(id='poc-longitudinal-v2',version='2.0.0',adapter='patient_report');db.records.append(typed(value))
        link=code['UNIT_authority']['close_stages'](db,NS(fault=None,clock=lambda:AT),p,d,a,None,AT)
        self.assertEqual(link.reward.status,'pending');self.assertTrue(all(b.status=='pending' and b.value is None for b in link.burden))
        self.assertFalse(any(r.kind=='support_stage_closure' for r in db.records))


def function(path,name,**bindings):
    tree=ast.parse((ROOT/path).read_text())
    fn=copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name))
    class ServiceImports(ast.NodeTransformer):
        def visit_ImportFrom(self,node):return None if node.level else node
    fn=ServiceImports().visit(fn);fn.returns=None
    ns=dict(datetime=datetime,timedelta=timedelta);ns.update(bindings)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),path,'exec'),ns)
    return ns[name]


class RouteAndConnectionTests(unittest.TestCase):
    def test_owned_mutation_and_original_receipt_replay(self):
        code,db,p,state=fixture();calls=[]
        tree=ast.parse((ROOT/'services/foundation/app.py').read_text())
        error=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='APIError')
        ns={};exec(compile(ast.Module(body=[error],type_ignores=[]),'actual_APIError','exec'),ns);APIError=ns['APIError']
        digest=lambda x:hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()
        mutation=function('services/foundation/app.py','mutation_receipt',APIError=APIError,canonical=canonical,digest=digest,json=json)
        save=function('services/foundation/app.py','save_mutation',canonical=canonical,digest=digest)
        data=ControllerCommand.model_validate(dict(schema_version='s2-controller-source-1.0.0',mode='current',action='pause',decision_id='UNIT-current',
            expected_version=1,expected_state_version=1,expected_consent_version=1,expected_eligibility_version=1,rationale='UNIT explicit command'))
        async def body(request,model):return data
        def session(db,request,**kwargs):
            self.assertTrue(kwargs['mutation']);calls.append('mutation_session');return dict(account_id='UNIT-owner',token_hash='UNIT-auth')
        def own(db,patient,owner):
            calls.append('ownership')
            if patient!=p['id'] or owner!=p['owner_id']:raise APIError(404,'not_found','Resource not found')
            return p
        def transition(*args):calls.append('transition');return dict(status='paused')
        route=copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='support_command'))
        route.decorator_list=[]
        class Strip(ast.NodeTransformer):
            def visit_ImportFrom(self,node):return None
        route=Strip().visit(route)
        bindings=dict(ControllerCommand=ControllerCommand,Request=object,body=body,store=NS(transaction=lambda **kwargs:nullcontext(db)),
            session=session,own=own,mutation_receipt=mutation,save_mutation=save,transition=transition,settings=NS(clock=lambda:AT),APIError=APIError)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[route],type_ignores=[])),'actual_support_route','exec'),bindings)
        def invoke():
            coroutine=bindings['support_command'](p['id'],NS(headers={'idempotency-key':'UNIT-stable-key'}))
            try:coroutine.send(None)
            except StopIteration as done:return done.value
            raise AssertionError('No actual async wait allowed in SOURCE route fixture')
        self.assertEqual(invoke(),invoke());self.assertEqual(calls.count('transition'),1)
        data.rationale='UNIT materially changed'
        with self.assertRaises(APIError) as error:invoke()
        self.assertEqual(error.exception.code,'idempotency_conflict')
        p['owner_id']='UNIT-foreign'
        with self.assertRaises(APIError) as error:invoke()
        self.assertEqual(error.exception.code,'not_found');self.assertEqual(calls.count('transition'),1)
    def test_orphan_admin_is_rejected_by_actual_live_history_entry(self):
        code,db,p,state=fixture();authority=code['UNIT_authority']
        original=next(r for r in db.records if r.kind=='approval')
        orphan=typed(original.model_dump(mode='json')|dict(record_id='s2-admin-orphan',lineage_id='s2-admin-orphan'))
        db.records=[orphan]
        read=function('services/foundation/workflow.py','history',json=json,canonical=canonical,validate_live_history=authority['validate_live_history'])
        with self.assertRaisesRegex(ValueError,'unbound'):read(db,p['id'])
    def test_default_connection_keeps_original_sqlite_arguments(self):
        calls=[]
        class DB:
            def execute(self,sql):return Cursor([(1 if 'foreign_keys' in sql else 2,)])
        def connect(*args,**kwargs):calls.append((args,kwargs));return DB()
        fn=function('services/foundation/store.py','connect',sqlite3=NS(connect=connect,Row='UNIT-row'),SupportConnection=InertSupportConnection)
        fn(NS(path='UNIT-never-opened',support_qualification=None))
        self.assertEqual(calls,[(('UNIT-never-opened',),dict(isolation_level=None,timeout=5))])


class AtomicAdvanceTests(unittest.TestCase):
    """Actual advance + product admission + Store transaction body; all I/O inert."""
    def preparation(self):
        code,db,p,state=fixture(actual_mask=True);a=code['UNIT_authority'];db.control['last_receipt_at']=(AT-timedelta(hours=1)).isoformat()
        from pydantic import TypeAdapter
        from contracts.domain.entities import ObservedRecord
        digest=lambda x:hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()
        actual_history=lambda db,p:a['validate_live_history'](db,history(db.records))
        class UnitSimulationError(Exception):pass
        admit=function('services/foundation/simulation.py','persist_product',history=actual_history,ADAPTER=TypeAdapter(ObservedRecord),
            LAW='poc-longitudinal-v1',canonical=canonical,digest=digest,timestamp=lambda x:x.isoformat(),instant=datetime.fromisoformat,
            START=BEFORE.isoformat(),timedelta=timedelta,SimulationError=UnitSimulationError,json=json)
        def product(settings,sim,patient,day):
            # Fabricated exhaustive observed product, including the ordinary
            # continuation's day/visit range. Never execute the generator law.
            values=[]
            for night in range(sim['day']+1,day+1):
                support=next((item for item in reversed(sim['support']) if item['day']==night-1),None)
                if support:
                    self.assertIn('support_decision',db.writes)
                    if support['option']=='support_prompt':
                        self.assertTrue(any(r.kind=='delivery' and r.stage=='offered' and r.assignment_id==support['assignment_id'] for r in db.records))
                    values.append(dict(**header('UNIT-advance-delivery-'+str(night),'UNIT-patient',BEFORE+timedelta(days=night-1,hours=8)),kind='delivery',
                        assignment_id=support['assignment_id'],option=support['option'],stage='delivered',adherence=1.,rescue=False,protocol_deviations=[]))
                values.append(dict(**(header('UNIT-advance-report-'+str(night),'UNIT-patient',BEFORE+timedelta(days=night,minutes=-1))|dict(schema_version='2.0.0')),
                    kind='daily_report',sleep_quality=7.,function=6.,adverse_symptoms=[],diary_sleep_minutes=420.,goals=[],burden=None,missingness='observed'))
                values.append(dict(**header('UNIT-background-delivery-'+str(night),'UNIT-patient',BEFORE+timedelta(days=night-1,hours=8)),kind='delivery',
                    assignment_id=sim['actions'][-1]['assignment_id'],option='behavioral_continue',stage='delivered',adherence=1.,rescue=False,protocol_deviations=[]))
                if night%14==0:
                    values.append(dict(**header('UNIT-isi-'+str(night),'UNIT-patient',BEFORE+timedelta(days=night,minutes=-1)),kind='isi',
                        instrument_version='UNIT-inert-ISI',recall_days=14,recall_start=(BEFORE+timedelta(days=night-14,minutes=-1)).isoformat(),
                        recall_end=(BEFORE+timedelta(days=night,minutes=-1)).isoformat(),items=[2,2,2,2,2,1,1]))
            entries=[]
            for value in values:
                value['source'].update(id='poc-longitudinal-v2',version='2.0.0',adapter='patient_report' if value['kind']=='daily_report' else 'simulation')
                r=typed(value);data=r.model_dump(mode='json');raw=canonical({k:v for k,v in data.items() if k!='source'})
                data['source']['raw_sha256']=digest(raw)
                entries.append(dict(record=data,raw_source=raw))
            return dict(name='UNIT patient',records=entries)
        def next_decision(db,patient,received):
            state=json.loads(db.patient['state_json']);day=state['simulation']['day']
            s=snapshot('UNIT-next-'+str(day),BEFORE+timedelta(days=day))
            value=s.model_dump(mode='json')
            value.update(patient_version=db.patient['version'],state_version=db.patient['state_version'],
                eligibility_version=db.patient['eligibility_version'],workflow=state['workflow'])
            db.snapshot=typed(value);db.patient['current_decision']=db.snapshot.record_id;db.patient['cutoff']=db.snapshot.cutoff.isoformat()
        code.update(history=actual_history,product=product,persist_product=admit,close_stages=a['close_stages'],create_decision=next_decision,
            patient_clock=lambda p,n:datetime.fromisoformat(json.loads(p['state_json'])['simulation']['origin'])+timedelta(days=json.loads(p['state_json'])['simulation']['day']))
        a['history']=actual_history
        tx=function('services/foundation/store.py','transaction',contextmanager=contextmanager,
            instant=datetime.fromisoformat,receive=lambda db,at:None,sqlite3=NS(OperationalError=type('UNIT-DBError',(Exception,),{})))
        store=NS(gate=NS(hold=lambda:nullcontext()),connect=lambda:db,validate_control=lambda db:db.control,clock=lambda:AT)
        return code,db,p,state,tx,store
    def test_actual_source_admits_product_closes_stages_and_commits_clock(self):
        code,db,p,state,tx,store=self.preparation()
        with tx(store,write=True):result=code['advance'](db,NS(fault=None,clock=lambda:AT),p,state,15,AT)
        self.assertEqual(result['day'],15);self.assertTrue(db.committed)
        self.assertEqual(json.loads(db.patient['state_json'])['simulation']['day'],15)
        self.assertTrue(any(r.kind=='support_outcome_link' for r in db.records))
        self.assertEqual(db.writes.count('support_decision'),1);self.assertEqual(db.writes.count('assignment'),1)
    def test_each_real_boundary_rolls_back_product_authority_and_clock(self):
        for stage in ('after_support_distribution','after_support_offer','after_support_product','after_support_completion','after_support_outcome','after_support_clock'):
            code,db,p,state,tx,store=self.preparation();code['keyed_uniform']=lambda seed:0.
            before=(len(db.records),copy.deepcopy(db.proofs),db.patient['state_json'])
            def fault(point):
                if point==stage:raise RuntimeError(stage)
            with self.assertRaisesRegex(RuntimeError,stage):
                with tx(store,write=True):code['advance'](db,NS(fault=fault,clock=lambda:AT),p,state,15,AT)
            self.assertEqual((len(db.records),db.proofs,db.patient['state_json']),before)


class CandidateBootstrapTests(unittest.TestCase):
    """Actual consent -> envelope -> product -> create_decision; no ACTUAL ref.

    External GO/receipt and all I/O are labeled inert authority/transaction doubles,
    never host authorization, app execution, SQLite or generator qualification.
    """
    def preparation(self,reactivate=False,post_N=False,later_consent_action=None,later_failure=None):
        from contracts.domain.support_s2_controller import UntrustedInteractiveInvocation
        code,db,p,state,tx,store=AtomicAdvanceTests().preparation();a=code['UNIT_authority']
        invocation_code=load('services/foundation/support_s2_invocation.py',SupportConnection=InertSupportConnection,
            digest=lambda x:hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest())
        contexts=invocation_code['candidate_context']
        a['candidate_context']=contexts;code['candidate_context']=contexts
        error_tree=ast.parse((ROOT/'services/foundation/simulation.py').read_text())
        error_class=next(n for n in error_tree.body if isinstance(n,ast.ClassDef) and n.name=='SimulationError')
        error_ns={};exec(compile(ast.Module(body=[error_class],type_ignores=[]),'actual_SimulationError','exec'),error_ns)
        code['SimulationError']=error_ns['SimulationError']
        # Remove ALL prebuilt support consent/approval/envelope/command fixtures.
        db.records=[r for r in db.records if r.kind not in ('consent','protocol_snapshot') and r.record_id!='UNIT-envelope']
        db.proofs={};state['simulation']['support_controller']=dict(status='unapproved')
        state['workflow'].update(support_policy=FIXED_SUPPORT_REF,support_mode='paused',learning='support_unavailable')
        if post_N:state['simulation']['nof1']=dict(status='completed',review='UNIT inert completed N')
        state['plan']='behavioral_continue';p['name']='UNIT synthetic';p['state_json']=canonical(state)
        packet=db.q.packet.model_dump(mode='json');db.q=None
        installed=dict(control=copy.deepcopy(db.control))
        packet['installed_bundle_sha256']=sha(installed)
        store.installed=NS(model_dump=lambda **kwargs:installed,control=NS(model_dump=lambda **kwargs:installed['control']))
        store.path='UNIT-no-SQLite';store.support_qualification=None
        store.support_source_commit=packet['app_commit'];store.support_runtime_ref=packet['runtime']
        digest=lambda x:hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()
        read_connections=[]
        def open_connection(*args,**kwargs):
            if 'factory' in kwargs:return db
            current=InertDB(copy.deepcopy(db.records),copy.deepcopy(db.snapshot));current.q=None
            for key in ('control','patient','proofs','decisions'):setattr(current,key,copy.deepcopy(getattr(db,key)))
            read_connections.append(current);return current
        connect=function('services/foundation/store.py','connect',sqlite3=NS(connect=open_connection,Row='UNIT-row'),
            SupportConnection=InertSupportConnection,UntrustedInteractiveContext=invocation_code['UntrustedInteractiveContext'],canonical=canonical,digest=digest)
        store.connect=lambda **kwargs:connect(store,**kwargs)
        store.transaction=lambda **kwargs:tx(store,**kwargs)
        invocation_code['UNIT_transaction']=tx;invocation_code['UNIT_read_connections']=read_connections
        flow=load('services/foundation/workflow.py',candidate_context=contexts,validate_live_history=a['validate_live_history'],
            canonical=canonical,digest=digest,timestamp=lambda x:x.isoformat(),instant=datetime.fromisoformat)
        real_history=flow['_producer_history']
        create=function('services/foundation/workflow.py','create_decision',json=json,patient_clock=code['patient_clock'],canonical=canonical,
            digest=digest,timestamp=lambda x:x.isoformat(),instant=datetime.fromisoformat,record_header=header,DecisionSnapshot=DecisionSnapshot,
            reference=flow['reference'],SUPPORT=FIXED_SUPPORT_REF,STAGES=flow['STAGES'],history=real_history,producer_id=a['producer_id'],
            support_eligibility=code['eligibility'],initialize_journal=lambda *args:None,overlay=lambda db,p,s:s,
            summary=lambda *args:[],dispute_reviews=lambda *args:None,active_episodes=lambda *args:[],reconcile=lambda db,row,state,at:state)
        code.update(history=real_history,create_decision=create,persist=a['producer_persist'])
        a.update(history=real_history)
        # persist_product is real source and now reaches the candidate-aware raw
        # history seam; product is the explicit fabricated exhaustive generator double.
        code['persist_product'].__globals__['history']=real_history
        safety=function('services/foundation/workflow.py','current_safety',history=real_history,
            lineage_heads=flow['lineage_heads'],visible_records=flow['visible_records'])
        entry=function('services/foundation/simulation.py','advance',json=json,SimulationError=type('UNIT-SimulationError',(Exception,),{}),
            active_episodes=lambda *args:[],current_safety=safety,advance_support=code['advance'],advance_nof1=lambda *args:(_ for _ in ()).throw(AssertionError('N route')),
            instant=datetime.fromisoformat,timedelta=timedelta,product=code['product'],persist_product=code['persist_product'],
            patient_clock=code['patient_clock'],timestamp=lambda x:x.isoformat(),canonical=canonical,create_decision=create,state_for=flow['state_for'])
        invocation_code.update(transition=code['transition'],advance_simulation=entry,selected=code['selected'],_producer_history=real_history)
        def command(action,version,consent_version,decision):
            return dict(schema_version='s2-controller-source-1.0.0',mode='current',action=action,decision_id=decision,
                expected_version=version,expected_state_version=version,expected_consent_version=consent_version,
                expected_eligibility_version=version,rationale='UNIT explicit synthetic case command')
        after_consent='candidate-s2-decision-'+sha([p['id'],2,AT.isoformat()])[:32]
        operations=[dict(patient_id=p['id'],action='consent',command=command('consent',1,1,p['current_decision'])),
            dict(patient_id=p['id'],action='approve',command=command('approve',2,2,after_consent)),
            dict(patient_id=p['id'],action='advance',target=15)]
        if reactivate:
            after_approve='candidate-s2-decision-'+sha([p['id'],3,AT.isoformat()])[:32]
            after_pause='candidate-s2-decision-'+sha([p['id'],4,AT.isoformat()])[:32]
            operations[2:2]=[dict(patient_id=p['id'],action='pause',command=command('pause',3,2,after_approve)),
                dict(patient_id=p['id'],action='approve',command=command('approve',4,2,after_pause))]
        if later_consent_action is not None:
            version=4;consent_version=2;at=AT+timedelta(days=1)
            sequence=(later_consent_action,) if isinstance(later_consent_action,str) else later_consent_action
            for action in sequence:
                if action in ('advance','visit'):
                    day=(at-BEFORE).days;target=day+1 if action=='advance' else (day//14+1)*14
                    operations.append(dict(patient_id=p['id'],action='advance',target=target))
                    version+=1;at=BEFORE+timedelta(days=target);continue
                current='candidate-s2-decision-'+sha([p['id'],version,at.isoformat()])[:32]
                data=command(action,version,consent_version,current)
                if later_failure=='stale':data['expected_version']-=1
                elif later_failure=='expired':data['consent_expires_at']=at.isoformat()
                operations.append(dict(patient_id=p['id'],action=action,command=data))
                version+=1;consent_version+=int(action in ('consent','withdraw'))
        inv=dict(schema_version='poc-support-untrusted-invocation-v1',invocation_id='UNIT-candidate',packet=packet,packet_sha256=sha(packet),
            source_acceptance=reference('UNIT-source-review','inert SOURCE review identity'),operation_go=reference('UNIT-OP-GO','placeholder'),
            owner_id=p['owner_id'],cases={p['id']:'UNIT-generation'},operations_sha256=sha(operations),
            not_before=(AT-timedelta(minutes=1)).isoformat(),expires_at=(AT+timedelta(minutes=1)).isoformat(),
            receipt_path='UNIT-exclusive-no-host-receipt',output_cap=524288)
        invocation=UntrustedInteractiveInvocation.model_validate_json(canonical(inv))
        inv['operation_go']=reference('UNIT-OP-GO',invocation.authority_body)
        invocation=UntrustedInteractiveInvocation.model_validate_json(canonical(inv))
        authority=io.BytesIO(canonical(invocation.authority_body).encode())
        receipt=io.BytesIO();opened=[]
        @contextmanager
        def exclusive(path,mode):
            self.assertEqual(str(path),invocation.receipt_path);self.assertEqual(mode,'x+b')
            if opened:raise FileExistsError('UNIT exact once receipt consumed')
            opened.append(True);yield receipt
        def run(settings=None):
            with patch.object(Path,'open',exclusive):
                return invocation_code['run_candidate'](store,settings or NS(clock=lambda:AT,fault=None),invocation,operations,external_authority=authority)
        return code,db,p,state,a,invocation_code,invocation,authority,receipt,run,flow

    def test_same_producer_bootstraps_without_ACTUAL_and_cannot_replay(self):
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation()
        result=run()
        self.assertEqual(result['status'],'UNTRUSTED_candidate_evidence');self.assertNotIn('actual_acceptance',canonical(result))
        self.assertIsNone(db.q);self.assertTrue(db.committed);self.assertEqual(json.loads(db.patient['state_json'])['simulation']['day'],15)
        self.assertTrue(any(r.kind=='consent' for r in db.records));self.assertTrue(any(r.kind=='protocol_snapshot' for r in db.records))
        self.assertTrue(any(r.kind=='support_outcome_link' for r in db.records))
        self.assertEqual(db.writes.count('support_decision'),1);self.assertEqual(db.writes.count('assignment'),1)
        self.assertTrue(db.patient['current_decision'].startswith('candidate-s2-'))
        self.assertEqual(result['histories'][0]['current']['current_decision'],result['histories'][0]['current_snapshot']['record_id'])
        self.assertTrue(all('id' in proof and 'created_at' in proof for proof in result['proofs']))
        with self.assertRaises(FileExistsError):run()
        with self.assertRaises(ValueError):h['candidate_context'](db)
        with self.assertRaises(ValueError):a['qualification'](db)
        with self.assertRaises(ValueError):flow['history'](db,p['id'])

    def test_candidate_full_path_rolls_back_each_actual_boundary(self):
        for boundary in ('after_support_distribution','after_support_offer','after_support_product','after_support_completion','after_support_outcome','after_support_clock'):
            code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation();code['keyed_uniform']=lambda seed:0.
            before=(copy.deepcopy(db.records),copy.deepcopy(db.proofs),db.patient['state_json'])
            def fault(point):
                if point==boundary:raise RuntimeError(boundary)
            with self.subTest(boundary=boundary),self.assertRaisesRegex(RuntimeError,boundary):run(NS(clock=lambda:AT,fault=fault))
            self.assertEqual((db.records,db.proofs,db.patient['state_json']),before)
            self.assertTrue(receipt.getvalue());self.assertTrue(db.closed)

    def test_delayed_multiple_activation_and_explicit_post_N_reentry_use_current_envelope(self):
        for post_N in (False,True):
            code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(reactivate=True,post_N=post_N)
            result=run();envelopes=[r for r in db.records if r.kind=='protocol_snapshot']
            self.assertEqual(len(envelopes),2);self.assertTrue(all(r.activation_at==AT and r.activation_at>BEFORE for r in envelopes))
            final=json.loads(db.patient['state_json'])['simulation']['support_controller']
            self.assertIn(final['snapshot_id'],[r.record_id for r in envelopes])
            self.assertEqual(next(r for r in db.records if r.kind=='support_decision').execution_receipt.id,'candidate-s2-'+a['BASIS_ID'])
            self.assertIn('UNTRUSTED_candidate_fallback_no_scientific_authority',canonical(result))
            if post_N:self.assertEqual(final['nof1_review_identity'],sha(state['simulation']['nof1']))

    def test_every_live_consumer_and_renamed_orphan_basis_refuses_candidate(self):
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation();run()
        protocol=load('services/foundation/protocol.py',history=flow['history'],patient_clock=code['patient_clock'],
            instant=datetime.fromisoformat,reject_candidate=a['reject_candidate'])
        prediction=load('services/foundation/support_s2_prediction.py',history=flow['history'])
        with self.assertRaises(ValueError):protocol['export_histories'](db,p['owner_id'],[p['id']],AT+timedelta(days=1))
        with self.assertRaises(ValueError):prediction['current_sources'](db,p['id'],AT+timedelta(days=1),BEFORE,None)
        basis=next(v for v in db.proofs.values() if json.loads(v['payload']).get('schema_version')=='s2-controller-authorization-v1')
        db.records=[];db.proofs={'UNIT-renamed-rehashed-orphan':basis}
        with self.assertRaises(ValueError):a['validate_live_history'](db,history([]))

    def test_external_authority_expiry_packet_case_generation_and_duck_refuse(self):
        for mutation in ('authority','expired','generation','owner','case','packet','duck'):
            code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation()
            if mutation=='authority':go.seek(0);go.write(b'{}');go.truncate()
            elif mutation=='generation':db.control['authority_generation']+=1
            elif mutation=='owner':db.patient['owner_id']='UNIT-foreign'
            elif mutation=='case':
                value=json.loads(db.patient['state_json']);value['simulation']['panel_id']='UNIT-reset';db.patient['state_json']=canonical(value)
            elif mutation=='packet':inv.packet.app_commit='1'*40
            elif mutation=='duck':db._candidate_context=NS(check=lambda *args:inv)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                if mutation=='duck':h['candidate_context'](db)
                else:run(NS(clock=lambda:AT+timedelta(minutes=2) if mutation=='expired' else AT,fault=None))

    def test_authority_and_generation_are_rechecked_during_the_producer(self):
        for change in ('GO','generation','expiry','closed_lease'):
            code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation();now=[AT]
            before=(copy.deepcopy(db.records),copy.deepcopy(db.proofs),db.patient['state_json'])
            def fault(point):
                if point!='after_support_distribution':return
                if change=='GO':go.seek(0);go.write(b'{}');go.truncate()
                elif change=='generation':db.control['authority_generation']+=1
                elif change=='expiry':now[0]=AT+timedelta(minutes=2)
                else:go.close()
            with self.subTest(change=change),self.assertRaises(ValueError):run(NS(clock=lambda:now[0],fault=fault))
            self.assertEqual((db.records,db.proofs,db.patient['state_json']),before)

    def test_renamed_rehashed_and_orphan_candidate_evidence_refuses_all_live_projection(self):
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation();run()
        protocol=load('services/foundation/protocol.py',reject_candidate=a['reject_candidate'])
        for r in db.records:
            if r.source.id!='candidate-s2-interactive-v1':continue
            value=r.model_dump(mode='json');value.update(record_id='UNIT-renamed-'+sha(r.record_id)[:16],lineage_id='UNIT-renamed-'+sha(r.record_id)[:16])
            changed=typed(value)
            for full in (history([changed]),history(db.records)):
                with self.assertRaises(ValueError):a['validate_live_history'](db,full)
                with self.assertRaises(ValueError):protocol['project_protocol'](full,AT+timedelta(days=1),family='support',origin=BEFORE)
        # Even removing visible prefixes/source labels from a support decision
        # cannot replace its candidate qualification with installed provenance.
        decision=next(r for r in db.records if r.kind=='support_decision')
        value=decision.model_dump(mode='json');value['source']['id']='UNIT-renamed-source'
        value.update(record_id='UNIT-renamed-decision',lineage_id='UNIT-renamed-decision')
        changed=typed(value)
        with self.assertRaises(ValueError):a['authorization_verifier'](db,history([changed]))(changed,AT+timedelta(days=1))


    def test_final_journal_rechecks_authority_before_commit_and_consumes_receipt(self):
        for change in ('expiry_equal','expiry_after','GO','receipt','generation','exception'):
            code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation();now=[AT]
            before=(copy.deepcopy(db.records),copy.deepcopy(db.proofs),db.patient['state_json'])
            def journal(current,at):
                if change=='expiry_equal':now[0]=inv.expires_at
                elif change=='expiry_after':now[0]=inv.expires_at+timedelta(seconds=1)
                elif change=='GO':go.seek(0);go.write(b'{}');go.truncate()
                elif change=='receipt':receipt.seek(0);receipt.write(b'UNIT-revoked');receipt.truncate()
                elif change=='generation':current.control['authority_generation']+=1
                else:raise RuntimeError('UNIT-journal-exception')
            h['UNIT_transaction'].__wrapped__.__globals__['receive']=journal
            with self.subTest(change=change),self.assertRaises((ValueError,RuntimeError)) as error:
                run(NS(clock=lambda:now[0],fault=None))
            self.assertNotIn('committed_output_withheld',str(error.exception))
            self.assertFalse(getattr(db,'committed',False));self.assertTrue(db.closed)
            self.assertEqual((db.records,db.proofs,db.patient['state_json']),before)
            self.assertTrue(receipt.getvalue());self.assertFalse(h['UNIT_read_connections'])
            # Restoring revoked external bytes does not refund the consumed path.
            go.seek(0);go.write(canonical(inv.authority_body).encode());go.truncate()
            with self.assertRaises(FileExistsError):run(NS(clock=lambda:AT,fault=None))

    def test_postcommit_rejection_withholds_output_without_claiming_write_rollback(self):
        for change in ('expiry','GO','receipt','generation','current_version','read_finalize_expiry'):
            code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation();now=[AT]
            original_commit=InertDB.commit
            def commit(current):
                original_commit(current)
                if change=='read_finalize_expiry':
                    if current is not db:now[0]=inv.expires_at
                    return
                if current is not db:return
                if change=='expiry':now[0]=inv.expires_at+timedelta(seconds=1)
                elif change=='GO':go.seek(0);go.write(b'{}');go.truncate()
                elif change=='receipt':receipt.seek(0);receipt.write(b'UNIT-revoked');receipt.truncate()
                elif change=='generation':current.control['authority_generation']+=1
                elif change=='current_version':current.patient['version']+=1
            with self.subTest(change=change),patch.object(InertDB,'commit',commit),self.assertRaisesRegex(ValueError,'candidate_committed_output_withheld'):
                run(NS(clock=lambda:now[0],fault=None))
            self.assertTrue(db.committed);self.assertTrue(db.closed)
            self.assertEqual(json.loads(db.patient['state_json'])['simulation']['day'],15)
            self.assertTrue(any(r.kind=='support_outcome_link' for r in db.records));self.assertTrue(receipt.getvalue())
            self.assertTrue(all(read is not db and read.closed for read in h['UNIT_read_connections']))

    def test_ontime_finalization_uses_fresh_read_and_emits_original_exact_output(self):
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation();seen=[]
        h['UNIT_transaction'].__wrapped__.__globals__['receive']=lambda current,at:seen.append((current,at))
        result=run()
        self.assertEqual(seen,[(db,AT)]);self.assertTrue(db.committed)
        self.assertEqual(result['status'],'UNTRUSTED_candidate_evidence')
        self.assertEqual(len(h['UNIT_read_connections']),1)
        self.assertIsNot(h['UNIT_read_connections'][0],db);self.assertTrue(h['UNIT_read_connections'][0].closed)

    def test_real_later_withdraw_command_preserves_lineage_and_prior_as_known_consent(self):
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action='withdraw')
        draws=[];code['keyed_uniform']=lambda seed:draws.append(seed) or 1.
        result=run();consents=[r for r in db.records if r.kind=='consent']
        self.assertEqual(len(consents),2);self.assertEqual(consents[1].event_at,consents[0].event_at)
        self.assertEqual(consents[1].available_at,AT+timedelta(days=1));self.assertEqual(consents[1].supersedes,consents[0].record_id)
        self.assertEqual(json.loads(db.patient['state_json'])['simulation']['support_controller']['status'],'withdrawn')
        self.assertEqual(code['mask'](history(db.records),json.loads(db.patient['state_json']),AT+timedelta(days=1),AT)[0],())
        self.assertEqual(len(draws),1);self.assertFalse(consents[1].permits('mrt_bandit',AT+timedelta(days=1)))
        self.assertEqual([r for r in history(db.records).as_known_at(AT+timedelta(microseconds=1)) if r.kind=='consent'],[consents[0]])
        self.assertEqual(result['status'],'UNTRUSTED_candidate_evidence')

    def test_real_later_renew_command_stays_unapproved_and_preserves_prior_consent(self):
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action='consent')
        run();consents=[r for r in db.records if r.kind=='consent'];current=json.loads(db.patient['state_json'])
        self.assertEqual(len(consents),2);self.assertEqual(consents[1].event_at,consents[0].event_at)
        self.assertEqual(consents[1].revision,2);self.assertEqual(current['simulation']['support_controller']['status'],'unapproved')
        self.assertEqual(code['mask'](history(db.records),current,AT+timedelta(days=1),AT)[0],())

    def test_real_withdraw_renew_revision3_and_new_approval_allow_reentry_only_then(self):
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action=('withdraw','consent'))
        draws=[];code['keyed_uniform']=lambda seed:draws.append(seed) or 1.
        frozen={}
        def capture(point):
            if point=='after_support_clock':
                frozen['records']={r.record_id:r.model_dump_json() for r in db.records}
                frozen['snapshots']={key:value.model_dump_json() for key,value in db.decisions.items()}
        result=run(NS(clock=lambda:AT,fault=capture));consents=sorted((r for r in db.records if r.kind=='consent'),key=lambda r:r.revision)
        self.assertEqual([r.revision for r in consents],[1,2,3]);self.assertEqual(len({r.event_at for r in consents}),1)
        self.assertEqual([r.supersedes for r in consents],[None,consents[0].record_id,consents[1].record_id])
        self.assertEqual([r.consent_status for r in consents],['active','withdrawn','active'])
        self.assertEqual([r.available_at for r in consents],[AT,AT+timedelta(days=1),AT+timedelta(days=1)])
        self.assertEqual(consents[1].withdrawn_at,AT+timedelta(days=1));self.assertIsNone(consents[2].withdrawn_at)
        self.assertEqual(consents[2].effective_at,AT+timedelta(days=1));self.assertEqual(len(draws),1)
        self.assertEqual(consents[1].recorded_at,consents[2].recorded_at)
        self.assertEqual([r for r in history(db.records).as_known_at(AT+timedelta(days=1)) if r.kind=='consent'],[consents[0]])
        inclusive=code['lineage_heads'](code['visible_records'](consents,AT+timedelta(days=1),inclusive=True))
        self.assertEqual(inclusive,[consents[2]])
        for identifier,encoded in frozen['records'].items():self.assertEqual(next(r for r in db.records if r.record_id==identifier).model_dump_json(),encoded)
        for identifier,encoded in frozen['snapshots'].items():self.assertEqual(db.decisions[identifier].model_dump_json(),encoded)
        current=json.loads(db.patient['state_json']);self.assertEqual(current['simulation']['support_controller']['status'],'unapproved')
        self.assertEqual(code['mask'](history(db.records),current,AT+timedelta(days=1),AT)[0],())
        self.assertEqual([db.patient[k] for k in ('version','state_version','consent_version','eligibility_version')],[6,6,4,6])
        self.assertEqual(db.snapshot.patient_version,6);self.assertEqual(db.snapshot.consent_version,4)
        self.assertTrue(all(json.loads(v['payload']).get('actor')==p['owner_id'] for v in db.proofs.values()
            if isinstance(json.loads(v['payload']),dict) and json.loads(v['payload']).get('kind')=='support_envelope_command'))
        for c in consents:
            raw=db.raw_sources[c.record_id];self.assertEqual(c.source.raw_sha256,hashlib.sha256(raw).hexdigest())
            self.assertEqual(RECORD_ADAPTER_V21.validate_json(canonical(json.loads(raw)|dict(source=c.source.model_dump(mode='json')))),c)
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action=('withdraw','consent','approve','advance'))
        draws=[];code['keyed_uniform']=lambda seed:draws.append(seed) or 1.
        run();self.assertEqual(len(draws),2);self.assertEqual(db.writes.count('support_decision'),2)
        self.assertEqual(len([r for r in db.records if r.kind=='protocol_snapshot']),2)
        self.assertEqual(json.loads(db.patient['state_json'])['simulation']['support_controller']['status'],'active')

    def test_real_later_stale_or_expired_renewal_rolls_back_and_consumes_receipt(self):
        for failure,reason in (('stale','stale_support'),('expired','expired_support_consent')):
            code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action='consent',later_failure=failure)
            before=(copy.deepcopy(db.records),copy.deepcopy(db.proofs),db.patient['state_json'])
            with self.subTest(failure=failure),self.assertRaisesRegex(Exception,reason):run()
            self.assertEqual((db.records,db.proofs,db.patient['state_json']),before);self.assertTrue(receipt.getvalue())
            self.assertFalse(getattr(db,'committed',False))
            with self.assertRaises(FileExistsError):run()

    def test_withdrawn_and_merely_renewed_background_continues_without_support(self):
        for commands,status in ((('withdraw','advance'),'withdrawn'),(('withdraw','consent','advance'),'unapproved'),
                                (('pause','advance'),'paused'),(('consent','advance'),'unapproved')):
            code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action=commands)
            draws=[];code['keyed_uniform']=lambda seed:draws.append(seed) or 1.
            old={}
            def capture(point):
                if point=='after_support_clock':
                    old['records']={r.record_id:r.model_dump_json() for r in db.records}
                    old['snapshots']={k:v.model_dump_json() for k,v in db.decisions.items()}
            with self.subTest(commands=commands):
                result=run(NS(clock=lambda:AT,fault=capture));current=json.loads(db.patient['state_json'])
                self.assertEqual(result['status'],'UNTRUSTED_candidate_evidence');self.assertEqual(current['simulation']['day'],16)
                self.assertEqual(current['simulation']['support_controller']['status'],status)
                self.assertEqual(len(draws),1);self.assertEqual(db.writes.count('support_decision'),1);self.assertEqual(db.writes.count('assignment'),1)
                self.assertEqual(len([r for r in db.records if r.kind=='daily_report' and r.event_at>AT]),2)
                later=[r for r in db.records if r.kind=='delivery' and r.event_at>=AT+timedelta(days=1)]
                self.assertEqual([(r.option,r.assignment_id) for r in later],[('behavioral_continue','UNIT-background')])
                self.assertEqual(db.patient['cutoff'],(AT+timedelta(days=2)).isoformat())
                for key,value in old['records'].items():self.assertEqual(next(r for r in db.records if r.record_id==key).model_dump_json(),value)
                for key,value in old['snapshots'].items():self.assertEqual(db.decisions[key].model_dump_json(),value)
                # Ordinary continuation cannot promote the candidate's earlier
                # linked history to LIVE, even after renaming every identifier.
                with self.assertRaises(ValueError):flow['history'](db,p['id'])
                renamed=history([typed(json.loads(r.model_dump_json().replace('candidate-s2-','UNIT-renamed-'))|
                    dict(source=r.source.model_dump(mode='json'))) for r in db.records])
                with self.assertRaises(ValueError):a['reject_candidate'](renamed)

    def test_between_review_commands_visit_continuation_then_fresh_envelope_reentry(self):
        commands=('withdraw','advance','consent','visit','approve','advance')
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action=commands)
        draws=[];code['keyed_uniform']=lambda seed:draws.append(seed) or 1.
        result=run();current=json.loads(db.patient['state_json'])
        self.assertEqual(current['simulation']['day'],29);self.assertEqual(current['simulation']['support_controller']['status'],'active')
        self.assertEqual(len(draws),2);self.assertEqual(db.writes.count('assignment'),2)
        self.assertEqual(len([r for r in db.records if r.kind=='protocol_snapshot']),2)
        self.assertEqual(len([r for r in db.records if r.kind=='isi']),1)
        consents=[r for r in db.records if r.kind=='consent'];self.assertEqual(consents[1].withdrawn_at,AT+timedelta(days=1))
        self.assertEqual(consents[2].effective_at,AT+timedelta(days=2))
        support=[r for r in db.records if r.kind=='support_decision'];self.assertEqual([r.cutoff for r in support],[AT,BEFORE+timedelta(days=28)])
        self.assertEqual(result['histories'][0]['current_snapshot']['cutoff'],(BEFORE+timedelta(days=29)).isoformat().replace('+00:00','Z'))

    def test_inactive_support_continuation_still_enforces_outer_hold_death_and_N_route(self):
        for restriction in ('hold','independent_hold','death','active_N','stopped_N','completed_N'):
            code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action=('withdraw','advance'))
            original=h['transition'];entry=h['advance_simulation'];called=[]
            def transition(*args):
                result=original(*args)
                if args[4].action=='withdraw':
                    current=json.loads(db.patient['state_json'])
                    if restriction=='hold':current['workflow']['hold_reasons']=['UNIT clinical hold']
                    elif restriction.endswith('_N'):current['simulation']['nof1']=dict(status=restriction[:-2])
                    db.patient['state_json']=canonical(current)
                return result
            h['transition']=transition
            if restriction=='independent_hold':entry.__globals__['active_episodes']=lambda *args:[dict(id='UNIT-hold')] if json.loads(db.patient['state_json'])['simulation']['support_controller']['status']=='withdrawn' else []
            if restriction=='death':
                original_safety=entry.__globals__['current_safety']
                entry.__globals__['current_safety']=lambda *args:list(original_safety(*args))+([NS(kind='intercurrent_event',event_type='death')] if json.loads(db.patient['state_json'])['simulation']['support_controller']['status']=='withdrawn' else [])
            entry.__globals__['advance_nof1']=lambda *args:called.append('N') or (_ for _ in ()).throw(AssertionError('N route retained'))
            reason='N route retained' if restriction.endswith('_N') else 'outside_scope' if restriction=='death' else 'clinical_hold'
            with self.subTest(restriction=restriction),self.assertRaisesRegex(Exception,reason):run()
            self.assertFalse(getattr(db,'committed',False));self.assertTrue(receipt.getvalue())
            self.assertEqual(bool(called),restriction.endswith('_N'))

    def test_real_withdrawal_task_owned_read_route_and_stable_command_replay(self):
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action='withdraw')
        tree=ast.parse((ROOT/'services/foundation/app.py').read_text())
        error=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='APIError')
        errors={};exec(compile(ast.Module(body=[error],type_ignores=[]),'actual_APIError','exec'),errors);APIError=errors['APIError']
        digest=lambda x:hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()
        mutation=function('services/foundation/app.py','mutation_receipt',APIError=APIError,canonical=canonical,digest=digest,json=json)
        save=function('services/foundation/app.py','save_mutation',canonical=canonical,digest=digest)
        route=copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='support_command'))
        route.decorator_list=[]
        class Strip(ast.NodeTransformer):
            def visit_ImportFrom(self,node):return None
        route=Strip().visit(route);original=h['transition'];pending=[];responses=[]
        async def body(request,model):return pending[-1]
        def own(current,patient,owner):
            if (patient,owner)!=(p['id'],p['owner_id']):raise APIError(404,'not_found','Resource not found')
            return db.patient
        bindings=dict(ControllerCommand=ControllerCommand,Request=object,body=body,store=NS(transaction=lambda **kw:nullcontext(db)),
            session=lambda *args,**kw:dict(account_id=p['owner_id'],token_hash='UNIT-owned-session'),own=own,
            mutation_receipt=mutation,save_mutation=save,transition=original,settings=NS(clock=lambda:AT,fault=None),APIError=APIError)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[route],type_ignores=[])),'actual_withdrawal_route','exec'),bindings)
        def invoke(key='UNIT-withdraw-once'):
            coroutine=bindings['support_command'](p['id'],NS(headers={'idempotency-key':key}))
            try:coroutine.send(None)
            except StopIteration as done:return done.value
            raise AssertionError('No actual async wait in SOURCE fixture')
        def transition(*args):
            if args[4].action!='withdraw':return original(*args)
            pending.append(args[4]);first=invoke();count=len(db.tasks)
            self.assertEqual(invoke(),first);self.assertEqual(len(db.tasks),count)
            with self.assertRaisesRegex(Exception,'stale_support'):invoke('UNIT-stale-new-key')
            self.assertEqual(len(db.tasks),count);responses.append(first);return first
        h['transition']=transition
        run();self.assertEqual(len(db.tasks),1);self.assertEqual(len(db.receipts),1)
        row=next(iter(db.tasks.values()));payload=json.loads(row['payload'])
        self.assertEqual((row['patient_id'],row['owner_id']),(p['id'],p['owner_id']))
        self.assertEqual(payload['owner_id'],p['owner_id']);self.assertEqual(payload['status'],'pending')
        self.assertEqual(payload['trigger'],'support_consent_withdrawal');self.assertEqual(row['bundle_id'],payload['command_id'])
        self.assertEqual(responses[0]['task_id'],row['id']);self.assertIn(payload['decision_id'],db.decisions)
        command=json.loads(db.proofs[payload['command_id']]['payload']);self.assertEqual(command['command']['action'],'withdraw')
        withdrawn=next(r for r in db.records if r.kind=='consent' and r.consent_status=='withdrawn')
        self.assertEqual(payload['consent_ref'],exact_ref(withdrawn).model_dump())
        self.assertEqual(payload['candidate_invocation'],inv.reference)
        reader=function('services/foundation/app.py','task',Request=object,app=NS(get=lambda path:lambda fn:fn),
            store=NS(transaction=lambda **kw:nullcontext(db)),session=lambda *args:dict(account_id=p['owner_id']),APIError=APIError,json=json)
        self.assertEqual(reader(row['id'],object()),payload)
        reader.__globals__['session']=lambda *args:dict(account_id='UNIT-other-owner')
        with self.assertRaises(APIError) as denied:reader(row['id'],object())
        self.assertEqual(denied.exception.code,'not_found')
        self.assertEqual(len(db.execute('SELECT * FROM tasks WHERE patient_id=?',(p['id'],)).fetchall()),1)

    def test_withdrawal_task_fault_rolls_back_consent_command_versions_and_clock(self):
        code,db,p,state,a,h,inv,go,receipt,run,flow=self.preparation(later_consent_action='withdraw')
        before=copy.deepcopy((db.records,db.proofs,db.patient,db.tasks,db.decisions,db.receipts))
        def fault(point):
            if point=='after_follow_up':
                self.assertEqual(len(db.tasks),1)
                self.assertTrue(any(r.kind=='consent' and r.consent_status=='withdrawn' for r in db.records))
                raise RuntimeError('UNIT withdrawal task fault')
        with self.assertRaisesRegex(RuntimeError,'withdrawal task fault'):run(NS(clock=lambda:AT,fault=fault))
        self.assertEqual((db.records,db.proofs,db.patient,db.tasks,db.decisions,db.receipts),before)
        self.assertFalse(getattr(db,'committed',False));self.assertTrue(receipt.getvalue())
        with self.assertRaises(FileExistsError):run()


class DispatchAuthorityTests(unittest.TestCase):
    def preparation(self,expires=None,prompt=True):
        original=consent
        def expiring(*args,**kwargs):
            value=original(*args,**kwargs).model_dump(mode='json')
            value['expires_at']=expires.isoformat() if expires else None
            return typed(value)
        with patch(__name__+'.consent',expiring):code,db,p,state=fixture(actual_mask=True)
        code['keyed_uniform']=lambda seed:0. if prompt else 1.
        decision,assignment=code['decide'](db,NS(fault=None),p,state,AT)
        return code,db,p,state,decision,assignment

    def test_dispatch_expiry_between_equal_after_and_valid_prompt_noprompt(self):
        for expiry,cancel in ((AT+timedelta(hours=4),True),(AT+timedelta(hours=8),True),
                              (AT+timedelta(hours=8,microseconds=1),False),(None,False)):
            for prompt in (True,False):
                code,db,p,state,decision,assignment=self.preparation(expiry,prompt)
                frozen=(decision.model_dump_json(),assignment.model_dump_json())
                offered,canceled=code['dispatch'](db,NS(fault=None),p,state,decision,assignment,AT)
                with self.subTest(expiry=expiry,prompt=prompt):
                    self.assertEqual(canceled,cancel)
                    self.assertEqual((decision.model_dump_json(),assignment.model_dump_json()),frozen)
                    self.assertEqual(offered is not None,prompt and not cancel)
                    self.assertEqual(any(s['assignment_id']==assignment.record_id for s in state['simulation']['support']),not cancel)
                    if offered:self.assertTrue(next(r for r in db.records if r.kind=='consent').permits('mrt_bandit',offered.event_at))

    def test_dispatch_current_withdrawal_hold_N_and_pause_cancel_frozen_prompt(self):
        for change in ('withdrawal','hold','N','pause','independent_hold'):
            code,db,p,state,decision,assignment=self.preparation()
            frozen=(decision.model_dump_json(),assignment.model_dump_json())
            if change=='withdrawal':
                previous=next(r for r in db.records if r.kind=='consent');at=AT+timedelta(hours=5)
                value=previous.model_dump(mode='json')
                value.update(record_id='UNIT-later-withdrawal',lineage_id='UNIT-later-withdrawal',revision=1,supersedes=None,
                    event_at=at.isoformat(),recorded_at=at.isoformat(),available_at=at.isoformat(),effective_at=at.isoformat(),
                    withdrawn_at=at.isoformat(),consent_status='withdrawn',oversight_status='withdrawn')
                db.records.append(typed(value))
            elif change=='hold':state['workflow']['hold_reasons']=['UNIT newly effective hold']
            elif change=='N':state['simulation']['nof1']=dict(status='active')
            elif change=='pause':state['workflow']['support_mode']='paused'
            else:code['active_episodes']=lambda *args:[dict(id='UNIT new independent hold')]
            offered,canceled=code['dispatch'](db,NS(fault=None),p,state,decision,assignment,AT)
            with self.subTest(change=change):
                self.assertIsNone(offered);self.assertTrue(canceled)
                self.assertEqual((decision.model_dump_json(),assignment.model_dump_json()),frozen)

    def test_dispatch_does_not_count_its_own_pending_assignment_in_burden(self):
        code,db,p,state=fixture(actual_mask=True)
        for days in (2,4):
            db.records.append(typed(dict(**header('UNIT-prior-prompt-'+str(days),p['id'],AT-timedelta(days=days)+timedelta(hours=8)),
                kind='delivery',assignment_id='UNIT-prior-assignment-'+str(days),option='support_prompt',stage='delivered',
                adherence=1.,rescue=False,protocol_deviations=[])))
        code['keyed_uniform']=lambda seed:0.
        decision,assignment=code['decide'](db,NS(fault=None),p,state,AT)
        self.assertEqual(code['mask'](history(db.records),state,AT+timedelta(hours=8),AT)[0],('no_prompt',))
        offered,canceled=code['dispatch'](db,NS(fault=None),p,state,decision,assignment,AT)
        self.assertFalse(canceled);self.assertIsNotNone(offered)

    def test_canceled_expired_assignment_never_closes_observed_offer_delivery_burden(self):
        code,db,p,state,decision,assignment=self.preparation(AT+timedelta(hours=4))
        offered,canceled=code['dispatch'](db,NS(fault=None),p,state,decision,assignment,AT)
        value=dict(**(header('UNIT-after-cancel-report',p['id'],AT+timedelta(days=1,minutes=-1))|dict(schema_version='2.0.0')),
            kind='daily_report',sleep_quality=7.,function=6.,adverse_symptoms=[],diary_sleep_minutes=420.,goals=[],burden=None,missingness='observed')
        value['source'].update(id='poc-longitudinal-v2',version='2.0.0',adapter='patient_report');db.records.append(typed(value))
        link=code['UNIT_authority']['close_stages'](db,NS(fault=None,clock=lambda:AT),p,decision,assignment,offered,AT,canceled=canceled)
        self.assertTrue(canceled);self.assertEqual(link.reward.status,'pending')
        self.assertTrue(all(b.status=='pending' and b.value is None for b in link.burden))
        self.assertFalse(any(r.kind=='support_stage_closure' or r.kind=='delivery' and r.assignment_id==assignment.record_id for r in db.records))

    def test_consent_revision_refuses_chronology_and_component_substitution_before_write(self):
        for change in ('future_availability','wrong_component'):
            code,db,p,state=fixture(actual_mask=True)
            value=consent().model_dump(mode='json')
            value.update(record_id='UNIT-stable-head',lineage_id='support-consent-'+p['id'])
            if change=='future_availability':
                value.update(recorded_at=(AT+timedelta(days=1)).isoformat(),available_at=(AT+timedelta(days=1)).isoformat())
            else:value['component']='nof1'
            db.records.append(typed(value))
            data=ControllerCommand.model_validate(dict(schema_version='s2-controller-source-1.0.0',mode='current',action='consent',
                decision_id=p['current_decision'],expected_version=1,expected_state_version=1,expected_consent_version=1,
                expected_eligibility_version=1,rationale='UNIT real command rejection'))
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'chronology_regression|same_patient_component'):
                code['transition'](db,NS(fault=None),p,p['owner_id'],data,AT)
            self.assertFalse(db.writes)


class ProtectedInverseTests(unittest.TestCase):
    """Compare public Git baseline ASTs; no service/app modules are imported."""
    def trees(self,module):
        return (ast.parse((ROOT/f'artifacts/s2-controller/source/base-{module}.py').read_text()),
                ast.parse((ROOT/f'services/foundation/{module}.py').read_text()))
    def dump(self,node):return ast.dump(node,include_attributes=False)
    def functions(self,tree):
        result={}
        def visit(node,prefix=''):
            for item in getattr(node,'body',[]):
                if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                    key=prefix+item.name
                    if not isinstance(item,ast.ClassDef):result[key]=item
                    visit(item,key+'.')
        visit(tree);return result
    def test_all_undeclared_existing_function_bodies_are_identical(self):
        allowed=dict(app={'create_app','create_app.panel_options','create_app.owned_analysis_view'},
            store={'Store.__init__','Store.connect','Store.transaction'},workflow={'history','current_safety','create_decision'},
            simulation={'persist_product','advance','assign'},protocol={'validate_support_v21','project_protocol','project_protocol.reduce','export_histories'},
            support_s2_prediction={'current_sources'})
        count=0
        for module,changed in allowed.items():
            old,new=map(self.functions,self.trees(module))
            self.assertTrue(old.keys()<=new.keys())
            for name,node in old.items():
                if name not in changed:
                    with self.subTest(module=module,function=name):self.assertEqual(self.dump(node),self.dump(new[name]))
                    count+=1
        self.assertGreater(count,75)
    def test_simulation_inverse_keeps_ordinary_N_and_product_laws(self):
        old,new=map(self.functions,self.trees('simulation'))
        for name in ('advance','assign'):
            node=copy.deepcopy(new[name]);node.body=[n for n in node.body if not (isinstance(n,ast.If) and "'support'" in ast.unparse(n.test))]
            self.assertEqual(self.dump(old[name]),self.dump(node))
        node=copy.deepcopy(new['persist_product'])
        node.body[1]=ast.ImportFrom(module='workflow',names=[ast.alias(name='history')],level=1)
        self.assertEqual(self.dump(old['persist_product']),self.dump(node))
    def test_store_default_transaction_and_connect_inverse(self):
        old,new=map(self.functions,self.trees('store'))
        for name in ('Store.connect','Store.transaction'):
            node=copy.deepcopy(new[name]);node.args.kwonlyargs=[] if name.endswith('connect') else node.args.kwonlyargs[:-1]
            node.args.kw_defaults=[] if name.endswith('connect') else node.args.kw_defaults[:-1]
            if name.endswith('connect'):node.body=node.body[0].orelse[0].body+node.body[1:]
            else:
                assignment=node.body[0].body[0];self.assertIsInstance(assignment.value,ast.IfExp);assignment.value=assignment.value.body
            self.assertEqual(self.dump(old[name]),self.dump(node))
    def test_shared_ordinary_support_validator_inverse(self):
        old,new=map(self.functions,self.trees('protocol'))
        node=copy.deepcopy(new['_validate_support_v21']);node.name='validate_support_v21'
        node.body=node.body[2:];node.args.kwonlyargs=[];node.args.kw_defaults=[]
        self.assertEqual(self.dump(old['validate_support_v21']),self.dump(node))
    def test_legacy_histories_keep_exact_typed_outputs(self):
        code,db,p,state=fixture();a=code['UNIT_authority']
        records=[r for r in db.records if r.schema_version=='1.0.0']
        db.proofs={str(i):dict(patient_id=p['id'],actor_id=p['owner_id'],payload=canonical(value))
            for i,value in enumerate(({},[],dict(qualification=None),dict(qualification='ordinary legacy metadata')))}
        for rows in ([],records):
            db.records=rows
            digest=lambda x:hashlib.sha256(x.encode()).hexdigest()
            old=load('artifacts/s2-controller/source/base-workflow.py',canonical=canonical,digest=digest)
            new=load('services/foundation/workflow.py',canonical=canonical,digest=digest,validate_live_history=a['validate_live_history'])
            self.assertEqual(old['history'](db,p['id']).model_dump(),new['history'](db,p['id']).model_dump())
