"""B3.1 guarded scalar/contract SOURCE checks; never full generation/runtime."""
import sys


def audit(event,args):
    if event in ('ctypes.dlopen','ctypes.dlsym','subprocess.Popen','os.system','os.spawn','sqlite3.connect','socket.__new__','socket.connect','socket.getaddrinfo'):
        raise AssertionError('native/process/network/SQLite forbidden in SOURCE')


sys.addaudithook(audit)
import builtins
from contextlib import ExitStack
import importlib.abc
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'artifacts/breadth-source'


if __name__=='__main__':
    OUTPUT.mkdir(parents=True,exist_ok=True);sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
    blocked={'apps','sqlite3','sqlalchemy','numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas',
        'statsmodels','ctypes','_ctypes','requests','winreg','win32api','win32file','win32security','psutil','methods'}
    preloaded=blocked.intersection(sys.modules);assert not preloaded-{'winreg'}
    allowed_services={'services','services.generator','services.generator.breadth'}
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in blocked or fullname.startswith('services') and fullname not in allowed_services:
                raise AssertionError('forbidden SOURCE import: '+fullname)
    sys.meta_path.insert(0,Guard())
    def refuse(*args,**kwargs):raise AssertionError('SOURCE access forbidden')
    roots=[str(p).replace('\\','/').lower() for p in (ROOT,Path(sys.prefix),Path(sys.base_prefix))]
    def permitted(path):
        if isinstance(path,int):raise AssertionError('descriptor IO forbidden')
        value=os.path.abspath(os.fspath(path)).replace('\\','/').lower()
        if any(word in value for word in ('/private/','/private-','/auth.json','/raw/','/results/','/supplemental-blind','/supplemental_blind')) or not any(value==r or value.startswith(r+'/') for r in roots):
            raise AssertionError('private/current/historical filesystem forbidden')
    original_open,original_io_open=builtins.open,io.open;original_stat,original_lstat=os.stat,os.lstat
    def open_guard(path,*a,**kw):permitted(path);return original_open(path,*a,**kw)
    def io_guard(path,*a,**kw):permitted(path);return original_io_open(path,*a,**kw)
    def stat_guard(path,*a,**kw):permitted(path);return original_stat(path,*a,**kw)
    def lstat_guard(path,*a,**kw):permitted(path);return original_lstat(path,*a,**kw)
    with ExitStack() as guards:
        for obj,name,value in ((os,'environ',{}),(subprocess,'Popen',refuse),(subprocess,'run',refuse),(os,'system',refuse),
                (socket,'socket',refuse),(socket,'create_connection',refuse),(socket,'getaddrinfo',refuse),
                (builtins,'open',open_guard),(io,'open',io_guard),(os,'stat',stat_guard),(os,'lstat',lstat_guard)):
            guards.enter_context(patch.object(obj,name,value))
        loaded=sys.modules.get('_winapi')
        if loaded:
            for name in ('CreateProcess','OpenProcess'):
                if hasattr(loaded,name):guards.enter_context(patch.object(loaded,name,refuse))
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_breadth_source'))
        record=dict(scope='B3.1 SOURCE: scalar short fixtures/Pydantic/lineage only',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
            status='PASS' if result.wasSuccessful() else 'FAIL',full_generation=False,scientific_qualification=False,model_consumption=False,
            app_Store_SQLite=False,private=False,host_environment_copy=False,native_or_network=False)
        OUTPUT.joinpath('checks.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    assert not blocked.intersection(sys.modules)-preloaded
    print('SOURCE ONLY: no full cohort generation, numerical imports, model consumption, runtime or scientific qualification')
    sys.exit(not result.wasSuccessful())
