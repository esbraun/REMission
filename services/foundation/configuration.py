"""Read deployment-mounted immutable configuration; no HTTP path selects files."""
import json
import os
from pathlib import Path
from contracts.runs.observed_v2 import ExportAuthorityV2
from contracts.service.live_hold import InstalledBundle
from .app import Settings


def read_archives(configuration):
    archives={}
    if configuration:
        for entry in json.loads(Path(configuration).read_bytes()):
            if set(entry)!={'export_id','manifest','artifact_root','authority'} or entry['export_id'] in archives:
                raise ValueError('invalid_archive_host_configuration')
            archives[entry['export_id']]=(Path(entry['manifest']).read_bytes(),Path(entry['artifact_root']),
                ExportAuthorityV2.model_validate_json(Path(entry['authority']).read_bytes()))
    return archives


def environment_settings():
    path=os.environ.get('REMISSION_CONTROL_BUNDLE')
    if not path:
        raise RuntimeError('service_control_bundle_required')
    installed=InstalledBundle.model_validate_json(Path(path).read_bytes())
    archives=read_archives(os.environ.get('REMISSION_ARCHIVE_CONFIG'))
    runtime=os.environ.get('REMISSION_RUNTIME_REF')
    return Settings(database=Path(os.environ.get('REMISSION_DATABASE','/data/remission.sqlite')),installed=installed,
        origin=os.environ.get('REMISSION_ORIGIN','http://127.0.0.1:8765'),web_root=Path(os.environ.get('REMISSION_WEB_ROOT','/app/web/dist')),
        observed_archives=archives,live_export_root=Path(os.environ['REMISSION_LIVE_EXPORT_ROOT']) if os.environ.get('REMISSION_LIVE_EXPORT_ROOT') else None,
        source_commit=os.environ.get('REMISSION_SOURCE_COMMIT'),runtime_ref=json.loads(Path(runtime).read_bytes()) if runtime else None)
