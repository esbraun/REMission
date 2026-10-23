"""Bounded N and affected lifecycle regressions; scientific imports forbidden."""
import importlib.abc
from pathlib import Path
import sys
import unittest

BLOCKED={'numpy','scipy','statsmodels','pymc','pytensor','arviz','arviz_stats','pandas','xarray'}


class ScientificImportTripwire(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:
            raise AssertionError('Scientific import forbidden in N source checks: '+fullname)


if __name__=='__main__':
    sys.meta_path.insert(0,ScientificImportTripwire())
    root=Path(__file__).resolve().parents[1]
    for path in (root,root/'tests',root/'tests/contracts',root/'tests/integration/replay',root/'tooling/foundation'):
        sys.path.insert(0,str(path))
    names=('tests.contracts.test_nof1_app','tests.contracts.test_nof1_dispatch',
        'tests.integration.replay.test_nof1_analysis','test_support_s1','test_support_s1_analysis',
        'tests.contracts.test_cohort_qualification','tests.contracts.test_cohort_runtime',
        'test_cohort_qualified_binding','test_cohort_completion_deadline','test_ordinary_dispatcher')
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in names)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not BLOCKED.intersection(sys.modules),'scientific module loaded'
    print('N source scientific-import tripwire: PASS; no blocked modules loaded')
    sys.exit(not result.wasSuccessful())
