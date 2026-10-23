"""Scalar S1 intake/path regressions; no scientific or generator imports."""
import importlib.abc
from pathlib import Path
import sys
import unittest

BLOCKED={'numpy','scipy','statsmodels','pymc','pytensor','arviz','arviz_stats','pandas','xarray','methods'}


class ScientificImportTripwire(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED or fullname.startswith('services.generator'):
            raise AssertionError('Scientific/generator import forbidden in S1 source checks: '+fullname)


if __name__=='__main__':
    sys.meta_path.insert(0,ScientificImportTripwire())
    root=Path(__file__).resolve().parents[1]
    for path in (root,root/'tests',root/'tests/contracts',root/'tests/run_contracts',root/'tests/integration/replay'):
        sys.path.insert(0,str(path))
    names=('test_s1_intake_performance.ArtifactAncestryTests','test_s1_intake_performance.S1IntakeSourceTests',
        'test_support_archive.SupportProofTests.test_supplemental_public_inventory_exact_set_ids_and_immutable_original_index',
        'test_support_archive.SupportProofTests.test_paths_links_and_changed_bytes_rejected',
        'test_support_archive.SupportProofTests.test_independently_configured_descriptor_source_runtime_members_and_pairs',
        'test_support_archive.SupportProofTests.test_positive_empty_closures_omissions_partial_future_and_corrected_refs',
        'test_support_archive.SupportProofTests.test_stage_source_runtime_and_cross_window_substitutions',
        'test_support_archive.SupportProofTests.test_known_probability_consent_and_hold_checks_are_not_inferred_from_projection_hash')
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in names)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert not BLOCKED.intersection(sys.modules),'scientific module loaded'
    assert not any(n.startswith('services.generator') for n in sys.modules),'generator module loaded'
    print('S1 source scientific/generator import tripwire: PASS; no blocked modules loaded')
    sys.exit(not result.wasSuccessful())
