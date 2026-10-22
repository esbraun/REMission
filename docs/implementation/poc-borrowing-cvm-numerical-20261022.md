# PA3 fixed-point CVM full-target qualification

The single authorized suite completed with runner status **accepted**, session52936, in1560.516450s under the shared1800s cap. All seven actual containers terminated exit0/notOOM. This is measured fixed-point qualification, awaiting independent evidence review; no posterior, production worker, native NUTS fit, accuracy or clinical acceptance is claimed.

Executable source is `6edeb1e9b4108399a6fbfdfdd5bb71a6e78989d5`; launch observer is `c3900aeeb92c03415a0191a2e03ee8a979aa8e04`; integration base is `045b373a18ad067a3ecd1281d445076aae423a80`. Later commits throughbd904 added only protocol-plan/proposal Markdown and did not change this executable. Actual gpt-6.1-sol/xhigh was retained for native combined mapping, full-target identity, actual VM and deadline evidence. Root authorized execution after independent SOURCE/COPY READY `ea549527774662af4c2e65479cce29d2bc352814` (index027d79bf9914a99f865f0172f903576876332336).

Exact command: `python tooling/foundation/run_pa3_compile.py --image sha256:b02a38ed1fd03841494935e03246ab0dbec419905e3e90b5a2f393cacd57d45e --evidence artifacts/pa3/cvm-run-6ede --cvm-policy tooling/foundation/pa3-cvm-policy.json`. Physical policy SHA256 is `bd708a70ed2f3a0df8ffc6985479e3269c8160571f8fbc97bfab364b0afd8892`. The [origin](evidence/pa3-cvm-numerical-20261022/origin.json) preserves executable/observer/image distinctions and bindings; inherited image origins remain the accepted source-build history, not relabeled as this report.

The legacy day14 input has H* `b0904f5ecd80781b474fa42d0b74f0e3a36cdb33d364535cf5f1d548ddcce034`, cutoff2026-01-15T12:00:00Z, physical input SHA74139ac2dfdc945dd1eb0be1e176f2ec66386dee39a09717c1f5a0b8da8551ac. Configuration is productionQ64 hash114d69435430a98d60d1724a30ba89073efebd5ba0e1b7bdae55ddb3f3a90675; public two-study source set11420d1f40754021a13cd7fed1152bc824d6b669af233efe60a0dc4facec9ddb. This is **not** the later queued4ff/ce5a patient information set, so its cost cannot substitute for that actual-H* profile.

The [numerical summary](evidence/pa3-cvm-numerical-20261022/qualification-summary.json) was recomputed from returned arrays with the unchanged runner qualifier, without model evaluation:

| Check | Observed result | Frozen gate |
|---|---:|---|
| Guided own-coordinate FD,47×3 | max absolute error7.94990e-8 | absolute1e-5 plus relative1e-4 |
| Original own-coordinate FD,47×3 | max absolute error8.69002e-8 | absolute1e-5 plus relative1e-4 |
| Native combined vs separate guided gradient | max absolute difference3.97904e-13 | same gradient gate |
| Native combined vs separate guided logp | max absolute difference2.84217e-13 | absolute1e-8 |
| Guided logp = original + log(80) + mapped Jacobian | max absolute error3.76894e-8 | absolute1e-7 |
| Original minus unchanged localV0 = independent two-source+original-prior term | max absolute error3.80932e-9 | absolute1e-8 |
| Omitted/doubled/reversed negative controls | minimum separation3.92733 | each greater than1e-6 |
| Changed source changes target, all3 points | absolute deltas.0114940/.0104494/.0875615 | each greater than1e-6 |

The guided gradient also reproduces the frozen diagnostic Monitor FD vectors. Gradients in unequal coordinate systems were never directly equated: each uses its own coordinate finite differences; the mapped density identity includes the Jacobian. Native ValueGradFunction initializes extra values before every call and publishes the explicit names/shapes/float64 offsets covering all47 coordinates.

