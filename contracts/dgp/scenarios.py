"""Frozen catalog expansion: explicit variant rows, then only authorized n copies.

Each cell is independently auditable. The rows below never take a product of
perturbations. Variant labels define distinct controls even when values overlap.
"""
from copy import deepcopy
from .parameters import VERSION, reference_parameters, validate_parameters

# Family, variant, parameter overrides, target, tiers. Unlisted values are taken
# from the REQUIRED complete validated input table, never from code fallbacks.
ROWS = [
    ("S01", "reference", {}, "visit", "R"),
    ("S02", "outcome_null", {"z_L": 0, "z_B": 0, "z_prompt": 0,
                              "z_delayed_prompt": 0, "prompt_state_gain": 0}, "visit_null", "RN"),
    ("S03", "constant", {}, "constant_fixture", "R"),
    ("S04", "observed_modifier", {"L_T": 0, "z_B": 0, "z_T_modifier": -0.4}, "visit_modifier", "RP"),
    ("S05", "prognostic_null", {"L_T": 0, "z_B": 0, "z_M": 0.2}, "visit_null", "RP"),
    ("S06", "feedback", {}, "visit", "R"),
    ("S07", "hidden_U", {"export_U": 0}, "visit", "R"),
    ("S08", "floor_020", {"assignment_floor": 0.2}, "visit", "R"),
    ("S08", "floor_005", {"assignment_floor": 0.05}, "visit", "R"),
    ("S08", "floor_001", {"assignment_floor": 0.01}, "visit", "R"),
    ("S08", "structural_zero", {"structural_zero_enabled": 1}, "visit_unsupported", "R"),
    ("S09", "compatible", {}, "external_visit", "R"),
    ("S10", "shift_1SE", {"external_shift_SE": 1}, "external_visit", "R"),
    ("S10", "shift_2SE", {"external_shift_SE": 2}, "external_visit", "R"),
    ("S10", "reverse_sign", {"external_reverse_sign": 1}, "external_visit", "R"),
    ("S11", "omitted_modifier_shift", {"external_modifier_export": 0, "external_X_law": [1, 1], "external_M_probability": 0.8,
                                         "L_T": 0, "z_B": 0, "z_T_modifier": -0.4}, "external_visit", "R"),
    ("S12", "IPD_and_summary", {}, "lineage", "D"),
    ("S12", "duplicated_summary_meta", {}, "lineage", "D"),
    ("S12", "repeated_update", {}, "lineage", "D"),
    ("S13", "blocks_2_rho04", {"n1_blocks": 2}, "n1", "R"),
    ("S13", "blocks_4_rho04", {"n1_blocks": 4}, "n1", "R"),
    ("S13", "blocks_8_rho04", {"n1_blocks": 8}, "n1", "R"),
    ("S13", "blocks_4_rho0", {"n1_blocks": 4, "n1_rho": 0}, "n1", "R"),
    ("S13", "blocks_4_rho08", {"n1_blocks": 4, "n1_rho": 0.8}, "n1", "R"),
    ("S14", "half_life_0", {"carry_half_life": 0}, "n1", "R"),
    ("S14", "half_life_1", {"carry_half_life": 1}, "n1", "R"),
    ("S14", "half_life_3", {"carry_half_life": 3}, "n1", "R"),
    ("S14", "rebound_absent", {"rebound_enabled": 0}, "n1", "R"),
    ("S14", "rebound_present", {"rebound_enabled": 1}, "n1", "R"),
    ("S15", "phase_aligned", {"n1_phase_mode": 1}, "n1", "R"),
    ("S15", "phase_balanced", {"n1_phase_mode": 2}, "n1", "R"),
    ("S16", "adherence_rescue", {"med_taken_probability": 0.7, "rescue_enabled": 1}, "n1", "R"),
    ("S16", "outcome_stop", {"n1_stop_mode": 1}, "n1", "R"),
    ("S16", "insufficient_blocks", {"n1_stop_mode": 2}, "n1", "R"),
    ("S17", "randomized_tree", {}, "randomized_tree", "R"),
    ("S18", "observational_tree", {}, "observational_tree", "R"),
    ("S19", "noisy_response", {"response_flip_probability": 0.2}, "randomized_tree", "R"),
    ("S19", "sparse_nonresponders", {"sparse_response_probability": 0.9}, "randomized_tree", "R"),
    ("S20", "prompt_null", {"z_prompt": 0, "z_delayed_prompt": 0, "prompt_state_gain": 0, "habituation_rate": 0}, "mrt_null", "RNP"),
    ("S21", "immediate", {}, "mrt", "RP"),
    ("S22", "habituation", {"habituation_rate": 0.2}, "mrt", "RP"),
    ("S22", "delayed_harm", {"z_delayed_prompt": 0.15}, "mrt", "RP"),
    ("S23", "MCAR_0", {"report_mode": 1, "missing_fraction": 0}, "report_visit_mrt", "R"),
    ("S23", "MCAR_20", {"report_mode": 1, "missing_fraction": 0.2}, "report_visit_mrt", "R"),
    ("S23", "MCAR_40", {"report_mode": 1, "missing_fraction": 0.4}, "report_visit_mrt", "R"),
    ("S23", "MAR_20", {"report_mode": 2, "missing_fraction": 0.2}, "report_visit_mrt", "R"),
    ("S23", "MAR_40", {"report_mode": 2, "missing_fraction": 0.4}, "report_visit_mrt", "R"),
    ("S24", "MNAR_20", {"report_mode": 3, "missing_fraction": 0.2}, "mrt", "RP"),
    ("S24", "MNAR_40", {"report_mode": 3, "missing_fraction": 0.4}, "mrt", "RP"),
    ("S24", "action_reporting_equal_rewards", {"report_mode": 4, "missing_fraction": 0.2, "report_action_quality": 1, "z_prompt": 0, "z_delayed_prompt": 0, "prompt_state_gain": 0}, "mrt_null", "RP"),
    ("S25", "quiet_wake", {"wearable_wake_bias": 0.3}, "measurement", "R"),
    ("S25", "device_shift", {"device_shift_minutes": 30}, "measurement", "R"),
    ("S26", "correlated_items", {"item_copula_rho": 0.4}, "measurement", "R"),
    ("S26", "overlapping_recall", {}, "measurement", "R"),
    ("S26", "phase_item_shift", {"item_phase_offsets": [0.3, 0.2, 0.1, 0, -0.1, -0.2, -0.3]}, "measurement", "R"),
    ("S27", "admission", {"admission_enabled": 1}, "interruptions", "RD"),
    ("S27", "death", {"death_enabled": 1}, "interruptions", "RD"),
    ("S27", "discontinuation", {"discontinuation_enabled": 1}, "visit", "RD"),
    ("S27", "regimen_change", {"regimen_change_enabled": 1}, "visit", "RD"),
    ("S28", "late_upload", {"delay_probabilities": [0.7, 0.2, 0.1]}, "system", "D"),
    ("S28", "correction", {}, "system", "D"),
    ("S28", "duplicate", {}, "system", "D"),
    ("S28", "stale_approval", {}, "system", "D"),
    ("S28", "consent_withdrawal", {}, "system", "D"),
    ("S29", "frozen_support", {}, "frozen_n1", "RPD"),
    ("S29", "drifting_global", {}, "frozen_n1", "RPD"),
    ("S30", "conflict_sparse_overlap", {"external_shift_SE": 2, "assignment_floor": 0.01}, "external_visit", "R"),
    ("S31", "phase_carryover", {"regimen_change_enabled": 1, "carry_half_life": 3}, "n1", "R"),
    ("S31", "admission_reporting", {"admission_enabled": 1, "report_mode": 2, "missing_fraction": 0.4}, "interruptions", "R"),
    ("S32", "wrong_propensity", {}, "system", "D"),
    ("S32", "infeasible_bounds", {}, "system", "D"),
    ("S32", "missing_fit", {}, "system", "D"),
    ("S32", "no_actions", {}, "system", "D"),
]

