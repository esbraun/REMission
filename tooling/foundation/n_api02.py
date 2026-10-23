"""Freeze/execute one separately reviewed UNIT scientific API operation.

Host stdlib byte/hash checks only. Scientific payload runs solely in the learner.
"""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import os
import sys
import importlib.util
import subprocess
import time

BINDINGS_BLOB='4bdb33116916ad362ed44d112d4a68f7bc6b6dd9'
BINDINGS_SHA='a6c91cac0697f0347d659795d9a7848ce6da14fccf65ed1304d38ed5c609f59e'
SOURCE_BASE='9c78bb4f7b4b9c381a4af4737b49c7ab05c085b8'
NAME='remission-n-api02-9c78bb4-unit-r2'
MAX_STDOUT=8388608
ARTIFACTS={'posterior.nc','expected-contrast.npz','predictive.npz'}

def sha(raw):return hashlib.sha256(raw).hexdigest()

LIFECYCLE_SHA='45cb568da0dd93642ab48fd5edb2aef76394393a1777c3c05c5645259f88ef2b'
STATE_FORMAT='{"Id":{{json .Id}},"Image":{{json .Image}},"User":{{json .Config.User}},"Path":{{json .Path}},"Args":{{json .Args}},"State":{{json .State}},"RestartCount":{{json .RestartCount}},"Memory":{{json .HostConfig.Memory}},"MemorySwap":{{json .HostConfig.MemorySwap}},"NanoCpus":{{json .HostConfig.NanoCpus}},"PidsLimit":{{json .HostConfig.PidsLimit}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Privileged":{{json .HostConfig.Privileged}},"CapAdd":{{json .HostConfig.CapAdd}},"CapDrop":{{json .HostConfig.CapDrop}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"Tmpfs":{{json .HostConfig.Tmpfs}},"NetworkMode":{{json .HostConfig.NetworkMode}},"Mounts":{{json .Mounts}},"PortBindings":{{json .HostConfig.PortBindings}},"PublishAllPorts":{{json .HostConfig.PublishAllPorts}},"RestartPolicy":{{json .HostConfig.RestartPolicy}},"AutoRemove":{{json .HostConfig.AutoRemove}}}'

