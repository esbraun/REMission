"""Fixed future owned-container S1 submit/export, never a host app runner.

No Store/auth/scientific import or private read occurs before exact admission.
The existing application owns receipt, cohort and immutable-history authority.
"""
import argparse
import hashlib
import importlib.abc
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time
from datetime import datetime,timezone

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
RECON_KIND='S1_ORIGINAL_REQUEST_RECONCILIATION_V1'
RECON_NAMESPACE='remission-s1-original-reconcile-261024-r2'
RECON_FOLDER=Path('/data/s1-p3-original-reconcile-r2')
RECON_PHASES=('admitted','authentication_before','authentication_after','snapshot_before','snapshot_after')
RECON_STATUSES=('unavailable','receipt_absent_at_snapshot','matched_queued_metadata','matched_other_job_state','conflict')
RECON_JOB_STATES=('queued','running','completed','failed','abstained')
SQL_RECON_SESSION="""SELECT CASE WHEN length(CAST(s.account_id AS BLOB))<=128 THEN s.account_id END AS account_id,
 CASE WHEN typeof(s.revoked)='integer' THEN s.revoked END AS revoked,
 CASE WHEN typeof(s.expires_at) IN ('real','integer') THEN s.expires_at END AS expires_at,
 CASE WHEN typeof(s.auth_version)='integer' THEN s.auth_version END AS auth_version,
 CASE WHEN typeof(a.auth_version)='integer' THEN a.auth_version END AS current_auth_version FROM sessions s LEFT JOIN accounts a ON a.id=s.account_id
 WHERE s.token_hash=? LIMIT 2"""
SQL_RECON_RECEIPT="""SELECT CASE WHEN length(CAST(scope AS BLOB))<=256 THEN scope END AS scope,
 CASE WHEN length(CAST(payload_sha256 AS BLOB))<=64 THEN payload_sha256 END AS payload_sha256,typeof(response) AS response_type,
 length(CAST(response AS BLOB)) AS response_bytes,
 CASE WHEN length(CAST(response AS BLOB))<=131072 THEN response END AS response
 FROM receipts WHERE owner_id=? AND key=? LIMIT 2"""
SQL_RECON_PATIENTS='SELECT id,CASE WHEN length(CAST(owner_id AS BLOB))<=128 THEN owner_id END AS owner_id,CASE WHEN typeof(version)=\'integer\' THEN version END AS version FROM patients WHERE id IN ('+','.join(['?']*12)+') LIMIT 13'
SQL_RECON_JOB="""SELECT job_id,owner_id,patient_id,status,stage,previous_attempt,
 claim_token IS NOT NULL AND claim_token!='' AS claimed,started_at IS NOT NULL AS started,
 finished_at IS NOT NULL AS finished,result_json IS NOT NULL AS result_present,
 length(CAST(cohort_json AS BLOB)) AS cohort_bytes,
 CASE WHEN length(CAST(cohort_json AS BLOB))<=4096 THEN cohort_json END AS cohort,
 length(CAST(configuration_json AS BLOB)) AS config_bytes,
 CASE WHEN length(CAST(configuration_json AS BLOB))<=1024 THEN configuration_json END AS configuration,
 json_valid(request_json) AS valid_request,
 json_extract(request_json,'$.schema_version') AS schema_version,
 json_extract(request_json,'$.kind') AS kind,json_extract(request_json,'$.purpose') AS purpose,
 json_extract(request_json,'$.attempt_id') AS attempt_id,
 json_extract(request_json,'$.archive.owner_id') AS request_owner,
 json_extract(request_json,'$.archive.archive_id') AS archive_id,
 json_extract(request_json,'$.archive.run_id') AS run_id,
 json_extract(request_json,'$.archive.cohort_id') AS cohort_id,
 json_extract(request_json,'$.archive.admission_sha256') AS admission,
 json_extract(request_json,'$.mode') AS mode,json_extract(request_json,'$.cutoff_day') AS cutoff_day,
 json_type(request_json,'$.cohort') AS cohort_type,json_array_length(request_json,'$.cohort') AS cohort_count,
 json_extract(request_json,'$.configuration') AS request_configuration
 FROM analysis_attempts WHERE job_id=? AND owner_id=? LIMIT 2"""
