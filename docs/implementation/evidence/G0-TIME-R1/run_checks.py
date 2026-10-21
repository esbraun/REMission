"""Read-only by default; --record intentionally writes this package's evidence."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = "6c3fb070d36bfefbd070f2a2c33ccba7631734be"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    commands = [[sys.executable, "-m", "pip", "check"],
                [sys.executable, "-m", "contracts.domain.export", "--check"],
                [sys.executable, "-m", "unittest", "discover", "-s", "tests/contracts", "-v"],
                [sys.executable, "docs/implementation/check-ledger-20261020.py"],
                ["git", "diff", "--check", BASE]]
    results = []
    for command in commands:
        start = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        results.append({"command": command, "started_utc": start,
                        "finished_utc": datetime.now(timezone.utc).isoformat(),
                        "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        print("PASS" if result.returncode == 0 else "FAIL", " ".join(command[1:]))
    paths = subprocess.check_output(["git", "diff", "--name-only", BASE], cwd=ROOT, text=True).splitlines()
    paths.append("contracts/domain/temporal-v1.json")
    sources = {p: hashlib.sha256((ROOT/p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
               for p in sorted(set(paths)) if (ROOT/p).is_file() and not p.endswith("check-results.json")}
    evidence = {"task": "G0-TIME-R1", "base": BASE,
                "candidate": "Exact commit in independent review/handoff; no self-referential SHA",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "python": platform.python_version(), "platform": platform.platform(),
                "packages": subprocess.check_output([sys.executable, "-m", "pip", "freeze"], cwd=ROOT, text=True).splitlines(),
                "source_sha256_LF_normalized": sources, "checks": results,
                "claim_limits": ["Temporal schema/pure guard fixtures only; no generator, fit, pilot, statistical or clinical acceptance",
                                 "Independent exact-head/base acceptance required before DGP timing consumes v2",
                                 "Source hashes normalize CRLF to LF; offline artifact payload checksums remain exact bytes"]}
    if args.record:
        Path(__file__).with_name("check-results.json").write_text(json.dumps(evidence, indent=2)+"\n")
    if any(r["exit_code"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__": main()
