"""One literal-CID watchdog, armed before start; no environment inspection."""
import json
from pathlib import Path
import subprocess
import sys
import time

cid,ready,done,evidence=sys.argv[1:]
if len(cid)!=64 or any(c not in '0123456789abcdef' for c in cid):raise SystemExit('literal CID required')
deadline=time.monotonic()+180
Path(ready).write_text(json.dumps(dict(cid=cid,deadline_monotonic=deadline,seconds=180)))
while not Path(done).exists() and time.monotonic()<deadline:time.sleep(.1)
if not Path(done).exists():
    Path(evidence,'ordinary-watchdog-timeout.json').write_text(json.dumps(dict(cid=cid,timeout=True)))
    subprocess.run(['docker','stop','--time=0',cid],capture_output=True,timeout=10)
    logs=subprocess.run(['docker','logs',cid],capture_output=True,text=True,timeout=10)
    Path(evidence,'ordinary-timeout.log').write_text(logs.stdout+logs.stderr)
    subprocess.run(['docker','rm','-f',cid],capture_output=True,timeout=10)
