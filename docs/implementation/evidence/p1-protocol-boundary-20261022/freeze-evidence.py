import hashlib,json,shutil
from pathlib import Path

names=['dev-contract-1','dev-contract-2','dev-controls-3','dev-api-1','dev-contract-4','copied-c4f8a47','copied-434306c','controls-434306c','copy-audit-434306c','boundary-434306c','controls-ac9a396','controls-r2','controls-proof-r2']
base=Path('artifacts/p1');curated=Path('docs/implementation/evidence/p1-protocol-boundary-20261022');curated.mkdir(parents=True,exist_ok=False)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='utf-8')
scripts={'copied-c4f8a47':['build-copied-roles.py'],'copied-434306c':['build-copied-roles-r1.py'],
    'controls-434306c':['run-copied-controls.py'],'copy-audit-434306c':['audit-copied-roles.py'],
    'boundary-434306c':['check-copied-boundary.py'],'controls-ac9a396':['run-copied-controls-r1.py','controls-ac9a396.Dockerfile'],
    'controls-r2':['run-copied-controls-r2.py','controls-r2.Dockerfile'],'controls-proof-r2':['audit-controls-r2.py']}
indices=[];commands=[]
for name in names:
    root=base/name
    for helper in scripts.get(name,[]):shutil.copyfile(base/helper,root/helper)
    for path in sorted(root.rglob('*.json')):
        value=json.loads(path.read_text())
        if 'command' in value and 'streams' in value:
            entry={k:v for k,v in value.items() if k!='source_snapshot'}
            entry.update(raw_metadata=path.as_posix(),raw_metadata_sha256=sha(path.read_bytes()),source_snapshot_sha256=sha(json.dumps(value.get('source_snapshot',{}),sort_keys=True,separators=(',',':')).encode()))
            commands.append(entry)
            if value['command'][:2]==['docker','run']:
                for stream in ['stdout','stderr']:
                    raw=path.parent/value['streams'][stream]['path']
                    shutil.copyfile(raw,curated/(name+'--'+raw.name))
    files={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()}
    save(root/'raw-manifest.json',{'files':files,'files_count':len(files),'status':'frozen; no more writes'})
    indices.append({'path':root.as_posix(),'files_including_manifest':len(files)+1,'raw_manifest_sha256':sha((root/'raw-manifest.json').read_bytes())})
    for path in sorted(root.glob('*')):
        if path.is_file() and path.suffix in ['.json','.py','.Dockerfile']:
            shutil.copyfile(path,curated/(name+'--'+path.name))
save(curated/'raw-roots.json',indices)
save(curated/'commands-selected-index.json',commands)
save(curated/'failure-chronology.json',{'dev_contract_1':'Three errors from a reducer local variable shadowed by a walrus context comprehension; captured original failures. Fixed variable name; next4/4 and final25 passed.',
    'dev_controls_3':'Added snapshot positive exposed overly narrow ordinary-assignment reduced whitelist. Fixed only fixed-support no-prompt assignment with exact fixed policy; six contracts and final25 passed.',
    'copied_c4f8a47':'Docker FROM sha256:... interpreted as repository/tag, failed metadata resolution before COPY. Actual failure preserved. Repaired build uses own local tags verified against exact immutable parent IDs; no numerical code changed.',
    'controls_ac9a396':'Original24 copied controls passed; added mandatory minor-version test made25, caught controls-role omission of export_observed.py. Production learner already contained it. Source8f fixes tests-only COPY; final7804 image25/25 passed.',
    'scope':'No failed phase is relabelled. Final source8f production code is unchanged from434; final controls overlay changes exactly two reader files plus the added minor-version test against original978. Boundary fixture930... originates from original genuine-owned24-run, production learner unchanged for final25-run.'})
shutil.copyfile(__file__,curated/'freeze-evidence.py')
files={p.relative_to(curated).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(curated.rglob('*')) if p.is_file()}
save(curated/'curated-manifest.json',{'files':files,'files_count':len(files),'private_environment_or_DB_payloads':False,'public_reduced_boundary_inputs_only':True})
print(json.dumps({'curated_files':len(files)+1,'curated_manifest_sha256':sha((curated/'curated-manifest.json').read_bytes()),'raw_roots':indices},sort_keys=True))
