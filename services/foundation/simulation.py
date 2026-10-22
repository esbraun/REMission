"""Account-owned PoC orchestration. This module contains no generator law."""
from datetime import timedelta
import json
import urllib.error
import urllib.request
import uuid
from pydantic import TypeAdapter
from contracts.domain.entities import ObservedRecord
from .store import canonical, digest, instant, timestamp

START = '2026-01-01T12:00:00+00:00'
LAW = 'poc-longitudinal-v1'
OPTIONS = ('behavioral_continue', 'behavioral_escalate')
ADAPTER = TypeAdapter(ObservedRecord)


class SimulationError(Exception):
    def __init__(self, code, detail, status=409):
        self.code, self.detail, self.status = code, detail, status


def product(settings, simulation, patient_id, through):
    if not settings.generator_url:
        raise SimulationError('generator_unavailable', 'The private generator is unavailable; retry after it is started.', 503)
    payload = dict(seed=simulation['seed'], index=simulation['index'], patient_id=patient_id,
                   through_day=through, actions=simulation['actions'])
    if simulation['law_version'] == 'poc-longitudinal-v2':
        payload.update(law_version=simulation['law_version'], family=simulation['family'],
                       medications=simulation['medications'], support=simulation['support'])
    try:
        request = urllib.request.Request(settings.generator_url + '/generate', data=canonical(payload).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read(524289)
        if len(raw) > 524288:
            raise ValueError('oversized_product')
        value = json.loads(raw)
        if set(value) != {'name', 'records'} or not isinstance(value['name'], str) or not 1 <= len(value['name']) <= 100 or not isinstance(value['records'], list):
            raise ValueError('invalid_product')
        return value
    except (OSError, ValueError) as error:
        raise SimulationError('generator_failed', 'Generation failed. No simulation time or observations were committed; retry the original action.', 503) from error


def persist_product(db, value, patient_id, *, after, cutoff, received_at, actions=(), simulation=None):
    """Admit observed records only, preserving synthetic availability and real receipt."""
    from .workflow import history
    allowed = {'patient', 'daily_report', 'isi', 'delivery'}
    inserted = 0
    counts = {}
    actual = set()
    v2 = simulation is not None and simulation['law_version'] == 'poc-longitudinal-v2'
    if v2:
        from contracts.domain.protocol import RECORD_ADAPTER_V21
    adapter = RECORD_ADAPTER_V21 if v2 else ADAPTER
    law = 'poc-longitudinal-v2' if v2 else LAW
    try:
        for entry in value['records']:
            if set(entry) != {'record', 'raw_source'}:
                raise ValueError('invalid_observed_product')
            record = adapter.validate_json(canonical(entry['record']))
            if record.patient_id != patient_id or record.kind not in allowed or record.source.id != law:
                raise ValueError('unexpected_observed_product')
            if v2 and (record.source.version != '2.0.0' or record.source.adapter != ('patient_report' if record.kind == 'daily_report' else 'simulation')):
                raise ValueError('unqualified_v2_channel')
            if record.available_at >= cutoff:
                raise ValueError('future_product_record')
            if after is not None and record.event_at <= after:
                continue
            raw = entry['raw_source'].encode()
            source = json.loads(raw)
            if 'source' in source or digest(raw) != record.source.raw_sha256:
                raise ValueError('invalid_raw_product')
            source['source'] = record.source.model_dump(mode='json')
            if adapter.validate_json(canonical(source)) != record:
                raise ValueError('raw_product_mismatch')
            encoded = canonical(record.model_dump(mode='json'))
            db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (record.record_id, patient_id, record.kind, record.lineage_id, record.revision, record.duplicate_of,
                 encoded, digest(encoded), raw, digest(raw), timestamp(record.event_at), timestamp(record.recorded_at),
                 timestamp(record.available_at), 3 if record.kind == 'daily_report' else 5, timestamp(received_at)))
            inserted += 1
            counts[record.kind] = counts.get(record.kind, 0) + 1
            actual.add((record.kind, record.event_at, record.assignment_id if record.kind == 'delivery' else None))
            if record.kind == 'delivery':
                night = (record.event_at - instant(START)).days + 1
                schedule = actions
                if v2 and record.option in ('MED_A', 'MED_B', 'support_prompt', 'no_prompt'):
                    schedule = simulation['medications'] if record.option.startswith('MED_') else simulation['support']
                    owned = db.execute('SELECT payload FROM events WHERE id=? AND patient_id=? AND kind=?', (record.assignment_id, patient_id, 'assignment')).fetchone()
                    if owned is None:
                        raise ValueError('unowned_protocol_delivery')
                    assigned = ADAPTER.validate_json(owned[0])
                    if assigned.option != record.option or assigned.event_at > record.event_at:
                        raise ValueError('protocol_delivery_assignment_mismatch')
                action = next((a for a in reversed(schedule) if a['day'] < night), None)
                if record.option in ('support_prompt', 'no_prompt') and action and action['day'] != night-1:
                    action = None
                if action is None or record.assignment_id != action['assignment_id'] or record.option != action['option']:
                    raise ValueError('unassigned_delivery')
        history(db, patient_id)  # Full lineage and no-post-death invariant before commit.
        if not inserted:
            raise ValueError('empty_product')
        start = instant(START)
        last_day = (cutoff - start).days
        first_day = (after - start).days + 1 if after is not None else 0
        expected_reports = last_day - max(1, first_day) + 1
        expected_isi = sum(day % 14 == 0 for day in range(first_day, last_day + 1))
        expected = set()
        for day in range(first_day, last_day + 1):
            at = start + timedelta(days=day, minutes=-1)
            if day == 0:
                expected.add(('patient', at, None))
            if day > 0:
                expected.add(('daily_report', at, None))
                schedules = [(actions, False), (simulation['medications'], False), (simulation['support'], True)] if v2 else [(actions, False)]
                for schedule, one_night in schedules:
                    assignment = next((a for a in reversed(schedule) if a['day'] < day), None)
                    if assignment and assignment['option'] is not None and (not one_night or assignment['day'] == day-1):
                        expected.add(('delivery', start + timedelta(days=day - 1, hours=8), assignment['assignment_id']))
            if day % 14 == 0:
                expected.add(('isi', at, None))
        if (counts.get('daily_report', 0) != max(0, expected_reports)
                or counts.get('isi', 0) != expected_isi
                or counts.get('patient', 0) != int(after is None) or actual != expected or len(actual) != inserted):
            raise ValueError('incomplete_product')
    except (ValueError, TypeError, KeyError) as error:
        raise SimulationError('invalid_generator_product', 'Generator output failed observed-data validation; no changes were committed.', 503) from error
    return inserted


