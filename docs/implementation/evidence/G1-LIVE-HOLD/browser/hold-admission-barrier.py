"""Actual second-process admission lock, released by explicit host input."""
from pathlib import Path
import hashlib, json, subprocess, sys, time, uuid
root=Path(__file__).parent/'c'
root.mkdir(exist_ok=True)
stem=uuid.uuid4().hex
code="from services.foundation.admission import AdmissionGate; import sys; gate=AdmissionGate('/data/remission.sqlite'); ctx=gate.hold(); ctx.__enter__(); print('ADMISSION_HELD',flush=True); assert sys.stdin.readline().strip()=='RELEASE'; ctx.__exit__(None,None,None); print('ADMISSION_RELEASED',flush=True)"
command=['docker','exec','-i','remission-g1-live-hold-20261021-799f2981-service','python','-u','-c',code]
start=time.time()
child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
ready=child.stdout.readline()
assert ready==b'ADMISSION_HELD\n',ready
print('ADMISSION_HELD barrier acknowledged; type RELEASE',flush=True)
release=sys.stdin.readline()
assert release.strip()=='RELEASE'
stdout,stderr=child.communicate(release.encode())
stdout=ready+stdout
streams={}
for name,raw in [('stdout',stdout),('stderr',stderr)]:
    path=root/(stem+'.'+name);path.write_bytes(raw)
    streams[name]=dict(path=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
metadata=dict(command=command,source_head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),test_setup='explicit_second_process_gate_barrier',started_unix=start,elapsed_seconds=time.time()-start,exit=child.returncode,streams=streams)
(root/(stem+'.json')).write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
print(json.dumps(metadata),flush=True)
raise SystemExit(child.returncode)
