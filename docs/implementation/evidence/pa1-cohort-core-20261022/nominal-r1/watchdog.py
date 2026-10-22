"""One literal-container external UTC deadline; no model or configuration changes."""
import datetime,json,os,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[1]);config=json.loads((root/'watchdog-config.json').read_text())
identifier=config['container_id'];deadline=datetime.datetime.fromisoformat(config['deadline'])
assert len(identifier)==64 and all(c in '0123456789abcdef' for c in identifier)
def write(name,value):(root/name).write_text(json.dumps(value,indent=2)+'\n')
write('watchdog-ready.json',dict(pid=os.getpid(),container_id=identifier,deadline=config['deadline'],
    armed_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
while True:
    state=subprocess.run(['docker','inspect',identifier,'--format','{{json .State}}'],capture_output=True,text=True,timeout=15)
    if state.returncode:
        write('watchdog-inspect-error.json',dict(exit=state.returncode,stderr=state.stderr))
    else:
        value=json.loads(state.stdout)
        if value['Status'] in ('exited','dead'):
            write('watchdog-terminal.json',dict(observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),state=value,deadline_reached=False));break
    if datetime.datetime.now(datetime.timezone.utc)>=deadline:
        stopped=subprocess.run(['docker','stop','--time','0',identifier],capture_output=True,text=True,timeout=30)
        after=subprocess.run(['docker','inspect',identifier,'--format','{{json .State}}'],capture_output=True,text=True,timeout=15)
        final=json.loads(after.stdout) if after.returncode==0 else None
        if final and final['Running']:
            killed=subprocess.run(['docker','kill',identifier],capture_output=True,text=True,timeout=30)
            write('watchdog-kill.json',dict(exit=killed.returncode,stdout=killed.stdout,stderr=killed.stderr))
            after=subprocess.run(['docker','inspect',identifier,'--format','{{json .State}}'],capture_output=True,text=True,timeout=15)
            final=json.loads(after.stdout) if after.returncode==0 else None
        write('watchdog-terminal.json',dict(observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            deadline_reached=True,stop_exit=stopped.returncode,stop_stdout=stopped.stdout,stop_stderr=stopped.stderr,state=final));break
    time.sleep(1)
