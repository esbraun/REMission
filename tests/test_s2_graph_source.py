"""Stdlib/AST/temp-FS/process doubles only. No scientific module execution."""
import ast
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tooling.foundation import s2_graph as host
from tooling.foundation import s2_graph_entry as entry

ROOT=Path(__file__).resolve().parents[1]


def without_policy_exception(function):
    """Remove ONLY declared R3 policy preconditions/report metadata for inverse proof."""
    class Inverse(ast.NodeTransformer):
        def visit_Import(self,node):
            if len(node.names)==1 and node.names[0].name in ('pytensor','pymc'):return None
            return node
        def visit_Expr(self,node):
            call=node.value
            if isinstance(call,ast.Call):
                if isinstance(call.func,ast.Name) and call.func.id in ('require_construction_policy','require_actual_policy'):return None
                if isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name) and call.func.value.id=='construction_policy' and call.func.attr=='update':return None
            return self.generic_visit(node)
        def visit_Assign(self,node):
            target=node.targets[0]
            if isinstance(target,ast.Name) and target.id in ('construction_policy','half_normal_inputs'):return None
            if isinstance(target,ast.Name) and target.id=='STAGE' and isinstance(node.value,ast.Constant) and node.value.value=='construction_policy':return None
            if isinstance(target,ast.Subscript) and isinstance(target.slice,ast.Constant) and target.slice.value=='half_normal_inputs':return None
            if isinstance(target,ast.Name) and target.id=='report':
                node.value.keywords=[k for k in node.value.keywords if k.arg!='construction_policy']
            return self.generic_visit(node)
        def visit_If(self,node):
            if 'pymc.__version__' in ast.unparse(node.test):return None
            return self.generic_visit(node)
    return Inverse().visit(copy.deepcopy(function))


