"""Retained host admission/sandbox controls after freezing the ordinary interface.

Lifecycle flow controls now live in test_ordinary_dispatcher, which exercises
the literal-CID create/prearm/start path. The old permissive daemon interface
is deliberately rejected before Docker or claim.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import analysis_dispatcher as dispatcher
import analysis_lifecycle as lifecycle


class DispatcherAdmissionControls(unittest.TestCase):
    def test_host_typed_cohort_protocol_admission_and_legacy_parser(self):
        from tests.contracts.test_cohort import database,export
        from contracts.domain.cohort import make_cohort_input
        db=database()
        try:product=make_cohort_input(export(db),'host-closed-control')
        finally:db.close()
        with self.assertRaisesRegex(ValueError,'qualification'):dispatcher.require_dispatchable(product.model_dump(mode='json'))
        with self.assertRaisesRegex(ValueError,'protocol'):dispatcher.require_dispatchable(dict(kind='poc_protocol_input'))
        self.assertIsNone(dispatcher.require_dispatchable(dict(kind='poc_visit_input')))

    def test_original_cohort_sandbox_and_thread_bounds(self):
        limits=dispatcher.worker_limits(True,cohort=True)
        for flag,value in [('--network','none'),('--cpus','2'),('--memory','2g'),('--memory-swap','2g'),
                ('--pids-limit','64'),('--cap-drop','ALL'),('--security-opt','no-new-privileges'),
                ('--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m'),('--restart','no')]:
            self.assertEqual(limits[limits.index(flag)+1],value)
        self.assertIn('--read-only',limits)

    def test_only_selected_container_state_is_captured(self):
        from test_ordinary_dispatcher import inventory,CID
        import json
        result=subprocess.CompletedProcess([],0,json.dumps(inventory()).encode(),b'')
        with patch.object(lifecycle,'command',return_value=result) as invoke:lifecycle.inspect(CID)
        argv=invoke.call_args.args[0]
        self.assertEqual(argv,['docker','inspect','--format',lifecycle.STATE_FORMAT,CID])
        self.assertNotIn('Config',argv[3]);self.assertNotIn('Env',argv[3])

    def test_old_unbound_invocation_cannot_claim_or_create(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(dispatcher,'command') as command:
            path=Path(temp)/'deployment.json';path.write_text('{}')
            with patch.object(sys,'argv',['dispatcher','--deployment',str(path),'--once']),self.assertRaises(SystemExit):dispatcher.main()
            command.assert_not_called()


if __name__=='__main__':unittest.main()
