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
BIND_KIND='S1_SELECTED_OWNER_BINDING_V1'
BIND_NAMESPACE='remission-s1-selected-owner-261024-r1'
BIND_PRIVATE=Path('/data/s1-p3-owner-binding-r1')
BIND_EXPECTED=dict(store_instance='f4d6bea5-10aa-4247-afa0-76b8e5c3fceb',authority_generation=1,
    archive_id='support-dev-once-20261022:support-dev-cohort-20261022',archive_export_id='accepted-support-dev-20261022',
    admission_sha256='7f411f3cc7b60fa28eb61481db15c590089fa874827ca8fdab547628438bcf98')
AUTHORITY_SHA='048960f15bc0cc1ca7136a491755bbb64bfd1e0778418fd88e50a15480c65004'
SQL_ARCHIVE="""SELECT owner_id,mode,export_sha256,
 json_extract(receipt,'$.admission_sha256') AS admission_sha256,
 json_extract(receipt,'$.manifest_sha256') AS manifest_sha256,
 json_extract(receipt,'$.members') AS members,
 json_extract(receipt,'$.qualification_scope') AS qualification_scope,
 json_extract(receipt,'$.archive_id') AS archive_id
 FROM observed_archives WHERE id=? LIMIT 2"""
SQL_OWNER='SELECT id FROM accounts WHERE id=? LIMIT 2'
SQL_MEMBERS='SELECT id,owner_id FROM patients WHERE id IN ('+','.join(['?']*12)+') LIMIT 13'
SQL_PARTITIONS='SELECT DISTINCT patient_id,partition_id FROM observed_archive_entries WHERE archive_id=? LIMIT 25'
SQL_PENDING="SELECT 1 FROM analysis_attempts WHERE status IN ('queued','running') LIMIT 1"
SQL_PENDING_WORK="SELECT 1 FROM pending_work WHERE status IN ('queued','running') LIMIT 1"
SQL_MIGRATIONS='SELECT version FROM schema_migrations LIMIT 6'


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


def binding_admit(spec):
    require(type(spec) is dict and spec.get('executable') is True and spec.get('kind')==BIND_KIND
        and spec.get('namespace')==BIND_NAMESPACE and spec.get('volume')==VOLUME
        and spec.get('binding_only') is True and spec.get('no_submit_claim_fit') is True
        and spec.get('owner_id') is None and spec.get('public_authority_sha256')==AUTHORITY_SHA)
    require(all(spec.get(k)==v and type(spec.get(k)) is type(v) for k,v in BIND_EXPECTED.items()))
    require(type(spec.get('source_commit')) is str and re.fullmatch('[a-f0-9]{40}',spec['source_commit']) is not None
        and spec.get('authority_mode')=='EXTERNAL_ROOT_EXACT_ONCE_AFTER_SOURCE_OP')
    # Reviewed byte bindings confer no permission. Current review/GO receipts
    # are external orchestration metadata, never circular inputs to this spec.
    require(not any(k in spec for k in ('private_auth_path','public_archive_path','private_export_cap','key',
        'source_review','operation_review','root_go')))
    return spec


def bounded(db,sql,args,maximum):
    # Every selected SQL also has LIMIT maximum+1 (pending LIMIT1 suffices).
    rows=db.execute(sql,args).fetchmany(maximum+1)
    require(len(rows)<=maximum)
    return rows


def read_only_connection(connect,path,row_factory):
    # URI mode=ro prohibits creating/writing the DB. No immutable flag or copy:
    # SQLite retains normal WAL visibility and may need sidecar bookkeeping.
    db=connect(path.as_uri()+'?mode=ro',uri=True,isolation_level=None,timeout=5)
    try:
        db.row_factory=row_factory
        db.execute('PRAGMA query_only=ON')
        require(db.execute('PRAGMA query_only').fetchone()[0]==1)
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA busy_timeout=5000')
        require(db.execute('PRAGMA foreign_keys').fetchone()[0]==1
            and db.execute('PRAGMA synchronous').fetchone()[0]==2
            and db.execute('PRAGMA journal_mode').fetchone()[0]=='wal')
        return db
    except BaseException:
        db.close();raise