class CarrierTests(unittest.TestCase):
    def fixture(self,base):
        root=base/'carrier';app=base/'app';root.mkdir();app.mkdir()
        expected={}
        for index in range(84):
            raw=('public-'+str(index)).encode();name='file-'+str(index)
            (app/name).write_bytes(raw);expected['/app/'+name]=hashlib.sha256(raw).hexdigest()
        for name in entry.PAYLOAD_FILES:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(json.dumps(dict(qualified_project_source=expected)).encode() if name=='dependency.json' else b'public')
        files={name:dict(bytes=(root/name).stat().st_size,sha256=hashlib.sha256((root/name).read_bytes()).hexdigest()) for name in entry.PAYLOAD_FILES}
        raw=json.dumps(dict(kind='S2-fixed-graph-carrier-v1',files=files)).encode()
        (root/'manifest.json').write_bytes(raw)
        return root,app,hashlib.sha256(raw).hexdigest()

    def test_complete_public_inventory_exactpass_and_missing_changed_extra_fail(self):
        for mode in ('pass','missing','changed','extra','carrier_extra','digest'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temporary:
                root,app,digest=self.fixture(Path(temporary))
                if mode=='missing':(app/'file-0').unlink()
                if mode=='changed':(app/'file-0').write_bytes(b'changed')
                if mode=='extra':(app/'unknown').write_bytes(b'NEVER READ UNKNOWN')
                if mode=='carrier_extra':(root/'unknown').write_bytes(b'NEVER READ UNKNOWN')
                if mode=='digest':digest='0'*64
                original=Path.read_bytes
                def guarded(path):
                    if path.name=='unknown':raise AssertionError('unknown content read')
                    return original(path)
                with patch.object(Path,'read_bytes',guarded):
                    if mode=='pass':entry.checked_sources(digest,root,app)
                    else:
                        with self.assertRaises(ValueError):entry.checked_sources(digest,root,app)

    def test_dependency_symlink_does_not_follow_unknown(self):
        with tempfile.TemporaryDirectory() as temporary:
            root,app,digest=self.fixture(Path(temporary))
            try:(app/'link').symlink_to(app/'file-0')
            except OSError:self.skipTest('Windows real-symlink privilege unavailable')
            with self.assertRaisesRegex(ValueError,'symlink'):entry.checked_sources(digest,root,app)

    def test_actual_package_paths_cover_transitive_imports_and_no_installed_overwrite(self):
        self.assertEqual(set(entry.MODULES.values()),set(host.CARRIER)-{'entry.py','tooling/foundation/pa3-cvm-policy.json'})
        self.assertIn('contracts/domain/support_s2.py',entry.PAYLOAD_FILES)
        self.assertIn('tooling/foundation/pa3_monitor.py',entry.PAYLOAD_FILES)
        tree=ast.parse((ROOT/'tooling/foundation/s2_graph_entry.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='package_setup')
        source=ast.unparse(function)
        self.assertIn('spec.origin != str(staged / path)',source)
        self.assertIn('name in sys.modules',source)
        self.assertIn('foreign package path',source)
        self.assertNotIn('spec_from_file_location',source)

    def test_actual_package_setup_checks_origins_search_paths_and_every_new_module(self):
        for mode in ('pass','foreign_package','wrong_module_origin','preloaded_new_module'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary)/'carrier';root.mkdir();staged=Path(temporary)/'staged'
                for name in (*entry.MODULES.values(),'tooling/foundation/pa3-cvm-policy.json'):
                    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'public source bytes only')
                seen=[]
                def package(name):
                    seen.append(name);suffix=name.replace('.','/')
                    paths=['/foreign'] if mode=='foreign_package' else ['/app/'+suffix]
                    return SimpleNamespace(__spec__=SimpleNamespace(origin='/app/'+suffix+'/__init__.py'),__path__=paths)
                def spec(name):return SimpleNamespace(origin='/wrong.py' if mode=='wrong_module_origin' else str(staged/entry.MODULES[name]))
                modules={'methods.support.s2_model':object()} if mode=='preloaded_new_module' else {}
                with patch.object(entry,'sys',SimpleNamespace(path=[],modules=modules)),patch.object(entry.importlib,'import_module',side_effect=package),patch.object(entry.importlib.util,'find_spec',side_effect=spec):
                    if mode=='pass':
                        entry.package_setup(root,staged)
                        self.assertEqual(len(seen),6);self.assertEqual((staged/'methods/support/s2_model.py').read_bytes(),b'public source bytes only')
                    else:
                        with self.assertRaises(ValueError):entry.package_setup(root,staged)


class PrivacyTests(unittest.TestCase):
    def test_fixed_error_projection_omits_secret_messages_and_unknown_absolute_locations(self):
        try:raise ValueError('SECRET-PATIENT-ACCESS-TOKEN')
        except ValueError as error:row=entry.failure(error,'density')
        raw=json.dumps(row)
        self.assertNotIn('SECRET',raw);self.assertNotIn(str(ROOT),raw)
        self.assertEqual(row['error_class'],'ValueError');self.assertTrue(row['omitted'])
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'stderr';path.write_text(raw)
            self.assertEqual(entry.read_failure(path)['status'],'available')

    def test_strict_failure_parser_rejects_unknown_duplicate_nonfinite_oversized_and_missing(self):
        valid=dict(kind='s2-graph-child-failure-v1',stage='compile',error_class='ValueError',locations=[],omitted=True)
        bad=[b'',b'{}',b'{"kind":1,"kind":2}',b'{"value":NaN}',b'x'*65537,
             json.dumps(dict(valid,secret='NO')).encode(),
             json.dumps(dict(valid,locations=[dict(file='/secret/private.py',line=1)])).encode(),
             json.dumps(dict(valid,error_class='ArbitrarySecretClass')).encode()]
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'stderr'
            for raw in bad:
                with self.subTest(raw_length=len(raw)):
                    path.write_bytes(raw);self.assertEqual(entry.read_failure(path)['status'],'unavailable')
            self.assertEqual(entry.read_failure(Path(temporary)/'absent')['code'],'read_failed')

    def test_failure_sink_error_does_not_raise_and_budget_is_bounded(self):
        with patch.object(entry.sys,'stderr',SimpleNamespace(write=lambda _:(_ for _ in ()).throw(OSError()))):
            self.assertFalse(entry.emit(dict(kind='failed')))
        with contextlib.redirect_stderr(io.StringIO()) as out:
            self.assertTrue(entry.emit(dict(kind='failed')))
            self.assertFalse(entry.emit(dict(kind='x'*4096)))
        self.assertLessEqual(len(out.getvalue().encode()),4096)

    def run_double(self,base,returncode=0,timeout=False,unreaped=False):
        result=dict(kind='S2-ORIGINAL-COORDINATE-DENSITY-GRADIENT-STRUCTURAL-ONLY')
        row=dict(kind='s2-graph-child-failure-v1',stage='compile',error_class='ValueError',locations=[],omitted=True)
        events=[]
        class Process:
            pid=77
            def __init__(self,argv,**kwargs):
                events.append('spawn');kwargs['stdout'].write(json.dumps(result).encode());kwargs['stdout'].flush()
                kwargs['stderr'].write(json.dumps(row).encode());kwargs['stderr'].flush();self.waits=0
            def wait(self,timeout):
                events.append('wait');self.waits+=1
                if unreaped or (self.waits==1 and timeout_flag):raise subprocess.TimeoutExpired('fixed',1)
                return returncode
            def poll(self):return None if timeout_flag or unreaped else returncode
            def kill(self):events.append('kill')
        timeout_flag=timeout
        original=Path.read_bytes
        def guarded(path):
            if path.name=='graph.stdout' and (returncode!=0 or timeout or unreaped):
                raise AssertionError('failed stdout content read')
            events.append('read-'+path.name);return original(path)
        with patch.object(entry.subprocess,'Popen',Process),patch.object(Path,'read_bytes',guarded),contextlib.redirect_stderr(io.StringIO()) as captured:
            try:value=entry.run_child(20.,'a'*64,base)
            except entry.ChildFailed as error:value=error.reason
        return value,events,captured.getvalue()

    def test_success_one_child_and_fixed_short_argv(self):
        with tempfile.TemporaryDirectory() as temporary:
            value,events,_=self.run_double(Path(temporary))
        self.assertEqual(events.count('spawn'),1);self.assertTrue(value['custody']['reaped'])
        self.assertEqual(value['argv'][1:5],['-I','-B','/qualification/entry.py','--child'])

    def test_nonzero_timeout_and_unreaped_preserve_precedence_reap_before_projection(self):
        for kwargs,reason in ((dict(returncode=1),'nonzero'),(dict(timeout=True,returncode=-9),'timeout'),(dict(unreaped=True),'unreaped')):
            with self.subTest(reason=reason),tempfile.TemporaryDirectory() as temporary:
                value,events,raw=self.run_double(Path(temporary),**kwargs)
                self.assertEqual(value,reason);self.assertEqual(events.count('spawn'),1)
                self.assertNotIn('read-graph.stdout',events)
                if reason!='nonzero':self.assertIn('kill',events)
                self.assertIn(reason,raw)
                if reason=='unreaped':self.assertIn('"code":"unreaped"',raw)

    def test_parent_one_child_subtracts_elapsed_and_reserve_not_a_fresh_1080(self):
        observed=[]
        with patch.object(entry,'checked_sources'),patch.object(entry.Path,'mkdir'),patch.object(entry.time,'monotonic',side_effect=[10000.,10020.,10025.]),patch.object(entry,'run_child',side_effect=lambda budget,*_:observed.append(budget) or {}),contextlib.redirect_stdout(io.StringIO()):
            entry.parent('a'*64,1000.)
        self.assertEqual(observed,[950.])


class HostTests(unittest.TestCase):
    def test_complete_report_scope_and_corrupt_transport_rejected(self):
        rows=[]
        cases=[('observed',n,rho) for n in (1,2) for rho in (-.949999,-.4,0.,.4,.949999)]
        cases.append(('prior_only_empty_rows',1,0.))
        for fixture,members,rho in cases:
            names=['mu_alpha','mu_tau','b','s_alpha','s_tau','s_e','s_Q','rho','z','u']+['epsilon_'+str(i) for i in range(members)]
            rows.append(dict(fixture=fixture,members=members,rho=rho,value_variable_order=names,
                half_normal_inputs=[dict(rv=name,location_ordinal=2,scale_ordinal=3,location_dtype='float64',scale_dtype='float64',location_is_constant=True,scale_is_constant=True) for name in ('s_alpha','s_tau','s_e','s_Q')],
                compiled=[dict(label=n) for n in ['full','gradient','likelihood',*['prior:'+n for n in names]]],
                gradient_sweeps=[dict(direction=d,step=s) for d in (0,1) for s in (1e-4,3e-5,1e-5,3e-6)],
                directions=[{},{}],likelihood_actual=0.,negative_controls={}))
        result=dict(kind='S2-ORIGINAL-COORDINATE-DENSITY-GRADIENT-STRUCTURAL-ONLY',qualification_fixture_only=True,
            construction_policy=dict(host.CONSTRUCTION_POLICY),
            model_fitted=False,genuine_data=False,serving_authority=False,density=rows,
            shapes=[dict(cutoff=day,compiled=False,members=list(range(12))) for day in (14,28)])
        original=dict(kind='S2-GRAPH-STRUCTURAL-ONLY',scientific_parent_imports=False,model_fitted=False,genuine_data=False,
            serving_authority=False,run=dict(custody=dict(pid=5,returncode=0,reaped=True,timed_out=False),result=result))
        self.assertEqual(host.decode_output(json.dumps(original)),original)
        for mode in ('missing_case','missing_step','missing_compiled','not_reaped','prior_likelihood','full12_compiled','policy_conflict','missing_halfnormal','half_constant_wrongtype'):
            value=copy.deepcopy(original);run=value['run']
            if mode=='missing_case':run['result']['density'].pop()
            if mode=='missing_step':run['result']['density'][0]['gradient_sweeps'].pop()
            if mode=='missing_compiled':run['result']['density'][0]['compiled'].pop()
            if mode=='not_reaped':run['custody']['reaped']=False
            if mode=='prior_likelihood':run['result']['density'][-1]['likelihood_actual']=1.
            if mode=='full12_compiled':run['result']['shapes'][0]['compiled']=True
            if mode=='policy_conflict':run['result']['construction_policy']['cast_policy']='custom'
            if mode=='missing_halfnormal':run['result']['density'][0]['half_normal_inputs'].pop()
            if mode=='half_constant_wrongtype':run['result']['density'][0]['half_normal_inputs'][0]['location_is_constant']=1
            with self.subTest(mode=mode),self.assertRaises(ValueError):host.decode_output(json.dumps(value))
        with self.assertRaises(ValueError):host.decode_output('x'*(host.MAX_OUTPUT+1))

    def test_cross_os_transfer_is_duration_with_setup_reserve_and_absolute_deadlines(self):
        self.assertEqual(host.relative_budget(900000.,900010.),1070.)
        self.assertEqual(host.relative_budget(100.,110.),1070.)
        with self.assertRaises(TimeoutError):host.relative_budget(100.,160.)
        tree=ast.parse((ROOT/'tooling/foundation/s2_graph.py').read_text())
        source=ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='controller'))
        self.assertIn('work = start + 1140',source);self.assertIn('setup = start + 60',source)
        self.assertIn("folder / 'results/supervision', work",source)
        self.assertNotIn('time.monotonic() + 1080',source)

    def test_short_fixed_argv_only_pid_delta_and_one_ro_mount(self):
        from tooling.foundation.n_api02 import LIMITS
        argv=host.proposed_argv('sha256:'+'a'*64,Path('C:/public/carrier'),'b'*64,1070.,LIMITS)
        self.assertEqual(argv[argv.index('--pids-limit')+1],'256');self.assertEqual(LIMITS[LIMITS.index('--pids-limit')+1],'64')
        self.assertEqual(argv.count('--mount'),1);self.assertNotIn('-c',argv)
        self.assertLess(len(subprocess.list2cmdline(argv)),30000)

    def test_mount_joint_strictness_and_two_accepted_mode_forms(self):
        path=Path('C:/public/carrier')
        # Path string normalization itself is platform-specific and frozen on Windows.
        source=host.ntpath.normcase(str(path)).replace('\\','/')
        row=dict(Source=source,Type='bind',Destination='/qualification',RW=False,Mode='ro',Propagation='rprivate')
        for mode in ('','ro'):host.checked_mount([dict(row,Mode=mode)],path)
        for changed in (dict(RW=True),dict(RW=0),dict(Mode=None),dict(Source=source+'/other'),dict(Type='volume'),dict(Destination='/app'),dict(Propagation='shared')):
            with self.subTest(changed=changed),self.assertRaises(ValueError):host.checked_mount([dict(row,**changed)],path)
        with self.assertRaises(ValueError):host.checked_mount([row,row],path)

    def test_created_checks_pid_and_mount_then_unchanged_primitive(self):
        path=Path('C:/public/carrier');row=dict(Source=str(path),Type='bind',Destination='/qualification',RW=False,Mode='',Propagation='rprivate')
        calls=[];primitive=SimpleNamespace(checked_created=lambda *args:calls.append(args))
        value=dict(Mounts=[row],PidsLimit=256,SecurityOpt=['no-new-privileges'])
        host.checked_created(value,'cid','image',[],path,primitive,None)
        self.assertEqual(calls[0][0],dict(value,Mounts=[],PidsLimit=64))
        with self.assertRaises(ValueError):host.checked_created(dict(value,PidsLimit=64),'cid','image',[],path,primitive,None)
        self.assertEqual(len(calls),1)

    def test_controller_unknown_create_halts_without_guessed_cleanup_and_prestart_before_supervise(self):
        tree=ast.parse((ROOT/'tooling/foundation/s2_graph.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='controller')
        source=ast.unparse(function)
        self.assertLess(source.index('checked_created('),source.index('life.supervise('))
        self.assertIn('if cid is not None:',source)
        self.assertIn("raise life.StopUnconfirmed('graph create/CID unknown')",source)

    def test_controller_doubles_success_invalid_create_resource_and_late_prestart(self):
        from tooling.foundation import n_api02 as primitive
        class StopUnknown(RuntimeError):pass
        for mode in ('success','unknown_create','wrong_resource','late_prestart'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temporary:
                folder=Path(temporary);(folder/'payload').mkdir();(folder/'results').mkdir()
                dependency=dict(learner_image='sha256:'+'a'*64,qualified_image_config=dict(Id='image',Entrypoint=None))
                (folder/'payload/dependency.json').write_text(json.dumps(dependency))
                events=[];cid='b'*64;clock=[101.];created_argv=[]
                def require(value):
                    if value!=cid:raise ValueError()
                    return value
                def call(argv,label,end):
                    events.append(label)
                    if label=='image':return json.dumps(dependency['qualified_image_config'])
                    if label=='absence':return ''
                    if label=='create':created_argv.extend(argv);return 'unknown' if mode=='unknown_create' else cid
                    if label=='prestart':
                        if mode=='late_prestart':clock[0]=156.
                        state=dict(Status='created',Pid=0)
                        row=dict(Id=cid,Image=dependency['learner_image'],User='10002:10002',Path='python',
                            Args=created_argv[created_argv.index(dependency['learner_image'])+2:],State=state,RestartCount=0,
                            Memory=2147483648,MemorySwap=2147483648,NanoCpus=2000000000,PidsLimit=256,
                            ReadonlyRootfs=True,Privileged=False,CapAdd=None,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],
                            NetworkMode='none',Mounts=[dict(Source=str(folder/'payload'),Type='bind',Destination='/qualification',
                                RW=False,Mode='',Propagation='rprivate')],PortBindings=None,PublishAllPorts=False,
                            Tmpfs={'/tmp':'rw,exec,nosuid,nodev,size=512m'},RestartPolicy={'Name':'no','MaximumRetryCount':0},AutoRemove=False)
                        if mode=='wrong_resource':row['Memory']=123
                        return json.dumps(row)
                    if label=='unit-output':return 'result checked separately'
                    raise AssertionError(label)
                def supervise(*args):events.append('supervise');self.assertEqual(args[2],1240.);return dict(Pid=0)
                life=SimpleNamespace(StopUnconfirmed=StopUnknown,require_cid=require,
                    checked_state=lambda row,_:row,supervise=supervise,
                    stop_owned=lambda value:events.append('stop-'+value) or [],check_deadline=lambda _:None)
                with patch.object(host.time,'monotonic',side_effect=lambda:clock[0]),patch.object(host,'decode_output',return_value={'scope':'transport-double'}):
                    if mode=='success':
                        result=host.controller(dict(manifest_sha256='c'*64),folder,primitive,life,call,100.)
                        self.assertEqual(result['cid'],cid);self.assertEqual(events,['image','absence','create','prestart','supervise','unit-output'])
                    else:
                        with self.assertRaises((ValueError,TimeoutError,StopUnknown)):
                            host.controller(dict(manifest_sha256='c'*64),folder,primitive,life,call,100.)
                        self.assertNotIn('supervise',events)
                        if mode=='unknown_create':self.assertFalse(any(e.startswith('stop-') for e in events))
                        else:self.assertEqual(events[-1],'stop-'+cid)

    def test_scalar_json_rejects_overflow_numbers_at_both_transport_boundaries(self):
        for parser in (host.strict_json,entry.strict_json):
            for raw in ('{"x":1e400}','{"x":NaN}','{"x":1,"x":2}'):
                with self.assertRaises(ValueError):parser(raw)


class QualificationSourceTests(unittest.TestCase):
    def test_reference_and_point_generator_unchanged_from_original_ast_freeze(self):
        after=ast.parse((ROOT/'tooling/foundation/s2_model_qualification.py').read_text())
        # AST digests measured from original accepted878, not a local ignored file.
        expected=dict(reference='ae182d977e406b657640071ec39ccc874fc722fb4e56cb9a4674aa3e39887d47',
            point_for='3674f41247c5f98b7c3abd524463865be69b1d06001f796c6367fda783d16ed0',
            require_admitted='2be26ecb779ce08c4b7fe2ed0da50ad7d6c9ac00ce0bd25871aef38124a735c3')
        for name,digest in expected.items():
            node=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),digest)

    def test_exact_observed_points_steps_directions_and_prior_only_scope_are_explicit(self):
        source=(ROOT/'tooling/foundation/s2_model_qualification.py').read_text()
        tree=ast.parse(source);flat=ast.unparse(tree)
        self.assertIn('CORRELATIONS = (-0.949999, -0.4, 0.0, 0.4, 0.949999)',flat)
        self.assertIn('for direction_id in (0, 1):',flat);self.assertIn("for step in settings['steps']:",flat)
        self.assertIn('replace(data14.members[0], rows=())',flat)
        for text in ('rvs <= registered',"optimizer != NATIVE_OPTIMIZER",'verify_cvm(fn.f)',"actual_like != 0.0",'math.isfinite',"compiled=False"):
            self.assertIn(text,flat)
        self.assertNotIn('pm.sample',source)

    def test_source_scope_and_admission_no_science_host_import_or_new_runtime(self):
        for name in ('s2_graph.py','s2_graph_entry.py'):
            tree=ast.parse((ROOT/'tooling/foundation'/name).read_text())
            for node in tree.body:
                if isinstance(node,ast.Import):
                    self.assertFalse({'numpy','scipy','pymc','pytensor'}&{v.name for v in node.names})
        self.assertEqual(host.GATES,dict(density_atol=1e-8,normalizer_atol=1e-10,gradient_atol=1e-5,gradient_rtol=1e-5,steps=[1e-4,3e-5,1e-5,3e-6]))
        self.assertEqual(host.RESOURCES['pids'],256)
        self.assertEqual(host.RESOURCES['outer_seconds'],1200)
        self.assertEqual(host.PLAN_CRITIQUE,'990ae7aeae3633035db622138fc8ec5da3d0c7ef')


