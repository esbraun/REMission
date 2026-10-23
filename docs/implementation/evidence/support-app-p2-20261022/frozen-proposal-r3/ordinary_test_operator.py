"""Freeze or run one explicitly reviewed Linux ordinary-test package.

No build, scientific imports, accepted mounts, live service or credentials.
Invocation: host Python -P -B this.py freeze|run.
"""
from contextlib import ExitStack
from datetime import datetime,timezone
import hashlib
import os
import re
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
STAGING=REPO/'artifacts/support-p2-ordinary-tests-r3'
IMAGE='sha256:146a84b1ff4306235bec2d15212350a7d58c94a3ea812b4d02c4e8318a4a3de0'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,obj):path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def now():return datetime.now(timezone.utc).isoformat()
STATE_FORMAT='{"Id":{{json .Id}},"State":{{json .State}}}'
def encode(value):return json.dumps(value,sort_keys=True,indent=2).encode()+b'\n'
def docker(*args,timeout=15):
    return subprocess.run(['docker',*args],capture_output=True,text=True,timeout=timeout,check=True).stdout.strip()


def attempt(argv,folder,label,timeout=20):
    record=dict(argv=argv,timeout_seconds=timeout,started_at=now())
    rawout=rawerr=b''
    try:
        result=subprocess.run(argv,capture_output=True,timeout=timeout)
        rawout,rawerr=result.stdout,result.stderr
        record['exit']=result.returncode
    except Exception as error:
        record['error']=repr(error)
        record['timed_out']=isinstance(error,subprocess.TimeoutExpired)
        if isinstance(error,subprocess.TimeoutExpired):rawout,rawerr=error.stdout or b'',error.stderr or b''
    rawout=rawout.encode() if isinstance(rawout,str) else rawout
    rawerr=rawerr.encode() if isinstance(rawerr,str) else rawerr
    record.update(stdout=rawout.decode(errors='replace'),stderr=rawerr.decode(errors='replace'),ended_at=now())
    (folder/(label+'.stdout')).write_bytes(rawout);(folder/(label+'.stderr')).write_bytes(rawerr)
    save(folder/(label+'.json'),record)
    return record
def require(record):
    if record.get('exit')!=0 or 'error' in record:raise RuntimeError('bounded command failed: '+repr(record))
    return record['stdout']
def literal_cid(text):
    cid=text.strip()
    if not re.fullmatch('[0-9a-f]{64}',cid):raise ValueError('invalid immutable CID; retain create evidence')
    return cid
def validate_state(value):
    if not isinstance(value,dict):raise ValueError('malformed State object')
    if type(value.get('Running')) is not bool or value.get('Status') not in ('created','running','paused','restarting','removing','exited','dead'):raise ValueError('malformed State status/running')
    if type(value.get('Pid')) is not int or value['Pid']<0 or type(value.get('ExitCode')) is not int or type(value.get('OOMKilled')) is not bool:raise ValueError('malformed State pid/exit/OOM')
    return value
def stopped(value):
    return value is not None and value['Status'] in ('exited','dead') and value['Running'] is False and value['Pid']==0
def state(cid,folder,label):
    value=json.loads(require(attempt(['docker','inspect','--format',STATE_FORMAT,cid],folder,label,3)))
    if not isinstance(value,dict) or value.get('Id')!=cid:raise ValueError('independent State exact-CID mismatch')
    return validate_state(value.get('State'))
def readiness(folder,cid,child,require_live=True):
    ready=json.loads((folder/'watchdog-ready.json').read_bytes())
    if not isinstance(ready,dict) or ready.get('cid')!=cid or type(ready.get('seconds')) is not int or ready['seconds']!=180 or type(ready.get('pid')) is not int or ready['pid']!=child.pid:raise ValueError('exact-CID watchdog readiness binding mismatch')
    if require_live and child.poll() is not None:raise RuntimeError('watchdog died after readiness')
    return ready
def terminal_receipt(folder,cid,observed=None):
    receipt=json.loads((folder/'watchdog-terminal.json').read_bytes())
    if not isinstance(receipt,dict) or receipt.get('cid')!=cid:raise ValueError('invalid exact-CID watchdog receipt')
    events=receipt.get('events')
    if not isinstance(events,list) or len(events)!=1 or not isinstance(events[0],dict) or set(events[0])!={'terminal'}:raise ValueError('invalid watchdog terminal events')
    terminal=validate_state(events[0]['terminal'])
    if not stopped(terminal):raise ValueError('watchdog lacks confirmed stopped terminal State')
    if observed is not None and any(terminal[field]!=observed[field] for field in ('Status','Running','Pid','ExitCode','OOMKilled')):raise ValueError('watchdog disagrees with independent State')
    return receipt
