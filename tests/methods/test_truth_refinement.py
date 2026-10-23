"""TA-T5/6 scalar fixtures and lifecycle doubles; no scientific runtime imports."""
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from methods.truth import refinement as r
from services.evaluator import restricted_refinement as driver
from tooling.foundation import truth_refinement as wrapper


def fixture():
    history = r.canonical(dict(patient_id='scalar-fixture-patient', cutoff='2026-01-15T12:00:00Z'))
    binding = dict(data_schema=r.SCHEMA, namespace=r.NAMESPACE, target=deepcopy(r.TARGET), runtime=dict(r.RUNTIME),
        image=r.IMAGE, patient_id='scalar-fixture-patient', history_sha256=r.digest(history),
        history_raw_sha256=r.digest(history), history_bytes=len(history), source_head='1'*40,
        source_files={'fixture.txt':wrapper.file_binding(b'TEST-LOCAL-SCALAR-FIXTURE')},
        refs={'policy':'TEST-LOCAL-FROZEN-POLICY'})
    return dict(binding=binding, workload=r.workload(binding['patient_id'], binding['history_sha256'])), history


def result(item, binding, estimate=1., se=.008):
    value = deepcopy(binding['target'])
    value.update(status='exploratory_unqualified', reason='TA2_refinement_and_matched_SE_pending',
        patient_id=binding['patient_id'], history_sha256=binding['history_sha256'],
        namespace=binding['namespace'], replicate=item['replicate'], prng='NumPy-PCG64',
        seeds=item['seeds'], estimate=estimate, within_filter_rollout_mcse=se,
        filter_diagnostics={'severe_weight_collapse':False}, future_trajectories=20000,
        batches=[dict(index=0,trajectories=10000),dict(index=1,trajectories=10000)],
        conditioning_seconds=.25, elapsed_seconds=.4)
    return value


def completed(plan):
    rows = []
    for item in plan['workload']:
        # Low m_i=i. First paired changes i/100, next -i/200;
        # stability changes exactly +.003. All expectations are closed form.
        i = item['replicate']
        value = i
        if item['particles'] >= 4096:
            value += i/100
        if item['particles'] == 16384:
            value -= i/200
        if item['moves'] == 4:
            value += .003
        rows.append(dict(key=item['key'], status='completed', result=result(item,plan['binding'],value)))
    return rows