class PriorInputDiagnosticTests(unittest.TestCase):
    @staticmethod
    def namespace():
        tree=ast.parse((ROOT/'tooling/foundation/s2_model_qualification.py').read_text())
        assignments={'PRIOR_INPUT_FAILURE','PRIOR_INPUT_RVS','PRIOR_INPUT_DTYPES','PRIOR_INPUT_MAX_ORDINAL'}
        functions={'prior_input_metadata','prior_input_rejected'}
        nodes=[n for n in tree.body if (isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in assignments)
               or (isinstance(n,ast.FunctionDef) and n.name in functions)]
        result={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'finite_prior_metadata_only','exec'),result)
        return result,tree

    def test_finite_metadata_schema_and_bounded_exact_scalar_types(self):
        namespace,_=self.namespace();produce=namespace['prior_input_metadata']
        valid=produce('s_alpha',2,'float32',True,['mu_alpha','s_alpha'])
        self.assertEqual(valid,dict(status='available',rv='s_alpha',input_ordinal=2,dtype='float32',is_constant=True))
        self.assertEqual(entry.checked_prior_input(valid),valid)
        self.assertEqual(namespace['PRIOR_INPUT_RVS'],entry.PRIOR_INPUT_RVS)
        self.assertEqual(namespace['PRIOR_INPUT_DTYPES'],entry.PRIOR_INPUT_DTYPES)
        self.assertEqual(namespace['PRIOR_INPUT_MAX_ORDINAL'],entry.PRIOR_INPUT_MAX_ORDINAL)
        for args in (('SECRET',2,'float32',True),('s_alpha',True,'float32',True),('s_alpha',-1,'float32',True),
                     ('s_alpha',8,'float32',True),('s_alpha',2.,'float32',True),('s_alpha',2,'SECRET',True),
                     ('s_alpha',2,'float32',1),('s_alpha',2,'float32',None)):
            with self.subTest(args=args):
                row=produce(*args,['s_alpha']);self.assertEqual(row,dict(status='unavailable',code='refused'))
                self.assertNotIn('SECRET',json.dumps(row))

    def test_single_failure_envelope_optional_roundtrip_and_unknown_fields_refused(self):
        try:raise AssertionError('SECRET not emitted')
        except AssertionError as error:base=entry.failure(error,'graph')
        metadata=dict(status='available',rv='s_e',input_ordinal=0,dtype='float32',is_constant=False)
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'stderr'
            for item in (None,metadata,dict(status='unavailable',code='classification_failed')):
                row=entry.attach_prior_input(copy.deepcopy(base),item);raw=json.dumps(row)
                self.assertNotIn('SECRET',raw);path.write_text(raw)
                self.assertEqual(entry.read_failure(path),dict(status='available',failure=row))
                self.assertEqual(raw.count('s2-graph-child-failure-v1'),1)
            for item in (dict(metadata,secret='SECRET'),dict(metadata,rv='SECRET'),dict(metadata,dtype='SECRET'),
                         dict(metadata,input_ordinal=True),dict(metadata,is_constant='SECRET'),dict(metadata,input_ordinal=8)):
                # Producer never emits the malformed value; strict decoder also
                # rejects independently forged optional metadata.
                produced=entry.attach_prior_input(copy.deepcopy(base),item)
                self.assertEqual(produced['prior_input'],dict(status='unavailable',code='refused'))
                self.assertNotIn('SECRET',json.dumps(produced))
                path.write_text(json.dumps(dict(base,prior_input=item)))
                self.assertEqual(entry.read_failure(path)['status'],'unavailable')
            path.write_text(json.dumps(dict(base,prior_input=metadata,stage='compile')))
            self.assertEqual(entry.read_failure(path)['status'],'unavailable')

    def test_original_predicate_first_failure_and_assertion_survive_classifier_failure(self):
        for broken in (False,True):
            with self.subTest(classifier_broken=broken):
                namespace,tree=self.namespace();seen=[];continued=[]
                class Scalar:
                    def __init__(self,name,dtype):self.name=name;self.kind=dtype
                    @property
                    def dtype(self):seen.append(self.name);return self.kind
                first=SimpleNamespace(name='mu_alpha',owner=SimpleNamespace(inputs=[Scalar('f64','float64'),Scalar('first','float32'),Scalar('late','float16')]))
                second=SimpleNamespace(name='mu_tau',owner=SimpleNamespace(inputs=[Scalar('next_rv','float32')]))
                namespace.update(model=SimpleNamespace(free_RVs=[first,second]),expected_names=['mu_alpha','mu_tau'],Constant=Scalar,continued=continued)
                if broken:namespace['prior_input_metadata']=lambda *_:(_ for _ in ()).throw(ValueError('SECRET'))
                qualify=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='qualify')
                guard=next(n for n in ast.walk(qualify) if isinstance(n,ast.For) and any(isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id=='prior_input_rejected' for c in ast.walk(n)) and isinstance(n.iter,ast.Attribute) and n.iter.attr=='free_RVs')
                marker=ast.parse('continued.append(True)').body[0]
                with self.assertRaisesRegex(AssertionError,'prior parameter input not float64'):
                    exec(compile(ast.Module(body=[guard,marker],type_ignores=[]),'actual_prior_guard_only','exec'),namespace)
                self.assertNotIn('late',seen);self.assertNotIn('next_rv',seen);self.assertEqual(continued,[])
                expected=(dict(status='unavailable',code='classification_failed') if broken else dict(status='available',rv='mu_alpha',input_ordinal=1,dtype='float32',is_constant=True))
                self.assertEqual(namespace['PRIOR_INPUT_FAILURE'],expected)
                # Sticky first failure: no overwrite if another failing input
                # is passed to the helper by an inert test caller.
                namespace['prior_input_rejected'](Scalar('later','float16'),'mu_tau',0,['mu_alpha','mu_tau'],Scalar)
                self.assertEqual(namespace['PRIOR_INPUT_FAILURE'],expected)

    def test_success_and_original_predicate_errors_remain_unmodified(self):
        namespace,_=self.namespace();reject=namespace['prior_input_rejected']
        for dtype in ('float64','int64','bool'):
            self.assertFalse(reject(SimpleNamespace(dtype=dtype),'b',0,['b'],object))
        self.assertIsNone(namespace['PRIOR_INPUT_FAILURE'])
        with self.assertRaises(AttributeError):reject(SimpleNamespace(dtype=None),'b',0,['b'],object)
        self.assertIsNone(namespace['PRIOR_INPUT_FAILURE'])

    def test_inverse_ast_restores_entire_R1_qualification_math_and_control_flow(self):
        _,tree=self.namespace();qualify=without_policy_exception(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='qualify'))
        for node in qualify.body:
            if isinstance(node,ast.Global):node.names.remove('PRIOR_INPUT_FAILURE')
        qualify.body=[n for n in qualify.body if not (isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='PRIOR_INPUT_FAILURE')]
        count=0
        for node in ast.walk(qualify):
            if isinstance(node,ast.GeneratorExp) and isinstance(node.elt,ast.Call) and isinstance(node.elt.func,ast.Name) and node.elt.func.id=='prior_input_rejected':
                count+=1;node.elt=ast.parse("getattr(v,'dtype','').startswith('float') and v.dtype!='float64'",mode='eval').body
                node.generators[0].target=ast.Name(id='v',ctx=ast.Store())
                node.generators[0].iter=ast.parse('rv.owner.inputs',mode='eval').body
        self.assertEqual(count,1)
        digest=hashlib.sha256(ast.dump(qualify,include_attributes=False).encode()).hexdigest()
        self.assertEqual(digest,'796179aaf6331ad50f881ba81e36626af34d7dfeffb4a3b12efb888652b5e4b9')


