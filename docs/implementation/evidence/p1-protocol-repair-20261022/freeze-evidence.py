import hashlib,json,shutil,subprocess
from pathlib import Path
base=Path('artifacts/p1');curated=Path('docs/implementation/evidence/p1-protocol-repair-20261022');curated.mkdir(parents=True,exist_ok=False)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='utf-8')
names=['repair-before','repair-after','repair-copy-7c20','repair-controls-7c20','repair-proof-7c20','repair-boundary-7c20']
scripts={'repair-copy-7c20':['build-repair-copy.py','repair-source/COPY.Dockerfile'],'repair-controls-7c20':['run-repair-controls.py'],
    'repair-proof-7c20':['audit-repair-copy.py'],'repair-boundary-7c20':['check-repair-boundary.py']}
roots=[];commands=[]
for name in names:
    root=base/name
    for script in scripts.get(name,[]):shutil.copyfile(base/script,root/Path(script).name)
    for p in sorted(root.rglob('*.json')):
        value=json.loads(p.read_text())
        if 'command' in value and 'streams' in value:
            entry={k:v for k,v in value.items() if k!='source_snapshot'}
            entry.update(raw_metadata=p.as_posix(),raw_metadata_sha256=sha(p.read_bytes()),source_snapshot_sha256=sha(json.dumps(value.get('source_snapshot',{}),sort_keys=True,separators=(',',':')).encode()))
            commands.append(entry)
            if value['command'][:2]==['docker','run']:
                for stream in ['stdout','stderr']:
                    raw=p.parent/value['streams'][stream]['path'];shutil.copyfile(raw,curated/(name+'--'+raw.name))
    files={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()}
    save(root/'raw-manifest.json',{'files':files,'files_count':len(files),'status':'frozen; no more writes'})
    roots.append({'path':root.as_posix(),'files_including_manifest':len(files)+1,'raw_manifest_sha256':sha((root/'raw-manifest.json').read_bytes())})
    for path in sorted(root.glob('*')):
        if path.is_file() and path.suffix in ['.json','.py','.Dockerfile']:shutil.copyfile(path,curated/(name+'--'+path.name))
reviews={}
for label,blob in [('source-review-8f','63503f05097f163b42824f5f696bf86a259d3431'),('source-refresh-7c20','72b94e02827cf0910e1268139725e19145c2673e')]:
    raw=subprocess.check_output(['git','cat-file','-p',blob]);(curated/(label+'.md')).write_bytes(raw)
    reviews[label]={'git_blob':blob,'sha256':sha(raw)}
save(curated/'review-identities.json',reviews)
images=json.loads((base/'repair-copy-7c20/images.json').read_text())
save(curated/'handoff-manifest.json',{'source_commit':'7c20a3926b410a3cf7359bde3e1a857dae2de046','accepted_integration_base':'045b373a18ad067a3ecd1281d445076aae423a80','runtime_merge_source':'a1f20e76e532da60e94b125d21b5049172e4bcd6','previous_reviewed_source':'8f4b21f907ff7f8e36c69e63ad349e14395da256','final_candidate':'Evidence/report descendant of source7c20; no source changes after7c20','images':{k:v['Id'] for k,v in images.items()},'initial_evidence_manifest_sha256':'c6cae29e042473807c80f634bfcf4fdfa5c7a890531f1681108616992d207c78','executable_protocol_configuration_allowlist':[],'no_protocol_fit_or_activation':True,'live8780_and_native_job_untouched':True,'actual_checks':'three reproduced pre-repair failures; repaired10 light contracts and copied28 controls + new genuine-owned-v2 export and actual repaired learner boundary/three negatives','review':'Pending independent final source/COPY/runtime acceptance; no PoC completion claim'})
save(curated/'raw-roots.json',roots);save(curated/'commands-selected-index.json',commands)
shutil.copyfile(__file__,curated/'freeze-evidence.py')
files={p.relative_to(curated).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(curated.rglob('*')) if p.is_file()}
save(curated/'curated-manifest.json',{'files':files,'files_count':len(files),'private_environment_or_DB_payloads':False,'public_reduced_boundary_inputs_only':True})
print(json.dumps({'files':len(files)+1,'curated_manifest_sha256':sha((curated/'curated-manifest.json').read_bytes()),'raw_roots':roots},sort_keys=True))
