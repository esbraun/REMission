"""Stdlib process/daemon doubles only: never Docker, SQLite, HTTP or secrets."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guarded_backup as op

CID = 'a' * 64
ORIGINAL = 'b' * 64
REPLACEMENT = 'c' * 64


def state(status='exited', cid=CID, code=0):
    return dict(Id=cid, RestartCount=0, State=dict(Status=status, Running=status == 'running',
        Paused=False, Restarting=False, Dead=status == 'dead', OOMKilled=False,
        Pid=99 if status == 'running' else 0, ExitCode=code))


class Controls(unittest.TestCase):
    def setUp(self):
        root = op.WORKTREE / 'artifacts/appt-genuine/lifecycle-control-doubles'
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'backup'
        self.plan = dict(database_volume='original-database', original_cid=ORIGINAL,
            retained_service='original-retained', service='original-service',
            failed_replacement='failed-replacement', old_image='sha256:' + 'd' * 64,
            private_root=str(self.root), temporary_envfile=str(self.root / 'replacement.env'),
            backup_source='print("nonoperational control")', backup_create_argv=['docker', 'create', 'frozen-backup'],
            replacement_create_argv=['docker', 'create', 'frozen-replacement'])
        # Catch every accidental real child process; command/inspect/Popen are
        # explicitly replaced only by the bounded doubles exercised below.
        self.addCleanup(patch.stopall)
        patch.object(op.subprocess, 'run', side_effect=AssertionError('real subprocess forbidden')).start()

    def prepared(self, status='exited', failure=None):
        self.folder.mkdir()
        op.life.save(self.folder / 'created.json', dict(cid=CID))
        (self.folder / 'lifecycle').mkdir()
        terminal = state(status)
        op.life.save(self.folder / 'lifecycle/supervision.json', dict(cid=CID, deadline=200,
            failure=failure, cleanup=[], returncodes={'attach': 0, 'watchdog': 0}, terminal=terminal))
        op.life.save(self.folder / 'lifecycle/watchdog-ready.json', dict(nonce='test', cid=CID, deadline=200, pid=99))
        op.life.save(self.folder / 'lifecycle/watchdog-terminal.json', dict(nonce='test', cid=CID,
            deadline=200, failure=None, terminal=terminal))
        op.life.save(self.folder / 'backup-result.json', dict(passed=True, cid=CID))
        return terminal

    def command(self, calls, consumers=b''):
        def invoke(argv, **kwargs):
            calls.append(argv)
            raw = consumers if argv[:2] == ['docker', 'ps'] else REPLACEMENT.encode() if argv[:2] == ['docker', 'create'] else b''
            return subprocess.CompletedProcess(argv, 0, raw, b'')
        return invoke

    def test_each_forward_step_requires_fresh_terminal_reaped_helper_and_empty_database(self):
        terminal = self.prepared()
        calls = []
        with patch.object(op.life, 'inspect', return_value=terminal) as inspect, patch.object(op.life, 'command', side_effect=self.command(calls)):
            for step in ('rename-original', 'create-replacement', 'start-replacement'):
                op.forward(self.plan, self.folder, step)
        self.assertEqual(inspect.call_count, 3)
        self.assertEqual([v[:2] for v in calls], [['docker', 'ps'], ['docker', 'rename'],
            ['docker', 'ps'], ['docker', 'create'], ['docker', 'ps'], ['docker', 'start']])
        self.assertEqual(calls[-1], ['docker', 'start', REPLACEMENT])
        with patch.object(op.life, 'inspect', return_value=terminal), patch.object(op.life, 'command', side_effect=self.command([])) as command:
            with self.assertRaises(FileExistsError):
                op.forward(self.plan, self.folder, 'start-replacement')
            self.assertEqual(command.call_count, 1, 'only read-only inventory before duplicate reservation denial')

    def test_live_helper_or_foreign_consumer_never_allows_forward_or_original_restart(self):
        self.prepared()
        for live in (True, False):
            with self.subTest(live=live):
                calls = []
                with patch.object(op.life, 'inspect', return_value=state('running') if live else state()), \
                        patch.object(op.life, 'command', side_effect=self.command(calls, ('e' * 64).encode())):
                    for step in ('rename-original', 'create-replacement', 'start-replacement'):
                        if step == 'create-replacement':
                            (self.folder / 'rename-original.json').write_text('{"passed":true}')
                        if step == 'start-replacement':
                            (self.folder / 'create-replacement.json').write_text(json.dumps(dict(passed=True, cid=REPLACEMENT)))
                        with self.assertRaises(op.life.StopUnconfirmed):
                            op.forward(self.plan, self.folder, step)
                self.assertTrue(all(argv[:2] == ['docker', 'ps'] for argv in calls))
        with patch.object(op.life, 'inspect', return_value=state('running')), patch.object(op.life, 'command') as command:
            with self.assertRaises(op.life.StopUnconfirmed):
                op.recover_original(self.plan, self.folder)
            command.assert_not_called()

    def test_invalid_terminal_or_unreaped_process_receipt_fails_closed(self):
        terminal = self.prepared()
        path = self.folder / 'lifecycle/supervision.json'
        original = op.load(path)
        variants = [dict(original, terminal=state('running')), dict(original, cid='e' * 64),
            dict(original, returncodes={'attach': None, 'watchdog': 0}),
            dict(original, returncodes={'attach': False, 'watchdog': 0}),
            dict(original, cleanup=[{'process': 'watchdog', 'reap_error': 'unconfirmed'}])]
        malformed = copy.deepcopy(original); malformed['terminal']['State']['Pid'] = 42; variants.append(malformed)
        for value in variants:
            with self.subTest(value=value):
                path.write_text(json.dumps(value))
                with patch.object(op.life, 'inspect', return_value=terminal), patch.object(op.life, 'command') as command:
                    with self.assertRaises((ValueError, op.life.StopUnconfirmed)):
                        op.barrier(self.plan, self.folder)
                    command.assert_not_called()

    def test_stop_unconfirmed_during_recovery_never_renames_or_restarts(self):
        terminal = self.prepared()
        op.life.save(self.folder / 'create-replacement-reserved.json', {})
        op.life.save(self.folder / 'create-replacement.json', dict(passed=True, cid=REPLACEMENT))
        calls = []
        with patch.object(op.life, 'inspect', return_value=terminal), \
                patch.object(op.life, 'command', side_effect=self.command(calls, REPLACEMENT.encode())), \
                patch.object(op.life, 'stop_owned', side_effect=op.life.StopUnconfirmed('test daemon proof unavailable')) as stop:
            with self.assertRaises(op.life.StopUnconfirmed):
                op.recover_original(self.plan, self.folder)
            stop.assert_called_once_with(REPLACEMENT)
            with self.assertRaises(op.life.StopUnconfirmed):
                op.forward(self.plan, self.folder, 'rename-original')
        self.assertTrue(all(v[:2] == ['docker', 'ps'] for v in calls))
        self.assertIn('STOP UNCONFIRMED', op.load(self.folder / 'recovery.json')['status'])

    def test_conditional_original_restart_requires_terminal_and_no_competing_consumer(self):
        terminal = self.prepared(failure='backup exited unsuccessfully but terminal observed')
        calls = []
        with patch.object(op.life, 'inspect', side_effect=lambda cid: terminal if cid == CID else state(cid=ORIGINAL)), \
                patch.object(op.life, 'command', side_effect=self.command(calls)):
            op.recover_original(self.plan, self.folder)
        self.assertEqual(calls[-1], ['docker', 'start', ORIGINAL])
        self.assertEqual(op.load(self.folder / 'recovery.json')['events'][0]['before_original_restart']['reaped_returncodes'],
                         {'attach': 0, 'watchdog': 0})

    def test_backup_uses_one_create_and_supervisor_absolute_deadline_and_retains_halt(self):
        calls = []
        def command(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, CID.encode() if argv[:2] == ['docker', 'create'] else b'{}', b'')
        with patch.object(op, 'valid_preflight', return_value={'protected_tables': {}}), \
                patch.object(op, 'no_consumers', return_value=[]), \
                patch.object(op.life, 'inspect', return_value=state(cid=ORIGINAL)), \
                patch.object(op.life, 'command', side_effect=command), patch.object(op, 'backup_audit'), \
                patch.object(op.life.time, 'monotonic', return_value=100), \
                patch.object(op.life, 'supervise', side_effect=op.life.StopUnconfirmed('test hung daemon')) as supervisor:
            with self.assertRaises(op.life.StopUnconfirmed):
                op.run_backup(self.plan, self.folder)
            supervisor.assert_called_once_with(CID, self.folder / 'lifecycle', 160)
            with self.assertRaises(op.life.StopUnconfirmed):
                op.barrier(self.plan, self.folder)
        self.assertEqual([v[0][:2] for v in calls], [['docker', 'create'], ['docker', 'inspect']])
        self.assertEqual(calls[0][1], {'deadline': 160, 'cap': 10})
        self.assertEqual(op.load(self.folder / 'created.json')['cid'], CID)
        self.assertIn('STOP UNCONFIRMED', op.load(self.folder / 'backup-failure.json')['status'])

    def test_actual_accepted_supervisor_never_starts_without_exact_prearm_ack(self):
        for fault in ('exited', 'foreign'):
            with self.subTest(fault=fault):
                folder = self.root / ('arm-' + fault)
                processes = []
                class Process:
                    def __init__(self, argv, **kwargs):
                        self.pid = 99; self.returncode = None; processes.append(self)
                        if fault == 'foreign':
                            op.life.save(folder / 'watchdog-ready.json', dict(cid='e' * 64))
                    def poll(self): return 1 if fault == 'exited' else None
                    def wait(self, timeout): self.returncode = 1; return 1
                    def kill(self): self.returncode = -9
                with patch.object(op.life, 'inspect', return_value=state('created')), \
                        patch.object(op.life, 'stop_owned', return_value=[]), \
                        patch.object(op.life.subprocess, 'Popen', side_effect=Process) as spawn:
                    with self.assertRaises(RuntimeError):
                        op.life.supervise(CID, folder, op.time.monotonic() + 20)
                self.assertEqual(spawn.call_count, 1, 'watchdog only; no attached start')
                self.assertTrue(all(p.returncode is not None for p in processes))
                self.assertIsNone(op.load(folder / 'supervision.json')['returncodes']['attach'])

    def test_actual_accepted_supervisor_bounds_hung_backup_stops_same_cid_and_reaps(self):
        folder = self.root / 'hung'
        processes = []; running = [False]; stopped = [False]; ticks = [100.0]
        class Process:
            def __init__(self, argv, **kwargs):
                self.pid = 99 + len(processes); self.returncode = None; processes.append(self)
                if len(processes) == 1:
                    op.life.save(folder / 'watchdog-ready.json', dict(cid=CID, nonce=argv[-1], deadline=101., pid=self.pid))
                else: running[0] = True
            def poll(self): return None
            def wait(self, timeout): self.returncode = 137; return 137
            def kill(self): self.returncode = -9
        def observe(*args, **kwargs):
            return state('exited', code=137) if stopped[0] else state('running' if running[0] else 'created')
        def stop(cid):
            self.assertEqual(cid, CID); stopped[0] = True; return [{'observed': state(code=137)}]
        def advance(_): ticks[0] += .6
        with patch.object(op.life, 'inspect', side_effect=observe), patch.object(op.life, 'stop_owned', side_effect=stop) as stop_call, \
                patch.object(op.life.subprocess, 'Popen', side_effect=Process), \
                patch.object(op.life.time, 'sleep', side_effect=advance), patch.object(op.life.time, 'monotonic', side_effect=lambda: ticks[0]):
            with self.assertRaisesRegex(RuntimeError, 'deadline'):
                op.life.supervise(CID, folder, 101.)
        self.assertTrue(running[0]); self.assertTrue(stop_call.called)
        self.assertTrue(all(p.returncode is not None for p in processes))
        result = op.load(folder / 'supervision.json')
        self.assertEqual(result['terminal']['State']['Pid'], 0)
        self.assertEqual(set(result['returncodes']), {'attach', 'watchdog'})
        self.assertTrue(all(type(v) is int for v in result['returncodes'].values()))

    def test_accepted_stop_kill_observation_is_bounded_and_unconfirmed_is_not_terminal(self):
        with patch.object(op.life, 'command', side_effect=TimeoutError('test client timeout')) as command, \
                patch.object(op.life, 'inspect', side_effect=ValueError('test daemon unavailable')):
            with self.assertRaises(op.life.StopUnconfirmed): op.life.stop_owned(CID)
        self.assertEqual([v.args[0] for v in command.call_args_list],
            [['docker', 'stop', '--time', '1', CID], ['docker', 'kill', CID]])
        self.assertTrue(all(v.kwargs['cap'] == 4 for v in command.call_args_list))


if __name__ == '__main__':
    unittest.main(verbosity=2)
