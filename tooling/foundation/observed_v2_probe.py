"""Actual curated-role positive v2 admission and denied privileged access."""
import importlib
import json
import os
from pathlib import Path
import socket
import sys

from contracts.runs.admission import verify_export
from contracts.runs.observed_v2 import ExportAuthorityV2


def main():
    root = Path('/public-v2')
    authority = ExportAuthorityV2.model_validate_json((root / 'authority.json').read_bytes())
    assert authority.allow_contract_fixture and authority.producer.role == 'contract_fixture'
    manifest, partitions = verify_export((root / 'manifest.json').read_bytes(), root, authority)
    assert len(partitions) == 1
    assert any(r.kind == 'daily_report' and r.diary_sleep_minutes == -25.0 for r in partitions[0][1].records)
    assert all(not name.startswith('numpy') for name in sys.modules), 'public modules imported private numerical logic'
    if os.getuid() == 10001:
        from datetime import timedelta
        from tempfile import TemporaryDirectory
        from fastapi.testclient import TestClient
        from services.foundation.app import Settings, create_app
        from services.foundation.cli import DEMO_PASSWORDS, seed
        from services.foundation.store import Store
        with TemporaryDirectory() as directory:
            settings = Settings(Path(directory) / 'actual.sqlite', clock=lambda: manifest.cutoff + timedelta(days=1),
                                observed_archives={manifest.id: ((root / 'manifest.json').read_bytes(), root, authority)})
            seed(Store(settings.database))
            with TestClient(create_app(settings), base_url=settings.origin) as client:
                bootstrap = client.get('/api/session').json()
                login = client.post('/api/login', json=dict(username='alice', password=DEMO_PASSWORDS['alice']), headers={'Origin': settings.origin, 'X-CSRF-Token': bootstrap['csrf']})
                assert login.status_code == 200, login.text
                headers = {'Origin': settings.origin, 'X-CSRF-Token': client.get('/api/session').json()['csrf']}
                response = client.post('/api/observed-archives/' + manifest.id, json={'mode': 'clinical_observation_import'}, headers=headers)
                assert response.status_code == 409 and response.json()['code'] == 'independent_hold_live_integration_required', response.text
                response = client.post('/api/observed-archives/' + manifest.id, json={'mode': 'archive_only'}, headers=headers)
                assert response.status_code == 200 and response.json()['status'] == 'archived_read_only', response.text
    else:
        from tempfile import TemporaryDirectory
        from services.learner.export_observed import admit_run_export
        with TemporaryDirectory() as directory:
            admitted = admit_run_export((root / 'manifest.json').read_bytes(), root, Path(directory), authority)
            assert (admitted / 'manifest.json').read_bytes() == (root / 'manifest.json').read_bytes()
    attempts = {'private_v2_import': lambda: importlib.import_module('contracts.runs.private_v2'),
                'private_v1_import': lambda: importlib.import_module('contracts.runs.private'),
                'private_dgp_import': lambda: importlib.import_module('contracts.dgp.parameters'),
                'evaluator_import': lambda: importlib.import_module('evaluation.truth'),
                'generator_import': lambda: importlib.import_module('simulation'),
                'private_file': lambda: Path('/truth/canary.json').read_bytes(),
                'private_directory': lambda: list(Path('/truth').iterdir()),
                'observed_write': lambda: (root / 'forged.json').write_text('forged'),
                'image_source_write': lambda: Path('/app/contracts/runs/injected.py').write_text('forged'),
                'evaluator_network': lambda: socket.create_connection((os.environ['OBS2_EVALUATOR_IP'], 8766), timeout=2)}
    denied = {}
    for name, action in attempts.items():
        try:
            result = action()
            if hasattr(result, 'close'):
                result.close()
            denied[name] = False
        except (OSError, ImportError):
            denied[name] = True
    assert all(denied.values()), denied
    assert os.getuid() in (10001, 10002)
    assert not Path('/app/contracts/dgp').exists()
    assert not Path('/app/contracts/runs/private_v2.py').exists()
    assert not Path('/var/run/docker.sock').exists()
    print(json.dumps(dict(status='passed', uid=os.getuid(), gid=os.getgid(), fixture_export=manifest.id,
                          fixture_records=len(partitions[0][1].records), positive_v2_admission=True, denied=denied,
                          no_private_numpy_import=True, limitation='Wire fixture only; no producer or likelihood qualification'), indent=2))


if __name__ == '__main__':
    main()
