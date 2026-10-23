# Bounded offline Caddy configuration validation

**CAPABILITY REPAIR: SOURCE ONLY; NEW WORKLOAD UNEXECUTED.** This is the Caddy portion of CS-T2, separate from the passed local app/private-generator CS-T1 fixture and actual public TLS/deployment acceptance. [Repair evidence](evidence/caddy-capability-repair-20261023/source-repair.json) preserves the acquisition/failure/review lineage. All prior authorizations are consumed. No new Docker command, pull, cleanup or runtime is authorized by this proposal.

## Observed failure and minimal correction

At source `94d30c35c54853ab4c31992c835a9080f350a734`, one reviewed acquisition succeeded for the official Linux amd64 Caddy 2.11.7 manifest `docker.io/library/caddy@sha256:04913b1da43339a40ad1ea87827d70a576ac5aa6cf674c6e24fdca675887533a`. Raw acquisition manifest `dc6adb44488b10a6ae53d0eef2881029add8b477` binds the exact-digest stdout and exit0/reaped client/worker receipts. Root accepted acquisition; no repeat pull is proposed. Its daemon-stop field remains false, with no daemon-cancellation claim.

The separately authorized offline attempt failed before version or either configuration: `/bin/sh: caddy: Operation not permitted`, exit126. Its retained CID is `92d2ea660a8a8392f0c65985768763831f1f93f35048bccd6d833cf581383272`; watchdog, supervision and fresh final receipts agree on exited/PID0/nondead/non-OOM/restart0/exit126, and both clients were reaped. Failure manifest `09f7b35e0ba3250c4876794363f66ae9e601a2b5` preserves all 40 files, with SHA256 `baf9f59d9e268519ce4ba4118692d7e74516e23bdc77b1a402c84c8b7497b044`. No cleanup/removal or retry follows. Both historical plan directories remain unchanged.

