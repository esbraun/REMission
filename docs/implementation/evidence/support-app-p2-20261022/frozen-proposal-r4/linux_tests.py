"""Frozen ordinary-test payload. No accepted source output or scientific run."""
import importlib.abc
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import sys
import unittest

ROOT=Path('/source')
sys.path=[str(ROOT),str(ROOT/'tests/integration/replay'),str(ROOT/'tests/run_contracts'),
          *[p for p in sys.path if p and not p.startswith('/app')]]
os.chdir(ROOT)


class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'numpy','scipy','pymc','pytensor','statsmodels','methods'} or fullname.startswith('services.generator'):
            raise ImportError('Scientific/generator imports excluded from ordinary fixture tests: '+fullname)


sys.meta_path.insert(0,NoScience())
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('150 second ordinary-test limit')))
signal.alarm(150)
print(json.dumps(dict(scope='structural fixtures only; no accepted archive or browser',python=sys.version,
    dependencies={p:importlib.metadata.version(p) for p in ('fastapi','pydantic','httpx','argon2-cffi')})),flush=True)
suite=unittest.defaultTestLoader.loadTestsFromNames(['test_support_archive','test_foundation','test_observed_v2_archive'])
result=unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))),flush=True)
sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)
