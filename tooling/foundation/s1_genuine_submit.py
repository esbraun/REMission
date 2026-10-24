"""Fixed future owned-container S1 submit/export, never a host app runner.

No Store/auth/scientific import or private read occurs before exact admission.
The existing application owns receipt, cohort and immutable-history authority.
"""
import argparse
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import re
import signal
import sys
import time

VOLUME='remission-s1-completion-261024-r1-positive'
NAMESPACE='remission-s1-genuine-submit-261024-r1'
KEY='s1-genuine-day84-261024-r1'
PRIVATE=Path('/data/s1-p3-submit-r1')
PUBLIC_STAGES=('session','login','csrf','submit','receipt_export')
PUBLIC=[]
PRIVATE_CAPS={'intent.json':8192,'submission-response.json':131072,'queued-export.json':16*1024*1024,
    'selection.json':8192,'public-result.json':4096}


def require(value):
    if not value:raise ValueError('S1 submit binding refused')


def admit(spec):
    require(type(spec) is dict and spec.get('kind')=='S1_GENUINE_SUBMIT_EXPORT_V1'
        and spec.get('executable') is True and spec.get('namespace')==NAMESPACE
        and spec.get('volume')==VOLUME and spec.get('key')==KEY
        and type(spec.get('cutoff_day')) is int and spec['cutoff_day']==84
        and type(spec.get('members')) is int and spec['members']==12
        and spec.get('no_claim_or_fit') is True)
    for key in ('store_instance','authority_generation','owner_id','archive_id','archive_export_id',
                'admission_sha256','source_commit','source_review','operation_review','root_go'):
        require(spec.get(key) is not None and spec[key]!='UNKNOWN')
    require(spec.get('request_seconds')==180 and spec.get('private_export_cap')==16*1024*1024)
    require(type(spec['authority_generation']) is int and spec['authority_generation']>=1)
    for key in ('source_commit','source_review','operation_review'):
        require(type(spec[key]) is str and re.fullmatch('[a-f0-9]{40}',spec[key]) is not None)
    for key in ('admission_sha256','root_go'):
        require(type(spec[key]) is str and re.fullmatch('[a-f0-9]{64}',spec[key]) is not None)
    return spec


def private_once(path,value,cap=16*1024*1024):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    require(len(raw)<=cap)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw)


def emit(value):
    # The later host receives only this fixed public file, never process logs.
    raw=json.dumps(value,sort_keys=True,allow_nan=False).encode()
    require(len(raw)<=512 and len(PUBLIC)<12)
    PUBLIC.append(value)


def submit_export(request,resolve,save,submission,key):
    """One POST; original receipt reconciliation is read-only and never resends."""
    save('intent.json',dict(key=key,submission=submission,status='submission_outcome_unknown'))
    job=None;response_confirmed=False
    try:
        response=request(submission,key)
        require(response['status_code']==202)
        value=response['payload'];job=value['id'];response_confirmed=True
    except Exception:
        # Do not print exception text or issue a second mutation. A unique
        # original owner/key receipt is the only route to resolve the job.
        pass
    if response_confirmed:save('submission-response.json',value)
    proof=resolve(key,submission,job)
    require(type(proof) is dict and proof.get('schema')=='support-s1-queued-request-v1'
        and proof.get('submission')==submission and proof.get('receipt',{}).get('key')==key
        and type(proof.get('attempt_id')) is str and bool(proof['attempt_id'])
        and type(proof.get('owner_id')) is str and bool(proof['owner_id'])
        and proof.get('active_attempts')==[dict(attempt_id=proof['attempt_id'],status='queued')]
        and (job is None or proof.get('attempt_id')==job))
    save('queued-export.json',proof)
    save('selection.json',dict(owner=proof['owner_id'],job=proof['attempt_id'],key=key,submission=submission))
    return dict(status='queued_export_saved',members=12,cutoff_day=84,
        response_confirmed=response_confirmed,original_receipt_resolved=True,claim=False,fit=False)


