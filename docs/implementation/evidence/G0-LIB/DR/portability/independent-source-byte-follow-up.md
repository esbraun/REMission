# Bounded R1 producer-source byte follow-up

2026-10-21. Frozen source d84203709b0164a0824913950c1d7cd7be25a2fb, accepted base f11e90536b635a7db08cfed640445bec197a415c. Astra/medium requested; effective introspection unavailable. No new qualification/ship approval or DR-plan change.

Result: **fresh LF reproduction succeeds; no demonstrated defect in the committed R1 source hashes.** A Windows checkout/replay limitation remains explicit below.

The R1 lineage builder hashes exact bytes of captured producer sources. prepare_exchange_r1.py uses shutil.copyfile from the producer paths into its source snapshots, with no source newline normalization. Its recipe/source VersionRefs therefore identify the captured execution-source bytes, not a documented canonicalized source representation. The workflow source is then run from those producer paths. Committed source snapshots are LF and exactly equal to the corresponding Git source blobs. This is consistent with the author's observed run capturing LF files before Git later materializes Windows checkouts; there is no evidence that the builder silently normalized executed source. The report does not assert independent authentication of the author's historical process.

.gitattributes marks both exchange trees -text, preserving exact raw payload/source-snapshot bytes. Ordinary tooling/library/*.py and *.R have no text/eol override; this reviewer's inherited system core.autocrlf=true materializes those ordinary source paths as CRLF. Consequently, in the ordinary Windows reviewer checkout, the current executable producer source hashes differ from the committed LF snapshots even though LF-normalized source content is identical. The earlier bounded Python/R reruns reproduced output bytes but did not reproduce identical producer-source bytes. The standard lineage check validates captured sources/recipes, not equality between captured and current tooling source. Its success must not be described as proving that latter equality under arbitrary Git settings.

Created a new owned ignored HTTPS clone with `git -c core.autocrlf=false clone --single-branch --no-local --branch launch/g0-library-20261020 https://github.com/esbraun/REMission.git contracts/artifacts/__pycache__/r1-review/lf-clone`, then persisted core.autocrlf=false in that clone. Verified exact d842037, clean status, HTTPS origin and no alternates. No author checkout, local overlay or source edit was used.

Mounted only this LF clone read-only and the own ignored artifact directory writable in qualified Python image sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7. The affected checks pass: current WCLS Python, offline R and historical PyMC Python source bytes exactly equal all three captured snapshots; the actual deterministic WCLS generator produces byte-identical CSV; all seven R1 manifests reconstruct identically. No expensive fits or broad checks reran.

Exact LF source SHA256 values:

- wcls_fixture.py / wcls-source.py: cc00293fec411b7ddccc74fb3fc8458d110c39de1c7056c6ac81e3faefd681ec
- probe-offline.R / offline-source.R: a601dc0cb0fcf4f4ffcc8b738a9c76551ba145923a6aac5758ce2ccfda94d49d
- probe-python.py / python-original-source.py: 09da9ccd0cf88197ce43cffccf6838400bff0e016b2bc190997dc57802eff5b3

Evidence: source-byte-inspection.json records current Windows source/snapshot/Git-byte comparisons; lf-source-result.json records qualified LF-clone checks; lf-wcls.csv is the independently generated payload. Payload/input hashes remain raw-byte exact throughout.

Reproduction instructions for an identical source identity should use an explicit LF checkout, execute the captured source bytes, or deliberately pin producer-source EOLs. A future canonical-source normalization scheme must label its hashes as normalized source identity rather than raw executed-byte identity, while retaining raw-byte artifact checksums. This is a bounded existing provenance/reproduction limitation, not a request to change the accepted DR estimator plan. No historical report or evidence was edited.