| Phase | Host elapsed seconds | Compilation seconds | Warm median / p95 milliseconds |
|---|---:|---:|---:|
| guided-gradient |473.232|465.965|5.554 /7.343|
| guided-native-logp-gradient |474.030|466.951|7.320 /11.852|
| guided-logp |50.102|46.264|2.467 /2.800|
| original-logp |41.534|37.860|2.455 /3.068|
| original-gradient |460.142|453.061|4.093 /5.004|
| local-logp |14.379|11.819|.0717 /.1060|
| changed-logp |41.172|37.702|2.429 /2.741|

Every compiled function inventory records actual `pytensor.link.c.cvm.CVM`, VMLinker/use_cloop/c_thunks true and empty callbacks, rejecting whole-VM fallback. Individual operations may still use Python thunks. Requested optimizer is exactly the default OPT_FAST_RUN query, with no exclusions; actual compiled queries additionally include PyMC's local_check_parameter_to_ninf_switch/random_make_inplace registrations, disclosed in full inventories. Full stderr retains no-BLAS/NumPy C-API messages and a kernel-argument fusion warning in each gradient phase; no rewrite ERROR appears. A warning alone establishes no causal explanation for the earlier Numba timeouts.

All phases used2CPU/2GiB, UID10002, networknone, ROroot, cap-dropALL/no-new-privileges, private exec/nosuid/nodev scratch. Old reference/input volumes wereRO and only each new output wasRW. The three gradient phases reached cgroup memory.peak2147483648 with max events10054/10133/10208, but oom/oom_kill/group_kill all0 and actual terminal OOMKilledfalse. This demonstrates compilation under the cap with substantial pressure, **not spare memory headroom**. Full event streams, terminal state and resource/mount identities are retained. Phase600s/shared1800s stop-and-veto logic remained active; this successful run did not exercise a timeout. Prior watchdog negative controls and failed runs remain unchanged.

[The raw manifest](evidence/pa3-cvm-numerical-20261022/raw-manifest.json) is33784bytes/SHA256 `5877967d29ae358134037f5b6eba59bb7ea2bfad15ac7039d417bd09f1dd2124`, freezing167 physical files under the exact own roots `artifacts/pa3/cvm-run-6ede` and `artifacts/pa3/cvm-execution-6ede`. **No more writes will occur in either root or the seven output volumes.** Assigned reviewer/root may read only those frozen roots, exact named volumes from its RO allowlist, seven retained actual containers and the immutable image; live8780 DB/other WIP are excluded. Unique main-command matching binds complete stdout/stderr to each compute container, separately from later hash helpers. [Physical volume hashes](evidence/pa3-cvm-numerical-20261022/physical-volume-hashes.json) verify all11 volumes, including actual input/policy reference bytes and all phase outputs, against retained host captures. Full inventories remain ignored outside Git; bounded summaries and complete numerical arrays/streams are committed.

The next proposed step, after independent acceptance, is a separately reviewed **borrowing-only** use of this supported CVM compilation mode through the existing native PyMC path, preserving defaultV0 and all mathematical/prior/sampler/precision gates. Before fitting, qualify its native combined function and memory/compile lifetime on the actual queued4ff/ce5a H*/cutoff/source/seed binding, with the same actual-VM/mapping/FD guard and hard bounds; release prior-predictive graph references before posterior compilation rather than retain two graphs. Private scratch needs the already demonstrated exec/nosuid/nodev property for compiled C modules. This is a concrete source/profile proposal, not implemented or authorized by the present result. Native sampling, posterior bridge/effect precision, Q128 diagnostic family, paired day14/day42 refits and actual result ingestion remain unmeasured. Original OOM, Numba deadlines, loader failure and diagnostic-only Monitor evidence remain frozen separately. Existing-app continuity PASS6b607 and PA1+thinPA2 PR22 acceptance remain scoped; full shared cohort/PA2 consumption, PA4–7/studies/human review remain open.
