"""Generate v2 schema products and noncircular exact schema-set bindings."""
import argparse
import json
from pathlib import Path
from pydantic import TypeAdapter
from contracts.domain.export_v2 import encoded, products as domain_products
from .common import sha256
from .coverage_v2 import CompletionReceiptV2, ScheduleInputV2, StageLedgerV2, SupportCoverageV2, SupportMechanismV2
from .observed_v2 import BindingsV2, ExportAuthorityV2, ObservedExportV2, ReplayBatchV2
from .private_v2 import AuthorityV2, RunManifestV2, RunResultV2, SeedLedgerV2, TruthRequestV2, TruthResponseV2

PACKAGE = Path(__file__).parent
ROOT = PACKAGE.parents[1]
MODELS = {'observed-export': ObservedExportV2, 'observed-replay': ReplayBatchV2, 'run-manifest': RunManifestV2,
          'run-result': RunResultV2, 'seed-ledger': SeedLedgerV2, 'evaluator-request': TruthRequestV2,
          'evaluator-response': TruthResponseV2, 'trusted-run-authority': AuthorityV2, 'trusted-export-authority': ExportAuthorityV2,
          'support-schedule-input': ScheduleInputV2, 'support-coverage': SupportCoverageV2,
          'completion-receipt': CompletionReceiptV2, 'support-stage-ledger': StageLedgerV2, 'support-mechanism': SupportMechanismV2}


def products():
    result = {}
    dictionary = {}
    for name, model in MODELS.items():
        schema = TypeAdapter(model).json_schema()
        schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        schema['$id'] = f'urn:remission:runs:2.0.0:{name}'
        result[f'schemas/v2/{name}.schema.json'] = schema
        for title, definition in {**schema.get('$defs', {}), model.__name__: schema}.items():
            if 'properties' in definition:
                dictionary[title] = {'description': definition.get('description', 'OBS-REP-02; accepted complete R1 proposal'),
                                     'fields': {key: dict(required=key in definition.get('required', []), schema=value) for key, value in definition['properties'].items()}}
    result['dictionary-v2.json'] = {'contract_version': '2.0.0', 'claim': 'Wire contract; fixtures cannot qualify production', 'models': dictionary}
    schema_set = {'id': 'OBS2-RUN-SCHEMAS', 'version': '2.0.0', 'sha256_by_path': {k: sha256(encoded(v)) for k, v in result.items()}}
    result['schemas/v2/schema-set.json'] = schema_set
    bindings = json.loads((PACKAGE / 'bindings-v1.json').read_bytes())
    bindings.update(observed_representation={'id': 'OBS-REP-02', 'version': '2.0.0', 'sha256': sha256((ROOT / 'docs/implementation/g1-observed-representation-proposal-r1-20261021.md').read_bytes())},
                    domain_schema_set={'id': 'OBS2-DOMAIN-SCHEMAS', 'version': '2.0.0', 'sha256': sha256(encoded(domain_products()['schemas/v2/schema-set.json']))},
                    run_schema_set={'id': 'OBS2-RUN-SCHEMAS', 'version': '2.0.0', 'sha256': sha256(encoded(schema_set))})
    result['bindings-v2.json'] = bindings
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, value in products().items():
        path = PACKAGE / name
        if args.check:
            if not path.is_file() or path.read_bytes() != encoded(value):
                raise SystemExit('v2 run schema/dictionary/binding drift: ' + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded(value))
    print('PASS: separate v2 run products and exact representation/schema bindings')


if __name__ == '__main__':
    main()
