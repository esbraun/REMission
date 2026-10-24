"""Guarded actual scalar adapter/contract + AST tests; no graph compilation."""
import importlib.abc
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
    forbidden={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas','statsmodels',
        'services','adapters','apps','sqlalchemy','sqlite3','ctypes','probe_roles','run_support_once'}
    science_modules=('methods.nof1','methods.measurement','methods.support.data','methods.support.s2_model',
        'methods.support.s2_prediction','tooling.foundation.s2_model_qualification')
    class Tripwire(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden or any(fullname==v or fullname.startswith(v+'.') for v in science_modules):
                raise AssertionError('host science/app/Store/qualification import forbidden')
    sys.meta_path.insert(0,Tripwire())
    def no_native(*args,**kwargs):raise AssertionError('native process/network forbidden')
    class NoChild(subprocess.Popen):
        def __init__(self,*args,**kwargs):no_native()
    with patch.object(subprocess,'Popen',NoChild),patch.object(subprocess,'run',side_effect=no_native),patch.object(socket,'socket',side_effect=no_native),patch.object(socket,'create_connection',side_effect=no_native),patch.object(socket,'getaddrinfo',side_effect=no_native):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_s2_model_source'))
    assert not forbidden.intersection(sys.modules)
    print('Observed scalar adapter/Pydantic/AST only; no science/native/Store/graph compilation or fit')
    sys.exit(not result.wasSuccessful())
