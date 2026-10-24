"""N-FIT04 PREP: scalar contracts, clocks and inert process doubles only.

Run this file directly with the approved isolated scalar Python. Real process,
network, Store/app/SQLite and scientific imports are blocked for the whole run.
"""
import ast
import copy
import importlib.abc
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
for path in (ROOT,ROOT/'tests',ROOT/'tests/contracts',ROOT/'tests/integration/replay',ROOT/'tooling/foundation'):
    sys.path.insert(0,str(path))
DENIED={'numpy','scipy','pymc','pytensor','statsmodels','arviz','arviz_stats','xarray','pandas',
    'netCDF4','sqlite3','_sqlite3','requests','httpx','urllib.request'}


class Tripwire(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in DENIED or fullname.startswith(('services.foundation','methods.')):
            raise AssertionError('PREP import forbidden: '+fullname)


sys.meta_path.insert(0,Tripwire())
import analysis_dispatcher as d
from contracts.domain.analysis import sha
from contracts.domain.nof1_app import NResult,execution_binding,ownership_manifest
from tests.contracts.test_nof1_app import product

CID='a'*64
ATTEMPT='analysis-'+'1'*32
INPUT_HASH='2'*64


def packet():
    return dict(schema='n-fit04-v1',executable=True,file_caps=d.N_FILE_CAPS.copy(),total_cap=d.N_TOTAL_CAP,
        progress_cap=d.N_PROGRESS_CAP,json_rows=d.N_JSON_ROWS,**{k:'3'*64 for k in
            ('data03_actual','queue_export_actual','source_review','operation_review','root_go')})


def marker(stage='fitting',elapsed=10,sequence=1,start=None,finish=None,**changes):
    return dict(schema='n-fit04-progress-v1',attempt_id=ATTEMPT,input_sha256=INPUT_HASH,
        stage=stage,sequence=sequence,elapsed_seconds=elapsed,rollouts_started_elapsed_seconds=start,
        integration_finished_elapsed_seconds=finish,extension=False,K=None,**changes)


def archive(name='result.json',content=b'{}',kind=tarfile.REGTYPE):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        info=tarfile.TarInfo(name);info.size=len(content);info.type=kind
        tar.addfile(info,io.BytesIO(content) if kind==tarfile.REGTYPE else None)
    return buf.getvalue()


class StageControls(unittest.TestCase):
    def setUp(self):
        self.now=100.;self.stages=d.NStages(100.,7300.,ATTEMPT,INPUT_HASH)
        self.clock=patch.object(d.time,'monotonic',side_effect=lambda:self.now);self.clock.start();self.addCleanup(self.clock.stop)
    def admit(self,**kwargs):return self.stages.admit(d.canonical(marker(**kwargs)))
    def test_missing_progress_fitting_forever_and_extension_cannot_reset_pre_rollout(self):
        self.now=110.;self.admit()
        self.now=1000.;self.admit(stage='diagnostics',elapsed=900,sequence=2)
        self.now=2000.;v=marker(elapsed=1900,sequence=3);v['extension']=True;self.stages.admit(d.canonical(v))
        self.assertEqual(self.stages.active_deadline(),5100.)
        self.now=5100.
        with self.assertRaises(TimeoutError):self.stages.check()
        with self.assertRaises(TimeoutError):self.admit(stage='rollouts',elapsed=4999,start=4999,sequence=4)
    def test_first_rollout_uses_earlier_launch_plus_duration_and_never_resets(self):
        self.now=500.;self.admit(stage='rollouts',elapsed=300,start=100)
        self.assertEqual(self.stages.active_deadline(),2000.)  # Not observation time +1800.
        self.now=1900.;self.admit(stage='rollouts',elapsed=1800,start=100,sequence=2)
        self.assertEqual(self.stages.active_deadline(),2000.)
        self.now=2000.
        with self.assertRaises(TimeoutError):self.admit(stage='rollouts',elapsed=1899,start=100,finish=1899,sequence=3)
    def test_timely_completion_releases_only_integration_bound_with_original_common_deadline(self):
        self.now=200.;self.admit(stage='rollouts',elapsed=100,start=100)
        self.now=400.;self.admit(stage='rollouts',elapsed=300,start=100,finish=299,sequence=2)
        self.assertEqual(self.stages.active_deadline(),7300.)
        self.now=7300.
        with self.assertRaises(TimeoutError):self.stages.check()
    def test_stale_identity_schema_wrong_types_and_reset_refuse(self):
        self.now=500.
        for changes in (dict(attempt_id='foreign'),dict(input_sha256='3'*64),dict(sequence=True),
                dict(elapsed_seconds=True),dict(K=3),dict(extension=1),dict(stage='complete'),dict(extra='private')):
            v=marker();v.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.stages.admit(d.canonical(v))
        self.admit(stage='rollouts',elapsed=100,start=100)
        for v in (marker(stage='rollouts',elapsed=110,start=101,sequence=2),
                marker(stage='rollouts',elapsed=110,start=100,sequence=1),marker(elapsed=110,sequence=2)):
            with self.assertRaises(ValueError):self.stages.admit(d.canonical(v))
        self.assertIsNone(self.stages.admit(d.canonical(self.stages.last)))
    def test_worker_stage_uses_durations_and_keeps_the_first_rollout(self):
        tree=ast.parse((ROOT/'services/learner/nof1_worker.py').read_text(encoding='utf-8'))
        run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        funcs=[n for n in run.body if isinstance(n,ast.FunctionDef) and n.name in ('stage','check_deadline')]
        emitted=[];state=dict(sequence=0,extension=False,rollouts_started_elapsed_seconds=None,integration_finished_elapsed_seconds=None)
        ns=dict(time=d.time,started=100.,deadline=7300.,progress_state=state,out=Path('INERT'),
            product=Mock(attempt_id=ATTEMPT),base={'input_sha256':INPUT_HASH},publish=lambda path,v:emitted.append(v))
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'<actual-worker-progress>','exec'),ns)
        self.now=200.;ns['stage']({'stage':'rollouts'})
        self.now=500.;ns['stage']({'stage':'rollouts','K':1024,'checks':{'private':'never-published'}})
        self.assertEqual(emitted[-1]['rollouts_started_elapsed_seconds'],100.)
        self.assertNotIn('checks',emitted[-1]);self.assertEqual(emitted[-1]['elapsed_seconds'],400.)
        self.now=2000.
        with self.assertRaises(TimeoutError):ns['stage']({'stage':'rollouts','integration_finished':True})


