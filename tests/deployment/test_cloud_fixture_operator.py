"""Stdlib host doubles for CS1 supervision; never invoke Docker or app imports."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tooling/foundation'))
import run_cloud_fixture as operator

CID = 'a' * 64
NETWORK = 'b' * 64


def state(status='created', code=0):
    return dict(Id=CID, RestartCount=0, State=dict(Status=status, Running=status == 'running',
        Paused=False, Restarting=False, Dead=False, OOMKilled=False,
        Pid=123 if status == 'running' else 0, ExitCode=code))


def plan():
    closures = json.loads((ROOT / 'docs/implementation/evidence/cloud-simulation-prep-20261023/image-closures.json').read_bytes())
    return dict(prefix='remission-cloud-fixture-123456789abc', source_commit='c' * 40,
                cloud_source='C:\\reviewed\\cloud', fixture_source='C:\\reviewed\\fixture.py', closures=closures)


class FixtureOperatorTests(unittest.TestCase):
    def test_prestart_rejects_swap_privilege_mount_network_and_command_drift(self):
        p = plan()
        # An independent selected-field Docker observation, including a Desktop
        # translated source path and an explicitly reported tmpfs mount.
        value = dict(state(), Image=operator.IMAGES['fixture'], User='10001:10001',
            Labels={'remission.task': p['prefix']}, Memory=2147483648, MemorySwap=2147483648,
            NanoCpus=2000000000, PidsLimit=256, ReadonlyRootfs=True, CapDrop=['ALL'],
            Privileged=False, CapAdd=None, AutoRemove=False, PublishAllPorts=False,
            SecurityOpt=['no-new-privileges'], Tmpfs={'/tmp': 'rw,noexec,nosuid,size=256m'},
            NetworkMode=p['prefix'] + '-private', RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0},
            Path='python', Args=operator.workload('fixture', p['closures']['fixture'])[1:], PortBindings={},
            Mounts=[dict(Source='/run/desktop/mnt/host/c/reviewed/cloud', Destination='/deployment', Type='bind', RW=False),
                    dict(Source='/run/desktop/mnt/host/c/reviewed/fixture.py', Destination='/qualification/linux_simulation_fixture.py', Type='bind', RW=False),
                    dict(Source='', Destination='/tmp', Type='tmpfs', RW=True)],
            Networks={p['prefix'] + '-private': {'NetworkID': NETWORK}})
        operator.audit_container(value, CID, p, 'fixture', NETWORK)
        pending = dict(value, Networks={p['prefix'] + '-private': {'NetworkID': ''}})
        operator.audit_container(pending, CID, p, 'fixture', NETWORK)
        for key, bad in [('MemorySwap', 4294967296), ('CapDrop', []), ('ReadonlyRootfs', False),
                         ('SecurityOpt', []), ('NanoCpus', 0), ('PidsLimit', 0),
                         ('PortBindings', {'8765/tcp': [{'HostPort': '8765'}]}),
                         ('Args', ['-m', 'services.foundation.server']), ('Mounts', []),
                         ('Networks', {'bridge': {'NetworkID': NETWORK}})]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                operator.audit_container(dict(value, **{key: bad}), CID, p, 'fixture', NETWORK)

    def test_no_start_when_watchdog_never_arms_or_receipt_is_foreign(self):
        for failure in ('dead', 'foreign'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                service = operator.Generator(CID, Path(directory) / 'generator', 12345)
                child = Mock(pid=99)
                child.poll.return_value = 1 if failure == 'dead' else None
                def spawn(*args, **kwargs):
                    if failure == 'foreign':
                        operator.life.save(service.folder / 'watchdog-ready.json', dict(cid='d' * 64))
                    return child
                with patch.object(operator.life, 'check_deadline'), patch.object(operator.subprocess, 'Popen', side_effect=spawn) as popen:
                    with self.assertRaises((RuntimeError, ValueError)):
                        service.start()
                    self.assertEqual(popen.call_count, 1, 'must never start without own armed watchdog')
                service.reap()

    def test_intentional_stop_accepts_both_orders_but_rejects_early_exit_and_oom(self):
        for first in ('watchdog', 'attach'):
            with self.subTest(first=first), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                service = operator.Generator(CID, folder, 12345)
                service.watch = Mock(returncode=None); service.watch.poll.return_value = None
                service.attach = Mock(returncode=None); service.attach.poll.return_value = None
                terminal = state('exited', 143)
                def stop(_cid):
                    winner = service.watch if first == 'watchdog' else service.attach
                    winner.returncode = 0 if first == 'watchdog' else 143
                    operator.life.save(folder / 'watchdog-terminal.json', dict(cid=CID, nonce=service.nonce,
                        deadline=12345, terminal=terminal, failure=None))
                    return [{'operation': 'stop', 'returncode': 0}]
                service.watch.wait.side_effect = lambda **kw: setattr(service.watch, 'returncode', 0)
                service.attach.wait.side_effect = lambda **kw: setattr(service.attach, 'returncode', 143)
                with patch.object(operator.life, 'check_deadline'), patch.object(operator.life, 'inspect', side_effect=[state('running'), terminal]), patch.object(operator.life, 'stop_owned', side_effect=stop):
                    service.finish()
                receipt = json.loads((folder / 'supervision.json').read_bytes())
                self.assertTrue(receipt['intentional_stop'])
                self.assertEqual(receipt['terminal']['State']['Pid'], 0)
                service.watch.poll.return_value = 0
                with patch.object(operator.life, 'check_deadline'), self.assertRaisesRegex(RuntimeError, 'before intentional'):
                    service.check()
        # A typed terminal receipt remains required even after an intended stop.
        with tempfile.TemporaryDirectory() as directory:
            service = operator.Generator(CID, Path(directory), 12345)
            service.watch = Mock(returncode=0); service.watch.poll.return_value = None
            service.attach = Mock(returncode=137); service.attach.poll.return_value = None
            terminal = state('exited', 137); terminal['State']['OOMKilled'] = True
            operator.life.save(service.folder / 'watchdog-terminal.json', dict(cid=CID, nonce=service.nonce,
                deadline=12345, terminal=terminal, failure=None))
            with patch.object(operator.life, 'check_deadline'), patch.object(operator.life, 'inspect', side_effect=[state('running'), terminal]), patch.object(operator.life, 'stop_owned', return_value=[]), self.assertRaisesRegex(RuntimeError, 'intentional-stop'):
                service.finish()

    def test_authorization_binds_exact_bytes_and_prevents_children(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); plan_path = folder / 'plan.json'; auth = folder / 'auth.json'
            operator.life.save(plan_path, {'attempts': 1})
            operator.life.save(auth, dict(authorized=True, scope='one-local-CS-T1-fixture',
                plan_sha256='0' * 64, attempts=1, retain_resources=True, cloud=False, training=False))
            with patch.object(operator.life, 'command', side_effect=AssertionError('authorization must precede children')):
                with self.assertRaisesRegex(ValueError, 'authorization'):
                    operator.execute(plan_path, auth)
            self.assertFalse((folder / 'attempt').exists())

    def test_failure_retains_evidence_and_cannot_claim_stop_from_client_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); p = plan(); p['physical_sources'] = {'frozen': 'bytes'}
            plan_path = folder / 'plan.json'; plan_path.write_text('{}'); auth = folder / 'auth.json'; auth.write_text('{}')
            network = dict(Id=NETWORK, Name=p['prefix'] + '-private', Internal=True, Labels={'remission.task': p['prefix']})
            responses = [dict(Id=operator.PARENT, Os='linux', Architecture='amd64'),
                dict(Id=operator.IMAGES['fixture'], Os='linux', Architecture='amd64', User='10001:10001'),
                dict(Id=operator.IMAGES['generator'], Os='linux', Architecture='amd64', User='20000:20000'),
                NETWORK, network, CID, {}]
            p['create_argv'] = {'generator': ['docker', 'create'], 'fixture': ['docker', 'create']}
            def command(argv, **kwargs):
                item = responses.pop(0)
                return SimpleNamespace(stdout=(item if isinstance(item, str) else json.dumps(item)).encode(), stderr=b'', returncode=0)
            with patch.object(operator, 'authorize', return_value=p), patch.object(operator, 'physical_sources', return_value=p['physical_sources']), patch.object(operator.life, 'command', side_effect=command), patch.object(operator, 'audit_container', side_effect=ValueError('resource mismatch')), patch.object(operator.life, 'inspect', side_effect=RuntimeError('daemon unavailable')), patch.object(operator.life, 'stop_owned', side_effect=operator.life.StopUnconfirmed('daemon unavailable')):
                with self.assertRaises(operator.life.StopUnconfirmed):
                    operator.execute(plan_path, auth)
            result = json.loads((folder / 'attempt/result.json').read_bytes())
            self.assertEqual(result['status'], 'STOP UNCONFIRMED')
            self.assertEqual(result['owned'], {'generator': CID})
            self.assertTrue(result['resources_retained'])
            self.assertIn('resource mismatch', result['failure'])
            with patch.object(operator, 'authorize', return_value=p), self.assertRaises(FileExistsError):
                operator.execute(plan_path, auth)


if __name__ == '__main__':
    unittest.main()
