"""Host SOURCE-only runner: active science/app/DB/process/network tripwires."""
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
        'statsmodels','services','adapters','apps','sqlalchemy','sqlite3','ctypes','requests','methods'}
    class Tripwire(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden:raise AssertionError('forbidden SOURCE import: '+fullname)
    sys.meta_path.insert(0,Tripwire())
    def refuse(*args,**kwargs):raise AssertionError('process/network forbidden in SOURCE checks')
    with patch.object(subprocess,'Popen',side_effect=refuse),patch.object(subprocess,'run',side_effect=refuse), \
            patch.object(socket,'socket',side_effect=refuse),patch.object(socket,'create_connection',side_effect=refuse), \
            patch.object(socket,'getaddrinfo',side_effect=refuse):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_s2_controller_source'))
    assert not forbidden.intersection(sys.modules)
    print('SOURCE ONLY: actual scalar/contract/AST bodies with inert typed records/transactions; no app/SQLite/science/process/network')
    sys.exit(not result.wasSuccessful())
