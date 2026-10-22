"""Affected privacy repair checks; reuse exact consumer-byte identity evidence."""
import hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
SOURCE='37376a69629b6143ecc6af84c44669e84f63b609';BASE='b17bf991b910c2c28da6979aab5a04650a4baa66'
RUNTIME='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
checks=[]
def run(name,args):
 print('START '+name,flush=True);start=time.monotonic();p=subprocess.run(args,cwd=ROOT,capture_output=True)
 (OUT/(name+'.stdout')).write_bytes(p.stdout);(OUT/(name+'.stderr')).write_bytes(p.stderr)
 checks.append(dict(name=name,command=args,exit_code=p.returncode,seconds=time.monotonic()-start))
 print('DONE '+name+' exit='+str(p.returncode),flush=True);assert p.returncode==0
 return p
p=run('research-final-17',['docker','run','--rm','--network','none','--mount','type=bind,source='+str(ROOT)+',target=/app,readonly','-e','RESEARCH_TEST_IMAGE='+RUNTIME,'-e','RESEARCH_TEST_SOURCE='+SOURCE,RUNTIME,'python','-m','unittest','discover','-s','tests/run_contracts','-p','test_research_producer.py','-v'])
run('build-generator-final',['docker','build','--network','none','-f','tooling/foundation/generator.Dockerfile','-t','remission-research-prod-sol-generator:20261022','.'])
p=run('image-generator-final',['docker','image','inspect','remission-research-prod-sol-generator:20261022']);image=json.loads(p.stdout)[0]['Id']
prior=json.loads((OUT/'observed-role-pins.json').read_bytes())
command=next(c['command'] for c in prior['checks'] if c['name']=='qualified-inventory-generator')
command=[image if v==prior['roles']['generator']['image_sha256'] else v for v in command]
p=run('inventory-generator-final',command);inventory=json.loads(p.stdout)
for name,digest in inventory['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
consumers={}
for role in ('service','learner'):
 old=prior['roles'][role]
 unchanged=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in old['inventory']['files'].items())
 assert unchanged
 consumers[role]=dict(image_sha256=old['image_sha256'],original_source=BASE,current_source=SOURCE,all_copied_bytes_identical=True,inventory_evidence='qualified-inventory-'+role+'.stdout')
runtime=dict(prior['runtime']);runtime['image_sha256']=image.removeprefix('sha256:')
result=dict(status='author_frozen_candidate_pending_independent_source_runtime_review',source_commit=SOURCE,prior_source=BASE,
 repair='Public partition identity/order only; generation and private seed/index mapping source unchanged.',
 runtime=runtime,producer=dict(image_sha256=image,inventory=inventory),consumers=consumers,checks=checks,
 methods_tree=subprocess.check_output(['git','rev-parse',SOURCE+':methods'],cwd=ROOT,text=True).strip(),
 canonical_v1_bindings_unchanged=subprocess.run(['git','diff','--quiet','393edc9e9e80fc303a50e99e061e2c266bbd688e',SOURCE,'--','contracts/runs/bindings-v1.json'],cwd=ROOT).returncode==0,
 v2_products_unchanged=subprocess.run(['git','diff','--quiet','393edc9e9e80fc303a50e99e061e2c266bbd688e',SOURCE,'--','contracts/runs/bindings-v2.json','contracts/runs/dictionary-v2.json','contracts/runs/schemas/v2'],cwd=ROOT).returncode==0,
 production_authority=False,production_exports=False,production_enrollment=False,fits=False)
assert result['canonical_v1_bindings_unchanged'] and result['v2_products_unchanged']
(OUT/'final-observed-pins.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(source=SOURCE,producer_image=image,consumer_bytes_unchanged=True)),flush=True)
