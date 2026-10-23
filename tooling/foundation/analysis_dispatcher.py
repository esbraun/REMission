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
    return 'services.learner.support_s1_worker' if input_value.get('kind')=='poc_support_s1_input' else 'services.learner.analysis_worker'


def require_dispatchable(input_value):
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
    namespace=('remission-support-s1-http-261023','remission-support-s1-job-261023') if s1 else ('remission-cohort-day14-http-261022','remission-cohort-day14-job-261022')
    if (state['service_container'],state['prefix'])!=namespace:
        raise ValueError('ordinary operation namespace differs from reviewed proposal')
    cohort_reviewed_runtime(state,state['learner_image'])
    expected=state['expected'];selection=expected['selection'];job=selection['job']
    if re.fullmatch('analysis-[a-f0-9]{32}',job) is None:raise ValueError('ordinary persisted attempt ID required')
    proof=json.loads(ordinary_path(deployment.parent/state['queued_export_path']).read_bytes())
    if (sha(proof)!=expected['export_sha256'] or proof.get('attempt_id')!=job
            or proof.get('owner_id')!=selection['owner'] or proof.get('submission')!=selection['submission']
            or proof.get('receipt',{}).get('key')!=selection['key']
            or proof.get('input',{}).get('kind')!=('poc_support_s1_input' if s1 else 'poc_visit_cohort_input')
            or sha(proof['input'])!=proof.get('input_sha256')):
        raise ValueError('frozen actual queued export mismatch')
    require_dispatchable(proof['input'])
    if s1 and proof['input']['cutoff_day']!=84:raise ValueError('reviewed S1 operation requires day84')
    return proof


