"""Typed admission of synthetic observed exports; no opaque source blobs."""
import hashlib
import json
from pathlib import Path
from contracts.domain.boundaries import ObservedHistory


def admit(source: Path, destination: Path):
    raw=source.read_bytes()
    wrapper=json.loads(raw)
    if not isinstance(wrapper,dict):
        raise ValueError('observed history wrapper required')
    if wrapper.get('schema_version') == '2.1.0':
        from contracts.domain.protocol import ObservedHistoryV21
        observed=ObservedHistoryV21.model_validate_json(raw)
    elif wrapper.get('schema_version') == '2.0.0':
        from contracts.domain.observed_v2 import ObservedHistoryV2
        observed=ObservedHistoryV2.model_validate_json(raw)
    else:
        observed=ObservedHistory.model_validate_json(raw)
    # The export consists only of the accepted schema. Extra fields in either
    # the wrapper or any record fail before an observed artifact is written.
    payload=observed.model_dump_json().encode()
    destination.write_bytes(payload)
    destination.chmod(0o444)
    return hashlib.sha256(payload).hexdigest()


if __name__=="__main__":print(admit(Path("/staging/history.json"),Path("/observed/history.json")))


def admit_run_export(manifest: bytes, staging: Path, destination: Path, authority):
    """Versioned multi-patient admission with trusted out-of-band producer binding."""
    from contracts.runs.admission import admit_export
    return admit_export(manifest,staging,destination,authority)


def admit_live_safety(manifest: bytes, staging: Path, destination: Path, authority):
    """Require the complete independently authorized operational product."""
    from contracts.service.live_safety_admission import verify_live_safety
    verify_live_safety(manifest,staging,authority)
    # Reuse only the immutable file publisher, not service authority/configuration.
    from .live_product import publish_product
    # Read untrusted staging into private bytes and reverify the copied complete
    # three-file product before its single atomic directory publication.
    observed=(staging/'observed-projection.json').read_bytes();facts=(staging/'live-hold-facts.json').read_bytes()
    return publish_product(destination,manifest,observed,facts,validate=lambda root:verify_live_safety(manifest,root,authority))
