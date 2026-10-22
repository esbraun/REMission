"""A terminal success after either frozen deadline cannot qualify."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tooling/foundation'))
from run_pa3_compile import terminal_reason


class CompileDeadlineTests(unittest.TestCase):
    def test_terminal_after_phase_cap_is_vetoed(self):
        state=dict(Running=False,ExitCode=0,OOMKilled=False)
        self.assertEqual(terminal_reason(state,0,600.001,600,False),'deadline-exceeded')
        self.assertEqual(terminal_reason(state,0,599.999,600,False),None)
        self.assertEqual(terminal_reason(state,0,1,600,True),'deadline-exceeded')

    def test_actual_running_and_oom_never_qualify(self):
        self.assertEqual(terminal_reason(dict(Running=True),124,600,600,True),'termination-unconfirmed')
        self.assertEqual(terminal_reason(dict(Running=False,ExitCode=137,OOMKilled=True),137,20,600,False),'oom-killed')


if __name__=='__main__':unittest.main()
