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
        observed_binding=ref('OBS-REP-02'),archive_verifier=ref('fixture-archive-verifier'),
        producer=ref('fixture-producer'),source_registry=ref('fixture-registry'),execution='contract_fixture',grants=grants or [])))
    review_rules=ReviewRules.model_validate_json(canonical(dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,rules=rules or [])))
    return bundle_for(authority,review_rules)


def fresh_store(path, installed=None):
    return activate_new(Path(path),installed or fixture_bundle(),ACTIVATION)
