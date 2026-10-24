"""Fixed graph-only learner carrier. Never import/execute on the host.

One stdlib parent, one owned bounded child. No sampler, activation, or Store.
"""
import argparse
import hashlib
import importlib
import importlib.util
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

ROOT=Path('/qualification')
STAGED=Path('/tmp/s2-graph-packages')
MODULES={
    'contracts.domain.support_s2':'contracts/domain/support_s2.py',
    'contracts.domain.support_s2_fit':'contracts/domain/support_s2_fit.py',
    'methods.support.s2_data':'methods/support/s2_data.py',
    'methods.support.s2_model':'methods/support/s2_model.py',
    'tooling.foundation.s2_model_qualification':'tooling/foundation/s2_model_qualification.py',
    'tooling.foundation.pa3_monitor':'tooling/foundation/pa3_monitor.py',
    's2_model_fixtures':'s2_model_fixtures.py'}
PAYLOAD_FILES={'entry.py','dependency.json','settings.json','resources.json',
               'tooling/foundation/pa3-cvm-policy.json',*MODULES.values()}
CHILD_OUTPUT=2*1024*1024
PARENT_OUTPUT=3*1024*1024
STAGES=('source_check','construction_policy','package_setup','module_import','fixtures','admission','shape',
        'graph','compile','density','gradient','serialization','serialization_output')
ERROR_CLASSES={ValueError:'ValueError',TypeError:'TypeError',KeyError:'KeyError',
    AttributeError:'AttributeError',ImportError:'ImportError',ModuleNotFoundError:'ModuleNotFoundError',
    RuntimeError:'RuntimeError',TimeoutError:'TimeoutError',OSError:'OSError',MemoryError:'MemoryError',
    AssertionError:'AssertionError',PermissionError:'PermissionError'}
LOCATIONS={'/qualification/entry.py':'entry.py'}
LOCATIONS.update({str(STAGED/name):name for name in MODULES.values()})
REASONS=('launch_failed','unreaped','timeout','process_failed','nonzero','stdout_empty',
         'stdout_overflow','stderr_overflow','capture_metadata_failed','output_invalid')
PRIOR_INPUT_RVS=('mu_alpha','mu_tau','b','s_alpha','s_tau','s_e','s_Q','rho','z','u','epsilon_0','epsilon_1')
PRIOR_INPUT_DTYPES=('float16','float32','float64','float128')
PRIOR_INPUT_MAX_ORDINAL=7
CONSTRUCTION_FLAGS='base_compiledir=/tmp/pytensor,floatX=float64,cast_policy=numpy+floatX'
CONSTRUCTION_POLICY=dict(floatX='float64',cast_policy='numpy+floatX',pymc_version='6.3.2',pytensor_version='3.3.4')
FAILURE_PATH=Path('/tmp/s2-graph-parent/graph.failure.json')
FAILURE_BYTES=4096


def require_construction_policy(environ,bound):
    if (bound!=CONSTRUCTION_POLICY or environ.get('PYTENSOR_FLAGS')!=CONSTRUCTION_FLAGS
            or environ.get('PYTENSORRC') not in (None,'')):
        raise ValueError('fixed isolated construction policy required before imports')


def checked_prior_input(value):
    if type(value) is not dict:raise ValueError('invalid finite prior-input metadata')
    if value.get('status')=='unavailable':
        if set(value)!={'status','code'} or value['code'] not in ('refused','classification_failed'):
            raise ValueError('invalid fixed prior-input refusal')
    elif (set(value)!={'status','rv','input_ordinal','dtype','is_constant'} or value['status']!='available'
            or type(value['rv']) is not str or value['rv'] not in PRIOR_INPUT_RVS
            or type(value['input_ordinal']) is not int or not 0<=value['input_ordinal']<=PRIOR_INPUT_MAX_ORDINAL
            or type(value['dtype']) is not str or value['dtype'] not in PRIOR_INPUT_DTYPES
            or type(value['is_constant']) is not bool):
        raise ValueError('invalid finite prior-input metadata')
    return value


def attach_prior_input(row,value):
    if value is not None:
        try:row['prior_input']=checked_prior_input(value)
        except BaseException:row['prior_input']=dict(status='unavailable',code='refused')
    return row


def strict_json(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('duplicate JSON key')
            value[key]=item
        return value
    def finite(value):
        result=float(value)
        if not math.isfinite(result):raise ValueError('nonfinite JSON number')
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_float=finite,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))


def emit(row):
    try:
        raw=json.dumps(row,separators=(',',':'),allow_nan=False)+'\n'
        if len(raw.encode())>4096:return False
        sys.stderr.write(raw);sys.stderr.flush();return True
    except BaseException:return False


