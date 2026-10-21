"""G0-DGP contract risks, independently expected values, no statistical runs."""
import copy
import json
import math
from pathlib import Path
import unittest

from contracts.dgp.parameters import reference_parameters, validate_parameters
from contracts.dgp.calibration import (CalibrationBinding, ExternalTargetEvidence,
                                       calibration_request, require_solved)
from contracts.domain.common import VersionRef
from contracts.dgp.scenarios import resolve_cell, scenario_manifest, validate_scenarios
from contracts.dgp.truth import (beta_posterior, bisect_calibration, escalation,
                                 normal_posterior, ordinal_expectation, seed_words,
                                 truth_status, two_period)

ROOT = Path(__file__).resolve().parents[2]


class ParameterAndCellContracts(unittest.TestCase):
    def test_missing_required_coefficient_is_rejected_before_resolution(self):
        parameters = reference_parameters()
        del parameters["parameters"]["z_L"]
        with self.assertRaisesRegex(ValueError, "z_L"):
            resolve_cell(parameters, scenario_manifest(), "S01.reference.n60")

    def test_unknown_and_malformed_parameter_records_are_not_defaults(self):
        for mutation in (lambda p: p.update(version="2.0.0"),
                         lambda p: p["parameters"].update(unknown=p["parameters"]["z_L"]),
                         lambda p: p["parameters"]["z_L"].update(value=True),
                         lambda p: p["parameters"]["z_L"].pop("unit")):
            with self.subTest(mutation=mutation):
                data = reference_parameters()
                mutation(data)
                with self.assertRaises(ValueError):
                    validate_parameters(data)

    def test_target_version_override_and_order_are_frozen(self):
        for mutation in (lambda p: p.update(version="1"),
                         lambda p: p["cells"][0]["overrides"].update(z_L=99),
                         lambda p: p["cells"][0].update(outcome="daily_sleep_quality"),
                         lambda p: p["cells"].reverse(),
                         lambda p: p["cells"].pop()):
            data = scenario_manifest()
            mutation(data)
            with self.assertRaises(ValueError):
                validate_scenarios(data)

    def test_exact_family_variant_counts_no_implicit_products(self):
        # Independent canonical expansion chosen in dgp-decisions.md.
        counts = [2, 2, 2, 2, 2, 1, 1, 4, 1, 3, 1, 3, 5, 5, 2, 3,
                  1, 1, 2, 2, 2, 4, 5, 3, 2, 3, 4, 5, 2, 1, 2, 4]
        cells = scenario_manifest()["cells"]
        self.assertEqual(len(cells), sum(counts))
        self.assertEqual(len({c["id"] for c in cells}), len(cells))
        self.assertEqual([sum(c["family"] == f"S{i:02}" for c in cells) for i in range(1, 33)], counts)
        self.assertEqual(cells[0]["id"], "S01.reference.n60")
        self.assertEqual(cells[1]["id"], "S01.reference.n240")
        self.assertEqual(cells[-1]["id"], "S32.no_actions.n60")
        for cell in cells:
            self.assertIn(cell["patients"], [60, 240])
            if cell["patients"] == 240:
                self.assertIn(cell["family"], {"S01", "S02", "S03", "S04", "S05", "S20", "S21", "S22"})

    def test_resolution_is_isolated_and_never_unknown_cell_fallback(self):
        parameters = reference_parameters()
        result = resolve_cell(parameters, scenario_manifest(), "S14.half_life_3.n60")
        self.assertEqual(result["parameters"]["carry_half_life"]["value"], 3)
        self.assertEqual(parameters["parameters"]["carry_half_life"]["value"], 1)
        with self.assertRaisesRegex(ValueError, "unknown cell"):
            resolve_cell(parameters, scenario_manifest(), "S33.fake.n60")

    def test_null_paths_and_modifier_target_do_not_conflate_medication(self):
        params = reference_parameters()
        scenarios = scenario_manifest()
        null = resolve_cell(params, scenarios, "S02.outcome_null.n60")["parameters"]
        self.assertEqual(null["L_T"]["value"], -0.1)  # diagnostic intermediate changes
        for key in ("z_L", "z_B", "z_T", "z_T_modifier", "z_prompt", "z_delayed_prompt", "prompt_state_gain"):
            self.assertEqual(null[key]["value"], 0)
        prompt = resolve_cell(params, scenarios, "S20.prompt_null.n60")["parameters"]
        for key in ("z_prompt", "z_delayed_prompt", "prompt_state_gain", "habituation_rate"):
            self.assertEqual(prompt[key]["value"], 0)
        modifier = resolve_cell(params, scenarios, "S04.observed_modifier.n60")
        self.assertEqual(modifier["cell"]["intervention"], "behavioral_continue")
        self.assertEqual(modifier["cell"]["outcome"], "ISI")
        self.assertEqual(modifier["parameters"]["z_med_A_modifier"]["value"], 0)
        self.assertEqual(modifier["parameters"]["z_T_modifier"]["value"], -0.4)

    def test_s02_threshold_crossing_changes_availability_but_not_outcome_law(self):
        p = {k: row["value"] for k, row in resolve_cell(
            reference_parameters(), scenario_manifest(), "S02.outcome_null.n60")["parameters"].items()}
        # Independent algebra from shared innovations after 28 assigned nights;
        # consent, weekday, preference, envelope and burden prerequisites agree.
        delta = p["L_T"] * (1 - p["L_ar"] ** 28) / (1 - p["L_ar"])
        histories = [(0, [3.05, 0, 0], .1), (1, [3.05 + delta, delta, delta], .7)]
        available = [all(x <= p["stability_max_L"] for x in L) for _, L, _ in histories]
        self.assertEqual(available, [False, True])
        self.assertNotEqual(histories[0][1], histories[1][1])
        transitions = []
        for (T, L, B), offered in zip(histories, available):
            # All varying parents of the declared severity equation are included;
            # common other terms/innovation are represented by .3. Different B,
            # current and prior prompt histories cannot change the null law.
            transitions.append(.3 + p["z_L"] * sum(L) / 3 + p["z_B"] * B +
                               p["z_T"] * T + p["z_T_modifier"] * T +
                               p["z_prompt"] * offered + p["z_delayed_prompt"] * offered +
                               p["z_nonlinear"] * (L[0] ** 2 - 1))
        self.assertEqual(transitions[0], transitions[1])
        # Identical recall/error implies identical category CDFs, stronger than
        # checking only an expected total. This is bounded algebra, not G1 rollout.
        laws = [[1 / (1 + math.exp(-(cut - z - offset)))
                 for offset in p["item_offsets"] for cut in p["item_cutpoints"]]
                for z in transitions]
        self.assertEqual(laws[0], laws[1])

    def test_generated_artifacts_are_valid_complete_inputs(self):
        validate_parameters(json.loads((ROOT / "contracts/dgp/parameters-v1.json").read_text()))
        validate_scenarios(json.loads((ROOT / "contracts/dgp/scenarios-v1.json").read_text()))

    def test_reference_numeric_units_and_covariance_preserve_canonical_defaults(self):
        records = reference_parameters()["parameters"]
        for symbol, expected in {"L_ar": .6, "L_z": .15, "L_T": -.1, "B_retention": .995,
                                 "B_gain": .08, "z_med_A": -.2, "z_med_B": -.12, "z_prompt": -.08,
                                 "z_innovation_sd": .4, "recall_sd": .2, "wearable_wake_bias": .3,
                                 "visit_horizon": 42, "recall_days": 14}.items():
            self.assertEqual(records[symbol]["value"], expected)
        covariance = records["L_covariance"]["value"]
        self.assertEqual(covariance, [.09, .027, .027, .027, .09, .027, .027, .027, .09])
        self.assertGreater(.09 - .027, 0)  # two repeated equicorrelation eigenvalues
        self.assertGreater(.09 + 2 * .027, 0)
        self.assertEqual(records["Q_z"]["unit"], "quality_points")
        self.assertEqual(records["z_med_A"]["unit"], "dimensionless")
        self.assertEqual(records["visit_days"]["value"], [0, 21, 42])
        self.assertEqual(records["isi_days"]["value"], [0, 14, 28, 42, 56, 70, 84])

    def test_omitted_source_modifier_actually_modifies_the_behavioral_target(self):
        s11 = resolve_cell(reference_parameters(), scenario_manifest(), "S11.omitted_modifier_shift.n60")
        self.assertEqual(s11["parameters"]["z_T_modifier"]["value"], -.4)
        self.assertEqual(s11["parameters"]["external_modifier_export"]["value"], 0)
        self.assertEqual(s11["parameters"]["external_M_probability"]["value"], .8)


