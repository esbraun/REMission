"""Host source-only checks: scientific payload is parsed, never imported/run."""
import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('draft',ROOT/'tooling/foundation/n_api02.py')
draft=importlib.util.module_from_spec(spec);spec.loader.exec_module(draft)

def unit_result(raw=b'UNIT byte fixture; no scientific format parsed on host'):
    controls=['target','dtype','axes','unit','predictive-mask-dtype','summary-sd','netcdf-patient-order','netcdf-dtype']
    return dict(kind='N-API02-UNIT-ONLY',seed=91740203,domain=9202,target='UNIT-API02-B',patients=['UNIT-API02-A','UNIT-API02-B'],
        model_fitted=False,genuine_data=False,Store_opened=False,availability_serialization_equal=True,
        semantics=dict(status='accepted',chains=4,draws=1000,patients=['UNIT-API02-A','UNIT-API02-B'],target_ids=['UNIT-API02-B'],
            expected_axes=['chain','draw','target'],predictive_axes=['chain','draw','target','arm','night'],
            expected_unit='quality_points',predictive_unit='reported_quality_points'),
        diagnostics=dict(accepted=True,**{k:dict(expected_contrast=1.) for k in ('rhat','ess_bulk','ess_tail','mcse')}),
        summary=dict(mean=.1,sd=.2,lower=-.3,upper=.5),controls=[dict(control=k,rejected=True) for k in controls],
        artifacts={name:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode()) for name in draft.ARTIFACTS})

