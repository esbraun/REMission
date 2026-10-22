"""Host policy/FD/watchdog controls only. No clinical graph or sampling."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tooling/foundation'))
import run_pa3_compile as runner


def policy():
    return json.loads((Path(__file__).resolve().parents[2]/'tooling/foundation/pa3-borrow-profile-policy.json').read_bytes())


class ActualProfileControls(unittest.TestCase):
    def test_production_policy_rejects_changed_phase_deadline_and_config(self):
        runner.check_borrow_policy(policy())
        for key,value in [('phase_seconds',601),('suite_seconds',1801),('phases',['guided-gradient'])]:
            changed=policy();changed[key]=value
            with self.assertRaises(ValueError):runner.check_borrow_policy(changed)
        changed=policy();changed['configuration']['sha256']='0'*64
        with self.assertRaises(ValueError):runner.check_borrow_policy(changed)

    def test_final_fd_native_and_information_binding_are_required(self):
        names=['x'+str(i) for i in range(11)]
        layout=[dict(name=n,start=i,stop=47 if i==10 else i+1,shape=[],dtype='float64') for i,n in enumerate(names)]
        binding=dict(history='actual-control')
        points=[[0.]*47 for _ in range(3)]
        rows=dict(coordinates=dict(binding=binding,native_coordinate_map=layout),
            **{'guided-logp':dict(binding=binding,value_variable_order=names,values=[1.,2.,3.],coordinate_finite_difference=copy.deepcopy(points)),
               'guided-gradient':dict(binding=binding,value_variable_order=names,values=copy.deepcopy(points)),
               'guided-native-logp-gradient':dict(binding=binding,value_variable_order=names,values=copy.deepcopy(points),native_logp=[1.,2.,3.],native_coordinate_map=layout)})
        runner.qualify_borrow_profile(rows)
        for kind in ['fd','native-density','missing-point','different-history','native-map']:
            changed=copy.deepcopy(rows)
            if kind=='fd':changed['guided-gradient']['values'][0][0]=.01
            elif kind=='native-density':changed['guided-native-logp-gradient']['native_logp'][0]+=.01
            elif kind=='missing-point':changed['guided-gradient']['values'].pop()
            elif kind=='different-history':changed['guided-gradient']['binding']={'history':'legacy'}
            else:changed['guided-native-logp-gradient']['native_coordinate_map']=[]
            with self.assertRaises(ValueError):runner.qualify_borrow_profile(changed)

    def test_first_phase_deadline_kills_actual_owned_computation_and_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);clock=[0.];launches=[];killed=[];running=[True]
            files={'actual.json':b'ACTUAL INPUT CONTROL\n','services/foundation/studies/source-7c97862d.json':b'SOURCE CONTROL\n'}
            points=dict(input_sha256=hashlib.sha256(files['actual.json']).hexdigest(),source_file_sha256=hashlib.sha256(files['services/foundation/studies/source-7c97862d.json']).hexdigest())
            files['points.json']=json.dumps(points).encode()
            for name,data in files.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            p=policy();p.update(input_file='actual.json',points_file='points.json',input_files={
                'input.json':points['input_sha256'],'sources.json':points['source_file_sha256'],'points.json':hashlib.sha256(files['points.json']).hexdigest()})
            config=root/'policy.json';config.write_text(json.dumps(p));evidence=root/'evidence'

            def capture(argv,*args,**kwargs):
                text='';timeout=False
                if argv[:3]==['docker','image','inspect']:text=runner.RUNTIME if argv[3]=='remission-foundation-runtime:candidate' else 'sha256:OWNED-PROFILE-CONTROL'
                elif argv[:3]==['git','rev-parse','HEAD']:text='TEST-ONLY-SOURCE'
                elif argv[:3]==['docker','run','--name']:
                    launches.append(argv);clock[0]+=600.01;timeout=True
                elif argv[:2]==['docker','kill']:
                    killed.append(argv[2]);running[0]=False
                elif argv[:2]==['docker','inspect']:
                    text=json.dumps([dict(Id='owned-control',Image='sha256:OWNED-PROFILE-CONTROL',Config=dict(User='10002:10002'),
                        State=dict(Running=running[0],ExitCode=0 if running[0] else 137,OOMKilled=False),
                        HostConfig=dict(Memory=2147483648,NanoCpus=2000000000,NetworkMode='none',ReadonlyRootfs=True),Mounts=[])])
                elif argv[:2]==['docker','cp'] and argv[2].endswith(':/output'):
                    target=Path(argv[3]);target.mkdir();(target/'partial-marker.json').write_text('{"stage":"control-hang"}')
                return subprocess.CompletedProcess(argv,124 if timeout else 0,text.encode(),b''),dict(timed_out=timeout,streams={'stderr':{'path':'RETAINED-CONTROL'}})

            with patch.object(runner,'ROOT',root),patch.object(runner,'run',capture),patch.object(runner.time,'monotonic',lambda:clock[0]), \
                    patch.object(sys,'argv',['run_pa3_compile','--image','owned','--evidence',str(evidence),'--borrow-profile-policy',str(config)]):
                with self.assertRaises(SystemExit) as stopped:runner.main()
                self.assertEqual(stopped.exception.code,1)
            self.assertEqual(len(launches),1)
            argv=launches[0];name=argv[3]
            self.assertEqual(argv[argv.index('--phase')+1],'coordinates');self.assertEqual(killed,[name])
            self.assertIn('--read-only',argv);self.assertEqual(argv[argv.index('--network')+1],'none')
            self.assertTrue(any('target=/input' in value or 'dst=/input,readonly' in value for value in argv))
            result=json.loads((evidence/'result.json').read_bytes())
            self.assertEqual(result['reason'],'deadline-exceeded');self.assertEqual(result['status'],'not-qualified')
            self.assertTrue((evidence/'coordinates/partial-marker.json').exists())
            self.assertFalse((evidence/'guided-native-logp-gradient').exists())


if __name__=='__main__':unittest.main()
