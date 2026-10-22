"""Postfit all-draw resolution and frozen chain-balanced reference checks."""
import hashlib
from pathlib import Path
import time
import numpy as np
from scipy.stats import norm
from contracts.domain.analysis import canonical
from contracts.domain.borrowing import seed_value
from .borrowing import FIELDS,marginal
from .source_reference import forward


def theta_arrays(posterior):
    result={name:np.asarray(posterior[source].values) for name,source in [('mu_b','mu_b'),('sd_b','sd_b'),
        ('p','p_adherence'),('rho','rho'),('sigma_e','sigma_e'),('sigma_isi','sigma_isi'),('a','a')]}
    result.update(beta_c=np.asarray(posterior['population_beta'].values[...,0]),beta_e=np.asarray(posterior['population_beta'].values[...,1]),
        sd_beta_c=np.asarray(posterior['sd_beta'].values[...,0]),sd_beta_e=np.asarray(posterior['sd_beta'].values[...,1]))
    return result


def select_indices(g,vmax):
    if g.shape!=vmax.shape or len(g.shape)!=2 or g.shape[0]!=4 or g.shape[1]<8 or not np.isfinite(g).all() or not np.isfinite(vmax).all():
        raise ValueError('four finite chains with at least8 saved draws required')
    selected=[];n=g.shape[1]
    for chain in range(4):
        candidates=[int(np.floor((n-1)*q)) for q in (1/8,3/8,5/8,7/8)]
        candidates.extend([int(g[chain].argmin()),int(g[chain].argmax()),int(vmax[chain].argmin()),int(vmax[chain].argmax())])
        indices=list(dict.fromkeys(candidates))
        for i in range(n):
            if len(indices)==8:break
            if i not in indices:indices.append(i)
        selected.extend(dict(chain=chain,draw=i) for i in indices)
    return selected


def validate(posterior,product,configuration,out,stage):
    started=time.monotonic();cap=configuration['bridge_postfit_seconds'];deadline=started+cap
    order=configuration['quadrature_order'];arrays=theta_arrays(posterior);shape=arrays['mu_b'].shape
    epsilon=min(min(.05,.1*s.se) for s in product.sources.studies)
    g=np.empty(shape);double=np.empty(shape);vmax=np.empty(shape)
    def expired():return time.monotonic()>deadline
    metadata=dict(status='bridge-precision-unmet',order=order,double_order=2*order,epsilon=epsilon,
        resolution_tolerance=epsilon/4,family_id=product.attempt_id+':'+configuration['reference_family'],
        information_set='independent public fitted-model source marginal, not PA6 private conditional truth',
        seconds_cap=cap,alpha=.01,bonferroni_tests=4320,z=float(norm.isf(.01/(2*4320))),selected=[],points=[])
    def save():
        metadata['seconds']=time.monotonic()-started
        (out/'bridge-precision.json').write_text(canonical(metadata)+'\n')
    for chain in range(shape[0]):
        for draw in range(shape[1]):
            if expired():metadata['reason']='all-draw-resolution-timeout';save();return metadata
            theta={name:float(array[chain,draw]) for name,array in arrays.items()}
            g[chain,draw],vmax[chain,draw]=marginal(theta,order,details=True)
            double[chain,draw]=marginal(theta,2*order)
    delta=np.abs(g-double)
    metadata.update(retained_draws=int(g.size),maximum_resolution_difference=float(delta.max()),
        resolution_pass=bool(np.isfinite(delta).all() and np.all(delta<=epsilon/4)),
        resolution_failure_count=int(np.sum(delta>epsilon/4)))
    np.savez_compressed(out/'bridge-marginals.npz',g=g,double_g=double,vmax=vmax,chain=np.arange(shape[0]),draw=np.arange(shape[1]))
    metadata['selected']=select_indices(g,vmax)
    # Freeze all32 indices and actual reference keys before any MC results.
    for selected in metadata['selected']:
        selected['seeds']=[seed_value('pa3-bridge-20261021-v1',-1,selected['chain'],batch,selected['draw'],
            (product.history.cutoff-product.history.origin).days,'bridge-reference:'+product.attempt_id+':'+str(product.numerical_seeds.bridge_reference)) for batch in range(8)]
    seeds=[s for row in metadata['selected'] for s in row['seeds']]
    if len(set(seeds))!=len(seeds):raise ValueError('posterior reference seed collision')
    save();stage(dict(stage='diagnostics'))
    for selected in metadata['selected']:
        chain,draw=selected['chain'],selected['draw'];theta={name:float(array[chain,draw]) for name,array in arrays.items()}
        streams=[np.random.default_rng(seed) for seed in selected['seeds']]
        count=0;total=0.;square=0.;looks=[]
        point=dict(chain=chain,draw=draw,theta=theta,g=float(g[chain,draw]),looks=looks,accepted=False)
        metadata['points'].append(point)
        for size in configuration['bridge_reference_looks']:
            for rng in streams:
                if expired():metadata['reason']='reference-timeout';save();return metadata
                values=forward(theta,size-count,rng);total+=float(values.sum());square+=float(values@values)
                if expired():metadata['reason']='reference-timeout';save();return metadata
            count=size;n=8*count;mean=total/n;se=(max(0.,(square-total*total/n)/(n-1))/n)**.5
            difference=abs(float(g[chain,draw])-mean);upper=difference+metadata['z']*se;lower=max(0.,difference-metadata['z']*se)
            looks.append(dict(per_batch=size,trajectories=n,mean=mean,paired_se=se,upper_error_bound=upper,lower_error_bound=lower,
                reference_pass=upper<=epsilon,significant_discrepancy=lower>epsilon))
            save()
            if upper<=epsilon:break
        point['accepted']=looks[-1]['reference_pass']
        save()
    if expired():metadata['reason']='publication-timeout'
    elif not metadata['resolution_pass']:metadata['reason']='quadrature-resolution-unmet'
    elif any(p['looks'][-1]['significant_discrepancy'] for p in metadata['points']):metadata['reason']='moment-approximation-failure'
    elif not all(p['accepted'] for p in metadata['points']):metadata['reason']='reference-precision-unmet'
    else:metadata.update(status='accepted',reason=None)
    save()
    if expired() and metadata['status']=='accepted':
        metadata.update(status='bridge-precision-unmet',reason='publication-timeout');save()
    return metadata
