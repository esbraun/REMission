"""Contract fixtures: no empirical fits, generated patients or clinical acceptance."""
import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from contracts.domain.boundaries import (ContractViolation, LearnerInput,
    ObservedHistory, ensure_isi_comparable, validate_approval,
    validate_assignment, validate_fit_request, validate_isi_endpoint)
from contracts.domain.common import Estimated, FitMetadata
from contracts.domain.entities import (Approval, Assignment, Consent, DailyReport,
    DecisionSnapshot, ExternalStudy, ISIAssessment, ObservedRecord)
from contracts.domain.estimands import (EstimandContract, FitRequest,
    InterruptionResult, NamedThreshold)
from contracts.domain.evaluation import (DGPConfig, EvaluationCell, EvaluationProtocol,
    EvidenceRecord, GateEvidence, ReplicateResult, TruthResult)
from contracts.domain.export import ADAPTERS, products
from contracts.domain.temporal import TemporalContract

ROOT = Path(__file__).resolve().parents[2]


def parse(model, payload):
    return model.model_validate_json(json.dumps(payload))


def at(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def ref(name="fixture-version"):
    return {"id": name, "version": "1.0.0", "sha256": "a" * 64}


def seed():
    return {"namespace": "fixture", "protocol": "fixture", "scenario": "fixture",
            "replicate": 0, "patient": "P1", "time_index": 0, "process": "contract_test"}


def record(kind, name="R1", event="2026-10-01T07:00:00Z", available=None):
    return {"schema_version": "1.0.0", "synthetic": True, "kind": kind,
            "record_id": name, "patient_id": "P1", "event_at": event,
            "recorded_at": available or event, "available_at": available or event,
            "source": {"id": "fixture", "version": "1.0.0", "adapter": "simulation", "raw_sha256": "a" * 64},
            "lineage_id": name, "revision": 1, "supersedes": None,
            "duplicate_of": None, "record_status": "active"}


def report(name="R1", event="2026-10-01T07:00:00Z", available=None):
    return {**record("daily_report", name, event, available), "sleep_quality": 7.0,
            "function": 6.0, "adverse_symptoms": [], "diary_sleep_minutes": 400.0,
            "goals": ["rest"], "burden": 0.0, "missingness": "observed"}


def isi(name="I1", event="2026-10-15T07:00:00Z"):
    return {**record("isi", name, event), "instrument_version": "ISI-two-week-v1",
            "recall_days": 14, "recall_start": "2026-10-01T07:00:00Z",
            "recall_end": event, "items": [1, 2, 3, 4, 0, 1, 2]}


def history(records):
    return {"schema_version": "1.0.0", "synthetic": True, "kind": "observed_history",
            "patient_id": "P1", "records": records}


def request():
    context = {name: ref(name) for name in ["estimand", "dgp", "scenario", "input_data", "prior", "model", "protocol", "comparator_estimand"]}
    context.update({"observation_cutoff": "2026-10-02T08:00:00Z", "seed": seed(),
                    "allowed_information": "available_observed_history_only", "truth_access": "denied",
                    "comparator_information": "same_permitted_history", "source_ids": ["iche9", "gformula", "sim-check", "sim-ademp"],
                    "failure_policy": "retain_all_attempts_fail_or_abstain_never_fabricate"})
    return {"schema_version": "1.0.0", "synthetic": True, "kind": "fit_request",
            "context": context, "backend": "pymc", "sampler": "native_nuts",
            "precision": "float64", "configuration": ref("fit-config")}


def snapshot():
    return {**record("decision_snapshot", "D1"), "cutoff": "2026-10-01T06:59:59Z",
            "patient_version": 2, "state_version": 3, "consent_version": 4,
            "eligibility_version": 5, "workflow": {"clinical": "initial_assignment",
            "learning": "nof1_design", "data_readiness": "ready", "hold_reasons": [],
            "support_policy": ref("support-fixed"), "support_mode": "fixed"},
            "view": {"patient_id": "P1", "mode": "current", "snapshot_id": None},
            "eligibility": [{"action": a, "status": "eligible", "reasons": []} for a in ["MED_A", "MED_B"]],
            "outcome": "daily_sleep_quality", "horizon_days": 7, "estimand": ref("EST-N1"),
            "model": ref("model"), "posterior": None, "evidence": [], "policy": ref("policy")}


def approval(protocol=True):
    return {**record("approval", "APP1", "2026-10-01T08:00:00Z"), "decision_id": "D1",
            "option": None if protocol else "MED_A", "permitted_options": ["MED_A", "MED_B"] if protocol else [],
            "clinician_id": "DOC1", "purpose": "randomization_protocol" if protocol else "ordinary_treatment",
            "expected_patient_version": 2, "expected_state_version": 3,
            "expected_consent_version": 4, "expected_eligibility_version": 5}


def consent(component="nof1"):
    return {**record("consent", "C1"), "component": component, "consent_version": "1.0.0",
            "oversight_version": "synthetic-protocol-1", "consent_status": "active",
            "oversight_status": "approved_synthetic", "effective_at": "2026-10-01T07:00:00Z",
            "expires_at": "2026-11-01T00:00:00Z", "withdrawn_at": None}


def estimand(identifier="EST-VISIT"):
    interrupt = identifier == "EST-INT"
    outcome = {"EST-VISIT": "ISI", "EST-N1": "daily_sleep_quality", "EST-ESC-STAGE": "ISI",
               "EST-ESC-STRATEGY": "ISI", "EST-MRT": "proximal_support_reward",
               "EST-POLICY": "policy_value", "EST-INT": "interruption_vector"}[identifier]
    isi_based = outcome in ("ISI", "interruption_vector")
    pair = ("MED_A", "MED_B") if identifier == "EST-N1" else ("support_prompt", "no_prompt") if identifier in ("EST-MRT", "EST-POLICY") else ("behavioral_escalate", "behavioral_continue")
    return {"schema_version": "1.0.0", "synthetic": True, "kind": "estimand", "estimand_id": identifier,
            "estimand_version": "1.0.0", "population": "synthetic eligible fixture only", "eligibility_rule": ref("eligibility"),
            "history": "available_observed_preassignment_only", "observation_cutoff": "2026-10-01T07:59:59Z",
            "time_zero": "2026-10-01T08:00:00Z", "intervention": pair[0], "comparator": pair[1],
            "contrast": "assignment", "patient_blinded": False, "clinician_blinded": False,
            "outcome": outcome, "unit": "probability_vector" if interrupt else "ISI_points" if isi_based else "quality_points",
            "direction": "no_overall_order" if interrupt else "lower_is_better" if isi_based else "higher_is_better",
            "horizon": {"amount": 42 if identifier in ("EST-VISIT", "EST-INT") else 1,
                        "unit": "days" if identifier in ("EST-VISIT", "EST-INT", "EST-MRT") else "protocol_blocks" if identifier == "EST-N1" else "cohorts" if identifier == "EST-POLICY" else "protocol_stages",
                        "endpoint_rule": "day42" if identifier in ("EST-VISIT", "EST-INT") else "fixture-only versioned protocol endpoint",
                        "protocol": ref("fixture-protocol-not-an-accepted-run")},
            "continuation_policy": ref("common-continuation"), "support_policy": ref("fixed-support"),
            "intervention_strategy": ref("fixture-strategy-A") if identifier == "EST-ESC-STRATEGY" else None,
            "comparator_strategy": ref("fixture-strategy-B") if identifier == "EST-ESC-STRATEGY" else None,
            "intervention_policy": ref("fixture-target-policy-A") if identifier == "EST-POLICY" else None,
            "comparator_policy": ref("fixture-target-policy-B") if identifier == "EST-POLICY" else None,
            "policy_value_target": "fixed_contextual" if identifier == "EST-POLICY" else None,
            "event_strategies": [{"event": event, "strategy": "separate_survival_and_conditional_symptoms" if event == "death" else "separate_admission_and_conditional_symptoms" if event == "admission" else "treatment_policy", "explanation": "Canonical synthetic default; no common survivor or adherer restriction"}
                                 for event in ["death", "admission", "regimen_change", "steroid_change", "rescue", "discontinuation", "override"]],
            "missing_data_assumptions": ["explicit protocol sensitivity required"], "identification_assumptions": ["consistency, exchangeability and adequate support are assumptions"],
            "comparator_information": "same_permitted_history", "source_ids": ["iche9", "gformula"],
            "isi_instrument_version": "ISI-two-week-v1" if isi_based else None,
            "isi_recall_days": 14 if isi_based else None, "earliest_isi_days_after_assignment": 14 if isi_based else None,
            "limitations": ["Contract fixture, no clinical or causal validation"]}


class ContractTests(unittest.TestCase):
    def test_version_and_strict_types_reject_without_coercion(self):
        for patch in [{"schema_version": "2.0.0"}, {"synthetic": False}, {"sleep_quality": "7"}, {"sleep_quality": True}, {"sleep_quality": float("nan")}, {"unknown_field": 1}]:
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                parse(DailyReport, {**report(), **patch})

    def test_all_estimand_semantics_roundtrip(self):
        for identifier in ["EST-VISIT", "EST-N1", "EST-ESC-STAGE", "EST-ESC-STRATEGY", "EST-MRT", "EST-POLICY", "EST-INT"]:
            with self.subTest(identifier=identifier):
                value = parse(EstimandContract, estimand(identifier))
                self.assertEqual(value, EstimandContract.model_validate_json(value.model_dump_json()))

    def test_invalid_estimand_units_recall_and_event_strategy(self):
        cases = []
        for field, value in [("unit", "quality_points"), ("earliest_isi_days_after_assignment", 7), ("contrast", "per_protocol")]:
            cases.append({**estimand(), field: value})
        bad = estimand(); bad["event_strategies"][0]["strategy"] = "treatment_policy"; cases.append(bad)
        bad = estimand("EST-INT"); bad["direction"] = "lower_is_better"; cases.append(bad)
        bad = estimand(); bad["horizon"]["amount"] = 7; cases.append(bad)
        bad = estimand("EST-ESC-STRATEGY"); bad["comparator_strategy"] = bad["intervention_strategy"]; cases.append(bad)
        bad = estimand("EST-POLICY"); bad["policy_value_target"] = None; cases.append(bad)
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                parse(EstimandContract, payload)

    def test_cutoff_excludes_equal_time_late_and_future_records(self):
        payload = history([report("early"), report("equal", available="2026-10-02T08:00:00Z"), report("late", available="2026-10-03T08:00:00Z")])
        value = parse(ObservedHistory, payload)
        self.assertEqual([r.record_id for r in value.as_known_at(at("2026-10-02T08:00:00Z"))], ["early"])
        with self.assertRaises(ValidationError):
            parse(LearnerInput, {"schema_version": "1.0.0", "synthetic": True, "kind": "learner_input", "request": request(), "history": payload})

    def test_late_correction_does_not_rewrite_old_history_and_duplicates_drop(self):
        original = report()
        corrected = {**report("R2", available="2026-10-03T07:00:00Z"), "lineage_id": "R1", "revision": 2, "supersedes": "R1", "sleep_quality": 3.0}
        duplicate = {**report("R3", available="2026-10-04T07:00:00Z"), "duplicate_of": "R2", "sleep_quality": 3.0}
        value = parse(ObservedHistory, history([corrected, duplicate, original]))
        self.assertEqual([(r.record_id, r.sleep_quality) for r in value.as_known_at(at("2026-10-02T08:00:00Z"))], [("R1", 7.0)])
        self.assertEqual([(r.record_id, r.sleep_quality) for r in value.as_known_at(at("2026-10-05T08:00:00Z"))], [("R2", 3.0)])
        corrected["event_at"] = "2026-10-02T07:00:00Z"
        with self.assertRaises(ValidationError):
            parse(ObservedHistory, history([original, corrected]))

    def test_record_clock_naive_timezone_and_future_nested_covariate_rejected(self):
        for patch in [{"available_at": "2026-09-01T00:00:00Z"}, {"event_at": "2026-10-01T07:00:00"}]:
            with self.assertRaises(ValidationError): parse(DailyReport, {**report(), **patch})
        obs = {**record("observation"), "measure": {"concept": "pain", "value": 1.0, "unit": "dimensionless", "observed_at": "2026-10-03T00:00:00Z", "available_at": "2026-10-03T00:00:00Z"}, "lab_reference_context": None}
        with self.assertRaises(ValidationError):
            parse(LearnerInput, {"schema_version": "1.0.0", "synthetic": True, "kind": "learner_input", "request": request(), "history": history([obs])})

    def test_no_latent_or_truth_payload_can_enter_learner_schema(self):
        good = {"schema_version": "1.0.0", "synthetic": True, "kind": "learner_input", "request": request(), "history": history([report()])}
        parse(LearnerInput, good)
        for location in [good, good["request"]["context"], good["history"]["records"][0]]:
            bad = copy.deepcopy(good)
            target = bad if location is good else bad["request"]["context"] if location is good["request"]["context"] else bad["history"]["records"][0]
            target["latent_severity"] = 99.0
            with self.assertRaises(ValidationError): parse(LearnerInput, bad)
        bad = copy.deepcopy(good); bad["request"]["context"]["truth_access"] = "allowed"
        with self.assertRaises(ValidationError): parse(LearnerInput, bad)
        self.assertNotIn("SimulatorTruth", ADAPTERS["learner-input"].json_schema().get("$defs", {}))

    def test_isi_items_recall_trending_and_no_postdeath_isi(self):
        value = parse(ISIAssessment, isi()); self.assertEqual(value.total, 13)
        bad = isi(); bad["items"] = [0] * 6
        with self.assertRaises(ValidationError): parse(ISIAssessment, bad)
        bad = isi(); bad["recall_days"] = 30
        with self.assertRaises(ValidationError): parse(ISIAssessment, bad)
        other = isi(); other["instrument_version"] = "different-version"
        with self.assertRaises(ContractViolation): ensure_isi_comparable([value, parse(ISIAssessment, other)])
        death = {**record("intercurrent_event", "death", "2026-10-10T00:00:00Z"), "event_type": "death", "detail": "synthetic fixture"}
        with self.assertRaises(ValidationError): parse(ObservedHistory, history([death, isi()]))
        with self.assertRaises(ContractViolation): validate_isi_endpoint(value, parse(EstimandContract, estimand()))
        later = isi(event="2026-10-16T08:00:00Z")
        later["recall_start"] = "2026-10-02T08:00:00Z"
        validate_isi_endpoint(parse(ISIAssessment, later), parse(EstimandContract, estimand()))

    def test_missing_reward_is_not_zero(self):
        with self.assertRaises(ValidationError): parse(DailyReport, {**report(), "missingness": "pending"})
        empty = report(); empty.update({"missingness": "missing", "sleep_quality": None, "function": None, "diary_sleep_minutes": None, "burden": None})
        self.assertIsNone(parse(DailyReport, empty).sleep_quality)

    def test_stale_patient_history_hold_permissions_and_exclusions_block_approval(self):
        current, draft = parse(DecisionSnapshot, snapshot()), parse(Approval, approval(False))
        view = current.view; now = at("2026-10-01T08:00:00Z")
        validate_approval(draft, current, view, "doctor", now, None, [])
        cases = [("stale_approval", {**snapshot(), "state_version": 99}, view, "doctor"),
                 ("patient_mismatch", snapshot(), view.model_copy(update={"patient_id": "P2"}), "doctor"),
                 ("permission_denied", snapshot(), view, "nurse"),
                 ("historical_write", snapshot(), view.model_copy(update={"mode": "historical", "snapshot_id": "old"}), "doctor")]
        hold = snapshot(); hold["workflow"].update({"clinical": "clinical_hold", "hold_reasons": ["admission"]}); cases.append(("clinical_hold", hold, view, "doctor"))
        excluded = snapshot(); excluded["eligibility"][0]["status"] = "requires_prescriber_review"; cases.append(("ineligible_action", excluded, view, "doctor"))
        for code, current_payload, use_view, role in cases:
            with self.subTest(code=code), self.assertRaises(ContractViolation) as caught:
                validate_approval(draft, parse(DecisionSnapshot, current_payload), use_view, role, now, None, [])
            self.assertEqual(caught.exception.code, code)

    def test_component_consent_missing_expired_withdrawn_and_simultaneous_withdrawal(self):
        current, draft = parse(DecisionSnapshot, snapshot()), parse(Approval, approval())
        now = at("2026-10-01T08:00:00Z")
        validate_approval(draft, current, current.view, "doctor", now, "nof1", [parse(Consent, consent())])
        cases = [[], [parse(Consent, consent("escalation"))]]
        for field, value in [("consent_status", "expired"), ("oversight_status", "pending"), ("expires_at", "2026-10-01T07:30:00Z")]:
            cases.append([parse(Consent, {**consent(), field: value})])
        withdrawn = {**consent(), "record_id": "C2", "lineage_id": "C1", "revision": 2, "supersedes": "C1", "recorded_at": "2026-10-01T08:00:00Z", "available_at": "2026-10-01T08:00:00Z", "consent_status": "withdrawn", "withdrawn_at": "2026-10-01T08:00:00Z"}
        cases.append([parse(Consent, consent()), parse(Consent, withdrawn)])
        for records in cases:
            with self.assertRaises(ContractViolation) as caught:
                validate_approval(draft, current, current.view, "doctor", now, "nof1", records)
            self.assertEqual(caught.exception.code, "consent_unavailable")

    def test_protocol_approval_does_not_preselect_randomized_winner(self):
        self.assertIsNone(parse(Approval, approval()).option)
        draft, current = parse(Approval, approval()), parse(DecisionSnapshot, snapshot())
        assignment = {**record("assignment", "A1", "2026-10-01T08:00:01Z"), "decision_id": "D1", "approval_id": "APP1", "option": "MED_B", "experimental": True, "component": "nof1", "probability": 0.5, "seed": seed(), "support_policy": ref("support-fixed"), "patient_blinded": False, "clinician_blinded": False, "clinician_override": None, "override_reason": None}
        validate_assignment(parse(Assignment, assignment), draft, current, current.view, "doctor", [parse(Consent, consent())])
        for patch in [{"probability": None}, {"component": "mrt_bandit"}, {"probability": 0.0}]:
            with self.assertRaises(ValidationError): parse(Assignment, {**assignment, **patch})
        with self.assertRaises(ValidationError): parse(Approval, {**approval(), "option": "MED_A"})

    def test_support_freeze_cannot_drift_during_block_or_washout(self):
        for state in ["nof1_block", "nof1_washout"]:
            payload = snapshot(); payload["workflow"].update({"learning": state, "support_mode": "adaptive"})
            with self.assertRaises(ValidationError): parse(DecisionSnapshot, payload)
            payload["workflow"]["support_mode"] = "frozen"; parse(DecisionSnapshot, payload)

    def test_fit_versions_and_hashes_rejected_before_dispatch(self):
        value = parse(FitRequest, request())
        accepted = [v for v in value.context.__dict__.values() if hasattr(v, "sha256")] + [value.configuration]
        validate_fit_request(value, accepted)
        for path in ["estimand", "input_data", "prior", "model"]:
            bad = request(); bad["context"][path]["version"] = "unsupported"
            with self.assertRaises(ContractViolation) as caught: validate_fit_request(parse(FitRequest, bad), accepted)
            self.assertEqual(caught.exception.code, "unsupported_input_version")
        for patch in [{"sampler": "nutpie"}, {"backend": "stan"}, {"precision": "float32"}]:
            with self.assertRaises(ValidationError): parse(FitRequest, {**request(), **patch})

    def test_typed_fit_metadata_roundtrip_and_failure(self):
        data = {"backend": "pymc", "backend_version": "fixture-not-installed-PyMC", "sampler": "native_nuts", "sampler_version": "fixture-version", "packages": {"pymc": "fixture-version"}, "precision": "float64", "status": "failed", "diagnostics_artifacts": [], "failure_reason": "fixture: no fit was run"}
        value = parse(FitMetadata, data)
        self.assertEqual(data, json.loads(value.model_dump_json()))
        with self.assertRaises(ValidationError): parse(FitMetadata, {**data, "failure_reason": None})
        with self.assertRaises(ValidationError): parse(FitMetadata, {**data, "status": "accepted", "failure_reason": None})

    def test_est_int_zero_denominator_and_tradeoffs_remain_separate(self):
        outcome = {"action": "MED_A", "survival_day42": 0.8, "admission_by_day42": 0.3, "alive_outpatient_day42": 0.0, "conditional_isi": {"numerator_count": 0, "denominator_count": 10, "conditioning_probability": 0.0, "isi": {"status": "undefined", "reason": "no alive outpatients"}}, "death_times_days": [2.0, 5.0], "admission_times_days": [3.0]}
        payload = {"schema_version": "1.0.0", "synthetic": True, "kind": "interruption_result", "estimand_id": "EST-INT", "estimand_version": "1.0.0", "horizon_days": 42, "intervention": outcome, "comparator": {**copy.deepcopy(outcome), "action": "MED_B"}, "interpretation": "intervention_specific_conditional_populations_not_common_survivors", "overall_ranking": "suppressed"}
        parse(InterruptionResult, payload)
        bad = copy.deepcopy(payload); bad["intervention"]["conditional_isi"]["isi"] = {"status": "estimated", "value": 0.0, "unit": "ISI_points", "standard_error": None, "interval": None}
        with self.assertRaises(ValidationError): parse(InterruptionResult, bad)
        with self.assertRaises(ValidationError): parse(InterruptionResult, {**payload, "overall_winner": "MED_A"})

    def test_external_study_ipd_summary_double_count_denied(self):
        data = {"schema_version": "1.0.0", "synthetic": True, "kind": "external_study", "study": ref("study"), "population": "synthetic fixture", "intervention": "behavioral", "comparator": "usual", "outcome": "ISI", "scale": "ISI_points", "follow_up_days": 42, "likelihood_input": "summary", "effect": -1.0, "standard_error": 0.5, "ipd": None, "covariate_distribution": [], "blinding": "open_label", "bias_transport_notes": ["not real literature effect"], "rationale_source_ids": ["iche9"]}
        parse(ExternalStudy, data)
        with self.assertRaises(ValidationError): parse(ExternalStudy, {**data, "ipd": ref("same-study-ipd")})

    def test_temporal_parent_graph_and_seeded_future_cycle_faults(self):
        data = json.loads((ROOT / "contracts/domain/temporal-v1.json").read_text())
        value = parse(TemporalContract, data)
        variables = {v.id: v for v in value.variables}
        self.assertIn(("visit_assignment", -1), [(p.variable, p.day_offset) for p in variables["clinical_L"].parents])
        self.assertNotIn("random_intercept", [p.variable for p in variables["visit_assignment"].parents])
        self.assertEqual(variables["clinical_L"].postassignment_role_by_estimand["EST-VISIT"], "mediator")
        for parent in [{"variable": "severity", "day_offset": 0}, {"variable": "clinical_L", "day_offset": 1}, {"variable": "unknown", "day_offset": -1}]:
            bad = copy.deepcopy(data); next(v for v in bad["variables"] if v["id"] == "clinical_L")["parents"].append(parent)
            with self.assertRaises(ValidationError): parse(TemporalContract, bad)

    def test_evaluation_minimums_truth_precision_and_source_boundary(self):
        for tier, too_few in [("smoke", 4), ("sbc", 999), ("recovery", 999), ("decision_null", 1999), ("integrated_policy", 999)]:
            with self.assertRaises(ValidationError): parse(EvaluationCell, {"id": "cell", "scenario": ref(), "estimand": ref(), "patients": 60, "tier": tier, "repetitions": too_few})
        truth = {"schema_version": "1.0.0", "synthetic": True, "kind": "truth_result", "estimand": ref(), "method": "analytic", "estimate": {"status": "estimated", "value": -1.0, "unit": "quality_points", "standard_error": None, "interval": None}, "numerical_standard_error": 0.0, "information_set": "evaluator_only_structural_system", "privileged_information": True, "dgp": ref(), "seed": seed(), "draws": 0, "independent_implementation": ref("analytic-fixture")}
        parse(TruthResult, truth)
        with self.assertRaises(ValidationError): parse(TruthResult, {**truth, "method": "numerical"})
        with self.assertRaises(ValidationError): parse(TruthResult, {**truth, "numerical_standard_error": 0.1})
        source = {"schema_version": "1.0.0", "synthetic": True, "kind": "evidence_record", "source_id": "iche9", "bibliography": "fixture locator, not a new evidence verification", "year": 2019, "url": "https://example.invalid/fixture", "doi": None, "evidence_type": "real_literature_rationale", "source_version": "fixture", "supported_claim": "estimand rationale", "limitations": ["not quantitative synthetic likelihood"], "locator": "fixture", "verified_at": None, "verification_status": "unverified", "consuming_requirements": ["CONTRACT-01"], "role": "rationale_only"}
        parse(EvidenceRecord, source)
        with self.assertRaises(ValidationError): parse(EvidenceRecord, {**source, "role": "synthetic_likelihood"})

    def test_schema_exports_match_and_contain_no_evaluator_types_in_learner(self):
        for relative, content in products().items():
            self.assertEqual(json.loads((ROOT / "contracts/domain" / relative).read_text()), content)
        for name in ["learner-input", "observed-records", "fit-request"]:
            definitions = ADAPTERS[name].json_schema().get("$defs", {})
            self.assertFalse({"TruthResult", "SimulatorTruth", "ParameterSpec", "DGPConfig"} & definitions.keys())

    def test_all_entity_fixtures_and_registered_estimands_are_serializable(self):
        fixtures = json.loads((ROOT / "tests/contracts/fixtures/observed-entities-v1.json").read_text())
        expected = {"patient", "consent", "encounter", "medication_order", "medication_exposure", "observation", "intercurrent_event", "oura_like", "daily_report", "isi", "decision_snapshot", "recommendation", "approval", "assignment", "delivery", "follow_up", "audit_run"}
        self.assertEqual({r["kind"] for r in fixtures["records"]}, expected)
        for payload in fixtures["records"]:
            with self.subTest(kind=payload["kind"]):
                parsed = ADAPTERS["observed-records"].validate_json(json.dumps(payload))
                self.assertEqual(parsed, ADAPTERS["observed-records"].validate_json(parsed.model_dump_json()))
        registry = json.loads((ROOT / "contracts/domain/estimand-registry-v1.json").read_text())
        estimands = json.loads((ROOT / "tests/contracts/fixtures/estimands-v1.json").read_text())["contracts"]
        self.assertEqual({r["id"] for r in registry["contracts"]}, {e["estimand_id"] for e in estimands})
        for payload in estimands:
            parse(EstimandContract, payload)

    def test_dgp_interface_requires_explicit_initial_visit_and_parameter_contracts(self):
        data = {"schema_version": "1.0.0", "synthetic": True, "kind": "dgp_config", "dgp": ref("fixture-dgp"), "layer": "analytic", "scenario": ref("fixture-scenario"), "patients": 1, "external_study_sizes": [], "start_day": 0, "end_day": 1, "initialized_day": -1, "time_grid_unit": "days", "temporal_contract": ref("TIME-01"), "equations": ref("fixture-equations"), "parameter_table": [{"symbol": "fixture_constant", "unit": "dimensionless", "value": 0.0, "distribution": "fixture-only constant", "provenance": "synthetic_engineering", "rationale": "interface fixture, not reference DGP acceptance"}], "initial_distribution": ref("fixture-initial"), "irregular_visit_process": ref("fixture-visits"), "observation_rules": ref("fixture-observation"), "learner_export_schema": ref("observed-records"), "seed_namespaces": [seed()], "clinical_interpretation": "synthetic_not_clinically_calibrated"}
        parse(DGPConfig, data)
        for key in ["initial_distribution", "irregular_visit_process", "parameter_table"]:
            bad = copy.deepcopy(data); del bad[key]
            with self.assertRaises(ValidationError): parse(DGPConfig, bad)

    def test_evaluation_accounting_failure_and_confirmation_contracts(self):
        cell = {"id": "fixture-cell", "scenario": ref(), "estimand": ref(), "patients": 1, "tier": "deterministic", "repetitions": 1}
        protocol = {"schema_version": "1.0.0", "synthetic": True, "kind": "evaluation_protocol", "protocol": ref("fixture-protocol"), "locked_at": "2026-10-01T00:00:00Z", "cells": [cell], "metrics": ["fixture boundary check"], "thresholds": [ref("fixture-threshold")], "development_namespace": "fixture-development", "confirmation_namespace": "fixture-confirmation", "model": ref(), "prior": ref(), "decision": ref(), "failure_handling": "retain_all_attempted_completed_failed_abstained_undefined_pending_counts", "checkpoint_commands": ["fixture-only command; no simulation executed"]}
        parse(EvaluationProtocol, protocol)
        with self.assertRaises(ValidationError): parse(EvaluationProtocol, {**protocol, "confirmation_namespace": "fixture-development"})
        evidence = {"schema_version": "1.0.0", "synthetic": True, "kind": "gate_evidence", "requirement_ids": ["CONTRACT-01"], "input_versions": [ref()], "executed_checks": ["hand-authored fixture only"], "commands": ["contract fixture"], "manifests": [ref()], "attempted": 2, "completed": 1, "failed": 1, "abstained": 0, "undefined": 0, "pending": 0, "failures": ["retained fixture failure"], "reviewer_disposition": "pending", "claim_limits": ["no app or statistical acceptance"]}
        parse(GateEvidence, evidence)
        with self.assertRaises(ValidationError): parse(GateEvidence, {**evidence, "failed": 0})
        failed = {"backend": "pymc", "backend_version": "fixture", "sampler": "native_nuts", "sampler_version": "fixture", "packages": {"pymc": "fixture"}, "precision": "float64", "status": "failed", "diagnostics_artifacts": [], "failure_reason": "fixture no fit"}
        result = {"schema_version": "1.0.0", "synthetic": True, "kind": "replicate_result", "run_id": "fixture", "replicate_id": "fixture-0", "input_versions": [ref()], "seeds": [seed()], "attempted_fit": True, "fit": failed, "estimate": {"status": "failed", "reason": "fixture only"}, "truth_ref": None, "assignment_refs": [], "executed_propensities": [], "outcome_refs": [], "violations": [], "execution_seconds": 0.0, "peak_memory_bytes": 0, "failure_reason": "fixture failure retained"}
        parse(ReplicateResult, result)
        with self.assertRaises(ValidationError): parse(ReplicateResult, {**result, "estimate": {"status": "estimated", "value": 0.0, "unit": "ISI_points", "standard_error": None, "interval": None}})

    def test_named_threshold_is_provisional_and_no_unit_substitution(self):
        threshold = {"schema_version": "1.0.0", "synthetic": True, "kind": "threshold", "id": "fixture-benefit", "parameter_version": "fixture-only", "value": 1.0, "unit": "ISI_points", "provenance": "provisional_synthetic_engineering", "clinical_review": "deferred", "rationale": "fixture validation only; no threshold selected"}
        parse(NamedThreshold, threshold)
        with self.assertRaises(ValidationError): parse(NamedThreshold, {**threshold, "clinical_review": "accepted"})
        data = json.loads((ROOT / "tests/contracts/fixtures/observed-entities-v1.json").read_text())
        observation = next(r for r in data["records"] if r["kind"] == "observation")
        observation["measure"]["unit"] = "minutes"
        with self.assertRaises(ValidationError): ADAPTERS["observed-records"].validate_json(json.dumps(observation))


if __name__ == "__main__":
    unittest.main()
