"""Watchdog/dispatcher doubles only; actual commands and science are blocked."""
import importlib.abc
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

BLOCKED={'numpy','scipy','statsmodels','pymc','pytensor','arviz','arviz_stats','pandas','xarray','methods'}


class ScientificImportTripwire(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED or fullname.startswith('services.generator'):
            raise AssertionError('scientific/generator import forbidden: '+fullname)


if __name__=='__main__':
    sys.meta_path.insert(0,ScientificImportTripwire())
    root=Path(__file__).resolve().parents[1]
    for path in (root,root/'tests',root/'tests/contracts',root/'tests/integration/replay',root/'tooling/foundation'):
        sys.path.insert(0,str(path))
    with patch('subprocess.Popen',side_effect=AssertionError('real child creation forbidden')), \
            patch('subprocess.run',side_effect=AssertionError('real command execution forbidden')):
        suite=unittest.defaultTestLoader.loadTestsFromName('test_ordinary_dispatcher')
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not BLOCKED.intersection(sys.modules),'scientific module loaded'
    assert not any(n.startswith('services.generator') for n in sys.modules),'generator module loaded'
    print('Watchdog source tripwire PASS: no science/generator imports; no real subprocess calls')
    sys.exit(not result.wasSuccessful())
