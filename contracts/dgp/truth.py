"""Independent Layer A answers and contract-level numerical truth controls.

This module contains no longitudinal generator, fit or learner prediction code.
It is evaluator-only. Layer B rollouts and actual calibration are G1 work.
"""
from hashlib import sha256
import json
from math import exp, isfinite

VERSION = "1.0.0"


def expit(x: float) -> float:
    return 1 / (1 + exp(-x))


def normal_posterior(total_y: float, n: int = 20) -> tuple[float, float]:
    if n <= 0 or not isfinite(total_y):
        raise ValueError("finite observations and positive n required")
    variance = 1 / (1 / 4 + n)
    return variance * total_y, variance


def beta_posterior(k: int, n: int = 20) -> tuple[int, int]:
    if type(k) is not int or type(n) is not int or not 0 <= k <= n:
        raise ValueError("binomial counts required")
    return 2 + k, 3 + n - k


def two_period(a0: int, a1: int) -> float:
    """Enumerate L0,L1 under fixed assignments, integrating zero-mean error."""
    if a0 not in (0, 1) or a1 not in (0, 1):
        raise ValueError("binary regime required")
    value = 0.0
    for l0 in (0, 1):
        p = expit(-1 + 0.8 * l0 + 0.7 * a0)
        for l1 in (0, 1):
            mass = 0.5 * (p if l1 else 1 - p)
            value += mass * (l0 + l1 - a0 - 2 * a1)
    return value


def ordinal_expectation(severity: float, offsets: tuple[float, ...] = (0.0,)) -> float:
    # Tail-sum identity. Item dependence never changes a sum's expectation.
    return sum(expit(severity + offset - cut) for offset in offsets
               for cut in (-1.5, -0.5, 0.5, 1.5))


def escalation(a0: int, nonresponder_action: int, *, observational: bool = False,
               flip: float = 0.0, sparse_response: float | None = None) -> float:
    """Enumerate X,true response,classifier noise under an intervened regime.

    Only observed nonresponders receive action b. Classification does not alter
    true response or erase durable treatment. The outcome uses true response.
    """
    if a0 not in (0, 1) or nonresponder_action not in (0, 1) or not 0 <= flip <= 1:
        raise ValueError("invalid regime/classification probability")
    if sparse_response is not None and not 0 <= sparse_response <= 1:
        raise ValueError("invalid sparse response probability")
    result = 0.0
    for x in (0, 1):
        p_response = 0.3 + 0.2 * a0 + 0.2 * x if observational else 0.4 + 0.2 * a0
        for response in (0, 1):
            p_r = p_response if response else 1 - p_response
            # In sparse fixture an independently observed classification is 90%
            # responder. It is not falsely called the latent response rate.
            p_label1 = sparse_response if sparse_response is not None else (1 - flip if response else flip)
            for label in (0, 1):
                mass = 0.5 * p_r * (p_label1 if label else 1 - p_label1)
                a1 = nonresponder_action if label == 0 else 0
                outcome = 2 + a0 + response + 2 * (1 - response) * a1 + (x if observational else 0)
                result += mass * outcome
    return result


def fixture_manifest() -> dict:
    return {"version": VERSION, "synthetic": True,
            "information": "evaluator_only_analytic_not_learner_predictions",
            "fixtures": {
                "normal": {"prior": [0, 2], "likelihood_sd": 1, "n": 20, "sum_y": 10,
                           "truth_mean": 40 / 81, "truth_variance": 4 / 81},
                "beta": {"prior": [2, 3], "n": 20, "k": 8, "truth_shape": [10, 15]},
                "constant": {"equation": "X~N(0,1);A~Bernoulli(.5);Y=1+X-A+N(0,1)", "n": 200, "ATE": -1},
                "modifier": {"equation": "M~Bernoulli(.5);X~N(0,1);Y=1+X+A*(2*M-1)+N(0,1)", "CATE_M0": -1, "CATE_M1": 1, "ATE": 0},
                "two_period": {"assignment": "p(A0)=expit(-.5+.5*L0);p(A1)=expit(-.5+.8*L1+.2*A0)",
                               "transition": "L0~Bernoulli(.5);p(L1)=expit(-1+.8*L0+.7*A0)",
                               "outcome": "Y=L0+L1-A0-2*A1+N(0,1)",
                               "regime_values": {f"{a}{b}": two_period(a, b) for a in (0, 1) for b in (0, 1)}},
                "ordinal": {"cutpoints": [-1.5, -0.5, 0.5, 1.5], "single_item_at0": 2.0,
                            "single_item_at1": ordinal_expectation(1), "seven_equal_at0": 14.0},
                "contextual_policy": {"equation": "M~Bernoulli(.5);reward=1+A*(2*M-1)+N(0,1)",
                                      "logging_p": 0.5, "no_action": 1, "always_action": 1, "A_equals_M": 1.5},
                "escalation_randomized": {"response": "p=.4+.2*A0", "A0_p": 0.5, "A1_nonresponder_p": 0.5,
                                          "Y": "2+A0+R+2*(1-R)*A1+N(0,1)",
                                          "regime_values": {f"{a}{b}": escalation(a, b) for a in (0, 1) for b in (0, 1)}},
                "escalation_observational": {"X_p": 0.5, "A0_p": ".2+.6*X", "response": ".3+.2*A0+.2*X",
                                            "A1_nonresponder_p": 0.5, "Y": "2+A0+R+2*(1-R)*A1+X+N(0,1)",
                                            "regime_values": {f"{a}{b}": escalation(a, b, observational=True) for a in (0, 1) for b in (0, 1)}}}}