def generate_panel(db, settings, owner, seed, count, now, *, protocol=None):
    from .workflow import create_decision, state_for
    from .live_journal import initialize_journal
    panel_id = 'panel-' + uuid.uuid4().hex
    identifiers = []
    for index in range(count):
        identifier = 'POC-' + uuid.uuid4().hex
        simulation = dict(panel_id=panel_id, seed=seed, index=index, day=0, horizon_days=84,
                          origin=START, law_version=LAW, actions=[])
        if protocol is not None:
            # Selection never grants consent/approval or starts a controller.
            simulation.update(law_version='poc-longitudinal-v2', family=protocol.family,
                law=protocol.law.model_dump(mode='json'), protocol=protocol.protocol.model_dump(mode='json'),
                medications=[], support=[], protocol_status='not_activated')
        generated = product(settings, simulation, identifier, 0)
        state = state_for('ASSIGN-02')
        state['simulation'] = simulation
        db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (identifier, owner, generated['name'], 1, 1, 1, 1, canonical(state), None, START))
        initialize_journal(db, identifier, now)
        persist_product(db, generated, identifier, after=None, cutoff=instant(START), received_at=now, simulation=simulation)
        create_decision(db, identifier, now)
        identifiers.append(identifier)
    return dict(status='generated', panel_id=panel_id, seed=seed, count=count, patient_ids=identifiers)


