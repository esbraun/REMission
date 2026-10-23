"""One fixed S2 graph qualification proposal; host stdlib bytes/JSON only.

Default preparation confers no operation authority. Only a separately reviewed
frozen packet and fresh once-only root GO admit execution. No graph imports here.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import ntpath
from pathlib import Path
import re
import subprocess
import time

SOURCE_BASE='5ed3eb9be56bd338433c24a05c2dc3ac8e77e1e1'
NAME='remission-s2-graph-5ed3eb9-r1'
PRIMITIVE_SHA='2fcdee42c4c16b91d010fc223120d35a7bcb667af254aa939fbe4c2631ae65f8'
LIFECYCLE_SHA='45cb568da0dd93642ab48fd5edb2aef76394393a1777c3c05c5645259f88ef2b'
DEPENDENCY_BLOB='4bdb33116916ad362ed44d112d4a68f7bc6b6dd9'
DEPENDENCY_SHA='a6c91cac0697f0347d659795d9a7848ce6da14fccf65ed1304d38ed5c609f59e'
PLAN_CRITIQUE='990ae7aeae3633035db622138fc8ec5da3d0c7ef'
MAX_OUTPUT=3*1024*1024
CARRIER={
    'entry.py':'tooling/foundation/s2_graph_entry.py',
    'contracts/domain/support_s2.py':'contracts/domain/support_s2.py',
    'contracts/domain/support_s2_fit.py':'contracts/domain/support_s2_fit.py',
    'methods/support/s2_data.py':'methods/support/s2_data.py',
    'methods/support/s2_model.py':'methods/support/s2_model.py',
    'tooling/foundation/s2_model_qualification.py':'tooling/foundation/s2_model_qualification.py',
    'tooling/foundation/pa3_monitor.py':'tooling/foundation/pa3_monitor.py',
    'tooling/foundation/pa3-cvm-policy.json':'tooling/foundation/pa3-cvm-policy.json',
    's2_model_fixtures.py':'tests/s2_model_fixtures.py'}
RESOURCES=dict(outer_seconds=1200,setup_seconds=60,metadata_seconds=5,create_seconds=10,
    host_work_cutoff_seconds=1140,child_seconds=1080,parent_reserve_seconds=30,
    cross_os_transit_reserve_seconds=60,cpus=2,memory_bytes=2147483648,
    swap_bytes=2147483648,pids=256,tmpfs_mib=512,native_threads=1,
    child_stdout_bytes=2097152,parent_stdout_bytes=3145728,stderr_bytes=65536)
GATES=dict(density_atol=1e-8,normalizer_atol=1e-10,gradient_atol=1e-5,
    gradient_rtol=1e-5,steps=[1e-4,3e-5,1e-5,3e-6])


def sha(raw):return hashlib.sha256(raw).hexdigest()


def ordinary(path):
    path=Path(path).absolute()
    for item in (path,*path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(),'st_file_attributes',0)&0x400):
            raise ValueError('ordinary fixed public paths required')
    if any(c in str(path) for c in (',','\n','\r','\0')):raise ValueError('unsafe literal path')
    return path


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


def encoded(value):return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()


def strict_json(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('duplicate JSON key')
            value[key]=item
        return value
    def finite(value):
        result=float(value)
        if not math.isfinite(result):raise ValueError('nonfinite JSON number')
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_float=finite,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))


def load_primitive(folder):
    path=ordinary(folder/'operator/n_api02.py')
    if sha(path.read_bytes())!=PRIMITIVE_SHA:raise ValueError('accepted NAPI primitive changed')
    spec=importlib.util.spec_from_file_location('s2_graph_exact_napi',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    value.MAX_STDOUT=MAX_OUTPUT  # Only unit-output; ordinary CLI/stderr64KiB unchanged.
    return value


def relative_budget(start,now):
    # Only host monotonic values enter this calculation. Transfer a duration,
    # never a Windows epoch. Reserve the FULL setup/transit cap even after setup.
    if now-start>=60:raise TimeoutError('absolute setup lease exhausted')
    value=min(1080.,start+1140-now-60)
    if value<=33:raise TimeoutError('insufficient graph work/reap budget')
    return value


def proposed_argv(image,carrier,digest,budget,limits):
    if type(budget) is not float or not 33<budget<=1080:raise ValueError('fixed relative budget')
    carrier=ordinary(carrier);limits=list(limits)
    if limits.count('64')!=1:raise ValueError('accepted PID64 base required')
    limits[limits.index('64')]='256'
    argv=['docker','create','--name',NAME,*limits,
        '--mount',f'type=bind,source={carrier},target=/qualification,readonly',
        '--env','S2_MODEL_SYMBOLIC_QUALIFY=1',
        '--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1',
        '--env','MKL_NUM_THREADS=1','--env','NUMEXPR_NUM_THREADS=1',
        image,'python','-I','-B','/qualification/entry.py','--manifest-sha256',digest,
        '--budget',str(budget)]
    if len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2+1>30000:
        raise ValueError('Windows command-length ceiling')
    return argv


def checked_mount(mounts,carrier):
    if not isinstance(mounts,list) or len(mounts)!=1:raise ValueError('one fixed public RO mount')
    row=mounts[0];source=row.get('Source')
    if not isinstance(source,str):raise ValueError('literal mount source')
    expected=ntpath.normcase(str(carrier)).replace('\\','/')
    allowed={expected,'/run/desktop/mnt/host/'+expected[0]+expected[2:],
             '/host_mnt/'+expected[0]+expected[2:]}
    if (source.replace('\\','/').lower() not in allowed or row.get('Type')!='bind'
            or row.get('Destination')!='/qualification' or row.get('RW') is not False
            or row.get('Mode') not in ('','ro') or row.get('Propagation')!='rprivate'):
        raise ValueError('literal readonly carrier mismatch')


def checked_created(value,cid,image,argv,carrier,primitive,life):
    checked_mount(value['Mounts'],carrier)
    if type(value['PidsLimit']) is not int or value['PidsLimit']!=256:raise ValueError('exact graph PID256')
    # Only the two explicitly verified workload deltas are projected away.
    # Every unchanged isolation/resource/state/argv field remains primitive-gated.
    primitive.checked_created(dict(value,Mounts=[],PidsLimit=64),cid,image,argv,life)


def decode_output(raw):
    if len(raw.encode())>MAX_OUTPUT:raise ValueError('graph parent stdout ceiling')
    value=strict_json(raw)
    if (value['kind']!='S2-GRAPH-STRUCTURAL-ONLY'
            or any(value[k] is not False for k in ('scientific_parent_imports','model_fitted','genuine_data','serving_authority'))):
        raise ValueError('graph scope mismatch')
    run=value['run'];custody=run['custody'];result=run['result']
    if (type(custody['pid']) is not int or custody['pid']<=0 or custody['returncode']!=0
            or custody['reaped'] is not True or custody['timed_out'] is not False
            or result['kind']!='S2-ORIGINAL-COORDINATE-DENSITY-GRADIENT-STRUCTURAL-ONLY'
            or result['qualification_fixture_only'] is not True
            or any(result[k] is not False for k in ('model_fitted','genuine_data','serving_authority'))
            or len(result['density'])!=11 or len(result['shapes'])!=2):raise ValueError('complete graph result/custody required')
    expected=[('observed',n,rho) for n in (1,2) for rho in (-.949999,-.4,0.,.4,.949999)]
    expected.append(('prior_only_empty_rows',1,0.))
    if [(r['fixture'],r['members'],r['rho']) for r in result['density']]!=expected:
        raise ValueError('complete fixed graph points required')
    for row in result['density']:
        names=['mu_alpha','mu_tau','b','s_alpha','s_tau','s_e','s_Q','rho','z','u']+['epsilon_'+str(i) for i in range(row['members'])]
        if (row['value_variable_order']!=names
                or [item['label'] for item in row['compiled']]!=['full','gradient','likelihood',*['prior:'+n for n in names]]):
            raise ValueError('every original-coordinate compiled function required')
        if (len(row['gradient_sweeps'])!=8 or len(row['directions'])!=2
                or [(v['direction'],v['step']) for v in row['gradient_sweeps']]!=[(d,s) for d in (0,1) for s in GATES['steps']]):
            raise ValueError('complete two-direction four-step sweep required')
        if row['fixture']=='prior_only_empty_rows' and (row['likelihood_actual']!=0 or row['negative_controls']):
            raise ValueError('prior-only exact-zero fixture required')
    for row,day in zip(result['shapes'],(14,28)):
        if row['cutoff']!=day or row['compiled'] is not False or len(row['members'])!=12:
            raise ValueError('full12 shape-only scope required')
    return value


def controller(plan,folder,primitive,life,call,start):
    dependency=strict_json((folder/'payload/dependency.json').read_bytes())
    image=dependency['learner_image'];cid=None;work=start+1140;setup=start+60
    try:
        image_format='{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"Layers":{{json .RootFS.Layers}},"User":{{json .Config.User}},"WorkingDir":{{json .Config.WorkingDir}},"Entrypoint":{{json (index .Config "Entrypoint")}},"Cmd":{{json .Config.Cmd}}}'
        if strict_json(call(['docker','image','inspect','--format',image_format,image],'image',setup))!=dependency['qualified_image_config']:
            raise ValueError('accepted learner dependency/config mismatch')
        if call(['docker','ps','-aq','--filter','name=^/'+NAME+'$'],'absence',setup).strip():raise ValueError('fresh literal name occupied')
        budget=relative_budget(start,time.monotonic())
        argv=proposed_argv(image,folder/'payload',plan['manifest_sha256'],budget,primitive.LIMITS)
        try:cid=life.require_cid(call(argv,'create',setup).strip())
        except BaseException as error:raise life.StopUnconfirmed('graph create/CID unknown') from error
        typed=strict_json(call(['docker','inspect','--format',primitive.STATE_FORMAT,cid],'prestart',setup))
        checked_created(typed,cid,image,argv,folder/'payload',primitive,life)
        if time.monotonic()+5>=setup:raise TimeoutError('setup lease lacks fixed five-second prearm reserve')
        # Watchdog epoch belongs solely to this host. Linux receives only budget.
        terminal=life.supervise(cid,folder/'results/supervision',work)
        result=decode_output(call(['docker','logs',cid],'unit-output',start+1200))
        life.check_deadline(start+1200)
        return dict(status='S2_GRAPH_STRUCTURAL_ONLY',cid=cid,terminal=terminal,result=result,
            transferred_parent_seconds=budget,host_work_deadline=work,host_outer_deadline=start+1200)
    except BaseException:
        if cid is not None:
            try:events=life.stop_owned(cid)
            except BaseException as error:raise life.StopUnconfirmed('graph exact-CID stop unknown') from error
            save(folder/'results/cleanup.json',dict(cid=cid,events=events))
        raise


def freeze(folder,source):
    source=ordinary(source);folder=ordinary(folder)
    if folder.exists() or not folder.is_relative_to(source/'artifacts'):raise ValueError('fresh own graph packet required')
    dependency=subprocess.check_output(['git','show',DEPENDENCY_BLOB],cwd=source,timeout=15)
    if sha(dependency)!=DEPENDENCY_SHA:raise ValueError('accepted dependency bytes changed')
    resources=encoded(RESOURCES)
    settings=encoded(dict(GATES,operation_review=PLAN_CRITIQUE,resource_plan_sha256=sha(resources)))
    entries={'payload/'+name:ordinary(source/path).read_bytes() for name,path in CARRIER.items()}
    entries.update({'payload/dependency.json':dependency,'payload/resources.json':resources,'payload/settings.json':settings})
    manifest=encoded(dict(kind='S2-fixed-graph-carrier-v1',files={k.removeprefix('payload/'):dict(bytes=len(v),sha256=sha(v)) for k,v in entries.items()}))
    entries['payload/manifest.json']=manifest
    entries.update({'operator/s2_graph.py':Path(__file__).read_bytes(),
        'operator/n_api02.py':(source/'tooling/foundation/n_api02.py').read_bytes(),
        'operator/analysis_lifecycle.py':(source/'tooling/foundation/analysis_lifecycle.py').read_bytes()})
    if sha(entries['operator/n_api02.py'])!=PRIMITIVE_SHA or sha(entries['operator/analysis_lifecycle.py'])!=LIFECYCLE_SHA:
        raise ValueError('accepted host primitives changed')
    folder.mkdir(parents=True,exist_ok=False)
    for name,raw in entries.items():
        path=folder/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    plan=dict(kind='S2-fixed-graph-proposal-v1',source_base=SOURCE_BASE,name=NAME,root=str(folder),
        preparation_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,timeout=15).decode().strip(),
        resources=RESOURCES,manifest_sha256=sha(manifest),files={k:dict(bytes=len(v),sha256=sha(v)) for k,v in entries.items()},
        host_science=False,model_fitted=False,serving_authority=False)
    save(folder/'plan.json',plan)
    return dict(plan=str(folder/'plan.json'),sha256=sha((folder/'plan.json').read_bytes()))


def validate(path,authorized):
    path=ordinary(path);raw=path.read_bytes()
    if sha(raw)!=authorized:raise ValueError('exact independent graph operation plan required')
    plan=strict_json(raw);folder=ordinary(plan['root'])
    expected={'payload/'+name for name in (*CARRIER,'dependency.json','settings.json','resources.json','manifest.json')}
    expected|={'operator/s2_graph.py','operator/n_api02.py','operator/analysis_lifecycle.py'}
    if (folder!=path.parent or plan['kind']!='S2-fixed-graph-proposal-v1' or plan['name']!=NAME
            or plan['source_base']!=SOURCE_BASE or plan['resources']!=RESOURCES
            or re.fullmatch('[a-f0-9]{40}',plan['preparation_head']) is None
            or set(plan['files'])!=expected or any(plan[k] is not False for k in ('host_science','model_fitted','serving_authority'))):
        raise ValueError('graph exact source/scope/caps mismatch')
    actual=set()
    for sub in ('payload','operator'):
        for path in (folder/sub).rglob('*'):
            ordinary(path)
            if path.is_file():actual.add(path.relative_to(folder).as_posix())
    if actual!=expected:raise ValueError('graph exact packet inventory mismatch')
    for name,row in plan['files'].items():
        raw=ordinary(folder/name).read_bytes()
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('graph frozen bytes changed')
    if sha((folder/'payload/dependency.json').read_bytes())!=DEPENDENCY_SHA:raise ValueError('accepted dependency changed')
    if sha((folder/'payload/manifest.json').read_bytes())!=plan['manifest_sha256']:raise ValueError('graph carrier manifest changed')
    if strict_json((folder/'payload/resources.json').read_bytes())!=RESOURCES:raise ValueError('graph resource leaf mismatch')
    settings=dict(GATES,operation_review=PLAN_CRITIQUE,resource_plan_sha256=sha((folder/'payload/resources.json').read_bytes()))
    if strict_json((folder/'payload/settings.json').read_bytes())!=settings:raise ValueError('exact fixed gates/admission metadata mismatch')
    if Path(__file__).resolve()!=folder/'operator/s2_graph.py':raise ValueError('frozen graph operator required')
    return folder,plan


def execute(path,authorized):
    start=time.monotonic()  # Absolute outer lease starts before metadata/helper setup.
    folder,plan=validate(path,authorized);primitive=load_primitive(folder)
    primitive.check_host_dependency(strict_json((folder/'payload/dependency.json').read_bytes()))
    life=primitive.load_lifecycle(folder)
    output=folder/'results';output.mkdir(exist_ok=False)
    save(output/'authorization-consumed.json',dict(plan_sha256=authorized,started_unix=time.time(),scope='S2_GRAPH_STRUCTURAL_ONLY'))
    result=None;error=None;status='failed'
    def call(argv,label,end):
        life.check_deadline(end)
        cap=10 if label=='create' else 5
        row=primitive.command_attempt(argv,output,label,min(cap,end-time.monotonic()),3)
        if row['timed_out'] or row['deadline_rejected'] or time.monotonic()>=end:
            raise life.StopUnconfirmed('graph CLI/descendants outcome unknown')
        if row['exit']!=0 or row.get('error') or row.get('stdout_truncated') or row.get('stderr_truncated'):
            raise RuntimeError('bounded graph command failed: '+label)
        return row['stdout']
    try:
        result=controller(plan,folder,primitive,life,call,start);status='S2_GRAPH_STRUCTURAL_PASS'
    except BaseException as failure:
        error=type(failure).__name__
        if isinstance(failure,life.StopUnconfirmed):status='STOP_UNCONFIRMED'
        raise
    finally:save(output/'observed.json',dict(status=status,error_class=error,result=result,
        host_science=False,model_fitted=False,serving_authority=False,host_descendants='UNKNOWN'))
    return dict(status=status,cid=result['cid'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze',action='store_true');mode.add_argument('--execute',action='store_true')
    parser.add_argument('--directory',type=Path);parser.add_argument('--source',type=Path)
    parser.add_argument('--plan',type=Path);parser.add_argument('--authorized-plan-sha256');args=parser.parse_args()
    if args.freeze:
        if not args.directory or not args.source:parser.error('fixed directory/source required')
        print(json.dumps(freeze(args.directory,args.source)))
    else:
        if not args.plan or not args.authorized_plan_sha256:parser.error('exact plan/authorized SHA required')
        print(json.dumps(execute(args.plan,args.authorized_plan_sha256)))
