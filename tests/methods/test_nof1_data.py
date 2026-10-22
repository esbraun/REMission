"""Typed H* fixture controls, using no simulator, database or service state."""
import copy
from datetime import datetime, timedelta, timezone
import unittest

import numpy as np

from contracts.domain.analysis import canonical, sha, FIXED_SUPPORT_REF
from contracts.domain.protocol import NOF1_REF
from contracts.domain.protocol_analysis import ProtocolHistory, ReducedHeader
from methods.nof1.data import prepare, Unavailable


ORIGIN = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def fixture(patient="N-PATIENT-A", *, start=0, review=36, arms=("MED_A", "MED_B", "MED_A", "MED_B")):
    day, records = start + review, []

    def add(kind, name, at, **fields):
        identifier = patient + "-" + name
        row = dict(record_id=identifier, patient_id=patient, kind=kind, record_schema="2.0.0",
            event_at=at, recorded_at=at, available_at=at, lineage_id=identifier, revision=1,
            supersedes=None, duplicate_of=None, record_status="active", **fields)
        records.append(row)
        return row

    before = ORIGIN - timedelta(seconds=2)
    decision = add("decision_snapshot", "decision", before, cutoff=before,
        workflow=dict(clinical="treatment_active", learning="nof1_design", data_readiness="ready", hold_reasons=[],
            support_policy=FIXED_SUPPORT_REF, support_mode="fixed"), eligibility=[])
    approval = add("approval", "approval", before, decision_id=decision["record_id"], option=None,
        permitted_options=["MED_A", "MED_B"], purpose="randomization_protocol")
    consent = add("consent", "consent", before, component="nof1", consent_status="active",
        oversight_status="approved_synthetic", effective_at=before, expires_at=None, withdrawn_at=None)

    def assigned(name, option, at, experimental=False):
        return add("assignment", name, at, decision_id=decision["record_id"], approval_id=approval["record_id"],
            option=option, experimental=experimental, component="nof1" if experimental else None,
            probability=.5 if experimental else None, support_policy=FIXED_SUPPORT_REF,
            patient_blinded=False, clinician_blinded=False, clinician_override=None, override_reason=None)

    background = assigned("background", "behavioral_continue", ORIGIN)
    support = assigned("support", "no_prompt", ORIGIN)
    # Resolve nested reduced refs from typed values, matching the actual wire hash.
    def ref(row):
        from contracts.domain.protocol_analysis import REDUCED_MODELS
        value = REDUCED_MODELS[row["kind"]].model_validate(row)
        return dict(record_id=row["record_id"], projection_sha256=sha(value.model_dump(mode="json")))

    activated = ORIGIN + timedelta(days=start)
    add("protocol_snapshot", "snapshot", activated, family="nof1_med", protocol=NOF1_REF, template=NOF1_REF,
        consent_refs=[ref(consent)], approval_refs=[ref(approval)], background_ref=ref(background),
        support_refs=[ref(support)], activation_at=activated)
    blocks = []
    for block, offset in enumerate(range(0, review, 9)):
        blocks.append(assigned("block-" + str(block), arms[block % len(arms)],
            ORIGIN + timedelta(days=start + offset), True))
    for t in range(1, day + 1):
        missingness = "missing" if t % 10 == 0 else "pending" if t == 11 else "observed"
        add("daily_report", "quality-" + str(t), ORIGIN + timedelta(days=t, minutes=-1),
            sleep_quality=5.001 + (t % 7) * .2 if missingness == "observed" else None, missingness=missingness)
        at = ORIGIN + timedelta(days=t - 1, hours=8)
        block = next((b for b in blocks if 0 < t - (b["event_at"] - ORIGIN).days <= 7), None)
        for component, assignment in (("C", background), ("M", block), ("support", support)):
            if assignment is None:
                continue
            taken = t % (3 if component == "M" else 4) != 0
            add("delivery", component + "-delivery-" + str(t), at,
                assignment_id=assignment["record_id"], option=assignment["option"],
                stage="delivered" if component == "support" else "taken" if taken else "not_taken",
                adherence=1. if component == "support" else float(taken), rescue=False, protocol_deviations=[])
    for t in range(0, day + 1, 14):
        end = ORIGIN + timedelta(days=t, hours=-1)
        add("isi", "isi-" + str(t), end + timedelta(minutes=59), total=16,
            instrument_version="ISI-7-synthetic-14d-v1", recall_days=14,
            recall_start=end - timedelta(days=14), recall_end=end)
    return parsed(patient, records, day)


def parsed(patient, records, day):
    return ProtocolHistory.model_validate(dict(schema_version="2.0.0", synthetic=True, kind="poc_protocol_history",
        version="poc-analysis-history-v1-protocol-v2", patient_id=patient, family="nof1_med",
        cutoff=ORIGIN + timedelta(days=day), origin=ORIGIN, protocol=NOF1_REF, records=records,
        provenance=[{key: r[key] for key in ReducedHeader.model_fields} for r in records]))


def changed(history, record_id, **fields):
    rows = [r.model_dump(mode="python") for r in history.records]
    next(r for r in rows if r["record_id"] == record_id).update(fields)
    return parsed(history.patient_id, rows, (history.cutoff - history.origin).days)


def read(histories, purpose="N1", target="N-PATIENT-A"):
    return prepare(histories, purpose=purpose, target_id=target, seed_patient=target)


