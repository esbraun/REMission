# Concrete first deployment binding

Prepared only. No cloud, Docker, network, credential or runtime command has run.
Root owns billing, cleanup and release authorization. Wait for ROOTGO plus the
integrated accepted source/review binding, then update this worker's own branch
to that integrated commit and verify HEAD, ancestry, clean tracked state and
unchanged relevant source closures. Do not modify another live worktree.
`binding.json` contains the single selected resource set and unresolved outputs.
The accepted plan is critique ea618b86dee95a61577c7beeeca91e8d51ac3fb5,
manifest 831454bcbb86edc46b06e6974667f0bc59a6e6a8. There is no new human
approval gate. Failed commands and resources remain preserved; no automatic retry
or cleanup, no PR/merge, no builds or unnecessary local pulls.

## Operator execution and selected receipts

Run stock commands sequentially from this checkout. Use the qualified SDK root:
`C:/Users/erics/Documents/Projects/REMission-worktrees/cloud-generator-build-sol-261023/artifacts/cloud-sdk/590.0.0/google-cloud-sdk`.
`gc` below denotes precisely its `platform/bundledpython/python.exe -S -B
lib/gcloud.py --quiet --configuration=remission-poc
--project=remission-poc-esbraun`, with absolute paths and list arguments.

Reuse only these fixed child-process settings from the qualified collector:
`CLOUDSDK_ACTIVE_CONFIG_NAME=remission-poc`,
`CLOUDSDK_CORE_PROJECT=remission-poc-esbraun`,
`CLOUDSDK_CORE_DISABLE_PROMPTS=true`,
`CLOUDSDK_CORE_DISABLE_USAGE_REPORTING=true`,
`CLOUDSDK_CORE_DISABLE_FILE_LOGGING=true`,
`CLOUDSDK_COMPONENT_MANAGER_DISABLE_UPDATE_CHECK=true`,
`CLOUDSDK_CORE_HTTP_TIMEOUT=20`, `CLOUDSDK_CORE_LOG_HTTP=false`,
`CLOUDSDK_CORE_VERBOSITY=error`,
`CLOUDSDK_CORE_SHOULD_PROMPT_TO_ENABLE_API=false`,
`PYTHONDONTWRITEBYTECODE=1`. Do not dump the inherited environment.

For each nonsecret command save argv, UTC start/end, exit/timeout, selected
stdout/stderr, elapsed time and SHA256 in this directory, not a shared checkout.
Use bounded foreground subprocess supervision: local/SDK selected reads 60s,
allocation mutations 300s, pushes/pulls/package installation 900s, remote
provisioning 300s, startup 240s; HTTP timeout remains20s. Tool calls yield at
30s and poll at <=60s. On timeout terminate/reap the client and record unknown
remote operation outcome; inspect that exact operation/resource before proceeding,
without repeating a mutation. A client timeout is not proof that remote work ended.
No HTTP debug logs, token/credential output, secret admin stdin, cookies or CSRF
headers/bodies belong in evidence. Keep unredacted session state only in private
memory/files. Capture selected Docker identity/state fields, never broad inspect
Env/config or global Docker/gcloud configuration.

Before publication bind integrated source and both actual-byte closure manifests
from `docs/implementation/evidence/cloud-simulation-prep-20261023/image-closures.json`.
Compare every repo-backed copied source path with final source, not just the Git
label. App/generator IDs and original build source remain separate from the later
release/config source; no assertion that the earlier image was built at final HEAD.
Reuse actual local fixture proof and offline Caddy proof from source042; no rerun.

## Publication

