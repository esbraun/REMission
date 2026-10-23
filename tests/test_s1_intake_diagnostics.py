"""Scalar/AST doubles only: never import the app, Store or archive models."""
import ast
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

ROOT=Path(__file__).resolve().parents[1]
loader=importlib.util.spec_from_file_location('scalar_support_diagnostics',ROOT/'services/foundation/support_diagnostics.py')
diag=importlib.util.module_from_spec(loader);loader.loader.exec_module(diag)
BASELINE=None  # The source-only runner supplies exact accepted Git bytes.
SCHEMA_BASELINE=None
CONTROL_BASELINE=None
canonical=lambda value:json.dumps(value,sort_keys=True).encode()
digest=lambda raw:hashlib.sha256(raw).hexdigest()
WALL=datetime(2026,10,23,tzinfo=timezone.utc)


def functions(raw,names,env):
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'scalar-source-seam','exec'),env)
    return env


def transaction_fixture(raw,*,prior=False,fail=None,callback=None,fault=None):
    log=[];payload=b'public scalar proof';artifact=NS(path='completion',id='artifact',role='observed')
    record=NS(patient_id='PUBLIC-0',record_id='public-record',schema_version='x',kind='scalar',model_dump=lambda **_:dict(value=1))
    trajectory=NS(partition_id='public-partition',completions=artifact)
    index=NS(run_id='public-run',cohort_id='public-cohort',members=('PUBLIC-0',),trajectories=(trajectory,),origin=WALL,horizon=84)
    package=NS(index=index,artifacts={'completion':b'[]','proof':payload},histories={'public-partition':NS(records=(record,))})
    class Rows:
        def __init__(self,one=None,rows=()):self.one=one;self.rows=rows
        def fetchone(self):return self.one
        def __iter__(self):return iter(self.rows)
    class DB:
        def execute(self,sql,args):
            log.append(('execute',sql,args))
            if sql.startswith('SELECT 1 FROM accounts'):return Rows((1,))
            if sql.startswith('SELECT * FROM observed_archives'):
                return Rows(dict(owner_id='PRIVATE_OWNER',export_sha256=digest(b'raw'),manifest=b'raw',mode='restricted_support_historical',receipt='{"admission_sha256":"public-admission"}')) if prior else Rows()
            if sql.startswith('SELECT * FROM observed_archive_artifacts'):
                return Rows(rows=[dict(path=p,payload=v,sha256=digest(v)) for p,v in package.artifacts.items()])
            return Rows()
    class StoreDouble:
        @contextmanager
        def transaction(self,**kwargs):
            log.append('acquire')
            if fail=='acquire':raise RuntimeError('scalar acquisition failure')
            if kwargs.get('authorize'):kwargs['authorize'](None)
            log.append('entered')
            try:
                yield DB()
                if fail=='commit':raise RuntimeError('scalar commit failure')
                log.append('commit')
            except BaseException:log.append('rollback');raise
            finally:log.append('closed')
    env=dict(observe=diag.observe,json=json,timedelta=timedelta,MODE='restricted_support_historical',
        verify_support_archive=lambda *args,**kw:package,
        SupportCompletion=NS(model_validate_json=lambda value:NS(**json.loads(value))),canonical_bytes=canonical,
        marker_key=lambda _: 'scalar-marker',canonical=lambda value:json.dumps(value),state_for=lambda _:dict(scalar=True),
        timestamp=lambda value:value.isoformat(),sha256=digest,_identity=lambda *args:dict(scalar=True),
        _owners=lambda *args:log.append('owners'),_check_entries=lambda *args:log.append('check_entries'),
        _check_receipt=lambda *args:dict(receipt='same'),_receipt_bindings=lambda *args:dict(receipt='same'))
    functions(raw,{'admit_support_archive'},env)
    kwargs=dict(owner_id='PRIVATE_OWNER',received_at=WALL+timedelta(days=100),authorize=lambda _:log.append('authorize'),fault=fault)
    if callback is not None:kwargs['diagnostic']=callback
    try:return env['admit_support_archive'](StoreDouble(),b'raw','NOT_A_REAL_PATH',NS(admission_sha256='public-admission'),**kwargs),log,None
    except BaseException as error:return None,log,(type(error).__name__,str(error))


