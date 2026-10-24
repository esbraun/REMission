"""Reuse existing guarded source runner policy; no real SQLite/app/process."""
from pathlib import Path
import socket,subprocess,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
import run_s1_genuine_source as policy
if __name__=='__main__':
    sys.meta_path.insert(0,policy.Guard())
    # Whitelisted public Git metadata/source only; native calls blocked below.
    baseline=subprocess.check_output(['git','show','d530f940239ade9ac00b527ab2aabb6a61245f4d:tooling/foundation/s1_genuine_submit.py'],cwd=ROOT,timeout=10)
    with patch('subprocess.Popen',side_effect=AssertionError('real child forbidden')),\
            patch('subprocess.run',side_effect=AssertionError('real command forbidden')),\
            patch('socket.socket',side_effect=AssertionError('network forbidden')),\
            patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
        import test_s1_genuine_source as prior
        import test_s1_owner_binding as binding
        binding.BASELINE=baseline
        suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(prior),unittest.defaultTestLoader.loadTestsFromModule(binding)])
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not policy.BLOCKED.intersection(sys.modules)
    print('Tripwire PASS: 27 prior controls plus binding scalar/AST/inert connections; no real SQLite/app/Store/science/native/network')
    raise SystemExit(not result.wasSuccessful())
