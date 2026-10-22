"""Durable bounded manifests for the two completed owned jobs."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HELPER = HERE.with_name('poc-n-ar-helper-8464')
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
rows = [json.loads(line) for line in (HERE/'run/profile-events.jsonl').read_text().splitlines()]
pre_enter = next(r for r in rows if r.get('phase') == 'core.rewrite_pregrad' and r['kind'] == 'phase-enter')
pre_exit = next(r for r in rows if r.get('phase') == 'core.rewrite_pregrad' and r['kind'] == 'phase-exit')
stacks = [r for r in rows if r['kind'] == 'python-stacks' and pre_enter['elapsed'] < r['elapsed'] < pre_exit['elapsed']]
summary = dict(phases=[r for r in rows if r['kind'] != 'python-stacks'], pregrad_stack_count=len(stacks),
    all_pregrad_stacks_local_greedy_distributor=all('local_greedy_distributor' in ''.join(sum(r['threads'].values(), [])) for r in stacks),
    downstream_stack_classification=['FunctionGraph import at elapsed241.5135', 'MergeOptimizer/remove_client at elapsed257.1224 and272.5729'],
    no_compiled_gradient=True, no_gradient_value=True, no_fit=True)
(HERE/'run/phase-summary.json').write_text(json.dumps(summary, sort_keys=True, indent=2)+'\n')

# Original probe and all four original input files are copied unchanged. The
# next reviewer stamps its exact reviewed execution head into a NEW manifest;
# this package does not start or authorize the full qualification.
qualification = HERE.with_name('poc-n-compile-repair-qualification')
qualification.mkdir(exist_ok=True)
prep = HERE/'source/artifacts/user-reports/poc-n-symbolic-e6d5-prep'
shutil.copyfile(prep/'probe.py', qualification/'original-probe.py')
shutil.copytree(prep/'frozen', qualification/'frozen', dirs_exist_ok=True)
original_manifest = json.loads((HERE/'original-run/input-manifest.json').read_bytes())
files = dict(original_manifest['files'])
for name in files:
    if not name.startswith('artifacts/'):
        files[name] = digest(REPO/name)
template = dict(source=None, numeric_source_checkpoint='8464c8f1d047be31fdb2ee3ec6767fcb477dca07',
    image=original_manifest['image'], files=files,
    status='not-executed; requires exact-head/base Astra readiness and root authorization',
    layout='Copy original-probe.py and frozen/ under /source/artifacts/user-reports/poc-n-symbolic-e6d5-prep/; stamp reviewed HEAD as source in a new input-manifest.json there; original probe bytes and compile options unchanged')
(qualification/'input-manifest-template.json').write_text(json.dumps(template, sort_keys=True, indent=2)+'\n')

paths = ['methods/nof1/model.py','tests/methods/test_nof1_symbolic.py','methods/measurement.py',
    'contracts/domain/nof1_config.py','contracts/domain/protocol_request.py','contracts/domain/protocol_analysis.py',
    'tooling/foundation/pa3_monitor.py','tooling/foundation/pa3-cvm-policy.json']
checkpoints = ['8464c8f1d047be31fdb2ee3ec6767fcb477dca07','2b854a6e2f92075f4f1b612aac851d1d8e2130c9']
identities = {ref: {name: subprocess.check_output(['git','rev-parse',ref+':'+name],cwd=REPO,text=True).strip() for name in paths} for ref in checkpoints}
assert identities[checkpoints[0]] == identities[checkpoints[1]]
identity = dict(base='393edc9e9e80fc303a50e99e061e2c266bbd688e', merge=checkpoints[1],
    source_checkpoint=checkpoints[0], merge_numeric_identities_unchanged=True, git_blobs=identities,
    sha256={name:digest(REPO/name) for name in paths})
(HERE/'merged-source-identities.json').write_text(json.dumps(identity, sort_keys=True, indent=2)+'\n')

for folder, excluded in [(HERE, {'source','pinned-library'}), (HELPER, {'source'}), (qualification, set())]:
    files = []
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or any(part in excluded for part in path.relative_to(folder).parts):
            continue
        if path.name in {'raw-manifest.json','source.tar','source-e6d5.tar'}:
            continue
        files.append(dict(name=path.relative_to(folder).as_posix(), bytes=path.stat().st_size, sha256=digest(path)))
    manifest = dict(folder=folder.name, files=files)
    (folder/'raw-manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2)+'\n')
    print(json.dumps(dict(folder=folder.name, files=len(files), manifest_sha256=digest(folder/'raw-manifest.json'))))
print(json.dumps(dict(pregrad_stack_count=summary['pregrad_stack_count'], all_pregrad_stacks_local_greedy_distributor=summary['all_pregrad_stacks_local_greedy_distributor'])))
