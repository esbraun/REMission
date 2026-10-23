# Cloud launch binding: Artifact Registry helper

Task: `/root/cloud_launch_bindings_luna`; runtime verified by root as thread `thread01a166eb-c51e-7123-b281-824a926b3c55`, `gpt-6-luna/high`. Worktree: `C:/Users/erics/Documents/Projects/REMission-worktrees/cloud-launch-bindings-luna-261023`; branch `docs/cloud-launch-bindings-20261023`; base/verified starting HEAD `9b681568949f37e4fe04f094850b42df78d5e991`.

## Pinned helper artifact

- Project: `GoogleCloudPlatform/docker-credential-gcr`, release tag `v2.1.29`.
- Target: Linux amd64 release archive `docker-credential-gcr_linux_amd64-2.1.29.tar.gz`.
- Official release asset: https://github.com/GoogleCloudPlatform/docker-credential-gcr/releases/download/v2.1.29/docker-credential-gcr_linux_amd64-2.1.29.tar.gz
- Official release checksum metadata: https://github.com/GoogleCloudPlatform/docker-credential-gcr/releases/download/v2.1.29/checksums.txt
- SHA-256 (archive, as listed in official `checksums.txt`): `9e676f2233b93e763276101dd8530e634aebf5d31d5581f64e7ffa978aefa0d8`.
- API release record: https://api.github.com/repos/GoogleCloudPlatform/docker-credential-gcr/releases/tags/v2.1.29

The archive was not downloaded, installed, or executed. This binds the checksum to the release's own checksum metadata; it is not an independently recomputed archive hash, and no signature verification of the checksum file was performed. The GitHub release page identifies the v2.1.29 tag commit as verified, but that does not by itself authenticate the separate checksum asset. Raw release JSON and checksum bytes are preserved alongside this report with SHA-256 values in `manifest.json`.

## Minimal deployment binding

Packet instructions already select ADC from the attached VM service account, require the helper under `/usr/bin/docker-credential-gcr`, and configure only `us-central1-docker.pkg.dev` via `docker-credential-gcr configure-docker --registries=us-central1-docker.pkg.dev`. The remaining static pin is now supplied above. On the authorized future host-preparation step, verify the downloaded archive against this exact SHA-256 before extracting/installing, record actual helper version and host package versions, then qualify a pull of the published image digests using the attached service-account identity. No credential file, OAuth login, token-print test, cloud call, or runtime was used here.

The existing project registry reader binding is already recorded as applied/verified in the packet and static config; this work adds no IAM. The packet's final image digests, host qualification, and successful VM pull remain pending.

## Existing billing and credential-delivery context

Inspection was limited to safe fields in the explicitly authorized original-root `infra/cloud-resources.json`. It records a USD 20 monthly project alert budget with thresholds at 50%, 80%, and 100%, with notices routed to project owners and billing administrators. This static file does not report current spend or remaining budget, so neither is asserted. The separate USD 15 Cloud Run spend cap does not apply as a total project/Compute ceiling. No named private delivery destination or preference is present in the inspected static configuration. Existing user cloud-deployment authorization and the existing $20 monthly budget were supplied by the orchestrator; this helper creates no new policy or acceptance gate. Billing ownership and credential delivery remain orchestration bindings.

## Sources and scope

- Launch packet: `docs/implementation/poc-cloud-launch-packet-20261023.md`, especially its unresolved inputs and helper appendix.
- Runbook: `docs/implementation/poc-cloud-simulation-runbook-20261023.md`.
- Repo entry point / delegation: `implementation-prompt.md`, `docs/execution/delegation.md`.
- Official project README: https://github.com/GoogleCloudPlatform/docker-credential-gcr
- Official Artifact Registry standalone-helper docs: https://docs.cloud.google.com/artifact-registry/docs/docker/authentication#standalone-helper

No Docker, cloud, credentials, deployment, runtime, or app changes were performed.