# Targets are separate from generative coefficients. A conditional claim must
# integrate latent history, not use the structural realization as known data.
TARGETS = {
    "visit": ("EST-VISIT", "ISI", "ISI_points", "behavioral_continue", "usual_care", "reference"),
    "visit_null": ("EST-VISIT", "ISI", "ISI_points", "behavioral_continue", "usual_care", "reference"),
    "visit_modifier": ("EST-VISIT", "ISI", "ISI_points", "behavioral_continue", "usual_care", "reference"),
    "visit_unsupported": ("EST-VISIT", "ISI", "ISI_points", "behavioral_continue", "usual_care", "adversarial"),
    "constant_fixture": ("FIX-CONSTANT", "linear_Y", "fixture_points", "A1", "A0", "analytic"),
    "external_visit": ("EST-VISIT", "ISI", "ISI_points", "behavioral_continue", "usual_care", "reference"),
    "n1": ("EST-N1", "daily_sleep_quality", "quality_points", "MED_A", "MED_B", "reference"),
    "randomized_tree": ("FIX-ESC-RANDOMIZED", "linear_Y", "fixture_points", "regime_11", "regime_00", "analytic"),
    "observational_tree": ("FIX-ESC-OBSERVATIONAL", "linear_Y", "fixture_points", "regime_11", "regime_00", "analytic"),
    "mrt": ("EST-MRT", "proximal_support_reward", "quality_points", "support_prompt", "no_prompt", "reference"),
    "mrt_null": ("EST-MRT", "proximal_support_reward", "quality_points", "support_prompt", "no_prompt", "reference"),
    "report_visit_mrt": ("EST-MRT", "proximal_support_reward", "quality_points", "support_prompt", "no_prompt", "adversarial"),
    "measurement": ("EST-VISIT", "ISI", "ISI_points", "behavioral_continue", "usual_care", "adversarial"),
    "interruptions": ("EST-INT", "interruption_vector", "probability_vector", "behavioral_continue", "usual_care", "adversarial"),
    "frozen_n1": ("EST-N1", "daily_sleep_quality", "quality_points", "MED_A", "MED_B", "reference"),
    "lineage": ("SYSTEM-LINEAGE", "rejection", "none", "reject", "accept_unique", "system"),
    "system": ("SYSTEM-BOUNDARY", "rejection", "none", "reject", "retain_valid", "system"),
}


