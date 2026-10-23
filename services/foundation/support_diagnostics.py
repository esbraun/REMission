"""Opt-in fixed public intake milestones; no data, SQL or exception logging."""
import json
import math
import time

KIND='s1_intake_diagnostic'
MAX_EVENTS=512
MAX_BYTES=49152  # Includes newline and the reserved terminal diagnostic summary.
MAX_ROW_BYTES=384
MAX_STDOUT_BYTES=131072
MAX_PROGRESS_BYTES=320
MAX_RESULT_BYTES=32768
STAGES=frozenset(('post_before','post_return','status_checked','json_decoded','response_checked','counts_before','counts_after',
    'count_before','count_after','endpoint_before','endpoint_return','admit_before','verify_before','index_after',
    'trajectory_before','history_after','ledgers_after','completions_after','cut_before','cut_after',
    'closures_before','closures_after','trajectory_after','supplement_before','supplement_after',
    'manifest_before','manifest_after','inventory_before','inventory_after','verify_after',
    'publication_before','publication_after','transaction_acquire','transaction_enter','owners_after',
    'idempotent_pending','receipt_after','entries_after','artifacts_after','precommit','commit_returned','summary'))
COARSE=frozenset(('post_before','post_return','status_checked','json_decoded','response_checked','counts_before','counts_after',
    'endpoint_before','endpoint_return','admit_before','verify_before','verify_after','transaction_acquire',
    'transaction_enter','owners_after','idempotent_pending','precommit','commit_returned','summary'))
LIMITS=dict(trajectory=24,cut=3,table=9,count_pass=8,reads=10000000,bytes=2147483648,hits=10000000,
    visits=100000,files=100000,attempted=MAX_EVENTS,emitted=MAX_EVENTS,suppressed=1000000,omitted=1000000)


def validate_row(value):
    """Strict host/payload shared decoder; never project unknown raw fields."""
    required={'kind','stage','request','seconds'}
    if (type(value) is not dict or not required<=value.keys() or value.keys()-required-LIMITS.keys()
            or value.get('kind')!=KIND or type(value.get('stage')) is not str or value['stage'] not in STAGES
            or type(value.get('request')) is not int or not 1<=value['request']<=4
            or type(value.get('seconds')) not in (int,float) or not math.isfinite(value['seconds'])
            or not 0<=value['seconds']<=1200):
        raise ValueError('invalid_intake_diagnostic')
    for key,limit in LIMITS.items():
        if key in value and (type(value[key]) is not int or not 0<=value[key]<=limit):
            raise ValueError('invalid_intake_diagnostic')
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    if len(raw.encode())+1>MAX_ROW_BYTES:raise ValueError('invalid_intake_diagnostic')
    return raw


def observe(callback,stage,**values):
    # This catch belongs only to diagnostics. The independent fault callback,
    # verification and Store transaction exceptions retain their normal paths.
    if callback is not None:
        try:callback(stage,**values)
        except BaseException:pass


def parse_p2_stdout(raw):
    """The fixed one-shot operator accepts diagnostics, never unknown rows."""
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('duplicate_p2_field')
            result[key]=value
        return result
    def invalid(_value):raise ValueError('nonfinite_p2_output')
    if len(raw)>MAX_STDOUT_BYTES:raise ValueError('p2_stdout_bound')
    lines=raw.splitlines()
    if (not raw.endswith(b'\n') or not lines or len(lines)>MAX_EVENTS+151
            or any(not line.strip() for line in lines)):raise ValueError('invalid_p2_rows')
    rows=[json.loads(line,object_pairs_hook=pairs,parse_constant=invalid) for line in lines]
    final=rows[-1]
    if (len(lines[-1])+1>MAX_RESULT_BYTES or type(final) is not dict
            or final.get('status')!='genuine_p2_intake_idempotence_72_replays_pass'):
        raise ValueError('required_p2_result_absent')
    progress=[];diagnostics=[];diagnostic_bytes=0
    fields={'kind','phase','state','elapsed_seconds','completed_replays','member_id','mode','cutoff_day'}
    for line,value in zip(lines[:-1],rows[:-1]):
        if type(value) is not dict:raise ValueError('invalid_p2_row')
        if value.get('kind')=='p2_phase_progress':
            if (len(line)+1>MAX_PROGRESS_BYTES or value.keys()-fields or len(progress)>=150
                    or value.get('phase') not in ('bootstrap','initial_intake','idempotent_intake','saved_get')
                    or value.get('state') not in ('before','after')
                    or type(value.get('elapsed_seconds')) not in (int,float) or not math.isfinite(value['elapsed_seconds'])
                    or not 0<=value['elapsed_seconds']<=1200 or type(value.get('completed_replays')) is not int
                    or not 0<=value['completed_replays']<=72):
                raise ValueError('invalid_p2_progress')
            progress.append(value)
        elif value.get('kind')==KIND:
            validate_row(value);diagnostic_bytes+=len(line)+1
            if len(diagnostics)>=MAX_EVENTS or diagnostic_bytes>MAX_BYTES:raise ValueError('diagnostic_budget')
            diagnostics.append(value)
        else:raise ValueError('unknown_p2_row')
    return final,progress,diagnostics


class IntakeDiagnostics:
    """One serial diagnostic harness owns this sink; disabled in normal Settings."""
    def __init__(self,sink,*,clock=time.monotonic):
        self.sink=sink;self.clock=clock;self.request=0;self.attempted=0;self.emitted=0;self.bytes=0;self.suppressed=0;self.omitted=0;self.closed=False
        try:self.started=clock()
        except BaseException:self.started=None

    def begin_request(self):
        # Called by the frozen serial harness immediately before its existing
        # POST. No process/global state, HTTP header or environment enables it.
        self.request+=1
        self('post_before')

    def __call__(self,stage,**values):
        try:
            if self.closed:return
            if stage not in STAGES or values.keys()-LIMITS.keys():raise ValueError('invalid_intake_diagnostic')
            if self.request!=1 and stage not in COARSE:
                self.omitted=min(1000000,self.omitted+1);return
            seconds=round(self.clock()-self.started,6)
            value=dict(kind=KIND,stage=stage,request=self.request,seconds=seconds,**values)
            raw=validate_row(value);size=len(raw.encode())+1
            # Preserve room for one summary even if detailed rows are exhausted.
            reserve=0 if stage=='summary' else MAX_ROW_BYTES
            if self.attempted>=MAX_EVENTS-(stage!='summary') or self.bytes+size+reserve>MAX_BYTES:
                raise ValueError('diagnostic_budget')
            # A sink may write and then fail: reserve its entire row first.
            self.attempted+=1;self.bytes+=size
            self.sink(raw)
            self.emitted+=1
        except BaseException:self.suppressed=min(1000000,self.suppressed+1)

    def summary(self):
        self('summary',attempted=self.attempted,emitted=self.emitted,suppressed=self.suppressed,omitted=self.omitted)
        self.closed=True
