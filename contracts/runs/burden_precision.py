"""BURDEN-PRECISION-01/1.0.0-r1 finite arithmetic, not a scientific engine.

All arrays describe expressly private complete outcomes. Public observed R and
upload arrival cannot select these rows. Artifact/execution/source admission
must independently establish the population, independence, counts, and any
structural proof before these arithmetic checks can qualify a run.
"""
from math import exp, expm1, isfinite, log, sqrt

import numpy as np
from scipy.special import logsumexp
from scipy.stats import beta, binom

LEVELS = (1024, 4096, 16384, 65536)
COMPONENTS = ('q', 'theta0', 'theta1', 'theta2', 'theta3', 'theta4', 'mu')
ALPHA = .05 / 6


class UnresolvedPrecision(ValueError):
    """A failed numerical qualification cannot become an analytic certificate."""


def _n(n):
    if type(n) is not int or n < 1:
        raise ValueError('strict_positive_assigned_arm_size_required')


def _q(q, *, interior=False):
    if isinstance(q, bool) or not isfinite(q) or not (0 < q < 1 if interior else 0 < q <= 1):
        raise UnresolvedPrecision('positive_definition_probability_required; boundary needs independent structural derivation')


def ratio_factor(n, q):
    """Exact E[1/M | M>0], via qualified SciPy finite log-PMF/log-SF."""
    _n(n);_q(q)
    if q == 1:
        return 1. / n
    m = np.arange(1, n+1, dtype=np.float64)
    log_rho = binom.logsf(0, n, q)
    value = float(exp(logsumexp(binom.logpmf(m, n, q)-np.log(m))-log_rho))
    if not isfinite(value) or value <= 0:
        raise UnresolvedPrecision('nonfinite_exact_finite_denominator_sum')
    return value


def ratio_factor_derivative(n, q):
    """Accepted explicit interior derivative; no boundary epsilon substitute."""
    _n(n);_q(q, interior=True)
    m = np.arange(1, n+1, dtype=np.float64)
    w = np.exp(binom.logpmf(m, n, q))
    rho = float(binom.sf(0, n, q));r = ratio_factor(n, q)
    first = float(np.sum(w*(m/q-(n-m)/(1-q))/m))
    value = (first-r*n*(1-q)**(n-1))/rho
    if not isfinite(value):
        raise UnresolvedPrecision('nonfinite_interior_ratio_derivative')
    return value


def _theta(theta):
    x = np.asarray(theta, dtype=np.float64)
    if x.shape != (5,) or not np.isfinite(x).all() or (x < 0).any() or abs(float(x.sum())-1) > 1e-12:
        raise ValueError('complete_normalized_five_category_probability_vector_required')
    return x


def sampling_variances(n, q, theta):
    """Conditional ratio variance plus separate q variance/undefined mass."""
    _n(n);_q(q);theta = _theta(theta)
    r = ratio_factor(n, q)
    score_v = sum(theta[k]*theta[l]*(k-l)**2 for k in range(5) for l in range(k+1, 5))
    return dict(q=q*(1-q)/n, theta=theta*(1-theta)*r, mu=float(score_v*r),
        ratio_factor=r, undefined_probability=float(binom.pmf(0, n, q)))


def _counts(counts, n, *, rows=1000):
    _n(n);x = np.asarray(counts)
    if x.shape != (rows, 6) or not np.issubdtype(x.dtype, np.integer) or (x < 0).any() or (x > n).any() or not np.all(x.sum(axis=1) == n):
        raise ValueError('complete_fixed_roster_integer_undefined_plus_five_category_counts_required')
    return x


def partial_trial_values(counts, n, component):
    """Retain null partial ratios; M=1 has a point, never an invented SE."""
    x = _counts(counts, n);m = x[:, 1:].sum(axis=1)
    if component == 'q':
        return np.ones(1000, dtype=bool), m.astype(float)/n, m
    if component not in COMPONENTS:
        raise ValueError('unknown_burden_component')
    defined = m > 0;values = np.full(1000, np.nan)
    numerator = x[:, int(component[-1])+1] if component.startswith('theta') else x[:, 1:]@np.arange(5)
    values[defined] = numerator[defined]/m[defined]
    return defined, values, m


