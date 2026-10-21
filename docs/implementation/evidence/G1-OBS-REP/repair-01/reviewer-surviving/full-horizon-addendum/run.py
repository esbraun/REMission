import subprocess,pathlib,hashlib,json,datetime
root=pathlib.Path.cwd();out=root/'.review-artifacts/complete-horizon-addendum';n=len(list(out.glob('attempt-*.json')));stem=out/f'attempt-{n:03d}'
args=['docker','run','--rm','--cpus','2','--memory','2g','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=128m','--env','PYTHONPATH=/app','--mount',f'type=bind,source={root.as_posix()},target=/app,readonly','--mount',f'type=bind,source={out.as_posix()},target=/out','--workdir','/app','sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7','python','/app/.review-artifacts/complete-horizon-addendum/probe.py']
source=(out/'probe.py').read_bytes();stem.with_suffix('.probe.py').write_bytes(source)
start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(args,cwd=root,capture_output=True)
stem.with_suffix('.stdout').write_bytes(r.stdout);stem.with_suffix('.stderr').write_bytes(r.stderr)
stem.with_suffix('.json').write_text(json.dumps(dict(args=args,cwd=str(root),start=start,end=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit=r.returncode,probe_sha256=hashlib.sha256(source).hexdigest(),stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),stderr_sha256=hashlib.sha256(r.stderr).hexdigest()),indent=2))
print(r.stdout.decode(errors='replace'));print(r.stderr.decode(errors='replace'));print('EXIT',r.returncode)
