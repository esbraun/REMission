"""Saved prediction SOURCE-only guard runner, no scientific/native execution."""
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
    forbidden={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas',
        'statsmodels','services','adapters','apps','sqlalchemy','sqlite3','ctypes','requests'}
    scientific={'methods.nof1','methods.measurement','methods.support.s2_model',
        'methods.support.s2_prediction','methods.support.s2_fit'}
    class Tripwire(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden or any(fullname==n or fullname.startswith(n+'.') for n in scientific):
                raise AssertionError('forbidden SOURCE import: '+fullname)
    sys.meta_path.insert(0,Tripwire())
    def refuse(*args,**kwargs):raise AssertionError('native/network forbidden in SOURCE checks')
    with patch.object(subprocess,'Popen',side_effect=refuse),patch.object(subprocess,'run',side_effect=refuse), \
            patch.object(socket,'socket',side_effect=refuse),patch.object(socket,'create_connection',side_effect=refuse), \
            patch.object(socket,'getaddrinfo',side_effect=refuse):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_s2_saved_source'))
    assert not forbidden.intersection(sys.modules)
    print('S2-PROD3 scalar/AST/inert metadata/API only; no Store/SQLite/science/binary/native/network')
    sys.exit(not result.wasSuccessful())
