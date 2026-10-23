"""Inert privacy/process doubles only. Never run/import scientific payload."""
import ast
import builtins
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('s2_failure_entry',ROOT/'tooling/foundation/s2_numerics_entry.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
SECRET='SECRET_password_patient_case_value_do_not_publish'


def raised(path='/qualification/s2_numerics_unit.py',error=ValueError):
    namespace=dict(problem=error,secret=SECRET)
    exec(compile('def fail(*args):\n    raise problem(secret)\n',path,'exec'),namespace)
    try:namespace['fail']()
    except BaseException as failure:return failure


def row():
    return dict(kind='s2-child-failure-v1',draws=1000,stage='unit_call',error_class='ValueError',
                locations=[dict(file='s2_numerics_unit.py',line=24)],omitted=True)


def old_entry():
    path=ROOT/'artifacts/s2-r4-source-checks/old-entry.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest()=='5c31c1f0dc460ee1574121dc97923106de8577a3a667cac60c16ef93a6c26a5f'
    spec=importlib.util.spec_from_file_location('s2_old_entry_equivalence',path)
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    return previous


@contextlib.contextmanager
def child_doubles(subject,stage=None,unit_raw='{"inert":"fixed","artifact":"VU5JVA=="}'):
    original_import=builtins.__import__
    contracts=SimpleNamespace(domain=SimpleNamespace(__path__=[]))
    methods=SimpleNamespace(support=SimpleNamespace(__path__=[]))
    def unit_call(*args):
        if stage=='unit_call':raise raised()
        return unit_raw
    unit=SimpleNamespace(main=unit_call)
    def importer(name,*args,**kwargs):
        if name=='contracts.domain':
            if stage=='package_setup':raise ImportError(SECRET)
            return contracts
        if name=='methods.support':return methods
        if name=='s2_numerics_unit':
            if stage=='module_import':raise ImportError(SECRET)
            return unit
        return original_import(name,*args,**kwargs)
    with patch.object(subject,'checked_sources'),patch.object(Path,'exists',return_value=False),\
            patch.object(sys,'path',list(sys.path)),patch.object(builtins,'__import__',side_effect=importer),\
            patch.object(subject.time,'monotonic',side_effect=[10.,11.,12.,13.]):
        yield


class FakeProcess:
    pid=123
    def __init__(self,events,code=1,timeout=False,unreaped=False):
        self.events=events;self.code=code;self.timeout=timeout;self.unreaped=unreaped;self.killed=False
    def wait(self,timeout):
        self.events.append('wait')
        if self.timeout and (not self.killed or self.unreaped):raise subprocess.TimeoutExpired(SECRET,timeout)
        return -9 if self.killed else self.code
    def poll(self):
        self.events.append('poll')
        return None if self.timeout and (not self.killed or self.unreaped) else -9 if self.killed else self.code
    def kill(self):self.events.append('kill');self.killed=True


class FailurePrivacy(unittest.TestCase):
    def test_projection_only_exact_carrier_paths_fixed_class_and_bounded_locations(self):
        projected=entry.child_failure(raised(),'unit_call',1000)
        self.assertEqual(projected['error_class'],'ValueError')
        self.assertEqual(projected['locations'],[dict(file='s2_numerics_unit.py',line=2)])
        self.assertTrue(projected['omitted']);self.assertNotIn(SECRET,json.dumps(projected))
        class SecretNamedError(Exception):pass
        unknown=entry.child_failure(raised('/private/SECRET/s2_numerics_unit.py',SecretNamedError),'module_import',1000)
        self.assertEqual(unknown['locations'],[]);self.assertEqual(unknown['error_class'],'other')
        self.assertNotIn('SecretNamedError',json.dumps(unknown));self.assertNotIn('/private',json.dumps(unknown))
        namespace={}
        exec(compile('def fail(n):\n    if n: return fail(n-1)\n    raise ValueError()\n','/qualification/entry.py','exec'),namespace)
        try:namespace['fail'](12)
        except ValueError as error:many=entry.child_failure(error,'unit_call',1000)
        self.assertEqual(len(many['locations']),8);self.assertTrue(many['omitted'])

    def test_strict_single_schema_rejects_messages_unknown_frames_duplicates_nonfinite_and_size(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as directory:
            p=Path(directory)/'fixed.stderr';p.write_text(json.dumps(row())+'\n',encoding='utf-8')
            self.assertEqual(entry.read_child_failure(p,1000)['status'],'available')
            cases=[b'',b'not JSON '+SECRET.encode(),json.dumps(row()).encode()+b'\n'+json.dumps(row()).encode(),
                   b'{"kind":1,"kind":2}',b'{"kind":NaN}',b'x'*65537]
            for changed in (dict(row(),message=SECRET),dict(row(),draws=True),dict(row(),stage=SECRET),
                    dict(row(),error_class=SECRET),dict(row(),omitted=0),
                    dict(row(),locations=[dict(file='/private/s2_numerics_unit.py',line=2)]),
                    dict(row(),locations=[dict(file='entry.py',line=True)]),
                    dict(row(),locations=[dict(file='entry.py',line=100001)]),
                    dict(row(),locations=[dict(file='entry.py',line=2)]*9)):
                cases.append(json.dumps(changed).encode())
            for raw in cases:
                p.write_bytes(raw);detail=entry.read_child_failure(p,1000)
                self.assertEqual(detail['status'],'unavailable');self.assertNotIn(SECRET,json.dumps(detail))
            missing=entry.read_child_failure(Path(directory)/'absent',1000)
            self.assertEqual(missing,dict(status='unavailable',code='read_failed'))

    def test_bounded_read_and_sink_or_serialization_failure_have_no_raw_fallback(self):
        reads=[]
        class Stream:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):reads.append(size);return b'x'*65537
        with patch.object(Path,'open',return_value=Stream()):
            self.assertEqual(entry.read_child_failure(Path('fixed'),1000)['code'],'oversized')
        self.assertEqual(reads,[65537])
        sink=SimpleNamespace(write=lambda value:(_ for _ in ()).throw(OSError(SECRET)),flush=lambda:None)
        with patch.object(entry.sys,'stderr',sink):self.assertFalse(entry.emit_failure_safe(row()))
        with patch.object(entry.json,'dumps',side_effect=ValueError(SECRET)):
            self.assertFalse(entry.emit_failure_safe(row()))
        output=io.StringIO()
        with contextlib.redirect_stderr(output):self.assertFalse(entry.emit_failure_safe(dict(message='x'*4096)))
        self.assertEqual(output.getvalue(),'')

    def test_top_level_child_stage_failure_suppresses_automatic_raw_traceback(self):
        stderr=io.StringIO()
        with patch.object(entry,'checked_sources',side_effect=ValueError(SECRET)),contextlib.redirect_stderr(stderr):
            code=entry.main(['--child','1000','--budget','300','--manifest-sha256','a'*64])
        self.assertEqual(code,1);lines=stderr.getvalue().splitlines();self.assertEqual(len(lines),1)
        value=json.loads(lines[0]);self.assertEqual(value['stage'],'source_check')
        self.assertNotIn(SECRET,stderr.getvalue());self.assertNotIn('Traceback',stderr.getvalue())
        tree=ast.parse((ROOT/'tooling/foundation/s2_numerics_entry.py').read_text(encoding='utf-8'))
        top=tree.body[-1];self.assertIsInstance(top,ast.If)
        namespace=dict(__name__='__main__',main=lambda:code)
        with self.assertRaises(SystemExit) as stop:exec(compile(ast.Module(body=[top],type_ignores=[]),'top_only','exec'),namespace)
        self.assertEqual(stop.exception.code,1)

    def test_fixed_parent_failure_has_no_chained_exception_or_argument_text(self):
        for problem in (ValueError(SECRET),entry.ChildRunFailed('timeout'),entry.ChildRunFailed(SECRET)):
            stderr=io.StringIO()
            with patch.object(entry,'parent',side_effect=problem),contextlib.redirect_stderr(stderr):
                code=entry.main(['--manifest-sha256','a'*64])
            self.assertEqual(code,1);self.assertNotIn(SECRET,stderr.getvalue());self.assertNotIn('Traceback',stderr.getvalue())
            self.assertLessEqual(len(stderr.getvalue().encode()),4096)
        stderr=io.StringIO()
        with contextlib.redirect_stderr(stderr):self.assertEqual(entry.main(['--unknown',SECRET]),1)
        self.assertNotIn(SECRET,stderr.getvalue())

    def test_all_child_stage_failures_are_fixed_private_rows(self):
        for stage in ('package_setup','module_import','unit_call','serialization_output'):
            stderr=io.StringIO();stdout=io.StringIO()
            raw='{"value":NaN}' if stage=='serialization_output' else '{"inert":true}'
            with child_doubles(entry,stage,raw),contextlib.redirect_stderr(stderr),contextlib.redirect_stdout(stdout):
                code=entry.child(1000,300.,'a'*64)
            self.assertEqual(code,1);self.assertEqual(stdout.getvalue(),'')
            lines=stderr.getvalue().splitlines();self.assertEqual(len(lines),1)
            value=json.loads(lines[0]);self.assertEqual(value['stage'],stage)
            self.assertNotIn(SECRET,stderr.getvalue());self.assertNotIn('Traceback',stderr.getvalue())
            if stage=='unit_call':self.assertIn(dict(file='s2_numerics_unit.py',line=2),value['locations'])

    def test_success_child_json_artifact_bytes_and_timing_match_original(self):
        outputs=[]
        for subject in (old_entry(),entry):
            stdout=io.StringIO();stderr=io.StringIO()
            with child_doubles(subject),contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                subject.child(1000,300.,'a'*64)
            outputs.append(stdout.getvalue());self.assertEqual(stderr.getvalue(),'')
        self.assertEqual(outputs[0],outputs[1])


class ProcessCustody(unittest.TestCase):
    def run_double(self,folder,raw=None,code=1,timeout=False,unreaped=False,stdout=b'UNREAD_'+SECRET.encode()):
        events=[];process=FakeProcess(events,code,timeout,unreaped);calls=[]
        def create(argv,**kwargs):
            calls.append(argv);kwargs['stdout'].write(stdout)
            kwargs['stderr'].write(json.dumps(row()).encode() if raw is None else raw)
            return process
        return events,process,calls,create

    def test_failed_stdout_never_read_reap_precedes_fixed_stderr_and_parent_row_bounded(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as directory:
            folder=Path(directory);events,process,calls,create=self.run_double(folder)
            original=Path.read_bytes;original_open=Path.open
            def read(path):
                if path.name=='cost-1000.stdout':raise AssertionError('failure stdout content forbidden')
                return original(path)
            def open_file(path,*args,**kwargs):
                if path.name=='cost-1000.stderr' and args and args[0]=='rb':
                    self.assertIn('wait',events);self.assertIn('poll',events);events.append('detail-read')
                return original_open(path,*args,**kwargs)
            stderr=io.StringIO()
            with patch.object(entry.subprocess,'Popen',side_effect=create),patch.object(Path,'read_bytes',read),\
                    patch.object(Path,'open',open_file),contextlib.redirect_stderr(stderr):
                with self.assertRaises(entry.ChildRunFailed) as failure:entry.run_child(1000,300.,'a'*64,folder)
            self.assertEqual(failure.exception.reason,'nonzero');self.assertEqual(len(calls),1)
            lines=stderr.getvalue().splitlines();self.assertEqual(len(lines),2)
            summary=json.loads(lines[1]);self.assertEqual(summary['detail']['status'],'available')
            self.assertLessEqual(len((lines[1]+'\n').encode()),4096)
            self.assertLess(len(stderr.getvalue().encode()),65536);self.assertNotIn(SECRET,stderr.getvalue())

    def test_timeout_unreaped_and_read_sink_failures_preserve_original_classification(self):
        for timeout,unreaped,reason in ((True,False,'timeout'),(True,True,'unreaped'),(False,False,'nonzero')):
            with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as directory:
                folder=Path(directory);events,process,calls,create=self.run_double(folder,timeout=timeout,unreaped=unreaped)
                sink=SimpleNamespace(write=lambda value:(_ for _ in ()).throw(OSError(SECRET)),flush=lambda:None)
                original_open=Path.open
                def open_file(path,*args,**kwargs):
                    if args and args[0]=='rb':raise OSError(SECRET)
                    return original_open(path,*args,**kwargs)
                with patch.object(entry.subprocess,'Popen',side_effect=create),patch.object(Path,'open',open_file),\
                        patch.object(entry.sys,'stderr',sink):
                    with self.assertRaises(entry.ChildRunFailed) as failure:entry.run_child(1000,300.,'a'*64,folder)
                self.assertEqual(failure.exception.reason,reason);self.assertEqual(len(calls),1)
                if timeout:self.assertIn('kill',events)

    def test_failure_detail_invalid_or_unavailable_never_replaces_nonzero_or_leaks_raw(self):
        for raw in (b'',SECRET.encode(),b'x'*65537,b'{"kind":1,"kind":2}'):
            with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as directory:
                folder=Path(directory);_,_,calls,create=self.run_double(folder,raw=raw);stderr=io.StringIO()
                with patch.object(entry.subprocess,'Popen',side_effect=create),contextlib.redirect_stderr(stderr):
                    with self.assertRaises(entry.ChildRunFailed) as failure:entry.run_child(1000,300.,'a'*64,folder)
                self.assertEqual(failure.exception.reason,'nonzero');self.assertEqual(len(calls),1)
                self.assertEqual(json.loads(stderr.getvalue().splitlines()[1])['detail']['status'],'unavailable')
                self.assertNotIn(SECRET,stderr.getvalue());self.assertNotIn('x'*100,stderr.getvalue())

    def test_first_child_failure_prevents_second_fixed_child(self):
        class Resource:
            RUSAGE_SELF=0
        fake_resource=Resource();calls=[]
        def fail(draws,*args):calls.append(draws);raise entry.ChildRunFailed('nonzero')
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as directory:
            original_path=entry.Path
            def path(value):
                return original_path(directory)/'fixed-parent' if value=='/tmp/s2-numerics-fixed' else original_path(value)
            with patch.dict(sys.modules,resource=fake_resource),patch.object(entry,'checked_sources'),\
                    patch.object(entry,'Path',side_effect=path),patch.object(entry,'run_child',side_effect=fail):
                with self.assertRaises(entry.ChildRunFailed):entry.parent('a'*64)
        self.assertEqual(calls,[1000])

    def test_success_result_json_artifact_argv_and_clock_are_identical_to_old_entry(self):
        # Pure process/capture bytes; no actual NumPy/NPZ/scientific parsing.
        # Materialized by the guarded runner before native calls are blocked.
        previous=old_entry()
        value=dict(draws=1000,kind='S2-NUMERICS-STRUCTURAL-ONLY',import_finished_monotonic=12.,
                   artifact=dict(name='structural-1000.npz',base64='VU5JVA=='))
        results=[];receipts=[];arglists=[]
        for subject in (previous,entry):
            with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as directory:
                folder=Path(directory);_,_,calls,create=self.run_double(folder,raw=b'',code=0,stdout=json.dumps(value).encode())
                stderr=io.StringIO()
                with patch.object(subject.subprocess,'Popen',side_effect=create),\
                        patch.object(subject.time,'monotonic',side_effect=[10.,13.,14.]),contextlib.redirect_stderr(stderr):
                    results.append(subject.run_child(1000,300.,'a'*64,folder))
                receipts.append(stderr.getvalue());arglists.append(calls)
        self.assertEqual(results[0],results[1]);self.assertEqual(receipts[0],receipts[1]);self.assertEqual(arglists[0],arglists[1])


if __name__=='__main__':unittest.main()
