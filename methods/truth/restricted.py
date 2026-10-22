"""Independent resample/move integration of the restricted v1 observed H* law.

No generator keys, realized patient effects, learner model or prediction code is
used. A single filter is exploratory: rollout MCSE is not conditioning accuracy.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import math
import time
from typing import Callable

import numpy as np
from scipy.signal import lfilter
from scipy.special import log_ndtr, logsumexp, ndtr

from contracts.domain.analysis import AnalysisHistory, sha


@dataclass(frozen=True)
class Law:
    baseline: tuple[float, float] = (16., 22.)
    response: tuple[float, float] = (.8, 1.2)
    rho: float = .55
    innovation_sd: float = .8
    phase_amplitude: float = .55
    continue_effect: float = 2.
    escalate_effect: float = 4.
    adherence: float = .85
    quality_sd: float = .45
    isi_sd: float = 1.

    def __post_init__(self):
        values = (*self.baseline, *self.response, self.rho, self.innovation_sd,
                  self.phase_amplitude, self.continue_effect, self.escalate_effect,
                  self.adherence, self.quality_sd, self.isi_sd)
        if (not all(math.isfinite(x) for x in values) or
                self.baseline[0] > self.baseline[1] or self.response[0] > self.response[1]
                or abs(self.rho) >= 1 or min(self.innovation_sd, self.quality_sd, self.isi_sd) <= 0
                or not 0 <= self.adherence <= 1):
            raise ValueError('invalid distributional law')


V1 = Law()


@dataclass(frozen=True)
class Problem:
    """Numerical seam also used by small independently integrable overlap cases.

    Real histories can only enter through compile_history. ISI entries are
    (last index, total, recall length); each is ONE measurement of shared burden.
    Gaussian entries are solely an unrounded linear-Gaussian overlap check.
    """
    nights: tuple[int, ...]
    continue_state: tuple[float, ...]
    escalate_state: tuple[float, ...]
    quality: tuple[tuple[int, float], ...] = ()
    isi: tuple[tuple[int, int, int], ...] = ()
    gaussian: tuple[tuple[int, float, float], ...] = ()
    constant_log_probability: float = 0.

    def __post_init__(self):
        n = len(self.nights)
        if (not n or len(self.continue_state) != n or len(self.escalate_state) != n
                or any(b != a+1 for a, b in zip(self.nights, self.nights[1:]))
                or not all(math.isfinite(x) and 0 <= x <= 1
                           for x in (*self.continue_state, *self.escalate_state))):
            raise ValueError('invalid complete state grid')
        seen = set()
        for i, q in self.quality:
            if not 0 <= i < n or not math.isfinite(q) or not 0 <= q <= 10 or abs(q*1000-round(q*1000)) > 1e-8 or ('q', i) in seen:
                raise ValueError('invalid quality observation')
            seen.add(('q', i))
        for i, total, width in self.isi:
            if type(total) is not int or not 0 <= total <= 28 or not 1 <= width <= i+1 or i >= n or ('i', i) in seen:
                raise ValueError('invalid single ISI observation/recall')
            seen.add(('i', i))
        for i, y, sd in self.gaussian:
            if not 0 <= i < n or not math.isfinite(y) or not math.isfinite(sd) or sd <= 0:
                raise ValueError('invalid Gaussian overlap observation')


def compile_history(history: AnalysisHistory) -> Problem:
    """Revalidate strict typed resolved deliveries and available-at lineage.

    Revalidation prevents model_construct/mutated instances bypassing admission.
    Excluded public fields are errors, as are seeds/private paths in input JSON.
    """
    if not isinstance(history, AnalysisHistory):
        raise TypeError('strict reduced AnalysisHistory required')
    history = AnalysisHistory.model_validate_json(history.model_dump_json())
    if history.origin != datetime(2026, 1, 1, 12, tzinfo=timezone.utc):
        raise ValueError('v1 public origin must be January 1 2026 noon UTC')
    day = (history.cutoff-history.origin).days
    nights = tuple(range(-13, day+1))
    deliveries = {int((r.event_at-history.origin-timedelta(hours=8)).total_seconds()/86400)+1: r
                  for r in history.records if r.kind == 'delivery'}
    c = e = 0.
    cs, es = [], []
    for night in nights:
        d = deliveries.get(night)
        c = .65*c+.35*int(d is not None and d.stage == 'taken' and d.option == 'behavioral_continue')
        e = .8*e+.2*int(d is not None and d.stage == 'taken' and d.option == 'behavioral_escalate')
        cs.append(c); es.append(e)
    quality, isi = [], []
    constant = 0.
    for r in sorted(history.records, key=lambda r: (r.event_at, r.record_id)):
        if r.kind == 'daily_report':
            night = (r.event_at+timedelta(minutes=1)-history.origin).days
            if r.missingness == 'observed':
                quality.append((night+13, r.sleep_quality))
                constant += math.log(.9)
            elif r.missingness == 'missing':
                constant += math.log(.1)
            # Pending observations add no fabricated measurement likelihood.
        elif r.kind == 'isi':
            night = (r.recall_end+timedelta(hours=1)-history.origin).days
            isi.append((night+13, r.total, 14))
        elif r.kind == 'delivery':
            constant += math.log(.85 if r.stage == 'taken' else .15)
    return Problem(nights, tuple(cs), tuple(es), tuple(sorted(quality)), tuple(sorted(isi)),
                   constant_log_probability=constant)


def normal_bin_logmass(value, mean, sd: float, step: float, upper: float):
    """Float64 CDF/survival interval difference, including both clipping tails."""
    if sd <= 0 or step <= 0 or upper <= 0:
        raise ValueError('invalid measurement scale')
    value, mean = np.broadcast_arrays(np.asarray(value, float), np.asarray(mean, float))
    if np.any(~np.isfinite(value)) or np.any(~np.isfinite(mean)) or np.any((value < 0) | (value > upper)):
        raise ValueError('nonfinite/out-of-range measurement')
    lo = np.where(value == 0, -np.inf, (value-step/2-mean)/sd)
    hi = np.where(value == upper, np.inf, (value+step/2-mean)/sd)
    # Difference of upper tails in the right half avoids subtracting near-one CDFs.
    use_sf = lo >= 0
    large = np.where(use_sf, log_ndtr(-lo), log_ndtr(hi))
    small = np.where(use_sf, log_ndtr(-hi), log_ndtr(lo))
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        answer = large+np.log(-np.expm1(small-large))
    return answer


def residuals(innovations, law=V1):
    # e[-14]=0: the FIRST random innovation belongs to night -13.
    return lfilter([law.innovation_sd], [1., -law.rho], innovations, axis=1)


def burden(problem: Problem, b, r, innovations, law=V1):
    n = innovations.shape[1]
    state = residuals(innovations, law)
    phase = law.phase_amplitude*np.sin(2*np.pi*np.asarray(problem.nights[:n])/21)
    treatment = law.continue_effect*np.asarray(problem.continue_state[:n])+law.escalate_effect*np.asarray(problem.escalate_state[:n])
    return b[:, None]+phase+state-r[:, None]*treatment


def prefix_loglikelihood(problem: Problem, b, r, innovations, law=V1):
    z = burden(problem, b, r, innovations, law)
    n = z.shape[1]
    ll = np.zeros(len(b))
    for i, q in problem.quality:
        if i < n:
            ll += normal_bin_logmass(q, 10-z[:, i]/3, law.quality_sd, .001, 10.)
    for i, total, width in problem.isi:
        if i < n:
            ll += normal_bin_logmass(total, z[:, i-width+1:i+1].mean(axis=1), law.isi_sd, 1., 28.)
    for i, y, sd in problem.gaussian:
        if i < n:
            ll += -.5*((y-z[:, i])/sd)**2-math.log(sd*math.sqrt(2*np.pi))
    return ll


class Inconclusive(RuntimeError):
    pass


@dataclass
class Budget:
    seconds: float
    started: float = field(default_factory=time.monotonic)

    def check(self):
        if time.monotonic()-self.started >= self.seconds:
            raise Inconclusive('wall_time_cap')


@dataclass(frozen=True)
class Settings:
    particles: int = 1024
    moves: int = 2
    slice_limit: int = 128
    batches: int = 2
    batch_size: int = 10000
    seconds: float = 240.

    def __post_init__(self):
        if (type(self.particles) is not int or not 16 <= self.particles <= 65536
                or type(self.moves) is not int or not 1 <= self.moves <= 16
                or type(self.slice_limit) is not int or not 1 <= self.slice_limit <= 1024
                or type(self.batches) is not int or not 1 <= self.batches <= 1000
                or self.batch_size != 10000 or not math.isfinite(self.seconds) or self.seconds <= 0):
            raise ValueError('invalid frozen settings')


def normalized_weights(log_weights):
    total = logsumexp(log_weights)
    if not np.isfinite(total) or np.any(np.isnan(log_weights)):
        raise Inconclusive('impossible_or_nonfinite_weights')
    w = np.exp(log_weights-total)
    return w, float(1/np.dot(w, w))


def systematic_resample(weights, rng):
    positions = (np.arange(len(weights))+rng.random())/len(weights)
    return np.searchsorted(np.cumsum(weights), positions, side='right').clip(max=len(weights)-1)


def move(b, r, x, loglike: Callable, rng, law, settings, budget, diagnostics):
    """Invariant full-prefix kernels. No adaptation, jitter or stale path cache.

    Reject-outside symmetric b/r RW is reversible for bounded uniform priors.
    Elliptical slice updates standard-normal innovations, using only likelihood
    in the slice test; its Gaussian prior is preserved by the ellipse rotation.
    """
    ll = loglike(b, r, x)
    n = len(b)
    for _ in range(settings.moves):
        budget.check()
        proposal_b = b+rng.normal(0, .04*(law.baseline[1]-law.baseline[0]), n)
        proposal_r = r+rng.normal(0, .08*(law.response[1]-law.response[0]), n)
        inside = ((proposal_b >= law.baseline[0]) & (proposal_b <= law.baseline[1]) &
                  (proposal_r >= law.response[0]) & (proposal_r <= law.response[1]))
        candidate_ll = np.full(n, -np.inf)
        candidate_ll[inside] = loglike(proposal_b[inside], proposal_r[inside], x[inside])
        accept = np.log(rng.random(n)) < candidate_ll-ll
        b[accept], r[accept], ll[accept] = proposal_b[accept], proposal_r[accept], candidate_ll[accept]
        diagnostics['mh_proposals'] += n
        diagnostics['mh_accepts'] += int(accept.sum())
        diagnostics['mh_bounds_rejected'] += int((~inside).sum())
        auxiliary = rng.standard_normal(x.shape)
        threshold = ll+np.log(rng.random(n))
        angle = rng.uniform(0, 2*np.pi, n)
        lower, upper = angle-2*np.pi, angle.copy()
        active = np.arange(n)
        for _ in range(settings.slice_limit):
            budget.check()
            proposed = x[active]*np.cos(angle[active, None])+auxiliary[active]*np.sin(angle[active, None])
            proposed_ll = loglike(b[active], r[active], proposed)
            accepted = proposed_ll >= threshold[active]
            ids = active[accepted]
            x[ids], ll[ids] = proposed[accepted], proposed_ll[accepted]
            diagnostics['slice_evaluations'] += len(active)
            diagnostics['slice_accepts'] += int(accepted.sum())
            active = active[~accepted]
            if not len(active):
                break
            negative = angle[active] < 0
            lower[active[negative]] = angle[active[negative]]
            upper[active[~negative]] = angle[active[~negative]]
            angle[active] = rng.uniform(lower[active], upper[active])
        else:
            # Do not substitute an unaccepted candidate or claim an approximate kernel.
            raise Inconclusive('elliptical_slice_bracket_cap')
    return b, r, x, ll


@dataclass
class Posterior:
    baseline: np.ndarray
    response: np.ndarray
    innovations: np.ndarray
    weights: np.ndarray
    diagnostics: dict


def condition(problem, settings, rng, law=V1, budget=None, diagnostics=None, progress=None):
    budget = budget or Budget(settings.seconds)
    d = diagnostics if diagnostics is not None else {}
    d.update(stages=[], resamplings=0, mh_proposals=0, mh_accepts=0,
             mh_bounds_rejected=0, slice_evaluations=0, slice_accepts=0,
             severe_weight_collapse=False, known_independent_log_factors=problem.constant_log_probability)
    n = settings.particles
    b = rng.uniform(*law.baseline, n)
    r = rng.uniform(*law.response, n)
    x = np.empty((n, 0))
    log_weights, ll = np.zeros(n), np.zeros(n)
    ancestors = np.arange(n)
    observed = {i for i, _ in problem.quality} | {i for i, _, _ in problem.isi} | {i for i, _, _ in problem.gaussian}
    for i, night in enumerate(problem.nights):
        budget.check()
        x = np.column_stack((x, rng.standard_normal(n)))
        if i not in observed:
            continue
        full = lambda bb, rr, xx: prefix_loglikelihood(problem, bb, rr, xx, law)
        next_ll = full(b, r, x)
        log_weights += next_ll-ll
        ll = next_ll
        w, ess = normalized_weights(log_weights)
        severe = ess < max(4., .01*n) or w.max() > .9
        d['severe_weight_collapse'] |= bool(severe)
        stage = dict(night=night, ess=ess, max_weight=float(w.max()),
                     resampled=ess < .5*n, severe_weight_collapse=bool(severe))
        if stage['resampled']:
            indices = systematic_resample(w, rng)
            b, r, x, ancestors = b[indices].copy(), r[indices].copy(), x[indices].copy(), ancestors[indices]
            log_weights = np.zeros(n)
            d['resamplings'] += 1
            b, r, x, ll = move(b, r, x, full, rng, law, settings, budget, d)
        stage.update(ancestral_count=int(len(np.unique(ancestors))),
                     unique_parameters=int(len(np.unique(np.column_stack((b, r)), axis=0))),
                     elapsed_seconds=time.monotonic()-budget.started)
        d['stages'].append(stage)
        if progress:
            progress(d)
    w, ess = normalized_weights(log_weights)
    d.update(final_ess=ess, baseline_mean=float(w@b), response_mean=float(w@r),
             baseline_sd=float(np.sqrt(w@((b-w@b)**2))), response_sd=float(np.sqrt(w@((r-w@r)**2))),
             ancestral_count=int(len(np.unique(ancestors))),
             unique_parameters=int(len(np.unique(np.column_stack((b, r)), axis=0))))
    return Posterior(b, r, x, w, d)


def expected_isi(mean, sd=1.):
    """E[clip(floor(N(mean,sd)+.5),0,28)] by the 28 survival thresholds."""
    return ndtr((np.asarray(mean)[..., None]-(np.arange(1, 29)-.5))/sd).sum(axis=-1)


def future_pair(problem, posterior, rng, size, law=V1, horizon=42, recall=14,
                arms=('behavioral_escalate', 'behavioral_continue'), budget=None):
    if not 1 <= recall <= horizon or any(a not in ('behavioral_escalate', 'behavioral_continue') for a in arms) or len(arms) != 2:
        raise ValueError('invalid retained intervention')
    selected = rng.choice(len(posterior.weights), size=size, p=posterior.weights)
    b, r = posterior.baseline[selected], posterior.response[selected]
    error = residuals(posterior.innovations[selected], law)[:, -1]
    c = np.full((2, size), problem.continue_state[-1])
    e = np.full((2, size), problem.escalate_state[-1])
    total = np.zeros((2, size))
    start = problem.nights[-1]
    for h in range(1, horizon+1):
        if budget:
            budget.check()
        taken = rng.random(size) < law.adherence
        error = law.rho*error+law.innovation_sd*rng.standard_normal(size)
        for j, arm in enumerate(arms):
            c[j] = .65*c[j]+.35*taken*(arm == 'behavioral_continue')
            e[j] = .8*e[j]+.2*taken*(arm == 'behavioral_escalate')
        if h > horizon-recall:
            z = b+law.phase_amplitude*np.sin(2*np.pi*(start+h)/21)+error
            total += z-r*(law.continue_effect*c+law.escalate_effect*e)
    # Outcome missingness is MCAR and fully integrated, not a .9 reward multiplier.
    return expected_isi(total[0]/recall, law.isi_sd), expected_isi(total[1]/recall, law.isi_sd)


def truth_seed(namespace, patient_id, history_sha256, replicate, process):
    if not namespace.startswith('truth-') or type(replicate) is not int or replicate < 0:
        raise ValueError('independent truth namespace and nonnegative replicate required')
    key = f'{namespace}|restricted-v1|{patient_id}|{history_sha256}|{replicate}|{process}'
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:16], 'big')


def evaluate(history, settings, namespace, replicate=0, progress=None):
    problem = compile_history(history)
    if problem.nights[-1] != 14:
        raise ValueError('TA1 exploratory CLI admits day14 only')
    history_hash = sha(history.model_dump(mode='json'))
    seeds = {p: truth_seed(namespace, history.patient_id, history_hash, replicate, p) for p in ('conditioning', 'future')}
    budget = Budget(settings.seconds)
    d = {}
    result = dict(status='inconclusive', truth_kind='observed-Hstar-conditional-mean',
                  information_set='strict-reduced-Hstar-v1', privileged_information=False,
                  production_truth=False, history_sha256=history_hash, patient_id=history.patient_id,
                  cutoff=history.cutoff.isoformat(), endpoint_absolute_day=56,
                  recall_absolute_nights=[43, 56], retained_visits_absolute_days=[28, 42],
                  outcome='rounded-clipped-ISI-total', direction='escalate-minus-continue',
                  horizon_nights=42, support='no_prompt', seeds=seeds, replicate=replicate,
                  namespace=namespace, prng='NumPy-PCG64', filter_diagnostics=d, batches=[])
    try:
        posterior = condition(problem, settings, np.random.default_rng(seeds['conditioning']),
                              budget=budget, diagnostics=d, progress=progress)
        result['conditioning_seconds'] = time.monotonic()-budget.started
        rng = np.random.default_rng(seeds['future'])
        count, total, square = 0, np.zeros(3), np.zeros(3)
        for batch in range(settings.batches):
            budget.check()
            escalate, continuation = future_pair(problem, posterior, rng, settings.batch_size, budget=budget)
            values = np.stack((escalate, continuation, escalate-continuation))
            count += settings.batch_size
            total += values.sum(axis=1); square += (values**2).sum(axis=1)
            means = total/count
            ses = np.sqrt(np.maximum(0, (square-total**2/count)/(count-1)/count))
            result['batches'].append(dict(index=batch, trajectories=settings.batch_size,
                estimate=float((escalate-continuation).mean()), elapsed_seconds=time.monotonic()-budget.started))
            result.update(estimate=float(means[2]), arm_means=means[:2].tolist(),
                          within_filter_rollout_mcse=float(ses[2]), arm_rollout_mcse=ses[:2].tolist(),
                          future_trajectories=count)
            if progress:
                progress(result)
        result['status'] = 'inconclusive' if d['severe_weight_collapse'] else 'exploratory_unqualified'
        result['reason'] = 'severe_weight_collapse' if d['severe_weight_collapse'] else 'TA2_refinement_and_matched_SE_pending'
    except Inconclusive as exc:
        result['reason'] = str(exc)
    result.update(elapsed_seconds=time.monotonic()-budget.started,
                  numerical_error_components=dict(quadrature_change=None, conditioning_refinement=None,
                      within_filter_mcse=result.get('within_filter_rollout_mcse'), between_filter_mcse=None,
                      finite_grid_discrepancy_bound=None),
                  qualification='No 32-filter refinement, matched-estimator-SE or finite-grid qualification')
    return result
