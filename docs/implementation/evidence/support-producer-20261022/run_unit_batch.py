"""Host stdlib-only bounded UNIT orchestration; no numerical imports.

Run with PYTHONSAFEPATH=1. Retains terminal/container/watchdog evidence, including
failures. A child watchdog is armed with the exact immutable CID before start.
"""
import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

IMAGE='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
# Restrict at the Docker boundary, before stdout is captured or persisted. Role
# qualification and genuine-run harnesses must retain this discipline as well.
TERMINAL_INSPECT_FORMAT=(
    '{"Id":{{json .Id}},"Image":{{json .Image}},"State":{{json .State}},'
    '"User":{{json .Config.User}},"WorkingDir":{{json .Config.WorkingDir}},'
    '"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},'
    '"NetworkMode":{{json .HostConfig.NetworkMode}},"NanoCpus":{{json .HostConfig.NanoCpus}},'
    '"Memory":{{json .HostConfig.Memory}},"MemorySwap":{{json .HostConfig.MemorySwap}},'
    '"PidsLimit":{{json .HostConfig.PidsLimit}},"CapAdd":{{json .HostConfig.CapAdd}},'
    '"CapDrop":{{json .HostConfig.CapDrop}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},'
    '"Tmpfs":{{json .HostConfig.Tmpfs}},"Mounts":{{json .Mounts}}}')


def write(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True),encoding='utf-8')


def watchdog(cid,folder,seconds):
    # This argv contains a literal CID, never a mutable name/pattern or discovery
    # query over unrelated containers. It owns only this batch's process.
    log=[];deadline=time.monotonic()+seconds
    write(folder/'watchdog-ready.json',dict(cid=cid,pid=os.getpid(),seconds=seconds,armed_at=datetime.now(timezone.utc).isoformat()))
    while True:
        result=subprocess.run(['docker','inspect','--format','{{json .State}}',cid],capture_output=True,text=True,timeout=10)
        if result.returncode:
            log.append(dict(error=result.stderr));break
        state=json.loads(result.stdout)
        if state['Status'] in ('exited','dead'):
            log.append(dict(terminal=state));break
        if time.monotonic()>=deadline:
            killed=subprocess.run(['docker','kill',cid],capture_output=True,text=True,timeout=15)
            log.append(dict(deadline_exceeded=True,kill_returncode=killed.returncode,stdout=killed.stdout,stderr=killed.stderr));break
        time.sleep(.5)
    write(folder/'watchdog-terminal.json',dict(cid=cid,events=log,ended_at=datetime.now(timezone.utc).isoformat()))


def batch(source,folder,tests):
    folder.mkdir(parents=True,exist_ok=False)
    head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    args=['docker','create','--user','10002:10002','--network','none','--read-only',
        '--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','64','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,exec,size=512m,mode=1777',
        '--mount',f'type=bind,source={source},target=/src,readonly','--workdir','/src',
        '--env','PYTHONPATH=/src:/src/tests:/src/tests/generator:/src/tests/integration/replay','--env','PYTHONSAFEPATH=1','--env','PYTHONDONTWRITEBYTECODE=1',
        '--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1','--env','MKL_NUM_THREADS=1',
        '--env','NUMEXPR_NUM_THREADS=1','--env','PYTENSOR_FLAGS=base_compiledir=/tmp/pytensor,floatX=float64',
        '--env',f'RESEARCH_TEST_IMAGE={IMAGE}','--env',f'RESEARCH_TEST_SOURCE={head}',IMAGE,
        'python','-m','unittest','-v',*tests]
    paths=['services/generator/research_support.py','contracts/runs/support_research.py','services/foundation/protocol.py',
        'services/generator/restricted.py','services/generator/restricted_v2.py',
        'tests/run_contracts/test_support_research_producer.py','tests/methods/test_support_wcls.py',
        'tests/contracts/test_protocol_boundary.py',
        'docs/implementation/evidence/support-producer-20261022/run_unit_batch.py',
        'docs/implementation/evidence/support-producer-20261022/run_support_once.py',
        'docs/implementation/evidence/support-producer-20261022/support_roles.Dockerfile']
    write(folder/'command.json',dict(argv=args,source_head=head,unit_only=True,watchdog_seconds=300,
        terminal_inspect_format=TERMINAL_INSPECT_FORMAT,
        source_sha256={p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in paths}))
    created=subprocess.run(args,capture_output=True,text=True,timeout=30)
    (folder/'create.stdout').write_text(created.stdout);(folder/'create.stderr').write_text(created.stderr)
    if created.returncode:raise RuntimeError('container creation failed; retained logs')
    cid=created.stdout.strip();(folder/'cid.txt').write_text(cid)
    child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--watchdog-cid',cid,'--evidence',str(folder),
        '--seconds','300'],cwd=folder,env=os.environ.copy(),stdout=(folder/'watchdog.stdout').open('w'),
        stderr=(folder/'watchdog.stderr').open('w'),creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    for _ in range(100):
        if (folder/'watchdog-ready.json').exists():break
        if child.poll() is not None:raise RuntimeError('watchdog failed before start')
        time.sleep(.1)
    else:raise RuntimeError('watchdog not armed; container was not started')
    started=time.monotonic()
    with (folder/'terminal.stdout').open('w') as stdout,(folder/'terminal.stderr').open('w') as stderr:
        result=subprocess.run(['docker','start','--attach',cid],stdout=stdout,stderr=stderr,timeout=325)
    child.wait(timeout=20)
    terminal=subprocess.run(['docker','inspect','--format',TERMINAL_INSPECT_FORMAT,cid],capture_output=True,text=True,timeout=15)
    terminal.check_returncode()
    (folder/'container-terminal.json').write_text(terminal.stdout)
    wait=subprocess.run(['docker','wait',cid],capture_output=True,text=True,timeout=10)
    write(folder/'result.json',dict(cid=cid,attach_returncode=result.returncode,container_exit=wait.stdout.strip(),
        watchdog_exit=child.returncode,elapsed_seconds=time.monotonic()-started,retained_stopped_container=True))
    print((folder/'terminal.stdout').read_text());print((folder/'terminal.stderr').read_text())
    print((folder/'result.json').read_text())
    return int(wait.stdout.strip())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path);parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--watchdog-cid');parser.add_argument('--seconds',type=int,default=300)
    parser.add_argument('tests',nargs='*');args=parser.parse_args()
    if args.watchdog_cid:watchdog(args.watchdog_cid,args.evidence.resolve(),args.seconds)
    else:sys.exit(batch(args.source.resolve(),args.evidence.resolve(),args.tests))
