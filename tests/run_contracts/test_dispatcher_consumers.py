"""Current-source caller/COPY controls; no Docker, provisioning or science."""
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import live_stack

ROOT=Path(__file__).resolve().parents[2]


class DispatcherConsumerControls(unittest.TestCase):
    def test_exports_template_changes_mode_before_releasing_root_ownership(self):
        specification=json.loads((ROOT/'docs/implementation/poc-cohort-ordinary-prep-20261022.json').read_bytes())
        command=specification['service']['exports_owner_command']
        self.assertEqual(command[:2],['python','-c'])
        caps=specification['service']['exports_owner_caps']
        self.assertEqual(caps[caps.index('--cap-add')+1],'CHOWN')
        for fault in (None,'owner','group','symlink','nonempty'):
            with self.subTest(fault=fault):
                observed=SimpleNamespace(st_uid=1 if fault=='owner' else 0,st_gid=1 if fault=='group' else 0,
                    st_mode=(stat.S_IFLNK if fault=='symlink' else stat.S_IFDIR)|0o755)
                events=[]
                def chmod(path,mode):
                    self.assertEqual(path,'/exports')
                    if observed.st_uid!=0:raise PermissionError('CHOWN-only root cannot chmod foreign inode')
                    events.append('chmod');observed.st_mode=stat.S_IFDIR|mode
                def chown(path,uid,gid):
                    self.assertEqual(path,'/exports');events.append('chown');observed.st_uid=uid;observed.st_gid=gid
                fake=SimpleNamespace(lstat=Mock(return_value=observed),listdir=Mock(return_value=['retained'] if fault=='nonempty' else []),
                    chmod=chmod,chown=chown)
                with patch.dict(sys.modules,{'os':fake}):
                    if fault:
                        with self.assertRaises(AssertionError):exec(command[2],{})
                    else:exec(command[2],{})
                self.assertEqual(events,[] if fault else ['chmod','chown'])
                if not fault:self.assertEqual((observed.st_uid,observed.st_gid,stat.S_IMODE(observed.st_mode)),(10001,10001,0o700))

    def test_live_stack_rejects_retired_option_before_any_side_effect(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence=Path(temp)/'must-not-exist';error=io.StringIO()
            argv=['live_stack','--service-image','unused','--learner-image','unused',
                '--analysis-dispatcher','--evidence',str(evidence)]
            with patch.object(sys,'argv',argv),patch.object(live_stack,'run') as run, \
                    patch.object(live_stack.subprocess,'Popen') as popen,patch.object(live_stack.uuid,'uuid4') as uuid, \
                    redirect_stderr(error),self.assertRaises(SystemExit) as raised:
                live_stack.main()
            self.assertEqual(raised.exception.code,2)
            self.assertIn('is retired',error.getvalue())
            self.assertIn('poc-cohort-ordinary-prep-20261022.md',error.getvalue())
            self.assertFalse(evidence.exists());run.assert_not_called();popen.assert_not_called();uuid.assert_not_called()

    def test_retained_recipe_dispatcher_import_closure_without_base_tooling(self):
        for recipe in ('p1-protocol.Dockerfile','pa3-dispatcher-controls.Dockerfile'):
            with self.subTest(recipe=recipe),tempfile.TemporaryDirectory() as temp:
                stage=Path(temp)
                for line in (ROOT/'tooling/foundation'/recipe).read_text().splitlines():
                    if not line.startswith('COPY '):continue
                    sources=shlex.split(line)[1:-1]
                    for source in sources:
                        if Path(source).name in ('analysis_dispatcher.py','analysis_lifecycle.py'):
                            shutil.copyfile(ROOT/source,stage/Path(source).name)
                        if source.rstrip('/')=='tests/integration/replay' or source=='tests/integration/replay/test_borrowing_dispatcher.py':
                            shutil.copyfile(ROOT/'tests/integration/replay/test_borrowing_dispatcher.py',stage/'test_borrowing_dispatcher.py')
                self.assertTrue((stage/'analysis_dispatcher.py').is_file())
                self.assertTrue((stage/'analysis_lifecycle.py').is_file())
                # Stage the exact narrow consumer; its selected inspection test
                # must not depend on another test module absent from the overlay.
                self.assertTrue((stage/'test_borrowing_dispatcher.py').is_file())
                program="""import sys,unittest
def audit(event,args):
    if event=='import' and args[0].split('.')[0] in ('numpy','scipy','pymc'):
        raise RuntimeError('numerical import forbidden')
sys.addaudithook(audit)
sys.path.insert(0,sys.argv[1])
import analysis_dispatcher,analysis_lifecycle
suite=unittest.defaultTestLoader.loadTestsFromName('test_borrowing_dispatcher.DispatcherAdmissionControls.test_only_selected_container_state_is_captured')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
"""
                result=subprocess.run([sys.executable,'-I','-B','-c',program,str(stage)],capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
