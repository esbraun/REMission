"""No-native, no-science host controls for the one controls COPY proposal."""
import importlib.abc
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

BLOCKED={'numpy','scipy','pymc','pytensor','arviz','statsmodels','pandas','xarray','methods','services','contracts','ctypes','sqlite3'}
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:raise AssertionError('project/science/Store/native import forbidden')

if __name__=='__main__':
    sys.meta_path.insert(0,Guard());sys.path.insert(0,str(Path(__file__).resolve().parent))
    with patch('subprocess.Popen',side_effect=AssertionError('real Popen forbidden')),patch('subprocess.run',side_effect=AssertionError('real command forbidden')):
        import test_s1_diagnostic_image_preparation as tests
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    assert not BLOCKED.intersection(sys.modules)
    print('S1 controls overlay tripwire PASS: source/packet AST and owned-process doubles only')
    sys.exit(not result.wasSuccessful())
