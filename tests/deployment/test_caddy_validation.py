"""Targeted host-only selected-output and authorization parsers; no Docker."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_caddy', ROOT / 'tooling/foundation/validate_caddy.py')
caddy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(caddy)


class CaddyValidationTests(unittest.TestCase):
    def test_selected_image_requires_digest_platform_without_optional_config(self):
        value = dict(Id='sha256:' + 'a' * 64, Os='linux', Architecture='amd64',
                     RepoDigests=[caddy.IMAGE.removeprefix('docker.io/library/')])
        self.assertEqual(caddy.image_identity(value), value['Id'])
        for key, bad in [('RepoDigests', []), ('Architecture', 'arm64'), ('Id', 'latest')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                caddy.image_identity(dict(value, **{key: bad}))

    def test_prestart_rejects_resource_volume_command_and_state_drift(self):
        cid = 'a' * 64; image = 'sha256:' + 'b' * 64; name = 'remission-caddy-123456789abc'
        value = dict(Id=cid, Image=image, User='0:0',
            Labels={'remission.task': name, 'org.opencontainers.image.title': 'Caddy'},
            Healthcheck={'Test': ['NONE']}, Path='/bin/sh', Args=['-ec', caddy.WORK], RestartCount=0,
            State=dict(Status='created', Running=False, Paused=False, Restarting=False, Dead=False,
                       OOMKilled=False, Pid=0, ExitCode=0),
            Memory=134217728, MemorySwap=134217728, NanoCpus=500000000, PidsLimit=64,
            ReadonlyRootfs=True, Privileged=False, CapAdd=['NET_BIND_SERVICE'], CapDrop=['ALL'], AutoRemove=False,
            PublishAllPorts=False, SecurityOpt=['no-new-privileges'], Tmpfs=caddy.TMPFS,
            NetworkMode='none', PortBindings={}, RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0},
            Mounts=[dict(Source=str(caddy.INPUTS / (case + '.Caddyfile')),
                         Destination='/inputs/' + case + '.Caddyfile', Type='bind', RW=False)
                    for case in ('ipv4', 'dns')])
        caddy.audit(value, cid, image, name)
        mutations = [('MemorySwap', 268435456), ('NetworkMode', 'bridge'), ('PidsLimit', True),
                     ('Args', ['-ec', 'caddy run']), ('RestartCount', 1), ('Labels', {}),
                     ('User', '65532:65532'), ('User', ''), ('CapAdd', None), ('CapAdd', []),
                     ('CapAdd', ['NET_BIND_SERVICE', 'SYS_ADMIN']), ('CapAdd', ['SETFCAP']),
                     ('CapAdd', ['NET_BIND_SERVICE', 'NET_BIND_SERVICE']), ('CapDrop', []),
                     ('SecurityOpt', []), ('Privileged', True),
                     ('Mounts', value['Mounts'] + [dict(Source='/var/lib/docker/volumes/x',
                          Destination='/data', Type='volume', RW=True)])]
        for key, bad in mutations:
            with self.subTest(key=key), self.assertRaises(ValueError):
                caddy.audit(dict(copy.deepcopy(value), **{key: bad}), cid, image, name)

    def test_workload_requires_exact_capabilities_identity_version_and_both_configs(self):
        expected = ['/usr/bin/caddy cap_net_bind_service=ep', 'Uid: 0 0 0 0', 'Gid: 0 0 0 0',
                    'CapPrm: 0000000000000400', 'CapEff: 0000000000000400',
                    'CapBnd: 0000000000000400', 'NoNewPrivs: 1', 'v2.11.7 fixture',
                    'REMISSION_IPV4_VALIDATED', 'REMISSION_DNS_VALIDATED']
        caddy.check_output(expected)
        for index, bad in [(0, '/usr/bin/caddy cap_net_bind_service,cap_setfcap=ep'),
                           (0, '/usr/bin/caddy cap_net_bind_service=p'), (1, 'Uid: 65532 65532 65532 65532'),
                           (2, 'Gid: 0 0 0 1'), (3, 'CapPrm: 0000000000000000'),
                           (4, 'CapEff: 0000000000000401'), (5, 'CapBnd: 0000000000000000'),
                           (6, 'NoNewPrivs: 0'), (7, 'v2.11.6'), (8, ''), (9, '')]:
            with self.subTest(index=index, bad=bad), self.assertRaises(ValueError):
                value = expected.copy(); value[index] = bad; caddy.check_output(value)
        for value in (expected[:-1], expected + ['unexpected'], expected[7:]):
            with self.assertRaises(ValueError): caddy.check_output(value)
        argv = caddy.create('remission-caddy-123456789abc')
        self.assertEqual(argv[argv.index('--cap-add') + 1], 'NET_BIND_SERVICE')
        self.assertEqual(argv.count('--cap-add'), 1)
        self.assertEqual(argv[argv.index('--user') + 1], '0:0')
        self.assertEqual(argv[-1], caddy.WORK)
        self.assertLess(caddy.WORK.index('getcap /usr/bin/caddy'), caddy.WORK.index('caddy version'))
        self.assertIn("' /proc/$$/status\n", caddy.WORK)

    def test_authorization_binds_raw_plan_and_rejects_boolean_integer_confusion(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); path = folder / 'plan.json'; auth = folder / 'authorization.json'
            caddy.life.save(path, caddy.plan('remission-caddy-123456789abc', folder))
            value = dict(authorized=True, scope='one-offline-caddy-validation',
                         plan_sha256=caddy.sha(path.read_bytes()), attempts=1, retain_resources=True,
                         image_pull=False, network=False, cloud=False)
            auth.write_text(json.dumps(value))
            caddy.authorized(path, auth)
            for key, bad in [('authorized', 1), ('attempts', True), ('plan_sha256', '0' * 64), ('image_pull', True)]:
                auth.write_text(json.dumps(dict(value, **{key: bad})))
                with self.subTest(key=key), self.assertRaises(ValueError): caddy.authorized(path, auth)
            original = json.loads(path.read_bytes())
            for field in ('create_argv', 'capability_stdout'):
                changed = copy.deepcopy(original)
                if field == 'create_argv':
                    changed[field][changed[field].index('--cap-add') + 1] = 'SYS_ADMIN'
                else: changed[field][0] = '/usr/bin/caddy cap_net_bind_service=p'
                path.write_text(json.dumps(changed))
                auth.write_text(json.dumps(dict(value, plan_sha256=caddy.sha(path.read_bytes()))))
                with self.subTest(field=field), self.assertRaises(ValueError): caddy.authorized(path, auth)

    def test_acquisition_authorization_binds_launcher_evidence_plan_and_types(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve(); path = folder / 'plan.json'
            auth = folder / 'acquisition-authorization.json'
            frozen = caddy.plan('remission-caddy-123456789abc', folder)
            caddy.life.save(path, frozen)
            value = dict(authorized=True, scope='one-caddy-image-acquisition',
                         plan_sha256=caddy.sha(path.read_bytes()),
                         launcher_sha256=caddy.sha(Path(caddy.__file__).read_bytes()),
                         evidence=str(folder / 'acquisition'), attempts=1,
                         timeout_seconds=120, external_seconds=140, cloud=False)
            auth.write_text(json.dumps(value))
            caddy.acquisition_authorized(path, auth)
            self.assertEqual(frozen['acquisition_proposal']['launcher_argv'],
                             caddy.acquisition_argv(folder, '--acquire'))
            for key, bad in [('attempts', True), ('timeout_seconds', 120.0),
                             ('launcher_sha256', '0' * 64), ('plan_sha256', '0' * 64),
                             ('evidence', str(folder)), ('cloud', True)]:
                auth.write_text(json.dumps(dict(value, **{key: bad})))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    caddy.acquisition_authorized(path, auth)
            auth.write_text(json.dumps(value))
            for field in ('source_commit', 'physical_sources', 'acquisition_proposal'):
                changed = copy.deepcopy(frozen)
                if field == 'acquisition_proposal': changed[field]['argv'][-1] = 'caddy:latest'
                elif field == 'physical_sources': changed[field][str(Path(caddy.__file__).resolve())] = '0' * 64
                else: changed[field] = '0' * 40
                path.write_text(json.dumps(changed))
                value['plan_sha256'] = caddy.sha(path.read_bytes()); auth.write_text(json.dumps(value))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    caddy.acquisition_authorized(path, auth)

    def acquisition_fixture(self, folder):
        return dict(acquisition_proposal=dict(evidence=str(folder / 'acquisition'),
            argv=['docker', 'pull', '--platform', 'linux/amd64', caddy.IMAGE],
            worker_argv=caddy.acquisition_argv(folder, '--acquisition-worker')))

    def test_one_pull_reservation_retains_literal_receipts_and_streams(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); frozen = self.acquisition_fixture(folder)
            child = Mock(pid=123, returncode=0); child.wait.return_value = 0
            def spawn(argv, **kwargs):
                kwargs['stdout'].write(b'pulled\n'); kwargs['stderr'].write(b'progress\n')
                return child
            with patch.object(caddy, 'acquisition_authorized', return_value=frozen), \
                    patch.object(caddy.subprocess, 'Popen', side_effect=spawn) as popen:
                caddy.acquire_worker(folder / 'plan.json', folder / 'unused-fixture')
                with self.assertRaises(FileExistsError):
                    caddy.acquire_worker(folder / 'plan.json', folder / 'unused-fixture')
            self.assertEqual(popen.call_count, 1)
            attempt = folder / 'acquisition/attempt'
            receipt = json.loads((attempt / 'terminal.json').read_bytes())
            self.assertEqual((receipt['pid'], receipt['argv'], receipt['returncode']),
                             (123, frozen['acquisition_proposal']['argv'], 0))
            self.assertIs(receipt['reaped'], True); self.assertIsNone(receipt['failure'])
            self.assertEqual((attempt / 'stdout').read_bytes(), b'pulled\n')
            self.assertEqual((attempt / 'stderr').read_bytes(), b'progress\n')
            self.assertLessEqual(child.wait.call_args_list[0].kwargs['timeout'], 120)
            self.assertGreater(child.wait.call_args_list[0].kwargs['timeout'], 119)

    def test_pull_deadline_kills_reaps_but_never_claims_daemon_stopped(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); frozen = self.acquisition_fixture(folder)
            child = Mock(pid=124, returncode=None); child.poll.return_value = None
            child.wait.side_effect = [caddy.subprocess.TimeoutExpired('fixture', 120), -9]
            def kill(): child.returncode = -9
            child.kill.side_effect = kill
            with patch.object(caddy, 'acquisition_authorized', return_value=frozen), \
                    patch.object(caddy.subprocess, 'Popen', return_value=child) as popen:
                with self.assertRaisesRegex(RuntimeError, 'STOP UNCONFIRMED: daemon pull may continue'):
                    caddy.acquire_worker(folder / 'plan.json', folder / 'unused-fixture')
            self.assertEqual(popen.call_count, 1); child.kill.assert_called_once_with()
            receipt = json.loads((folder / 'acquisition/attempt/terminal.json').read_bytes())
            self.assertTrue(receipt['reaped']); self.assertTrue(receipt['kill_requested'])
            self.assertFalse(receipt['daemon_stop_confirmed']); self.assertEqual(receipt['returncode'], -9)
            self.assertEqual(child.wait.call_args_list[1].kwargs['timeout'], 2)

    def test_reap_failure_retains_uncertain_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); frozen = self.acquisition_fixture(folder)
            child = Mock(pid=125, returncode=None); child.poll.return_value = None
            child.wait.side_effect = caddy.subprocess.TimeoutExpired('fixture', 120)
            with patch.object(caddy, 'acquisition_authorized', return_value=frozen), \
                    patch.object(caddy.subprocess, 'Popen', return_value=child):
                with self.assertRaisesRegex(RuntimeError, 'reap'):
                    caddy.acquire_worker(folder / 'plan.json', folder / 'unused-fixture')
            receipt = json.loads((folder / 'acquisition/attempt/terminal.json').read_bytes())
            self.assertIs(receipt['reaped'], False)
            self.assertIn('STOP UNCONFIRMED', receipt['failure'])

    def test_external_bound_reserves_once_and_retains_failed_reap(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); frozen = self.acquisition_fixture(folder)
            child = Mock(pid=126, returncode=None)
            child.wait.side_effect = caddy.subprocess.TimeoutExpired('fixture', 136)
            with patch.object(caddy, 'acquisition_authorized', return_value=frozen), \
                    patch.object(caddy.subprocess, 'Popen', return_value=child) as popen:
                with self.assertRaisesRegex(RuntimeError, 'daemon pull may continue; no retry'):
                    caddy.launch(folder / 'plan.json', folder / 'unused-fixture', acquisition=True)
                with self.assertRaises(FileExistsError):
                    caddy.launch(folder / 'plan.json', folder / 'unused-fixture', acquisition=True)
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(popen.call_args.args[0], frozen['acquisition_proposal']['worker_argv'])
            waits = [call.kwargs['timeout'] for call in child.wait.call_args_list]
            self.assertLessEqual(waits[0], 136); self.assertGreater(waits[0], 135)
            self.assertEqual(waits[1:], [2, 2]); child.kill.assert_called_once_with()
            receipt = json.loads((folder / 'acquisition/launch/terminal.json').read_bytes())
            self.assertFalse(receipt['reaped']); self.assertIn('reap', receipt['failure'])

    def test_external_success_requires_pull_client_receipt(self):
        for reaped in (True, False):
            with self.subTest(reaped=reaped), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); frozen = self.acquisition_fixture(folder)
                attempt = folder / 'acquisition/attempt'; attempt.mkdir(parents=True)
                caddy.life.save(attempt / 'terminal.json', dict(pid=127, returncode=0,
                    argv=frozen['acquisition_proposal']['argv'], reaped=reaped, failure=None))
                child = Mock(pid=128, returncode=0); child.wait.return_value = 0
                with patch.object(caddy, 'acquisition_authorized', return_value=frozen), \
                        patch.object(caddy.subprocess, 'Popen', return_value=child):
                    if reaped: caddy.launch(folder / 'plan.json', folder / 'unused-fixture', acquisition=True)
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'success/reap receipt missing'):
                            caddy.launch(folder / 'plan.json', folder / 'unused-fixture', acquisition=True)


if __name__ == '__main__': unittest.main()
