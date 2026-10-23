"""ROOTGO PHASE1: selected stock publication commands and bounded receipts only."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
sdk = Path('C:/Users/erics/Documents/Projects/REMission-worktrees/cloud-generator-build-sol-261023/artifacts/cloud-sdk/590.0.0/google-cloud-sdk')
source = '286aa87a10a24ad9925c90be033e7d8c0570d99b'
tag = 'first-286aa87a10a2'
repository = 'us-central1-docker.pkg.dev/remission-poc-esbraun/remission'
images = {'fixture': 'sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72',
          'generator': 'sha256:d64907d76a2810d2e6cad8acaa012f3df132ced69bfe2636c7eb07f7090b4eee'}
env = os.environ.copy()
for key in ('DOCKER_AUTH_CONFIG', 'DOCKER_CONFIG', 'DOCKER_CONTEXT', 'DOCKER_HOST', 'DOCKER_CERT_PATH', 'DOCKER_TLS_VERIFY'):
    env.pop(key, None)
env.update(CLOUDSDK_ACTIVE_CONFIG_NAME='remission-poc', CLOUDSDK_CORE_PROJECT='remission-poc-esbraun',
           CLOUDSDK_CORE_DISABLE_PROMPTS='true', CLOUDSDK_CORE_DISABLE_USAGE_REPORTING='true',
           CLOUDSDK_CORE_DISABLE_FILE_LOGGING='true', CLOUDSDK_COMPONENT_MANAGER_DISABLE_UPDATE_CHECK='true',
           CLOUDSDK_CORE_HTTP_TIMEOUT='20', CLOUDSDK_CORE_LOG_HTTP='false', CLOUDSDK_CORE_VERBOSITY='error',
           CLOUDSDK_CORE_SHOULD_PROMPT_TO_ENABLE_API='false', PYTHONDONTWRITEBYTECODE='1',
           CLOUDSDK_PYTHON=str(sdk/'platform/bundledpython/python.exe'),
           CLOUDSDK_PYTHON_ARGS='-S -B', CLOUDSDK_PYTHON_SITEPACKAGES='0')
env['PATH'] = str(sdk/'bin') + os.pathsep + env['PATH']
gc = [str(sdk/'platform/bundledpython/python.exe'), '-S', '-B', str(sdk/'lib/gcloud.py'),
      '--quiet', '--configuration=remission-poc', '--project=remission-poc-esbraun']
docker = shutil.which('docker', path=env['PATH'])
if not docker:
    raise RuntimeError('docker_cli_missing')

receipts = []
def call(name, argv, timeout=60):
    # No credential-helper get/token command or secret stdin is used here.
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick = time.monotonic()
    child = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        child.kill()
        stdout, stderr = child.communicate()
    for suffix, data in (('stdout', stdout), ('stderr', stderr)):
        (out/(name+'.'+suffix)).write_bytes(data)
    receipt = dict(name=name, argv=argv, pid=child.pid, started_utc=start,
                   ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   elapsed_seconds=time.monotonic()-tick, returncode=child.returncode,
                   timeout=timed_out, client_reaped=True, timeout_seconds=timeout,
                   remote_operation_state='unknown_after_client_timeout' if timed_out else 'client_completed')
    receipts.append(receipt)
    (out/(name+'.receipt.json')).write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({'operation': name, 'exit': child.returncode, 'timeout': timed_out,
                      'elapsed_seconds': receipt['elapsed_seconds']}), flush=True)
    if timed_out or child.returncode:
        raise RuntimeError(name+'_failed_preserved_no_retry')
    return stdout

try:
    assert call('source-head', ['git','rev-parse','HEAD']).decode().strip() == source
    assert not call('tracked-status', ['git','status','--porcelain','--untracked-files=no']).strip()
    assert call('integrated-tree', ['git','rev-parse','HEAD^{tree}']) == call('reviewed-tree', ['git','rev-parse','f43e327714b803760c1fac3df209c604846f894c^{tree}'])
    closures = json.loads((root/'docs/implementation/evidence/cloud-simulation-prep-20261023/image-closures.json').read_bytes())
    qualification = {}
    remap = {'/app/boundary_probe.py': 'tooling/foundation/consumer_probe.py',
             '/app/observed_v2_probe.py': 'tooling/foundation/observed_v2_probe.py'}
    for role, selected in images.items():
        assert closures[role]['image'] == selected
        checked = []
        for image_path, expected in closures[role]['files'].items():
            relative = remap.get(image_path, image_path.removeprefix('/app/'))
            physical = hashlib.sha256((root/relative).read_bytes()).hexdigest()
            git_bytes = subprocess.check_output(['git','show',source+':'+relative],cwd=root)
            canonical = hashlib.sha256(git_bytes).hexdigest()
            if expected not in (physical, canonical):
                raise RuntimeError('source_closure_mismatch:'+relative)
            checked.append({'path': relative, 'expected': expected, 'physical': physical, 'git_blob_bytes': canonical})
        qualification[role] = {'image': selected, 'original_source': closures[role]['source_commit'], 'files': checked}
    (out/'source-closure-qualification.json').write_text(json.dumps(qualification,indent=2)+'\n')
    endpoint = call('docker-selected-context', [docker,'context','inspect','desktop-linux','--format','{{.Endpoints.docker.Host}}']).decode().strip()
    if endpoint != 'npipe:////./pipe/dockerDesktopLinuxEngine':
        raise RuntimeError('unexpected_local_engine_endpoint')
    private = out/'private/docker'
    private.mkdir(exist_ok=False)
    (private/'config.json').write_text('{"credHelpers":{"us-central1-docker.pkg.dev":"gcloud"}}\n')
    dp = [docker,'--config',str(private),'--host',endpoint]
    inspect_format = '{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"RepoDigests":{{json .RepoDigests}}}'
    rows = call('selected-images', dp+['image','inspect','--format',inspect_format]+list(images.values())).decode().splitlines()
    for row, expected in zip(rows, images.values(), strict=True):
        observed = json.loads(row)
        assert (observed['Id'],observed['Os'],observed['Architecture']) == (expected,'linux','amd64')
    result = {'source':source,'tag':tag,'registry':repository,'publications':{}}
    for role, selected in images.items():
        name = 'simulation-app' if role == 'fixture' else 'simulation-generator'
        ref = repository+'/'+name+':'+tag
        call(role+'-tag',dp+['image','tag',selected,ref])
        pushed = call(role+'-push',dp+['image','push',ref],timeout=900).decode()
        matches = re.findall(r'digest: (sha256:[0-9a-f]{64})',pushed)
        if len(matches) != 1:
            raise RuntimeError('push_digest_ambiguous:'+role)
        digest = matches[0]
        observed = json.loads(call(role+'-registry',gc+['artifacts','docker','images','describe',ref,
                                      '--format=json(image_summary.digest,image_summary.fully_qualified_digest)']))
        summary = observed.get('image_summary',{})
        assert summary.get('digest') == digest
        immutable = repository+'/'+name+'@'+digest
        assert summary.get('fully_qualified_digest') == immutable
        local = json.loads(call(role+'-published-local',dp+['image','inspect','--format',inspect_format,ref]))
        assert local['Id'] == selected
        assert immutable in local['RepoDigests']
        result['publications'][role] = {'selected_image_id':selected,'tag':ref,'registry_digest':digest,'immutable_ref':immutable,'push_registry_local_agree':True}
        (out/'publication-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'published':role,'immutable_ref':immutable}),flush=True)
    result['status'] = 'PHASE1-two-images-published-verified-PHASE2-HOLD'
    (out/'publication-result.json').write_text(json.dumps(result,indent=2)+'\n')
finally:
    (out/'publication-receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
    files = []
    for path in out.iterdir():
        if path.is_file() and path.name != 'publication-raw-manifest.json':
            files.append({'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (out/'publication-raw-manifest.json').write_text(json.dumps(files,indent=2)+'\n')