SQL_RECON_MEMBER_IDS="""SELECT CASE WHEN length(CAST(json_extract(value,'$.patient_id') AS BLOB))<=128 THEN json_extract(value,'$.patient_id') END AS patient_id,
 CASE WHEN length(CAST(json_extract(value,'$.partition_id') AS BLOB))<=128 THEN json_extract(value,'$.partition_id') END AS partition_id,
 json_type(value,'$.patient_version') AS version_type,
 CASE WHEN json_type(value,'$.patient_version')='integer' THEN json_extract(value,'$.patient_version') END AS patient_version
 FROM analysis_attempts,json_each(request_json,'$.cohort')
 WHERE job_id=? AND owner_id=? ORDER BY CAST(json_each.key AS INTEGER) LIMIT 13"""
SQL_RECON_PENDING='SELECT id,CASE WHEN length(CAST(patient_id AS BLOB))<=128 THEN patient_id END AS patient_id,CASE WHEN length(CAST(status AS BLOB))<=16 THEN status END AS status FROM pending_work WHERE id=? LIMIT 2'
SQL_RECON_OVERLAP="""SELECT CASE WHEN length(CAST(job_id AS BLOB))<=64 THEN job_id END AS job_id,
 CASE WHEN length(CAST(owner_id AS BLOB))<=128 THEN owner_id END AS owner_id,status FROM analysis_attempts a
 WHERE status IN ('queued','running') AND (json_valid(cohort_json)=0 OR
 json_type(CASE WHEN json_valid(cohort_json) THEN cohort_json ELSE '[]' END)!='array' OR EXISTS
 (SELECT 1 FROM json_each(CASE WHEN json_valid(a.cohort_json) THEN a.cohort_json ELSE '[]' END) WHERE value IN ("""+','.join(['?']*12)+'))) LIMIT 3'
SQL_RECON_PENDING_OVERLAP="""SELECT CASE WHEN length(CAST(id AS BLOB))<=64 THEN id END AS id,patient_id,status FROM pending_work
 WHERE status IN ('queued','running') AND patient_id IN ("""+','.join(['?']*12)+') LIMIT 3'
# Fixed selected scalar projection limits apply before Python materialization.
# Never return request_json or result_json. SQL predicates may scan; the common
# deadline, not LIMIT, bounds operation time.
for _field,_cap in (('schema_version',16),('kind',64),('purpose',32),('attempt_id',64),
        ('archive.owner_id',128),('archive.archive_id',128),('archive.run_id',128),
        ('archive.cohort_id',128),('archive.admission_sha256',64),('mode',8),('configuration',1024)):
    _expr="json_extract(request_json,'$."+_field+"')"
    SQL_RECON_JOB=SQL_RECON_JOB.replace(_expr,'CASE WHEN length(CAST('+_expr+' AS BLOB))<='+str(_cap)+' THEN '+_expr+' END')
SQL_RECON_JOB=SQL_RECON_JOB.replace("json_extract(request_json,'$.cutoff_day')",
    "CASE WHEN json_type(request_json,'$.cutoff_day')='integer' THEN json_extract(request_json,'$.cutoff_day') END")
for _field,_cap in (('patient_id',128),('status',16),('stage',32),('previous_attempt',128)):
    SQL_RECON_JOB=SQL_RECON_JOB.replace(_field+',','CASE WHEN length(CAST('+_field+' AS BLOB))<='+str(_cap)+' THEN '+_field+' END AS '+_field+',',1)