def empirical_statistics(counts, n, component):
    a, y, m = partial_trial_values(counts, n, component)
    jplus = int(a.sum());rho = float(a.mean())
    if jplus < 2:
        raise UnresolvedPrecision('fewer_than_two_defined_trial_ratios')
    mean = float(y[a].mean());sd = float(y[a].std(ddof=1))
    if not isfinite(sd) or sd <= 0:
        raise UnresolvedPrecision('zero_empirical_dispersion_is_not_structural_proof')
    g = np.zeros(1000);h = np.zeros(1000)
    # Undefined values are never evaluated, multiplied by zero, or filled in.
    g[a] = (y[a]-mean)/rho
    h[a] = ((y[a]-mean)**2-sd*sd)/(2*sd*rho)
    mcse = float(h.std(ddof=1)/sqrt(1000));lower = sd-1.645*mcse
    if not isfinite(lower) or lower <= 0:
        raise UnresolvedPrecision('nonpositive_empirical_dispersion_lower_limit')
    return dict(component=component, values=[float(v) if known else None for v,known in zip(y,a,strict=True)],
        defined=a, defined_trials=jplus, undefined_trials=1000-jplus,
        M0_trials=int((m==0).sum()), M1_trials=int((m==1).sum()),
        mean=mean, sd=sd, sd_mcse=mcse, lower=lower, mean_influence=g, sd_influence=h)


def cp_interval(successes, total):
    if type(successes) is not int or type(total) is not int or total < 1 or not 0 <= successes <= total:
        raise UnresolvedPrecision('exact_CP_requires_nonempty_valid_independent_roster')
    return (0. if successes == 0 else float(beta.ppf(ALPHA/2, successes, total-successes+1)),
            1. if successes == total else float(beta.ppf(1-ALPHA/2, successes+1, total-successes)))


def pooled_box(counts, n):
    x = _counts(counts, n);total = 1000*n;categories = x[:, 1:].sum(axis=0);defined = int(categories.sum())
    if defined == 0:
        raise UnresolvedPrecision('sampled_all_undefined_does_not_prove_structural_q0')
    q_interval = cp_interval(defined, total)
    category_intervals = [cp_interval(int(k), defined) for k in categories]
    return dict(total=total, defined=defined, categories=categories, probabilities=x.sum(axis=0)/total,
        q=defined/total, theta=categories/defined, q_interval=q_interval, theta_intervals=category_intervals,
        interval_alpha=ALPHA, family='pointwise_arm_level_six_interval_Bonferroni_CP')


def conservative_variance(n, component, box):
    lq,uq = box['q_interval']
    if component == 'q':
        return min(lq*(1-lq), uq*(1-uq))/n
    if lq <= 0:
        raise UnresolvedPrecision('positive_definition_probability_lower_bound_required')
    intervals = box['theta_intervals'];r = ratio_factor(n, uq)
    if component.startswith('theta') and component in COMPONENTS:
        lo,hi = intervals[int(component[-1])]
        return min(lo*(1-lo), hi*(1-hi))*r
    if component == 'mu':
        return sum(intervals[k][0]*intervals[l][0]*(k-l)**2 for k in range(5) for l in range(k+1, 5))*r
    raise ValueError('unknown_burden_component')


def analytic_sd_gradient(n, probabilities, component):
    """Unconstrained-extension gradient on six probabilities, interior q only."""
    _n(n);p = np.asarray(probabilities, dtype=np.float64)
    if p.shape != (6,) or not np.isfinite(p).all() or (p < 0).any() or abs(float(p.sum())-1) > 1e-12:
        raise ValueError('six_category_probability_vector_required')
    q = float(p[1:].sum());_q(q, interior=True);theta = _theta(p[1:]/q)
    variance = sampling_variances(n, q, theta)
    value = variance['theta'][int(component[-1])] if component.startswith('theta') and component in COMPONENTS else variance.get(component)
    if value is None or value <= 0:
        raise UnresolvedPrecision('unproved_nondifferentiable_SD_boundary')
    sd = sqrt(value);gradient = np.zeros(6)
    if component == 'q':
        gradient[1:] = (1-2*q)/(2*n*sd)
    else:
        if component.startswith('theta'):
            k = int(component[-1]);v = theta[k]*(1-theta[k]);dv = np.zeros(5);dv[k] = 1-2*theta[k]
        else:
            marks = np.arange(5);mu = float(marks@theta);v = float(variance['mu']/variance['ratio_factor']);dv = marks**2-2*mu*marks
        dq = v*ratio_factor_derivative(n, q)/(2*sd)
        dtheta = variance['ratio_factor']*dv/(2*sd)
        gradient[1:] = dq+(dtheta-float(dtheta@theta))/q
    return sd, gradient


def fixed_defined_sd_gradient(n, theta, component):
    """Algebra for an independently proved fixed q=1 model; not a proof itself."""
    _n(n);theta = _theta(theta);r = 1/n
    if component.startswith('theta') and component in COMPONENTS:
        k = int(component[-1]);v = theta[k]*(1-theta[k]);dv = np.zeros(5);dv[k] = 1-2*theta[k]
    elif component == 'mu':
        marks = np.arange(5);mu = float(marks@theta);v = float(sum(theta[k]*theta[l]*(k-l)**2 for k in range(5) for l in range(k+1,5)));dv = marks**2-2*mu*marks
    else:
        raise UnresolvedPrecision('fixed_q_component_requires_its_own_analytic_constant_proof')
    if v <= 0:
        raise UnresolvedPrecision('constant_category_requires_its_own_structural_proof')
    sd = sqrt(v*r)
    return sd, r*dv/(2*sd)


