"""Explicit offline service activation for isolated contract fixtures only."""
from datetime import datetime, timezone
from pathlib import Path
from contracts.service.live_hold import LiveHoldAuthority, ReviewRules
from services.foundation.cutover import activate_new, bundle_for
from services.foundation.store import canonical

ACTIVATION=datetime(2026,10,21,8,tzinfo=timezone.utc)


def ref(identifier):
    return dict(id=identifier,version='1.0.0',sha256='0'*64)


def fixture_bundle(grants=None, rules=None):
    authority=LiveHoldAuthority.model_validate_json(canonical(dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,
        authority_id='explicit-test-only',version=ref('test-only-authority'),enabled=True,
        service_contract=__import__('json').loads(Path('contracts/service/bindings-v1.json').read_bytes())['live_hold'],
        schema_binding=__import__('json').loads(Path('contracts/service/bindings-v1.json').read_bytes())['service_schema_set'],follow_up_amendments=[],
        observed_binding=__import__('json').loads(Path('contracts/runs/bindings-v2.json').read_bytes())['observed_representation'],archive_verifier=ref('fixture-archive-verifier'),
        producer=ref('fixture-producer'),source_registry=ref('fixture-registry'),execution='contract_fixture',grants=grants or [])))
    review_rules=ReviewRules.model_validate_json(canonical(dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,rules=rules or [])))
    return bundle_for(authority,review_rules)


def fresh_store(path, installed=None):
    store=activate_new(Path(path),installed or fixture_bundle(),ACTIVATION)
    store.clock=lambda:datetime(2026,10,21,9,tzinfo=timezone.utc)
    return store


def live_fixture(root,*,run_name='obs2-fixture-run',threshold=False,extra_hold=False):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'run_contracts'))
    from observed_v2_fixtures import build
    from contracts.domain.evidence_v2 import exact_ref
    from contracts.runs.observed_v2 import ExportAuthorityV2
    from services.foundation.store import digest
    fixture=build(root/'staging',hold=True,service_owner='alice',run_name=run_name,threshold_concern=threshold,extra_hold=extra_hold)
    authority=ExportAuthorityV2.model_validate_json(canonical(fixture['authority']))
    entries=[entry['record'] for entry in fixture['entries']]
    bundle=next(r for r in entries if r['kind']=='hold_transition_bundle' and r['transition_type']=='enter')
    trigger=next(r for r in entries if r['record_id']==bundle['trigger_refs'][0]['record_id'])
    task=next(r for r in entries if r['record_id']==bundle['follow_up_refs'][0]['record_id'])
    requirement=dict(requirement_id='review-threshold' if threshold else 'review-concern',definition=trigger['requirement'],responsible_role='doctor',
        evidence_kinds=['hold_review_evidence'],source_ids=['fixture-simulation'])
    archive_id=bundle['run_id']+':'+__import__('json').loads(fixture['raw'])['id']
    grant=dict(account_id='alice',service_patient_id='SYN-02',archive_patient_id='SYN-02',source_id='fixture-simulation',source_version='1.2.0',
        run_id=bundle['run_id'],partition_id=bundle['partition_id'],archive_id=archive_id,package_sha256=digest(fixture['raw']),
        archive_authority_sha256=digest(canonical(authority.model_dump(mode='json'))),ownership_ref=bundle['ownership_ref'],episode_namespace='synthetic-fixture',
        allowed_operations=['invalidate'],trigger_bindings=[dict(trigger_rule=trigger['rule'],required_reviews=[requirement],
            follow_ups=[dict(reference=bundle['follow_up_refs'][0],owner_id='alice',policy=ref('explicit-fixture-follow-up'),due_at=task['due_at'],escalation_destination=task['escalation_destination'])])])
    for record in entries:
        if record['kind']=='hold_transition_bundle' and record['transition_type']=='change_reason':
            for reference in record['follow_up_refs']:
                follow=next(r for r in entries if r['record_id']==reference['record_id'])
                grant['trigger_bindings'][0]['follow_ups'].append(dict(reference=reference,owner_id='alice',policy=ref('explicit-fixture-follow-up'),due_at=follow['due_at'],escalation_destination=follow['escalation_destination']))
    manual_rule=dict(ref=ref('MANUAL-HOLD-REVIEW'),trigger_rule=trigger['rule'],requirements=[requirement])
    installed=fixture_bundle([grant],[] if threshold else [manual_rule])
    command=dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,archive_id=archive_id,partition_id=bundle['partition_id'],
        bundle_ref=dict(record_id=bundle['record_id'],payload_sha256=digest(canonical(bundle))),trigger_refs=bundle['trigger_refs'])
    return fixture,authority,installed,command
