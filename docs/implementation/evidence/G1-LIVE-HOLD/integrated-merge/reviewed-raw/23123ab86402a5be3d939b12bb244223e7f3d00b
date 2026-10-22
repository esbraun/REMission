"""Consumer-only three-file publication; no service/store imports."""
import os
from pathlib import Path
import uuid


def publish_product(destination,manifest,observed,facts,*,validate,fault=None):
    destination=Path(destination)
    if destination.exists():
        raise ValueError('immutable live admission destination exists')
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    partial=destination.parent/('.partial-'+destination.name+'-'+uuid.uuid4().hex)
    partial.mkdir(mode=0o700)
    for name,raw in [('observed-projection.json',observed),('live-hold-facts.json',facts),('manifest.json',manifest)]:
        with (partial/name).open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        (partial/name).chmod(0o444)
        if fault:fault('after_'+name)
    context=validate(partial)
    descriptor=os.open(partial,os.O_RDONLY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)
    if fault:fault('before_product_rename')
    partial.rename(destination)
    descriptor=os.open(destination.parent,os.O_RDONLY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)
    return context
