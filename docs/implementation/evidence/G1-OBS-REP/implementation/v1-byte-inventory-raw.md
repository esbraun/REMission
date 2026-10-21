# G1 OBS-REP v1 generated-product baseline

Base `6bc8bd998e8a0baaef9884998e740665fb5fd7b1`; branch `launch/g1-v1-products-20261021`; worktree `C:\Users\erics\Documents\Projects\REMission-worktrees\g1-v1-products-luna-20261021`. Source-only, read/hash inventory.

R1, §2 “Versioned wire proposal” and §3 “Archive, live authority and compatibility,” requires v1 parsers, schema URNs, dictionaries, fixtures, historical envelopes and hashes to remain reproducible while v2 uses separate paths/bindings. §5 includes a planned compatibility check requiring golden v1 raw/schema/dictionary/binding/fixture/snapshot hashes unchanged. The file list below covers all generated outputs from the domain and run exporters, only source files named in v1 run bindings, and checked-in raw contract fixtures. No tests/exports/code generation were run.

`contracts/runs/export.py` hashes binding sources after CRLF-to-LF normalization; values below are SHA-256 over exact Git blob bytes. `.gitattributes` explicitly sets `contracts/runs/** text eol=lf`; `contracts/domain/**` has no matching explicit rule. Thirty scoped worktree files differ from the base Git bytes only by checkout CRLF conversion; normalizing CRLF to LF reproduces their exact Git bytes. The JSON records each differing worktree byte count and SHA-256, alongside the Git blob hash.

## Generated products