class ReductionTests(unittest.TestCase):
    def test_order_counts_shared_keys_and_frozen_seed_recipe(self):
        plan,_ = fixture(); inventory = plan['workload']
        self.assertEqual(len(inventory),128)
        self.assertEqual([(inventory[i]['particles'],inventory[i]['moves']) for i in (0,32,64,96)],
                         [(1024,2),(4096,2),(16384,2),(16384,4)])
        self.assertEqual(inventory[0]['seeds'],inventory[32]['seeds'])
        self.assertEqual(inventory[0]['seeds'],inventory[96]['seeds'])
        self.assertNotEqual(inventory[0]['seeds'],inventory[1]['seeds'])
        # Independently checked with .NET SHA256 over the literal UTF8 key.
        self.assertEqual(r.seed('truth-x','p','h',0,'future'),
                         184599159104322890640448309619373491495)

    def test_hand_calculated_sample_se_pairing_and_draw_denominators(self):
        plan,_ = fixture()
        report=r.reduce_rows(completed(plan),plan['workload'],plan['binding'],quadrature_change=.001)
        # For integers0..31: mean15.5, sample variance88.
        self.assertAlmostEqual(report['levels'][0]['mean'],15.5)
        self.assertAlmostEqual(report['levels'][0]['between_filter_mcse'],math.sqrt(88/32))
        self.assertAlmostEqual(report['levels'][0]['within_filter_mcse'],.008/math.sqrt(32))
        first,second=report['refinements']
        self.assertAlmostEqual(first['signed_mean_difference'],.155)
        self.assertAlmostEqual(first['paired_standard_error'],math.sqrt(88/32)/100)
        self.assertAlmostEqual(second['signed_mean_difference'],-.0775)
        self.assertAlmostEqual(second['paired_standard_error'],math.sqrt(88/32)/200)
        self.assertAlmostEqual(second['bound'],.0775+1.96*math.sqrt(88/32)/200)
        self.assertAlmostEqual(report['moves_stability']['signed_mean_difference'],.003)
        self.assertAlmostEqual(report['moves_stability']['paired_standard_error'],0,places=14)
        self.assertEqual(report['levels'][2]['future_trajectories'],640000)
        self.assertEqual(report['total_recorded_future_trajectories'],2560000)
        self.assertEqual(report['independent_replicate_groups'],32)
        self.assertEqual(report['status'],'unresolved')

    def test_pairing_is_actual_replicate_difference_not_unpaired_sd(self):
        low=list(range(32)); high=[x+.25 for x in low]
        paired=r.paired(low,high)
        self.assertEqual(paired['signed_mean_difference'],.25)
        self.assertEqual(paired['paired_standard_error'],0.)
        self.assertGreater(r.paired(low,list(reversed(high)))['paired_standard_error'],1)

    def test_missing_duplicate_unknown_and_failures_are_not_dropped(self):
        plan,_=fixture();rows=completed(plan)
        for bad in (rows[:-1],rows+[rows[0]],rows[:-1]+[dict(key='unknown',status='pending')]):
            with self.assertRaises(ValueError):r.reduce_rows(bad,plan['workload'],plan['binding'])
        for state in ('pending','running','failed','inconclusive'):
            altered=deepcopy(rows);altered[0]={'key':rows[0]['key'],'status':state}
            report=r.reduce_rows(altered,plan['workload'],plan['binding'])
            self.assertEqual(report['levels'][0]['status'],'incomplete')
            self.assertNotIn('mean',report['levels'][0])
            self.assertEqual(report['refinements'][0]['status'],'incomplete')
            self.assertEqual(report['counts'][state],1)

    def test_nonfinite_negative_and_wrong_draws_reject(self):
        plan,_=fixture()
        for key,value in [('estimate',float('nan')),('within_filter_rollout_mcse',-.1),('future_trajectories',19999)]:
            rows=completed(plan);rows[0]['result'][key]=value
            with self.assertRaises(ValueError):r.reduce_rows(rows,plan['workload'],plan['binding'])

    def test_budget_missing_zero_matched_se_and_no_qualification(self):
        plan,_=fixture();rows=completed(plan)
        for row in rows:row['result'].update(estimate=-1.,within_filter_rollout_mcse=.00001)
        for matched in (None,0.,.2):
            report=r.reduce_rows(rows,plan['workload'],plan['binding'],matched_se=matched,quadrature_change=.001)
            self.assertEqual(report['status'],'unresolved')
            self.assertFalse(report['production_truth'])
            self.assertIsNone(report['finite_grid_discrepancy_bound'])
            self.assertEqual(report['full_conditioning_qualification'],'unresolved')
            self.assertAlmostEqual(report['epsilon'],.02 if matched else .05)
            self.assertTrue(report['budget_diagnostics']['each_within_quarter'])
        self.assertIsNone(r.reduce_rows(rows,plan['workload'],plan['binding'])['budget_diagnostics'])


class FileSeamTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.plan,self.history=fixture()
        self.expected=deepcopy(self.plan['binding'])
        (self.root/'fixture.txt').write_bytes(b'TEST-LOCAL-SCALAR-FIXTURE')
        (self.root/'history.json').write_bytes(self.history)
        self.expected_raw=r.canonical(self.expected)
        (self.root/'expected.json').write_bytes(self.expected_raw)
        self.write_plan()

    def write_plan(self):
        (self.root/'plan.json').write_bytes(r.canonical(self.plan))

    def load(self):
        return driver.load_inputs(self.root/'plan.json',self.root/'expected.json',r.digest(self.expected_raw),
                                  self.root/'history.json',self.root)

    def test_valid_independent_fixture_and_raw_corruption(self):
        self.assertEqual(self.load()[1],self.expected)
        for name in ('history.json','fixture.txt','expected.json'):
            path=self.root/name;raw=path.read_bytes();path.write_bytes(raw+b' ')
            with self.assertRaises(ValueError):self.load()
            path.write_bytes(raw)

    def test_internally_rehashed_semantic_mutations_at_actual_file_seam(self):
        original=deepcopy(self.plan)
        mutations=[lambda p:p['binding'].update(patient_id='other-patient'),
            lambda p:p['binding'].update(history_sha256='2'*64),
            lambda p:p['binding'].update(source_head='2'*40),
            lambda p:p['binding']['runtime'].update(numpy='wrong-runtime'),
            lambda p:p['binding']['refs'].update(policy='wrong-policy'),
            lambda p:p['binding']['target'].update(direction='continue-minus-escalate'),
            lambda p:p['binding']['target'].update(endpoint_absolute_day=42),
            lambda p:p['workload'][0]['seeds'].update(conditioning=3),
            lambda p:p['workload'][0].update(seconds=600),
            lambda p:p['workload'].reverse()]
        for mutate in mutations:
            self.plan=deepcopy(original);mutate(self.plan)
            self.write_plan()  # canonical bytes/hashes are internally consistent
            self.assertEqual(r.digest((self.root/'plan.json').read_bytes()),r.digest(r.canonical(self.plan)))
            with self.assertRaises(ValueError):self.load()

    def test_result_semantic_failure_and_collapse_batch_failure(self):
        item=self.plan['workload'][0];good=result(item,self.expected)
        for key,value in [('patient_id','other'),('history_sha256','0'*64),('direction','wrong'),
                          ('endpoint_absolute_day',42),('replicate',1),('seeds',{'future':4})]:
            bad=deepcopy(good);bad[key]=value
            with self.assertRaises(ValueError):r.validate_result(bad,item,self.expected)
        bad=deepcopy(good);bad['filter_diagnostics']['severe_weight_collapse']=True
        self.assertFalse(r.validate_result(bad,item,self.expected))
        bad=deepcopy(good);bad['batches'][1]['index']=0
        with self.assertRaises(ValueError):r.validate_result(bad,item,self.expected)


class DriverTests(unittest.TestCase):
    def test_serial_persist_before_next_and_no_retry_after_failure(self):
        plan,_=fixture();calls=[]
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'run'
            def evaluate(item,progress):
                index=len(calls);calls.append(item['key'])
                inventory=json.loads((output/'inventory.json').read_bytes())
                self.assertEqual(inventory[index]['status'],'running')
                if index:
                    self.assertTrue((output/'rows'/calls[index-1]/'outcome.json').exists())
                progress(dict(fixture='raw progress',index=index))
                if index==1:raise RuntimeError('injected scalar failure')
                return result(item,plan['binding'])
            report=driver.run_rows(plan,plan['binding'],output,evaluate)
            self.assertEqual(len(calls),2)
            self.assertEqual(report['counts'],dict(pending=126,running=0,completed=1,inconclusive=0,failed=1))
            self.assertTrue((output/'rows'/calls[1]/'progress.json').exists())
            with self.assertRaises(FileExistsError):driver.run_rows(plan,plan['binding'],output,evaluate)
            self.assertEqual(len(calls),2)

    def test_cap_preserves_expected_pending_inventory(self):
        plan,_=fixture();calls=[];ticks=iter([0.,1700.,1701.,1702.,1703.,1704.])
        with tempfile.TemporaryDirectory() as folder:
            report=driver.run_rows(plan,plan['binding'],Path(folder)/'run',
                lambda *args:calls.append(args),clock=lambda:next(ticks))
            self.assertEqual(calls,[])
            self.assertEqual(report['counts']['pending'],128)
            self.assertEqual(report['stop_reason'],'internal_operation_cap_no_next_evaluation')

    def test_inconclusive_partial_batches_retained_not_replaced(self):
        plan,_=fixture();calls=[]
        with tempfile.TemporaryDirectory() as folder:
            def evaluate(item,progress):
                calls.append(item['key']);value=result(item,plan['binding'])
                if len(calls)==1:value.update(status='inconclusive',reason='wall_time_cap',batches=[])
                return value
            report=driver.run_rows(plan,plan['binding'],Path(folder)/'run',evaluate)
            self.assertEqual(len(calls),128);self.assertEqual(len(set(calls)),128)
            self.assertEqual(report['counts']['inconclusive'],1)
            self.assertEqual(report['levels'][0]['status'],'incomplete')


