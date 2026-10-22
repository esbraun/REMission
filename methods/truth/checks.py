"""Independent reduced integrations. No primary filter/generator/learner import.

Tensor quadrature integrates the ratio of joint prior/observation integrals.
The Gaussian overlap instead conditions a multivariate Normal by linear algebra.
These algorithms intentionally do not call the particle likelihood or rollout.
"""
from dataclasses import dataclass
from itertools import product
import math

import numpy as np
from numpy.polynomial.hermite import hermgauss
from numpy.polynomial.legendre import leggauss
from scipy.linalg import solve
from scipy.special import logsumexp
from scipy.stats import norm


@dataclass(frozen=True)
class ReducedCase:
    nights: tuple[int, ...]
    treatment: tuple[float, ...]
    quality: tuple[tuple[int, float], ...] = ()
    isi: tuple[tuple[int, int, int], ...] = ()
    baseline: tuple[float, float] = (16., 22.)
    response: tuple[float, float] = (.8, 1.2)
    rho: float = .55
    innovation_sd: float = .8
    phase_amplitude: float = .55


def _measurement_log_probability(observed, location, sd, resolution, maximum):
    # Independent SciPy distribution implementation; switch to survival tails
    # before differencing, rather than subtracting two nearly-one probabilities.
    a = -np.inf if observed == 0 else (observed-resolution/2-location)/sd
    b = np.inf if observed == maximum else (observed+resolution/2-location)/sd
    left, right = norm.logcdf(b), norm.logcdf(a)
    if np.ndim(a):
        choose = a >= 0
        left, right = np.where(choose, norm.logsf(a), left), np.where(choose, norm.logsf(b), right)
    elif a >= 0:
        left, right = norm.logsf(a), norm.logsf(b)
    with np.errstate(divide='ignore', invalid='ignore'):
        return left+np.log1p(-np.exp(right-left))


def quadrature(case: ReducedCase, order: int):
    """One/two innovations only; moments (b,r,last residual,last residual^2).

    Integral weights are prior probabilities, not posterior particle weights.
    Every observation is evaluated at each shared latent path before summing.
    """
    n = len(case.nights)
    if n not in (1, 2) or len(case.treatment) != n or not 2 <= order <= 96:
        raise ValueError('bounded one/two-night quadrature only')
    leg_x, leg_w = leggauss(order)
    herm_x, herm_w = hermgauss(order)
    nodes = list(product(range(order), repeat=n))
    innovations = np.array([[math.sqrt(2)*herm_x[j] for j in row] for row in nodes])
    prior_logs = np.array([sum(math.log(herm_w[j]/math.sqrt(math.pi)) for j in row) for row in nodes])
    errors, previous = [], np.zeros(len(nodes))
    for i in range(n):
        previous = case.rho*previous+case.innovation_sd*innovations[:, i]
        errors.append(previous)
    errors = np.stack(errors, axis=1)

    def uniform_nodes(bounds):
        if bounds[0] == bounds[1]:
            return [(bounds[0], 1.)]
        return [(bounds[0]+(node+1)*(bounds[1]-bounds[0])/2, weight/2) for node, weight in zip(leg_x, leg_w)]

    logs, moments = [], []
    for b, wb in uniform_nodes(case.baseline):
        for r, wr in uniform_nodes(case.response):
            z = b+case.phase_amplitude*np.sin(2*np.pi*np.array(case.nights)/21)+errors-r*np.array(case.treatment)
            ll = prior_logs+math.log(wb)+math.log(wr)
            for i, q in case.quality:
                ll = ll+_measurement_log_probability(q, 10-z[:, i]/3, .45, .001, 10)
            for i, total, width in case.isi:
                ll = ll+_measurement_log_probability(total, z[:, i-width+1:i+1].mean(axis=1), 1, 1, 28)
            logs.append(ll)
            moments.append(np.column_stack((np.full(len(ll), b), np.full(len(ll), r), errors[:, -1], errors[:, -1]**2)))
    logs, moments = np.concatenate(logs), np.concatenate(moments)
    denominator = logsumexp(logs)
    return dict(order=order, log_evidence=float(denominator),
                moments=(np.exp(logs-denominator)@moments).tolist(),
                nodes=len(logs), method='independent-Legendre-Hermite-ratio-of-integrals')


def gaussian_overlap(*, observed_values, observed_indices, observation_sds,
                     observed_nights, future_nights=0, recall=1, baseline=19.,
                     rho=.55, innovation_sd=.8):
    """Kalman-equivalent joint Gaussian conditioning from independent covariance.

    Index0 is the first innovation after the deterministic zero initial state.
    This is an unrounded burden-observation overlap, not the real rounded model.
    """
    n = observed_nights+future_nights
    indices = np.asarray(observed_indices, int)
    if (n < 1 or len(indices) != len(observed_values) or len(indices) != len(observation_sds)
            or any(i < 0 or i >= observed_nights for i in indices)
            or any(s <= 0 for s in observation_sds) or not 1 <= recall <= n):
        raise ValueError('invalid Gaussian overlap')
    covariance = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            covariance[i, j] = innovation_sd**2*sum(rho**(i+j-2*k) for k in range(min(i, j)+1))
    cross = covariance[:, indices]
    observed_covariance = covariance[np.ix_(indices, indices)]+np.diag(np.square(observation_sds))
    y = np.asarray(observed_values)-baseline
    mean = baseline+cross@solve(observed_covariance, y, assume_a='pos')
    conditional_covariance = covariance-cross@solve(observed_covariance, cross.T, assume_a='pos')
    endpoint_mean = float(mean[-recall:].mean())
    endpoint_variance = float(conditional_covariance[-recall:, -recall:].sum()/recall**2)
    rounded_isi = sum(norm.sf(k-.5, loc=endpoint_mean, scale=math.sqrt(1+endpoint_variance)) for k in range(1, 29))
    return dict(mean=mean.tolist(), covariance=conditional_covariance.tolist(),
                endpoint_mean=endpoint_mean, endpoint_variance=endpoint_variance,
                expected_rounded_isi=float(rounded_isi), method='independent-joint-Gaussian-Kalman-overlap')


def exact_adherence_tree(*, horizon, recall, baseline=19., response=1.,
                        initial_continue=0., initial_escalate=0., start_day=14,
                        adherence=.85, continue_effect=2., escalate_effect=4., phase_amplitude=.55):
    """Enumerated paired adherence, deterministic process overlap only."""
    if not 1 <= recall <= horizon <= 12:
        raise ValueError('bounded exact tree only')
    expectation = np.zeros(2)
    for taken in product((0, 1), repeat=horizon):
        probability = adherence**sum(taken)*(1-adherence)**(horizon-sum(taken))
        for arm in range(2):
            c, e, burdens = initial_continue, initial_escalate, []
            for h, dose in enumerate(taken, 1):
                c = .65*c+.35*dose*(arm == 1)
                e = .8*e+.2*dose*(arm == 0)
                burdens.append(baseline+phase_amplitude*math.sin(2*math.pi*(start_day+h)/21)
                               -response*(continue_effect*c+escalate_effect*e))
            location = sum(burdens[-recall:])/recall
            expectation[arm] += probability*sum(norm.sf(k-.5, loc=location) for k in range(1, 29))
    return dict(arm_means=expectation.tolist(), contrast=float(expectation[0]-expectation[1]),
                leaves=2**horizon, method='independent-exact-adherence-tree')
