"""Deterministic UNIT checks; these are not recovery/calibration/study evidence."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
import unittest

import numpy as np
from numpy.testing import assert_allclose
from pydantic import TypeAdapter, ValidationError
from scipy.stats import t

from contracts.domain.analysis import reference, sha
from contracts.domain.protocol_analysis import ReducedRecord
from methods.support.data import PublicHistory, DecisionRow, FeatureData, InvalidInput, build_features, design
from methods.support.wcls import fit, sensitivity

ORIGIN = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
POLICY = reference('UNIT-support-policy', 'unit fixture; no activation')
SEED = 'fit/wcls-unused-provenance/UNIT-deterministic-no-RNG'
ADAPTER = TypeAdapter(ReducedRecord)


def record(kind, name, at, **fields):
    return ADAPTER.validate_python(dict(kind=kind, record_id=name, patient_id='UNIT-P',
        record_schema='2.0.0', event_at=at, recorded_at=at, available_at=at,
        lineage_id=name, revision=1, supersedes=None, duplicate_of=None, record_status='active', **fields))


def ref(record):
    return dict(record_id=record.record_id, projection_sha256=sha(record.model_dump(mode='json')))


def source_history(*, day=7, status='observed', prior=True, missing_prior=False, mode='mrt',
                   probability=.5, malformed_missing_context=False, late_prior=False, pending=False,
                   delivery_offsets=(-7, -6, -1), availability='randomized', ordinary=False,
                   bad_report_time=False, bad_link=False):
    """Actual reduced public types, no generator/truth/store imports."""
    at = ORIGIN+timedelta(days=day)
    records, context = [], []
    if prior:
        quality = record('daily_report', 'prior', at-timedelta(days=2, minutes=1),
                         sleep_quality=3., missingness='observed')
        if late_prior:
            quality = quality.model_copy(update=dict(recorded_at=at, available_at=at))
        records.append(quality)
        if not late_prior:
            context.append(ref(quality))
    if missing_prior:
        records.append(record('daily_report', 'recent-missing', at-timedelta(days=1, minutes=1),
                              sleep_quality=None, missingness='missing'))
    # Deliveries on nights t-6 and t-1 count; night t-7 is excluded.
    for index, offset in enumerate(delivery_offsets):
        when = at+timedelta(days=offset, hours=8)
        assigned = record('assignment', f'old-a{index}', when-timedelta(hours=8),
            decision_id='old-decision', approval_id='old-approval', option='support_prompt',
            experimental=True, component='mrt_bandit', probability=.5, support_policy=POLICY,
            patient_blinded=False, clinician_blinded=False, clinician_override=None, override_reason=None)
        delivery = record('delivery', f'delivery{index}', when, assignment_id=assigned.record_id,
                          option='support_prompt', stage='delivered', adherence=None, rescue=False, protocol_deviations=[])
        records.extend([assigned, delivery])
        if -6 <= offset < 0:
            context.append(ref(delivery))
    snapshot = record('decision_snapshot', 'snapshot', at, cutoff=at, eligibility=[],
        workflow=dict(clinical='treatment_active', learning='support_active', data_readiness='ready',
                      hold_reasons=[], support_policy=POLICY, support_mode='mrt'))
    approval = record('approval', 'approval', at, decision_id=snapshot.record_id, option=None,
                      permitted_options=['support_prompt', 'no_prompt'], purpose='randomization_protocol')
    assignment = record('assignment', 'assignment', at, decision_id=snapshot.record_id, approval_id=approval.record_id,
        option='support_prompt', experimental=not ordinary, component='mrt_bandit', probability=probability,
        support_policy=POLICY, patient_blinded=False, clinician_blinded=False, clinician_override=None, override_reason=None)
    assessment = at+timedelta(days=1, minutes=-1)
    if malformed_missing_context:
        context = []
    decision = record('support_decision', 'support', at+timedelta(seconds=1),
        decision_snapshot=ref(snapshot), decision_index=day, cutoff=at, context=context,
        context_projection_sha256=sha(context), policy=POLICY, mode=mode,
        eligibility=[dict(action=a, status='eligible', reasons=[]) for a in ('support_prompt', 'no_prompt')],
        policy_constraint=dict(allowed_actions=['support_prompt', 'no_prompt'], reason='unrestricted', snapshot_ref=None),
        availability=availability, unavailable_reasons=[], probabilities=dict(support_prompt=probability, no_prompt=1-probability),
        assignment_id=assignment.record_id, distribution_persisted_at=at, execution_receipt_id='UNIT-receipt',
        outcome_window=dict(id='window', starts_at=at, ends_at=assessment, assessment_at=assessment,
            timezone='UTC', local_date=at.date(), endpoint_definition=reference('UNIT-quality', 'next-morning quality')),
        outcome_link_id='outcome').model_copy(update=dict(event_at=at))
    report = record('daily_report', 'reward', assessment-timedelta(minutes=1) if bad_report_time else assessment,
                    sleep_quality=6. if status == 'observed' else None,
                    missingness='observed' if status == 'observed' else 'missing')
    publication = assessment+timedelta(seconds=10)
    outcome = record('support_outcome_link', 'outcome', publication, support_decision=ref(decision),
        assignment_ref=ref(assignment), window_id='wrong-window' if bad_link else 'window', assessment_at=assessment, evaluated_as_of=publication,
        reward=dict(status='pending' if pending else status, report_ref=ref(report) if status == 'observed' and not pending else None,
            field='sleep_quality', unit='quality_points', reason=None if status == 'observed' and not pending else 'UNIT-status',
            evidence_refs=[] if status == 'observed' and not pending else [ref(report)], definition_refs=[]),
        burden=[dict(definition=reference('UNIT-burden', 'not used as a feature'), type=kind, unit='count',
                     status='pending', value=None, source_refs=[])
                for kind in ('offered_prompt_count', 'delivered_prompt_count')],
        offered_closure_ref=None, delivered_closure_ref=None).model_copy(update=dict(event_at=assessment))
    return PublicHistory('UNIT-P', ORIGIN, at+timedelta(days=2, hours=3),
                         tuple([*records, snapshot, approval, assignment, decision, report, outcome]))


def numerical_data(effect=.6, groups=12):
    """Full-rank artificial controls and deterministic residuals, not a DGP study."""
    rows = []
    for patient in range(groups):
        for night in range(1, 13):
            missing = float(night == 1 or (patient % 3 == 0 and night == 2))
            quality = 7. if missing else 4.+((patient+night) % 7)/3
            prompts = (patient+2*night) % 4
            controls = (1., quality, missing, float(prompts), night/84)
            action = int((patient+night+(night//3)) % 2)
            reward = 3.+.2*quality+.15*missing-.1*prompts+.2*night/84+effect*(action-.5)+.08*math.sin(patient+2*night)
            rows.append(DecisionRow(str(patient), f'UNIT-{patient}-{night}', night, controls, action, .5, reward, ()))
    return FeatureData(tuple(rows), ORIGIN+timedelta(days=14), sha('UNIT-only-artificial-numerical-input'), {})


class PublicFeatureTests(unittest.TestCase):
    def test_prior_available_and_public_six_nights(self):
        data = build_features([source_history(missing_prior=True)])
        self.assertEqual(data.rows[0].controls, (1., 3., 0., 2., 8/84))
        self.assertEqual(data.rows[0].reward, 6.)
        self.assertEqual(data.rows[0].source_ids, ('delivery1', 'delivery2', 'prior'))
        with_current_delivery = build_features([source_history(delivery_offsets=(-7, -6, -1, 0))])
        self.assertEqual(with_current_delivery.rows[0].controls[3], 2.)

    def test_no_history_and_equal_time_report_unavailable(self):
        for history in (source_history(prior=False), source_history(late_prior=True)):
            self.assertEqual(build_features([history]).rows[0].controls[1:3], (7., 1.))
        first = build_features([source_history(day=0, prior=False, delivery_offsets=())]).rows[0]
        self.assertEqual(first.night, 1)
        self.assertEqual(first.controls, (1., 7., 1., 0., 1/84))

    def test_record_order_and_irregular_common_cutoff(self):
        history = source_history()
        first = build_features([history])
        second = build_features([replace(history, records=tuple(reversed(history.records)))])
        self.assertEqual(first, second)
        # The source adapter accepts an irregular as-of cutoff; decision nights
        # still align with the public origin and no future quality is consumed.
        self.assertEqual(first.cutoff.hour, 15)

    def test_missing_never_zero_and_pending_excluded(self):
        data = build_features([source_history(status='missing')])
        self.assertEqual(len(data.rows), 1)
        self.assertIsNone(data.rows[0].reward)
        self.assertEqual(data.observed, ())
        self.assertEqual(build_features([source_history(pending=True)]).rows, ())
        self.assertEqual(build_features([source_history(status='undefined')]).rows, ())
        self.assertEqual(build_features([source_history(mode='adaptive')]).rows, ())
        self.assertEqual(build_features([source_history(mode='fixed')]).rows, ())
        self.assertEqual(build_features([source_history(availability='deterministic')]).rows, ())
        self.assertEqual(build_features([source_history(availability='unavailable')]).rows, ())

    def test_assignment_linkage_and_causal_clock_negatives(self):
        for kwargs, message in ((dict(ordinary=True), 'ordinary/unrandomized'),
                                (dict(bad_report_time=True), 'report/assessment'),
                                (dict(bad_link=True), 'linkage/clock')):
            with self.assertRaisesRegex(InvalidInput, message):
                build_features([source_history(**kwargs)])
        h = source_history()
        outcome = next(r for r in h.records if r.kind == 'support_outcome_link')
        # An assessment exactly at the common cutoff is still incomplete.
        before_publication = tuple(r for r in h.records if r.available_at < outcome.assessment_at)
        not_completed = build_features([replace(h, cutoff=outcome.assessment_at, records=before_publication)])
        self.assertEqual(not_completed.rows, ())
        self.assertEqual(not_completed.excluded['incomplete_window'], 1)

    def test_propensity_and_source_negatives(self):
        with self.assertRaisesRegex(InvalidInput, 'exact recorded'):
            build_features([source_history(probability=.6)])
        with self.assertRaisesRegex(InvalidInput, 'feature source absent'):
            build_features([source_history(malformed_missing_context=True)])
        h = source_history()
        with self.assertRaisesRegex(InvalidInput, 'duplicate public'):
            build_features([replace(h, records=(*h.records, h.records[0]))])
        with self.assertRaisesRegex(InvalidInput, 'unavailable'):
            build_features([replace(h, cutoff=next(r.available_at for r in h.records if r.kind == 'support_outcome_link'))])
        payload = h.records[0].model_dump() | {'private_habit': 1.}
        with self.assertRaises(ValidationError):
            ADAPTER.validate_python(payload)

    def test_invalid_missing_context_withholds_only_sensitivity(self):
        data = build_features([source_history(status='missing', malformed_missing_context=True)])
        self.assertIn('feature source absent', data.sensitivity_reason)
        missing = build_features([source_history(status='missing', bad_link=True)])
        self.assertIn('linkage/clock', missing.sensitivity_reason)

    def test_exact_reduced_hash_binding(self):
        h = source_history()
        changed = tuple(r.model_copy(update=dict(sleep_quality=4.)) if r.record_id == 'prior' else r for r in h.records)
        with self.assertRaisesRegex(InvalidInput, 'changed public reduced reference'):
            build_features([replace(h, records=changed)])
        # Delivery adherence does not supply n_t; the public delivered stage does.
        h = source_history()
        changed = tuple(r.model_copy(update=dict(adherence=0.)) if r.kind == 'delivery' else r for r in h.records)
        decision = next(r for r in changed if r.kind == 'support_decision')
        by_id = {r.record_id: r for r in changed}
        decision = decision.model_copy(update=dict(context=[type(v).model_validate(ref(by_id[v.record_id])) for v in decision.context]))
        by_id[decision.record_id] = decision
        outcome = by_id['outcome'].model_copy(update=dict(support_decision=type(by_id['outcome'].support_decision).model_validate(ref(decision))))
        by_id['outcome'] = outcome
        self.assertEqual(build_features([replace(h, records=tuple(by_id.values()))]).rows[0].controls[3], 2.)


class WCLSTests(unittest.TestCase):
    def test_independent_normal_equations_cluster_sandwich_and_t(self):
        for effect in (0., .6):
            data = numerical_data(effect)
            result = fit(data, provenance_seed=SEED)
            self.assertEqual(result.status, 'estimated', result.reasons)
            # Independent normal equations and cluster score outer products.
            x = np.asarray([list(r.controls)+[r.action-.5] for r in data.rows])
            y = np.asarray([r.reward for r in data.rows])
            w = np.asarray([.5/r.probability for r in data.rows])
            bread = np.linalg.inv(x.T@(w[:, None]*x))
            coefficients = bread@(x.T@(w*y))
            residual = y-x@coefficients
            scores = np.array([np.sum((w*residual)[:, None]*x*np.array([r.patient_id == str(i) for r in data.rows])[:, None], axis=0)
                               for i in range(12)])
            covariance = bread@(scores.T@scores)@bread*(12/11)*(len(y)-1)/(len(y)-6)
            assert_allclose(result.coefficients, coefficients, rtol=1e-11, atol=1e-11)
            assert_allclose(result.covariance, covariance, rtol=1e-10, atol=1e-11)
            expected_se = np.sqrt(covariance[-1, -1])
            assert_allclose(result.interval, coefficients[-1]+np.array([-1, 1])*t.ppf(.975, 11)*expected_se, rtol=1e-10)
            self.assertEqual(result.df, 11)
            self.assertLess(abs(result.estimate-effect), .03)
            self.assertFalse(result.identity['seed_used'])

    def test_order_and_reward_translation(self):
        data = numerical_data()
        result = fit(data, provenance_seed=SEED)
        reverse = fit(replace(data, rows=tuple(reversed(data.rows))), provenance_seed=SEED)
        shifted = fit(replace(data, rows=tuple(replace(r, reward=r.reward+1.) for r in data.rows)), provenance_seed=SEED)
        assert_allclose(result.estimate, reverse.estimate, atol=1e-12)
        assert_allclose(result.interval, shifted.interval, atol=1e-12)

    def test_rank_clusters_propensity_and_seed_reject(self):
        data = numerical_data()
        singular = replace(data, rows=tuple(replace(r, controls=(*r.controls[:2], 0., *r.controls[3:])) for r in data.rows))
        self.assertIn('rank deficient', fit(singular, provenance_seed=SEED).reasons[0])
        self.assertIn('G<8', fit(numerical_data(groups=7), provenance_seed=SEED).reasons[0])
        self.assertEqual(fit(numerical_data(groups=8), provenance_seed=SEED).status, 'estimated')
        corrupt = replace(data, rows=(replace(data.rows[0], probability=.6), *data.rows[1:]))
        self.assertEqual(fit(corrupt, provenance_seed=SEED).status, 'abstained')
        self.assertEqual(fit(data, provenance_seed='wrong').status, 'abstained')
        small = fit(replace(data, rows=data.rows[:6]), provenance_seed=SEED)
        self.assertEqual(small.status, 'abstained')
        self.assertTrue(any('N<=K' in reason for reason in small.reasons))

    def test_missing_contexts_and_sensitivity_failure_preserve_primary(self):
        data = numerical_data()
        baseline = fit(data, provenance_seed=SEED)
        with_missing = replace(data, rows=(*data.rows, replace(data.rows[0], decision_id='UNIT-missing', reward=None)))
        result = fit(with_missing, provenance_seed=SEED)
        self.assertEqual(result.coefficients, baseline.coefficients)
        self.assertEqual(result.interval, baseline.interval)
        self.assertEqual(result.counts['missing'], 1)
        incomplete = fit(replace(with_missing, sensitivity_reason='UNIT missing-only bad linkage'), provenance_seed=SEED)
        self.assertEqual(incomplete.status, 'estimated')
        self.assertEqual(incomplete.interval, baseline.interval)
        self.assertEqual(incomplete.sensitivity, ())


class SensitivityTests(unittest.TestCase):
    def test_nine_interior_cells_and_exact_anchor(self):
        cells = sensitivity([5., 0., 0., 0., 0., .6], [[1., 7., 0., 0., .2]])
        self.assertEqual(len(cells), 9)
        for cell in cells:
            assert_allclose(cell.shift, .1*(cell.delta1-cell.delta0), atol=1e-15)
            if cell.delta0 == cell.delta1 == 0:
                self.assertEqual(cell.estimate, .6)
        assert_allclose([min(c.shift for c in cells), max(c.shift for c in cells)], [-.1, .1])

    def test_boundary_orientation_and_equal_decision_averaging(self):
        # m0=9.5,m1=10 at first context: common +.5 gives -.05.
        coefficients = [9.75, 0., 0., 0., -5., .5]
        contexts = [[1, 7, 0, 0, 0], [1, 7, 0, 0, 1], [1, 7, 0, 0, 1]]
        cells = sensitivity(coefficients, contexts)
        common = next(c for c in cells if c.delta0 == c.delta1 == .5)
        assert_allclose(common.shift, -.05/3, atol=1e-15)
        negative = next(c for c in cells if c.delta0 == .5 and c.delta1 == -.5)
        positive = next(c for c in cells if c.delta0 == -.5 and c.delta1 == .5)
        self.assertLess(negative.shift, 0)
        self.assertGreater(positive.shift, 0)
        self.assertNotEqual(abs(negative.shift), abs(positive.shift))
        self.assertTrue(all(c.direction == 'positive' for c in cells))

    def test_missing_context_affects_average_without_changing_primary(self):
        data = numerical_data()
        # This missing context changes the finite sensitivity average only.
        missing = replace(data.rows[0], decision_id='UNIT-missing-boundary', controls=(1., 10., 0., 0., 1.), reward=None)
        augmented = replace(data, rows=(*data.rows, missing))
        baseline, result = fit(data, provenance_seed=SEED), fit(augmented, provenance_seed=SEED)
        self.assertEqual(result.coefficients, baseline.coefficients)
        expected = sensitivity(result.coefficients, [r.controls for r in augmented.rows])
        self.assertEqual(result.sensitivity, expected)


if __name__ == '__main__':
    unittest.main()
