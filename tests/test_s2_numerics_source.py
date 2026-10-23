"""Source/stdlib controls only. No numerical prediction or science import."""
import ast
import base64
import copy
import hashlib
import importlib.util
import json
import math
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
            def __init__(self,shape,dtype='float64',bad=False,value=0.):self.shape=shape;self.dtype=dtype;self.bad=bad;self.value=value
            def __abs__(self):return Array(self.shape,self.dtype,self.bad,abs(self.value))
            def __gt__(self,other):return self.bad or self.value>other
            def __ge__(self,other):return self.bad
            def __lt__(self,other):return self.bad
        fake=SimpleNamespace(ndarray=Array,dtype=lambda x:x,isfinite=lambda x:math.isfinite(x.value),abs=abs,
                             all=lambda x:x,any=lambda x:x)
        tree=ast.parse((ROOT/'methods/support/s2_prediction.py').read_text(encoding='utf-8'))
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='checked_arrays')
        namespace=dict(np=fake,FIELDS={'alpha','tau','e_T','b','rho','s_e','s_Q'})
        exec(compile(ast.Module(body=[function],type_ignores=[]),'isolated_shape_guard_AST','exec'),namespace)
        ids=[f'UNIT-{i:02}' for i in range(12)];context=S2Request.model_validate(wire())
        arrays={key:Array((4,1000,12) if key in ('alpha','tau','e_T') else (4,1000,4) if key=='b' else (4,1000)) for key in namespace['FIELDS']}
        self.assertEqual(namespace['checked_arrays'](arrays,ids,context),7)
        for rho in (-.95,.95,-.95+1e-12,.95-1e-12):
            self.assertEqual(namespace['checked_arrays'](dict(arrays,rho=Array((4,1000),value=rho)),ids,context),7)
        for rho in (-.95-1e-12,.95+1e-12,float('nan'),float('inf'),-float('inf')):
            with self.assertRaises(ValueError):namespace['checked_arrays'](dict(arrays,rho=Array((4,1000),value=rho)),ids,context)
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

    def test_fixed_and_exposed_regression_counts_with_supplemental_still_sealed(self):
        value=json.loads((ROOT/'tooling/foundation/s2_numerics_inputs/fixed.json').read_bytes())
        self.assertEqual((len(value['scalar']),len(value['cdf'])),(64,16))
        self.assertEqual(len({v['id'] for v in value['scalar']}),64)
        raw=(ROOT/'tooling/foundation/s2_numerics_inputs/held-out.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'e943cc2985f23f2a7732745bfdb93ccc0fa6c910af2a54d281b9c050f3578747')
        exposed=json.loads(raw)
        self.assertEqual((len(exposed['scalar_cases']),len(exposed['cdf_cases'])),(32,16))
        self.assertFalse((ROOT/'tooling/foundation/s2_numerics_inputs/supplemental-blind.json').exists())

    def test_action_guard_endpoints_horizons_and_derived_finite_guard_without_arithmetic(self):
        tree=ast.parse((ROOT/'methods/support/s2_prediction.py').read_text(encoding='utf-8'))
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='action_moments')
        guards=[n for n in function.body if isinstance(n,ast.If)]
        # Execute ONLY the original support predicate. The arithmetic body is
        # replaced with a sentinel, never run or imported on this host.
        reduced=copy.deepcopy(function);reduced.body=[copy.deepcopy(guards[0]),
            ast.Raise(exc=ast.Call(func=ast.Name(id='RuntimeError',ctx=ast.Load()),args=[ast.Constant(value='ARITHMETIC_NOT_EXECUTED')],keywords=[]),cause=None)]
        reduced=ast.fix_missing_locations(reduced)
        namespace=dict(np=SimpleNamespace(any=bool,abs=abs))
        exec(compile(ast.Module(body=[reduced],type_ignores=[]),'support_predicate_only','exec'),namespace)
        for h in (1,14):
            for rho in (-.95,.95,-.95+1e-12,.95-1e-12):
                with self.assertRaisesRegex(RuntimeError,'ARITHMETIC_NOT_EXECUTED'):
                    namespace['action_moments'](None,None,None,rho,None,0.,0.,None,h)
        for h,rho in ((0,0.),(15,0.),(1.,0.),(True,0.),(1,-.95-1e-12),(14,.95+1e-12)):
            with self.assertRaises(ValueError):namespace['action_moments'](None,None,None,rho,None,0.,0.,None,h)
        finite=compile(ast.Expression(guards[1].test),'derived_finite_guard_only','eval')
        for base,sd,positive,expected in ((1.,1.,True,False),(float('nan'),1.,True,True),
                (float('inf'),1.,True,True),(1.,float('nan'),True,True),(1.,0.,True,True)):
            fake=SimpleNamespace(all=bool,any=bool,isfinite=math.isfinite)
            self.assertEqual(eval(finite,dict(np=fake,base=base,sd=sd,positive=positive)),expected)

    def test_qualification_admission_and_rejection_fixture_match_inclusive_domain(self):
        tree=ast.parse((ROOT/'tooling/foundation/s2_numerics_unit.py').read_text(encoding='utf-8'))
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='scalar_cases')
        assignment=next(n for n in ast.walk(function) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='scalar_support' for t in n.targets))
        predicate=compile(ast.Expression(assignment.value),'scalar_support_predicate_only','eval')
        for h in (1,14):
            for rho in (-.95,.95,-.95+1e-12,.95-1e-12,-.95-1e-12,.95+1e-12,float('nan'),float('inf')):
                case=dict(b=[0.]*4,x=[0.]*4,rho=rho,h=h,s_e=0.,s_Q=1.,r0=.1,r1=.2)
                expected=math.isfinite(rho) and -.95<=rho<=.95
                self.assertEqual(eval(predicate,dict(case=case,values=[rho],math=math)),expected)
        controls=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='boundary_controls')
        self.assertTrue(any(isinstance(n,ast.Constant) and n.value==.9500001 for n in ast.walk(controls)))

    def test_inclusive_numerical_metadata_updates_derived_content_refs_not_latent_prior(self):
        from contracts.domain.analysis import reference
        from contracts.domain.support_s2 import CONFIG,NUMERICS,PRIOR
        self.assertEqual(NUMERICS['rho'],[-.95,.95]);self.assertEqual(NUMERICS['h'],[1,14])
        self.assertEqual(PRIOR['rho'],'Uniform(-.95,.95)')
        self.assertEqual(DEFINITIONS['numerics'],reference(NUMERICS['id'],NUMERICS))
        self.assertEqual(CONFIG_REF,reference(CONFIG['id'],CONFIG))

    def test_supplemental_loader_is_fixed_16_8_beside_unchanged_regression_counts(self):
        self.assertIn('supplemental-blind.json',entry.PAYLOAD_FILES)
        self.assertEqual(operator.CARRIER['supplemental-blind.json'],
                         'tooling/foundation/s2_numerics_inputs/supplemental-blind.json')
        tree=ast.parse((ROOT/'tooling/foundation/s2_numerics_unit.py').read_text(encoding='utf-8'))
        guard=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and any(
            isinstance(x,ast.Raise) and isinstance(x.exc,ast.Call) and any(
                isinstance(arg,ast.Constant) and arg.value=='frozen112/40 case counts required'
                for arg in x.exc.args) for x in n.body))
        expression=compile(ast.Expression(guard.test),'case_counts_only','eval')
        fixed=dict(scalar=[None]*64,cdf=[None]*16);held=dict(scalar_cases=[None]*32,cdf_cases=[None]*16)
        for scalar_count,cdf_count,expected in ((16,8,False),(15,8,True),(17,8,True),(16,7,True),(16,9,True)):
            supplemental=dict(scalar_cases=[None]*scalar_count,cdf_cases=[None]*cdf_count)
            self.assertEqual(eval(expression,dict(fixed=fixed,held=held,supplemental=supplemental)),expected)


