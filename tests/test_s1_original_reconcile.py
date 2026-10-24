"""Original-request metadata semantics; no actual Store/SQL/auth operation."""
import ast
from copy import deepcopy
import hashlib
import io
import json
import stat
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from test_s1_genuine_source import module,created,tar
host=module('s1_genuine_once');driver=module('s1_genuine_submit')
ROOT=Path(__file__).resolve().parents[1]
BASELINE_HOST=BASELINE_DRIVER=None
PRE_REPAIR_DRIVER=None
PRE_REPAIR_HOST=None
OWNER='1946fb30-b736-402e-a6d0-a0b50eb92496';JOB='analysis-'+'a'*32;CID='b'*64
MEMBERS=[f'member-{n:02}' for n in range(12)]
PARTS=[(m,m+'-'+s) for m in MEMBERS for s in ('S0','S1')]
S1PARTS=[(m,m+'-S1') for m in MEMBERS]
COHORT='support-dev-cohort-20261022';MANIFEST='a'*64
CUTOFF='2026-01-01T00:00:00+00:00'
CONFIG={'id':'poc-support-s1-app-v1','version':'1.0.0','sha256':'c'*64}
REFS={name:dict(id='scalar-'+name,version='1.0.0',sha256='f'*64) for name in ('model','prior','estimand','law','protocol')}
SUB=dict(archive_id=driver.BIND_EXPECTED['archive_id'],mode='S1',cutoff_day=84,configuration=CONFIG,previous_attempt=None)
def spec():return dict(kind=driver.RECON_KIND,executable=True,namespace=driver.RECON_NAMESPACE,volume=driver.VOLUME,
    **driver.BIND_EXPECTED,owner_id=OWNER,key=driver.KEY,source_commit='d'*40,
    authority_mode='EXTERNAL_ROOT_EXACT_ONCE_AFTER_SOURCE_OP',metadata_only=True,no_submit_claim_fit=True,
    request_seconds=180,original_spec_blob='a92f061741cf283e4bc5cf4f46a94979acf0731e',original_submission=deepcopy(SUB),
    expected_references=deepcopy(REFS),expected_cutoff=CUTOFF)
def hspec():return dict(spec(),image=host.IMAGE,bounds=deepcopy(host.BOUNDS),reconcile_spec_sha256='a'*64,
    archive_configuration_sha256='a'*64,private_auth_path='C:/fixture-only/auth.json')
def response():return dict(id=JOB,kind='support_s1_analysis',patient_id=MEMBERS[0],archive_id=SUB['archive_id'],
    cohort_id=COHORT,member_count=12,mode='S1',cutoff_day=84,configuration=CONFIG,cohort=MEMBERS,
    previous_attempt=None,status='queued',stage='queued',cutoff=CUTOFF,input_sha256='PRIVATE_SENTINEL')
def fixture():
    raw=json.dumps(response())
    receipt=dict(scope='support-s1:'+SUB['archive_id'],payload_sha256='e'*64,response_type='text',response_bytes=len(raw.encode()),response=raw)
    job=dict(job_id=JOB,owner_id=OWNER,patient_id=MEMBERS[0],previous_attempt=None,valid_request=1,schema_version='3.0.0',
        kind='poc_support_s1_input',purpose='S1-WCLS',attempt_id=JOB,request_owner=OWNER,archive_id=SUB['archive_id'],
        run_id=SUB['archive_id'].split(':')[0],cohort_id=COHORT,admission=spec()['admission_sha256'],mode='S1',cutoff_day=84,
        cohort_type='array',cohort_count=12,cohort_bytes=len(json.dumps(MEMBERS)),cohort=json.dumps(MEMBERS),
        config_bytes=len(json.dumps(CONFIG)),configuration=json.dumps(CONFIG),request_configuration=json.dumps(CONFIG),
        status='queued',stage='queued',claimed=0,started=0,finished=0,result_present=0,synthetic_type='true',cutoff=CUTOFF,request_cutoff=CUTOFF,
        **{'request_'+k:json.dumps(v) for k,v in REFS.items()})
    return {driver.SQL_RECON_RECEIPT:[receipt],driver.SQL_RECON_OVERLAP:[dict(job_id=JOB,owner_id=OWNER,status='queued')],
        driver.SQL_RECON_PENDING_OVERLAP:[dict(id=JOB,patient_id=MEMBERS[0],status='queued')],driver.SQL_RECON_JOB:[job],
        driver.SQL_RECON_MEMBER_IDS:[dict(patient_id=m,partition_id=p,version_type='integer',patient_version=1) for m,p in S1PARTS],
        driver.SQL_RECON_PENDING:[dict(id=JOB,patient_id=MEMBERS[0],status='queued')],
        driver.SQL_RECON_SESSION:[dict(account_id=OWNER,revoked=0,expires_at=200.,auth_version=1,current_auth_version=1)],
        driver.SQL_RECON_ARCHIVE:[dict(owner_id=OWNER,mode='restricted_support_historical',export_sha256=MANIFEST,manifest_sha256=MANIFEST,
            admission_sha256=spec()['admission_sha256'],members=12,qualification_scope='accepted_saved_producer',archive_id=SUB['archive_id'])],
        driver.SQL_OWNER:[dict(id=OWNER)],driver.SQL_RECON_PATIENTS:[dict(id=m,owner_id=OWNER,version=1) for m in MEMBERS],
        driver.SQL_PARTITIONS:[dict(patient_id=m,partition_id=p) for m,p in PARTS],driver.SQL_RECON_JSON:[dict(valid=1,kind='array',count=1)]}
