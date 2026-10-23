"""Task-local TA2 freeze/run wrapper; prepare uses stdlib and never calls Docker.

Run requires the independently reviewed, root-approved invocation SHA256. No
resume, image pull, automatic retry, application mount or learner output exists.
"""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time

from methods.truth.refinement import (IMAGE, NAMESPACE, RUNTIME, SCHEMA, TARGET, canonical,
                                      digest, validate_plan, workload)

ROOT = Path(__file__).resolve().parents[2]
PATIENT = 'p-08aa51d3e737479495085ea07881adcf'
HISTORY_HASH = '5bd8d8ebcd84ff862cb3caa8255f7b9cb8eba73aba3e2d2a7a721993743b3289'
PUBLIC_BLOB = 'e8d5c1aa51867d0317e937afe7331b479a4473dd'
SOURCES = ['contracts/domain/__init__.py', 'contracts/domain/common.py',
    'contracts/domain/estimands.py', 'contracts/domain/analysis.py',
    'contracts/runs/restricted-profile-v1.json', 'methods/__init__.py',
    'methods/truth/__init__.py', 'methods/truth/restricted.py',
    'methods/truth/refinement.py', 'services/evaluator/__init__.py',
    'services/evaluator/restricted_refinement.py',
    'tooling/foundation/analysis_lifecycle.py', 'tooling/foundation/truth_refinement.py',
    'tests/methods/test_truth_refinement.py']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def file_binding(raw):
    return dict(bytes=len(raw), sha256=digest(raw))


def save(path, value):
    with path.open('xb') as stream:
        stream.write(canonical(value))


def analysis_refs(raw):
    # Read literal existing reference definitions without importing Pydantic or
    # any numerical/application module. Reject a changed definition shape.
    names = {'HISTORY_REF', 'ESTIMAND_REF', 'PROTOCOL_REF'}
    refs = {}
    for statement in ast.parse(raw).body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = statement.targets[0]
            if isinstance(target, ast.Name) and target.id in names:
                call = statement.value
                if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != 'reference':
                    raise ValueError('changed analysis reference definition')
                identifier, value = [ast.literal_eval(arg) for arg in call.args]
                refs[target.id] = dict(id=identifier, version='1.0.0', sha256=digest(canonical(value)))
    if refs.keys() != names:
        raise ValueError('missing existing analysis references')
    return refs


def create_argv(stage):
    argv = ['docker', 'create', '--pull', 'never', '--name', 'remission-truth-ta2-'+stage.name,
        '--network', 'none', '--read-only', '--cpus', '2', '--memory', '2g', '--memory-swap', '2g',
        '--pids-limit', '64', '--user', '10002:10002', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges', '--tmpfs',
        '/tmp:rw,exec,nosuid,nodev,size=512m,uid=10002,gid=10002,mode=1770']
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        argv += ['--env', name+'=1']
    for source, target, readonly in [('source', '/workspace', True), ('input', '/input', True),
                                      ('output', '/output', False)]:
        argv += ['--mount', f'type=bind,source={(stage/source).as_posix()},target={target}'+(',readonly' if readonly else '')]
    expected_hash = digest((stage/'input/expected-binding.json').read_bytes())
    return argv+['--workdir', '/workspace', '--entrypoint', 'python', IMAGE, '-B', '-m',
        'services.evaluator.restricted_refinement', '--plan', '/input/workload.json',
        '--expected-binding', '/input/expected-binding.json', '--expected-sha256', expected_hash,
        '--history', '/input/history.json', '--output', '/output/refinement']


