"""Host SOURCE-only runner: active science/app/DB/process/network tripwires."""
import importlib.abc
import builtins
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch

ROOT=Path('C:\\Users\\erics\\Documents\\Projects\\REMission-worktrees\\s2-controller-review-astra-261024')
if __name__=='__main__':
    sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
    forbidden={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas',
        'statsmodels','services','adapters','apps','sqlalchemy','sqlite3','ctypes','requests','methods',
        'win32api','win32file','win32security','win32process','winreg','psutil'}
    preloaded=forbidden.intersection(sys.modules)
    assert not preloaded-{'winreg'}
    class Tripwire(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in forbidden:raise AssertionError('forbidden SOURCE import: '+fullname)
    sys.meta_path.insert(0,Tripwire())
    def refuse(*args,**kwargs):raise AssertionError('process/network forbidden in SOURCE checks')
    roots=[str(ROOT).replace('\\','/').lower(),str(Path(sys.prefix)).replace('\\','/').lower(),
           str(Path(sys.base_prefix)).replace('\\','/').lower()]
    def permitted(path):
        if isinstance(path,int):return
        value=os.path.abspath(os.fspath(path)).replace('\\','/').lower()
        if ('supplemental-blind' in value or 'supplemental_blind' in value
                or not any(value==root or value.startswith(root+'/') for root in roots)):
            raise AssertionError('private/sealed filesystem operation forbidden in SOURCE checks')
    original_open,original_io_open=builtins.open,io.open
    original_stat,original_lstat=os.stat,os.lstat
    def guarded_open(path,*args,**kwargs):permitted(path);return original_open(path,*args,**kwargs)
    def guarded_io_open(path,*args,**kwargs):permitted(path);return original_io_open(path,*args,**kwargs)
    def guarded_stat(path,*args,**kwargs):permitted(path);return original_stat(path,*args,**kwargs)
    def guarded_lstat(path,*args,**kwargs):permitted(path);return original_lstat(path,*args,**kwargs)
    with ExitStack() as guards,patch.object(subprocess,'Popen',side_effect=refuse),patch.object(subprocess,'run',side_effect=refuse), \
            patch.object(socket,'socket',side_effect=refuse),patch.object(socket,'create_connection',side_effect=refuse), \
            patch.object(socket,'getaddrinfo',side_effect=refuse),patch.object(os,'system',side_effect=refuse), \
            patch.object(builtins,'open',side_effect=guarded_open),patch.object(io,'open',side_effect=guarded_io_open), \
            patch.object(os,'stat',side_effect=guarded_stat),patch.object(os,'lstat',side_effect=guarded_lstat):
        for module,names in (('winreg',('OpenKey','OpenKeyEx','CreateKey','CreateKeyEx','QueryValue','QueryValueEx','SetValue','SetValueEx','DeleteKey','DeleteValue','ConnectRegistry')),
                             ('_winapi',('CreateProcess','OpenProcess'))):
            loaded=sys.modules.get(module)
            if loaded:
                for name in names:
                    if hasattr(loaded,name):guards.enter_context(patch.object(loaded,name,side_effect=refuse))
        import test_s2_controller_source as t
        code,db,p,state,d,a=t.DispatchAuthorityTests().preparation(expires=t.AT+t.timedelta(hours=4))
        offered,canceled=code['dispatch'](db,t.NS(fault=None),p,state,d,a,t.AT)
        assert offered is None and canceled
        print('PASS original16:00consent/20:00dispatch counterexample now cancels')
        code,db,p,state,a,h,inv,go,receipt,run,flow=t.CandidateBootstrapTests().preparation();now=[t.AT]
        h['UNIT_transaction'].__wrapped__.__globals__['receive']=lambda current,at:now.__setitem__(0,inv.expires_at+t.timedelta(seconds=1))
        try:run(t.NS(clock=lambda:now[0],fault=None))
        except ValueError as e:assert 'expired' in str(e)
        else:raise AssertionError('late candidate accepted')
        assert not getattr(db,'committed',False) and receipt.getvalue()
        print('PASS original latejournal counterexample now rollsback consumedreceipt')
        code,db,p,state,a,h,inv,go,receipt,run,flow=t.CandidateBootstrapTests().preparation(later_consent_action='withdraw')
        sql=[];execute=db.execute
        def trace(query,args=()):sql.append(query);return execute(query,args)
        db.execute=trace
        run()
        assert not any('INSERT' in q.upper() and 'TASK' in q.upper() for q in sql)
        print('REPRO successful actual withdrawal command has no task insert; final loop=',t.json.loads(db.patient['state_json'])['simulation']['support_controller']['status'])
        for sequence in [('withdraw','advance'),('withdraw','consent','advance')]:
            code,db,p,state,a,h,inv,go,receipt,run,flow=t.CandidateBootstrapTests().preparation(later_consent_action=sequence)
            try:run()
            except Exception as e:print('REPRO subsequent ordinary advance after',sequence,'refuses:',type(e).__name__,str(e))
            else:print('advance succeeded',sequence)
        result=unittest.TestResult()
        if False:
            from freeze_s2_controller_source import freeze
            freeze(ROOT,result)
    assert not forbidden.intersection(sys.modules)-preloaded
    print('SOURCE ONLY: actual scalar/contract/AST bodies with inert typed records/transactions; no app/SQLite/science/process/network')
    sys.exit(not result.wasSuccessful())
