"""Required merged suites only; no source writes or statistical production jobs."""
import subprocess
import sys

checks = [
    ['docs/implementation/evidence/G1-OBS-REP/implementation/schema_checks.py'],
    ['-m', 'unittest', 'discover', '-s', 'tests/contracts', '-v'],
    ['-m', 'unittest', 'discover', '-s', 'tests/run_contracts', '-v'],
    ['-m', 'unittest', 'discover', '-s', 'tests/integration/replay', '-v'],
    ['docs/implementation/evidence/G1-OBS-REP/repair-01/re_admit_independent.py'],
]
for command in checks:
    print('MERGED CHECK', ' '.join(command), flush=True)
    subprocess.run([sys.executable, *command], check=True)
print('PASS: merged required domain/run/service/export/runtime/artifact/DR and unchanged independent full85 wire checks')
