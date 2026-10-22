"""Frozen restricted law v1. See poc-generator-interface-20261021.md.

Only generate()'s observed product crosses the private process boundary.
Keyed exogenous streams do not depend on choices, UUIDs or request batching.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math

VERSION = 'poc-longitudinal-v1'
START = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def uniform(seed, index, day, process):
    key = json.dumps([VERSION, seed, index, day, process], separators=(',', ':'))
    number = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big') >> 11
    return (number + .5) / (2 ** 53)


def normal(seed, index, day, process):
    u = uniform(seed, index, day, process + '-u')
    v = uniform(seed, index, day, process + '-v')
    return math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * v)


def clip(value, low, high):
    return min(high, max(low, value))


def generate(request):
    if set(request) != {'seed', 'index', 'patient_id', 'through_day', 'actions'}:
        raise ValueError('invalid_generator_request')
    seed, index, through = (request[k] for k in ('seed', 'index', 'through_day'))
    if any(type(v) is not int for v in (seed, index, through)) or not (0 <= seed <= 2147483647 and 0 <= index < 24 and 0 <= through <= 84):
        raise ValueError('invalid_generator_bounds')
    patient = request['patient_id']
    if not isinstance(patient, str) or not 1 <= len(patient) <= 90 or not all(c.isalnum() or c in '-_' for c in patient):
        raise ValueError('invalid_patient_id')
    actions = request['actions']
    if not isinstance(actions, list) or len(actions) > 84:
        raise ValueError('invalid_actions')
    previous = -1
    for action in actions:
        if (set(action) != {'day', 'option', 'assignment_id'} or type(action['day']) is not int
                or not previous < action['day'] < through or action['option'] not in ('behavioral_continue', 'behavioral_escalate')
                or not isinstance(action['assignment_id'], str) or not action['assignment_id']):
            raise ValueError('invalid_action_schedule')
        previous = action['day']
    records = []

    def add(kind, day, values, *, delivery=False):
        at = START + timedelta(days=day, minutes=-1)
        if delivery:
            at = START + timedelta(days=day - 1, hours=8)
        identifier = f'{patient}-{kind}-{day}'
        envelope = dict(schema_version='1.0.0', synthetic=True, record_id=identifier, patient_id=patient,
            event_at=at.isoformat(), recorded_at=at.isoformat(), available_at=at.isoformat(),
            lineage_id=identifier, revision=1, supersedes=None, duplicate_of=None, record_status='active', kind=kind, **values)
        raw = json.dumps(envelope, sort_keys=True, separators=(',', ':'), allow_nan=False)
        envelope['source'] = dict(id=VERSION, version='1.0.0', adapter='simulation', raw_sha256=hashlib.sha256(raw.encode()).hexdigest())
        records.append(dict(record=envelope, raw_source=raw))

    baseline = 16 + 6 * uniform(seed, index, 0, 'baseline')
    response = .8 + .4 * uniform(seed, index, 0, 'response')
    name = ['Avery', 'Morgan', 'Riley', 'Jordan', 'Casey', 'Quinn'][int(uniform(seed, index, 0, 'name') * 6)]
    add('patient', 0, dict(covariates=[], diagnosis_context='Fictional outpatient leukemia chemotherapy',
        clinical_context='Stable synthetic reference setting', preferences=['Discuss treatment burden'], goals=['Improve reported sleep'],
        baseline_eligibility=['Behavioral plans reviewed eligible'], care_team=['synthetic-care-team'], timezone='UTC'))
    error = carry_continue = carry_escalate = 0
    burdens = []
    for day in range(-13, through + 1):
        action = next((a for a in reversed(actions) if a['day'] < day), None)
        taken = action is not None and uniform(seed, index, day, 'adherence') < .85
        carry_continue = .65 * carry_continue + .35 * int(taken and action['option'] == 'behavioral_continue')
        carry_escalate = .8 * carry_escalate + .2 * int(taken and action['option'] == 'behavioral_escalate')
        error = .55 * error + .8 * normal(seed, index, day, 'process')
        burden = baseline + .55 * math.sin(2 * math.pi * day / 21) + error - 2 * response * carry_continue - 4 * response * carry_escalate
        burdens.append(burden)
        if day > 0:
            if action:
                add('delivery', day, dict(assignment_id=action['assignment_id'], option=action['option'],
                    stage='taken' if taken else 'not_taken', adherence=float(taken), rescue=False, protocol_deviations=[]), delivery=True)
            missing = uniform(seed, index, day, 'missing') < .1
            add('daily_report', day, dict(sleep_quality=None if missing else round(clip(10 - burden / 3 + .45 * normal(seed, index, day, 'quality'), 0, 10), 3),
                function=None if missing else round(clip(9 - burden / 4 + .5 * normal(seed, index, day, 'function'), 0, 10), 3),
                diary_sleep_minutes=None if missing else round(clip(470 - 8 * burden + 20 * normal(seed, index, day, 'minutes'), 0, 1440), 1),
                adverse_symptoms=[], goals=['Improve reported sleep'], burden=None if missing else float(bool(action)),
                missingness='missing' if missing else 'observed'))
        if day >= 0 and day % 14 == 0:
            total = int(clip(math.floor(sum(burdens[-14:]) / 14 + normal(seed, index, day, 'isi') + .5), 0, 28))
            items = [total // 7 + int(i < total % 7) for i in range(7)]
            end = START + timedelta(days=day, hours=-1)
            add('isi', day, dict(instrument_version='ISI-7-synthetic-14d-v1', recall_days=14,
                recall_start=(end - timedelta(days=14)).isoformat(), recall_end=end.isoformat(), items=items))
    return dict(name=f'Synthetic {name} {index + 1:02d}', records=records)
