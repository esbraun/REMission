"""SOURCE ONLY: one joint PA1 posterior; requires independent qualification.

Canonical priors/rounded likelihood/exact-guide algebra are retained. Shared
normal coordinates occur once; each patient's innovations and observations
occupy disjoint blocks. No build/sample is called by the inactive worker path.
"""
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt

from contracts.domain.analysis import CONFIG
from .model import inputs, gaussian_guide, log_bin
from .cohort_geometry import coordinate_slices, embed_basis


def cohort_inputs(cohort):
    # Revalidate the envelope before model data construction, including its
    # cross-member record ownership and canonical order.
    from contracts.domain.cohort import CohortHistory
    cohort = CohortHistory.model_validate_json(cohort.model_dump_json())
    return [(h.patient_id, inputs(h)) for h in cohort.histories]


def build_cohort(data, *, guide=True, prior_predictive=False):
    if pytensor.config.floatX != 'float64':
        raise ValueError('float64 required')
    if prior_predictive and guide:
        raise ValueError('unconditioned prior simulation requires original coordinates')
    patients = [patient for patient, _ in data]
    n = len(data[0][1]['nights'])
    layout = coordinate_slices(patients, n)
    if any(not np.array_equal(d['nights'], data[0][1]['nights']) for _, d in data):
        raise ValueError('cohort common grid required')
    count = len(patients)
    with pm.Model(coords=dict(patient=patients, night=data[0][1]['nights'],
            arm=['continue', 'escalate'], latent=np.arange(layout['dimension']))) as model:
        sd_b = pm.HalfNormal('sd_b', 3)
        sd_beta = pm.HalfNormal('sd_beta', 1, dims='arm')
        rho = pm.Uniform('rho', -.95, .95)
        sigma_e = pm.HalfNormal('sigma_e', 2)
        sigma_isi = pm.HalfNormal('sigma_isi', 2)
        sigma_quality = pm.HalfNormal('sigma_quality', 1)
        lag = np.arange(n)[:, None]-np.arange(n)[None, :]
        powers = [pt.as_tensor_variable(np.float64(1.))]
        for _ in range(1, n):
            powers.append(powers[-1]*rho)
        transition = (lag >= 0)*pt.stack(powers)[np.maximum(lag, 0)]
        if guide:
            designs, variances, centered = [], [], []
            for i, (_, d) in enumerate(data):
                shared = pt.stack([pt.full((n,), 5.), -4*d['c'], -4*d['e'],
                    np.sin(2*np.pi*d['nights']/21)], axis=1)
                local = pt.concatenate([pt.stack([pt.ones(n)*sd_b,
                    -sd_beta[0]*d['c'], -sd_beta[1]*d['e']], axis=1), sigma_e*transition], axis=1)
                basis = embed_basis(shared, local, i, count, concatenate=pt.concatenate, zeros=pt.zeros)
                designs.extend([pt.mean(basis[d['recall']], axis=1), -basis[d['qindex']]/3])
                variances.extend([pt.ones(len(d['isi']))*(sigma_isi**2+CONFIG['guide_isi_variance_floor']),
                    pt.ones(len(d['quality']))*(sigma_quality**2+CONFIG['guide_quality_variance_floor'])])
                centered.extend([d['isi']-19., d['quality']-(10-19/3)])
            eta = pm.Normal('guide_innovation', 0, 1, dims='latent')
            u, correction, jacobian = gaussian_guide(pt.concatenate(designs, axis=0),
                pt.concatenate(variances), pt.as_tensor_variable(np.concatenate(centered)), eta)
            pm.Deterministic('prior_normal_coordinates', u, dims='latent')
            pm.Deterministic('guide_log_jacobian', jacobian)
            pm.Potential('exact_guide_correction', correction)
            mu_b = pm.Deterministic('mu_b', 19+5*u[0])
            beta = pm.Deterministic('population_beta', 4*u[1:3], dims='arm')
            a = pm.Deterministic('a', u[3])
            local = pt.stack([u[layout['patients'][patient]] for patient in patients])
            b_raw = pm.Deterministic('b_raw', local[:, 0], dims='patient')
            beta_raw = pm.Deterministic('beta_raw', local[:, 1:3], dims=('patient', 'arm'))
            innovation = pm.Deterministic('innovation', local[:, 3:], dims=('patient', 'night'))
        else:
            mu_b = pm.Normal('mu_b', 19, 5)
            beta = pm.Normal('population_beta', 0, 4, dims='arm')
            a = pm.Normal('a', 0, 1)
            b_raw = pm.Normal('b_raw', 0, 1, dims='patient')
            beta_raw = pm.Normal('beta_raw', 0, 1, dims=('patient', 'arm'))
            innovation = pm.Normal('innovation', 0, 1, dims=('patient', 'night'))
        b = pm.Deterministic('b', mu_b+sd_b*b_raw, dims='patient')
        individual = pm.Deterministic('patient_beta', beta+sd_beta*beta_raw, dims=('patient', 'arm'))
        error = pm.Deterministic('error', sigma_e*pt.dot(innovation, transition.T), dims=('patient', 'night'))
        c = np.stack([d['c'] for _, d in data]); e = np.stack([d['e'] for _, d in data])
        z = pm.Deterministic('burden', b[:, None]+a*np.sin(2*np.pi*data[0][1]['nights']/21)
            +error-individual[:, 0, None]*c-individual[:, 1, None]*e, dims=('patient', 'night'))
        for i, (_, d) in enumerate(data):
            pm.Potential(f'isi_likelihood_{i}', log_bin(d['isi'], pt.mean(z[i][d['recall']], axis=1), sigma_isi, 1., 28.).sum())
            if len(d['quality']):
                pm.Potential(f'quality_likelihood_{i}', log_bin(d['quality'], 10-z[i][d['qindex']]/3, sigma_quality, .001, 10.).sum())
        # One shared probability, each unique typed contribution counted once.
        taken = 0 if prior_predictive else sum(d['taken'] for _, d in data)
        deliveries = 0 if prior_predictive else sum(d['deliveries'] for _, d in data)
        observed = 0 if prior_predictive else sum(len(d['quality']) for _, d in data)
        reports = 0 if prior_predictive else sum(d['day'] for _, d in data)
        pm.Beta('p_adherence', np.float64(1+taken), np.float64(1+deliveries-taken))
        pm.Beta('observation_rate', np.float64(1+observed), np.float64(1+reports-observed))
    return model


