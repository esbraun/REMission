# PoC ablation harness: requirements intake and source map

**Status: intake/source inventory only; pending Astra design and independent critique.** This note records a new user requirement against the frozen source tree at `3a65db89118d0c941b03800620e71b8aab871507` (branch `docs/poc-ablation-harness-intake-20261024`). It does not amend the accepted scientific plan, define a study, approve a data model, or authorize implementation or study execution. The source locators below use repository-relative paths, line numbers, and Git blob IDs at that base.

## Requirements to carry forward

The user's new instructions are:

> “at the appropriate time and plan step, have an astra agent carefully design the ablation study- we need to sinulate sleep data from a device like oura, EMR clinical features, patient demographic features and treatment features at least. the ablation doesnt mean much if our simulation isnt robust. document these requirements for the appropriate time, and make sure the analytics we develop themselves are ready for the appropriate breadth of covariates”
>
> “also, treat the ablation study as a testing harness- well need to study multiple iterations of analytics overtime, so we must consider this a modular reusable framework”

Treat these as requirements for a **future study design and amendment**. At minimum, the simulated source domains must cover (1) Oura-like device sleep measurements, (2) EMR clinical features, (3) patient demographic features, and (4) treatment features. “Oura-like” means mocked synthetic records; no live device/account connection is requested. Simulation robustness is a prerequisite for interpreting ablation comparisons. The analytics and their consumed feature inputs must be assessed for the intended breadth of covariates, and the study workflow must support repeated iterations of analytics through a modular reusable harness.

Carry forward the existing functional modest-PoC boundary: keep work synthetic; preserve the existing app and its current scope; do not add a training UI or appointment fitting. This intake does not select covariates, hypotheses, estimands, study conditions, distributions, dependencies, statistical methods, schemas, or new architecture, and it makes no claim that any of the four domains is already covered end to end.

**Required timing gate:** queue the Astra design and independent critique before choosing or changing the DGP, scenario set, feature contract, pilot, or frozen study protocol. This gate is before design freeze and execution, not a retrospective review after running the study.

## Source inventory at the frozen base

This bounded public-source inventory covers 16 files. It records what the current tree shows and where an identified consumer boundary stops; “missing” means absent from the inspected path, while “unknown” means this inventory does not establish it. The existing [longitudinal truth/seven-condition plan](poc-truth-ablation-plan-20261022.md) remains the controlling accepted plan until a reviewed amendment says otherwise. Its [task ledger](poc-truth-ablation-task-ledger-20261022.json) records substantial unfinished truth, runtime, and study dependencies; this note does not reinterpret its status.

| Source (line locator; frozen blob) | Observed feature families / consumer or harness boundary |
|---|---|
| `services/generator/restricted.py:73-108` — `98412e5b3789abfa974d004adec28ff5eda8a293` | V1 synthetic baseline writes empty `covariates`, diagnosis/clinical context strings, daily self-reported sleep quality, function, diary minutes, missingness, and 14-day ISI. No generated device/wearable records or age/sex/demographic values are present in this generator path. |
| `services/generator/restricted_v2.py:29-68,71-80` — `a034179a6acf979c4c8988cf759f2bcbcddc0b6c` | V2 adds medication and support schedules, adherence/delivery records, and support's effect on reported quality. This establishes treatment-feature generation for these restricted schedules; broader clinical treatment histories are not established. |
| `services/generator/research.py:27-44,76-101,135-170` — `4ffe619d9150bde0a78d75fce067ded565e60ced` | Existing V1 research preparation binds a fixed n=12 reference, assignment and replay/export workflow. This is a producer path, not a general repeated-ablation runner. |
| `services/generator/research_support.py:33-53,160-196,274-342` — `8582c5c4842f0e93a59cee5b6ce0654fc9a3ac31` | Existing support research producer builds synthetic support histories and a fixed cohort workflow. Its presence does not show a common producer interface across analytics or scenarios. |
| `contracts/domain/entities.py:16-44,87-165,305-342` — `64a3a763b276c0f3e0c242966506e323c4273513` | Broad observed-record vocabulary includes generic covariates (including age, site and steroid indicator), diagnosis/clinical context, medication order/exposure, Oura-like sleep episodes, patient reports, assignment, and delivery. This is contract capability; it does not mean the restricted generator emits or a current model consumes all fields. |
| `contracts/domain/analysis.py:38-43,49-102,109-145,187-241` — `8de671be4963e8a8cc15cdf1c05a2378bb2faa61` | V1 analytic H* deliberately reduces inputs to daily sleep quality/missingness, ISI total/recall, behavioral assignment and delivery lineage. Function, diary minutes, generic covariates, clinical context and wearable observations are outside this consumer input. |
| `contracts/domain/protocol_analysis.py:40-86,227-280` — `8762313d11d8d07f487fd46d68c82eadc927b4e8` | Protocol reduced history represents quality, ISI, assignments/deliveries and support decision/outcome records. The schema’s existence does not establish demographic or EMR-covariate ingestion by consumers. |
| `methods/visit/model.py:10-30,68-128` — `5e33008e36809b78f182993a88f1e09bdf641c78` | Visit model inputs derive quality, ISI, and behavioral exposure from reduced H*. No code path here consumes the broad entity covariates, wearable records, or EMR context. |
| `methods/nof1/data.py:21-48,57-171` — `a65dbd5d326fa715a2add50edfa5603c1917f29c` | N-of-1 prepared data retains quality/ISI and behavioral plus medication exposure arrays from protocol history. It does not demonstrate broad clinical or demographic covariates in the model input. |
| `methods/support/data.py:23-53,64-157,213-214` — `42bdb124b02bfd32f344036eb0e93f6288ec062e` | S1 feature builder uses prior reported quality (default 7 when absent), a prior-quality-missing indicator, delivered prompts in the prior six nights, and time fraction. This is a narrow current feature contract, not evidence of readiness for the requested breadth. |
| `methods/support/wcls.py:23-36,67-110` — `130b22afe36bcc3c864602aff1a5dbafe746a207` | Current S1 estimator configuration and design are explicitly small and versioned. A future breadth review must account for each analytics consumer’s own feature contract rather than infer readiness from generator fields alone. |
| `methods/truth/restricted.py:21-82,188-204,276-407` — `98a8a3e8f3f1902a6e0552e7b46b94af55e0d616` | Existing conditional-truth engine is bound to restricted V1 history and its settings/evaluate function. It is not a general multi-analytics ablation abstraction. |
| `methods/truth/refinement.py:40-66,93-168` — `2851d52aa130f3ce05f1de9cb8eae6e65da7cd02` | Refinement workload, binding validation, per-row result validation, and reduction are frozen for a specific truth-refinement task. The current workload is not a pluggable cross-analytics study manifest. |
| `services/evaluator/restricted_refinement.py:48-114,116-170` — `4b83dfebe35ab710d4122cfe3cdba0e4340b6b5b` | Runner already has useful seams: plan/expected binding/history inputs, an `evaluate_one` callback, per-attempt inventory/result/outcome files, reduction, and explicit status/timing. Its CLI and validation remain TA2-specific; a reusable ablation harness is a design question for Astra, not an existing capability to claim. |
| `docs/implementation/poc-truth-ablation-plan-20261022.md:1-15,77-106` — `e73a951b6d879f97c786e84dfc4e40980b53c5b8` | Accepted plan separates truth, paired runner, and saved app handoff, and labels incomplete dependencies. It does not yet include the new four-family simulation breadth requirement. |
| `docs/implementation/poc-truth-ablation-task-ledger-20261022.json:1-20,231-293,369-373` — `b4892a97f1733d411c9d345f36cc99d00d9312b5` | Existing ledger explicitly leaves later family truth, paired runner and handoff work pending. This inventory did not inspect or copy evidence corpora or private run inputs. |