class DraftControls(unittest.TestCase):
    def test_selected_metadata_missing_or_null_entrypoint_projects_null_only(self):
        """Template source + selected-output double; no actual Go/Docker claim."""
        payload='UNIT_NOT_EXECUTED'
        binding=json.loads((ROOT/'docs/implementation/poc-n-api02-bindings-20261023.json').read_bytes())
        for config in ({}, {'Entrypoint':None}):
            calls=[]
            def call(argv,label,deadline):
                calls.append(label)
                if label=='image':
                    template=argv[argv.index('--format')+1]
                    self.assertIn('{{json (index .Config "Entrypoint")}}',template)
                    self.assertNotIn('.Config.Entrypoint',template)
                    for required in ('User','WorkingDir','Cmd'):
                        self.assertIn('{{json .Config.'+required+'}}',template)
                    selected=copy.deepcopy(binding['qualified_image_config'])
                    selected['Entrypoint']=config.get('Entrypoint')
                    return json.dumps(selected)
                if label=='absence':raise RuntimeError('BOUNDARY_AFTER_METADATA')
                raise AssertionError('create forbidden')
            plan=dict(binding,payload_sha256=hashlib.sha256(payload.encode()).hexdigest())
            with self.assertRaisesRegex(RuntimeError,'BOUNDARY_AFTER_METADATA'):
                draft._controller_body(plan,payload,ROOT,None,call)
            self.assertEqual(calls,['image','absence'])

    def test_selected_metadata_required_fields_and_wrong_entrypoints_reject_before_absence(self):
        payload='UNIT_NOT_EXECUTED'
        binding=json.loads((ROOT/'docs/implementation/poc-n-api02-bindings-20261023.json').read_bytes())
        base=binding['qualified_image_config'];variants=[]
        for entrypoint in ([],['unexpected'],'unexpected',0,False,{}):
            v=copy.deepcopy(base);v['Entrypoint']=entrypoint;variants.append(v)
        for field in base:
            v=copy.deepcopy(base);v.pop(field);variants.append(v)
            if field!='Entrypoint':
                v=copy.deepcopy(base);v[field]=None;variants.append(v)
        for raw in [*map(json.dumps,variants),'null','[]','{malformed']:
            calls=[]
            def call(argv,label,deadline):
                calls.append(label);self.assertEqual(label,'image');return raw
            with self.subTest(raw=raw[:100]),self.assertRaises((ValueError,TypeError)):
                draft._controller_body(dict(binding,payload_sha256=hashlib.sha256(payload.encode()).hexdigest()),payload,ROOT,None,call)
            self.assertEqual(calls,['image'])

    def test_inspect_template_or_required_config_error_is_not_swallowed(self):
        payload='UNIT_NOT_EXECUTED';calls=[]
        def call(argv,label,deadline):
            calls.append(label)
            raise RuntimeError('selected inspect required Config/template failure')
        with self.assertRaisesRegex(RuntimeError,'required Config/template failure'):
            draft._controller_body(dict(learner_image='sha256:'+'a'*64,
                payload_sha256=hashlib.sha256(payload.encode()).hexdigest()),payload,ROOT,None,call)
        self.assertEqual(calls,['image'])

    def test_unknown_created_cid_stops_without_start_or_cleanup_guess(self):
        payload='UNIT_NOT_EXECUTED';image='sha256:'+'a'*64;config=dict(Id=image,User='10002:10002',WorkingDir='/app',Entrypoint=None,Cmd=['original'])
        plan=dict(learner_image=image,payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),qualified_image_config=config)
        class StopUnconfirmed(RuntimeError):pass
        calls=[]
        def call(argv,label,deadline):
            calls.append(label)
            if label=='image':return __import__('json').dumps(config)
            if label=='absence':return ''
            if label=='create':return 'UNKNOWN'
            raise AssertionError('no later command permitted')
        def require(value):raise ValueError('not literalCID')
        life=SimpleNamespace(require_cid=require,StopUnconfirmed=StopUnconfirmed,stop_owned=lambda cid:(_ for _ in ()).throw(AssertionError('no guessed cleanup')))
        with self.assertRaises(StopUnconfirmed):draft._controller_body(plan,payload,ROOT,life,call)
        self.assertEqual(calls,['image','absence','create'])

    def test_payload_change_fails_before_any_image_or_native_command(self):
        with self.assertRaisesRegex(ValueError,'payload changed'):
            draft._controller_body(dict(payload_sha256='0'*64),'UNIT_NOT_EXECUTED',ROOT,None,
                lambda *a:(_ for _ in ()).throw(AssertionError('command forbidden')))

    def test_transport_exact_bytes_and_invalid_names_count_base64_hash_or_length(self):
        original=unit_result();_,decoded=draft.decode_output(json.dumps(original))
        self.assertEqual(set(decoded),draft.ARTIFACTS)
        variants=[]
        for key,value in [('bytes',999),('sha256','0'*64),('base64','not+valid!'),('bytes',3145729)]:
            changed=copy.deepcopy(original);changed['artifacts']['posterior.nc'][key]=value;variants.append(changed)
        changed=copy.deepcopy(original);changed['artifacts']['../bad']=changed['artifacts'].pop('posterior.nc');variants.append(changed)
        changed=copy.deepcopy(original);changed['artifacts'].pop('predictive.npz');variants.append(changed)
        for value in variants:
            with self.subTest(value=str(value)[:80]),self.assertRaises((ValueError,TypeError)):draft.decode_output(json.dumps(value))

    def test_overflow_truncation_duplicate_keys_and_missing_corrupt_control_fail(self):
        with self.assertRaises(ValueError):draft.decode_output(' '*8388609)
        with self.assertRaises(ValueError):draft.decode_output(json.dumps(unit_result())[:-1])
        with self.assertRaisesRegex(ValueError,'duplicate'):draft.decode_output('{"kind":1,"kind":2}')
        changed=unit_result();changed['controls'].pop()
        with self.assertRaisesRegex(ValueError,'controls'):draft.decode_output(json.dumps(changed))
        # 5.55MiB raw remains below8MiB encoded but exceeds the5MiB total limit.
        with self.assertRaisesRegex(ValueError,'total'):draft.decode_output(json.dumps(unit_result(b'x'*1850000)))

    def test_target_axis_unit_or_nonfinite_scalar_is_not_partial_success(self):
        original=unit_result()
        for key,value in [('target','UNIT-API02-A'),('availability_serialization_equal',False)]:
            changed=copy.deepcopy(original);changed[key]=value
            with self.assertRaises(ValueError):draft.decode_output(json.dumps(changed))
        for key,value in [('expected_axes',['draw','chain','target']),('expected_unit','wrong')]:
            changed=copy.deepcopy(original);changed['semantics'][key]=value
            with self.assertRaises(ValueError):draft.decode_output(json.dumps(changed))
        changed=copy.deepcopy(original);changed['summary']['sd']=float('nan')
        with self.assertRaises(ValueError):draft.decode_output(json.dumps(changed))

    def test_planned_container_has_no_mounts_network_or_root_write(self):
        argv=draft.proposed_argv('sha256:'+'a'*64,'UNIT_PAYLOAD_NOT_EXECUTED')
        self.assertNotIn('--mount',argv);self.assertNotIn('-v',argv);self.assertNotIn('-p',argv)
        for key,value in [('--network','none'),('--user','10002:10002'),('--cpus','2'),('--pids-limit','64'),('--memory','2g'),('--memory-swap','2g')]:
            self.assertEqual(argv[argv.index(key)+1],value)
        self.assertIn('--read-only',argv);self.assertEqual(argv[-5:],['python','-I','-B','-c','UNIT_PAYLOAD_NOT_EXECUTED'])

    def test_payload_ast_has_no_fit_or_store_call_and_no_host_top_level_science(self):
        text=(ROOT/'tooling/foundation/n_api02_unit.py').read_text(encoding='utf-8');tree=ast.parse(text)
        self.assertEqual([n.name for n in tree.body if isinstance(n,ast.FunctionDef)],['main'])
        self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in tree.body))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        forbidden={'sample','build','run','fit','Store','Popen','system','exec','eval'}
        self.assertFalse(any((n.func.id if isinstance(n.func,ast.Name) else n.func.attr if isinstance(n.func,ast.Attribute) else '') in forbidden for n in calls))
        compile(tree,'UNIT_PAYLOAD_AST_ONLY','exec')

    def test_capture_keeps_ordinary_64KiB_and_only_unit_output_has_8MiB_cap(self):
        parent=ROOT/'artifacts/n-api02-capture-doubles';parent.mkdir(parents=True,exist_ok=True)
        for label,truncated in [('image',True),('unit-output',False)]:
            with tempfile.TemporaryDirectory(dir=parent) as folder:
                def process(argv,**kwargs):
                    kwargs['stdout'].write(b'x'*70000)
                    return SimpleNamespace(pid=123,wait=lambda timeout:0,poll=lambda:0)
                with patch.object(subprocess,'Popen',side_effect=process):
                    value=draft.command_attempt(['DOUBLED_NEVER_EXECUTED'],Path(folder),label,10,3)
                self.assertEqual(value['stdout_truncated'],truncated)
                self.assertEqual(len(value['stdout']),65536 if truncated else 70000)

class FrozenControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=ROOT/'artifacts/n-api02-source-tests';folder.mkdir(parents=True,exist_ok=True)
        cls.temp=tempfile.TemporaryDirectory(dir=folder);cls.template=Path(cls.temp.name)/'template'
        draft.freeze(cls.template,ROOT)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        import shutil
        self.tempfile=tempfile.TemporaryDirectory(dir=ROOT/'artifacts/n-api02-source-tests');self.addCleanup(self.tempfile.cleanup)
        self.folder=Path(self.tempfile.name)/'packet';shutil.copytree(self.template,self.folder)
        spec=importlib.util.spec_from_file_location('frozen_unit',self.folder/'operator/n_api02.py')
        self.op=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.op)
        self.path=self.folder/'plan.json';self.plan=json.loads(self.path.read_bytes());self.plan['root']=str(self.folder);self.authorize()
        self.binding=json.loads((self.folder/'bindings.json').read_bytes());self.life=self.op.load_lifecycle(self.folder)

    def authorize(self):
        self.path.write_text(json.dumps(self.plan),encoding='utf-8');self.digest=self.op.sha(self.path.read_bytes())

    def fixture(self,fail=None):
        calls=[];cid='a'*64;image=self.binding['learner_image'];payload=(self.folder/'payload/n_api02_unit.py').read_text()
        argv=self.op.proposed_argv(image,payload)
        state=dict(Status='created',Pid=0,ExitCode=0,Running=False,Paused=False,Restarting=False,Dead=False,OOMKilled=False)
        typed=dict(Id=cid,Image=image,User='10002:10002',Path='python',Args=argv[argv.index(image)+2:],State=state,
            RestartCount=0,Memory=2147483648,MemorySwap=2147483648,NanoCpus=2000000000,PidsLimit=64,
            ReadonlyRootfs=True,Privileged=False,CapAdd=None,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],
            NetworkMode='none',Mounts=[],PortBindings={},PublishAllPorts=False,RestartPolicy={'Name':'no','MaximumRetryCount':0},
            AutoRemove=False,Tmpfs={'/tmp':'rw,exec,nosuid,nodev,size=512m'})
        def capture(argv,output,label,timeout,grace):
            calls.append(label);self.assertTrue((output/'authorization-consumed.json').exists())
            raw={'image':json.dumps(self.binding['qualified_image_config']),'absence':'','create':cid,
                'prestart':json.dumps(typed),'unit-output':json.dumps(unit_result())}[label]
            value=dict(exit=0,timed_out=False,deadline_rejected=False,stdout=raw,stderr='',stdout_truncated=False,stderr_truncated=False)
            if fail:fail(label,value)
            return value
        return calls,capture

    def test_success_once_uses_exact_supervised_cid_and_retains_known_artifact_bytes(self):
        calls,capture=self.fixture()
        with patch.object(self.op,'check_host_dependency'),patch.object(self.op,'load_lifecycle',return_value=self.life),\
                patch.object(self.op,'command_attempt',side_effect=capture),patch.object(self.life,'supervise',return_value={'typed':'terminal'}) as supervise:
            value=self.op.execute(self.path,self.digest)
            with self.assertRaises(FileExistsError):self.op.execute(self.path,self.digest)
        self.assertEqual(calls,['image','absence','create','prestart','unit-output'])
        self.assertEqual(supervise.call_args.args[0],'a'*64)
        self.assertEqual(set(p.name for p in (self.folder/'results/unit-artifacts').iterdir()),draft.ARTIFACTS)
        self.assertEqual(value['status'],'UNIT_STRUCTURAL_API_ARTIFACT_PASS')

    def test_rehashed_wrong_accepted_proof_or_helper_fails_before_loading_or_reserving(self):
        p=self.folder/'bindings.json';v=json.loads(p.read_bytes());v['accepted_image_evidence']='b'*40;p.write_text(json.dumps(v))
        raw=p.read_bytes();self.plan['files']['bindings.json']=dict(bytes=len(raw),sha256=self.op.sha(raw));self.authorize()
        with patch.object(self.op,'load_lifecycle',side_effect=AssertionError('helper forbidden')),\
                patch.object(self.op,'command_attempt',side_effect=AssertionError('native forbidden')):
            with self.assertRaisesRegex(ValueError,'accepted UNIT learner'):self.op.execute(self.path,self.digest)
        self.assertFalse((self.folder/'results').exists())

    def test_bad_created_resources_never_start_and_stop_only_exact_owned_cid(self):
        def fail(label,value):
            if label=='prestart':
                v=json.loads(value['stdout']);v['ReadonlyRootfs']=False;value['stdout']=json.dumps(v)
        calls,capture=self.fixture(fail)
        with patch.object(self.op,'check_host_dependency'),patch.object(self.op,'load_lifecycle',return_value=self.life),\
                patch.object(self.op,'command_attempt',side_effect=capture),patch.object(self.life,'supervise',side_effect=AssertionError('no start')),\
                patch.object(self.life,'stop_owned',return_value=[]) as stop:
            with self.assertRaisesRegex(ValueError,'typed-created'):self.op.execute(self.path,self.digest)
            stop.assert_called_once_with('a'*64)
        self.assertNotIn('unit-output',calls)

    def test_truncated_collection_is_failure_and_not_partial_success(self):
        def fail(label,value):
            if label=='unit-output':value['stdout_truncated']=True
        calls,capture=self.fixture(fail)
        with patch.object(self.op,'check_host_dependency'),patch.object(self.op,'load_lifecycle',return_value=self.life),\
                patch.object(self.op,'command_attempt',side_effect=capture),patch.object(self.life,'supervise',return_value={}),\
                patch.object(self.life,'stop_owned',return_value=[]):
            with self.assertRaisesRegex(RuntimeError,'bounded command'):self.op.execute(self.path,self.digest)
        value=json.loads((self.folder/'results/observed-unit.json').read_bytes())
        self.assertEqual(value['status'],'failed');self.assertIsNone(value['result'])
        self.assertFalse((self.folder/'results/unit-artifacts').exists())

    def test_late_collection_remains_STOP_unknown_even_with_successful_cli_exit(self):
        def fail(label,value):
            if label=='unit-output':value['deadline_rejected']=True
        calls,capture=self.fixture(fail)
        with patch.object(self.op,'check_host_dependency'),patch.object(self.op,'load_lifecycle',return_value=self.life),\
                patch.object(self.op,'command_attempt',side_effect=capture),patch.object(self.life,'supervise',return_value={}),\
                patch.object(self.life,'stop_owned',return_value=[]):
            with self.assertRaises(self.life.StopUnconfirmed):self.op.execute(self.path,self.digest)
        self.assertEqual(json.loads((self.folder/'results/observed-unit.json').read_bytes())['status'],'STOP_UNCONFIRMED')

    def test_null_dependency_rehashed_plan_is_rejected_before_any_helper(self):
        p=self.folder/'bindings.json';v=json.loads(p.read_bytes());v['learner_image']=None;p.write_text(json.dumps(v))
        raw=p.read_bytes();self.plan['files']['bindings.json']=dict(bytes=len(raw),sha256=self.op.sha(raw));self.authorize()
        with patch.object(self.op,'load_lifecycle',side_effect=AssertionError('helper forbidden')):
            with self.assertRaisesRegex(ValueError,'accepted UNIT learner'):self.op.execute(self.path,self.digest)
        self.assertFalse((self.folder/'results').exists())

    def test_wrong_host_interpreter_fails_before_helper_or_reservation(self):
        with patch.object(self.op.sys,'executable','C:/different/python.exe'),\
                patch.object(self.op,'load_lifecycle',side_effect=AssertionError('helper denied')):
            with self.assertRaisesRegex(ValueError,'direct-base'):self.op.execute(self.path,self.digest)
        self.assertFalse((self.folder/'results').exists())

if __name__=='__main__':unittest.main()
