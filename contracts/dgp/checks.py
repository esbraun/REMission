"""Reproduce bounded G0 checks; --record intentionally refreshes evidence only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from .parameters import VERSION, reference_parameters
from .scenarios import ROWS, scenario_manifest

ROOT = Path(__file__).resolve().parents[2]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    commands = [
        [sys.executable, "-m", "pip", "check"],
        [sys.executable, "-m", "contracts.dgp.export", "--check"],
        [sys.executable, "-m", "contracts.domain.export", "--check"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests/contracts", "-v"],
        [sys.executable, "docs/implementation/check-ledger-20261020.py"],
        ["git", "diff", "--check"],
        ["git", "diff", "--check", "6c3fb070d36bfefbd070f2a2c33ccba7631734be"],
    ]
    results = []
    for command in commands:
        start = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        results.append({"command": command, "exit_code": result.returncode,
                        "elapsed_seconds": time.perf_counter() - start,
                        "stdout": result.stdout, "stderr": result.stderr})
        print("PASS" if result.returncode == 0 else "FAIL", " ".join(command[1:]))
    if any(r["exit_code"] for r in results):
        raise SystemExit(1)
    if not args.record:
        return
    files = sorted([*ROOT.glob("contracts/dgp/*.py"), *ROOT.glob("contracts/dgp/*.json"),
                    *ROOT.glob("tests/contracts/test_dgp*.py"),
                    ROOT / "docs/implementation/dgp-decisions.md"])
    common = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "input_base": "6c3fb070d36bfefbd070f2a2c33ccba7631734be",
              "repair_input": "6195f9b745b672f087c9fdbd670497f80b7864ba",
              "owner_thread": os.environ.get("CODEX_THREAD_ID"),
              "source_commit": "Candidate commit containing evidence; exact SHA in independent review/root handoff",
              "requested_model": "gpt-6.1-sol", "requested_effort": "high",
              "effective_model_introspection": "unavailable; assignment configuration only",
              "helpers": [], "python": platform.python_version(), "platform": platform.platform(),
              "packages": subprocess.check_output([sys.executable, "-m", "pip", "freeze"], cwd=ROOT, text=True).splitlines(),
              "source_sha256_normalized_LF": {str(p.relative_to(ROOT)).replace("\\", "/"): file_hash(p) for p in files},
              "acceptance": "pending_independent_Astra_exact_head_base_review",
              "human_factors": "not_started_deferred", "clinical_review": "not_started_deferred",
              "clinical_validation": "not_started_separate_future_project"}
    dgp = common | {"task": "G0-DGP", "artifact_version": VERSION, "kind": "contract_and_analytic_fixture_checks_only",
                    "parameter_count": len(reference_parameters()["parameters"]), "variant_count": len(ROWS),
                    "cell_count": len(scenario_manifest()["cells"]), "checks": results,
                    "not_executed": ["longitudinal generator", "independent Layer B rollout", "achieved-rate/external calibration",
                                     "source SE pilot", "distribution inspection", "paired-trajectory null equality",
                                     "evaluator process/storage denial", "scenario statistical/policy runs", "human/clinical reviews"]}
    path = ROOT / "docs/implementation/evidence/G0-DGP/R1/check-results-20261021.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dgp, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
