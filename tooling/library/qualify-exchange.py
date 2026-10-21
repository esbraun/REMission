"""Validate actual offline files and preserve small reproducible exchange evidence."""
import csv
import json
import shutil
from pathlib import Path
import numpy as np
from contracts.artifacts.manifest import ArtifactManifest, NormalMixture, digest, validate_artifact

root = Path("docs/implementation/evidence/G0-LIB/exchange")
root.mkdir(exist_ok=True)
outputs = Path("tooling/library/__pycache__/outputs")
for path in [*outputs.glob("*.*"), *outputs.joinpath("r").glob("*.*")]:
    shutil.copyfile(path, root / path.name)
py = json.loads(Path("docs/implementation/evidence/G0-LIB/python-probes.json").read_text())
r = json.loads(root.joinpath("r-probes.json").read_text())
np.testing.assert_allclose(py["wcls_python"]["coefficients"], r["wcls"]["coefficients"], rtol=0, atol=1e-12)
def table(name):
    with (root/name).open(newline="") as stream: return list(csv.DictReader(stream))
a, b = table("pymc-draws.csv"), table("sbc-return.csv")
assert [(x["chain"],x["draw"],x["quantity"]) for x in a] == [(x["chain"],x["draw"],x["quantity"]) for x in b]
np.testing.assert_allclose([float(x["value"]) for x in a], [float(x["value"]) for x in b], atol=1e-12, rtol=0)
def file(name): return {"path": name, "sha256": digest(root/name)}
def ref(name): return {"id":name,"version":"qualification-fixture-1","sha256":digest(Path("tooling/library/probe-offline.R"))}
runtime = {"image":"sha256:2d24b2af23795f11935fd917486dd132c708f2d22e90cf706d540bcd647100d5",
    "platform":"linux-x86_64","runtime":"R-4.5.2","packages":{p["package"]:p["version"] for p in r["packages"]},
    "precision":"float64","device":"cpu"}
def manifest(name, shape, unit):
    raw = {"schema_version":"1.0.0","synthetic":True,"kind":"offline_artifact","artifact_id":name,
        "payload":file(name),"inputs":[file("fit-input.json"),file("pymc-draws.csv")],
        "sources":[ref("offline-CLI-fixture")],"unit":unit,"model":ref("toy-normal-model"),
        "prior":ref("toy-normal-prior"),"transform":ref("identity"),
        "seed":{"namespace":"fixture","protocol":"API-qualification","scenario":"toy",
            "replicate":0,"patient":"synthetic","time_index":0,"process":"file-exchange"},
        "observation_cutoff":"2026-10-20T00:00:00Z","producer":runtime,
        "producer_status":"completed","failure_reason":None,"shape":shape}
    value=ArtifactManifest.model_validate_json(json.dumps(raw))
    validate_artifact(root,value)
    (root/(name+".manifest.json")).write_text(value.model_dump_json(indent=2)+"\n")
for w in [0,.5,.9,1]:
    name=f"mixture-{w}.json"
    mixture=NormalMixture.model_validate_json((root/name).read_bytes())
    manifest(name,{"kind":"normal_mixture","components":len(mixture.components),"marginal_scale":"ISI_points"},"ISI_points")
manifest("sbc-return.csv",{"kind":"mcmc_draws","chains":[0,1,2,3],"draws":200,"quantities":["mu"]},"ISI_points")
manifest("wcls-input.csv",{"kind":"wcls_fixture","rows":72,"analysis":file("wcls-analysis.json"),"independent_unit":"patient"},"quality_points")
Path("contracts/artifacts/manifest.schema.json").write_text(json.dumps(ArtifactManifest.model_json_schema(),indent=2,sort_keys=True)+"\n")
Path("contracts/artifacts/normal-mixture.schema.json").write_text(json.dumps(NormalMixture.model_json_schema(),indent=2,sort_keys=True)+"\n")
print("PASS: 6 actual artifact manifests; mixture boundaries; 800 chain/draw coordinates; PyMC/R draw values and Python/R WCLS coefficients within 1e-12. Variance estimators remain explicitly different.")