SQL_RECON_ARCHIVE=SQL_ARCHIVE.replace('SELECT owner_id,','SELECT CASE WHEN length(CAST(owner_id AS BLOB))<=128 THEN owner_id END AS owner_id,')
SQL_RECON_ARCHIVE=SQL_RECON_ARCHIVE.replace('mode,export_sha256,',
    'CASE WHEN length(CAST(mode AS BLOB))<=64 THEN mode END AS mode,CASE WHEN length(CAST(export_sha256 AS BLOB))<=64 THEN export_sha256 END AS export_sha256,')
SQL_RECON_ARCHIVE=SQL_RECON_ARCHIVE.replace("json_extract(receipt,'$.members')",
    "CASE WHEN json_type(receipt,'$.members')='integer' THEN json_extract(receipt,'$.members') END")
for _field,_cap in (('admission_sha256',64),('manifest_sha256',64),('qualification_scope',64),('archive_id',128)):
    _expr="json_extract(receipt,'$."+_field+"')"
    SQL_RECON_ARCHIVE=SQL_RECON_ARCHIVE.replace(_expr,'CASE WHEN length(CAST('+_expr+' AS BLOB))<='+str(_cap)+' THEN '+_expr+' END')
for _field in ('model','prior','estimand','protocol','law'):
    _expr="json_extract(request_json,'$."+_field+"')"
    SQL_RECON_JOB=SQL_RECON_JOB.replace('\n FROM analysis_attempts',',CASE WHEN length(CAST('+_expr+' AS BLOB))<=1024 THEN '+_expr+' END AS request_'+_field+'\n FROM analysis_attempts')
SQL_RECON_JOB=SQL_RECON_JOB.replace('\n FROM analysis_attempts',
    ",json_type(request_json,'$.synthetic') AS synthetic_type,CASE WHEN length(CAST(cutoff AS BLOB))<=64 THEN cutoff END AS cutoff,"
    "CASE WHEN length(CAST(json_extract(request_json,'$.cutoff') AS BLOB))<=64 THEN json_extract(request_json,'$.cutoff') END AS request_cutoff\n FROM analysis_attempts")
SQL_RECON_JSON="SELECT json_valid('{\"x\":[1]}') AS valid,json_type('{\"x\":[1]}','$.x') AS kind,json_array_length('[1]') AS count"


class ReconcileConflict(ValueError):
    pass


def recon_require(value):
    if not value:raise ReconcileConflict('original request metadata conflict')


def recon_json(raw):
    def pairs(items):
        value={}
        for key,item in items:recon_require(key not in value);value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ReconcileConflict('nonfinite metadata')))


