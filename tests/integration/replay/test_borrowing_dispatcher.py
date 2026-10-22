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
                response=b'[{"State":{"Running":false,"ExitCode":0,"OOMKilled":false}}]'
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


if __name__=='__main__':unittest.main()