### Coverage reading, limited to inspected sources

| Requested domain | Current observed status in inspected sources |
|---|---|
| Oura-like device sleep | **Contract present; generated/consumed in this restricted PoC path: missing.** The broader entity contract has an Oura-like sleep-episode record. The restricted generator currently emits patient reports and ISI instead; the examined V1, N-of-1, and S1 consumer inputs do not accept wearable records. |
| EMR clinical features | **Partial/unknown.** General entity contracts represent diagnoses/context, encounters, medications and intercurrent events. The restricted generator emits a fixed diagnosis/context string, while V1 H* excludes it. Which clinical records belong in a synthetic EMR-like study, their chronology, and analytic use remain unknown. |
| Patient demographics | **Generic contract vocabulary only; current restricted generator/model coverage: missing.** `ObservedCovariate` supports some generic measures including `age_years`, but restricted V1 writes `covariates=[]`, and inspected consumers do not consume a demographic covariate vector. The exact intended demographic fields are not chosen here. |
| Treatment features | **Partial coverage.** V1 generates behavioral assignments/deliveries; V2 adds restricted medication and support schedules. Current consumers encode these treatment histories in family-specific reduced inputs. The intended breadth of treatment features remains unknown. |

The current generator/consumer mismatch matters for ablation validity: a feature existing in a general record type is not evidence that the simulator generates it with an adequate joint/temporal structure, that a feature contract preserves it, or that a target analytic uses it. Astra’s design needs to trace all three layers for every planned domain and analytics version.

## Existing harness seams and future Astra handoff queue

Observed seams are: two distinct research producers (`research.prepare` and `research_support.prepare`), versioned analytic and truth inputs, a truth evaluator function with explicit settings, and a refinement runner that records every frozen attempt. The inspected source does **not** show a shared manifest/plugin contract for selecting multiple analytic versions, ensuring common synthetic inputs and paired comparisons across those versions, or running them over a reusable ablation matrix. That is an inventory finding, not a recommendation for a new service or architecture.

Queue for root to dispatch to Astra before DGP/scenario/feature-contract/pilot/study freeze:

1. Incorporate the two user instructions above into a proposed amendment to the existing PoC ablation plan while preserving its current scope and distinguishing accepted plan from future proposed work.
2. Design the synthetic data-generating study across all four minimum families. Assess whether the proposed joint data are robust enough for meaningful ablation, state the evidence needed to justify that assessment, and explicitly distinguish generated source records from reduced analytic inputs.
3. Map the breadth of covariates each candidate analytic can actually ingest, identify where consumer contracts/models would need reviewed expansion, and state unknowns. Do not assert compatibility solely because a generic domain schema can represent a field.
4. Design the reusable testing-harness requirements for successive analytics versions, including version/input/result identity, paired-input and attempt/failure accounting, and how the existing research/evaluator seams might be reused. Propose the smallest suitable design within the modest-PoC boundary; do not assume a new architecture.
5. Obtain a separate independent critique of the proposed study design and amendment before freezing any DGP, scenario, feature contract, pilot, or study protocol. Record disposition and unresolved points before implementation or execution is considered.

**Freeze:** this contribution is only requirements intake and a source map. No application/service/model/generator/contract code, existing plan, ledger, or study setting is changed here. No runtime, numerical, scientific, database, private artifact, or network operation was performed. Astra’s design, independent critique, and root’s disposition remain queued.
