"""Freeze or run one explicitly reviewed Linux ordinary-test package.

No build, scientific imports, accepted mounts, live service or credentials.
Invocation: host Python -P -B this.py freeze|run.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
STAGING=REPO/'artifacts/support-p2-ordinary-tests'
IMAGE='sha256:146a84b1ff4306235bec2d15212350a7d58c94a3ea812b4d02c4e8318a4a3de0'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return json.dumps(value,sort_keys=True,indent=2).encode()+b'\n'
def docker(*args,timeout=15):
    return subprocess.run(['docker',*args],capture_output=True,text=True,timeout=timeout,check=True).stdout.strip()


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
    cid=docker('create','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges',
        '--user=10001:10001','--cpus=2','--memory=1g','--memory-swap=1g','--pids-limit=128',
        '--tmpfs=/tmp:rw,nosuid,nodev,size=512m,mode=1777','--mount',f'type=bind,src={source},dst=/source,readonly',
        '--workdir=/source','--entrypoint=python',IMAGE,'-P','-B','/source/run_tests.py')
    if len(cid)!=64 or any(c not in '0123456789abcdef' for c in cid):raise ValueError('Literal CID required')
    (HERE/'ordinary-cid.txt').write_text(cid+'\n')
    ready=STAGING/'watchdog-ready.json';done=STAGING/'watchdog-done'
    watcher=subprocess.Popen([sys.executable,'-P','-B',str(HERE/'ordinary_watchdog.py'),cid,str(ready),str(done),str(HERE)])
    try:
        deadline=time.monotonic()+5
        while not ready.exists():
            if watcher.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Watchdog not armed')
            time.sleep(.05)
        if json.loads(ready.read_bytes())['cid']!=cid:raise ValueError('Watchdog CID mismatch')
        docker('start',cid)
        completed=docker('wait',cid,timeout=190)
        (HERE/'ordinary-tests.log').write_text(docker('logs',cid,timeout=15)+'\n',encoding='utf-8')
        # Logs contain both streams; docker's logs stderr is collected below.
        logs=subprocess.run(['docker','logs',cid],capture_output=True,text=True,timeout=15,check=True)
        (HERE/'ordinary-tests.log').write_text(logs.stdout+logs.stderr,encoding='utf-8')
        state=docker('inspect',cid,'--format','{{json .State}}')
        (HERE/'ordinary-state.json').write_text(state+'\n')
        print(json.dumps(dict(cid=cid,exit_code=completed,state=json.loads(state))))
        if completed!='0':raise RuntimeError('Ordinary fixture tests failed; preserve logs and revise source')
    finally:
        done.write_text('done')
        try:docker('rm','-f',cid)
        finally:watcher.wait(timeout=5)


if __name__=='__main__':
    if sys.argv[1:] not in (['freeze'],['run']):raise SystemExit('freeze or run required')
    freeze() if sys.argv[1]=='freeze' else run()
