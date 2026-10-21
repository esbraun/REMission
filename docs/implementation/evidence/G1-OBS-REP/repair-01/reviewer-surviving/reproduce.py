import subprocess,json,hashlib,pathlib,datetime,sys
root=pathlib.Path(__file__).resolve().parents[1]
out=root/'.review-artifacts'
def run(args,cwd=root):
 n=len(list(out.glob('*.command.json')));p=out/f'{n:03d}'
 r=subprocess.run(args,cwd=cwd,capture_output=True)
 p.with_suffix('.stdout').write_bytes(r.stdout);p.with_suffix('.stderr').write_bytes(r.stderr)
 p.with_suffix('.command.json').write_text(json.dumps({'args':args,'cwd':str(cwd),'exit':r.returncode,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest()},indent=2))
 print(n,r.returncode,r.stdout.decode(errors='replace')[-1200:],r.stderr.decode(errors='replace')[-1200:],flush=True)
 return r
image='sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7'
def checks(path):
 d=['docker','run','--rm','--cpus','2','--memory','2g','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=128m','--mount',f'type=bind,source={path.as_posix()},target=/app,readonly','--workdir','/app',image,'python']
 for a in [['docs/implementation/evidence/G1-OBS-REP/implementation/schema_checks.py']]+[['-m','unittest','discover','-s',p,'-v'] for p in ['tests/contracts','tests/run_contracts','tests/integration/replay']]:run(d+a,path)
 run([sys.executable,'docs/implementation/check-ledger-20261020.py'],path)
if __name__=='__main__':
 run(['git','rev-parse','HEAD']);run([sys.executable,'docs/implementation/evidence/G1-OBS-REP/implementation/verify_frozen_evidence.py']);checks(root)
 clone=out/'https-clone'
 if run(['git','clone','--config','core.autocrlf=false','--no-checkout','https://github.com/esbraun/REMission.git',str(clone)]).returncode==0:
  run(['git','checkout','--detach','ceb5a5fc786f487045fd948986bc4bb8b8a43bf4'],clone);run(['git','status','--porcelain'],clone);checks(clone);run(['git','status','--porcelain'],clone)
