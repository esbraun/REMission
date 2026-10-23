# S1 bounded intake diagnostics: source and overlay preparation

Status: SOURCE/PREPARATION ONLY. No new build, Store, API, archive replay or
runtime operation was executed. Base is accepted main
`e196187aea79cbc4a49576c0107e94e4c6499089`. The new controls image is UNKNOWN;
the final executable P2 specification is intentionally absent. Source review,
exact controls-overlay qualification review/GO and actual image acceptance must
precede a refreshed full-P2 binding and its separate review/GO.

The accepted stopped failure (`1ab20ff038d50ea506fb11c0879115c6136d72f5`,
checks `2ed620cf85abb115d8fb3148ec492e5c077a318c`) contains no initial-after
marker or P2 result. That marker follows POST, status assertion, JSON decoding
and the existing count queries. POST return, successful commit and private
counts remain UNKNOWN. This patch diagnoses those boundaries; it is no
performance repair or bottleneck claim. PLAN critique
`141d58ebd326c94c8b80fa7ec5550539f0f46c64` is plan-only. The corrected reading
also applies to Luna map `493c4413d2315c851cab2bae9cec39622e2d6b6d`.

`Settings.support_intake_diagnostic` defaults to `None`. Only the serial P2
control explicitly supplies the fixed callback. No HTTP header, environment
flag or service-wide tracer enables it. Events contain fixed labels, request
ordinals, finite elapsed seconds and bounded aggregate structural work counts.
There are no IDs, paths, hashes, SQL, response bodies, query values, exception
details or arbitrary locals. Reader counters measure existing successful
first reads and validated cache hits; inventory counters count existing work.
No event adds a request, query, artifact read, stat or hash.

The first POST has trajectory/parser completion markers, three cut ordinals,
all-closure, aggregate reader, supplemental, manifest, inventory, publication
and persistence boundaries. A parser completion marker includes its preceding
read and parse; it does not claim a parser-only timing. Subsequent idempotent
and negative POSTs emit only the fixed coarse subset. `request` identifies the
last begun POST (1..4); `count_pass` identifies the existing eight count batches,
including batches before the negative requests. Neither identifies a Store.
The harness's `post_before` precedes construction of the existing POST call,
including its existing CSRF header request; `post_return` follows the call.
Status/JSON success and each existing count-query return are separate events.

`transaction_acquire` is before context entry; `transaction_enter` is after the
existing context yields. `precommit` precedes the independent existing fault
callback. `commit_returned` occurs only after successful context exit, never in
`finally`. The idempotent return remains inside its original `with` statement:
`idempotent_pending` precedes receipt verification and is not a commit claim.
`endpoint_return` follows actual admission return, including that context exit.
Diagnostic callback/sink failures are contained independently and cannot change
admission results or suppress validation, fault, rollback or commit errors.

The sink reserves space before calling a potentially write-then-fail sink:
at most 512 rows, 384 bytes per row, 49,152 bytes including summary/newlines.
Only the initial request receives detailed rows. The fixed complete-path
scalar fixture emits 403 rows / 44,439 bytes with maximum elapsed-width and
work counts. The unchanged 150 original progress rows are capped at 320 bytes
each and the original final result at 32,768 bytes. Combined maximum is
129,920 bytes, below the existing 131,072-byte stdout bound. Rows exceeding
the diagnostic allowance are suppressed, with bounded summary counters.

The terminal parser accepts only the original progress kind or this exact
typed diagnostic kind before the required original successful P2 result.
Unknown rows, duplicate keys, nonfinite values, incomplete output and budget
violations fail. This does not make a diagnostic summary a P2 result. The live
observer remains restricted to the original eight-field progress kind; the
new diagnostic kind is retained for terminal evidence review only. A later
operation may authorize a narrow diagnostic live reader separately.

All 24 accepted assertion ASTs and the 72-GET loop AST are unchanged, including
the two distinct fresh authenticated-409 fixtures. The original queries,
returned count values and order are unchanged and remain in the original P2
result only. Default-off source doubles compare receipt/error/transaction and
reader/closure/inventory-call sequences against accepted base bytes.

Run the bounded host source controls in this checkout with:

