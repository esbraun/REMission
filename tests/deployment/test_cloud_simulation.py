"""Host-safe packaging/guard checks; no service/numerical imports or Docker calls."""
from contextlib import contextmanager
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CLOUD = ROOT / 'tooling/foundation/cloud'
sys.path.insert(0, str(CLOUD))
import prepare
import disk_guard
import admin


def configuration():
    return dict(service_image='registry.invalid/remission/app@sha256:' + '1' * 64,
                generator_image='registry.invalid/remission/generator@sha256:' + '2' * 64,
                proxy_image='registry.invalid/caddy@sha256:' + '3' * 64,
                source_commit='4' * 40, hostname='simulation.example.org',
                disk_device='/dev/disk/by-id/google-remission-data',
                disk_uuid='12345678-1234-1234-1234-123456789abc')


class DeploymentTests(unittest.TestCase):
    def test_minimal_build_preserves_full_scientific_default(self):
        sys.path.insert(0, str(ROOT / 'tooling/foundation'))
        spec = importlib.util.spec_from_file_location('build_live', ROOT / 'tooling/foundation/build_live.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual([r[0] for r in module.build_targets(True)], ['service', 'generator'])
        self.assertEqual({r[0] for r in module.build_targets()}, {'service', 'tests', 'learner', 'evaluator', 'generator'})

    def test_private_single_writer_https_and_durable_layout(self):
        stack = prepare.compose(configuration())
        services = stack['services']
        self.assertEqual(set(services), {'app', 'generator', 'proxy'})
        self.assertTrue(stack['networks']['private']['internal'])
        for name in ('app', 'generator'):
            self.assertNotIn('ports', services[name])
            self.assertEqual(services[name]['networks'], ['private'])
        self.assertEqual(services['proxy']['ports'], ['80:80', '443:443'])
        app = services['app']
        self.assertEqual(app['environment']['REMISSION_ORIGIN'], 'https://simulation.example.org')
        self.assertEqual(app['environment']['REMISSION_GENERATOR_URL'], 'http://generator:8780')
        self.assertNotIn('REMISSION_ARCHIVE_CONFIG', app['environment'])
        self.assertEqual({v['target'] for v in app['volumes']}, {'/data', '/fixtures', '/exports'})
        self.assertTrue(next(v for v in app['volumes'] if v['target'] == '/fixtures')['read_only'])
        for service in services.values():
            self.assertEqual(service['restart'], 'on-failure:5')
            for volume in service.get('volumes', []):
                self.assertFalse(volume['bind']['create_host_path'])
        unit = (CLOUD / 'remission-simulation.service').read_text()
        self.assertIn('BindsTo=srv-remission.mount', unit)
        self.assertIn('ExecStartPre=/usr/bin/python3 /opt/remission-simulation/disk_guard.py', unit)
        self.assertIn('--scale app=1', unit)

    def test_rejects_mutable_images_injected_origins_and_unknown_secret_keys(self):
        for key, value in [('service_image', 'app:latest'), ('generator_image', 'sha256:' + 'a' * 64),
                           ('hostname', 'localhost'), ('hostname', 'x.example.org; echo bad'),
                           ('hostname', '127.0.0.1'), ('disk_uuid', ''),
                           ('disk_device', '/dev/sdb'), ('password', 'do-not-accept')]:
            config = configuration()
            config[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                prepare.compose(config)

    def test_render_binds_admin_and_all_config_bytes_without_executing_children(self):
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.run', side_effect=AssertionError('no children')):
            target = Path(directory) / 'rendered'
            hashes = prepare.render(configuration(), target)
            self.assertIn('admin.py', hashes)
            self.assertIn('srv-remission.mount', hashes)
            self.assertEqual(hashes, json.loads((target / 'manifest.json').read_bytes()))
            for name, expected in hashes.items():
                self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(), expected)
                self.assertNotIn(b'\r', (target / name).read_bytes(), 'Linux assets must render with LF on Windows too')
            prepare.verify_rendered(target)
            self.assertEqual(json.loads((target / 'compose.json').read_bytes()), prepare.compose(configuration()))
            (target / 'admin.py').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'hash_mismatch'):
                prepare.verify_rendered(target)


class DiskGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.mount = Path(self.temp.name)
        for name in ('data', 'bootstrap', 'exports', 'proxy-data', 'proxy-config'):
            (self.mount / name).mkdir()
        for name in ('data/remission.sqlite', 'data/remission.sqlite.admission.lock',
                     'bootstrap/bundle.json', 'bootstrap/runtime.json', 'bootstrap/simulation.json'):
            (self.mount / name).write_bytes(b'synthetic-test-bytes')
        hashes = ''.join(hashlib.sha256((self.mount / 'bootstrap' / n).read_bytes()).hexdigest() + '  ' + n + '\n'
                         for n in ('bundle.json', 'runtime.json', 'simulation.json'))
        (self.mount / 'bootstrap/bootstrap.sha256').write_text(hashes)
        self.config = configuration()

    def probe(self, *command):
        if command[:3] == ('blkid', '-s', 'TYPE'):
            return 'ext4'
        if 'SOURCE' in command:
            return self.config['disk_device']
        return self.config['disk_uuid']

    def check(self, probe=None):
        with patch.object(disk_guard, 'block_device', return_value=True), patch.object(disk_guard, 'output', side_effect=probe or self.probe):
            disk_guard.check(self.config, self.mount)

    def test_accepts_identified_mount_and_unchanged_bootstrap(self):
        self.check()

    def test_missing_disk_wrong_mount_and_wrong_device_fail_before_any_reseed(self):
        with patch.object(disk_guard, 'block_device', return_value=False), self.assertRaisesRegex(RuntimeError, 'missing'):
            disk_guard.check(self.config, self.mount)
        for bad in ('wrong-uuid', '/dev/other'):
            def probe(*command):
                return bad if command[0] == 'findmnt' else self.probe(*command)
            with self.subTest(bad=bad), self.assertRaisesRegex(RuntimeError, 'not_mounted'):
                self.check(probe)
        self.assertEqual((self.mount / 'data/remission.sqlite').read_bytes(), b'synthetic-test-bytes')

    def test_missing_database_or_mutated_bundle_fails_without_creating_state(self):
        database = self.mount / 'data/remission.sqlite'
        database.unlink()
        with self.assertRaisesRegex(RuntimeError, 'artifact_missing'):
            self.check()
        self.assertFalse(database.exists())
        database.write_bytes(b'synthetic-test-bytes')
        (self.mount / 'bootstrap/bundle.json').write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'checksum_mismatch'):
            self.check()


class AccountInputTests(unittest.TestCase):
    def test_password_pipe_rejects_fixture_or_short_passwords_and_never_echoes(self):
        for password in ('short', 'Synthetic-Alice-2026!', 'Synthetic-Bob-2026!'):
            with patch.object(sys, 'stdin', io.StringIO(password + '\n')), self.assertRaises(ValueError):
                admin.read_password(True)
        value = 'unique-isolated-test-secret'
        with patch.object(sys, 'stdin', io.StringIO(value + '\n')), patch.object(sys, 'stdout', io.StringIO()) as stdout:
            self.assertEqual(admin.read_password(True), value)
            self.assertEqual(stdout.getvalue(), '')

    def test_new_account_is_hashed_and_duplicate_does_not_reset(self):
        # Pure SQLite seam only; actual Argon2/auth/reset proof remains Linux runtime work.
        class Store:
            def __init__(self):
                self.db = sqlite3.connect(':memory:')
                self.db.execute('CREATE TABLE accounts(id TEXT,username TEXT UNIQUE,display_name TEXT,password_hash TEXT)')
            @contextmanager
            def transaction(self, write=False):
                with self.db:
                    yield self.db
        class Hasher:
            def hash(self, value):
                return 'test-hash-output'
        store = Store()
        self.addCleanup(store.db.close)
        admin.create_account(store, 'physician-one', 'Synthetic physician one', 'test-secret', Hasher())
        self.assertEqual(store.db.execute('SELECT username,password_hash FROM accounts').fetchall(),
                         [('physician-one', 'test-hash-output')])
        with self.assertRaisesRegex(ValueError, 'account_exists'):
            admin.create_account(store, 'physician-one', 'Other', 'new-secret', Hasher())
        self.assertEqual(store.db.execute('SELECT count(*) FROM accounts').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