def selected_owner(db,members,partitions,manifest_sha256):
    require(len(members)==12 and len(set(members))==12 and len(partitions)==24 and len(set(partitions))==24)
    rows=bounded(db,SQL_ARCHIVE,(BIND_EXPECTED['archive_id'],),1)
    require(len(rows)==1);archive=rows[0];owner=archive['owner_id']
    require(type(owner) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}',owner) is not None
        and archive['mode']=='restricted_support_historical' and archive['export_sha256']==manifest_sha256
        and archive['admission_sha256']==BIND_EXPECTED['admission_sha256'] and archive['manifest_sha256']==manifest_sha256
        and type(archive['members']) is int and archive['members']==12
        and archive['qualification_scope']=='accepted_saved_producer' and archive['archive_id']==BIND_EXPECTED['archive_id'])
    accounts=bounded(db,SQL_OWNER,(owner,),1)
    require(len(accounts)==1 and accounts[0]['id']==owner)
    patients=bounded(db,SQL_MEMBERS,tuple(members),12)
    require(len(patients)==12 and {r['id'] for r in patients}==set(members)
        and all(r['owner_id']==owner for r in patients))
    linked=bounded(db,SQL_PARTITIONS,(BIND_EXPECTED['archive_id'],),24)
    require(len(linked)==24 and {(r['patient_id'],r['partition_id']) for r in linked}==set(partitions))
    require(not bounded(db,SQL_PENDING,(),1) and not bounded(db,SQL_PENDING_WORK,(),1))
    return dict(schema='s1-selected-owner-control-v1',kind='s1_selected_owner_binding',status='selected_owner_bound',
        **BIND_EXPECTED,owner_id=owner,members=12,selected_owner_consistency=True,no_conflicting_analysis=True,
        binding_only=True,submit=False,claim=False,fit=False)


def protected_binding(connect,row_factory,installed,gate,store_type,members,partitions,manifest_sha256):
    # Operation-local read connection only. Never call Store.__init__/connect or
    # transaction(), which opens a write-capable connection before query_only.
    # This is not a new Store abstraction: reuse the COMPLETE existing validator.
    store=object.__new__(store_type)
    store.path=gate.database;store.installed=installed;store.gate=gate
    with gate.hold():
        db=read_only_connection(connect,gate.database,row_factory)
        try:
            db.execute('BEGIN')
            rows=bounded(db,SQL_MIGRATIONS,(),5)
            require({r['version'] for r in rows}=={1,2,3,4,5})
            store_type.validate_control(store,db)
            result=selected_owner(db,members,partitions,manifest_sha256)
            store_type.validate_control(store,db)
            return result
        finally:
            try:db.rollback()
            finally:db.close()


def run_binding(spec):
    binding_admit(spec)  # Before every private/control or project import.
    class NoScience(importlib.abc.MetaPathFinder):
        def find_spec(self,name,path=None,target=None):
            if name.split('.')[0] in {'numpy','scipy','statsmodels','pymc','pytensor','arviz','arviz_stats','methods','pandas','xarray'}:
                raise AssertionError('binding cannot fit')
    sys.meta_path.insert(0,NoScience())
    import sqlite3
    from contracts.service.live_hold import InstalledBundle
    from contracts.runs.support_research import SupportArchiveAuthority
    from services.foundation.admission import AdmissionGate
    from services.foundation.store import Store
    # Exact control metadata reads are permitted only by a future binding GO.
    bundle=Path('/data/bootstrap/bundle.json')
    require(bundle.is_file() and not bundle.is_symlink() and bundle.stat().st_nlink==1 and bundle.stat().st_size<=1024*1024)
    installed=InstalledBundle.model_validate_json(bundle.read_bytes())
    require(installed.control.database_instance_id==BIND_EXPECTED['store_instance']
        and installed.control.authority_generation==1 and not installed.control.enabled)
    raw=Path('/operation/support-authority.json').read_bytes()
    require(len(raw)==699480 and hashlib.sha256(raw).hexdigest()==AUTHORITY_SHA)
    authority=SupportArchiveAuthority.model_validate_json(raw)
    require(authority.qualification_scope=='accepted_saved_producer'
        and authority.admission_sha256==BIND_EXPECTED['admission_sha256'])
    descriptor=authority.descriptor
    require(descriptor.run_id+':'+descriptor.cohort_id==BIND_EXPECTED['archive_id'])
    gate=AdmissionGate(Path('/data/remission.sqlite'))  # Existing DB+lock only; no create flags.
    result=protected_binding(sqlite3.connect,sqlite3.Row,installed,gate,Store,descriptor.members,
        [(r.member_id,r.partition_id) for r in descriptor.trajectories],authority.manifest_sha256)
    BIND_PRIVATE.mkdir(mode=0o700,exist_ok=False)
    private_once(BIND_PRIVATE/'owner-binding.json',result,cap=4096)


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
        and settings.source_commit==spec['source_commit'] and not settings.installed.control.enabled)
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
    value=json.loads(raw)
    if type(value) is dict and value.get('kind')==BIND_KIND:run_binding(value)
    else:run(value)


if __name__=='__main__':
    try:main()
    except BaseException:raise SystemExit(1) from None
