"""Frozen-source UNIT runner with a literal external 120-second watchdog."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[4]
IMAGE = 'sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7'
OUT = ROOT/'artifacts'/'support-s1-unit'/sys.argv[1]
OUT.mkdir(parents=True, exist_ok=False)
MANIFEST = dict(kind='deterministic_UNIT_not_study', image=IMAGE, watchdog_seconds=120, commands=[])


def command(argv, timeout=30):
    index = len(MANIFEST['commands'])
    started = time.time()
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired as error:
        result = subprocess.CompletedProcess(argv, -999, error.stdout or b'', error.stderr or b'')
        timed_out = True
    files = {}
    for stream in ('stdout', 'stderr'):
        path = OUT/f'{index:02}-{stream}.bin'
        value = getattr(result, stream)
        path.write_bytes(value)
        files[stream] = dict(path=path.relative_to(ROOT).as_posix(), bytes=len(value),
                             sha256=hashlib.sha256(value).hexdigest())
    MANIFEST['commands'].append(dict(argv=argv, exit_code=result.returncode, timed_out=timed_out,
        started_unix=started, elapsed_seconds=time.time()-started, streams=files))
    (OUT/'raw-manifest.json').write_text(json.dumps(MANIFEST, indent=2)+'\n', encoding='utf-8')
    return result, timed_out


head, _ = command(['git', 'rev-parse', 'HEAD'])
MANIFEST['source_head'] = head.stdout.decode().strip()
status, _ = command(['git', 'status', '--porcelain', '--untracked-files=no'])
if status.stdout:
    raise RuntimeError('tracked source not frozen')
MANIFEST['source_sha256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [*sorted((ROOT/'methods'/'support').glob('*.py')), ROOT/'tests'/'methods'/'test_support_wcls.py']}
image, _ = command(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}'])
if image.returncode or image.stdout.decode().strip() != IMAGE:
    raise RuntimeError('pinned G0 library image unavailable')
name = 'remission-s1-unit-'+uuid.uuid4().hex[:12]
script = "import json,platform,numpy,scipy,statsmodels,unittest; print(json.dumps(dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__,statsmodels=statsmodels.__version__)),flush=True); suite=unittest.defaultTestLoader.discover('tests/methods',pattern='test_support*.py'); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())"
created, _ = command(['docker', 'create', '--name', name, '--network', 'none', '--read-only',
    '--cpus', '2', '--memory', '2g', '--pids-limit', '64', '--user', '10002:10002',
    '--tmpfs', '/tmp:rw,noexec,nosuid,size=128m,uid=10002,gid=10002',
    '--mount', f'type=bind,source={ROOT.as_posix()},target=/workspace,readonly',
    '--workdir', '/workspace', IMAGE, 'python', '-B', '-c', script])
if created.returncode:
    raise RuntimeError('container creation failed')
result, timed_out = command(['docker', 'start', '--attach', name], timeout=120)
if timed_out:
    command(['docker', 'kill', name])
inspection, _ = command(['docker', 'inspect', name, '--format',
    '{{json .State}}|{{.Image}}|{{json .HostConfig.Resources}}|{{.HostConfig.NetworkMode}}|{{.HostConfig.ReadonlyRootfs}}|{{json .Mounts}}'])
# Never inspect Config/Env. Selected container state establishes stopped status.
MANIFEST['test_exit_code'] = result.returncode
MANIFEST['timed_out'] = timed_out
MANIFEST['container'] = name
MANIFEST['selected_inspection'] = inspection.stdout.decode().strip()
(OUT/'raw-manifest.json').write_text(json.dumps(MANIFEST, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(output=str(OUT), exit_code=result.returncode, timed_out=timed_out)))
print(result.stdout.decode(errors='replace'))
print(result.stderr.decode(errors='replace'))
raise SystemExit(result.returncode if not timed_out else 124)
