"""Exercise actual selected SQL and full existing control validator with inert metadata."""
import ast
from contextlib import contextmanager
from copy import deepcopy
import hashlib,json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import test_s1_genuine_source as prior
from test_s1_genuine_source import host,driver,ROOT,CID,created,spec as submit_spec,tar
BASELINE=None

MEMBERS=tuple('public-unit-'+str(i) for i in range(12))
PARTITIONS=tuple((p,p+'-'+s) for p in MEMBERS for s in ('S0','S1'))
MANIFEST='a'*64
OWNER='owner-unit'
class Ref:
    def __init__(self,value):self.value=value
    def model_dump(self,**_):return deepcopy(self.value)
    def __getattr__(self,key):
        try:return self.value[key]
        except KeyError:raise AttributeError(key) from None
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def digest(value):return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()
class AdmissionError(RuntimeError):pass

def actual_validator():
    raw=(ROOT/'services/foundation/store.py').read_bytes();tree=ast.parse(raw)
    bundle=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_bundle')
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Store')
    control=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='validate_control')
    env=dict(Path=Path,json=json,canonical=canonical,digest=digest,AdmissionError=AdmissionError,
        CAPABILITY='LIVE-HOLD-01/1.0.0',sqlite3=NS(Error=LookupError),__file__=str(ROOT/'services/foundation/store.py'))
    exec(compile(ast.Module(body=[bundle,control],type_ignores=[]),'actual-scalar-store-validator','exec'),env)
    class StoreType:
        validate_control=env['validate_control']
        def __init__(self,*_):raise AssertionError('ordinary Store constructor forbidden')
    return StoreType

class Row(dict):
    def __getitem__(self,key):return list(self.values())[key] if type(key) is int else super().__getitem__(key)
class Cursor:
    def __init__(self,rows,log):self.rows=rows;self.log=log
    def fetchone(self):return self.rows[0] if self.rows else None
    def fetchmany(self,size):self.log.append(('fetchmany',size));return self.rows[:size]
    def __iter__(self):return iter(self.rows)

def fixture(**changes):
    log=[];bindings=json.loads((ROOT/'contracts/service/bindings-v1.json').read_bytes())
    observed=json.loads((ROOT/'contracts/runs/bindings-v2.json').read_bytes())['observed_representation']
    authority=dict(service_contract=bindings['live_hold'],schema_binding=bindings['service_schema_set'],observed_binding=observed)
    installed=NS(control=Ref(dict(database_instance_id=driver.BIND_EXPECTED['store_instance'],capability='LIVE-HOLD-01/1.0.0',
        minimum_reader_writer_capability='LIVE-HOLD-01/1.0.0',authority_generation=1,authority_sha256=digest(canonical(authority)),
        review_rules_sha256=digest(canonical({})),enabled=False,activation_id='fixture-only')),
        authority=NS(**{k:Ref(v) for k,v in authority.items()},model_dump=lambda **_:deepcopy(authority)),review_rules=Ref({}))
    control=dict(installed.control.model_dump(),database_device=1,database_inode=2,lock_device=1,lock_inode=3)
    archive=dict(owner_id=OWNER,mode='restricted_support_historical',export_sha256=MANIFEST,manifest_sha256=MANIFEST,
        admission_sha256=driver.BIND_EXPECTED['admission_sha256'],members=12,qualification_scope='accepted_saved_producer',
        archive_id=driver.BIND_EXPECTED['archive_id'])
    control.update(changes.get('control',{}));archive.update(changes.get('archive',{}))
    class File:
        def __init__(self,inode):self.inode=inode
        def stat(self):return NS(st_dev=1,st_ino=self.inode)
        def as_uri(self):return 'file:///data/remission.sqlite'
    class Gate:
        database=File(changes.get('database_inode',2));path=File(changes.get('lock_inode',3));active=False
        @contextmanager
        def hold(self):
            log.append('gate-acquire')
            if changes.get('gate_error'):raise AdmissionError('unit invalid existing lock')
            self.active=True
            try:yield
            finally:self.active=False;log.append('gate-release')
    gate=Gate()
    class DB:
        row_factory=None;query=False
        def execute(self,sql,args=()):
            log.append(('sql',sql,args));require_read=sql.startswith('SELECT')
            if require_read and not self.query:raise AssertionError('selected SQL before query_only')
            if sql=='PRAGMA query_only=ON':self.query=True;rows=[]
            elif sql=='PRAGMA query_only':rows=[Row(value=0 if changes.get('query_only_fail') else 1)]
            elif sql in ('PRAGMA foreign_keys=ON','PRAGMA synchronous=FULL','PRAGMA busy_timeout=5000','BEGIN'):rows=[]
            elif sql=='PRAGMA foreign_keys':rows=[Row(value=1)]
            elif sql=='PRAGMA synchronous':rows=[Row(value=2)]
            elif sql=='PRAGMA journal_mode':
                if changes.get('wal_error'):raise OSError('SECRET_SENTINEL')
                rows=[Row(value=changes.get('journal','wal'))]
            elif sql==driver.SQL_MIGRATIONS or sql=='SELECT version FROM schema_migrations':rows=[Row(version=v) for v in changes.get('migrations',(1,2,3,4,5))]
            elif sql=='SELECT * FROM service_control WHERE singleton=1':rows=[] if changes.get('missing_control') else [Row(control)]
            elif sql==driver.SQL_ARCHIVE:rows=[Row(archive)]*changes.get('archives',1)
            elif sql==driver.SQL_OWNER:rows=[Row(id=OWNER)]*changes.get('owners',1)
            elif sql==driver.SQL_MEMBERS:rows=[Row(id=p,owner_id=('foreign-owner' if changes.get('foreign') and i==7 else OWNER)) for i,p in enumerate(MEMBERS)][:changes.get('member_count',12)]
            elif sql==driver.SQL_PARTITIONS:rows=[Row(patient_id=p,partition_id=s) for p,s in PARTITIONS][:changes.get('partitions',24)]
            elif sql==driver.SQL_PENDING:rows=[Row(value=1)] if changes.get('pending') else []
            elif sql==driver.SQL_PENDING_WORK:rows=[Row(value=1)] if changes.get('pending_work') else []
            else:raise AssertionError('write/unknown SQL refused')
            return Cursor(rows,log)
        def rollback(self):log.append('rollback')
        def close(self):log.append('close')
    db=DB()
    def connect(database,**kwargs):
        assert gate.active;log.append(('connect',database,kwargs))
        if changes.get('missing_database'):raise OSError('SECRET_SENTINEL')
        return db
    def run():return driver.protected_binding(connect,'inert-row-factory',installed,gate,actual_validator(),MEMBERS,PARTITIONS,MANIFEST)
    return run,log,db,installed

