"""Typed admission of synthetic observed exports; no opaque source blobs."""
import hashlib
from pathlib import Path
from contracts.domain.boundaries import ObservedHistory


def admit(source: Path, destination: Path):
    raw=source.read_bytes()
    observed=ObservedHistory.model_validate_json(raw)
    # The export consists only of the accepted schema. Extra fields in either
    # the wrapper or any record fail before an observed artifact is written.
    payload=observed.model_dump_json().encode()
    destination.write_bytes(payload)
    destination.chmod(0o444)
    return hashlib.sha256(payload).hexdigest()


if __name__=="__main__":print(admit(Path("/staging/history.json"),Path("/observed/history.json")))
