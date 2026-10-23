"""Source/stdlib controls only. No numerical prediction or science import."""
import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from contracts.domain.analysis import sha
from contracts.domain.protocol_request import EXECUTABLE_CONFIGURATIONS
from contracts.domain.support_s2 import (CELLS,CONFIG_REF,DEFINITIONS,HSTAR_REF,
    PrecisionSummary,S2Request,S2Result,precision_status)

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
operator=module('s2_source_operator','tooling/foundation/s2_numerics.py')
entry=module('s2_source_entry','tooling/foundation/s2_numerics_entry.py')


def wire():
    return dict(schema_version='s2-prediction-candidate-1.0.0',owner_id='UNIT-owner',store_id='UNIT-store',
        generation_id='UNIT-generation',cohort_id='UNIT-cohort',fit_id='UNIT-fit',fit_artifact_sha256='0'*64,
        fitted_hstar=HSTAR_REF,fitted_snapshot_sha256='1'*64,configuration=CONFIG_REF,definitions=DEFINITIONS,
        members=tuple(dict(patient_id=f'UNIT-{i:02}',patient_version=1,history_sha256='2'*64,
            revisions_sha256='3'*64,observed=(5,4),missing=(1,2)) for i in range(12)),
        cutoff=14,target_id='UNIT-07',context_id='UNIT-context',context_version=1,
        current_snapshot_sha256='4'*64,decision_day=20,reward_day=21,h=7,
        expires_before_decision=28,x_current=(7.,0.,2.,.25))


class Contracts(unittest.TestCase):
    def test_closed_activation_and_nonfirst_complete_owned_context(self):
        value=S2Request.model_validate(wire())
        self.assertEqual(value.target_id,value.members[7].patient_id)
        self.assertFalse(EXECUTABLE_CONFIGURATIONS)
        self.assertFalse(__import__('contracts.domain.support_s2',fromlist=['CONFIG']).CONFIG['executable'])

    def test_malformed_identity_roster_time_counts_or_features_rejected(self):
        variants=[]
        for key,value in [('target_id','unknown'),('h',8),('expires_before_decision',29),('reward_day',22),
                ('cutoff',28),('decision_day',28),('x_current',(7.,1.,2.,.5)),('x_current',(7.,0.,2.5,.25)),
                ('x_current',(float('nan'),0.,2.,.25))]:
            item=wire();item[key]=value;variants.append(item)
        for change in ('missing','order','duplicate','counts','configuration','hstar','definition'):
            item=copy.deepcopy(wire())
            if change=='missing':item['members']=item['members'][:-1]
            elif change=='order':item['members']=tuple(reversed(item['members']))
            elif change=='duplicate':item['members'][1]['patient_id']=item['members'][0]['patient_id']
            elif change=='counts':item['members'][3]['missing']=(14,14)
            elif change=='configuration':item['configuration']['sha256']='f'*64
            elif change=='hstar':item['fitted_hstar']['sha256']='f'*64
            else:item['definitions']['prior']['sha256']='f'*64
            variants.append(item)
        for value in variants:
            with self.subTest(value=str(value)[:60]),self.assertRaises(ValueError):S2Request.model_validate(value)

    def test_every_precision_gate_and_forced_constant_chain_abstention(self):
        good=dict(probability=.7,half_probability=.7,constant_chain=False,rhat=1.001,
                  ess_bulk=500.,ess_tail=500.,mcse=.01)
        self.assertEqual(precision_status(**good),'candidate_ready')
        for key,value in [('constant_chain',True),('rhat',1.01),('ess_bulk',399.9),('ess_tail',399.9),
                ('mcse',0.),('mcse',.0200001),('mcse',None),('half_probability',.67),('probability',.51)]:
            changed=dict(good,**{key:value})
            self.assertNotEqual(precision_status(**changed),'candidate_ready')
            with self.assertRaises(ValueError):PrecisionSummary.model_validate(dict(changed,status='candidate_ready'))

    def test_all_nine_cells_direction_and_unready_point_five_are_enforced(self):
        p=dict(probability=.7,half_probability=.7,constant_chain=False,rhat=1.001,
               ess_bulk=500.,ess_tail=500.,mcse=.01,status='candidate_ready')
        good=dict(schema_version='s2-prediction-candidate-1.0.0',request_sha256=sha(wire()),target_id='UNIT-07',
            context_id='UNIT-context',context_version=1,status='candidate_ready',reason='UNIT',primary=p,
            cells=tuple(dict(delta0=a,delta1=b,precision=copy.deepcopy(p)) for a,b in CELLS),probability=.7,
            serving_authority=False,empirical_domain_only=True)
        self.assertEqual(len(S2Result.model_validate(good).cells),9)
        for change in ('missing','order','reversal','notready','authority'):
            value=copy.deepcopy(good)
            if change=='missing':value['cells']=value['cells'][:-1]
            elif change=='order':value['cells']=tuple(reversed(value['cells']))
            elif change=='reversal':value['cells'][0]['precision'].update(probability=.3,half_probability=.3)
            elif change=='notready':value['status']='numerical_unready'
            else:value['serving_authority']=True
            with self.assertRaises(ValueError):S2Result.model_validate(value)


