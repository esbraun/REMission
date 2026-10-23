"""Fixed public RO carrier/stdlib parent SOURCE; learner operation only.

One container, two sequential fixed children. Never execute/import science on
the host. No generic module registry, source download or old image mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('/qualification')
PAYLOAD_FILES={'entry.py','support_s2.py','s2_prediction.py','s2_numerics_oracle.py',
               's2_numerics_unit.py','fixed.json','held-out.json','supplemental-blind.json','dependency.json'}
CHILD_OUTPUT=12*1024*1024
PARENT_OUTPUT=24*1024*1024
STAGES=('source_check','package_setup','module_import','unit_call','serialization_output')
ERROR_CLASSES={ValueError:'ValueError',TypeError:'TypeError',KeyError:'KeyError',
    AttributeError:'AttributeError',ImportError:'ImportError',ModuleNotFoundError:'ModuleNotFoundError',
    RuntimeError:'RuntimeError',TimeoutError:'TimeoutError',OSError:'OSError',MemoryError:'MemoryError'}
LOCATIONS={'/qualification/'+name:name for name in (
    'entry.py','support_s2.py','s2_prediction.py','s2_numerics_oracle.py','s2_numerics_unit.py')}
REASONS=('unreaped','timeout','launch_failed','process_failed','nonzero',
         'stdout_empty','stdout_overflow','stderr_overflow','capture_metadata_failed','output_invalid')


class ChildRunFailed(RuntimeError):
    def __init__(self,reason):
        super().__init__()
        self.reason=reason


def emit_failure_safe(row):
    """Fixed rows only; a diagnostic sink must never replace custody/failure."""
    try:
        raw=json.dumps(row,allow_nan=False)+'\n'
        if len(raw.encode('utf-8'))>4096:return False
        sys.stderr.write(raw);sys.stderr.flush()
        return True
    except BaseException:return False


def child_failure(error,stage,draws):
    locations=[];omitted=False;trace=error.__traceback__
    while trace is not None:
        if len(locations)==8:omitted=True;break
        name=LOCATIONS.get(trace.tb_frame.f_code.co_filename)
        line=trace.tb_lineno
        if name is not None and type(line) is int and 1<=line<=100000:
            locations.append(dict(file=name,line=line))
        else:omitted=True
        trace=trace.tb_next
    return dict(kind='s2-child-failure-v1',draws=draws,stage=stage,
        error_class=ERROR_CLASSES.get(type(error),'other'),locations=locations,omitted=omitted)


def read_child_failure(path,draws):
    def unavailable(code):return dict(status='unavailable',code=code)
    try:
        with path.open('rb') as stream:raw=stream.read(65537)
    except BaseException:return unavailable('read_failed')
    if len(raw)>65536:return unavailable('oversized')
    if not raw.strip():return unavailable('missing')
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError()
            value[key]=item
        return value
    try:
        value=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
            parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
        if (type(value) is not dict or set(value)!={'kind','draws','stage','error_class','locations','omitted'}
                or value['kind']!='s2-child-failure-v1' or type(value['draws']) is not int or value['draws']!=draws
                or value['stage'] not in STAGES or value['error_class'] not in (*ERROR_CLASSES.values(),'other')
                or type(value['omitted']) is not bool or type(value['locations']) is not list or len(value['locations'])>8):
            return unavailable('invalid')
        for location in value['locations']:
            if (type(location) is not dict or set(location)!={'file','line'}
                    or location['file'] not in LOCATIONS.values() or type(location['line']) is not int
                    or not 1<=location['line']<=100000):return unavailable('invalid')
        return dict(status='available',failure=value)
    except BaseException:return unavailable('invalid')


def checked_sources(digest,root=ROOT,app=Path('/app')):
    manifest=(root/'manifest.json').read_bytes()
    if hashlib.sha256(manifest).hexdigest()!=digest:raise ValueError('exact S2 manifest hash required')
    value=json.loads(manifest)
    if value['kind']!='S2-fixed-public-carrier-v1' or set(value['files'])!=PAYLOAD_FILES:
        raise ValueError('fixed S2 public carrier inventory required')
    paths=list(root.iterdir())
    if {p.name for p in paths}!=PAYLOAD_FILES|{'manifest.json'}:
        raise ValueError('extra or missing public carrier path')
    for p in paths:
        if p.is_symlink() or not p.is_file():raise ValueError('ordinary literal source files required')
    for name,row in value['files'].items():
        data=(root/name).read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('public carrier byte mismatch: '+name)
    dependency=json.loads((root/'dependency.json').read_bytes())
    expected=dependency['qualified_project_source']
    if len(expected)!=84:raise ValueError('qualified dependency map84 required')
    actual=set()
    for p in app.rglob('*'):
        if p.is_symlink():raise ValueError('dependency symlink rejected')
        if p.is_file():actual.add('/app/'+p.relative_to(app).as_posix())
    if actual!=set(expected):raise ValueError('unchanged dependency full84 equality failed')
    # Only known expected public bytes are read/hashed, never unknown extras.
    for name,digest in expected.items():
        p=app/Path(name).relative_to('/app')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('dependency source hash mismatch')
    return value


def child(draws,budget,digest):
    stage='source_check'
    try:
        checked_sources(digest)
        if draws not in (1000,2000) or not 0<budget<=300:raise ValueError('fixed child budget/size required')
        started=time.monotonic()
        # Two literal *new* submodule names are absent from accepted dependency84.
        # Extend those existing packages only to this exact hash-bound RO directory.
        # No replacement of an inherited module or methods.nof1 observation code.
        stage='package_setup'
        sys.path.insert(0,'/app');sys.path.insert(1,str(ROOT))
        import contracts.domain
        import methods.support
        if (Path('/app/contracts/domain/support_s2.py').exists()
                or Path('/app/methods/support/s2_prediction.py').exists()):
            raise ValueError('new S2 module unexpectedly present in old dependency')
        contracts.domain.__path__.append(str(ROOT));methods.support.__path__.append(str(ROOT))
        stage='module_import'
        import s2_numerics_unit
        imports=time.monotonic()-started
        import_finished=time.monotonic()
        remaining=budget-imports
        if remaining<=0:raise TimeoutError('child import exhausted work lease')
        stage='unit_call'
        output=json.loads(s2_numerics_unit.main(draws,remaining))
        stage='serialization_output'
        output['fresh_python_module_import_seconds']=imports
        output['import_finished_monotonic']=import_finished
        output['child_total_seconds']=time.monotonic()-started
        raw=json.dumps(output,separators=(',',':'),allow_nan=False)
        if len(raw.encode())+1>CHILD_OUTPUT:raise ValueError('child output ceiling exceeded')
        print(raw)
        return 0
    except BaseException as error:
        # Fixed nonzero return suppresses Python's automatic raw traceback.
        try:row=child_failure(error,stage,draws)
        except BaseException:row=dict(kind='s2-child-failure-v1',draws=draws,
            stage=stage,error_class='other',locations=[],omitted=True)
        emit_failure_safe(row)
        return 1


def run_child(draws,budget,digest,folder):
    """Exact owned internal child, fixed argv; no relaunch on any failure."""
    argv=[sys.executable,'-I','-B','/qualification/entry.py','--child',str(draws),
          '--budget',str(budget),'--manifest-sha256',digest]
    output=folder/f'cost-{draws}.stdout';error=folder/f'cost-{draws}.stderr'
    started=time.monotonic();process=None;returncode=None;timed_out=False;process_failed=False
    try:
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
        finally:
            receipt=dict(kind='fixed-internal-child-receipt',draws=draws,
                pid=None if process is None else process.pid,returncode=returncode,
                reaped=returncode is not None,timed_out=timed_out,
                elapsed_seconds=time.monotonic()-started)
            emit_failure_safe(receipt)
    reason=('launch_failed' if process is None else 'unreaped' if returncode is None
            else 'timeout' if timed_out else 'process_failed' if process_failed
            else 'nonzero' if returncode!=0 else None)
    if reason is None:
        try:
            size=output.stat().st_size
            reason=('stdout_empty' if size==0 else 'stdout_overflow' if size>CHILD_OUTPUT
                    else 'stderr_overflow' if error.stat().st_size>65536 else None)
        except BaseException:reason='capture_metadata_failed'
    if reason is not None:
        detail=(dict(status='unavailable',code='unreaped') if reason=='unreaped'
                else read_child_failure(error,draws))
        emit_failure_safe(dict(kind='s2-parent-child-failure-v1',reason=reason,custody=receipt,detail=detail))
        raise ChildRunFailed(reason) from None
    try:
        raw=output.read_bytes();result=json.loads(raw)
        if result['draws']!=draws or result['kind']!='S2-NUMERICS-STRUCTURAL-ONLY':raise ValueError()
    except BaseException:
        emit_failure_safe(dict(kind='s2-parent-child-failure-v1',reason='output_invalid',custody=receipt,
                              detail=read_child_failure(error,draws)))
        raise ChildRunFailed('output_invalid') from None
    return dict(pid=process.pid,returncode=returncode,reaped=True,timed_out=False,
                elapsed_seconds=time.monotonic()-started,
                fresh_python_startup_through_import_seconds=result['import_finished_monotonic']-started,
                argv=argv,result=result)


def parent(digest):
    import resource
    checked_sources(digest);started=time.monotonic()
    folder=Path('/tmp/s2-numerics-fixed');folder.mkdir(exist_ok=False)
    runs=[]
    for draws in (1000,2000):
        remaining=570-(time.monotonic()-started)
        if remaining<=3:raise TimeoutError('fixed parent work lease exhausted')
        runs.append(run_child(draws,min(300.,remaining),digest,folder))
    result=dict(kind='S2-NUMERICS-STRUCTURAL-ONLY',runs=runs,
        cold_definition='fresh Python/module startup; observed OS/image caches retained',
        parent_seconds=time.monotonic()-started,model_fitted=False,genuine_data=False,
        parent_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        serving_authority=False,scientific_parent_imports=False)
    raw=json.dumps(result,separators=(',',':'),allow_nan=False)
    if len(raw.encode())+1>PARENT_OUTPUT:raise ValueError('complete parent JSON ceiling exceeded')
    print(raw)


def main(argv=None):
    try:
        parser=argparse.ArgumentParser(add_help=False,exit_on_error=False)
        parser.add_argument('--manifest-sha256');parser.add_argument('--child',type=int,choices=(1000,2000))
        parser.add_argument('--budget',type=float);args,extra=parser.parse_known_args(argv)
        if extra or args.manifest_sha256 is None:raise ValueError()
        if args.child is None:
            if args.budget is not None:raise ValueError()
            parent(args.manifest_sha256);return 0
        if args.budget is None:raise ValueError()
        return child(args.child,args.budget,args.manifest_sha256)
    except BaseException as error:
        reason=error.reason if type(error) is ChildRunFailed and error.reason in REASONS else 'entry_failed'
        emit_failure_safe(dict(kind='s2-entry-failed-v1',reason=reason))
        return 1


if __name__=='__main__':raise SystemExit(main())
