"""Host-only custody/lifecycle counterexamples; never invokes Docker or science."""
import ast
import copy
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tooling/foundation/nof1_image01.py'


def module(path):
    spec=importlib.util.spec_from_file_location('image01_test_operator',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


class Image01Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=module(SOURCE)
        cls.artifacts=ROOT/'artifacts/nof1-image01-source-tests'
        cls.artifacts.mkdir(parents=True,exist_ok=True)
        cls.prepared=tempfile.TemporaryDirectory(dir=cls.artifacts)
        cls.template=Path(cls.prepared.name)/'frozen'
        cls.source.freeze(cls.template,ROOT)

    @classmethod
    def tearDownClass(cls):cls.prepared.cleanup()

    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(dir=self.artifacts)
        self.addCleanup(self.temporary.cleanup)
        self.folder=Path(self.temporary.name)/'frozen'
        shutil.copytree(self.template,self.folder)
        self.op=module(self.folder/'operator/nof1_image01.py')
        self.planpath=self.folder/'plan.json'
        self.plan=json.loads(self.planpath.read_bytes())
        self.plan['root']=str(self.folder)
        self.authorize()
        self.life=self.op.load_lifecycle(self.folder)

    def authorize(self):
        self.planpath.write_text(json.dumps(self.plan,sort_keys=True),encoding='utf-8')
        self.digest=self.op.sha(self.planpath.read_bytes())

    def test_freeze_binds_full_closure_git_bytes_generated_bytes_and_copied_probes(self):
        _,plan=self.op.validate_plan(self.planpath,self.digest)
        self.assertEqual(plan['bindings_git_blob'],self.op.BINDINGS_BLOB)
        self.assertEqual(self.op.sha(self.op.git(ROOT,'show',self.op.BINDINGS_BLOB)),self.op.BINDINGS_SHA)
        self.assertEqual(plan['future_images'],{'service':'UNKNOWN','learner':'UNKNOWN','controls':'UNKNOWN'})
        self.assertEqual(plan['future_CIDs'],{'service':'UNKNOWN','learner':'UNKNOWN','controls':'UNKNOWN'})
        for role,count in [('service',179),('learner',74),('controls',192)]:
            expected=json.loads((self.folder/'qualify'/f'{role}.json').read_bytes())
            self.assertEqual(len(expected['project_source']),count)
            self.assertEqual((self.folder/'qualify'/f'{role}.json').read_bytes(),
                (self.folder/'context/qualify'/f'{role}.json').read_bytes())
        recipe=(self.folder/'context/overlay.Dockerfile').read_text()
        self.assertEqual({line.split()[0] for line in recipe.splitlines()},{'ARG','FROM','COPY'})
        self.assertIn('COPY qualify/learner.json /qualify/expected.json',recipe)
        self.assertIn('COPY qualify/controls.json /qualify/expected.json',recipe)
        with self.assertRaises(FileExistsError):self.op.freeze(self.folder,ROOT)

    def test_service_and_controls_bind_both_accepted_repair_files_and_controls_retains_fixtures(self):
        for role in ('service','controls'):
            expected=json.loads((self.folder/'qualify'/f'{role}.json').read_bytes())['project_source']
            for name in ('services/foundation/protocol.py','contracts/runs/support_research.py'):
                actual=self.op.sha(self.op.git(ROOT,'show',self.op.SOURCE+':'+name))
                self.assertEqual(expected['/app/'+name],actual)
        expected=json.loads((self.folder/'qualify/controls.json').read_bytes())['project_source']
        self.assertIn('/app/tests/integration/replay/test_support_s1_analysis.py',expected)
        self.assertIn('/app/services/learner/support_s1_worker.py',expected)
        self.assertEqual(expected['/app/tooling/foundation/analysis_lifecycle.py'],
            self.op.sha(self.op.git(ROOT,'show',self.op.SOURCE+':tooling/foundation/analysis_lifecycle.py')))

    def test_pending_host_dependency_stops_before_helper_reservation_or_Docker(self):
        self.plan['host_controller'].update(dependency_status='PENDING',executable_sha256='UNKNOWN',public_files=[])
        for key in self.op.HOST_PROOF:self.plan['host_controller'][key]='UNKNOWN'
        self.authorize()
        with patch.object(self.op,'load_lifecycle',side_effect=AssertionError('helper must not load')),\
                patch.object(self.op,'command_attempt',side_effect=AssertionError('Docker must not run')):
            with self.assertRaisesRegex(RuntimeError,'PENDING'):self.op.execute(self.planpath,self.digest)
        self.assertFalse((self.folder/'results').exists())

    def test_accepted_host_fixture_still_rejects_other_interpreter_or_changed_bytes(self):
        self.op.validate_plan(self.planpath,self.digest)
        with patch.object(self.op.sys,'executable','C:/venv/python.exe'):
            with self.assertRaisesRegex(ValueError,'direct-base'):self.op.check_host_dependency(self.plan)
        fake=self.folder/'fake-base-bytes';fake.write_bytes(b'changed')
        with patch.object(self.op.sys,'executable','C:/Python313/python.exe'),patch.object(self.op,'ordinary',return_value=fake):
            with self.assertRaisesRegex(ValueError,'bytes changed'):self.op.check_host_dependency(self.plan)

    def test_all_three_public_file_bytes_are_checked_without_running_them(self):
        blobs=('444ad4330e159846dc13dae081d42904632cbf8e','0602c5617cba33e0df70cd0a4675db45457cccdb',
            '8fd7313806418ecf05c533f7c31c381b256ba8b9')
        public={row['path']:self.op.git(ROOT,'show',blob) for row,blob in zip(self.op.HOST_FILES,blobs)}
        def file(path):return SimpleNamespace(read_bytes=lambda:public[path])
        with patch.object(self.op.sys,'executable','C:/Python313/python.exe'),patch.object(self.op,'ordinary',side_effect=file):
            self.op.check_host_dependency(self.plan)
            for row in self.op.HOST_FILES:
                original=public[row['path']];public[row['path']]=b'corrupt'
                with self.subTest(path=row['path']),self.assertRaisesRegex(ValueError,'bytes changed'):
                    self.op.check_host_dependency(self.plan)
                public[row['path']]=original

    def test_accepted_looking_references_cannot_replace_the_reviewed_real_probe(self):
        self.plan['host_controller']['accepted_probe_receipt']='a'*40;self.authorize()
        with self.assertRaisesRegex(ValueError,'exact accepted'):self.op.validate_plan(self.planpath,self.digest)

    def test_unreviewed_plan_hash_or_extra_inventory_fails_before_helper_execution(self):
        with patch.object(self.op,'load_lifecycle',side_effect=AssertionError('must not load')):
            with self.assertRaises(ValueError):self.op.execute(self.planpath,'0'*64)
            (self.folder/'context/unlisted').write_bytes(b'unreviewed')
            with self.assertRaisesRegex(ValueError,'inventory'):self.op.execute(self.planpath,self.digest)
        self.assertFalse((self.folder/'results').exists())

    def test_changed_helper_or_probe_bytes_cannot_execute(self):
        for name in ('operator/analysis_lifecycle.py','context/qualify/probe.py'):
            with self.subTest(name=name):
                target=self.folder/name;original=target.read_bytes();target.write_bytes(original+b'\n')
                with patch.object(self.op,'load_lifecycle',side_effect=AssertionError('must not load')):
                    with self.assertRaisesRegex(ValueError,'bytes changed'):self.op.execute(self.planpath,self.digest)
                target.write_bytes(original)

    def test_role_or_resource_ceiling_cannot_drift_even_with_new_hash(self):
        self.plan['phase_seconds']=901;self.authorize()
        with self.assertRaisesRegex(ValueError,'ceilings'):self.op.validate_plan(self.planpath,self.digest)
        self.plan['phase_seconds']=900;self.plan['roles']['service']['uid']='0:0';self.authorize()
        with self.assertRaisesRegex(ValueError,'role identity'):self.op.validate_plan(self.planpath,self.digest)

    def image(self,role,identity=None,child=False):
        item=self.plan['roles'][role]
        return dict(Id=identity or item['parent'],Os='linux',Architecture='amd64',
            User=item['uid'],WorkingDir='/app',Entrypoint=None,Cmd=['python','-m','role'],
            Layers=item['parent_layers']+(['sha256:'+'f'*64] if child else []))

    def container(self,role,cid,image):
        return dict(Id=cid,Image=image,User=self.plan['roles'][role]['uid'],Path='python',
            Args=self.op.workload(role,self.plan)[1:],Labels={'remission.task':'shared-image02-8b82399'},
            State=dict(Status='created',Pid=0,ExitCode=0,Running=False,Paused=False,Restarting=False,
                Dead=False,OOMKilled=False),RestartCount=0,Memory=2147483648,MemorySwap=2147483648,
            NanoCpus=2000000000,PidsLimit=64,ReadonlyRootfs=True,Privileged=False,CapAdd=None,
            CapDrop=['ALL'],AutoRemove=False,SecurityOpt=['no-new-privileges'],
            NetworkMode='none',Tmpfs={'/tmp':'rw,exec,nosuid,nodev,size=512m'},PortBindings={},
            PublishAllPorts=False,RestartPolicy={'Name':'no','MaximumRetryCount':0},Mounts=[])

    def test_copy_image_preserves_parent_layers_and_runtime_configuration(self):
        parent=self.image('service');identity='sha256:'+'a'*64
        child=self.image('service',identity,True)
        self.op.image_checked(child,identity,'service',parent=parent)
        for key,value in [('Layers',['sha256:'+'f'*64]),('Cmd',['changed']),('Entrypoint',['sh']),('User','0:0')]:
            changed=copy.deepcopy(child);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.op.image_checked(changed,identity,'service',parent=parent)

    def test_prestart_denies_mounts_foreign_cid_live_state_and_resource_drift(self):
        cid='a'*64;image='sha256:'+'b'*64;base=self.container('service',cid,image)
        self.op.checked_container(base,cid,image,'service',self.plan,self.life)
        for key,value in [('Mounts',[{'Source':'private'}]),('Image','sha256:'+'c'*64),
                ('Id','c'*64),('Memory',2147483649),('MemorySwap',-1),('NanoCpus',3000000000),
                ('PidsLimit',65),('Privileged',True),('PortBindings',{'80/tcp':[]}),
                ('User','0:0'),('Args',['changed']),('AutoRemove',True)]:
            changed=copy.deepcopy(base);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.op.checked_container(changed,cid,image,'service',self.plan,self.life)
        changed=copy.deepcopy(base);changed['State'].update(Status='running',Running=True,Pid=22)
        with self.assertRaises(ValueError):self.op.checked_container(changed,cid,image,'service',self.plan,self.life)
        argv=self.op.create_argv('service',self.plan,image)
        self.assertNotIn('--mount',argv);self.assertNotIn('-v',argv)

    def fake_commands(self,fail=None):
        calls=[];ids={'service':'sha256:'+'a'*64,'learner':'sha256:'+'b'*64,'controls':'sha256:'+'e'*64}
        cids={'service':'c'*64,'learner':'d'*64,'controls':'f'*64}
        def attempt(argv,output,label,timeout,cleanup):
            calls.append(label)
            self.assertTrue((output/'authorization-consumed.json').is_file())
            result=dict(exit=0,timed_out=False,deadline_rejected=False,cli_pid=123,
                stdout='',stderr='',stdout_truncated=False,stderr_truncated=False)
            role=label.split('-')[0]
            item=self.plan['roles'][role]
            if label.endswith('-parent'):result['stdout']=json.dumps(self.image(role))
            elif label.endswith('-tag-absence'):
                result.update(exit=1,stderr='Error: No such image: '+argv[-1])
            elif label.endswith('-parent-alias-id'):result['stdout']=item['parent']
            elif label.endswith('-build'):(output/f'{role}.iid').write_text(ids[role])
            elif label.endswith('-child'):result['stdout']=json.dumps(self.image(role,ids[role],True))
            elif label.endswith('-create'):result['stdout']=cids[role]
            elif label.endswith('-prestart'):result['stdout']=json.dumps(self.container(role,cids[role],ids[role]))
            elif label.endswith('-probe-output'):
                expected=json.loads((self.folder/'qualify'/f'{role}.json').read_bytes())
                result['stdout']=json.dumps(dict(status='copied_source_metadata_scalar_imports_only',
                    role=role,project_source=expected['project_source'],probe_sha256=self.plan['probe_sha256'],
                    expected_sha256=item['expected_sha256'],scientific_imports=False,worker_executed=False,
                    Store_opened=False,generated_or_fitted=False))
            if fail:fail(label,result)
            return result
        return calls,attempt

    @contextmanager
    def mocked_dependencies(self):
        with patch.object(self.op,'load_lifecycle',return_value=self.life),\
                patch.object(self.op,'check_host_dependency'):
            yield

    def run_double(self,attempt):
        return patch.object(self.op,'command_attempt',side_effect=attempt),self.mocked_dependencies()

    def test_success_is_once_only_and_all_three_roles_are_absent_before_first_mutation(self):
        calls,attempt=self.fake_commands();a,b=self.run_double(attempt)
        with a,b,patch.object(self.life,'supervise',return_value={'typed':'terminal'}):
            result=self.op.execute(self.planpath,self.digest)
            self.assertEqual(result['status'],'qualified_copy_metadata_scalar_imports_only')
            first=len(calls)
            with self.assertRaises(FileExistsError):self.op.execute(self.planpath,self.digest)
            self.assertEqual(len(calls),first)
        self.assertLess(calls.index('controls-container-absence'),calls.index('service-tag-parent'))
        self.assertEqual(sum(x.endswith('-build') for x in calls),3)
        receipt=json.loads((self.folder/'results/observed-images.json').read_bytes())
        self.assertFalse(receipt['generation_or_fit']);self.assertFalse(receipt['Store_opened'])

    def test_truncated_absence_is_failure_and_never_mutates(self):
        def fail(label,result):
            if label=='service-parent-tag-absence':result['stderr_truncated']=True
        calls,attempt=self.fake_commands(fail);a,b=self.run_double(attempt)
        with a,b,self.assertRaisesRegex(RuntimeError,'absence not proven'):
            self.op.execute(self.planpath,self.digest)
        self.assertNotIn('service-tag-parent',calls)

    def test_uncertain_build_stops_without_retry_or_inventing_cid(self):
        def fail(label,result):
            if label=='service-build':result.update(timed_out=True,exit=-9)
        calls,attempt=self.fake_commands(fail);a,b=self.run_double(attempt)
        with a,b,self.assertRaises(self.life.StopUnconfirmed):self.op.execute(self.planpath,self.digest)
        self.assertEqual(calls.count('service-build'),1);self.assertNotIn('learner-build',calls)
        receipt=json.loads((self.folder/'results/observed-images.json').read_bytes())
        self.assertEqual(receipt['status'],'STOP UNCONFIRMED');self.assertEqual(receipt['owned_cids'],[])
        self.assertEqual(receipt['unresolved'][0]['daemon_build'],'UNKNOWN')

    def test_controls_failure_preserves_actual_qualified_roles_without_claiming_all_pass(self):
        def fail(label,result):
            if label=='controls-probe-output':result['stdout']='{}'
        calls,attempt=self.fake_commands(fail);a,b=self.run_double(attempt)
        with a,b,patch.object(self.life,'supervise',return_value={}),patch.object(
                self.life,'stop_owned',return_value=[{'stopped':True}]):
            with self.assertRaises(KeyError):self.op.execute(self.planpath,self.digest)
        receipt=json.loads((self.folder/'results/observed-images.json').read_bytes())
        self.assertEqual(receipt['status'],'failed')
        self.assertEqual(set(receipt['images']),{'service','learner'})
        self.assertEqual(receipt['owned_cids'],['c'*64,'d'*64,'f'*64])
        self.assertEqual(calls.count('controls-build'),1)

    def test_corrupt_probe_stops_exact_owned_cid_and_retains_failure(self):
        def fail(label,result):
            if label=='service-probe-output':result['stdout']='{}'
        calls,attempt=self.fake_commands(fail);a,b=self.run_double(attempt)
        with a,b,patch.object(self.life,'supervise',return_value={}),patch.object(
                self.life,'stop_owned',return_value=[{'stopped':True}]) as stop:
            with self.assertRaises(KeyError):self.op.execute(self.planpath,self.digest)
            stop.assert_called_once_with('c'*64)
        self.assertNotIn('learner-build',calls)
        self.assertTrue((self.folder/'results/observed-images.json').is_file())

    def test_unknown_creation_never_advances_or_invents_an_owned_cid(self):
        def fail(label,result):
            if label=='service-create':result['stdout']='not-a-cid'
        calls,attempt=self.fake_commands(fail);a,b=self.run_double(attempt)
        with a,b,self.assertRaises(self.life.StopUnconfirmed):self.op.execute(self.planpath,self.digest)
        self.assertNotIn('service-prestart',calls);self.assertNotIn('learner-build',calls)
        receipt=json.loads((self.folder/'results/observed-images.json').read_bytes())
        self.assertEqual(receipt['unresolved'][-1]['CID'],'UNKNOWN')
        self.assertEqual(receipt['owned_cids'],[])

    def test_late_successful_command_is_rejected_and_cleanup_failure_stays_unconfirmed(self):
        def fail(label,result):
            if label=='service-probe-output':result['deadline_rejected']=True
        calls,attempt=self.fake_commands(fail);a,b=self.run_double(attempt)
        with a,b,patch.object(self.life,'supervise',return_value={}),patch.object(
                self.life,'stop_owned',side_effect=self.life.StopUnconfirmed('not observed')):
            with self.assertRaises(self.life.StopUnconfirmed):self.op.execute(self.planpath,self.digest)
        self.assertNotIn('learner-build',calls)
        receipt=json.loads((self.folder/'results/observed-images.json').read_bytes())
        self.assertEqual(receipt['status'],'STOP UNCONFIRMED');self.assertEqual(receipt['images'],{})
        self.assertEqual(receipt['cleanup'][0]['cid'],'c'*64)

    def test_regular_file_capture_reaps_exact_child_and_never_claims_daemon_stop(self):
        output=self.folder/'child-capture';output.mkdir()
        value=self.op.command_attempt([sys.executable,'-I','-B','-c','import time;time.sleep(5)'],
            output,'timeout',.03,3)
        self.assertTrue(value['timed_out']);self.assertTrue(value['deadline_rejected'])
        self.assertEqual(value['cli_terminal'],'OWNED_POPEN_CHILD_EXIT_OBSERVED')
        self.assertEqual(value['cli_descendants_terminal'],'UNKNOWN')
        self.assertIn('kill_exact_Popen_child',value['cleanup'])
        self.assertTrue((output/'timeout.json').is_file())

    def test_no_host_or_probe_static_scientific_imports(self):
        denied={'numpy','scipy','pandas','pymc','pytensor','arviz','arviz_base','arviz_stats',
            'arviz_plots','xarray','netCDF4','statsmodels','methods'}
        for path in (SOURCE,SOURCE.with_name('nof1_image01_probe.py')):
            tree=ast.parse(path.read_text(encoding='utf-8'))
            imports={name.name.split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.Import) for name in node.names}
            imports|={node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.ImportFrom) and node.module}
            self.assertFalse(denied&imports)
        self.assertFalse(denied&sys.modules.keys())


if __name__=='__main__':unittest.main()