class SourceAxes(unittest.TestCase):
    def test_joint_shapes_dtype_member_order_and_explicit_target_without_numeric_runtime(self):
        class Array:
            def __init__(self,shape,dtype='float64',bad=False):self.shape=shape;self.dtype=dtype;self.bad=bad
            def __abs__(self):return self
            def __ge__(self,other):return self.bad
            def __lt__(self,other):return self.bad
        fake=SimpleNamespace(ndarray=Array,dtype=lambda x:x,isfinite=lambda x:True,abs=abs,
                             all=lambda x:x,any=lambda x:x)
        tree=ast.parse((ROOT/'methods/support/s2_prediction.py').read_text(encoding='utf-8'))
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='checked_arrays')
        namespace=dict(np=fake,FIELDS={'alpha','tau','e_T','b','rho','s_e','s_Q'})
        exec(compile(ast.Module(body=[function],type_ignores=[]),'isolated_shape_guard_AST','exec'),namespace)
        ids=[f'UNIT-{i:02}' for i in range(12)];context=S2Request.model_validate(wire())
        arrays={key:Array((4,1000,12) if key in ('alpha','tau','e_T') else (4,1000,4) if key=='b' else (4,1000)) for key in namespace['FIELDS']}
        self.assertEqual(namespace['checked_arrays'](arrays,ids,context),7)
        for key,changed in [('alpha',Array((1000,4,12))),('tau',Array((4,1000,11))),
                ('b',Array((4,1000,3))),('s_e',Array((4,1000),'float32')),('rho',Array((4,1000),bad=True))]:
            with self.subTest(key=key),self.assertRaises(ValueError):namespace['checked_arrays'](dict(arrays,**{key:changed}),ids,context)
        with self.assertRaises(ValueError):namespace['checked_arrays'](arrays,list(reversed(ids)),context)

    def test_unchanged_reference_two_g_calls_and_no_oracle_ndtr(self):
        tree=ast.parse((ROOT/'methods/support/s2_prediction.py').read_text(encoding='utf-8'))
        predict=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='predict')
        self.assertEqual(sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='expected_quality' for n in ast.walk(predict)),2)
        oracle=(ROOT/'tooling/foundation/s2_numerics_oracle.py').read_text(encoding='utf-8')
        self.assertNotIn('from scipy.special',oracle);self.assertNotIn('ndtr(',oracle)
        self.assertIn('math.fsum',oracle);self.assertIn('from scipy.integrate import quad',oracle)
        expected='b7bbd413ce2eff3a15610db3bc663f2e0f688bbc815bb6331a2e7f429cc6ab68'
        # Git source bytes are LF; local checkout may use CRLF.
        raw=(ROOT/'methods/nof1/observation.py').read_bytes().replace(b'\r\n',b'\n')
        self.assertEqual(hashlib.sha256(raw).hexdigest(),expected)

    def test_only_fixed64_and16_and_no_heldout_inputs_present(self):
        value=json.loads((ROOT/'tooling/foundation/s2_numerics_inputs/fixed.json').read_bytes())
        self.assertEqual((len(value['scalar']),len(value['cdf'])),(64,16))
        self.assertEqual(len({v['id'] for v in value['scalar']}),64)
        self.assertFalse((ROOT/'tooling/foundation/s2_numerics_inputs/held-out.json').exists())


