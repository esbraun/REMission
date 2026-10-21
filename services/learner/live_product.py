"""Consumer-only three-file publication; no service/store imports."""
import os
from pathlib import Path


def publish_product(destination,manifest,observed,facts):
    destination=Path(destination)
    if destination.exists():
        raise ValueError('immutable live admission destination exists')
    destination.mkdir(parents=True,mode=0o700)
    for name,raw in [('observed-projection.json',observed),('live-hold-facts.json',facts),('manifest.json',manifest)]:
        with (destination/name).open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        (destination/name).chmod(0o444)
