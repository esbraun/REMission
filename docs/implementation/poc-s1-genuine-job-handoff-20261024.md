# S1 genuine same-Store job: staged source preparation

Status: **SOURCE PREPARATION ONLY; both phases nonexecutable; no runtime GO.**
Base: `caeca8b4bd85cede013efa92347fd20ff0f77df9`. Author: gpt-6.1-sol/high.

The accepted P2 operation established offline intake/idempotence and 72 history
projection reads in the retained positive Store. Its public counts were zero
analysis attempts and zero pending jobs. This preparation supplies the missing
genuine authenticated app submission; it does not turn those history reads into
saved S1 results or rerun the offline benchmark.

## Phase A: concrete submit and queued export

`s1_genuine_once.py` supervises one fixed container on the existing positive
volume `remission-s1-completion-261024-r1-positive`. It never creates, changes
ownership of, reinitializes, imports into, or removes that volume. Selected
volume label and absence of running writers must pass before the new container.
There is no network, host port, generator, scientific worker, claim, or fit.

Inside that container, `s1_genuine_submit.py` authenticates the original owner
with existing credentials, obtains the current CSRF token, persists an exclusive
private intent, and sends **one** S1 day84 request with the fixed receipt key.
An ambiguous response is reconciled by the original owner/key receipt and the
existing `export_queued_request` guard. It never repeats the POST. That guard
rechecks exact submission, owner, full12 cohort, cutoff, immutable history and
artifacts, authority, configuration, and sole unclaimed queued job. Missing or
conflicting receipts remain failures. Private intent/response/export/selection
remain inside the owned Store volume. Per-file caps are 8192/131072/16777216/8192
bytes respectively; a separate public result is at most4096 bytes.

Proposed Phase A ceilings are **900 seconds outer**, common absolute work840,
setup60, controller wait870, CLI reap2, and HTTP request plus decoding180. The
outer origin precedes public preflight; the one owned controller receives that
same origin. Timeout kills and reaps that exact child before reading its bounded
public acquired-CID record. The remaining outer reserve covers literal-CID stop
and independent final audit. Late/unreaped/unknown create or stop fails closed.
These are proposals for exact operation review, not inherited fit authority or
observed timings. The fixed container has2CPU,2GiB equal swap,64PIDs,UID10001,
read-only root, no network or ports, dropALL/NNP, and128MiB noexec tmpfs.

The unchanged lifecycle helper supplies typed State and matching live owned
watchdog PID/CID/nonce/deadline ACK before attach/start, terminal checks and owned
reaping. The new controller additionally audits all requested resources, exact
five mounts and read-only directions, selected image, UID, argv and labels.
`--log-driver none` and `discard_output=True` prevent retaining app process
streams. After successful supervision/reaping, only the fixed public filename
`/data/s1-p3-submit-r1/public-result.json` may be copied. The existing N transfer
pattern is narrowed to that name: at most20480 transport bytes, one regular tar
member, at most4096 payload bytes, no extraction, no other filenames. Strict
JSON rejects duplicates/nonfinite values/unknown fields. Only fixed stage times
and queued-export counts/booleans can be published; failed streams and private
export/auth/Store contents are never read by the host.

The draft packet explicitly has `executable:false`. Store instance, authority
generation, owner/archive/export/admission identities, private auth location,
public archive/authority paths, and exact new review/GO proofs are unknown. It
fails before helper import, reservation, any private access, or Docker. Root
must bind and authorize those selected paths later; this author has not read
them. No executable final operation or current once authority is claimed.

## Proven source/image reuse

Use accepted app image
`sha256:4c293e2de7f89fc484e575f23e7af7505b28a72d4a6b35f944aa3da56c6040fd`,
full196 source manifest `3036d68fc928db13bbbf8597eb0bb163603a3f8a`,
review `9223202139d4ea01ea3567efd9b7e7e68af79953`. The old controls615 image has
stale app/support-archive bytes and is not substituted. Current external host
lifecycle bytes are bound separately; the old embedded helper is not used.
Public helper inventory `61f3d09b7f98e1813a6ede20f04ee47c981386c9` documents those
distinctions. The packet records Git and raw hashes separately and exact selected
S1 service/contract matches. It does not claim all new tooling is in an old image.

Accepted P2 actual report `e3b270a7faac2242be1cd84d2b676d40ca1e93db` and full
index `afd9d675e1800d641ad9e588f11c91507c6759c2` provide lineage only. They confer
no private read or later job authority. Accepted plan is
`ac04d7c9fe505d42af538ba8035552d01b8bf60c`; different critique is
`29c371a454109a2f0adc2ac9d4fd812e2020e79b`.

## Phase B: genuinely pending

The dedicated existing host dispatcher already selects
`services.learner.support_s1_worker`; no dispatch branch is missing. Its S1
180-second lifecycle literal and60-second learner subwindow are existing code,
not feasibility evidence or permission to increase limits. A later bounded
source repair must give the chosen S1 operation the existing N-style named-file
collection/output/privacy guards and full typed resource/config audit without
weakening S1 owner/input/claim/host-image/source/deadline/ingestion semantics.
That repair and its actual budgets need separate review before a genuine claim.

Phase B remains nonexecutable until Phase A produces the actual private queued
export and job identity and those guards are accepted. Reuse the immutable
learner `sha256:1ee228092f77070242169bda307a2c351709a6892f73635d24cd2f1bc720f85f`
only with its accepted full84 dependency map/report; no rebuild or fit is done
here. Compare coefficient, SE and all36 covariance entries to the public exact
input/config/history-matched reference using
`abs(a-b)<=1e-10+1e-9*abs(b)`. Reference
`89cf5ea6735447e36a9f42ba4c14d0175f08df85` is not a transplantable result.
Historical/current saved reads remain read-only, with reload/reauth/persistence
and browser verification in later separately reviewed operations. No serving,
appointment fit, seven-config study or clinical acceptance follows.

## Source verification

Run `tests/run_s1_genuine_source.py` under the read-only approved isolated
source-check Python. Guarded scalar/AST/inert process doubles cover original
receipt reconciliation and no resubmit, required persistence failure, exclusive
private byte caps, pre-import refusal, strict finite public receipt/framing,
typed resource/mount mutations, capped named-file transport, same-origin outer
success/timeout/reap/stop custody and discarded streams. Real app/Store/SQLite,
science, network and native child operations are tripwired. Source controls do
not establish actual TestClient, Docker copy, deadlines or WCLS performance.
