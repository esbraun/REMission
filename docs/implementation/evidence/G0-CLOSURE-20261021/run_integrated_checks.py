"""Capture the unchanged 14-command DR runner plus bounded closure checks.

Run with the qualified dependency-only contract interpreter. No --record is
passed to the historical runner; prior evidence is never rewritten. For a
frozen checkout, direct new output to an ignored own artifact directory.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import runpy
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
BASE = "fa3fca61b5b5c886064d2429d785b8de9e6fd146"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    checks = []
    actual_run = subprocess.run

    def capture(command, **kwargs):
        started = datetime.now(timezone.utc).isoformat()
        result = actual_run(command, **kwargs)
        checks.append(dict(command=command, started_utc=started,
                           finished_utc=datetime.now(timezone.utc).isoformat(),
                           exit_code=result.returncode,
                           stdout=result.stdout, stderr=result.stderr))
        return result

    historical = ROOT / "docs/implementation/evidence/G0-LIB/DR/run_checks.py"
    namespace = runpy.run_path(str(historical))
    entry = namespace["main"]
    # Observe the exact original commands/results without editing its source.
    entry.__globals__["subprocess"] = SimpleNamespace(run=capture)
    argv = sys.argv
    sys.argv = [str(historical)]
    runner_exit = 0
    try:
        entry()
    except SystemExit as error:
        runner_exit = error.code
    finally:
        sys.argv = argv
    assert len(checks) == 14, "historical qualifier command inventory changed"
    for command in [
        ["git", "diff", "--quiet", BASE, "--", "contracts", "methods", "tooling", "tests", "requirements-contracts.txt"],
        ["git", "diff", "--check", BASE],
        ["docker", "image", "inspect", "sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7", "--format", "{{.Id}}"],
    ]:
        result = capture(command, cwd=ROOT, capture_output=True, text=True)
        print("PASS" if result.returncode == 0 else "FAIL", " ".join(command))
    report = dict(package="G0-CLOSURE", accepted_base=BASE,
                  observed_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  observed_branch=subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
                  worktree=ROOT.as_posix(), interpreter=sys.executable,
                  python_version=platform.python_version(),
                  created_utc=datetime.now(timezone.utc).isoformat(),
                  historical_runner="G0-LIB/DR/run_checks.py unchanged; no --record",
                  historical_runner_exit=runner_exit, historical_command_count=14,
                  checks=checks,
                  limits=["Bounded integrated engineering qualification; independent combined review/root G0 acceptance pending",
                          "No unchanged expensive NUTS/R/BCF fits rerun; historical failures preserved",
                          "No G1 source, final statistical/consumer/application/human/clinical acceptance"])
    (output / "integrated-check-results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if runner_exit or any(item["exit_code"] for item in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
