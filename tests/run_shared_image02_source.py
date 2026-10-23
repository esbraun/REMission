"""IMAGE04 source checks only: no native/Popen probe, Docker or science."""
import importlib.abc
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BLOCKED={'numpy','scipy','statsmodels','pymc','pytensor','arviz','arviz_stats','pandas','xarray','methods'}
class Tripwire(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED or fullname.startswith('services.generator'):
            raise AssertionError('science/generator import forbidden')

if __name__=='__main__':
    sys.meta_path.insert(0,Tripwire())
    for path in (ROOT,ROOT/'tests',ROOT/'tests/integration/replay',ROOT/'tooling/foundation'):
        sys.path.insert(0,str(path))
    temporary=ROOT/'artifacts/shared-image04-source-temp';temporary.mkdir(parents=True,exist_ok=True)
    tempfile.tempdir=str(temporary)
    original_popen=subprocess.Popen;original_run=subprocess.run
    def require_git(argv):
        if not isinstance(argv,list) or argv[0]!='git' or argv[1] not in ('show','rev-parse','ls-tree'):
            raise AssertionError('non-Git child creation forbidden during IMAGE04 preparation')
    def git_metadata_only(argv,*args,**kwargs):
        require_git(argv)
        return original_popen(argv,*args,**kwargs)
    def git_run_only(argv,*args,**kwargs):
        require_git(argv)
        return original_run(argv,*args,**kwargs)
    suite=unittest.TestSuite()
    from test_nof1_image01_operator import Image01Controls
    for name in unittest.defaultTestLoader.getTestCaseNames(Image01Controls):
        if name!='test_regular_file_capture_reaps_exact_child_and_never_claims_daemon_stop':
            suite.addTest(Image01Controls(name))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName('test_ordinary_dispatcher'))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName('test_shared_image03_probe'))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName('test_shared_image04_packaging'))
    with patch('subprocess.Popen',side_effect=git_metadata_only),\
            patch('subprocess.run',side_effect=git_run_only):
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not BLOCKED.intersection(sys.modules)
    print('IMAGE04 source-only: native/Popen timeout probe excluded; Git metadata children only; Docker/lifecycle doubles; no science')
    sys.exit(not result.wasSuccessful())
