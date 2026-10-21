"""Reproduce planning preservation/dependency checks; this runs no app or fits."""
import json
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
    # G0 contract implementation is now active; this package cannot accept a gate.
    assert data["gate_status"]["G0"] == "running"
    assert all(state == "not-started" for gate, state in data["gate_status"].items() if gate != "G0")
    prior = data["repair_assignment"]
    assert prior["review_disposition"] == "ready_to_ship"
    assert prior["reviewed_head"] == "3af3553cb6aec3a762ce883d968bec621244409b"
    assert prior["reviewed_base"] == REVIEW_BASE
    merge = PUBLISHED_MERGE
    assert git("show", "-s", "--format=%P", merge).split() == [REVIEW_BASE, prior["reviewed_head"]]
    report = "docs/implementation/evidence/G0-LAUNCH-FIX-01/independent-review-20261020.md"
    assert git("hash-object", "--path", report, report).strip() == "c7036122a5db0f40cbc3ea962741a306c7ecead7"
    current = data["current_assignment"]
    assert current["id"] == "G0-CONTRACT" and current["base_commit"] == merge
    prior_contract = current["prior_reviews"][0]
    assert prior_contract["reviewed_head"] == "939dd29254bc4a6f2c4f6c92330bd1c3fc11c9d4"
    assert prior_contract["reviewed_base"] == merge and prior_contract["disposition"] == "changes_requested"
    assert git("hash-object", "--path", prior_contract["path"], prior_contract["path"]).strip() == "9b81514185ab38ed7550b8c3719cb30e85b7edc9"
    print("PASS: JSON; 635 unique rows/stable test IDs; exact original category sets; canonical 483 LEG/51 named/32 scenarios/14 UX sets; all paths/references; bidirectional mappings; acyclic feasible pilot ordering; final checks/release dependencies preserved; LIB-03/VAL-01 ownership; Git-identical raw review blobs; exact target base/tree ancestry; gates unaccepted.")


if __name__ == "__main__":
    main()
