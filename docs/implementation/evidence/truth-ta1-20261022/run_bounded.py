"""Freeze TA1-only source/argv; reuse unchanged reviewed generic lifecycle.

Host imports stdlib only. No S1 plans/validate/run/public-copy are used. Prepare
does no numerical work. A real-history invocation needs root authorization of
its exact invocation hash; focused UNIT scope is separately authorized.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
IMAGE = 'sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
OPERATOR = '2eddca721629ae5e2e5ac2c2e7a3221fbc51fd7b'
SOURCES = ['contracts/domain/__init__.py',
           'contracts/domain/common.py', 'contracts/domain/estimands.py',
           'contracts/domain/analysis.py', 'methods/__init__.py',
           'methods/truth/__init__.py', 'methods/truth/restricted.py',
           'methods/truth/checks.py',
           'services/evaluator/__init__.py', 'services/evaluator/restricted.py',
           'tests/methods/test_restricted_truth.py']


def sha(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def git(*argv):
    return subprocess.check_output(['git', *argv], cwd=ROOT)


def prepare(name, mode):
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name):
        raise ValueError('literal ordinary stage name required')
    stage = ROOT/'artifacts'/'truth-ta1'/name
    stage.mkdir(parents=True, exist_ok=False)
    if git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('commit source before freezing')
    head = git('rev-parse', 'HEAD').decode().strip()
    source_hashes = {}
    for relative in SOURCES:
        raw = git('show', head+':'+relative)
        path = stage/'source'/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        source_hashes[relative] = dict(bytes=len(raw), sha256=sha(raw))
    op = git('show', OPERATOR)
    (stage/'accepted_operator.py').write_bytes(op)
    image = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', IMAGE]).decode().strip()
    if image != IMAGE:
        raise ValueError('pinned dependency image unavailable; do not pull')
    (stage/'output').mkdir()
    if mode == 'unit':
        cap = 180
        script = "import json,platform,numpy,scipy,pydantic,unittest;print(json.dumps(dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__,pydantic=pydantic.__version__)),flush=True);suite=unittest.defaultTestLoader.discover('tests/methods',pattern='test_restricted_truth.py');result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)"
        workload = ['python', '-B', '-c', script]
        input_binding = None
    else:
        cap = 300
        raw = (ROOT/'artifacts/truth-ta1/input/history.json').read_bytes()
        digest = '5bd8d8ebcd84ff862cb3caa8255f7b9cb8eba73aba3e2d2a7a721993743b3289'
        if sha(raw) != digest:
            raise ValueError('frozen reduced input mismatch')
        (stage/'history.json').write_bytes(raw)
        input_binding = dict(raw_sha256=digest, canonical_sha256=digest,
            patient='p-08aa51d3e737479495085ea07881adcf', patient_version=19,
            source_public_blob='e8d5c1aa51867d0317e937afe7331b479a4473dd', bytes=len(raw))
        workload = ['python', '-B', '-m', 'services.evaluator.restricted', '--history', '/input/history.json',
            '--raw-sha256', digest, '--history-sha256', digest, '--patient', input_binding['patient'],
            '--output', '/output/estimate', '--namespace', 'truth-ta1-development-20261022-v1',
            '--replicate', '0', '--particles', '1024', '--moves', '2', '--slice-limit', '128',
            '--batches', '2', '--seconds', '240']
    argv = ['docker', 'create', '--pull', 'never', '--name', 'remission-truth-ta1-'+name,
        '--network', 'none', '--read-only', '--cpus', '2', '--memory', '2g', '--memory-swap', '2g',
        '--pids-limit', '64', '--user', '10002:10002', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,exec,nosuid,nodev,size=512m,uid=10002,gid=10002,mode=1770',
        '--env', 'OPENBLAS_NUM_THREADS=1', '--env', 'OMP_NUM_THREADS=1', '--env', 'MKL_NUM_THREADS=1',
        '--env', 'NUMEXPR_NUM_THREADS=1', '--env', 'VECLIB_MAXIMUM_THREADS=1',
        '--mount', f'type=bind,source={(stage/"source").as_posix()},target=/workspace,readonly',
        '--mount', f'type=bind,source={(stage/"output").as_posix()},target=/output']
    if mode == 'real':
        argv += ['--mount', f'type=bind,source={(stage/"history.json").as_posix()},target=/input/history.json,readonly']
    argv += ['--workdir', '/workspace', '--entrypoint', 'python', IMAGE, *workload[1:]]
    spec = dict(kind='TA1_focused_UNIT_overlap' if mode == 'unit' else 'TA1_single_exploratory_history',
        mode=mode, source_head=head, source_files=source_hashes, operator_blob=OPERATOR,
        operator_sha256=sha(op), pinned_dependency_image=IMAGE,
        frozen_stage_root=str(stage), caps_seconds={mode: cap}, create_commands={mode: argv},
        input=input_binding, root_authorization_required=mode == 'real',
        claim='unqualified exploratory numerical evidence; no fit, admission, accuracy or clinical badge')
    encoded = canonical(spec)
    (stage/'invocation.json').write_bytes(encoded)
    print(json.dumps(dict(stage=str(stage), invocation_sha256=sha(encoded), spec=spec), indent=2))


def run(stage, token):
    raw = (stage/'invocation.json').read_bytes()
    if sha(raw) != token:
        raise ValueError('exact frozen invocation hash required')
    spec = json.loads(raw)
    if stage != Path(spec['frozen_stage_root']):
        raise ValueError('no stage relocation')
    for name, binding in spec['source_files'].items():
        source = (stage/'source'/name).read_bytes()
        if sha(source) != binding['sha256'] or len(source) != binding['bytes']:
            raise ValueError('frozen source changed: '+name)
    if sha((stage/'accepted_operator.py').read_bytes()) != spec['operator_sha256']:
        raise ValueError('reviewed generic operator changed')
    if spec['input'] and sha((stage/'history.json').read_bytes()) != spec['input']['raw_sha256']:
        raise ValueError('input changed')
    # Reserve before Docker creation. Failure never authorizes automatic retry.
    with (stage/'attempt-reserved.json').open('xb') as stream:
        stream.write(canonical(dict(invocation_sha256=token)))
    loader = importlib.util.spec_from_file_location('accepted_truth_lifecycle', stage/'accepted_operator.py')
    op = importlib.util.module_from_spec(loader); loader.loader.exec_module(op)
    op.ROOT = stage
    op.ordinary_path(stage)
    try:
        op.container(spec['mode'], spec)
    finally:
        manifest = dict(invocation_sha256=token, source_head=spec['source_head'], files={})
        for path in sorted(stage.rglob('*')):
            if path.is_file() and path.name != 'raw-manifest.json' and '__pycache__' not in path.parts:
                data = path.read_bytes()
                manifest['files'][path.relative_to(stage).as_posix()] = dict(bytes=len(data), sha256=sha(data))
        (stage/'raw-manifest.json').write_bytes(canonical(manifest))
    print(json.dumps(dict(stage=str(stage), invocation_sha256=token, status='stopped-and-reaped')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--name', required=True); p.add_argument('--mode', choices=['unit', 'real'], required=True)
    p = sub.add_parser('run'); p.add_argument('--stage', type=Path, required=True); p.add_argument('--token', required=True)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.name, args.mode)
    else:
        run(args.stage, args.token)