class FileControls(unittest.TestCase):
    def test_exact_regular_capped_complete_file_only(self):
        self.assertEqual(d.n_tar_payload(archive(), 'result.json',2),b'{}')
        cases=(archive('other.json'),archive('../result.json'),archive(content=b'xxx'),
            archive(kind=tarfile.SYMTYPE),archive(kind=tarfile.DIRTYPE),archive()[:700],archive()[:512])
        for raw in cases:
            with self.subTest(length=len(raw)),self.assertRaises((ValueError,tarfile.TarError)):
                d.n_tar_payload(raw,'result.json',2)
        buf=archive();buf=buf[:1024]+archive()
        with self.assertRaises(ValueError):d.n_tar_payload(buf,'result.json',2)
    def receive(self,chunks,*,code=0,cap=2,timeout=False):
        clock=[100.];process=Mock(pid=51);process.stdout.fileno.return_value=7
        process.poll.return_value=code;process.wait.return_value=code
        def read(fd,size):
            if timeout:clock[0]=120.;raise BlockingIOError()
            chunk=chunks.pop(0) if chunks else b''
            self.assertLessEqual(size,cap+16385);return chunk
        receipts=[]
        with patch.object(subprocess,'Popen',return_value=process),patch.object(d.os,'set_blocking'), \
                patch.object(d.os,'read',side_effect=read),patch.object(d.time,'monotonic',side_effect=lambda:clock[0]),patch.object(d.time,'sleep'):
            if timeout:
                with self.assertRaises(TimeoutError):d.n_file(CID,'result.json',cap,110.,receipts=receipts)
            else:
                result=d.n_file(CID,'result.json',cap,110.,receipts=receipts)
                self.assertEqual(result,b'{}')
        self.assertTrue(receipts[0]['reaped']);self.assertTrue(process.stdout.close.called)
        return process,receipts
    def test_stream_receiver_caps_bytes_reaps_and_checks_deadline_even_without_bytes(self):
        self.receive([archive(),b''])
        process,_=self.receive([],timeout=True);process.kill.assert_called_once()
        process=Mock(pid=51);process.stdout.fileno.return_value=7
        with patch.object(subprocess,'Popen',return_value=process),patch.object(d.os,'set_blocking'), \
                patch.object(d.os,'read',return_value=b'x'*16387),patch.object(d.time,'monotonic',return_value=100.):
            with self.assertRaisesRegex(ValueError,'receive byte cap'):d.n_file(CID,'result.json',2,110.)
        process.kill.assert_called_once();process.wait.assert_called_once()
    def test_unknown_names_missing_caps_and_reap_uncertainty_refuse(self):
        for name,cap in (('worker.stderr',1),('output/.',1),('result.json',0),('result.json',None)):
            with self.assertRaises(ValueError):d.n_file(CID,name,cap,100.)
        process=Mock(pid=52);process.stdout.fileno.return_value=7;process.wait.side_effect=RuntimeError('private')
        with patch.object(subprocess,'Popen',return_value=process),patch.object(d.os,'set_blocking',side_effect=ValueError('private')):
            with self.assertRaisesRegex(d.StopUnconfirmed,'reap unconfirmed'):d.n_file(CID,'result.json',2,d.time.monotonic()+20)
    def test_scalar_rows_duplicate_keys_nonfinite_and_private_payload_overflow_refuse(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',d.canonical(['x']*(d.N_JSON_ROWS+1)),d.canonical({'error':'x'*2049})):
            with self.assertRaises(ValueError):d.n_json(raw)
    def test_existing_result_identity_hash_ownership_and_required_set_remain_authoritative(self):
        import tempfile
        p=product();host=dict(source_commit='4'*40,learner_image='sha256:'+'5'*64);trusted=execution_binding(p,host)
        diag=dict(execution=trusted,fits=[],timings=dict(worker_seconds=10))
        fields=dict(schema_version='4.0.0',synthetic=True,kind='poc_nof1_result',purpose=p.purpose,
            attempt_id=p.attempt_id,target_id=p.target_id,input_sha256=sha(p.model_dump(mode='json')),
            history_sha256=p.history_sha256,cohort=[m.model_dump() for m in p.cohort],cutoff=p.cutoff.isoformat(),
            run=p.run.model_dump(),configuration=p.request.configuration.model_dump(),status='failed',readiness='eligible',
            reason='INERT-CONTROL',generated_at=p.cutoff.isoformat(),effect=None,diagnostics=diag,limitations=['INERT-CONTROL'])
        ctx=p.request.context
        fields.update({k:getattr(ctx,k).model_dump() for k in ('model','prior','estimand','protocol')})
        from contracts.domain.nof1_app import consumed_ids
        fields['consumed_record_ids']=consumed_ids(p)
        ownership=ownership_manifest(p)
        for fault in (None,'wrong-owner','wrong-input','bad-hash','extra-file','partial'):
            files={'diagnostics.json':d.canonical(diag),'ownership.json':d.canonical(ownership)}
            result=copy.deepcopy(fields);result['artifacts']=[dict(path=name,sha256=d.hashlib.sha256(raw).hexdigest()) for name,raw in files.items()]
            if fault=='wrong-owner':files['ownership.json']=d.canonical(dict(ownership,target_id='other'))
            if fault=='wrong-input':result['input_sha256']='0'*64
            if fault=='bad-hash':result['artifacts'][0]['sha256']='0'*64
            if fault=='extra-file':result['artifacts'].append(dict(path='worker.stderr',sha256='0'*64))
            files['result.json']=d.canonical(result)
            if fault=='partial':files['diagnostics.json']=b'{'
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=ROOT) as temp, \
                    patch.object(d,'n_file',side_effect=lambda cid,name,*a,**kw:files[name]):
                stages=Mock();stages.active_deadline.return_value=100.
                if fault:
                    with self.assertRaises(ValueError):d.n_collect(CID,Path(temp),{'input':p.model_dump(mode='json')},trusted,stages,[])
                else:self.assertEqual(set(d.n_collect(CID,Path(temp),{'input':p.model_dump(mode='json')},trusted,stages,[])),set(files))


