"""Reproduce planning preservation/dependency checks; this runs no app or fits."""
import json
import hashlib
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "50403963d11cc51e6109a635f9a2b6b1031b8cf4"
# Identical original planning blob imported by this reachable, published commit.
# The author commit c239dca is historical provenance, not a clone prerequisite.
ORIGINAL = "f986495522fad161adc80222bcad23d41a03e9f3"
REVIEW_BASE = "c7cdf4a8415073d0b275064a0b0aca188fc022fe"
PUBLISHED_MERGE = "e7965b998fa70df82e63a89ef720a6c8ad46ce6d"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def unique(values):
    assert len(values) == len(set(values)), "duplicate ID"


def main():
    ledger_path = "docs/implementation/g0-task-test-ledger-20261020.json"
    data = json.loads(read(ledger_path))
    original = json.loads(git("show", f"{ORIGINAL}:{ledger_path}"))
    assert git("rev-parse", f"{ORIGINAL}:{ledger_path}").strip() == "ed6985be48731e1b88fda569fed27f5a1047a371"
    subprocess.check_call(["git", "merge-base", "--is-ancestor", ORIGINAL, PUBLISHED_MERGE], cwd=ROOT)
    rows = data["coverage"]
    unique([r["requirement_id"] for r in rows])
    unique([test for r in rows for test in r["test_ids"]])
    assert len(rows) == 635
    assert dict(Counter(r["kind"] for r in rows)) == data["coverage_counts"]
    kinds = set(r["kind"] for r in rows)
    for kind in kinds:
        before = {r["requirement_id"]: r["test_ids"] for r in original["coverage"] if r["kind"] == kind}
        after = {r["requirement_id"]: r["test_ids"] for r in rows if r["kind"] == kind}
        assert before == after, f"original {kind} set/stable test IDs changed"

    def category(kind):
        return {r["requirement_id"] for r in rows if r["kind"] == kind}

    canonical_legacy = set()
    for path in (ROOT / "docs/spec/traceability").glob("g[0-7].md"):
        canonical_legacy.update(re.findall(r"^\| (LEG-\d{2}-\d{3}) \|", path.read_text(encoding="utf-8"), re.M))
    assert len(canonical_legacy) == 483
    assert category("legacy_atomic") == canonical_legacy
    named = set()
    named_tables = read("docs/spec/requirement-map.md")
    for line in named_tables.splitlines():
        if line.startswith("| "):
            for identifier in line.split("|")[1].strip().split(", "):
                if re.fullmatch(r"[A-Z]+(?:-[A-Z0-9]+)+", identifier) and not identifier.startswith("LEG-"):
                    named.add(identifier)
    assert len(named) == 51
    assert category("named_requirement") == named
    scenarios = set(re.findall(r"^\| (S\d{2}) \|", read("docs/spec/scenario-catalog.md"), re.M))
    assert len(scenarios) == 32 and category("scenario_family") == scenarios
    ux = set(re.findall(r"UX-T\d{2}", read("docs/plans/ux/06-validation-and-integration.md")))
    assert len(ux) == 14 and category("ux_test") == ux

    tasks = {t["id"]: t for t in data["tasks"]}
    assert len(tasks) == len(data["tasks"])
    unique([test for t in tasks.values() for test in t["test_ids"]])
    by_id = {r["requirement_id"]: r for r in rows}
    for row in rows:
        unique(row["task_ids"])
        assert row["task_ids"]
        for task_id in row["task_ids"]:
            assert task_id in tasks
            assert row["requirement_id"] in tasks[task_id]["requirement_ids"]
        docs = row["canonical_doc"]
        for doc in [docs] if isinstance(docs, str) else docs:
            assert (ROOT / doc).is_file(), doc
    for task in tasks.values():
        unique(task["requirement_ids"])
        for requirement in task["requirement_ids"]:
            assert requirement in by_id
            assert task["id"] in by_id[requirement]["task_ids"]
        for doc in task["canonical_docs"]:
            assert (ROOT / doc).is_file(), doc
        unique(task["depends_on"])
        assert all(dep in tasks for dep in task["depends_on"])

    ancestors = {}
    visiting = set()

    def visit(task_id):
        assert task_id not in visiting, f"cycle at {task_id}"
        if task_id not in ancestors:
            visiting.add(task_id)
            result = set(tasks[task_id]["depends_on"])
            for dependency in tasks[task_id]["depends_on"]:
                result.update(visit(dependency))
            ancestors[task_id] = result
            visiting.remove(task_id)
        return ancestors[task_id]

    for task_id in tasks:
        visit(task_id)
    assert set(tasks["G2-PILOT"]["depends_on"]) == {"G2-BAYES-IMPL", "G2-BORROW-IMPL"}
    assert not ({"G2-BAYES", "G2-BORROW", "G2-PILOT"} & ancestors["G2-BAYES-IMPL"])
    assert not ({"G2-BAYES", "G2-BORROW", "G2-PILOT"} & ancestors["G2-BORROW-IMPL"])
    finals = {"G2-BAYES", "G2-BORROW", "G3-N1", "G3-SMART", "G4-MRT", "G4-POLICY"}
    for task_id in finals:
        assert "G2-PILOT" in tasks[task_id]["depends_on"]
        assert task_id in ancestors["G7-REPRO"], f"release bypasses {task_id}"
        before = next(t for t in original["tasks"] if t["id"] == task_id)
        assert all(item in tasks[task_id]["acceptance"] for item in before["acceptance"])
    assert "VAL-01" in tasks["G2-PILOT"]["requirement_ids"]
    assert {"docs/spec/07-validation-protocol.md", "docs/plans/methods/03-validation-and-benchmarks.md"} <= set(tasks["G2-PILOT"]["canonical_docs"])
    assert set(by_id["LIB-03"]["task_ids"]) == {"G0-LIB", "G2-BAYES-IMPL", "G2-BORROW-IMPL", "G2-BAYES", "G2-BORROW", "G5-SERVICE"}
    for report in ["ready-review-01.md", "g0-critique-20261020.md"]:
        path = "docs/implementation/reviews/" + report
        # Compare Git-cleaned blobs: Windows checkout may expand LF to CRLF.
        expected = {"ready-review-01.md": "aa8df5b95e3a5c44fc10dc4b2d1a1365775e3a0d",
                    "g0-critique-20261020.md": "f727e620ad38c9c66d7b51d344745c4185323ca0"}[report]
        assert git("rev-parse", f"{PUBLISHED_MERGE}:{path}").strip() == expected
        assert git("hash-object", "--path", path, path).strip() == expected, "raw review changed"
    assert data["accepted_specification_base"] == BASE
    assert data["repair_assignment"]["review_target_base"] == REVIEW_BASE
    assert data["task_defaults"]["integration_target"] == "main"
    assert git("rev-parse", BASE + "^{tree}") == git("rev-parse", REVIEW_BASE + "^{tree}")
    subprocess.check_call(["git", "merge-base", "--is-ancestor", BASE, REVIEW_BASE], cwd=ROOT)
    # Exact combined closure record governs the current review checkpoint.
    # Package qualification cannot accept the combined gate by itself.
    closure = data["g0_closure"]
    assert closure["status"] == "accepted_contract_library_qualification"
    assert closure["gate_status"] == data["gate_status"]["G0"] == "accepted"
    assert closure["independent_combined_review"] == "ready_to_ship" and closure["root_gate_acceptance"] == "accepted"
    assert data["gate_status"]["G1"] == "running"
    assert all(state == "not-started" for gate, state in data["gate_status"].items() if gate not in ("G0", "G1"))
    prior = data["repair_assignment"]
    assert prior["review_disposition"] == "ready_to_ship"
    assert prior["reviewed_head"] == "3af3553cb6aec3a762ce883d968bec621244409b"
    assert prior["reviewed_base"] == REVIEW_BASE
    merge = PUBLISHED_MERGE
    assert git("show", "-s", "--format=%P", merge).split() == [REVIEW_BASE, prior["reviewed_head"]]
    report = "docs/implementation/evidence/G0-LAUNCH-FIX-01/independent-review-20261020.md"
    assert git("hash-object", "--path", report, report).strip() == "c7036122a5db0f40cbc3ea962741a306c7ecead7"
    accepted = data["accepted_contract_assignment"]
    assert accepted["status"] == "accepted" and accepted["base_commit"] == merge
    accepted_head = "abd511c5870d41269980f4554be89407b31749d6"
    accepted_merge = "6c3fb070d36bfefbd070f2a2c33ccba7631734be"
    assert git("show", "-s", "--format=%P", accepted_merge).split() == [merge, accepted_head]
    assert accepted["reviewed_head"] == accepted_head and accepted["merge_commit"] == accepted_merge
    accepted_report = accepted["accepted_review"]["path"]
    assert git("hash-object", "--path", accepted_report, accepted_report).strip() == "78c63b418994faac455ccecf25020c6fb63c88e1"
    temporal = data["accepted_temporal_assignment"]
    main_base = "b24c3c0fb78bf19928750eae29e852141bd649a7"
    assert temporal["status"] == "accepted" and temporal["review_disposition"] == "ready_to_ship"
    assert temporal["reviewed_head"] == "62e6ce85299b477b0c21a18d70b49392a68e1522" and temporal["reviewed_base"] == accepted_merge
    assert git("show", "-s", "--format=%P", main_base).split() == [accepted_merge, temporal["reviewed_head"]]
    temporal_report = temporal["accepted_review"]["path"]
    assert git("hash-object", "--path", temporal_report, temporal_report).strip() == "80f39d8512ef631249374a1378a80aeda2f74561"
    current = data["accepted_library_assignment"]
    assert current["id"] == "G0-LIB" and current["package_id"] == "G0-LIB-DR"
    dgp_merge = "f11e90536b635a7db08cfed640445bec197a415c"
    assert git("show", "-s", "--format=%P", dgp_merge).split() == [main_base, "985ce540f0cc6ae1e57a6268651971acb546929d"]
    for task_id in ["G0-DGP", "G0-WORKFLOW"]:
        package = data["accepted_dgp_workflow_assignment"][task_id]
        assert package["status"] == "accepted_contract_scope_only" and package["review_disposition"] == "ready_to_ship"
        assert package["merge_commit"] == dgp_merge and package["reviewed_base"] == main_base
        package_report = package["accepted_review"]["path"]
        assert git("hash-object", "--path", package_report, package_report).strip() == "78e75133364b6babc2d3ce75d10f76b22e40105e"
    assert current["base_commit"] == current["review_target_base"] == dgp_merge
    lib_head = "142f61217c850b132c3fcd21f59a5657fd9bbcfa"
    lib_merge = "fa3fca61b5b5c886064d2429d785b8de9e6fd146"
    assert current["status"] == "accepted_library_qualification_scope_only"
    assert current["review_disposition"] == "ready_to_ship"
    assert current["reviewed_head"] == current["candidate_commit"] == lib_head
    assert current["reviewed_base"] == dgp_merge and current["merge_commit"] == lib_merge
    assert current["pr_url"] == "https://github.com/esbraun/REMission/pull/14"
    assert git("show", "-s", "--format=%P", lib_merge).split() == [dgp_merge, lib_head]
    lib_review = current["accepted_review"]
    for key, expected in [("path", "72eef90709ba4aba9de4097f0ec6d778472c8cc5"),
                          ("evidence_manifest_path", "376fec50de6dda096c20b85ff570b56dec6444de")]:
        assert git("hash-object", "--no-filters", lib_review[key]).strip() == expected
    assert lib_review["disposition"] == "ready_to_ship"
    assert "not G0 overall" in read(lib_review["path"])
    assignment = data["current_assignment"]
    foundation_base = "8ca67682505d78accc855e92cbfbb6692edf8316"
    closure_head = "236ebfb84952a63c58a4cc885d17a9754e93051b"
    assert closure["reviewed_head"] == closure_head and closure["reviewed_base"] == closure["base_commit"] == lib_merge
    assert closure["merge_commit"] == foundation_base and closure["pr_url"] == "https://github.com/esbraun/REMission/pull/15"
    assert git("show", "-s", "--format=%P", foundation_base).split() == [lib_merge, closure_head]
    closure_report = closure["accepted_review"]["path"]
    assert git("hash-object", "--no-filters", closure_report).strip() == "51cf9d0c2692bbf5ed18ac269cc00e8893fd047f"
    foundation = data["accepted_foundation_assignment"]
    foundation_head = "3179f3d2fcc7c9f285129b0272e868d413ced089"
    generator_base = "69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e"
    assert foundation["status"] == "accepted_engineering_scope_only" and foundation["review_disposition"] == "ready_to_ship"
    assert foundation["reviewed_head"] == foundation["candidate_commit"] == foundation_head
    assert foundation["reviewed_base"] == foundation["base_commit"] == foundation_base
    assert foundation["merge_commit"] == generator_base and foundation["pr_url"] == "https://github.com/esbraun/REMission/pull/16"
    assert git("show", "-s", "--format=%P", generator_base).split() == [foundation_base, foundation_head]
    assert git("hash-object", "--no-filters", foundation["accepted_review"]["path"]).strip() == "fbbf95f62dd5d2a2d016caabcd5c22f58bf94268"
    assert git("hash-object", "--no-filters", foundation["accepted_review"]["evidence_manifest_path"]).strip() == "369c9fc71a32117c161dbf4423e4bac193d45a84"
    assert assignment["id"] == "G1-GENERATOR" and assignment["package_id"] == "G1-GENERATOR-INTERFACES" and assignment["status"] == "needs_review"
    assert assignment["base_commit"] == assignment["review_target_base"] == generator_base
    assert tasks["G1-FOUNDATION"]["status"] == foundation["status"] and tasks["G1-GENERATOR"]["status"] == "running"
    merged = json.loads(git("show", f"{generator_base}:{ledger_path}"))
    assert data["coverage"] == merged["coverage"] and data["coverage_counts"] == merged["coverage_counts"]
    for task in data["tasks"]:
        before = next(t for t in merged["tasks"] if t["id"] == task["id"])
        assert all(task[key] == before[key] for key in ("id", "depends_on", "test_ids", "requirement_ids"))
    probability = data["accepted_probability_plan"]
    assert probability["status"] == "root_accepted_plan_only" and probability["root_accepted"] is True
    assert (probability["contract_id"], probability["contract_version"]) == ("ESTINT-PRECISION-01", "1.0.0-r1")
    assert probability["reviewed_head"] == "99fbcc31267284481fe8e4820530635eaecc7ce5" and probability["reviewed_base"] == generator_base
    for record in [probability, probability["accepted_critique"], probability["original_proposal"], probability["original_critique"]]:
        assert git("hash-object", "--no-filters", record["path"]).strip() == record["blob"]
    assert probability["accepted_critique"]["disposition"] == "ready_to_proceed"
    rejected = assignment["prior_reviews"][0]
    assert rejected["reviewed_head"] == "2a7726be23864cf9c933295f1d33da3d6fbedd1b" and rejected["reviewed_base"] == generator_base
    assert rejected["disposition"] == "changes_requested"
    assert git("hash-object", "--no-filters", rejected["path"]).strip() == "bb708c7e9bffea3ff997fd0eafba05303b6f94fd"
    assert git("hash-object", "--no-filters", rejected["evidence_manifest_path"]).strip() == "a732313d5a0b1957ca5c724691728db3d709a489"
    interpretation = probability["iid_admission_interpretation"]
    assert interpretation["status"] == "root_accepted_conservative_engineering_interpretation"
    assert git("hash-object", "--no-filters", interpretation["path"]).strip() == "aede75810ca4ff2178b5f4126d0f80f050366618"
    assert closure["required_packages"] == ["G0-PLAN", "G0-CONTRACT", "G0-TIME-R1", "G0-DGP", "G0-WORKFLOW", "G0-LIB"]
    assert closure["accepted_merge_chain"] == [PUBLISHED_MERGE, accepted_merge, main_base, dgp_merge, lib_merge]
    subprocess.check_call(["git", "merge-base", "--is-ancestor", lib_merge, "HEAD"], cwd=ROOT)
    plan = current["accepted_plan"]
    assert plan["disposition"] == "ready_to_proceed" and plan["root_accepted"] is True
    assert plan["reviewed_head"] == "d84203709b0164a0824913950c1d7cd7be25a2fb" and plan["reviewed_base"] == dgp_merge
    assert git("hash-object", "--path", plan["path"], plan["path"]).strip() == "bd9eb376680c7225cfdad3c0ac162d1698326063"
    assert tasks["G0-LIB"]["status"] == current["status"] and tasks["G0-LIB"]["shipping_review"] == "ready_to_ship"
    assert all(row["status"] == "planned" for row in rows), "package review cannot close shared requirement rows"
    assert data["claim_status"] == {"synthetic-engineering": "running", "human-factors": "not-started", "clinical-review": "not-started", "clinical-validation": "not-started"}
    current_evidence = {item["task_id"]: item for item in data["execution_evidence"] if item.get("record_kind") == "current_accepted_package"}
    assert set(current_evidence) == {"G0-TIME-R1", "G0-DGP", "G0-WORKFLOW", "G0-LIB", "G1-FOUNDATION"}
    for item in current_evidence.values():
        assert item["review_disposition"] == "ready_to_ship" and (ROOT / item["evidence"]).is_file()
    workflow = read("docs/implementation/workflow-contract.md")
    assert set(re.findall(r"^\| (ASSIGN-\d{2}) ", workflow, re.M)) == {f"ASSIGN-{i:02d}" for i in range(1, 11)}
    g1 = data["accepted_g1_plan"]
    assert g1["status"] == "root_accepted_plan_only"
    assert g1["reviewed_head"] == "690b538f45a54dd4707e02e7e68e1c63bbea0884" and g1["reviewed_base"] == dgp_merge
    # Original planning commits are provenance, not fresh-clone prerequisites.
    assert git("hash-object", "--path", g1["path"], g1["path"]).strip() == "5d46eb071485a9d5f2ed0473880a75fcab181556"
    for key, blob in [("first_critique", "0d261661bc426dc037a5d93cec7f04736f47558c"),
                      ("accepted_critique", "a0addffb138bc991f1f54a6676ae59ca5dde538d")]:
        assert git("hash-object", "--no-filters", g1[key]["path"]).strip() == blob
    for name, blob in [("independent-source-byte-follow-up.md", "df3ed8b9375d7a1ad4acd0e5fda1c424d0be678e"),
                       ("byte-inspection.json", "93a8d185b34f94f742886aa9c5e9bc38e676654e"),
                       ("lf-reproduction.json", "6e694cd446277b5dadbf176dfed118221ab7989d")]:
        report_path = "docs/implementation/evidence/G0-LIB/DR/portability/" + name
        assert git("hash-object", "--path", report_path, report_path).strip() == blob
    for review in current["prior_reviews"]:
        assert git("hash-object", "--path", review["path"], review["path"]).strip() == review["blob"]
    assert tasks["G0-TIME-R1"]["depends_on"] == ["G0-CONTRACT"]
    assert "G0-TIME-R1" in tasks["G0-DGP"]["depends_on"]
    assert "G0-TIME-R1" in ancestors["G7-REPRO"]
    v1 = "contracts/domain/temporal-v1.json"
    assert git("hash-object", "--path", v1, v1).strip() == git("rev-parse", f"{accepted_merge}:{v1}").strip() == "2a197d76b938dbda3279a26a6645cada78a89508"
    version = json.loads(read("docs/implementation/evidence/G0-TIME-R1/consumer-version.json"))
    assert version["id"] == "TIME-01" and version["version"] == "2.0.0" and version["schema_version"] == "1.0.0"
    normalized = (ROOT / version["path"]).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == version["sha256"] == tasks["G0-TIME-R1"]["consumer_version"]["sha256"]
    for name, blob in [("dgp-review-changes-requested.md", "94b100b39558fce4c6c17f9f79a6acad0c159b04"),
                       ("ope-plan-review-changes-requested.md", "052677a20145fb14f5e1d2f509592a4de4942ef4")]:
        report_path = "docs/implementation/evidence/G0-TIME-R1/" + name
        assert git("hash-object", "--path", report_path, report_path).strip() == blob
    prior_contract = accepted["prior_reviews"][0]
    assert prior_contract["reviewed_head"] == "939dd29254bc4a6f2c4f6c92330bd1c3fc11c9d4"
    assert prior_contract["reviewed_base"] == merge and prior_contract["disposition"] == "changes_requested"
    assert git("hash-object", "--path", prior_contract["path"], prior_contract["path"]).strip() == "9b81514185ab38ed7550b8c3719cb30e85b7edc9"
    print("PASS: JSON; 635 unique rows/stable test IDs; exact original category sets; canonical 483 LEG/51 named/32 scenarios/14 UX sets; all paths/references; bidirectional mappings; acyclic feasible pilot ordering; final checks/release dependencies preserved; LIB-03/VAL-01 ownership; Git-identical raw review blobs; exact target base/tree ancestry; G0 accepted in contract/library scope; G1 running and later gates unaccepted.")


if __name__ == "__main__":
    main()
