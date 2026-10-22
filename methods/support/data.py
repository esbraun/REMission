"""Public reduced-record features for the accepted S1 MCAR excursion analysis.

The caller supplies active as-of-cutoff public records, normally from the existing
ProtocolHistory. This small input view is not an event store or wire contract.
Private truth, adherence, ISI and evaluator inputs have no feature path here.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

import numpy as np
from pydantic import TypeAdapter

from contracts.domain.analysis import sha
from contracts.domain.protocol_analysis import ReducedRecord, nested_refs


class InvalidInput(ValueError):
    """A malformed required public input; never a silently removed row."""


@dataclass(frozen=True)
class PublicHistory:
    patient_id: str
    origin: datetime
    cutoff: datetime
    records: tuple[ReducedRecord, ...]


@dataclass(frozen=True)
class DecisionRow:
    patient_id: str
    decision_id: str
    night: int
    controls: tuple[float, ...]
    action: int
    probability: float
    reward: float | None
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class FeatureData:
    rows: tuple[DecisionRow, ...]
    cutoff: datetime
    history_sha256: str
    excluded: dict[str, int]
    sensitivity_reason: str | None = None

    @property
    def observed(self):
        return tuple(row for row in self.rows if row.reward is not None)


def _require(condition, reason):
    if not condition:
        raise InvalidInput(reason)


def _aware(value):
    return value.tzinfo is not None and value.utcoffset() is not None


def _row(history, decision, active):
    origin, at = history.origin, decision.cutoff
    day = (at-origin).total_seconds()/86400
    _require(day == int(day) and 0 <= day < 84, 'decision must be public-origin noon for night1..84')
    _require(decision.event_at == at == decision.outcome_window.starts_at, 'decision/window start mismatch')
    _require(decision.outcome_window.assessment_at == origin+timedelta(days=int(day)+1, minutes=-1),
             'next-morning assessment mismatch')
    _require(decision.outcome_window.ends_at == decision.outcome_window.assessment_at,
             'outcome window end mismatch')
    _require(decision.distribution_persisted_at >= at, 'distribution precedes decision')
    _require(decision.distribution_persisted_at <= decision.recorded_at, 'distribution not persisted before publication')
    for ref in nested_refs(decision):
        _require(ref.record_id in active and sha(active[ref.record_id].model_dump(mode='json')) == ref.projection_sha256,
                 'unresolved/changed public reduced reference')
    _require(set(decision.probabilities) == {'support_prompt', 'no_prompt'}
             and all(decision.probabilities[a] == .5 for a in decision.probabilities),
             'S1 requires exact recorded final probability .5 for both actions')
    _require({e.action for e in decision.eligibility if e.status == 'eligible'} == {'support_prompt', 'no_prompt'}
             and len(decision.eligibility) == 2, 'S1 requires both eligible actions')
    _require(set(decision.policy_constraint.allowed_actions) == {'support_prompt', 'no_prompt'}, 'S1 policy constraint excludes action')
    assignment = active.get(decision.assignment_id)
    _require(assignment is not None and assignment.kind == 'assignment', 'missing S1 assignment')
    _require(assignment.option in ('support_prompt', 'no_prompt') and assignment.experimental
             and assignment.component == 'mrt_bandit' and assignment.probability == .5
             and assignment.clinician_override is None and assignment.override_reason is None,
             'ordinary/unrandomized or inconsistent S1 assignment')
    _require(assignment.decision_id == decision.decision_snapshot.record_id
             and assignment.support_policy == decision.policy, 'assignment decision/policy mismatch')
    snapshot = active.get(assignment.decision_id)
    approval = active.get(assignment.approval_id)
    _require(snapshot is not None and snapshot.kind == 'decision_snapshot'
             and snapshot.cutoff == at and snapshot.available_at <= at
             and snapshot.workflow.clinical != 'clinical_hold' and not snapshot.workflow.hold_reasons,
             'missing/unavailable/held decision snapshot')
    _require(approval is not None and approval.kind == 'approval' and approval.purpose == 'randomization_protocol'
             and approval.decision_id == snapshot.record_id and approval.available_at <= assignment.event_at
             and set(approval.permitted_options) == {'support_prompt', 'no_prompt'},
             'approved randomized binary support envelope required')
    _require(decision.distribution_persisted_at <= assignment.event_at, 'assignment precedes persisted final distribution')
    _require(decision.available_at < decision.outcome_window.assessment_at
             and assignment.available_at < decision.outcome_window.assessment_at,
             'decision and assignment must be published before the outcome')
    context_ids = {ref.record_id for ref in decision.context}
    _require(len(context_ids) == len(decision.context), 'duplicate predecision context')
    _require(all(active[r].available_at < at for r in context_ids), 'unavailable predecision context')
    # A later correction can hide an earlier as-known value in an active-only
    # export. Refuse that unsupported reconstruction rather than invent history.
    _require(not any(r.kind == 'daily_report' and r.event_at < at <= r.available_at and r.supersedes
                     for r in active.values()), 'predecision report revision unavailable in active-only view')
    prior = [r for r in active.values() if r.kind == 'daily_report' and r.event_at < at
             and r.available_at < at and r.missingness == 'observed']
    previous = max(prior, key=lambda r: (r.event_at, r.available_at, r.recorded_at, r.record_id), default=None)
    lower = at-timedelta(days=6)
    delivered = [r for r in active.values() if r.kind == 'delivery' and r.option == 'support_prompt'
                 and r.stage == 'delivered' and lower <= r.event_at < at and r.available_at < at]
    _require(len({r.assignment_id for r in delivered}) == len(delivered)
             and len({r.event_at for r in delivered}) == len(delivered), 'duplicate delivered prompt')
    for record in delivered:
        owner = active.get(record.assignment_id)
        _require(owner is not None and owner.kind == 'assignment' and owner.option == 'support_prompt'
                 and owner.event_at == record.event_at-timedelta(hours=8), 'unowned public prompt delivery')
        hours = (record.event_at-origin).total_seconds()/3600
        _require((hours-8) % 24 == 0, 'prompt delivery must be at public 20:00 night boundary')
    sources = ([previous.record_id] if previous else []) + [r.record_id for r in delivered]
    _require(set(sources) <= context_ids, 'required feature source absent from persisted predecision context')
    controls = (1., 7. if previous is None else float(previous.sleep_quality),
                float(previous is None), float(len(delivered)), (int(day)+1)/84.)
    outcome = active.get(decision.outcome_link_id)
    _require(outcome is not None and outcome.kind == 'support_outcome_link', 'missing completed outcome link')
    for ref in nested_refs(outcome):
        _require(ref.record_id in active and sha(active[ref.record_id].model_dump(mode='json')) == ref.projection_sha256,
                 'unresolved/changed public reduced outcome reference')
    _require(outcome.support_decision.record_id == decision.record_id
             and outcome.assignment_ref is not None and outcome.assignment_ref.record_id == assignment.record_id
             and outcome.window_id == decision.outcome_window.id
             and outcome.event_at == outcome.assessment_at == decision.outcome_window.assessment_at
             and outcome.assessment_at <= outcome.evaluated_as_of <= outcome.recorded_at,
             'outcome linkage/clock mismatch')
    status = outcome.reward.status
    if status in ('pending', 'undefined'):
        return None, status
    reward = None
    if status == 'observed':
        report = active.get(outcome.reward.report_ref.record_id)
        _require(report is not None and report.kind == 'daily_report' and report.missingness == 'observed'
                 and report.event_at == outcome.assessment_at and report.available_at < outcome.evaluated_as_of,
                 'observed reward report/assessment/availability mismatch')
        reward = float(report.sleep_quality)
    return DecisionRow(history.patient_id, decision.record_id, int(day)+1, controls,
                       int(assignment.option == 'support_prompt'), float(assignment.probability), reward,
                       tuple(sorted(sources))), status


def build_features(histories: Sequence[PublicHistory]) -> FeatureData:
    """Build unique completed S1 contexts; invalid observed inputs reject the fit.

    Invalid missing-only contexts retain a valid complete-case primary and mark
    the separate sensitivity unavailable. Pending/undefined/S0/S2/deterministic
    points do not enter either completed eligible analysis population.
    """
    _require(bool(histories), 'empty support cohort')
    cutoff = histories[0].cutoff
    _require(_aware(cutoff), 'timezone-aware common cutoff required')
    _require(len({h.patient_id for h in histories}) == len(histories), 'duplicate patient')
    rows, hashes, missing_errors = [], [], []
    excluded = dict(non_s1=0, not_randomized=0, pending=0, undefined=0, incomplete_window=0)
    adapter = TypeAdapter(ReducedRecord)
    for history in sorted(histories, key=lambda h: h.patient_id):
        _require(history.cutoff == cutoff and _aware(history.origin), 'common cutoff/aware origin required')
        records = [adapter.validate_python(r.model_dump()) for r in history.records]
        active = {r.record_id: r for r in records}
        _require(len(active) == len(records), 'duplicate public record')
        _require(all(r.patient_id == history.patient_id and r.event_at <= r.recorded_at <= r.available_at < cutoff
                     and r.record_status != 'retracted' and r.duplicate_of is None for r in records),
                 'unavailable/cross-patient/inactive public record')
        _require(not any(r.supersedes in active for r in records if r.supersedes), 'active view contains superseded value')
        hashes.append(dict(patient_id=history.patient_id, origin=history.origin.isoformat(),
                           records=[r.model_dump(mode='json') for r in sorted(records, key=lambda r: r.record_id)]))
        decisions = [r for r in records if r.kind == 'support_decision']
        _require(len({r.cutoff for r in decisions}) == len(decisions), 'duplicate nightly support decision')
        for decision in sorted(decisions, key=lambda r: (r.cutoff, r.record_id)):
            if decision.mode != 'mrt':
                excluded['non_s1'] += 1
                continue
            if decision.availability != 'randomized':
                excluded['not_randomized'] += 1
                continue
            if decision.outcome_window.assessment_at >= cutoff:
                excluded['incomplete_window'] += 1
                continue
            outcome = active.get(decision.outcome_link_id)
            if outcome is not None and outcome.kind == 'support_outcome_link' and outcome.reward.status in ('pending', 'undefined'):
                excluded[outcome.reward.status] += 1
                continue
            try:
                row, status = _row(history, decision, active)
            except InvalidInput as error:
                if outcome is not None and outcome.kind == 'support_outcome_link' and outcome.reward.status == 'missing':
                    missing_errors.append(f'{decision.record_id}: {error}')
                    continue
                raise
            if row is None:
                excluded[status] += 1
            else:
                rows.append(row)
    return FeatureData(tuple(rows), cutoff, sha(hashes), excluded,
                       '; '.join(missing_errors) if missing_errors else None)


def design(rows):
    return np.asarray([(*r.controls, r.action-.5) for r in rows], dtype=np.float64).reshape(-1, 6)
