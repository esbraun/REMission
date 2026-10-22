"""Terminal-after-deadline control through the real host dispatcher function."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
import analysis_dispatcher


class DispatcherDeadlineTests(unittest.TestCase):
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


if __name__=='__main__':unittest.main()
