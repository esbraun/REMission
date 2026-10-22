"""Transparent timing/stacks around the byte-identical original probe call.

No model expression, API argument, optimizer, linker, fixture or point changes.
The only numerical invocation is the original frozen probe via runpy.
"""
from datetime import datetime, timezone
import functools
import hashlib
import json
from pathlib import Path
import runpy
import sys
import threading
import time
import traceback

OUT = Path('/output')
START = time.monotonic()
LOCK = threading.Lock()
def event(kind, **fields):
    row = dict(kind=kind, utc=datetime.now(timezone.utc).isoformat(), elapsed=time.monotonic()-START, **fields)
    encoded = json.dumps(row, sort_keys=True)
    with LOCK:
        print(encoded, flush=True)
        with (OUT/'profile-events.jsonl').open('a') as stream:
            stream.write(encoded+'\n')
            stream.flush()

def snapshots():
    while True:
        time.sleep(15)
        rows = {str(tid): traceback.format_stack(frame) for tid, frame in sys._current_frames().items()}
        event('python-stacks', threads=rows)

event('profile-import-start')
threading.Thread(target=snapshots, name='readonly-stack-sampler', daemon=True).start()
sys.path.insert(0, '/source')
import pymc as pm
import pymc.model.core as core
event('profile-import-end', pymc=pm.__version__)

def wrap(owner, name, label):
    original = getattr(owner, name)
    @functools.wraps(original)
    def timed(*args, **kwargs):
        start = time.monotonic()
        event('phase-enter', phase=label)
        try:
            result = original(*args, **kwargs)
        except BaseException as exc:
            event('phase-error', phase=label, seconds=time.monotonic()-start, error=type(exc).__name__)
            raise
        event('phase-exit', phase=label, seconds=time.monotonic()-start)
        return result
    setattr(owner, name, timed)

for name in ('logp', 'dlogp', 'compile_dlogp', 'compile_fn'):
    wrap(pm.Model, name, 'Model.'+name)
for name in ('rewrite_pregrad', 'gradient'):
    wrap(core, name, 'core.'+name)
probe = Path('/source/artifacts/user-reports/poc-n-symbolic-e6d5-prep/probe.py')
assert hashlib.sha256(probe.read_bytes()).hexdigest() == '170795862e4a5892e88b1f24f380acbc899c2cadd57234f205fd3bc8a9dd2f33'
event('original-probe-start', original_sha256=hashlib.sha256(probe.read_bytes()).hexdigest())
runpy.run_path(str(probe), run_name='__main__')
