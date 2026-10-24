"""DATA03 source/scalar/double controls only; never launches a real workload."""
import importlib.abc
from pathlib import Path
import subprocess
import socket
import sys
import unittest

BLOCKED={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','statsmodels','pandas','xarray','methods','sqlite3','ctypes'}
class Tripwire(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED or fullname.startswith(('services.foundation.app','services.foundation.store','services.generator')):
            raise AssertionError('DATA03 PREPARATION import blocked: '+fullname)
def no_process(*_args,**_kwargs):raise AssertionError('DATA03 PREPARATION real process blocked')
class NoChild(subprocess.Popen):
    def __init__(self,*args,**kwargs):no_process()

if __name__=='__main__':
    sys.meta_path.insert(0,Tripwire());subprocess.Popen=NoChild;subprocess.run=no_process
    socket.create_connection=no_process;socket.getaddrinfo=no_process
    root=Path(__file__).resolve().parents[1]
    sys.path[:0]=[str(root),str(root/'tests'),str(root/'tooling/foundation')]
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_n_data03_source'))
    assert not BLOCKED.intersection(sys.modules),'blocked module loaded'
    print('DATA03 source/scalar/process-double tripwire: PASS; no actual workflow or runtime acceptance')
    sys.exit(not result.wasSuccessful())
