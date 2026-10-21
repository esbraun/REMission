"""Review regressions against actual R1 files, not mocked statistical outputs."""
import copy
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path

from contracts.artifacts.manifest import ArtifactManifest, digest, dispatch_checked, validate_artifact
from contracts.domain.boundaries import ContractViolation
from contracts.domain.common import VersionRef
from contracts.domain.estimands import FitRequest
from tooling.library.lineage import PY_IMAGE, R_IMAGE, build_manifests
from tests.contracts.test_domain import parse, request

ROOT=Path(__file__).resolve().parents[2]
EXCHANGE=ROOT/"docs/implementation/evidence/G0-LIB/R1/exchange"


class LineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for p in EXCHANGE.iterdir():
            if p.is_file():shutil.copyfile(p,self.root/p.name)
        self.py=json.loads((ROOT/"docs/implementation/evidence/G0-LIB/python-probes.json").read_text())["packages"]
        self.r={p["package"]:p["version"] for p in json.loads((self.root/"r-probes.json").read_text())["packages"]}
        self.calls=[]

    def dispatch(self,manifest):
        raw=request();raw["context"]["model"]=manifest.model.model_dump(mode="json");raw["context"]["prior"]=manifest.prior.model_dump(mode="json")
        fit=parse(FitRequest,raw)
        refs=[parse(VersionRef,raw["configuration"]),*list(fit.context.model_dump(include={"estimand","dgp","scenario","input_data","prior","model","protocol","comparator_estimand"}).values())]
        accepted=[VersionRef.model_validate(x) if isinstance(x,dict) else x for x in refs]
        accepted += [manifest.transform,*manifest.sources]
        return dispatch_checked(fit,accepted,[(self.root,manifest)],lambda _:self.calls.append(True) or "done")

    def test_artifact_specific_producers_and_direct_inputs(self):
        m=build_manifests(self.root,self.py,self.r)
        w=m["wcls-input.csv"];result=m["wcls-result.json"];mix=m["mixture-0.5.json"]
        self.assertEqual(w.producer.image,PY_IMAGE);self.assertEqual(result.producer.image,R_IMAGE)
        self.assertEqual({r.path for r in w.inputs},{"wcls-definition.json","wcls-source.py"})
        self.assertEqual({r.path for r in mix.inputs},{"mixture-recipe.json","offline-source.R"})
        self.assertEqual(w.sources[0].sha256,digest(self.root/"wcls-source.py"))
        self.assertEqual(result.shape.input.sha256,w.payload.sha256)
        typed=validate_artifact(self.root,result)
        self.assertEqual(typed.input_sha256,w.payload.sha256)
        for name,value in m.items():
            stored=ArtifactManifest.model_validate_json((self.root/(name+".manifest.json")).read_bytes())
            self.assertEqual(value,stored)

    def test_generator_definition_mutation_changes_lineage_and_stale_source_rejected(self):
        original=build_manifests(self.root,self.py,self.r)
        source=self.root/"wcls-source.py"
        source.write_bytes(source.read_bytes().replace(b".2*x",b".3*x"))
        with self.assertRaises(ContractViolation):self.dispatch(original["wcls-input.csv"])
        with self.assertRaises(ContractViolation):build_manifests(self.root,self.py,self.r)
        recipe=json.loads((self.root/"wcls-definition.json").read_text())
        recipe["source_sha256"]=digest(source);recipe["y"]="1+0.3*x+2*(action-0.5)+0.1*sin(patient+2*time)"
        (self.root/"wcls-definition.json").write_text(json.dumps(recipe))
        changed=build_manifests(self.root,self.py,self.r)
        self.assertNotEqual(changed["wcls-input.csv"].sources[0].sha256,original["wcls-input.csv"].sources[0].sha256)
        self.assertNotEqual(changed["wcls-input.csv"].model.sha256,original["wcls-input.csv"].model.sha256)
        self.assertEqual(changed["mixture-0.5.json"],original["mixture-0.5.json"])
        self.assertEqual(self.calls,[])

    def test_R_result_wrong_input_hash_or_unit_rejected_before_worker(self):
        original=build_manifests(self.root,self.py,self.r)["wcls-result.json"]
        path=self.root/"wcls-result.json";payload=json.loads(path.read_text())
        for key,value in [("input_sha256","b"*64),("unit","ISI_points")]:
            bad={**payload,key:value};path.write_text(json.dumps(bad))
            manifest=original.model_copy(deep=True);manifest.payload.sha256=digest(path)
            with self.assertRaises(ContractViolation):self.dispatch(manifest)
        self.assertEqual(self.calls,[])