class ConstructionPolicyTests(unittest.TestCase):
    @staticmethod
    def namespace():
        tree=ast.parse((ROOT/'tooling/foundation/s2_model_qualification.py').read_text())
        names={'CONSTRUCTION_FLAGS','CONSTRUCTION_POLICY'};functions={'require_construction_policy','require_actual_policy','half_normal_metadata'}
        nodes=[n for n in tree.body if (isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in names)
               or (isinstance(n,ast.FunctionDef) and n.name in functions)]
        result={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual_policy_scalar_helpers','exec'),result)
        return result,tree

    def test_exact_flags_before_imports_no_duplicate_extra_or_inherited_override(self):
        namespace,tree=self.namespace()
        self.assertEqual(namespace['CONSTRUCTION_FLAGS'],entry.CONSTRUCTION_FLAGS)
        self.assertEqual(namespace['CONSTRUCTION_POLICY'],entry.CONSTRUCTION_POLICY)
        self.assertEqual(namespace['CONSTRUCTION_POLICY'],host.CONSTRUCTION_POLICY)
        self.assertEqual(host.CONSTRUCTION_FLAGS,'base_compiledir=/tmp/pytensor,floatX=float64,cast_policy=numpy+floatX')
        valid=dict(PYTENSOR_FLAGS=host.CONSTRUCTION_FLAGS)
        namespace['require_construction_policy'](valid);entry.require_construction_policy(valid,host.CONSTRUCTION_POLICY)
        for value in (None,'',host.CONSTRUCTION_FLAGS+',floatX=float32',host.CONSTRUCTION_FLAGS+',cast_policy=custom',
                      host.CONSTRUCTION_FLAGS+',optimizer=None',host.CONSTRUCTION_FLAGS.replace('numpy+floatX','custom'),
                      host.CONSTRUCTION_FLAGS.replace('float64','float32')):
            for guard in (namespace['require_construction_policy'],lambda env:entry.require_construction_policy(env,host.CONSTRUCTION_POLICY)):
                with self.subTest(flags=value),self.assertRaises(ValueError):guard(dict(PYTENSOR_FLAGS=value))
        with self.assertRaises(ValueError):entry.require_construction_policy(dict(valid,PYTENSORRC='/SECRET'),host.CONSTRUCTION_POLICY)
        with self.assertRaises(ValueError):entry.require_construction_policy(valid,dict(host.CONSTRUCTION_POLICY,pymc_version='wrong'))
        qualify=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='qualify')
        source=ast.unparse(qualify)
        self.assertLess(source.index('require_construction_policy(os.environ)'),source.index('import pytensor'))
        self.assertLess(source.index('require_actual_policy(pytensor.config)'),source.index('import pymc'))
        self.assertLess(source.index('require_actual_policy(pytensor.config)'),source.index('from methods.support.s2_model'))
        child=ast.unparse(next(n for n in ast.parse((ROOT/'tooling/foundation/s2_graph_entry.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='child'))
        self.assertLess(child.index('require_construction_policy('),child.index('package_setup()'))
        self.assertLess(child.index('qualification.require_actual_policy('),child.index('compilation_options(policy)'))

    def test_actual_policy_scalar_checks_and_finite_report_no_guessed_version(self):
        namespace,tree=self.namespace();check=namespace['require_actual_policy']
        self.assertEqual(check(SimpleNamespace(floatX='float64',cast_policy='numpy+floatX')),dict(floatX='float64',cast_policy='numpy+floatX'))
        for config in (SimpleNamespace(floatX='float32',cast_policy='numpy+floatX'),SimpleNamespace(floatX='float64',cast_policy='custom')):
            with self.assertRaises(ValueError):check(config)
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='qualify')
        guard=next(n for n in function.body if isinstance(n,ast.If) and 'pymc.__version__' in ast.unparse(n.test))
        for pm,pt in (('6.3.2','3.3.4'),('WRONG','3.3.4'),('6.3.2','WRONG')):
            values=dict(pymc=SimpleNamespace(__version__=pm),pytensor=SimpleNamespace(__version__=pt))
            if pm=='6.3.2' and pt=='3.3.4':exec(compile(ast.Module(body=[guard],type_ignores=[]),'actual_version_guard_only','exec'),values)
            else:
                with self.assertRaises(ValueError):exec(compile(ast.Module(body=[guard],type_ignores=[]),'actual_version_guard_only','exec'),values)

    def test_all_four_halfnormal_location_scale_metadata_without_values(self):
        namespace,_=self.namespace()
        class ConstantMetadata:
            dtype='float64'
            @property
            def data(self):raise AssertionError('no value read')
        model=SimpleNamespace(named_vars={name:SimpleNamespace(owner=SimpleNamespace(inputs=[object(),object(),ConstantMetadata(),ConstantMetadata()])) for name in ('s_alpha','s_tau','s_e','s_Q')})
        rows=namespace['half_normal_metadata'](model,ConstantMetadata)
        self.assertEqual([r['rv'] for r in rows],['s_alpha','s_tau','s_e','s_Q'])
        self.assertTrue(all(r['location_dtype']==r['scale_dtype']=='float64' for r in rows))
        self.assertTrue(all(set(r)=={'rv','location_ordinal','scale_ordinal','location_dtype','scale_dtype','location_is_constant','scale_is_constant'} for r in rows))
        for change in ('float32','nonconstant'):
            before=model.named_vars['s_alpha'].owner.inputs[2]
            model.named_vars['s_alpha'].owner.inputs[2]=SimpleNamespace(dtype='float32' if change=='float32' else 'float64')
            with self.assertRaises(AssertionError):namespace['half_normal_metadata'](model,ConstantMetadata)
            model.named_vars['s_alpha'].owner.inputs[2]=before

    def test_both_original_strict_dtype_guards_still_reject(self):
        namespace,tree=PriorInputDiagnosticTests.namespace()
        class ConstantMetadata:pass
        for constant in (True,False):
            value=ConstantMetadata() if constant else SimpleNamespace()
            value.dtype='float32';namespace['PRIOR_INPUT_FAILURE']=None
            self.assertTrue(namespace['prior_input_rejected'](value,'s_alpha',2,['s_alpha'],ConstantMetadata))
            self.assertEqual(namespace['PRIOR_INPUT_FAILURE']['is_constant'],constant)
        qualify=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='qualify')
        loop=next(n for n in ast.walk(qualify) if isinstance(n,ast.For) and isinstance(n.iter,ast.Call) and isinstance(n.iter.func,ast.Name) and n.iter.func.id=='graph_inputs')
        value=ConstantMetadata();value.dtype='float32'
        with self.assertRaisesRegex(AssertionError,'float32 graph constant'):
            exec(compile(ast.Module(body=loop.body,type_ignores=[]),'actual_graph_constant_scalar_guard','exec'),dict(value=value,Constant=ConstantMetadata))

    def test_policy_only_inverse_to_R2_and_unchanged_failure_reaping(self):
        _,tree=self.namespace();qualify=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='qualify')
        inverse=without_policy_exception(qualify)
        self.assertEqual(hashlib.sha256(ast.dump(inverse,include_attributes=False).encode()).hexdigest(),'d3cc84ad168c1c9d063b1014109b35a036a852d20928d1a9c7d1ef7062547a53')
        expected=dict(parent='2fb800e77e4a9276091fd335b0eeb12bbafc3a414aa1a4d668a1e487df417e73',
            run_child='09804bd7a7d137d3c017fb1658ba7f71d54fa1cfff4750a1c0e84e44cbc58f0e',
            read_failure='923f40a9f715c51a4beb97cfee7713c6a90422546dddad6680e5ca33bad1e776',
            failure='cb54c978eadbe6456b9bc8b99e083fd7a40fe8056ee327efd5d9661bc73eb502')
        entry_tree=ast.parse((ROOT/'tooling/foundation/s2_graph_entry.py').read_text())
        for name,digest in expected.items():
            node=next(n for n in entry_tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),digest)
        from tooling.foundation.n_api02 import LIMITS
        argv=host.proposed_argv('image',Path('C:/public/carrier'),'f'*64,1000.,LIMITS)
        flags=[argv[i+1] for i,v in enumerate(argv[:-1]) if v=='--env' and argv[i+1].startswith('PYTENSOR_FLAGS=')]
        self.assertEqual(flags,['PYTENSOR_FLAGS='+host.CONSTRUCTION_FLAGS])
