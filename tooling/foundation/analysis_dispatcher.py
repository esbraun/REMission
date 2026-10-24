"""One reviewed ordinary cohort attempt through the existing background worker.

Host uses stdlib plus pinned non-numerical Pydantic admission. Freeze and review
one invocation. No discovery cleanup, global interrupt, retries or removal.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from analysis_lifecycle import (StopUnconfirmed, check_deadline, command,
    inspect, require_cid, save, stop_owned, supervise)

COMMON=['--network','none','--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','64',
    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m','--restart','no']

# Prospective ceilings, never measurements of genuine n12 output sizes.
N_FILE_CAPS={'result.json':2*1024**2,'diagnostics.json':1024**2,'ownership.json':2*1024**2,
    'posterior.nc':256*1024**2,'expected-contrast.npz':2*1024**2,'predictive.npz':8*1024**2}
N_TOTAL_CAP=271*1024**2
N_PROGRESS_CAP=2048
N_JSON_ROWS=12000
N_INPUT_CAP=8*1024**2


def n_packet(state):
    packet=state.get('n_fit04')
    if (not isinstance(packet,dict) or set(packet)!={'schema','executable','file_caps','total_cap','progress_cap',
            'json_rows','data03_actual','queue_export_actual','source_review','operation_review','root_go'}
            or packet['schema']!='n-fit04-v1' or packet['executable'] is not True
            or packet['file_caps']!=N_FILE_CAPS or packet['total_cap']!=N_TOTAL_CAP
            or packet['progress_cap']!=N_PROGRESS_CAP or packet['json_rows']!=N_JSON_ROWS
            or any(type(packet[k]) is not str or re.fullmatch('[a-f0-9]{64}',packet[k]) is None for k in
                ('data03_actual','queue_export_actual','source_review','operation_review','root_go'))):
        raise ValueError('N-FIT04 requires exact caps and separately reviewed actual bindings')


def n_json(raw,*,nodes=150000):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('duplicate N JSON key')
            value[key]=item
        return value
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite N JSON')))
    count=[0]
    def bounded(item,depth=0):
        count[0]+=1
        if depth>20 or count[0]>nodes:raise ValueError('N JSON structure cap')
        if isinstance(item,dict):
            if len(item)>128:raise ValueError('N JSON object cap')
            for key,child in item.items():bounded(key,depth+1);bounded(child,depth+1)
        elif isinstance(item,list):
            if len(item)>N_JSON_ROWS:raise ValueError('N JSON row cap')
            for child in item:bounded(child,depth+1)
        elif isinstance(item,str):
            if len(item)>2048:raise ValueError('N JSON string cap')
        elif type(item) in (int,float):
            if not math.isfinite(item):raise ValueError('nonfinite N JSON')
        elif item is not None and type(item) is not bool:raise ValueError('N JSON scalar type')
    bounded(value)
    return value


class NStages:
    """Host epochs stay local; worker durations only shorten admission windows."""
    def __init__(self,origin,deadline,attempt,input_sha256):
        self.origin=origin;self.deadline=deadline;self.attempt=attempt;self.input_sha256=input_sha256
        self.launch=origin;self.rollout=None;self.integration_done=False;self.last=None;self.next_poll=0.
    def active_deadline(self):
        return min(self.deadline,self.origin+5000 if self.rollout is None else
            self.deadline if self.integration_done else self.rollout+1800)
    def check(self):check_deadline(self.active_deadline())
    def admit(self,raw):
        self.check();v=n_json(raw)
        fields={'schema','attempt_id','input_sha256','stage','sequence','elapsed_seconds',
            'rollouts_started_elapsed_seconds','integration_finished_elapsed_seconds','extension','K'}
        if (not isinstance(v,dict) or set(v)!=fields or v['schema']!='n-fit04-progress-v1'
                or v['attempt_id']!=self.attempt or v['input_sha256']!=self.input_sha256
                or v['stage'] not in ('preparing','fitting','diagnostics','rollouts')
                or type(v['sequence']) is not int or not 1<=v['sequence']<=100
                or type(v['extension']) is not bool
                or (v['K'] is not None and (type(v['K']) is not int or v['K'] not in [1024*2**i for i in range(7)]))):
            raise ValueError('invalid N progress identity/schema')
        elapsed=v['elapsed_seconds'];start=v['rollouts_started_elapsed_seconds'];finish=v['integration_finished_elapsed_seconds']
        if (type(elapsed) not in (int,float) or not 0<=elapsed<7200
                or elapsed>time.monotonic()-self.launch
                or any(x is not None and (type(x) not in (int,float) or not 0<=x<=elapsed) for x in (start,finish))
                or (start is None)!=(v['stage']!='rollouts')
                or (finish is not None and (start is None or not start<=finish<start+1800))):
            raise ValueError('invalid N progress durations')
        if self.last is not None:
            old=self.last
            if v==old:return None
            if (v['sequence']<=old['sequence'] or elapsed<old['elapsed_seconds']
                    or (old['extension'] and not v['extension'])
                    or (old['stage']=='rollouts' and v['stage']!='rollouts')
                    or (old['rollouts_started_elapsed_seconds'] is not None and start!=old['rollouts_started_elapsed_seconds'])
                    or (old['integration_finished_elapsed_seconds'] is not None and finish!=old['integration_finished_elapsed_seconds'])):
                raise ValueError('stale or reset N progress')
        if start is not None:
            candidate=self.launch+start
            if candidate>=self.origin+5000:raise TimeoutError('N rollouts entered too late')
            if self.rollout is None:self.rollout=candidate
            # Check before admitting completion: a late marker never waives expiry.
            self.check()
            if finish is not None:self.integration_done=True
        self.last=v;self.check()
        return {key:v[key] for key in ('attempt_id','input_sha256','stage','extension','K') if v[key] is not None}


def n_tar_payload(raw,name,cap):
    import tarfile
    if len(raw)<1536 or len(raw)%512:raise ValueError('partial N file transfer')
    info=tarfile.TarInfo.frombuf(raw[:512],'utf-8','strict')
    end=512+((info.size+511)//512)*512
    if (info.name!=name or info.type not in (tarfile.REGTYPE,tarfile.AREGTYPE)
            or not 0<info.size<=cap or len(raw)<end+1024 or any(raw[512+info.size:])):
        raise ValueError('invalid/overflow N exact-file transfer')
    return raw[512:512+info.size]


def n_file(cid,name,cap,deadline,*,optional=False,receipts=None):
    """Receive one capped tar stream, never extract paths or capture raw stderr."""
    import subprocess
    if name not in (*N_FILE_CAPS,'progress.json') or type(cap) is not int or cap<=0:
        raise ValueError('N exact known file and positive cap required')
    if receipts is not None and len(receipts)>=4000:raise ValueError('N file-client receipt row cap')
    require_cid(cid);check_deadline(deadline)
    process=None;raw=bytearray();record=dict(name=name,pid=None,reaped=False,returncode=None)
    try:
        process=subprocess.Popen(['docker','cp',cid+':/output/'+name,'-'],stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        record['pid']=process.pid;os.set_blocking(process.stdout.fileno(),False)
        command_deadline=min(deadline,time.monotonic()+15)
        while True:
            check_deadline(command_deadline)
            try:chunk=os.read(process.stdout.fileno(),min(65536,cap+16385-len(raw)))
            except BlockingIOError:chunk=None
            if chunk:
                raw.extend(chunk)
                if len(raw)>cap+16384:raise ValueError('N receive byte cap exceeded')
            elif chunk==b'' and process.poll() is not None:break
            else:time.sleep(min(.01,max(0,command_deadline-time.monotonic())))
        code=process.wait(timeout=max(.001,min(2,command_deadline-time.monotonic())))
        record.update(reaped=True,returncode=code);check_deadline(command_deadline)
        if code:
            if optional and not raw:return None
            raise ValueError('N named file unavailable')
        return n_tar_payload(raw,name,cap)
    finally:
        if process is not None:
            if not record['reaped']:
                try:
                    process.kill();record['returncode']=process.wait(timeout=2);record['reaped']=True
                except BaseException:raise StopUnconfirmed('N exact-file client reap unconfirmed') from None
            process.stdout.close()
        if receipts is not None:receipts.append(record)


def n_collect(cid,directory,proof,trusted,stages,receipts):
    from contracts.domain.nof1_app import NInput,NResult,ownership_manifest,validate_result
    values={};total=0
    for name in ('result.json','diagnostics.json','ownership.json'):
        stages.check();raw=n_file(cid,name,N_FILE_CAPS[name],stages.active_deadline(),receipts=receipts);stages.check()
        total+=len(raw);values[name]=n_json(raw)
        (directory/name).write_bytes(raw)
    product=NInput.model_validate_json(canonical(proof['input']))
    result=NResult.model_validate_json(canonical(values['result.json']))
    validate_result(result,product,trusted)
    required=set(N_FILE_CAPS)-{'result.json'} if result.status=='completed' else {'diagnostics.json','ownership.json'}
    refs={a.get('path'):a.get('sha256') for a in result.artifacts}
    if len(refs)!=len(result.artifacts) or set(refs)!=required:raise ValueError('N exact artifact set mismatch')
    if values['diagnostics.json']!=result.diagnostics or values['ownership.json']!=ownership_manifest(product):
        raise ValueError('N scalar artifact ownership/diagnostics mismatch')
    if result.status=='completed' and (stages.rollout is None or not stages.integration_done):
        raise ValueError('N completed result lacks timely integration evidence')
    for name in N_FILE_CAPS:
        if name not in required:continue
        if name not in values:
            stages.check();raw=n_file(cid,name,N_FILE_CAPS[name],stages.active_deadline(),receipts=receipts);stages.check()
            total+=len(raw)
            if total>N_TOTAL_CAP:raise ValueError('N aggregate artifact cap exceeded')
            (directory/name).write_bytes(raw)
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=refs[name]:raise ValueError('N artifact hash mismatch')
    stages.check()
    return ['result.json',*(name for name in N_FILE_CAPS if name in required)]


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def sha(value):return hashlib.sha256(canonical(value)).hexdigest()


def ordinary_path(path):
    path=Path(path).absolute()
    for item in (path,*path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(),'st_file_attributes',0)&0x400):
            raise ValueError('path alias/reparse point denied')
    if any(c in str(path) for c in (',','\n','\r','\x00')):raise ValueError('unsafe path grammar')
    return path


def exclusive(path):
    stream=path.open('a+b')
    if stream.tell()==0:stream.write(b'0');stream.flush()
    stream.seek(0)
    if os.name=='nt':
        import msvcrt
        msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
    else:
        import fcntl
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
    return stream


def worker_limits(borrowing, *, cohort=False):return list(COMMON)


def worker_module(input_value):
    if input_value.get('kind')=='poc_nof1_input':return 'services.learner.nof1_worker'
    return 'services.learner.support_s1_worker' if input_value.get('kind')=='poc_support_s1_input' else 'services.learner.analysis_worker'


def require_dispatchable(input_value):
    if input_value.get('kind')=='poc_nof1_input':
        from contracts.domain.nof1_app import NInput
        NInput.model_validate_json(json.dumps(input_value))
    if input_value.get('kind')=='poc_support_s1_input':
        from contracts.domain.support_s1 import S1Input
        S1Input.model_validate_json(json.dumps(input_value))
    if input_value.get('kind')=='poc_protocol_input':raise ValueError('protocol configuration is not executable in P1')
    if input_value.get('kind')=='poc_visit_cohort_input':
        from contracts.domain.cohort import CohortInput,require_executable
        require_executable(CohortInput.model_validate_json(json.dumps(input_value)))


def cohort_reviewed_runtime(state, actual_image):
    reviewed=state.get('cohort_reviewed_runtime')
    if (not isinstance(reviewed,dict) or set(reviewed)!={'learner_image','source_commit'}
            or re.fullmatch('sha256:[a-f0-9]{64}',str(reviewed.get('learner_image'))) is None
            or re.fullmatch('[a-f0-9]{40}',str(reviewed.get('source_commit'))) is None):
        raise ValueError('Cohort deployment requires exactly one reviewed source/image pair.')
    if reviewed!=dict(learner_image=actual_image,source_commit=state['source_commit']):
        raise ValueError('Cohort actual runtime differs from reviewed deployment pair.')
    return reviewed


def absent(argv, *, deadline):
    if command(argv,deadline=deadline).stdout.strip():raise RuntimeError('owned namespace collision; retain existing resource')


def validate_deployment(state, deployment):
    require_cid(state['service_cid'])
    s1=state.get('operation')=='support-s1-day84-v1'
    nof1=state.get('operation')=='nof1-representative-v1'
    if nof1:n_packet(state)
    namespace=(('remission-nof1-http-261023','remission-nof1-job-261023') if nof1 else
        ('remission-support-s1-http-261023','remission-support-s1-job-261023') if s1 else
        ('remission-cohort-day14-http-261022','remission-cohort-day14-job-261022'))
    if (state['service_container'],state['prefix'])!=namespace:
        raise ValueError('ordinary operation namespace differs from reviewed proposal')
    cohort_reviewed_runtime(state,state['learner_image'])
    expected=state['expected'];selection=expected['selection'];job=selection['job']
    if re.fullmatch('analysis-[a-f0-9]{32}',job) is None:raise ValueError('ordinary persisted attempt ID required')
    proof_path=ordinary_path(deployment.parent/state['queued_export_path'])
    if nof1:
        with proof_path.open('rb') as stream:raw=stream.read(N_INPUT_CAP+1)
        if len(raw)>N_INPUT_CAP:raise ValueError('N queued export byte cap')
        proof=n_json(raw,nodes=1000000)
    else:proof=json.loads(proof_path.read_bytes())
    if (sha(proof)!=expected['export_sha256'] or proof.get('attempt_id')!=job
            or proof.get('owner_id')!=selection['owner'] or proof.get('submission')!=selection['submission']
            or proof.get('receipt',{}).get('key')!=selection['key']
            or proof.get('input',{}).get('kind')!=('poc_nof1_input' if nof1 else 'poc_support_s1_input' if s1 else 'poc_visit_cohort_input')
            or sha(proof['input'])!=proof.get('input_sha256')):
        raise ValueError('frozen actual queued export mismatch')
    require_dispatchable(proof['input'])
    if nof1:
        from contracts.domain.nof1_app import NInput,readiness
        product=NInput.model_validate_json(canonical(proof['input']))
        ready=readiness(product.histories,product.target_id)
        if len(product.cohort)!=12 or ready['review_day']!=72 or ready['status']!='eligible':
            raise ValueError('N-FIT04 requires accepted full12 eligible day72 input')
    if s1 and proof['input']['cutoff_day']!=84:raise ValueError('reviewed S1 operation requires day84')
    return proof


def run_once(state, deployment, deployment_digest):
    proof=validate_deployment(state,deployment)
    nof1=proof['input']['kind']=='poc_nof1_input'
    root=ordinary_path(deployment.parent/'analysis-jobs');root.mkdir(exist_ok=True)
    lock=exclusive(root/'dispatcher.lock');identifier=proof['attempt_id'];directory=root/identifier
    token=None;owned=[];manifest=dict(attempt_id=identifier,status='reserved',deployment_sha256=deployment_digest,
        source_head=state['source_commit'],learner_image=state['learner_image'],failure=None)
    # Reservation precedes all Docker commands and claim, including preflight.
    try:
        if nof1:
            import sys
            if os.name=='nt' and sys.version_info<(3,13):raise ValueError('N private staging requires Python3.13 Windows ACL semantics')
            # Python3.13 Windows 0700 grants current user/administrators only;
            # POSIX grants owner only. All private files inherit this fresh ACL.
            directory.mkdir(mode=0o700,exist_ok=False)
        else:directory.mkdir(exist_ok=False)
    except BaseException:
        lock.close()
        raise
    save(directory/'reservation.json',dict(deployment_sha256=deployment_digest,attempt_id=identifier,
        queued_export_sha256=state['expected']['export_sha256'],reserved_unix=time.time()))
    def persist():
        temporary=directory/'dispatch.tmp';temporary.write_bytes(canonical(manifest)+b'\n');temporary.replace(directory/'dispatch.json')
    lifecycle_seconds=180 if proof['input']['kind']=='poc_support_s1_input' else 7200
    common_origin=time.monotonic()
    deadline=common_origin+lifecycle_seconds;accept_before=datetime.fromtimestamp(time.time()+lifecycle_seconds,timezone.utc).isoformat()
    stages=NStages(common_origin,deadline,identifier,proof['input_sha256']) if nof1 else None
    if nof1:manifest['file_clients']=[]
    manifest.update(deadline_monotonic=deadline,accept_before=accept_before,watchdog_seconds=lifecycle_seconds)
    def call(argv, **kwargs):
        if nof1:stages.check()
        result=command(argv,deadline=stages.active_deadline() if nof1 else deadline,**kwargs)
        if nof1:stages.check()
        return result
    def cli(*values):return json.loads(call(['docker','exec',state['service_cid'],'python','-m','services.foundation.analysis_cli',*values]).stdout)
    def create(argv, role):
        manifest['creating_role']=role;persist()
        try:cid=require_cid(call(argv,cap=30).stdout.decode().strip())
        except BaseException as error:
            raise StopUnconfirmed('Docker create outcome unconfirmed for '+role+'; retain exact namespace: '+repr(error)) from None
        owned.append(cid)
        save(directory/(role+'-cid.json'),dict(cid=cid,argv=argv));return cid
    try:
        persist()
        if (type(state.get('service_deadline_unix')) not in (int,float) or not math.isfinite(state['service_deadline_unix'])
                or state['service_deadline_unix']-time.time()<lifecycle_seconds+300):
            raise RuntimeError('service lifetime cannot cover 7200 seconds plus 300 collection margin')
        if inspect(state['service_cid'],deadline=stages.active_deadline() if nof1 else deadline)['State']['Status']!='running':raise RuntimeError('reviewed service is not running')
        service_identity=json.loads(call(['docker','inspect','--format',
            '{"Name":{{json .Name}},"Image":{{json .Image}}}',state['service_cid']]).stdout)
        if service_identity!=dict(Name='/'+state['service_container'],Image=state['service_image']):
            raise ValueError('service CID/name/qualified image mismatch')
        absent(['docker','ps','-aq','--filter','label=remission.analysis='+state['prefix']],deadline=stages.active_deadline() if nof1 else deadline)
        absent(['docker','ps','-aq','--filter','label=remission.attempt='+identifier],deadline=stages.active_deadline() if nof1 else deadline)
        learner=state['prefix']+'-'+identifier;input_volume=learner+'-input';output_volume=learner+'-output'
        for name in (learner,learner+'-stage'):
            absent(['docker','ps','-aq','--filter','name=^/'+name+'$'],deadline=stages.active_deadline() if nof1 else deadline)
        for name in (input_volume,output_volume):absent(['docker','volume','ls','-q','--filter','name=^'+name+'$'],deadline=stages.active_deadline() if nof1 else deadline)
        actual=call(['docker','image','inspect','--format','{{.Id}}',state['learner_image']]).stdout.decode().strip()
        reviewed=cohort_reviewed_runtime(state,actual)
        if cli('queued-request','--value',canonical(state['expected']['selection']).decode())!=proof:raise RuntimeError('queued selection changed before claim')
        if state['service_deadline_unix']-time.time()<lifecycle_seconds+300:raise RuntimeError('service remaining lifetime insufficient immediately before claim')
        manifest['claim_outcome']='unknown';persist()
        job=cli('claim','--value',canonical(state['expected']).decode())
        if not isinstance(job,dict) or job.get('attempt_id')!=identifier or job.get('input')!=proof['input']:
            raise RuntimeError('claim identity/input mismatch; no worker may start')
        token=job['claim_token']
        if not isinstance(token,str) or re.fullmatch('[a-f0-9]{48}',token) is None:raise ValueError('invalid claim token')
        manifest['claim_outcome']='confirmed_expected_attempt'
        require_dispatchable(job['input'])
        if job['input'].get('sources') is not None:raise ValueError('ordinary slice requires original V0 input')
        (directory/'input.json').write_bytes(canonical(job['input'])+b'\n')
        origin=dict(learner_image=actual,source_commit=state['source_commit'])
        trusted=cli('bind-execution','--job',identifier,'--token',token,'--value',canonical(origin).decode())
        if any(trusted.get(k)!=v for k,v in dict(input_sha256=proof['input_sha256'],**origin).items()):raise RuntimeError('service did not confirm execution binding')
        manifest.update(status='preparing',trusted_launch=trusted,input_sha256=proof['input_sha256']);persist()
        for volume in (input_volume,output_volume):call(['docker','volume','create','--label','remission.task='+state['prefix'],volume])
        helper=create(['docker','create','--name',learner+'-stage','--label','remission.analysis='+state['prefix'],'--label','remission.attempt='+identifier,
            *COMMON,'--cap-add','CHOWN','--user','0:0','--mount',f'type=volume,source={input_volume},target=/input',
            '--mount',f'type=volume,source={output_volume},target=/output',actual,'python','-c',
            "import os;os.chmod('/input',0o755);os.chmod('/input/input.json',0o444);os.chown('/input/input.json',10002,10002);os.chmod('/output',0o700);os.chown('/output',10002,10002)"],'stage')
        call(['docker','cp',str(directory/'input.json'),helper+':/input/input.json'])
        supervise(helper,directory/'stage-supervision',min(stages.active_deadline() if nof1 else deadline,time.monotonic()+60))
        env=[]
        for key,value in dict(REMISSION_LEARNER_IMAGE=actual,REMISSION_SOURCE_COMMIT=state['source_commit'],
                REMISSION_COHORT_REVIEWED_LEARNER_IMAGE=reviewed['learner_image'],REMISSION_COHORT_REVIEWED_SOURCE_COMMIT=reviewed['source_commit'],
                OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1').items():env.extend(['-e',key+'='+value])
        cid=create(['docker','create','--name',learner,'--label','remission.analysis='+state['prefix'],'--label','remission.attempt='+identifier,
            *worker_limits(True,cohort=True),'--user','10002:10002','--mount',f'type=volume,source={input_volume},target=/input,readonly',
            '--mount',f'type=volume,source={output_volume},target=/output',*env,actual,
            'python','-m',worker_module(job['input']),'--input','/input/input.json','--output','/output'],'learner')
        last=[None];next_poll=[0.]
        if nof1:stages.launch=time.monotonic()
        def progress(force=False):
            if nof1:
                stages.check()  # Always before throttle, including a blocked native sampler.
                if not force and time.monotonic()<stages.next_poll:return
                stages.next_poll=time.monotonic()+2
                stages.check()
                raw=n_file(cid,'progress.json',N_PROGRESS_CAP,stages.active_deadline(),optional=True,receipts=manifest['file_clients'])
                stages.check()
                if raw is not None:
                    value=stages.admit(raw)
                    if value is not None:
                        stages.check();cli('progress','--job',identifier,'--token',token,'--value',canonical(value).decode());stages.check()
                return
            if time.monotonic()<next_poll[0]:return
            next_poll[0]=time.monotonic()+2
            copied=call(['docker','cp',cid+':/output/progress.json',str(directory/'progress.json')],check=False)
            if copied.returncode==0:
                value=json.loads((directory/'progress.json').read_bytes());encoded=canonical(value).decode()
                if encoded!=last[0] and value['stage'] in ('preparing','fitting','diagnostics','rollouts'):
                    cli('progress','--job',identifier,'--token',token,'--value',encoded);last[0]=encoded
        manifest.update(status='running',container_cid=cid);persist()
        terminal=supervise(cid,directory/'learner-supervision',min(deadline,time.monotonic()+60) if lifecycle_seconds==180 else deadline,progress)
        if nof1:
            # supervise can return between callbacks; expiry still vetoes terminal success.
            stages.check();progress(force=True);stages.check()
            (directory/'output').mkdir(mode=0o700,exist_ok=False)
            names=n_collect(cid,directory/'output',proof,trusted,stages,manifest['file_clients'])
        else:
            logs=call(['docker','logs',cid],check=False)
            (directory/'worker.stdout').write_bytes(logs.stdout);(directory/'worker.stderr').write_bytes(logs.stderr)
            call(['docker','cp',cid+':/output/.',str(directory/'output')],cap=60)
            (directory/'output'/'worker.stdout').write_bytes(logs.stdout);(directory/'output'/'worker.stderr').write_bytes(logs.stderr)
        dest='/exports/analyses/'+identifier
        call(['docker','exec',state['service_cid'],'mkdir','-p','/exports/analyses'])
        if nof1:
            call(['docker','exec',state['service_cid'],'mkdir','-m','700',dest])
            for name in names:
                call(['docker','cp',str(directory/'output'/name),state['service_cid']+':'+dest+'/'+name],cap=15)
        else:
            call(['docker','exec',state['service_cid'],'mkdir',dest])
            call(['docker','cp',str(directory/'output')+'/.',state['service_cid']+':'+dest],cap=60)
        response=cli('ingest','--job',identifier,'--token',token,'--directory',dest,'--accept-before',accept_before)
        if nof1:stages.check()
        check_deadline(deadline)
        if response.get('id')!=identifier or response.get('status') not in ('completed','failed','abstained'):raise RuntimeError('unconfirmed ingest response')
        manifest.update(status=response['status'],terminal=terminal,accepted_response=response)
    except BaseException as error:
        failures=[];unconfirmed=isinstance(error,StopUnconfirmed)
        for cid in reversed(owned):
            try:
                stopped=stop_owned(cid)
                failures.append(dict(cid=cid,stopped=True) if nof1 else dict(cid=cid,cleanup=stopped))
            except BaseException as stopped_error:
                unconfirmed=True;failures.append(dict(cid=cid,stopped=False) if nof1 else dict(cid=cid,error=repr(stopped_error)))
        message=('n-fit04-stop-unconfirmed' if unconfirmed else 'n-fit04-failed') if nof1 else (
            repr(error).replace(token,'[claim-token-redacted]') if token else repr(error))
        manifest.update(status='STOP UNCONFIRMED' if unconfirmed else 'failed',failure=message,cleanup=failures)
        if not nof1 and not unconfirmed and manifest.get('container_cid'):
            # Evidence collection is cleanup only, with independent short caps;
            # it cannot extend the scientific/acceptance deadline.
            try:
                logs=command(['docker','logs',manifest['container_cid']],check=False,cap=10)
                (directory/'failure-worker.stdout').write_bytes(logs.stdout)
                (directory/'failure-worker.stderr').write_bytes(logs.stderr)
                copied=command(['docker','cp',manifest['container_cid']+':/output/.',str(directory/'failure-output')],check=False,cap=30)
                manifest['failure_output_copy_returncode']=copied.returncode
            except BaseException as capture_error:
                manifest['failure_capture_error']=repr(capture_error).replace(token,'[claim-token-redacted]') if token else repr(capture_error)
        if token and not unconfirmed:
            try:command(['docker','exec',state['service_cid'],'python','-m','services.foundation.analysis_cli',
                'fail','--job',identifier,'--token',token,'--value',message],cap=10)
            except BaseException as failed:manifest['failure_publication_error']='n-fit04-fail-publication-unconfirmed' if nof1 else repr(failed).replace(token,'[claim-token-redacted]')
        if unconfirmed:raise StopUnconfirmed(message) from None
        raise RuntimeError(message) from None
    finally:
        manifest.update(finished_unix=time.time(),claim_through_completion_seconds=lifecycle_seconds-(deadline-time.monotonic()),retained_cids=owned)
        persist();lock.close()
    return manifest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--deployment',type=Path,required=True)
    parser.add_argument('--once',action='store_true');parser.add_argument('--authorized-deployment-sha256',required=True);args=parser.parse_args()
    if not args.once:parser.error('reviewed ordinary dispatcher requires --once')
    path=ordinary_path(args.deployment);raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if digest!=args.authorized_deployment_sha256:raise ValueError('exact reviewed deployment bytes required')
    result=run_once(json.loads(raw),path,digest)
    print(json.dumps(dict(attempt_id=result['attempt_id'],status=result['status'])),flush=True)


if __name__=='__main__':main()
