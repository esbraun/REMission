"""Append-only operational journal and inclusive persisted safety overlay."""
import json
import uuid
from contracts.service.live_safety import LiveHoldFact
from .store import canonical, digest, instant, timestamp


def control(db):
    return db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone()


def receive(db, at):
    row = control(db)
    if at < instant(row['last_receipt_at']):
        raise ValueError('service_clock_regression')
    db.execute('UPDATE service_control SET last_receipt_at=? WHERE singleton=1', (timestamp(at),))


def append_fact(db, patient_id, operation_id, at, operation, *, event_at=None):
    c = control(db)
    journal = db.execute('SELECT journal_id FROM live_patient_journals WHERE patient_id=?',(patient_id,)).fetchone()
    if journal is None:
        raise ValueError('patient_journal_uninitialized')
    prior = db.execute('SELECT patient_sequence,payload_sha256,received_at FROM live_safety_facts WHERE patient_id=? ORDER BY patient_sequence DESC LIMIT 1',(patient_id,)).fetchone()
    if prior and instant(prior['received_at']) > at:
        raise ValueError('service_clock_regression')
    value = dict(schema_version='1.0.0',kind='live_hold_fact',synthetic=True,patient_id=patient_id,
        journal_id=journal[0],operation_id=operation_id,patient_sequence=prior[0]+1 if prior else 1,
        previous_fact_sha256=prior[1] if prior else None,authority_generation=c['authority_generation'],
        authority_sha256=c['authority_sha256'],review_rules_sha256=c['review_rules_sha256'],
        event_at=timestamp(event_at or at),recorded_at=timestamp(at),available_at=timestamp(at),operation=operation)
    fact = LiveHoldFact.model_validate_json(canonical(value))
    encoded = canonical(fact.model_dump(mode='json'))
    db.execute('INSERT INTO live_safety_facts VALUES(?,?,?,?,?,?)',(patient_id,fact.patient_sequence,operation_id,timestamp(at),encoded,digest(encoded)))
    return fact


def initialize_journal(db, patient_id, at):
    if db.execute('SELECT 1 FROM live_patient_journals WHERE patient_id=?',(patient_id,)).fetchone():
        return
    db.execute('INSERT INTO live_patient_journals VALUES(?,?)',(patient_id,'journal-'+uuid.uuid4().hex))
    append_fact(db,patient_id,'baseline-'+uuid.uuid4().hex,at,
        dict(type='baseline',scope='independent_live_holds',active_episodes=[]))


def active_episodes(db, patient_id):
    return [dict(**dict(r),data=json.loads(r['payload'])) for r in db.execute(
        "SELECT * FROM live_hold_episodes WHERE patient_id=? AND status='active' ORDER BY id,generation",(patient_id,))]


def summary(db, patient_id):
    c = control(db)
    sequence = db.execute('SELECT max(patient_sequence) FROM live_safety_facts WHERE patient_id=?',(patient_id,)).fetchone()[0]
    return dict(contract='LIVE-HOLD-01',schema_version='1.0.0',authority_generation=c['authority_generation'],
        authority_sha256=c['authority_sha256'],review_rules_sha256=c['review_rules_sha256'],patient_sequence=sequence or 0,
        active_episodes=[dict(episode_id=e['id'],generation=e['generation'],trigger_set_sha256=e['data']['trigger_set_sha256'],
            obligation_set_sha256=e['data']['obligation_set_sha256'],task_ids=e['data']['task_ids']) for e in active_episodes(db,patient_id)])


def overlay(db, patient_id, state):
    episodes = active_episodes(db,patient_id)
    if episodes:
        state['stage']='ASSIGN-09'
        workflow=state['workflow']
        workflow.update(clinical='clinical_hold',data_readiness='stale',support_mode='paused')
        workflow['hold_reasons']=sorted(set(workflow['hold_reasons']) | {r for e in episodes for r in e['data']['reason_codes']})
    return state


def dispute_reviews(db, patient_id, at, context_sha256):
    for episode in active_episodes(db,patient_id):
        e=episode['data']
        if e.get('current_review_id'):
            op='dispute-'+uuid.uuid4().hex
            append_fact(db,patient_id,op,at,dict(type='evidence_disputed',episode_id=episode['id'],generation=episode['generation'],
                reason='current_context_changed',affected_refs=[],changed_context_sha256=context_sha256))
            e['current_review_id']=None
            db.execute('UPDATE live_hold_episodes SET payload=?,last_operation=? WHERE id=? AND generation=?',
                (canonical(e),op,episode['id'],episode['generation']))
