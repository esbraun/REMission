"""One reviewed controls-only COPY qualification; no application operation.

Reuses the accepted IMAGE05 regular-file command runner and strict lifecycle.
Only --execute can invoke Docker; packet preparation is a separate source step.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

SOURCE='0cce8aee2c89a153ddb9da12a9f033cfd11cad1c'
PARENT='sha256:615beab9880965ab25b32c3b27d6a525f716e361583e26a665fbff1861739273'
NAMESPACE='remission-s1-diag-image-261023-r1'
PARENT_TAG=NAMESPACE+'-parent:v1'
CHILD_TAG=NAMESPACE+':v1'
QUALIFIER=NAMESPACE+'-qualifier'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def validate(path,authorized):
    path=path.absolute();raw=path.read_bytes()
    if sha(raw)!=authorized:raise ValueError('exact reviewed plan hash required')
    plan=json.loads(raw);root=path.parent
    if (root.as_posix()!=plan['root'] or plan['kind']!='s1-diagnostic-controls-COPY-qualification-r1'
            or plan['source_commit']!=SOURCE or plan['parent']!=PARENT
            or plan['namespace']!=NAMESPACE or plan['parent_tag']!=PARENT_TAG
            or plan['child_tag']!=CHILD_TAG or plan['qualifier']!=QUALIFIER
            or plan['bounds']!=dict(phase_seconds=900,build_seconds=300,qualification_seconds=60,cli_cleanup_seconds=3)
            or plan['future_image']!='UNKNOWN' or plan['future_CID']!='UNKNOWN'
            or plan['project_files']!=196 or plan['output']!='results'):
        raise ValueError('literal operation identity or bounds changed')
    # No hidden or aliased input in the tiny public packet. Unknown files are
    # metadata-only failures; do not read their contents.
    actual=set()
    for folder in ('context','qualify','operator','proof'):
        for item in (root/folder).rglob('*'):
            if item.is_symlink() or getattr(item.lstat(),'st_file_attributes',0)&0x400:
                raise ValueError('aliased input denied')
            if item.is_file():actual.add(item.relative_to(root).as_posix())
    if actual!=set(plan['files']):raise ValueError('frozen input inventory changed')
    for name,row in plan['files'].items():
        item=root/name
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('escaped input')
        for part in (item,*item.parents):
            if part.is_symlink() or getattr(part.lstat(),'st_file_attributes',0)&0x400:
                raise ValueError('aliased input ancestry denied')
        value=item.read_bytes()
        if len(value)!=row['bytes'] or sha(value)!=row['sha256']:raise ValueError('frozen input changed')
    if Path(__file__).resolve()!=root/'operator/s1_diagnostic_image.py':raise ValueError('frozen operator only')
    shared=load(root/'operator/image05_shared.py','s1_exact_image05_shared')
    shared.ordinary(root)
    if (plan['host_controller']['public_files']!=shared.HOST_FILES
            or any(plan['host_controller'][k]!=v for k,v in shared.HOST_PROOF.items())
            or plan['host_controller']['executable']!='C:/Python313/python.exe'
            or plan['host_controller']['dependency_status']!='ACCEPTED'
            or list(sys.version_info[:3])!=[3,13,7] or sys.flags.isolated!=1 or sys.flags.dont_write_bytecode!=1
            or Path(sys._base_executable).as_posix().casefold()!=plan['host_controller']['executable'].casefold()):
        raise ValueError('accepted direct-base identity changed')
    shared.check_host_dependency(plan)
    expected=json.loads((root/'qualify/controls.json').read_bytes())
    parent_map=json.loads((root/'proof/parent-expected.json').read_bytes())['project_source']
    if (expected['role']!='controls' or expected['uid']!=10001 or len(parent_map)!=195
            or len(expected['project_source'])!=196):raise ValueError('complete expected map required')
    closure=dict(parent_map)
    for row in plan['overlay']:
        closure[row['destination']]=row['sha256']
    if closure!=expected['project_source']:raise ValueError('parent plus exact overlay closure changed')
    return root,plan,shared


def checked_container(value,cid,image,plan,life,shared):
    # Same IMAGE05 predicate with only this operation's fixed task label/name.
    state=life.checked_state(dict(Id=value['Id'],State=value['State'],RestartCount=value['RestartCount']),cid)['State']
    if (state['Status']!='created' or state['Pid']!=0 or value['Image']!=image
            or value['User']!='10001:10001' or value['Path']!='python'
            or value['Args']!=shared.workload('controls',plan)[1:]
            or value['Labels']!={'remission.task':NAMESPACE}
            or value['Memory']!=2147483648 or value['MemorySwap']!=2147483648
            or value['NanoCpus']!=2000000000 or value['PidsLimit']!=64
            or value['ReadonlyRootfs'] is not True or value['Privileged'] is not False
            or value['CapAdd'] not in (None,[]) or value['CapDrop']!=['ALL'] or value['AutoRemove'] is not False
            or value['SecurityOpt']!=['no-new-privileges'] or value['NetworkMode']!='none'
            or value['Tmpfs']!={'/tmp':'rw,exec,nosuid,nodev,size=512m'}
            or value['PortBindings'] not in (None,{}) or value['PublishAllPorts'] is not False
            or value['RestartPolicy']!={'Name':'no','MaximumRetryCount':0} or value['Mounts'] not in (None,[])):
        raise ValueError('literal prestart qualifier configuration mismatch')


def execute(path,authorized):
    root,plan,shared=validate(path,authorized);life=shared.load_lifecycle(root)
    output=root/'results';output.mkdir(exist_ok=False)
    shared.save(output/'authorization-consumed.json',dict(plan_sha256=authorized,started_unix=time.time(),scope=plan['kind']))
    deadline=time.monotonic()+900;owned=[];images={};parents={};unresolved=[];cleanup=[];status='failed';failure=None
    def call(argv,label,*,cap=15,check=True):
        life.check_deadline(deadline)
        value=shared.command_attempt(argv,output,label,min(cap,deadline-time.monotonic()),3)
        failed=(value['exit']!=0 or value.get('error') or value.get('stdout_truncated') or value.get('stderr_truncated'))
        if value['timed_out'] or value['deadline_rejected'] or time.monotonic()>=deadline or (argv[1:2]==['build'] and failed):
            unresolved.append(dict(operation=label,cli_pid=value['cli_pid'],cli_descendants='UNKNOWN',daemon_build='UNKNOWN' if argv[1:2]==['build'] else 'not_applicable'))
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
        parent=shared.image_checked(json.loads(call(['docker','image','inspect','--format',shared.IMAGE_FORMAT,PARENT],'controls-parent')),PARENT,'controls')
        if parent!=plan['parent_metadata']:raise ValueError('exact accepted parent metadata changed')
        parents['controls']=parent
        absent(PARENT_TAG,'parent-tag-absence');absent(CHILD_TAG,'child-tag-absence')
        if call(['docker','ps','-aq','--filter','name=^/'+QUALIFIER+'$'],'qualifier-name-absence').strip():raise RuntimeError('qualifier exists')
        call(['docker','image','tag',PARENT,PARENT_TAG],'tag-parent')
        if call(['docker','image','inspect','--format','{{.Id}}',PARENT_TAG],'parent-alias-id').strip()!=PARENT:raise ValueError('parent alias drift')
        iid=output/'controls.iid'
        call(['docker','build','--network','none','--pull=false','--file',str(root/'context/overlay.Dockerfile'),
            '--tag',CHILD_TAG,'--iidfile',str(iid),'--build-arg','CONTROLS_PARENT='+PARENT_TAG,str(root/'context')],'controls-build',cap=300)
        image=iid.read_text().strip()
        child=shared.image_checked(json.loads(call(['docker','image','inspect','--format',shared.IMAGE_FORMAT,CHILD_TAG],'controls-child')),image,'controls',parent=parent)
        try:
            cid=life.require_cid(call(['docker','create','--name',QUALIFIER,'--label','remission.task='+NAMESPACE,
                *shared.LIMITS,'--user','10001:10001',image,*shared.workload('controls',plan)],'controls-create').strip())
        except BaseException as error:
            unresolved.append(dict(operation='controls-create',name=QUALIFIER,CID='UNKNOWN',error_type=type(error).__name__))
            raise life.StopUnconfirmed('qualifier creation/CID unconfirmed') from error
        owned.append(cid)
        value=json.loads(call(['docker','inspect','--format',shared.CONTAINER_FORMAT,cid],'controls-prestart'))
        checked_container(value,cid,image,plan,life,shared)
        terminal=life.supervise(cid,output/'controls-supervision',min(deadline,time.monotonic()+60))
        probe=json.loads(call(['docker','logs',cid],'controls-probe-output'))
        expected=json.loads((root/'qualify/controls.json').read_bytes())
        if (probe['status']!='copied_source_metadata_scalar_imports_only' or probe['role']!='controls'
                or probe['project_source']!=expected['project_source'] or probe['probe_sha256']!=plan['probe_sha256']
                or probe['expected_sha256']!=plan['roles']['controls']['expected_sha256']
                or any(probe.get(k) is not False for k in ('scientific_imports','worker_executed','Store_opened','generated_or_fitted'))):
            raise ValueError('qualifier output/identity/scope mismatch')
        images['controls']=dict(metadata=child,cid=cid,terminal=terminal,probe=probe)
        life.check_deadline(deadline);status='qualified_packaging_metadata_scalar_imports_only'
    except BaseException as error:
        failure=type(error).__name__
        if isinstance(error,life.StopUnconfirmed):status='STOP UNCONFIRMED'
        for cid in reversed(owned):
            try:cleanup.append(dict(cid=cid,events=life.stop_owned(cid)))
            except BaseException as stopped:cleanup.append(dict(cid=cid,error_type=type(stopped).__name__));status='STOP UNCONFIRMED'
        raise
    finally:
        shared.save(output/'observed-images.json',dict(status=status,failure=failure,source_commit=SOURCE,plan_sha256=authorized,
            images=images,parents=parents,owned_cids=owned,unresolved=unresolved,cleanup=cleanup,finished_unix=time.time(),
            scientific_imports=False,worker_executed=False,Store_opened=False,generation_or_fit=False,
            descendant_or_daemon_termination='UNKNOWN unless separately observed; no removal/retry'))
    return dict(status=status,image=images['controls']['metadata']['Id'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true',required=True)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--authorized-plan-sha256',required=True)
    args=parser.parse_args();print(json.dumps(execute(args.plan,args.authorized_plan_sha256)))