LIMITS=['--network','none','--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','64',
    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m','--restart','no','--user','10002:10002']

def proposed_argv(image,payload):
    """Inspection/test seam only; caller cannot launch through this module."""
    if image is None:raise ValueError('accepted learner dependency unavailable')
    return ['docker','create','--name',NAME,*LIMITS,
        '--env','REMISSION_N_API_UNIT=UNIT-API02-91740203',image,'python','-I','-B','-c',payload]

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

def _controller_body(plan,payload,output,life,call,deadline=None):
    deadline=time.monotonic()+180 if deadline is None else deadline;cid=None
    if hashlib.sha256(payload.encode()).hexdigest()!=plan['payload_sha256']:raise ValueError('payload changed')
    image=plan['learner_image'];argv=proposed_argv(image,payload)
    try:
        # Entrypoint is optional in this immutable image's Config. Map-index
        # projects an absent key as null; required fields retain strict lookups.
        image_format='{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"Layers":{{json .RootFS.Layers}},"User":{{json .Config.User}},"WorkingDir":{{json .Config.WorkingDir}},"Entrypoint":{{json (index .Config "Entrypoint")}},"Cmd":{{json .Config.Cmd}}}'
        metadata=json.loads(call(['docker','image','inspect','--format',image_format,image],'image',deadline))
        if metadata!=plan['qualified_image_config'] or metadata['Id']!=image:
            raise ValueError('UNIT accepted image/config mismatch')
        if call(['docker','ps','-aq','--filter','name=^/'+NAME+'$'],'absence',deadline).strip():
            raise ValueError('UNIT literal name is not absent')
        try:cid=life.require_cid(call(argv,'create',deadline).strip())
        except Exception as error:raise life.StopUnconfirmed('UNIT create/CID unknown') from error
        value=json.loads(call(['docker','inspect','--format',STATE_FORMAT,cid],'prestart',deadline))
        checked_created(value,cid,image,argv,life)
        terminal=life.supervise(cid,output/'supervision',min(deadline,time.monotonic()+120))
        raw=call(['docker','logs',cid],'unit-output',deadline)
        result,artifacts=decode_output(raw)
        destination=output/'unit-artifacts';destination.mkdir(exist_ok=False)
        for name,data in artifacts.items():
            with (destination/name).open('xb') as stream:stream.write(data)
        result['artifacts']={name:{k:v for k,v in item.items() if k!='base64'} for name,item in result['artifacts'].items()}
        life.check_deadline(deadline)
        return dict(status='UNIT_STRUCTURAL_ONLY',terminal=terminal,result=result,cid=cid)
    except BaseException as primary:
        if cid is not None:
            try:events=life.stop_owned(cid)
            except BaseException as failure:
                save(output/'cleanup.json',dict(cid=cid,primary=repr(primary),cleanup_error=repr(failure),status='STOP_UNCONFIRMED'))
                raise life.StopUnconfirmed('UNIT exact-CID cleanup unknown: '+cid) from primary
            save(output/'cleanup.json',dict(cid=cid,primary=repr(primary),events=events))
        raise

def decode_output(raw):
    if len(raw.encode())>MAX_STDOUT:raise ValueError('UNIT stdout ceiling exceeded')
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('duplicate UNIT JSON key')
            value[key]=item
        return value
    result=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite UNIT JSON')))
    if (result['kind']!='N-API02-UNIT-ONLY' or result['seed']!=91740203 or result['domain']!=9202
            or result['target']!='UNIT-API02-B' or result['patients']!=['UNIT-API02-A','UNIT-API02-B']
            or any(result[k] is not False for k in ('model_fitted','genuine_data','Store_opened'))
            or result['availability_serialization_equal'] is not True):
        raise ValueError('UNIT output identity/scope mismatch')
    semantics=result['semantics']
    if (semantics['status']!='accepted' or semantics['chains']!=4 or semantics['draws']!=1000
            or semantics['patients']!=result['patients'] or semantics['target_ids']!=[result['target']]
            or semantics['expected_axes']!=['chain','draw','target']
            or semantics['predictive_axes']!=['chain','draw','target','arm','night']
            or semantics['expected_unit']!='quality_points' or semantics['predictive_unit']!='reported_quality_points'):
        raise ValueError('UNIT semantic identity mismatch')
    if result['diagnostics']['accepted'] is not True:raise ValueError('UNIT diagnostic gate failed')
    values=[result['diagnostics'][key]['expected_contrast'] for key in ('rhat','ess_bulk','ess_tail','mcse')]
    values += [result['summary'][key] for key in ('mean','sd','lower','upper')]
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('UNIT finite scalar diagnostics required')
    required={'target','dtype','axes','unit','predictive-mask-dtype','summary-sd','netcdf-patient-order','netcdf-dtype'}
    if len(result['controls'])!=8 or {v['control'] for v in result['controls']}!=required or any(v['rejected'] is not True for v in result['controls']):
        raise ValueError('UNIT corruption controls incomplete')
    if set(result['artifacts'])!=ARTIFACTS:raise ValueError('UNIT exact artifact names/count required')
    decoded={};total=0
    for name,item in result['artifacts'].items():
        if (set(item)!={'bytes','sha256','base64'} or type(item['bytes']) is not int or not 0<item['bytes']<=3145728
                or not isinstance(item['base64'],str) or len(item['base64'])>4194304
                or re.fullmatch('[a-f0-9]{64}',item['sha256']) is None):raise ValueError('UNIT artifact byte declaration invalid')
        data=base64.b64decode(item['base64'],validate=True);total+=len(data)
        if total>5242880 or len(data)!=item['bytes'] or sha(data)!=item['sha256']:raise ValueError('UNIT artifact length/hash/total mismatch')
        decoded[name]=data
    return result,decoded


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
                limit=MAX_STDOUT if label=='unit-output' and key=='stdout' else 65536
                with path.open('rb') as stream:raw=stream.read(limit+1)
                record[key]=raw[:limit].decode('utf-8',errors='strict');record[key+'_truncated']=len(raw)>limit
        record['deadline_rejected']=time.monotonic()>=end;record['elapsed_seconds']=time.monotonic()-started
        save(output/(label+'.json'),record)
    return record

def freeze(directory,root):
    root=ordinary(root);directory=ordinary(directory)
    if directory.exists() or not directory.is_relative_to(root/'artifacts'):raise ValueError('fresh own UNIT packet required')
    raw=subprocess.check_output(['git','show',BINDINGS_BLOB],cwd=root,timeout=15)
    if sha(raw)!=BINDINGS_SHA:raise ValueError('accepted UNIT binding bytes changed')
    binding=json.loads(raw)
    payload=(root/'tooling/foundation/n_api02_unit.py').read_bytes()
    if sha(payload)!=binding['payload_sha256']:raise ValueError('UNIT payload source changed')
    directory.mkdir(parents=True,exist_ok=False);files={}
    entries={'bindings.json':raw,'payload/n_api02_unit.py':payload,
        'operator/n_api02.py':Path(__file__).read_bytes(),
        'operator/analysis_lifecycle.py':(root/'tooling/foundation/analysis_lifecycle.py').read_bytes()}
    if sha(entries['operator/analysis_lifecycle.py'])!=LIFECYCLE_SHA:raise ValueError('accepted lifecycle source changed')
    for name,data in entries.items():
        path=directory/name;path.parent.mkdir(exist_ok=True)
        with path.open('xb') as stream:stream.write(data)
        files[name]=dict(bytes=len(data),sha256=sha(data))
    plan=dict(kind='N-API02-UNIT-exact-operation-v1',source_base=SOURCE_BASE,
        preparation_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,timeout=15).decode().strip(),
        root=str(directory),files=files,bindings_sha256=BINDINGS_SHA,work_seconds=120,lifecycle_seconds=180,
        name=NAME,output='results',stdout_bytes=MAX_STDOUT,scientific_host_imports=False,
        model_fitted=False,Store_opened=False)
    save(directory/'plan.json',plan)
    return dict(plan=str(directory/'plan.json'),sha256=sha((directory/'plan.json').read_bytes()))

