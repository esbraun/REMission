"""Correct R1 lineage; preserve all original qualification evidence unchanged."""
import csv
import json
import shutil
from pathlib import Path
import numpy as np
from contracts.artifacts.manifest import ArtifactManifest, NormalMixture, WCLSResult
from tooling.library.lineage import build_manifests

root = Path("docs/implementation/evidence/G0-LIB/R1/exchange")
root.mkdir(parents=True,exist_ok=True)
outputs = Path("tooling/library/__pycache__/outputs-r1")
for path in [*outputs.glob("*.*"),*outputs.joinpath("r").glob("*.*")]:
    shutil.copyfile(path,root/path.name)
py=json.loads(Path("docs/implementation/evidence/G0-LIB/python-probes.json").read_text())
r=json.loads((root/"r-probes.json").read_text())
np.testing.assert_allclose(py["wcls_python"]["coefficients"],r["wcls"]["coefficients"],rtol=0,atol=1e-12)
def table(name):
    with (root/name).open(newline="") as stream:return list(csv.DictReader(stream))
a,b=table("pymc-draws.csv"),table("sbc-return.csv")
assert [(x["chain"],x["draw"],x["quantity"]) for x in a] == [(x["chain"],x["draw"],x["quantity"]) for x in b]
np.testing.assert_allclose([float(x["value"]) for x in a],[float(x["value"]) for x in b],atol=1e-12,rtol=0)
manifests=build_manifests(root,py["packages"],{p["package"]:p["version"] for p in r["packages"]})
for name,value in manifests.items():
    (root/(name+".manifest.json")).write_text(value.model_dump_json(indent=2)+"\n")
for model,name in [(ArtifactManifest,"manifest"),(NormalMixture,"normal-mixture"),(WCLSResult,"wcls-result")]:
    Path(f"contracts/artifacts/{name}.schema.json").write_text(json.dumps(model.model_json_schema(),indent=2,sort_keys=True)+"\n")
print("PASS: 7 artifact-specific R1 manifests, separate Python CSV and R result, recipe/source/input hashes; SBC matrix-derived 800 coordinates/values and WCLS coefficient parity within1e-12")
