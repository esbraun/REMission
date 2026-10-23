# TA2 first refinement: completed diagnostic evidence, accuracy unresolved

2026-10-23. One authorized refinement operation completed all128 evaluations in32 independent replicate groups. This is evaluator-only numerical diagnostic evidence for the frozen synthetic patient/history. **It does not qualify TA2 truth, estimator accuracy, appointment performance or clinical effects.** No matched estimator SE was supplied; reduced quadrature, full-history conditioning and finite53-bit-versus-continuous-law qualification remain unresolved.

Owner `/root/truth_refinement_sol`, actual `gpt-6.1-sol/high`, own worktree `C:/Users/erics/Documents/Projects/REMission-worktrees/truth-refinement-sol-261023`. Documentation/evidence branch `docs/poc-truth-ta2-refinement-20261023` starts at accepted PR43 merge `6413979188099a6b283d7e5e4d5dc15e6e03b15e`; the original feature branch is preserved. Source candidate `9b77f782d79f34b462aa13932590021a61b2c8ab` and executed frozen source `97d3ae8794b60f51232bf12b4e2c41af2292db75` are unchanged. No scientific source, input, operator, setting or invocation was amended after review/GO.

## Authority and actual operation

The [source-preparation handoff](poc-truth-ta2-refinement-prep-20261023.md) retains the16 scalar-fixture checks, prior failed preparation/fixture checks, exact plan and accepted TA1 review. Independent exact source/operation review `c709b92be543f88f7c36cc307f9509a252c9d9df`, checks `223faaefc2974d98761d3f15972adebe6bee64bf`, accepted the source and bounded operation. Postmerge verification `d5da369558a0024d2d3d219d9694879af21b5dcd` passed19 static checks: exact merge parents/tree, all17 frozen files,14 execution-source files and actual host wrapper/helpers matching accepted merged bytes, unchanged TA1/lifecycle/admission and intact input/ledger/check evidence. Root then issued one explicit GO on invocation SHA256 `aa69f1b9a48c44915a271f77dc9bd433476c2b49a8d61704304ed34c852036b2`. There was one reservation/create/start, no retry or extra evaluation. Existing14-test TA1 reproduction was not repeated.

The exact command, run from the reviewed worktree without `-P`, was:

```text
python -B -m tooling.foundation.truth_refinement run --stage C:/Users/erics/Documents/Projects/REMission-worktrees/truth-refinement-sol-261023/artifacts/truth-ta2/refinement-01 --token aa69f1b9a48c44915a271f77dc9bd433476c2b49a8d61704304ed34c852036b2
```

The frozen [invocation](evidence/truth-ta2-refinement-20261023/raw/invocation.json), [independent expected binding](evidence/truth-ta2-refinement-20261023/raw/input/expected-binding.json) and [ordered workload](evidence/truth-ta2-refinement-20261023/raw/input/workload.json) preserve source/file hashes, exact complete refs, image/runtime, PRNG/seed recipe, settings and argv. The actual worker checks Python3.13.7/NumPy2.5.4/SciPy1.18.1/Pydantic2.14.1 before any evaluation; terminal success confirms that check passed, rather than a separately printed package-version observation. The existing dependency image was `sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa`, selected as linux/amd64. No image pull/build, install, app/DB/browser/cloud action, credential/private-generator mount, learner fit or training occurred.

Fixed patient `p-08aa51d3e737479495085ea07881adcf`,27455-byte H* SHA256 `5bd8d8ebcd84ff862cb3caa8255f7b9cb8eba73aba3e2d2a7a721993743b3289`; cutoff January15,2026 noonUTC/day14; expected rounded/clipped ISI escalation minus continuation at absolute day56, recall43–56,42 future nights, retained visits28/42 and no prompt. NumPy-PCG64 namespace `truth-ta2-development-20261023-v1` is separate from generation and fitting. Replicate IDs0–31 are independent groups; using the same replicate/process keys across particle/move variants intentionally couples them without assuming variance reduction or identical trajectories.

Serial workload:1024/4096/16384 particles, moves2,32 filters each, then16384/moves4 for the same32 keys; slice limit128, two10000-trajectory future batches per filter. Network-none/read-only container,2CPU/2GiB/equal memory-swap/PID64/UID10002/dropALL/no-new-privileges/private512MiB exec tmpfs, BLAS threads1; only isolated evaluator output was writable. Per-evaluation60s, internal1740s and absolute1800s lifecycle ceilings were unchanged. Selected capacity observations are retained separately as a point-in-time snapshot, not a scalability result.

## Observed reductions

[All128 attempted rows](evidence/truth-ta2-refinement-20261023/raw/output/refinement/inventory.json) are present and complete, with zero failed/inconclusive/pending/running rows. Every row retains exact seeds/settings, two batch counts, result, filter diagnostics, timing and memory scope. There were2560000 future trajectories over all variants; each level/screen has640000. These are32 independent filter groups, not128 independent groups or millions of independent conditional filters.