Create this directory's `private` folder with inherited ACLs removed and only
current Windows user FullControl plus SYSTEM FullControl, propagating to children.
Verify effective ACL and `git check-ignore` before placing secrets there. No secret
exists yet. Use `private/docker/config.json` containing only
`{"credHelpers":{"us-central1-docker.pkg.dev":"gcloud"}}`.
Pass `docker --config <absolute-private/docker>` on each publication command;
never configure global authentication. Select the existing qualified Linux engine
using `docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'`
and use only that returned endpoint with explicit `--host`; do not copy context
credential/TLS material. Stop if this is not the existing local Linux engine.
Process-only PATH prepends the fixed SDK `bin`; set `CLOUDSDK_PYTHON` to its
bundled python, `CLOUDSDK_PYTHON_ARGS=-S -B` and
`CLOUDSDK_PYTHON_SITEPACKAGES=0`. The inspected official
`docker-credential-gcloud.cmd` calls `gcloud.cmd auth docker-helper`; its token
stdout flows only into Docker's internal credential-helper pipe. Never invoke
`get` or `print-access-token` as a receipt command. No login or key download.

After ROOTGO choose `RELEASE_TAG=first-<final-integrated-source-first12>` and run:

```text
docker image inspect --format '{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}}}' sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72 sha256:d64907d76a2810d2e6cad8acaa012f3df132ced69bfe2636c7eb07f7090b4eee
docker image tag sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72 us-central1-docker.pkg.dev/remission-poc-esbraun/remission/simulation-app:RELEASE_TAG
docker image tag sha256:d64907d76a2810d2e6cad8acaa012f3df132ced69bfe2636c7eb07f7090b4eee us-central1-docker.pkg.dev/remission-poc-esbraun/remission/simulation-generator:RELEASE_TAG
docker --config PRIVATE_DOCKER --host SELECTED_ENDPOINT image push us-central1-docker.pkg.dev/remission-poc-esbraun/remission/simulation-app:RELEASE_TAG
gc artifacts docker images describe us-central1-docker.pkg.dev/remission-poc-esbraun/remission/simulation-app:RELEASE_TAG --format=json(image_summary.digest,image_summary.fully_qualified_digest)
docker --config PRIVATE_DOCKER --host SELECTED_ENDPOINT image push us-central1-docker.pkg.dev/remission-poc-esbraun/remission/simulation-generator:RELEASE_TAG
gc artifacts docker images describe us-central1-docker.pkg.dev/remission-poc-esbraun/remission/simulation-generator:RELEASE_TAG --format=json(image_summary.digest,image_summary.fully_qualified_digest)
```

Require push digest and selected registry result to agree for each image, then bind
immutable refs. Local image IDs are configuration identities, not registry manifest
digests. Do not publish Caddy again; keep the pinned official amd64 manifest.

## Allocation and host

Bind allocation-start UTC and absolute `STOP_AT` 48h later immediately before the
first billable resource; retain that deadline through all later steps. Root binds
$5 incremental exposure with the existing $20 monthly budget and unknown current
spend. Record static alert thresholds50/80/100 and billing lag/current-spend unknown.
No additional billing access research, grant/API enable or quota check is planned.

```text
gc compute firewall-rules create remission-sim-20261023-deny-ingress --network=default --direction=INGRESS --priority=1000 --target-tags=remission-sim-20261023 --source-ranges=0.0.0.0/0 --deny=all
gc compute firewall-rules create remission-sim-20261023-iap-ssh --network=default --direction=INGRESS --priority=900 --target-tags=remission-sim-20261023 --source-ranges=35.235.240.0/20 --allow=tcp:22
gc compute disks create remission-sim-data-20261023 --zone=us-central1-a --type=pd-standard --size=10GB
gc compute addresses create remission-sim-ip-20261023 --region=us-central1
gc compute instances create remission-sim-20261023 --zone=us-central1-a --machine-type=e2-small --image=debian-12-bookworm-v20261014 --image-project=debian-cloud --boot-disk-size=20GB --boot-disk-type=pd-standard --network=default --subnet=default --address=remission-sim-ip-20261023 --service-account=remission-poc-runtime@remission-poc-esbraun.iam.gserviceaccount.com --scopes=https://www.googleapis.com/auth/cloud-platform --metadata=enable-oslogin=TRUE --tags=remission-sim-20261023 --disk=name=remission-sim-data-20261023,device-name=remission-data,mode=rw,boot=no,auto-delete=no --termination-time=STOP_AT --instance-termination-action=STOP
gc compute instances describe remission-sim-20261023 --zone=us-central1-a --format=json(id,status,scheduling,serviceAccounts.email,serviceAccounts.scopes,disks.deviceName,disks.source,disks.autoDelete,networkInterfaces.accessConfigs.natIP,tags.items)
gc compute ssh remission-sim-20261023 --zone=us-central1-a --tunnel-through-iap --command=SELECTED_NONSECRET_HOST_COMMAND
```

