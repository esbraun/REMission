# Google Cloud physician simulation deployment

CS1/CS2 preparation plus a passed bounded local CS-T1 fixture, pending refreshed exact-candidate independent review. [Runtime evidence](evidence/cloud-simulation-prep-20261023/local-fixture-runtime.json) records Linux source/import/UID and TestClient behavior qualification. Cloud/runtime deployment commands below remain unexecuted; deployed CS-T1/CS-T3–T8 remain unpassed. Use the [canonical ledger](poc-cloud-simulation-ledger-20261022.md) and [immediate requirements](../spec/poc-amendment-20261021.md#immediate-physician-simulation-milestone-2026-10-22). This starts the existing app, private generator and HTTPS proxy with one SQLite writer. It performs no training, fitting, analytics dispatch, learner or evaluator work. Existing scientific launch procedures are preserved.

## Resolve these inputs before execution

The orchestrator's sanitized discovery record (Git blob `a061a46ea30b3bd06f6c4264c37f7fef087fe82d`) and active profile record `8e92fdea3bf4dd7731198a267d9ffaff5313fb9a` identify project `remission-poc-esbraun` (number `302481784991`), region `us-central1`, repository `us-central1-docker.pkg.dev/remission-poc-esbraun/remission`, and runtime service account `remission-poc-runtime@remission-poc-esbraun.iam.gserviceaccount.com`. The different inactive default profile is not authoritative. Root's subsequent read-only authenticated project receipt `94185cb84171511d376793fc937631c16e625a26` confirms this project ACTIVE. Read-only inventory `6770f377f837d78c7e516779633cee29ffbb6d55` confirms billing enabled, the existing DOCKER repository and runtime service-account identity, and no target `remission-poc` Cloud Run service in `us-central1`. Reuse these identities; do not create duplicates. The service-account disabled field was omitted, so do not infer its value. Compute/DNS APIs were absent from the enabled list; they were not queried or enabled. Domain ownership, IAM policies, live budget/spend and deployment/push permissions remain unverified. This worker read no credentials or original `.env`. Existing data/model buckets are not a SQLite filesystem or training dependency.

Local configuration records a project monthly budget of $20 and a previous Cloud Run $15 spending configuration; the alert budget amount is null. A Cloud Run setting does not cap Compute Engine/disk/address/snapshot charges. Accepted primary-source cost note `0a2529fe6e02b25969ea87ba0cbb178fe680e0d2` estimates an e2-small/2GiB, IPv4 and 30GiB Persistent Disk at about $17.08 per 730-hour month, leaving only $2.92 before registry, backups, logging, egress, DNS and other project usage. This is an estimate, not an approved total or measured fit: app/generator maxima alone total 4GiB plus proxy/host. Capture actual working set and disk footprint before selecting a VM. Resolve the total estimate, authorized billing owner and stop/delete date before allocation. Keep the retained SQLite disk/private generator/proxy topology; an ephemeral Cloud Run filesystem or bucket FUSE mount does not preserve unchanged SQLite semantics.

Still resolve the authorized billing owner, zone, VPC/subnet, permitted VM size, disk type/size, operator IAM/IAP/OS Login access, repository read/push permission, exact tested service/generator registry digests, qualified Caddy image/host architecture, immutable host OS image and approved secure credential provisioning/delivery for two synthetic physicians. The stable public IPv4 from the authorized allocation can supply the HTTPS origin; an owned DNS name is optional. Actual trusted TLS remains to be proven. Root's separate setup retained a checksum-verified task-private Google Cloud SDK 590.0.0 and reused the existing active profile successfully; no global SDK change, new login, account key or duplicate credential setup is needed. Project-read success does not establish deployment/IAM/push authorization.

The Linux VM image must have systemd, Python 3, ext4 utilities, Docker Engine and the Docker Compose plugin, and `/usr/bin/docker`. Record installed versions in runtime evidence. Follow the [Docker Debian installation instructions](https://docs.docker.com/engine/install/debian/) and [Compose plugin instructions](https://docs.docker.com/compose/install/linux/); pin the resulting host image rather than installing an unbounded latest runtime at each boot. Do not enable Docker live-restore. The VM service account needs repository-scoped Artifact Registry read access for image pulls; it does not need deployment/Compute administrator roles. The operator needs the permissions for the specific create/attach/firewall/snapshot actions below plus IAP and OS Login administration as selected by the project owner. Review permissions against the project's policy rather than granting an Owner role.

## Source and image contract

The nonsecret renderer is [prepare.py](../../tooling/foundation/cloud/prepare.py). It accepts exactly seven fields: `service_image`, `generator_image`, `proxy_image`, `source_commit`, `hostname`, `disk_device`, `disk_uuid`. `hostname` can be the canonical global unicast IPv4 returned by the authorized allocation or an existing selected public DNS name. Private/loopback/link-local/CGNAT/documentation/multicast/reserved IPs and IPv6 are rejected. All images require `registry/path@sha256:<64 hex>`; local image IDs and mutable tags are rejected. Use app/generator registry digests obtained after accepted source-to-image qualification/push; local image IDs are different identities. IPv4 mode requires the official Caddy 2.11.7 linux amd64 manifest `docker.io/library/caddy@sha256:04913b1da43339a40ad1ea87827d70a576ac5aa6cf674c6e24fdca675887533a`, currently metadata-pinned but not pulled or runtime-qualified. Root's frozen TLS research note is Git blob `9554aa68b735e9499f4cc9c3d12e8add49dc3a0d`, references `9b729d2b9dbb04afed5ec5d15d94ae3f0d3a2899`.

The current app build `sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72` passed the bounded local fixture and is not a deployable registry reference. It consumed the independently reviewed P2 service/UI component `9b3a61b0f02f881fe3a8fe7e60c11015074b3e9a` on source `4a903a01a7aa90938bb2b69c0911dafaff4cce7c`; PR39 changed documentation only. Record the final package SHA and manifest-pinned admin/config bytes alongside that component association. Exact-current generator build `sha256:d64907d76a2810d2e6cad8acaa012f3df132ced69bfe2636c7eb07f7090b4eee` consumed canonical `de4a0c5d8a8146a02101617c0fcf8f655aba6474` through reviewed build candidate `6168302a2db95a3d8ee9f4b8ce17c678bef9b575`; it passed actual copied-source/platform/UID/import qualification and private HTTP fixture operation. The historical generator is excluded. The [concrete bounded fixture operator and proposal](poc-cloud-simulation-fixture-proposal-20261023.md) bind actual copied-byte closure/platform/UID/import qualification, exact prearmed CID supervision and a one-attempt authorization receipt. The [runtime evidence](evidence/cloud-simulation-prep-20261023/local-fixture-runtime.json) supplies that bounded local proof; deployed ingress, registry/proxy and durable restart qualification remain separate.

Two separately authorized local CS-T1 attempts failed before any container was created: optional parent metadata, then exhausted Docker default network pools. The [fixture proposal](poc-cloud-simulation-fixture-proposal-20261023.md) preserves both failures and the observed local nonoverlap behind a source-only explicit-subnet repair. Its fresh plan froze `10.253.240.0/28`/gateway `10.253.240.1` with exact IPAM admission; after independent ready_to_execute review and matching root authorization, the third local attempt passed. Both stopped containers and the network are retained; the new evidence/documentation candidate still requires ready_to_ship review. This task-private local network choice does not configure a GCP subnet or establish cloud routing acceptance.

For a future authorized clean build with the pinned foundation-runtime prerequisite already installed:

```powershell
python tooling/foundation/build_live.py --simulation-only --evidence <fresh-evidence-directory>
```

This builds only service and generator. Omit `--simulation-only` to preserve the old all-role scientific build. Do not rerun this build to duplicate the already prepared component: the active build workers own those exact build proposals. Neither the renderer nor structural tests build, pull or start containers.

On the approved operator machine, write the seven resolved nonsecret values into `cloud-config.json`, then render to a fresh directory:

```bash
python tooling/foundation/cloud/prepare.py --config cloud-config.json --output rendered-cloud
python tooling/foundation/cloud/prepare.py --verify rendered-cloud
```

The filesystem UUID is read during the one-time disk step below, so render after that step. Record the rendered `manifest.json` SHA-256 outside the VM as the release/configuration fingerprint; the manifest pins all generated assets, including the read-only administrative script. Only root may modify `/opt/remission-simulation`. An image/config change creates a new rendered manifest and requires affected review. The stack uses fixed Compose project `remission-simulation`; never run another copy against the same durable directory or use `--scale app` above one.

## Create an unrouted VM and retained disk

These Bash commands are parameterized examples for the resolved, authorized operator environment. Required nonsecret variables are `PROJECT`, `REGION`, `ZONE`, `VM`, `DISK`, `DISK_TYPE`, `DISK_SIZE_GB`, `MACHINE_TYPE`, `NETWORK`, `SUBNET`, `HOST_IMAGE`, `HOST_IMAGE_PROJECT`, `RUNTIME_SERVICE_ACCOUNT`, `ADDRESS_NAME`. Keep shell tracing disabled. This phase creates billable resources and must wait for the applicable execution authorization.

```bash
gcloud compute disks create "$DISK" --project "$PROJECT" --zone "$ZONE" --type "$DISK_TYPE" --size "${DISK_SIZE_GB}GB"
gcloud compute addresses create "$ADDRESS_NAME" --project "$PROJECT" --region "$REGION"
gcloud compute instances create "$VM" --project "$PROJECT" --zone "$ZONE" \
  --machine-type "$MACHINE_TYPE" --image "$HOST_IMAGE" --image-project "$HOST_IMAGE_PROJECT" \
  --network "$NETWORK" --subnet "$SUBNET" --address "$ADDRESS_NAME" \
  --service-account "$RUNTIME_SERVICE_ACCOUNT" --scopes https://www.googleapis.com/auth/cloud-platform \
  --metadata enable-oslogin=TRUE --tags remission-simulation \
  --disk "name=$DISK,device-name=remission-data,mode=rw,boot=no,auto-delete=no"
gcloud compute instances set-disk-auto-delete "$VM" --project "$PROJECT" --zone "$ZONE" --disk "$DISK" --no-auto-delete
gcloud compute firewall-rules create "${VM}-iap-ssh" --project "$PROJECT" --network "$NETWORK" \
  --target-tags remission-simulation --source-ranges 35.235.240.0/20 --allow tcp:22
gcloud compute ssh "$VM" --project "$PROJECT" --zone "$ZONE" --tunnel-through-iap
```

Use a dedicated tag or equivalent project policy if another VM already uses `remission-simulation`. Do not open app port 8765 or generator port 8780. No public HTTP/HTTPS firewall is opened until accounts are provisioned. The selected host image must not contain an existing REMission service or other SQLite writer.

On the VM, verify that `/dev/disk/by-id/google-remission-data` is the **new disk created above**, using the GCP attachment record and `lsblk`. This explicit first-use format is separate from startup and is never run on restart, rollback, restore, or an existing disk:

```bash
set -euo pipefail
DEVICE=/dev/disk/by-id/google-remission-data
sudo lsblk --paths --output NAME,SIZE,TYPE,FSTYPE,UUID,MOUNTPOINTS "$DEVICE"
test -b "$DEVICE"
SIGNATURES=$(sudo wipefs --no-act --noheadings --output TYPE "$DEVICE")
test -z "$SIGNATURES"
test "$(lsblk --noheadings --output TYPE "$DEVICE" | wc -l)" -eq 1
sudo mkfs.ext4 -m 0 "$DEVICE"
sudo install -d -m 0755 /srv/remission
sudo mount -o nodev,nosuid "$DEVICE" /srv/remission
sudo blkid -s UUID -o value "$DEVICE"
sudo install -d -o 10001 -g 10001 -m 0700 /srv/remission/data /srv/remission/bootstrap /srv/remission/exports
sudo install -d -o root -g root -m 0700 /srv/remission/proxy-data /srv/remission/proxy-config
```

Stop on any failed check; do not paste the next command independently. Preserve the observed UUID and attachment identity in nonsecret evidence. The new disk must be empty of previous app state. Existing private native/analytics databases and bundles must never be reused for this deployment.

## Install assets and provision two accounts offline

Render the resolved config on the operator machine using the observed UUID. Copy the rendered directory through IAP (`gcloud compute scp --recurse --tunnel-through-iap --project "$PROJECT" --zone "$ZONE" rendered-cloud "$VM:~/"`). On the VM, verify its manifest against the operator's retained fingerprint, then install the files:

```bash
sudo install -d -o root -g root -m 0755 /opt/remission-simulation
sudo cp -a ~/rendered-cloud/. /opt/remission-simulation/
sudo chown -R root:root /opt/remission-simulation
sudo chmod -R go-w /opt/remission-simulation
sudo python3 /opt/remission-simulation/prepare.py --verify /opt/remission-simulation
```

Pull only the three qualified digests from the rendered Compose definition after configuring the VM's registry credential helper for its repository-scoped service account. No key file or credential is baked into the image or metadata. `docker compose pull` is an execution step; capture image RepoDigests and platform without secrets.

```bash
sudo docker compose -p remission-simulation -f /opt/remission-simulation/compose.json pull
```

With no app/generator/proxy running, initialize the new database through the existing `bundle_for`/`activate_new` contracts using the exact app image. This does not seed any fixture password/patient or import an archive. It creates a new synthetic disabled archive authority with no source grants; ordinary generated-patient consent/eligibility/hold rules remain in the existing service. The runtime reference records the existing foundation runtime, not a fitted model. Mount the administrative script/config read-only and override only the bootstrap mount for this one-time write:

```bash
sudo docker compose -p remission-simulation -f /opt/remission-simulation/compose.json run --rm --no-deps \
  --volume /opt/remission-simulation:/deployment:ro --volume /srv/remission/bootstrap:/fixtures:rw \
  app python /deployment/admin.py initialize
```

Run the following twice, with distinct resolved usernames and synthetic display names. Supply each password at the hidden terminal prompt and confirmation. Do not put it in argv, environment, shell history, an image layer, a here-document, screen recording or command-evidence capture. `admin.py` uses the service's Argon2 hasher, rejects both public fixture passwords, and refuses duplicate creation. An approved secret pipe can use `--password-stdin`; record only the operation/result, never the pipe payload. Deliver credentials only through the approved secure channel.

```bash
sudo docker compose -p remission-simulation -f /opt/remission-simulation/compose.json run --rm --no-deps \
  --volume /opt/remission-simulation:/deployment:ro \
  app python /deployment/admin.py create-account --username "$PHYSICIAN_USERNAME" --display-name "$SYNTHETIC_DISPLAY_NAME"
sudo docker compose -p remission-simulation -f /opt/remission-simulation/compose.json run --rm --no-deps \
  --volume /opt/remission-simulation:/deployment:ro app python /deployment/admin.py verify
```

For a later password reset, stop the unit first, run the same command with `reset-password --username "$PHYSICIAN_USERNAME"`, then restart the unit. This calls the existing reset function, increments `auth_version` and revokes prior sessions. Actual deployed expiry/reset rejection remains CS-T4; no host structural test claims to exercise Argon2 or authentication middleware.

## HTTPS and boot

Use the reserved regional external IPv4 returned by the authorized GCE allocation as `hostname`. If choosing an existing DNS name instead, point its A record at that address. With accounts ready and publication authorized, open only TCP 80/443 for the proxy and install the supported startup script as instance metadata:

```bash
gcloud compute firewall-rules create "${VM}-https" --project "$PROJECT" --network "$NETWORK" \
  --target-tags remission-simulation --source-ranges 0.0.0.0/0 --allow tcp:80,tcp:443
gcloud compute instances add-metadata "$VM" --project "$PROJECT" --zone "$ZONE" \
  --metadata-from-file startup-script=rendered-cloud/startup.sh
```

On the VM: `sudo bash /opt/remission-simulation/startup.sh`. The script installs an exact device mount unit and the app unit, verifies UUID/type/mount/source, required durable files and immutable bootstrap checksums, then starts the stack. It never formats, initializes, migrates or seeds. Missing disk/bootstrap/database fails startup. Bind mounts disable automatic host-directory creation. Docker `on-failure:5` handles bounded process crashes without starting containers at daemon restart; systemd owns mount-before-start after reboot. After a Docker daemon maintenance restart, explicitly run `sudo systemctl restart remission-simulation.service` through the same guard. There is no second app supervisor, scheduler or analytics job.

The Caddyfile names the exact public origin and proxies only to `app:8765`; generator has no published port or data mount, and its network is internal. IPv4 mode emits an explicit `https://IP` site, global `default_sni IP` for clients without SNI behind GCE/Docker NAT, and `issuer acme https://acme-v02.api.letsencrypt.org/directory` with `profile shortlived` and `disable_tlsalpn_challenge`. This selects Let's Encrypt public IP certificates and HTTP-01 on port80; certificates last 160 hours. Ordinary DNS-host automatic HTTPS remains available. No Cloud DNS, load balancer, certbot or additional TLS service is needed. See [Let's Encrypt released IP certificates](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability), [Caddy issuer/profile syntax](https://caddyserver.com/docs/caddyfile/directives/tls) and [default_sni](https://caddyserver.com/docs/caddyfile/options#default-sni).

Caddy persists ACME/certificate state in retained `/data` and needs outbound ACME HTTPS. Keep port80 and the proxy available for renewal; monitor renewal errors/expiry. After an outage beyond expiry, require successful public reissuance before trusting access. Before credentials, verify ordinary browser trust and a no-SNI TLS client against the actual allocated IPv4, then login/CSRF/history/logout. The app's `https://<hostname>` origin supplies existing Secure/HttpOnly/SameSite cookies; the isolated TestClient fixture now exercises an IP origin, not real TLS. No staging/self-signed fallback or certificate-check bypass is acceptance. See [Compose service settings](https://docs.docker.com/reference/compose-file/services/) and [Docker restart policies](https://docs.docker.com/engine/containers/start-containers-automatically/).

Actual Caddy syntax/adaptation/provisioning validation is pending, separately from the two-container CS-T1 fixture. The [concrete offline proposal](poc-caddy-validation-proposal-20261023.md) freezes two exact renderer-produced IPv4/DNS Caddyfiles, physical source hashes, official image, literal argv and separate acquisition/validation authorization schemas. It uses one **network-none** container with no ports or volumes, two read-only input file binds, equal 128MiB memory/swap, 0.5 CPU/64 PIDs and private 16MiB tmpfs at `/tmp`, `/data` and `/config`. It qualifies selected image/prestart fields, then reuses `analysis_lifecycle.supervise` to prearm before attached start and validate both configurations within one 45-second absolute deadline, with an external 100-second parent bound and typed PID0/restart0/terminal/reap evidence. Image acquisition, this additional single-container stage and eventual public issuance each remain unauthorized/unexecuted; no hidden third container is added to CS-T1. Deployment still requires the actual allocated-origin render and public TLS acceptance.

## Verification and operating limits

Run CS-T1 and deployed CS-T3–T7 from the ledger: real trusted HTTPS health/login; wrong/unknown credentials; anonymous read/write; cookie/CSRF/origin; logout/old-session/expiry/reset; two-account list/detail/mutation isolation; default12/bounded2–24 seeded panel, explicit eligible decision/rationale, stale/ineligible rejection, advance/outcomes/history, unavailable analysis; keyboard/narrow rendering and console/network failures. A health response alone cannot establish generator operation. Bind evidence to source/component SHAs, all three actual image digests, admin/rendered-manifest hash, disk UUID/attachment, project/zone/VM and tested HTTPS origin. Redact secrets before evidence capture.

Compare persisted panel, decision/rationale, clock/outcomes/history after browser reload, `sudo systemctl restart remission-simulation.service`, and an authorized VM reboot. Confirm no reseed, then advance again. The existing Store also binds database and lockfile POSIX device/inode identity; actual reboot must demonstrate that the selected persistent attachment preserves it. If identity changes, fail closed and report it; do not edit `service_control` or disable admission checks. One VM has restart/maintenance downtime and no high availability. Size/cost and lifetime acceptance remain unresolved until the operator selects resources and records the estimate/budget.

## Backup, recovery, rollback and teardown

For a consistent backup, stop the app unit (Compose removes containers), verify no process has the SQLite/WAL/SHM/lock open, flush the filesystem, and unmount the data disk before snapshotting it. Snapshot the entire disk so database, WAL/SHM, admission lock, bootstrap, exports and proxy state remain together. Also retain the reviewed rendered assets/manifests in operator-controlled storage. Protect backups as account/session material; they are not public evidence.

```bash
# On the VM:
sudo systemctl stop remission-simulation.service
sudo systemctl stop srv-remission.mount
# On the authorized operator machine, with BACKUP_NAME resolved:
gcloud compute disks snapshot "$DISK" --project "$PROJECT" --zone "$ZONE" --snapshot-names "$BACKUP_NAME"
```

Restart via `startup.sh` once the snapshot operation succeeds. To recover, keep the original disk retained and unrouted; create a replacement from the snapshot (`gcloud compute disks create "$RECOVERY_DISK" --project "$PROJECT" --zone "$ZONE" --source-snapshot "$BACKUP_NAME"`), attach it to a stopped/recovery VM with the same device name, and verify UUID, file identity and `admin.py verify` offline before allowing routing. Never attach both disks with duplicate UUIDs to one running app host. Update the reviewed configuration/manifest for a changed disk identity. **Recovery is limited by existing physical-identity admission:** a snapshot restored to a different device number/inode can fail Store verification. This candidate does not provide an approved cross-identity recovery/rebind operation. Keep it unrouted, preserve both disks, and obtain an affected recovery implementation/review; copying a `.sqlite` file, editing stored identities or reseeding is not an accepted restore. Recovery is documented but unexecuted, and this limitation remains open for cloud acceptance.

For a compatible image rollback: stop the unit, retain/snapshot the data disk, render the preceding reviewed service/generator/proxy digests into a new asset directory, verify that the preceding service supports the current SQLite schema/control capability and bootstrap, stage/pull those pinned images, run `admin.py verify` offline with that service image, then install the reviewed assets and start through `startup.sh`. Do not downgrade a changed schema in place; keep the failed deployment unrouted and use a separately reviewed recovery procedure. Record the previous manifest and image identities. No automatic migration or rollback is hidden in startup.

To stop billing for VM compute, stop the app and VM using explicit project/zone/VM. To tear down the VM, use `gcloud compute instances delete "$VM" --project "$PROJECT" --zone "$ZONE" --keep-disks=data` after recording disk auto-delete=false and backup status; the data disk remains billable. Remove only this deployment's firewall rules and release its reserved address when DNS/publication is retired. Delete the retained data disk and snapshots only after a separate explicit data-deletion decision, naming their exact project/resource IDs. Never use a broad label-based delete.

Google sources checked 2026-10-23: [supported container startup migration](https://docs.cloud.google.com/compute/docs/containers/prepare-for-container-agent-shutdown), [instance create flags](https://docs.cloud.google.com/sdk/gcloud/reference/compute/instances/create), [Persistent Disk attachment](https://docs.cloud.google.com/compute/docs/disks/add-persistent-disk), [snapshot consistency](https://docs.cloud.google.com/compute/docs/disks/snapshot-best-practices), and [systemd mount units](https://www.freedesktop.org/software/systemd/man/latest/systemd.mount.html). This uses startup scripts and standard containers, not the deprecated container-declaration path.
