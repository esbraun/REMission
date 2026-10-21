"""Generate new service-only products; never regenerate observed v1/v2 bytes."""
import argparse
import json
from pathlib import Path
from pydantic import TypeAdapter
from contracts.runs.common import sha256
from .live_hold import LiveHoldAuthority, InstalledBundle, InvalidationInput, ReviewInput, ClearanceInput, ExportInput
from .live_safety import LiveHoldFact, LiveSafetyExport, TrustedLiveSafetyAuthority

ROOT=Path(__file__).parent
MODELS={'live-safety-export':LiveSafetyExport,'live-hold-fact':LiveHoldFact,'live-safety-authority':TrustedLiveSafetyAuthority,
        'live-hold-authority':LiveHoldAuthority,'installed-bundle':InstalledBundle,'live-hold-command':InvalidationInput,
        'live-review-command':ReviewInput,'live-clearance-command':ClearanceInput,'live-export-command':ExportInput}


def encoded(value):
    return (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()


def products():
    output={};dictionary={}
    for name,model in MODELS.items():
        schema=TypeAdapter(model).json_schema()
        schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':f'urn:remission:service:{name}:1.0.0'})
        output[f'schemas/v1/{name}.schema.json']=schema
        dictionary[name]=schema
    output['dictionary-v1.json']=dict(schema_version='1.0.0',contract='LIVE-HOLD-01',models=dictionary,
        claim='Synthetic structural service contract; no clinical or scientific producer qualification')
    schema_set={path:sha256(encoded(value)) for path,value in output.items()}
    output['schemas/v1/schema-set.json']=dict(id='LIVE-SAFETY-SERVICE-SCHEMAS',version='1.0.0',sha256_by_path=schema_set)
    repo=ROOT.parents[1]
    proposal=(repo/'docs/implementation/g1-live-hold-executable-contract-proposal-r1-20261021.md').read_bytes().replace(b'\r\n',b'\n')
    output['bindings-v1.json']=dict(live_hold=dict(id='LIVE-HOLD-01',version='1.0.0',sha256=sha256(proposal)),
        live_safety=dict(id='LIVE-SAFETY-EXPORT',version='1.0.0',sha256=sha256(proposal)),
        service_schema_set=dict(id='LIVE-SAFETY-SERVICE-SCHEMAS',version='1.0.0',sha256=sha256(encoded(output['schemas/v1/schema-set.json']))),
        observed_domain={'1.0.0':dict(id='DOMAIN-LEARNER-HISTORY',version='1.0.0',sha256=sha256((repo/'contracts/domain/schemas/learner-history.schema.json').read_bytes().replace(b'\r\n',b'\n'))),
                         '2.0.0':json.loads((repo/'contracts/runs/bindings-v2.json').read_bytes())['domain_schema_set']})
    return output


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--stdout',action='store_true');args=parser.parse_args()
    values=products()
    if args.stdout:
        print(json.dumps(values,sort_keys=True));return
    for path,value in values.items():
        target=ROOT/path;raw=encoded(value)
        if args.check:
            if not target.is_file() or target.read_bytes().replace(b'\r\n',b'\n')!=raw:
                raise SystemExit('service schema drift: '+path)
        else:
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)


if __name__=='__main__':main()
