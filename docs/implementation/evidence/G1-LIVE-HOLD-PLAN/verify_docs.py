"""Documentation-only provenance/link/preservation check; no runtime tests."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path.cwd()
BASE = "ec18cb4020ba239710a3fd615e365d5cd72b4d80"
DOC = "docs/implementation/g1-live-hold-executable-contract-proposal-20261021.md"
OUT = Path("docs/implementation/evidence/G1-LIVE-HOLD-PLAN")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


assert Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve() == ROOT.resolve()
assert git("merge-base", "HEAD", BASE).decode().strip() == BASE
assert git("branch", "--show-current").decode().strip() == "launch/g1-live-hold-plan-20261021"
paths = [
    "implementation-prompt.md", "docs/execution/engineering-guidelines.md",
    "docs/execution/delegation.md", "docs/spec/requirement-map.md",
    "docs/spec/00-scope-and-invariants.md", "docs/spec/06-service-and-ui.md",
    "docs/implementation/workflow-contract.md",
    "docs/implementation/g1-observed-representation-proposal-r1-20261021.md",
    "docs/implementation/g0-task-test-ledger-20261020.json",
    "services/foundation/app.py", "services/foundation/workflow.py",
    "services/foundation/replay.py", "services/foundation/archive.py",
    "services/foundation/store.py", "services/foundation/migrations/001_foundation.sql",
    "services/foundation/migrations/002_observed_archive.sql",
]
inventory = []
for name in paths:
    raw = git("show", f"{BASE}:{name}")
    blob = git("rev-parse", f"{BASE}:{name}").decode().strip()
    assert git("rev-parse", f"HEAD:{name}").decode().strip() == blob
    inventory.append(dict(path=name, base_git_blob=blob, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))

refs = ["7f70e3659e2062a2af3d4ce7f5bccfc30a67f713", "b03e3b54078778d2a7d063ea2cf9cd41e5ccf9a4",
        "bc0c81f2410fb1c42ba60b75cf38cd12d8322e78:docs/implementation/evidence/G1-OBS-REP/integrated/README.md"]
context = []
for ref in refs:
    raw = git("show", ref)
    context.append(dict(ref=ref, git_blob=git("rev-parse", ref).decode().strip(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))

links = re.findall(r"\]\(([^)]+)\)", Path(DOC).read_text(encoding="utf-8-sig"))
for link in links:
    if "://" not in link:
        assert (Path(DOC).parent / link.split("#")[0]).exists(), link

# Existing tracked bytes may not change anywhere outside the assigned docs scope.
allowed = [DOC, str(OUT).replace("\\", "/") + "/"]
changed = git("diff", "--name-only", BASE).decode().splitlines()
for path in changed:
    assert path == allowed[0] or path.startswith(allowed[1]), path
subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
result = dict(base=BASE, check="documentation-only", inspected_sources=inventory,
              accepted_context=context, relative_links_checked=len(links),
              existing_tracked_changes_outside_scope=[],
              ledger_git_bytes_unchanged=True, runtime_tests_executed=False,
              note="635 mappings are preserved by exact ledger byte identity; no ledger runtime checker or service tests run.")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "source-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(dict(status="passed", source_files=len(paths), relative_links=len(links), runtime_tests=False)))
