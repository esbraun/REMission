"""Export/check the source-versioned G0 DGP authoring artifacts."""
import argparse
import json
from pathlib import Path
from .parameters import VERSION, reference_parameters, validate_parameters
from .scenarios import scenario_manifest, validate_scenarios
from .truth import fixture_manifest
from .calibration import CalibrationBinding, ExternalTargetEvidence
from .timing import timing_manifest

ROOT = Path(__file__).resolve().parent


def artifacts() -> dict:
    parameters = validate_parameters(reference_parameters())
    scenarios = validate_scenarios(scenario_manifest())
    return {"parameters-v1.json": parameters, "scenarios-v1.json": scenarios,
            "timing-v1.json": timing_manifest(),
            "truth-fixtures-v1.json": fixture_manifest(),
            "calibration-binding-v1.schema.json": CalibrationBinding.model_json_schema(),
            "external-target-evidence-v1.schema.json": ExternalTargetEvidence.model_json_schema()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for filename, data in artifacts().items():
        path = ROOT / filename
        content = json.dumps(data, indent=2, ensure_ascii=True) + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"stale or missing authoring artifact: {path}")
        else:
            path.write_text(content, encoding="utf-8")
    print(f"DGP parameter/scenario artifacts match v{VERSION}; independent fixtures remain v1.0.0")


if __name__ == "__main__":
    main()