Supplemental Astra report `338eba6e165d106909bce257a9d080d9e2bdfe9e`, manifest `bc73d11345019844ca5101c46fcbad3956bca410`, requests changes to production and validator together. The [immutable upstream Dockerfile](https://github.com/caddyserver/caddy-docker/blob/9234f5785658cae8129bfae366e196d0670468ac/2.11/alpine/Dockerfile) sets `cap_net_bind_service=+ep` on `/usr/bin/caddy`. Linux bounding-set masking can reject execution of a file-capability executable with EPERM; this strongly supports the diagnosis but is not measured local binary-xattr proof. See [Linux capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html) and [no_new_privs](https://docs.kernel.org/userspace-api/no_new_privs.html).

The minimal source correction gives only the proxy and offline validator `cap_add NET_BIND_SERVICE`, retaining `cap_drop ALL`, no-new-privileges and read-only filesystems. Both explicitly use `0:0`, matching the previous official-image production default and existing root-owned 0700 proxy stores. No privileged mode, SETFCAP/SYS_ADMIN/DAC_OVERRIDE, binary alteration or removed safeguard is introduced. App 10001/generator 20000 and their empty capability grants remain unchanged.

## Frozen inputs and fresh independent review

[validate_caddy.py](../../tooling/foundation/validate_caddy.py) remains a small stdlib adapter to unchanged [analysis_lifecycle.py](../../tooling/foundation/analysis_lifecycle.py). It runs one container for two exact renderer-produced [IPv4](evidence/caddy-validation-prep-20261023/ipv4.Caddyfile) and [DNS](evidence/caddy-validation-prep-20261023/dns.Caddyfile) inputs. [inputs.json](evidence/caddy-validation-prep-20261023/inputs.json) contains nonsecret examples only. `8.8.8.8` is an offline parser representative, not an owned origin; `simulation.example.org` is the example DNS case. Neither is contacted or resolved. `check_inputs` verifies exact renderer output before freeze/authorization.

From the clean combined committed candidate, freeze a new directory and name:

```powershell
C:/Python313/python.exe -P -B tooling/foundation/validate_caddy.py --freeze artifacts/caddy-capability-repair-20261023 --name remission-caddy-ef837a6bc209
```

Freeze binds the actual commit, all seven physical controller/lifecycle/renderer/input hashes, exact Python/controller paths, literal create/workload argv, expected capability-output lines, image, inspect formats and bounds. Review must use the physical raw plan SHA256 and no-filters raw blob; normalization is not a physical-byte binding. Any source/path/name change requires a fresh plan and affected review. Historical plans/attempt reservations are preserved and must never be reused for another attempt.

Root assigns a fresh exact combined candidate/base review against `de4a0c5d8a8146a02101617c0fcf8f655aba6474`. The review must explicitly accept reuse of the existing pinned-image acquisition dependency; the plan retains the separately authorized acquisition controller for completeness, but no new pull authorization is requested. Local image qualification still runs within validation. Source review does not establish successful execution or merge readiness while runtime proof remains pending.

## Proposed one offline attempt, after review and separate authorization

Only after exact-candidate/concrete-plan acceptance, root may supply `authorization.json` beside the new plan with exactly these keys, values and JSON types, binding the actual raw SHA256:

```json
{"authorized":true,"scope":"one-offline-caddy-validation","plan_sha256":"<physical raw plan SHA256>","attempts":1,"retain_resources":true,"image_pull":false,"network":false,"cloud":false}
```

The sole future launcher invocation is:

```powershell
C:/Python313/python.exe -P -B tooling/foundation/validate_caddy.py --launch artifacts/caddy-capability-repair-20261023/plan.json --authorization artifacts/caddy-capability-repair-20261023/authorization.json
```

Missing, extra, differently typed or stale authorization fails before child creation. The existing launcher exclusively reserves `launch/`, records worker PID/argv, enforces the 100-second child wait and bounded reap. The worker independently reauthorizes and exclusively reserves `attempt/`. No bare worker invocation, automatic retry, pull or cleanup/removal is included.

1. Selected `docker image inspect` fields must prove Linux amd64, a full image content ID and exact manifest RepoDigest association. Optional image Config.User is irrelevant because container user is explicit.
2. Exact create argv uses `--pull never --platform linux/amd64 --network none --user 0:0 --cpus 0.5 --memory 128m --memory-swap 128m --pids-limit 64 --read-only --cap-drop ALL --cap-add NET_BIND_SERVICE --security-opt no-new-privileges --restart no --no-healthcheck`. Exactly two config file binds are read-only. Private 16 MiB noexec/nosuid tmpfs at `/tmp`, `/data`, `/config` override official image volumes. No anonymous/named volume, private/durable file, port, network creation, app or generator enters this container.
3. Retain the literal full CID and selected prestart inspection. Typed audit requires the exact user, single capability grant, ALL drop, NNP, image/label/shell argv, created/PID0/restart0 state, equal 128 MiB memory/swap, CPU/PID/security/healthcheck limits and exact mounts. Missing, extra or different capability/user fails before start.
4. Unchanged supervision prearms the independent literal-CID/nonce/deadline/PID watchdog, verifies readiness and liveness, then starts attach. One 45-second absolute worker deadline covers selection/create/audit/prearm/start/workload/terminal proof, with existing independent short failure-stop/reap caps.
5. Within that same shell, `getcap /usr/bin/caddy` must equal `/usr/bin/caddy cap_net_bind_service=ep`. Selected own-shell `/proc/$$/status` fields must prove all four UIDs/GIDs0, CapPrm/CapEff/CapBnd each exactly `0000000000000400`, NoNewPrivs1. Shell assertions fail before Caddy if any check differs. Only these six selected fields and getcap output are retained; no broad proc/environment/config dump occurs. Host acceptance independently requires the same exact seven lines.
6. Then `caddy version` must report v2.11.7, followed by both existing IPv4/DNS `caddy validate --config /inputs/<case>.Caddyfile --adapter caddyfile` commands and success markers. Exact stdout has ten lines: seven capability/identity lines, version, then both markers. `validate` adapts/provisions without starting a server; network-none prevents issuance traffic.
7. Success additionally requires attach/watchdog exit0/reap, fresh typed exited/PID0/nondead/non-OOM/restart0/exit0 state equal to watchdog terminal receipt, final unchanged physical inputs and parent exit0/reap. On failure, retained exact-CID stop/kill/fresh inspection/reap proofs govern; missing proof remains STOP UNCONFIRMED. Never infer workload stop from client exit. Stopped container and receipts remain retained for root.

[Host checks](evidence/caddy-capability-repair-20261023/host-checks.json) cover proxy-only capability/identity changes, validator admission/output rejection, raw authorization/source/argv binding and unchanged fixture/lifecycle failure seams. They use stdlib/mocks without Docker or app/numerical imports. A later passing run would establish local released-image binary execution and both example configurations only. Actual allocated-origin rendering, public issuance/renewal/no-SNI/browser trust and deployed auth/persistence/reboot remain CS3 acceptance.