class Carrier(unittest.TestCase):
    def test_captured_empty_mode_and_ro_require_same_strict_readonly_joint_guard(self):
        # Exact public Mounts[0] projection from R2 raw prestart Git blob
        # 0671e3af702c856807d4c5622e1a8f57153a3373. No live query/inspection.
        mount=dict(Destination='/qualification',Mode='',Propagation='rprivate',RW=False,
            Source=r'C:\Users\erics\Documents\Projects\REMission-worktrees\s2-numerics-sol-261023\artifacts\s2-numerics-8c32371-r2\final-packet\payload',Type='bind')
        carrier=Path(mount['Source'])
        for mode in ('','ro'):operator.checked_mount([dict(mount,Mode=mode)],carrier)
        variants=[]
        for value in (True,0,None,'false',[],{}):variants.append(dict(mount,RW=value))
        for value in (None,'rw','RO',False,0,[]):variants.append(dict(mount,Mode=value))
        for field in ('RW','Mode'):
            changed=dict(mount);changed.pop(field);variants.append(changed)
        for field,value in [('Source',mount['Source']+'-other'),('Destination','/app'),
                ('Type','volume'),('Propagation','rshared')]:variants.append(dict(mount,**{field:value}))
        for value in variants:
            with self.subTest(value=value),self.assertRaises(ValueError):operator.checked_mount([value],carrier)
        with self.assertRaises(ValueError):operator.checked_mount([mount,mount],carrier)

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
            # Exposed input alone is insufficient: the fresh blind confirmation
            # file must be independently released before any packet can exist.
            exposed=source/'tooling/foundation/s2_numerics_inputs/held-out.json'
            exposed.parent.mkdir(parents=True);exposed.write_bytes(b'UNIT missing-blind fixture')
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
        for defect in ('mount','resource','empty-mode-resource'):
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
                else:
                    typed['Memory']=1
                    if defect=='empty-mode-resource':typed['Mounts'][0]['Mode']=''
                stopped=[];calls=[]
                life=SimpleNamespace(require_cid=lambda raw:cid,StopUnconfirmed=StopUnconfirmed,
                    checked_state=lambda value,cid:value,stop_owned=lambda cid:stopped.append(cid),
                    supervise=lambda *args:(_ for _ in ()).throw(AssertionError('start forbidden')))
                def call(argv,label,deadline):
                    calls.append(label)
                    return {'image':json.dumps(dependency['qualified_image_config']),'absence':'','create':cid,'prestart':json.dumps(typed)}[label]
                with self.assertRaisesRegex(ValueError,'mount' if defect=='mount' else 'typed-created'):
                    operator.controller(dict(manifest_sha256='b'*64),folder,primitive,life,call,1000.)
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
