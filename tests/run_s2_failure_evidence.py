"""Safe R4 diagnostics doubles; Git fixture bytes are materialized separately."""
import importlib.abc
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
    forbidden={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4',
               'pandas','statsmodels','methods','probe_roles','run_support_once',
               's2_numerics_unit','s2_numerics_oracle'}
    class Tripwire(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden:raise AssertionError('host science/payload import forbidden')
    sys.meta_path.insert(0,Tripwire())
    folder=ROOT/'artifacts/s2-source-temp';folder.mkdir(parents=True,exist_ok=True);tempfile.tempdir=str(folder)
    with patch.object(subprocess,'Popen',side_effect=AssertionError('native children forbidden in S2 source controls')):
        suite=unittest.defaultTestLoader.loadTestsFromName('test_s2_failure_evidence')
        existing=unittest.defaultTestLoader.loadTestsFromName('test_s2_numerics_source')
        def current(items):
            for item in items:
                if isinstance(item,unittest.TestSuite):yield from current(item)
                elif not item.id().endswith('test_fixed_and_exposed_regression_counts_with_supplemental_still_sealed'):yield item
        suite.addTests(current(existing))
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not forbidden.intersection(sys.modules)
    print('S2 diagnostics/source only; historical sealed-absence assertion excluded, not passed; no science/native child')
    sys.exit(not result.wasSuccessful())
