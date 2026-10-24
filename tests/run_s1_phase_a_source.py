"""Guarded PhaseA scalar/source suite; app/SQLite/native/science blocked."""
from pathlib import Path
import socket,subprocess,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
import run_s1_genuine_source as policy
if __name__=='__main__':
    sys.meta_path.insert(0,policy.Guard())
    initial=subprocess.check_output(['git','show','d530f940239ade9ac00b527ab2aabb6a61245f4d:tooling/foundation/s1_genuine_submit.py'],cwd=ROOT,timeout=10)
    accepted=subprocess.check_output(['git','show','942335085284bde6accee5c125e91c5290c1094a:tooling/foundation/s1_genuine_submit.py'],cwd=ROOT,timeout=10)
    with patch('subprocess.Popen',side_effect=AssertionError('real child forbidden')),\
            patch('subprocess.run',side_effect=AssertionError('real command forbidden')),\
            patch('socket.socket',side_effect=AssertionError('network forbidden')),\
            patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
        import test_s1_genuine_source as original
        import test_s1_owner_binding as binding
        import test_s1_phase_a_source as phase
        binding.BASELINE=initial;phase.BASELINE=accepted
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(v) for v in (original,binding,phase))
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not policy.BLOCKED.intersection(sys.modules)
    print('Tripwire PASS: scalar/AST/inert fixtures only; no actual auth/Store/SQLite/science/native/network')
    raise SystemExit(not result.wasSuccessful())
