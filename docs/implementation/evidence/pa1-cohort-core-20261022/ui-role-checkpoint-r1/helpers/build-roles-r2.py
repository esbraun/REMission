"""One root-approved pinned npm acquisition retry; all old failures retained."""
import hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
root=Path('artifacts/cohort/roles-r2');root.mkdir(exist_ok=False)
source=Path('artifacts/cohort/roles-r1/source')
manifest=Path('artifacts/cohort/roles-r1/source-manifest.json')
frozen=json.loads(manifest.read_text());assert frozen['source']=='45d35071036ca3b635ae60e97ca04e924d98f74e'
for name,item in frozen['files'].items():
    p=source/name
    assert p.stat().st_size==item['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
shutil.copyfile(manifest,root/'source-manifest.json');shutil.copyfile(__file__,root/'helper.py')
(root/'network-scope.json').write_text(json.dumps(dict(service='default solely for exact integrity-locked npm ci --ignore-scripts acquisition after preserved r1 EAI_AGAIN',
    learner='none',generator='none',source=str(source.resolve()),lock_sha256=hashlib.sha256((source/'web/package-lock.json').read_bytes()).hexdigest(),
    original_failure='artifacts/cohort/roles-r1/commands/99364653a15f40298959ce9ecedeefa9.stderr'),indent=2)+'\n')
def command(argv,timeout=1200):
    p,m=run(argv,root/'commands',timeout_seconds=timeout)
    print(json.dumps(dict(command=argv[:3],exit=p.returncode,streams=m['streams'])),flush=True)
    if p.returncode:raise RuntimeError('Retained r2 command failure; no further automatic retries.')
    return p.stdout.decode().strip()
base='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
assert command(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'],60)==base
images={}
for role in ('service','learner','generator'):
    tag='remission-cohort-sol-'+role+':45d3507'
    argv=['docker','build','--network','default' if role=='service' else 'none','--file',str(source/'tooling/foundation'/f'{role}.Dockerfile'),'--tag',tag]
    if role=='service':argv.extend(['--target','service'])
    command([*argv,str(source)])
    images[role]=command(['docker','image','inspect',tag,'--format','{{.Id}}'],60)
    (root/'images-partial.json').write_text(json.dumps(dict(source=frozen['source'],base=base,images=images),indent=2)+'\n')
(root/'images.json').write_text(json.dumps(dict(source=frozen['source'],base=base,images=images,model_compile=False,fit=False),indent=2)+'\n')
print(json.dumps(dict(source=frozen['source'],images=images)),flush=True)
