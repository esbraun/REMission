"""Source-only reconciliation guard; whitelisted public Git before tripwires."""
from pathlib import Path
import socket,subprocess,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
import run_s1_genuine_source as policy
if __name__=='__main__':
    baseline={name:subprocess.check_output(['git','show','ff0fb3f03220772e4512a337b3cc4afb53c7cce3:tooling/foundation/'+name+'.py'],cwd=ROOT,timeout=10)
        for name in ('s1_genuine_once','s1_genuine_submit')}
    previous=subprocess.check_output(['git','show','917b8e14af47efb60fa79885113cfdedba719de2:tooling/foundation/s1_genuine_submit.py'],cwd=ROOT,timeout=10)
    previous_host=subprocess.check_output(['git','show','917b8e14af47efb60fa79885113cfdedba719de2:tooling/foundation/s1_genuine_once.py'],cwd=ROOT,timeout=10)
    preauth={name:subprocess.check_output(['git','show','ad82d6825ab4c08d1bbdaa8d5e4de4866f6cc52d:tooling/foundation/'+name+'.py'],cwd=ROOT,timeout=10)
        for name in ('s1_genuine_once','s1_genuine_submit')}
    sys.meta_path.insert(0,policy.Guard())
    with patch('subprocess.Popen',side_effect=AssertionError('real child forbidden')),patch('subprocess.run',side_effect=AssertionError('real command forbidden')),\
            patch('socket.socket',side_effect=AssertionError('network forbidden')),patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
        import test_s1_original_reconcile as tests
        tests.BASELINE_HOST=baseline['s1_genuine_once'];tests.BASELINE_DRIVER=baseline['s1_genuine_submit']
        tests.PRE_REPAIR_DRIVER=previous
        tests.PRE_REPAIR_HOST=previous_host
        tests.PREAUTH_BASE_DRIVER=preauth['s1_genuine_submit'];tests.PREAUTH_BASE_HOST=preauth['s1_genuine_once']
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    assert not policy.BLOCKED.intersection(sys.modules)
    print('Tripwire PASS: no actual app/SQLite/Store/science/native/network/private queries')
    raise SystemExit(not result.wasSuccessful())
