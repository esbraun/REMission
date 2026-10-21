"""Artifact-specific qualification lineage, not a general provenance registry."""
from pathlib import Path
import json
from contracts.artifacts.manifest import ArtifactManifest, NormalMixture, digest, validate_artifact
from contracts.domain.boundaries import ContractViolation

PY_IMAGE = "sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7"
R_IMAGE = "sha256:2d24b2af23795f11935fd917486dd132c708f2d22e90cf706d540bcd647100d5"


def file(root, name): return {"path": name, "sha256": digest(root/name)}
def ref(root, name, identity): return {"id": identity, "version": "qualification-R1", "sha256": digest(root/name)}


def build_manifests(root: Path, py_packages, r_packages):
    for name, pairs in [("wcls-definition.json",[("source_sha256","wcls-source.py")]),
                        ("mixture-recipe.json",[("source_sha256","offline-source.R")]),
                        ("draw-transfer.json",[("input_draws_sha256","pymc-draws.csv"),
                            ("python_source_sha256","python-original-source.py"),("R_source_sha256","offline-source.R")])]:
        definition=json.loads((root/name).read_text())
        if any(definition[key] != digest(root/source) for key,source in pairs):
            raise ContractViolation("definition_source_lineage", "Fixture recipe must match its exact generating source/input")
    py = {"image": PY_IMAGE, "runtime": "Python-3.13.7", "packages": py_packages}
    r = {"image": R_IMAGE, "runtime": "R-4.5.2", "packages": r_packages}
    outputs = {}

    def add(name, shape, unit, producer, inputs, source, definition, model, prior, transform):
        raw = {"schema_version":"1.0.0", "synthetic":True, "kind":"offline_artifact", "artifact_id":name,
            "payload":file(root,name), "inputs":[file(root,p) for p in inputs],
            "sources":[ref(root,p,i) for p,i in source], "unit":unit,
            "model":ref(root,definition,model), "prior":ref(root,definition,prior),
            "transform":ref(root,definition,transform),
            "seed":{"namespace":"fixture","protocol":"API-qualification","scenario":"toy",
                "replicate":0,"patient":"synthetic","time_index":0,"process":"deterministic-file-exchange"},
            "observation_cutoff":"2026-10-20T00:00:00Z",
            "producer":{**producer,"platform":"linux-x86_64","precision":"float64","device":"cpu"},
            "producer_status":"completed","failure_reason":None,"shape":shape}
        value=ArtifactManifest.model_validate_json(json.dumps(raw))
        validate_artifact(root,value)
        outputs[name]=value

    for w in [0,.5,.9,1]:
        name=f"mixture-{w}.json"
        mixture=NormalMixture.model_validate_json((root/name).read_bytes())
        add(name,{"kind":"normal_mixture","components":len(mixture.components),"marginal_scale":"ISI_points"},
            "ISI_points",r,["mixture-recipe.json","offline-source.R"],[("offline-source.R","RBesT-fixed-mixture-CLI")],
            "mixture-recipe.json","fixed-normal-mixture-recipe","fixed-normal-prior-not-gMAP","RBesT-robustify-to-JSON")
    add("sbc-return.csv",{"kind":"mcmc_draws","chains":[0,1,2,3],"draws":200,"quantities":["mu"]},
        "ISI_points",r,["pymc-draws.csv","draw-transfer.json","offline-source.R"],
        [("offline-source.R","SBC-draw-matrix-CLI"),("python-original-source.py","historical-native-PyMC-producer")],
        "draw-transfer.json","toy-normal-normal-model","toy-mu-normal-0-sd2","chain-draw-matrix-file-transfer")
    add("wcls-input.csv",{"kind":"wcls_fixture","rows":72,"analysis":file(root,"wcls-analysis.json"),"independent_unit":"patient"},
        "quality_points",py,["wcls-definition.json","wcls-source.py"],[("wcls-source.py","Python-deterministic-WCLS-generator")],
        "wcls-definition.json","WCLS-fixture-formula","not-applicable-frequentist-fixture","identity-CSV-column-order")
    add("wcls-result.json",{"kind":"wcls_result","input":file(root,"wcls-input.csv"),"analysis":file(root,"wcls-analysis.json")},
        "quality_points",r,["wcls-input.csv","wcls-analysis.json","offline-source.R"],[("offline-source.R","MRTAnalysis-WCLS-CLI")],
        "offline-source.R","MRTAnalysis-WCLS-reference","not-applicable-frequentist-analysis","R-coefficients-JSON-export")
    return outputs