Require returned scheduling deadline, account/scope, attachment and IPv4 to match.
Existing-name conflicts fail closed; never adopt an unrelated resource. Confirm
actual IAP access and selected effective ingress after allocation.

Prepared `host-setup.sh` carries the stock Debian/helper commands; it is not run.
Use the launch packet's exact Debian signed-repository host appendix, once:
verify Debian bookworm/amd64, inspect package conflicts, install CA/curl/python3/
e2fsprogs/util-linux, install Docker official repository, resolve and record exact
Docker package versions, install/hold them, record versions and require
LiveRestoreEnabled=false. No build on VM and no installation at reboot.
Download helper v2.1.29 exact official archive URL from packet; require SHA256
9e676f2233b93e763276101dd8530e634aebf5d31d5581f64e7ffa978aefa0d8
before extraction; install `/usr/bin/docker-credential-gcr`, record actual version,
configure only us-central1-docker.pkg.dev as root. ADC uses attached runtime account.
No account key, OAuth login, or token-print check.

## Empty disk, renderer, real pull and offline accounts

Prepared `new-disk-once.sh` carries the stock guarded first-use commands. Require
the external new-disk/attachment identity match before invoking it exactly once.
Match disk creation/attachment IDs with `/dev/disk/by-id/google-remission-data`
and selected `lsblk --paths --output NAME,SIZE,TYPE,FSTYPE,UUID,MOUNTPOINTS`.
Require block device, no wipefs signatures, a single disk node/no partitions and
no mount. Only then run the runbook's one-time `mkfs.ext4 -m 0`, mount nodev,nosuid
at `/srv/remission`, capture actual UUID, create the documented UID10001 0700 app
directories and root0700 proxy directories. Never format existing/reboot state.

Write exactly seven nonsecret renderer fields: two observed registry refs, pinned
proxy ref, final accepted source, actual global IPv4, exact disk device and UUID.
Use existing `prepare.py --config ... --output <fresh-rendered-directory>` then
`--verify`. Retain physical manifest SHA externally. `gc compute scp --recurse
--tunnel-through-iap --zone=us-central1-a <rendered-directory>
remission-sim-20261023:~/rendered-cloud`; compare remote manifest SHA before
installing root-owned `/opt/remission-simulation`; reverify installed assets.

Run exact runbook `sudo docker compose -p remission-simulation -f
/opt/remission-simulation/compose.json pull`. Capture selected RepoDigests,
Id/OS/architecture and require each pulled component to match its accepted digest;
app/generator Id must match qualified local IDs. This actual service-account pull
is the runtime Reader proof. Capture disk use and available memory before start.

With services stopped, use the runbook's unchanged admin Compose command to
`initialize`, create physician-one/physician-two with distinct synthetic display
names, then `verify`. Generate two strong unique passwords only after private ACL
qualification; save only in private/physician-access.json. Supply each by approved
local subprocess stdin pipe through SSH to admin `--password-stdin`; never argv,
environment, shell interpolation, here-document, stdout, chat or evidence. Commands
and result are nonsecret; payload never captured. Stop if transport cannot keep
secret stdin private. Final local credential file is linked after TLS is trusted.

## Public start and deployed acceptance

```text
gc compute firewall-rules create remission-sim-20261023-https --network=default --direction=INGRESS --priority=900 --target-tags=remission-sim-20261023 --source-ranges=0.0.0.0/0 --allow=tcp:80,tcp:443
gc compute instances add-metadata remission-sim-20261023 --zone=us-central1-a --metadata-from-file=startup-script=RENDERED/startup.sh
gc compute ssh remission-sim-20261023 --zone=us-central1-a --tunnel-through-iap --command='sudo bash /opt/remission-simulation/startup.sh'
```