| Path | URN / version | Git blob | SHA-256 | Locator |
|---|---|---|---|---|
| `contracts/domain/schemas/dgp-config.schema.json` | `urn:remission:domain:1.0.0:dgp-config` / 1.0.0 | `bad35c18eefed6165ab933b9038d6177826d18a7` | `fa6f2772ec72e5c04fda461aa8a8cb7c19f5cf3e15f1bdf4642021db8db4815f` | `contracts/domain/export.py` |
| `contracts/domain/schemas/estimand.schema.json` | `urn:remission:domain:1.0.0:estimand` / 1.0.0 | `9f004314c944dab797643ad43d50884a97287da8` | `05c964b2d29c7fc2a22572c8448e8039c7d7f665022f038eaa0296e8088aa4fb` | `contracts/domain/export.py` |
| `contracts/domain/schemas/evaluation-protocol.schema.json` | `urn:remission:domain:1.0.0:evaluation-protocol` / 1.0.0 | `b4cd68cd27e90ec47b38b430056ed50db8dcdc1d` | `c8fbf0b5cad9527ce4de8d8d9dd9c10d030a6d1c1154146a4c0967712f09b0c6` | `contracts/domain/export.py` |
| `contracts/domain/schemas/evaluator-truth.schema.json` | `urn:remission:domain:1.0.0:evaluator-truth` / 1.0.0 | `aae73417a14d141eab8aaf9002ccff5bad98397a` | `5aa61410c27a885e16da2e7a3a2a8156aa1f73986e759c7066cc9853c650f0c4` | `contracts/domain/export.py` |
| `contracts/domain/schemas/evidence-record.schema.json` | `urn:remission:domain:1.0.0:evidence-record` / 1.0.0 | `3501671e8662be893c54dbe8bbd965838a0df116` | `4cd496e4d3e6eef6ebeb6a9e33dfa33308d442fa805cb2b42de536be7165e9b1` | `contracts/domain/export.py` |
| `contracts/domain/schemas/external-study.schema.json` | `urn:remission:domain:1.0.0:external-study` / 1.0.0 | `d7f5cb3e0178883f0cfdfd71956e908796ee95c9` | `c802d33cd3cab73f25ae2290185498d15bff0658364fad0607fa00829d563b95` | `contracts/domain/export.py` |
| `contracts/domain/schemas/fit-metadata.schema.json` | `urn:remission:domain:1.0.0:fit-metadata` / 1.0.0 | `a657d421044261658294af6872720d4d3b76a4c3` | `1c2f6cd408eca8282ec0ddc8db6deb56ba720990a2431dbc79bd6f1249efcdb5` | `contracts/domain/export.py` |
| `contracts/domain/schemas/fit-request.schema.json` | `urn:remission:domain:1.0.0:fit-request` / 1.0.0 | `95f8c84ccdc5cabff3065ebb272229baa57d96cd` | `7c163ec3a8b3f8047f9dc4af86e1615e6bb9dbdcd951f9efa6652bbd779fa313` | `contracts/domain/export.py` |
| `contracts/domain/schemas/gate-evidence.schema.json` | `urn:remission:domain:1.0.0:gate-evidence` / 1.0.0 | `419ecf8fd7864556c01480de222c7d8cc1c6a2e2` | `83fd14cfaa63e0205f71c3d83a846fbb736d75f6bc75a443bd58378de92d78c7` | `contracts/domain/export.py` |
| `contracts/domain/schemas/interruption-result.schema.json` | `urn:remission:domain:1.0.0:interruption-result` / 1.0.0 | `6a7ee5c6fc3a7ea725bfa837bbc4837ff8c9e51a` | `757a43760f6b0586b9b87a865a65ab8be725472e3cbf43410a57afb924f3a265` | `contracts/domain/export.py` |
| `contracts/domain/schemas/learner-history.schema.json` | `urn:remission:domain:1.0.0:learner-history` / 1.0.0 | `d39a7f00ea368248204ee4f3013d16f09a18c248` | `8a20cd303f76458182deb654903a99fb9e5365076d6bf5c28f36d1fcdc989f92` | `contracts/domain/export.py` |
| `contracts/domain/schemas/learner-input.schema.json` | `urn:remission:domain:1.0.0:learner-input` / 1.0.0 | `ec3516206aa1a0c05485395ab8b77afb5acd2012` | `74533b319683b858fa9e2fd15be4bdd40dbe90729bab1ed41f31e84e1e62fe2b` | `contracts/domain/export.py` |
| `contracts/domain/schemas/observed-history.schema.json` | `urn:remission:domain:1.0.0:observed-history` / 1.0.0 | `782e8b2b0ea818b22c8fb2a1a57afe239e9cd48a` | `19b9c363bb2a53a693a01d6c43541fc54b09f204481f40b03f80ebe8ae29c60a` | `contracts/domain/export.py` |
| `contracts/domain/schemas/observed-records.schema.json` | `urn:remission:domain:1.0.0:observed-records` / 1.0.0 | `14b6c8cfc67b3fc9adbf73b6e06abe92d82ed7f9` | `206c08fe517e169adcab8ebc83572e616243056f23baf3a46089c2bbb76a00c3` | `contracts/domain/export.py` |
| `contracts/domain/schemas/replicate-result.schema.json` | `urn:remission:domain:1.0.0:replicate-result` / 1.0.0 | `a208aaa37c843dc57599f12238b67b8fa7514d4b` | `f047871e35ca18f029389cbb520208f866358f1a2745ea3028acec229e6211e8` | `contracts/domain/export.py` |
| `contracts/domain/schemas/reporting-decision.schema.json` | `urn:remission:domain:1.0.0:reporting-decision` / 1.0.0 | `c7783071edd092bb3a1e3a715a011d26e6ac3400` | `3070db119c9b5f07ee1640fb8e8292a0a26a0a2c558461304db07b31e4c31b36` | `contracts/domain/export.py` |
| `contracts/domain/schemas/temporal.schema.json` | `urn:remission:domain:1.0.0:temporal` / 1.0.0 | `70e092df9c35b9895d73972d343f5180d2bd9975` | `61425e6683b44b1609161775266ffbfa8cb04f9fccdb37f4e8e54a42b9abac0d` | `contracts/domain/export.py` |
| `contracts/domain/schemas/threshold.schema.json` | `urn:remission:domain:1.0.0:threshold` / 1.0.0 | `ecac818600a627f38a945b7a135a0357370a539f` | `aa6e6644e9f03dfbea8c67c5cf0b5e8c192fb6df345b4b0b2981d42df696b44b` | `contracts/domain/export.py` |
| `contracts/runs/schemas/calibration-artifact.schema.json` | `urn:remission:runs:1.0.0:calibration-artifact` / 1.0.0 | `0149ffb9b9b1c43d942eafec7098359c7b4eb303` | `e1ba454cdb8b094c8be28c7327e949002665594ef835dacb10669accc2fe19ad` | `contracts/runs/export.py` |
| `contracts/runs/schemas/evaluator-request.schema.json` | `urn:remission:runs:1.0.0:evaluator-request` / 1.0.0 | `5254f66771ba9de9432211972a80ebfd36ce9b02` | `fc06d3d1148f7fd0b54e6f1aa6e1621fe3cf040c0c788d015efe90f826cdc31a` | `contracts/runs/export.py` |
| `contracts/runs/schemas/evaluator-response.schema.json` | `urn:remission:runs:1.0.0:evaluator-response` / 1.0.0 | `2a35a48c442d86f2a3605ba74c1ee5bee6167539` | `583ad3aa3dccab5e16dd57add158e35f8b1357d4762719d65d9866473045ca12` | `contracts/runs/export.py` |
| `contracts/runs/schemas/external-calibration-evidence.schema.json` | `urn:remission:runs:1.0.0:external-calibration-evidence` / 1.0.0 | `04d0aa3476b5108d042d3b6651bb0c9c81d6ec9c` | `1bb422e1188b9175c08701223d158463a591d62668b4de38e491fe738d71f3a6` | `contracts/runs/export.py` |
| `contracts/runs/schemas/iid-investigation.schema.json` | `urn:remission:runs:1.0.0:iid-investigation` / 1.0.0 | `5545b552455736b421dbf71ef731f98fa9187702` | `1e4700b72070e1f1e15bb96de40450b887e0eb1aa656d87c3ba30c555e25d16b` | `contracts/runs/export.py` |
| `contracts/runs/schemas/observed-export.schema.json` | `urn:remission:runs:1.0.0:observed-export` / 1.0.0 | `54204a9d0c29ee8240f2ea54e9e2dff209f9b913` | `fd0bbdc4059c6298b46d20893c060121c501d9be14ba21a7f09e8f8071c2f304` | `contracts/runs/export.py` |
| `contracts/runs/schemas/observed-replay.schema.json` | `urn:remission:runs:1.0.0:observed-replay` / 1.0.0 | `af27485ec43de8fdba8163311a2e9f2659c6dc43` | `6ef37a10ede0d68755f8366985e56d77e4008936a2bbd18f95dfb06908892a63` | `contracts/runs/export.py` |
| `contracts/runs/schemas/probability-evidence.schema.json` | `urn:remission:runs:1.0.0:probability-evidence` / 1.0.0 | `56d427c1c2a4dd5b154c2481aec8422908e3f28f` | `359083c701598b3155c121baa6286876ab11d91223b8b7337f60777f5f9b0a4f` | `contracts/runs/export.py` |
| `contracts/runs/schemas/probability-paired-path.schema.json` | `urn:remission:runs:1.0.0:probability-paired-path` / 1.0.0 | `018fcae7146348c89082cd55470df07335c9066d` | `37d9da109f513e21177e2b68c97f08d0115e4254100dc1e85b390d150f79d086` | `contracts/runs/export.py` |
| `contracts/runs/schemas/probability-pilot-plan.schema.json` | `urn:remission:runs:1.0.0:probability-pilot-plan` / 1.0.0 | `be9a37d90c3d6680793d0d249e4af3506e0463a1` | `3fb722e7e696c47cc0120aeb85e83297dfc640e40fe79fed815245a01e99624a` | `contracts/runs/export.py` |
| `contracts/runs/schemas/probability-pilot-trial.schema.json` | `urn:remission:runs:1.0.0:probability-pilot-trial` / 1.0.0 | `8e9dfc412dcbc65ee22a3917d22c7c61c6a119c8` | `7797e384511fbae85ad8e0e90b19ea3932482c8c2a75627c5ac13782f158b109` | `contracts/runs/export.py` |
| `contracts/runs/schemas/probability-structural-proof.schema.json` | `urn:remission:runs:1.0.0:probability-structural-proof` / 1.0.0 | `265ed808d46717e49a559e2beedfc5b03894a728` | `e0779d40cf3e900efef2d38d1d35bbbcd72465533ab88804b4a467e747b141bb` | `contracts/runs/export.py` |
| `contracts/runs/schemas/probability-truth-filter-receipt.schema.json` | `urn:remission:runs:1.0.0:probability-truth-filter-receipt` / 1.0.0 | `f639a96247bdd4fd74a0533d1c9937ede028a7d8` | `f2103c596867c9448bccbe87ff721745f8338b745b95a9d95a81fe393d2aa3b5` | `contracts/runs/export.py` |
| `contracts/runs/schemas/run-manifest.schema.json` | `urn:remission:runs:1.0.0:run-manifest` / 1.0.0 | `60896bdd8e00081a6f5fb6274901bccc79088a49` | `419a91ab249e7b9ec6bf0c69d36a869376af52abd73c2af4a77f1a8d5f0e8f48` | `contracts/runs/export.py` |
| `contracts/runs/schemas/run-result.schema.json` | `urn:remission:runs:1.0.0:run-result` / 1.0.0 | `0d448a631418fe08bc12c690afe12042568cddb6` | `43f2ca8af4b0fe652c9f8e6642f3287027e34e8740cce811b6ae894c83e152d3` | `contracts/runs/export.py` |
| `contracts/runs/schemas/seed-ledger.schema.json` | `urn:remission:runs:1.0.0:seed-ledger` / 1.0.0 | `6fbd248f34a58397cf79787915e65b60e928b85d` | `2e5dc9941738a7e0f066bde2e06f7cab4d6a1c5ebd1f0cc8b208c0437ff0cc83` | `contracts/runs/export.py` |
| `contracts/runs/schemas/symptom-pilot-binding.schema.json` | `urn:remission:runs:1.0.0:symptom-pilot-binding` / 1.0.0 | `397d3b68d04666799fcec55240025c81a0e1bf6c` | `bbc6965631aa2443f91ad9d3700779ed426d192b574fe39be42744e58d5bcbef` | `contracts/runs/export.py` |
| `contracts/runs/schemas/trusted-export-authority.schema.json` | `urn:remission:runs:1.0.0:trusted-export-authority` / 1.0.0 | `ff1e1e082b3cfba01eac983dc9e4720a5b0cf0b9` | `52b0341f37dd9783da57e7e8e793b6bbaf0af19a0d0e193c7a08f2a666d198c1` | `contracts/runs/export.py` |
| `contracts/runs/schemas/trusted-iid-investigation-authority.schema.json` | `urn:remission:runs:1.0.0:trusted-iid-investigation-authority` / 1.0.0 | `099f136caaf0c94d1e163531553968275f6436fb` | `863d56cb3ae566fe4b92465731add0d3dc26634e8e51ffe91aba362e21214e60` | `contracts/runs/export.py` |
| `contracts/runs/schemas/trusted-run-authority.schema.json` | `urn:remission:runs:1.0.0:trusted-run-authority` / 1.0.0 | `744cc2c76b182c40f8e979333f114c0260722bdc` | `356d4e6fb9598d1b5aeb358338f53a674d59b3eeb5ea2a34a22d198fc72555ce` | `contracts/runs/export.py` |
| `contracts/domain/dictionary-v1.json` | `—` / 1.0.0 | `5a6dcfeabf75a8a262cffeb56e8d20ac9795ff96` | `3ef0512b6c4c83c972d0c42843cde260eba91ca7468bffa513842020a26412d5` | `contracts/domain/export.py` |
| `contracts/runs/bindings-v1.json` | `—` / — | `02a49d4594e035af3f0e44a520d05434c73b6058` | `0f48859258c76d56e4969cf87f54d94c70242f384ede632988e5c07c7796971d` | `contracts/runs/export.py` |
| `contracts/runs/dictionary-v1.json` | `—` / 1.0.0 | `4cb0f65c26cc7c6cb21cd9352e70a34491386365` | `81637308dbc9eee63bddb3fca54db4f8f21d84fd598774804013af8189d7f8b3` | `contracts/runs/export.py` |

