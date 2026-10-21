"""Install explicitly fixture-only sources into this task's private deployment."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
from contracts.service.live_hold import LiveHoldAuthority,ReviewRules
from services.foundation.archive import archive_export
from services.foundation.cli import seed
from services.foundation.cutover import activate_new,bundle_for
from services.foundation.store import canonical,digest


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--fixture-root',type=Path,required=True)
    parser.add_argument('--database',type=Path,required=True);parser.add_argument('--historical-source',type=Path)
    parser.add_argument('--source-commit',required=True);args=parser.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests/integration/replay'))
    from live_helpers import live_fixture
    fixtures=[];grants=[];rules={}
    for name,threshold in [('concern',False),('threshold',True),('second-concern',False)]:
        location=args.fixture_root/name
        fixture,authority,installed,command=live_fixture(location,run_name='live-demo-'+name,threshold=threshold)
        fixtures.append((name,location,fixture,authority,command))
        grants.extend(installed.authority.grants)
        for rule in installed.review_rules.rules:rules[rule.ref.id]=rule
    last=installed.authority.model_dump(mode='json');last['grants']=[g.model_dump(mode='json') for g in grants]
    authority=LiveHoldAuthority.model_validate_json(canonical(last))
    review_rules=ReviewRules.model_validate_json(canonical(dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,rules=[r.model_dump(mode='json') for r in rules.values()])))
    bundle=bundle_for(authority,review_rules)
    store=activate_new(args.database,bundle,datetime.now(timezone.utc),source=args.historical_source)
    if args.historical_source is None:seed(store)
    configs=[];cases=[]
    for name,location,fixture,archive_authority,command in fixtures:
        archive_export(store,fixture['raw'],location/'staging',archive_authority,owner_id='alice',received_at=datetime.now(timezone.utc))
        configs.append(dict(export_id=name,manifest=str(location/'staging/manifest.json'),artifact_root=str(location/'staging'),authority=str(location/'staging/authority.json')))
        cases.append(dict(name=name,patient_id='SYN-02',command=command,expected='named T-OBS2-CLEARANCE-POLICY block' if name=='threshold' else 'explicit structural concern review then assessment only'))
    args.fixture_root.joinpath('bundle.json').write_text(bundle.model_dump_json(),encoding='utf-8')
    args.fixture_root.joinpath('archives.json').write_text(canonical(configs),encoding='utf-8')
    runtime=dict(id='foundation-qualified-linux-sqlite',version='Python3.13.7-SQLite3.54.1',sha256='ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa')
    args.fixture_root.joinpath('runtime.json').write_text(canonical(runtime),encoding='utf-8')
    args.fixture_root.joinpath('demo-cases.json').write_text(canonical(dict(synthetic=True,execution='contract_fixture',source_commit=args.source_commit,cases=cases)),encoding='utf-8')
    for path in args.fixture_root.rglob('*'):
        if path.is_file():path.chmod(0o444)
    print(canonical(dict(status='fixture-only-new-private-deployment-unrouted',instance_id=bundle.control.database_instance_id,
        authority_sha256=bundle.control.authority_sha256,review_rules_sha256=bundle.control.review_rules_sha256,cases=cases)))


if __name__=='__main__':main()
