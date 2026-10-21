"""Generate/check exact run schemas, field dictionary and accepted input refs."""
import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter
from .common import Authority, Bindings, ExportAuthority, canonical, sha256
from .observed import ObservedExport, ReplayBatch
from .private import CalibrationArtifact, ExternalCalibrationEvidence, RunManifest, RunResult, SeedLedger, TruthRequest, TruthResponse
from .probability import ProbabilityEvidence, ProbabilityPilotPlan, PilotTrial, PairedPath, StructuralDerivation, TruthFilterReceipt, SymptomPilotBinding, IIDInvestigation, IIDInvestigationAuthority

ROOT=Path(__file__).resolve().parents[2]
PACKAGE=Path(__file__).resolve().parent
SOURCES={
    'protocol':('remission-g1-v1','1.0.0','docs/implementation/g1-technical-plan-20261021.md'),
    'dgp':('DGP-01','1.2.0','contracts/dgp/parameters-v1.json'),
    'parameters':('DGP-PARAMETERS','1.2.0','contracts/dgp/parameters-v1.json'),
    'equations':('DGP-EQUATIONS','1.2.0','docs/spec/dgp-reference.md'),
    'scenarios':('DGP-SCENARIOS','1.2.0','contracts/dgp/scenarios-v1.json'),
    'catalog':('DGP-CATALOG','1.2.0','docs/spec/scenario-catalog.md'),
    'timing':('DGP-TIMING','1.2.0','contracts/dgp/timing-v1.json'),
    'temporal':('TIME-01','2.0.0','contracts/domain/temporal-v2.json'),
    'calibration_schema':('DGP-CALIBRATION','1.1.0','contracts/dgp/calibration-binding-v1.schema.json'),
    'analytic_fixtures':('DGP-ANALYTIC-FIXTURES','1.0.0','contracts/dgp/truth-fixtures-v1.json'),
    'probability_precision':('ESTINT-PRECISION-01','1.0.0-r1','docs/implementation/g1-estint-probability-precision-proposal-r1-20261021.md')}
MODELS={'observed-export':ObservedExport,'observed-replay':ReplayBatch,'run-manifest':RunManifest,'run-result':RunResult,
        'seed-ledger':SeedLedger,'evaluator-request':TruthRequest,'evaluator-response':TruthResponse,
        'calibration-artifact':CalibrationArtifact,'external-calibration-evidence':ExternalCalibrationEvidence,'trusted-run-authority':Authority,'trusted-export-authority':ExportAuthority,
        'probability-evidence':ProbabilityEvidence,'probability-pilot-plan':ProbabilityPilotPlan,'probability-pilot-trial':PilotTrial,'probability-paired-path':PairedPath,'probability-structural-proof':StructuralDerivation,'probability-truth-filter-receipt':TruthFilterReceipt,'symptom-pilot-binding':SymptomPilotBinding,'iid-investigation':IIDInvestigation,'trusted-iid-investigation-authority':IIDInvestigationAuthority}


def bindings_data():
    return {name:dict(id=identifier,version=version,sha256=sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')))
            for name,(identifier,version,path) in SOURCES.items()}


def products():
    products={'bindings-v1.json':bindings_data()};dictionary={}
    for name,model in MODELS.items():
        schema=TypeAdapter(model).json_schema()
        schema['$schema']='https://json-schema.org/draft/2020-12/schema'
        schema['$id']=f'urn:remission:runs:1.0.0:{name}'
        products[f'schemas/{name}.schema.json']=schema
        for title,definition in {**schema.get('$defs',{}),model.__name__:schema}.items():
            if 'properties' in definition:
                dictionary[title]={'description':definition.get('description','See contracts/runs/README.md and canonical G1 plan'),
                    'fields':{key:dict(required=key in definition.get('required',[]),schema=value) for key,value in definition['properties'].items()}}
    products['dictionary-v1.json']={'contract_version':'1.0.0','claim':'Wire contract only; fixture examples are not generator/calibration/truth executions','models':dictionary}
    return products


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for name,value in products().items():
        path=PACKAGE/name;text=json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True)+'\n'
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8')!=text:raise SystemExit('run schema/dictionary/binding drift: '+name)
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n')
    print('Run interface schemas/dictionary and exact accepted source references match v1.0.0')


if __name__=='__main__':main()
