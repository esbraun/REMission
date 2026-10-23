"""Targeted host-only selected-output and authorization parsers; no Docker."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

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
        value = dict(Id=cid, Image=image, User='65532:65532',
            Labels={'remission.task': name, 'org.opencontainers.image.title': 'Caddy'},
            Healthcheck={'Test': ['NONE']}, Path='/bin/sh', Args=['-ec', caddy.WORK], RestartCount=0,
            State=dict(Status='created', Running=False, Paused=False, Restarting=False, Dead=False,
                       OOMKilled=False, Pid=0, ExitCode=0),
            Memory=134217728, MemorySwap=134217728, NanoCpus=500000000, PidsLimit=64,
            ReadonlyRootfs=True, Privileged=False, CapAdd=None, CapDrop=['ALL'], AutoRemove=False,
            PublishAllPorts=False, SecurityOpt=['no-new-privileges'], Tmpfs=caddy.TMPFS,
            NetworkMode='none', PortBindings={}, RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0},
            Mounts=[dict(Source=str(caddy.INPUTS / (case + '.Caddyfile')),
                         Destination='/inputs/' + case + '.Caddyfile', Type='bind', RW=False)
                    for case in ('ipv4', 'dns')])
        caddy.audit(value, cid, image, name)
        mutations = [('MemorySwap', 268435456), ('NetworkMode', 'bridge'), ('PidsLimit', True),
                     ('Args', ['-ec', 'caddy run']), ('RestartCount', 1), ('Labels', {}),
                     ('Mounts', value['Mounts'] + [dict(Source='/var/lib/docker/volumes/x',
                          Destination='/data', Type='volume', RW=True)])]
        for key, bad in mutations:
            with self.subTest(key=key), self.assertRaises(ValueError):
                caddy.audit(dict(copy.deepcopy(value), **{key: bad}), cid, image, name)

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


if __name__ == '__main__': unittest.main()
