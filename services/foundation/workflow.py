"""Foundation presentation composes the accepted domain, without an estimator."""
from datetime import datetime, timedelta
import json
from contracts.domain.boundaries import ObservedHistory, lineage_heads, visible_records
from contracts.domain.entities import DecisionSnapshot, Workflow
from .store import canonical, digest, timestamp, instant

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


def patient_clock(patient, fallback):
    simulation = json.loads(patient['state_json']).get('simulation')
    return instant(simulation['origin']) + timedelta(days=simulation['day']) if simulation else fallback


def preserve_simulation(previous, state):
    if 'simulation' in previous:
        state['simulation'] = previous['simulation']
    return state


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
    if any(r['schema_version'] == '2.1.0' for r in records):
        from contracts.domain.protocol import ObservedHistoryV21
        return ObservedHistoryV21.model_validate_json(canonical(dict(schema_version='2.1.0', synthetic=True, kind='observed_history', patient_id=patient_id, records=records)))
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
    receipt_at = at
    at = patient_clock(row, at)
    state = json.loads(row["state_json"])
    from .live_journal import initialize_journal, overlay, summary, dispute_reviews, active_episodes
    initialize_journal(db,patient_id,receipt_at)
    state = overlay(db,patient_id,state)
    if state.get('simulation',{}).get('nof1'):
        from .nof1 import reconcile
        state=reconcile(db,row,state,receipt_at)
    db.execute('UPDATE patients SET state_json=? WHERE id=?',(canonical(state),patient_id))
    # Non-live mutations invalidate review usability without an extra version bump.
    # A freshly recorded review targets this exact resulting version and is retained.
    for episode in active_episodes(db,patient_id):
        review_id=episode['data'].get('current_review_id')
        if review_id:
            review=db.execute('SELECT payload FROM live_hold_reviews WHERE id=?',(review_id,)).fetchone()
            saved=json.loads(review[0])
            expected=dict(saved['input_versions']);expected.update(version=expected['version']+1,state_version=expected['state_version']+1,eligibility_version=expected['eligibility_version']+1)
            if any(row[k]!=v for k,v in expected.items()):
                dispute_reviews(db,patient_id,receipt_at,digest(canonical([patient_id,row['version'],state])))
                break
    identifier = "decision-" + digest(canonical([patient_id, row["version"], timestamp(at)]))[:32]
    actions = ['behavioral_continue', 'behavioral_escalate'] if 'simulation' in state else ["MED_A", "MED_B", "behavioral_continue", "behavioral_escalate", "usual_care"]
    eligibility = [dict(action=action, status="excluded" if state["workflow"]["hold_reasons"] else "eligible",
                        reasons=state["workflow"]["hold_reasons"]) for action in actions]
    nof1=None
    if state.get('simulation',{}).get('family')=='nof1_med':
        from .nof1 import readiness
        from contracts.domain.protocol import NOF1_REF
        reasons=readiness(db,row,state,at,receipt_at)
        eligibility.extend(dict(action=action,status='requires_prescriber_review' if reasons else 'eligible',reasons=reasons)
                           for action in ('MED_A','MED_B'))
        eligibility.append(dict(action='no_prompt',status='excluded' if state['workflow']['hold_reasons'] else 'eligible',reasons=state['workflow']['hold_reasons']))
        nof1=dict(template=NOF1_REF,
            readiness_reasons=reasons,review_assertions_are_synthetic=True,
            loop=state['simulation'].get('nof1'),analysis_status='unavailable_methods_pending')
    snapshot = DecisionSnapshot.model_validate_json(canonical(dict(**record_header(identifier, patient_id, at),
        kind="decision_snapshot", cutoff=timestamp(at), patient_version=row["version"], state_version=row["state_version"],
        consent_version=row["consent_version"], eligibility_version=row["eligibility_version"], workflow=state["workflow"],
        view=dict(patient_id=patient_id, mode="current", snapshot_id=None), eligibility=eligibility,
        outcome="Ordinary synthetic care; statistical estimates unavailable", horizon_days=42,
        estimand=reference("EST-VISIT"), model=reference("foundation-no-estimator", "No statistical engine implemented"),
        posterior=None, evidence=[], policy=SUPPORT)))
    projected = history(db, patient_id).project(at).model_dump(mode="json")
    options = eligibility if state["stage"] != "ASSIGN-07" else [e for e in eligibility if e["action"].startswith("behavioral_")]
    if nof1 is not None:options=[e for e in options if e['action']=='behavioral_continue']
    ordinary = state["stage"] in ("ASSIGN-02", "ASSIGN-07") and state["workflow"]["data_readiness"] == "ready" and not state["workflow"]["hold_reasons"]
    if state.get('simulation', {}).get('day', 0) >= 84:
        ordinary = False
    display = dict(patient_id=patient_id, name=row["name"], stage=state["stage"], stage_label=STAGES[state["stage"]][0],
                   snapshot=snapshot.model_dump(mode="json"), projection=projected, plan=state["plan"],
                   options=options, permissions=dict(approve_ordinary=ordinary, request_review=True, randomize=False, estimate=False),
                   engines=dict(bayesian="unavailable", nof1="unavailable", escalation="unavailable", support="unavailable"),
                   estimates=dict(status="pending", reason="Statistical engines are not implemented; no treatment ranking is available"),
                   labels=["Synthetic demonstration", "No acute clinical monitoring"],
                   version_status="Foundation contract consumer; downstream G2-G5 engines pending")
    display['live_safety_summary']=summary(db,patient_id)
    # Only a NEW decision may freeze a saved analysis reference. Older decision
    # and bundle bytes are immutable; asynchronous completion never rewrites them.
    analysis=db.execute("SELECT job_id,cutoff,result_json,input_sha256 FROM analysis_attempts WHERE patient_id=? AND status='completed' ORDER BY created_at DESC,rowid DESC LIMIT 1",(patient_id,)).fetchone()
    if analysis:
        display['analysis_reference']=dict(id=analysis['job_id'],cutoff=analysis['cutoff'],input_sha256=analysis['input_sha256'],
            stale=instant(analysis['cutoff'])!=at,result=json.loads(analysis['result_json']))
    if 'simulation' in state:
        display['simulation'] = state['simulation']
        display['version_status'] = 'Generated synthetic PoC; observed-only V0 on demand; randomized protocols pending'
        display['engines']['bayesian']='poc-visit-v1 on demand after day14'
        display['estimates']['reason']='Visit analysis is available in Analysis; ordinary options have no superiority ranking'
        display['labels'].append('Generated longitudinal observations; fictional clock')
        display['plan'] = state['plan']
    if nof1 is not None:
        display['nof1']=nof1
        display['engines']['nof1']='Fixed synthetic physician loop; analysis methods unavailable'
        display['estimates']['reason']='N0/N1 analysis is unavailable pending accepted methods; no estimated winner'
    encoded = canonical(display)
    db.execute("INSERT INTO decisions VALUES (?,?,?,?,?)", (identifier, patient_id, snapshot.model_dump_json(), encoded, digest(encoded)))
    db.execute("UPDATE patients SET current_decision=?,cutoff=? WHERE id=?", (identifier, timestamp(at), patient_id))
    return identifier
