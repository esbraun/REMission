"""Offline boundary regressions, independent of expensive fit execution."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from contracts.artifacts.manifest import (ArtifactManifest, NormalMixture, digest,
    dispatch_checked, validate_artifact)
from contracts.domain.boundaries import ContractViolation
from contracts.domain.common import VersionRef
from contracts.domain.estimands import FitRequest
from tests.contracts.test_domain import request, ref, seed, parse


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / "input.json"
        self.input.write_text("{}", encoding="utf-8")
        self.payload = self.root / "mixture.json"
        self.mixture = {"schema_version": "1.0.0", "synthetic": True,
            "kind": "normal_mixture", "marginal_scale": "ISI_points",
            "informative_weight": .5, "weak_sd": 5.0, "components": [
                {"weight": .5, "mean": -2.0, "sd": 1.0, "role": "informative"},
                {"weight": .5, "mean": 0.0, "sd": 5.0, "role": "weak"}]}
        self.payload.write_text(json.dumps(self.mixture), encoding="utf-8")
        self.raw = {"schema_version": "1.0.0", "synthetic": True,
            "kind": "offline_artifact", "artifact_id": "fixture",
            "payload": self.file(self.payload), "inputs": [self.file(self.input)],
            "sources": [ref("source")], "unit": "ISI_points", "model": ref("model"),
            "prior": ref("prior"), "transform": ref("transform"), "seed": seed(),
            "observation_cutoff": "2026-10-01T00:00:00Z",
            "producer": {"image": "sha256:" + "a"*64, "platform": "linux-x86_64",
                "runtime": "R-4.5.2", "packages": {"RBesT": "1.12.0"},
                "precision": "float64", "device": "cpu"},
            "producer_status": "completed", "failure_reason": None,
            "shape": {"kind": "normal_mixture", "components": 2, "marginal_scale": "ISI_points"}}
        self.calls = []
        self.request = parse(FitRequest, request())
        self.accepted = [parse(VersionRef, ref(name)) for name in ["estimand", "dgp", "scenario",
            "input_data", "prior", "model", "protocol", "comparator_estimand", "fit-config", "source", "transform"]]

    def file(self, path):
        return {"path": path.name, "sha256": digest(path)}

    def dispatch(self, raw=None, accepted=None):
        return dispatch_checked(self.request, self.accepted if accepted is None else accepted,
            [(self.root, parse(ArtifactManifest, self.raw if raw is None else raw))],
            lambda r: self.calls.append(r) or "done")

    def test_positive_roundtrip_and_dispatch(self):
        artifact = parse(ArtifactManifest, self.raw)
        self.assertEqual(parse(ArtifactManifest, artifact.model_dump(mode="json")), artifact)
        self.assertEqual(validate_artifact(self.root, artifact).informative_weight, .5)
        self.assertEqual(self.dispatch(), "done")
        self.assertEqual(len(self.calls), 1)

    def test_versions_and_malformed_request_before_worker(self):
        for mutate in [lambda x: x.update(schema_version="2.0.0"),
                       lambda x: x.update(precision="float32"),
                       lambda x: x.update(sampler="nutpie")]:
            raw = request(); mutate(raw)
            with self.assertRaises(ValidationError): parse(FitRequest, raw)
        with self.assertRaises(ContractViolation): self.dispatch(accepted=[])
        bad = copy.deepcopy(self.raw); bad["transform"]["sha256"] = "b"*64
        with self.assertRaises(ContractViolation): self.dispatch(bad)
        self.assertEqual(self.calls, [])

    def test_input_and_payload_tampering_before_worker(self):
        for path in [self.input, self.payload]:
            original = path.read_bytes(); path.write_bytes(original + b" ")
            with self.assertRaisesRegex(ContractViolation, "modified"): self.dispatch()
            path.write_bytes(original)
        self.assertEqual(self.calls, [])

    def test_failure_context_and_path_before_worker(self):
        for field, value in [("producer_status", "failed"), ("observation_cutoff", "2026-10-03T00:00:00Z")]:
            bad = copy.deepcopy(self.raw); bad[field] = value
            if field == "producer_status": bad["failure_reason"] = "producer failed"
            with self.assertRaises(ContractViolation): self.dispatch(bad)
        bad = copy.deepcopy(self.raw); bad["payload"]["path"] = "../outside.json"
        with self.assertRaises(ContractViolation): self.dispatch(bad)
        bad = copy.deepcopy(self.raw); bad["model"] = ref("other-model")
        with self.assertRaises(ContractViolation): self.dispatch(bad)
        self.assertEqual(self.calls, [])

    def test_units_schema_weights_and_shape(self):
        for field, value in [("schema_version", "2.0.0"), ("marginal_scale", "quality_points"),
                             ("informative_weight", .9)]:
            bad = copy.deepcopy(self.mixture); bad[field] = value
            with self.assertRaises(ValidationError): parse(NormalMixture, bad)
        bad = copy.deepcopy(self.raw); bad["shape"]["components"] = 3
        with self.assertRaises(ContractViolation): self.dispatch(bad)
        self.assertEqual(self.calls, [])

    def test_draw_coordinates_and_nonfinite(self):
        path = self.root / "draws.csv"
        raw = copy.deepcopy(self.raw)
        raw["shape"] = {"kind": "mcmc_draws", "chains": [0,1], "draws": 1, "quantities": ["mu"]}
        for body, valid in [("0,0,mu,1.2\n1,0,mu,1.3\n", True),
                            ("0,0,mu,1.2\n0,0,mu,1.3\n", False),
                            ("0,0,mu,nan\n1,0,mu,1.3\n", False), ("0,0,mu,1.2\n", False)]:
            path.write_text("chain,draw,quantity,value\n" + body, encoding="utf-8")
            raw["payload"] = self.file(path)
            if valid: self.assertEqual(len(validate_artifact(self.root, parse(ArtifactManifest, raw))), 2)
            else:
                with self.assertRaises(ContractViolation): self.dispatch(raw)
        self.assertEqual(self.calls, [])

    def test_wcls_manifest_and_probability(self):
        path = self.root / "wcls.csv"; analysis = self.root / "analysis.json"
        analysis.write_text(json.dumps({"schema_version": "1.0.0", "unit": "quality_points", "centering": .5,
            "independent_unit": "patient", "r_se": "hat_matrix_small_sample", "python_se": "cluster_correction_not_identical"}), encoding="utf-8")
        raw = copy.deepcopy(self.raw); raw["unit"] = "quality_points"
        raw["shape"] = {"kind": "wcls_fixture", "rows": 1, "analysis": self.file(analysis), "independent_unit": "patient"}
        for p in [.5, 0.0]:
            path.write_text(f"id,time,y,action,logging_probability,numerator_probability,availability,x\nP1,0,3,1,{p},0.5,1,2\n", encoding="utf-8")
            raw["payload"] = self.file(path)
            if p: self.assertEqual(len(validate_artifact(self.root, parse(ArtifactManifest, raw))), 1)
            else:
                with self.assertRaises(ContractViolation): self.dispatch(raw)
        self.assertEqual(self.calls, [])


if __name__ == "__main__": unittest.main()
