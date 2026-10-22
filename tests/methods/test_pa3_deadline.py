"""Reject numerical acceptance after a deadline and preserve timeout evidence."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from qualify_pa3_bridge import diagnosis, freeze, run
from capture import run as capture_run


class DeadlineTests(unittest.TestCase):
    def test_external_command_timeout_retains_streams(self):
        with tempfile.TemporaryDirectory() as directory,patch('capture.subprocess.check_output',side_effect=[b'',b'fixture-head\n']):
            result,metadata=capture_run([sys.executable,'-c',"import time;print('before-timeout',flush=True);time.sleep(10)"],Path(directory),timeout_seconds=.2)
            self.assertEqual(result.returncode,124)
            self.assertTrue(metadata['timed_out'])
            self.assertIn(b'before-timeout',result.stdout)

    def test_resolution_failure_cannot_be_called_moment_bias(self):
        self.assertEqual(diagnosis(False,True,False),'quadrature-resolution-unmet')
        self.assertEqual(diagnosis(False,True,True),'moment-approximation-failure')
        self.assertEqual(diagnosis(False,False,True),'reference-precision-unmet')

    def test_last_batch_crossing_cap_withholds_acceptance(self):
        manifest=freeze([dict(se=.5),dict(se=.5)])
        manifest['seconds_cap']=1
        elapsed=[0.]
        calls=[0]
        def reference(theta,count,rng):
            calls[0]+=1
            # Cross the deadline during the last of eight otherwise exact
            # batches: a pre-look-only deadline check would falsely pass.
            if calls[0]==8:elapsed[0]=2.
            return np.zeros(count)
        with tempfile.TemporaryDirectory() as directory, patch('qualify_pa3_bridge.time.monotonic',side_effect=lambda:elapsed[0]), \
                patch('qualify_pa3_bridge.forward',side_effect=reference),patch('qualify_pa3_bridge.marginal',return_value=0.),contextlib.redirect_stdout(io.StringIO()):
            out=Path(directory)/'out';result=run(manifest,out,16)
            self.assertEqual(result['status'],'not-qualified')
            self.assertTrue(result['timed_out'])
            point=json.loads((out/'points.json').read_text())[0]
            self.assertFalse(point['accepted'])
            self.assertEqual(point['diagnosis'],'qualification-timeout')
            self.assertEqual(point['looks'][-1]['completed_batches'],8)


if __name__=='__main__':unittest.main()
