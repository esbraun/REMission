# Bounded offline Caddy configuration validation

**SOURCE/PREPARATION ONLY; UNEXECUTED.** This is the pending Caddy portion of CS-T2, not public TLS acceptance or a deployment. Base `965cbd37efef2a911d40989bcfbbc0a93f8e7eb7` is independently source reviewed, with the separate app fixture runtime still pending. No Docker command, image pull, cloud action, private file/database read, numerical import, server or certificate issuance was authorized or executed during this preparation. Frozen Astra research note `9554aa68b735e9499f4cc9c3d12e8add49dc3a0d` and references `9b729d2b9dbb04afed5ec5d15d94ae3f0d3a2899` were read fully and reused without further research.

[validate_caddy.py](../../tooling/foundation/validate_caddy.py) is a small stdlib adapter to existing [analysis_lifecycle.py](../../tooling/foundation/analysis_lifecycle.py), with no new supervision framework or application changes. One container validates both committed [IPv4](evidence/caddy-validation-prep-20261023/ipv4.Caddyfile) and [DNS](evidence/caddy-validation-prep-20261023/dns.Caddyfile) inputs. [inputs.json](evidence/caddy-validation-prep-20261023/inputs.json) supplies exact nonsecret renderer inputs: fake app/generator registry references, fake disk identities, source base and pinned Caddy reference. Only the two Caddyfiles enter the container. They are exact `prepare.validate`/`prepare.caddyfile` outputs, rechecked during freeze and authorization. `8.8.8.8` is solely an offline globally routable parser representative, never an allocated or owned deployment origin; `simulation.example.org` is the reserved example-domain DNS case. Neither address is contacted or resolved.

The IPv4 bytes include global `default_sni`, explicit HTTPS origin, Let's Encrypt directory, `profile shortlived` and disabled TLS-ALPN challenge; the DNS case preserves ordinary automatic HTTPS. SHA256: IPv4 `2d66f498b2f2647dc237eda4968f37aa2a8f5167330295810e69d29b4a5cd579`; DNS `8a69c9423d5751ebd64767c40f4977d79d5a113d3d4da060582446cc3c2de846`; input JSON `954ce44e4e1a533298be224c71249d3bc8ddd2ccce7b065c8f7e64be13b2ad6a`.

## Freeze and independent review

From the exact committed candidate in the assigned checkout:

```powershell
python -P -B tooling/foundation/validate_caddy.py --freeze artifacts/caddy-acquisition-20261023-r1 --name remission-caddy-b52f03d8c741
```

This host-only command freezes the actual candidate commit, physical absolute paths/SHA256 for operator/lifecycle/renderer/all input files, literal create argv, selected inspect formats, exact image and bounds into `plan.json`; it prints that file's raw SHA256. Root retains this plan and submits the exact candidate/base, physical bytes and plan hash to separate Astra review. A different checkout/path/name or source change requires a new freeze, review of affected changes and fresh matching authorization. No illustrative SHA is an authorization.

The earlier `artifacts/caddy-validation-20261023/plan.json` is preserved unchanged as historical preparation (raw SHA256 `4dd6027a0b833bb15b9d7590331098923314d7fda655fc37a060a4b6dbdf4ae0`). It does not bind this repaired acquisition controller. The new candidate requires fresh independent acquisition review; the previous review's conditional validation disposition supplies no acquisition authorization.

## Separate proposed acquisition prerequisite

The official linux amd64 platform manifest is `docker.io/library/caddy@sha256:04913b1da43339a40ad1ea87827d70a576ac5aa6cf674c6e24fdca675887533a` (released Caddy 2.11.7). It is metadata-pinned, **not locally pulled or executed by this task**. The frozen plan binds this sole pull argv, the exact Python executable/controller path, both launcher and worker argv, physical source hashes and absolute acquisition evidence path:

```text
docker pull --platform linux/amd64 docker.io/library/caddy@sha256:04913b1da43339a40ad1ea87827d70a576ac5aa6cf674c6e24fdca675887533a
```

After fresh independent review, root must separately supply `acquisition-authorization.json` beside the new frozen plan, with exactly these typed fields and actual hashes/path:

```json
{"authorized":true,"scope":"one-caddy-image-acquisition","plan_sha256":"<raw plan SHA256>","launcher_sha256":"<physical validate_caddy.py SHA256>","evidence":"<absolute frozen acquisition evidence path>","attempts":1,"timeout_seconds":120,"external_seconds":140,"cloud":false}
```

The authorization is bound through the raw plan hash to the exact source commit, physical controller/lifecycle/renderer/input bytes, Python executable, invocation, image and evidence. Missing, extra or differently typed fields fail before child creation. No authorization file is created during preparation. Root's future sole acquisition invocation is the plan's exact `acquisition_proposal.launcher_argv`, rendered here relative to its frozen root:

```powershell
python -P -B tooling/foundation/validate_caddy.py --acquire artifacts/caddy-acquisition-20261023-r1/plan.json --authorization artifacts/caddy-acquisition-20261023-r1/acquisition-authorization.json
```

