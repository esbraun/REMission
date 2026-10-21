"""Validated observed-only admission and deterministic resumable synthetic replay."""
from datetime import datetime
import json
from zoneinfo import ZoneInfo
from pydantic import TypeAdapter
from contracts.domain.entities import ObservedRecord
from contracts.domain.boundaries import ObservedHistory
from .store import Store, canonical, digest, instant, timestamp
from .workflow import create_decision, current_safety, history, state_for

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
    if record.source.raw_sha256 != digest(raw):
        raise ValueError("raw_source_hash_mismatch")
    # This initial adapter accepts raw synthetic observed envelopes. Real FHIR
    # and device transports require their own reviewed adapter, not opaque
    # unvalidated payloads smuggled into an observed export.
    source_record = record
    if record.duplicate_of is not None:
        prior_source = db.execute("SELECT payload FROM events WHERE id=? AND patient_id=?", (record.duplicate_of,record.patient_id)).fetchone()
        if prior_source is None:raise ValueError("duplicate_original_unavailable")
        source_record = ADAPTER.validate_json(prior_source[0])
    try:
        source_payload = json.loads(raw)
        if not isinstance(source_payload,dict) or "source" in source_payload:raise ValueError("raw_source_must_be_observed_envelope_without_source_header")
        source_payload["source"] = source_record.source.model_dump(mode="json")
        parsed_source = parse_observed(canonical(source_payload).encode())
        expected = source_record.model_dump(mode="json");actual=parsed_source.model_dump(mode="json")
        # Admission adds actual live receipt availability; the source retains
        # its declared availability. Other clinical/source fields must agree.
        expected.pop("available_at");actual.pop("available_at")
        if actual != expected:raise ValueError("raw_source_observation_mismatch")
    except (ValueError,TypeError) as error:
        raise ValueError("raw_source_not_validated_observed_data") from error
    if received_at is not None and record.available_at < received_at:
        # Live receipt cannot be backdated by an uploader. Revalidate the
        # adapter record with the actual receipt before authoritative admission.
        data = record.model_dump(mode="json")
        data["available_at"] = timestamp(received_at)
        record = ADAPTER.validate_json(canonical(data))
    existing = db.execute("SELECT payload,payload_sha256,raw_sha256 FROM events WHERE id=?", (record.record_id,)).fetchone()
    encoded = canonical(record.model_dump(mode="json"))
    if existing:
        prior_payload=json.loads(existing["payload"]);current_payload=json.loads(encoded)
        prior_payload.pop("available_at");current_payload.pop("available_at")
        if prior_payload!=current_payload or existing["raw_sha256"] != digest(raw):
            raise ValueError("record_id_payload_conflict")
        return False
    prior = history(db, record.patient_id)
    ObservedHistory.model_validate_json(canonical(dict(schema_version="1.0.0", synthetic=True, kind="observed_history", patient_id=record.patient_id,
                                                     records=[*[r.model_dump(mode="json") for r in prior.records], record.model_dump(mode="json")])))
    db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (record.record_id, record.patient_id, record.kind,
        record.lineage_id, record.revision, record.duplicate_of, encoded, digest(encoded), raw, digest(raw),
        timestamp(record.event_at), timestamp(record.recorded_at), timestamp(record.available_at), PHASE.get(record.kind, 5),
        timestamp(received_at) if received_at else None))
    return True


