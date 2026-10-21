# Run and evaluator interfaces 1.0.0

These are admission contracts and pure qualification helpers. They contain no
generator, conditional filter, calibration engine or truth engine. The tests use
hand-authored contract fixtures, never qualified production results.

`RunManifest` freezes inputs before execution. `RunResult` binds output hashes
after execution, avoiding self-referential hashes. `Authority` and
`ExportAuthority` come from trusted operator configuration outside the uploaded
artifacts; an uploader's self-declared authority authenticates nothing. Verify
all input bytes with `private_admission.verify_run`, then all output bytes with
`verify_result`, before publishing observed exports. Configurations, exact cell
and cohort rosters, seed keys and source identities remain bound across files.
Calibration-dependent cells require a separately trusted, solved evaluator
binding before observed data can be admitted.

Only `common`, `observed`, `admission` and the nonsecret bindings manifest ship
in service/learner images. Observed history uses the existing canonical record
union and strict cutoff projection. Administrative records remain in exported
history but cannot acquire clinical event-store authority through replay. Raw
sources must parse to the same accepted typed payload; opaque or privileged
fields are rejected. Published directories are immutable and become readable
only after their final manifest is present. Replay requires existing ownership
for every patient and uses the accepted transactional/cursor/idempotency path.

The evaluator alone imports `private`, `private_admission` and `probability`.
Requests bind the canonical clinical, FIX, SYSTEM or native analytic target;
these target kinds cannot be relabelled. Pending, failed, undefined and capped
answers remain explicit. Scalar ISI/quality precision rules are unchanged.

The accepted companion **ESTINT-PRECISION-01/1.0.0-r1** is the exact R1 plan
at `docs/implementation/g1-estint-probability-precision-proposal-r1-20261021.md`.
Its LF-normalized SHA-256 is generated in `bindings-v1.json`; this is the sole
accepted probability precision rule. The original proposal and critique are
historical. Six probability components use MCSE <= min(.001, .1 * matched SE).
The probability-only matched pilot exception retains all 1000 trial outcomes,
uses empirical dispersion and its lower bound plus exact Clopper-Pearson IID
cross-check, and binds the final epsilon across both last particle transitions.
It does not apply to conditional ISI or source-shift scalar pilots.

Each conditional pilot environment requires its own full filter/selection/one
rollout key and execution/ancestry/innovation provenance; reuse with fresh labels
is rejected. Diagnostic filters (32 per level) are distinct from the mandatory
60,000 pilot filters per configuration/history/level. These receipts and hashes
are necessary IO checks. Actual producer independence still requires independent
source/runtime qualification; accepting a schema is not evidence of execution.
No producer is qualified by this interface candidate.

After the rejected2a review, unconditional IID admission requires both batch
and pooled Bernoulli MCSE to meet the same final epsilon. Every such admission
also requires a resolved investigation with a separately supplied trusted
expected digest/producer/runtime/qualification authority. The artifact binds
the exact request, complete truth-file manifest, raw counts, independent units,
and recomputed mean/MCSE/covariance, with method and rationale. An uploaded
`consistent` flag grants no authority; no investigation overrides an inequality
or authorizes conditional descendants as IID units. There is no invented
materiality ratio. Wire-test fixture authority is explicitly not production
investigation or producer qualification.

Computed conditional ISI uses its own authenticated `SymptomPilotBinding` and
actual1000-trial eligible-arm values. Each trial needs at least two eligible
values and positive sample SE. The conservative binding retains the minimum
positive realized SE and `RMS_SE - 1.645*MCSE(RMS_SE)`; probability dispersion
does not replace this unchanged symptom policy. A smaller authenticated-request
comparison SE only tightens that bound. Conditional pilot refinements and the
separate response approximation budget use the symptom's own ISI epsilon.
Authenticated pilot and probability-truth particle levels/final level must equal
the separate symptom response accuracy levels, including partial vectors.
Computed numerical probability references must equal the already authenticated
request comparator pilot plan; nonexistent or substituted reported references
cannot accompany otherwise valid numbers.
Missing/undefined/zero pilots leave symptoms uncomputed while retaining the
labelled event vector.

Result event times are the sorted multisets of all non-null path event times
through day42, retaining multiplicity across all paired batches and both arms
separately. Admission before death remains present. Embedded ISI standard error
must agree with qualified numerical MCSE or be absent when the precision record
is authoritative; an unqualified interval is rejected. These consistency checks
also apply when a vector retains computed components under an overall partial
or undefined status.

Probability evidence is read and recomputed from authenticated artifact bytes
before a computed numerical interruption vector can be admitted. Complete paired
paths retain death, admission and each arm's own eligible ISI values/counts.
Truth uncertainty uses independent batch means and covariance, not a falsely
enlarged number of conditional descendants. Sampled all-zero/all-one conditional
paths remain unresolved at the 1000-batch cap unless an independent structural
proof applies. Known death does not prove absence of earlier admission. Full
analytic interruption vectors currently fail closed without a separately
qualified vector proof adapter; scalar and component structural proofs retain
their distinct units and provenance.

Schemas and dictionary are generated with `python -m contracts.runs.export` in
the qualified numerical/service runtime; `--check` detects drift. Consumer
imports do not require NumPy/SciPy. Numerical qualification helpers use the
existing locked NumPy/SciPy runtime, with no new dependency or lock change.

Future ownership: generator produces run/seed/observed artifacts from simulation
source; an independent evaluator produces calibration and target-matched truth
artifacts from its private storage/process. The integration owner controls these
shared schemas, root manifests/locks, admission adapters and migration numbering.
No production code may treat the fixtures as solved calibration or truth.
# Separate OBS-REP-02 profile

Version 2.0.0 lives in `observed_v2.py`, `coverage_v2.py`, `admission_v2.py` and evaluator-only `private_v2.py`. Dispatch uses explicit schema version and record kind. `bindings-v2.json` adds the exact accepted R1 representation and noncircular domain/run schema-set manifests; every scientific v1 binding stays identical. `export_v2 --check` verifies only new products under `schemas/v2/` and `dictionary-v2.json`; it never regenerates v1 products.

V2 replay retains every history record's original UTF-8 source bytes, source header, payload hash and complete append-only lineage, including administrative evidence. A trusted out-of-band ExportAuthorityV2 binds independently derived day0â€“84 support coverage, the day85 administrative endpoint reservation, terminal reconciliation, complete policy mechanism, stage ledgers, completion/persistence receipts and deterministic/full-key record identities. Its uploader cannot shorten the roster, change time zero/timezone, declare an absent stage empty, or supply its own production qualification. Empty ledgers are explicit artifacts; all observed counts require visible exact completed closure chains. Completion receipts bind immutable planned inputs and independent stage outputs; final coverage and archive bind the receipts without circular hashes. Fixtures cannot qualify actual production.

The foundation's configured authenticated owned archive route returns `archived_read_only`. Clinical import uses a fixed allowlist that excludes consent, approvals, snapshots, assignments, delivery and support/hold administrative evidence. Independent hold partitions fail closed before clinical/state/cursor publication under **B-OBS2-LIVE-HOLD**. Legacy entry points apply this guard too. Clearing or granting live consent/approval from generated artifacts is forbidden. The later authenticated invalidation-only latch route is a required separate engineering task; archive acceptance cannot close it. See the [accepted R1 proposal](../../docs/implementation/g1-observed-representation-proposal-r1-20261021.md) and [current checkpoint](../../docs/implementation/evidence/G1-OBS-REP/implementation/checkpoint.md).
