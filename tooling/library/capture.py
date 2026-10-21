"""Capture an actual command's merged output and exit code; propagate failures."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

name, *command = sys.argv[1:]
root = Path(__file__).resolve().parents[2]
start = datetime.now(timezone.utc).isoformat()
result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
directory = root / "docs/implementation/evidence/G0-LIB"
(directory / (name + ".log")).write_bytes(result.stdout)
(directory / (name + ".command.json")).write_text(json.dumps({
    "started_utc": start, "finished_utc": datetime.now(timezone.utc).isoformat(),
    "cwd": str(root), "command": command, "exit_code": result.returncode}, indent=2)+"\n")
print(result.stdout.decode(errors="replace"))
sys.exit(result.returncode)
