"""Non-author-root executable replay controls; no author checkout is accessed."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
HELPERS=runpy.run_path(str(ROOT/'docs/implementation/evidence/G1-GENERATOR-INTERFACES-20261021/repair/command_paths.py'))


class RunnerPaths(unittest.TestCase):
    def test_recorded_author_script_executes_only_separate_owned_clone_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary);foreign=parent/'historical author';own=parent/'own clone'
            relative=Path('docs/implementation/evidence/G1-GENERATOR-INTERFACES-20261021/preservation.py')
            for checkout in (foreign,own):(checkout/relative).parent.mkdir(parents=True)
            (foreign/relative).write_text("raise RuntimeError('FOREIGN SOURCE EXECUTED')\n")
            (own/relative).write_text("import json;from pathlib import Path;print(json.dumps({'source':str(Path(__file__).resolve()),'cwd':str(Path.cwd().resolve())}))\n")
            historical=[['docker','run','--mount',f'type=bind,source={foreign.as_posix()},target=/workspace,readonly','fixture-image','python','-m','not_executed'],['C:/historical/dependency/python.exe',str(foreign/relative)]]
            current=HELPERS['rebind_commands'](historical,own,sys.executable)
            self.assertEqual(current[1],[sys.executable,str((own/relative).resolve())])
            self.assertIn('source='+own.as_posix(),current[0][3])
            observed=subprocess.run(current[1],cwd=own,capture_output=True,text=True,check=True)
            identity=json.loads(observed.stdout)
            self.assertEqual(identity,dict(source=str((own/relative).resolve()),cwd=str(own.resolve())))
            # Replaying the corrected command again (affected runner case)
            # remains local; a missing author fixture is no dependency.
            (foreign/relative).unlink()
            repeated=HELPERS['rebind_commands'](current,own,sys.executable)
            self.assertEqual(repeated,current)
            subprocess.run(repeated[1],cwd=own,capture_output=True,text=True,check=True)

    def test_windows_history_and_unknown_escaped_symlink_or_wrong_cwd_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary);own=parent/'clone';own.mkdir();(own/'docs').mkdir()
            script=own/'docs/check.py';script.write_text('pass\n')
            history=[['docker','run','--mount','type=bind,source=C:/old-author,target=/workspace,readonly','image'],['C:/old-environment/python.exe',r'C:\old-author\docs\check.py']]
            current=HELPERS['rebind_commands'](history,own,sys.executable)
            self.assertEqual(current[1][1],str(script.resolve()))
            # Docker paths retain their container namespace while their host
            # counterpart is checked against this checkout, including replay.
            container=history[0]+['python','-m','unittest','discover','-s','docs']
            rebound=HELPERS['rebind_commands']([container],own,sys.executable)[0]
            self.assertEqual(rebound[-1],'docs')
            container_script=history[0]+['python','/workspace/docs/check.py']
            rebound=HELPERS['rebind_commands']([container_script],own,sys.executable)[0]
            self.assertEqual(rebound[-1],'/workspace/docs/check.py')
            for bad in ('../outside.py','C:/unrecognized/other.py',str(parent/'outside.py')):
                with self.subTest(path=bad),self.assertRaises(ValueError):HELPERS['rebind_commands']([history[0],[sys.executable,bad]],own,sys.executable)
            outside=parent/'outside.py';outside.write_text('pass\n');link=own/'docs/link.py';link.symlink_to(outside)
            with self.assertRaises(ValueError):HELPERS['rebind_commands']([history[0],[sys.executable,str(link)]],own,sys.executable)
            with self.assertRaises(ValueError):HELPERS['assert_own_cwd'](own,cwd=parent)
            with self.assertRaises(ValueError):HELPERS['rebind_commands']([history[0],[sys.executable,'-c',"open('C:/old-author/private.py')"]],own,sys.executable)


if __name__=='__main__':unittest.main()
