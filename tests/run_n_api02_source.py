"""AST/stdlib/doubles only; no scientific payload import or native child."""
import importlib.abc
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'tests'))
    blocked={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas',
        'statsmodels','methods','probe_roles','run_support_once','n_api02_unit'}
    class Tripwire(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in blocked:raise AssertionError('host science/payload/dormant import denied')
    sys.meta_path.insert(0,Tripwire())
    folder=ROOT/'artifacts/n-api02-source-temp';folder.mkdir(parents=True,exist_ok=True);tempfile.tempdir=str(folder)
    original_popen=subprocess.Popen
    def metadata_only(argv,*args,**kwargs):
        if not isinstance(argv,list) or argv[0]!='git' or argv[1] not in ('show','rev-parse'):
            raise AssertionError('native child forbidden in NAPI source checks')
        return original_popen(argv,*args,**kwargs)
    with patch('subprocess.Popen',side_effect=metadata_only):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_n_api02_preparation'))
    assert not blocked.intersection(sys.modules)
    print('NAPI source only: payload AST not imported; Git metadata children and capture/lifecycle doubles; no science')
    sys.exit(not result.wasSuccessful())
