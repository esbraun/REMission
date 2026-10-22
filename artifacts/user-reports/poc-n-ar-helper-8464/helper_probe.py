"""Only light discovery and the selected AR symbolic unit, never build()."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT, OUT = Path('/source'), Path('/output')
sys.path[:0] = [str(ROOT), str(ROOT/'tests/methods')]
def emit(kind, **fields):
    print(json.dumps(dict(kind=kind, **fields), sort_keys=True), flush=True)

if len(sys.argv) > 1 and sys.argv[1] == '--pure':
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests/methods'), pattern='test_nof1*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert 'pymc' not in sys.modules and 'pytensor' not in sys.modules
    emit('pure-result', tests=result.testsRun, skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors), symbolic_imported=False)
    sys.exit(0 if result.wasSuccessful() else 1)
if len(sys.argv) > 1 and sys.argv[1] == '--helper':
    from tooling.foundation import pa3_monitor
    original = pa3_monitor.verify_cvm
    policy = json.loads((ROOT/'tooling/foundation/pa3-cvm-policy.json').read_bytes())
    def verify(function):
        vm = original(function)
        optimizer = pa3_monitor.optimizer_identity(function.maker.mode.provided_optimizer)
        assert optimizer == policy['candidate_optimizer']
        emit('actual-helper-compiled', actual_vm=vm, optimizer=optimizer)
        return vm
    pa3_monitor.verify_cvm = verify
    from methods.nof1 import model
    def forbidden_build(*args, **kwargs):
        raise AssertionError('whole N model construction forbidden in helper unit')
    model.build = forbidden_build
    from test_nof1_symbolic import SymbolicTests
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
        SymbolicTests('test_ar_convolution_and_pullback_at_zero_and_negative_rho')]))
    emit('helper-result', tests=result.testsRun, skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors), whole_model_build=False, fit=False)
    assert result.testsRun == 1 and not result.skipped
    sys.exit(0 if result.wasSuccessful() else 1)

manifest = json.loads(Path('/input/input-manifest.json').read_bytes())
for name, want in manifest['files'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == want, name
emit('frozen-helper-inputs', source=manifest['source'], files=manifest['files'])
for label, flag, seconds in [('pure', '0', 30), ('helper', '1', 90)]:
    env = dict(os.environ, NOF1_SYMBOLIC_QUALIFY=flag)
    start = time.monotonic()
    emit('phase-start', phase=label)
    run = subprocess.run([sys.executable, __file__, '--'+label], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=seconds)
    (OUT/(label+'.log')).write_bytes(run.stdout)
    emit('phase-end', phase=label, seconds=time.monotonic()-start, exit_code=run.returncode)
    if run.returncode:
        print(run.stdout.decode(errors='replace'), flush=True)
        raise SystemExit(run.returncode)
emit('terminal', status='passed-light-only', whole_model_build=False, fit=False)
