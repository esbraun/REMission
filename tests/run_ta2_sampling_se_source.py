"""Isolated TA2 SE SOURCE controls; active private/app/science/native tripwires."""
import builtins
from contextlib import ExitStack
import importlib.abc
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
    forbidden={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas','statsmodels',
        'services','apps','sqlite3','sqlalchemy','ctypes','requests','winreg','win32api','win32file','win32security','win32process','psutil'}
    preloaded=forbidden.intersection(sys.modules)
    assert not preloaded-{'winreg'}
    safe_methods={'methods','methods.truth','methods.truth.sampling_se','methods.truth.refinement'}
    class Tripwire(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden or fullname.startswith('methods.') and fullname not in safe_methods:
                raise AssertionError('forbidden SOURCE import: '+fullname)
    sys.meta_path.insert(0,Tripwire())
    def refuse(*args,**kwargs):raise AssertionError('process/network/native forbidden in SOURCE controls')
    roots=[str(p).replace('\\','/').lower() for p in (ROOT,Path(sys.prefix),Path(sys.base_prefix))]
    def permitted(path):
        if isinstance(path,int):return
        value=os.path.abspath(os.fspath(path)).replace('\\','/').lower()
        if ('supplemental-blind' in value or 'supplemental_blind' in value or '/raw/' in value
                or not any(value==r or value.startswith(r+'/') for r in roots)):
            raise AssertionError('private/sealed/historical raw filesystem forbidden in SOURCE controls')
    original_open,original_io_open=builtins.open,io.open
    original_stat,original_lstat=os.stat,os.lstat
    def guarded_open(path,*args,**kwargs):permitted(path);return original_open(path,*args,**kwargs)
    def guarded_io_open(path,*args,**kwargs):permitted(path);return original_io_open(path,*args,**kwargs)
    def guarded_stat(path,*args,**kwargs):permitted(path);return original_stat(path,*args,**kwargs)
    def guarded_lstat(path,*args,**kwargs):permitted(path);return original_lstat(path,*args,**kwargs)
    with ExitStack() as guards:
        for obj,name,replacement in ((subprocess,'Popen',refuse),(subprocess,'run',refuse),(os,'system',refuse),
                (socket,'socket',refuse),(socket,'create_connection',refuse),(socket,'getaddrinfo',refuse),
                (builtins,'open',guarded_open),(io,'open',guarded_io_open),(os,'stat',guarded_stat),(os,'lstat',guarded_lstat)):
            guards.enter_context(patch.object(obj,name,replacement))
        for module,names in (('winreg',('OpenKey','OpenKeyEx','CreateKey','CreateKeyEx','QueryValue','QueryValueEx','SetValue','SetValueEx','DeleteKey','DeleteValue','ConnectRegistry')),
                             ('_winapi',('CreateProcess','OpenProcess'))):
            loaded=sys.modules.get(module)
            if loaded:
                for name in names:
                    if hasattr(loaded,name):guards.enter_context(patch.object(loaded,name,refuse))
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_ta2_sampling_se_source'))
        from methods.truth import sampling_se as s
        output=ROOT/'artifacts/ta2-sampling-se-source'
        output.joinpath('checks.json').write_text(json.dumps(dict(scope='guarded SOURCE/Pydantic/hand-scalar/inert admission only',
            tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),expected_failures=len(result.expectedFailures),
            status='PASS' if result.wasSuccessful() else 'FAIL',actual_fit=False,actual_artifact_admission=False,actual_study=False,
            actual_app_Store_SQLite=False,actual_runtime_GO=False,retained_numerics='17/18 oneFAIL unchanged; no sealed operation'),sort_keys=True,indent=2)+'\n')
        if result.wasSuccessful():
            models=(s.SamplingDesign,s.PlannedCohort,s.CohortAttempt,s.AdmittedWholeCohort,s.MemberTarget,s.ReductionRow,s.SamplingSEBinding)
            output.joinpath('schema.json').write_text(json.dumps({m.__name__:m.model_json_schema() for m in models},sort_keys=True,indent=2)+'\n')
    assert not forbidden.intersection(sys.modules)-preloaded
    print('SOURCE ONLY: hand scalar/Pydantic and inert admission; no actual fits/artifact qualification/study/app/Store/SQLite/science/native/network')
    sys.exit(not result.wasSuccessful())
