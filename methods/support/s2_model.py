"""Native float64 S2 graph SOURCE, no sampler/dispatch/serving activation.

The private graph seam also admits labeled 1/2-member prior-only density
fixtures. Production build always requires the complete prepared12 cohort.
"""
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt
from contracts.domain.support_s2_fit import S2FitProvenance
from methods.measurement import log_bin
from methods.nof1.model import _ar_error
from .s2_data import CohortData

F=np.float64
FEATURES=['prior_available_quality_default7','no_prior_available_quality',
          'previous_six_nights_delivered_prompts','reward_night/84']


def _graph(members,*,original_coordinates=False):
    """Qualification original-coordinate option changes transforms, not law."""
    if pytensor.config.floatX!='float64':raise ValueError('S2 model requires float64')
    coords=dict(patient=[p.patient_id for p in members],feature=FEATURES)
    coords.update({'night_'+str(i):p.nights for i,p in enumerate(members)})
    transform=dict(default_transform=None) if original_coordinates else {}
    with pm.Model(coords=coords) as model:
        mu_alpha=pm.Normal('mu_alpha',F(5.),F(3.))
        mu_tau=pm.Normal('mu_tau',F(0.),F(2.))
        b=pm.Normal('b',F(0.),F(2.),dims='feature')
        s_alpha=pm.HalfNormal('s_alpha',F(2.),**transform)
        s_tau=pm.HalfNormal('s_tau',F(2.),**transform)
        s_e=pm.HalfNormal('s_e',F(2.),**transform)
        s_Q=pm.HalfNormal('s_Q',F(2.),**transform)
        rho=pm.Uniform('rho',F(-.95),F(.95),**transform)
        z=pm.Normal('z',F(0.),F(1.),dims='patient')
        u=pm.Normal('u',F(0.),F(1.),dims='patient')
        alpha=pm.Deterministic('alpha',mu_alpha+s_alpha*z,dims='patient')
        tau=pm.Deterministic('tau',mu_tau+s_tau*u,dims='patient')
        final=[]
        for i,patient in enumerate(members):
            name=str(i)
            epsilon=pm.Normal('epsilon_'+name,F(0.),F(1.),dims='night_'+name)
            error=pm.Deterministic('error_'+name,_ar_error(epsilon,rho,s_e,len(patient.nights)),dims='night_'+name)
            rows=patient.observed
            if rows:
                index=np.asarray([r.index for r in rows],dtype=np.int64)
                x=np.asarray([r.x for r in rows],dtype=np.float64).reshape(-1,4)
                centered=np.asarray([r.action-r.probability for r in rows],dtype=np.float64)
                quality=np.asarray([r.quality for r in rows],dtype=np.float64)
                eta=alpha[i]+pt.dot(x,b)+centered*tau[i]+error[index]
                pm.Potential('quality_likelihood_'+name,log_bin(quality,eta,s_Q,F(.001),F(10.)).sum())
            final.append(error[-1])
        pm.Deterministic('e_T',pt.stack(final),dims='patient')
    return model


def build(data):
    if not isinstance(data,CohortData):raise ValueError('prepared observed S2 cohort required')
    source=S2FitProvenance.model_validate(data.provenance)
    if [p.patient_id for p in data.members]!=[m.patient_id for m in source.members]:
        raise ValueError('production S2 graph requires complete ordered12')
    if any(p.nights!=tuple(range(1,source.cutoff_day+1)) for p in data.members):
        raise ValueError('full missing-night latent grid required')
    return _graph(data.members)
