"""Bounded orchestration doubles only; no Docker, service, DB or numerical run."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import traceback
import unittest
from unittest.mock import Mock, patch
import analysis_dispatcher as dispatcher
import analysis_lifecycle as life
from contracts.domain.cohort import make_cohort_input
from tests.contracts.test_cohort_qualification import qualified_input

CID='a'*64


def inventory(status='exited', **changes):
    state=dict(Status=status,Running=status=='running',Paused=False,Restarting=False,Dead=status=='dead',
        Pid=100 if status=='running' else 0,ExitCode=0,OOMKilled=False)
    state.update(changes)
    return dict(Id=CID,RestartCount=0,State=state)


class LifecycleControls(unittest.TestCase):
    def test_receipt_publication_is_exclusive_and_failed_write_is_invisible(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'receipt.json'
            life.save(path,dict(original=True))
            with self.assertRaises(FileExistsError):life.save(path,dict(replacement=True))
            self.assertEqual(json.loads(path.read_bytes()),dict(original=True))
            failed=Path(temp)/'failed.json'
            with patch.object(life.json,'dump',side_effect=OSError('injected write failure')):
                with self.assertRaises(OSError):life.save(failed,{})
            self.assertFalse(failed.exists())
            self.assertEqual(list(Path(temp).iterdir()),[path])

    def test_actual_supervise_waits_for_delayed_complete_ready_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'supervision';opened=threading.Event();release=threading.Event()
            processes=[];threads=[];errors=[];started=[];binding={};pending=[]
            real_dump=json.dump
            def paused_dump(value,stream,**kwargs):
                if 'watchdog-ready.json' in Path(stream.name).name:
                    opened.set()
                    if not release.wait(5):raise TimeoutError('test writer was not released')
                return real_dump(value,stream,**kwargs)
            def publish():
                try:life.save(folder/'watchdog-ready.json',binding)
                except BaseException as error:errors.append(error)
            class Process:
                def __init__(self,argv,**kwargs):
                    self.pid=101+len(processes);self.returncode=None;self.watch=not processes;processes.append(self)
                    if self.watch:
                        binding.update(cid=CID,nonce=argv[-1],deadline=200.,pid=self.pid)
                        thread=threading.Thread(target=publish);threads.append(thread);thread.start()
                        if not opened.wait(5):raise TimeoutError('test writer never opened')
                    else:
                        started.append(True)
                        life.save(folder/'watchdog-terminal.json',dict(cid=CID,nonce=binding['nonce'],
                            deadline=200.,failure=None,terminal=inventory()))
                def poll(self):
                    if started:self.returncode=0
                    return self.returncode
                def wait(self,timeout):
                    release.set()
                    for thread in threads:thread.join(timeout)
                    self.returncode=0;return 0
                def kill(self):self.returncode=-9
            def advance(_):
                if not started:
                    pending.append(not (folder/'watchdog-ready.json').exists())
                    release.set()
                    for thread in threads:thread.join(5)
            def observe(*args,**kwargs):return inventory() if started else inventory('created')
            try:
                with patch.object(life.json,'dump',side_effect=paused_dump),patch.object(life,'inspect',side_effect=observe), \
                        patch.object(life,'stop_owned',return_value=[dict(stopped=True)]), \
                        patch.object(life.subprocess,'Popen',side_effect=Process),patch.object(life.time,'sleep',side_effect=advance), \
                        patch.object(life.time,'monotonic',return_value=100.):
                    self.assertEqual(life.supervise(CID,folder,200.),inventory())
            finally:
                release.set()
                for thread in threads:thread.join(5)
            self.assertEqual(pending,[True]);self.assertEqual(errors,[])
            self.assertTrue(started);self.assertTrue(all(p.returncode==0 for p in processes))
            self.assertEqual(json.loads((folder/'watchdog-ready.json').read_bytes()),binding)

    def test_strict_independent_state_rejects_ambiguity(self):
        for value in (dict(inventory(),Id='b'*64),dict(inventory(),RestartCount=True),dict(inventory(),RestartCount=1),
                inventory(Pid=True),inventory(Pid=8),inventory(Running=0),inventory(Paused=True),
                inventory(Restarting=True),inventory(Dead=True),inventory(ExitCode=False),inventory(OOMKilled=0),
                inventory('running',Pid=0),inventory('paused')):
            with self.subTest(value=value),self.assertRaises(ValueError):life.checked_state(value,CID)
        self.assertTrue(life.stopped(life.checked_state(inventory('dead'),CID)))
        self.assertFalse(life.stopped(life.checked_state(inventory('running'),CID)))

    def test_bounded_command_denies_late_return_and_passes_timeout(self):
        run=Mock(return_value=subprocess.CompletedProcess([],0,b'',b''))
        with patch.object(life.subprocess,'run',run),patch.object(life.time,'monotonic',side_effect=[10,11,21]):
            with self.assertRaises(TimeoutError):life.command(['non-executed-double'],deadline=20,cap=30)
        self.assertEqual(run.call_args.kwargs['timeout'],9)

    def test_stop_failure_requires_observed_pid_zero_even_when_commands_fail(self):
        failed=subprocess.CompletedProcess([],1,b'',b'failure')
        with patch.object(life,'command',return_value=failed) as run,patch.object(life,'inspect',side_effect=[ValueError('malformed'),inventory()]):
            events=life.stop_owned(CID)
        self.assertEqual(run.call_count,2);self.assertIn('observed',events[-1])
        with patch.object(life,'command',side_effect=TimeoutError('unavailable')),patch.object(life,'inspect',side_effect=ValueError('malformed')):
            with self.assertRaises(life.StopUnconfirmed):life.stop_owned(CID)

    def test_receipts_reject_foreign_stale_missing_and_contradictory_terminal(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'receipt.json';valid=dict(cid=CID,nonce='original',deadline=200.,failure=None,terminal=inventory())
            for changes in (dict(cid='b'*64),dict(nonce='old'),dict(deadline=199.),dict(failure='deadline'),dict(terminal=inventory('created'))):
                path.write_text(json.dumps(dict(valid,**changes)))
                with self.subTest(changes=changes),self.assertRaises(ValueError):life.receipt(path,CID,'original',200.)
            path.write_text(json.dumps(valid))
            with self.assertRaises(ValueError):life.receipt(path,CID,'original',200.,inventory(ExitCode=3))
            path.unlink()
            with self.assertRaises(FileNotFoundError):life.receipt(path,CID,'original',200.)

    def supervise_double(self, order, fault=None):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'supervision';processes=[];started=[False];binding={}
            class Process:
                def __init__(self,argv,**kwargs):
                    self.pid=101+len(processes);self.returncode=None;self.watch=len(processes)==0;processes.append(self)
                    if self.watch:
                        binding.update(cid=CID,nonce=argv[-1],deadline=200.,pid=self.pid)
                        if fault!='arm-timeout':life.save(folder/'watchdog-ready.json',binding)
                    else:
                        started[0]=True
                        if fault!='missing':life.save(folder/'watchdog-terminal.json',dict(cid=CID,nonce='foreign' if fault=='foreign' else binding['nonce'],
                            deadline=200.,failure=None,terminal=inventory(ExitCode=1 if fault=='nonzero' else 0)))
                def poll(self):
                    if fault=='arm-exit' and self.watch:self.returncode=1
                    elif started[0] and ((order=='watch' and self.watch) or (order=='attach' and not self.watch)):self.returncode=0
                    return self.returncode
                def wait(self,timeout):self.returncode=0;return 0
                def kill(self):self.returncode=-9
            def observe(*args,**kwargs):return inventory(ExitCode=1 if fault=='nonzero' else 0) if started[0] else inventory('created')
            ticks=iter([100.]*8+[206.]*50) if fault=='arm-timeout' else None
            with patch.object(life,'inspect',side_effect=observe),patch.object(life,'stop_owned',return_value=[dict(stopped=True)]) as stop, \
                    patch.object(life.subprocess,'Popen',side_effect=Process),patch.object(life.time,'sleep'), \
                    patch.object(life.time,'monotonic',side_effect=(lambda:next(ticks)) if ticks else lambda:100.):
                if fault:
                    with self.assertRaises(RuntimeError):life.supervise(CID,folder,200.)
                    self.assertTrue(stop.called)
                else:self.assertEqual(life.supervise(CID,folder,200.),inventory())
            result=json.loads((folder/'supervision.json').read_bytes())
            self.assertTrue(all(p.returncode is not None for p in processes))
            if fault in ('arm-timeout','arm-exit'):self.assertFalse(started[0])
            self.assertEqual(result['failure'] is None,not bool(fault))

    def test_both_completion_orders_and_guarded_arm_terminal_failures(self):
        for order in ('watch','attach'):
            for fault in (None,'arm-exit','arm-timeout','missing','foreign','nonzero'):
                with self.subTest(order=order,fault=fault):self.supervise_double(order,fault)

    def test_watchdog_launch_error_and_unobservable_final_state_retains_primary(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(life,'inspect',side_effect=[inventory('created'),ValueError('daemon unavailable')]), \
                patch.object(life.subprocess,'Popen',side_effect=OSError('launch failed')),patch.object(life,'stop_owned',side_effect=life.StopUnconfirmed('cleanup unavailable')):
            folder=Path(temp)/'supervision'
            with self.assertRaises(life.StopUnconfirmed):life.supervise(CID,folder,life.time.monotonic()+30)
            result=json.loads((folder/'supervision.json').read_bytes())
            self.assertIn('launch failed',result['failure']);self.assertIn('stop_error',result['cleanup'][0])


class DispatcherControls(unittest.TestCase):
    def test_one_shot_reservation_exact_claim_and_late_response(self):
        for fault in (None,'claim-mismatch','late-ingest','stop-unconfirmed','token-error'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);path=root/'deployment.json';calls=[];clock=[100.];created=[]
                product=make_cohort_input(qualified_input().cohort,'analysis-'+'1'*32).model_dump(mode='json')
                selection=dict(owner='alice',job=product['attempt_id'],key='original',submission={})
                proof=dict(attempt_id=product['attempt_id'],owner_id='alice',submission={},receipt=dict(key='original'),
                    input=product,input_sha256=dispatcher.sha(product))
                (root/'queued.json').write_text(json.dumps(proof))
                image='sha256:'+'1'*64;source='2'*40
                state=dict(service_cid=CID,service_container='remission-cohort-day14-http-261022',service_image='sha256:'+'3'*64,
                    service_deadline_unix=20000,prefix='remission-cohort-day14-job-261022',learner_image=image,source_commit=source,
                    cohort_reviewed_runtime=dict(learner_image=image,source_commit=source),queued_export_path='queued.json',
                    expected=dict(selection=selection,export_sha256=dispatcher.sha(proof)))
                def command(argv,**kwargs):
                    calls.append(argv)
                    self.assertTrue((root/'analysis-jobs'/product['attempt_id']/'reservation.json').is_file())
                    response=b''
                    if argv[:2]==['docker','inspect']:response=json.dumps(dict(Name='/'+state['service_container'],Image=state['service_image'])).encode()
                    elif argv[:3]==['docker','image','inspect']:response=image.encode()
                    elif argv[:2]==['docker','create']:
                        created.append(('c' if not created else 'd')*64);response=created[-1].encode()
                    elif argv[:2]==['docker','cp'] and argv[-1].endswith('output'):Path(argv[-1]).mkdir()
                    elif argv[:2]==['docker','exec'] and 'services.foundation.analysis_cli' in argv:
                        op=argv[6]
                        if op=='queued-request':response=json.dumps(proof).encode()
                        elif op=='claim':response=json.dumps(dict(attempt_id='foreign' if fault=='claim-mismatch' else product['attempt_id'],input=product,claim_token='f'*48)).encode()
                        elif op=='bind-execution':
                            if fault=='token-error':raise RuntimeError('injected '+'f'*48)
                            response=json.dumps(dict(input_sha256=proof['input_sha256'],learner_image=image,source_commit=source)).encode()
                        elif op=='ingest':
                            if fault=='late-ingest':clock[0]=7300.
                            response=json.dumps(dict(id=product['attempt_id'],status='completed')).encode()
                        else:response=b'null'
                    return subprocess.CompletedProcess(argv,0,response,b'')
                def supervised(cid,*args):
                    if fault=='stop-unconfirmed':raise life.StopUnconfirmed('structural unknown stop')
                    return inventory()
                with patch.object(dispatcher,'command',side_effect=command),patch.object(dispatcher,'inspect',return_value=inventory('running')), \
                        patch.object(dispatcher,'supervise',side_effect=supervised),patch.object(dispatcher,'stop_owned',return_value=[]), \
                        patch.object(dispatcher,'exclusive',return_value=Mock()),patch.object(dispatcher.time,'monotonic',side_effect=lambda:clock[0]), \
                        patch.object(dispatcher.time,'time',return_value=1000.):
                    if fault:
                        try:dispatcher.run_once(state,path,'digest')
                        except (RuntimeError,TimeoutError):self.assertNotIn('f'*48,traceback.format_exc())
                        else:self.fail('fault must deny completion')
                    else:self.assertEqual(dispatcher.run_once(state,path,'digest')['status'],'completed')
                    before=len(calls)
                    with self.assertRaises(FileExistsError):dispatcher.run_once(state,path,'digest')
                    self.assertEqual(len(calls),before)
                result=json.loads((root/'analysis-jobs'/product['attempt_id']/'dispatch.json').read_bytes())
                self.assertEqual(result['status'],'STOP UNCONFIRMED' if fault=='stop-unconfirmed' else 'failed' if fault else 'completed')
                self.assertFalse(any(a[:2]==['docker','run'] or 'interrupt' in a or a[:2]==['docker','rm'] for a in calls))
                if fault=='claim-mismatch':self.assertFalse(created)
                if fault=='stop-unconfirmed':self.assertFalse(any('fail' in a for a in calls))
                self.assertNotIn('f'*48,json.dumps(result))

    def test_missing_mismatched_runtime_pair_denied(self):
        image='sha256:'+'1'*64;source='2'*40
        for pair in (None,{},dict(learner_image=image),dict(learner_image=image,source_commit=source,extra=1),
                dict(learner_image='sha256:'+'3'*64,source_commit=source)):
            with self.subTest(pair=pair),self.assertRaises(ValueError):dispatcher.cohort_reviewed_runtime(dict(source_commit=source,cohort_reviewed_runtime=pair),image)

    def test_namespace_inventory_failure_is_not_absence(self):
        with patch.object(dispatcher,'command',side_effect=TimeoutError('daemon unavailable')):
            with self.assertRaises(TimeoutError):dispatcher.absent(['non-executed'],deadline=200)
        with patch.object(dispatcher,'command',return_value=subprocess.CompletedProcess([],0,b'existing-cid',b'')):
            with self.assertRaises(RuntimeError):dispatcher.absent(['non-executed'],deadline=200)


if __name__=='__main__':unittest.main()