def recon_instant(value):
    # Exact aware-instant comparison follows store.instant without importing
    # Store. Reject finer-than-microsecond strings rather than truncating them.
    recon_require(type(value) is str and 0<len(value.encode())<=64
        and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',value) is not None)
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    recon_require(result.tzinfo is not None and result.utcoffset() is not None)
    return result.astimezone(timezone.utc)


def recon_admit(spec):
    require(type(spec) is dict and spec.get('kind')==RECON_KIND and spec.get('executable') is True
        and spec.get('namespace')==RECON_NAMESPACE and spec.get('volume')==VOLUME
        and spec.get('key')==KEY and spec.get('owner_id')=='1946fb30-b736-402e-a6d0-a0b50eb92496'
        and all(spec.get(k)==v and type(spec.get(k)) is type(v) for k,v in BIND_EXPECTED.items())
        and spec.get('authority_mode')=='EXTERNAL_ROOT_EXACT_ONCE_AFTER_SOURCE_OP'
        and spec.get('metadata_only') is True and spec.get('no_submit_claim_fit') is True
        and spec.get('request_seconds')==180 and type(spec.get('request_seconds')) is int
        and type(spec.get('source_commit')) is str and re.fullmatch('[a-f0-9]{40}',spec['source_commit']) is not None
        and spec.get('original_spec_blob')=='a92f061741cf283e4bc5cf4f46a94979acf0731e'
        and type(spec.get('original_submission')) is dict
        and set(spec['original_submission'])=={'archive_id','mode','cutoff_day','configuration','previous_attempt'}
        and spec['original_submission']['archive_id']==BIND_EXPECTED['archive_id']
        and spec['original_submission']['mode']=='S1' and type(spec['original_submission']['cutoff_day']) is int
        and spec['original_submission']['cutoff_day']==84 and spec['original_submission']['previous_attempt'] is None
        and type(spec.get('expected_references')) is dict and set(spec['expected_references'])=={'model','prior','estimand','protocol','law'}
        and type(spec.get('expected_cutoff')) is str and len(spec['expected_cutoff'])<=64
        and not any(k in spec for k in ('source_review','operation_review','root_go','private_export_cap')))
    return spec


def recon_result(status,*,phase='snapshot_after',job=None,job_state=None,claimed=False,started=False,result_present=False,complete=True):
    value=dict(schema='s1-original-request-control-v1',kind='s1_original_request_reconciliation',phase=phase,status=status,
        complete=complete,job_id=job,job_state=job_state,claimed=claimed,started=started,result_present=result_present,
        metadata_only=True,current_input_validated=False,submit=False,claim=False,fit=False)
    require(status in RECON_STATUSES and phase in RECON_PHASES and type(complete) is bool
        and (job is None or type(job) is str and re.fullmatch('analysis-[a-f0-9]{32}',job) is not None)
        and (job_state is None or job_state in RECON_JOB_STATES)
        and all(type(v) is bool for v in (claimed,started,result_present)))
    return value


def recon_publish(value):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    require(0<len(raw)<=4096)
    temporary=RECON_FOLDER/'.control.next';target=RECON_FOLDER/'control.json'
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        info=os.fstat(fd);require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.getuid())
        with os.fdopen(fd,'wb') as stream:fd=None;stream.write(raw);stream.flush();os.fsync(stream.fileno())
        if target.exists() or target.is_symlink():
            info=target.lstat();require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.getuid())
        os.replace(temporary,target)
    finally:
        if fd is not None:os.close(fd)


def recon_session(db,token_hash,owner,now):
    require(type(token_hash) is str and re.fullmatch('[a-f0-9]{64}',token_hash) is not None)
    rows=bounded(db,SQL_RECON_SESSION,(token_hash,),1)
    require(len(rows)==1);r=rows[0]
    require(r['account_id']==owner and type(r['revoked']) is int and r['revoked']==0
        and type(r['expires_at']) in (int,float) and math.isfinite(r['expires_at']) and r['expires_at']>now
        and type(r['auth_version']) is int and r['auth_version']>=1
        and type(r['current_auth_version']) is int and r['auth_version']==r['current_auth_version'])


def recon_archive(db,members,partitions,manifest_sha256,owner):
    require(len(members)==12 and len(set(members))==12 and len(partitions)==24 and len(set(partitions))==24)
    rows=bounded(db,SQL_RECON_ARCHIVE,(BIND_EXPECTED['archive_id'],),1)
    require(len(rows)==1);r=rows[0]
    require(r['owner_id']==owner and r['mode']=='restricted_support_historical'
        and r['export_sha256']==r['manifest_sha256']==manifest_sha256
        and r['admission_sha256']==BIND_EXPECTED['admission_sha256']
        and type(r['members']) is int and r['members']==12
        and r['qualification_scope']=='accepted_saved_producer' and r['archive_id']==BIND_EXPECTED['archive_id'])
    require(len(bounded(db,SQL_OWNER,(owner,),1))==1)
    patients=bounded(db,SQL_RECON_PATIENTS,tuple(members),12)
    require(len(patients)==12 and {r['id'] for r in patients}==set(members)
        and all(r['owner_id']==owner and type(r['version']) is int and r['version']>=1 for r in patients))
    linked=bounded(db,SQL_PARTITIONS,(BIND_EXPECTED['archive_id'],),24)
    require(len(linked)==24 and {(r['patient_id'],r['partition_id']) for r in linked}==set(partitions))


