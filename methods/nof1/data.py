"""Observed-only restricted N cohort reader; no service/private state inputs."""
from dataclasses import dataclass
from datetime import timedelta

import numpy as np

from contracts.domain.analysis import sha
from contracts.domain.protocol_analysis import ProtocolHistory
from .dynamics import ExposurePath, exposure_path, medication_design


class Unavailable(ValueError):
    """A correctly labeled pre-fit gate, never a successful estimate."""

    def __init__(self, status, reason):
        self.status, self.reason = status, reason
        super().__init__(reason)


@dataclass(frozen=True)
class PatientData:
    patient_id: str
    day: int
    start_day: int
    review_day: int
    nights: np.ndarray
    c: np.ndarray
    path: ExposurePath
    medication: np.ndarray
    quality: np.ndarray
    qindex: np.ndarray
    isi: np.ndarray
    recall: np.ndarray
    counts: dict
    arm_blocks: dict
    ownership: dict
    record_ids: tuple


@dataclass(frozen=True)
class CohortData:
    purpose: str
    target_id: str
    target_index: int
    patients: tuple[PatientData, ...]
    history_sha256: str
    readiness: str


def _integer_day(at, origin):
    days = (at - origin).total_seconds() / 86400
    if days != int(days):
        raise ValueError("N protocol noon must align with the public origin")
    return int(days)


def _patient(history, purpose):
    records = history.records
    active = {r.record_id: r for r in records}
    day = _integer_day(history.cutoff, history.origin)
    snapshots = [r for r in records if r.kind == "protocol_snapshot"]
    if len(snapshots) != 1:
        raise ValueError("one observed uninterrupted N protocol snapshot required")
    snapshot = snapshots[0]
    start = _integer_day(snapshot.activation_at, history.origin)
    review = day - start
    if start < 0 or start + 72 > 84:
        raise ValueError("N activation must allow the full public 72-night template")
    if review not in (36, 72):
        raise Unavailable("unavailable", "N analysis requires protocol-relative review day36 or72")
    if any(r.kind == "intercurrent_event" for r in records):
        raise ValueError("interrupted history is outside the restricted N model")
    for r in records:
        if r.kind == "consent" and r.component == "nof1":
            if (r.consent_status != "active" or r.oversight_status != "approved_synthetic"
                    or r.withdrawn_at is not None or (r.expires_at is not None and r.expires_at <= history.cutoff)):
                raise ValueError("uninterrupted active N consent required")
        if r.kind == "decision_snapshot" and (r.workflow.clinical == "clinical_hold" or r.workflow.hold_reasons):
            raise ValueError("held history is outside the restricted N model")
        if r.kind == "support_decision" and r.probabilities.get("support_prompt", 0) != 0:
            raise ValueError("N support must remain no-prompt")
    assignments = [r for r in records if r.kind == "assignment"]
    if any(r.clinician_override is not None or r.override_reason is not None for r in assignments):
        raise ValueError("overridden history is outside the restricted N model")
    background = sorted((r for r in assignments if r.option == "behavioral_continue"), key=lambda r: r.event_at)
    frozen = active.get(snapshot.background_ref.record_id)
    if (frozen is None or frozen.kind != "assignment" or frozen.option != "behavioral_continue"
            or frozen.experimental or frozen.event_at > snapshot.activation_at):
        raise ValueError("observed fixed continuation snapshot required")
    if not background or any(r.experimental or r.component is not None for r in background):
        raise ValueError("ordinary continuation background required")
    if any(r.event_at > snapshot.activation_at for r in background):
        raise ValueError("background changed after activation")
    if background[-1].record_id != frozen.record_id:
        raise ValueError("background snapshot must name the current continuation assignment")
    if any(r.option not in ("behavioral_continue", "MED_A", "MED_B", "no_prompt") for r in assignments):
        raise ValueError("unsupported N action")
    for ref in snapshot.support_refs:
        support = active[ref.record_id]
        if ((support.kind == "assignment" and support.option != "no_prompt") or
                (support.kind == "support_decision" and support.probabilities.get("support_prompt", 0) != 0)):
            raise ValueError("frozen no-prompt evidence required")
    if not snapshot.support_refs:
        raise ValueError("explicit frozen no-prompt evidence required")
    medication = sorted((r for r in assignments if r.option in ("MED_A", "MED_B")), key=lambda r: r.event_at)
    expected_starts = [history.origin + timedelta(days=start + offset) for offset in range(0, review, 9)]
    if [r.event_at for r in medication] != expected_starts:
        raise ValueError("complete unique completed randomized block assignments required")
    approvals = {ref.record_id for ref in snapshot.approval_refs}
    for r in medication:
        if (not r.experimental or r.component != "nof1" or r.probability != .5
                or r.approval_id not in approvals or r.patient_blinded or r.clinician_blinded):
            raise ValueError("canonical independent unblinded binary block assignment required")
    nights = np.arange(-13, day + 1)
    assigned, taken, c = [None] * len(nights), [None] * len(nights), np.zeros(len(nights))
    deliveries = {}
    for r in records:
        if r.kind != "delivery":
            continue
        night = _integer_day(r.event_at - timedelta(hours=8), history.origin) + 1
        if not 1 <= night <= day or r.rescue or r.protocol_deviations:
            raise ValueError("invalid or deviating N delivery")
        if r.option == "no_prompt":
            continue
        if r.stage not in ("taken", "not_taken") or r.adherence != float(r.stage == "taken"):
            raise ValueError("resolved binary component delivery required")
        key = (night, "C" if r.option == "behavioral_continue" else "M")
        if key in deliveries:
            raise ValueError("duplicate nightly component delivery")
        deliveries[key] = r
    used, owned_c, owned_m = set(), [], []
    for i, t in enumerate(nights):
        c[i] = .65 * (c[i - 1] if i else 0.)
        if t <= 0:
            continue
        at = history.origin + timedelta(days=int(t - 1), hours=8)
        current = [r for r in background if r.event_at <= at]
        block = next((r for r in medication if 1 <= t - _integer_day(r.event_at, history.origin) <= 7), None)
        for component, assignment in (("C", current[-1] if current else None), ("M", block)):
            r = deliveries.get((int(t), component))
            if assignment is None:
                if r is not None:
                    raise ValueError("delivery on an unassigned baseline/washout night")
                continue
            if r is None or r.assignment_id != assignment.record_id or r.option != assignment.option:
                raise ValueError("missing, unknown or mismatched required component exposure")
            used.add((int(t), component))
            (owned_c if component == "C" else owned_m).append(r)
            if component == "C":
                c[i] += .35 * (r.stage == "taken")
            else:
                assigned[i] = assignment.option
                taken[i] = assignment.option if r.stage == "taken" else None
    if used != deliveries.keys():
        raise ValueError("unconsumed component delivery")
    path = exposure_path(assigned, taken)
    quality_records = sorted((r for r in records if r.kind == "daily_report"), key=lambda r: r.event_at)
    observed = [r for r in quality_records if r.missingness == "observed"]
    isi = sorted((r for r in records if r.kind == "isi"), key=lambda r: r.recall_end)
    last = [_integer_day(r.recall_end + timedelta(hours=1), history.origin) for r in isi]
    qindex = [_integer_day(r.event_at + timedelta(minutes=1), history.origin) + 13 for r in observed]
    ownership = dict(quality=tuple(r.record_id for r in observed), isi=tuple(r.record_id for r in isi),
        adherence_C=tuple(r.record_id for r in owned_c), adherence_M=tuple(r.record_id for r in owned_m),
        observation_indicators=tuple(r.record_id for r in quality_records if r.missingness != "pending"))
    counts = dict(C_success=sum(r.stage == "taken" for r in owned_c), C_total=len(owned_c),
        M_success=sum(r.stage == "taken" for r in owned_m), M_total=len(owned_m),
        observed=len(observed), missing=sum(r.missingness == "missing" for r in quality_records))
    return PatientData(history.patient_id, day, start, review, nights, c, path, medication_design(path, purpose),
        np.array([r.sleep_quality for r in observed]), np.asarray(qindex, dtype=int),
        np.array([r.total for r in isi]), np.asarray([np.arange(t - 13, t + 1) + 13 for t in last], dtype=int),
        counts, {arm: sum(r.option == arm for r in medication) for arm in ("MED_A", "MED_B")}, ownership,
        tuple(r.record_id for r in records))


