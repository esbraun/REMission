# Preserved initial R2 check failure

2026-10-21. The initial read-only `python -m contracts.dgp.checks` run passed pip consistency, DGP exports, domain exports, ledger, working diff whitespace and full diff whitespace against accepted base b24c3c0. Contract unittest discovery failed: 60 tests ran, with two errors and no assertion failures.

Both errors were `ValueError: calibration request requires current DGP version` in the preserved calibration regression groups `test_calibration_binding_rejects_missing_derived_values_and_wrong_target` and `test_external_target_is_derived_and_bound_to_independent_upstream_identities`. Their fixture VersionRefs still requested DGP 1.1.0 after the current DGP moved to 1.2.0. The fail-closed production guard correctly rejected these stale inputs.

Repair: update only those two test fixture DGP version strings to 1.2.0. The CalibrationBinding wire schema stays 1.1.0. Wrong target/purpose/cell/upstream-identity rejection and S02 threshold/null regressions remain intact. The subsequent complete runner passed; its new R2 JSON records the final successful execution. This note preserves the observed failed attempt and does not replace the original 43-test author evidence, original changes_requested review or 18-test partial checkpoint.
