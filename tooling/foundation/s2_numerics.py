"""One fixed S2 qualification proposal, stdlib host only. No authority implied.

Reuses exact accepted NAPI capture/config/host/lifecycle functions. The original
84-file image is dependency-only; eight new public RO carrier files are bound
separately. No science import/decoding, image build or arbitrary module runner.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import ntpath
from pathlib import Path
import re
import subprocess
import sys
import time

SOURCE_BASE='8c32371d15d04a5d155f50ddec6c0b9169abfa08'
NAME='remission-s2-numerics-8c32371-r4'
PRIMITIVE_SHA='2fcdee42c4c16b91d010fc223120d35a7bcb667af254aa939fbe4c2631ae65f8'
DEPENDENCY_BLOB='4bdb33116916ad362ed44d112d4a68f7bc6b6dd9'
DEPENDENCY_SHA='a6c91cac0697f0347d659795d9a7848ce6da14fccf65ed1304d38ed5c609f59e'
MAX_OUTPUT=24*1024*1024
CARRIER={'entry.py':'tooling/foundation/s2_numerics_entry.py',
    'support_s2.py':'contracts/domain/support_s2.py','s2_prediction.py':'methods/support/s2_prediction.py',
    's2_numerics_oracle.py':'tooling/foundation/s2_numerics_oracle.py',
    's2_numerics_unit.py':'tooling/foundation/s2_numerics_unit.py',
    'fixed.json':'tooling/foundation/s2_numerics_inputs/fixed.json',
    'held-out.json':'tooling/foundation/s2_numerics_inputs/held-out.json',
    'supplemental-blind.json':'tooling/foundation/s2_numerics_inputs/supplemental-blind.json'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def ordinary(path):
    path=Path(path).absolute()
    for p in (path,*path.parents):
        if p.is_symlink() or (p.exists() and getattr(p.lstat(),'st_file_attributes',0)&0x400):
            raise ValueError('ordinary literal S2 paths required')
    if any(c in str(path) for c in (',','\n','\r','\0')):raise ValueError('unsafe carrier path')
    return path


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


def load_primitive(folder):
    path=ordinary(folder/'operator/n_api02.py')
    if sha(path.read_bytes())!=PRIMITIVE_SHA:raise ValueError('exact accepted NAPI primitive required')
    spec=importlib.util.spec_from_file_location('s2_exact_napi_primitive',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    # One explicit capture adaptation for this new workload. Ordinary command
    # stdout/stderr remain64KiB; only label unit-output receives24MiB.
    value.MAX_STDOUT=MAX_OUTPUT
    return value


def proposed_argv(image,carrier,digest,limits):
    carrier=ordinary(carrier)
    argv=['docker','create','--name',NAME,*limits,
        '--mount',f'type=bind,source={carrier},target=/qualification,readonly',
        '--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1',
        '--env','MKL_NUM_THREADS=1','--env','NUMEXPR_NUM_THREADS=1',
        image,'python','-I','-B','/qualification/entry.py','--manifest-sha256',digest]
    # Windows CreateProcessW max32767 UTF16 characters including terminating
    # NUL. Leave a strict margin; never send source itself through -c.
    if len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2+1>30000:
        raise ValueError('Windows native command length ceiling exceeded')
    return argv


def checked_mount(mounts,carrier):
    if not isinstance(mounts,list) or len(mounts)!=1:raise ValueError('one RO public carrier mount required')
    value=mounts[0];source=value.get('Source')
    if not isinstance(source,str):raise ValueError('literal mount Source required')
    # Explicit proposed Windows/Docker Desktop spellings only. Unexpected
    # representations fail before start; no discovery or path negotiation.
    expected=ntpath.normcase(str(carrier)).replace('\\','/')
    allowed={expected,'/run/desktop/mnt/host/'+expected[0]+expected[2:],
             '/host_mnt/'+expected[0]+expected[2:]}
    actual=source.replace('\\','/').lower()
    if (actual not in allowed or value.get('Type')!='bind' or value.get('Destination')!='/qualification'
            or value.get('RW') is not False or value.get('Mode') not in ('','ro')
            or value.get('Propagation')!='rprivate'):
        raise ValueError('public literal carrier mount mismatch')


def decode_output(raw):
    if len(raw.encode())>MAX_OUTPUT:raise ValueError('S2 stdout24MiB exceeded')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('duplicate S2 JSON key')
            result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
    if (value['kind']!='S2-NUMERICS-STRUCTURAL-ONLY' or len(value['runs'])!=2
            or any(value[k] is not False for k in ('model_fitted','genuine_data','serving_authority','scientific_parent_imports'))):
        raise ValueError('S2 operation scope mismatch')
    artifacts={};total=0
    for index,draws in enumerate((1000,2000)):
        run=value['runs'][index];result=run['result']
        if (run['returncode']!=0 or run['reaped'] is not True or run['timed_out'] is not False
                or type(run['pid']) is not int or run['pid']<=0 or result['draws']!=draws
                or result['seed']!=91740323 or len(result['cost'])!=2
                or any(result[k] is not False for k in ('model_fitted','genuine_data','serving_authority'))):
            raise ValueError('S2 original child/process identity mismatch')
        for position,label in enumerate(('cold','warm')):
            cost=result['cost'][position]
            if (cost['draws']!=draws or cost['chains']!=4 or cost['targets']!=12 or cost['run']!=label
                    or [row['target'] for row in cost['contexts']]!=[f'UNIT-S2-{i:02}' for i in range(12)]):
                raise ValueError('complete original S2 cost scope required')
        if (len(result['scalar'])!=(112 if draws==1000 else 0)
                or len(result['cdf'])!=(40 if draws==1000 else 0)):
            raise ValueError('S2 complete frozen case counts required')
        groups={'fixed_regression':(64,16),'exposed_heldout_regression':(32,16),
                'supplemental_blind_confirmation':(16,8)}
        for group,(scalar_count,cdf_count) in groups.items():
            if (sum(row['group']==group for row in result['scalar'])!=(scalar_count if draws==1000 else 0)
                    or sum(row['group']==group for row in result['cdf'])!=(cdf_count if draws==1000 else 0)):
                raise ValueError('S2 regression/blind confirmation provenance counts changed')
        item=result['artifact'];name=f'structural-{draws}.npz'
        if (set(item)!={'name','bytes','sha256','base64'} or item['name']!=name
                or type(item['bytes']) is not int or not 0<item['bytes']<=8*1024*1024
                or not isinstance(item['base64'],str) or len(item['base64'])>11184812
                or re.fullmatch('[a-f0-9]{64}',item['sha256']) is None):
            raise ValueError('S2 exact known artifact declaration required')
        data=base64.b64decode(item['base64'],validate=True);total+=len(data)
        if len(data)!=item['bytes'] or sha(data)!=item['sha256'] or total>16*1024*1024:
            raise ValueError('S2 known artifact byte integrity failed')
        artifacts[name]=data
        result['artifact']={k:v for k,v in item.items() if k!='base64'}
    return value,artifacts


def controller(plan,folder,primitive,life,call,deadline):
    dependency=json.loads((folder/'payload/dependency.json').read_bytes())
    image=dependency['learner_image'];argv=proposed_argv(image,folder/'payload',plan['manifest_sha256'],primitive.LIMITS)
    cid=None
    try:
        image_format='{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"Layers":{{json .RootFS.Layers}},"User":{{json .Config.User}},"WorkingDir":{{json .Config.WorkingDir}},"Entrypoint":{{json (index .Config "Entrypoint")}},"Cmd":{{json .Config.Cmd}}}'
        if json.loads(call(['docker','image','inspect','--format',image_format,image],'image',deadline))!=dependency['qualified_image_config']:
            raise ValueError('S2 accepted dependency image/config changed')
        if call(['docker','ps','-aq','--filter','name=^/'+NAME+'$'],'absence',deadline).strip():raise ValueError('fresh S2 literal name occupied')
        try:cid=life.require_cid(call(argv,'create',deadline).strip())
        except Exception as error:raise life.StopUnconfirmed('S2 create/CID unknown') from error
        typed=json.loads(call(['docker','inspect','--format',primitive.STATE_FORMAT,cid],'prestart',deadline))
        checked_mount(typed['Mounts'],folder/'payload')
        checked=dict(typed,Mounts=[])
        primitive.checked_created(checked,cid,image,argv,life)
        terminal=life.supervise(cid,folder/'results/supervision',deadline)
        result,artifacts=decode_output(call(['docker','logs',cid],'unit-output',deadline))
        destination=folder/'results/structural-artifacts';destination.mkdir(exist_ok=False)
        for name,data in artifacts.items():
            with (destination/name).open('xb') as stream:stream.write(data)
        life.check_deadline(deadline)
        return dict(status='S2_STRUCTURAL_ONLY',cid=cid,terminal=terminal,result=result)
    except BaseException as primary:
        if cid is not None:
            try:events=life.stop_owned(cid)
            except BaseException as error:raise life.StopUnconfirmed('S2 literal owned CID stop unknown') from error
            save(folder/'results/cleanup.json',dict(cid=cid,primary=repr(primary),events=events))
        raise


def freeze(folder,source):
    source=ordinary(source);folder=ordinary(folder)
    # Sealed input absence hard-blocks all final packet creation. No substitute.
    if any(not (source/CARRIER[name]).is_file() for name in ('held-out.json','supplemental-blind.json')):
        raise ValueError('sealed inputs not released; no executable final packet')
    if folder.exists() or not folder.is_relative_to(source/'artifacts'):raise ValueError('fresh own S2 packet required')
    dependency=subprocess.check_output(['git','show',DEPENDENCY_BLOB],cwd=source,timeout=15)
    if sha(dependency)!=DEPENDENCY_SHA:raise ValueError('accepted dependency identity changed')
    entries={f'payload/{name}':ordinary(source/path).read_bytes() for name,path in CARRIER.items()}
    entries['payload/dependency.json']=dependency
    manifest=dict(kind='S2-fixed-public-carrier-v1',files={Path(k).name:dict(bytes=len(v),sha256=sha(v)) for k,v in entries.items()})
    manifest_raw=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode();entries['payload/manifest.json']=manifest_raw
    entries.update({'operator/s2_numerics.py':Path(__file__).read_bytes(),
        'operator/n_api02.py':(source/'tooling/foundation/n_api02.py').read_bytes(),
        'operator/analysis_lifecycle.py':(source/'tooling/foundation/analysis_lifecycle.py').read_bytes()})
    if sha(entries['operator/n_api02.py'])!=PRIMITIVE_SHA:raise ValueError('accepted primitive bytes changed')
    folder.mkdir(parents=True,exist_ok=False)
    for name,data in entries.items():
        p=folder/name;p.parent.mkdir(exist_ok=True)
        with p.open('xb') as stream:stream.write(data)
    plan=dict(kind='S2-fixed-numerics-proposal-v1',source_base=SOURCE_BASE,
        implementation_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,timeout=15).decode().strip(),
        root=str(folder),name=NAME,lifecycle_seconds=600,parent_work_seconds=570,child_seconds=300,
        manifest_sha256=sha(manifest_raw),files={k:dict(bytes=len(v),sha256=sha(v)) for k,v in entries.items()},
        host_science=False,model_fitted=False,serving_authority=False)
    save(folder/'plan.json',plan)
    return dict(plan=str(folder/'plan.json'),sha256=sha((folder/'plan.json').read_bytes()))


def validate(path,authorized):
    path=ordinary(path);raw=path.read_bytes()
    if sha(raw)!=authorized:raise ValueError('exact independent S2 operation plan required')
    plan=json.loads(raw);folder=ordinary(plan['root'])
    expected={'payload/'+name for name in (*CARRIER,'dependency.json','manifest.json')}
    expected|={'operator/s2_numerics.py','operator/n_api02.py','operator/analysis_lifecycle.py'}
    if (folder!=path.parent or plan['kind']!='S2-fixed-numerics-proposal-v1' or plan['name']!=NAME
            or plan['source_base']!=SOURCE_BASE or plan['lifecycle_seconds']!=600
            or plan['parent_work_seconds']!=570 or plan['child_seconds']!=300
            or set(plan['files'])!=expected or any(plan[k] is not False for k in ('host_science','model_fitted','serving_authority'))):
        raise ValueError('S2 exact source/scope/caps mismatch')
    actual={p.relative_to(folder).as_posix() for sub in ('payload','operator') for p in (folder/sub).rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('S2 frozen inventory mismatch')
    for name,row in plan['files'].items():
        raw=ordinary(folder/name).read_bytes()
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('S2 frozen file changed')
    if sha((folder/'payload/dependency.json').read_bytes())!=DEPENDENCY_SHA:raise ValueError('S2 accepted dependency changed')
    if sha((folder/'payload/manifest.json').read_bytes())!=plan['manifest_sha256']:raise ValueError('S2 carrier manifest changed')
    if Path(__file__).resolve()!=folder/'operator/s2_numerics.py':raise ValueError('frozen S2 operator required')
    return folder,plan


def execute(path,authorized):
    folder,plan=validate(path,authorized);primitive=load_primitive(folder)
    primitive.check_host_dependency(json.loads((folder/'payload/dependency.json').read_bytes()))
    life=primitive.load_lifecycle(folder)
    output=folder/'results';output.mkdir(exist_ok=False)
    save(output/'authorization-consumed.json',dict(plan_sha256=authorized,started_unix=time.time(),scope='S2_STRUCTURAL_NUMERICS_ONLY'))
    deadline=time.monotonic()+600;result=None;error=None;status='failed'
    def call(argv,label,end):
        life.check_deadline(end);row=primitive.command_attempt(argv,output,label,min(15,end-time.monotonic()),3)
        if row['timed_out'] or row['deadline_rejected'] or time.monotonic()>=end:raise life.StopUnconfirmed('S2 CLI/descendants unknown')
        if row['exit']!=0 or row.get('error') or row.get('stdout_truncated') or row.get('stderr_truncated'):raise RuntimeError('S2 bounded command failed: '+label)
        return row['stdout']
    try:
        result=controller(plan,folder,primitive,life,call,deadline);status='S2_STRUCTURAL_NUMERICS_PASS'
    except BaseException as failure:
        error=repr(failure)
        if isinstance(failure,life.StopUnconfirmed):status='STOP_UNCONFIRMED'
        raise
    finally:save(output/'observed.json',dict(status=status,error=error,result=result,host_science=False,model_fitted=False,host_descendants='UNKNOWN'))
    return dict(status=status,cid=result['cid'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--freeze',action='store_true');group.add_argument('--execute',action='store_true')
    parser.add_argument('--directory',type=Path);parser.add_argument('--source',type=Path)
    parser.add_argument('--plan',type=Path);parser.add_argument('--authorized-plan-sha256');args=parser.parse_args()
    if args.freeze:
        if not args.directory or not args.source:parser.error('directory/source required')
        print(json.dumps(freeze(args.directory,args.source)))
    else:
        if not args.plan or not args.authorized_plan_sha256:parser.error('exact plan/authorization hash required')
        print(json.dumps(execute(args.plan,args.authorized_plan_sha256)))