def recon_metadata(db,spec,members,partitions,submission,payload_sha,cohort_id,s1_partitions):
    owner=spec['owner_id'];ordered=sorted(members)
    receipt=bounded(db,SQL_RECON_RECEIPT,(owner,KEY),1)
    active=bounded(db,SQL_RECON_OVERLAP,tuple(ordered),2)
    work=bounded(db,SQL_RECON_PENDING_OVERLAP,tuple(ordered),2)
    if not receipt:
        recon_require(not active and not work)
        return recon_result('receipt_absent_at_snapshot')
    r=receipt[0]
    recon_require(type(r['scope']) is str and r['scope']=='support-s1:'+submission['archive_id']
        and r['payload_sha256']==payload_sha and r['response_type']=='text'
        and type(r['response_bytes']) is int and 0<r['response_bytes']<=131072 and type(r['response']) is str
        and len(r['response'].encode())==r['response_bytes'])
    try:value=recon_json(r['response'])
    except (ValueError,TypeError,RecursionError):raise ReconcileConflict('invalid response') from None
    recon_require(type(value) is dict and type(value.get('id')) is str and re.fullmatch('analysis-[a-f0-9]{32}',value['id']) is not None)
    job=value['id']
    expected=dict(kind='support_s1_analysis',patient_id=ordered[0],archive_id=submission['archive_id'],cohort_id=cohort_id,
        member_count=12,mode='S1',cutoff_day=84,configuration=submission['configuration'],cohort=ordered,
        previous_attempt=None,status='queued',stage='queued')
    recon_require(all(value.get(k)==v and type(value.get(k)) is type(v) for k,v in expected.items()))
    rows=bounded(db,SQL_RECON_JOB,(job,owner),1);recon_require(len(rows)==1);r=rows[0]
    expected=dict(job_id=job,owner_id=owner,patient_id=ordered[0],previous_attempt=None,valid_request=1,
        schema_version='3.0.0',kind='poc_support_s1_input',purpose='S1-WCLS',attempt_id=job,request_owner=owner,
        archive_id=submission['archive_id'],run_id=submission['archive_id'].split(':')[0],cohort_id=cohort_id,
        admission=spec['admission_sha256'],mode='S1',cutoff_day=84,cohort_type='array',cohort_count=12,synthetic_type='true')
    recon_require(all(r[k]==v and type(r[k]) is type(v) for k,v in expected.items()))
    recon_require(type(r['cohort_bytes']) is int and 0<r['cohort_bytes']<=4096 and type(r['cohort']) is str
        and type(r['config_bytes']) is int and 0<r['config_bytes']<=1024 and type(r['configuration']) is str
        and type(r['request_configuration']) is str and len(r['request_configuration'].encode())<=1024)
    recon_require(recon_json(r['cohort'])==ordered and recon_json(r['configuration'])==submission['configuration']
        and recon_json(r['request_configuration'])==submission['configuration'])
    recon_require(recon_instant(value.get('cutoff'))==recon_instant(r['cutoff'])
        ==recon_instant(r['request_cutoff'])==recon_instant(spec['expected_cutoff']))
    for name,expected in spec['expected_references'].items():
        field=r['request_'+name]
        recon_require(type(field) is str and len(field.encode())<=1024 and recon_json(field)==expected)
    member_rows=bounded(db,SQL_RECON_MEMBER_IDS,(job,owner),12)
    recon_require(len(member_rows)==12 and [v['patient_id'] for v in member_rows]==ordered
        and all(type(v['patient_version']) is int and v['patient_version']>=1 and v['version_type']=='integer' for v in member_rows))
    recon_require(len({(v['patient_id'],v['partition_id']) for v in member_rows})==12
        and {(v['patient_id'],v['partition_id']) for v in member_rows}==set(s1_partitions))
    pending=bounded(db,SQL_RECON_PENDING,(job,),1)
    recon_require(len(pending)==1 and pending[0]['id']==job and pending[0]['patient_id']==ordered[0]
        and r['status'] in RECON_JOB_STATES and pending[0]['status']==r['status']
        and all(type(r[k]) is int and r[k] in (0,1) for k in ('claimed','started','finished','result_present')))
    recon_require(all(v['job_id']==job and v['owner_id']==owner and v['status']==r['status'] for v in active)
        and all(v['id']==job and v['patient_id']==ordered[0] and v['status']==r['status'] for v in work))
    if r['status']=='queued':
        recon_require(not any(r[k] for k in ('claimed','started','finished','result_present')) and r['stage']=='queued'
            and len(active)==len(work)==1)
        status='matched_queued_metadata'
    else:
        recon_require(r['stage'] in ('preparing','fitting','diagnostics','rollouts','complete','failed','abstained'))
        status='matched_other_job_state'
    return recon_result(status,job=job,job_state=r['status'],claimed=bool(r['claimed']),started=bool(r['started']),result_present=bool(r['result_present']))