class DispatchControls(unittest.TestCase):
    def test_prep_template_unknown_review_or_caps_refuses_before_private_export(self):
        template=json.loads((ROOT/'tooling/foundation/nof1_fit04_packet.json').read_bytes())
        with self.assertRaises(ValueError):d.n_packet(template)
        d.n_packet({'n_fit04':packet()})
        for field in packet():
            value=packet();value.pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):d.n_packet({'n_fit04':value})
    def scenario(self,fault):
        import tempfile
        clock=[100.];calls=[];captures=[];callbacks=[]
        proof=dict(attempt_id=ATTEMPT,input={'kind':'poc_nof1_input'},input_sha256=INPUT_HASH)
        state=dict(prefix='INERT',source_commit='4'*40,learner_image='sha256:'+'5'*64,
            cohort_reviewed_runtime=dict(source_commit='4'*40,learner_image='sha256:'+'5'*64),
            expected=dict(selection={},export_sha256='6'*64),service_deadline_unix=100000.,
            service_cid='c'*64,service_container='INERT-SERVICE',service_image='sha256:'+'7'*64)
        created=[]
        def command(argv,**kw):
            calls.append((argv,kw));out=b''
            if argv[:2]==['docker','inspect']:out=d.canonical(dict(Name='/INERT-SERVICE',Image=state['service_image']))
            elif argv[:3]==['docker','image','inspect']:out=state['learner_image'].encode()
            elif argv[:2]==['docker','create']:created.append('a' if not created else 'b');out=(created[-1]*64).encode()
            elif argv[:2]==['docker','exec'] and 'services.foundation.analysis_cli' in argv:
                op=argv[6]
                if op=='queued-request':out=d.canonical(proof)
                elif op=='claim':out=d.canonical(dict(attempt_id=ATTEMPT,input=proof['input'],claim_token='f'*48))
                elif op=='bind-execution':out=d.canonical(dict(input_sha256=INPUT_HASH,source_commit=state['source_commit'],learner_image=state['learner_image']))
                elif op=='ingest':
                    if fault=='late-ingest':clock[0]=7301.
                    out=d.canonical(dict(id=ATTEMPT,status='failed'))
                else:
                    if op=='progress' and fault=='slow-publication':clock[0]=5100.
                    out=b'null'
            return subprocess.CompletedProcess(argv,0,out,b'NEVER-PUBLISH-PRIVATE')
        def progress_file(*args,**kwargs):
            captures.append(kwargs)
            if fault=='slow-copy':clock[0]=5101.;return None
            if fault=='failed-copy':return None
            if fault in ('throttle-expiry','slow-publication'):return d.canonical(marker(elapsed=10 if fault=='slow-publication' else 4999))
            if fault=='integration-exhaustion':return d.canonical(marker(stage='rollouts',elapsed=10,start=5))
            return d.canonical(marker(stage='rollouts',elapsed=10,start=5,finish=9))
        def supervised(cid,folder,deadline,on_poll=None):
            if on_poll is None:return {}
            callbacks.append(on_poll);clock[0]=5099. if fault=='throttle-expiry' else 120.
            if fault=='terminal-late':clock[0]=5101.;return {}
            on_poll()
            if fault in ('no-progress','failed-copy'):
                clock[0]=5100.;on_poll()
            elif fault=='throttle-expiry':
                clock[0]=5100.;on_poll()
            elif fault=='integration-exhaustion':
                clock[0]=1905.;on_poll()
            return {}
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path=Path(temp)/'deployment.json'
            with patch.object(d,'validate_deployment',return_value=proof),patch.object(d,'require_dispatchable'), \
                    patch.object(d,'exclusive',return_value=Mock()),patch.object(d,'command',side_effect=command), \
                    patch.object(d,'absent'),patch.object(d,'inspect',return_value={'State':{'Status':'running'}}), \
                    patch.object(d,'supervise',side_effect=supervised),patch.object(d,'stop_owned',return_value=[]), \
                    patch.object(d,'n_file',side_effect=(lambda *a,**kw:None) if fault=='no-progress' else progress_file), \
                    patch.object(d,'n_collect',return_value=['result.json','diagnostics.json','ownership.json']), \
                    patch.object(d.time,'monotonic',side_effect=lambda:clock[0]),patch.object(d.time,'time',return_value=1000.):
                if fault in ('terminal-late','slow-copy','failed-copy','no-progress','late-ingest','throttle-expiry','integration-exhaustion','slow-publication'):
                    with self.assertRaisesRegex(RuntimeError,'n-fit04-failed'):d.run_once(state,path,'INERT')
                else:self.assertEqual(d.run_once(state,path,'INERT')['status'],'failed')
            manifest=json.loads((Path(temp)/'analysis-jobs'/ATTEMPT/'dispatch.json').read_bytes())
            encoded=json.dumps(manifest)
            self.assertNotIn('NEVER-PUBLISH-PRIVATE',encoded);self.assertNotIn('f'*48,encoded)
            self.assertFalse(any(argv[:2]==['docker','logs'] or '/output/.' in ' '.join(argv) for argv,_ in calls))
            for argv,kw in calls:
                if 'progress' in argv:self.assertLessEqual(kw['deadline'],7300.)
            return calls,manifest
    def test_deadlines_veto_terminal_between_callbacks_and_slow_failed_copy_and_late_ingest(self):
        for fault in ('terminal-late','slow-copy','failed-copy','no-progress','late-ingest',
                'throttle-expiry','integration-exhaustion','slow-publication',None):
            with self.subTest(fault=fault):self.scenario(fault)