def verification_fixture(raw,*,callback=None,failure=None,trajectory_ordinal=1):
    log=[]
    def artifact(path):return NS(path=path,id=path,role='observed')
    h,l,c,o,s=(artifact(value) for value in ('PRIVATE_HISTORY_PATH','PRIVATE_LEDGER_PATH','PRIVATE_COMPLETION_PATH','PRIVATE_OUTPUT_PATH','PRIVATE_SUPPLEMENT_PATH'))
    projections={str(day):artifact('PRIVATE_PROJECTION_'+str(day)) for day in (14,42,84)}
    trajectory=NS(member_id='PRIVATE_MEMBER_ID',partition_id='PRIVATE_PARTITION_ID',mode='S0',history=h,stage_ledgers=l,completions=c,projections=projections)
    closure=NS(kind='support_stage_closure',stage_ledger=NS(id='ledger'),completion_receipt=NS(id='completion'))
    full=NS(patient_id='wrong' if failure=='member' else trajectory.member_id,records=[closure,NS(kind='support_decision',mode='fixed',availability='fixed')])
    index=NS(trajectories=[trajectory],cuts=(14,42,84),origin=WALL,horizon=84,run_id='scalar-run',source_commit='scalar-source',runtime='scalar-runtime',frozen_plan_sha256='scalar-plan')
    authority=NS(supplemental_public_artifacts=[NS(partition_id=trajectory.partition_id,artifact=s)])
    payloads={h.path:b'public history fixture',l.path:b'[{"id":"ledger"}]',c.path:b'[{"id":"completion"}]',o.path:b'public output fixture',s.path:b'public supplement fixture','manifest.json':b'raw'}
    payloads.update({item.path:canonical(dict(day=int(day))) for day,item in projections.items()})
    class InventoryPath:
        def __init__(self,path):self.path=path
        def is_symlink(self):log.append(('link',self.path));return failure=='link' and self.path==h.path
        def lstat(self):log.append(('stat',self.path));return NS(st_file_attributes=0)
        def is_file(self):log.append(('file',self.path));return True
        def relative_to(self,directory):return self
        def as_posix(self):return self.path
    class Directory:
        def __init__(self,_root):pass
        def rglob(self,_pattern):return [InventoryPath(path) for path in payloads]
    def read(_root,item):
        log.append(('read',item.path))
        if failure=='projection_reader' and item.path==projections['14'].path:raise RuntimeError('scalar reader failure')
        return payloads[item.path]
    def verifier(*args,**kwargs):
        reader=kwargs['artifact_reader']
        def verify(closure,cutoff):log.append(('closure',cutoff));reader(o)
        return verify
    def project(full,cutoff,**kwargs):
        log.append(('project',cutoff,kwargs['family'],kwargs['origin']))
        if failure=='project':raise RuntimeError('scalar projection failure')
        kwargs['verify_closure'](closure,cutoff)
        return NS(model_dump=lambda **_:dict(day=999 if failure=='comparison' else (cutoff-WALL).days))
    env=dict(observe=diag.observe,json=json,timedelta=timedelta,Path=Directory,stat=NS(FILE_ATTRIBUTE_REPARSE_POINT=1024),
        _index=lambda *args:index,ObservedHistoryV21=NS(model_validate_json=lambda raw:full),
        StageLedgerV2=NS(model_validate_json=lambda raw:NS(**json.loads(raw))),
        SupportCompletion=NS(model_validate_json=lambda raw:NS(id=json.loads(raw)['id'],output_artifacts=[o])),
        StageVerifier=verifier,canonical_bytes=canonical,project_protocol=project,Artifact=lambda **kwargs:NS(**kwargs),
        sha256=digest,read_artifact=read,VerifiedSupportArchive=lambda *args:NS(artifacts=args[3],histories=args[4]))
    functions(raw,{'verify_support_archive','_trajectory'},env)
    if trajectory_ordinal!=1:
        original=env['_trajectory']
        def selected(*args,**kwargs):
            kwargs['trajectory_ordinal']=trajectory_ordinal
            return original(*args,**kwargs)
        env['_trajectory']=selected
    try:
        kwargs={} if callback is None else dict(diagnostic=callback)
        package=env['verify_support_archive'](b'raw','NOT_A_REAL_PATH',authority,**kwargs)
        return dict(artifacts=package.artifacts,histories=sorted(package.histories)),log,None
    except BaseException as error:return None,log,(type(error).__name__,str(error))


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        if BASELINE is None or CONTROL_BASELINE is None:self.skipTest('Use run_s1_intake_diagnostics_source.py for guarded exact-baseline checks')
        self.current=(ROOT/'services/foundation/support_archive.py').read_bytes()

    def test_default_off_first_and_idempotent_output_error_and_call_equivalence(self):
        for prior,fail in ((False,None),(True,None),(False,'acquire'),(False,'commit')):
            with self.subTest(prior=prior,fail=fail):
                self.assertEqual(transaction_fixture(BASELINE,prior=prior,fail=fail),transaction_fixture(self.current,prior=prior,fail=fail))

    def test_reader_inventory_closure_and_error_equivalence_without_new_IO(self):
        for failure in (None,'member','link'):
            self.assertEqual(verification_fixture(BASELINE,failure=failure),verification_fixture(self.current,failure=failure))
        self.assertEqual(verification_fixture(BASELINE),verification_fixture(self.current,callback=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('sink'))))

    def test_trajectory_cut_parser_inventory_order_and_reader_aggregates(self):
        rows=[];observer=diag.IntakeDiagnostics(rows.append,clock=lambda:0.);observer.begin_request()
        candidate=verification_fixture(self.current,callback=observer)
        self.assertEqual(candidate,verification_fixture(BASELINE))
        events=[json.loads(row) for row in rows];stages=[row['stage'] for row in events]
        for before,after in (('trajectory_before','history_after'),('history_after','ledgers_after'),('ledgers_after','completions_after'),('closures_before','closures_after'),('inventory_before','inventory_after')):
            self.assertLess(stages.index(before),stages.index(after))
        self.assertEqual([row['cut'] for row in events if row['stage']=='cut_after'],[1,2,3])
        aggregate=next(row for row in events if row['stage']=='verify_after')
        self.assertEqual((aggregate['reads'],aggregate['hits']),(9,4))
        self.assertNotIn('PRIVATE_',''.join(rows))

    def test_sink_failure_never_changes_valid_admission_or_idempotent_commit(self):
        def broken(*args,**kwargs):raise KeyboardInterrupt('PRIVATE_CALLBACK_VALUE')
        for prior in (False,True):
            self.assertEqual(transaction_fixture(self.current,prior=prior),transaction_fixture(self.current,prior=prior,callback=broken))

    def test_transaction_entry_commit_return_and_idempotent_pending_are_distinct(self):
        stages=[]
        callback=lambda stage,**kw:stages.append(stage)
        result,log,error=transaction_fixture(self.current,callback=callback)
        self.assertIsNone(error);self.assertIn('commit',log)
        self.assertLess(stages.index('transaction_acquire'),stages.index('transaction_enter'))
        self.assertLess(stages.index('precommit'),stages.index('commit_returned'))
        stages.clear();transaction_fixture(self.current,prior=True,callback=callback)
        self.assertIn('idempotent_pending',stages);self.assertNotIn('commit_returned',stages)
        # Return stays inside with. The caller receives it only after commit.
        result,log,error=transaction_fixture(self.current,prior=True,callback=callback)
        self.assertEqual(result,dict(receipt='same'));self.assertIn('commit',log)

    def test_acquisition_and_commit_failure_never_report_commit_success(self):
        for failure in ('acquire','commit'):
            stages=[];result,log,error=transaction_fixture(self.current,fail=failure,callback=lambda stage,**kw:stages.append(stage))
            self.assertIsNotNone(error);self.assertNotIn('commit_returned',stages)
            self.assertEqual('transaction_enter' in stages,failure!='acquire')
            if failure=='commit':self.assertIn('rollback',log)

    def test_independent_fault_callback_still_rolls_back_with_broken_diagnostic(self):
        def fault(stage):
            self.assertEqual(stage,'before_support_archive_commit');raise RuntimeError('existing scalar fault')
        baseline=transaction_fixture(BASELINE,fault=fault)
        current=transaction_fixture(self.current,fault=fault,callback=lambda *args,**kw:(_ for _ in ()).throw(ValueError('sink')))
        self.assertEqual(baseline,current);self.assertIn('rollback',current[1]);self.assertNotIn('commit',current[1])

    def test_private_values_unknown_fields_nonfinite_and_nested_values_are_not_emitted(self):
        rows=[];sink=diag.IntakeDiagnostics(rows.append,clock=lambda:1.);sink.begin_request()
        for stage,values in [('PRIVATE_OWNER',{}),('cut_before',dict(owner_id='PRIVATE_OWNER')),('cut_before',dict(trajectory={'private':'PRIVATE_OWNER'})),('cut_before',dict(reads=10**100))]:
            sink(stage,**values)
        sink.clock=lambda:float('nan');sink('cut_before');sink.clock=lambda:1.;sink.summary()
        self.assertGreaterEqual(sink.suppressed,5)
        self.assertNotIn('PRIVATE_OWNER',''.join(rows));self.assertNotIn('NaN',''.join(rows))
        with self.assertRaises(ValueError):diag.validate_row(dict(kind=diag.KIND,stage=[],request=1,seconds=0))

    def test_write_then_fail_sink_is_still_byte_and_attempt_bounded(self):
        rows=[]
        def sink(raw):rows.append(raw);raise RuntimeError('after partial publication')
        observer=diag.IntakeDiagnostics(sink,clock=lambda:0.);observer.begin_request()
        for _ in range(2000):observer('trajectory_after',trajectory=24,reads=10000000,bytes=2147483648,hits=10000000)
        observer.summary()
        self.assertLessEqual(len(rows),diag.MAX_EVENTS)
        self.assertLessEqual(sum(len(row.encode())+1 for row in rows),diag.MAX_BYTES)
        self.assertEqual(observer.emitted,0);self.assertGreater(observer.suppressed,0)

    def test_first_trajectory_request_only_markers_all_three_cuts_and_plain_callback(self):
        new={'cut_projection_return','cut_reader_return'}
        expected=[(cut,stage) for cut in (1,2,3) for stage in ('cut_projection_return','cut_reader_return')]
        for ordinal in (0,1,2,24):
            for request in (1,2,3,4):
                rows=[];sink=diag.IntakeDiagnostics(rows.append,clock=lambda:0.)
                for _ in range(request):sink.begin_request()
                self.assertEqual(verification_fixture(self.current,callback=sink,trajectory_ordinal=ordinal),verification_fixture(BASELINE,trajectory_ordinal=ordinal))
                events=[json.loads(row) for row in rows]
                observed=[(row['cut'],row['stage']) for row in events if row['stage'] in new]
                self.assertEqual(observed,expected if ordinal==request==1 else [])
                if ordinal==request==1:
                    sequence=[row['stage'] for row in events if row['stage'] in new|{'cut_before','cut_after'}]
                    self.assertEqual(sequence,['cut_before','cut_projection_return','cut_reader_return','cut_after']*3)
        # An ordinary callable has no request attribute. Request filtering is
        # the existing sink's job; the call site guards only the trajectory.
        events=[];plain=lambda stage,**kw:events.append(stage)
        self.assertEqual(verification_fixture(self.current,callback=plain),verification_fixture(BASELINE))
        self.assertEqual(sum(stage in new for stage in events),6)

    def test_cut_return_exceptions_and_failed_sink_or_clock_preserve_results(self):
        for failure in ('project','projection_reader','comparison'):
            events=[]
            observed=verification_fixture(self.current,failure=failure,callback=lambda stage,**kw:events.append(stage))
            self.assertEqual(observed,verification_fixture(BASELINE,failure=failure))
            self.assertNotIn('cut_after',events)
            self.assertEqual('cut_projection_return' in events,failure!='project')
            self.assertEqual('cut_reader_return' in events,failure=='comparison')
        def broken(*args,**kwargs):raise KeyboardInterrupt('PRIVATE_SINK')
        self.assertEqual(verification_fixture(self.current,callback=broken),verification_fixture(BASELINE))
        for write_then_fail in (False,True):
            rows=[]
            def output(row):
                rows.append(row)
                if write_then_fail:raise RuntimeError('PRIVATE_WRITE_FAILURE')
            sink=diag.IntakeDiagnostics(output,clock=lambda:0.);sink.begin_request()
            if not write_then_fail:sink.clock=lambda:(_ for _ in ()).throw(RuntimeError('PRIVATE_CLOCK'))
            self.assertEqual(verification_fixture(self.current,callback=sink),verification_fixture(BASELINE))
            self.assertGreater(sink.suppressed,0);self.assertNotIn('PRIVATE_',''.join(rows))

    def test_only_two_guarded_statements_and_two_detailed_stage_names_are_added(self):
        tree=ast.parse(self.current);new={'cut_projection_return','cut_reader_return'}
        class Strip(ast.NodeTransformer):
            def visit_If(self,node):
                if len(node.body)==1 and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Call):
                    call=node.body[0].value
                    if isinstance(call.func,ast.Name) and call.func.id=='observe' and len(call.args)>1 and isinstance(call.args[1],ast.Constant) and call.args[1].value in new:
                        self.guards.append(ast.dump(node.test));return None
                return self.generic_visit(node)
        strip=Strip();strip.guards=[];normalized=strip.visit(tree)
        self.assertEqual(strip.guards,["Compare(left=Name(id='trajectory_ordinal', ctx=Load()), ops=[Eq()], comparators=[Constant(value=1)])"]*2)
        self.assertEqual(ast.dump(normalized),ast.dump(ast.parse(BASELINE)))
        old={};exec(compile(ast.parse(SCHEMA_BASELINE),'old-public-schema','exec'),old)
        self.assertEqual(diag.STAGES-old['STAGES'],new);self.assertEqual(old['STAGES']-diag.STAGES,set())
        self.assertEqual(diag.COARSE,old['COARSE']);self.assertTrue(new.isdisjoint(diag.COARSE))
        final=b'{"status":"genuine_p2_intake_idempotence_72_replays_pass"}\n'
        rows=[dict(kind=diag.KIND,stage=stage,request=1,seconds=1.,trajectory=1,cut=1) for stage in sorted(new)]
        raw=b''.join((diag.validate_row(row)+'\n').encode() for row in rows)
        self.assertEqual(diag.parse_p2_stdout(raw+final)[2],rows)

    def test_complete_fixed_run_worst_scalar_diagnostic_budget_and_later_coarsening(self):
        rows=[];sink=diag.IntakeDiagnostics(rows.append,clock=lambda:1199.999999);sink.started=0.
        def event(stage,**kw):sink(stage,**kw)
        for request in range(1,5):
            sink.begin_request();event('endpoint_before');event('admit_before');event('verify_before');event('index_after')
            for trajectory in range(1,25):
                for stage in ('trajectory_before','history_after','ledgers_after','completions_after'):event(stage,trajectory=trajectory)
                for cut in range(1,4):
                    event('cut_before',trajectory=trajectory,cut=cut)
                    if trajectory==1:
                        event('cut_projection_return',trajectory=trajectory,cut=cut)
                        event('cut_reader_return',trajectory=trajectory,cut=cut)
                    event('cut_after',trajectory=trajectory,cut=cut)
                event('closures_before',trajectory=trajectory);event('closures_after',trajectory=trajectory)
                event('trajectory_after',trajectory=trajectory,reads=10000000,bytes=2147483648,hits=10000000)
            for stage in ('supplement_before','supplement_after','manifest_before','manifest_after'):event(stage)
            event('inventory_before',reads=10000000,bytes=2147483648,hits=10000000)
            event('inventory_after',visits=100000,files=100000);event('verify_after',reads=10000000,bytes=2147483648,hits=10000000)
            for stage in ('publication_before','publication_after','transaction_acquire','transaction_enter'):event(stage)
            if request<3:
                event('owners_after')
                if request==2:event('idempotent_pending')
                else:
                    for stage in ('receipt_after','entries_after','artifacts_after','precommit','commit_returned'):event(stage)
                event('endpoint_return')
            event('post_return')
            for stage in (('status_checked','json_decoded') if request==1 else ('response_checked',)):event(stage)
            for count_pass in ((1,) if request==1 else (2,3,4) if request==2 else (5,6) if request==3 else (7,8)):
                event('counts_before',count_pass=count_pass)
                for table in range(1,10):event('count_before',count_pass=count_pass,table=table);event('count_after',count_pass=count_pass,table=table)
                event('counts_after',count_pass=count_pass)
        sink.summary()
        self.assertEqual(sink.suppressed,0);self.assertLessEqual(sink.bytes,diag.MAX_BYTES)
        self.assertTrue(sink.omitted>0);self.assertLessEqual(len(rows),diag.MAX_EVENTS)
        self.assertEqual(len(rows),409);self.assertLessEqual(sink.bytes,46743)
        extra=[json.loads(row) for row in rows if json.loads(row)['stage'] in ('cut_projection_return','cut_reader_return')]
        self.assertEqual(len(extra),6);self.assertTrue(all(row['request']==row['trajectory']==1 for row in extra))
        self.assertTrue(all(len(row.encode())+1<=384 for row in rows))
        self.assertFalse(any(json.loads(row)['request']!=1 and json.loads(row)['stage']=='cut_before' for row in rows))
        self.worst_run_rows=len(rows);self.worst_run_bytes=sink.bytes
        self.assertLessEqual(diag.MAX_BYTES+150*diag.MAX_PROGRESS_BYTES+diag.MAX_RESULT_BYTES,diag.MAX_STDOUT_BYTES)
        print('Fixed-path scalar budget:',len(rows),'rows,',sink.bytes,'bytes; max total stdout',diag.MAX_BYTES+150*diag.MAX_PROGRESS_BYTES+diag.MAX_RESULT_BYTES)

    def test_parser_requires_original_final_and_refuses_unknown_nonfinite_or_oversized_rows(self):
        final=b'{"status":"genuine_p2_intake_idempotence_72_replays_pass"}\n'
        progress=b'{"kind":"p2_phase_progress","phase":"initial_intake","state":"before","elapsed_seconds":1,"completed_replays":0}\n'
        row=dict(kind=diag.KIND,stage='post_return',request=1,seconds=1.)
        diagnostic=(diag.validate_row(row)+'\n').encode()
        result,coarse,details=diag.parse_p2_stdout(progress+diagnostic+final)
        self.assertEqual(len(coarse),1);self.assertEqual(details,[row])
        for invalid in (progress+diagnostic,b'{"kind":"unknown"}\n'+final,diagnostic.replace(b'1.0',b'NaN')+final,
                b'{"status":"failed"}\n',b'x'*(diag.MAX_STDOUT_BYTES+1),final.rstrip(),b'{"kind":"x","kind":"y"}\n'+final):
            with self.subTest(size=len(invalid)),self.assertRaises((ValueError,UnicodeError)):diag.parse_p2_stdout(invalid)

    def test_disabled_observation_never_calls_a_clock_or_callback(self):
        diag.observe(None,'PRIVATE_INVALID_STAGE',unknown='PRIVATE_VALUE')
        self.assertIsNone(diag.observe(None,'transaction_enter'))

    def test_original_24_assertions_and_saved_GET_body_unchanged(self):
        original=ast.parse(CONTROL_BASELINE)
        current=ast.parse((ROOT/'tooling/foundation/s1_intake_diagnostic_control.py').read_bytes())
        assertions=lambda tree:[ast.dump(node) for node in ast.walk(tree) if isinstance(node,ast.Assert)]
        self.assertEqual(len(assertions(original)),24);self.assertEqual(assertions(original),assertions(current))
        get_loop=lambda tree:next(node for node in ast.walk(tree) if isinstance(node,ast.For) and isinstance(node.target,ast.Name) and node.target.id=='trajectory')
        self.assertEqual(ast.dump(get_loop(original)),ast.dump(get_loop(current)))
        settings=next(node for node in ast.parse((ROOT/'services/foundation/app.py').read_bytes()).body if isinstance(node,ast.ClassDef) and node.name=='Settings')
        field=next(node for node in settings.body if isinstance(node,ast.AnnAssign) and node.target.id=='support_intake_diagnostic')
        self.assertIsNone(field.value.value)

    def test_existing_nine_count_queries_values_and_order_unchanged_but_never_logged(self):
        def run(raw,callback):
            calls=[]
            class DB:
                def execute(self,sql):calls.append(sql);return NS(fetchone=lambda:(987654,))
            class Store:
                @contextmanager
                def transaction(self):yield DB()
            node=next(node for node in ast.walk(ast.parse(raw)) if isinstance(node,ast.FunctionDef) and node.name=='counts')
            env=dict(observe=diag.observe,_DIAGNOSTIC=callback,_COUNT_PASS=0)
            exec(compile(ast.Module(body=[node],type_ignores=[]),'scalar-count-query','exec'),env)
            return env['counts'](Store()),calls
        current=(ROOT/'tooling/foundation/s1_intake_diagnostic_control.py').read_bytes()
        rows=[];callback=diag.IntakeDiagnostics(rows.append,clock=lambda:0.);callback.begin_request()
        self.assertEqual(run(CONTROL_BASELINE,None),run(current,callback))
        self.assertEqual(len(run(current,None)[1]),9)
        self.assertNotIn('987654',''.join(rows));self.assertNotIn('SELECT',''.join(rows))
        parsed=[json.loads(row) for row in rows]
        self.assertEqual([row['table'] for row in parsed if row['stage']=='count_after'],list(range(1,10)))

    def test_endpoint_return_follows_actual_admit_return_and_is_absent_on_error(self):
        tree=ast.parse((ROOT/'services/foundation/app.py').read_bytes())
        branch=next(node for node in ast.walk(tree) if isinstance(node,ast.If) and isinstance(node.test,ast.Name) and node.test.id=='restricted'
            and any(isinstance(item,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='receipt' for target in item.targets) for item in node.body))
        body=[node for node in branch.body if not isinstance(node,ast.ImportFrom)]
        wrapper=ast.FunctionDef(name='endpoint',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body,decorator_list=[])
        for fail in (False,True):
            order=[]
            def admit(*args,**kwargs):
                order.append('admit_enter')
                if fail:raise RuntimeError('scalar admission/commit error')
                order.append('successful_context_exit');return dict(receipt='same')
            settings=NS(clock=lambda:WALL,fault=None,support_intake_diagnostic=lambda stage,**kw:order.append(stage))
            env=dict(data=NS(mode='archive_only'),observe=diag.observe,settings=settings,admit_support_archive=admit,
                store=None,raw=b'public',root=None,authority=None,owner='PRIVATE_OWNER',authorize=None)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper],type_ignores=[])),'scalar-endpoint','exec'),env)
            if fail:
                with self.assertRaises(RuntimeError):env['endpoint']()
                self.assertNotIn('endpoint_return',order)
            else:
                self.assertEqual(env['endpoint'](),dict(receipt='same'))
                self.assertLess(order.index('successful_context_exit'),order.index('endpoint_return'))
