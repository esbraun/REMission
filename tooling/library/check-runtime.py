"""Read-only qualification checks against committed manifests and exchange files."""
import csv
import json
from importlib.metadata import distributions
from pathlib import Path

from contracts.artifacts.manifest import ArtifactManifest, NormalMixture, validate_artifact

root = Path("docs/implementation/evidence/G0-LIB/exchange")
for path in sorted(root.glob("*.manifest.json")):
    validate_artifact(root, ArtifactManifest.model_validate_json(path.read_bytes()))
for model, name in [(ArtifactManifest,"manifest"),(NormalMixture,"normal-mixture")]:
    assert json.loads(Path(f"contracts/artifacts/{name}.schema.json").read_text()) == model.model_json_schema()
expected = json.loads(Path("docs/implementation/evidence/G0-LIB/python-probes.json").read_text())["packages"]
actual = {p.metadata["Name"]:p.version for p in distributions()}
assert expected == actual, (expected,actual)
print("PASS: exact locked runtime package inventory, six committed real exchange manifests, deterministic artifact JSON Schemas")