def advance(db, settings, patient, expected_version, mode, now):
    from .workflow import create_decision, current_safety, patient_clock, state_for
    from .live_journal import active_episodes
    state = json.loads(patient['state_json'])
    simulation = state.get('simulation')
    if not simulation:
        raise SimulationError('not_generated', 'Generate a patient panel before advancing simulated time.')
    if patient['version'] != expected_version:
        raise SimulationError('stale_simulation', 'Patient information changed. Refresh and review before advancing.')
    if state['workflow']['hold_reasons'] or active_episodes(db, patient['id']):
        raise SimulationError('clinical_hold', 'Clinical hold blocks simulated advancement; review the hold first.')
    if any(r.kind == 'intercurrent_event' and r.event_type == 'death' for r in current_safety(db, patient['id'], now)):
        raise SimulationError('outside_scope', 'No outcomes can be generated after death.')
    day = simulation['day']
    if day >= 84:
        raise SimulationError('simulation_complete', 'The 84-day demonstration is complete.')
    target = min(84, day + 1 if mode == 'day' else (day // 14 + 1) * 14)
    cutoff = instant(simulation['origin']) + timedelta(days=target)
    generated = product(settings, simulation, patient['id'], target)
    count = persist_product(db, generated, patient['id'], after=patient_clock(patient, now), cutoff=cutoff, received_at=now, actions=simulation['actions'], simulation=simulation)
    if settings.fault:
        settings.fault('after_simulation_events')
    simulation['day'] = target
    if target % 14 == 0:
        new_state = state_for('ASSIGN-10' if target == 84 else 'ASSIGN-02')
        new_state.update(plan=state['plan'], simulation=simulation)
        state = new_state
    db.execute('UPDATE patients SET state_json=?,version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1 WHERE id=?',
               (canonical(state), patient['id']))
    create_decision(db, patient['id'], now)
    return dict(status='advanced', day=target, cutoff=timestamp(cutoff), records_added=count)


def assign(db, patient, state, approval, now, received_at):
    """Persist the ordinary assignment separately from approval and later delivery."""
    from .workflow import record_header, SUPPORT
    simulation = state['simulation']
    if simulation['law_version'] == 'poc-longitudinal-v2' and approval.option != 'behavioral_continue':
        raise SimulationError('frozen_background', 'Protocol patients retain the continuing behavioral background.')
    if simulation['day'] >= 84:
        raise SimulationError('simulation_complete', 'The 84-day demonstration is complete.')
    if simulation['actions'] and simulation['actions'][-1]['day'] == simulation['day']:
        raise SimulationError('plan_already_chosen', 'One plan is already approved for this day. Advance before choosing again.')
    identifier = 'assignment-' + uuid.uuid4().hex
    record = dict(**record_header(identifier, patient['id'], now), kind='assignment',
        decision_id=approval.decision_id, approval_id=approval.record_id, option=approval.option,
        experimental=False, component=None, probability=None, seed=None, support_policy=SUPPORT,
        patient_blinded=False, clinician_blinded=False, clinician_override=None, override_reason=None)
    raw = canonical({k: v for k, v in record.items() if k != 'source'}).encode()
    record['source']['raw_sha256'] = digest(raw)
    typed = ADAPTER.validate_json(canonical(record))
    encoded = canonical(typed.model_dump(mode='json'))
    db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (identifier, patient['id'], 'assignment', identifier, 1, None, encoded, digest(encoded), raw, digest(raw),
         timestamp(now), timestamp(now), timestamp(now), 5, timestamp(received_at)))
    simulation['actions'].append(dict(day=simulation['day'], option=approval.option, assignment_id=identifier))
    state['plan'].update(decided_at=timestamp(now), effective_at=timestamp(now + timedelta(hours=8)), assignment_id=identifier,
                         received_at=timestamp(received_at))
