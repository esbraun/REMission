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
                elif operation=='interrupt':response=b'{"interrupted":0}'
                elif operation=='ingest':self.fail('Late worker must never reach ingestion')
                else:response=b'{}'
            elif argv[:2]==['docker','inspect']:
                # The worker finished AFTER the frozen cap between polls.
                clock[0]=7201.
                response=json.dumps([dict(Image='sha256:'+'a'*64,State=dict(Running=False,ExitCode=0,OOMKilled=False))]).encode()
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
