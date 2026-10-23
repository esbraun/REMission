# Bounded first cloud launch packet

Historical proposal, executed 2026-10-23 UTC; see the current binding below. Owner `/root/cloud_launch_plan_astra`, root-verified Astra/medium, branch `docs/poc-cloud-launch-plan-20261023`, isolated checkout `C:/Users/erics/Documents/Projects/REMission-worktrees/cloud-launch-plan-a-261023`, starting base `8f9e5296a3c1371a9924240009ad4920751e23ca`. This planning worker changed no resources or IAM, pushed no images, ran no workloads and read no secrets. This supplements the [runbook](poc-cloud-simulation-runbook-20261023.md) and [CS ledger](poc-cloud-simulation-ledger-20261022.md); it does not replace their account, disk, guard or acceptance contracts.

## Integration update

The [definitive deployed handoff](evidence/cloud-first-deploy-20261023/README.md) now records source PR40 merge286, independently accepted source/operational/publication bindings, actual registry digests and VM pulls, host/helper hashes, disk guard, trusted TLS/auth, both browser workflows and real container/VM persistence. Final CS4 deployed-evidence review and documentation integration remain pending. Historical raw proposal/checkpoint files remain unchanged. No training/fitting occurred.

The following proposal requirements describe the execution contract. Its prior unresolved prerequisites were satisfied by observed receipts or root's accepted bounded billing/delivery bindings: $5 incremental48h, existing $20 monthly budget/static alerts, current spend unknown, root billing/cleanup owner. Absolute STOP is `2026-10-25T04:24:25Z` and must not be extended. Renewals, backup/restore, previous-version rollback and teardown remain unperformed. The final handoff defines observed scope and limits.

## Decision and remaining dependencies

Launch the existing FastAPI/React app, private synthetic generator and pinned Caddy on one `e2-small` in `us-central1-a`, with 20GiB `pd-standard` boot and 10GiB retained `pd-standard` data. Preserve one SQLite writer. No fitting, training, learner, evaluator or new infrastructure framework is required.

Root's accepted discovery establishes profile `remission-poc`, project **`remission-poc-esbraun`**, project number **`302481784991`**, billing enabled, existing registry/runtime account, all 28 selected deployment permissions, and Compute/IAP/OS Login APIs enabled. Do not re-enable or poll the historical API operation. Zone UP, Debian image `debian-cloud/debian-12-bookworm-v20261014` ID `3188631002576736407`, x86_64 READY, default VPC ID `8310840357343948094`, regional subnet ID `5223357826184211765` (`10.128.0.0/20`, IPv4) and zero-usage quota snapshot are already evidenced. These facts supersede stale unresolved statements in the runbook, without claiming resource capacity reservation. Latest direct user report (forwarded by root) confirms `roles/artifactregistry.reader` granted and verified for `remission-poc-runtime@remission-poc-esbraun.iam.gserviceaccount.com` on repository `remission` in `us-central1`, plus both regional and global quota headroom; no quota increase is needed. The user also updated local project configuration and saved evidence. These prerequisites are resolved with source=direct user report; the bounded local readiness summary is linked above. Do not repeat the grant or quota work. This prerequisite paragraph predates execution: both images are now published and actual VM pulls passed, as bound in the handoff.