class IndependentTruthFixtures(unittest.TestCase):
    def test_calibration_binding_rejects_missing_derived_values_and_wrong_target(self):
        ref = {"id": "dgp-v1", "version": "1.1.0", "sha256": "a" * 64}
        request = calibration_request(cell_id="S23.MAR_20.n60", dgp=VersionRef.model_validate(ref))
        data = {"schema_version": "1.1.0", "synthetic": True, "purpose": "report_rate", "status": "solved",
                "dgp": ref, "cell_id": "S23.MAR_20.n60", "calibration_sample_sha256": "b" * 64,
                "seed_key_sha256": "c" * 64, "sample_size": 200000, "target": .8, "achieved": .8,
                "achieved_mcse": .001, "coefficient": 2.0, "iterations": 10,
                "source_se": None, "source_se_mcse": None, "source_pilot": None, "source_reference": None,
                "target_spec": request["target_spec"],
                "smallest_estimator_se": None, "frozen_before": "development_and_confirmation"}
        binding = CalibrationBinding.model_validate(data)
        self.assertEqual(require_solved(binding, cell_id="S23.MAR_20.n60", dgp=VersionRef.model_validate(ref)), 2)
        with self.assertRaises(ValueError):
            require_solved(binding, cell_id="S23.MAR_40.n60", dgp=VersionRef.model_validate(ref))
        for field in ("coefficient", "achieved_mcse", "target"):
            changed = copy.deepcopy(data)
            del changed[field]
            with self.assertRaises(ValueError):
                CalibrationBinding.model_validate(changed)
        with self.assertRaises(ValueError):
            CalibrationBinding.model_validate(data | {"achieved": .7})
        unresolved = CalibrationBinding.model_validate(data | {"status": "inconclusive", "coefficient": None})
        with self.assertRaises(ValueError):
            require_solved(unresolved, cell_id=data["cell_id"], dgp=VersionRef.model_validate(ref))

        # Each hostile record is internally solved to its own target and keeps
        # matching DGP/cell hashes. Consumption must still reject it.
        for changes in ({"target": .6, "achieved": .6}, {"purpose": "event_rate"},
                        {"target_spec": request["target_spec"] | {"sha256": "d" * 64}},
                        {"cell_id": "S99.fake.n60"}, {"cell_id": "S01.reference.n60"},
                        {"cell_id": "S23.MCAR_20.n60"}):
            with self.subTest(changes=changes):
                hostile = CalibrationBinding.model_validate(data | changes)
                with self.assertRaises(ValueError):
                    require_solved(hostile, cell_id=hostile.cell_id, dgp=VersionRef.model_validate(ref))

    def test_external_target_is_derived_and_bound_to_independent_upstream_identities(self):
        ref = VersionRef(id="dgp-v1", version="1.1.0", sha256="a" * 64)
        evidence = ExternalTargetEvidence(
            source_reference=VersionRef(id="reference-contrast", version="1", sha256="b" * 64),
            source_pilot=VersionRef(id="source-se-pilot", version="1", sha256="c" * 64),
            reference_contrast=-1., source_se=.2, source_se_mcse=.001, smallest_estimator_se=.1)
        request = calibration_request(cell_id="S10.shift_2SE.n60", dgp=ref, external=evidence)
        self.assertAlmostEqual(request["target"], -.6)
        binding = CalibrationBinding.model_validate(request | {
            "schema_version": "1.1.0", "synthetic": True, "status": "solved",
            "calibration_sample_sha256": "d" * 64, "seed_key_sha256": "e" * 64,
            "sample_size": 200000, "achieved": request["target"], "achieved_mcse": .001,
            "coefficient": .15, "iterations": 12, "frozen_before": "development_and_confirmation"})
        self.assertEqual(require_solved(binding, cell_id=binding.cell_id, dgp=ref, external=evidence), .15)
        for changed in (evidence.model_copy(update={"source_pilot": VersionRef(id="source-se-pilot", version="2", sha256="f" * 64)}),
                        evidence.model_copy(update={"source_reference": VersionRef(id="reference-contrast", version="2", sha256="f" * 64)}),
                        evidence.model_copy(update={"reference_contrast": -.9})):
            with self.assertRaises(ValueError):
                require_solved(binding, cell_id=binding.cell_id, dgp=ref, external=changed)
        with self.assertRaises(ValueError):
            require_solved(binding, cell_id=binding.cell_id, dgp=ref)
        reversal = calibration_request(cell_id="S10.reverse_sign.n60", dgp=ref, external=evidence)
        self.assertEqual(reversal["target"], 1.)

    def test_normal_beta_analytic_answers(self):
        self.assertEqual(normal_posterior(10), (40 / 81, 4 / 81))
        self.assertEqual(beta_posterior(8), (10, 15))
        with self.assertRaises(ValueError):
            beta_posterior(21)

    def test_two_period_descendants_and_continuation_are_recomputed(self):
        # Direct marginal expectation, separate from state enumeration.
        expected00 = 0.5 + 0.5 * (1 / (1 + math.exp(1)) + 1 / (1 + math.exp(0.2)))
        expected10 = -0.5 + 0.5 * (1 / (1 + math.exp(0.3)) + 1 / (1 + math.exp(-0.5)))
        self.assertAlmostEqual(two_period(0, 0), expected00)
        self.assertAlmostEqual(two_period(1, 0), expected10)
        self.assertNotAlmostEqual(two_period(1, 0) - two_period(0, 0), -1)  # omitted descendant fault
        self.assertAlmostEqual(two_period(1, 1) - two_period(1, 0), -2)
        self.assertNotAlmostEqual(two_period(1, 1), two_period(1, 0))  # wrong continuation fault
        self.assertLess(two_period(1, 0) - two_period(0, 0), 0)  # reversed sign fault

    def test_ordinal_tail_sum_and_exact_policy_tree_values(self):
        self.assertAlmostEqual(ordinal_expectation(0), 2)
        self.assertAlmostEqual(ordinal_expectation(0, (0.0,) * 7), 14)
        self.assertGreater(ordinal_expectation(1), ordinal_expectation(0))
        for a, b, expected in [(0, 0, 2.4), (0, 1, 3.6), (1, 0, 3.6), (1, 1, 4.4)]:
            self.assertAlmostEqual(escalation(a, b), expected)
            self.assertAlmostEqual(escalation(a, b, observational=True), expected + 0.5)
        self.assertAlmostEqual(escalation(0, 1, flip=0.2), 2.4 + 2 * 0.6 * 0.8)
        self.assertAlmostEqual(escalation(1, 1, sparse_response=0.9), 3.6 + 2 * 0.4 * 0.1)

    def test_both_precision_constraints_zero_se_and_cap(self):
        self.assertEqual(truth_status(.04, .2, "ISI_points", batches=1, cap=2), "continue_independent_batches")
        self.assertEqual(truth_status(.04, .2, "ISI_points", batches=2, cap=2), "inconclusive")
        self.assertEqual(truth_status(.01, .2, "ISI_points", batches=1, cap=2), "resolved")
        self.assertEqual(truth_status(.02, 2, "quality_points", batches=2, cap=2), "inconclusive")
        self.assertEqual(truth_status(0, 0, "ISI_points", batches=1, cap=2), "unresolved_zero_target_se")
        self.assertEqual(truth_status(0, 0, "ISI_points", batches=0, cap=2, analytic=True), "resolved")
        for error in (float("nan"), -0.1):
            with self.assertRaises(ValueError):
                truth_status(error, .2, "ISI_points", batches=1, cap=2)

    def test_keyed_streams_do_not_depend_on_prior_draw_counts(self):
        key = dict(protocol="g0-v1", phase="development", namespace="generation", scenario="S01.reference.n60",
                   replicate=0, patient="p1", time_index=0, process="clinical_L", stream="innovation", root_seed=20261020)
        before = seed_words(**key)
        seed_words(**(key | {"process": "unused_variable_draw_count"}))
        self.assertEqual(seed_words(**key), before)
        for change in ({"namespace": "truth"}, {"phase": "confirmation"}, {"time_index": 1}, {"stream": "alternate"}):
            self.assertNotEqual(seed_words(**(key | change)), before)
        with self.assertRaises(ValueError):
            seed_words(**(key | {"namespace": "shared"}))

    def test_calibration_solver_rejects_infeasible_and_cap_not_pass(self):
        solved = bisect_calibration(lambda x: 1 / (1 + math.exp(-x)), .8, lower=-30, upper=30,
                                    tolerance=1e-4, iterations=100, increasing=True)
        self.assertEqual(solved["status"], "solved")
        self.assertLessEqual(abs(solved["achieved"] - .8), 1e-4)
        self.assertEqual(bisect_calibration(lambda x: x, 2, lower=0, upper=1, tolerance=.01,
                                          iterations=100, increasing=True)["status"], "infeasible")
        self.assertEqual(bisect_calibration(lambda x: x, .123, lower=0, upper=1, tolerance=1e-10,
                                          iterations=1, increasing=True)["status"], "inconclusive")
        reverse = bisect_calibration(lambda x: -x, .8, lower=-5, upper=5, tolerance=.005,
                                     iterations=100, increasing=False)
        self.assertEqual(reverse["status"], "solved")


if __name__ == "__main__":
    unittest.main()
