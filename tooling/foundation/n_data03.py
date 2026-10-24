"""One separately authorized DATA03 attempt. Host stdlib; no action on import.

Consumes a fresh output reservation, owns one direct-base worker, reuses the
accepted CID lifecycle/regular-file CLI helper and retains all resources.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

APP='sha256:4c293e2de7f89fc484e575f23e7af7505b28a72d4a6b35f944aa3da56c6040fd'
GEN='sha256:d64907d76a2810d2e6cad8acaa012f3df132ced69bfe2636c7eb07f7090b4eee'
OWNER='sha256:a8e8aa54c20ac6011d0fb108d6c626ff693a518e50acb87fb62679e61e0279a4'
NETWORK='7638c2cac0dd63cfff83c8321a30b3763b0e42be8cb09603d11476ba66a2443d'
NETWORK_NAME='remission-cloud-fixture-6e48c02af5b9-private'
BOUNDS=dict(outer=7200,work=7140,setup=180,ownership=30,readiness=30,request=180,metadata=5,create=10,cli_reap=2)
IMAGE_FORMAT='{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"User":{{json .Config.User}}}'
NETWORK_FORMAT='{"Id":{{json .Id}},"Name":{{json .Name}},"Driver":{{json .Driver}},"Internal":{{json .Internal}},"Labels":{{json .Labels}},"IPAM":{{json .IPAM.Config}},"Containers":{{json .Containers}}}'
CONTAINER_FORMAT='{"Id":{{json .Id}},"Image":{{json .Image}},"User":{{json .Config.User}},"Path":{{json .Path}},"Args":{{json .Args}},"Labels":{{json .Config.Labels}},"State":{{json .State}},"RestartCount":{{json .RestartCount}},"Memory":{{json .HostConfig.Memory}},"MemorySwap":{{json .HostConfig.MemorySwap}},"NanoCpus":{{json .HostConfig.NanoCpus}},"PidsLimit":{{json .HostConfig.PidsLimit}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Privileged":{{json .HostConfig.Privileged}},"CapAdd":{{json .HostConfig.CapAdd}},"CapDrop":{{json .HostConfig.CapDrop}},"AutoRemove":{{json .HostConfig.AutoRemove}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"Tmpfs":{{json .HostConfig.Tmpfs}},"NetworkMode":{{json .HostConfig.NetworkMode}},"PortBindings":{{json .HostConfig.PortBindings}},"PublishAllPorts":{{json .HostConfig.PublishAllPorts}},"RestartPolicy":{{json .HostConfig.RestartPolicy}},"Mounts":{{json .Mounts}},"Networks":{{json .NetworkSettings.Networks}}}'
OWNERSHIP_CODE="""import os,json,stat
from pathlib import Path
p=Path('/data');assert os.geteuid()==os.getegid()==0
assert p.is_dir() and not p.is_symlink() and not any(p.iterdir())
os.chown(p,0,0);assert p.stat().st_uid==p.stat().st_gid==0
os.chmod(p,0o700);assert not any(p.iterdir())
os.chown(p,10001,10001);s=p.stat()
assert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(10001,10001,0o700)
print(json.dumps(dict(status='fresh_empty_private_volume_owned',uid=10001,gid=10001,mode=448)))
"""


def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(value):
    if not value:raise ValueError('DATA03 fixed binding rejected')
def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
def ordinary(path):
    path=Path(path)
    require('..' not in path.parts)
    path=path.absolute()
    require(not any(c in str(path) for c in (',','\r','\n','\x00')))
    for item in (path,*path.parents):
        require(not item.is_symlink() and not (item.exists() and getattr(item.lstat(),'st_file_attributes',0)&0x400))
    return path
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded);return loaded
def bounded_stdout(path,cap):
    with Path(path).open('rb') as stream:raw=stream.read(cap+1)
    require(len(raw)<=cap)
    return raw


def audit_network(value,*,empty):
    require(type(value) is dict and set(value)=={'Id','Name','Driver','Internal','Labels','IPAM','Containers'})
    require(value['Id']==NETWORK and value['Name']==NETWORK_NAME and value['Driver']=='bridge' and value['Internal'] is True
        and value['Labels']=={'remission.task':'remission-cloud-fixture-6e48c02af5b9'}
        and value['IPAM']==[{'Subnet':'10.253.240.0/28','Gateway':'10.253.240.1'}] and type(value['Containers']) is dict)
    if empty:require(value['Containers']=={})


def normalized_mount(value):
    value=value.replace('\\','/').rstrip('/')
    for prefix in ('/run/desktop/mnt/host/','/host_mnt/'):
        if value.startswith(prefix) and re.match('[a-zA-Z]/',value[len(prefix):]):
            value=value[len(prefix)]+':'+value[len(prefix)+1:]
    return value.lower() if re.match('[a-zA-Z]:/',value) else value


def create_argv(spec,role,lease_unix):
    prefix=spec['namespace'];ownership=role=='ownership'
    image=OWNER if ownership else APP if role=='app' else GEN
    argv=['docker','create','--name',prefix+'-'+role,'--network','none' if ownership else NETWORK_NAME,
        '--cpus','2','--memory','1g' if ownership else '2g','--memory-swap','1g' if ownership else '2g',
        '--pids-limit','64','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
        '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=128m','--restart','no','--label','remission.task='+prefix,
        '--user','0:0' if ownership else '10001:10001' if role=='app' else '20000:20000']
    if ownership:argv+=['--cap-add','CHOWN']
    else:
        for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
            argv+=['--env',name+'=1']
    if role!='generator':argv+=['--mount','type=volume,source='+spec['volume']+',target=/data']
    if role=='app':argv+=['--mount','type=bind,source='+spec['carrier']+',target=/carrier,readonly']
    if role=='generator':argv+=['--network-alias','generator']
    argv+=['--workdir','/app','--entrypoint','python',image,'-B']
    if ownership:argv+=['-c',OWNERSHIP_CODE]
    elif role=='app':argv+=['/carrier/n_data03_driver.py','--lease-unix',str(lease_unix)]
    else:argv+=['-m','services.generator.server']
    return argv


def audit_created(value,cid,spec,role,argv,life):
    life.checked_state(value,cid);ownership=role=='ownership'
    expected=dict(Image=OWNER if ownership else APP if role=='app' else GEN,
        User='0:0' if ownership else '10001:10001' if role=='app' else '20000:20000',
        Labels={'remission.task':spec['namespace']},Memory=1073741824 if ownership else 2147483648,
        MemorySwap=1073741824 if ownership else 2147483648,NanoCpus=2000000000,PidsLimit=64,
        ReadonlyRootfs=True,Privileged=False,CapAdd=['CHOWN'] if ownership else None,CapDrop=['ALL'],
        AutoRemove=False,SecurityOpt=['no-new-privileges'],Tmpfs={'/tmp':'rw,noexec,nosuid,nodev,size=128m'},
        NetworkMode='none' if ownership else NETWORK_NAME,PublishAllPorts=False,
        RestartPolicy={'Name':'no','MaximumRetryCount':0})
    for key,wanted in expected.items():require(value.get(key)==wanted and type(value.get(key)) is type(wanted))
    require(value['State']['Status']=='created' and value['Path']=='python' and value['Args']==argv[argv.index('--entrypoint')+3:]
        and value['PortBindings'] in (None,{}))
    actual=set()
    for mount in value['Mounts']:
        if mount['Type']=='tmpfs':require(mount['Destination']=='/tmp' and mount['RW'] is True);continue
        source=mount.get('Name') if mount['Type']=='volume' else normalized_mount(mount['Source'])
        actual.add((source,mount['Destination'],mount['Type'],mount['RW']))
    wanted=set() if role=='generator' else {(spec['volume'],'/data','volume',True)}
    if role=='app':wanted.add((normalized_mount(spec['carrier']),'/carrier','bind',False))
    require(actual==wanted)
    if not ownership:
        require(set(value['Networks'])=={NETWORK_NAME})
        network=value['Networks'][NETWORK_NAME];require(network['NetworkID'] in ('',NETWORK))
        if role=='generator':require('generator' in network['Aliases'])


class Generator:
    """Existing fixed service consumer pattern, with exact live PID prearm."""
    def __init__(self,cid,folder,deadline,life):
        self.cid=cid;self.folder=folder;self.deadline=deadline;self.life=life
        self.watch=None;self.attach=None;self.streams=[];self.nonce=secrets.token_hex(24);self.intentional=False
    def start(self):
        self.folder.mkdir();pre=dict(expected=None,received=None,identity_matched=False,live_ack_before_start=False)
        for name in ('watchdog.stdout','watchdog.stderr','attach.stdout','attach.stderr'):self.streams.append((self.folder/name).open('xb'))
        argv=[sys.executable,'-P','-B',str(Path(self.life.__file__).resolve()),'--watchdog-cid',self.cid,
            '--folder',str(self.folder),'--deadline',str(self.deadline),'--nonce',self.nonce]
        try:
            self.watch=subprocess.Popen(argv,stdout=self.streams[0],stderr=self.streams[1],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            expected=dict(cid=self.cid,nonce=self.nonce,deadline=self.deadline,pid=self.watch.pid);pre.update(expected=expected,argv=argv,popen_pid=self.watch.pid)
            arm=min(self.deadline,time.monotonic()+5)
            while True:
                self.life.check_deadline(arm);code=self.watch.poll();pre['before_ready_poll']=code
                require(code is None)
                ready=self.folder/'watchdog-ready.json'
                if ready.exists():
                    value=json.loads(ready.read_bytes());pre['received_type']=type(value).__name__
                    require(type(value) is dict and set(value)==set(expected)
                        and type(value.get('pid')) is int and type(value.get('deadline')) in (int,float)
                        and math.isfinite(value['deadline']) and value==expected)
                    pre.update(received=expected,identity_matched=True);break
                time.sleep(.05)
            self.life.check_deadline(self.deadline);pre['after_ready_poll']=self.watch.poll();require(pre['after_ready_poll'] is None)
            pre['live_ack_before_start']=True
            save(self.folder/'prearm.json',pre)
            self.attach=subprocess.Popen(['docker','start','--attach',self.cid],stdout=self.streams[2],stderr=self.streams[3],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except BaseException:
            if not (self.folder/'prearm.json').exists():save(self.folder/'prearm.json',pre)
            raise
    def check(self):
        self.life.check_deadline(self.deadline)
        require(self.watch is not None and self.watch.poll() is None and self.attach is not None and self.attach.poll() is None)
    def finish(self):
        self.check();before=self.life.inspect(self.cid,deadline=self.deadline);require(before['State']['Running'])
        self.intentional=True;save(self.folder/'intentional-stop.json',dict(cid=self.cid,reason='DATA03 driver terminal',before=before))
        cleanup=self.life.stop_owned(self.cid)
        for process in (self.attach,self.watch):process.wait(timeout=2)
        terminal=self.life.inspect(self.cid,deadline=self.deadline)
        self.life.receipt(self.folder/'watchdog-terminal.json',self.cid,self.nonce,self.deadline,terminal)
        require(terminal['State']['Status']=='exited' and terminal['State']['ExitCode'] in (0,143)
            and not terminal['State']['OOMKilled'] and not terminal['State']['Dead']
            and self.watch.returncode==0 and self.attach.returncode in (0,terminal['State']['ExitCode']))
        save(self.folder/'intentional-terminal.json',dict(terminal=terminal,cleanup=cleanup))
    def reap(self):
        records={}
        try:
            for name,process in (('attach',self.attach),('watchdog',self.watch)):
                records[name]=dict(created=process is not None,pid=process.pid if process is not None else None,
                    returncode=self.life.reap(process),reaped=process is not None)
            save(self.folder/'process-reaping.json',records)
        finally:
            for stream in self.streams:stream.close()


def validate_packet(spec_path,authorized,authority):
    packet=ordinary(spec_path).parent;raw=spec_path.read_bytes();require(sha(raw)==authorized)
    spec=json.loads(raw);require(spec['bounds']==BOUNDS and spec['images']=={'app':APP,'generator':GEN,'ownership':OWNER})
    require(spec['network_id']==NETWORK and spec['network_current_state']=='UNKNOWN' and spec['scope']=='N_DATA03_OBSERVED_ONLY')
    auth=json.loads(ordinary(authority).read_bytes())
    require(auth['spec_sha256']==authorized and auth['scope']==spec['scope'] and auth['candidate_commit']==spec['candidate_commit'])
    require(sha((packet/'plan.json').read_bytes())==spec['plan_sha256'])
    manifest=json.loads((packet/'inputs.json').read_bytes());require(sha((packet/'inputs.json').read_bytes())==spec['inputs_sha256'])
    for item in manifest['files']:
        path=ordinary(packet/item['path']);require(path.is_relative_to(packet) and path.stat().st_size==item['bytes'] and sha(path.read_bytes())==item['sha256'])
    require(Path(__file__).resolve()==(packet/'operators/n_data03.py').resolve()
        and sha(Path(__file__).read_bytes())==spec['operator_sha256'])
    require(normalized_mount(spec['carrier'])==normalized_mount(str(packet/'carrier')))
    require({p.name for p in (packet/'carrier').iterdir()}=={'admin.py','n_data03_driver.py','deployment.json'}
        and all(p.is_file() and not p.is_symlink() for p in (packet/'carrier').iterdir()))
    require(spec['namespace']=='remission-n-data03-261023-r1' and spec['volume']==spec['namespace']+'-positive')
    return packet,spec


def worker(packet,spec,start,lease_unix,outer):
    life=module(packet/'helpers/analysis_lifecycle.py','data03_life')
    runner=module(packet/'helpers/qualify_build_once.py','data03_cli')
    output=packet/'attempt';owned={};terminal=set();generator=None;failure=None;unresolved=[];events=[];sequence=0
    work=start+BOUNDS['work'];setup=start+BOUNDS['setup']
    def command(argv,label,cap=5,check=True,deadline=None):
        nonlocal sequence
        deadline=min(work,deadline if deadline is not None else work);remaining=deadline-time.monotonic()
        require(remaining>0);sequence+=1
        record=runner.command_attempt(argv,output,f'{sequence:03}-{label}',min(cap,remaining),2)
        if record.get('timed_out') or record.get('deadline_rejected') or record.get('cli_terminal')!='OWNED_POPEN_CHILD_EXIT_OBSERVED':
            raise life.StopUnconfirmed('selected command terminal/cap UNKNOWN')
        if (argv[1:2]==['create'] or argv[1:3]==['volume','create']) and (record.get('exit')!=0 or record.get('error')
                or record.get('stdout_snapshot_truncated') or record.get('stderr_snapshot_truncated')):
            raise life.StopUnconfirmed('selected create outcome UNKNOWN')
        require(not record.get('error') and not record.get('stdout_snapshot_truncated') and not record.get('stderr_snapshot_truncated'))
        if check:require(record['exit']==0)
        return record['stdout'] if check else record
    try:
        for role,image in spec['images'].items():
            value=json.loads(command(['docker','image','inspect','--format',IMAGE_FORMAT,image],role+'-image',deadline=setup))
            require(value==dict(Id=image,Os='linux',Architecture='amd64',User='10001:10001' if role!='generator' else '20000:20000'))
        value=json.loads(command(['docker','network','inspect','--format',NETWORK_FORMAT,NETWORK],'selected-network-empty',deadline=setup));audit_network(value,empty=True)
        for role in ('ownership','generator','app'):
            require(not command(['docker','ps','--all','--quiet','--filter','name=^'+spec['namespace']+'-'+role+'$'],role+'-absent',deadline=setup).strip())
        require(not command(['docker','volume','ls','--quiet','--filter','name=^'+spec['volume']+'$'],'volume-absent',deadline=setup).strip())
        if command(['docker','volume','create','--label','remission.task='+spec['namespace'],spec['volume']],'volume-create',10,deadline=setup).strip()!=spec['volume']:
            raise life.StopUnconfirmed('selected volume create identity UNKNOWN')
        for role in ('ownership','generator','app'):
            argv=create_argv(spec,role,lease_unix)
            record=command(argv,role+'-create',10,deadline=setup)
            try:cid=life.require_cid(record.strip())
            except BaseException:raise life.StopUnconfirmed('literal selected create CID UNKNOWN') from None
            owned[role]=cid
            save(output/(role+'-cid.json'),dict(cid=cid))
            created=json.loads(command(['docker','inspect','--format',CONTAINER_FORMAT,cid],role+'-typed-created',3,deadline=setup))
            audit_created(created,cid,spec,role,argv,life)
            if role=='ownership':life.supervise(cid,output/'ownership',min(setup,time.monotonic()+30));terminal.add(cid)
        audit_network(json.loads(command(['docker','network','inspect','--format',NETWORK_FORMAT,NETWORK],'selected-network-before-start',deadline=setup)),empty=True)
        generator=Generator(owned['generator'],output/'generator',work,life);generator.start()
        life.supervise(owned['app'],output/'app',work,on_poll=generator.check);terminal.add(owned['app'])
        generator.finish();terminal.add(owned['generator'])
        driver=module(packet/'carrier/n_data03_driver.py','data03_public')
        raw=bounded_stdout(output/'app/attach.stdout',driver.STDOUT_CAP)
        rows=driver.parse_rows(raw);require(rows[-1]['kind']=='n_data03_custody' and rows[-1]['reason']=='completed'
            and rows[-1]['reaped'] is True and rows[-1]['identity_matched'] is True and rows[-1]['returncode']==0)
        results=[r for r in rows if r['kind']=='n_data03_result'];require(len(results)==1)
        save(output/'public-data03-result.json',results[0])
    except BaseException as error:
        failure=type(error).__name__
        if isinstance(error,life.StopUnconfirmed):unresolved.append('selected_command_or_create_outcome')
    finally:
        # Data work is over. Cleanup/collection only, with the common outer
        # parent backstop; never allocate a new work lease during cleanup.
        for role,cid in owned.items():
            try:
                if cid not in terminal:events.append(dict(role=role,cleanup=life.stop_owned(cid)))
                observed=life.inspect(cid);require(life.stopped(observed));events.append(dict(role=role,independent_final=observed))
            except BaseException:unresolved.append(role)
        if generator is not None:
            try:generator.reap()
            except BaseException:unresolved.append('generator_owned_process_reap')
        save(output/'operation-terminal.json',dict(status='STOP UNCONFIRMED' if unresolved else 'failed' if failure else 'complete',
            failure_class=failure,owned_cids=owned,events=events,unresolved=unresolved,resources_retained=True,
            work_deadline=work,outer_deadline=outer,broader_descendants='UNKNOWN'))
    return 2 if unresolved else 1 if failure else 0


def launch(spec_path,authorized,authority):
    start=time.monotonic();wall=time.time();outer=start+7200;lease_unix=wall+7140
    packet,spec=validate_packet(spec_path,authorized,authority);output=packet/'attempt';output.mkdir()
    save(output/'reservation.json',dict(spec_sha256=authorized,consumed=True,start_monotonic=start,start_unix=wall,
        work_deadline_monotonic=start+7140,outer_deadline_monotonic=outer,container_absolute_utc_cutoff=lease_unix,
        clock_policy='host monotonic authoritative; Linux UTC cutoff and interval timers are additional fail-closed bounds'))
    require(normalized_mount(sys.executable)=='c:/python313/python.exe')
    for item in spec['host_runtime']:
        path=ordinary(item['path']);require(path.stat().st_size==item['bytes'] and sha(path.read_bytes())==item['sha256'])
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=spec['worktree'],timeout=5).decode().strip()==spec['candidate_commit'])
    require(not subprocess.check_output(['git','status','--porcelain=v1'],cwd=spec['worktree'],timeout=5).strip())
    # A direct base interpreter owns the worker; no venv redirector/Job manager.
    nonce=secrets.token_hex(24);child=None;reaped=False;code=None
    argv=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--spec',str(spec_path),'--authorized-spec-sha256',authorized,
        '--authorization',str(authority),'--worker','--start',str(start),'--lease-unix',str(lease_unix),'--outer',str(outer),'--nonce',nonce]
    with (output/'operator.stdout').open('xb') as stdout,(output/'operator.stderr').open('xb') as stderr:
        try:
            child=subprocess.Popen(argv,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            expected=dict(pid=child.pid,ppid=os.getpid(),nonce=nonce,start=start,outer=outer,lease_unix=lease_unix)
            until=min(outer,time.monotonic()+5)
            while True:
                require(time.monotonic()<until and child.poll() is None)
                ready=output/'worker-ready.json'
                if ready.exists():require(json.loads(ready.read_bytes())==expected);break
                time.sleep(.05)
            require(child.poll() is None);save(output/'worker-ack.json',expected)
            code=child.wait(timeout=max(.001,outer-2-time.monotonic()));reaped=True
        except BaseException:
            if child is not None:
                if child.poll() is None:child.kill()
                try:code=child.wait(timeout=max(.001,min(2,outer-time.monotonic())));reaped=True
                except BaseException:pass
        finally:save(output/'launcher-terminal.json',dict(pid=child.pid if child is not None else None,returncode=code,reaped=reaped,
            status='worker_terminal' if reaped and code in (0,1,2) else 'STOP UNCONFIRMED',outer_deadline=outer,
            broader_descendants='UNKNOWN',resources_retained=True))
    require(reaped and code==0)
    print(json.dumps(dict(status='N_DATA03_OBSERVED_ONLY_COMPLETE',resources_retained=True)))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--authorized-spec-sha256',required=True);parser.add_argument('--authorization',type=Path,required=True)
    parser.add_argument('--worker',action='store_true');parser.add_argument('--start',type=float);parser.add_argument('--lease-unix',type=float)
    parser.add_argument('--outer',type=float);parser.add_argument('--nonce');args=parser.parse_args()
    if not args.worker:return launch(args.spec,args.authorized_spec_sha256,args.authorization)
    packet,spec=validate_packet(args.spec,args.authorized_spec_sha256,args.authorization)
    require(all(type(v) is float and math.isfinite(v) for v in (args.start,args.lease_unix,args.outer))
        and args.outer==args.start+7200 and len(args.nonce)==48)
    identity=dict(pid=os.getpid(),ppid=os.getppid(),nonce=args.nonce,start=args.start,outer=args.outer,lease_unix=args.lease_unix)
    save(packet/'attempt/worker-ready.json',identity);until=min(args.outer,time.monotonic()+5)
    while True:
        require(time.monotonic()<until)
        ack=packet/'attempt/worker-ack.json'
        if ack.exists():require(json.loads(ack.read_bytes())==identity);break
        time.sleep(.05)
    return worker(packet,spec,args.start,args.lease_unix,args.outer)


if __name__=='__main__':
    try:sys.exit(main())
    except BaseException as error:
        if type(error) is SystemExit:raise
        print(json.dumps(dict(status='N_DATA03_FAILED_OR_STOP_UNCONFIRMED',error_class=type(error).__name__,private_details_withheld=True)))
        sys.exit(1)