def failure(error,stage):
    locations=[];omitted=False;trace=error.__traceback__
    while trace is not None:
        if len(locations)==8:omitted=True;break
        name=LOCATIONS.get(trace.tb_frame.f_code.co_filename)
        if name is not None and type(trace.tb_lineno) is int and 1<=trace.tb_lineno<=100000:
            locations.append(dict(file=name,line=trace.tb_lineno))
        else:omitted=True
        trace=trace.tb_next
    return dict(kind='s2-graph-child-failure-v1',stage=stage,
        error_class=ERROR_CLASSES.get(type(error),'other'),locations=locations,omitted=omitted)


def checked_receipt_fd(fd,identity=None,*,empty=False):
    value=os.fstat(fd)
    current=(value.st_dev,value.st_ino,value.st_uid)
    if (not stat.S_ISREG(value.st_mode) or value.st_uid!=os.geteuid()
            or stat.S_IMODE(value.st_mode)!=0o600 or (empty and value.st_size!=0)
            or (identity is not None and current!=identity)):
        raise ValueError('fixed receipt descriptor refused')
    return current


def reserve_failure(path):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:return checked_receipt_fd(fd,empty=True)
    finally:os.close(fd)


def write_failure(row,identity):
    fd=None
    try:
        raw=(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n').encode()
        if len(raw)>FAILURE_BYTES:return False
        fd=os.open(FAILURE_PATH,os.O_WRONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        checked_receipt_fd(fd,identity,empty=True)
        return os.write(fd,raw)==len(raw)
    except BaseException:return False
    finally:
        if fd is not None:
            try:os.close(fd)
            except BaseException:pass


def read_failure(path,identity):
    def unavailable(code):return dict(status='unavailable',code=code)
    fd=None
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        checked_receipt_fd(fd,identity)
        with os.fdopen(fd,'rb') as stream:
            fd=None;raw=stream.read(FAILURE_BYTES+1)
    except BaseException:return unavailable('read_failed')
    finally:
        if fd is not None:
            try:os.close(fd)
            except BaseException:pass
    if len(raw)>FAILURE_BYTES:return unavailable('oversized')
    if not raw.strip():return unavailable('missing')
    try:value=strict_json(raw)
    except BaseException:return unavailable('invalid_json')
    try:
        if (type(value) is not dict or set(value) not in ({'kind','stage','error_class','locations','omitted'},
                {'kind','stage','error_class','locations','omitted','prior_input'})
                or value['kind']!='s2-graph-child-failure-v1' or value['stage'] not in STAGES
                or value['error_class'] not in (*ERROR_CLASSES.values(),'other')
                or type(value['omitted']) is not bool or type(value['locations']) is not list
                or len(value['locations'])>8):raise ValueError()
        for location in value['locations']:
            if (type(location) is not dict or set(location)!={'file','line'}
                    or location['file'] not in LOCATIONS.values() or type(location['line']) is not int
                    or not 1<=location['line']<=100000):raise ValueError()
        if 'prior_input' in value:
            if value['stage']!='graph' or value['error_class']!='AssertionError':raise ValueError()
            checked_prior_input(value['prior_input'])
        return dict(status='available',failure=value)
    except BaseException:return unavailable('invalid_schema')


def emit_parent_failure(reason,custody,detail):
    row=dict(kind='s2-graph-parent-failure-v1',reason=reason,custody=custody,detail=detail)
    try:
        if len((json.dumps(row,separators=(',',':'),allow_nan=False)+'\n').encode())>FAILURE_BYTES:
            row['detail']=dict(status='unavailable',code='outer_oversized')
    except BaseException:row['detail']=dict(status='unavailable',code='outer_invalid')
    return emit(row)


def checked_sources(digest,root=ROOT,app=Path('/app')):
    manifest=(root/'manifest.json').read_bytes()
    if hashlib.sha256(manifest).hexdigest()!=digest:raise ValueError('graph manifest mismatch')
    value=strict_json(manifest)
    if value['kind']!='S2-fixed-graph-carrier-v1' or set(value['files'])!=PAYLOAD_FILES:
        raise ValueError('fixed graph carrier required')
    actual=set()
    for path in root.rglob('*'):
        if path.is_symlink():raise ValueError('carrier symlink rejected')
        if path.is_file():actual.add(path.relative_to(root).as_posix())
        elif not path.is_dir():raise ValueError('nonregular carrier rejected')
    if actual!=PAYLOAD_FILES|{'manifest.json'}:raise ValueError('carrier inventory mismatch')
    for name,row in value['files'].items():
        raw=(root/name).read_bytes()
        if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('known public carrier bytes changed')
    expected=strict_json((root/'dependency.json').read_bytes())['qualified_project_source']
    if len(expected)!=84:raise ValueError('qualified dependency84 required')
    actual=set()
    for path in app.rglob('*'):
        if path.is_symlink():raise ValueError('dependency symlink rejected')
        if path.is_file():actual.add('/app/'+path.relative_to(app).as_posix())
        elif not path.is_dir():raise ValueError('nonregular dependency rejected')
    if actual!=set(expected):raise ValueError('complete dependency84 equality required')
    for name,digest in expected.items():
        if hashlib.sha256((app/Path(name).relative_to('/app')).read_bytes()).hexdigest()!=digest:
            raise ValueError('known dependency public source mismatch')
    return value


def package_setup(root=ROOT,staged=STAGED):
    # Fixed new modules only; installed dependency files are never overwritten.
    staged.mkdir(exist_ok=False)
    for name in (*MODULES.values(),'tooling/foundation/pa3-cvm-policy.json'):
        target=staged/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write((root/name).read_bytes())
    sys.path[:0]=[str(staged),'/app']
    # Existing regular packages retain their original __init__. Namespace
    # packages get an explicit fixed path list; no dynamic loader or alias.
    for name in ('contracts','contracts.domain','methods','methods.support','tooling','tooling.foundation'):
        module=importlib.import_module(name)
        suffix=name.replace('.','/')
        origin=module.__spec__.origin
        if origin not in (None,'/app/'+suffix+'/__init__.py'):
            raise ValueError('package origin mismatch')
        allowed={str(staged/suffix),'/app/'+suffix}
        if any(str(path) not in allowed for path in module.__path__):raise ValueError('foreign package path')
        module.__path__=[str(staged/suffix),'/app/'+suffix]
    for name,path in MODULES.items():
        if name in sys.modules:raise ValueError('new graph module loaded before precedence proof')
        spec=importlib.util.find_spec(name)
        if spec is None or spec.origin!=str(staged/path):raise ValueError('graph module precedence mismatch')


def child(budget,digest,receipt_identity):
    stage='source_check';qualification=None;started=time.monotonic()
    try:
        if type(budget) is not float or not 0<budget<=1080:raise ValueError('fixed graph child budget')
        stage='construction_policy'
        settings=strict_json((ROOT/'settings.json').read_bytes())
        require_construction_policy(os.environ,settings.pop('construction_policy'))
        installed=dict(pymc_version=version('pymc'),pytensor_version=version('pytensor'))
        if installed!={key:CONSTRUCTION_POLICY[key] for key in installed}:raise ValueError('pinned installed metadata conflict')
        stage='source_check'
        checked_sources(digest);stage='package_setup';package_setup()
        threads={name:os.environ.get(name) for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}
        if any(value!='1' for value in threads.values()):raise ValueError('fixed single-thread environment required before science import')
        stage='module_import'
        from tooling.foundation import s2_model_qualification as qualification
        import pytensor
        qualification.require_actual_policy(pytensor.config)
        from tooling.foundation.pa3_monitor import compilation_options
        from methods.support.s2_data import prepare
        from s2_model_fixtures import cohort,provenance
        settings['steps']=tuple(settings['steps'])
        qualification.require_admitted(settings)
        policy=strict_json((STAGED/'tooling/foundation/pa3-cvm-policy.json').read_bytes())
        options,compiler_policy=compilation_options(policy)
        stage='fixtures'
        first=cohort(14);second=cohort(28)
        data14=prepare(first,provenance(first));data28=prepare(second,provenance(second))
        if time.monotonic()-started>=budget:raise TimeoutError()
        stage='admission'
        report=qualification.qualify(data14,data28,settings=settings,compile_options=options)
        stage='serialization_output'
        report['compiler_policy']=compiler_policy;report['thread_environment']=threads
        report['child_seconds']=time.monotonic()-started
        raw=json.dumps(report,separators=(',',':'),allow_nan=False)+'\n'
        if len(raw.encode())>CHILD_OUTPUT:raise ValueError('graph child output ceiling')
        sys.stdout.write(raw);return 0
    except BaseException as error:
        if qualification is not None and qualification.STAGE in STAGES and stage=='admission':
            stage=qualification.STAGE
        try:row=failure(error,stage)
        except BaseException:row=dict(kind='s2-graph-child-failure-v1',stage=stage,error_class='other',locations=[],omitted=True)
        if qualification is not None and stage=='graph' and type(error) is AssertionError:
            try:attach_prior_input(row,qualification.PRIOR_INPUT_FAILURE)
            except BaseException:row['prior_input']=dict(status='unavailable',code='classification_failed')
        write_failure(row,receipt_identity);return 1  # Never leak an automatic chained/raw traceback.


class ChildFailed(RuntimeError):
    def __init__(self,reason):super().__init__();self.reason=reason


def run_child(budget,digest,folder):
    argv=[sys.executable,'-I','-B','/qualification/entry.py','--child','--budget',str(budget),'--manifest-sha256',digest]
    output=folder/'graph.stdout';error=folder/'graph.stderr'
    failure_path=folder/FAILURE_PATH.name;identity=None
    started=time.monotonic();process=None;returncode=None;timed_out=False;process_failed=False
    try:
        identity=reserve_failure(failure_path)
        argv+=['--failure-identity',':'.join(str(value) for value in identity)]
        with output.open('xb') as out,error.open('xb') as err:
            process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
            returncode=process.wait(timeout=max(.001,budget-3))
    except subprocess.TimeoutExpired:timed_out=True
    except BaseException:process_failed=True
    finally:
        try:
            if process is not None and process.poll() is None:
                process.kill();returncode=process.wait(timeout=3)
            elif process is not None:returncode=process.poll()
        except BaseException:process_failed=True
        receipt=dict(kind='s2-graph-internal-child-custody',pid=None if process is None else process.pid,
            returncode=returncode,reaped=returncode is not None,timed_out=timed_out,
            elapsed_seconds=time.monotonic()-started)
        emit(receipt)
    reason=('launch_failed' if process is None else 'unreaped' if returncode is None else 'timeout' if timed_out
            else 'process_failed' if process_failed else 'nonzero' if returncode!=0 else None)
    if reason is None:
        try:
            size=output.stat().st_size
            reason=('stdout_empty' if size==0 else 'stdout_overflow' if size>CHILD_OUTPUT
                    else 'stderr_overflow' if error.stat().st_size>65536 else None)
        except BaseException:reason='capture_metadata_failed'
    if reason is not None:
        detail=(dict(status='unavailable',code='unreaped') if returncode is None
                else read_failure(failure_path,identity))
        emit_parent_failure(reason,receipt,detail)
        raise ChildFailed(reason) from None  # Failed stdout content is unread.
    try:
        result=strict_json(output.read_bytes())
        if result['kind']!='S2-ORIGINAL-COORDINATE-DENSITY-GRADIENT-STRUCTURAL-ONLY':raise ValueError()
    except BaseException:
        emit_parent_failure('output_invalid',receipt,read_failure(failure_path,identity))
        raise ChildFailed('output_invalid') from None
    return dict(custody=receipt,argv=argv,result=result)


def parent(digest,budget):
    started=time.monotonic()
    if type(budget) is not float or not 30<budget<=1080:raise ValueError('fixed relative parent budget')
    checked_sources(digest)
    folder=Path('/tmp/s2-graph-parent');folder.mkdir(exist_ok=False)
    remaining=budget-(time.monotonic()-started)-30
    if remaining<=3:raise TimeoutError()
    run=run_child(min(1080.,remaining),digest,folder)
    value=dict(kind='S2-GRAPH-STRUCTURAL-ONLY',run=run,parent_seconds=time.monotonic()-started,
        scientific_parent_imports=False,model_fitted=False,genuine_data=False,serving_authority=False)
    raw=json.dumps(value,separators=(',',':'),allow_nan=False)+'\n'
    if len(raw.encode())>PARENT_OUTPUT:raise ValueError('graph parent output ceiling')
    sys.stdout.write(raw)


def main(argv=None):
    try:
        parser=argparse.ArgumentParser(add_help=False,exit_on_error=False)
        parser.add_argument('--manifest-sha256');parser.add_argument('--budget',type=float)
        parser.add_argument('--failure-identity')
        parser.add_argument('--child',action='store_true');args,extra=parser.parse_known_args(argv)
        if extra or args.manifest_sha256 is None or args.budget is None:raise ValueError()
        if args.child:
            parts=[] if args.failure_identity is None else args.failure_identity.split(':')
            if (len(parts)!=3 or any(not value.isascii() or not value.isdecimal()
                    or len(value)>20 or str(int(value))!=value or int(value)>2**64-1 for value in parts)):
                raise ValueError()
            return child(args.budget,args.manifest_sha256,tuple(int(value) for value in parts))
        if args.failure_identity is not None:raise ValueError()
        parent(args.manifest_sha256,args.budget);return 0
    except BaseException as error:
        reason=error.reason if type(error) is ChildFailed and error.reason in REASONS else 'entry_failed'
        emit(dict(kind='s2-graph-entry-failed-v1',reason=reason));return 1


if __name__=='__main__':raise SystemExit(main())