def freeze_proof(payload):
    """Inverse only the declared N delta; compare complete residual source ASTs."""
    import hashlib
    base=payload['files'];dump=lambda tree:ast.dump(tree,include_attributes=False)
    digest=lambda raw:hashlib.sha256(raw).hexdigest()
    worker='services/learner/nof1_worker.py';dispatcher='tooling/foundation/analysis_dispatcher.py'
    old_worker=ast.parse(base[worker]);old_run=next(n for n in old_worker.body if isinstance(n,ast.FunctionDef) and n.name=='run')
    old_progress={n.name:n for n in old_run.body if isinstance(n,ast.FunctionDef)}
    class WorkerInverse(ast.NodeTransformer):
        def visit_FunctionDef(self,node):
            if node.name in ('stage','check_deadline'):return copy.deepcopy(old_progress[node.name])
            return self.generic_visit(node)
        def visit_Assign(self,node):
            if any(isinstance(t,ast.Name) and t.id=='progress_state' for t in node.targets):return None
            return self.generic_visit(node)
        def visit_Expr(self,node):
            expected=ast.parse("stage(dict(stage='rollouts',integration_finished=True))").body[0]
            return None if dump(node)==dump(expected) else self.generic_visit(node)
    class DispatcherInverse(ast.NodeTransformer):
        function=None
        def visit_FunctionDef(self,node):
            if node.name.startswith('n_'):return None
            prior=self.function;self.function=node.name;node=self.generic_visit(node);self.function=prior
            if node.name=='progress':node.args.args=[];node.args.defaults=[]
            if node.name=='call':
                assert len(node.body)==2 and isinstance(node.body[0],ast.Assign) and isinstance(node.body[1],ast.Return)
                node.body=[ast.Return(value=node.body[0].value)]
            return node
        def visit_ClassDef(self,node):return None if node.name=='NStages' else self.generic_visit(node)
        def visit_Assign(self,node):
            names=[t.id for t in node.targets if isinstance(t,ast.Name)]
            if any(n.startswith('N_') for n in names):return None
            if self.function=='run_once' and set(names)&{'nof1','stages','common_origin'}:return None
            if self.function=='validate_deployment' and names==['proof_path']:return None
            node=self.generic_visit(node)
            if self.function=='run_once' and names==['deadline']:
                assert isinstance(node.value,ast.BinOp) and isinstance(node.value.left,ast.Name) and node.value.left.id=='common_origin'
                node.value.left=ast.parse('time.monotonic()',mode='eval').body
            if self.function=='validate_deployment' and names==['proof']:
                node.value=ast.parse("json.loads(ordinary_path(deployment.parent/state['queued_export_path']).read_bytes())",mode='eval').body
            return node
        def visit_If(self,node):
            if isinstance(node.test,ast.Name) and node.test.id=='nof1':
                return [self.visit(n) for n in node.orelse]
            if isinstance(node.test,ast.BoolOp) and isinstance(node.test.values[0],ast.UnaryOp) and isinstance(node.test.values[0].operand,ast.Name) and node.test.values[0].operand.id=='nof1':
                node.test.values.pop(0)
            return self.generic_visit(node)
        def visit_IfExp(self,node):
            if self.function!='validate_deployment' and isinstance(node.test,ast.Name) and node.test.id=='nof1':return self.visit(node.orelse)
            return self.generic_visit(node)
        def visit_Try(self,node):
            node=self.generic_visit(node)
            if (len(node.body)==2 and isinstance(node.body[0],ast.Assign)
                    and isinstance(node.body[0].targets[0],ast.Name) and node.body[0].targets[0].id=='stopped'):
                expected=ast.parse('failures.append(dict(cid=cid,cleanup=stopped))').body[0]
                assert dump(node.body[1])==dump(expected)
                node.body=[ast.parse('failures.append(dict(cid=cid,cleanup=stop_owned(cid)))').body[0]]
            return node
    proofs={}
    for name,inverse in ((worker,WorkerInverse()),(dispatcher,DispatcherInverse())):
        original=ast.parse(base[name]);projected=inverse.visit(ast.parse((ROOT/name).read_text(encoding='utf-8')))
        before=dump(original);after=dump(projected)
        if before!=after:
            import difflib
            print('\n'.join(list(difflib.unified_diff(ast.unparse(original).splitlines(),ast.unparse(ast.fix_missing_locations(projected)).splitlines()))[:100]))
            raise AssertionError('inverse residual differs: '+name)
        proofs[name]=dict(base_ast_sha256=digest(before.encode()),inverse_ast_sha256=digest(after.encode()),equal=True)
    protected={}
    for name,text in base.items():
        if name in (worker,dispatcher):continue
        current=(ROOT/name).read_bytes();original=text.encode('utf-8')
        # Git text arrives through JSON with LF; normalize CRLF checkout bytes.
        normalized=current.replace(b'\r\n',b'\n')
        assert normalized==original.replace(b'\r\n',b'\n'),name
        protected[name]=dict(git_text_sha256=digest(original.replace(b'\r\n',b'\n')),checkout_sha256=digest(current),unchanged=True)
    changed=[worker,dispatcher,'tests/test_nof1_fit04_prep.py','tooling/foundation/nof1_fit04_packet.json']
    index=dict(task='N-FIT04',status='PARTIAL_PREP_STOP_FOR_INDEPENDENT_SOURCE_REVIEW',base=payload['base'],source_head=payload['source_head'],
        branch='feat/poc-n-fit04-prep-20261024',model='gpt-6.1-sol',effort='xhigh',settings_verified_by='parent launch telemetry',
        plan_blob='8a6a814dc4f7e2cfdb76de368935d9ac214eb4b7',critique_blob='4629945e4d52b9cbcd9c8da8e1c4d5c105b5027a',
        checks=dict(guarded_scalar_and_inert_double_tests=40,passed=True,actual_science_app_store_sqlite_native_network=False),
        source_sha256={name:digest((ROOT/name).read_bytes()) for name in changed},inverse_ast=proofs,
        protected=protected,pr27_applicability='No changes from d889ca129c5dbae02ec642edfc82b85d616eab51 to methods/nof1, methods/measurement.py or nof1_config.py; runtime config/version applicability UNKNOWN',
        data03_actual='UNKNOWN',queue_export_actual='UNKNOWN',genuine_n12_feasibility='UNKNOWN',combined_source_op_ready=False)
    path=ROOT/'docs/implementation/poc-n-fit04-prep-index-20261024.json'
    path.write_text(json.dumps(index,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(inverse_ast_equal=True,protected_paths=len(protected),status=index['status'])))


if __name__=='__main__':
    def forbidden(*args,**kwargs):raise AssertionError('real process/network forbidden in PREP')
    import os
    with tempfile.TemporaryDirectory(dir=ROOT) as scratch,patch.object(tempfile,'tempdir',scratch), \
            patch.object(subprocess,'Popen',side_effect=forbidden),patch.object(subprocess,'run',side_effect=forbidden), \
            patch.object(socket,'socket',side_effect=forbidden),patch.object(os,'system',side_effect=forbidden):
        if sys.argv[1:]==['--freeze-proof']:
            freeze_proof(json.load(sys.stdin));sys.exit(0)
        names=('__main__','tests.contracts.test_nof1_app','tests.contracts.test_nof1_dispatch','test_ordinary_dispatcher')
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in names)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not DENIED.intersection(sys.modules)
    print('N-FIT04 guarded PREP only; no app/Store/SQLite/science/process/network execution')
    sys.exit(not result.wasSuccessful())
