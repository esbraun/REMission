"""Capture reproducible G0 contract checks; never invokes a simulator or fit."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true", help="intentionally refresh saved evidence; omit for read-only review")
    args = parser.parse_args()
    checks = [
        [sys.executable, "-m", "pip", "check"],
        [sys.executable, "-m", "contracts.domain.export", "--check"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests/contracts", "-v"],
        [sys.executable, "docs/implementation/check-ledger-20261020.py"],
    ]
    results = []
    for command in checks:
        started = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        results.append({"command": command, "exit_code": result.returncode,
                        "seconds": time.perf_counter() - started,
                        "stdout": result.stdout, "stderr": result.stderr})
        print("PASS" if result.returncode == 0 else "FAIL", " ".join(command[1:]))
    sources = sorted([*ROOT.glob("contracts/domain/**/*.py"), *ROOT.glob("contracts/domain/**/*.json"),
                      *ROOT.glob("tests/contracts/**/*.py"), *ROOT.glob("tests/contracts/fixtures/*.json"),
                      ROOT / "requirements-contracts.txt",
                      ROOT / "docs/implementation/check-ledger-20261020.py",
                      ROOT / "docs/implementation/g0-task-test-ledger-20261020.json"])
    evidence = {"task": "G0-CONTRACT", "kind": "contract_fixtures_not_empirical_validation",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "input_base": "e7965b998fa70df82e63a89ef720a6c8ad46ce6d",
                "source_commit": "Candidate commit containing this manifest; exact SHA supplied in independent review/handoff",
                "python": platform.python_version(), "platform": platform.platform(),
                "packages": subprocess.check_output([sys.executable, "-m", "pip", "freeze"], cwd=ROOT, text=True).splitlines(),
                "sources_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in sources},
                "checks": results,
                "limitations": ["No application/service/storage, empirical fitting/simulation, package-method qualification or human session",
                                "All source hashes normalize checkout CRLF to LF; artifact import checksum conventions remain G0-LIB"]}
    if args.record:
        path = ROOT / "docs/implementation/evidence/G0-CONTRACT/check-results-20261020.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if any(r["exit_code"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
