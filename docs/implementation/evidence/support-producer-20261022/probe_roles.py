"""Exact copied-source/import proof only; never generate or fit here."""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys


def available(name):
    try:return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:return False


def probe(role,expected):
    target='services.generator.research_support' if role=='generator' else 'run_support_once'
    importlib.import_module(target)
    denied=['contracts.dgp','contracts.domain.evaluation','services.foundation.store','services.foundation.app']
    if role=='learner':denied.extend(['services.generator','services.foundation.protocol'])
    failures=[name for name in denied if available(name) or name in sys.modules]
    if failures:raise ValueError('private_or_live_modules_available:'+','.join(failures))
    actual={str(p.relative_to('/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app').rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('copied_role_source_set_or_hash_mismatch')
    imported={name:str(getattr(module,'__file__','')) for name,module in sys.modules.items()
              if str(getattr(module,'__file__','')).startswith('/app/')}
    return dict(role=role,copied_files=actual,imported_application_modules=imported,denied_modules=denied,
        deny_checks_passed=True,generated=False,fitted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--role',choices=['generator','learner'],required=True)
    parser.add_argument('--expected',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(probe(args.role,json.loads(args.expected.read_bytes())),sort_keys=True))
