"""Freeze or execute one separately reviewed N COPY/fixed-unlink/scalar image operation.

Host stdlib only. No Docker action occurs during freeze or validation. Execute
requires the exact reviewed plan hash and consumes an exclusive receipt first.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent

SOURCE='31aa05cc8d9c66a3b64910eda65a1883b2d16c44'
TREE='a5b4ed30e724cc09368f5df77c0d35eddaa4fba2'
BINDINGS_SHA='8435ae642843068e1e02d285c907b28cfa028fb89141ec35bea6c86950ad635d'
BINDINGS_BLOB='7010d78a77b38952f46d39e0e0ce3b1c6985fbc9'
PARENT_MANIFEST='35b77dfcb25b9473807bf50fea65fd43b2f6f9ec'
INHERITED_PUBLIC_MANIFEST=dict(path='/app/role-copy-manifest.json',bytes=77023,
    sha256='fc607c0fb4b61283e48e6279bf75f1c81e1a8d0ec24a8894d3e092b4c1822836',
    git_blob='8879d91eb59c3bc30761d831ac040a534dae1d00',
    prepared_manifest='24042076bd9841950afd4791fa935a2056ba8594',
    roles_Dockerfile='31906e090db1a95d2c9842f24b016f4c3e1eafd1',
    context_manifest='e2733119b50fc6fa445e036f7bc164e8ec4cc7c0')
PARENTS={'learner':'sha256:76d8eec82e4b31646440d178952cf6f9d2072a0ce812ffaf7aafe81b2fdf6fef',
    'controls':'sha256:02247f1940d6fe4e52d9331e15f6ddd947e2d160858f464152f0de51b528dc85'}
ROLES=('learner','controls')
RETAINED_SERVICE_SHA='6d9a7656d98abb928e6f52d126cd60f5ea3419cb7fc1f7c1e49d4119a652e687'
# Literal, non-scientific packaging action only. Its daemon RUN is bounded by
# the existing build lease, not by the later qualifier's resource/ACK gates.
UNLINK_CODE='''import json
from pathlib import Path
import stat
target=Path('/app/web/dist/assets/index-_kvz3Qwx.js')
result='already_absent'
for ancestor in reversed(target.parents):
    try:
        entry=ancestor.lstat()
    except FileNotFoundError:
        break
    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISDIR(entry.st_mode):
        raise ValueError('packaging ancestor must be an ordinary directory')
else:
    try:
        entry=target.lstat()
    except FileNotFoundError:
        pass
    else:
        if not stat.S_ISREG(entry.st_mode):
            raise ValueError('packaging target must be an ordinary regular file')
        target.unlink()
        result='removed'
print(json.dumps({'packaging_unlink':result,'path':str(target)},sort_keys=True))
'''
HOST_PROOF=dict(accepted_probe_receipt='2c794f3dae6a329da3d1f4fe2f6f7ac37bd3eec9',
    accepted_probe_checks='f3db7afd0871343be05519d9c3e201fffea2d0e9',
    acceptance_review='6f316215b0a317474f34021a789b3d041d90003e',
    acceptance_checks='16720b003912dd878a2c2cf825014b60817a5d66')
HOST_FILES=[dict(path='C:/Python313/python.exe',bytes=105816,
    sha256='d932e5e2f324d57f392e8fd063dcf6d0185be8a664c57c6d24e7762ed02c28ca'),
    dict(path='C:/Python313/python313.dll',bytes=6123864,
        sha256='41ec4fc4e5bc8b207258590238f7f050b13fdfee84c4a7b1ecff6e945d031a10'),
    dict(path='C:/Python313/Lib/subprocess.py',bytes=91718,
        sha256='970207fdd712c92f7dc14d1623d2574f7e0910ceb0b5c37652a7a0850f35a396')]
LIMITS=['--network','none','--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','64',
    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m','--restart','no']
IMAGE_FORMAT='{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"Layers":{{json .RootFS.Layers}},"User":{{json (index .Config "User")}},"WorkingDir":{{json (index .Config "WorkingDir")}},"Entrypoint":{{json (index .Config "Entrypoint")}},"Cmd":{{json (index .Config "Cmd")}}}'
CONTAINER_FORMAT='{"Id":{{json .Id}},"Image":{{json .Image}},"User":{{json .Config.User}},"Path":{{json .Path}},"Args":{{json .Args}},"Labels":{{json .Config.Labels}},"State":{{json .State}},"RestartCount":{{json .RestartCount}},"Memory":{{json .HostConfig.Memory}},"MemorySwap":{{json .HostConfig.MemorySwap}},"NanoCpus":{{json .HostConfig.NanoCpus}},"PidsLimit":{{json .HostConfig.PidsLimit}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Privileged":{{json .HostConfig.Privileged}},"CapAdd":{{json .HostConfig.CapAdd}},"CapDrop":{{json .HostConfig.CapDrop}},"AutoRemove":{{json .HostConfig.AutoRemove}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"Tmpfs":{{json .HostConfig.Tmpfs}},"NetworkMode":{{json .HostConfig.NetworkMode}},"PortBindings":{{json .HostConfig.PortBindings}},"PublishAllPorts":{{json .HostConfig.PublishAllPorts}},"RestartPolicy":{{json .HostConfig.RestartPolicy}},"Mounts":{{json .Mounts}}}'


def sha(raw):return hashlib.sha256(raw).hexdigest()


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


def git(root,*args):
    return subprocess.check_output(['git',*args],cwd=root,timeout=15)


def check_retained_service(value):
    # Exact accepted evidence + original map/overlays/recipe/config; static reuse
    # is distinct from this operation's newly observed remaining-role results.
    if sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())!=RETAINED_SERVICE_SHA:
        raise ValueError('exact accepted retained service proof/source/map/config required')


def recipe(roles):
    lines=['ARG LEARNER_PARENT','ARG CONTROLS_PARENT']
    for role in ROLES:
        lines.append('FROM ${'+role.upper()+'_PARENT} AS '+role)
        for row in roles[role]['overlay']:
            lines.append('COPY '+role+'/'+row['source']+' '+row['destination'])
        if role=='controls':
            lines+=['USER 0:0','RUN '+json.dumps(['python','-I','-B','-c',UNLINK_CODE]),
                'USER 10001:10001']
        lines+=['COPY qualify/probe.py /qualify/probe.py',
            'COPY qualify/'+role+'.json /qualify/expected.json']
    return '\n'.join(lines)+'\n'


def freeze(directory,root):
    directory=ordinary(directory);root=ordinary(root)
    if directory.exists():raise FileExistsError('exclusive N image preparation already exists')
    if not directory.is_relative_to(root/'artifacts'):raise ValueError('operation must stay in own artifacts')
    # Raw reviewed Git bytes avoid checkout line-ending conversion or a mutable
    # working-copy binding. The candidate commit must retain this exact blob.
    raw=git(root,'show',BINDINGS_BLOB)
    if sha(raw)!=BINDINGS_SHA:raise ValueError('reviewed source bindings changed')
    bindings=json.loads(raw)
    check_retained_service(bindings['retained_service'])
    if set(bindings['roles'])!=set(ROLES):raise ValueError('only learner and controls may execute')
    if bindings['inherited_public_manifest']!=INHERITED_PUBLIC_MANIFEST:raise ValueError('declared parent metadata provenance changed')
    inherited=git(root,'show',INHERITED_PUBLIC_MANIFEST['git_blob'])
    if len(inherited)!=INHERITED_PUBLIC_MANIFEST['bytes'] or sha(inherited)!=INHERITED_PUBLIC_MANIFEST['sha256']:
        raise ValueError('original public parent manifest bytes changed')
    parent=json.loads(git(root,'show',PARENT_MANIFEST))
    if git(root,'rev-parse',SOURCE+'^{tree}').decode().strip()!=TREE:raise ValueError('accepted source tree changed')
    for role,item in bindings['roles'].items():
        if item['parent']!=PARENTS[role] or item['parent']!=parent['images'][role]['image']:
            raise ValueError('accepted parent identity changed')
    directory.mkdir(parents=True,exist_ok=False)
    context=directory/'context';context.mkdir();qualify=directory/'qualify';qualify.mkdir()
    operator=directory/'operator';operator.mkdir();files={}
    def write(relative,data):
        path=directory/relative;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(data)
        files[relative]=dict(bytes=len(data),sha256=sha(data))
    roles={}
    for role,item in bindings['roles'].items():
        expected=dict(parent['images'][role]['probe']['copied_source'])
        expected[INHERITED_PUBLIC_MANIFEST['path']]=INHERITED_PUBLIC_MANIFEST['sha256']
        for row in item['overlay']:
            name=row['source']
            destination={'tooling/foundation/consumer_probe.py':'/app/boundary_probe.py',
                'tooling/foundation/observed_v2_probe.py':'/app/observed_v2_probe.py',
                'docs/implementation/evidence/support-producer-20261022/probe_roles.py':'/app/probe_roles.py',
                'docs/implementation/evidence/support-producer-20261022/run_support_once.py':'/app/run_support_once.py'}.get(name,'/app/'+name)
            if (Path(name).is_absolute() or '..' in Path(name).parts or row['destination']!=destination):
                raise ValueError('noncanonical COPY source/destination')
            data=(ordinary(root/name).read_bytes() if 'generated' in row else git(root,'show',SOURCE+':'+name))
            if len(data)!=row['bytes'] or sha(data)!=row['sha256']:raise ValueError('COPY input changed: '+name)
            write('context/'+role+'/'+name,data);expected[row['destination']]=row['sha256']
        if expected!=item['expected_project_source']:raise ValueError('complete parent-plus-overlay closure changed')
        payload=json.dumps(dict(role=role,uid=item['uid'],project_source=expected),sort_keys=True).encode()+b'\n'
        write('qualify/'+role+'.json',payload)
        write('context/qualify/'+role+'.json',payload)
        roles[role]=dict(parent=PARENTS[role],parent_tag='remission-shared05-31aa05c-'+role+'-parent:v1',
            tag=item['tag'],name=item['qualifier'],uid=str(item['uid'])+':'+str(item['uid']),
            parent_layers=parent['images'][role]['layers'],expected_sha256=sha(payload))
    write('context/overlay.Dockerfile',recipe(bindings['roles']).encode())
    for name in ('nof1_image01.py','analysis_lifecycle.py'):
        write('operator/'+name,(HERE/name).read_bytes())
    write('qualify/probe.py',(HERE/'nof1_image01_probe.py').read_bytes())
    write('context/qualify/probe.py',(HERE/'nof1_image01_probe.py').read_bytes())
    plan=dict(kind='poc-shared-image05-exact-operation-v1',source_commit=SOURCE,source_tree=TREE,
        scope='remaining_learner_controls_COPY_plus_fixed_controls_unlink_and_scalar_qualification',bindings_sha256=BINDINGS_SHA,
        bindings_git_blob=BINDINGS_BLOB,host_controller=bindings['host_controller'],
        inherited_public_manifest=INHERITED_PUBLIC_MANIFEST,retained_service=bindings['retained_service'],
        root=str(directory),roles=roles,files=files,probe_sha256=files['qualify/probe.py']['sha256'],
        packaging_unlink_sha256=sha(UNLINK_CODE.encode()),
        preparation_head=git(root,'rev-parse','HEAD').decode().strip(),
        phase_seconds=900,build_seconds=300,qualification_seconds=60,cli_cleanup_seconds=3,
        future_images={role:'UNKNOWN' for role in ROLES},future_CIDs={role:'UNKNOWN' for role in ROLES},
        output='results',scientific_imports=False,Store_open=False)
    save(directory/'plan.json',plan)
    return dict(plan=str(directory/'plan.json'),sha256=sha((directory/'plan.json').read_bytes()))


def validate_plan(path,authorized):
    path=ordinary(path);raw=path.read_bytes()
    if sha(raw)!=authorized:raise ValueError('exact independently reviewed plan hash required')
    plan=json.loads(raw);check_retained_service(plan.get('retained_service'));root=ordinary(plan['root'])
    if (root!=path.parent or plan['source_commit']!=SOURCE or plan['source_tree']!=TREE
            or plan['kind']!='poc-shared-image05-exact-operation-v1' or set(plan['roles'])!=set(ROLES)
            or plan['inherited_public_manifest']!=INHERITED_PUBLIC_MANIFEST
            or plan['scope']!='remaining_learner_controls_COPY_plus_fixed_controls_unlink_and_scalar_qualification'
            or plan['bindings_sha256']!=BINDINGS_SHA or plan['bindings_git_blob']!=BINDINGS_BLOB
            or plan['packaging_unlink_sha256']!=sha(UNLINK_CODE.encode())
            or re.fullmatch('[a-f0-9]{40}',plan['preparation_head']) is None
            or plan['phase_seconds']!=900
            or plan['build_seconds']!=300 or plan['qualification_seconds']!=60
            or plan['cli_cleanup_seconds']!=3 or plan['output']!='results'
            or plan['scientific_imports'] is not False or plan['Store_open'] is not False):
        raise ValueError('operation identity/scope/ceilings changed')
    expected=set(plan['files'])
    actual={p.relative_to(root).as_posix() for folder in ('context','qualify','operator')
        for p in (root/folder).rglob('*') if p.is_file()}
    for folder in ('context','qualify','operator'):
        for item in (root/folder).rglob('*'):ordinary(item)
    if actual!=expected:raise ValueError('frozen context/probe/operator inventory changed')
    for name,entry in plan['files'].items():
        target=ordinary(root/name)
        if not target.is_relative_to(root) or target.is_dir():raise ValueError('escaped frozen input')
        raw=target.read_bytes()
        if len(raw)!=entry['bytes'] or sha(raw)!=entry['sha256']:raise ValueError('frozen input bytes changed: '+name)
    if Path(__file__).resolve()!=root/'operator/nof1_image01.py':
        raise ValueError('execute only the frozen operator copy')
    for role,item in plan['roles'].items():
        if (item['parent']!=PARENTS[role] or item['parent_tag']!='remission-shared05-31aa05c-'+role+'-parent:v1'
                or item['tag']!='remission-shared05-31aa05c-'+role+':v1'
                or item['name']!='remission-shared05-31aa05c-'+role+'-qual-v1'
                or item['uid']!=('10002:10002' if role=='learner' else '10001:10001')):
            raise ValueError('literal role identity changed')
    host=plan['host_controller']
    if (set(host)!={'executable','executable_sha256','dependency_status','public_files',*HOST_PROOF}
            or host['executable']!='C:/Python313/python.exe' or host['dependency_status'] not in ('PENDING','ACCEPTED')):
        raise ValueError('literal proposed host controller changed')
    if host['dependency_status']=='PENDING':
        if host['public_files'] or host['executable_sha256']!='UNKNOWN' or any(host[k]!='UNKNOWN' for k in HOST_PROOF):
            raise ValueError('pending host controller dependency must remain unknown')
    elif (host['public_files']!=HOST_FILES or host['executable_sha256']!=HOST_FILES[0]['sha256']
            or any(host[k]!=v for k,v in HOST_PROOF.items())):
        raise ValueError('exact accepted direct-base evidence or public byte bindings changed')
    return root,plan


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
    spec=importlib.util.spec_from_file_location('n48_frozen_lifecycle',root/'operator/analysis_lifecycle.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def image_checked(value,identity,role,*,parent=None):
    if (value['Id']!=identity or re.fullmatch('sha256:[a-f0-9]{64}',identity) is None
            or value['Os']!='linux' or value['Architecture']!='amd64'
            or value['User']!=('10002:10002' if role=='learner' else '10001:10001')
            or value['WorkingDir']!='/app' or value['Entrypoint'] is not None):
        raise ValueError('image ID/platform/UID/entrypoint mismatch')
    if parent and (value['Layers'][:len(parent['Layers'])]!=parent['Layers']
            or len(value['Layers'])<=len(parent['Layers'])
            or any(value[k]!=parent[k] for k in ('User','WorkingDir','Entrypoint','Cmd'))):
        raise ValueError('packaging child changed parent layers or runtime configuration')
    return value


def workload(role,plan):
    return ['python','-I','-B','/qualify/probe.py','--role',role,'--expected','/qualify/expected.json',
        '--expected-sha256',plan['roles'][role]['expected_sha256'],'--probe-sha256',plan['probe_sha256']]


def create_argv(role,plan,image):
    item=plan['roles'][role]
    return ['docker','create','--name',item['name'],'--label','remission.task=shared-image05-31aa05c',
        *LIMITS,'--user',item['uid'],image,*workload(role,plan)]


def checked_container(value,cid,image,role,plan,life):
    item=plan['roles'][role];state=life.checked_state(
        dict(Id=value['Id'],State=value['State'],RestartCount=value['RestartCount']),cid)['State']
    mounts=value['Mounts']
    if (state['Status']!='created' or state['Pid']!=0 or value['Image']!=image
            or value['User']!=item['uid'] or value['Path']!='python' or value['Args']!=workload(role,plan)[1:]
            or value['Labels']!={'remission.task':'shared-image05-31aa05c'}
            or value['Memory']!=2147483648 or value['MemorySwap']!=2147483648
            or value['NanoCpus']!=2000000000 or value['PidsLimit']!=64
            or value['ReadonlyRootfs'] is not True or value['Privileged'] is not False
            or value['CapAdd'] not in (None,[]) or value['CapDrop']!=['ALL'] or value['AutoRemove'] is not False
            or value['SecurityOpt']!=['no-new-privileges'] or value['NetworkMode']!='none'
            or value['Tmpfs']!={'/tmp':'rw,exec,nosuid,nodev,size=512m'}
            or value['PortBindings'] not in (None,{}) or value['PublishAllPorts'] is not False
            or value['RestartPolicy']!={'Name':'no','MaximumRetryCount':0}
            or mounts not in (None,[])):
        raise ValueError('literal prestart qualifier resource/custody/configuration mismatch')


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


def execute(path,authorized):
    root,plan=validate_plan(path,authorized)
    check_host_dependency(plan)
    life=load_lifecycle(root)
    # Exclusive reservation precedes every Docker call, including metadata.
    output=root/'results';output.mkdir(exist_ok=False)
    save(output/'authorization-consumed.json',dict(plan_sha256=authorized,started_unix=time.time(),scope=plan['scope']))
    deadline=time.monotonic()+900;owned=[];images={};parents={};unresolved=[];cleanup=[]
    status='failed';failure=None
    def call(argv,label,*,cap=15,check=True):
        life.check_deadline(deadline)
        value=command_attempt(argv,output,label,min(cap,deadline-time.monotonic()),3)
        failed=(value['exit']!=0 or value.get('error') or value.get('stdout_truncated') or value.get('stderr_truncated'))
        if value['timed_out'] or value['deadline_rejected'] or time.monotonic()>=deadline or (argv[1:2]==['build'] and failed):
            unresolved.append(dict(operation=label,argv=argv,cli_pid=value['cli_pid'],cli_descendants='UNKNOWN',daemon_build='UNKNOWN' if argv[1:2]==['build'] else 'not_applicable'))
            raise life.StopUnconfirmed('command/build outcome unconfirmed: '+label)
        if check and failed:raise RuntimeError('captured command failed: '+label)
        return value['stdout'] if check else value
    def absent(tag,label):
        value=call(['docker','image','inspect','--format','{{.Id}}',tag],label,check=False)
        accepted=('Error response from daemon: No such image: '+tag,'Error: No such image: '+tag)
        if (value['exit']!=1 or value.get('error') or value.get('stdout_truncated') or value.get('stderr_truncated')
                or value['stdout'].strip() or value['stderr'].strip() not in accepted):
            raise RuntimeError('exact selected tag absence not proven: '+label)
    try:
        for role in ROLES:
            item=plan['roles'][role]
            parent=image_checked(json.loads(call(['docker','image','inspect','--format',IMAGE_FORMAT,item['parent']],role+'-parent')),item['parent'],role)
            if parent['Layers']!=item['parent_layers']:raise ValueError('accepted parent layer inventory changed')
            parents[role]=parent;absent(item['parent_tag'],role+'-parent-tag-absence');absent(item['tag'],role+'-child-tag-absence')
            if call(['docker','ps','-aq','--filter','name=^/'+item['name']+'$'],role+'-container-absence').strip():
                raise RuntimeError('qualifier name already exists')
        for role in ROLES:
            item=plan['roles'][role]
            call(['docker','image','tag',item['parent'],item['parent_tag']],role+'-tag-parent')
            if call(['docker','image','inspect','--format','{{.Id}}',item['parent_tag']],role+'-parent-alias-id').strip()!=item['parent']:
                raise ValueError('parent alias drift')
        for role in ROLES:
            item=plan['roles'][role]
            iid=output/(role+'.iid')
            argv=['docker','build','--network','none','--pull=false','--file',str(root/'context/overlay.Dockerfile'),
                '--target',role,'--tag',item['tag'],'--iidfile',str(iid),
                '--build-arg','LEARNER_PARENT='+plan['roles']['learner']['parent_tag'],
                '--build-arg','CONTROLS_PARENT='+plan['roles']['controls']['parent_tag'],str(root/'context')]
            call(argv,role+'-build',cap=300);image=iid.read_text().strip()
            child=image_checked(json.loads(call(['docker','image','inspect','--format',IMAGE_FORMAT,item['tag']],role+'-child')),image,role,parent=parents[role])
            try:cid=life.require_cid(call(create_argv(role,plan,image),role+'-create').strip())
            except BaseException as error:
                unresolved.append(dict(operation=role+'-create',name=item['name'],CID='UNKNOWN',error=repr(error)))
                raise life.StopUnconfirmed('qualifier creation/CID unconfirmed: '+item['name']) from error
            owned.append(cid)
            value=json.loads(call(['docker','inspect','--format',CONTAINER_FORMAT,cid],role+'-prestart'))
            checked_container(value,cid,image,role,plan,life)
            terminal=life.supervise(cid,output/(role+'-supervision'),min(deadline,time.monotonic()+60))
            probe=json.loads(call(['docker','logs',cid],role+'-probe-output'))
            expected=json.loads((root/'qualify'/ (role+'.json')).read_bytes())
            if (probe['status']!='copied_source_metadata_scalar_imports_only' or probe['role']!=role
                    or probe['project_source']!=expected['project_source'] or probe['probe_sha256']!=plan['probe_sha256']
                    or probe['expected_sha256']!=item['expected_sha256']
                    or any(probe.get(k) is not False for k in ('scientific_imports','worker_executed','Store_opened','generated_or_fitted'))):
                raise ValueError('qualifier output/identity/scope mismatch')
            images[role]=dict(metadata=child,cid=cid,terminal=terminal,probe=probe)
        life.check_deadline(deadline);status='qualified_packaging_metadata_scalar_imports_only'
    except BaseException as error:
        failure=repr(error)
        if isinstance(error,life.StopUnconfirmed):status='STOP UNCONFIRMED'
        for cid in reversed(owned):
            try:cleanup.append(dict(cid=cid,events=life.stop_owned(cid)))
            except BaseException as stopped:cleanup.append(dict(cid=cid,error=repr(stopped)));status='STOP UNCONFIRMED'
        raise
    finally:
        save(output/'observed-images.json',dict(status=status,failure=failure,source_commit=SOURCE,plan_sha256=authorized,
            images=images,retained_service=plan['retained_service'],parents=parents,owned_cids=owned,unresolved=unresolved,cleanup=cleanup,finished_unix=time.time(),
            scientific_imports=False,worker_executed=False,Store_opened=False,generation_or_fit=False,
            descendant_or_daemon_termination='UNKNOWN unless separately observed; no removal/retry'))
    return dict(status=status,images={k:v['metadata']['Id'] for k,v in images.items()},
        retained_service=plan['retained_service'])


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze',action='store_true');mode.add_argument('--execute',action='store_true')
    parser.add_argument('--directory',type=Path);parser.add_argument('--root',type=Path)
    parser.add_argument('--plan',type=Path);parser.add_argument('--authorized-plan-sha256');args=parser.parse_args()
    if args.freeze:
        if not args.directory or not args.root:parser.error('freeze requires exact own directory and source root')
        print(json.dumps(freeze(args.directory,args.root)))
    else:
        if not args.plan or not args.authorized_plan_sha256:parser.error('execute requires exact reviewed plan and hash')
        print(json.dumps(execute(args.plan,args.authorized_plan_sha256)))


if __name__=='__main__':main()
