"""Actual hanging-container negative control for the PA3 external watchdog."""
import argparse
import json
from pathlib import Path
import uuid
from capture import run
from run_pa3_prefit import RUNTIME,bounded_container


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    name='remission-pa3-watchdog-'+uuid.uuid4().hex[:12];volume=name+'-output'
    limits=['--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges']
    def command(argv):
        outcome,metadata=run(argv,args.evidence/'commands',timeout_seconds=30)
        if outcome.returncode:raise RuntimeError(metadata)
        return outcome.stdout.decode().strip()
    command(['docker','volume','create',volume])
    command(['docker','run','--rm',*limits,'--user','0:0','--mount',f'type=volume,src={volume},dst=/output',
             '--entrypoint','python',RUNTIME,'-c',"from pathlib import Path;Path('/output').chmod(0o777)"])
    code="from pathlib import Path;import time;Path('/output/partial.json').write_text('{\"stage\":\"hang-negative-control\"}');print('partial-written-before-hang',flush=True);time.sleep(3600)"
    argv=['docker','run','--name',name,*limits,'--user','10002:10002','--mount',f'type=volume,src={volume},dst=/output',
          '--entrypoint','python',RUNTIME,'-c',code]
    outcome,metadata=bounded_container(argv,name,args.evidence/'commands',2)
    state=json.loads(command(['docker','inspect',name,'--format','{{json .State}}']))
    command(['docker','cp',name+':/output/partial.json',str(args.evidence/'partial.json')])
    partial=json.loads((args.evidence/'partial.json').read_text())
    accepted=metadata['timed_out'] and not state['Running'] and state['ExitCode']==137 and not state['OOMKilled'] and partial['stage']=='hang-negative-control'
    result=dict(accepted=accepted,container=name,volume=volume,timeout_seconds=2,cli_exit=outcome.returncode,
                state=state,partial=partial)
    (args.evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    if not accepted:raise RuntimeError('watchdog negative control failed')


if __name__=='__main__':main()
