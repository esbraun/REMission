"""Bind the existing accepted service image to current committed source only."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
BASE = "41056f0c06a2afa1141c33eeb3a934a1969d19bb"
IMAGE = "sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72"
assert Path.cwd().resolve() == ROOT.parents[3]
closure_path = Path("docs/implementation/evidence/cloud-first-deploy-20261023/ops/source-closure-qualification.json")
closure = json.loads(closure_path.read_bytes())["fixture"]
assert closure["image"] == IMAGE
files = []
for entry in closure["files"]:
    blob = subprocess.check_output(["git", "show", BASE + ":" + entry["path"]])
    current = hashlib.sha256(blob).hexdigest()
    assert current == entry["git_blob_bytes"] == entry["expected"], entry["path"]
    files.append({"path": entry["path"], "current_git_sha256": current})
argv = ["docker", "image", "inspect", IMAGE, "--format", '{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"Created":{{json .Created}},"User":{{json .Config.User}},"WorkingDir":{{json .Config.WorkingDir}},"Cmd":{{json .Config.Cmd}},"Entrypoint":{{json (index .Config "Entrypoint")}},"RepoDigests":{{json .RepoDigests}}}']
process = subprocess.run(argv, capture_output=True, text=True, timeout=20)
assert process.returncode == 0, process.stderr
image = json.loads(process.stdout)
assert image["Id"] == IMAGE and image["Os"] == "linux" and image["Architecture"] == "amd64"
assert image["User"] == "10001:10001" and image["WorkingDir"] == "/app"
out = {"task_id": "APPT-GENUINE-POSITIVE", "observed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "base": BASE, "image": image, "inspection": {"argv": argv, "exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr},
       "source_closure_reference": str(closure_path).replace("\\", "/"), "source_closure_reference_sha256": hashlib.sha256(closure_path.read_bytes()).hexdigest(),
       "current_committed_source_matches_accepted_image_closure": True, "file_count": len(files), "files": files,
       "limitations": ["No image container was launched or copied here; actual-image byte qualification is reused from the accepted committed closure receipts.",
                       "Earlier selected-image inspect in this session failed because .Config.Entrypoint is absent; original tool output retained in conversation. Corrected lookup uses index and returns null. No resource mutation/retry of a runtime occurred."]}
destination = ROOT / "existing-current-image-binding.json"
assert not destination.exists()
destination.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "files": len(files), "image": image["Id"]}))