def validate_plan(path,authorized):
    path=ordinary(path);raw=path.read_bytes()
    if sha(raw)!=authorized:raise ValueError('exact independently reviewed UNIT plan hash required')
    plan=json.loads(raw);root=ordinary(plan['root'])
    if (root!=path.parent or plan['kind']!='N-API02-UNIT-exact-operation-v1' or plan['source_base']!=SOURCE_BASE
            or plan['name']!=NAME or plan['work_seconds']!=120 or plan['lifecycle_seconds']!=180
            or plan['output']!='results' or plan['stdout_bytes']!=MAX_STDOUT
            or plan['bindings_sha256']!=BINDINGS_SHA or re.fullmatch('[a-f0-9]{40}',plan['preparation_head']) is None
            or any(plan[k] is not False for k in ('scientific_host_imports','model_fitted','Store_opened'))):
        raise ValueError('UNIT plan identity/caps/scope mismatch')
    expected={'bindings.json','payload/n_api02_unit.py','operator/n_api02.py','operator/analysis_lifecycle.py'}
    actual={'bindings.json'}|{p.relative_to(root).as_posix() for folder in ('payload','operator') for p in (root/folder).rglob('*') if p.is_file()}
    if set(plan['files'])!=expected or actual!=expected:raise ValueError('UNIT exact frozen inventory required')
    for folder in ('payload','operator'):
        for item in (root/folder).rglob('*'):ordinary(item)
    for name,row in plan['files'].items():
        raw=ordinary(root/name).read_bytes()
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('UNIT frozen bytes changed: '+name)
    raw=(root/'bindings.json').read_bytes()
    if sha(raw)!=BINDINGS_SHA:raise ValueError('exact accepted UNIT learner/source/proof required')
    if Path(__file__).resolve()!=root/'operator/n_api02.py':raise ValueError('only exact frozen UNIT controller may execute')
    binding=json.loads(raw)
    if sha((root/'payload/n_api02_unit.py').read_bytes())!=binding['payload_sha256']:raise ValueError('UNIT payload identity mismatch')
    return root,plan,binding

def execute(path,authorized):
    root,plan,binding=validate_plan(path,authorized)
    check_host_dependency(binding)
    life=load_lifecycle(root)
    output=root/'results';output.mkdir(exist_ok=False)
    save(output/'authorization-consumed.json',dict(plan_sha256=authorized,started_unix=time.time(),scope='UNIT_SCIENTIFIC_API_ONLY'))
    deadline=time.monotonic()+180;result=None;status='failed';error=None
    def call(argv,label,end):
        life.check_deadline(end)
        value=command_attempt(argv,output,label,min(15,end-time.monotonic()),3)
        if value['timed_out'] or value['deadline_rejected'] or time.monotonic()>=end:
            raise life.StopUnconfirmed('UNIT CLI/descendant outcome unknown: '+label)
        if value['exit']!=0 or value.get('error') or value.get('stdout_truncated') or value.get('stderr_truncated'):
            raise RuntimeError('UNIT bounded command failed: '+label)
        return value['stdout']
    try:
        result=_controller_body(binding,(root/'payload/n_api02_unit.py').read_text(encoding='utf-8'),output,life,call,deadline)
        status='UNIT_STRUCTURAL_API_ARTIFACT_PASS'
    except BaseException as failure:
        error=repr(failure)
        if isinstance(failure,life.StopUnconfirmed):status='STOP_UNCONFIRMED'
        raise
    finally:
        save(output/'observed-unit.json',dict(status=status,error=error,result=result,plan_sha256=authorized,
            finished_unix=time.time(),science_host_imports=False,model_fitted=False,Store_opened=False,
            host_descendant_termination='UNKNOWN',native_N_fit_or_genuine_data_acceptance=False))
    return dict(status=status,cid=result['cid'],artifact_names=sorted(ARTIFACTS))

if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze',action='store_true');mode.add_argument('--execute',action='store_true')
    parser.add_argument('--directory',type=Path);parser.add_argument('--root',type=Path)
    parser.add_argument('--plan',type=Path);parser.add_argument('--authorized-plan-sha256');args=parser.parse_args()
    if args.freeze:
        if not args.directory or not args.root:parser.error('exact directory/root required')
        print(json.dumps(freeze(args.directory,args.root)))
    else:
        if not args.plan or not args.authorized_plan_sha256:parser.error('exact plan/authorized SHA required')
        print(json.dumps(execute(args.plan,args.authorized_plan_sha256)))