def binding_spec():
    return dict(kind=host.BIND_KIND,executable=True,namespace=host.BIND_NAME,volume=host.VOLUME,image=host.IMAGE,
        bounds=dict(host.BOUNDS),**host.BIND_EXPECTED,owner_id=None,binding_only=True,no_submit_claim_fit=True,
        public_authority_sha256=host.AUTHORITY_SHA,source_commit='b'*40,
        authority_mode='EXTERNAL_ROOT_EXACT_ONCE_AFTER_SOURCE_OP',binding_spec_sha256='f'*64)

class ReadonlyTests(unittest.TestCase):
    def test_complete_control_coherent_readonly_before_selected_SQL(self):
        run,log,_,_=fixture();result=run()
        self.assertEqual(result['owner_id'],OWNER);self.assertEqual(result['members'],12)
        self.assertFalse(result['submit']);self.assertFalse(result['claim']);self.assertFalse(result['fit'])
        connection=next(v for v in log if isinstance(v,tuple) and v[0]=='connect')
        self.assertEqual(connection,('connect','file:///data/remission.sqlite?mode=ro',dict(uri=True,isolation_level=None,timeout=5)))
        sql=[v[1] for v in log if isinstance(v,tuple) and v[0]=='sql']
        self.assertEqual(sql[0],'PRAGMA query_only=ON');self.assertLess(sql.index('BEGIN'),sql.index(driver.SQL_ARCHIVE))
        self.assertEqual(sql.count('SELECT * FROM service_control WHERE singleton=1'),2)
        self.assertEqual(log[-3:],['rollback','close','gate-release']);self.assertNotIn('commit',log)
    def test_schema_control_generation_DB_lock_and_bindings_fail_closed(self):
        cases=[dict(control={'authority_generation':2}),dict(control={'database_instance_id':'wrong'}),
            dict(control={'authority_sha256':'f'*64}),dict(control={'review_rules_sha256':'f'*64}),
            dict(control={'minimum_reader_writer_capability':'wrong'}),dict(database_inode=20),dict(lock_inode=30),
            dict(migrations=(1,2,3,4)),dict(migrations=(1,2,3,4,5,6)),dict(missing_control=True)]
        for case in cases:
            with self.subTest(case=case),self.assertRaises((ValueError,AdmissionError)):
                run,log,_,_=fixture(**case);run()
            self.assertIn('close',log);self.assertNotIn(('sql',driver.SQL_ARCHIVE,(driver.BIND_EXPECTED['archive_id'],)),log)
    def test_missing_multiple_foreign_owner_members_partitions_admission_pending(self):
        cases=[dict(archives=0),dict(archives=2),dict(owners=0),dict(owners=2),dict(foreign=True),dict(member_count=11),
            dict(partitions=23),dict(archive={'admission_sha256':'wrong'}),dict(archive={'manifest_sha256':'wrong'}),
            dict(archive={'mode':'wrong'}),dict(archive={'qualification_scope':'structural_fixture'}),dict(pending=True),dict(pending_work=True)]
        for case in cases:
            with self.subTest(case=case),self.assertRaises(ValueError):fixture(**case)[0]()
    def test_WAL_queryonly_and_no_create_failure_has_no_fallback(self):
        for case in (dict(journal='delete'),dict(wal_error=True),dict(query_only_fail=True),dict(missing_database=True),dict(gate_error=True)):
            run,log,_,_=fixture(**case)
            with self.subTest(case=case),self.assertRaises((OSError,ValueError,AdmissionError)):run()
            self.assertFalse(any(isinstance(v,tuple) and v[0]=='sql' and v[1]==driver.SQL_ARCHIVE for v in log))
            self.assertEqual(sum(isinstance(v,tuple) and v[0]=='connect' for v in log),0 if case.get('gate_error') else 1)
    def test_cardinality_capped_before_materializing_and_no_payload_scan(self):
        run,log,db,_=fixture();run()
        caps=[v[1] for v in log if isinstance(v,tuple) and v[0]=='fetchmany']
        self.assertEqual(caps,[6,2,2,13,25,2,2])
        for sql in (driver.SQL_ARCHIVE,driver.SQL_OWNER,driver.SQL_MEMBERS,driver.SQL_PARTITIONS,driver.SQL_PENDING,driver.SQL_PENDING_WORK):
            self.assertIn('LIMIT ',sql);self.assertNotIn('SELECT *',sql)
            self.assertFalse(any(word in sql for word in ('password','username','session','payload','raw_source','history')))
        with self.assertRaises(AssertionError):db.execute('INSERT INTO accounts VALUES (?)',('SECRET_SENTINEL',))
    def test_actual_gate_no_create_and_existing_identity_contract(self):
        tree=ast.parse((ROOT/'services/foundation/admission.py').read_bytes());text=ast.unparse(tree)
        self.assertIn('resolve(strict=True)',text);self.assertIn('os.O_RDWR | os.O_NOFOLLOW',text)
        self.assertNotIn('os.O_CREAT',text);self.assertNotIn('os.O_TRUNC',text)
        self.assertIn('(opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)',text)

