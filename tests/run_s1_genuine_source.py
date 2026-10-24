"""Guarded Phase A source seams; no app, Store, science or native child."""
import importlib.abc
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BLOCKED={'services','contracts','methods','sqlite3','ctypes','numpy','scipy','statsmodels','pymc',
    'pytensor','arviz','arviz_stats','pandas','xarray','fastapi','starlette','httpx'}
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name.split('.')[0] in BLOCKED:raise AssertionError('source-only import tripwire')

if __name__=='__main__':
    sys.meta_path.insert(0,Guard());sys.path.insert(0,str(ROOT/'tests'))
    with patch('subprocess.Popen',side_effect=AssertionError('real child forbidden')),\
            patch('subprocess.run',side_effect=AssertionError('real command forbidden')),\
            patch('socket.socket',side_effect=AssertionError('real network forbidden')),\
            patch('socket.create_connection',side_effect=AssertionError('real network forbidden')):
        import test_s1_genuine_source as tests
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    assert not BLOCKED.intersection(sys.modules)
    print('Tripwire PASS: scalar/AST/inert doubles and own temporary files only')
    raise SystemExit(not result.wasSuccessful())