class DB:
    def __init__(self,data=None):self.data=fixture() if data is None else data;self.log=[]
    def execute(self,sql,args=()):
        self.log.append((sql,args));return NS(fetchmany=lambda count:self.data.get(sql,[])[:count],fetchone=lambda:self.data.get(sql,[None])[0])
    def rollback(self):self.log.append(('ROLLBACK',()))
    def close(self):self.log.append(('CLOSE',()))
def metadata(data):return driver.recon_metadata(DB(data),spec(),MEMBERS,PARTS,SUB,'e'*64,COHORT,S1PARTS)

class MetadataTests(unittest.TestCase):
    def test_actual_aware_datetime_JSON_serialization_old_rejects_repaired_accepts(self):
        from datetime import datetime
        from pydantic import BaseModel,AwareDatetime
        class TypedCutoff(BaseModel):cutoff:AwareDatetime
        typed=TypedCutoff(cutoff=datetime.fromisoformat(CUTOFF)).model_dump(mode='json')['cutoff']
        self.assertTrue(typed.endswith('Z'))
        cls=next(n for n in ast.parse((ROOT/'contracts/domain/support_s1.py').read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='S1Input')
        annotation=next(n.annotation for n in cls.body if isinstance(n,ast.AnnAssign) and n.target.id=='cutoff')
        self.assertEqual(ast.unparse(annotation),'AwareDatetime')
        data=fixture();data[driver.SQL_RECON_JOB][0]['request_cutoff']=typed
        old=next(n for n in ast.parse(PRE_REPAIR_DRIVER).body if isinstance(n,ast.FunctionDef) and n.name=='recon_metadata')
        namespace=dict(vars(driver));exec(compile(ast.Module(body=[old],type_ignores=[]),'previous-public-source','exec'),namespace)
        with self.assertRaises(driver.ReconcileConflict):namespace['recon_metadata'](DB(data),spec(),MEMBERS,PARTS,SUB,'e'*64,COHORT,S1PARTS)
        self.assertEqual(metadata(data)['status'],'matched_queued_metadata')
    def test_all_four_cutoffs_accept_equivalent_explicit_offsets(self):
        for field in ('response','row','request','expected'):
            data=fixture();s=spec();offset='2026-01-01T01:00:00+01:00'
            if field=='response':
                value=response();value['cutoff']=offset;raw=json.dumps(value)
                data[driver.SQL_RECON_RECEIPT][0].update(response=raw,response_bytes=len(raw.encode()))
            elif field=='expected':s['expected_cutoff']=offset
            else:data[driver.SQL_RECON_JOB][0]['cutoff' if field=='row' else 'request_cutoff']=offset
            with self.subTest(field=field):self.assertEqual(driver.recon_metadata(DB(data),s,MEMBERS,PARTS,SUB,'e'*64,COHORT,S1PARTS)['status'],'matched_queued_metadata')
    def test_all_four_cutoffs_refuse_naive_malformed_changed_microsecond_or_day(self):
        for value in ('2026-01-01T00:00:00','malformed','2026-01-01T00:00:01Z','2026-01-01T00:00:00.000001Z',
                '2026-01-02T00:00:00Z','2026-01-01T00:00:00.0000001Z',True,None,'x'*65):
            for field in ('response','row','request','expected'):
                data=fixture();s=spec()
                if field=='response':
                    v=response();v['cutoff']=value;raw=json.dumps(v);data[driver.SQL_RECON_RECEIPT][0].update(response=raw,response_bytes=len(raw.encode()))
                elif field=='expected':s['expected_cutoff']=value
                else:data[driver.SQL_RECON_JOB][0]['cutoff' if field=='row' else 'request_cutoff']=value
                with self.subTest(value=value,field=field),self.assertRaises(ValueError):driver.recon_metadata(DB(data),s,MEMBERS,PARTS,SUB,'e'*64,COHORT,S1PARTS)
        self.assertEqual(driver.recon_instant('2026-01-01T00:00:00.123456Z'),driver.recon_instant('2026-01-01T01:00:00.123456+01:00'))
    def test_legitimate_original_pending_is_allowed_only_reconciliation(self):
        result=metadata(fixture());self.assertEqual(result['status'],'matched_queued_metadata');self.assertEqual(result['job_id'],JOB)
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(result));self.assertFalse(result['current_input_validated'])
        data=fixture();data[driver.SQL_ARCHIVE]=data[driver.SQL_RECON_ARCHIVE]
        data[driver.SQL_MEMBERS]=data[driver.SQL_RECON_PATIENTS];data[driver.SQL_PENDING]=[dict(pending=1)]
        with self.assertRaises(ValueError):driver.selected_owner(DB(data),MEMBERS,PARTS,MANIFEST)
        data[driver.SQL_PENDING]=[];data[driver.SQL_PENDING_WORK]=[]
        self.assertEqual(driver.selected_owner(DB(data),MEMBERS,PARTS,MANIFEST)['status'],'selected_owner_bound')
    def test_absence_snapshot_only_and_orphan_conflict(self):
        data=fixture()
        for sql in (driver.SQL_RECON_RECEIPT,driver.SQL_RECON_OVERLAP,driver.SQL_RECON_PENDING_OVERLAP):data[sql]=[]
        self.assertEqual(metadata(data)['status'],'receipt_absent_at_snapshot')
        data[driver.SQL_RECON_OVERLAP]=[dict(job_id=JOB,owner_id=OWNER,status='queued')]
        with self.assertRaises(ValueError):metadata(data)
    def test_duplicate_scope_payload_and_response_job_conflicts(self):
        for key,value in (('scope','wrong'),('payload_sha256','wrong'),('response_type','blob'),('response_bytes',131073),
                ('response','{"id":"wrong"}'),('response','{"id":1,"id":2}'),('response','NaN'),('response_bytes',1)):
            data=fixture();data[driver.SQL_RECON_RECEIPT][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):metadata(data)
        data=fixture();data[driver.SQL_RECON_RECEIPT]*=2
        with self.assertRaises(ValueError):metadata(data)
    def test_original_response_identity_fields_are_checked(self):
        for key,value in (('configuration',{}),('cohort',MEMBERS[::-1]),('member_count',True),('status','running'),('archive_id','other')):
            data=fixture();value_response=response();value_response[key]=value;raw=json.dumps(value_response)
            data[driver.SQL_RECON_RECEIPT][0].update(response=raw,response_bytes=len(raw.encode()))
            with self.subTest(key=key),self.assertRaises(ValueError):metadata(data)
    def test_request_member_config_pending_and_competing_conflicts(self):
        for key,value in (('schema_version','2.0.0'),('request_owner','foreign'),('kind','wrong'),('purpose','wrong'),('cutoff_day',True),
                ('claimed',1),('started',1),('configuration','{}'),('cohort_bytes',4097),('request_configuration','{"x":1}'),
                ('request_model','{}'),('synthetic_type','integer'),('request_cutoff','wrong')):
            data=fixture();data[driver.SQL_RECON_JOB][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):metadata(data)
        for sql in (driver.SQL_RECON_PENDING,driver.SQL_RECON_MEMBER_IDS):
            data=fixture();data[sql]=[]
            with self.assertRaises(ValueError):metadata(data)
        data=fixture();data[driver.SQL_RECON_MEMBER_IDS][0]['partition_id']=MEMBERS[0]+'-S0'
        with self.assertRaises(ValueError):metadata(data)
        data=fixture();data[driver.SQL_RECON_OVERLAP].append(dict(job_id='analysis-'+'f'*32,owner_id=OWNER,status='queued'))
        with self.assertRaises(ValueError):metadata(data)
    def test_existing_running_and_completed_are_reported_without_reset(self):
        for status,stage in (('running','fitting'),('completed','complete'),('failed','failed'),('abstained','abstained')):
            data=fixture();data[driver.SQL_RECON_JOB][0].update(status=status,stage=stage,claimed=1,started=1,
                finished=int(status!='running'),result_present=int(status=='completed'))
            data[driver.SQL_RECON_PENDING][0]['status']=status
            if status=='running':
                data[driver.SQL_RECON_OVERLAP][0]['status']=status;data[driver.SQL_RECON_PENDING_OVERLAP][0]['status']=status
            else:data[driver.SQL_RECON_OVERLAP]=[];data[driver.SQL_RECON_PENDING_OVERLAP]=[]
            result=metadata(data);self.assertEqual(result['status'],'matched_other_job_state');self.assertEqual(result['job_state'],status)
            self.assertFalse(result['submit']);self.assertFalse(result['claim']);self.assertFalse(result['fit'])
    def test_session_actual_predicate_expiry_revocation_owner_auth_version(self):
        for key,value in (('account_id','other'),('revoked',1),('revoked',False),('expires_at',99),('expires_at',float('inf')),('current_auth_version',2),('current_auth_version',True)):
            data=fixture();data[driver.SQL_RECON_SESSION][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):driver.recon_session(DB(data),'a'*64,OWNER,100.)
        driver.recon_session(DB(),'a'*64,OWNER,100.)
    def test_protected_transaction_full_control_rechecks_and_rollback_every_fault(self):
        class Gate:
            database=Path('/fixture-only/db')
            def hold(self):return self
            def __enter__(self):return self
            def __exit__(self,*_):pass
        class Store:
            @staticmethod
            def validate_control(_store,db):db.log.append(('CONTROL',()))
        for faulty in (False,True):
            db=DB()
            if faulty:db.data[driver.SQL_RECON_SESSION][0]['revoked']=1
            with patch.object(driver,'read_only_connection',return_value=db):
                args=(None,None,None,Gate(),Store,MEMBERS,PARTS,MANIFEST,spec(),'a'*64,lambda:100.,SUB,'e'*64,COHORT,S1PARTS)
                if faulty:
                    with self.assertRaises(ValueError):driver.protected_reconcile(*args)
                else:self.assertEqual(driver.protected_reconcile(*args)['status'],'matched_queued_metadata')
            self.assertEqual(db.log[:3],[('CONTROL',()),('BEGIN',()),('CONTROL',())]);self.assertEqual(db.log[-2:],[('ROLLBACK',()),('CLOSE',())])
    def test_sql_bounded_projection_never_returns_histories_request_result_tokens(self):
        self.assertNotIn('SELECT *',driver.SQL_RECON_JOB);self.assertNotIn(' AS request_json',driver.SQL_RECON_JOB)
        self.assertIn('response_bytes',driver.SQL_RECON_RECEIPT);self.assertIn('<=131072 THEN response',driver.SQL_RECON_RECEIPT)
        self.assertIn('LIMIT 2',driver.SQL_RECON_RECEIPT);self.assertNotIn('session_id=?',driver.SQL_RECON_RECEIPT)
        for forbidden in ('request_json AS','result_json AS','claim_token AS','$.histories','UPDATE ','INSERT ','DELETE '):
            self.assertNotIn(forbidden,' '.join(v for k,v in vars(driver).items() if k.startswith('SQL_RECON_') and type(v) is str))
        self.assertIn('<=1024 THEN json_extract',driver.SQL_RECON_JOB)
    def test_archive_owner_generation_metadata_and_sql_capability_refuse(self):
        for key,value in (('owner_id','foreign'),('members',True),('manifest_sha256','other'),('admission_sha256','other')):
            data=fixture();data[driver.SQL_RECON_ARCHIVE][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):driver.recon_archive(DB(data),MEMBERS,PARTS,MANIFEST,OWNER)
        data=fixture();data[driver.SQL_RECON_PATIENTS][0]['owner_id']='foreign'
        with self.assertRaises(ValueError):driver.recon_archive(DB(data),MEMBERS,PARTS,MANIFEST,OWNER)
    def test_control_and_json_capability_fail_before_metadata_and_always_close(self):
        class Gate:
            database=Path('/fixture-only/db')
            def hold(self):return self
            def __enter__(self):return self
            def __exit__(self,*_):pass
        for control_fault in (False,True):
            db=DB();db.data[driver.SQL_RECON_JSON]=[dict(valid=0,kind='missing',count=0)]
            class Store:
                @staticmethod
                def validate_control(_store,db):
                    if control_fault:raise ValueError('SECRET_SENTINEL')
            with patch.object(driver,'read_only_connection',return_value=db):
                with self.assertRaises(ValueError):driver.protected_reconcile(None,None,None,Gate(),Store,MEMBERS,PARTS,MANIFEST,
                    spec(),'a'*64,lambda:100.,SUB,'e'*64,COHORT,S1PARTS)
            self.assertNotIn(driver.SQL_RECON_RECEIPT,[v[0] for v in db.log]);self.assertEqual(db.log[-2:],[('ROLLBACK',()),('CLOSE',())])
        data=fixture();data[driver.SQL_PARTITIONS]=data[driver.SQL_PARTITIONS][:-1]
        with self.assertRaises(ValueError):driver.recon_archive(DB(data),MEMBERS,PARTS,MANIFEST,OWNER)

