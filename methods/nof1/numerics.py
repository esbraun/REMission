"""Prespecified N quality integration gates, independent of visit endpoint/config."""
import time

import numpy as np

from contracts.domain.nof1_config import configuration
from .rollout import simulate, validate_draws


def integration_bounds(batches, *, settings, deadline=None):
    """Whole20-draw within-chain bootstrap carrying all eight batch results."""
    batches = np.asarray(batches, dtype=np.float64)
    if batches.ndim != 3 or not np.all(np.isfinite(batches)):
        raise ValueError("finite chain/draw/batch array required")
    chains, draws, count = batches.shape
    block = settings["bootstrap_block"]
    if count != 8 or draws < block or draws % block:
        raise ValueError("eight batches and whole within-chain20-draw blocks required")
    delta, v = batches.mean(axis=-1), batches.var(axis=-1, ddof=1) / 8
    m, nb = delta.size, draws // block
    sums = np.stack([delta.reshape(chains, nb, block).sum(-1),
        (delta ** 2).reshape(chains, nb, block).sum(-1), v.reshape(chains, nb, block).sum(-1)], axis=-1)
    rng = np.random.default_rng(settings["bootstrap_seed"])
    upper, lower = [], []
    for _ in range(settings["bootstrap_resamples"]):
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError("whole-integration-deadline")
        selected = sums[np.arange(chains)[:, None], rng.integers(nb, size=(chains, nb))].sum(axis=(0, 1))
        vbar = selected[2] / m
        s2 = (selected[1] - selected[0] ** 2 / m) / (m - 1)
        upper.append(vbar)
        lower.append(max(0., s2 - vbar))
    U, L = float(np.quantile(upper, .95)), float(np.quantile(lower, .05))
    se, floor = float(np.sqrt(U / m)), settings["sd_floor"]
    return dict(U=U, L=L, residual_variance=float(v.mean()), raw_effect_variance=float(delta.var(ddof=1)),
        uninflated_effect_variance=max(0., float(delta.var(ddof=1) - v.mean())), mean_integration_se=se,
        variance_pass=bool(U <= settings["relative_variance"] * max(L, floor ** 2)),
        mean_pass=bool(se <= min(settings["mean_se"], .1 * max(np.sqrt(L), floor))))


def _peak_rss_mib():
    # Numerical jobs run in the pinned Linux container; ru_maxrss is KiB there.
    import resource
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)


def integrate(draws, *, seed, stage=lambda value: None, seconds=None):
    """Expected effect per joint draw, with a separate singleton target axis.

    Future process/measurement randomness is averaged WITHIN each draw. Eight
    batch means quantify its residual error. No predictive interval is emitted.
    Only a shorter deadline may be supplied; all numerical gates remain fixed.
    """
    validate_draws(draws)
    settings = configuration(draws.purpose)
    cap = settings["integration_seconds"] if seconds is None else seconds
    if not 0 < cap <= settings["integration_seconds"]:
        raise ValueError("integration deadline must be positive and within frozen cap")
    shape = draws.parameters["b"].shape
    if shape[1] % settings["bootstrap_block"]:
        raise ValueError("whole chain bootstrap blocks required")
    started, deadline = time.monotonic(), time.monotonic() + cap
    flat = {k: np.asarray(v).reshape(-1) for k, v in draws.parameters.items()}
    m = flat["b"].size
    streams = [[np.random.default_rng(np.random.SeedSequence([seed, i, batch, 8101])) for batch in range(8)] for i in range(m)]
    totals = np.zeros((m, 8))
    previous, reports, n = None, [], 0

    def result(delta, status, reason=None):
        return (None if delta is None else delta[..., None]), dict(status=status, reason=reason, attempted=reports,
            seconds=time.monotonic() - started, peak_rss_mib=_peak_rss_mib(), cap_seconds=cap,
            target_ids=[draws.target_id], axes=["chain", "draw", "target"], unit="quality_points",
            kind="conditional_expected_assignment_contrast", history_state="retained exposure/rebound/current AR",
            bootstrap=dict(resamples=settings["bootstrap_resamples"], block=settings["bootstrap_block"], seed=settings["bootstrap_seed"]),
            seed=seed, inner_domain=8101, memory="stream eight batches one posterior draw at a time")

    k = settings["initial_k"]
    while k <= settings["max_k"]:
        add = k // 8 - n
        for i in range(m):
            if time.monotonic() > deadline:
                reports.append(dict(K=k, status="interrupted", completed_outer_draws=i))
                return result(None, "numerical-precision-unmet", "whole-integration-deadline")
            theta = {key: value[i] for key, value in flat.items()}
            for batch, rng in enumerate(streams[i]):
                quality = simulate(theta, draws, rng, add)
                totals[i, batch] += (quality[:, 0] - quality[:, 1]).mean(axis=-1).sum()
        n = k // 8
        batches = (totals / n).reshape(*shape, 8)
        delta = batches.mean(axis=-1)
        try:
            bounds = integration_bounds(batches, settings=settings, deadline=deadline)
        except TimeoutError:
            reports.append(dict(K=k, status="precision-checks-interrupted"))
            return result(None, "numerical-precision-unmet", "whole-integration-deadline")
        summary = np.array([delta.std(ddof=1), *np.quantile(delta, [.025, .975])])
        tolerance = max(settings["absolute_stability"], settings["relative_stability"] * np.sqrt(bounds["L"]))
        change = None if previous is None else np.abs(summary - previous)
        stable = change is not None and bool(np.all(change <= tolerance))
        record = dict(K=k, **bounds, sd=float(summary[0]), interval=summary[1:].tolist(),
            changes=None if change is None else change.tolist(), stability_tolerance=tolerance,
            stability_pass=stable, seconds=time.monotonic() - started, peak_rss_mib=_peak_rss_mib())
        reports.append(record)
        stage(dict(stage="rollouts", K=k, checks=record))
        if time.monotonic() > deadline:
            return result(None, "numerical-precision-unmet", "whole-integration-deadline")
        if bounds["variance_pass"] and bounds["mean_pass"] and stable:
            return result(delta, "accepted")
        previous, k = summary, k * 2
    return result(None, "numerical-precision-unmet", "rollout-cap")
