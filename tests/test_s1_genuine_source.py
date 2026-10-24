"""Protect receipt identity, private boundaries, resources and absolute custody."""
import ast
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/('tooling/foundation/'+name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
host=module('s1_genuine_once');driver=module('s1_genuine_submit')
CID='a'*64
SUB=dict(archive_id='archive-public-unit',mode='S1',cutoff_day=84,configuration={'unit':'scalar'},previous_attempt=None)
def proof():return dict(schema='support-s1-queued-request-v1',attempt_id='job-unit',owner_id='owner-unit',submission=deepcopy(SUB),
    receipt={'key':driver.KEY},active_attempts=[dict(attempt_id='job-unit',status='queued')])
def spec():return dict(kind='S1_GENUINE_SUBMIT_EXPORT_V1',executable=True,namespace=host.NAME,volume=host.VOLUME,image=host.IMAGE,
    bounds=dict(host.BOUNDS),no_claim_or_fit=True,store_instance='store-unit',authority_generation=1,owner_id='owner-unit',
    archive_id='archive-unit',archive_export_id='export-unit',admission_sha256='a'*64,source_commit='b'*40,
    source_review='c'*40,operation_review='d'*40,root_go='e'*64,archive_configuration_sha256='f'*64,
    submit_spec_sha256='a'*64,private_auth_path='C:/private-unit/auth.json',public_archive_path='C:/public-unit/archive',
    public_authority_path='C:/public-unit/authority.json')
def final():return dict(kind='s1_p3_submit_result',status='queued_export_saved',members=12,cutoff_day=84,
    response_confirmed=True,original_receipt_resolved=True,claim=False,fit=False)
def encoded(rows):return json.dumps(dict(schema='s1-p3-public-v1',rows=rows)).encode()
def tar(raw=b'{}',name=host.PUBLIC_NAME,kind=tarfile.REGTYPE):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as output:
        member=tarfile.TarInfo(name);member.type=kind;member.size=len(raw)
        output.addfile(member,io.BytesIO(raw) if kind==tarfile.REGTYPE else None)
    return stream.getvalue()
def created(args,mounts):
    return dict(Id=CID,RestartCount=0,State=dict(Status='created'),Image=host.IMAGE,User='10001:10001',Path='python',
        Args=args[args.index(host.IMAGE)+2:],Labels={'remission.task':host.NAME},Memory=2147483648,MemorySwap=2147483648,
        NanoCpus=2000000000,PidsLimit=64,ReadonlyRootfs=True,Privileged=False,CapAdd=None,CapDrop=['ALL'],
        SecurityOpt=['no-new-privileges'],Tmpfs={'/tmp':'rw,noexec,nosuid,nodev,size=128m'},NetworkMode='none',
        PublishAllPorts=False,RestartPolicy={'Name':'no','MaximumRetryCount':0},LogConfig={'Type':'none','Config':{}},PortBindings=None,
        Mounts=[dict(Type=k,Name=s,Source=s,Destination=d,RW=not r) for k,s,d,r in mounts])

class SubmitTests(unittest.TestCase):
    def flow(self,request=None,resolve=None,save=None):
        log=[]
        def request_default(value,key):log.append(('POST',key,deepcopy(value)));return dict(status_code=202,payload={'id':'job-unit'})
        def resolve_default(key,value,job):log.append(('resolve',job));return proof()
        result=driver.submit_export(request or request_default,resolve or resolve_default,
            save or (lambda name,value:log.append(('save',name))),deepcopy(SUB),driver.KEY)
        return result,log
    def test_one_post_intent_before_mutation_then_original_export(self):
        result,log=self.flow();self.assertEqual(log[0],('save','intent.json'))
        self.assertEqual(sum(v[0]=='POST' for v in log),1);self.assertEqual(log[1][1],driver.KEY)
        self.assertEqual(log[-1],('save','selection.json'));self.assertFalse(result['claim']);self.assertFalse(result['fit'])
    def test_unknown_response_resolves_original_key_without_retry(self):
        calls=[]
        def request(*_):calls.append('POST');raise ValueError('SECRET_SENTINEL')
        def resolve(key,value,job):calls.append((key,job));return proof()
        result,_=self.flow(request,resolve);self.assertEqual(calls,['POST',(driver.KEY,None)])
        self.assertFalse(result['response_confirmed'])
    def test_invalid_original_receipt_never_reports_saved(self):
        for change in ({'schema':'wrong'},{'submission':{}},{'receipt':{'key':'different'}},{'attempt_id':'other'},{'active_attempts':[]}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.flow(resolve=lambda *_:dict(proof(),**change))
    def test_missing_receipt_does_not_resubmit(self):
        calls=[]
        def request(*_):calls.append('POST');raise RuntimeError()
        with self.assertRaises(ValueError):self.flow(request,lambda *_:None)
        self.assertEqual(calls,['POST'])
    def test_required_private_persist_failure_propagates(self):
        calls=[]
        def save(name,_):
            calls.append(name)
            if name=='submission-response.json':raise OSError('SECRET_SENTINEL')
        with self.assertRaises(OSError):self.flow(save=save)
        self.assertEqual(calls,['intent.json','submission-response.json'])
    def test_private_exclusive_cap_precedes_file_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'intent.json'
            with self.assertRaises(ValueError):driver.private_once(path,{'x':'oversize'},cap=3)
            self.assertFalse(path.exists());driver.private_once(path,{'x':1})
            with self.assertRaises(FileExistsError):driver.private_once(path,{'x':2})
            self.assertEqual(json.loads(path.read_bytes()),{'x':1})
    def test_driver_refuses_before_import_or_private_path(self):
        with patch.object(driver,'PRIVATE',NS(mkdir=lambda **_:self.fail('private read'))):
            with self.assertRaises(ValueError):driver.run({'executable':False})
    def test_no_activation_claim_fit_or_store_reinitialization(self):
        tree=ast.parse((ROOT/'tooling/foundation/s1_genuine_submit.py').read_bytes())
        names={n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
        self.assertTrue({'fit','claim','initialize','initialise','intake','advance','approve'}.isdisjoint(names))
        run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        self.assertEqual(ast.unparse(run.body[0]),'admit(spec)')

class PublicTests(unittest.TestCase):
    def test_one_fixed_public_envelope(self):self.assertEqual(host.public_rows(encoded([final()])),[final()])
    def test_duplicate_nonfinite_unknown_private_data_rejected(self):
        for raw in (b'{"schema":"s1-p3-public-v1","rows":[],"rows":[]}',encoded([dict(final(),secret='SECRET_SENTINEL')]),
            b'{"schema":"s1-p3-public-v1","rows":[NaN]}',encoded([final(),final()]),b'[]',b' '*4097):
            with self.subTest(raw=raw[:40]),self.assertRaises((ValueError,TypeError)):host.public_rows(raw)
    def test_phase_times_finite_typed_nonnegative(self):
        row=dict(kind='s1_p3_phase',stage='submit',seconds=.5,response_seconds=.4,decode_seconds=.1)
        self.assertEqual(host.public_rows(encoded([row,final()]))[0],row)
        for bad in (True,-1,float('inf')):
            with self.assertRaises(ValueError):host.public_rows(encoded([dict(row,seconds=bad),final()]))
    def test_final_false_like_counts_refused(self):
        for key,bad in (('members',True),('cutoff_day',84.0),('claim',0),('fit',0),('response_confirmed',1)):
            with self.subTest(key=key),self.assertRaises(ValueError):host.public_rows(encoded([dict(final(),**{key:bad})]))
    def test_tar_framing_exact_name_regular_single_member_cap(self):
        self.assertEqual(host.public_tar(tar(b'{}')),b'{}')
        for value in (tar(name='private-input.json'),tar(raw=b'x'*4097),tar(kind=tarfile.SYMTYPE),tar()+b'x',tar()[:512]):
            with self.subTest(size=len(value)),self.assertRaises(ValueError):host.public_tar(value)
    def test_tar_extra_member_rejected_without_extraction(self):
        value=bytearray(tar());value[1536]=1
        with self.assertRaises(ValueError):host.public_tar(value)

class AdmissionTests(unittest.TestCase):
    def test_valid_scalar_spec_and_draft_unknown_refusals(self):
        host.admit(spec())
        for key,value in (('executable',False),('owner_id',None),('root_go',None),('authority_generation',True),('image','wrong')):
            with self.subTest(key=key),self.assertRaises(ValueError):host.admit(dict(spec(),**{key:value}))
    def test_private_path_is_string_admission_never_host_open(self):
        for value in ('C:/auth/../secret','C:/auth,readonly','relative/auth','C:/auth\\secret','C:/auth\nsecret'):
            with self.subTest(value=value),self.assertRaises(ValueError):host.admit(dict(spec(),private_auth_path=value))
    def test_exact_mounts_no_new_volume_or_accounts(self):
        args,mounts=host.argv(spec(),Path('C:/own-unit/packet'))
        self.assertEqual(len(mounts),5);self.assertEqual(args[args.index('--log-driver')+1],'none')
        self.assertEqual(args[args.index('--network')+1],'none');self.assertNotIn('create_account',args)
        self.assertEqual([(s,d,r) for k,s,d,r in mounts if k=='volume'],[(host.VOLUME,'/data',False)])
    def test_resource_config_and_mount_changes_fail_before_supervision(self):
        args,mounts=host.argv(spec(),Path('C:/own-unit/packet'));row=created(args,mounts)
        life=NS(checked_state=lambda value,cid:self.assertEqual((value['Id'],cid),(CID,CID)))
        host.audit_created(row,CID,args,mounts,life)
        changes={'Memory':0,'MemorySwap':0,'NanoCpus':0,'PidsLimit':True,'ReadonlyRootfs':False,'Privileged':True,
            'CapAdd':['CHOWN'],'CapDrop':[],'SecurityOpt':[],'NetworkMode':'bridge','PublishAllPorts':True,
            'RestartPolicy':{},'Image':'other','User':'0:0','Labels':{},'LogConfig':{'Type':'json-file','Config':{}},'Args':['wrong']}
        for key,value in changes.items():
            with self.subTest(key=key),self.assertRaises(ValueError):host.audit_created(dict(row,**{key:value}),CID,args,mounts,life)
        for change in ({'RW':True},{'RW':0},{'Destination':'/other'},{'Source':'C:/other'}):
            bad=deepcopy(row);bad['Mounts'][1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):host.audit_created(bad,CID,args,mounts,life)
        bad=deepcopy(row);bad['Mounts'].append(bad['Mounts'][0])
        with self.assertRaises(ValueError):host.audit_created(bad,CID,args,mounts,life)
    def test_draft_refuses_before_any_helper_or_process(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'spec.json';path.write_text('{"executable":false}')
            with patch.object(host,'load',side_effect=AssertionError('helper forbidden')):
                with self.assertRaises(ValueError):host.launch(path,host.sha(path.read_bytes()))
            self.assertEqual(list(Path(directory).iterdir()),[path])
    def test_host_payload_identity_mismatch_precedes_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            packet=Path(directory);value=spec();value['public_inputs']=[]
            payload=dict(value,key=driver.KEY,cutoff_day=84,members=12,request_seconds=180,private_export_cap=16*1024*1024)
            for name in host.FILES:
                path=packet/name;path.parent.mkdir(exist_ok=True)
                raw=json.dumps(payload).encode() if name.endswith('submit-spec.json') else b'[]' if name.endswith('archive-config.json') else b'# inert public source\n'
                path.write_bytes(raw);value['public_inputs'].append(dict(path=name,bytes=len(raw),sha256=host.sha(raw)))
            value['submit_spec_sha256']=host.sha((packet/'payload/submit-spec.json').read_bytes())
            value['archive_configuration_sha256']=host.sha((packet/'payload/archive-config.json').read_bytes())
            path=packet/'spec.json';path.write_text(json.dumps(value));host.checked_packet(path,host.sha(path.read_bytes()))
            payload['owner_id']='different-owner';raw=json.dumps(payload).encode();(packet/'payload/submit-spec.json').write_bytes(raw)
            value['submit_spec_sha256']=host.sha(raw)
            item=next(i for i in value['public_inputs'] if i['path']=='payload/submit-spec.json');item.update(bytes=len(raw),sha256=host.sha(raw))
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):host.checked_packet(path,host.sha(path.read_bytes()))
    def test_discard_custody_and_fixed_receipt_after_supervise(self):
        tree=ast.parse((ROOT/'tooling/foundation/s1_genuine_once.py').read_bytes())
        execute=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
        text=ast.unparse(execute)
        self.assertIn('discard_output=True',text);self.assertLess(text.index('life.supervise('),text.index('collect_public('))
        self.assertNotIn('attach.stdout',text);self.assertNotIn('attach.stderr',text)
        collect=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='collect_public')
        self.assertNotIn('read_bytes',ast.unparse(collect));self.assertIn('20481 - len(raw)',ast.unparse(collect))
    def test_fixed_outer_child_same_origin_and_reap_before_cid(self):
        tree=ast.parse((ROOT/'tooling/foundation/s1_genuine_once.py').read_bytes())
        launch=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='launch');text=ast.unparse(launch)
        self.assertIn('origin + 870 - time.monotonic()',text);self.assertIn('origin + 900',text)
        self.assertIn('stdout=subprocess.DEVNULL',text);self.assertIn('stderr=subprocess.DEVNULL',text)
        self.assertLess(text.index('process.kill()'),text.index("packet / 'results/cid.json'"))
        self.assertLess(text.index("checked_packet(path, token)"),text.index('subprocess.Popen('))

class CustodyTests(unittest.TestCase):
    def outer(self,mode):
        log=[]
        class StopUnconfirmed(RuntimeError):pass
        life=NS(StopUnconfirmed=StopUnconfirmed,check_deadline=lambda v:log.append(('deadline',v)),
            require_cid=lambda v:v if v==CID else host.require(False),
            stop_owned=lambda cid:log.append(('stop',cid)) or [],
            inspect=lambda cid:log.append(('inspect',cid)) or {'stopped':True},stopped=lambda v:v=={'stopped':True})
        with tempfile.TemporaryDirectory() as directory:
            packet=Path(directory);path=packet/'spec.json'
            class Child:
                pid=123;code=None;waits=0
                def poll(self):return self.code
                def wait(self,timeout):
                    log.append(('wait',timeout));self.waits+=1
                    if mode=='unreaped' or (mode=='timeout' and self.waits==1):raise host.subprocess.TimeoutExpired(['fixed'],timeout)
                    self.code=-9 if mode=='timeout' else 0
                    return self.code
                def kill(self):log.append('kill')
            child=Child()
            def popen(args,**kwargs):
                log.append(('Popen',args,kwargs));(packet/'results').mkdir()
                if mode!='unreaped':
                    (packet/'results/cid.json').write_text(json.dumps({'cid':CID}))
                    (packet/'results/terminal.json').write_text(json.dumps(dict(status='queued_export_saved',cid=CID,error_class=None,unresolved=[])))
                return child
            with patch.object(host,'checked_packet',return_value=(spec(),packet)),patch.object(host,'check_host'),\
                    patch.object(host,'load',return_value=life),patch.object(host.time,'monotonic',return_value=100.),\
                    patch.object(host.subprocess,'Popen',side_effect=popen):
                try:host.launch(path,'a'*64)
                except ValueError:pass
            result=json.loads((packet/'launcher/terminal.json').read_bytes())
        return result,log
    def test_owned_outer_success_same_absolute_origin(self):
        result,log=self.outer('success');self.assertEqual(result['status'],'queued_export_saved')
        self.assertTrue(result['controller_reaped']);self.assertIn(('wait',870.),log)
        self.assertIn(('deadline',1000.),log);self.assertIn(('stop',CID),log)
        call=next(v for v in log if isinstance(v,tuple) and v[0]=='Popen')
        self.assertEqual(call[1][-2:],['--origin','100.0'])
        self.assertEqual(call[2]['stdout'],host.subprocess.DEVNULL)
    def test_timeout_preserved_and_owned_controller_reaped_before_stop(self):
        result,log=self.outer('timeout');self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error_class'],'controller_deadline');self.assertEqual(result['controller_exit'],-9)
        self.assertLess(log.index('kill'),log.index(('stop',CID)))
    def test_unreaped_controller_prevents_cid_read_and_success(self):
        result,log=self.outer('unreaped');self.assertEqual(result['status'],'STOP UNCONFIRMED')
        self.assertIn('controller_reap',result['unresolved']);self.assertFalse(any(isinstance(v,tuple) and v[0]=='stop' for v in log))
    def transfer(self,chunks):
        log=[];receipts=[]
        class Child:
            pid=321
            stdout=NS(fileno=lambda:4,close=lambda:log.append('closed'))
            def poll(self):return 0
            def wait(self,timeout):log.append('reaped');return 0
            def kill(self):log.append('kill')
        life=NS(require_cid=lambda v:host.require(v==CID),check_deadline=lambda _:None,StopUnconfirmed=RuntimeError)
        with patch.object(host.subprocess,'Popen',side_effect=lambda args,**kw:log.append(args) or Child()),\
                patch.object(host.os,'set_blocking'),patch.object(host.os,'read',side_effect=chunks),\
                patch.object(host.time,'monotonic',return_value=100.):
            try:value=host.collect_public(CID,200.,life,receipts);failure=None
            except ValueError:value=None;failure='bounded_refusal'
        return value,failure,receipts,log
    def test_named_public_file_bounded_transfer_and_reap(self):
        value,failure,receipts,log=self.transfer([tar(encoded([final()])),b''])
        self.assertIsNone(failure);self.assertEqual(host.public_rows(value),[final()]);self.assertTrue(receipts[0]['reaped'])
        self.assertEqual(log[0],['docker','cp',CID+':'+host.PUBLIC_PATH,'-'])
    def test_transport_overflow_fails_and_reaps_without_parse(self):
        value,failure,receipts,log=self.transfer([b'x'*20481])
        self.assertIsNone(value);self.assertEqual(failure,'bounded_refusal');self.assertTrue(receipts[0]['reaped'])
        self.assertIn('kill',log)

if __name__=='__main__':unittest.main()