def apply_current_state(db, patient_id: str, at: datetime, *, advance_by: int = 1):
    row = db.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    # Known safety/consent arrivals also invalidate immediately at equal time;
    # symptom/learner projections retain strict-before availability.
    known_safety = current_safety(db, patient_id, at)
    held = any(r.kind == "intercurrent_event" and r.event_type in ("death", "admission", "regimen_change", "steroid_change", "fever_suspected_infection", "confusion", "fall") and r.record_status != "retracted" for r in known_safety)
    state = state_for("ASSIGN-09", "Known safety event requires clinical review") if held else json.loads(row["state_json"])
    consent_version=1+db.execute("SELECT count(*) FROM events WHERE patient_id=? AND kind='consent'",(patient_id,)).fetchone()[0]
    db.execute("UPDATE patients SET version=version+?,state_version=state_version+?,eligibility_version=eligibility_version+?,consent_version=?,state_json=? WHERE id=?",
               (advance_by,advance_by,advance_by,consent_version,canonical(state),patient_id))
    create_decision(db, patient_id, at)
    db.execute("INSERT INTO pending_work VALUES(?,?,?,?)", ("work-"+digest(canonical([patient_id,row["version"],timestamp(at)]))[:32],patient_id,"unavailable","New observed data; statistical worker unavailable"))


def replay(store: Store, run_id: str, entries: list[dict], cutoff: str, *, batch_size: int = 100, fault=None):
    at = instant(cutoff)
    prepared = [(parse_observed(canonical(e["record"]).encode()), e["raw_source"].encode()) for e in entries]
    prepared = [(r,raw) for r,raw in prepared if r.available_at <= at]
    prepared.sort(key=lambda item: (item[0].available_at, PHASE.get(item[0].kind, 5), item[0].record_id))
    source_hash = digest(canonical([[r.model_dump(mode="json"),raw.decode()] for r,raw in prepared]))
    with store.transaction(write=True) as db:
        existing = db.execute("SELECT * FROM replay_runs WHERE id=?", (run_id,)).fetchone()
        if existing and (existing["source_sha256"] != source_hash or existing["cutoff"] != timestamp(at)):
            raise ValueError("immutable_replay_run_conflict")
        if not existing:
            db.execute("INSERT INTO replay_runs VALUES(?,?,?,?,?)", (run_id,source_hash,0,len(prepared),timestamp(at)))
    if batch_size<1:raise ValueError("positive_batch_size_required")
    while True:
        failed_record=None
        try:
            with store.transaction(write=True) as db:
                cursor = db.execute("SELECT cursor FROM replay_runs WHERE id=?", (run_id,)).fetchone()[0]
                if cursor == len(prepared):break
                changed={};end=min(cursor+batch_size,len(prepared))
                # One arrival group is atomic, including correction metadata
                # whose stable ID sorts before its equal-time predecessor.
                while end<len(prepared) and prepared[end][0].available_at==prepared[end-1][0].available_at:end+=1
                remaining=list(prepared[cursor:end])
                while remaining:
                    pending_ids={record.record_id for record,_ in remaining}
                    ready=next(((record,raw) for record,raw in remaining if not ({record.supersedes,record.duplicate_of}-{None}) & pending_ids),remaining[0])
                    record,raw=ready;failed_record=ready
                    inserted=append_event(db,record,raw)
                    db.execute("INSERT INTO ingestion_receipts VALUES(?,?,?,?,?)",(run_id,record.record_id,digest(raw),"accepted" if inserted else "repeated","validated"))
                    if inserted:changed[record.patient_id]=changed.get(record.patient_id,0)+1
                    remaining.remove(ready)
                for patient_id in sorted(changed):apply_current_state(db,patient_id,at,advance_by=changed[patient_id])
                db.execute("UPDATE replay_runs SET cursor=? WHERE id=?",(end,run_id))
                if fault:fault("before_replay_commit")
        except ValueError as error:
            # Reject the batch atomically, then retain its failed admission
            # receipt in a distinct transaction instead of rolling it away.
            if failed_record:
                record,raw=failed_record
                with store.transaction(write=True) as db:
                    db.execute("INSERT OR IGNORE INTO ingestion_receipts VALUES(?,?,?,?,?)",(run_id,record.record_id,digest(raw),"rejected",str(error)))
            raise
    return {"run_id":run_id,"source_sha256":source_hash,"records":len(prepared),"status":"completed"}
