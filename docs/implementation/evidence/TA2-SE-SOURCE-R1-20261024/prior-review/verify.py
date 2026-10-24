from pathlib import Path
import subprocess,json,hashlib
root=Path.cwd();out=root/'artifacts/ta2-independent-review';out.mkdir(exist_ok=True)
def git(*args):return subprocess.check_output(['git',*args],cwd=root)
def blob(r):return git('cat-file','blob',r)
head=git('rev-parse','HEAD').decode().strip();base='9292844a46aa4ba46701c9bb45cd703f0862dee6';source='0a81a798792e2d83b87f30f5e694fdc1cd99dc00'
assert head=='4c80ad58088734eac1baa389b564269f615959b2'
assert not git('status','--porcelain')
idx=json.loads(blob('a1fa1dc284441fa216aac929fb2c5c6609a3203e'))
records=[]
for e in idx['source_and_canonical_entries']+idx['evidence_entries']:
 b=blob(e['git_blob']);assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'],e['path']
 assert git('rev-parse',head+':'+e['path']).decode().strip()==e['git_blob']
 records.append(e|{'verified_exact_Git_bytes':True})
proof=json.loads(blob('4cc1a9884678b8e7bac246f6a61088968f2eab55'))
for e in proof['protected']:
 assert git('rev-parse',base+':'+e['path'])==git('rev-parse',head+':'+e['path'])
def tree(ref):return git('ls-tree','-r',ref).decode().splitlines()
excluded=set(proof['changed_paths'])
a=[x for x in tree(base) if x.split('\t')[1] not in excluded]
b=[x for x in tree(source) if x.split('\t')[1] not in excluded]
assert a==b and len(a)==8365
for inv in proof['inverses']:
 expected=git('diff','--binary','--no-ext-diff',source,base,'--',*inv['paths'])
 assert expected==blob(inv['blob']),inv['name']
assert set(git('diff','--name-only',base,head).decode().splitlines())==set(idx['all_changed_paths'])
assert len(idx['all_changed_paths'])==32
assert not git('diff','--check',base,head)
for r in ['b97296f43598fb9d2cff2473a4910dc9c1d999bb','f41b34efed3d7e3fd08dac846e3fc5e8886d95f5','c9d32072b585a47e7d0fded20758a6949c2265b6','a1fa1dc284441fa216aac929fb2c5c6609a3203e','21da2c81ea3f6d0b5c5cf43d2afd95d02ffd59ec']:
 b=blob(r);records.append({'git_blob':r,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'identity':'exact Git bytes; no worktree normalization'})
result={'head':head,'base':base,'source_parent':source,'verified_index_entries':len(idx['source_and_canonical_entries'])+len(idx['evidence_entries']),'protected_objects_equal':14,'source_outside_nine_equal':8365,'inverse_patches_exact_git_diff':2,'changed_paths':32,'diff_check':'PASS','original_tests':{'tests':19,'failures':0,'errors':0,'seconds':33.307,'terminal_tool':'5e7fa1','initial_tool':'841698','session':38241},'counterexample':{'tests':1,'observed_admission_of_reserved_extension_collision':True,'tool':'8d4799','seconds':3.275},'runtime_or_actual_admission':False,'numerics_17_of_18_failure':'preserved; not rerun or waived','disposition':'changes_requested'}
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
(out/'verified-input-index.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