def truth_status(mcse: float, estimator_se: float, unit: str, *, batches: int,
                 cap: int, analytic: bool = False) -> str:
    if (not all(isfinite(v) and v >= 0 for v in (mcse, estimator_se))
            or type(batches) is not int or type(cap) is not int or not 0 <= batches <= cap or cap <= 0):
        raise ValueError("invalid precision/budget")
    absolute = {"ISI_points": 0.05, "quality_points": 0.01}[unit]
    if analytic:
        if mcse != 0:
            raise ValueError("analytic truth must have zero MCSE")
        return "resolved"
    if estimator_se == 0:
        return "unresolved_zero_target_se"
    if batches > 0 and mcse <= min(absolute, 0.1 * estimator_se):
        return "resolved"
    return "inconclusive" if batches == cap else "continue_independent_batches"


def seed_words(*, protocol: str, phase: str, namespace: str, scenario: str,
               replicate: int, patient: str, time_index: int, process: str,
               stream: str, root_seed: int) -> list[int]:
    """SHA256 canonical key -> eight little-endian uint32 SeedSequence words.

    Future G1 uses NumPy Generator(PCG64DXSM(SeedSequence(words))) and records
    the qualified NumPy version. Subdraw names, not draw-count offsets, branch.
    """
    if namespace not in {"generation", "assignment", "measurement", "missingness", "fitting", "posterior_rollout", "truth"}:
        raise ValueError("unknown independent stream namespace")
    if phase not in {"fixture", "calibration", "pilot", "smoke", "development", "confirmation"}:
        raise ValueError("unknown execution phase")
    if (any(not isinstance(v, str) or not v for v in (protocol, scenario, patient, process, stream))
            or type(replicate) is not int or replicate < 0 or type(time_index) is not int
            or type(root_seed) is not int or root_seed < 0):
        raise ValueError("complete typed seed key required")
    payload = ["remission-seed-v1", root_seed, protocol, phase, namespace, scenario,
               replicate, patient, time_index, process, stream]
    digest = sha256(json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")).digest()
    return [int.from_bytes(digest[i:i + 4], "little") for i in range(0, 32, 4)]


def bisect_calibration(mean_at, target: float, *, lower: float, upper: float,
                       tolerance: float, iterations: int, increasing: bool) -> dict:
    """Deterministic solver on a separately fixed calibration sample/CRN rollout.

    Caller supplies independent sample and achieved-rate uncertainty; this pure
    routine cannot claim that a rate or source contrast was empirically reached.
    """
    if (not all(isfinite(v) for v in (target, lower, upper, tolerance))
            or lower >= upper or tolerance <= 0 or type(iterations) is not int or iterations <= 0):
        raise ValueError("invalid calibration request")
    low_value, high_value = mean_at(lower), mean_at(upper)
    if not all(isfinite(v) for v in (low_value, high_value)):
        raise ValueError("nonfinite calibration response")
    if not min(low_value, high_value) <= target <= max(low_value, high_value):
        return {"status": "infeasible", "target": target}
    if (increasing and low_value > high_value) or (not increasing and low_value < high_value):
        raise ValueError("calibration monotonicity declaration mismatch")
    for step in range(1, iterations + 1):
        midpoint = (lower + upper) / 2
        achieved = mean_at(midpoint)
        if not isfinite(achieved):
            raise ValueError("nonfinite calibration response")
        if abs(achieved - target) <= tolerance:
            return {"status": "solved", "coefficient": midpoint, "achieved": achieved, "target": target, "iterations": step}
        if (achieved < target) == increasing:
            lower = midpoint
        else:
            upper = midpoint
    return {"status": "inconclusive", "target": target, "achieved": achieved, "iterations": iterations}
