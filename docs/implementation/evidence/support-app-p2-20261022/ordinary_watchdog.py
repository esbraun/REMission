"""Retained literal-CID watchdog; ready before start, independent typed State."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def inspect(cid):
    result=subprocess.run(['docker','inspect','--format','{"Id":{{json .Id}},"State":{{json .State}}}',cid],capture_output=True,text=True,timeout=3,check=True)
    value=json.loads(result.stdout)
    if value.get('Id')!=cid:raise ValueError('Watchdog exact-CID mismatch')
    state=value['State']
    if (type(state.get('Running')) is not bool or type(state.get('Pid')) is not int or state['Pid']<0
            or type(state.get('ExitCode')) is not int or type(state.get('OOMKilled')) is not bool
            or state.get('Status') not in ('created','running','paused','restarting','removing','exited','dead')):
        raise ValueError('Watchdog malformed State')
    return state


def stopped(state):return state['Status'] in ('exited','dead') and state['Running'] is False and state['Pid']==0


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--watchdog-cid',required=True);parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--seconds',type=int,choices=[180],required=True)
    args=parser.parse_args();cid=args.watchdog_cid;folder=args.evidence
    if not re.fullmatch('[0-9a-f]{64}',cid):raise ValueError('literal CID required')
    deadline=time.monotonic()+args.seconds;failure=None;terminal=None
    save(folder/'watchdog-ready.json',dict(cid=cid,pid=os.getpid(),seconds=args.seconds,armed_at=datetime.now(timezone.utc).isoformat()))
    try:
        while True:
            current=inspect(cid)
            if stopped(current):terminal=current;break
            if time.monotonic()>=deadline:
                failure='ordinary test external deadline exceeded'
                result=subprocess.run(['docker','kill',cid],capture_output=True,text=True,timeout=5)
                save(folder/'watchdog-deadline-kill.json',dict(cid=cid,exit=result.returncode,stdout=result.stdout,stderr=result.stderr))
                terminal=inspect(cid)
                if not stopped(terminal):raise RuntimeError('STOP UNCONFIRMED')
                break
            time.sleep(.5)
    except BaseException as error:failure=failure or repr(error)
    save(folder/'watchdog-terminal.json',dict(cid=cid,events=[dict(terminal=terminal)] if terminal else [],failure=failure,
        ended_at=datetime.now(timezone.utc).isoformat()))
    return 1 if failure else 0


if __name__=='__main__':sys.exit(main())
