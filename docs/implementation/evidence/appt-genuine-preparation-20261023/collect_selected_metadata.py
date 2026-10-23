"""APPT-GENUINE-POSITIVE readiness: metadata only; no exec, mounts or Env."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
PREFIX = "remission-poc13-ac8e16e0"
BASE = "41056f0c06a2afa1141c33eeb3a934a1969d19bb"
FORMAT = '{"Id":{{json .Id}},"Name":{{json .Name}},"Image":{{json .Image}},"State":{{json .State}},"User":{{json .Config.User}},"WorkingDir":{{json .Config.WorkingDir}},"Cmd":{{json .Config.Cmd}},"Entrypoint":{{json .Config.Entrypoint}},"Mounts":{{json .Mounts}},"Networks":{{json .NetworkSettings.Networks}},"Ports":{{json .NetworkSettings.Ports}},"Memory":{{json .HostConfig.Memory}},"NanoCpus":{{json .HostConfig.NanoCpus}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"CapDrop":{{json .HostConfig.CapDrop}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"Tmpfs":{{json .HostConfig.Tmpfs}},"RestartPolicy":{{json .HostConfig.RestartPolicy}}}'


def run(argv):
    started = time.monotonic()
    result = subprocess.run(argv, capture_output=True, text=True, timeout=20, check=False)
    record = {"argv": argv, "exit_code": result.returncode,
              "elapsed_seconds": time.monotonic() - started,
              "stdout": result.stdout, "stderr": result.stderr}
    commands.append(record)
    if result.returncode:
        return None
    return result.stdout


commands = []
assert Path.cwd().resolve() == ROOT.parents[3]
assert run(["git", "rev-parse", "HEAD"]).strip() == BASE
containers = {}
for suffix in ["service", "service-pre-pa3-4a", "generator", "analysis-4ff86193058d4d13a1600f0423e91f12"]:
    name = PREFIX + "-" + suffix
    value = run(["docker", "inspect", name, "--format", FORMAT])
    containers[name] = json.loads(value) if value else None
volumes = {}
for suffix in ["database", "exports", "fixtures", "analysis-4ff86193058d4d13a1600f0423e91f12-input", "analysis-4ff86193058d4d13a1600f0423e91f12-output"]:
    name = PREFIX + "-" + suffix
    value = run(["docker", "volume", "inspect", name, "--format", '{"Name":{{json .Name}},"Driver":{{json .Driver}},"Scope":{{json .Scope}},"CreatedAt":{{json .CreatedAt}}}'])
    volumes[name] = json.loads(value) if value else None
inventory = {}
for key, filters in [
    ("original_database_consumers", ["--filter", "volume=" + PREFIX + "-database"]),
    ("owned_analysis_workers", ["--filter", "label=remission.analysis=" + PREFIX]),
    ("original_stack", ["--filter", "name=^/" + PREFIX + "-"]),
]:
    inventory[key] = run(["docker", "ps", "-a", *filters, "--format", '{"ID":{{json .ID}},"Names":{{json .Names}},"Image":{{json .Image}},"State":{{json .State}},"Status":{{json .Status}},"Ports":{{json .Ports}}}'])
out = {"task_id": "APPT-GENUINE-POSITIVE", "observed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "base": BASE, "worktree": str(Path.cwd()), "branch": run(["git", "branch", "--show-current"]).strip(),
       "host": {"python": sys.version, "platform": platform.platform()},
       "scope": "Selected Docker metadata and host stdlib only; no Config.Env, container exec, payload, volume mount or lifecycle operation.",
       "containers": containers, "volumes": volumes, "inventory": inventory, "commands": commands}
destination = ROOT / "selected-current-metadata.json"
assert not destination.exists()
destination.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                  "current_service_image": containers[PREFIX + "-service"]["Image"],
                  "current_service_running": containers[PREFIX + "-service"]["State"]["Running"],
                  "original_database_volume_present": volumes[PREFIX + "-database"] is not None}, sort_keys=True))
