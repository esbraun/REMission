"""Scientific-process semantic validation of the actual N NetCDF/NPZ bytes.

CORE validates the bounded result JSON and file digests independently. It must
never import this module to inspect scientific arrays during requests or ingest.
"""


def validate(directory,product,effect):
    import numpy as np
    import xarray as xr
    from contracts.domain.nof1_app import MONITORED

    patients=[m.patient_id for m in product.cohort]
    with xr.open_dataset(directory/'posterior.nc',engine='netcdf4',group='posterior') as posterior:
        if (posterior.sizes.get('chain')!=4 or posterior.sizes.get('draw') not in (1000,2000)
                or list(posterior.coords['patient'].values)!=patients
                or not set(MONITORED)<=set(posterior.data_vars)):
            raise ValueError('posterior chain/draw/patient/monitor coordinates mismatch')
        chains,draws=posterior.sizes['chain'],posterior.sizes['draw']
        for name,value in posterior.data_vars.items():
            array=np.asarray(value.values)
            if array.dtype!=np.dtype('float64') or not np.all(np.isfinite(array)):
                raise ValueError('finite float64 posterior variables required: '+name)
        for name in ('b','current_error','p_C','p_M','q'):
            if posterior[name].dims!=('chain','draw','patient'):
                raise ValueError('explicit patient-specific posterior axes required')
        if posterior['patient_amplitude'].dims!=('chain','draw','patient','coefficient'):
            raise ValueError('patient coefficient coordinates mismatch')
        if list(posterior.coords['coefficient'].values)!=['C','E','A','B','R']:
            raise ValueError('complete original hierarchy coefficient coordinates required')
        for i,h in enumerate(product.histories):
            night='night_'+str(i);day=(h.cutoff-h.origin).days
            if not np.array_equal(posterior.coords[night].values,np.arange(-13,day+1)):
                raise ValueError('patient-specific complete public-origin grid required')
    with xr.open_dataset(directory/'posterior.nc',engine='netcdf4',group='sample_stats') as stats:
        if stats.sizes.get('chain')!=chains or stats.sizes.get('draw')!=draws:
            raise ValueError('sampler and posterior axes mismatch')
        for name in ('energy','diverging','tree_depth'):
            if not np.all(np.isfinite(stats[name].values)):raise ValueError('finite sampler artifact required')
        if int(stats['diverging'].sum()) or int(stats['tree_depth'].max())>=12:
            raise ValueError('sampler artifact fails native N gates')
        energy=np.asarray(stats['energy'].transpose('chain','draw'))
        bfmi=np.mean(np.diff(energy,axis=1)**2,axis=1)/np.var(energy,axis=1)
        if not np.all(np.isfinite(bfmi)) or np.any(bfmi<=.3):raise ValueError('sampler artifact BFMI failed')
    with np.load(directory/'expected-contrast.npz',allow_pickle=False) as saved:
        if set(saved.files)!={'effect','chain','draw','target','axes','unit','kind','history_sha256'}:
            raise ValueError('expected contrast artifact fields mismatch')
        delta=saved['effect']
        if (delta.shape!=(chains,draws,1) or delta.dtype!=np.dtype('float64')
                or not np.all(np.isfinite(delta)) or np.any(np.abs(delta)>10)
                or list(saved['axes'])!=['chain','draw','target']
                or list(saved['target'])!=[product.target_id]
                or str(saved['unit'])!='quality_points'
                or str(saved['kind'])!='conditional_expected_assignment_contrast'
                or str(saved['history_sha256'])!=product.history_sha256
                or not np.array_equal(saved['chain'],np.arange(chains))
                or not np.array_equal(saved['draw'],np.arange(draws))):
            raise ValueError('expected contrast artifact target/axes/units/state mismatch')
        actual=[float(delta.mean()),float(delta.std(ddof=1)),*np.quantile(delta,[.025,.975]).tolist()]
        expected=[effect[k] for k in ('mean','sd','lower','upper')]
        if not np.allclose(actual,expected,rtol=1e-12,atol=1e-12):
            raise ValueError('expected contrast artifact/summary mismatch')
    with np.load(directory/'predictive.npz',allow_pickle=False) as saved:
        if set(saved.files)!={'quality','available','chain','draw','target','arm','night','axes','unit','kind','history_sha256'}:
            raise ValueError('predictive artifact fields mismatch')
        quality,available=saved['quality'],saved['available']
        target=next(h for h in product.histories if h.patient_id==product.target_id)
        day=(target.cutoff-target.origin).days
        if (quality.shape!=(chains,draws,1,2,7) or quality.dtype!=np.dtype('float64')
                or not np.all(np.isfinite(quality)) or np.any((quality<0)|(quality>10))
                or not np.allclose(quality*1000,np.round(quality*1000),atol=1e-8,rtol=0)
                or available.shape!=(chains,draws,1,7) or available.dtype!=np.dtype('bool')
                or list(saved['axes'])!=['chain','draw','target','arm','night']
                or list(saved['arm'])!=['MED_A','MED_B'] or list(saved['target'])!=[product.target_id]
                or not np.array_equal(saved['night'],np.arange(day+1,day+8))
                or not np.array_equal(saved['chain'],np.arange(chains))
                or not np.array_equal(saved['draw'],np.arange(draws))
                or str(saved['unit'])!='reported_quality_points' or str(saved['kind'])!='predictive_trajectory'
                or str(saved['history_sha256'])!=product.history_sha256):
            raise ValueError('predictive artifact target/axes/quality/availability mismatch')
    return dict(schema='poc-nof1-file-semantics-v1',status='accepted',chains=chains,draws=draws,
        patients=patients,target_ids=[product.target_id],expected_axes=['chain','draw','target'],
        predictive_axes=['chain','draw','target','arm','night'],
        expected_unit='quality_points',predictive_unit='reported_quality_points')
