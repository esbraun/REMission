"""Accepted S1 WCLS and R1 missing-reward sensitivity, offline only.

Primary inference targets the eligible S1 decision-point average excursion under
the declared independent .1 MCAR reporting law. It is not an ordinary physician
choice estimator, MNAR correction, adaptive-policy interval or coverage claim.
The G>=8 floor is an engineering gate, not a calibration theorem.
"""
from dataclasses import dataclass
from itertools import product
import platform

import numpy as np
import scipy
from scipy.stats import t
import statsmodels
from statsmodels.regression.linear_model import WLS

from contracts.domain.analysis import reference, sha
from contracts.domain.protocol_request import S1_ESTIMAND, WCLS_PRIOR_REF
from contracts.domain.protocol import LAW_REF, SUPPORT_REF
from .data import FeatureData, design

SETTINGS = dict(id='poc-support-s1-offline-r1', version='1.0.0', q=.5,
    controls=['intercept', 'prior_available_quality_default7', 'no_prior_available_quality',
              'previous_six_nights_delivered_prompts', 'night/84'], effect='A-.5',
    reporting='complete-observed-reward; independent MCAR .1', min_clusters=8,
    columns=6, weighted_rank='max(N,K)*float64_epsilon*s_max',
    covariance=dict(type='cluster', use_correction=True, df_correction=True, use_t=True),
    interval='beta +/- t(.975,G-1)*SE', missing_rate=.1, deltas=[-.5, 0., .5],
    baseline='clip(controls@gamma+(a-.5)*beta,0,10)',
    sensitivity='beta + mean_context(.1*(d1-d0)); equal decision weights; point estimates only',
    statsmodels='0.15.0', precision='float64', production_activation=False)
CONFIGURATION = reference(SETTINGS['id'], SETTINGS)
SENSITIVITY_LABEL = 'Assumption-driven missing-reward sensitivity; point estimates only'


@dataclass(frozen=True)
class SensitivityCell:
    delta0: float
    delta1: float
    estimate: float
    shift: float
    direction: str


@dataclass(frozen=True)
class WCLSResult:
    status: str
    reasons: tuple[str, ...]
    identity: dict
    counts: dict
    coefficients: tuple[float, ...] = ()
    covariance: tuple[tuple[float, ...], ...] = ()
    estimate: float | None = None
    standard_error: float | None = None
    interval: tuple[float, float] | None = None
    df: int | None = None
    singular_values: tuple[float, ...] = ()
    condition_number: float | None = None
    sensitivity_status: str = 'unavailable'
    sensitivity_reason: str | None = 'primary unavailable'
    sensitivity: tuple[SensitivityCell, ...] = ()
    sensitivity_range: tuple[float, float] | None = None
    sensitivity_label: str = SENSITIVITY_LABEL


def sensitivity(coefficients, controls):
    """Finite R1 sum; no imputed rows, refit, CI or Monte Carlo uncertainty."""
    coefficients, controls = np.asarray(coefficients), np.asarray(controls)
    if coefficients.shape != (6,) or controls.ndim != 2 or controls.shape[1] != 5 or not len(controls):
        raise ValueError('six coefficients and nonempty five-control contexts required')
    if not np.all(np.isfinite(coefficients)) or not np.all(np.isfinite(controls)):
        raise ValueError('finite sensitivity inputs required')
    beta = float(coefficients[-1])
    m0 = np.clip(controls@coefficients[:5]-.5*beta, 0., 10.)
    m1 = np.clip(controls@coefficients[:5]+.5*beta, 0., 10.)
    cells = []
    for delta0, delta1 in product(SETTINGS['deltas'], repeat=2):
        shift = float(np.mean(.1*(np.clip(m1+delta1, 0., 10.)-m1
                                 -np.clip(m0+delta0, 0., 10.)+m0)))
        estimate = beta+shift
        cells.append(SensitivityCell(delta0, delta1, estimate, shift,
                     'positive' if estimate > 0 else 'negative' if estimate < 0 else 'zero'))
    return tuple(cells)