class DataTests(unittest.TestCase):
    def test_delayed_start_keeps_origin_grid_phase_recall_and_delivery_night(self):
        p = read([fixture(start=10)]).patients[0]
        self.assertEqual((p.day, p.start_day, p.review_day), (46, 10, 36))
        np.testing.assert_array_equal(p.nights, np.arange(-13, 47))
        self.assertEqual(p.path.medication[23, 0], 0)  # public night10, before first MED night11
        self.assertEqual(p.path.medication[24, 0], .5)  # delivery evening10 -> report11
        np.testing.assert_array_equal(p.recall[0], np.arange(14))
        self.assertEqual(p.qindex[0], 14)
        self.assertEqual(p.counts["M_total"], 28)

    def test_component_conjugate_counts_pending_and_missing(self):
        p = read([fixture()]).patients[0]
        self.assertEqual(p.counts["C_total"], 36)
        self.assertEqual(p.counts["C_success"], 27)
        self.assertEqual(p.counts["M_total"], 28)
        self.assertEqual(p.counts["M_success"], 20)
        self.assertEqual(p.counts["missing"], 3)
        self.assertEqual(p.counts["observed"], 32)
        self.assertEqual(len(p.ownership["observation_indicators"]), 35)
        self.assertEqual(len(p.quality), 32)
        self.assertTrue(all("support" not in r for r in p.ownership["adherence_M"]))

    def test_same_full_history_hash_ownership_and_rebound_n0_n1(self):
        h = fixture()
        n0, n1 = read([h], "N0"), read([h], "N1")
        self.assertEqual(n0.history_sha256, n1.history_sha256)
        a, b = n0.patients[0], n1.patients[0]
        self.assertEqual(a.ownership, b.ownership)
        self.assertEqual(a.counts, b.counts)
        np.testing.assert_array_equal(a.path.rebound, b.path.rebound)
        np.testing.assert_array_equal(a.c, b.c)
        self.assertFalse(np.array_equal(a.medication, b.medication))

    def test_target_gate_not_bypassed_by_cohort_and_no_first_member_default(self):
        sparse = fixture("N-PATIENT-B", arms=("MED_A",) * 4)
        data = read([fixture(), sparse], target="N-PATIENT-B")
        self.assertEqual(data.target_index, 1)
        self.assertEqual(data.readiness, "inconclusive")
        self.assertEqual(read([fixture(), sparse]).readiness, "eligible")
        with self.assertRaises(ValueError):
            prepare([fixture(), sparse], purpose="N1", target_id="N-PATIENT-B", seed_patient="N-PATIENT-A")

    def test_unknown_missing_mismatched_exposure_rejected(self):
        h = fixture()
        for fields in [dict(stage="unknown", adherence=None), dict(stage="delivered", adherence=1.),
                       dict(stage="taken", adherence=0.)]:
            with self.assertRaises(ValueError):
                read([changed(h, "N-PATIENT-A-M-delivery-1", **fields)])
        rows = [r.model_dump(mode="python") for r in h.records if r.record_id != "N-PATIENT-A-M-delivery-1"]
        with self.assertRaises(ValueError):
            read([parsed(h.patient_id, rows, 36)])

    def test_strict_cutoff_hstar_unknown_fields_and_clock(self):
        h = fixture()
        rows = [r.model_dump(mode="python") for r in h.records]
        extra = copy.deepcopy(next(r for r in rows if r["kind"] == "assignment" and r["experimental"]))
        extra.update(record_id="N-PATIENT-A-next-block", lineage_id="N-PATIENT-A-next-block",
            event_at=h.cutoff, recorded_at=h.cutoff, available_at=h.cutoff)
        with self.assertRaises(ValueError):
            parsed(h.patient_id, [*rows, extra], 36)
        value = h.model_dump(mode="python")
        next(r for r in value["records"] if r["kind"] == "daily_report")["function"] = 8.
        with self.assertRaises(ValueError):
            ProtocolHistory.model_validate(value)
        early = fixture(review=18, arms=("MED_A", "MED_B"))
        with self.assertRaises(Unavailable) as result:
            read([early])
        self.assertEqual(result.exception.status, "unavailable")
        with self.assertRaises(ValueError):
            read([fixture(), fixture("N-PATIENT-B", start=1)])

    def test_lineage_correction_consumed_once(self):
        h = fixture()
        value = h.model_dump(mode="python")
        old = next(r for r in value["records"] if r["record_id"] == "N-PATIENT-A-M-delivery-1")
        old_header = {key: old[key] for key in ReducedHeader.model_fields}
        old.update(record_id=old["record_id"] + "-corrected", revision=2, supersedes=old_header["record_id"],
                   stage="not_taken", adherence=0., recorded_at=old["recorded_at"] + timedelta(seconds=1),
                   available_at=old["available_at"] + timedelta(seconds=1))
        value["provenance"] = [p for p in value["provenance"] if p["record_id"] != old_header["record_id"]]
        value["provenance"].extend([old_header, {key: old[key] for key in ReducedHeader.model_fields}])
        corrected = read([ProtocolHistory.model_validate(value)]).patients[0]
        self.assertEqual(corrected.counts["M_total"], 28)
        self.assertEqual(corrected.counts["M_success"], 19)
        self.assertNotIn(old_header["record_id"], corrected.ownership["adherence_M"])


if __name__ == "__main__":
    unittest.main()
