"""Bounded changed-source checks. Fails on any scientific import attempt."""
import importlib.abc
from pathlib import Path
import sys
import unittest

BLOCKED={'numpy','scipy','statsmodels','pymc','pytensor','arviz','pandas','xarray'}


class ScientificImportTripwire(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:
            raise AssertionError('Scientific import forbidden in scalar checks: '+fullname)


if __name__=='__main__':
    sys.meta_path.insert(0,ScientificImportTripwire())
    root=Path(__file__).resolve().parents[1]
    for path in (root,root/'tests',root/'tests/contracts',root/'tests/integration/replay'):
        sys.path.insert(0,str(path))
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name)
        for name in ('test_support_s1','test_support_s1_analysis'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not BLOCKED.intersection(sys.modules),'scientific module loaded'
    print('Scientific import tripwire: PASS; no blocked modules loaded')
    sys.exit(not result.wasSuccessful())
