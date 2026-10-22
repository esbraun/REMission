"""Terminal-after-deadline control through the real host dispatcher function."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
import unittest
from unittest.mock import Mock,patch
import analysis_dispatcher


class DispatcherDeadlineTests(unittest.TestCase):
    def test_cohort_v0_v1_use_native_binding_digest_scratch_and_policy(self):
        for configuration in ('poc-visit-cohort-v1','poc-visit-cohort-borrow-v1'):
            for mismatch in (None,'binding','actual-image','deadline'):
                with self.subTest(configuration=configuration,mismatch=mismatch),tempfile.TemporaryDirectory() as directory:
                    root=Path(directory);deployment=root/'deployment.json';calls=[];clock=[0.]
                    deployment.write_text(json.dumps(dict(service_container='test-service',learner_image='mutable-tag',prefix='test',source_commit='a'*40,
                        cohort_reviewed_runtime=dict(learner_image='sha256:'+'a'*64,source_commit='a'*40))))
                    job=dict(attempt_id='analysis-cohort',claim_token='PRIVATE-CLAIM',input=dict(kind='poc_visit_cohort_input',request=dict(configuration=dict(id=configuration))))
                    digest='sha256:'+'a'*64
                    def command(argv,check=True):
                        calls.append(argv);response=b''
                        if argv[:6]==['docker','exec','test-service','python','-m','services.foundation.analysis_cli']:
                            op=argv[6]
                            if op=='claim':response=json.dumps(job).encode()
                            elif op=='interrupt':response=b'{}'
                            elif op=='bind-execution':
                                response=json.dumps(dict(learner_image=digest,source_commit='a'*40,input_sha256='wrong' if mismatch=='binding' else __import__('hashlib').sha256(json.dumps(job['input'],sort_keys=True,separators=(',',':')).encode()).hexdigest())).encode()
                            elif op=='ingest':response=b'{"status":"completed"}'
                            else:response=b'{}'
                        elif argv[:3]==['docker','image','inspect']:response=digest.encode()
                        elif argv[:2]==['docker','inspect']:
                            if mismatch=='deadline':clock[0]=7201.
                            response=json.dumps(dict(Image='wrong' if mismatch=='actual-image' else digest,State=dict(Running=False,ExitCode=0,OOMKilled=False))).encode()
                        elif argv[:2]==['docker','cp'] and Path(argv[-1]).name=='output':Path(argv[-1]).mkdir()
                        return subprocess.CompletedProcess(argv,0,response,b'')
                    # Explicit orchestration double only: production admission remains closed.
                    with patch.object(sys,'argv',['analysis_dispatcher','--deployment',str(deployment),'--once']),patch.object(analysis_dispatcher,'exclusive',return_value=Mock()),patch.object(analysis_dispatcher,'require_dispatchable'),patch.object(analysis_dispatcher,'command',side_effect=command),patch.object(analysis_dispatcher.time,'monotonic',side_effect=lambda:clock[0]):
                        analysis_dispatcher.main()
                    result=json.loads((root/'analysis-jobs/analysis-cohort/dispatch.json').read_bytes())
                    self.assertEqual(result['execution_policy'],'poc-cohort-native-cvm-v1')
                    self.assertEqual(result['status'],'failed' if mismatch else 'completed')
                    launches=[a for a in calls if a[:2]==['docker','run']]
                    if mismatch=='binding':self.assertEqual(launches,[])
                    else:
                        self.assertIn('/tmp:rw,exec,nosuid,nodev,size=512m',launches[0])
                        self.assertIn(digest,launches[0]);self.assertNotIn('PRIVATE-CLAIM',launches[0])
                        self.assertIn('REMISSION_COHORT_REVIEWED_LEARNER_IMAGE='+digest,launches[0])
                        self.assertIn('REMISSION_COHORT_REVIEWED_SOURCE_COMMIT='+'a'*40,launches[0])
                        self.assertEqual(launches[0][launches[0].index('--memory-swap')+1],'2g')
                        self.assertEqual(launches[0][launches[0].index('--pids-limit')+1],'64')
                        for env in ('OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','MKL_NUM_THREADS=1','NUMEXPR_NUM_THREADS=1'):
                            self.assertIn(env,launches[0])
                    if mismatch:self.assertFalse(any('ingest' in a for a in calls))

    def test_cohort_deployment_misconfiguration_is_recorded_before_launch(self):
        digest='sha256:'+'a'*64;source='a'*40
        for config in (None,{},dict(learner_image=digest),dict(learner_image=digest,source_commit=source,extra=True),
                dict(learner_image='sha256:'+'b'*64,source_commit=source),
                dict(learner_image=digest,source_commit='b'*40)):
            with self.subTest(config=config),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);deployment=root/'deployment.json';calls=[]
                deployment.write_text(json.dumps(dict(service_container='test-service',learner_image='tag',prefix='test',
                    source_commit=source,cohort_reviewed_runtime=config)))
                job=dict(attempt_id='analysis-config',claim_token='PRIVATE-CLAIM',input=dict(kind='poc_visit_cohort_input'))
                def command(argv,check=True):
                    calls.append(argv);response=b''
                    if argv[:6]==['docker','exec','test-service','python','-m','services.foundation.analysis_cli']:
                        response=json.dumps(job).encode() if argv[6]=='claim' else b'{}'
                    elif argv[:3]==['docker','image','inspect']:response=digest.encode()
                    return subprocess.CompletedProcess(argv,0,response,b'')
                with patch.object(sys,'argv',['analysis_dispatcher','--deployment',str(deployment),'--once']), \
                        patch.object(analysis_dispatcher,'exclusive',return_value=Mock()), \
                        patch.object(analysis_dispatcher,'require_dispatchable'), \
                        patch.object(analysis_dispatcher,'command',side_effect=command):analysis_dispatcher.main()
                result=json.loads((root/'analysis-jobs/analysis-config/dispatch.json').read_bytes())
                self.assertEqual(result['status'],'failed')
                self.assertFalse(any(a[:2]==['docker','run'] or 'bind-execution' in a for a in calls))
                self.assertTrue(any('fail' in a for a in calls))
                # Host never supplies configuration overrides to the service.
                self.assertTrue(all(a[2]=='test-service' for a in calls if a[:2]==['docker','exec']))

    def test_host_cohort_and_protocol_admission_remain_closed_legacy_v0_unchanged(self):
        from tests.contracts.test_cohort import database,export
        from contracts.domain.cohort import make_cohort_input
        db=database()
        try:product=make_cohort_input(export(db),'host-closed-control')
        finally:db.close()
        with self.assertRaisesRegex(ValueError,'qualification'):
            analysis_dispatcher.require_dispatchable(product.model_dump(mode='json'))
        with self.assertRaisesRegex(ValueError,'protocol'):
            analysis_dispatcher.require_dispatchable(dict(kind='poc_protocol_input'))
        self.assertIsNone(analysis_dispatcher.require_dispatchable(dict(kind='poc_visit_input')))

    def test_slow_claim_consumes_native_deadline_before_launch(self):
        calls=[];clock=[0.]
        job=dict(attempt_id='analysis-slow-claim',claim_token='PRIVATE',input=dict(kind='poc_visit_borrow_input'))
        def command(argv,check=True):
            calls.append(argv);response=b''
            if argv[:6]==['docker','exec','test-service','python','-m','services.foundation.analysis_cli']:
                if argv[6]=='claim':clock[0]=7201.;response=json.dumps(job).encode()
                else:response=b'{}'
            return subprocess.CompletedProcess(argv,0,response,b'')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);deployment=root/'deployment.json'
            deployment.write_text(json.dumps(dict(service_container='test-service',learner_image='image',prefix='test',source_commit='a'*40)))
            with patch.object(sys,'argv',['analysis_dispatcher','--deployment',str(deployment),'--once']),patch.object(analysis_dispatcher,'exclusive',return_value=Mock()),patch.object(analysis_dispatcher,'command',side_effect=command),patch.object(analysis_dispatcher.time,'monotonic',side_effect=lambda:clock[0]):analysis_dispatcher.main()
            result=json.loads((root/'analysis-jobs/analysis-slow-claim/dispatch.json').read_bytes())
            self.assertEqual(result['status'],'failed');self.assertIn('deadline',result['failure'])
            self.assertFalse(any(a[:2]==['docker','run'] for a in calls))

    def test_terminal_completion_after_cap_is_failed_without_ingestion(self):
        calls=[];clock=[0.]
        job=dict(attempt_id='analysis-late-terminal',claim_token='token',input=dict(kind='poc_visit_borrow_input'))
        def command(argv,check=True):
            calls.append(argv)
            response=b''
            if argv[:3]==['docker','exec','test-service']:
                operation=argv[6]
                if operation=='claim':response=json.dumps(job).encode()
                elif operation=='bind-execution':response=json.dumps(dict(learner_image='sha256:'+'a'*64,source_commit='test-head',input_sha256=__import__('hashlib').sha256(json.dumps(job['input'],sort_keys=True,separators=(',',':')).encode()).hexdigest())).encode()
                elif operation=='interrupt':response=b'{"interrupted":0}'
                elif operation=='ingest':self.fail('Late worker must never reach ingestion')
                else:response=b'{}'
            elif argv[:2]==['docker','inspect']:
                # The worker finished AFTER the frozen cap between polls.
                clock[0]=7201.
                self.assertEqual(argv[3:],['--format',analysis_dispatcher.CONTAINER_FORMAT])
                response=json.dumps(dict(Image='sha256:'+'a'*64,State=dict(Running=False,ExitCode=0,OOMKilled=False))).encode()
            elif argv[:3]==['docker','image','inspect']:
                response=('sha256:'+'a'*64).encode()
            return subprocess.CompletedProcess(argv,0,response,b'')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);deployment=root/'deployment.json'
            deployment.write_text(json.dumps(dict(service_container='test-service',learner_image='test-image',prefix='test-private',source_commit='test-head')))
            lock=Mock()
            with patch.object(sys,'argv',['analysis_dispatcher','--deployment',str(deployment),'--once']), \
                    patch.object(analysis_dispatcher,'exclusive',return_value=lock),patch.object(analysis_dispatcher,'command',side_effect=command), \
                    patch.object(analysis_dispatcher.time,'monotonic',side_effect=lambda:clock[0]):
                analysis_dispatcher.main()
            result=json.loads((root/'analysis-jobs/analysis-late-terminal/dispatch.json').read_text())
            self.assertEqual(result['status'],'failed')
            self.assertIn('deadline',result['failure'])
            self.assertTrue(any(argv[:2]==['docker','stop'] for argv in calls))
            self.assertTrue(any('fail' in argv for argv in calls))
            self.assertFalse(any('ingest' in argv for argv in calls))

    def test_formatted_inspection_is_selected_before_capture(self):
        result=subprocess.CompletedProcess([],0,b'{"Image":"expected"}',b'')
        with patch.object(analysis_dispatcher.subprocess,'run',return_value=result) as invoke:
            self.assertIs(analysis_dispatcher.inspect_container('owned-worker'),result)
        argv=invoke.call_args.args[0]
        self.assertEqual(argv[:4],['docker','inspect','owned-worker','--format'])
        self.assertNotIn('Env',argv[4])
        for required in ['Image','State','Memory','NanoCpus','NetworkMode','ReadonlyRootfs','Tmpfs','Mounts','remission.attempt','remission.analysis','Args']:
            self.assertIn(required,argv[4])

    def test_before_deadline_ingests_and_pre_ingest_deadline_vetoes(self):
        # Real dispatcher branch flow, no Docker/model/service/SQLite side effect.
        for expired,fail_ingest in [(False,False),(True,False),(False,True)]:
            with self.subTest(expired_before_ingest=expired,fail_ingest=fail_ingest),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);deployment=root/'deployment.json';calls=[];clock=[0.]
                deployment.write_text(json.dumps(dict(service_container='test-service',learner_image='test-image',prefix='test-private',source_commit='test-head')))
                job=dict(attempt_id='analysis-positive',claim_token='NEVER-PERSIST-CLAIM',input=dict(kind='poc_visit_borrow_input'))
                def command(argv,check=True):
                    calls.append(argv);response=b''
                    if argv[:6]==['docker','exec','test-service','python','-m','services.foundation.analysis_cli']:
                        operation=argv[6]
                        if operation=='claim':response=json.dumps(job).encode()
                        elif operation=='interrupt':response=b'{"interrupted":0}'
                        elif operation=='bind-execution':response=json.dumps(dict(learner_image='sha256:'+'a'*64,source_commit='test-head',input_sha256=__import__('hashlib').sha256(json.dumps(job['input'],sort_keys=True,separators=(',',':')).encode()).hexdigest())).encode()
                        elif operation=='ingest':
                            if fail_ingest:raise RuntimeError('injected '+job['claim_token'])
                            response=b'{"status":"completed"}'
                        else:response=b'{}'
                    elif argv[:2]==['docker','inspect']:
                        self.assertEqual(argv[3:],['--format',analysis_dispatcher.CONTAINER_FORMAT])
                        response=json.dumps(dict(Image='sha256:'+'a'*64,State=dict(Running=False,ExitCode=0,OOMKilled=False))).encode()
                    elif argv[:3]==['docker','image','inspect']:response=('sha256:'+'a'*64).encode()
                    elif argv[:2]==['docker','cp'] and Path(argv[-1]).name=='output':
                        Path(argv[-1]).mkdir()
                    elif argv[:2]==['docker','cp'] and 'test-service:/exports/' in argv[-1] and expired:
                        clock[0]=7201.
                    return subprocess.CompletedProcess(argv,0,response,b'')
                with patch.object(sys,'argv',['analysis_dispatcher','--deployment',str(deployment),'--once']),patch.object(analysis_dispatcher,'exclusive',return_value=Mock()),patch.object(analysis_dispatcher,'command',side_effect=command),patch.object(analysis_dispatcher.time,'monotonic',side_effect=lambda:clock[0]):
                    analysis_dispatcher.main()
                manifest=(root/'analysis-jobs/analysis-positive/dispatch.json').read_text()
                result=json.loads(manifest)
                self.assertNotIn(job['claim_token'],manifest)
                self.assertEqual(result['status'],'failed' if expired or fail_ingest else 'completed')
                self.assertEqual(any('ingest' in argv for argv in calls),not expired)
                if expired:
                    self.assertTrue(result['worker_stop_verified'])
                    self.assertIn('deadline',result['failure'])
                if fail_ingest:self.assertIn('[claim-token-redacted]',result['failure'])
                for argv in calls:
                    if argv[:2]==['docker','run']:self.assertNotIn(job['claim_token'],argv)

    def test_exec_scratch_is_borrow_only_and_keeps_other_limits(self):
        ordinary=analysis_dispatcher.worker_limits(False)
        borrowed=analysis_dispatcher.worker_limits(True)
        self.assertEqual(ordinary,analysis_dispatcher.COMMON)
        index=ordinary.index('--tmpfs')+1
        self.assertEqual(borrowed[:index],ordinary[:index])
        self.assertEqual(borrowed[index+1:],ordinary[index+1:])
        self.assertEqual(ordinary[index],'/tmp:rw,nosuid,size=256m')
        self.assertEqual(borrowed[index],'/tmp:rw,exec,nosuid,nodev,size=512m')

    def test_unconfirmed_stop_traceback_cannot_reveal_claim_token(self):
        token='SYNTHETIC-PRIVATE-CLAIM-DO-NOT-PERSIST';calls=[];inspections=[0]
        job=dict(attempt_id='analysis-stop-control',claim_token=token,input=dict(kind='poc_visit_borrow_input'))
        def command(argv,check=True):
            calls.append(argv);response=b''
            if argv[:6]==['docker','exec','test-service','python','-m','services.foundation.analysis_cli']:
                if argv[6]=='claim':response=json.dumps(job).encode()
                elif argv[6]=='interrupt':response=b'{"interrupted":0}'
                elif argv[6]=='bind-execution':response=json.dumps(dict(learner_image='sha256:'+'a'*64,source_commit='test-head',input_sha256=__import__('hashlib').sha256(json.dumps(job['input'],sort_keys=True,separators=(',',':')).encode()).hexdigest())).encode()
                else:self.fail('Unconfirmed running computation must not reach fail/ingest')
            elif argv[:3]==['docker','image','inspect']:response=('sha256:'+'a'*64).encode()
            elif argv[:2]==['docker','inspect']:
                self.assertEqual(argv[3:],['--format',analysis_dispatcher.CONTAINER_FORMAT])
                inspections[0]+=1
                if inspections[0]==1:raise RuntimeError('injected origin '+token)
                response=json.dumps(dict(Image='sha256:'+'a'*64,State=dict(Running=True,ExitCode=0,OOMKilled=False))).encode()
            return subprocess.CompletedProcess(argv,0,response,b'')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);deployment=root/'deployment.json'
            deployment.write_text(json.dumps(dict(service_container='test-service',learner_image='test-image',prefix='test-private',source_commit='test-head')))
            with patch.object(sys,'argv',['analysis_dispatcher','--deployment',str(deployment),'--once']),patch.object(analysis_dispatcher,'exclusive',return_value=Mock()),patch.object(analysis_dispatcher,'command',side_effect=command):
                with self.assertRaisesRegex(RuntimeError,'Owned worker termination unconfirmed') as raised:
                    analysis_dispatcher.main()
            rendered=''.join(traceback.format_exception(raised.exception))
            self.assertNotIn(token,rendered)
            self.assertIn('retain live handle',rendered)
            manifest=(root/'analysis-jobs/analysis-stop-control/dispatch.json').read_text()
            self.assertNotIn(token,manifest)
            self.assertEqual(json.loads(manifest)['status'],'worker-stop-unconfirmed')
            self.assertEqual(inspections[0],3)
            self.assertTrue(any(argv[:2]==['docker','stop'] for argv in calls))
            self.assertTrue(any(argv[:2]==['docker','kill'] for argv in calls))


if __name__=='__main__':unittest.main()
