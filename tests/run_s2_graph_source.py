"""Guarded source-only runner: actual scalar adapter + stdlib graph seams."""
import importlib.abc
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root),str(root/'tests')]
    forbidden={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas','statsmodels',
        'services','adapters','apps','sqlalchemy','probe_roles','run_support_once'}
    blocked=('methods.nof1','methods.measurement','methods.support.s2_model',
             'methods.support.s2_prediction','tooling.foundation.s2_model_qualification')
    class Tripwire(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden or any(fullname==v or fullname.startswith(v+'.') for v in blocked):
                raise AssertionError('source-only scientific/native/app/Store boundary')
    sys.meta_path.insert(0,Tripwire())
    with patch.object(subprocess,'Popen',side_effect=AssertionError('native children blocked')):
        suite=unittest.defaultTestLoader.loadTestsFromNames(['test_s2_model_source','test_s2_graph_source'])
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not forbidden.intersection(sys.modules)
    print('SAFE scalar/AST/stdlib/temp-FS/process doubles only; NO graph/science/native/Docker execution')
    sys.exit(not result.wasSuccessful())