def fit(data: FeatureData, *, provenance_seed: str) -> WCLSResult:
    """Fit the frozen offline design, keeping failures and information identity.

    Seed is unused provenance in the existing WCLS namespace. FeatureData must
    come from build_features; production request admission remains separate.
    """
    observed = data.observed
    groups = np.asarray([r.patient_id for r in observed])
    n, g = len(observed), len(set(groups))
    counts = dict(eligible_completed=len(data.rows), observed=n, missing=len(data.rows)-n,
                  participants=g, context_participants=len({r.patient_id for r in data.rows}),
                  excluded=data.excluded, eligible_counts_complete=data.sensitivity_reason is None)
    identity = dict(configuration=CONFIGURATION, settings_sha256=sha(SETTINGS),
        estimand=S1_ESTIMAND, prior=WCLS_PRIOR_REF, observation_cutoff=data.cutoff.isoformat(),
        history_sha256=data.history_sha256, seed=provenance_seed, seed_used=False,
        expected_public_law=LAW_REF, expected_protocol=SUPPORT_REF,
        input_view='active public reduced records; parent ProtocolInput admission remains required',
        source='public reduced quality/assignment/delivery/support-decision/outcome records only',
        package_versions=dict(python=platform.python_version(), numpy=np.__version__,
                              scipy=scipy.__version__, statsmodels=statsmodels.__version__))
    def abstain(reason, **kwargs):
        return WCLSResult('abstained', (reason,), identity, counts, **kwargs)
    if not provenance_seed.startswith('fit/wcls-unused-provenance/'):
        return abstain('independent fit/wcls-unused-provenance seed namespace required')
    if statsmodels.__version__ != SETTINGS['statsmodels']:
        return abstain('unqualified statsmodels version; requires '+SETTINGS['statsmodels'])
    if g < 8:
        return abstain('insufficient contributing participants: G<8')
    if n <= 6:
        return abstain('insufficient retained rewards: N<=K')
    x = design(observed)
    y = np.asarray([r.reward for r in observed], dtype=np.float64)
    p = np.asarray([r.probability for r in observed], dtype=np.float64)
    if not np.all(p == .5) or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        return abstain('invalid S1 design/reward/recorded probability')
    if not np.all((0 <= y) & (y <= 10)) or set(r.action for r in observed) != {0, 1}:
        return abstain('invalid quality bounds or both actions not represented')
    w = .5/p
    singular = np.linalg.svd(np.sqrt(w)[:, None]*x, compute_uv=False)
    tolerance = max(n, 6)*np.finfo(np.float64).eps*singular[0]
    rank = int(np.sum(singular > tolerance))
    diagnostics = dict(singular_values=tuple(float(v) for v in singular),
                       condition_number=float(singular[0]/singular[-1]) if singular[-1] > 0 else None)
    if rank != 6:
        return abstain('weighted design rank deficient; columns are never removed or repaired', **diagnostics)
    try:
        ordinary = WLS(y, x, weights=w, missing='raise').fit()
        robust = ordinary.get_robustcov_results(cov_type='cluster', groups=groups,
                    use_correction=True, df_correction=True, use_t=True)
    except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as error:
        return abstain('statsmodels fit failed: '+str(error), **diagnostics)
    if robust.df_resid_inference != g-1 or not robust.use_t:
        return abstain('library inference degrees of freedom/use_t mismatch', **diagnostics)
    beta, variance = float(robust.params[-1]), float(robust.cov_params()[-1, -1])
    if not np.all(np.isfinite(robust.params)) or not np.all(np.isfinite(robust.cov_params())) or variance <= 0:
        return abstain('nonfinite fit or nonpositive treatment variance', **diagnostics)
    se = float(np.sqrt(variance))
    critical = float(t.ppf(.975, g-1))
    cells = () if data.sensitivity_reason else sensitivity(robust.params, [r.controls for r in data.rows])
    return WCLSResult('estimated', (), identity, counts, tuple(float(v) for v in robust.params),
        tuple(tuple(float(v) for v in row) for row in robust.cov_params()), beta, se,
        (beta-critical*se, beta+critical*se), g-1, **diagnostics,
        sensitivity_status='unavailable' if data.sensitivity_reason else 'available',
        sensitivity_reason=data.sensitivity_reason, sensitivity=cells,
        sensitivity_range=(min(c.estimate for c in cells), max(c.estimate for c in cells)) if cells else None)
