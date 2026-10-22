"""Independent public-model source reference, qualified originally at PA3 prefit.

This full-path code intentionally shares no filters, quadrature or moment
approximation with the deterministic bridge. It is not private generator truth.
"""
import numpy as np
from scipy.special import ndtr


def forward(theta,count,rng):
    baseline=rng.normal(theta['mu_b'],theta['sd_b'],count)
    standard_beta=rng.normal(size=count)
    beta_c=theta['beta_c']+theta['sd_beta_c']*standard_beta
    beta_e=theta['beta_e']+theta['sd_beta_e']*standard_beta
    error=np.zeros(count);carry_c=np.zeros(count);carry_e=np.zeros(count)
    sum_c=np.zeros(count);sum_e=np.zeros(count)
    for night in range(-13,43):
        error=theta['rho']*error+theta['sigma_e']*rng.normal(size=count)
        taken=rng.random(count)<theta['p'] if night>0 else np.zeros(count)
        carry_c=.65*carry_c+.35*taken;carry_e=.8*carry_e+.2*taken
        if night>=29:
            burden=baseline+theta['a']*np.sin(2*np.pi*night/21)+error
            sum_c+=burden-beta_c*carry_c;sum_e+=burden-beta_e*carry_e
    def measured(mean):
        total=np.zeros(count)
        for category in range(1,29):
            total+=(mean>=category-.5) if theta['sigma_isi']==0 else ndtr((mean-(category-.5))/theta['sigma_isi'])
        return total
    return measured(sum_e/14)-measured(sum_c/14)
