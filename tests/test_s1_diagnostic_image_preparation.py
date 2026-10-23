"""No real process/container/image or application tests."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
PACKET=ROOT/'artifacts/s1-intake-diagnostic-r1/image-qualification'
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
operator=load(ROOT/'tooling/foundation/s1_diagnostic_image.py','scalar_s1_image_operator')
shared=load(ROOT/'tooling/foundation/nof1_image01.py','scalar_accepted_image05')


def configuration(image,cid):
    return dict(Id=cid,State=dict(Status='created',Pid=0),RestartCount=0,Image=image,User='10001:10001',Path='python',
        Args=shared.workload('controls',json.loads((PACKET/'plan.json').read_bytes()))[1:],Labels={'remission.task':operator.NAMESPACE},
        Memory=2147483648,MemorySwap=2147483648,NanoCpus=2000000000,PidsLimit=64,ReadonlyRootfs=True,Privileged=False,
        CapAdd=None,CapDrop=['ALL'],AutoRemove=False,SecurityOpt=['no-new-privileges'],NetworkMode='none',
        Tmpfs={'/tmp':'rw,exec,nosuid,nodev,size=512m'},PortBindings={},PublishAllPorts=False,
        RestartPolicy={'Name':'no','MaximumRetryCount':0},Mounts=[])


class PreparationTests(unittest.TestCase):
    def exercise(self,folder,*,failure=None):
        plan=json.loads((PACKET/'plan.json').read_bytes());calls=[];supervised=[];stops=[]
        (folder/'qualify').mkdir(exist_ok=True)
        (folder/'qualify/controls.json').write_bytes((PACKET/'qualify/controls.json').read_bytes())
        image='sha256:'+'b'*64;cid='c'*64
        class StopUnconfirmed(RuntimeError):pass
        def require(value):
            if re.fullmatch('[a-f0-9]{64}',value) is None:raise ValueError('literal fullCID required')
            return value
        def supervise(value,output,deadline):
            self.assertEqual(value,cid);self.assertEqual(calls[-1][0],'controls-prestart');supervised.append(value)
            return dict(cid=value,PID=0,exit=0,attach_reaped=True,watchdog_reaped=True,independent_final=True)
        life=NS(StopUnconfirmed=StopUnconfirmed,check_deadline=lambda _:None,require_cid=require,supervise=supervise,
            stop_owned=lambda value:stops.append(value),checked_state=lambda value,_cid:value)
        def command(argv,output,label,timeout,cleanup):
            calls.append((label,argv,timeout,cleanup));stdout='';exitcode=0;stderr=''
            if label=='controls-parent':stdout=json.dumps(plan['parent_metadata'])
            elif label.endswith('tag-absence'):exitcode=1;stderr='Error: No such image: '+argv[-1]
            elif label=='parent-alias-id':stdout=operator.PARENT
            elif label=='controls-build':(output/'controls.iid').write_text(image)
            elif label=='controls-child':
                child=dict(plan['parent_metadata'],Id=image,Layers=plan['parent_metadata']['Layers']+['sha256:'+'d'*64]);stdout=json.dumps(child)
            elif label=='controls-create':stdout='not-a-CID' if failure=='CID' else cid
            elif label=='controls-prestart':stdout=json.dumps(configuration(image,cid))
            elif label=='controls-probe-output':
                expected=json.loads((PACKET/'qualify/controls.json').read_bytes())
                stdout=json.dumps(dict(status='copied_source_metadata_scalar_imports_only',role='controls',project_source=expected['project_source'],
                    probe_sha256=plan['probe_sha256'],expected_sha256=plan['roles']['controls']['expected_sha256'],
                    scientific_imports=False,worker_executed=False,Store_opened=False,generated_or_fitted=False))
            return dict(exit=exitcode,error=None,stdout_truncated=False,stderr_truncated=False,timed_out=failure=='build-timeout' and label=='controls-build',
                deadline_rejected=False,cli_pid=123,stdout=stdout,stderr=stderr)
        fake=NS(command_attempt=command,save=shared.save,load_lifecycle=lambda _:life,image_checked=shared.image_checked,
            IMAGE_FORMAT=shared.IMAGE_FORMAT,CONTAINER_FORMAT=shared.CONTAINER_FORMAT,LIMITS=shared.LIMITS,workload=shared.workload)
        with patch.object(operator,'validate',return_value=(folder,plan,fake)):
            try:result=operator.execute(folder/'plan.json','fixed-authorized-scalar-hash');error=None
            except BaseException as caught:result=None;error=caught
        return NS(plan=plan,calls=calls,supervised=supervised,stops=stops,result=result,error=error,life=life)

    def test_packet_copy_map_source_probe_and_bound_inputs(self):
        plan=json.loads((PACKET/'plan.json').read_bytes())
        for name,row in plan['files'].items():
            raw=(PACKET/name).read_bytes();self.assertEqual(len(raw),row['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256'])
            if name.endswith('.py'):compile(raw,name,'exec')
        self.assertEqual(hashlib.sha256((PACKET/'qualify/probe.py').read_bytes()).hexdigest(),'a63bbe6158c7509201345624247a3be4f38da905f3defd1fb1423002adfb0f94')
        self.assertEqual(hashlib.sha256((PACKET/'operator/analysis_lifecycle.py').read_bytes()).hexdigest(),'45cb568da0dd93642ab48fd5edb2aef76394393a1777c3c05c5645259f88ef2b')
        before=json.loads((PACKET/'proof/parent-expected.json').read_bytes())['project_source']
        after=json.loads((PACKET/'qualify/controls.json').read_bytes())['project_source']
        changed={key for key in after if before.get(key)!=after[key]}
        self.assertEqual(len(before),195);self.assertEqual(len(after),196)
        self.assertEqual(changed,{row['destination'] for row in plan['overlay']});self.assertEqual(len(changed),3)
        recipe=(PACKET/'context/overlay.Dockerfile').read_text().splitlines()
        self.assertEqual(sum(line.startswith('COPY ') for line in recipe),4)
        self.assertFalse(any(line.startswith(('RUN ','USER ','ENV ','CMD ','ENTRYPOINT ')) for line in recipe))
        self.assertIsNone(json.loads((PACKET.parent/'stage-p2-diag-r1/p2-service-spec.DRAFT.json').read_bytes())['images']['controls'])
        self.assertFalse((PACKET.parent/'stage-p2-diag-r1/p2-service-spec.json').exists())

    def test_fixed_success_acquires_only_literal_fullCID_and_reuses_exact_supervision(self):
        with tempfile.TemporaryDirectory() as folder:
            record=self.exercise(Path(folder));self.assertIsNone(record.error);self.assertEqual(record.supervised,['c'*64]);self.assertEqual(record.stops,[])
            self.assertEqual(record.result['status'],'qualified_packaging_metadata_scalar_imports_only')
            self.assertTrue((Path(folder)/'results/authorization-consumed.json').exists())
            labels=[row[0] for row in record.calls];self.assertEqual(labels.count('controls-build'),1);self.assertEqual(labels.count('controls-create'),1)
            build=next(row[1] for row in record.calls if row[0]=='controls-build')
            self.assertIn('--pull=false',build);self.assertNotIn('--target',build)
            self.assertTrue(all(row[3]==3 for row in record.calls));self.assertEqual(next(row[2] for row in record.calls if row[0]=='controls-build'),300)

    def test_exclusive_once_output_refuses_second_invocation_before_any_command(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(self.exercise(Path(folder)).error)
            second=self.exercise(Path(folder));self.assertIsInstance(second.error,FileExistsError);self.assertEqual(second.calls,[])

    def test_build_timeout_retains_UNKNOWN_and_never_creates_or_starts_qualifier(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.exercise(Path(folder),failure='build-timeout')
            self.assertIsInstance(result.error,result.life.StopUnconfirmed);self.assertEqual(result.supervised,[]);self.assertEqual(result.stops,[])
            self.assertNotIn('controls-create',[row[0] for row in result.calls])
            observed=json.loads((Path(folder)/'results/observed-images.json').read_bytes())
            self.assertEqual(observed['status'],'STOP UNCONFIRMED');self.assertEqual(observed['unresolved'][0]['daemon_build'],'UNKNOWN')

    def test_unconfirmed_CID_never_attaches_or_uses_a_reported_partial_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.exercise(Path(folder),failure='CID')
            self.assertIsInstance(result.error,result.life.StopUnconfirmed);self.assertEqual(result.supervised,[]);self.assertEqual(result.stops,[])
            self.assertNotIn('controls-prestart',[row[0] for row in result.calls])

    def test_prestart_config_refuses_resource_or_mount_drift(self):
        plan=json.loads((PACKET/'plan.json').read_bytes());cid='c'*64;image='sha256:'+'b'*64
        life=NS(checked_state=lambda value,_cid:value)
        for key,value in [('PidsLimit',128),('CapAdd',['CHOWN']),('Mounts',[{'Source':'forbidden'}]),('NetworkMode','bridge'),('User','0:0')]:
            state=configuration(image,cid);state[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):operator.checked_container(state,cid,image,plan,life,shared)
