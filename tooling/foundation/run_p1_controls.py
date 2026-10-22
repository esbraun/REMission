"""Copied non-fitting P1 controls; private generator exists in tests role only."""
import json
import unittest

NAMES=[
    'test_protocol_boundary.ProtocolBoundaryTests',
    'test_protocol_v2.ProtocolGeneratorTests',
    'test_protocol_service.ProtocolServiceTests',
    'test_protocol_admission.ProtocolAdmissionTests',
    'test_borrowing_dispatcher',
    'test_borrowing.JointTargetTests.test_real_frozen_pre_v1_input_result_canonical_identity',
    'test_borrowing.BorrowingRoutesTests.test_genuine_pre_v1_stored_receipt_replays_with_optional_defaults',
    'test_borrowing.BorrowingRoutesTests.test_legacy_v0_receipt_retry_with_new_default_fields_and_immutable_failed_comparison',
]


def owned_boundary_fixture():
    from test_protocol_service import ProtocolServiceTests
    from contracts.domain.analysis import reference
    from contracts.domain.protocol import LAW_REF,PROTOCOL_REFS
    from contracts.domain.protocol_request import make_boundary_input
    from services.foundation.protocol import export_histories
    from services.foundation.store import instant
    case=ProtocolServiceTests('test_explicit_v2_panel_same_route_owner_cutoff_and_no_activation')
    case.setUpClass()
    try:
        case.setUp()
        try:
            response=case.client.post('/api/panels/generate',json=dict(schema_version='2.0.0',kind='poc_protocol_panel',seed=1245,count=2,
                family='support',law=LAW_REF,protocol=PROTOCOL_REFS['support']),headers=case.headers('owned-copied-boundary'))
            case.assertEqual(response.status_code,200)
            patients=response.json()['patient_ids']
            for patient in patients:
                for _ in range(2):case.assertEqual(case.step(patient,'day').status_code,200)
            with case.store.transaction() as db:
                histories=export_histories(db,'alice',patients,instant('2026-01-03T12:00:00Z'))
            run=reference('p1-owned-v2-boundary-fixture','actual authenticated sameendpoint v2 panel plus advance/owned export; not executable')
            seed=dict(namespace='fit',protocol=PROTOCOL_REFS['support']['id'],scenario=run['id'],replicate=0,
                patient=sorted(patients)[0],time_index=2,process='wcls-unused-provenance')
            value=make_boundary_input(histories,'S1-WCLS','analysis-p1-owned-boundary',run,seed)
            print(json.dumps({'kind':'p1-owned-v2-boundary-fixture','input':value.model_dump(mode='json')},sort_keys=True),flush=True)
        finally:case.tearDown()
    finally:case.tearDownClass()
if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromNames(NAMES)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():owned_boundary_fixture()
    raise SystemExit(not result.wasSuccessful())