class ModeTests(unittest.TestCase):
    def test_binding_spec_no_auth_or_archive_mount_and_no_submit_fallthrough(self):
        value=binding_spec();host.admit(value);driver.binding_admit({k:v for k,v in value.items() if k not in ('image','bounds','binding_spec_sha256')})
        args,mounts=host.argv(value,Path('C:/public-unit/packet'))
        self.assertEqual(len(mounts),2);self.assertFalse(any('/private' in arg or '/public'==arg for arg in args))
        self.assertIn('/operation/binding-spec.json',args);self.assertNotIn('/operation/submit-spec.json',args)
        for extra in ('private_auth_path','public_archive_path','key'):
            with self.assertRaises(ValueError):host.admit(dict(value,**{extra:'SECRET_SENTINEL'}))
        tree=ast.parse((ROOT/'tooling/foundation/s1_genuine_submit.py').read_bytes())
        function=next(v for v in tree.body if isinstance(v,ast.FunctionDef) and v.name=='run_binding')
        text=ast.unparse(function);self.assertEqual(ast.unparse(function.body[0]),'binding_admit(spec)')
        self.assertNotIn('TestClient',text);self.assertNotIn('Store(',text);self.assertNotIn('environment_settings',text)
        self.assertNotIn('/private/auth.json',text)
    def test_binding_resource_mutations_and_extra_mount_rejected(self):
        args,mounts=host.argv(binding_spec(),Path('C:/public-unit/packet'));row=created(args,mounts)
        row['Labels']={'remission.task':host.BIND_NAME};life=NS(checked_state=lambda *_:None)
        host.audit_created(row,CID,args,mounts,life,binding=True)
        for field,bad in (('User','0:0'),('PidsLimit',True),('ReadonlyRootfs',False),('CapAdd',['CHOWN']),('Memory',1),('Labels',{'remission.task':host.NAME})):
            with self.subTest(field=field),self.assertRaises(ValueError):host.audit_created(dict(row,**{field:bad}),CID,args,mounts,life,binding=True)
        row['Mounts'].append(dict(Type='bind',Source='C:/private-unit/auth.json',Destination='/private/auth.json',RW=False))
        with self.assertRaises(ValueError):host.audit_created(row,CID,args,mounts,life,binding=True)
    def test_closed_public_binding_receipt_no_secret_or_false_like(self):
        value=fixture()[0]();raw=json.dumps(value).encode();self.assertEqual(host.public_rows(raw,binding=True),[value])
        for changes in ({'email':'SECRET_SENTINEL'},{'owner_id':['first','second']},{'members':True},
            {'binding_only':1},{'submit':True},{'authority_generation':True},{'admission_sha256':'wrong'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):host.public_rows(json.dumps(dict(value,**changes)).encode(),binding=True)
        for raw in (b'{"schema":"x","schema":"y"}',b'{"x":NaN}',b'x'*4097):
            with self.assertRaises(ValueError):host.public_rows(raw,binding=True)
        with self.assertRaises(ValueError):host.public_rows(json.dumps(value).encode())
    def test_nonexec_or_unknown_review_before_project_imports(self):
        for bad in ({'executable':False},{'root_go':'e'*64},{'source_commit':None},{'authority_generation':2},
                {'authority_mode':'INTERNAL_OR_AUTOMATIC'}):
            value=dict(binding_spec(),**bad)
            with self.assertRaises(ValueError):host.admit(value)
            with self.assertRaises(ValueError):driver.run_binding(value)
    def test_enabled_fix_uses_actual_contract_field_and_inverse_only_declared_expression(self):
        tree=ast.parse((ROOT/'contracts/service/live_hold.py').read_bytes())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='InstalledBundle')
        fields={n.target.id for n in cls.body if isinstance(n,ast.AnnAssign)}
        self.assertIn('control',fields);self.assertNotIn('enabled',fields)
        control=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ControlBinding')
        self.assertIn('enabled',{n.target.id for n in control.body if isinstance(n,ast.AnnAssign)})
        settings=NS(installed=NS(control=NS(enabled=False)))
        self.assertFalse(settings.installed.control.enabled)
        with self.assertRaises(AttributeError):getattr(settings.installed,'enabled')
        raw=(ROOT/'tooling/foundation/s1_genuine_submit.py').read_text()
        self.assertEqual(raw.count('not settings.installed.control.enabled'),1)
        prior=ast.parse(BASELINE);current=ast.parse(raw)
        def function(tree,name):return ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name))
        self.assertEqual(function(prior,'run').replace('not settings.installed.enabled','not settings.installed.control.enabled'),function(current,'run'))
        for name in ('admit','private_once','emit','submit_export','invoke'):
            self.assertEqual(function(prior,name),function(current,name))
    def test_binding_timeout_unreaped_and_cross_mode_success_refused(self):
        # Reuse the already fault-tested owned-controller doubles in the actual
        # new mode, without touching the original27-control source file.
        with patch('test_s1_genuine_source.spec',return_value=binding_spec()):
            value,_=prior.CustodyTests().outer('timeout');self.assertEqual(value['status'],'failed')
            value,_=prior.CustodyTests().outer('unreaped');self.assertEqual(value['status'],'STOP UNCONFIRMED')
            value,_=prior.CustodyTests().outer('success')
            self.assertEqual(value['status'],'failed');self.assertEqual(value['error_class'],'controller_terminal_unconfirmed')
    def test_binding_exact_receipt_name_and_maximum_closed_public_size(self):
        value=fixture()[0]();value['owner_id']='x'*128;raw=json.dumps(value).encode()
        self.assertLessEqual(len(raw),4096);self.assertEqual(host.public_rows(raw,binding=True),[value])
        encoded=tar(raw,name=host.BIND_PUBLIC_NAME)
        self.assertEqual(host.public_tar(encoded,binding=True),raw)
        with self.assertRaises(ValueError):host.public_tar(encoded)
        with self.assertRaises(ValueError):host.public_tar(tar(raw),binding=True)

if __name__=='__main__':unittest.main()
