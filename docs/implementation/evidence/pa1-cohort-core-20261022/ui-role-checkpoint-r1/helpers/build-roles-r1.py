import hashlib,io,json,subprocess,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
root=Path('artifacts/cohort/roles-r1');root.mkdir(exist_ok=False)
source=root/'source';source.mkdir()
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head=='45d35071036ca3b635ae60e97ca04e924d98f74e'
archive=subprocess.check_output(['git','archive','--format=zip',head,'.dockerignore','contracts','methods','services','tooling/foundation','web'])
with zipfile.ZipFile(io.BytesIO(archive)) as z:z.extractall(source)
files={p.relative_to(source).as_posix():dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(source.rglob('*')) if p.is_file()}
(root/'source-manifest.json').write_text(json.dumps(dict(source=head,files=files),indent=2)+'\n')
def command(argv,timeout=1200):
    p,m=run(argv,root/'commands',timeout_seconds=timeout)
    print(json.dumps(dict(command=argv[:3],exit=p.returncode,streams=m['streams'])),flush=True)
    if p.returncode:raise RuntimeError('Retained nonfitting build command failure; no automatic network retry.')
    return p.stdout.decode().strip()
base='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
assert command(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'],60)==base
images={}
for role in ('service','learner'):
    tag='remission-cohort-sol-'+role+':45d3507'
    argv=['docker','build','--network','none','--file',str(source/'tooling/foundation'/f'{role}.Dockerfile'),'--tag',tag]
    if role=='service':argv.extend(['--target','service'])
    command([*argv,str(source)])
    images[role]=command(['docker','image','inspect',tag,'--format','{{.Id}}'],60)
    (root/'images-partial.json').write_text(json.dumps(dict(source=head,base=base,images=images),indent=2)+'\n')
(root/'images.json').write_text(json.dumps(dict(source=head,base=base,images=images,model_compile=False,fit=False),indent=2)+'\n')
print(json.dumps(dict(source=head,images=images)),flush=True)
