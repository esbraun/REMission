"""Separate v2 generated products; never rewrites a v1 file."""
import argparse
import json
from pathlib import Path
from pydantic import TypeAdapter
from .observed_v2 import (DailyReportV2, HoldReviewEvidenceV2, HoldTransitionBundleV2, LearnerHistoryV2,
                         LearnerInputV2, ObservedHistoryV2, ObservedRecordV2, SupportDecision,
                         SupportOutcomeLink, SupportStageClosureV2)

MODELS = {'observed-records': ObservedRecordV2, 'observed-history': ObservedHistoryV2, 'learner-history': LearnerHistoryV2,
          'learner-input': LearnerInputV2, 'daily-report': DailyReportV2, 'support-decision': SupportDecision,
          'support-outcome-link': SupportOutcomeLink, 'hold-transition-bundle': HoldTransitionBundleV2,
          'hold-review-evidence': HoldReviewEvidenceV2, 'support-stage-closure': SupportStageClosureV2}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode()


def products():
    result = {}
    dictionary = {}
    for name, model in MODELS.items():
        schema = TypeAdapter(model).json_schema()
        schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        schema['$id'] = f'urn:remission:domain:2.0.0:{name}'
        result[f'schemas/v2/{name}.schema.json'] = schema
        for title, definition in {**schema.get('$defs', {}), name: schema}.items():
            if 'properties' in definition:
                dictionary[title] = {'description': definition.get('description', 'OBS-REP-02; accepted complete R1 proposal'),
                                     'fields': {key: dict(required=key in definition.get('required', []), schema=value) for key, value in definition['properties'].items()}}
    result['dictionary-v2.json'] = {'contract_version': '2.0.0', 'claim': 'Wire representation; no producer or clinical validation',
                                    'models': dictionary}
    import hashlib
    result['schemas/v2/schema-set.json'] = {'id': 'OBS2-DOMAIN-SCHEMAS', 'version': '2.0.0', 'sha256_by_path':
                                           {k: hashlib.sha256(encoded(v)).hexdigest() for k, v in result.items()}}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).parent
    for name, value in products().items():
        path = root / name
        raw = encoded(value)
        if args.check:
            if not path.is_file() or path.read_bytes() != raw:
                raise SystemExit('v2 domain schema/dictionary drift: ' + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    print('PASS: separate v2 domain products')


if __name__ == '__main__':
    main()
