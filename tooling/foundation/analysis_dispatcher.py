"""One local host dispatcher. Docker control never enters the web container."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
COMMON=['--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
        '--tmpfs','/tmp:rw,nosuid,size=256m']


def command(argv, *, check=True):
    result=subprocess.run(argv,capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[:2000])
    return result


def exclusive(path):
    """Kernel lock is released on crash. Same deployment cannot have two hosts."""
    stream=path.open('a+b')
    if stream.tell()==0:
        stream.write(b'0');stream.flush()
    stream.seek(0)
    if os.name=='nt':
        import msvcrt
        msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
    else:
        import fcntl
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
    return stream


def check_deadline(deadline):
    if time.monotonic()>deadline:raise TimeoutError('fit-watchdog-deadline-exceeded')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--deployment',type=Path,required=True);parser.add_argument('--once',action='store_true')
    args=parser.parse_args()
    state=json.loads(args.deployment.read_bytes())
    root=args.deployment.resolve().parent/'analysis-jobs'
    root.mkdir(parents=True,exist_ok=True)
    lock=exclusive(root/'dispatcher.lock')
    service=state['service_container'];image=state['learner_image'];prefix=state['prefix']
    def cli(*values):
        result=command(['docker','exec',service,'python','-m','services.foundation.analysis_cli',*values])
        return json.loads(result.stdout)
    # All preceding fit processes must stop BEFORE marking their attempts failed.
    prior=command(['docker','ps','-aq','--filter','label=remission.analysis='+prefix]).stdout.decode().split()
    for name in prior:
        command(['docker','stop','--time','10',name],check=False)
        inventory=json.loads(command(['docker','inspect',name]).stdout)[0]
        identifier=inventory['Config']['Labels'].get('remission.attempt')
        if identifier and identifier.startswith('analysis-') and Path(identifier).name==identifier:
            saved=root/identifier
            saved.mkdir(exist_ok=True)
            stamp=str(time.time_ns())
            logs=command(['docker','logs',name],check=False)
            (saved/('restart-'+stamp+'.stdout')).write_bytes(logs.stdout)
            (saved/('restart-'+stamp+'.stderr')).write_bytes(logs.stderr)
            command(['docker','cp',name+':/output/.',str(saved/('restart-output-'+stamp))],check=False)
    cli('interrupt')
    print(json.dumps(dict(stage='dispatcher-ready',pid=os.getpid(),source_head=state['source_commit'],learner_image=image)),flush=True)
    while True:
        job=cli('claim')
        if job is None:
            if args.once:
                break
            time.sleep(2)
            continue
        identifier=job['attempt_id'];token=job['claim_token'];directory=root/identifier
        attempt_started=time.monotonic()
        directory.mkdir(exist_ok=False)
        (directory/'input.json').write_text(json.dumps(job['input'],sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
        # Claim token stays with the host supervisor, never with the learner.
        learner=prefix+'-'+identifier
        input_volume=learner+'-input';output_volume=learner+'-output';helper=learner+'-stage'
        manifest=dict(attempt_id=identifier,source_head=state['source_commit'],learner_image=image,input_volume=input_volume,
                      output_volume=output_volume,container=learner,started_unix=time.time(),status='preparing')
        def save():
            (directory/'dispatch.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        save()
        launched=False
        try:
            for volume in (input_volume,output_volume):
                command(['docker','volume','create','--label','remission.task='+prefix,volume])
            command(['docker','create','--name',helper,*COMMON,'--cap-add','CHOWN','--user','0:0',
                '--mount',f'type=volume,source={input_volume},target=/input',
                '--mount',f'type=volume,source={output_volume},target=/output',image,'python','-c',
                "import os;os.chmod('/input',0o755);os.chmod('/input/input.json',0o444);os.chown('/input/input.json',10002,10002);os.chmod('/output',0o700);os.chown('/output',10002,10002)"])
            command(['docker','cp',str(directory/'input.json'),helper+':/input/input.json'])
            command(['docker','start','--attach',helper])
            command(['docker','rm',helper])
            command(['docker','run','--detach','--name',learner,'--label','remission.analysis='+prefix,'--label','remission.attempt='+identifier,*COMMON,
                '--user','10002:10002','--mount',f'type=volume,source={input_volume},target=/input,readonly',
                '--mount',f'type=volume,source={output_volume},target=/output','-e','REMISSION_LEARNER_IMAGE='+image,'-e','REMISSION_SOURCE_COMMIT='+state['source_commit'],
                image,'python','-m','services.learner.analysis_worker','--input','/input/input.json','--output','/output'])
            launched=True
            manifest.update(status='running',inventory=json.loads(command(['docker','inspect',learner]).stdout)[0])
            save()
            last=None
            borrowing=job['input'].get('kind')=='poc_visit_borrow_input'
            watchdog_seconds=7200 if borrowing else 4*3600
            manifest['watchdog_seconds']=watchdog_seconds
            deadline=(attempt_started if borrowing else time.monotonic())+watchdog_seconds
            while True:
                inventory=json.loads(command(['docker','inspect',learner]).stdout)[0]
                # Check BEFORE trusting terminal state: completion between polls
                # after the cap cannot escape the same frozen deadline.
                check_deadline(deadline)
                if not inventory['State']['Running']:
                    break
                copied=command(['docker','cp',learner+':/output/progress.json',str(directory/'progress.json')],check=False)
                if copied.returncode==0:
                    value=json.loads((directory/'progress.json').read_bytes())
                    encoded=json.dumps(value,sort_keys=True,separators=(',',':'))
                    if encoded!=last and value['stage'] in ('preparing','fitting','diagnostics','rollouts'):
                        cli('progress','--job',identifier,'--token',token,'--value',encoded)
                        last=encoded
                time.sleep(2)
            logs=command(['docker','logs',learner],check=False)
            (directory/'worker.stdout').write_bytes(logs.stdout);(directory/'worker.stderr').write_bytes(logs.stderr)
            command(['docker','cp',learner+':/output/.',str(directory/'output')])
            (directory/'output'/'worker.stdout').write_bytes(logs.stdout)
            (directory/'output'/'worker.stderr').write_bytes(logs.stderr)
            # Stopped output is copied into the service's established artifact
            # volume; learner never mounts that volume or the service database.
            dest='/exports/analyses/'+identifier
            command(['docker','exec',service,'mkdir','-p',dest])
            command(['docker','cp',str(directory/'output')+'/.',service+':'+dest])
            check_deadline(deadline)
            response=cli('ingest','--job',identifier,'--token',token,'--directory',dest)
            manifest.update(status=response['status'],exit=inventory['State']['ExitCode'],oom_killed=inventory['State']['OOMKilled'])
        except Exception as error:
            command(['docker','stop','--time','10',learner],check=False)
            if launched:
                stopped=command(['docker','inspect',learner],check=False)
                confirmed=stopped.returncode==0 and not json.loads(stopped.stdout)[0]['State']['Running']
                if not confirmed:
                    command(['docker','kill',learner],check=False)
                    stopped=command(['docker','inspect',learner],check=False)
                    confirmed=stopped.returncode==0 and not json.loads(stopped.stdout)[0]['State']['Running']
                if not confirmed:
                    manifest.update(status='worker-stop-unconfirmed',failure=str(error));save()
                    raise RuntimeError('Owned worker termination unconfirmed; retain live handle '+learner) from error
                manifest['worker_stop_verified']=True
            logs=command(['docker','logs',learner],check=False)
            (directory/'failure-worker.stdout').write_bytes(logs.stdout);(directory/'failure-worker.stderr').write_bytes(logs.stderr)
            command(['docker','cp',learner+':/output/.',str(directory/'failure-output')],check=False)
            message=str(error)
            manifest.update(status='failed',failure=message)
            (directory/'dispatcher-failure.log').write_text(message,encoding='utf-8')
            try:
                cli('fail','--job',identifier,'--token',token,'--value',message)
            except Exception as failed:
                manifest['ingestion_failure']=str(failed)
        manifest['finished_unix']=time.time()
        save()
        print(json.dumps({k:v for k,v in manifest.items() if k!='inventory'}),flush=True)
        if args.once:
            break
    lock.close()


if __name__=='__main__':
    main()