def run_once(state, deployment, deployment_digest):
    proof=validate_deployment(state,deployment)
    root=ordinary_path(deployment.parent/'analysis-jobs');root.mkdir(exist_ok=True)
    lock=exclusive(root/'dispatcher.lock');identifier=proof['attempt_id'];directory=root/identifier
    token=None;owned=[];manifest=dict(attempt_id=identifier,status='reserved',deployment_sha256=deployment_digest,
        source_head=state['source_commit'],learner_image=state['learner_image'],failure=None)
    # Reservation precedes all Docker commands and claim, including preflight.
    try:directory.mkdir(exist_ok=False)
    except BaseException:
        lock.close()
        raise
    save(directory/'reservation.json',dict(deployment_sha256=deployment_digest,attempt_id=identifier,
        queued_export_sha256=state['expected']['export_sha256'],reserved_unix=time.time()))
    def persist():
        temporary=directory/'dispatch.tmp';temporary.write_bytes(canonical(manifest)+b'\n');temporary.replace(directory/'dispatch.json')
    lifecycle_seconds=180 if proof['input']['kind']=='poc_support_s1_input' else 7200
    deadline=time.monotonic()+lifecycle_seconds;accept_before=datetime.fromtimestamp(time.time()+lifecycle_seconds,timezone.utc).isoformat()
    manifest.update(deadline_monotonic=deadline,accept_before=accept_before,watchdog_seconds=lifecycle_seconds)
    def call(argv, **kwargs):return command(argv,deadline=deadline,**kwargs)
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
        if inspect(state['service_cid'],deadline=deadline)['State']['Status']!='running':raise RuntimeError('reviewed service is not running')
        service_identity=json.loads(call(['docker','inspect','--format',
            '{"Name":{{json .Name}},"Image":{{json .Image}}}',state['service_cid']]).stdout)
        if service_identity!=dict(Name='/'+state['service_container'],Image=state['service_image']):
            raise ValueError('service CID/name/qualified image mismatch')
        absent(['docker','ps','-aq','--filter','label=remission.analysis='+state['prefix']],deadline=deadline)
        absent(['docker','ps','-aq','--filter','label=remission.attempt='+identifier],deadline=deadline)
        learner=state['prefix']+'-'+identifier;input_volume=learner+'-input';output_volume=learner+'-output'
        for name in (learner,learner+'-stage'):
            absent(['docker','ps','-aq','--filter','name=^/'+name+'$'],deadline=deadline)
        for name in (input_volume,output_volume):absent(['docker','volume','ls','-q','--filter','name=^'+name+'$'],deadline=deadline)
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
        supervise(helper,directory/'stage-supervision',min(deadline,time.monotonic()+60))
        env=[]
        for key,value in dict(REMISSION_LEARNER_IMAGE=actual,REMISSION_SOURCE_COMMIT=state['source_commit'],
                REMISSION_COHORT_REVIEWED_LEARNER_IMAGE=reviewed['learner_image'],REMISSION_COHORT_REVIEWED_SOURCE_COMMIT=reviewed['source_commit'],
                OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1').items():env.extend(['-e',key+'='+value])
        cid=create(['docker','create','--name',learner,'--label','remission.analysis='+state['prefix'],'--label','remission.attempt='+identifier,
            *worker_limits(True,cohort=True),'--user','10002:10002','--mount',f'type=volume,source={input_volume},target=/input,readonly',
            '--mount',f'type=volume,source={output_volume},target=/output',*env,actual,
            'python','-m',worker_module(job['input']),'--input','/input/input.json','--output','/output'],'learner')
        last=[None];next_poll=[0.]
        def progress():
            if time.monotonic()<next_poll[0]:return
            next_poll[0]=time.monotonic()+2
            copied=call(['docker','cp',cid+':/output/progress.json',str(directory/'progress.json')],check=False)
            if copied.returncode==0:
                value=json.loads((directory/'progress.json').read_bytes());encoded=canonical(value).decode()
                if encoded!=last[0] and value['stage'] in ('preparing','fitting','diagnostics','rollouts'):
                    cli('progress','--job',identifier,'--token',token,'--value',encoded);last[0]=encoded
        manifest.update(status='running',container_cid=cid);persist()
        terminal=supervise(cid,directory/'learner-supervision',min(deadline,time.monotonic()+60) if lifecycle_seconds==180 else deadline,progress)
        logs=call(['docker','logs',cid],check=False)
        (directory/'worker.stdout').write_bytes(logs.stdout);(directory/'worker.stderr').write_bytes(logs.stderr)
        call(['docker','cp',cid+':/output/.',str(directory/'output')],cap=60)
        (directory/'output'/'worker.stdout').write_bytes(logs.stdout);(directory/'output'/'worker.stderr').write_bytes(logs.stderr)
        dest='/exports/analyses/'+identifier
        call(['docker','exec',state['service_cid'],'mkdir','-p','/exports/analyses'])
        call(['docker','exec',state['service_cid'],'mkdir',dest])
        call(['docker','cp',str(directory/'output')+'/.',state['service_cid']+':'+dest],cap=60)
        response=cli('ingest','--job',identifier,'--token',token,'--directory',dest,'--accept-before',accept_before)
        check_deadline(deadline)
        if response.get('id')!=identifier or response.get('status') not in ('completed','failed','abstained'):raise RuntimeError('unconfirmed ingest response')
        manifest.update(status=response['status'],terminal=terminal,accepted_response=response)
    except BaseException as error:
        failures=[];unconfirmed=isinstance(error,StopUnconfirmed)
        for cid in reversed(owned):
            try:failures.append(dict(cid=cid,cleanup=stop_owned(cid)))
            except BaseException as stopped_error:unconfirmed=True;failures.append(dict(cid=cid,error=repr(stopped_error)))
        message=repr(error).replace(token,'[claim-token-redacted]') if token else repr(error)
        manifest.update(status='STOP UNCONFIRMED' if unconfirmed else 'failed',failure=message,cleanup=failures)
        if not unconfirmed and manifest.get('container_cid'):
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
            except BaseException as failed:manifest['failure_publication_error']=repr(failed).replace(token,'[claim-token-redacted]')
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
