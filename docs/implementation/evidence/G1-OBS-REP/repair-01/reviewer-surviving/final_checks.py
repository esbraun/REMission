import reproduce
from pathlib import Path
base=reproduce.out
reproduce.out=base/'final-checks';reproduce.out.mkdir(exist_ok=True)
reproduce.image='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
reproduce.run(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'])
reproduce.run(['docker','run','--rm','--cpus','2','--memory','2g','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=128m','remission-obs2-astra-review-20261021-tests:candidate'])
reproduce.run(['git','rev-parse','HEAD'],base/'https-clone')
reproduce.run(['git','status','--porcelain'],base/'https-clone')
# Source audits from each namespace; no foreign-checkout executable.
import json,subprocess,hashlib
for root in [reproduce.root,base/'https-clone']:
 b=json.loads((root/'docs/implementation/evidence/G1-OBS-REP/implementation/v1-byte-inventory-raw.json').read_bytes())
 result=[]
 for item in b['files']:
  blob=subprocess.check_output(['git','hash-object','--path',item['path'],item['path']],cwd=root).decode().strip()
  result.append({'path':item['path'],'expected':item['git_blob'],'actual':blob,'pass':blob==item['git_blob']})
 assert all(r['pass'] for r in result)
 (reproduce.out/('v1-clone.json' if root.name=='https-clone' else 'v1-own.json')).write_text(json.dumps(result,indent=2))
 print(root,'53 V1 blobs',len(result),'PASS')
