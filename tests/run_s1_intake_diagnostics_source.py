"""Source-only scalar checks. Git bytes once; then real native calls denied."""
import importlib.abc
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BLOCKED={'numpy','scipy','statsmodels','pymc','pytensor','arviz','arviz_stats','pandas','xarray','methods','services','contracts','ctypes','sqlite3'}
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:raise AssertionError('real project/science/Store/native import forbidden')

if __name__=='__main__':
    sys.meta_path.insert(0,Guard());sys.path.insert(0,str(ROOT/'tests'))
    # Exact public source inspection only; no old worker checkout access.
    baseline=subprocess.check_output(['git','show','e196187aea79cbc4a49576c0107e94e4c6499089:services/foundation/support_archive.py'],cwd=ROOT,timeout=10)
    control=subprocess.check_output(['git','cat-file','blob','d117840386e45c54005e8f38da884dc3fc1dd7ed'],cwd=ROOT,timeout=10)
    with patch('subprocess.Popen',side_effect=AssertionError('real Popen forbidden')),patch('subprocess.run',side_effect=AssertionError('real command forbidden')):
        import test_s1_intake_diagnostics as tests
        tests.BASELINE=baseline
        tests.CONTROL_BASELINE=control
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    assert not BLOCKED.intersection(sys.modules)
    print('S1 diagnostic source tripwire PASS: AST/scalar doubles only, no real Store/API/archive/native/science execution')
    sys.exit(not result.wasSuccessful())