```powershell
& 'C:/Users/erics/Documents/Projects/REMission/artifacts/s1-app/artifacts/source-check-env/Scripts/python.exe' -I -B tests/run_s1_intake_diagnostics_source.py
```

The runner reads two exact public Git source blobs, then blocks real Popen/run,
native, project, SQLite and scientific imports. Tests extract source seams by
AST and supply scalar doubles. They do not instantiate a real Store, API or
archive. This is source equivalence/invariant evidence, not full-P2 acceptance.

The controls-only overlay is three COPY operations on accepted controls
`sha256:615beab9880965ab25b32c3b27d6a525f716e361583e26a665fbff1861739273`:
replace `services/foundation/app.py` and `support_archive.py`, add
`support_diagnostics.py`. The complete expected project inventory becomes 196
from 195; all other hashes, dependencies and image configuration stay bound to
the accepted parent. Reuse its exact strict qualification probe and accepted
lifecycle; do not rebuild unaffected service/learner roles. Exact source bytes,
map and COPY proposal are frozen in this worker's public ignored packet.

The derivative future P2 operator keeps fresh namespace/auth/Store ownership,
180-second setup, 30-second ownership, 900-second P2, two-second CLI cleanup,
PID64, 2CPU/2GiB/equal swap, nonroot RO/network-none/dropALL/NNP/tmp512MiB,
literal CID/strict live watchdog ACK/terminal and reap checks. Legacy
`a8e8aa54...` is ownership-only UID0/dropALL+CHOWN, never intake. No old Store,
auth, volume or resource is opened or reused. Same-handle polling and retention
remain required; no retry, cap increase, cleanup discovery, service, job, fit
or browser permission follows from this preparation.

The source checkpoint is `0cce8aee2c89a153ddb9da12a9f033cfd11cad1c`.
`tooling/foundation/s1_diagnostic_image.py` is the later controls-only operation
derivative. Its frozen public packet lives under
`artifacts/s1-intake-diagnostic-r1/image-qualification` in this checkout. It
reuses exact IMAGE05 helper `f7bacdfb3516a02a4cbb82925b64b4219894ef74`,
lifecycle `a63db64c57032fa68b7b854292a829c9165fd108` and inherited probe
`8d5e06dae9978a9657029b65c5df04b73c424ae1`. The parent is controls615b,
not the older022 image. One expected-map COPY under `/qualify` accompanies
the three production COPYs; the probe is already inherited byte-identically.
The child must retain the full accepted parent layer prefix and runtime
configuration. Service and learner roles have no commands in the derivative.

The separate qualification operation preserves IMAGE05 limits: 900-second
phase, 300-second build client, 60-second qualifier, three-second exact CLI
cleanup. Qualifier limits are 2CPU/2GiB/equal swap/PID64/RO/dropALL/NNP,
UID10001, network-none, no mounts/ports and existing512MiB exec tmpfs. These
limits apply to the qualifier, not Docker daemon COPY work. No RUN executes
during build; a client timeout/reap does not prove daemon completion. Build
failure/deadline is STOP UNCONFIRMED and retains all outputs with no retry.
The exclusive results reservation precedes the first Docker call, including
metadata. Name/tag collisions halt; literal full CID and typed configuration
must precede unchanged strict live-ACK supervision. No partial/reported PID
or CID is trusted for cleanup.

Six additional host-only controls use a fake command/lifecycle boundary under
real-Popen/run and import tripwires. They cover map/COPY purity, successful
literal-CID supervision, once reservation, build timeout UNKNOWN/no start,
unconfirmed CID/no attach and resource drift refusal. The first fixture capture
retains two failures caused by its missing temporary expected-map fixture;
the fixed six-control capture passes. No Docker command was executed.

```powershell
& 'C:/Users/erics/Documents/Projects/REMission/artifacts/s1-app/artifacts/source-check-env/Scripts/python.exe' -I -B tests/run_s1_diagnostic_image_preparation.py
```

This qualification packet needs independent exact SOURCE+OP review and new
root GO. An accepted actual child image would permit preparation of the later
P2 executable specification, followed by its own review and GO. None is granted
by the source controls or the proposed qualification command.
