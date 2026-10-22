"""Verify preservation and write a non-self-referential author freeze manifest."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASE = 'ec18cb4020ba239710a3fd615e365d5cd72b4d80'
ORIGINAL = '01ffab3a3f55cf4c228648ab28a934aed9f30ec6'
PROPOSAL = ROOT/'docs/implementation/g1-clearance-burden-contract-proposal-r1-20261021.md'

def git(*args, data=None):
    return subprocess.check_output(['git',*args], input=data, cwd=ROOT)

def identity(raw):
    blob=git('hash-object','-w','--stdin',data=raw).decode().strip()
    assert git('cat-file','blob',blob)==raw
    return {'raw_git_blob':blob,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

assert git('rev-parse','--show-toplevel').decode().strip().replace('\\','/')==str(ROOT).replace('\\','/')
assert git('branch','--show-current').decode().strip()=='launch/g1-clearance-burden-plan-r1-20261021'
assert git('merge-base','HEAD',BASE).decode().strip()==BASE
original_paths=git('diff-tree','--no-commit-id','--name-only','-r',ORIGINAL).decode().splitlines()
original=[]
for path in original_paths:
    raw=git('show',ORIGINAL+':'+path)
    working=(ROOT/path).read_bytes()
    assert working.replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n'), 'Original content changed: '+path
    assert git('rev-parse','HEAD:'+path).decode().strip()==identity(raw)['raw_git_blob']
    original.append({'path':path,**identity(raw),'working_bytes':identity(working),
                     'checkout_CRLF_only_difference':working!=raw})

envelope=json.loads((HERE/'preserved-inputs.json').read_text())
preserved=[]
for item in envelope['items']:
    raw=base64.b64decode(item['base64'],validate=True)
    ident=identity(raw)
    assert ident['raw_git_blob']==item['git_blob'] and ident['sha256']==item['sha256'] and ident['bytes']==item['bytes']
    preserved.append({'label':item['label'],**ident})

# Includes preserved original warnings. New untracked files get their own no-index checks.
whole=subprocess.run(['git','diff','--check',BASE],cwd=ROOT,capture_output=True)
assert whole.returncode in (0,2)
warning_raw=whole.stdout+whole.stderr
(HERE/'whitespace-check.json').write_text(json.dumps({'encoding':'base64 exact Git stdout/stderr bytes',
    'exit_code':whole.returncode,'raw_output':identity(warning_raw),
    'base64':base64.b64encode(warning_raw).decode()},indent=2)+'\n',encoding='utf-8',newline='\n')
scoped=[]
for path in [PROPOSAL,*sorted(HERE.iterdir())]:
    if not path.is_file() or path.name=='artifact-manifest.json':
        continue
    result=subprocess.run(['git','-c','core.autocrlf=false','diff','--no-index','--check','--','NUL',str(path)],cwd=ROOT,capture_output=True)
    assert result.returncode in (0,1) and not result.stdout and not result.stderr, (str(path),result.stdout,result.stderr)
    scoped.append(path.relative_to(ROOT).as_posix())

artifacts=[]
for path in [PROPOSAL,*sorted(HERE.iterdir())]:
    if path.is_file() and path.name!='artifact-manifest.json':
        artifacts.append({'path':path.relative_to(ROOT).as_posix(),**identity(path.read_bytes())})
manifest={'status':'UNACCEPTED author proposal; independent critique required','base':BASE,
          'original_head':ORIGINAL,'original_cherry_pick':'8033f2dec27dc0fb24ba3e872d56f4fb3a4ef715',
          'model':'assigned gpt-6-astra/medium; independent effective-model introspection unavailable',
          'scope':'docs and finite source/arithmetic evidence only; no runtime or full G1 acceptance',
          'original_paths_verified':original,'decoded_preserved_objects_verified':preserved,
          'new_scoped_whitespace_pass':scoped,'whole_diff_check_exit':whole.returncode,
          'artifacts':artifacts,'self_reference':'manifest excludes itself; final commit and manifest blob supplied at handoff'}
target=HERE/'artifact-manifest.json'
target.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'proposal':identity(PROPOSAL.read_bytes()),'manifest':identity(target.read_bytes()),
                  'new_artifacts':len(artifacts),'original_paths_unchanged':len(original),
                  'preserved_raw_objects':len(preserved),'whole_diff_check_exit':whole.returncode},indent=2))
