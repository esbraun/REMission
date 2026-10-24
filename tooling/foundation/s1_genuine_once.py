"""Fixed Phase A submit/export controller proposal. Default draft is inert.

Only a future exact reviewed spec plus root GO may admit one owned container.
Host never opens the private credentials, Store, queued input or receipt files.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import time

NAME='remission-s1-genuine-submit-261024-r1'
VOLUME='remission-s1-completion-261024-r1-positive'
IMAGE='sha256:4c293e2de7f89fc484e575f23e7af7505b28a72d4a6b35f944aa3da56c6040fd'
BOUNDS=dict(outer=900,work=840,controller_wait=870,setup=60,request=180,metadata=5,create=10,cli_reap=2)
FILES={'helpers/analysis_lifecycle.py','helpers/qualify_build_once.py','payload/s1_genuine_submit.py',
    'payload/submit-spec.json','payload/archive-config.json','payload/support-manifest.json','payload/support-authority.json'}
MANIFEST_SHA='a7628300469875bb9ded11b5d595c3f4ed2fe34ad2003b989cc9031c19a67b72'
HOST_FILES=(('C:/Python313/python.exe',105816,'d932e5e2f324d57f392e8fd063dcf6d0185be8a664c57c6d24e7762ed02c28ca'),
    ('C:/Python313/python313.dll',6123864,'41ec4fc4e5bc8b207258590238f7f050b13fdfee84c4a7b1ecff6e945d031a10'),
    ('C:/Python313/Lib/subprocess.py',91718,'970207fdd712c92f7dc14d1623d2574f7e0910ceb0b5c37652a7a0850f35a396'))
PUBLIC_NAME='public-result.json'
PUBLIC_PATH='/data/s1-p3-submit-r1/'+PUBLIC_NAME
BIND_KIND='S1_SELECTED_OWNER_BINDING_V1'
BIND_NAME='remission-s1-selected-owner-261024-r1'
BIND_FILES={'helpers/analysis_lifecycle.py','helpers/qualify_build_once.py','payload/s1_genuine_submit.py',
    'payload/binding-spec.json','payload/support-authority.json'}
BIND_PUBLIC_NAME='owner-binding.json'
BIND_PUBLIC_PATH='/data/s1-p3-owner-binding-r1/'+BIND_PUBLIC_NAME
BIND_EXPECTED=dict(store_instance='f4d6bea5-10aa-4247-afa0-76b8e5c3fceb',authority_generation=1,
    archive_id='support-dev-once-20261022:support-dev-cohort-20261022',archive_export_id='accepted-support-dev-20261022',
    admission_sha256='7f411f3cc7b60fa28eb61481db15c590089fa874827ca8fdab547628438bcf98')
AUTHORITY_SHA='048960f15bc0cc1ca7136a491755bbb64bfd1e0778418fd88e50a15480c65004'
TYPED='{"Id":{{json .Id}},"Image":{{json .Image}},"User":{{json .Config.User}},"Path":{{json .Path}},"Args":{{json .Args}},"State":{{json .State}},"RestartCount":{{json .RestartCount}},"Labels":{{json .Config.Labels}},"Memory":{{json .HostConfig.Memory}},"MemorySwap":{{json .HostConfig.MemorySwap}},"NanoCpus":{{json .HostConfig.NanoCpus}},"PidsLimit":{{json .HostConfig.PidsLimit}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Privileged":{{json .HostConfig.Privileged}},"CapAdd":{{json .HostConfig.CapAdd}},"CapDrop":{{json .HostConfig.CapDrop}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"Tmpfs":{{json .HostConfig.Tmpfs}},"NetworkMode":{{json .HostConfig.NetworkMode}},"PortBindings":{{json .HostConfig.PortBindings}},"PublishAllPorts":{{json .HostConfig.PublishAllPorts}},"RestartPolicy":{{json .HostConfig.RestartPolicy}},"LogConfig":{{json .HostConfig.LogConfig}},"Mounts":{{json .Mounts}}}'


def require(value):
    if not value:raise ValueError('S1 phase A binding refused')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        value={}
        for key,item in items:
            require(key not in value);value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite public JSON')))


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


def admit(spec):
    # First refusal precedes helper import, reservation and every private path.
    require(type(spec) is dict and spec.get('executable') is True)
    if spec.get('kind')==BIND_KIND:
        require(spec.get('namespace')==BIND_NAME and spec.get('volume')==VOLUME and spec.get('image')==IMAGE
            and spec.get('bounds')==BOUNDS and type(spec.get('bounds')) is dict
            and all(type(spec['bounds'].get(k)) is int for k in BOUNDS)
            and spec.get('binding_only') is True and spec.get('no_submit_claim_fit') is True
            and spec.get('owner_id') is None and spec.get('public_authority_sha256')==AUTHORITY_SHA)
        require(all(spec.get(k)==v and type(spec.get(k)) is type(v) for k,v in BIND_EXPECTED.items()))
        require(not any(k in spec for k in ('private_auth_path','public_archive_path','public_authority_path','key',
            'no_claim_or_fit','source_review','operation_review','root_go')))
        require(type(spec.get('source_commit')) is str and re.fullmatch('[a-f0-9]{40}',spec['source_commit']) is not None
            and spec.get('authority_mode')=='EXTERNAL_ROOT_EXACT_ONCE_AFTER_SOURCE_OP')
        require(type(spec.get('binding_spec_sha256')) is str and re.fullmatch('[a-f0-9]{64}',spec['binding_spec_sha256']) is not None)
        return spec
    require(spec.get('kind')=='S1_GENUINE_SUBMIT_EXPORT_V1' and spec.get('namespace')==NAME
        and spec.get('volume')==VOLUME and spec.get('image')==IMAGE and spec.get('bounds')==BOUNDS
        and spec.get('no_claim_or_fit') is True)
    for key in ('store_instance','authority_generation','owner_id','archive_id','archive_export_id',
                'admission_sha256','source_commit','private_auth_path',
                'archive_configuration_sha256'):
        require(spec.get(key) is not None and spec[key]!='UNKNOWN')
    require(type(spec['authority_generation']) is int and spec['authority_generation']>=1)
    require(type(spec['bounds']) is dict and all(type(spec['bounds'].get(k)) is int for k in BOUNDS))
    require(type(spec['source_commit']) is str and re.fullmatch('[a-f0-9]{40}',spec['source_commit']) is not None
        and spec.get('authority_mode')=='EXTERNAL_ROOT_EXACT_ONCE_AFTER_SOURCE_OP')
    require(not any(k in spec for k in ('source_review','operation_review','root_go','public_archive_path','public_authority_path')))
    for key in ('admission_sha256','archive_configuration_sha256','submit_spec_sha256'):
        require(type(spec.get(key)) is str and re.fullmatch('[a-f0-9]{64}',spec[key]) is not None)
    for key in ('store_instance','owner_id','archive_id','archive_export_id'):
        require(type(spec[key]) is str and 1<=len(spec[key])<=128 and re.fullmatch('[A-Za-z0-9_.:-]+',spec[key]))
    for key in ('private_auth_path',):
        path=spec[key]
        require(type(path) is str and len(path)<=1024 and re.match('[A-Za-z]:/',path)
            and not any(c in path for c in ',\\\r\n\x00') and all(p not in ('','.','..') for p in path[3:].split('/')))
    return spec


def public_rows(raw,*,binding=False):
    require(type(binding) is bool)
    require(0<len(raw)<=4096)
    envelope=strict_json(raw)
    if binding:
        fields={'schema','kind','status',*BIND_EXPECTED,'owner_id','members','selected_owner_consistency',
            'no_conflicting_analysis','binding_only','submit','claim','fit'}
        require(type(envelope) is dict and set(envelope)==fields
            and envelope['schema']=='s1-selected-owner-control-v1' and envelope['kind']=='s1_selected_owner_binding'
            and envelope['status']=='selected_owner_bound'
            and all(envelope[k]==v and type(envelope[k]) is type(v) for k,v in BIND_EXPECTED.items())
            and type(envelope['owner_id']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}',envelope['owner_id']) is not None
            and type(envelope['members']) is int and envelope['members']==12
            and all(envelope[k] is True for k in ('selected_owner_consistency','no_conflicting_analysis','binding_only'))
            and all(envelope[k] is False for k in ('submit','claim','fit')))
        return [envelope]
    require(type(envelope) is dict and set(envelope)=={'schema','rows'} and envelope['schema']=='s1-p3-public-v1'
        and type(envelope['rows']) is list and 1<=len(envelope['rows'])<=12)
    rows=[]
    for value in envelope['rows']:
        require(type(value) is dict and len(json.dumps(value,allow_nan=False).encode())<=512)
        if value.get('kind')=='s1_p3_phase':
            require(set(value)=={'kind','stage','seconds','response_seconds','decode_seconds'}
                and value['stage'] in ('session','login','csrf','submit','receipt_export'))
            require(all(v is None or (type(v) in (int,float) and math.isfinite(v) and v>=0)
                for v in (value['seconds'],value['response_seconds'],value['decode_seconds'])))
        else:
            require(set(value)=={'kind','status','members','cutoff_day','job_id','response_confirmed','original_receipt_resolved','claim','fit'}
                and value['kind']=='s1_p3_submit_result' and value['status']=='queued_export_saved'
                and type(value['members']) is int and value['members']==12
                and type(value['cutoff_day']) is int and value['cutoff_day']==84
                and type(value['job_id']) is str and re.fullmatch('analysis-[a-f0-9]{32}',value['job_id']) is not None
                and type(value['response_confirmed']) is bool and value['original_receipt_resolved'] is True
                and value['claim'] is False and value['fit'] is False)
        rows.append(value)
    require(rows and rows[-1]['kind']=='s1_p3_submit_result'
        and sum(v['kind']=='s1_p3_submit_result' for v in rows)==1)
    return rows


def load(path,name):
    descriptor=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(descriptor);descriptor.loader.exec_module(value);return value


def argv(spec,packet):
    binding=spec['kind']==BIND_KIND;name=BIND_NAME if binding else NAME
    mounts=[('volume',VOLUME,'/data',False),('bind',str(packet/'payload'),'/operation',True)]
    if not binding:mounts.append(('bind',spec['private_auth_path'],'/private/auth.json',True))
    args=['docker','create','--name',name,'--label','remission.task='+name,'--network','none','--log-driver','none',
        '--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','64','--read-only',
        '--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=128m',
        '--restart','no','--user','10001:10001','--workdir','/app']
    for kind,source,target,readonly in mounts:
        args+=['--mount','type='+kind+',source='+source+',target='+target+(',readonly' if readonly else '')]
    environment={} if binding else dict(REMISSION_CONTROL_BUNDLE='/data/bootstrap/bundle.json',REMISSION_DATABASE='/data/remission.sqlite',
            REMISSION_ARCHIVE_CONFIG='/operation/archive-config.json',REMISSION_SOURCE_COMMIT=spec['source_commit'],
            REMISSION_ORIGIN='http://127.0.0.1:8765')
    for key,value in environment.items():args+=['--env',key+'='+value]
    args += [IMAGE,'python','-B','/operation/s1_genuine_submit.py','--spec',
        '/operation/binding-spec.json' if binding else '/operation/submit-spec.json',
        '--authorized-spec-sha256',spec['binding_spec_sha256'] if binding else spec['submit_spec_sha256']]
    return args,mounts


def normalized(value):
    value=value.replace('\\','/').rstrip('/')
    for prefix in ('/run/desktop/mnt/host/','/host_mnt/'):
        if value.startswith(prefix) and re.match('[a-zA-Z]/',value[len(prefix):]):
            value=value[len(prefix)]+':'+value[len(prefix)+1:]
    return value.casefold() if re.match('[a-zA-Z]:/',value) else value


def audit_created(value,cid,arguments,mounts,life,*,binding=False):
    require(type(binding) is bool)
    life.checked_state(value,cid)
    expected=dict(Image=IMAGE,User='10001:10001',Labels={'remission.task':BIND_NAME if binding else NAME},Memory=2147483648,
        MemorySwap=2147483648,NanoCpus=2000000000,PidsLimit=64,ReadonlyRootfs=True,Privileged=False,
        CapAdd=None,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],Tmpfs={'/tmp':'rw,noexec,nosuid,nodev,size=128m'},
        NetworkMode='none',PublishAllPorts=False,RestartPolicy={'Name':'no','MaximumRetryCount':0},LogConfig={'Type':'none','Config':{}})
    require(all(value.get(k)==v and type(value.get(k)) is type(v) for k,v in expected.items()))
    require(value['State']['Status']=='created' and value['Path']=='python'
        and value['Args']==arguments[arguments.index(IMAGE)+2:] and value['PortBindings'] in (None,{}))
    actual=[]
    for mount in value['Mounts']:
        if mount['Type']=='tmpfs':require(mount['Destination']=='/tmp' and mount['RW'] is True);continue
        source=mount.get('Name') if mount['Type']=='volume' else mount['Source']
        require(type(mount['RW']) is bool)
        actual.append((mount['Type'],normalized(source),mount['Destination'],not mount['RW']))
    require(len(actual)==len(mounts) and set(actual)=={(k,normalized(s),t,r) for k,s,t,r in mounts})


def checked_packet(path,token):
    raw=path.read_bytes();require(sha(raw)==token)
    spec=admit(strict_json(raw));packet=path.parent
    binding=spec['kind']==BIND_KIND;files=BIND_FILES if binding else FILES
    require(type(spec.get('public_inputs')) is list and len(spec['public_inputs'])==len(files)
        and {r['path'] for r in spec['public_inputs']}==files)
    for item in spec['public_inputs']:
        cap=699480 if item['path']=='payload/support-authority.json' else 128*1024
        require(set(item)=={'path','bytes','sha256'} and type(item['bytes']) is int and 0<item['bytes']<=cap)
        source=packet/item['path'];require(source.resolve().is_relative_to(packet.resolve()) and not source.is_symlink())
        value=source.read_bytes();require(len(value)==item['bytes'] and sha(value)==item['sha256'])
    if binding:
        checked_binding_carrier(packet/'payload')
        authority=(packet/'payload/support-authority.json').read_bytes()
        require(len(authority)==699480 and sha(authority)==AUTHORITY_SHA)
        raw=(packet/'payload/binding-spec.json').read_bytes();require(sha(raw)==spec['binding_spec_sha256'])
        payload=strict_json(raw)
        keys=('kind','executable','namespace','volume',*BIND_EXPECTED,'owner_id','source_commit','authority_mode',
            'public_authority_sha256','binding_only','no_submit_claim_fit')
        require(type(payload) is dict and all(payload.get(k)==spec[k] and type(payload.get(k)) is type(spec[k]) for k in keys)
            and not any(k in payload for k in ('private_auth_path','public_archive_path','public_authority_path','key',
                'source_review','operation_review','root_go')))
        return spec,packet
    checked_submit_carrier(packet/'payload')
    require(sha((packet/'payload/support-manifest.json').read_bytes())==MANIFEST_SHA)
    authority=(packet/'payload/support-authority.json').read_bytes()
    require(len(authority)==699480 and sha(authority)==AUTHORITY_SHA)
    require(sha((packet/'payload/archive-config.json').read_bytes())==spec['archive_configuration_sha256'])
    require(sha((packet/'payload/submit-spec.json').read_bytes())==spec['submit_spec_sha256'])
    payload=strict_json((packet/'payload/submit-spec.json').read_bytes())
    keys=('kind','executable','namespace','volume','store_instance','authority_generation','owner_id',
        'archive_id','archive_export_id','admission_sha256','source_commit','authority_mode','no_claim_or_fit')
    require(type(payload) is dict and all(payload.get(k)==spec[k] and type(payload.get(k)) is type(spec[k]) for k in keys)
        and payload.get('key')=='s1-genuine-day84-261024-r1' and type(payload.get('cutoff_day')) is int
        and payload['cutoff_day']==84 and type(payload.get('members')) is int and payload['members']==12
        and payload.get('request_seconds')==180 and payload.get('private_export_cap')==16*1024*1024
        and not any(k in payload for k in ('source_review','operation_review','root_go')))
    return spec,packet


def checked_binding_carrier(payload):
    # Fixed three public leaves only: no extra module may shadow the installed
    # sqlite/contracts/services imports when Python starts at /operation.
    names=set()
    for path in payload.iterdir():
        require(path.is_file() and not path.is_symlink() and not (getattr(path.lstat(),'st_file_attributes',0)&0x400))
        names.add(path.name);require(len(names)<=3)
    require(names=={'s1_genuine_submit.py','binding-spec.json','support-authority.json'})


def checked_submit_carrier(payload):
    names=set()
    for path in payload.iterdir():
        require(path.is_file() and not path.is_symlink() and not (getattr(path.lstat(),'st_file_attributes',0)&0x400))
        names.add(path.name);require(len(names)<=5)
    require(names=={'s1_genuine_submit.py','submit-spec.json','archive-config.json','support-manifest.json','support-authority.json'})


def check_host():
    require(Path(sys.executable).as_posix().casefold()==HOST_FILES[0][0].casefold()
        and Path(sys._base_executable).as_posix().casefold()==HOST_FILES[0][0].casefold()
        and sys.flags.isolated==1 and sys.flags.dont_write_bytecode==1)
    for name,size,digest in HOST_FILES:
        raw=Path(name).read_bytes();require(len(raw)==size and sha(raw)==digest)


def public_tar(raw,*,binding=False):
    require(type(binding) is bool)
    # Exact-file framing reused from the accepted N transfer; no extraction.
    require(len(raw)>=1536 and len(raw)%512==0 and len(raw)<=20480)
    info=tarfile.TarInfo.frombuf(raw[:512],'utf-8','strict')
    end=512+((info.size+511)//512)*512
    require(info.name==(BIND_PUBLIC_NAME if binding else PUBLIC_NAME) and info.type in (tarfile.REGTYPE,tarfile.AREGTYPE)
        and 0<info.size<=4096 and len(raw)>=end+1024 and not any(raw[512+info.size:]))
    return raw[512:512+info.size]


def collect_public(cid,deadline,life,receipts,*,binding=False):
    """One named public receipt; hard transport cap before JSON parsing."""
    require(type(binding) is bool);life.require_cid(cid);life.check_deadline(deadline)
    process=None;raw=bytearray();record=dict(pid=None,reaped=False,returncode=None)
    try:
        process=subprocess.Popen(['docker','cp',cid+':'+(BIND_PUBLIC_PATH if binding else PUBLIC_PATH),'-'],stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        record['pid']=process.pid;os.set_blocking(process.stdout.fileno(),False)
        end=min(deadline,time.monotonic()+15)
        while True:
            life.check_deadline(end)
            try:chunk=os.read(process.stdout.fileno(),min(65536,20481-len(raw)))
            except BlockingIOError:chunk=None
            if chunk:
                raw.extend(chunk);require(len(raw)<=20480)
            elif chunk==b'' and process.poll() is not None:break
            else:time.sleep(min(.01,max(0,end-time.monotonic())))
        record['returncode']=process.wait(timeout=max(.001,min(2,end-time.monotonic())));record['reaped']=True
        life.check_deadline(end);require(record['returncode']==0)
        return public_tar(raw,binding=binding)
    finally:
        if process is not None:
            if not record['reaped']:
                try:process.kill();record['returncode']=process.wait(timeout=2);record['reaped']=True
                except BaseException:raise life.StopUnconfirmed('public file client reap unknown') from None
            process.stdout.close()
        receipts.append(record)


def execute(path,token,origin):
    require(type(origin) in (int,float) and math.isfinite(origin) and 0<=time.monotonic()-origin<BOUNDS['setup'])
    spec,packet=checked_packet(path,token)
    binding=spec['kind']==BIND_KIND;name=BIND_NAME if binding else NAME
    success='owner_binding_saved' if binding else 'queued_export_saved'
    life=load(packet/'helpers/analysis_lifecycle.py','s1_p3_life')
    runner=load(packet/'helpers/qualify_build_once.py','s1_p3_cli')
    output=packet/'results';output.mkdir(exist_ok=False);save(output/'reservation.json',dict(spec_sha256=token,consumed=True))
    work=origin+BOUNDS['work'];setup=origin+BOUNDS['setup'];cid=None;error=None;unresolved=[];events=[];sequence=0;receipts=[]
    def call(args,label,cap=5,deadline=work):
        nonlocal sequence
        life.check_deadline(deadline);sequence+=1
        r=runner.command_attempt(args,output,f'{sequence:03}-{label}',min(cap,deadline-time.monotonic()),2)
        if r.get('timed_out') or r.get('deadline_rejected') or r.get('cli_terminal')!='OWNED_POPEN_CHILD_EXIT_OBSERVED':
            raise life.StopUnconfirmed('selected command terminal unknown')
        require(not r.get('error') and r['exit']==0 and not r.get('stdout_snapshot_truncated') and not r.get('stderr_snapshot_truncated'))
        return r['stdout']
    try:
        require(call(['docker','image','inspect','--format','{{.Id}}',IMAGE],'image',deadline=setup).strip()==IMAGE)
        require(not call(['docker','ps','--all','--quiet','--filter','name=^/'+name+'$'],'name-absent',deadline=setup).strip())
        require(not call(['docker','ps','--quiet','--filter','volume='+VOLUME],'volume-no-writer',deadline=setup).strip())
        value=json.loads(call(['docker','volume','inspect','--format','{"Name":{{json .Name}},"Labels":{{json .Labels}}}',VOLUME],'retained-volume',deadline=setup))
        require(value==dict(Name=VOLUME,Labels={'remission.task':'remission-s1-completion-261024-r1'}))
        arguments,mounts=argv(spec,packet)
        try:cid=life.require_cid(call(arguments,'create',10,deadline=setup).strip())
        except BaseException:raise life.StopUnconfirmed('selected create CID unknown') from None
        save(output/'cid.json',dict(cid=cid))
        created=json.loads(call(['docker','inspect','--format',TYPED,cid],'typed-created',deadline=setup))
        audit_created(created,cid,arguments,mounts,life,binding=binding)
        life.supervise(cid,output/'supervision',work,discard_output=True)
        # The stopped-container volume contains one explicitly public file.
        # No private input/export/auth file or process stream is collected.
        captured=collect_public(cid,work,life,receipts,binding=binding)
        rows=public_rows(captured,binding=binding)
        save(output/'public-result.json',rows[-1])
    except BaseException as failure:
        error=type(failure).__name__
        if isinstance(failure,life.StopUnconfirmed):unresolved.append('command_or_create')
    finally:
        if cid is not None:
            try:
                events=life.stop_owned(cid);final=life.inspect(cid);require(life.stopped(final))
                save(output/'independent-final.json',final)
            except BaseException:unresolved.append('owned_container_stop')
        save(output/'terminal.json',dict(status='STOP UNCONFIRMED' if unresolved else 'failed' if error else success,
            error_class=error,cid=cid,cleanup=events,unresolved=unresolved,file_clients=receipts,
            resources_retained=True,private_outputs_not_read=True))
    require(error is None and not unresolved)


def launch(path,token):
    """One owned controller; absolute common origin includes all preflight."""
    origin=time.monotonic();spec,packet=checked_packet(path,token);check_host()
    success='owner_binding_saved' if spec['kind']==BIND_KIND else 'queued_export_saved'
    folder=packet/'launcher';folder.mkdir(exist_ok=False)
    save(folder/'reservation.json',dict(spec_sha256=token,consumed=True,origin=origin,outer_deadline=origin+900,work_deadline=origin+840))
    life=load(packet/'helpers/analysis_lifecycle.py','s1_p3_parent_life')
    process=None;error=None;code=None;events=[];unresolved=[];cid=None
    try:
        life.check_deadline(origin+60)
        process=subprocess.Popen([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--execute','--controller',
            '--spec',str(path),'--authorized-spec-sha256',token,'--origin',str(origin)],stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:code=process.wait(timeout=max(.001,origin+870-time.monotonic()))
        except subprocess.TimeoutExpired:error='controller_deadline'
    except BaseException as failure:error=type(failure).__name__
    finally:
        if process is not None and process.poll() is None:
            try:process.kill();code=process.wait(timeout=min(2,max(.001,origin+872-time.monotonic())))
            except BaseException:unresolved.append('controller_reap')
        # Child-created public CID record only, after owned controller reap.
        if 'controller_reap' not in unresolved:
            record=packet/'results/cid.json'
            if record.exists():
                try:
                    require(record.stat().st_size<=128 and not record.is_symlink())
                    value=strict_json(record.read_bytes());require(set(value)=={'cid'});cid=life.require_cid(value['cid'])
                    life.check_deadline(origin+875)
                    events=life.stop_owned(cid);final=life.inspect(cid);require(life.stopped(final))
                    save(folder/'independent-final.json',final)
                except BaseException:unresolved.append('owned_container_stop')
            elif process is not None:unresolved.append('controller_cid_outcome_unknown')
            if code==0:
                try:
                    terminal=packet/'results/terminal.json'
                    require(terminal.stat().st_size<=8192 and not terminal.is_symlink())
                    value=strict_json(terminal.read_bytes())
                    require(value['status']==success and value['cid']==cid
                        and value['error_class'] is None and value['unresolved']==[])
                except BaseException:error='controller_terminal_unconfirmed'
        try:life.check_deadline(origin+900)
        except BaseException:unresolved.append('outer_deadline')
        save(folder/'terminal.json',dict(status='STOP UNCONFIRMED' if unresolved else 'failed' if error or code!=0 else success,
            controller_pid=None if process is None else process.pid,controller_exit=code,controller_reaped=process is not None and process.poll() is not None,
            cid=cid,error_class=error,cleanup=events,unresolved=unresolved,common_origin=origin,elapsed=time.monotonic()-origin))
    require(not unresolved and error is None and code==0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true',required=True)
    parser.add_argument('--spec',type=Path,required=True);parser.add_argument('--authorized-spec-sha256',required=True)
    parser.add_argument('--controller',action='store_true');parser.add_argument('--origin',type=float)
    args=parser.parse_args()
    try:
        if args.controller:execute(args.spec,args.authorized_spec_sha256,args.origin)
        else:require(args.origin is None);launch(args.spec,args.authorized_spec_sha256)
    except BaseException:raise SystemExit(1) from None