def prepare(name):
    if re.fullmatch('[a-z][a-z0-9-]{0,47}', name) is None:
        raise ValueError('literal ordinary stage name required')
    if git('status', '--porcelain').strip():
        raise ValueError('commit all source before freezing')
    head = git('rev-parse', 'HEAD').decode().strip()
    stage = ROOT/'artifacts/truth-ta2'/name
    stage.mkdir(parents=True, exist_ok=False)
    source_files = {}
    for relative in SOURCES:
        raw = git('show', head+':'+relative)
        path = stage/'source'/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        source_files[relative] = file_binding(raw)
    # Exact accepted public input and fixed selection; no searching patients.
    public_raw = git('show', PUBLIC_BLOB)
    if len(public_raw) != 335568 or digest(public_raw) != '0be1e829af83456980639e7c93553f30abfda13925d8cd40733665423b29c044':
        raise ValueError('accepted public CohortInput mismatch')
    cohort = json.loads(public_raw)['cohort']
    selected = [h for h in cohort['histories'] if h['patient_id'] == PATIENT]
    if len(selected) != 1:
        raise ValueError('fixed patient absent/duplicate')
    history = canonical(selected[0])
    if len(history) != 27455 or digest(history) != HISTORY_HASH:
        raise ValueError('frozen reduced Hstar mismatch')
    (stage/'input').mkdir()
    (stage/'output').mkdir()
    (stage/'input/history.json').write_bytes(history)
    profile_raw = (stage/'source/contracts/runs/restricted-profile-v1.json').read_bytes()
    profile = json.loads(profile_raw)
    refs = analysis_refs((stage/'source/contracts/domain/analysis.py').read_bytes())
    refs.update(profile=dict(id=profile['id'], version=profile['version'], sha256=digest(canonical(profile))),
        scenario=profile['bindings']['scenarios'], law=profile['bindings']['dgp'],
        evaluation=profile['evaluation_configuration']['reference'])
    binding = dict(data_schema=SCHEMA, source_head=head, source_files=source_files, image=IMAGE, runtime=RUNTIME,
        refs=refs, profile_file=file_binding(profile_raw), patient_id=PATIENT, patient_version=19,
        history_raw_sha256=HISTORY_HASH, history_sha256=HISTORY_HASH, history_bytes=27455,
        public_cohort_blob=PUBLIC_BLOB, namespace=NAMESPACE, target=TARGET,
        seed_recipe='int.from_bytes(SHA256(namespace|restricted-v1|patient_id|history_sha256|replicate|process)[:16],big)',
        prng='NumPy-PCG64', generator_prng='keyed-SHA256-53bit-BoxMuller-v1',
        canonical_prng='PCG64DXSM (not used here)',
        precision='float64; finite53-bit versus continuous discrepancy unresolved')
    plan = dict(binding=binding, workload=workload(PATIENT, HISTORY_HASH))
    validate_plan(plan, binding)
    save(stage/'input/expected-binding.json', binding)
    save(stage/'input/workload.json', plan)
    spec = dict(kind='TA2_first_refinement_preparation', source_head=head, stage=str(stage),
        files={str(p.relative_to(stage).as_posix()):file_binding(p.read_bytes())
               for root in ('source', 'input') for p in sorted((stage/root).rglob('*')) if p.is_file()},
        create_argv=create_argv(stage), lifecycle_cap_seconds=1800, internal_operation_cap_seconds=1740,
        evaluation_cap_seconds=60, root_go_required=True,
        claim='Unresolved evaluator diagnostics only; no admission, matched accuracy, clinical or study badge')
    save(stage/'invocation.json', spec)
    print(json.dumps(dict(stage=str(stage), invocation_sha256=digest(canonical(spec)),
        expected_binding_sha256=digest(canonical(binding)), evaluations=128,
        independent_groups=32, status='prepared_only_not_executed'), indent=2))
    return stage


def run(stage, token, *, lifecycle=None, clock=time.monotonic):
    stage = Path(stage).resolve()
    raw = (stage/'invocation.json').read_bytes()
    if digest(raw) != token:
        raise ValueError('independent root-approved invocation hash required')
    spec = json.loads(raw)
    if str(stage) != spec['stage']:
        raise ValueError('stage relocation denied')
    for relative, item in spec['files'].items():
        data = (stage/relative).read_bytes()
        if file_binding(data) != item:
            raise ValueError('frozen file integrity mismatch: '+relative)
    # Authenticate expected through the external invocation token, then compare
    # independent semantic bindings at the actual worker file seam as well.
    from services.evaluator.restricted_refinement import load_inputs
    load_inputs(stage/'input/workload.json', stage/'input/expected-binding.json',
        spec['files']['input/expected-binding.json']['sha256'], stage/'input/history.json', stage/'source')
    if create_argv(stage) != spec['create_argv'] or spec['lifecycle_cap_seconds'] != 1800:
        raise ValueError('frozen operation policy mismatch')
    save(stage/'attempt-reserved.json', dict(invocation_sha256=token))
    if lifecycle is None:
        loader = importlib.util.spec_from_file_location('frozen_analysis_lifecycle',
            stage/'source/tooling/foundation/analysis_lifecycle.py')
        lifecycle = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(lifecycle)
    deadline = clock()+1800
    attempt = stage/'execution'
    attempt.mkdir(exist_ok=False)
    cid = None
    try:
        created = lifecycle.command(spec['create_argv'], check=False, deadline=deadline)
        (attempt/'create.stdout').write_bytes(created.stdout)
        (attempt/'create.stderr').write_bytes(created.stderr)
        if created.returncode:
            raise RuntimeError('container create failed; preserve attempt; no retry')
        cid = lifecycle.require_cid(created.stdout.decode().strip())
        save(attempt/'created.json', dict(cid=cid, deadline=deadline))
        terminal = lifecycle.supervise(cid, attempt/'supervision', deadline)
        save(attempt/'terminal.json', terminal)
    finally:
        manifest = {p.relative_to(stage).as_posix():file_binding(p.read_bytes())
                    for p in sorted(stage.rglob('*')) if p.is_file()
                    and p.name != 'raw-manifest.json' and '__pycache__' not in p.parts}
        save(stage/'raw-manifest.json', dict(invocation_sha256=token, cid=cid, files=manifest))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    p = commands.add_parser('prepare'); p.add_argument('--name', required=True)
    p = commands.add_parser('run'); p.add_argument('--stage', type=Path, required=True); p.add_argument('--token', required=True)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.name)
    else:
        run(args.stage, args.token)