| Particles / moves | Mean contrast, ISI points | Within-filter rollout MCSE of mean | Between-filter MCSE |
| --- | ---: | ---: | ---: |
|1024 /2|-1.6906930190533624|0.000308674159214|0.003125587975025|
|4096 /2|-1.6942796906173796|0.000309208435736|0.001371848766240|
|16384 /2|-1.6933555158438140|0.000308225245863|0.000631765806709|
|16384 /4 stability screen|-1.6939847438905260|0.000308862279325|0.000559256364611|

| Actual paired contrast | Signed mean difference | Sample paired SE | abs(mean difference)+1.96 SE |
| --- | ---: | ---: | ---: |
|4096 minus1024|-0.003586671564017|0.003245676418685|0.009948197344640|
|16384 minus4096|0.000924174773566|0.001372524357519|0.003614322514302|
|moves4 minus2 at16384|-0.000629228046712|0.000743485798451|0.002086460211675|

The [raw reduction](evidence/truth-ta2-refinement-20261023/raw/output/refinement/reduction.json) preserves full precision and formulas from actual replicate differences. Between-filter MCSE conservatively contains rollout variation; the four move/particle variants are not new independent replicates. The .05 absolute target is provisional: `status=unresolved`, `budget_diagnostics=null`, `matched_estimator_se=null`, `quadrature_change=null`, `finite_grid_discrepancy_bound=null`, `full_conditioning_qualification=unresolved`, `production_truth=false`, `root_admission=closed`. Small empirical differences do not establish unbiased conditioning or settle the remaining gates. No uncertainty was borrowed from the different served V1 patient.

## Timing, memory and terminal evidence

Typed container start/finish:08:18:10.392537370–08:20:28.283903969UTC, about137.891s (138s rounded). Driver total136.176299s; main validation/numerical import startup1.104663s; reduction/report write0.004839s. Top-level stdlib imports/container startup are excluded from the main-startup value. Exact whole host operator lifecycle wall time was not separately captured; the container timestamps are the retained external duration. This is one evaluator workload, not learner fitting, saved-read latency, APPT-04, p95 or a scaling benchmark.

| Particles / moves | Sum conditioning seconds | Sum future rollout plus evaluator bookkeeping seconds | Sum row elapsed seconds | Maximum row elapsed seconds |
| --- | ---: | ---: | ---: | ---: |
|1024 /2|9.783819|2.833072|13.956809|0.523982|
|4096 /2|15.585935|2.833515|19.915413|1.229634|
|16384 /2|35.993207|2.326294|39.817422|1.354055|
|16384 /4|53.289853|2.270099|57.047661|2.125244|

Process-lifetime peak RSS141608KiB; container cgroup `memory.peak`107696128 bytes. These retain different accounting scopes and are not interchangeable or per-evaluation allocation measurements. Missing memory values were not replaced with invented zeroes. Each stage/row's raw scope is retained in the inventory and [timing](evidence/truth-ta2-refinement-20261023/raw/output/refinement/timing.json).

One literal CID `1eedc9313f92bc361c2dfe44403f887282bf0430ae6a5fdc252991afb9e3f4d3`, matching prearm ACK/deadline782125.5987331, typed terminal exited0/PID0/Runningfalse/Deadfalse/OOMfalse/RestartCount0, attach0/watchdog0 reaped, operator session30765 exit0, failure null/cleanup[]. The unchanged accepted lifecycle supervisor independently audited terminal state. All resources/logs were retained; nothing was removed or restarted. Four empty process logs remain exact zero-byte copies, without weakening canonical `Artifact.bytes>0`.

## Evidence preservation and remaining gates

[Curated manifest](evidence/truth-ta2-refinement-20261023/curated-manifest.json) binds23 physical copies by exact bytes/SHA256/Git blob: full128-row inventory, raw reduction/timing, source/runtime/input/invocation/ordering bindings, reservation/create/prearm/terminal/reap/logs, and capacity/postmerge records. [Actual evidence manifest](evidence/truth-ta2-refinement-20261023/actual-evidence-manifest.json), Git blob `90e2a7a81b9bafdd603c1a2cfd14d735d2e90c57`, indexes all548 original raw Git blobs, including per-row journals. Original raw manifest blob `65c9762208153b00843b39660c3d747170eac097` matches its exact file set/byte hashes. Physical copies are preserved with local `.gitattributes -text`; the existing byte/hash/Git-index check pattern verifies them without numerical imports or re-execution.

This evidence candidate requires separate independent Astra review against base6413979 before root PR/integration. Matched same-patient/H*/target estimator SE, applicable independent reduced quadrature allowance, full conditioning/finite-grid qualification, restricted admission and actual denied learner access remain open. TA3–6/seven-condition study, N0/N1/S2 operational work, APPT-04 and all human/clinical gates remain open. Genuine accepted V1/PR41/PR42 and earlier failed checks were neither repeated nor relabeled. No study-level accuracy/superiority/scaling claim follows from completing this operation.
