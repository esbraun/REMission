"""Validated observed-only admission and deterministic resumable synthetic replay."""
from datetime import datetime
import json
from zoneinfo import ZoneInfo
from pydantic import TypeAdapter
from contracts.domain.entities import ObservedRecord
from contracts.domain.boundaries import ObservedHistory
from .store import Store, canonical, digest, instant, timestamp
from .workflow import create_decision, history, state_for

ADAPTER = TypeAdapter(ObservedRecord)
INGESTIBLE = {"patient", "consent", "encounter", "medication_order", "medication_exposure", "observation", "intercurrent_event", "oura_like", "daily_report", "isi"}
PHASE = {"intercurrent_event": 0, "consent": 0, "patient": 1, "observation": 2, "daily_report": 3, "oura_like": 4}


def parse_observed(raw: bytes):
    record = ADAPTER.validate_json(raw)
    if record.kind not in INGESTIBLE:
        raise ValueError("administrative_record_route_required")
    covariates = record.covariates if record.kind == "patient" else [record.measure] if record.kind == "observation" else []
    if any(c.observed_at > record.event_at or c.available_at > record.available_at for c in covariates):
        raise ValueError("nested_future_covariate")
    if record.kind in ("patient", "oura_like"):
        zone = ZoneInfo(record.timezone)
        if record.kind == "oura_like" and record.episode_end.astimezone(zone).date() != record.local_date:
            raise ValueError("sleep_local_date_mismatch: local date identifies episode end")
    return record


def append_event(db, record, raw: bytes, *, received_at: datetime | None = None):
    if received_at is not None and record.available_at < received_at:
        # Live receipt cannot be backdated by an uploader. Revalidate the
        # adapter record with the actual receipt before authoritative admission.
        data = record.model_dump(mode="json")
        data["available_at"] = timestamp(received_at)
        record = ADAPTER.validate_json(canonical(data))
    existing = db.execute("SELECT payload_sha256,raw_sha256 FROM events WHERE id=?", (record.record_id,)).fetchone()
    encoded = canonical(record.model_dump(mode="json"))
    if existing:
        if existing["payload_sha256"] != digest(encoded) or existing["raw_sha256"] != digest(raw):
            raise ValueError("record_id_payload_conflict")
        return False
    prior = history(db, record.patient_id)
    ObservedHistory.model_validate_json(canonical(dict(schema_version="1.0.0", synthetic=True, kind="observed_history", patient_id=record.patient_id,
                                                     records=[*[r.model_dump(mode="json") for r in prior.records], record.model_dump(mode="json")])))
    if record.source.raw_sha256 != digest(raw):
        # The source hash identifies external source bytes, supplied separately
        # by admission; it must not be a self-hash of the envelope JSON.
        raise ValueError("raw_source_hash_mismatch")
    db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (record.record_id, record.patient_id, record.kind,
        record.lineage_id, record.revision, record.duplicate_of, encoded, digest(encoded), raw, digest(raw),
        timestamp(record.event_at), timestamp(record.recorded_at), timestamp(record.available_at), PHASE.get(record.kind, 5),
        timestamp(received_at) if received_at else None))
    return True


def apply_current_state(db, patient_id: str, at: datetime):
    row = db.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    records = history(db, patient_id).as_known_at(at)
    # Known safety/consent arrivals also invalidate immediately at equal time;
    # symptom/learner projections retain strict-before availability.
    known_safety = [r for r in history(db, patient_id).records if r.kind in ("consent", "intercurrent_event") and r.event_at <= at and r.available_at <= at]
    held = any(r.kind == "intercurrent_event" and r.event_type in ("death", "admission", "regimen_change", "steroid_change", "fever_suspected_infection", "confusion", "fall") and r.record_status != "retracted" for r in known_safety)
    state = state_for("ASSIGN-09", "Known safety event requires clinical review") if held else json.loads(row["state_json"])
    db.execute("UPDATE patients SET version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1,consent_version=consent_version+?,state_json=? WHERE id=?",
               (1 if any(r.kind == "consent" for r in known_safety) else 0, canonical(state), patient_id))
    create_decision(db, patient_id, at)
    db.execute("INSERT INTO pending_work VALUES(?,?,?,?)", ("work-"+digest(canonical([patient_id,row["version"],timestamp(at)]))[:32],patient_id,"unavailable","New observed data; statistical worker unavailable"))


def replay(store: Store, run_id: str, entries: list[dict], cutoff: str, *, batch_size: int = 100, fault=None):
    at = instant(cutoff)
    prepared = [(parse_observed(canonical(e["record"]).encode()), e["raw_source"].encode()) for e in entries]
    prepared.sort(key=lambda item: (item[0].available_at, PHASE.get(item[0].kind, 5), item[0].record_id))
    source_hash = digest(canonical([[r.model_dump(mode="json"),raw.decode()] for r,raw in prepared]))
    with store.transaction(write=True) as db:
        existing = db.execute("SELECT * FROM replay_runs WHERE id=?", (run_id,)).fetchone()
        if existing and (existing["source_sha256"] != source_hash or existing["cutoff"] != timestamp(at)):
            raise ValueError("immutable_replay_run_conflict")
        if not existing:
            db.execute("INSERT INTO replay_runs VALUES(?,?,?,?,?)", (run_id,source_hash,0,len(prepared),timestamp(at)))
    while True:
        with store.transaction(write=True) as db:
            cursor = db.execute("SELECT cursor FROM replay_runs WHERE id=?", (run_id,)).fetchone()[0]
            if cursor == len(prepared):
                break
            changed = set()
            end = min(cursor+batch_size,len(prepared))
            for record,raw in prepared[cursor:end]:
                key=record.record_id
                try:
                    inserted=append_event(db,record,raw)
                except ValueError as error:
                    db.execute("INSERT INTO ingestion_receipts VALUES(?,?,?,?,?)",(run_id,key,digest(raw),"rejected",str(error)))
                    raise
                db.execute("INSERT INTO ingestion_receipts VALUES(?,?,?,?,?)",(run_id,key,digest(raw),"accepted" if inserted else "repeated","validated"))
                changed.add(record.patient_id)
            for patient_id in sorted(changed):
                apply_current_state(db,patient_id,at)
            db.execute("UPDATE replay_runs SET cursor=? WHERE id=?",(end,run_id))
            if fault:
                fault("before_replay_commit")
    return {"run_id":run_id,"source_sha256":source_hash,"records":len(prepared),"status":"completed"}
