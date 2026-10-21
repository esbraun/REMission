"""Generate deterministic JSON Schema and field dictionary from maintained types."""
import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from .boundaries import LearnerHistory, LearnerInput, ObservedHistory
from .common import FitMetadata
from .entities import ExternalStudy, ObservedRecord
from .estimands import EstimandContract, FitRequest, InterruptionResult, NamedThreshold
from .evaluation import (DGPConfig, EvaluationProtocol, EvidenceRecord,
                         GateEvidence, ReplicateResult, SimulatorTruth, TruthResult)
from .temporal import TemporalContract

ROOT = Path(__file__).resolve().parent
ADAPTERS = {
    "observed-records": TypeAdapter(ObservedRecord),
    "learner-input": TypeAdapter(LearnerInput),
    "learner-history": TypeAdapter(LearnerHistory),
    "observed-history": TypeAdapter(ObservedHistory),
    "estimand": TypeAdapter(EstimandContract),
    "fit-request": TypeAdapter(FitRequest),
    "fit-metadata": TypeAdapter(FitMetadata),
    "interruption-result": TypeAdapter(InterruptionResult),
    "threshold": TypeAdapter(NamedThreshold),
    "external-study": TypeAdapter(ExternalStudy),
    "temporal": TypeAdapter(TemporalContract),
    "dgp-config": TypeAdapter(DGPConfig),
    "evaluation-protocol": TypeAdapter(EvaluationProtocol),
    "replicate-result": TypeAdapter(ReplicateResult),
    "gate-evidence": TypeAdapter(GateEvidence),
    "evidence-record": TypeAdapter(EvidenceRecord),
    "evaluator-truth": TypeAdapter(SimulatorTruth | TruthResult),
}


def products():
    output = {}
    dictionary = {}
    for name, adapter in ADAPTERS.items():
        schema = adapter.json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"urn:remission:domain:1.0.0:{name}"
        output[f"schemas/{name}.schema.json"] = schema
        definitions = schema.get("$defs", {})
        if "properties" in schema:
            definitions = {**definitions, schema["title"]: schema}
        for model_name, definition in definitions.items():
            if "properties" in definition:
                dictionary[model_name] = {
                    "description": definition.get("description", "See typed class and canonical source map in contracts.md"),
                    "fields": {field: {"required": field in definition.get("required", []), "schema": field_schema}
                               for field, field_schema in definition["properties"].items()},
                }
    output["dictionary-v1.json"] = {"schema_version": "1.0.0", "status": "proposal_for_independent_review", "models": dictionary}
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files drift")
    args = parser.parse_args()
    for relative, value in products().items():
        path = ROOT / relative
        text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                raise SystemExit(f"generated contract drift: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    print("Contract JSON Schema/dictionary " + ("match typed source" if args.check else "exported"))


if __name__ == "__main__":
    main()
