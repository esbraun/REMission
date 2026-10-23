"""Stdlib draft only. No Docker, lifecycle import or executable operation mode."""
import hashlib
import json
from pathlib import Path
import re
import os
import sys
import importlib.util
import subprocess
import time

LIFECYCLE_SHA='45cb568da0dd93642ab48fd5edb2aef76394393a1777c3c05c5645259f88ef2b'
STATE_FORMAT='{"Id":{{json .Id}},"Image":{{json .Image}},"User":{{json .Config.User}},"Path":{{json .Path}},"Args":{{json .Args}},"State":{{json .State}},"RestartCount":{{json .RestartCount}},"Memory":{{json .HostConfig.Memory}},"MemorySwap":{{json .HostConfig.MemorySwap}},"NanoCpus":{{json .HostConfig.NanoCpus}},"PidsLimit":{{json .HostConfig.PidsLimit}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Privileged":{{json .HostConfig.Privileged}},"CapAdd":{{json .HostConfig.CapAdd}},"CapDrop":{{json .HostConfig.CapDrop}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"Tmpfs":{{json .HostConfig.Tmpfs}},"NetworkMode":{{json .HostConfig.NetworkMode}},"Mounts":{{json .Mounts}},"PortBindings":{{json .HostConfig.PortBindings}},"PublishAllPorts":{{json .HostConfig.PublishAllPorts}},"RestartPolicy":{{json .HostConfig.RestartPolicy}},"AutoRemove":{{json .HostConfig.AutoRemove}}}'

LIMITS=['--network','none','--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','64',
    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m','--restart','no','--user','10002:10002']

def inspect_draft(path):
    value=json.loads(Path(path).read_bytes())
    if value['status']!='DRAFT_DEPENDENCY_PENDING' or value['learner_image'] is not None:
        raise ValueError('draft must retain unknown learner identity')
    return value

def proposed_argv(image,payload):
    """Inspection/test seam only; caller cannot launch through this module."""
    if image is None:raise ValueError('accepted learner dependency unavailable')
    return ['docker','create','--name','remission-n-api02-unit-r1',*LIMITS,
        '--env','REMISSION_N_API_UNIT=UNIT-API02-91740203',image,'python','-I','-B','-c',payload]

def execute_draft(spec):
    # Deliberately before helper loading, reservation or subprocess creation.
    raise RuntimeError('DRAFT: exact accepted learner/source evidence and new source/operation review required')

def checked_created(value,cid,image,argv,life):
    state=life.checked_state(dict(Id=value['Id'],State=value['State'],RestartCount=value['RestartCount']),cid)['State']
    if (state['Status']!='created' or state['Pid']!=0 or value['Image']!=image or value['User']!='10002:10002'
            or value['Path']!='python' or value['Args']!=argv[argv.index(image)+2:]
            or value['Memory']!=2147483648 or value['MemorySwap']!=2147483648
            or value['NanoCpus']!=2000000000 or value['PidsLimit']!=64
            or value['ReadonlyRootfs'] is not True or value['Privileged'] is not False
            or value['CapAdd'] not in (None,[]) or value['CapDrop']!=['ALL']
            or value['SecurityOpt']!=['no-new-privileges'] or value['NetworkMode']!='none'
            or value['Mounts'] or value['PortBindings'] not in (None,{}) or value['PublishAllPorts'] is not False
            or value['Tmpfs']!={'/tmp':'rw,exec,nosuid,nodev,size=512m'}
            or value['RestartPolicy']!={'Name':'no','MaximumRetryCount':0} or value['AutoRemove'] is not False):
        raise ValueError('UNIT typed-created image/resource/isolation mismatch')

def _controller_body(plan,payload,output,life,call):
    """Draft body exercised only with doubles. execute_draft cannot reach it.

    Future call must use the accepted bounded command_attempt capture primitive;
    final image/proof/source/host/once bindings still require a new source review.
    """
    deadline=time.monotonic()+180;cid=None
    if hashlib.sha256(payload.encode()).hexdigest()!=plan['payload_sha256']:raise ValueError('payload changed')
    image=plan['learner_image'];argv=proposed_argv(image,payload)
    try:
        image_format='{"Id":{{json .Id}},"User":{{json .Config.User}},"WorkingDir":{{json .Config.WorkingDir}},"Entrypoint":{{json .Config.Entrypoint}},"Cmd":{{json .Config.Cmd}}}'
        metadata=json.loads(call(['docker','image','inspect','--format',image_format,image],'image',deadline))
        if metadata!=plan['qualified_image_config'] or metadata['Id']!=image:
            raise ValueError('UNIT accepted image/config mismatch')
        if call(['docker','ps','-aq','--filter','name=^/remission-n-api02-unit-r1$'],'absence',deadline).strip():
            raise ValueError('UNIT literal name is not absent')
        try:cid=life.require_cid(call(argv,'create',deadline).strip())
        except Exception as error:raise life.StopUnconfirmed('UNIT create/CID unknown') from error
        value=json.loads(call(['docker','inspect','--format',STATE_FORMAT,cid],'prestart',deadline))
        checked_created(value,cid,image,argv,life)
        terminal=life.supervise(cid,output/'supervision',min(deadline,time.monotonic()+120))
        raw=call(['docker','logs',cid],'unit-output',deadline)
        if len(raw.encode())>65536:raise ValueError('UNIT result exceeds64KiB')
        result=json.loads(raw)
        if (result['kind']!='N-API02-UNIT-ONLY' or result['seed']!=91740203 or result['domain']!=9202
                or result['target']!='UNIT-API02-B' or result['patients']!=['UNIT-API02-A','UNIT-API02-B']
                or any(result[k] is not False for k in ('model_fitted','genuine_data','Store_opened'))):
            raise ValueError('UNIT output identity/scope mismatch')
        life.check_deadline(deadline)
        return dict(status='UNIT_STRUCTURAL_ONLY',terminal=terminal,result=result,cid=cid)
    except BaseException:
        if cid is not None:life.stop_owned(cid)
        raise


HOST_FILES=[dict(path='C:/Python313/python.exe',bytes=105816,
    sha256='d932e5e2f324d57f392e8fd063dcf6d0185be8a664c57c6d24e7762ed02c28ca'),
    dict(path='C:/Python313/python313.dll',bytes=6123864,
        sha256='41ec4fc4e5bc8b207258590238f7f050b13fdfee84c4a7b1ecff6e945d031a10'),
    dict(path='C:/Python313/Lib/subprocess.py',bytes=91718,
        sha256='970207fdd712c92f7dc14d1623d2574f7e0910ceb0b5c37652a7a0850f35a396')]


def ordinary(path):
    path=Path(path).absolute()
    for item in (path,*path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(),'st_file_attributes',0)&0x400):
            raise ValueError('aliased/reparse operation path denied')
    if any(c in str(path) for c in (',','\n','\r','\x00')):raise ValueError('unsafe operation path')
    return path


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


