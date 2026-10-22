"""Consumer-safe byte/provenance admission; no evaluator or DGP imports."""
import os
import json
from pathlib import Path
import tempfile

from contracts.domain.boundaries import ObservedHistory
from .common import ExportAuthority, read_artifact, sha256
from .observed import ObservedExport, ReplayBatch, verify_partition


def verify_export(raw: bytes, root: Path, authority: ExportAuthority):
    version = json.loads(raw).get('schema_version')
    if version == '2.0.0':
        from .observed_v2 import ExportAuthorityV2
        from .admission_v2 import verify_export_v2
        if not isinstance(authority, ExportAuthorityV2):
            raise ValueError('explicit v2 trusted authority required')
        return verify_export_v2(raw, root, authority)
    if version != '1.0.0':
        raise ValueError('unsupported observed export version')
    # The authority is trusted caller configuration, never accepted from the
    # uploaded artifact. A self-declared producer/digest does not authenticate it.
    if sha256(raw)!=authority.export_sha256:
        raise ValueError('untrusted export digest')
    manifest=ObservedExport.model_validate_json(raw)
    if (manifest.id!=authority.export_id or manifest.run_id!=authority.run_id or manifest.producer!=authority.producer
            or manifest.source_commit!=authority.source_commit or manifest.runtime!=authority.runtime
            or manifest.run_manifest.sha256!=authority.manifest_sha256):
        raise ValueError('untrusted producer/run/source/runtime provenance')
    if manifest.execution=='contract_fixture' and not authority.allow_contract_fixture:
        raise ValueError('contract fixture cannot be admitted as generated evidence')
    partitions=[]
    for partition in manifest.partitions:
        history_raw=read_artifact(root,partition.history,'observed')
        replay_raw=read_artifact(root,partition.replay,'replay')
        history=ObservedHistory.model_validate_json(history_raw)
        batch=ReplayBatch.model_validate_json(replay_raw)
        projection=verify_partition(manifest,partition,history,batch)
        partitions.append((partition,history,batch,projection,history_raw,replay_raw))
    return manifest,partitions


def _immutable_write(path: Path, raw: bytes):
    path.parent.mkdir(parents=True,exist_ok=True)
    # Link a fully written file into place without overwriting an existing run.
    with tempfile.TemporaryDirectory(dir=path.parent) as directory:
        temporary=Path(directory)/'payload'
        temporary.write_bytes(raw);temporary.chmod(0o444)
        os.link(temporary,path)


def admit_export(raw: bytes, staging: Path, destination: Path, authority: ExportAuthority):
    manifest,partitions=verify_export(raw,staging,authority)
    destination=destination.resolve(strict=True)
    run_root=destination/manifest.run_id
    if run_root.is_symlink():raise ValueError('symlink output root denied')
    run_root.mkdir(exist_ok=True)
    target=run_root/manifest.id
    target.mkdir(exist_ok=False)
    # Verify everything before the first output write. Manifest is the final
    # publication marker; an interrupted directory has no consumable manifest.
    for partition,_,_,_,history_raw,replay_raw in partitions:
        _immutable_write(target/partition.history.path,history_raw)
        _immutable_write(target/partition.replay.path,replay_raw)
        if manifest.schema_version == '2.0.0':
            for artifact in [partition.coverage, *partition.stage_ledgers, *partition.completion_receipts, *partition.mechanisms]:
                _immutable_write(target/artifact.path, read_artifact(staging, artifact, artifact.role))
    _immutable_write(target/'manifest.json',raw)
    return target


def read_admitted(root: Path, authority: ExportAuthority):
    # Opaque configured run/export IDs choose the root, never user path input.
    return verify_export((root/'manifest.json').read_bytes(),root,authority)