def prepare(histories, *, purpose, target_id, seed_patient):
    """Consume only validated reduced H*, with an explicit saved target binding.

    Admission/routing remains the service's responsibility. This function does
    not turn the existing non-executable boundary request into a fit request.
    """
    if purpose not in ("N0", "N1") or not target_id or seed_patient != target_id:
        raise ValueError("explicit N purpose and matching target/seed patient required")
    if not histories or any(not isinstance(h, ProtocolHistory) for h in histories):
        raise ValueError("only typed reduced protocol histories are accepted")
    histories = [ProtocolHistory.model_validate(h.model_dump(mode="python")) for h in histories]
    ids = [h.patient_id for h in histories]
    if ids != sorted(set(ids)) or target_id not in ids:
        raise ValueError("unique sorted declared cohort containing the bound target required")
    if len({h.cutoff for h in histories}) != 1 or any(h.family != "nof1_med" for h in histories):
        raise ValueError("common-cutoff N cohort required")
    patients = tuple(_patient(h, purpose) for h in histories)
    if len({p.review_day for p in patients}) != 1:
        raise ValueError("same protocol-relative scheduled review required")
    index = ids.index(target_id)
    ready = "eligible" if min(patients[index].arm_blocks.values()) >= 2 else "inconclusive"
    return CohortData(purpose, target_id, index, patients,
        sha([h.model_dump(mode="json") for h in histories]), ready)