## v1 run-binding source dependencies

| Binding key(s) | Version/ID | Source | Git blob | SHA-256 |
|---|---|---|---|---|
| `protocol` | `remission-g1-v1/1.0.0` | `docs/implementation/g1-technical-plan-20261021.md` | `5d46eb071485a9d5f2ed0473880a75fcab181556` | `730871eadff578f6e51fd75035876fb338bd9c168b71d84021b3e287664ef2e2` |
| `dgp` | `DGP-01/1.2.0` | `contracts/dgp/parameters-v1.json` | `9b67acbd5b2e63c952918b29fbe161adf4e208b9` | `f273d92792e09570c19a9145c09da08e3c214ac6d520059f12b3c26809e5b22d` |
| `parameters` | `DGP-PARAMETERS/1.2.0` | `contracts/dgp/parameters-v1.json` | `9b67acbd5b2e63c952918b29fbe161adf4e208b9` | `f273d92792e09570c19a9145c09da08e3c214ac6d520059f12b3c26809e5b22d` |
| `equations` | `DGP-EQUATIONS/1.2.0` | `docs/spec/dgp-reference.md` | `62f7894b887acbaab603b33da4f90cc85405c8a3` | `16b61de53f7b9fb6e837db63d89ccbc0efc105300d8bbd80ceec6cfbbf216b84` |
| `scenarios` | `DGP-SCENARIOS/1.2.0` | `contracts/dgp/scenarios-v1.json` | `b5b542bfbb83e970f57af0676b78b9b942f97263` | `ed5e29aa398b615c623e24d218b8442f3ab14c2bf4187e6657b2589bde7809ac` |
| `catalog` | `DGP-CATALOG/1.2.0` | `docs/spec/scenario-catalog.md` | `a5e6b6c5b6fc855090b94ddf86cbe3647a8f2975` | `ef8f5720ac05b887d2def3f44b09dcf29be352474940bc8ed8ec7ba49d6eee40` |
| `timing` | `DGP-TIMING/1.2.0` | `contracts/dgp/timing-v1.json` | `e336c9f22a5734fe3a33da3f3f2d4b97a9d4ab7d` | `336a3a9e5182212cf26f873359c82e08f92f154a5dbe34ceb280cf6a5feed87b` |
| `temporal` | `TIME-01/2.0.0` | `contracts/domain/temporal-v2.json` | `ce009c021e65bfca5b8ab6f9b630ab2013767944` | `fd2fe478e1fbf5237a307af8a2067fd6d485183763086ac7e10c133fda002275` |
| `calibration_schema` | `DGP-CALIBRATION/1.1.0` | `contracts/dgp/calibration-binding-v1.schema.json` | `f2cbfd79e0732cc336a7b0ed9194a8ecdc25b361` | `cfbaa02466c698c2ab24457eeddfd94bc18e25264491442d9f5e6b268f2154c6` |
| `analytic_fixtures` | `DGP-ANALYTIC-FIXTURES/1.0.0` | `contracts/dgp/truth-fixtures-v1.json` | `f327e36e2264d3a8cd5e6da270a7e0196f4355b6` | `059032cf5e0e1c6849eab8ed42237a0ddf2255366410d1be4bfbf5e99f75fcae` |
| `probability_precision` | `ESTINT-PRECISION-01/1.0.0-r1` | `docs/implementation/g1-estint-probability-precision-proposal-r1-20261021.md` | `233d78d5f9233499e566c87ecf34d3d4f12e3785` | `087e61f462c4447697f40de8471c818de58346e0b2a8f330854392585f43e989` |

