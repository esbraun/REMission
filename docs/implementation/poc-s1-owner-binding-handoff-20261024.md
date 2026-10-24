# S1 selected-owner binding preparation

**SOURCE/OP preparation only; no current GO or private/runtime access.** Base
`d530f940239ade9ac00b527ab2aabb6a61245f4d`; author gpt-6.1-sol/high.

The binding mode resolves one missing selected-archive owner before the genuine
S1 submission. It does not authenticate, submit, claim, fit, initialize, import,
repair, create an account, or select the first of P2's two accounts. Later Phase
A must perform normal login/CSRF and match that owner, then revalidate full12,
H*/cutoff/current versions/admission/configuration/history and the original
stable-key receipt/export guards. This receipt is an advisory snapshot, not an
eligibility cache or permission to skip those guards.

## Fixed public expectations and minimal dependencies

- Instance `f4d6bea5-10aa-4247-afa0-76b8e5c3fceb`, generation1.
- Archive `support-dev-once-20261022:support-dev-cohort-20261022`, export key
  `accepted-support-dev-20261022`, full12 original members and24 partitions.
- Public admission provenance
  `7f411f3cc7b60fa28eb61481db15c590089fa874827ca8fdab547628438bcf98`.
- Retained volume `remission-s1-completion-261024-r1-positive`; current presence
  and absence of writers remain unknown until selected runtime preflight.
- Exact public authority blob `437547e14ae0fa1ea9d3899bb9f7f44373699bf9`,699480B,
  SHA256 `048960f15bc0cc1ca7136a491755bbb64bfd1e0778418fd88e50a15480c65004`.
  The packet materializes only those public Git bytes, not the103MB archive.

Use the accepted app4c immutable image and full196 public inventory. The public
packet verifies selected installed service/contract source matches, including
Store, AdmissionGate, schemas and authority model. New payload bytes are bound
as a public carrier; no image build or claim that old images contain new tooling.
Current external PR63 lifecycle and qualified CLI runner are copied exactly.
The binding container has only two mounts: existing volumeRW at`/data`, and
public packet payloadRO at`/operation`. It has no auth or archive mount, no port
or network, and no app/TestClient import or endpoint call in its binding branch.

## Exact read-only contract

`Store.__init__`, `Store.connect`, `Store.transaction`, configuration loading
and initialization are not called. An operation-local Store instance is created
without its constructor solely to invoke the **entire unchanged**
`Store.validate_control`. The existing `AdmissionGate` first requires the exact
existing regular, single-link DB and lock, then holds the same process mutex and
exclusive flock. Its lock opens`O_RDWR|O_NOFOLLOW`, without create or truncate.

Under that gate, connect to the resolved database URI with`?mode=ro`,
`uri=True,isolation_level=None,timeout=5`. Enable`PRAGMA query_only=ON` before
selected reads, verify it, set/verify the original foreign-keys and synchronous
connection settings and busy timeout, and require existing`journal_mode=wal`.
There is no immutable flag, backup/copy, write-capable fallback, journal-mode
change, DB creation, or lock repair. SQLite retains normal WAL visibility;
unavailable WAL/SHM access is a failure. A read-only DB connection and query-only
SQL do **not** prove zero OS writes: SQLite may perform normal sidecar
bookkeeping on the existing RW volume, the existing lock needs a writable
descriptor, and the new public receipt is intentionally written separately.

Begin one read transaction, bound the migrations query to six rows and require
the exact five versions before the existing validator iterates them. Invoke
the complete existing control validator before and after selected queries in
that same snapshot. It retains bundle/authority/review/bindings/capability,
schema migrations, instance/generation and DB+lock device/inode validation.
Always rollback and close before releasing the gate; never commit app writes.
The installed control bundle read is capped at1MiB and requires an existing
regular single-link file. No credential or DB-content digest is computed or
published by this binding operation.

Selected SQL uses fixed predicates and LIMIT plus bounded`fetchmany` before
materialization; no account listing, history/payload scan or patient array is
published. The packet records exact literal SQL/column contracts:

1. One archive by exact ID, at most2 rows: select`owner_id,mode,export_sha256`
   and fixed`json_extract(receipt,...)` metadata for admission/manifest/members/
   qualification/archive identity. Require one accepted saved-producer archive.
2. One account by that exact owner ID, at most2 rows: select only`id`.
3. The twelve descriptor patient IDs, at most13 rows: select only`id,owner_id`;
   require exact membership and the same selected owner for every member.
4. Selected archive at most25 distinct`patient_id,partition_id` pairs; require
   the exact24 public descriptor pairs, without reading record payloads.
5. At most one scalar active row from each of`analysis_attempts` and
   `pending_work` with status`queued`or`running`; any result refuses binding.

## Receipt, custody and authority

Distinct fixed kind`S1_SELECTED_OWNER_BINDING_V1`, namespace
`remission-s1-selected-owner-261024-r1`, and receipt
`/data/s1-p3-owner-binding-r1/owner-binding.json` cannot fall through to submit.
Its closed public schema permits only expected public provenance, one bounded
owner identifier, members12 and consistency/no-conflict/binding-only flags plus
submit/claim/fit=false. No credentials, sessions, email, patient arrays, raw SQL
errors or private digests are permitted. The4096-byte exclusive file is collected
only after successful supervision/reap through the existing single regular tar
member transport, hard-capped before parsing. Duplicates/nonfinite/extra fields,
wrong mode, filename, types or counts are rejected. App streams are discarded
and logging is disabled.

Reuse proposed900outer/840commonwork/870controllerwait/60setup/2reap bounds,
2CPU/2GiB equal swap/64PID/UID10001/RO root/no network/dropALL/NNP/128MiB noexec
tmpfs. The180 HTTP limit belongs to later submit, not a binding HTTP request.
Preserve literal acquired-CID typed resource/mount checks, strict matching live
owned watchdog PID/CID/nonce/deadline ACK before start, typed terminal PID0/exit/
OOM/restarts, all owned reaps and independent final stop. Uncertainty fails
closed; broader host/daemon descendants remain unknown. No new relative lease,
discovery cleanup, removal, retry or resource growth.

Binding SOURCE/OP reviews and fresh root GO are external orchestration metadata
as in accepted R5. Embedding the current review hashes in their own spec would
create a circular byte binding. The CLI spec SHA is a public immutable input
binding, **not permission**. A complete executable-by-shape candidate may be
frozen now with public expected values; only fresh independent exact SOURCE/OP
acceptance and an explicit root once GO authorize its invocation. Exclusive
fresh reservation consumes the attempt even on failure. No GO exists here.

## Tests and one additional authorized correction

Forty unique guarded controls pass: the prior27 plus13 focused binding tests.
They execute actual AST-extracted`validate_bundle`and`validate_control` on inert
metadata, with real app/Store/SQLite/science/network/native imports/actions
tripwired. They cover read-only order, schema/bindings/generation/DB+lock/WAL,
missing/multiple/foreign owner, bounded full membership/admission/pending work,
closed receipt/privacy, mode isolation, resources, timeout/unreaped/cross-mode
success rejection and the named receipt bound. No real SQLite or private Store
was opened. Actual WAL/identity/presence/operating feasibility remains unknown.

Root also authorized one source-proven Phase A correction:
`settings.installed.enabled`becomes`settings.installed.control.enabled`.
`InstalledBundle`has no top-level enabled field. The actual contract AST and
scalar counterexample prove that representation bug; this is not an observed
Phase A runtime failure. The entire existing submit`run()`inverse differs only
at this expression, and its admission/CSRF/stable POST/export guards remain.
Initial inert fixture-shim failures and the superseded45-count run (five imported
controls repeated) are retained; final40 is the unique campaign.

Accepted plan `6c6137af060fd135dc24c8ee654ba8a780f84cd4`, different critique
`591ad04dc23e4ca73d64d2192466110a695304ec`, and read-only source map
`f42b8c91f64fb0d8c91179031ea7d7b04f2929d6` are preparation evidence. Future GO
must explicitly permit the selected control bundle/DB/lock/WAL metadata access
and new public receipt write. Later authentication, genuine job fit/ingest,
saved-result/reload/browser and study/clinical gates remain separate.
