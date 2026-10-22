"""Private fixed medication/support extension; no controller or learner imports."""
import hashlib
import json
from .restricted import _generate

VERSION = 'poc-longitudinal-v2'


def medication_taken(seed, index, day):
    key = json.dumps([VERSION, seed, index, day, 'medication-adherence'], separators=(',', ':'))
    number = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big') >> 11
    return (number + .5) / 2**53 < .85


def schedule(value, through, options, *, washout=False):
    if not isinstance(value, list) or len(value) > 84:
        raise ValueError('invalid_v2_schedule')
    previous = -1
    for row in value:
        if (not isinstance(row, dict) or set(row) != {'day', 'option', 'assignment_id'} or type(row['day']) is not int
                or not previous < row['day'] < through or row['option'] not in options
                or (row['option'] is None and (not washout or row['assignment_id'] is not None))
                or (row['option'] is not None and (not isinstance(row['assignment_id'], str) or not row['assignment_id']))):
            raise ValueError('invalid_v2_schedule')
        previous = row['day']
    return value


class Extension:
    def __init__(self, request):
        self.seed, self.index = request['seed'], request['index']
        self.medications = schedule(request['medications'], request['through_day'], {'MED_A', 'MED_B', None}, washout=True)
        self.support = schedule(request['support'], request['through_day'], {'support_prompt', 'no_prompt'})
        if request['family'] == 'nof1_med' and any(s['option'] != 'no_prompt' for s in self.support):
            raise ValueError('nof1_support_must_remain_no_prompt')
        if request['family'] == 'support' and self.medications:
            raise ValueError('support_cohort_cannot_receive_medication')
        prompts = {s['day'] + 1 for s in self.support if s['option'] == 'support_prompt'}
        if any(day-1 in prompts or sum(day-6 <= old <= day for old in prompts) > 3 for day in prompts):
            raise ValueError('support_burden_envelope_exceeded')
        self.prompts = prompts
        self.ma = self.mb = self.rebound = 0.
        self.previous_assigned = None
        self.current = None
        self.taken = False

    def medication_burden(self, day, response):
        self.current = next((a for a in reversed(self.medications) if a['day'] < day), None)
        assigned = self.current['option'] if self.current else None
        self.taken = assigned is not None and medication_taken(self.seed, self.index, day)
        self.ma = .5*self.ma + .5*int(self.taken and assigned == 'MED_A')
        self.mb = .5*self.mb + .5*int(self.taken and assigned == 'MED_B')
        self.rebound = .5*self.rebound + int(self.previous_assigned == 'MED_B' and assigned != 'MED_B')
        self.previous_assigned = assigned
        return -1.5*response*self.ma - 2.5*response*self.mb + self.rebound

    def support_quality(self, day, response):
        prior = sum(day-6 <= old < day for old in self.prompts)
        return float(day in self.prompts) * (.6*response - .1*prior)

    def deliveries(self, day, add):
        if self.current and self.current['option'] is not None:
            add('delivery', day, dict(assignment_id=self.current['assignment_id'], option=self.current['option'],
                stage='taken' if self.taken else 'not_taken', adherence=float(self.taken), rescue=False, protocol_deviations=[]), delivery=True, suffix='-medication')
        support = next((s for s in self.support if s['day'] == day-1), None)
        if support:
            add('delivery', day, dict(assignment_id=support['assignment_id'], option=support['option'],
                stage='delivered', adherence=1., rescue=False, protocol_deviations=[]), delivery=True, suffix='-support')


def generate(request):
    if (set(request) != {'law_version', 'family', 'seed', 'index', 'patient_id', 'through_day', 'actions', 'medications', 'support'}
            or request['law_version'] != VERSION or request['family'] not in {'nof1_med', 'support'}):
        raise ValueError('invalid_v2_generator_request')
    # The unchanged v1 validator and exogenous streams remain authoritative for
    # base request bounds/equations. Extra streams never consume those streams.
    base = {k: request[k] for k in ('seed', 'index', 'patient_id', 'through_day', 'actions')}
    if any(a.get('option') != 'behavioral_continue' for a in base['actions']):
        raise ValueError('v2_background_must_remain_continuation')
    return _generate(base, (2, 4), protocol=Extension(request))
