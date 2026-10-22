"""Copied-role observations only; no generation, enrollment, server or fitting."""
import hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
SOURCE="b17bf991b910c2c28da6979aab5a04650a4baa66"
checks=[]
def run(name,args):
 print("START "+name,flush=True);t=time.monotonic();p=subprocess.run(args,cwd=ROOT,capture_output=True)
 (OUT/(name+".stdout")).write_bytes(p.stdout);(OUT/(name+".stderr")).write_bytes(p.stderr)
 checks.append(dict(name=name,command=args,exit_code=p.returncode,seconds=time.monotonic()-t))
 print("DONE "+name+" exit="+str(p.returncode),flush=True);return p
run("build-service-explicit-target",["docker","build","--target","service","-f","tooling/foundation/service.Dockerfile","-t","remission-research-prod-sol-service:20261022","."])
observed={}
for role in ("generator","service","learner"):
 p=run("qualified-image-"+role,["docker","image","inspect","remission-research-prod-sol-"+role+":20261022"])
 assert p.returncode==0
 info=json.loads(p.stdout)[0];image=info['Id'];observed[role]=dict(image_sha256=image,config=info['Config'])
 module={"generator":"services.generator.research","service":"services.foundation.research_enrollment","learner":"services.learner.worker"}[role]
 code="""import hashlib,importlib,json,os,platform,sys
from pathlib import Path
import numpy
role=sys.argv[1];importlib.import_module(sys.argv[2]);denied={}
if role!='generator':
 for name in ('services.generator.research','contracts.runs.private','contracts.dgp.parameters','services.evaluator'):
  try:importlib.import_module(name);denied[name]=False
  except ModuleNotFoundError:denied[name]=True
 assert all(denied.values()),denied
 assert not Path('/app/services/generator').exists() and not Path('/app/contracts/dgp').exists() and not Path('/app/contracts/runs/private.py').exists()
 if role=='service':assert not Path('/app/methods').exists() and not Path('/app/services/learner').exists()
files={str(p.relative_to('/app')):hashlib.sha256(p.read_bytes()).hexdigest() for base in ('/app/contracts','/app/services','/app/methods') for p in Path(base).rglob('*') if p.is_file() and p.suffix in ('.py','.json')}
assert os.getuid()!=0 and not Path('/var/run/docker.sock').exists()
print(json.dumps(dict(role=role,uid=os.getuid(),python=platform.python_version(),numpy=numpy.__version__,denied=denied,files=files),sort_keys=True))
"""
 p=run("qualified-inventory-"+role,["docker","run","--rm","--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",image,"python","-c",code,role,module])
 assert p.returncode==0
 inventory=json.loads(p.stdout);observed[role].update(inventory=inventory)
 copied={name:sha for name,sha in inventory['files'].items() if (ROOT/name).is_file()}
 assert len(copied)==len(inventory['files'])
 assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in copied.items())
result=dict(status='author_candidate_observations_not_independently_accepted',source_commit=SOURCE,checks=checks,roles=observed,
 methods_tree=subprocess.check_output(['git','rev-parse',SOURCE+':methods'],cwd=ROOT,text=True).strip(),
 source_paths_equal_frozen=subprocess.run(['git','diff','--quiet',SOURCE,'--','contracts','services','methods','tooling','tests'],cwd=ROOT).returncode==0,
 excluded_test_image='sha256:ff5a7f37dc6ba54689b6b09d104ff010c874bac048a9bcd1006363a34b054b4b',
 runtime=dict(image_sha256=observed['generator']['image_sha256'].removeprefix('sha256:'),python_version=observed['generator']['inventory']['python'],numpy_version=observed['generator']['inventory']['numpy'],
 prng='keyed-SHA256-53bit-BoxMuller-v1',seed_derivation='poc-restricted-adapter-map-v1',precision='float64',
 numerical_lock=dict(id='numerical-lock',version='20261021',sha256=hashlib.sha256(subprocess.check_output(['git','show',SOURCE+':tooling/library/requirements.lock'],cwd=ROOT)).hexdigest()),
 service_lock=dict(id='service-lock',version='20261021',sha256=hashlib.sha256(subprocess.check_output(['git','show',SOURCE+':tooling/foundation/requirements.lock'],cwd=ROOT)).hexdigest())),
 production_authority_created=False,production_exports_created=False,production_enrollment_run=False,fits_run=False)
assert result['source_paths_equal_frozen']
(OUT/'observed-role-pins.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(source=SOURCE,images={r:v['image_sha256'] for r,v in observed.items()},source_matches=True)),flush=True)