class TransportTests(unittest.TestCase):
    def test_closed_public_schema_privacy_and_finite_flags(self):
        v=metadata(fixture());self.assertEqual(host.recon_public(json.dumps(v).encode()),v)
        for extra in ({'owner_id':OWNER},{'key':driver.KEY},{'private_hash':'SECRET_SENTINEL'},{'complete':1},{'current_input_validated':True},
                {'job_id':'wrong'},{'phase':'arbitrary'},{'claimed':True}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):host.recon_public(json.dumps(dict(v,**extra)).encode())
        for raw in (b'{}',b'{"x":1,"x":2}',b'NaN',b'x'*4097):
            with self.assertRaises((ValueError,TypeError)):host.recon_public(raw)
    def test_new_fixed_tar_name_only(self):
        self.assertEqual(host.public_tar(tar(name='control.json'),reconcile=True),b'{}')
        with self.assertRaises(ValueError):host.public_tar(tar(),reconcile=True)
    def test_atomic_checkpoint_previous_value_survives_replace_fault(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(driver,'RECON_FOLDER',Path(directory)),patch.object(driver.os,'getuid',return_value=0,create=True):
            v=driver.recon_result('unavailable',phase='admitted',complete=False);driver.recon_publish(v)
            before=(Path(directory)/'control.json').read_bytes()
            with patch.object(driver.os,'replace',side_effect=OSError('SECRET_SENTINEL')):
                with self.assertRaises(OSError):driver.recon_publish(driver.recon_result('unavailable',phase='authentication_before',complete=False))
            self.assertEqual((Path(directory)/'control.json').read_bytes(),before)
    def test_atomic_checkpoint_nonregular_target_and_before_write_fault(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(driver,'RECON_FOLDER',Path(directory)),patch.object(driver.os,'getuid',return_value=0,create=True):
            v=driver.recon_result('unavailable',phase='admitted',complete=False)
            with patch.object(driver.os,'open',side_effect=OSError('SECRET_SENTINEL')):
                with self.assertRaises(OSError):driver.recon_publish(v)
            self.assertFalse((Path(directory)/'control.json').exists())
            (Path(directory)/'control.json').mkdir()
            with self.assertRaises(ValueError):driver.recon_publish(v)
    def test_atomic_checkpoint_wrong_owner_nonregular_and_symlink_doubles(self):
        for mode,owner in ((stat.S_IFREG|0o600,1),(stat.S_IFDIR|0o700,0)):
            with tempfile.TemporaryDirectory() as directory,patch.object(driver,'RECON_FOLDER',Path(directory)),patch.object(driver.os,'getuid',return_value=0,create=True):
                with patch.object(driver.os,'fstat',return_value=NS(st_mode=mode,st_uid=owner,st_nlink=1)):
                    with self.assertRaises(ValueError):driver.recon_publish(driver.recon_result('unavailable',complete=False))
        with tempfile.TemporaryDirectory() as directory,patch.object(driver,'RECON_FOLDER',Path(directory)),patch.object(driver.os,'getuid',return_value=0,create=True):
            target=Path(directory)/'control.json';target.write_text('unchanged')
            original=Path.lstat
            def lstat(path,*args,**kwargs):
                return NS(st_mode=stat.S_IFLNK,st_uid=0,st_nlink=1) if path==target else original(path,*args,**kwargs)
            with patch.object(Path,'lstat',lstat):
                with self.assertRaises(ValueError):driver.recon_publish(driver.recon_result('unavailable',complete=False))
            self.assertEqual(target.read_text(),'unchanged')
    def test_new_namespace_exact_resources_mounts_and_no_old_outputs(self):
        args,mounts=host.recon_argv(hspec(),Path('C:/public-fixture'))
        self.assertEqual(args[args.index('--name')+1],host.RECON_NAME);self.assertEqual(len(mounts),3)
        v=created(args,mounts);v['Id']=CID;v['Labels']={'remission.task':host.RECON_NAME}
        life=NS(checked_state=lambda *_:None)
        host.audit_created(v,CID,args,mounts,life,reconcile=True)
        for key,bad in (('User','0'),('Memory',True),('ReadonlyRootfs',False),('CapAdd',['CHOWN']),('NetworkMode','bridge')):
            with self.subTest(key=key),self.assertRaises(ValueError):host.audit_created(dict(v,**{key:bad}),CID,args,mounts,life,reconcile=True)
        v['Mounts'].append(dict(Type='bind',Source='C:/old-private',Destination='/old',RW=False))
        with self.assertRaises(ValueError):host.audit_created(v,CID,args,mounts,life,reconcile=True)
    def test_reconciliation_routes_no_analysis_mutation_or_expensive_read(self):
        tree=ast.parse((ROOT/'tooling/foundation/s1_genuine_submit.py').read_bytes())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_reconcile')
        calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='invoke']
        self.assertEqual([(n.args[2].value,n.args[3].value) for n in calls],[('get','/api/session'),('post','/api/login'),('get','/api/session')])
        names={n.id for n in ast.walk(fn) if isinstance(n,ast.Name)}
        self.assertTrue({'export_queued_request','prepare','revalidate','selected_owner','run','run_binding'}.isdisjoint(names))
    def test_admission_new_mode_and_unknowns_refused_before_private(self):
        driver.recon_admit(spec());host.recon_admit(hspec())
        for key,value in (('key','newkey'),('owner_id','other'),('authority_generation',True),('executable',False),('root_go','fake')):
            for fn,s in ((driver.recon_admit,spec()),(host.recon_admit,hspec())):
                with self.subTest(key=key),self.assertRaises(ValueError):fn(dict(s,**{key:value}))

def supervision():
    expected=dict(cid=CID,pid=123,nonce='a'*48,deadline=850.)
    return dict(cid=CID,prearm=dict(live_ack_before_start=True,identity_matched=True,expected=expected,received=expected,
        popen_pid=123,before_ready_poll=dict(returncode=None),after_ready_poll=dict(returncode=None)),
        processes=dict(attach=dict(created=True,reaped=True,pid=456,returncode=124),watchdog=dict(created=True,reaped=True,pid=123,returncode=0)))
FINAL=dict(Id=CID,State=dict(Pid=0,Running=False,Status='exited',ExitCode=124,OOMKilled=False,Dead=False),RestartCount=0)
class FailureCollectionTests(unittest.TestCase):
    def test_missing_unreaped_or_bad_ack_disallows_collection(self):
        self.assertTrue(host.recon_collectable(supervision(),FINAL))
        for item in ({},dict(supervision(),prearm={}),dict(supervision(),cid='c'*64)):
            self.assertFalse(host.recon_collectable(item,FINAL))
        v=supervision();v['processes']['attach']['reaped']=False;self.assertFalse(host.recon_collectable(v,FINAL))
        v=supervision();v['prearm']['received']=dict(v['prearm']['expected'],pid=124);self.assertFalse(host.recon_collectable(v,FINAL))
    def exercise(self,*,reaped=True,success=False,collector_error=None):
        log=[]
        class StopUnconfirmed(RuntimeError):pass
        life=NS(StopUnconfirmed=StopUnconfirmed,check_deadline=lambda end:log.append(('deadline',end)),require_cid=lambda c:c,
            checked_state=lambda *_:None,stop_owned=lambda cid:(log.append(('stop',cid)) or []),
            inspect=lambda cid:(log.append(('final',cid)) or FINAL),stopped=lambda v:v['State']['Pid']==0)
        with tempfile.TemporaryDirectory() as directory:
            packet=Path(directory);s=hspec();args,mounts=host.recon_argv(s,packet)
            typed=created(args,mounts);typed['Id']=CID;typed['Labels']={'remission.task':host.RECON_NAME}
            def command(arguments,*_):
                if arguments[1:3]==['image','inspect']:raw=host.IMAGE
                elif arguments[1]=='ps':raw=''
                elif arguments[1]=='volume':raw=json.dumps(dict(Name=host.VOLUME,Labels={'remission.task':'remission-s1-completion-261024-r1'}))
                elif arguments[1]=='create':raw=CID
                else:raw=json.dumps(typed)
                return dict(stdout=raw,exit=0,error=None,cli_terminal='OWNED_POPEN_CHILD_EXIT_OBSERVED')
            def supervise(_cid,folder,*_,**__):
                folder.mkdir();v=supervision();v['processes']['attach']['reaped']=reaped
                (folder/'supervision.json').write_text(json.dumps(v));log.append(('supervise',_cid))
                if not success:raise RuntimeError('SECRET_SENTINEL')
            life.supervise=supervise
            def collect(*_,**__):
                log.append(('collect',CID))
                if collector_error=='stop':raise StopUnconfirmed('SECRET_SENTINEL')
                if collector_error:raise collector_error
                return json.dumps(metadata(fixture())).encode()
            with patch.object(host,'checked_reconcile',return_value=(s,packet)),patch.object(host,'load',side_effect=[life,NS(command_attempt=command)]),\
                    patch.object(host,'collect_public',side_effect=collect),patch.object(host.time,'monotonic',return_value=10.):
                if success and not collector_error:host.execute_reconcile(Path('public-only'), 'a'*64,10.)
                else:
                    with self.assertRaises(ValueError):host.execute_reconcile(Path('public-only'),'a'*64,10.)
            terminal=json.loads((packet/'results/terminal.json').read_bytes())
            self.assertNotIn('SECRET_SENTINEL',json.dumps(terminal))
            return log,terminal
    def test_nonzero_stays_failed_after_poststop_valid_checkpoint(self):
        log,terminal=self.exercise();self.assertEqual(terminal['status'],'failed');self.assertEqual(terminal['error_class'],'RuntimeError')
        self.assertLess(log.index(('stop',CID)),log.index(('collect',CID)));self.assertLess(log.index(('final',CID)),log.index(('collect',CID)))
    def test_unreaped_no_collection_and_read_fault_preserves_primary_failure(self):
        log,terminal=self.exercise(reaped=False);self.assertNotIn(('collect',CID),log);self.assertEqual(terminal['error_class'],'RuntimeError')
        _,terminal=self.exercise(collector_error=OSError('SECRET_SENTINEL'));self.assertEqual(terminal['error_class'],'RuntimeError')
    def test_success_and_common_absolute_work_deadline(self):
        log,terminal=self.exercise(success=True);self.assertEqual(terminal['status'],'reconciliation_saved')
        self.assertIn(('deadline',850.),log);self.assertNotIn(('deadline',1680.),log)
    def test_unknown_file_client_reap_halts_and_does_not_mask_primary(self):
        log,v=self.exercise(collector_error='stop')
        self.assertEqual(v['status'],'STOP UNCONFIRMED');self.assertEqual(v['error_class'],'RuntimeError')
        self.assertEqual(v['unresolved'],['public_file_client_reap']);self.assertEqual(log.count(('collect',CID)),1)

def scalar_contract():
    """Actual scalar source declarations, not an alternate S1 schema."""
    from typing import Annotated,Literal
    from pydantic import BaseModel,ConfigDict,Field,model_validator
    namespace=dict(Annotated=Annotated,Literal=Literal,BaseModel=BaseModel,ConfigDict=ConfigDict,Field=Field,
        model_validator=model_validator,json=json,hashlib=hashlib,__name__=__name__)
    selections=[('contracts/domain/common.py',{'Name','Identifier','Sha256','StrictModel','VersionRef'}),
        ('contracts/domain/analysis.py',{'canonical','sha','reference'}),
        ('contracts/domain/protocol.py',{'LAW','LAW_REF','SUPPORT_REF'}),
        ('contracts/domain/protocol_request.py',{'WCLS_PRIOR_REF','S1_ESTIMAND'}),
        ('contracts/domain/support_s1.py',{'OFFLINE_SETTINGS','OFFLINE_REF','CONFIG','CONFIG_REF','MODEL_REF','S1Submission'})]
    for path,names in selections:
        body=[]
        for node in ast.parse((ROOT/path).read_bytes()).body:
            defined={node.name} if isinstance(node,(ast.ClassDef,ast.FunctionDef)) else {n.id for n in node.targets if isinstance(n,ast.Name)} if isinstance(node,ast.Assign) else set()
            if defined&names:body.append(node)
        exec(compile(ast.Module(body=body,type_ignores=[]),path,'exec'),namespace)
    return namespace

class SourceInverseTests(unittest.TestCase):
    def test_narrow_repair_whole_module_inverse_to_reviewed_r1(self):
        prior=ast.parse(PRE_REPAIR_DRIVER);current=ast.parse((ROOT/'tooling/foundation/s1_genuine_submit.py').read_bytes())
        old_metadata=next(n for n in prior.body if isinstance(n,ast.FunctionDef) and n.name=='recon_metadata')
        cutoff_stmt=next(n for n in old_metadata.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
            and any(isinstance(v,ast.Constant) and v.value=='request_cutoff' for v in ast.walk(n)))
        old_run=next(n for n in prior.body if isinstance(n,ast.FunctionDef) and n.name=='run_reconcile')
        origin=next(n for n in ast.walk(old_run) if isinstance(n,ast.Compare) and isinstance(n.left,ast.Subscript)
            and isinstance(n.left.slice,ast.Constant) and n.left.slice.value=='expected_cutoff')
        class Undo(ast.NodeTransformer):
            def visit_Constant(self,node):
                changes={'remission-s1-original-reconcile-261024-r2':'remission-s1-original-reconcile-261024-r1',
                    '/data/s1-p3-original-reconcile-r2':'/data/s1-p3-original-reconcile-r1',
                    '/data/s1-p3-original-reconcile-r2/control.json':'/data/s1-p3-original-reconcile-r1/control.json'}
                return ast.copy_location(ast.Constant(changes.get(node.value,node.value)),node) if type(node.value) is str else node
            def visit_Compare(self,node):
                if isinstance(node.left,ast.Call) and isinstance(node.left.func,ast.Name) and node.left.func.id=='recon_instant':return deepcopy(origin)
                return self.generic_visit(node)
        for fn in [n for n in current.body if isinstance(n,ast.FunctionDef) and n.name=='recon_metadata']:
            fn.body=[deepcopy(cutoff_stmt) if isinstance(n,ast.Expr) and any(isinstance(v,ast.Name) and v.id=='recon_instant' for v in ast.walk(n)) else n for n in fn.body]
        current.body=[n for n in current.body if not (isinstance(n,ast.FunctionDef) and n.name=='recon_instant')
            and not (isinstance(n,ast.ImportFrom) and n.module=='datetime')]
        self.assertEqual(ast.dump(Undo().visit(current),include_attributes=False),ast.dump(prior,include_attributes=False))
        host_current=ast.parse((ROOT/'tooling/foundation/s1_genuine_once.py').read_bytes())
        self.assertEqual(ast.dump(Undo().visit(host_current),include_attributes=False),ast.dump(ast.parse(PRE_REPAIR_HOST),include_attributes=False))
    def test_original_typed_normalization_and_frozen_configuration(self):
        ns=scalar_contract();value=dict(SUB,configuration=ns['CONFIG_REF'])
        cls=ns['S1Submission'];normalized=cls.model_validate_json(ns['canonical'](value)).model_dump(mode='json')
        self.assertEqual(normalized,value);self.assertEqual(set(normalized),{'archive_id','mode','cutoff_day','configuration','previous_attempt'})
        for changed in (dict(value,configuration=CONFIG),dict(value,extra=True),dict(value,mode='S2')):
            with self.assertRaises(ValueError):cls.model_validate_json(ns['canonical'](changed))
    def test_all_old_mode_AST_restored_by_only_explicit_mode_dispatch(self):
        class Undo(ast.NodeTransformer):
            def visit_IfExp(self,node):
                node=self.generic_visit(node)
                if any(isinstance(n,ast.Name) and n.id in {'reconcile','RECON_KIND'} for n in ast.walk(node.test)):return node.orelse
                return node
            def visit_Call(self,node):
                node=self.generic_visit(node)
                if isinstance(node.func,ast.Name) and node.func.id=='public_tar':node.keywords=[v for v in node.keywords if v.arg!='reconcile']
                return node
        for filename,baseline in (('s1_genuine_once',BASELINE_HOST),('s1_genuine_submit',BASELINE_DRIVER)):
            old=ast.parse(baseline);current=ast.parse((ROOT/('tooling/foundation/'+filename+'.py')).read_bytes())
            oldfuncs={v.name:v for v in old.body if isinstance(v,ast.FunctionDef)}
            for fn in [n for n in current.body if isinstance(n,ast.FunctionDef) and n.name in oldfuncs]:
                fn=deepcopy(fn)
                if fn.name=='main' and filename=='s1_genuine_submit':
                    branch=fn.body[-1];self.assertIsInstance(branch,ast.If);fn.body[-1]=branch.orelse[0]
                fn.body=[n for n in fn.body if not (isinstance(n,ast.If) and any(isinstance(v,ast.Name) and v.id in {'RECON_KIND','reconcile'} for v in ast.walk(n.test)))]
                kw=list(zip(fn.args.kwonlyargs,fn.args.kw_defaults));kw=[(k,v) for k,v in kw if k.arg!='reconcile']
                fn.args.kwonlyargs=[k for k,_ in kw];fn.args.kw_defaults=[v for _,v in kw]
                fn=Undo().visit(fn)
                self.assertEqual(ast.dump(fn,include_attributes=False),ast.dump(oldfuncs[fn.name],include_attributes=False),(filename,fn.name))
