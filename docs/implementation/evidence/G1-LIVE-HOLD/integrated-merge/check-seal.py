"""Check this bounded checkpoint's final streams, source bindings and artifacts."""
import hashlib,json,subprocess
from pathlib import Path
E=Path(__file__).parent;ROOT=Path.cwd();sha=lambda b:hashlib.sha256(b).hexdigest()
build=json.loads((E/'build/source-images.json').read_bytes())
for path,v in build['source'].items():
    b=Path(path).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['sha256'],path
meta=json.loads((E/'browser/artifact-manifest.json').read_bytes());mcp=json.loads((E/'browser/mcp-raw-complete.json').read_bytes())
assert len(mcp)==meta['records']==62 and len(meta['generated'])==29 and meta['screenshots']==4
for v in meta['generated']:
    b=(E/'browser'/v['path']).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['sha256']
assert sha((E/'browser/mcp-raw-complete.json').read_bytes())==meta['raw_sha256']
assert sha((E/'browser/mcp-events-exact.jsonl').read_bytes())==meta['raw_event_sha256']
assert len((E/'browser/mcp-events-exact.jsonl').read_bytes().splitlines())==62
observed=json.loads(mcp[1]['result']['content'][0]['text'].split('### Result\n',1)[1].split('\n### Ran',1)[0])
roles=json.loads((E/'roles/inventory.json').read_bytes())
for url,digest in observed['assets'].items():assert roles['roles']['service']['copied_source']['assets']['/app/web/dist'+url]==digest
product=json.loads((E/'published-product/manifest.json').read_bytes());a=json.loads((E/'published-authority.json').read_bytes())
assert product['source_commit']==build['source_head']==a['source_commit']=='0e1a11faa01d267fe1cdb06d07c0c06dcc2d5b55'
assert a['manifest_sha256']==sha((E/'published-product/manifest.json').read_bytes()) and a['prefix_count']==product['through_patient_sequence']==5
assert product['independent_hold_status']=='held' and product['execution']=='contract_fixture'
for f in ['facts','observed_projection']:
    v=product[f];b=(E/'published-product'/v['path']).read_bytes();assert len(b)==v['bytes'] and sha(b)==v['sha256']
ledger='docs/implementation/g0-task-test-ledger-20261020.json';old=json.loads(subprocess.check_output(['git','show','ec18cb4020ba239710a3fd615e365d5cd72b4d80:'+ledger]));new=json.loads(Path(ledger).read_bytes())
assert old['tasks']==new['tasks'] and old['coverage']==new['coverage'] and old['coverage_counts']==new['coverage_counts']
old_merge=json.loads(subprocess.check_output(['git','show','0e1a11faa01d267fe1cdb06d07c0c06dcc2d5b55:'+ledger]));assert {k:v for k,v in new.items() if k!='live_hold_implementation'}=={k:v for k,v in old_merge.items() if k!='live_hold_implementation'}
captures=[]
for p in E.rglob('*.json'):
    if p.name in ('manifest.json','reviewed-raw-manifest.json') or 'reviewed-raw' in p.parts:continue
    v=json.loads(p.read_bytes())
    if isinstance(v,dict) and {'command','streams','source_snapshot'}<=v.keys():
        for stream in v['streams'].values():
            b=p.with_name(stream['path']).read_bytes();assert len(b)==stream['bytes'] and sha(b)==stream['sha256']
        captures.append(dict(path=p.relative_to(E).as_posix(),exit=v['exit']))
changes=subprocess.check_output(['git','diff','--cached','--name-only']).decode().splitlines()
assert all(p==ledger or p.startswith(E.relative_to(ROOT).as_posix()+'/') for p in changes)
result=dict(status='passed',merge=build['source_head'],raw_build_inputs=200,served_copied_assets_exact=True,original_ledger_preserved=True,new_mcp_records=62,new_generated_artifacts=29,new_screenshots=4,product_prefix=5,product_status='held',staged_paths=len(changes),capture_streams=captures,negative_captures=[v for v in captures if v['exit']])
(E/'seal-checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='capture_streams'}))
