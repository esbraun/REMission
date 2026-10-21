"""Read-only old/new schema, artifact and qualified runtime checks."""
import subprocess
import sys


def main():
    checks = [['-m', module, '--check'] for module in ['contracts.domain.export', 'contracts.dgp.export', 'contracts.runs.export',
                                                     'contracts.domain.export_v2', 'contracts.runs.export_v2']]
    checks += [['-m', 'pip', 'check'], ['tooling/foundation/qualify.py'],
               ['-m', 'unittest', 'discover', '-s', 'tests/library', '-v'],
               ['-m', 'unittest', 'discover', '-s', 'tests/library/dr', '-v']]
    for arguments in checks:
        print('CHECK', ' '.join(arguments), flush=True)
        subprocess.run([sys.executable, *arguments], check=True)


if __name__ == '__main__':
    main()