The existing external validation launcher is also used for acquisition. It reserves `acquisition/launch/` exclusively, records the literal worker PID/argv, and waits at most 136 seconds followed by the unchanged lifecycle helper's bounded 2-second wait/kill/2-second reap, within the 140-second external child bound. The worker independently rechecks authorization and exclusively reserves `acquisition/attempt/` before exactly one pull. It records the Docker client PID/argv and absolute monotonic deadline, retains stdout/stderr files, and allows at most 120 seconds from before client creation to successful return. On timeout/interruption/error it requests client kill if still running, then uses bounded lifecycle reap; terminal receipts retain literal PID, argv, exit, kill request, reaped status and failure even when reaping fails. The external launcher checks the successful pull/reap receipt before acceptance. No automatic retry exists; existing reservations reject another attempt.

Killing or reaping the Docker client or worker does **not** prove daemon pull work stopped. Every failed/uncertain acquisition reports **STOP UNCONFIRMED: daemon pull may continue**, retains evidence and returns to root. No tag fallback, additional platform, retry, daemon cancellation or container creation is authorized. A successful client exit is acquisition evidence only; subsequent separately authorized validation still checks the local image's digest/platform association. No Docker command is executed by freezing or host tests.

## Root authorization and one offline attempt

After independent exact-candidate acceptance and separately accepted image acquisition, root supplies `authorization.json` with precisely these typed fields and actual raw plan hash:

```json
{"authorized":true,"scope":"one-offline-caddy-validation","plan_sha256":"<raw plan SHA256>","attempts":1,"retain_resources":true,"image_pull":false,"network":false,"cloud":false}
```

Then root may launch the reviewed recipe once:

```powershell
python -P -B tooling/foundation/validate_caddy.py --launch artifacts/caddy-acquisition-20261023-r1/plan.json --authorization artifacts/caddy-acquisition-20261023-r1/authorization.json
```

The external launcher exclusively reserves `launch/`, validates authorization/physical bytes before children, records the literal worker PID/argv and caps its wait at 100 seconds. It uses the existing bounded `life.reap` (up to 2 seconds then kill and up to 2 seconds to reap) and saves terminal evidence. Timeout/parent interruption means STOP UNCONFIRMED, never successful cleanup inferred from a killed Docker client. The worker independently validates the same authorization, exclusively reserves `attempt/`, and uses one 45-second absolute deadline for image selection, creation, qualification, prearm/start and successful terminal proof. Existing cleanup commands retain their independent short caps beyond that deadline. No retry, broad discovery, removal or other resource mutation is included. Stopped container and all receipts remain for root's exact-ID inspection/cleanup.

1. `docker image inspect --format <frozen IMAGE_FORMAT> <exact manifest reference>` selects only Id/Os/Architecture/RepoDigests inside Docker, before stdout. Require Linux amd64, full content ID and the exact manifest RepoDigest association (Docker's short official `caddy@sha256:...` spelling is admitted). Missing proof fails. Optional image `Config.User` is irrelevant; the workload explicitly sets 65532:65532. Actual `caddy version` output must independently report v2.11.7.
2. Frozen create argv uses `--pull never --platform linux/amd64 --network none --user 65532:65532 --cpus 0.5 --memory 128m --memory-swap 128m --pids-limit 64 --read-only --cap-drop ALL --security-opt no-new-privileges --restart no --no-healthcheck` (actual argv contains separate option/value tokens). Exactly two absolute file binds are read-only. `/tmp`, `/data` and `/config` are private 16MiB noexec/nosuid tmpfs; these explicitly override the official image's potential `/data`/`/config` VOLUME declarations. No anonymous/named volume, durable/private mount, port, network creation, app or generator exists.
3. Retain the returned full 64-hex CID immediately. Selected created-container inspection asserts image content ID, explicit user, task label, literal shell argv, typed created/PID0/restart0 state, equal 134217728-byte memory/swap, CPU/PID/root/capability/security/healthcheck bounds, network-none, no port bindings and exact mounts. Any anonymous volume fails before start. No complete inspect, image/container environment or Docker logs are emitted. An ambiguous create response is STOP UNCONFIRMED; no name-based cleanup is inferred.
4. Existing `life.supervise` prearms its independent CID/nonce/deadline/PID watchdog while the container is created, verifies its ready receipt and liveness, then starts `docker start --attach <literal CID>`. The shell uses `-ec`, prints `caddy version`, and runs exactly `caddy validate --config /inputs/ipv4.Caddyfile --adapter caddyfile` followed by the DNS counterpart, each with a success marker. `validate` adapts and provisions the configuration without starting Caddy. No server, issuance, renewal or live endpoint runs; network-none prevents external traffic even on failure.
5. Success requires both markers, v2.11.7 output, attach/watchdog exit0, fresh typed exited/PID0/nondead/non-OOM/restart0/exit0 state equal to the watchdog receipt, both children reaped and unchanged frozen physical inputs. Failure uses accepted exact-CID stop/kill/fresh inspect/reap; missing stop/reap proof remains STOP UNCONFIRMED. The external child must also exit0 and be reaped. Retain selected image/prestart states, create/terminal/result receipts and bounded attach/watchdog streams.

Host-only tests exercise selected image qualification without optional Config, prestart resource/volume/command/state rejection, typed raw-hash authorizations and acquisition launcher/evidence/source bindings. Mocked subprocess boundaries check exclusive one-pull reservations, exact argv, 120/140-second bounds, retained streams and PID/exit/reap receipts, client kill on timeout and retained failed reap uncertainty. They do not execute Docker or stand in for Caddy execution. Future successful offline validation establishes released-image configuration parsing/provisioning only; actual allocated-IP rendering, public issuance, renewal, no-SNI handshake, browser trust and deployed auth/persistence checks remain CS3 work.
