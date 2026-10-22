"""Fixed differentiable source-population marginal; no private generator inputs.

Only weighted Bernoulli adherence is moment approximated. Baseline/effect
hierarchies use fixed Gauss-Hermite nodes; AR and endpoint noise integrate exactly.
Qualification must pass independently before this likelihood may be enabled.
"""
import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.special import logsumexp
from .numerics import rounded_isi_mean

FIELDS = ('mu_b', 'beta_c', 'beta_e', 'sd_b', 'sd_beta_c', 'sd_beta_e',
          'p', 'rho', 'sigma_e', 'sigma_isi', 'a')
BASE = (19, 1, 3, 2, .8, .8, .7, .3, 1, 1.2, .4)
PRODUCTION_ORDER = 16
REFERENCE_ORDERS = (16, 32, 64)
LOOKS = (4096, 8192, 16384, 32768, 65536, 131072)
FAMILY_TESTS = 120 * 2 * 3 * 6
ALPHA = .01
QUALIFICATION_SECONDS = 1800
POSTFIT_SECONDS = 900
DISPATCH_SECONDS = 7200


def fixed_vectors():
    vectors = [dict(zip(FIELDS, BASE))]
    for name, values in [('mu_b', (8, 28)), ('beta_c', (-8, 8)),
        ('beta_e', (-8, 8)), ('sd_b', (.1, 6)), ('sd_beta_c', (.1, 6)),
        ('sd_beta_e', (.1, 6)), ('p', (.01, .5, .99)), ('rho', (-.94, 0, .94)),
        ('sigma_e', (.1, 4)), ('sigma_isi', (.1, 4))]:
        vectors.extend(dict(vectors[0], **{name: value}) for value in values)
    vectors.append(dict(vectors[0], mu_b=28, beta_e=-8, sd_b=6,
                        sd_beta_e=6, p=.5, rho=.94, sigma_e=4))
    assert len(vectors) == 24
    return vectors


def quadrature(order):
    nodes, weights = hermgauss(order)
    return nodes * np.sqrt(2), weights / np.sqrt(np.pi)


def filter_weights(rho, *, first=-13):
    # Recurrence is also used by tensor_filter_variance, including at rho=0.
    powers = [1.]
    for _ in range(55):
        powers.append(powers[-1] * rho)
    return np.array([sum(powers[t-k] for t in range(max(29, k), 43))/14
                     for k in range(first, 43)])


WC = .35 * filter_weights(.65, first=1)
WE = .2 * filter_weights(.8, first=1)
SINE = np.sin(2 * np.pi * np.arange(29, 43)/21).mean()


def marginal(theta, order=PRODUCTION_ORDER, *, details=False):
    nodes, weights = quadrature(order)
    b = theta['mu_b'] + theta['sd_b'] * nodes[:, None]
    p = theta['p']
    noise = theta['sigma_e']**2 * np.sum(filter_weights(theta['rho'])**2) + theta['sigma_isi']**2
    values, vmax = [], 0.
    for arm, w in [('c', WC), ('e', WE)]:
        beta = theta['beta_'+arm] + theta['sd_beta_'+arm]*nodes[None, :]
        mean = b + theta['a']*SINE - beta*p*w.sum()
        variance = beta**2*p*(1-p)*np.sum(w**2) + noise
        values.append(float(np.sum(rounded_isi_mean(mean, np.sqrt(variance))*weights[:, None]*weights[None, :])))
        vmax = max(vmax, float(np.max(variance)))
    g = values[1]-values[0]
    return (g, vmax) if details else g


def mixture_logp(d, se, g, bias, tau, *, weight=.5):
    def normal(value, mean, variance):
        return -.5*(np.log(2*np.pi*variance)+(value-mean)**2/variance)
    terms = np.array([np.log(weight) + normal(d, g+bias, se**2+tau**2),
                      np.log1p(-weight) + normal(d, 0, se**2+100)])
    return float(logsumexp(terms)), float(np.exp(terms[0]-logsumexp(terms)))


def tensor_marginal(theta, order=PRODUCTION_ORDER):
    import pytensor.tensor as pt
    nodes, weights = quadrature(order)
    b = theta['mu_b'] + theta['sd_b']*nodes[:, None]
    powers = [pt.as_tensor_variable(np.float64(1))]
    for _ in range(55):
        powers.append(powers[-1]*theta['rho'])
    h = pt.stack([sum(powers[t-k] for t in range(max(29, k), 43))/14 for k in range(-13, 43)])
    noise = theta['sigma_e']**2*pt.sum(h**2) + theta['sigma_isi']**2
    values = []
    for arm, w in [('c', WC), ('e', WE)]:
        beta = theta['beta_'+arm] + theta['sd_beta_'+arm]*nodes[None, :]
        mean = b + theta['a']*SINE-beta*theta['p']*w.sum()
        variance = beta**2*theta['p']*(1-theta['p'])*np.sum(w**2)+noise
        # erfc directly computes the upper-tail probabilities without 1-CDF.
        rounded = .5*pt.erfc((np.arange(.5, 28)-mean[..., None])/pt.sqrt(2*variance[..., None]))
        values.append(pt.sum(rounded.sum(axis=-1)*weights[:, None]*weights[None, :]))
    return values[1]-values[0]


def tensor_mixture(d, se, g, bias, tau):
    import pytensor.tensor as pt
    vi, vw = se**2+tau**2, se**2+100
    informative = -.5*(np.log(2*np.pi)+pt.log(vi)+(d-g-bias)**2/vi)-np.log(2)
    weak = -.5*(np.log(2*np.pi*vw)+d**2/vw)-np.log(2)
    total = pt.logaddexp(informative, weak)
    return total, pt.exp(informative-total)