Guard verifies manifest, exact disk UUID/type/mount and bootstrap, then systemd
starts only one app plus private generator and proxy. Check selected unit/container
health, IDs/digests, actual UID/capability/mount/port state; app8765/generator8780
stay unpublished. Verify public HTTPS health, actual browser certificate trust and
IP SAN/no-SNI chain with `openssl s_client -connect IP:443 -noservername
-verify_ip IP -verify_return_error`. Capture certificate issuer/SAN/expiry and
renewal errors; no TLS bypass. Keep port80 and persistent proxy state for renewal.

CS-T3: anonymous reads/writes denied, wrong/unknown account rejected, correct
login, Secure/HttpOnly/SameSite cookie assertions, missing/foreign CSRF/origin
rejection. Receipts include booleans/status codes, never token/header values.

CS-T4: logout and old-session denial, fresh login, password reset with unit stopped
through the unchanged offline admin command and old-session revocation after
restart. Save replacement password privately. Actual configured session lifetime
is1800s; preserve an isolated session privately, perform other tests, then prove
protected denial after its recorded expiry. Do not alter the DB/clock/TTL to fake it.

CS-T5: Playwright MCP actual UI generates default12 seeded panel, selects patient,
records explicit eligible choice/rationale/confirmation, advances day14, inspects
outcomes/history and unavailable analyses; record relevant visible identifiers.
Two owners cannot list/read/mutate the other's panel. Retain original local bounded
2-24/replay/different-seed/causal-path coverage within original scope. Use direct
HTTP for negative seam checks; UI workflow must use visible controls.

CS-T6: save sanitized panel/patient/decision/simulation/history snapshots. Compare
after browser reload; `sudo systemctl restart remission-simulation.service`
(Compose down/up recreates containers); then
`gc compute ssh remission-sim-20261023 --zone=us-central1-a --tunnel-through-iap
--command='sudo systemctl reboot'` on the same retained disk. Record the expected
SSH disconnect, boot identity, disk attachment/UUID and selected file
device/inode identity, healthy service/relogin, no reseed, identical saved history,
then successful next advance. Never alter Store admission identity on failure.

CS-T7: serial Playwright MCP session; keyboard workflow, desktop/narrow screenshots
and accessible chart/table alternatives, failure/no-result display, console and
selected network failure inspection. Tools are discoverable; browser launch itself
remains unexecuted. Follow browser-validation.md; never capture auth payloads.
For login use MCP's supported `browser_run_code_unsafe` to read only the exact
private credential file inside the server process and fill the visible, previously
observed username/password controls; return only a nonsecret success assertion.
No password literal enters tool arguments or returned content. This is private
input handling for the UI, not a hidden workflow mutation. If the server cannot
read this local ACL file, report that concrete transport limitation before exposing
or moving secrets. Sanitize selected network errors; never request auth request
details or full header/body dumps.

Measure `free -b`, `df -B1 / /srv/remission`, `docker stats --no-stream`,
`docker system df` and selected kernel OOM events before/during both users and
after persistence checks. Require >=20% free disk, record MemAvailable/container
peaks/OOM/latency; failure stops for bounded correction, never silent resize.

CS-T8: source/review head/base + final integrated source, original image/build
provenance + published/pulled digests, renderer/admin manifest, resource/disk IDs,
origin, UTC actions and actual CS-T3-T7 results go to independent Astra review.
Root owns PR/integration and user handoff. Unperformed cases remain pending.

## Root-owned deadline cleanup

Absolute STOP remains installed. Root must observe STOP at deadline, remove only
this VM/three rules and release its address; preserve the exact data disk for seven
additional days then record explicit disposition. No automatic cleanup by worker.
STOP alone leaves IP/storage charges; frozen48h base estimate is~$1.13, seven-day
10GiB retention~$0.092, with registry/egress/logs/contingency under $5 envelope.
Current spend stays unknown. Preserve failures and evidence; no unrelated deletes.
