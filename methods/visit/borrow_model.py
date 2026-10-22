"""Extend the original exact-guide model with one normalized source block."""
import numpy as np
import pymc as pm
import pytensor.tensor as pt
from .model import build
from .borrowing import tensor_marginal,tensor_mixture


def build_joint(data,sources,configuration,*,guide=True,prior_predictive=False):
    if prior_predictive and guide:raise ValueError('Unconditioned prior simulation requires the original coordinates.')
    # The original model analytically updates adherence through Beta counts.
    # For source PRIOR simulation alone restore its declared Beta(1,1), while
    # keeping all observed grids/exposures and every posterior path unchanged.
    prior_data=dict(data,taken=0,deliveries=0) if prior_predictive else data
    model=build(prior_data,guide=guide)
    with model:
        model.add_coord('source',[s.study_id for s in sources.studies])
        theta=dict(mu_b=model['mu_b'],beta_c=model['population_beta'][0],beta_e=model['population_beta'][1],
            sd_b=model['sd_b'],sd_beta_c=model['sd_beta'][0],sd_beta_e=model['sd_beta'][1],
            p=model['p_adherence'],rho=model['rho'],sigma_e=model['sigma_e'],sigma_isi=model['sigma_isi'],a=model['a'])
        g=pm.Deterministic('source_g',tensor_marginal(theta,configuration['quadrature_order']))
        bias=pm.Normal('source_bias',0,.5,dims='source')
        tau=pm.HalfNormal('source_tau',configuration['tau_prior_scale'])
        terms,weights=[],[]
        for i,study in enumerate(sources.studies):
            term,weight=tensor_mixture(study.d,study.se,g,bias[i],tau)
            terms.append(term);weights.append(weight)
        pm.Deterministic('source_logp',pt.stack(terms),dims='source')
        pm.Deterministic('source_responsibility',pt.stack(weights),dims='source')
        pm.Potential('external_summary_likelihood',pt.stack(terms).sum())
    return model
