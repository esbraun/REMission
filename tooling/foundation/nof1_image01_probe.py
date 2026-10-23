"""Image-local source/metadata/scalar import probe. Never opens a Store."""
import argparse
import ast
import hashlib
import importlib
import importlib.abc
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys

BLOCKED={'numpy','scipy','pandas','pymc','pytensor','arviz','arviz_base','arviz_stats',
    'arviz_plots','xarray','netCDF4','statsmodels','methods'}
VERSIONS={'pydantic':'2.14.1','fastapi':'0.157.0','numpy':'2.5.4','scipy':'1.18.1',
    'pymc':'6.3.2','pytensor':'3.3.4','arviz':'1.3.0','arviz-base':'1.3.1',
    'arviz-stats':'1.3.3','xarray':'2026.9.0','netCDF4':'1.7.5'}


class Tripwire(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:
            raise AssertionError('scientific import forbidden in scalar image qualification: '+fullname)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--role',choices=('service','learner'),required=True)
    parser.add_argument('--expected',type=Path,required=True);parser.add_argument('--expected-sha256',required=True)
    parser.add_argument('--probe-sha256',required=True);args=parser.parse_args()
    digest=lambda raw:hashlib.sha256(raw).hexdigest()
    if digest(Path(__file__).read_bytes())!=args.probe_sha256:raise ValueError('probe bytes changed')
    raw=args.expected.read_bytes()
    if digest(raw)!=args.expected_sha256:raise ValueError('expected closure bytes changed')
    expected=json.loads(raw);uid=10001 if args.role=='service' else 10002
    if ({p.name for p in Path('/qualify').iterdir()}!={'probe.py','expected.json'}
            or any(p.is_symlink() for p in Path('/qualify').iterdir())):
        raise ValueError('qualification image source custody mismatch')
    if (expected['role']!=args.role or expected['uid']!=uid or sys.platform!='linux'
            or platform.machine()!='x86_64' or os.getuid()!=uid or os.getgid()!=uid
            or platform.python_version()!='3.13.7' or sqlite3.sqlite_version!='3.54.1'):
        raise ValueError('role/platform/UID/runtime mismatch')
    root=Path('/app');actual={}
    for path in root.rglob('*'):
        if path.is_symlink():raise ValueError('project source symlink denied')
        if path.is_file() and '__pycache__' not in path.parts:actual[str(path)]=digest(path.read_bytes())
    if actual!=expected['project_source']:raise ValueError('complete parent-plus-overlay source closure mismatch')
    forbidden=['services/generator','services/evaluator','contracts/dgp','evaluation','tests']
    forbidden+=['methods','services/learner'] if args.role=='service' else ['services/foundation']
    if any((root/name).exists() for name in forbidden):raise ValueError('cross-role or private project source present')
    if args.role=='learner':
        for path in [*root.joinpath('methods/nof1').glob('*.py'),root/'methods/measurement.py']:
            ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    versions={name:importlib.metadata.version(name) for name in VERSIONS}
    if versions!=VERSIONS:raise ValueError('installed metadata differs from pinned dependencies')
    sys.meta_path.insert(0,Tripwire());sys.path.insert(0,'/app')
    from contracts.domain.nof1_app import NInput,NResult
    from contracts.domain.borrowing import parse_input,parse_result
    from pydantic import ValidationError
    for parser_fn,kind in ((parse_input,'poc_nof1_input'),(parse_result,'poc_nof1_result')):
        try:parser_fn(json.dumps(dict(kind=kind,schema_version='2.0.0')))
        except ValidationError:pass
        else:raise AssertionError('closed/incomplete N envelope was accepted')
    modules=('services.foundation.nof1_analysis','services.foundation.app') if args.role=='service' else (
        'services.learner.nof1_worker','services.learner.nof1_artifacts')
    for module in modules:importlib.import_module(module)
    if BLOCKED.intersection(sys.modules):raise AssertionError('scientific module loaded')
    print(json.dumps(dict(status='copied_source_metadata_scalar_imports_only',role=args.role,uid=uid,
        python=platform.python_version(),sqlite=sqlite3.sqlite_version,versions=versions,
        project_source=actual,probe_sha256=args.probe_sha256,expected_sha256=args.expected_sha256,
        scalar_parsers=[NInput.__name__,NResult.__name__],scientific_imports=False,
        worker_executed=False,Store_opened=False,generated_or_fitted=False),sort_keys=True))


if __name__=='__main__':main()