def scenario_manifest() -> dict:
    cells = []
    for family, variant, overrides, target, tiers in ROWS:
        sizes = [60, 240] if family in {"S01", "S02", "S03", "S04", "S05", "S20", "S21", "S22"} else [60]
        for n in sizes:
            estimand, outcome, unit, intervention, comparator, layer = TARGETS[target]
            cells.append({"id": f"{family}.{variant}.n{n}", "family": family,
                          "variant": variant, "patients": n, "version": VERSION,
                          "overrides": deepcopy(overrides), "target": target,
                          "estimand": estimand, "outcome": outcome, "unit": unit,
                          "intervention": intervention, "comparator": comparator,
                          "layer": layer, "tiers": list(tiers),
                          "source": f"docs/spec/scenario-catalog.md#{family}"})
    return {"version": VERSION, "catalog_version": 1, "synthetic": True, "cells": cells}


def validate_scenarios(manifest: dict) -> dict:
    expected = scenario_manifest()
    # JSON token equality rejects bool-as-number and reordered or extra cells.
    import json
    if json.dumps(manifest, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError("scenario version/override/target/coverage/order mismatch; use a new reviewed version")
    known = set(reference_parameters()["parameters"])
    for cell in manifest["cells"]:
        if not set(cell["overrides"]) <= known:
            raise ValueError("unknown override symbol")
    return deepcopy(manifest)


def resolve_cell(parameters: dict, scenarios: dict, cell_id: str) -> dict:
    validated = validate_parameters(parameters)
    catalog = validate_scenarios(scenarios)
    matches = [cell for cell in catalog["cells"] if cell["id"] == cell_id]
    if len(matches) != 1:
        raise ValueError("unknown cell; no reference fallback")
    cell = matches[0]
    for symbol, value in cell["overrides"].items():
        validated["parameters"][symbol]["value"] = deepcopy(value)
    return {"cell": cell, "parameters": validated["parameters"]}
