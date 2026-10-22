"""Non-fitting CVM controls plus affected default/Numba regressions."""
import copy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_pa3_numba as prior_controls
from pa3_monitor import compilation_options,optimizer_identity,verify_cvm
import run_pa3_compile as runner


def cvm_policy():
    return json.loads((Path(__file__).resolve().parents[2]/'tooling/foundation/pa3-cvm-policy.json').read_bytes())


class CvmControls(prior_controls.NumbaContrastTests):
    def test_cvm_keeps_original_query_without_exclusions(self):
        from pytensor.compile.mode import get_default_mode
        default=get_default_mode();before=optimizer_identity(default.provided_optimizer)
        options,binding=compilation_options(cvm_policy(),default)
        self.assertEqual(binding['candidate_optimizer'],before)
        self.assertEqual(optimizer_identity(default.provided_optimizer),before)
        linker=options['mode'].linker
        self.assertEqual(type(linker).__name__,'VMLinker')
        self.assertTrue(linker.use_cloop);self.assertTrue(linker.c_thunks)
        self.assertIsNone(linker.callback);self.assertIsNone(linker.callback_input)
        wrong=cvm_policy();wrong['excluded_tags']=['fusion']
        with self.assertRaises(ValueError):compilation_options(wrong,default)

    def test_tiny_scalar_actual_cvm_and_whole_vm_fallback_rejection(self):
        # A scalar library control, not a clinical graph, fit or benchmark.
        import pytensor
        import pytensor.tensor as pt
        options,_=compilation_options(cvm_policy())
        x=pt.dscalar('control_x');function=pytensor.function([x],x*x+1.,**options)
        actual=verify_cvm(function)
        self.assertEqual(actual['vm_type'],'pytensor.link.c.cvm.CVM')
        self.assertEqual(float(function(3.)),10.)
        fake=SimpleNamespace(maker=function.maker,vm=object())
        with self.assertRaisesRegex(ValueError,'whole-VM fallback'):verify_cvm(fake)
        changed=copy.copy(function.maker.mode.linker);changed.callback=lambda *args:None
        fake=SimpleNamespace(vm=function.vm,maker=SimpleNamespace(mode=SimpleNamespace(linker=changed)))
        with self.assertRaisesRegex(ValueError,'flags/callbacks'):verify_cvm(fake)

    def test_two_policy_flags_rejected_before_docker_or_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence=Path(directory)/'uncreated'
            argv=['run_pa3_compile','--image','unused','--evidence',str(evidence),'--numba-policy','old','--cvm-policy','new']
            with patch.object(sys,'argv',argv),patch.object(runner,'run',side_effect=AssertionError('Docker must not run')),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:runner.main()
            self.assertEqual(stopped.exception.code,2);self.assertFalse(evidence.exists())


if __name__=='__main__':prior_controls.unittest.main()
