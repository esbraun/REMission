"""Non-fitting controls for the one fixed compilation contrast."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tooling/foundation'))
from pa3_compile_probe import native_call,check_fd
from pa3_monitor import compilation_options,optimizer_identity,save_inventory
import run_pa3_compile as runner


def policy():
    return json.loads((Path(__file__).resolve().parents[2]/'tooling/foundation/pa3-numba-policy.json').read_bytes())


class NumbaContrastTests(unittest.TestCase):
    def test_default_has_no_override_or_mode_lookup(self):
        with patch.dict(sys.modules,{'pytensor.compile.mode':SimpleNamespace(get_default_mode=lambda: self.fail('default path imported mode'))}):
            self.assertEqual(compilation_options(None),({},None))

    def test_actual_mode_retains_numba_and_only_excludes_frozen_group(self):
        from pytensor.compile.mode import get_default_mode
        default=get_default_mode();before=optimizer_identity(default.provided_optimizer)
        options,binding=compilation_options(policy(),default)
        self.assertEqual(type(options['mode'].linker).__name__,'NumbaLinker')
        self.assertEqual(binding['candidate_optimizer']['exclude'],['fusion'])
        self.assertEqual(optimizer_identity(default.provided_optimizer),before)
        # Query cloning drops its display name; all other fields stay fixed.
        expected=dict(before,exclude=['fusion'],name=None)
        self.assertEqual(binding['candidate_optimizer'],expected)
        wrong=policy();wrong['excluded_tags']=['fusion','inplace']
        with self.assertRaisesRegex(ValueError,'only the frozen'):compilation_options(wrong,default)

    def test_native_order_offsets_and_explicit_extra_initialization(self):
        import numpy as np
        class Native:
            initialized=False
            def set_extra_values(self,point):self.initialized=point['first']==100.
            def __call__(self,raveled):
                if not self.initialized:raise ValueError('Extra values are not set.')
                np.testing.assert_array_equal(raveled.data,np.r_[100.,np.arange(46.)])
                return -123.,np.arange(47.)
        point={'second':np.arange(46.),'first':np.asarray(100.)}
        variables=[SimpleNamespace(name='first',dtype='float64'),SimpleNamespace(name='second',dtype='float64')]
        value,gradient,mapping=native_call(Native(),point,variables)
        self.assertEqual(value,-123.);self.assertEqual(len(gradient),47)
        self.assertEqual(mapping,[dict(name='first',shape=[],dtype='float64',start=0,stop=1),dict(name='second',shape=[46],dtype='float64',start=1,stop=47)])
        with self.assertRaisesRegex(ValueError,'every value variable'):native_call(Native(),dict(point,unexpected=np.array(1.)),variables)

    def test_fd_rejects_nonfinite_wrong_coordinate_and_missing_point(self):
        row=dict(binding={'history':'frozen'},value_variable_order=['x'],coordinate_finite_difference=[[0.]*47 for _ in range(3)])
        check_fd([[0.]*47 for _ in range(3)],row,['x'],row['binding'])
        for wrong in ([[float('nan')]+[0.]*46]+[[0.]*47]*2,[[.01]+[0.]*46]+[[0.]*47]*2,[[0.]*47]*2):
            with self.assertRaises(ValueError):check_fd(wrong,row,['x'],row['binding'])
        with self.assertRaisesRegex(ValueError,'identity'):check_fd([[0.]*47]*3,row,['wrong'],row['binding'])

    def test_inventory_overflow_prevents_evaluation_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fn=SimpleNamespace(maker=SimpleNamespace(fgraph=SimpleNamespace(toposort=lambda:[object(),object()])))
            with self.assertRaisesRegex(ValueError,'node cap'):save_inventory(fn,root,dict(inventory_node_cap=1))
            self.assertFalse((root/'optimized-inventory.json').exists())

    def check_runner_stops(self,elapsed,fd_pass):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);clock=[0.];launched=[]
            paths={'tests/integration/replay/fixtures/pa3-legacy-v0-input.json':b'input\n','services/foundation/studies/source-7c97862d.json':b'sources\n'}
            points=dict(input_sha256=hashlib.sha256(b'input\n').hexdigest(),source_file_sha256=hashlib.sha256(b'sources\n').hexdigest())
            paths['tooling/foundation/pa3-compile-points.json']=json.dumps(points).encode()
            paths['map.json']=b'{"log_jacobians":[]}\n'
            for name,data in paths.items():
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            p=policy();p['coordinates_file']='map.json';p['coordinates_sha256']=hashlib.sha256(paths['map.json']).hexdigest()
            p['input_files']={Path(name).name:hashlib.sha256(data).hexdigest() for name,data in paths.items() if name!='map.json'}
            p['input_files']={name:p['input_files'][other] for name,other in [('input.json','pa3-legacy-v0-input.json'),('sources.json','source-7c97862d.json'),('points.json','pa3-compile-points.json')]}
            config=root/'policy.json';config.write_text(json.dumps(p));evidence=root/'evidence'
            def capture(argv,*args,**kwargs):
                text=''
                if argv[:3]==['docker','image','inspect']:text=runner.RUNTIME if argv[3]=='remission-foundation-runtime:candidate' else 'sha256:owned-test-image'
                elif argv[:3]==['git','rev-parse','HEAD']:text='frozen-test-head'
                elif argv[:3]==['docker','run','--name']:
                    phase=argv[argv.index('--phase')+1];launched.append(phase);clock[0]+=elapsed
                elif argv[:2]==['docker','inspect']:
                    self.assertEqual(argv[3:],['--format',runner.CONTAINER_FORMAT])
                    text=json.dumps(dict(Id='owned',Image='sha256:owned-test-image',Config={'User':'10002:10002'},State=dict(Running=False,ExitCode=0,OOMKilled=False),HostConfig=dict(Memory=2147483648,NanoCpus=2000000000,NetworkMode='none',ReadonlyRootfs=True),Mounts=[]))
                elif argv[:2]==['docker','cp'] and argv[2].endswith(':/output'):
                    target=Path(argv[3]);target.mkdir();(target/(launched[-1]+'.json')).write_text(json.dumps(dict(status='evaluated',independent_fd={'passed':fd_pass})))
                return subprocess.CompletedProcess(argv,0,text.encode(),b''),dict(timed_out=False,streams={'stderr':{'path':'retained-test-stderr'}})
            with patch.object(runner,'ROOT',root),patch.object(runner,'run',capture),patch.object(runner.time,'monotonic',lambda:clock[0]),patch.object(sys,'argv',['run_pa3_compile','--image','owned','--evidence',str(evidence),'--numba-policy',str(config)]):
                with self.assertRaises(SystemExit) as stopped:runner.main()
                self.assertEqual(stopped.exception.code,1)
            self.assertEqual(launched,['guided-gradient'])
            result=json.loads((evidence/'result.json').read_bytes())
            self.assertEqual(result['status'],'not-qualified')
            self.assertTrue((evidence/'guided-gradient/guided-gradient.json').exists())
            return result

    def test_missing_first_fd_stops_before_native_phase(self):
        result=self.check_runner_stops(1.,False)
        self.assertIn('FD gate missing',result['reason'])

    def test_finished_between_polls_after_deadline_cannot_qualify(self):
        result=self.check_runner_stops(600.01,True)
        self.assertEqual(result['reason'],'deadline-exceeded')


if __name__=='__main__':unittest.main()
