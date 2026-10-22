"""Freeze only public consumer/service/test sources for actual stopped003 proofs."""
import base64,hashlib,json,subprocess
from pathlib import Path

HEAD='1096d6da86048e7a53f98ed70abdd85f6f497aed'
prefixes=['contracts/domain/','contracts/runs/','contracts/service/','services/foundation/']
explicit=['tests/integration/replay/live_helpers.py','tests/run_contracts/observed_v2_fixtures.py']
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',HEAD,*[p.rstrip('/') for p in prefixes],*explicit]).decode().splitlines()
items=[]
for path in paths:
    if path not in explicit and not (path.endswith('.py') or path.endswith('.sql') or path.endswith('/bindings-v1.json') or path.endswith('/bindings-v2.json')):continue
    raw=subprocess.check_output(['git','show',HEAD+':'+path])
    items.append(dict(path=path,git_blob=subprocess.check_output(['git','rev-parse',HEAD+':'+path]).decode().strip(),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode()))
target=Path('tests/integration/replay/checkpoint003-source.json')
target.write_text(json.dumps(dict(source_head=HEAD,scope='Public consumer contracts, foundation service and two public fixture assemblers only; no generator/evaluator engine',files=items),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_head=HEAD,files=len(items),bytes=target.stat().st_size)))