class LifecycleTests(unittest.TestCase):
    def stage(self,root):
        plan,history=fixture();(root/'source').mkdir();(root/'input').mkdir();(root/'output').mkdir()
        (root/'source/fixture.txt').write_bytes(b'TEST-LOCAL-SCALAR-FIXTURE')
        (root/'input/history.json').write_bytes(history)
        (root/'input/expected-binding.json').write_bytes(r.canonical(plan['binding']))
        (root/'input/workload.json').write_bytes(r.canonical(plan))
        files={p.relative_to(root).as_posix():wrapper.file_binding(p.read_bytes())
               for p in root.rglob('*') if p.is_file()}
        spec=dict(stage=str(root),files=files,create_argv=wrapper.create_argv(root),lifecycle_cap_seconds=1800)
        raw=r.canonical(spec);(root/'invocation.json').write_bytes(raw)
        return r.digest(raw)

    def test_one_literal_cid_absolute_deadline_and_no_retry_on_stop_unconfirmed(self):
        for failure in (None,TimeoutError('cap'),RuntimeError('STOP UNCONFIRMED')):
            with tempfile.TemporaryDirectory() as folder:
                stage=Path(folder).resolve();token=self.stage(stage);events=[];cid='a'*64
                def command(argv,**kwargs):
                    events.append(('create',kwargs['deadline']))
                    return SimpleNamespace(returncode=0,stdout=(cid+'\n').encode(),stderr=b'')
                def supervise(actual,output,deadline):
                    self.assertEqual(actual,cid);events.append(('supervise',deadline))
                    if failure:raise failure
                    return dict(Id=cid,State=dict(Status='exited',Pid=0,Running=False))
                lifecycle=SimpleNamespace(command=command,require_cid=lambda value:value,supervise=supervise)
                if failure:
                    with self.assertRaises(type(failure)):wrapper.run(stage,token,lifecycle=lifecycle,clock=lambda:7.)
                else:wrapper.run(stage,token,lifecycle=lifecycle,clock=lambda:7.)
                self.assertEqual(events,[('create',1807.),('supervise',1807.)])
                self.assertTrue((stage/'attempt-reserved.json').exists())
                manifest=json.loads((stage/'raw-manifest.json').read_bytes())
                self.assertEqual(manifest['files']['execution/create.stderr']['bytes'],0)
                with self.assertRaises(FileExistsError):wrapper.run(stage,token,lifecycle=lifecycle)
                self.assertEqual(len(events),2)

    def test_independent_invocation_token_rejects_internally_rehashed_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder).resolve();token=self.stage(stage)
            value=json.loads((stage/'invocation.json').read_bytes());value['lifecycle_cap_seconds']=9999
            (stage/'invocation.json').write_bytes(r.canonical(value))
            with self.assertRaises(ValueError):wrapper.run(stage,token,lifecycle=object())
            self.assertFalse((stage/'attempt-reserved.json').exists())

    def test_prepare_does_not_call_docker_even_on_failed_freeze(self):
        with patch.object(wrapper,'git',return_value=b'dirty source') as git:
            with self.assertRaises(ValueError):wrapper.prepare('scalar-fixture')
            self.assertEqual(git.call_args.args,('status','--porcelain'))

    def test_preserve_ten_empty_archival_logs_via_manifest_not_artifact_schema(self):
        root=Path(__file__).resolve().parents[2]
        manifest=json.loads((root/'docs/implementation/evidence/truth-ta1-20261022/raw-manifest.json').read_bytes())
        empty=[item for stage in manifest['artifacts'].values() for item in stage.values() if item['bytes']==0]
        self.assertEqual(len(empty),10)
        self.assertTrue(all(item['sha256']==r.digest(b'') for item in empty))
        # Verify manifest's zero-byte Git object identity, without Pydantic or
        # weakening canonical Artifact.bytes>0 for admissible result artifacts.
        blobs={item['git_blob'] for item in empty};self.assertEqual(len(blobs),1)
        for blob in blobs:
            raw=subprocess.check_output(['git','cat-file','blob',blob],cwd=root)
            self.assertEqual(raw,b'')
        source=(root/'contracts/runs/common.py').read_text()
        self.assertIn('bytes: Annotated[int, Field(gt=0)]',source)


if __name__=='__main__':unittest.main()
