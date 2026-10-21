"""Read-only qualification checks against committed manifests and exchange files."""
import csv
import json
from importlib.metadata import distributions
from pathlib import Path

from contracts.artifacts.manifest import ArtifactManifest, NormalMixture, WCLSResult, validate_artifact
from tooling.library.lineage import build_manifests

root = Path("docs/implementation/evidence/G0-LIB/exchange")
for path in sorted(root.glob("*.manifest.json")):
    validate_artifact(root, ArtifactManifest.model_validate_json(path.read_bytes()))
for model, name in [(ArtifactManifest,"manifest"),(NormalMixture,"normal-mixture"),(WCLSResult,"wcls-result")]:
    assert json.loads(Path(f"contracts/artifacts/{name}.schema.json").read_text()) == model.model_json_schema()
expected = json.loads(Path("docs/implementation/evidence/G0-LIB/python-probes.json").read_text())["packages"]
actual = {p.metadata["Name"]:p.version for p in distributions()}
assert expected == actual, (expected,actual)
root = root.parent/"R1/exchange"
r=json.loads((root/"r-probes.json").read_text())
for name,value in build_manifests(root,expected,{p["package"]:p["version"] for p in r["packages"]}).items():
    assert value == ArtifactManifest.model_validate_json((root/(name+".manifest.json")).read_bytes())
print("PASS: exact runtime inventory; historical six manifests byte/shape only (original provenance claims superseded); seven R1 artifact-specific manifests and deterministic schemas")
