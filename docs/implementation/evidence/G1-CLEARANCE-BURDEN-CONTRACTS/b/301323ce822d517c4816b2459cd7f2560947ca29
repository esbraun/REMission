"""Discriminating OBS2 value, clock, exact-reference and hold-chain cases."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'run_contracts'))
from observed_v2_fixtures import build, canonical, ORIGIN, ref
from contracts.domain.evidence_v2 import exact_ref, projection_hash, reconstruct_hold, resolve, validate_hold, validate_support_decision
from contracts.domain.observed_v2 import ObservedHistoryV2, RECORD_ADAPTER_V2
from contracts.domain.entities import DailyReport
from contracts.runs.common import sha256


def parsed(data, **updates):
    data = deepcopy(data.model_dump(mode='json') if hasattr(data, 'model_dump') else data)
    data.update(updates)
    data['source']['raw_sha256'] = sha256(canonical({k: v for k, v in data.items() if k != 'source'}))
    return RECORD_ADAPTER_V2.validate_json(canonical(data))


def history_with(history, *records):
    return ObservedHistoryV2(schema_version='2.0.0', synthetic=True, kind='observed_history', patient_id=history.patient_id, records=[*history.records, *records])


class ObservedV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = build(Path(self.tmp.name), hold=True)
        self.history = self.fixture['history']

    def tearDown(self):
        self.tmp.cleanup()

    def test_signed_unbounded_single_diary_and_version_dispatch(self):
        report = self.fixture['report']
        for value in [-1e12, -25.0, 0.0, 480.0, 1e12]:
            with self.subTest(value=value):
                self.assertEqual(parsed(report, diary_sleep_minutes=value).diary_sleep_minutes, value)
        for value in [float('nan'), float('inf'), -float('inf')]:
            with self.assertRaises(ValueError):
                data = report.model_dump(mode='json'); data['diary_sleep_minutes'] = value
                RECORD_ADAPTER_V2.validate_python(data)
        with self.assertRaises(ValueError):
            parsed(report, missingness='missing')
        old = report.model_dump(mode='json'); old['schema_version'] = '1.0.0'
        with self.assertRaises(ValueError):
            DailyReport.model_validate_json(canonical(old))
        with self.assertRaises(ValueError):
            parsed(report, schema_version='3.0.0')
        self.assertEqual(sum(r.kind == 'daily_report' for r in self.history.project(ORIGIN + timedelta(days=2)).records), 1)
        self.assertFalse(any(r.kind == 'observation' for r in self.history.records))

    def test_complete_vectors_and_exact_selected_propensity(self):
        d = self.fixture['decision']
        self.assertEqual(validate_support_decision(self.history, d), 'validated')
        excluded = [dict(action=a, status='excluded', reasons=['hold']) for a in ['support_prompt', 'no_prompt']]
        unavailable = parsed(d, availability='unavailable', eligibility=excluded, probabilities={'support_prompt': 0.0, 'no_prompt': 0.0}, assignment_id=None, unavailable_reasons=['hold'])
        self.assertEqual(unavailable.availability, 'unavailable')
        for changes in [dict(probabilities={'support_prompt': 0.0}), dict(probabilities={'support_prompt': .2, 'no_prompt': .8}),
                        dict(availability='unavailable', assignment_id=None, unavailable_reasons=['hold']),
                        dict(probability_tolerance=1e-3)]:
            with self.assertRaises(ValueError):
                parsed(d, **changes)
        eligible = [dict(action=a, status='eligible', reasons=[]) for a in ['support_prompt', 'no_prompt']]
        randomized = parsed(d, availability='randomized', eligibility=eligible, probabilities={'support_prompt': .1, 'no_prompt': .9})
        for p in [.099, .901]:
            with self.assertRaises(ValueError):
                parsed(randomized, probabilities={'support_prompt': p, 'no_prompt': 1 - p})
        # Independent selected-propensity comparison, beyond per-record vectors.
        snapshot = resolve(self.history, d.decision_snapshot)
        new_snapshot = parsed(snapshot, record_id='random-snapshot', lineage_id='random-snapshot', eligibility=eligible)
        assignment = next(r for r in self.history.records if r.kind == 'assignment')
        a = parsed(assignment, record_id='random-assignment', lineage_id='random-assignment', decision_id=new_snapshot.record_id,
                   approval_id='random-approval',
                   experimental=True, component='mrt_bandit', probability=.8,
                   seed=dict(namespace='assignment', protocol='remission-g1-v1', scenario='S23', replicate=0, patient='SYN-02', time_index=0, process='support_assignment'))
        random_d = parsed(randomized, decision_snapshot=exact_ref(new_snapshot).model_dump(), assignment_id=a.record_id)
        old_approval = next(r for r in self.history.records if r.kind == 'approval')
        approval = parsed(old_approval, record_id='random-approval', lineage_id='random-approval', decision_id=new_snapshot.record_id, purpose='randomization_protocol', option=None, permitted_options=['support_prompt', 'no_prompt'])
        h = history_with(self.history, new_snapshot, approval, a)
        with self.assertRaisesRegex(ValueError, 'selected_propensity'):
            validate_support_decision(h, random_d)

    def test_strict_knowledge_cutoff_and_stale_predecessor(self):
        baseline, entry = self.fixture['hold_records']
        for cutoff, state in [(entry.available_at - timedelta(microseconds=1), 'baseline'), (entry.available_at, 'baseline'), (entry.available_at + timedelta(microseconds=1), 'held')]:
            self.assertEqual(reconstruct_hold(self.history, cutoff)[-1]['interval_status'], state)
        at = ORIGIN + timedelta(days=2)
        correction = parsed(baseline, record_id='corrected-baseline', revision=2, supersedes=baseline.record_id, recorded_at=at.isoformat(), available_at=at.isoformat(), reason='corrected historical explanation')
        h = history_with(self.history, correction)
        self.assertEqual(reconstruct_hold(h, at)[-1]['interval_status'], 'held')
        self.assertEqual(reconstruct_hold(h, at + timedelta(microseconds=1))[-1]['interval_status'], 'unresolved')
        repaired = parsed(entry, record_id='rebound-entry', revision=2, supersedes=entry.record_id, recorded_at=(at + timedelta(hours=1)).isoformat(), available_at=(at + timedelta(hours=1)).isoformat(), predecessor_bundle_ref=exact_ref(correction).model_dump())
        restored = history_with(h, repaired)
        self.assertEqual(reconstruct_hold(restored, at + timedelta(hours=2))[-1]['interval_status'], 'held')
        tombstone = parsed(correction, record_id='retracted-baseline', revision=3, supersedes=correction.record_id, record_status='retracted', recorded_at=(at + timedelta(hours=3)).isoformat(), available_at=(at + timedelta(hours=3)).isoformat())
        self.assertEqual(reconstruct_hold(history_with(restored, tombstone), at + timedelta(hours=4))[-1]['interval_status'], 'unresolved')

    def test_later_review_never_rewrites_causal_context(self):
        _, entry = self.fixture['hold_records']
        trigger = resolve(self.history, entry.trigger_refs[0])
        at = ORIGIN + timedelta(days=2, hours=8)
        review = parsed(trigger, record_id='tomorrow-review', lineage_id='tomorrow-review', event_at=at.isoformat(), assessed_at=at.isoformat(), recorded_at=at.isoformat(), available_at=at.isoformat(), evidence_type='review', review_result='requirements_satisfied')
        h = history_with(self.history, review)
        correction = parsed(entry, record_id='entry-with-review', revision=2, supersedes=entry.record_id, recorded_at=(at + timedelta(hours=1)).isoformat(), available_at=(at + timedelta(hours=1)).isoformat(), review_refs=[exact_ref(review).model_dump()], evidence_roles=[*[e.model_dump() for e in entry.evidence_roles], dict(ref=exact_ref(review).model_dump(), role='later_review')])
        self.assertEqual(correction.context_projection_sha256, entry.context_projection_sha256)
        self.assertEqual(validate_hold(history_with(h, correction), correction).workflow.clinical, 'clinical_hold')
        bad = correction.model_dump(mode='json'); bad['evidence_roles'][-1]['role'] = 'causal_context'
        with self.assertRaises(ValueError):
            RECORD_ADAPTER_V2.validate_json(canonical(bad))
        # Later documentary material cannot become an earlier contemporaneous trigger.
        bad = parsed(correction, review_refs=[], trigger_refs=[exact_ref(review).model_dump()], evidence_roles=[dict(ref=exact_ref(review).model_dump(), role='transition_trigger')])
        with self.assertRaisesRegex(ValueError, 'retrospective_trigger'):
            validate_hold(history_with(h, bad), bad)

    def test_hold_owner_hash_follow_up_and_missing_baseline_denial(self):
        _, entry = self.fixture['hold_records']
        for changed in [dict(owner_id='foreign-owner'), dict(snapshot_ref=dict(record_id=entry.snapshot_ref.record_id, payload_sha256='f' * 64)), dict(follow_up_refs=[dict(record_id='missing-task', payload_sha256='0' * 64)])]:
            with self.assertRaises(ValueError):
                validate_hold(self.history, parsed(entry, **changed))
        incomplete = self.history.model_copy(deep=True)
        incomplete.records = [r for r in incomplete.records if r.record_id != self.fixture['hold_records'][0].record_id]
        self.assertEqual(reconstruct_hold(incomplete, ORIGIN + timedelta(days=2))[-1]['interval_status'], 'unresolved')

    def test_cross_version_correction_is_rejected(self):
        report = self.fixture['report']
        correction = parsed(report, schema_version='1.0.0', diary_sleep_minutes=360.0, record_id='cross-version', revision=2, supersedes=report.record_id)
        with self.assertRaisesRegex(ValueError, 'cross-version'):
            history_with(self.history, correction)

    def test_explicit_reviewed_resolution_and_same_time_causal_sequence(self):
        baseline, entry = self.fixture['hold_records']
        old_snapshot = resolve(self.history, entry.snapshot_ref)
        trigger = resolve(self.history, entry.trigger_refs[0])
        old_task = resolve(self.history, entry.follow_up_refs[0])
        reviewed_at = ORIGIN + timedelta(days=2, hours=8)
        assessment_at = reviewed_at + timedelta(hours=1)
        review = parsed(trigger, record_id='documented-clearance', lineage_id='documented-clearance', event_at=reviewed_at.isoformat(), assessed_at=reviewed_at.isoformat(), recorded_at=reviewed_at.isoformat(), available_at=reviewed_at.isoformat(), evidence_type='clearance', review_result='requirements_satisfied', rule=ref('fixture-explicit-script-only'), follow_up_refs=[])
        workflow = old_snapshot.workflow.model_dump(); workflow['clinical'] = 'assessment'; workflow['hold_reasons'] = []
        snapshot = parsed(old_snapshot, record_id='reviewed-assessment', lineage_id='reviewed-assessment', event_at=assessment_at.isoformat(), recorded_at=assessment_at.isoformat(), available_at=assessment_at.isoformat(), cutoff=assessment_at.isoformat(), patient_version=4, state_version=4, eligibility_version=4, workflow=workflow)
        task = parsed(old_task, record_id='assessment-task', lineage_id='assessment-task', event_at=assessment_at.isoformat(), recorded_at=assessment_at.isoformat(), available_at=assessment_at.isoformat(), due_at=(assessment_at + timedelta(days=1)).isoformat())
        h = history_with(self.history, review, snapshot, task)
        bundle = parsed(entry, record_id='resolved-bundle', lineage_id='resolved-bundle', transition_sequence=2, transition_type='resolve_to_assessment', event_at=assessment_at.isoformat(), effective_at=assessment_at.isoformat(), recorded_at=assessment_at.isoformat(), available_at=assessment_at.isoformat(), snapshot_ref=exact_ref(snapshot).model_dump(), predecessor_bundle_ref=exact_ref(entry).model_dump(), predecessor_snapshot_ref=entry.snapshot_ref.model_dump(), reason_codes=[], trigger_refs=[], blocked_actions=[], context_cutoff=assessment_at.isoformat(), context_projection_sha256=projection_hash(h, assessment_at), follow_up_refs=[exact_ref(task).model_dump()], required_reviews=[dict(requirement_id='required-review', definition=review.requirement.model_dump(), responsible_role=review.actor_role, status='satisfied', evidence_refs=[exact_ref(review).model_dump()])], review_refs=[exact_ref(review).model_dump()], clearance=dict(status='documented', rule=review.rule.model_dump(), evidence_refs=[exact_ref(review).model_dump()], assessment_snapshot_ref=exact_ref(snapshot).model_dump()), evidence_roles=[dict(ref=exact_ref(review).model_dump(), role='later_review')])
        resolved = history_with(h, bundle)
        self.assertEqual(reconstruct_hold(resolved, assessment_at + timedelta(seconds=1))[-1]['interval_status'], 'assessment')
        with self.assertRaises(ValueError):
            parsed(bundle, clearance=dict(status='pending', rule=None, evidence_refs=[], assessment_snapshot_ref=None))
        # Two equal-time transitions retain sequence/state order, never ID order.
        same_snapshot = parsed(old_snapshot, record_id='same-time-snapshot', lineage_id='same-time-snapshot', patient_version=4, state_version=4, eligibility_version=4)
        same = parsed(entry, record_id='aaa-change-reason', lineage_id='aaa-change-reason', transition_sequence=2, transition_type='change_reason', predecessor_bundle_ref=exact_ref(entry).model_dump(), predecessor_snapshot_ref=entry.snapshot_ref.model_dump(), snapshot_ref=exact_ref(same_snapshot).model_dump())
        equal_history = history_with(self.history, same_snapshot, same)
        intervals = reconstruct_hold(equal_history, entry.available_at + timedelta(seconds=1))
        self.assertEqual(intervals[-1]['interval_status'], 'held')
        self.assertEqual(intervals[-2]['starts_at'], intervals[-2]['ends_at'])


if __name__ == '__main__':
    unittest.main()
