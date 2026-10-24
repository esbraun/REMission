"""LABELED INERT public SOURCE fixtures, never a real fit, artifact or receipt.

Actual contracts/features/workflow snapshot constructor/adapter functions run;
only Store/history I/O and declared science API boundaries are inert doubles.
"""
import ast
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contracts.domain.analysis import canonical,sha,reference
from contracts.domain.entities import DecisionSnapshot
from contracts.domain.protocol_analysis import ReducedRef,Consent
from contracts.domain.support_s2_saved import *
from methods.support.s2_data import features,predecision_features
from test_s2_native_source import product,fake_result,functions
from test_s2_app_source import InertDB,Cursor,CURRENT,ORIGIN
from s2_model_fixtures import history

ROOT=Path(__file__).resolve().parents[1]
FOUNDATION='services/foundation/support_s2_prediction.py'
WORKER='services/learner/support_s2_predict_worker.py'


def namespace(path):
    ns=dict(__name__='inert_actual_source',__package__='services.foundation')
    exec(compile(ast.parse((ROOT/path).read_text(encoding='utf-8')),str(ROOT/path),'exec'),ns)
    return ns


def function_without_imports(path,name,**bindings):
    """Only declared import/I/O seams are replaced; actual function body runs."""
    tree=ast.parse((ROOT/path).read_text(encoding='utf-8'))
    fn=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name))
    fn.body=[n for n in fn.body if not isinstance(n,(ast.ImportFrom,ast.Import))]
    ns=dict(bindings);ns['__name__']='inert_actual_function'
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(ROOT/path),'exec'),ns)
    return ns[name]


def qualified_api_function(path,name,**bindings):
    """Actual role body with scientific/relative import statements replaced by
    named inert API bindings; never imports or performs scientific computation.
    """
    tree=ast.parse((ROOT/path).read_text())
    fn=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name))
    class Strip(ast.NodeTransformer):
        def visit_Import(self,node):return None
        def visit_ImportFrom(self,node):return None
    fn=Strip().visit(fn);ns=dict(bindings)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(ROOT/path),'exec'),ns)
    return ns[name]


class PredictionDB(InertDB):
    def __init__(self,ctx):
        super().__init__();self.decisions={ctx.decision.record_id:dict(snapshot=ctx.decision.model_dump_json())}
        p=self.patients[ctx.decision.patient_id];state=json.loads(p['state_json']);state['workflow']=ctx.decision.workflow.model_dump(mode='json')
        p.update(version=ctx.decision.patient_version,state_version=ctx.decision.state_version,consent_version=ctx.decision.consent_version,
            eligibility_version=ctx.decision.eligibility_version,current_decision=ctx.decision.record_id,cutoff=ctx.decision.cutoff.isoformat(),state_json=canonical(state))
    def execute(self,sql,args=()):
        if sql=='SELECT * FROM decisions WHERE id=? AND patient_id=?':
            row=self.decisions.get(args[0]);return Cursor([row] if row and json.loads(row['snapshot'])['patient_id']==args[1] else [])
        if "json_extract(request_json,'$.kind')='poc_support_s2_saved_prediction_input'" in sql:
            return Cursor([r for r in self.attempts if r['owner_id']==args[0] and json.loads(r['request_json'])['kind']=='poc_support_s2_saved_prediction_input'])
        return super().execute(sql,args)


def saved_fit():
    p=product();r,trusted=fake_result(p)
    collection=dict(schema='s2-native-owned-collection-v1',attempt_id=p.attempt_id,input_sha256=sha(p.model_dump(mode='json')),
        claim_sha256=trusted['claim_sha256'],terminal='reaped_exit_0_no_oom_no_restart',
        files=[r.semantics.artifact.model_dump(mode='json')],result_sha256=sha(r.model_dump(mode='json')))
    return SavedFit.model_validate_json(canonical(dict(product=p.model_dump(mode='json'),result=r.model_dump(mode='json'),
        launch=trusted,collection=collection,collection_reference=reference('poc-support-s2-saved-fit-collection-v1',collection))))


def snapshot(h,**workflow):
    """Execute the actual workflow.create_decision snapshot constructor AST."""
    tree=ast.parse((ROOT/'services/foundation/workflow.py').read_text(encoding='utf-8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='create_decision')
    node=next(n for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='snapshot' for t in n.targets))
    state=dict(workflow=next(r.workflow.model_dump(mode='json') for r in h.records if r.kind=='decision_snapshot'))
    state['workflow'].update(workflow)
    def header(identifier,patient,at):
        return dict(schema_version='1.0.0',synthetic=True,record_id=identifier,patient_id=patient,
            event_at=at.isoformat(),recorded_at=at.isoformat(),available_at=at.isoformat(),
            source=dict(id='UNIT-actual-constructor',version='1.0.0',adapter='research_configuration',raw_sha256='0'*64),
            lineage_id=identifier,revision=1,supersedes=None,duplicate_of=None,record_status='active')
    ns=dict(DecisionSnapshot=DecisionSnapshot,canonical=canonical,record_header=header,identifier='UNIT-current-'+str((h.cutoff-h.origin).days),
        patient_id=h.patient_id,at=h.cutoff,timestamp=lambda x:x.isoformat(),row=dict(version=15,state_version=2,consent_version=3,eligibility_version=4),
        state=state,eligibility=[dict(action='behavioral_continue',status='eligible',reasons=[])],
        reference=lambda name,value='foundation-v1':dict(id=name,version='1.0.0',sha256=hashlib.sha256(value.encode()).hexdigest()),
        SUPPORT=reference('UNIT-fixed','unchanged foundation snapshot metadata'))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'actual_workflow_snapshot_constructor','exec'),ns)
    return ns['snapshot']