def check_host_dependency(plan):
    host=plan['host_controller']
    if host['dependency_status']!='ACCEPTED':
        raise RuntimeError('direct-base inert probe dependency is PENDING; no execution authority')
    if os.path.normcase(os.path.abspath(sys.executable))!=os.path.normcase(os.path.abspath(host['executable'])):
        raise ValueError('execute only with the exact separately qualified direct-base controller')
    for row in HOST_FILES:
        raw=ordinary(row['path']).read_bytes()
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:
            raise ValueError('qualified direct-base public bytes changed: '+row['path'])


def load_lifecycle(root):
    # Validate every helper byte before executing it. Load the literal frozen
    # helper path rather than an unrelated cached/import-search-path module.
    if hashlib.sha256((root/'operator/analysis_lifecycle.py').read_bytes()).hexdigest()!=LIFECYCLE_SHA:
        raise ValueError('exact accepted lifecycle bytes required')
    spec=importlib.util.spec_from_file_location('n48_frozen_lifecycle',root/'operator/analysis_lifecycle.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def command_attempt(argv,output,label,timeout,cleanup_grace):
    """Regular-file child capture adapted from accepted S1 operator e85ff432.

    Reaping this exact Popen child never attests plugin/daemon termination.
    """
    started=time.monotonic();end=started+timeout;process=None
    record=dict(argv=argv,exit=None,timed_out=False,deadline_rejected=False,cli_pid=None,
        cli_terminal='NOT_OBSERVED',cli_descendants_terminal='UNKNOWN',stdout_file=label+'.stdout',
        stderr_file=label+'.stderr',cleanup=[],stdout='',stderr='')
    try:
        with (output/record['stdout_file']).open('xb') as out,(output/record['stderr_file']).open('xb') as err:
            process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            record['cli_pid']=process.pid
            remaining=end-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired(argv,timeout)
            record['exit']=process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:record['timed_out']=True
    except BaseException as error:record['error']=repr(error)
    finally:
        if process is not None:
            record['exit']=process.poll()
            if record['exit'] is None:
                try:
                    process.kill();record['cleanup'].append('kill_exact_Popen_child')
                    record['exit']=process.wait(timeout=cleanup_grace)
                except BaseException as error:record['cleanup'].append(repr(error))
            if record['exit'] is not None:record['cli_terminal']='OWNED_POPEN_CHILD_EXIT_OBSERVED'
        for key in ('stdout','stderr'):
            path=output/record[key+'_file']
            if path.exists():
                with path.open('rb') as stream:raw=stream.read(65537)
                record[key]=raw[:65536].decode('utf-8',errors='replace');record[key+'_truncated']=len(raw)>65536
        record['deadline_rejected']=time.monotonic()>=end;record['elapsed_seconds']=time.monotonic()-started
        save(output/(label+'.json'),record)
    return record