class Carrier(unittest.TestCase):
    def test_carrier_full_inventory_unknown_extra_never_read_and_known_hash_change_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as directory:
            folder=Path(directory);payload=folder/'payload';app=folder/'app';payload.mkdir();app.mkdir()
            expected={}
            for i in range(84):
                p=app/f'known-{i:02}.py';p.write_bytes(b'UNIT public source fixture')
                expected['/app/'+p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
            for name in entry.PAYLOAD_FILES:(payload/name).write_bytes(b'UNIT source fixture')
            (payload/'dependency.json').write_text(json.dumps(dict(qualified_project_source=expected)),encoding='utf-8')
            manifest=dict(kind='S2-fixed-public-carrier-v1',files={p.name:dict(bytes=len(p.read_bytes()),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in payload.iterdir()})
            raw=json.dumps(manifest).encode();(payload/'manifest.json').write_bytes(raw);digest=hashlib.sha256(raw).hexdigest()
            entry.checked_sources(digest,payload,app)
            extra=app/'unknown-extra';extra.write_bytes(b'NEVER READ')
            original=Path.read_bytes
            def known_only(path):
                if path==extra:raise AssertionError('unknown extra content must never be read/hashed')
                return original(path)
            with patch.object(Path,'read_bytes',known_only):
                with self.assertRaisesRegex(ValueError,'full84 equality'):entry.checked_sources(digest,payload,app)
            extra.unlink();(app/'known-00.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'source hash'):entry.checked_sources(digest,payload,app)
            (payload/'support_s2.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'carrier byte'):entry.checked_sources(digest,payload,app)

    def test_windows_short_argv_ro_mount_and_strict_mount_identity(self):
        limits=['--user','10002:10002','--network','none','--read-only']
        carrier=ROOT/'artifacts/fixed-carrier'
        argv=operator.proposed_argv('sha256:'+'a'*64,carrier,'b'*64,limits)
        self.assertNotIn('-c',argv);self.assertIn('/qualification/entry.py',argv)
        self.assertLess(len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2+1,30000)
        mount=dict(Type='bind',Source=str(carrier),Destination='/qualification',RW=False,Mode='ro',Propagation='rprivate')
        operator.checked_mount([mount],carrier)
        for field,value in [('RW',True),('Source',str(ROOT/'other')),('Destination','/app'),('Mode','rw')]:
            with self.assertRaises(ValueError):operator.checked_mount([dict(mount,**{field:value})],carrier)
        with self.assertRaises(ValueError):operator.checked_mount([],carrier)

    def test_missing_sealed_inputs_hardfails_before_any_git_native_or_packet(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as folder:
            source=Path(folder);packet=source/'artifacts/packet'
            with patch.object(operator.subprocess,'check_output',side_effect=AssertionError('native forbidden')):
                with self.assertRaisesRegex(ValueError,'sealed'):operator.freeze(packet,source)
            self.assertFalse(packet.exists())

    def test_internal_child_timeout_is_killed_reaped_and_never_relaunched(self):
        class Fake:
            pid=123
            def __init__(self):self.killed=False
            def wait(self,timeout):
                if not self.killed:raise subprocess.TimeoutExpired('FIXED_DOUBLE',timeout)
                return -9
            def poll(self):return -9 if self.killed else None
            def kill(self):self.killed=True
        process=Fake()
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as folder:
            with patch.object(entry.subprocess,'Popen',return_value=process) as create:
                with self.assertRaisesRegex(RuntimeError,'failed/late/overflow'):entry.run_child(1000,10.,'a'*64,Path(folder))
            create.assert_called_once();self.assertTrue(process.killed)

    def test_bad_mount_or_resource_cleans_only_owned_cid_before_start(self):
        primitive=module('s2_napi_config_only','tooling/foundation/n_api02.py')
        dependency=json.loads((ROOT/'docs/implementation/poc-n-api02-bindings-20261023.json').read_bytes())
        class StopUnconfirmed(RuntimeError):pass
        for defect in ('mount','resource'):
            with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as directory:
                folder=Path(directory);(folder/'payload').mkdir();(folder/'results').mkdir()
                (folder/'payload/dependency.json').write_text(json.dumps(dependency),encoding='utf-8')
                cid='a'*64;image=dependency['learner_image'];argv=operator.proposed_argv(image,folder/'payload','b'*64,primitive.LIMITS)
                typed=dict(Id=cid,Image=image,User='10002:10002',Path='python',Args=argv[argv.index(image)+2:],
                    State=dict(Status='created',Pid=0),RestartCount=0,Memory=2147483648,MemorySwap=2147483648,
                    NanoCpus=2000000000,PidsLimit=64,ReadonlyRootfs=True,Privileged=False,CapAdd=None,
                    CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],NetworkMode='none',
                    Mounts=[dict(Type='bind',Source=str(folder/'payload'),Destination='/qualification',RW=False,Mode='ro',Propagation='rprivate')],
                    PortBindings={},PublishAllPorts=False,RestartPolicy=dict(Name='no',MaximumRetryCount=0),
                    AutoRemove=False,Tmpfs={'/tmp':'rw,exec,nosuid,nodev,size=512m'})
                if defect=='mount':typed['Mounts'][0]['RW']=True
                else:typed['Memory']=1
                stopped=[];calls=[]
                life=SimpleNamespace(require_cid=lambda raw:cid,StopUnconfirmed=StopUnconfirmed,
                    checked_state=lambda value,cid:value,stop_owned=lambda cid:stopped.append(cid),
                    supervise=lambda *args:(_ for _ in ()).throw(AssertionError('start forbidden')))
                def call(argv,label,deadline):
                    calls.append(label)
                    return {'image':json.dumps(dependency['qualified_image_config']),'absence':'','create':cid,'prestart':json.dumps(typed)}[label]
                with self.assertRaises(ValueError):operator.controller(dict(manifest_sha256='b'*64),folder,primitive,life,call,1000.)
                self.assertEqual(calls,['image','absence','create','prestart']);self.assertEqual(stopped,[cid])

    def test_source_parent_and_host_have_no_science_or_dormant_imports(self):
        forbidden={'numpy','scipy','arviz_stats','xarray','pymc','pytensor','probe_roles','run_support_once'}
        for name in ('tooling/foundation/s2_numerics.py','tooling/foundation/s2_numerics_entry.py'):
            tree=ast.parse((ROOT/name).read_text(encoding='utf-8'))
            imports={n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module}
            imports|={alias.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for alias in n.names}
            self.assertFalse(imports&forbidden)
        source=(ROOT/'tooling/foundation/s2_numerics_entry.py').read_text(encoding='utf-8')
        self.assertIn("for draws in (1000,2000)",source)
        self.assertNotIn('ThreadPool',source);self.assertNotIn('multiprocessing',source)


if __name__=='__main__':unittest.main()