def build_cohort_borrow(data, sources, configuration, *, guide=True, prior_predictive=False):
    from .borrowing import tensor_marginal, tensor_mixture
    model = build_cohort(data, guide=guide, prior_predictive=prior_predictive)
    with model:
        model.add_coord('source', [s.study_id for s in sources.studies])
        theta = dict(mu_b=model['mu_b'], beta_c=model['population_beta'][0], beta_e=model['population_beta'][1],
            sd_b=model['sd_b'], sd_beta_c=model['sd_beta'][0], sd_beta_e=model['sd_beta'][1],
            p=model['p_adherence'], rho=model['rho'], sigma_e=model['sigma_e'], sigma_isi=model['sigma_isi'], a=model['a'])
        g = pm.Deterministic('source_g', tensor_marginal(theta, configuration['quadrature_order']))
        bias = pm.Normal('source_bias', 0, .5, dims='source')
        tau = pm.HalfNormal('source_tau', configuration['tau_prior_scale'])
        terms, weights = zip(*(tensor_mixture(s.d, s.se, g, bias[i], tau) for i, s in enumerate(sources.studies)), strict=True)
        pm.Deterministic('source_logp', pt.stack(terms), dims='source')
        pm.Deterministic('source_responsibility', pt.stack(weights), dims='source')
        pm.Potential('external_summary_likelihood', pt.stack(terms).sum())
    return model