def context(fit,day=14,**workflow):
    h=history('UNIT-S2-07',day);d=snapshot(h,**workflow)
    refs=tuple(ReducedRef.model_validate(dict(record_id=r.record_id,projection_sha256=sha(r.model_dump(mode='json')))) for r in sorted(h.records,key=lambda r:r.record_id))
    activation=next(r for r in h.records if r.kind=='protocol_snapshot')
    ar=ReducedRef.model_validate(dict(record_id=activation.record_id,projection_sha256=sha(activation.model_dump(mode='json'))))
    consents=tuple(r for r in h.records if r.kind=='consent')
    x,_=prospective_features(h,refs);mask,reason=current_mask(d,h,consents,ar,activation.approval_refs[0],refs)
    body=ContextBody.model_validate_json(canonical(dict(schema_version='s2-saved-context-v1',owner_id='UNIT-owner',store_id='UNIT-store',
        authority_generation=1,generation_id='UNIT-generation',decision=d.model_dump(mode='json'),projection=h.model_dump(mode='json'),
        current_consents=[c.model_dump(mode='json') for c in consents],activation_ref=ar.model_dump(),approval_ref=activation.approval_refs[0].model_dump(),
        feature_refs=[r.model_dump() for r in refs],x_current=x,allowed_actions=mask,mask_reason=reason)))
    value=body.model_dump(mode='json')
    return CurrentContext.model_validate_json(canonical(dict(value,reference=reference('poc-support-s2-current-context-v1',value))))


def request(fit,ctx):
    return SavedPredictionInput.model_validate_json(canonical(dict(schema_version='s2-saved-prediction-source-1.0.0',
        kind='poc_support_s2_saved_prediction_input',purpose='EST-POLICY:poc-support-prediction-v1',attempt_id='UNIT-prediction-1',
        fit=fit.model_dump(mode='json'),context=ctx.model_dump(mode='json'),request=make_request(fit,ctx).model_dump(mode='json'),configuration=CONFIG_REF,executable=False)))


def data_inverse():
    source=(ROOT/'methods/support/s2_data.py').read_text(encoding='utf-8')
    delta='''def features(history,decision,active):
    return predecision_features(history,cutoff=decision.cutoff,context=decision.context,
        context_projection_sha256=decision.context_projection_sha256,active=active)


def predecision_features(history,*,cutoff,context,context_projection_sha256,active):
    at=cutoff;refs=context;context=[r.record_id for r in refs]
    require(len(context)==len(set(context)) and context_projection_sha256==sha([r.model_dump(mode='json') for r in refs]),'''
    original='''def features(history,decision,active):
    at=decision.cutoff;context=[r.record_id for r in decision.context]
    require(len(context)==len(set(context)) and decision.context_projection_sha256==sha([r.model_dump(mode='json') for r in decision.context]),'''
    assert source.count(delta)==1
    inverse=source.replace(delta,original)
    assert inverse.count('for ref in refs:')==1
    return inverse.replace('for ref in refs:','for ref in decision.context:')


def prediction_result(p,status='failed',reason='worker_refused',candidate=None):
    launch=dict(schema_version='s2-saved-prediction-launch-v1',attempt_id=p.attempt_id,input_sha256=sha(p.model_dump(mode='json')),
        configuration=CONFIG_REF,source_commit='6'*40,learner_image='sha256:'+'7'*64,installed_closure_sha256='8'*64,claim_sha256='9'*64)
    value=dict(schema_version='s2-saved-prediction-source-1.0.0',kind='poc_support_s2_saved_prediction_result',attempt_id=p.attempt_id,
        input_sha256=launch['input_sha256'],context_reference=p.context.reference.model_dump(),fit_collection_reference=p.fit.collection_reference.model_dump(),
        configuration=CONFIG_REF,launch=launch,binary=None if candidate is None else p.fit.result.semantics.model_dump(mode='json'),candidate=candidate,
        status=status,reason=reason,probability=.5 if candidate is None else candidate['probability'],serving_authority=False)
    return SavedPredictionResult.model_validate_json(canonical(value)),launch


class SavedChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fit=saved_fit();cls.ctx=context(cls.fit);cls.p=request(cls.fit,cls.ctx)
    def test_actual_snapshot_constructor_and_deterministic_contract(self):
        self.assertEqual(self.ctx.decision.eligibility[0].action,'behavioral_continue')
        self.assertNotIn('support_prompt',[e.action for e in self.ctx.decision.eligibility])
        activation=next(r for r in self.ctx.projection.records if r.kind=='protocol_snapshot')
        self.assertIn(self.ctx.approval_ref,activation.approval_refs)
        self.assertEqual(self.p.request.members[7].missing,self.fit.product.initial.export.counts[7].missing)
        self.assertFalse(self.p.executable);self.assertFalse(CONFIG['serving_authority'])
        self.assertEqual(CONFIG['seed'],'none: deterministic inference, no RNG')
        self.assertEqual(SavedPredictionInput.model_validate_json(self.p.model_dump_json()),self.p)
    def test_pure_predecision_features_matches_actual_old_wrapper_all_members_and_cutoffs(self):
        old=dict(__name__='inert_original_feature_module')
        # The WHOLE inverse is independently pinned to accepted base below;
        # compare the actual original body, not a hand-mirrored formula.
        exec(compile(data_inverse(),'accepted_original_s2_data','exec'),old)
        for day in (14,28):
            for i in range(12):
                h=history(f'UNIT-S2-{i:02}',day);active={r.record_id:r for r in h.records}
                for d in (r for r in h.records if r.kind=='support_decision'):
                    self.assertEqual(old['features'](h,d,active),predecision_features(h,cutoff=d.cutoff,context=d.context,
                        context_projection_sha256=d.context_projection_sha256,active=active))
    def test_pure_feature_exact_cutoff_and_context_hash_negatives(self):
        h=self.ctx.projection;refs=self.ctx.feature_refs;active={r.record_id:r for r in h.records}
        kw=dict(cutoff=h.cutoff,context=refs,context_projection_sha256=sha([r.model_dump(mode='json') for r in refs]),active=active)
        with self.assertRaisesRegex(ValueError,'changed original'):predecision_features(h,**dict(kw,context_projection_sha256='0'*64))
        key=refs[0].record_id;active[key]=active[key].model_copy(update=dict(available_at=h.cutoff))
        with self.assertRaisesRegex(ValueError,'postdecision'):predecision_features(h,**kw)
    def test_current_context_exact_ref_hash_and_feature_values(self):
        for mutate in (lambda d:d['x_current'].__setitem__(0,1.),lambda d:d['feature_refs'].pop(),
                lambda d:d['reference'].update(sha256='0'*64),lambda d:d['decision'].update(cutoff=(ORIGIN+timedelta(days=15)).isoformat())):
            value=self.ctx.model_dump(mode='json');mutate(value)
            with self.assertRaises(ValueError):CurrentContext.model_validate_json(canonical(value))
    def test_current_consent_at_cutoff_withdrawal_overrides_historical_active(self):
        c=self.ctx.current_consents[0].model_dump(mode='json');c.update(record_id='UNIT-withdrawal',lineage_id='UNIT-withdrawal',
            available_at=self.ctx.decision.cutoff.isoformat(),recorded_at=self.ctx.decision.cutoff.isoformat(),
            event_at=self.ctx.decision.cutoff.isoformat(),consent_status='withdrawn')
        withdrawn=Consent.model_validate_json(canonical(c))
        mask,reason=current_mask(self.ctx.decision,self.ctx.projection,(*self.ctx.current_consents,withdrawn),self.ctx.activation_ref,self.ctx.approval_ref,self.ctx.feature_refs)
        self.assertEqual(mask,());self.assertEqual(reason,'current_support_unavailable')
        future=withdrawn.model_copy(update=dict(available_at=self.ctx.decision.cutoff+timedelta(microseconds=1)))
        with self.assertRaisesRegex(ValueError,'consent_projection'):current_mask(self.ctx.decision,self.ctx.projection,(future,),self.ctx.activation_ref,self.ctx.approval_ref,self.ctx.feature_refs)
    def test_holds_readiness_pause_and_N_freeze_current_mask(self):
        for wf,mask in ((dict(clinical='clinical_hold',hold_reasons=['UNIT-hold']),()),(dict(data_readiness='stale'),()),
                (dict(support_mode='paused'),()),(dict(support_mode='frozen',learning='nof1_block'),('no_prompt',))):
            self.assertEqual(context(self.fit,**wf).allowed_actions,mask)
    def test_burden_current_mask_from_deliveries_not_fitted_counts(self):
        self.assertEqual(context(self.fit,day=15).mask_reason,'current_burden_constraint')
        self.assertEqual(self.p.request.members[7].observed,(0,0))
    def test_foreign_owner_store_authority_target_and_seed_purpose_refused(self):
        for mutate in (lambda d:d['context'].update(owner_id='UNIT-foreign'),lambda d:d['context'].update(store_id='UNIT-foreign'),
                lambda d:d.update(purpose='fit'),lambda d:d.update(seed=1),lambda d:d['request'].update(target_id='UNIT-foreign')):
            v=self.p.model_dump(mode='json');mutate(v)
            with self.assertRaises(ValueError):SavedPredictionInput.model_validate_json(canonical(v))
    def test_day14_serves_through27_expiry_before28_and_no_late_revival(self):
        p=request(self.fit,context(self.fit,day=27));self.assertEqual(p.request.h,14)
        with self.assertRaises(ValueError):request(self.fit,context(self.fit,day=28))
        r,t=prediction_result(self.p)
        validate_saved_result(r,self.p,t,at=ORIGIN+timedelta(days=27,hours=23))
        with self.assertRaisesRegex(ValueError,'original_expiry'):validate_saved_result(r,self.p,t,at=ORIGIN+timedelta(days=28))
    def test_saved_fit_requires_complete_external_collection_identity(self):
        for mutate in (lambda d:d['collection']['files'][0].update(sha256='0'*64),lambda d:d['launch'].update(claim_sha256='0'*64),
                lambda d:d['collection'].update(terminal='running'),lambda d:d['result']['ownership'].update(owner_id='UNIT-foreign')):
            d=self.fit.model_dump(mode='json');mutate(d)
            with self.assertRaises(ValueError):SavedFit.model_validate_json(canonical(d))
    def test_saved_result_finite_status_identity_and_no_ready_promotion(self):
        r,t=prediction_result(self.p);validate_saved_result(r,self.p,t,at=self.ctx.decision.cutoff)
        for mutate in (lambda d:d.update(probability=.7),lambda d:d.update(status='candidate_ready'),
                lambda d:d.update(binary=dict(self.fit.result.semantics.model_dump(mode='json'),artifact=dict(self.fit.result.semantics.artifact.model_dump(mode='json'),sha256='0'*64))),lambda d:d['launch'].update(claim_sha256='0'*64)):
            d=r.model_dump(mode='json');mutate(d)
            with self.assertRaises(ValueError):validate_saved_result(SavedPredictionResult.model_validate_json(canonical(d)),self.p,t,at=self.ctx.decision.cutoff)
    def test_scalar_precision_all_thresholds_and_no_relaxation(self):
        from contracts.domain.support_s2 import precision_status
        good=(.7,.7,False,1.,500.,500.,.01)
        self.assertEqual(precision_status(*good),'candidate_ready')
        for i,value in ((0,.52),(1,.73),(2,True),(3,1.01),(4,399.),(5,399.),(6,0.),(6,.021)):
            bad=list(good);bad[i]=value;self.assertNotEqual(precision_status(*bad),'candidate_ready')
    def test_worker_gate_precedes_all_stat_and_scientific_calls(self):
        worker=namespace(WORKER)
        class Bomb:
            def __getattr__(self,name):raise AssertionError('private path touched before gate')
        with self.assertRaisesRegex(ValueError,'unqualified'):worker['run'](Bomb(),Bomb(),Bomb())
    def test_budget_absolute_monotonic_segment_and_no_reset(self):
        worker=namespace(WORKER);wall=[100.];mono=[10.]
        b=worker['Budget'](90.,clock=lambda:wall[0],monotonic=lambda:mono[0]);b.segment()
        with self.assertRaisesRegex(ValueError,'cannot_reset'):b.segment()
        mono[0]=310.
        with self.assertRaisesRegex(TimeoutError,'segment'):b.check()
        b=worker['Budget'](90.,clock=lambda:wall[0],monotonic=lambda:mono[0]);wall[0]=660.
        with self.assertRaisesRegex(TimeoutError,'absolute'):b.check()
    def test_reference_wrapper_observes_veto_and_restores_exact_functions(self):
        worker=namespace(WORKER);calls=[]
        fn=lambda *args: calls.append('numeric') or 'same-result'
        module=SimpleNamespace(expected_quality=fn,indicator_diagnostics=fn)
        module.predict=lambda *args:module.expected_quality()
        self.assertEqual(worker['reference_predict'](module,None,None,None,check=lambda:calls.append('check')),'same-result')
        self.assertIs(module.expected_quality,fn);self.assertEqual(calls,['check','check','numeric','check','check'])
        def veto():raise TimeoutError('parent stage veto')
        with self.assertRaises(TimeoutError):worker['reference_predict'](module,None,None,None,check=veto)
        self.assertIs(module.expected_quality,fn)
    def test_explicit_dispatch_unknown_refusal_and_no_fitting_rng_in_predict_worker(self):
        ns=functions('tooling/foundation/analysis_dispatcher.py','worker_module')
        self.assertEqual(ns['worker_module']({'kind':self.p.kind}),'services.learner.support_s2_predict_worker')
        with self.assertRaises(ValueError):ns['worker_module']({'kind':'poc_support_s2_unknown'})
        source=(ROOT/WORKER).read_text();self.assertNotIn('pm.sample',source);self.assertNotIn('randbelow',source)
        self.assertNotIn('s2_fit import',source);self.assertNotIn('s2_model import',source)
    def test_foundation_gates_before_Store_or_entropy_and_read_summary_is_bounded(self):
        ns=namespace(FOUNDATION)
        class Bomb:
            def __getattr__(self,name):raise AssertionError('Store touched before gate')
        with self.assertRaisesRegex(ValueError,'unqualified'):ns['enqueue'](Bomb(),{},None,None,None,now=None)
        with self.assertRaisesRegex(ValueError,'unqualified'):ns['ingest_saved'](Bomb(),None,None,Bomb(),Bomb())
        self.assertFalse(ns['read_summary'](Bomb(),None,None,current_context=None,current_fit=None,at=None)['summary_available'])
    def test_foundation_static_eager_imports_are_scalar_only(self):
        tree=ast.parse((ROOT/FOUNDATION).read_text())
        for n in tree.body:
            if isinstance(n,ast.ImportFrom):self.assertTrue(n.module.startswith(('contracts.','datetime')))
            elif isinstance(n,ast.Import):self.assertTrue(all(a.name in ('json','uuid') for a in n.names))
    def test_actual_prospective_adapter_uses_current_saved_row_versions_and_explicit_approval(self):
        ns=namespace(FOUNDATION);db=PredictionDB(self.ctx)
        def current_sources(db,target,cutoff,origin,closure):
            self.assertEqual((target,cutoff,origin),('UNIT-S2-07',self.ctx.decision.cutoff,ORIGIN))
            return self.ctx.projection,self.ctx.current_consents
        fn=function_without_imports(FOUNDATION,'current_context',**dict(ns,store_identity=lambda db:('UNIT-store',1),
            instant=lambda s:datetime.fromisoformat(s),current_sources=current_sources))
        result=fn(db,'UNIT-owner','UNIT-S2-07',self.fit)
        self.assertEqual(result,self.ctx)
        self.assertFalse(db.writes)
        for field,value in (('state_version',3),('current_decision','UNIT-missing'),('owner_id','UNIT-foreign')):
            broken=PredictionDB(self.ctx);broken.patients['UNIT-S2-07'][field]=value
            with self.assertRaises(ValueError):fn(broken,'UNIT-owner','UNIT-S2-07',self.fit)
        self.assertNotIn('SupportDecision',(ROOT/FOUNDATION).read_text())
    def test_actual_current_source_separates_inclusive_consent_and_strict_projection(self):
        from test_s2_app_source import consent as full_consent
        ns=namespace(FOUNDATION);calls=[];c=full_consent('UNIT-S2-07')
        c=c.model_copy(update=dict(record_id='UNIT-current-withdrawal',lineage_id='UNIT-current-withdrawal',
            event_at=self.ctx.decision.cutoff,recorded_at=self.ctx.decision.cutoff,available_at=self.ctx.decision.cutoff,consent_status='withdrawn'))
        activation=next(r for r in self.ctx.projection.records if r.kind=='protocol_snapshot')
        full=SimpleNamespace(records=[c],as_known_at=lambda at:[activation])
        def project(full,cutoff,**kw):
            calls.append(kw);return self.ctx.projection
        fn=function_without_imports(FOUNDATION,'current_sources',**dict(ns,history=lambda db,p:full,
            project_protocol=project,validate_snapshot=lambda *args:calls.append('validated-actual-snapshot')))
        projection,consents=fn(None,'UNIT-S2-07',self.ctx.decision.cutoff,ORIGIN,None)
        self.assertEqual(consents[0].consent_status,'withdrawn');self.assertIs(projection,self.ctx.projection)
        self.assertEqual(calls[0],'validated-actual-snapshot');self.assertIsNone(calls[1]['verify_closure'])
        self.assertTrue(all(r.available_at<projection.cutoff for r in projection.records))
    def test_real_projection_closure_refuses_missing_trusted_ledger(self):
        tree=ast.parse((ROOT/'services/foundation/protocol.py').read_text())
        project=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='project_protocol')
        closure=next(n for n in project.body if isinstance(n,ast.FunctionDef) and n.name=='closure')
        ns=dict(verify_closure=None,cutoff=self.ctx.decision.cutoff)
        exec(compile(ast.Module(body=[closure],type_ignores=[]),'actual_projection_closure','exec'),ns)
        with self.assertRaisesRegex(ValueError,'verified_stage_ledger'):ns['closure']('UNIT-inert-closure')
    def test_actual_background_receipt_queue_idempotency_conflicts_and_unknown(self):
        ns=namespace(FOUNDATION);db=PredictionDB(self.ctx)
        ns['uuid']=SimpleNamespace(uuid4=lambda:SimpleNamespace(hex='a'*32))
        old=namespace('services/foundation/support_s2_analysis.py')
        fn=function_without_imports(FOUNDATION,'_enqueue',**dict(ns,receipt_rows=old['receipt_rows'],timestamp=old['timestamp']))
        first=fn(db,CURRENT,'UNIT-prediction-receipt',self.fit,self.ctx,now=self.ctx.decision.cutoff)
        self.assertEqual(first,fn(db,CURRENT,'UNIT-prediction-receipt',self.fit,self.ctx,now=self.ctx.decision.cutoff))
        self.assertEqual(db.writes,['pending','attempt','receipt'])
        with self.assertRaisesRegex(ValueError,'reconcile_original'):fn(db,CURRENT,'UNIT-different-key',self.fit,self.ctx,now=self.ctx.decision.cutoff)
        other_ctx=context(self.fit,day=15)
        with self.assertRaisesRegex(ValueError,'already_pending'):fn(db,CURRENT,'UNIT-new-context',self.fit,other_ctx,now=other_ctx.decision.cutoff)
        reconcile=function_without_imports(FOUNDATION,'reconcile',**dict(ns,receipt_rows=old['receipt_rows']))
        self.assertEqual(reconcile(db,'UNIT-owner','UNIT-unknown'),dict(status='unknown',attempt=None))
        self.assertEqual(reconcile(db,'UNIT-owner','UNIT-prediction-receipt')['attempt'],first)
    def test_scalar_collection_current_staleness_and_persisted_summary_only(self):
        ns=namespace(FOUNDATION);r,t=prediction_result(self.p)
        custody=dict(schema='s2-saved-owned-collection-v1',attempt_id=self.p.attempt_id,input_sha256=sha(self.p.model_dump(mode='json')),
            claim_sha256=t['claim_sha256'],terminal='reaped_exit_0_no_oom_no_restart',path='result.json',result_sha256=sha(r.model_dump(mode='json')))
        kwargs=dict(current_context=self.ctx,current_fit=self.fit,custody=custody,at=self.ctx.decision.cutoff)
        self.assertEqual(ns['validate_collection'](r,self.p,t,**kwargs),r)
        with self.assertRaises(ValueError):ns['validate_collection'](r,self.p,t,**dict(kwargs,current_context=context(self.fit,day=15)))
        with self.assertRaises(ValueError):ns['validate_collection'](r,self.p,t,**dict(kwargs,custody=dict(custody,terminal='running')))
        db=PredictionDB(self.ctx);db.attempts=[dict(job_id=self.p.attempt_id,owner_id='UNIT-owner',status='completed',
            input_sha256=sha(self.p.model_dump(mode='json')),request_json=self.p.model_dump_json(),result_json=r.model_dump_json(),progress_json=canonical(dict(trusted_launch=t)))]
        summary=ns['_read_summary'](db,'UNIT-owner',self.p.attempt_id,**kwargs)
        self.assertEqual(summary['probability'],.5);self.assertFalse(summary['summary_available']);self.assertFalse(db.writes)
    def test_actual_loader_checks_complete_semantics_before_any_scientific_read(self):
        artifact='services/learner/support_s2_artifacts.py'
        calls=[]
        fn=function_without_imports(artifact,'load_joint',validate=lambda *args,**kw:calls.append('validate') or self.fit.result.semantics,
            JOINT_ARRAY_CAP=JOINT_ARRAY_CAP)
        wrong=self.fit.result.semantics.model_copy(update=dict(draws=2000))
        with self.assertRaisesRegex(ValueError,'actual_bytes'):fn(None,self.fit.product,wrong,check=lambda:None)
        self.assertEqual(calls,['validate'])
        tree=ast.parse((ROOT/artifact).read_text());load=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='load_joint')
        imports=[(n.lineno,n.names[0].name) for n in ast.walk(load) if isinstance(n,ast.Import)]
        validation=next(n.lineno for n in ast.walk(load) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='validate')
        self.assertTrue(all(line>validation for line,name in imports))
        literals=[n.value for n in ast.walk(load) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
        self.assertTrue({'alpha','tau','e_T','b','rho','s_e','s_Q'}<=set(literals))
    def test_actual_loader_retains_all_seven_api_values_and_original_member_order(self):
        # API declaration doubles only: opaque identity/nbytes markers, no
        # numerical arrays, model or fake scientific computation.
        calls=[];values={n:SimpleNamespace(nbytes=(12 if n in ('alpha','tau','e_T') else 4 if n=='b' else 1)*4*1000*8)
            for n in ('alpha','tau','e_T','b','rho','s_e','s_Q')}
        class Dataset:
            def __enter__(self):calls.append('open');return self
            def __exit__(self,*args):calls.append('close')
            def __getitem__(self,key):calls.append(key);return SimpleNamespace(values=values[key])
        fn=function_without_imports('services/learner/support_s2_artifacts.py','load_joint',
            validate=lambda *args,**kw:calls.append('full-binary-validation') or self.fit.result.semantics,
            JOINT_ARRAY_CAP=JOINT_ARRAY_CAP,np=SimpleNamespace(asarray=lambda value:value),
            xr=SimpleNamespace(open_dataset=lambda *args,**kw:Dataset()),
            file_digest=lambda *args:(self.fit.result.semantics.artifact.sha256,self.fit.result.semantics.artifact.bytes),
            dimension_bound=lambda *args:dict(file_cap=136*1024**2),
            coordinate_labels=lambda p:dict(patient=[m.patient_id for m in p.initial.export.provenance.members]))
        arrays,patients,semantics=fn(Path('INERT-NO-READ'),self.fit.product,self.fit.result.semantics,check=lambda:calls.append('check'))
        self.assertEqual(calls[0],'full-binary-validation');self.assertEqual(set(arrays),set(values))
        self.assertTrue(all(arrays[n] is values[n] for n in values))
        self.assertEqual(patients,[m.patient_id for m in self.fit.product.initial.export.provenance.members])
    def test_ready_requires_primary_and_all_nine_same_direction_nonconstant_precision_cells(self):
        from contracts.domain.support_s2 import CELLS
        precision=dict(probability=.7,rhat=1.,ess_bulk=500.,ess_tail=500.,mcse=.01,half_probability=.7,constant_chain=False,status='candidate_ready')
        candidate=dict(schema_version='s2-prediction-candidate-1.0.0',request_sha256=sha(self.p.request.model_dump(mode='json')),
            target_id=self.p.request.target_id,context_id=self.p.request.context_id,context_version=self.p.request.context_version,
            status='candidate_ready',reason='candidate empirical guards only; no serving authority',primary=precision,
            cells=[dict(delta0=a,delta1=b,precision=copy.deepcopy(precision)) for a,b in CELLS],probability=.7,
            serving_authority=False,empirical_domain_only=True)
        r,t=prediction_result(self.p,'candidate_ready','candidate_evidence_only',candidate)
        validate_saved_result(r,self.p,t,at=self.ctx.decision.cutoff)
        for mutate in (lambda d:d['cells'].pop(),lambda d:d['cells'][8].update(precision=None),
                lambda d:d['cells'][8]['precision'].update(probability=.3,half_probability=.3),
                lambda d:d['cells'][8]['precision'].update(constant_chain=True),
                lambda d:d['cells'][8]['precision'].update(mcse=.021),lambda d:d['primary'].update(ess_tail=399.)):
            c=copy.deepcopy(candidate);mutate(c)
            with self.assertRaises(ValueError):prediction_result(self.p,'candidate_ready','candidate_evidence_only',c)
    def test_whole_changed_modules_inverse_to_accepted_base_only_declared_deltas(self):
        expected={'methods/support/s2_data.py':'8b42e7099601334af2bd159823908b049985eac7f9e6c1e28ad07bf9c0f98505',
            'services/foundation/analysis.py':'00f7587d04cb66f672f7e70ffef680e34d640e3d1674ad3ee5337a4e6d440616',
            'services/learner/support_s2_artifacts.py':'659b8cccfa827b8b455a59a2d78dbaf7a70070929f18b68b618e274172dba241',
            'tooling/foundation/analysis_dispatcher.py':'dc2284fc6ae89fe4923108b79a3c3456954f1f9bb4b5900981a5482fd84f46dc'}
        inverse={'methods/support/s2_data.py':data_inverse()}
        source=(ROOT/'services/foundation/analysis.py').read_text()
        delta="    if json.loads(raw_result).get('kind')=='poc_support_s2_saved_prediction_result':\n        from .support_s2_prediction import ingest_saved\n        return ingest_saved(store,job,token,directory,raw_result,accept_before=accept_before)\n"
        self.assertEqual(source.count(delta),1);inverse['services/foundation/analysis.py']=source.replace(delta,'')
        source=(ROOT/'tooling/foundation/analysis_dispatcher.py').read_text()
        delta="        if kind=='poc_support_s2_saved_prediction_input':return 'services.learner.support_s2_predict_worker'\n"
        self.assertEqual(source.count(delta),1);inverse['tooling/foundation/analysis_dispatcher.py']=source.replace(delta,'')
        source=(ROOT/'services/learner/support_s2_artifacts.py').read_text()
        self.assertEqual(source.count('\n\ndef load_joint('),1)
        inverse['services/learner/support_s2_artifacts.py']=source.split('\n\ndef load_joint(')[0]
        for path,value in inverse.items():
            self.assertEqual(hashlib.sha256(value.encode()).hexdigest(),expected[path],path)
    def test_actual_prepared_worker_retains_precision_failure_and_skips_masked_binary_io(self):
        from contracts.domain.support_s2 import S2Result,CELLS
        worker=namespace(WORKER);stages=[];published=[];loaded=[]
        candidate=S2Result.model_validate_json(canonical(dict(schema_version='s2-prediction-candidate-1.0.0',
            request_sha256=sha(self.p.request.model_dump(mode='json')),target_id=self.p.request.target_id,
            context_id=self.p.request.context_id,context_version=self.p.request.context_version,status='probability_unready',
            reason='primary/cell precision, neutrality or sensitivity reversal',primary=None,
            cells=[dict(delta0=a,delta1=b,precision=None) for a,b in CELLS],probability=.5,
            serving_authority=False,empirical_domain_only=True)))
        _,trusted=prediction_result(self.p)
        algorithm=SimpleNamespace(expected_quality=lambda:None,indicator_diagnostics=lambda:None,
            predict=lambda *args:(candidate,{},{}))
        def load(*args,**kwargs):loaded.append('same joint fixture API');return {},[m.patient_id for m in self.p.request.members],self.fit.result.semantics
        fn=qualified_api_function(WORKER,'_qualified_predict',**dict(worker,canonical=canonical,sha=sha,
            SavedPredictionResult=SavedPredictionResult,PredictionLaunch=PredictionLaunch,CONFIG_REF=CONFIG_REF,RESULT_CAP=RESULT_CAP,
            validate_saved_result=validate_saved_result,load_joint=load,algorithm=algorithm,
            publish=lambda path,value,cap:published.append(value)))
        result=fn(self.p,Path('INERT-NO-BINARY'),Path('INERT-NO-OUTPUT'),budget=worker['Budget'](90.,clock=lambda:100.,monotonic=lambda:10.),
            trusted=trusted,progress=lambda e:stages.append(e['stage']))
        self.assertEqual(result.status,'fallback');self.assertEqual(result.reason,'numerical_or_precision_unready')
        self.assertEqual(len(result.candidate.cells),9);self.assertEqual(len(published),1);self.assertEqual(len(loaded),1)
        self.assertEqual(stages,['preparing','validating_saved_posterior','predicting','summarizing'])
        masked=request(self.fit,context(self.fit,day=15));_,trusted=prediction_result(masked)
        result=fn(masked,Path('INERT-NO-BINARY'),Path('INERT-NO-OUTPUT'),budget=worker['Budget'](90.,clock=lambda:100.,monotonic=lambda:10.),
            trusted=trusted,progress=lambda e:None)
        self.assertEqual(result.reason,'current_mask_not_binary');self.assertEqual(len(loaded),1)
    def test_actual_saved_fit_admission_requires_current_all12_and_external_custody(self):
        ns=namespace(FOUNDATION);old=namespace('services/foundation/support_s2_analysis.py');db=PredictionDB(self.ctx)
        row=dict(job_id=self.fit.product.attempt_id,owner_id='UNIT-owner',patient_id=self.fit.product.initial.export.provenance.target_id,
            status='completed',finished_at='INERT-terminal-time',request_json=self.fit.product.model_dump_json(),
            input_sha256=sha(self.fit.product.model_dump(mode='json')),cohort_json=canonical([m.patient_id for m in self.fit.product.initial.export.provenance.members]),
            history_sha256=self.fit.product.initial.export.provenance.histories_sha256,result_json=self.fit.result.model_dump_json(),
            progress_json=canonical(dict(trusted_launch=self.fit.launch.model_dump(mode='json'))))
        db.attempts=[row];current=[self.fit.product.initial.export]
        fn=function_without_imports(FOUNDATION,'admitted_fit',**dict(ns,export=lambda *args,**kw:current[0],
            store_identity=old['store_identity'],validate_native_collection=old['validate_native_collection']))
        custody=self.fit.collection.model_dump(mode='json',by_alias=True)
        kwargs=dict(file_custody=custody,collection_sha256=sha(custody),selection_key='UNIT-original-selection',source_commit='1'*40)
        self.assertEqual(fn(db,'UNIT-owner',row['job_id'],**kwargs),self.fit)
        with self.assertRaises(ValueError):fn(db,'UNIT-owner',row['job_id'],**dict(kwargs,file_custody=dict(custody,terminal='running')))
        current[0]=current[0].model_copy(update=dict(contribution_sha256='0'*64))
        with self.assertRaisesRegex(ValueError,'asof_authority'):fn(db,'UNIT-owner',row['job_id'],**kwargs)
        current[0]=self.fit.product.initial.export
        row['status']='running'
        with self.assertRaisesRegex(ValueError,'completed_owned'):fn(db,'UNIT-owner',row['job_id'],**kwargs)
    def test_recursive_new_scalar_import_closure_has_no_science(self):
        forbidden={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas','statsmodels'}
        visited=set()
        def visit(path):
            path=Path(path)
            if path in visited or not (ROOT/path).is_file():return
            visited.add(path)
            for node in ast.parse((ROOT/path).read_text()).body:
                if isinstance(node,ast.Import):
                    for alias in node.names:self.assertNotIn(alias.name.split('.')[0],forbidden)
                elif isinstance(node,ast.ImportFrom):
                    self.assertNotIn((node.module or '').split('.')[0],forbidden)
                    target=Path((node.module or '').replace('.','/')+'.py')
                    if node.level:target=path.parent/('../'*(node.level-1))/target
                    if node.module:visit(target)
        for path in ('contracts/domain/support_s2_saved.py',FOUNDATION,'methods/support/s2_data.py'):visit(path)
        self.assertGreaterEqual(len(visited),15)


if __name__=='__main__':unittest.main()
