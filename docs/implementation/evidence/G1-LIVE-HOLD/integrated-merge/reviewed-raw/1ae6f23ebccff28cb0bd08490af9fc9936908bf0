"""Foundation presentation composes the accepted domain, without an estimator."""
from datetime import datetime
import json
from contracts.domain.boundaries import ObservedHistory, lineage_heads, visible_records
from contracts.domain.entities import DecisionSnapshot, Workflow
from .store import canonical, digest, timestamp

STAGES = {
    "ASSIGN-01": ("Assessment incomplete", "assessment", "none", "incomplete", "fixed"),
    "ASSIGN-02": ("Initial ordinary choice", "initial_assignment", "none", "ready", "fixed"),
    "ASSIGN-03": ("Treatment active; no decision due", "treatment_active", "none", "ready", "fixed"),
    "ASSIGN-04": ("N-of-1 eligibility and design", "treatment_active", "nof1_design", "ready", "fixed"),
    "ASSIGN-05": ("N-of-1 block or washout", "treatment_active", "nof1_block", "ready", "frozen"),
    "ASSIGN-06": ("N-of-1 interim or final review", "scheduled_reassessment", "nof1_review", "ready", "fixed"),
    "ASSIGN-07": ("Behavioral reassessment", "scheduled_reassessment", "escalation_decision", "ready", "fixed"),
    "ASSIGN-08": ("Support envelope review", "treatment_active", "support_unavailable", "ready", "paused"),
    "ASSIGN-09": ("Clinical hold or major phase change", "clinical_hold", "none", "ready", "paused"),
    "ASSIGN-10": ("Maintenance and closeout", "maintenance_closeout", "none", "ready", "fixed"),
}


def reference(identifier: str, value: str = "foundation-v1") -> dict:
    return {"id": identifier, "version": "1.0.0", "sha256": digest(value)}


SUPPORT = reference("fixed-approved-support", "foundation fixed support; no learning")


def state_for(stage: str, reason: str = "Synthetic clinical concern requires review") -> dict:
    _, clinical, learning, readiness, support_mode = STAGES[stage]
    workflow = Workflow.model_validate(dict(clinical=clinical, learning=learning, data_readiness=readiness,
                                           hold_reasons=[reason] if clinical == "clinical_hold" else [],
                                           support_policy=SUPPORT, support_mode=support_mode))
    return {"stage": stage, "workflow": workflow.model_dump(mode="json"), "plan": None}


def record_header(record_id: str, patient_id: str, at: datetime) -> dict:
    clock = timestamp(at)
    return dict(schema_version="1.0.0", synthetic=True, record_id=record_id, patient_id=patient_id,
                event_at=clock, recorded_at=clock, available_at=clock,
                source=dict(id="foundation-synthetic", version="1.0.0", adapter="research_configuration", raw_sha256=digest(record_id)),
                lineage_id=record_id, revision=1, supersedes=None, duplicate_of=None, record_status="active")


def history(db, patient_id: str) -> ObservedHistory:
    records = [json.loads(row[0]) for row in db.execute("SELECT payload FROM events WHERE patient_id=? ORDER BY available_at,phase,id", (patient_id,))]
    if any(r['schema_version'] == '2.0.0' for r in records):
        from contracts.domain.observed_v2 import ObservedHistoryV2
        return ObservedHistoryV2.model_validate_json(canonical(dict(schema_version='2.0.0', synthetic=True, kind='observed_history', patient_id=patient_id, records=records)))
    return ObservedHistory.model_validate_json(canonical(dict(schema_version="1.0.0", synthetic=True, kind="observed_history", patient_id=patient_id, records=records)))


def current_safety(db, patient_id: str, at: datetime):
    """Current safety admission is inclusive; learner/history projections stay strict.

    Resolve visible lineage before selecting safety values so a correction,
    retraction or duplicate cannot revive an older clinical fact. Call inside
    the same transaction as the state transition or approval being admitted.
    """
    heads = lineage_heads(visible_records(history(db, patient_id).records, at, inclusive=True))
    return [r for r in heads if r.record_status != "retracted" and r.kind in ("consent", "intercurrent_event")]


def create_decision(db, patient_id: str, at: datetime) -> str:
    row = db.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    state = json.loads(row["state_json"])
    identifier = "decision-" + digest(canonical([patient_id, row["version"], timestamp(at)]))[:32]
    eligibility = [dict(action=action, status="excluded" if state["workflow"]["hold_reasons"] else "eligible",
                        reasons=state["workflow"]["hold_reasons"]) for action in ["MED_A", "MED_B", "behavioral_continue", "behavioral_escalate", "usual_care"]]
    snapshot = DecisionSnapshot.model_validate_json(canonical(dict(**record_header(identifier, patient_id, at),
        kind="decision_snapshot", cutoff=timestamp(at), patient_version=row["version"], state_version=row["state_version"],
        consent_version=row["consent_version"], eligibility_version=row["eligibility_version"], workflow=state["workflow"],
        view=dict(patient_id=patient_id, mode="current", snapshot_id=None), eligibility=eligibility,
        outcome="Ordinary synthetic care; statistical estimates unavailable", horizon_days=42,
        estimand=reference("EST-VISIT"), model=reference("foundation-no-estimator", "No statistical engine implemented"),
        posterior=None, evidence=[], policy=SUPPORT)))
    projected = history(db, patient_id).project(at).model_dump(mode="json")
    options = eligibility if state["stage"] != "ASSIGN-07" else [e for e in eligibility if e["action"].startswith("behavioral_")]
    ordinary = state["stage"] in ("ASSIGN-02", "ASSIGN-07") and state["workflow"]["data_readiness"] == "ready" and not state["workflow"]["hold_reasons"]
    display = dict(patient_id=patient_id, name=row["name"], stage=state["stage"], stage_label=STAGES[state["stage"]][0],
                   snapshot=snapshot.model_dump(mode="json"), projection=projected, plan=state["plan"],
                   options=options, permissions=dict(approve_ordinary=ordinary, request_review=True, randomize=False, estimate=False),
                   engines=dict(bayesian="unavailable", nof1="unavailable", escalation="unavailable", support="unavailable"),
                   estimates=dict(status="pending", reason="Statistical engines are not implemented; no treatment ranking is available"),
                   labels=["Synthetic demonstration", "No acute clinical monitoring"],
                   version_status="Foundation contract consumer; downstream G2-G5 engines pending")
    encoded = canonical(display)
    db.execute("INSERT INTO decisions VALUES (?,?,?,?,?)", (identifier, patient_id, snapshot.model_dump_json(), encoded, digest(encoded)))
    db.execute("UPDATE patients SET current_decision=?,cutoff=? WHERE id=?", (identifier, timestamp(at), patient_id))
    return identifier
