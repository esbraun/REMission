"""OBS2 trusted roster, closure, omission, correction and seed discrimination."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from observed_v2_fixtures import build, canonical, ORIGIN, ref
from contracts.domain.evidence_v2 import exact_ref, outcome_as_known, resolve, validate_outcome_link
from contracts.domain.observed_v2 import ObservedHistoryV2, RECORD_ADAPTER_V2
from contracts.runs.admission import verify_export
from contracts.runs.admission_v2 import verify_export_v2
from contracts.runs.common import sha256
from contracts.runs.coverage_v2 import ScheduleInputV2, SupportCoverageV2, derive_slots
from contracts.runs.observed_v2 import ExportAuthorityV2, ObservedExportV2, ReplayBatchV2


def parsed(data, **changes):
    data = deepcopy(data.model_dump(mode='json') if hasattr(data, 'model_dump') else data)
    data.update(changes)
    data['source']['raw_sha256'] = sha256(canonical({k: v for k, v in data.items() if k != 'source'}))
    return RECORD_ADAPTER_V2.validate_json(canonical(data))


class RunObservedV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.f = build(self.root, prompt=True)
        self.authority = ExportAuthorityV2.model_validate_json(canonical(self.f['authority']))

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_archive_and_verified_offered_one_delivered_zero(self):
        manifest, partitions = verify_export(self.f['raw'], self.root, self.authority)
        partition, history, batch, *_ = partitions[0]
        self.assertEqual(len(history.records), len(batch.entries))
        self.assertEqual({b.type: b.value for b in self.f['link'].burden}, {'offered_prompt_count': 1, 'delivered_prompt_count': 0})
        self.assertTrue(any(e.record.kind == 'assignment' for e in batch.entries))
        self.assertTrue(all(not b.import_to_event_store for b in partition.records if next(r for r in history.records if r.record_id == b.record_id).kind == 'assignment'))
        empty = build(self.root / 'empty')
        authority = ExportAuthorityV2.model_validate_json(canonical(empty['authority']))
        verify_export_v2(empty['raw'], self.root / 'empty', authority)
        self.assertTrue(all(b.value == 0 for b in empty['link'].burden))

    def test_raw_admin_and_delivery_duplicates_corrections_and_retraction(self):
        entries = deepcopy(self.f['entries'])
        at = ORIGIN + timedelta(days=3)
        for kind in ['consent', 'delivery']:
            original = next(e for e in entries if e['record']['kind'] == kind)
            duplicate = deepcopy(original['record'])
            duplicate.update(record_id='repeat-' + kind, lineage_id='repeat-' + kind, duplicate_of=original['record']['record_id'], available_at=at.isoformat())
            entries.append(dict(record=duplicate, raw_source=original['raw_source']))
        original = next(e for e in entries if e['record']['kind'] == 'consent')['record']
        correction = parsed(original, record_id='consent-correction', revision=2, supersedes=original['record_id'], recorded_at=at.isoformat(), available_at=at.isoformat(), consent_status='withdrawn', oversight_status='withdrawn', withdrawn_at=original['effective_at'])
        retraction = parsed(correction, record_id='consent-retracted', revision=3, supersedes=correction.record_id, recorded_at=(at + timedelta(hours=1)).isoformat(), available_at=(at + timedelta(hours=1)).isoformat(), record_status='retracted')
        for record in [correction, retraction]:
            payload = record.model_dump(mode='json')
            raw = canonical(record.model_dump(mode='json', exclude={'source'}))
            payload['source']['raw_sha256'] = sha256(raw)
            entries.append(dict(record=payload, raw_source=raw.decode()))
        batch = ReplayBatchV2.model_validate_json(canonical(dict(schema_version='2.0.0', synthetic=True, kind='observed_replay_batch', contract_version='2.0.0', run_id='obs2-fixture-run', partition_id='obs2-partition', patient_id='SYN-02', entries=list(reversed(entries)))))
        history = ObservedHistoryV2(schema_version='2.0.0', synthetic=True, kind='observed_history', patient_id='SYN-02', records=[e.record for e in batch.entries])
        active = history.as_known_at(at + timedelta(hours=2))
        self.assertEqual(sum(r.kind == 'delivery' for r in active), 1)
        self.assertEqual(sum(r.kind == 'consent' for r in active), 0)
        self.assertEqual(len(batch.entries), len(entries))
        duplicate_entry = next(e for e in entries if e['record']['record_id'] == 'repeat-delivery')
        self.assertEqual(duplicate_entry['raw_source'], next(e for e in entries if e['record']['record_id'] == duplicate_entry['record']['duplicate_of'])['raw_source'])
        # Mutating a duplicate header's clinical payload never creates a new fact.
        duplicate_entry['record']['option'] = 'no_prompt'
        with self.assertRaisesRegex(ValueError, 'original clinical payload'):
            ReplayBatchV2.model_validate_json(canonical(dict(schema_version='2.0.0', synthetic=True, kind='observed_replay_batch', contract_version='2.0.0', run_id='obs2-fixture-run', partition_id='obs2-partition', patient_id='SYN-02', entries=entries)))

    def test_missing_middle_shortened_roster_timezone_and_origin(self):
        coverage = deepcopy(self.f['coverage'])
        for mutation in ['middle', 'shorten', 'first', 'last', 'timezone', 'origin']:
            c = deepcopy(coverage)
            if mutation == 'middle':
                del c['slots'][40]; del c['expected_decisions'][40]
            elif mutation == 'shorten':
                c['slots'] = c['slots'][:10]; c['expected_decisions'] = c['expected_decisions'][:10]; c['last_decision_index'] = 9; c['last_decision_at'] = c['expected_decisions'][-1]['decision_at']
            elif mutation == 'first':
                c['first_decision_index'] = -1
            elif mutation == 'last':
                c['last_decision_index'] = 83
            elif mutation == 'timezone':
                c['schedule']['timezone'] = 'America/Los_Angeles'
            else:
                c['schedule']['time_zero_local_date'] = '2026-01-02'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                SupportCoverageV2.model_validate_json(canonical(c))
        self.assertEqual(coverage['expected_decisions'][0]['decision_index'], 0)
        self.assertEqual(coverage['expected_decisions'][-1]['decision_index'], 84)
        self.assertEqual(derive_slots(self.f['schedule'])[-1].assessment_at, ORIGIN + timedelta(days=85, hours=7))

    def test_terminal_phase_and_late_death_need_qualified_exact_evidence(self):
        for hour, expected_last in [(8, 16), (9, 16), (10, 17)]:
            slots = derive_slots(self.f['schedule'], death_at=ORIGIN + timedelta(days=17, hours=hour))
            self.assertEqual(slots[-1].decision_index, expected_last)
        c = deepcopy(self.f['coverage'])
        c['death_ref'] = dict(record_id='late-death', payload_sha256='0' * 64)
        c['death_effective_at'] = (ORIGIN + timedelta(days=17, hours=8)).isoformat()
        # Recomputed shortened list is still not evidence of terminal truncation.
        slots = derive_slots(self.f['schedule'], death_at=ORIGIN + timedelta(days=17, hours=8))
        c['expected_decisions'] = [s.model_dump(mode='json') for s in slots]
        c['slots'] = c['slots'][:len(slots)]
        c['last_decision_index'] = slots[-1].decision_index
        c['last_decision_at'] = slots[-1].decision_at.isoformat()
        with self.assertRaisesRegex(ValueError, 'terminal truncation'):
            SupportCoverageV2.model_validate_json(canonical(c))
        # Missing actual death remains unqualified even if uploader adds a hash.
        self.assertIsNone(self.authority.partitions[0].terminal_evidence_sha256)

    def test_zero_before_closure_equal_time_and_missing_stage_are_denied(self):
        h, link = self.f['history'], self.f['link']
        # At/before an exact evidence arrival it cannot produce an observed count.
        closure = self.f['closures'][0]
        late = parsed(closure, available_at=link.evaluated_as_of.isoformat(), recorded_at=link.evaluated_as_of.isoformat())
        records = [late if r.record_id == closure.record_id else r for r in h.records]
        h2 = ObservedHistoryV2(schema_version='2.0.0', synthetic=True, kind='observed_history', patient_id=h.patient_id, records=records)
        changed = parsed(link, offered_closure_ref=exact_ref(late).model_dump())
        with self.assertRaisesRegex(ValueError, 'visible'):
            validate_outcome_link(h2, changed, verify_closure=lambda *_: [])
        missing = parsed(link, offered_closure_ref=None)
        with self.assertRaisesRegex(ValueError, 'requires_verified_closure'):
            validate_outcome_link(h, missing, verify_closure=lambda *_: [])
        bad_rating = link.model_dump(mode='json'); bad_rating['burden'][0]['type'] = 'patient_rated_burden'
        with self.assertRaises(ValueError):
            RECORD_ADAPTER_V2.validate_json(canonical(bad_rating))

    def test_delete_delivery_or_ledger_never_creates_zero(self):
        ledger = self.f['manifest']['partitions'][0]['stage_ledgers'][0]
        path = self.root / ledger['path']
        original = path.read_bytes()
        payload = json.loads(original); payload['event_refs'] = []
        path.write_bytes(canonical(payload))
        with self.assertRaisesRegex(ValueError, 'hash'):
            verify_export_v2(self.f['raw'], self.root, self.authority)
        path.write_bytes(original)
        path.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            verify_export_v2(self.f['raw'], self.root, self.authority)
        path.write_bytes(original)
        # Remove a delivered event from both history and raw replay while the
        # independently trusted ledger still binds the original event.
        h = self.f['history']
        offered = next(r for r in h.records if r.kind == 'delivery')
        short = ObservedHistoryV2(schema_version='2.0.0', synthetic=True, kind='observed_history', patient_id=h.patient_id, records=[r for r in h.records if r.record_id != offered.record_id])
        with self.assertRaisesRegex(ValueError, 'missing_exact_dependency'):
            resolve(short, self.f['closures'][0].stage_event_refs[0], {'delivery'})

    def test_report_and_delivery_correction_make_link_stale_without_redirection(self):
        h, link = self.f['history'], self.f['link']
        at = ORIGIN + timedelta(days=3)
        for original in [self.f['report'], next(r for r in h.records if r.kind == 'delivery')]:
            correction = parsed(original, record_id='later-' + original.kind, revision=2, supersedes=original.record_id, recorded_at=at.isoformat(), available_at=at.isoformat())
            updated = ObservedHistoryV2(schema_version='2.0.0', synthetic=True, kind='observed_history', patient_id=h.patient_id, records=[*h.records, correction])
            def stage(closure, cutoff):
                return [resolve(updated, r, {'delivery'}, cutoff=cutoff) for r in closure.stage_event_refs]
            self.assertEqual(outcome_as_known(updated, at, verify_closure=stage)[0]['status'], 'available')
            self.assertEqual(outcome_as_known(updated, at + timedelta(microseconds=1), verify_closure=stage)[0]['status'], 'stale')

    def test_wrong_report_window_patient_hash_and_preassessment_link(self):
        h, link = self.f['history'], self.f['link']
        for changes in [dict(window_id='other-window'), dict(reward={**link.reward.model_dump(), 'report_ref': dict(record_id=self.f['report'].record_id, payload_sha256='f' * 64)}), dict(assessment_at=(link.assessment_at - timedelta(days=1)).isoformat())]:
            with self.assertRaises(ValueError):
                validate_outcome_link(h, parsed(link, **changes), verify_closure=lambda *_: [])
        with self.assertRaises(ValueError):
            parsed(link, recorded_at=(link.assessment_at - timedelta(seconds=1)).isoformat())
        self.assertTrue(any(row['endpoint_status'] == 'not_yet_due' for row in self.f['coverage']['slots']))

    def test_full_private_key_process_day_namespace_registry_and_draw_flag(self):
        from contracts.dgp.truth import seed_words
        from contracts.runs.private import StreamKey
        from contracts.runs.private_v2 import SeedLedgerV2, validate_record_keys
        manifest = ObservedExportV2.model_validate_json(self.f['raw'])
        partition = manifest.partitions[0].model_copy(deep=True)
        keys = []
        for binding in partition.records:
            i = binding.identity
            args = dict(root_seed=20261020, protocol=i.protocol, phase=i.phase, namespace=i.namespace, scenario=i.cell_id, replicate=i.replicate, patient=i.patient_id, time_index=i.time_index, process=i.process, stream=i.substream)
            words = seed_words(**args)
            key = StreamKey.model_validate_json(canonical({**args, 'words': words, 'key_sha256': b''.join(w.to_bytes(4, 'little') for w in words).hex()}))
            binding.seed_key_sha256 = key.key_sha256
            if key.key_sha256 not in {k.key_sha256 for k in keys}:
                keys.append(key)
        ledger = SeedLedgerV2(schema_version='2.0.0', synthetic=True, kind='seed_ledger', contract_version='2.0.0', run_id=manifest.run_id, keys=keys)
        identity = partition.records[0].identity
        run = SimpleNamespace(run_id=manifest.run_id, bindings=manifest.bindings, phase='fixture', source_registry=identity.source_registry, transformation_registry=identity.transformation,
                              sources=[r.source.model_dump(exclude={'raw_sha256'}) for r in self.f['history'].records])
        self.assertTrue(validate_record_keys(run, partition, self.f['history'], ledger, self.f['schedule']))
        for field, value in [('process', 'wrong-process'), ('time_index', 85), ('namespace', 'truth'), ('protocol', 'wrong-protocol')]:
            bad = partition.model_copy(deep=True)
            selected = next(b for b in bad.records if b.record_id == self.f['decision'].record_id)
            setattr(selected.identity, field, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_record_keys(run, bad, self.f['history'], ledger, self.f['schedule'])

    def test_v2_scientific_validation_preserves_frozen_v1_body(self):
        source = Path('contracts/runs/private.py').read_text()
        expected = source[source.index('def validate_truth_response('):]
        expected = expected.replace('def validate_truth_response(request: TruthRequest, response: TruthResponse,', 'def validate_truth_response_v2(request: TruthRequestV2, response: TruthResponseV2,', 1).replace("response.request.version!='1.0.0'", "response.request.version!='2.0.0'", 1)
        source = Path('contracts/runs/truth_validation_v2.py').read_text()
        self.assertEqual(source[source.index('def validate_truth_response_v2('):], expected)

    def test_explicit_v2_private_request_response_dispatch_and_fixture_limit(self):
        from test_evaluator import EvaluatorContracts
        from contracts.runs.private import TruthRequest
        from contracts.runs.private_v2 import AuthorityV2, TruthRequestV2, TruthResponseV2, parse_private_artifact
        from contracts.runs.private_admission_v2 import verify_truth_v2
        helper = EvaluatorContracts()
        helper.setUp()
        try:
            old_request = TruthRequest.model_validate_json(canonical(helper.request(method='analytic')))
            data = old_request.model_dump(mode='json')
            data.update(schema_version='2.0.0', contract_version='2.0.0', id='v2-wire-request', run_id='v2-wire-fixture-only',
                        run_manifest=ref('v2-wire-fixture-only', digest='e' * 64), bindings=self.f['manifest']['bindings'])
            request = TruthRequestV2.model_validate_json(canonical(data))
            response_data = helper.response(old_request, status='pending')
            response_data.update(schema_version='2.0.0', contract_version='2.0.0', id='v2-wire-response', run_id=request.run_id,
                                 request=ref(request.id, digest=sha256(canonical(request.model_dump(mode='json')))), bindings=self.f['manifest']['bindings'])
            response = TruthResponseV2.model_validate_json(canonical(response_data))
            authority_data = helper.authority.model_dump(mode='json')
            authority_data.update(contract_version='2.0.0', run_id=request.run_id, manifest_sha256='e' * 64, bindings=self.f['manifest']['bindings'], producer_qualification=None)
            authority = AuthorityV2.model_validate_json(canonical(authority_data))
            raw_request, raw_response = canonical(request.model_dump(mode='json')), canonical(response.model_dump(mode='json'))
            parsed_request, parsed_response = verify_truth_v2(raw_request, raw_response, helper.root,
                    request_sha256=sha256(raw_request), response_sha256=sha256(raw_response), evaluator=authority)
            self.assertEqual(parsed_response.status, 'pending')
            self.assertEqual(parse_private_artifact(raw_request), parsed_request)
            with self.assertRaises(ValueError):
                TruthRequest.model_validate_json(raw_request)
            authority_data['allow_contract_fixture'] = False
            with self.assertRaisesRegex(ValueError, 'fixture'):
                verify_truth_v2(raw_request, raw_response, helper.root, request_sha256=sha256(raw_request), response_sha256=sha256(raw_response), evaluator=AuthorityV2.model_validate_json(canonical(authority_data)))
        finally:
            helper.tearDown()


if __name__ == '__main__':
    unittest.main()