def numerical_binding(counts, n, component):
    """Interior numerical case; native q=1 needs separately qualified proof IO."""
    stats = empirical_statistics(counts, n, component);box = pooled_box(counts, n)
    lower_v = conservative_variance(n, component, box)
    if not isfinite(lower_v) or lower_v <= 0:
        raise UnresolvedPrecision('nonpositive_exact_box_variance_lower_bound_no_floor')
    analytic,gradient = analytic_sd_gradient(n, box['probabilities'], component)
    p = box['probabilities'];covariance = (np.diag(p)-np.outer(p,p))/box['total']
    analytic_var = float(gradient@covariance@gradient)
    if not isfinite(analytic_var) or analytic_var < 0:
        raise UnresolvedPrecision('invalid_analytic_SD_delta_covariance')
    analytic_mcse = sqrt(analytic_var)
    if abs(stats['sd']-analytic) > 1.96*(stats['sd_mcse']+analytic_mcse):
        raise UnresolvedPrecision('empirical_analytic_dispersion_disagreement')
    bound = min(stats['lower'], sqrt(lower_v))
    epsilon = min(.01 if component == 'mu' else .001, .1*bound)
    return dict(**stats, box=box, variance_lower=lower_v, analytic_sd=analytic, analytic_sd_mcse=analytic_mcse,
        analytic_gradient=gradient, pooled_multinomial_covariance=covariance, binding=bound, epsilon=epsilon)


def require_refinement(levels, statistics):
    if tuple(levels) not in (LEVELS[:3], LEVELS) or len(statistics) != len(levels):
        raise ValueError('first_three_or_all_four_approved_particle_levels_required')
    if len({s['component'] for s in statistics}) != 1:
        raise ValueError('cross_component_refinement_forbidden')
    epsilon = statistics[-1]['epsilon']
    if not isfinite(epsilon) or epsilon <= 0:
        raise UnresolvedPrecision('positive_final_epsilon_required')
    for index in range(len(statistics)-2, len(statistics)):
        before,after = statistics[index-1:index+1]
        if any(not isfinite(s['binding']) or s['binding'] <= 0 for s in (before,after)):
            raise UnresolvedPrecision('all_retained_levels_need_positive_qualified_binding')
        dg = after['mean_influence']-before['mean_influence'];dh = after['sd_influence']-before['sd_influence']
        mean = abs(after['mean']-before['mean'])+1.96*float(dg.std(ddof=1))/sqrt(1000)
        dispersion = .1*(abs(after['sd']-before['sd'])+1.96*float(dh.std(ddof=1))/sqrt(1000))
        change = .1*abs(after['binding']-before['binding'])
        if max(mean,dispersion,change) > epsilon/4:
            raise UnresolvedPrecision('last_two_adjacent_transitions_fail_at_final_epsilon')
    return epsilon


def pooled_truth_statistics(batch_counts, component):
    x = np.asarray(batch_counts)
    if x.ndim != 2 or not 32 <= len(x) <= 1000:
        raise UnresolvedPrecision('truth_requires_32_to_1000_complete_independent_outer_batches')
    x = _counts(x, 10000, rows=len(x));defined = x[:,1:].sum(axis=1).astype(float)
    if component == 'q':
        numerator = defined/10000;denominator = np.ones(len(x))
    elif component.startswith('theta') and component in COMPONENTS:
        numerator = x[:,int(component[-1])+1]/10000;denominator = defined/10000
    elif component == 'mu':
        numerator = (x[:,1:]@np.arange(5))/10000;denominator = defined/10000
    else:
        raise ValueError('unknown_burden_component')
    if denominator.mean() <= 0:
        raise UnresolvedPrecision('no_defined_truth_denominator_without_structural_proof')
    value = float(numerator.sum()/denominator.sum())
    influence = (numerator-value*denominator)/denominator.mean()
    mcse = float(influence.std(ddof=1)/sqrt(len(x)))
    return dict(value=value, mcse=mcse, influence=influence, numerator=numerator, denominator=denominator,
        independent_units=len(x), continuations_per_batch=10000, empirical_degenerate=bool(np.all(influence==0)),
        qualification='arithmetic_only; degenerate variation needs independent valid bound or structural proof')


def all_batch_absent_upper(batches, *, definition_lower=None):
    if type(batches) is not int or not 32 <= batches <= 1000:
        raise ValueError('independent_outer_batch_count_required')
    value = -expm1(log(.05)/batches)
    if definition_lower is not None:
        _q(definition_lower)
        value = min(1., value/definition_lower)
    return value
