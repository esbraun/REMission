"""Literal-CID supervision for the existing one-shot dispatcher; host stdlib only.

No discovery cleanup, removal, retries or numerical work. All evidence is retained.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time

STATE_FORMAT='{"Id":{{json .Id}},"State":{{json .State}},"RestartCount":{{json .RestartCount}}}'


class StopUnconfirmed(RuntimeError):
    pass


def save(path, value):
    # Publish complete bytes with exclusive creation: readers never see a partial
    # receipt, and an existing (including stale) receipt is never overwritten.
    path=Path(path)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                prefix='.'+path.name+'-',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary,path)
    finally:
        if temporary is not None:temporary.unlink()


def check_deadline(deadline):
    if not math.isfinite(deadline) or time.monotonic() >= deadline:
        raise TimeoutError('absolute analysis deadline exceeded')


def command(argv, *, check=True, deadline=None, cap=15):
    timeout=cap
    if deadline is not None:
        check_deadline(deadline)
        timeout=min(cap, deadline-time.monotonic())
    result=subprocess.run(argv, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError('command failed: '+result.stderr.decode(errors='replace')[:2000])
    if deadline is not None:
        check_deadline(deadline)
    return result


def require_cid(cid):
    if not isinstance(cid,str) or re.fullmatch('[a-f0-9]{64}',cid) is None:
        raise ValueError('literal full container ID required')
    return cid


def checked_state(value, cid):
    require_cid(cid)
    if not isinstance(value,dict) or value.get('Id')!=cid or type(value.get('RestartCount')) is not int or value['RestartCount']!=0:
        raise ValueError('foreign container or restarted container')
    state=value.get('State')
    if (not isinstance(state,dict) or any(type(state.get(k)) is not bool for k in ('Running','Paused','Restarting','Dead','OOMKilled'))
            or any(type(state.get(k)) is not int for k in ('Pid','ExitCode')) or state['Pid']<0
            or state.get('Status') not in ('created','running','exited','dead')
            or state['Paused'] or state['Restarting']
            or state['Running']!=(state['Status']=='running')
            or (state['Running'] and state['Pid']==0) or (not state['Running'] and state['Pid']!=0)
            or state['Dead']!=(state['Status']=='dead')):
        raise ValueError('malformed or ambiguous container State')
    return value


def inspect(cid, *, deadline=None):
    result=command(['docker','inspect','--format',STATE_FORMAT,require_cid(cid)],deadline=deadline,cap=3)
    return checked_state(json.loads(result.stdout),cid)


def stopped(value):
    state=value['State']
    return state['Running'] is False and state['Pid']==0 and state['Status'] in ('created','exited','dead')


def stop_owned(cid):
    """Cleanup has its own short caps even after the scientific deadline."""
    events=[]
    for argv in (['docker','stop','--time','1',require_cid(cid)], ['docker','kill',cid]):
        try:
            result=command(argv,check=False,cap=4)
            events.append(dict(operation=argv[1],returncode=result.returncode))
        except Exception as error:
            events.append(dict(operation=argv[1],error=repr(error)))
        try:
            observed=inspect(cid)
            events.append(dict(observed=observed))
            if stopped(observed):
                return events
        except Exception as error:
            events.append(dict(observation_error=repr(error)))
    raise StopUnconfirmed('STOP UNCONFIRMED '+cid+' '+json.dumps(events,sort_keys=True))


def receipt(path, cid, nonce, deadline, observed=None):
    value=json.loads(path.read_bytes())
    if (not isinstance(value,dict) or value.get('cid')!=cid or value.get('nonce')!=nonce
            or value.get('deadline')!=deadline or value.get('failure') is not None):
        raise ValueError('missing, stale or foreign watchdog receipt')
    terminal=checked_state(value.get('terminal'),cid)
    if not stopped(terminal) or terminal['State']['Status']=='created':
        raise ValueError('watchdog did not observe a terminal workload')
    if observed is not None and terminal!=observed:
        raise ValueError('watchdog and independent terminal State disagree')
    return value


def watchdog(cid, folder, deadline, nonce):
    failure=None;terminal=None;cleanup=[]
    try:
        check_deadline(deadline)
        initial=inspect(cid,deadline=deadline)
        if initial['State']['Status']!='created':
            raise ValueError('watchdog must arm before start')
        save(folder/'watchdog-ready.json',dict(cid=cid,nonce=nonce,deadline=deadline,pid=os.getpid()))
        while True:
            check_deadline(deadline)
            observed=inspect(cid,deadline=deadline)
            check_deadline(deadline)  # late terminal observations never pass
            if stopped(observed) and observed['State']['Status']!='created':
                terminal=observed
                break
            time.sleep(min(.1,max(0,deadline-time.monotonic())))
    except BaseException as error:
        failure=repr(error)
        try:cleanup=stop_owned(cid)
        except BaseException as stop_error:cleanup.append(dict(stop_error=repr(stop_error)))
    finally:
        save(folder/'watchdog-terminal.json',dict(cid=cid,nonce=nonce,deadline=deadline,
            terminal=terminal,failure=failure,cleanup=cleanup))
    return 1 if failure else 0


def reap(process):
    if process is None:return None
    try:return process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=2)


def supervise(cid, folder, deadline, on_poll=None):
    """Prearm, start, audit and reap one already created literal CID."""
    require_cid(cid);folder.mkdir(exist_ok=False)
    child=None;attached=None;primary=None;cleanup=[];terminal=None;codes={};nonce=secrets.token_hex(24)
    expected=dict(cid=cid,nonce=nonce,deadline=deadline,pid=None)
    prearm=dict(interpreter=sys.executable,flags=['-P','-B'],argv=None,popen_pid=None,
        expected=expected,received=None,received_invalid_fields=None,mismatch_fields=None,identity_matched=False,live_ack_before_start=False,
        before_ready_poll=dict(observed=False,returncode=None),after_ready_poll=dict(observed=False,returncode=None))
    processes={}
    def public_identity_value(key,value):
        # Diagnostics must remain bounded/serializable even for a rejected
        # receipt. Keep equality below on the original, unmodified receipt.
        if key in ('cid','nonce'):
            length=64 if key=='cid' else 48
            valid=type(value) is str and len(value)==length and re.fullmatch('[a-f0-9]+',value) is not None
        elif key=='pid':valid=type(value) is int and 0<value<=0xffffffff
        else:valid=type(value) in (int,float) and 0<value<=1e12 and math.isfinite(value)
        return value if valid else dict(invalid_type=type(value).__name__)
    try:
        check_deadline(deadline)
        if inspect(cid,deadline=deadline)['State']['Status']!='created':raise ValueError('workload already started')
        with (folder/'watchdog.stdout').open('wb') as wo, (folder/'watchdog.stderr').open('wb') as we, \
                (folder/'attach.stdout').open('wb') as ao, (folder/'attach.stderr').open('wb') as ae:
            prearm['argv']=[sys.executable,'-P','-B',str(Path(__file__).resolve()),'--watchdog-cid',cid,
                '--folder',str(folder),'--deadline',str(deadline),'--nonce',nonce]
            prearm['creationflags']=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            child=subprocess.Popen(prearm['argv'],stdout=wo,stderr=we,creationflags=prearm['creationflags'])
            prearm['popen_pid']=child.pid
            expected['pid']=child.pid
            arm_deadline=min(deadline,time.monotonic()+5)
            while True:
                check_deadline(arm_deadline)
                code=child.poll();prearm['before_ready_poll']=dict(observed=True,returncode=code)
                if code is not None:raise RuntimeError('watchdog exited before start')
                ready=folder/'watchdog-ready.json'
                if ready.exists():
                    value=json.loads(ready.read_bytes())
                    prearm['received_type']=type(value).__name__
                    if isinstance(value,dict):
                        prearm['received']={key:public_identity_value(key,value.get(key)) for key in expected}
                        prearm['received_invalid_fields']=[key for key,item in prearm['received'].items() if isinstance(item,dict)]
                        prearm['mismatch_fields']=[key for key in expected if key not in value or value[key]!=expected[key]]
                        if set(value)!=set(expected):prearm['mismatch_fields'].append('keys')
                    else:prearm['mismatch_fields']=['receipt_type']
                    if value!=expected:raise ValueError('invalid watchdog arm receipt')
                    prearm['identity_matched']=True
                    break
                time.sleep(.05)
            check_deadline(deadline)
            code=child.poll();prearm['after_ready_poll']=dict(observed=True,returncode=code)
            if code is not None:raise RuntimeError('watchdog died after arming')
            prearm['live_ack_before_start']=True
            attached=subprocess.Popen(['docker','start','--attach',cid],stdout=ao,stderr=ae,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            while True:
                check_deadline(deadline)
                watch_code=child.poll();attach_code=attached.poll()
                if watch_code is not None or attach_code is not None:
                    # Either completion order gets the same fresh independent audit.
                    if watch_code is not None and watch_code!=0:raise RuntimeError('watchdog failed')
                    if attach_code is not None and attach_code!=0:raise RuntimeError('attach failed')
                    if watch_code is None:child.wait(timeout=min(3,max(.001,deadline-time.monotonic())))
                    if attach_code is None:attached.wait(timeout=min(3,max(.001,deadline-time.monotonic())))
                    check_deadline(deadline)
                    terminal=inspect(cid,deadline=deadline)
                    receipt(folder/'watchdog-terminal.json',cid,nonce,deadline,terminal)
                    if child.returncode!=0 or attached.returncode!=0:raise RuntimeError('supervisor process failed')
                    state=terminal['State']
                    if state['Status']!='exited' or state['Dead'] or state['ExitCode']!=0 or state['OOMKilled']:
                        raise RuntimeError('workload exited unsuccessfully')
                    break
                if on_poll is not None:on_poll()
                time.sleep(.1)
    except BaseException as error:
        primary=repr(error)
    finally:
        if primary is not None:
            try:cleanup.extend(stop_owned(cid))
            except BaseException as error:cleanup.append(dict(stop_error=repr(error)))
        for name,process in (('attach',attached),('watchdog',child)):
            processes[name]=dict(created=process is not None,pid=process.pid if process is not None else None,
                reaped=False,returncode=None)
            try:
                codes[name]=reap(process)
                processes[name].update(reaped=process is not None,returncode=codes[name])
            except BaseException as error:cleanup.append(dict(process=name,reap_error=repr(error)))
        # Reaping a Docker client does not prove the owned workload stopped.
        try:
            terminal=inspect(cid)
            if not stopped(terminal):raise StopUnconfirmed('owned container remains live')
            if primary is None:receipt(folder/'watchdog-terminal.json',cid,nonce,deadline,terminal)
        except BaseException as error:
            cleanup.append(dict(final_observation_error=repr(error)))
            primary=primary or repr(error)
            try:
                cleanup.extend(stop_owned(cid))
                terminal=inspect(cid)
                if not stopped(terminal):terminal=None
            except BaseException as stop_error:
                cleanup.append(dict(final_stop_error=repr(stop_error)))
                terminal=None
        result=dict(cid=cid,deadline=deadline,failure=primary,cleanup=cleanup,returncodes=codes,terminal=terminal,
            prearm=prearm,processes=processes,host_descendant_termination='UNKNOWN')
        save(folder/'supervision.json',result)
    if terminal is None or any('reap_error' in event for event in cleanup):
        raise StopUnconfirmed('STOP UNCONFIRMED '+cid+'; retained supervision evidence')
    if primary is not None:raise RuntimeError(primary)
    return terminal


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--watchdog-cid',required=True)
    parser.add_argument('--folder',type=Path,required=True);parser.add_argument('--deadline',type=float,required=True)
    parser.add_argument('--nonce',required=True);args=parser.parse_args()
    sys.exit(watchdog(require_cid(args.watchdog_cid),args.folder,args.deadline,args.nonce))