def protected_reconcile(connect,row_factory,installed,gate,store_type,members,partitions,manifest_sha256,spec,token_hash,clock,submission,payload_sha,cohort_id,s1_partitions):
    store=object.__new__(store_type);store.path=gate.database;store.installed=installed;store.gate=gate
    with gate.hold():
        db=read_only_connection(connect,gate.database,row_factory)
        try:
            store_type.validate_control(store,db)
            db.execute('BEGIN');store_type.validate_control(store,db)
            capability=db.execute(SQL_RECON_JSON).fetchone()
            require(capability['valid']==1 and capability['kind']=='array' and capability['count']==1)
            recon_session(db,token_hash,spec['owner_id'],clock())
            recon_archive(db,members,partitions,manifest_sha256,spec['owner_id'])
            try:result=recon_metadata(db,spec,members,partitions,submission,payload_sha,cohort_id,s1_partitions)
            except (ValueError,KeyError,TypeError,RecursionError):result=recon_result('conflict')
            recon_session(db,token_hash,spec['owner_id'],clock());store_type.validate_control(store,db)
            return result
        finally:
            try:db.rollback()
            finally:db.close()


def run_reconcile(spec):
    recon_admit(spec)
    RECON_FOLDER.mkdir(mode=0o700,exist_ok=False)
    recon_publish(recon_result('unavailable',phase='admitted',complete=False))
    class NoScience(importlib.abc.MetaPathFinder):
        def find_spec(self,name,path=None,target=None):
            if name.split('.')[0] in {'numpy','scipy','statsmodels','pymc','pytensor','arviz','arviz_stats','methods','pandas','xarray'}:
                raise AssertionError('reconciliation cannot fit')
    sys.meta_path.insert(0,NoScience())
    import sqlite3
    from datetime import timedelta
    from fastapi.testclient import TestClient
    from services.foundation.app import create_app,COOKIE
    from services.foundation.configuration import environment_settings
    from services.foundation.admission import AdmissionGate
    from services.foundation.store import Store,digest
    from contracts.domain.analysis import canonical,sha
    from contracts.domain.support_s1 import S1Submission,MODEL_REF,WCLS_PRIOR_REF,S1_ESTIMAND,LAW_REF,SUPPORT_REF
    bundle=Path('/data/bootstrap/bundle.json');info=bundle.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.getuid()
        and 0<info.st_size<=1024*1024 and stat.S_IMODE(info.st_mode)&0o022==0)
    settings=environment_settings()
    require(settings.database==Path('/data/remission.sqlite') and settings.source_commit==spec['source_commit']
        and settings.installed.control.database_instance_id==spec['store_instance']
        and settings.installed.control.authority_generation==1 and not settings.installed.control.enabled)
    submission=S1Submission.model_validate_json(canonical(spec['original_submission'])).model_dump(mode='json')
    require(submission==spec['original_submission'] and spec['expected_references']==dict(model=MODEL_REF,prior=WCLS_PRIOR_REF,
        estimand=S1_ESTIMAND,law=LAW_REF,protocol=SUPPORT_REF))
    raw,_,authority=settings.observed_archives[spec['archive_export_id']]
    require(authority.qualification_scope=='accepted_saved_producer' and authority.admission_sha256==spec['admission_sha256'])
    descriptor=authority.descriptor
    require(descriptor.run_id+':'+descriptor.cohort_id==spec['archive_id']
        and recon_instant(spec['expected_cutoff'])==(descriptor.origin+timedelta(days=84)).astimezone(timezone.utc))
    auth=Path('/private/auth.json');info=auth.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.getuid() and 0<info.st_size<=65536
        and stat.S_IMODE(info.st_mode)&0o077==0)
    with auth.open('rb') as stream:
        credentials_raw=stream.read(65537)
    require(0<len(credentials_raw)<=65536)
    credentials=recon_json(credentials_raw)['owner']
    require(type(credentials) is dict and set(credentials)=={'username','password'}
        and all(type(v) is str and 0<len(v)<=1024 for v in credentials.values()))
    recon_publish(recon_result('unavailable',phase='authentication_before',complete=False))
    with TestClient(create_app(settings),base_url=settings.origin) as client:
        session=invoke(client,'session','get','/api/session')['payload']
        login=invoke(client,'login','post','/api/login',json=credentials,
            headers={'Origin':settings.origin,'X-CSRF-Token':session['csrf']})['payload']
        require(login['principal']['id']==spec['owner_id'])
        current=invoke(client,'csrf','get','/api/session')['payload']
        require(current['principal']['id']==spec['owner_id'])
        token=client.cookies.get(COOKIE);require(type(token) is str and 1<=len(token)<=512)
        token_hash=digest(token)
        recon_publish(recon_result('unavailable',phase='authentication_after',complete=False))
        gate=AdmissionGate(settings.database)
        recon_publish(recon_result('unavailable',phase='snapshot_before',complete=False))
        result=protected_reconcile(sqlite3.connect,sqlite3.Row,settings.installed,gate,Store,descriptor.members,
            [(r.member_id,r.partition_id) for r in descriptor.trajectories],hashlib.sha256(raw).hexdigest(),spec,
            token_hash,lambda:settings.clock().timestamp(),submission,sha(submission),descriptor.cohort_id,
            [(r.member_id,r.partition_id) for r in descriptor.trajectories if r.mode=='S1'])
        recon_publish(result)


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
                'admission_sha256','source_commit'):
        require(spec.get(key) is not None and spec[key]!='UNKNOWN')
    require(spec.get('request_seconds')==180 and spec.get('private_export_cap')==16*1024*1024)
    require(type(spec['authority_generation']) is int and spec['authority_generation']>=1)
    require(type(spec['source_commit']) is str and re.fullmatch('[a-f0-9]{40}',spec['source_commit']) is not None
        and spec.get('authority_mode')=='EXTERNAL_ROOT_EXACT_ONCE_AFTER_SOURCE_OP')
    require(type(spec['admission_sha256']) is str and re.fullmatch('[a-f0-9]{64}',spec['admission_sha256']) is not None)
    require(not any(k in spec for k in ('source_review','operation_review','root_go')))
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
        and type(proof.get('attempt_id')) is str and re.fullmatch('analysis-[a-f0-9]{32}',proof['attempt_id']) is not None
        and type(proof.get('owner_id')) is str and bool(proof['owner_id'])
        and proof.get('active_attempts')==[dict(attempt_id=proof['attempt_id'],status='queued')]
        and (job is None or proof.get('attempt_id')==job))
    save('queued-export.json',proof)
    save('selection.json',dict(owner=proof['owner_id'],job=proof['attempt_id'],key=key,submission=submission))
    return dict(status='queued_export_saved',members=12,cutoff_day=84,job_id=proof['attempt_id'],
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
    if type(value) is dict and value.get('kind')==RECON_KIND:run_reconcile(value)
    elif type(value) is dict and value.get('kind')==BIND_KIND:run_binding(value)
    else:run(value)


if __name__=='__main__':
    try:main()
    except BaseException:raise SystemExit(1) from None
