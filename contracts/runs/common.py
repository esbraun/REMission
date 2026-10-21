"""Consumer-safe identities and paths; no structural values or evaluator imports."""
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from contracts.domain.common import Identifier, Name, Sha256, StrictModel, VersionRef

Token = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")]
Commit = Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]
Role = Literal['generator', 'evaluator', 'contract_fixture']


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class Producer(StrictModel):
    id: Token
    version: Name
    role: Role


class Artifact(StrictModel):
    id: Token
    path: str
    sha256: Sha256
    bytes: Annotated[int, Field(gt=0)]
    role: Literal['configuration', 'observed', 'replay', 'observed_manifest', 'private_truth', 'seed_ledger', 'calibration', 'evaluator_request', 'evaluator_result', 'run_manifest']
    media_type: Literal['application/json','text/markdown','text/plain']

    @field_validator('path')
    @classmethod
    def relative_path(cls, value):
        # Reject encoded/Windows paths as well as POSIX traversal; no decoding.
        if not value or any(c in value for c in ('\\', ':', '%', '\x00')) or value.startswith('/'):
            raise ValueError('artifact path must be a plain relative POSIX path')
        parts=value.split('/')
        if any(p in ('', '.', '..') or not p.isascii() or p.rstrip(' .')!=p for p in parts):
            raise ValueError('noncanonical artifact path')
        devices={'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}
        if any(any(ord(c)<32 for c in part) or part.split('.')[0].upper() in devices for part in parts):
            raise ValueError('control characters and Windows device paths are denied')
        if PurePosixPath(value).as_posix()!=value:
            raise ValueError('noncanonical artifact path')
        return value


class Bindings(StrictModel):
    """Only nonsecret exact version/hash references may cross the export boundary."""
    protocol: VersionRef
    dgp: VersionRef
    parameters: VersionRef
    equations: VersionRef
    scenarios: VersionRef
    catalog: VersionRef
    timing: VersionRef
    temporal: VersionRef
    calibration_schema: VersionRef
    analytic_fixtures: VersionRef
    probability_precision: VersionRef

    @model_validator(mode='after')
    def accepted_source(self):
        expected=json.loads(Path(__file__).with_name('bindings-v1.json').read_text(encoding='utf-8'))
        if self.model_dump(mode='json')!=expected:
            raise ValueError('unaccepted protocol/DGP/equation/catalog/timing/calibration/fixture binding')
        return self


class Runtime(StrictModel):
    image_sha256: Sha256
    numerical_lock: VersionRef
    service_lock: VersionRef
    python_version: Name
    numpy_version: Literal['2.5.4']
    prng: Literal['PCG64DXSM']
    seed_derivation: Literal['remission-seed-v1']
    precision: Literal['float64']


class Authority(StrictModel):
    """Trusted caller configuration, supplied out-of-band, never read from a run.

    Exact hashes authenticate bytes only after a trusted host/operator has bound
    that digest to this producer/run. An uploader's own Authority is not trusted.
    """
    run_id: Token
    producer: Producer
    manifest_sha256: Sha256
    source_commit: Commit
    runtime: Runtime
    allow_contract_fixture: bool


class ExportAuthority(Authority):
    """Out-of-band authorized export digest from a verified producer result."""
    export_id: Token
    export_sha256: Sha256


def read_artifact(root: Path, artifact: Artifact, role: str) -> bytes:
    if artifact.role!=role:
        raise ValueError('artifact role mismatch')
    root=root.resolve(strict=True)
    path=root
    for component in artifact.path.split('/'):
        path=path/component
        if path.is_symlink():
            raise ValueError('symlink artifact denied')
    resolved=path.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError('artifact escapes trusted root or is not a file')
    raw=resolved.read_bytes()
    if len(raw)!=artifact.bytes or sha256(raw)!=artifact.sha256:
        raise ValueError('artifact byte count/hash mismatch')
    return raw


def unique(values, label):
    if len(values)!=len(set(values)):
        raise ValueError('duplicate '+label)