def reap(process,name,errors):
    if process is None:return None
    try:
        process.wait(timeout=20)
    except Exception as error:
        errors.append(dict(process=name,phase='wait',error=repr(error)))
        try:process.kill()
        except Exception as error:errors.append(dict(process=name,phase='kill',error=repr(error)))
        try:process.wait(timeout=5)
        except Exception as error:errors.append(dict(process=name,phase='reap',error=repr(error)))
    return process.returncode
def bounded(step,folder):
    folder.mkdir(exist_ok=False);save(folder/'command.json',step)
    created=attempt(step['argv'],folder,'create')
    cid=literal_cid(require(created));(folder/'cid.txt').write_text(cid)
    child=running=None;start_attempted=False;failure=None;final_state=None;cleanup=[];codes={}
    with ExitStack() as files:
        try:
            watchout=files.enter_context((folder/'watchdog.stdout').open('wb'));watcherr=files.enter_context((folder/'watchdog.stderr').open('wb'))
            out=files.enter_context((folder/'stdout').open('wb'));err=files.enter_context((folder/'stderr').open('wb'))
            tick=time.monotonic()
            watch_argv=[sys.executable,str(HERE/'ordinary_watchdog.py'),'--watchdog-cid',cid,'--evidence',str(folder),'--seconds','180']
            save(folder/'watchdog-command.json',dict(argv=watch_argv,readiness_timeout_seconds=10,container_seconds=180,started_at=now()))
            child=subprocess.Popen(watch_argv,stdout=watchout,stderr=watcherr,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            until=time.monotonic()+10
            while not (folder/'watchdog-ready.json').exists():
                if child.poll() is not None or time.monotonic()>until:raise RuntimeError('watchdog failed before start')
                time.sleep(.1)
            readiness(folder,cid,child)
            start_attempted=True
            save(folder/'attach-command.json',dict(argv=['docker','start','--attach',cid],parent_seconds=205,started_at=now()))
            running=subprocess.Popen(['docker','start','--attach',cid],stdout=out,stderr=err)
            while True:
                if time.monotonic()>tick+205:raise TimeoutError('bounded attach elapsed')
                watch_code=child.poll();attach_code=running.poll()
                if watch_code is not None:
                    readiness(folder,cid,child,False)
                    terminal_receipt(folder,cid)
                    current=state(cid,folder,'watchdog-first-state')
                    if watch_code or not stopped(current):raise RuntimeError('watchdog ended without independent stopped State')
                    if attach_code is None:running.wait(timeout=20)
                    break
                if attach_code is not None:
                    child.wait(timeout=20);readiness(folder,cid,child,False);terminal_receipt(folder,cid)
                    if child.returncode:raise RuntimeError('watchdog failed after attach')
                    break
                time.sleep(.1)
        except BaseException as error:failure=repr(error)
        finally:
            current=None
            try:current=state(cid,folder,'cleanup-before-state')
            except Exception as error:cleanup.append(dict(phase='inspect-before-stop',error=repr(error)))
            # Inspection failure never prevents bounded literal-CID stop or reaping.
            if start_attempted and (current is None or not stopped(current)):
                cleanup.append(dict(phase='stop',result=attempt(['docker','kill',cid],folder,'failure-stop',5)))
            try:final_state=state(cid,folder,'final-state')
            except Exception as error:cleanup.append(dict(phase='inspect-final',error=repr(error)))
            codes['attach']=reap(running,'attach',cleanup)
            codes['watchdog']=reap(child,'watchdog',cleanup)
            valid=False
            try:
                if child is None:raise RuntimeError('watchdog never launched')
                readiness(folder,cid,child,False)
                terminal_receipt(folder,cid,final_state);valid=True
            except Exception as error:
                cleanup.append(dict(phase='final-watchdog-validation',error=repr(error)))
                failure=failure or repr(error)
            confirmed=stopped(final_state)
            if not confirmed:failure=failure or 'STOP UNCONFIRMED; retain CID and cease work'
            if confirmed and (codes!=dict(attach=0,watchdog=0) or final_state['ExitCode']!=0 or final_state['OOMKilled']):failure=failure or 'nonzero process/container exit or OOM'
            accepted=(failure is None and not cleanup and confirmed and valid and codes==dict(attach=0,watchdog=0) and final_state['ExitCode']==0 and final_state['OOMKilled'] is False)
            save(folder/'outcome.json',dict(cid=cid,start_attempted=start_attempted,primary_error=failure,cleanup=cleanup,finalState=final_state,stop_confirmed=confirmed,stop_status='confirmed' if confirmed else 'STOP UNCONFIRMED',process_exit=codes,watchdog_terminal_valid=valid,success=accepted,retained=True))
    if not confirmed:raise RuntimeError('STOP UNCONFIRMED; retain CID and cease work; primary='+str(failure))
    if not accepted:raise RuntimeError('context step failed; retain evidence; no retry; primary='+str(failure))



def freeze():
    if STAGING.exists():raise ValueError('Use a fresh reviewed staging directory; do not replace frozen source')
    source=STAGING/'source';source.mkdir(parents=True)
    selected=sorted({p for folder in ('contracts','services/foundation') for p in (REPO/folder).rglob('*')
        if p.is_file() and p.suffix in ('.py','.json','.sql')})
    selected += [REPO/p for p in ('tests/integration/replay/test_support_archive.py','tests/integration/replay/support_archive_fixtures.py',
        'tests/integration/replay/test_foundation.py','tests/integration/replay/test_observed_v2_archive.py','tests/integration/replay/live_helpers.py',
        'tests/run_contracts/observed_v2_fixtures.py')]
    entries=[]
    for path in selected:
        relative=path.relative_to(REPO).as_posix();target=source/relative;target.parent.mkdir(parents=True,exist_ok=True)
        raw=path.read_bytes();target.write_bytes(raw);entries.append(dict(path=relative,bytes=len(raw),sha256=sha(raw)))
    runner=(HERE/'linux_tests.py').read_bytes();(source/'run_tests.py').write_bytes(runner)
    entries.append(dict(path='run_tests.py',bytes=len(runner),sha256=sha(runner)))
    manifest=encode(entries);(HERE/'ordinary-source-manifest.json').write_bytes(manifest)
    spec=dict(scope='ordinary isolated fixtures only; never accepted public archive/native volume/service/browser/science',
        image=IMAGE,image_provenance='Root identifies this immutable existing service image as accepted native-cohort day14 service; used for dependencies only. Candidate source is separately mounted and hashed.',
        source=str(source),source_manifest_sha256=sha(manifest),source_files=len(entries),source_bytes=sum(e['bytes'] for e in entries),
        argv=['python','-P','-B','/source/run_tests.py'],uid='10001:10001',cpus=2,memory='1g',memory_swap='1g',pids=128,
        network='none',read_only=True,cap_drop='ALL',no_new_privileges=True,tmpfs='/tmp:rw,nosuid,nodev,size=512m,mode=1777',
        internal_seconds=150,external_watchdog_seconds=180,accepted_mounts=[],database='private temporary /tmp only',
        forbidden_imports=['numpy','scipy','pymc','pytensor','statsmodels','methods','services.generator'],
        operator_sha256=sha(Path(__file__).read_bytes()),watchdog_sha256=sha((HERE/'ordinary_watchdog.py').read_bytes()))
    raw=encode(spec);(HERE/'ordinary-test-spec.json').write_bytes(raw)
    print(json.dumps(dict(spec_sha256=sha(raw),manifest_sha256=sha(manifest),files=len(entries),bytes=spec['source_bytes'])))


def run():
    spec=json.loads((HERE/'ordinary-test-spec.json').read_bytes())
    if spec['image']!=IMAGE or spec['operator_sha256']!=sha(Path(__file__).read_bytes()) or spec['watchdog_sha256']!=sha((HERE/'ordinary_watchdog.py').read_bytes()):
        raise ValueError('Frozen operator/image changed; re-review required')
    raw=(HERE/'ordinary-source-manifest.json').read_bytes()
    if sha(raw)!=spec['source_manifest_sha256']:raise ValueError('Frozen source manifest changed')
    source=Path(spec['source']);entries=json.loads(raw)
    if {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}!={e['path'] for e in entries}:raise ValueError('Frozen source set changed')
    for entry in entries:
        payload=(source/entry['path']).read_bytes()
        if len(payload)!=entry['bytes'] or sha(payload)!=entry['sha256']:raise ValueError('Frozen source bytes changed')
    metadata=docker('image','inspect',IMAGE,'--format','{{.Id}} {{.Os}} {{.Architecture}}')
    if metadata!=IMAGE+' linux amd64':raise ValueError('Unexpected immutable image platform')
    (HERE/'ordinary-image-metadata.txt').write_text(metadata+'\n')
    argv=['docker','create','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges',
        '--user=10001:10001','--cpus=2','--memory=1g','--memory-swap=1g','--pids-limit=128',
        '--tmpfs=/tmp:rw,nosuid,nodev,size=512m,mode=1777','--mount',f'type=bind,src={source},dst=/source,readonly',
        '--workdir=/source','--entrypoint=python',IMAGE,'-P','-B','/source/run_tests.py']
    bounded(dict(argv=argv),HERE/'ordinary-execution-r3')


if __name__=='__main__':
    if sys.argv[1:] not in (['freeze'],['run']):raise SystemExit('freeze or run required')
    freeze() if sys.argv[1]=='freeze' else run()
