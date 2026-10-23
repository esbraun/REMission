"""Stdlib draft only. No Docker, lifecycle import or executable operation mode."""
import hashlib
import json
from pathlib import Path

LIMITS=['--network','none','--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','64',
    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m','--restart','no','--user','10002:10002']

def inspect_draft(path):
    value=json.loads(Path(path).read_bytes())
    if value['status']!='DRAFT_DEPENDENCY_PENDING' or value['learner_image'] is not None:
        raise ValueError('draft must retain unknown learner identity')
    return value

def proposed_argv(image,payload):
    """Inspection/test seam only; caller cannot launch through this module."""
    if image is None:raise ValueError('accepted IMAGE04 learner dependency unavailable')
    return ['docker','create','--name','remission-n-api02-unit-r1',*LIMITS,
        '--env','REMISSION_N_API_UNIT=UNIT-API02-91740203',image,'python','-I','-B','-c',payload]

def execute_draft(spec):
    # Deliberately before helper loading, reservation or subprocess creation.
    raise RuntimeError('DRAFT: exact accepted IMAGE04 learner/source evidence and new source/operation review required')