def invoke(client,stage,method,path,*,timer=180,**kwargs):
    require(stage in PUBLIC_STAGES)
    started=time.monotonic();received=None;decoded=None
    # Linux whole-process request/decode bound; local private receipt/export
    # persistence is additionally bounded by the common container watchdog.
    def expired(*_):os._exit(124)
    previous=signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,timer)
    try:
        response=getattr(client,method)(path,**kwargs);received=time.monotonic()
        require(response.status_code in (200,202))
        value=response.json();decoded=time.monotonic()
        return dict(status_code=response.status_code,payload=value)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
        emit(dict(kind='s1_p3_phase',stage=stage,seconds=time.monotonic()-started,
            response_seconds=None if received is None else received-started,
            decode_seconds=None if decoded is None else decoded-received))


def run(spec):
    admit(spec)
    class NoScience(importlib.abc.MetaPathFinder):
        def find_spec(self,name,path=None,target=None):
            if name.split('.')[0] in {'numpy','scipy','statsmodels','pymc','pytensor','arviz','methods','pandas','xarray'}:
                raise AssertionError('S1 submission cannot fit')
    sys.meta_path.insert(0,NoScience())
    # These are allowed ONLY in the later reviewed owned container.
    from fastapi.testclient import TestClient
    from services.foundation.app import create_app
    from services.foundation.configuration import environment_settings
    from services.foundation.analysis import export_queued_request
    from services.foundation.store import Store
    from contracts.domain.support_s1 import CONFIG_REF
    settings=environment_settings()
    require(settings.database==Path('/data/remission.sqlite') and settings.database.is_file()
        and settings.installed.control.database_instance_id==spec['store_instance']
        and settings.installed.control.authority_generation==spec['authority_generation']
        and settings.source_commit==spec['source_commit'] and not settings.installed.enabled)
    configured=settings.observed_archives
    require(spec['archive_export_id'] in configured)
    _,_,authority=configured[spec['archive_export_id']]
    require(authority.qualification_scope=='accepted_saved_producer' and len(authority.descriptor.members)==12
        and authority.admission_sha256==spec['admission_sha256'])
    credentials=json.loads(Path('/private/auth.json').read_bytes())['owner']
    store=Store(settings.database,settings.installed)
    PRIVATE.mkdir(mode=0o700,exist_ok=False)
    submission=dict(archive_id=spec['archive_id'],mode='S1',cutoff_day=84,
        configuration=CONFIG_REF,previous_attempt=None)
    with TestClient(create_app(settings),base_url=settings.origin) as client:
        session=invoke(client,'session','get','/api/session')['payload']
        login=invoke(client,'login','post','/api/login',json=credentials,
            headers={'Origin':settings.origin,'X-CSRF-Token':session['csrf']})['payload']
        require(login['principal']['id']==spec['owner_id'])
        csrf=invoke(client,'csrf','get','/api/session')['payload']['csrf']
        def request(value,key):return invoke(client,'submit','post','/api/support-s1-analyses',json=value,
            headers={'Origin':settings.origin,'X-CSRF-Token':csrf,'idempotency-key':key})
        def resolve(key,value,job):
            # Existing export_queued_request rechecks owner/key/scope/content,
            # full12/H*/versions/authority and sole unclaimed queue. Never fit.
            if job is None:
                with store.transaction() as db:
                    rows=db.execute('SELECT response FROM receipts WHERE owner_id=? AND key=?',
                        (spec['owner_id'],key)).fetchall()
                    require(len(rows)==1);job=json.loads(rows[0]['response'])['id']
            return export_queued_request(store,configured=configured,owner=spec['owner_id'],job=job,key=key,submission=value)
        result=submit_export(request,resolve,lambda name,value:private_once(PRIVATE/name,value,PRIVATE_CAPS[name]),submission,KEY)
    emit(dict(kind='s1_p3_submit_result',**result))
    private_once(PRIVATE/'public-result.json',dict(schema='s1-p3-public-v1',rows=PUBLIC),cap=4096)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--authorized-spec-sha256',required=True);args=parser.parse_args()
    raw=args.spec.read_bytes();require(hashlib.sha256(raw).hexdigest()==args.authorized_spec_sha256)
    run(json.loads(raw))


if __name__=='__main__':
    try:main()
    except BaseException:raise SystemExit(1) from None