## Raw fixtures

| Path | Git blob | SHA-256 |
|---|---|---|
| `tests/contracts/fixtures/estimands-v1.json` | `92c9d25c9d4c40347bed75bdb237c7634f465903` | `6bfa95f18fcd8cd3e1932ab12526c92a2304e7d05b868e1e8b6edb4c1eb67b94` |
| `tests/contracts/fixtures/observed-entities-v1.json` | `9a4c6c941667ac6f6fb164443c81b285804d29a2` | `782b8ca7d704270c94cee94906d7765becc39615d475e3b413a6db16f66cb6fa` |

## Regeneration and cross-version risks

- The domain exporter derives 18 schema files and the dictionary from Pydantic models. Changes to shared types can alter the observed-record union and other v1 products. Keep v2 adapters/output paths separate so v1 checks remain reproducible.
- The run exporter emits 20 schema URNs under `urn:remission:runs:1.0.0:*`, plus bindings and dictionary. Model-list changes or direct schema edits change generated v1 products.
- Any edit to a source named in `bindings-v1.json` changes its regenerated binding hash, including the protocol plan, DGP parameter/scenario/timing inputs, TIME-01 v2, analytic fixtures and accepted probability-precision R1. `dgp` and `parameters` intentionally bind the same source.
- R1 explicitly requires separate v2 bindings/dictionaries/schema URNs. Do not globally change `Versioned.schema_version` or rewrite v1 fixtures/history. Existing v1 dispatch and hash bindings depend on these identities.
- Static raw fixtures are contract examples, not qualified production exports. The scoped run tests assemble fixtures in memory.

Machine-readable per-path Git blob IDs, byte counts, exact hashes and working-byte comparisons are in [`v1-product-baseline-luna.json`](v1-product-baseline-luna.json).