Two actual findings refine execution. The selected firewall read found unrestricted default SSH/RDP and internal all-port allowances at priority 65534. An IAP allow alone would **not** restrict SSH. Before creating the VM, add only a unique-tag deny-all ingress at priority 1000 plus IAP SSH allow at 900; add public 80/443 allow at 900 only after provisioning. Preserve existing rules. This overrides those observed VPC defaults; actual effective ingress and IAP access still require verification because this was not an organization-policy audit. [Google firewall priority semantics](https://docs.cloud.google.com/firewall/docs/firewalls#priority).

The permitted image inspection returned app 2,097,045,866 bytes/31 layers and generator 2,095,834,899 bytes/19 layers: 3.91GiB summed uncompressed, before shared-layer savings. A 20GiB boot disk leaves room for OS, extraction and proxy; 10GiB data is an initial synthetic-workload allowance, not measured capacity. Do not build on the VM. Measure actual disk use and memory during two-user panel generation/advance; retain at least 20% disk free and record `MemAvailable`, container peaks and OOM events. Two 2GiB container limits do not establish fit on a 2GiB VM. If it fails, stop and revise the bounded size/cost proposal; do not silently resize.

The original execution dependencies were final source/review, registry publication/pulls, host/helper, billing/delivery and allocated-origin/TLS/browser/persistence. These now have the bindings in the handoff; current spend and renewal/recovery/rollback remain explicitly unobserved. Root can resolve the billing/delivery facts from existing context where available; this packet invents neither approval nor an extra human acceptance gate.

## Finite initial exposure and cost

Use a fixed UTC deadline **48 hours after allocation begins**, with `--termination-time="$STOP_AT" --instance-termination-action=STOP`. SDK590 source and [Compute documentation](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime) support this on standard VMs. `--max-run-duration=48h` also exists, but stop/start resets that duration; the absolute deadline survives restarts and prevents starts after expiry. Reboot/reset does not extend it. Automatic stopping may begin up to 30 seconds late. Record the returned scheduling fields; never clear the deadline during tests.

Frozen cost note `0a2529fe6e02b25969ea87ba0cbb178fe680e0d2` gives e2-small $0.016752855/h, in-use IPv4 $0.005/h and 30GiB standard PD $0.00164385/h: **about $1.13 for 48 hours**. Propose **$5 incremental launch envelope**, including $2 allowance for registry/egress/logs and residual contingency; root accepted this bounded envelope under the recorded $20 monthly budget with current spend/headroom unknown; no available-balance proof is claimed. The old $15 Cloud Run setting is not a Compute cap. Billing enabled does not establish that remaining balance or owner.

At the deadline, stop if necessary, remove this VM/public rules and release its address; retain only the 10GiB data disk for **seven additional days**, then explicitly delete it or record a separately accepted retention extension. Seven days of that disk is about $0.092 at the frozen rate. STOP bounds compute, not storage, static-IP or other project charges; a missed cleanup keeps accruing charges and must be reported. A static address still attached to a stopped VM remains **in use** ($0.005/h in the frozen note); after VM deletion/detachment it is **unused** until released (currently $0.01/h). Disk billing also continues while stopped. [Official IP classification/pricing](https://cloud.google.com/vpc/network-pricing), [stop/suspend pricing](https://docs.cloud.google.com/compute/docs/instances/suspend-stop-reset-instances-overview). This lifecycle has an operator cleanup obligation, not a guaranteed billing cap or new scheduler. Observe actual project spend before launch and after billing data arrives; record unknown/lagged amounts honestly.

## Execution and acceptance order

1. Bind the later independently accepted main/source head, exact review head/base, source-byte closure, successful corrected proxy qualification and existing local app/generator proof. `8f9e5296a3c1371a9924240009ad4920751e23ca` is a planning base: its corrected proxy attempt failed before start on Docker capability spelling. The later strict repair and separately authorized offline pass are linked above; preserve that actual source/input provenance. Push only qualified existing app/generator images after authorization, capture registry manifest digests and provenance; local image IDs are not registry digests. Keep Caddy's existing pinned amd64 manifest.
2. Reuse the user-verified repository reader binding and quota headroom; create tagged firewall boundary, disks/address/VM with fixed deadline. Capture IDs, scheduling, attachment autoDelete=false and actual IPv4. Install and record host tools once using appendix; no install-on-reboot or live-restore. Actual versions and a successful pull qualify this host, not this paper plan.
3. Follow the runbook's fail-closed new-disk identity/signature checks and one-time ext4 format. Bind observed UUID/IP, accepted source and three registry digests in the seven-field renderer; retain manifest SHA externally. Verify root-owned installed assets. Pull as root with the VM service-account helper. Initialize through the existing offline admin contract; create two distinct accounts using hidden password prompts and private delivery. Never capture passwords or reuse fixture credentials.
4. Add public proxy ingress, attach the accepted startup script and start through its guard. Prove actual browser trust plus no-SNI IP SAN/chain verification. Reuse TLS note `9554aa68b735e9499f4cc9c3d12e8add49dc3a0d`; keep port80 for shortlived-certificate renewal, persist Caddy state, capture expiry/renewal health. There is no DNS dependency.
5. Complete CS-T3â€“T8: unauthenticated denial; login/logout/expiry/reset/CSRF; two-owner isolation; generated panel, rationale, explicit decision, day14 advance and history; no analysis jobs. Compare persisted identifiers/history after reload, container recreation and same-disk VM reboot. Capture memory/disk/latency and failed checks. Do not accept just health/TestClient success. Review exact deployed source/config/digests/evidence independently; synthetic engineering proof makes no clinical efficacy or accuracy claim.

## Exact command appendix (future authorized operator)

Commands below supplement the existing runbook's full disk/admin/render/start/verification procedures. Run sequentially, fail closed, without shell tracing. On Windows use the already qualified SDK590 Python launcher from evidence `receipt.json`; `gc` below denotes that launcher plus `--quiet --configuration=remission-poc --project=remission-poc-esbraun`, not a fresh login. Preserve its process-only timeout20/prompt/logging/API-enable safeguards and bounded parent supervision. On a qualified Bash operator host:

```bash
set -euo pipefail
gc() { gcloud --quiet --configuration=remission-poc --project=remission-poc-esbraun "$@"; }
PROJECT=remission-poc-esbraun
REGION=us-central1
ZONE=us-central1-a
VM=remission-sim-20261023
TAG=remission-sim-20261023
DISK=remission-sim-data-20261023
ADDRESS_NAME=remission-sim-ip-20261023
STOP_AT=$(date -u -d '+48 hours' +%Y-%m-%dT%H:%M:%SZ)
printf '%s\n' "$STOP_AT" > launch-stop-at.txt
# Repository reader and regional/global quota prerequisites are already user-verified.
gc compute firewall-rules create "$VM-deny-ingress" --network=default --direction=INGRESS \
  --priority=1000 --target-tags="$TAG" --source-ranges=0.0.0.0/0 --action=DENY --rules=all
gc compute firewall-rules create "$VM-iap-ssh" --network=default --direction=INGRESS \
  --priority=900 --target-tags="$TAG" --source-ranges=35.235.240.0/20 --action=ALLOW --rules=tcp:22
gc compute disks create "$DISK" --zone="$ZONE" --type=pd-standard --size=10GB
gc compute addresses create "$ADDRESS_NAME" --region="$REGION"
gc compute instances create "$VM" --zone="$ZONE" --machine-type=e2-small \
  --image=debian-12-bookworm-v20261014 --image-project=debian-cloud \
  --boot-disk-size=20GB --boot-disk-type=pd-standard \
  --network=default --subnet=default --address="$ADDRESS_NAME" \
  --service-account=remission-poc-runtime@remission-poc-esbraun.iam.gserviceaccount.com \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --metadata=enable-oslogin=TRUE --tags="$TAG" \
  --disk="name=$DISK,device-name=remission-data,mode=rw,boot=no,auto-delete=no" \
  --termination-time="$STOP_AT" --instance-termination-action=STOP
gc compute instances describe "$VM" --zone="$ZONE" \
  --format='json(id,status,scheduling,disks.deviceName,disks.source,disks.autoDelete,networkInterfaces.accessConfigs.natIP,tags.items)'
gc compute ssh "$VM" --zone="$ZONE" --tunnel-through-iap
```

On the new Debian host, inspect package conflicts first; do not remove unrelated packages blindly. This follows [Docker's official Debian repository install](https://docs.docker.com/engine/install/debian/) (Debian12 supported) and [Debian Python3 package](https://packages.debian.org/bookworm/python3). Package versions are resolved once from signed repositories, recorded and held; this is pending host qualification, not a claim of pretested versions.

```bash
set -euo pipefail
test "$(dpkg --print-architecture)" = amd64
. /etc/os-release
test "$ID:$VERSION_CODENAME" = debian:bookworm
sudo apt-get update
sudo apt-get install -y ca-certificates curl python3 e2fsprogs util-linux
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
printf '%s\n' 'Types: deb' 'URIs: https://download.docker.com/linux/debian' \
  'Suites: bookworm' 'Components: stable' 'Architectures: amd64' \
  'Signed-By: /etc/apt/keyrings/docker.asc' | sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null
sudo apt-get update
packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
pinned=()
for p in "${packages[@]}"; do
  v=$(apt-cache policy "$p" | awk '/Candidate:/ {print $2}')
  test -n "$v" && test "$v" != '(none)'
  pinned+=("$p=$v")
done
printf '%s\n' "${pinned[@]}" > docker-package-selection.txt
sudo apt-get install -y "${pinned[@]}"
sudo apt-mark hold "${packages[@]}"
dpkg-query -W python3 e2fsprogs util-linux "${packages[@]}" > host-package-versions.txt
test -x /usr/bin/docker
sudo docker version
sudo docker compose version
python3 --version
sudo docker info --format '{{.LiveRestoreEnabled}}' # Require false.
```

Use the [official standalone credential helper instructions](https://docs.cloud.google.com/artifact-registry/docs/docker/authentication#standalone-helper) and pinned [v2.1.29 release](https://github.com/GoogleCloudPlatform/docker-credential-gcr/releases/tag/v2.1.29), ADC from attached VM service account. No account key, OAuth login or token-print test. Record download hash/version; verify the release checksum before installation when preparing the execution receipt. The official release checksum binding is supplied above; verifying downloaded archive bytes and the actual installed host remains required.

```bash
HELPER_SHA256=9e676f2233b93e763276101dd8530e634aebf5d31d5581f64e7ffa978aefa0d8
curl -fsSL https://github.com/GoogleCloudPlatform/docker-credential-gcr/releases/download/v2.1.29/docker-credential-gcr_linux_amd64-2.1.29.tar.gz -o helper.tar.gz
printf '%s  helper.tar.gz\n' "$HELPER_SHA256" | sha256sum -c -
tar -xzf helper.tar.gz docker-credential-gcr
sudo install -m 0755 docker-credential-gcr /usr/bin/docker-credential-gcr
sudo docker-credential-gcr version
sudo docker-credential-gcr configure-docker --registries=us-central1-docker.pkg.dev
# Now perform the existing runbook disk/render/pull/offline account steps.
```

Back on operator host only after accounts are ready:

```bash
gc compute firewall-rules create "$VM-https" --network=default --direction=INGRESS \
  --priority=900 --target-tags="$TAG" --source-ranges=0.0.0.0/0 --action=ALLOW --rules=tcp:80,tcp:443
gc compute instances add-metadata "$VM" --zone="$ZONE" \
  --metadata-from-file=startup-script=rendered-cloud/startup.sh
# Start via runbook guard, then test actual IP. PUBLIC_IPV4 is allocated, not invented.
openssl s_client -connect "$PUBLIC_IPV4:443" -noservername \
  -verify_ip "$PUBLIC_IPV4" -verify_return_error </dev/null
# Host observations during generation and after persistence tests:
# free -b; df -B1 / /srv/remission; sudo docker stats --no-stream
# sudo docker system df; sudo journalctl -k --since '<launch UTC>' (selected OOM lines only)
```

At the fixed deadline, record automatic STOP or stop explicitly if still running; delete only this exact VM after confirming retained-data autoDelete=false, then release its address and remove only its three rules. Preserve the disk identity/UUID and evidence. The following are proposed lifecycle actions, not permission to delete unrelated or preexisting resources:

```bash
gc compute instances delete "$VM" --zone="$ZONE" --keep-disks=data
gc compute addresses delete "$ADDRESS_NAME" --region="$REGION"
gc compute firewall-rules delete "$VM-https" "$VM-iap-ssh" "$VM-deny-ingress"
# Seven days later, only after confirming this exact synthetic retained disk:
gc compute disks delete "$DISK" --zone="$ZONE"
```

## Evidence and handoff

New raw selected receipts: `artifacts/launch-plan-evidence/{firewall,images}.{stdout,stderr}.txt`, collector and `receipt.json`; SHA-256/Git blob manifest accompanies them. Exactly one SDK read and one selected Docker inspection were performed; no second SDK call was needed. Source evidence: metadata report `a962583a7fd176536ab7bdd70fec977d9280b334`, manifest `7641f61b4669d99167db50ca301870c5716ebe0b`; quota report `16c22fb21d7143aa3a188bb4bf1d55e3cf69bd2c`, manifest `a442d31303c7c4c81aff14df150ad7fdb6f77fd1`; repository IAM proposal `898b98084d5b38097924a29a06f37bb01d284c95`. That historical IAM proposal is superseded by the direct user report of the completed and verified grant; it is retained only for provenance, not as an execution dependency. Latest user-reported regional/global quota checks likewise supersede the earlier regional-only snapshot. The worker did not use its second permitted SDK read; the bounded local readiness summary above supplies the locator result without repeated cloud checks.

Next Sol execution uses the accepted critique above and needs root authorization bound to the final accepted source/review and image/config manifest, qualified helper checksum, this unique resource set, $5/48-hour envelope with current remaining-budget fact and billing responsibility, account delivery handling, publication/verification and cleanup obligations. It may then perform the qualified existing-image push, host setup, allocation, provisioning and CS3 checks. No repeat reader grant or quota increase is included. This packet itself authorizes none of those actions. No PR/merge or canonical-ledger status change is included in this planning branch; integrate and refresh stale runbook facts through the normal independently reviewed source owner.
