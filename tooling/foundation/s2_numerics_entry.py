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
    checked_sources(digest)
    if draws not in (1000,2000) or not 0<budget<=300:raise ValueError('fixed child budget/size required')
    started=time.monotonic()
    # Two literal *new* submodule names are absent from accepted dependency84.
    # Extend those existing packages only to this exact hash-bound RO directory.
    # No replacement of an inherited module or methods.nof1 observation code.
    sys.path.insert(0,'/app');sys.path.insert(1,str(ROOT))
    import contracts.domain
    import methods.support
    if (Path('/app/contracts/domain/support_s2.py').exists()
            or Path('/app/methods/support/s2_prediction.py').exists()):
        raise ValueError('new S2 module unexpectedly present in old dependency')
    contracts.domain.__path__.append(str(ROOT));methods.support.__path__.append(str(ROOT))
    import s2_numerics_unit
    imports=time.monotonic()-started
    import_finished=time.monotonic()
    remaining=budget-imports
    if remaining<=0:raise TimeoutError('child import exhausted work lease')
    output=json.loads(s2_numerics_unit.main(draws,remaining))
    output['fresh_python_module_import_seconds']=imports
    output['import_finished_monotonic']=import_finished
    output['child_total_seconds']=time.monotonic()-started
    raw=json.dumps(output,separators=(',',':'),allow_nan=False)
    if len(raw.encode())+1>CHILD_OUTPUT:raise ValueError('child output ceiling exceeded')
    print(raw)


def run_child(draws,budget,digest,folder):
    """Exact owned internal child, fixed argv; no relaunch on any failure."""
    argv=[sys.executable,'-I','-B','/qualification/entry.py','--child',str(draws),
          '--budget',str(budget),'--manifest-sha256',digest]
    output=folder/f'cost-{draws}.stdout';error=folder/f'cost-{draws}.stderr'
    started=time.monotonic();process=None;returncode=None;timed_out=False
    try:
        with output.open('xb') as out,error.open('xb') as err:
            process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
            returncode=process.wait(timeout=max(.001,budget-3))
    except subprocess.TimeoutExpired:timed_out=True
    finally:
        try:
            if process is not None and process.poll() is None:
                process.kill();returncode=process.wait(timeout=3)
            elif process is not None:returncode=process.poll()
        finally:
            print(json.dumps(dict(kind='fixed-internal-child-receipt',draws=draws,
                pid=None if process is None else process.pid,returncode=returncode,
                reaped=returncode is not None,timed_out=timed_out,
                elapsed_seconds=time.monotonic()-started)),file=sys.stderr,flush=True)
    if process is None or returncode is None:raise RuntimeError('owned internal child reap unconfirmed')
    raw=output.read_bytes() if output.stat().st_size<=CHILD_OUTPUT else b''
    if timed_out or returncode!=0 or not raw or error.stat().st_size>65536:
        raise RuntimeError('fixed internal cost child failed/late/overflow')
    result=json.loads(raw)
    if result['draws']!=draws or result['kind']!='S2-NUMERICS-STRUCTURAL-ONLY':
        raise ValueError('child output identity changed')
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


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--child',type=int,choices=(1000,2000));parser.add_argument('--budget',type=float)
    args=parser.parse_args()
    if args.child is None:
        if args.budget is not None:parser.error('budget only for fixed internal child')
        parent(args.manifest_sha256)
    else:
        if args.budget is None:parser.error('fixed child budget required')
        child(args.child,args.budget,args.manifest_sha256)
