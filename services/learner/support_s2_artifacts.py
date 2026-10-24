"""Learner-only bounded S2 NetCDF writer and actual-byte semantic validator.

No foundation import, duplicate NPZ, extract-all or posterior read on host.
These functions require future installed-API/binary corruption qualification.
"""
import hashlib
from contracts.domain.analysis import sha
from contracts.domain.support_s2_native import (FEATURES, MONITORED, STATS, SCHEMA_REF,
    ownership, variable_schema, dimension_bound, BinarySemantics)


def file_digest(path,cap):
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=cap:
        raise ValueError('S2_regular_named_posterior_file_cap_required')
    digest=hashlib.sha256();total=0
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(65536),b''):
            total+=len(chunk)
            if total>cap:raise ValueError('S2_posterior_grew_over_file_cap')
            digest.update(chunk)
    if total!=path.stat().st_size:raise ValueError('S2_posterior_changed_during_validation')
    return digest.hexdigest(),total


def attrs(product):
    return dict(schema_sha256=SCHEMA_REF['sha256'],
        input_sha256=sha(product.model_dump(mode='json')),ownership_sha256=sha(ownership(product)))


def dimensions(product):
    cutoff=product.initial.export.provenance.cutoff_day
    return dict(chain=4,draw=product.draws,patient=12,feature=4,
        **{'night_'+str(i):cutoff for i in range(12)})


def coordinate_labels(product):
    cutoff=product.initial.export.provenance.cutoff_day
    return dict(chain=list(range(4)),draw=list(range(product.draws)),
        patient=[m.patient_id for m in product.initial.export.provenance.members],feature=list(FEATURES),
        **{'night_'+str(i):list(range(1,cutoff+1)) for i in range(12)})


def write(trace,directory,product, *, check):
    import numpy as np
    import xarray as xr
    cutoff=product.initial.export.provenance.cutoff_day
    bound=dimension_bound(cutoff,product.draws)  # before copy/materialization
    check();schema=variable_schema(cutoff)
    posterior=trace['posterior'].to_dataset().copy(deep=False)
    if set(posterior.data_vars)!=set(MONITORED):raise ValueError('S2_posterior_inventory_changed')
    labels=coordinate_labels(product)
    for name,expected in labels.items():
        if name not in posterior.coords or np.asarray(posterior.coords[name].values).tolist()!=expected:
            raise ValueError('S2_original_sampler_coordinate_labels_changed')
    # Fixed-width ASCII removes NetCDF VLEN allocation ambiguity. Every label
    # is already an admitted <=128-character ASCII identifier/feature name.
    posterior=posterior.assign_coords(patient=np.asarray(labels['patient'],dtype='S128'),
        feature=np.asarray(labels['feature'],dtype='S128'))
    source=trace['sample_stats'].to_dataset()
    if not {'energy','lp','diverging','tree_depth','warning'}<=set(source.data_vars):
        raise ValueError('S2_sampler_statistics_incomplete')
    stats=source[['energy','lp','diverging','tree_depth']].copy(deep=False)
    warning=np.asarray(source['warning'].values)
    if warning.shape!=(4,product.draws):raise ValueError('S2_warning_axes_mismatch')
    stats['sampler_warning']=(('chain','draw'),np.asarray([v is not None for v in warning.flat],dtype=bool).reshape(warning.shape))
    # Record semantic bool/int exactly. Continuous values are never recast to
    # hide precision changes. Unsupported sampler dtypes refuse below.
    for name in ('diverging','sampler_warning'):
        if np.asarray(stats[name].values).dtype!=np.dtype('bool'):
            raise ValueError('S2_boolean_sampler_stat_required')
    if np.asarray(stats['tree_depth'].values).dtype!=np.dtype('int64'):
        raise ValueError('S2_int64_tree_depth_required')
    for group,dataset in (('posterior',posterior),('sample_stats',stats)):
        dataset.attrs={}
        for name,value in dataset.data_vars.items():
            value.attrs={'unit':schema[group][name]['unit']}
            value.encoding={}
        for coordinate in dataset.coords.values():
            coordinate.attrs={};coordinate.encoding={}
    tree=xr.DataTree.from_dict({'/':xr.Dataset(attrs=attrs(product)),
        '/posterior':posterior,'/sample_stats':stats})
    path=directory/'posterior.nc'
    if path.exists():raise ValueError('S2_immutable_artifact_must_not_be_overwritten')
    check()
    # No compression/duplicate array: on-disk and semantic budgets are explicit.
    encoding={group:{name:{'_FillValue':None,'zlib':False,'shuffle':False} for name in dataset.data_vars}
        for group,dataset in (('/posterior',posterior),('/sample_stats',stats))}
    encoding['/posterior'].update({name:dict(dtype='S1',char_dim_name=name+'_label_byte') for name in ('patient','feature')})
    tree.to_netcdf(path,engine='netcdf4',encoding=encoding)
    check();file_digest(path,bound['file_cap'])
    # Producer-to-binary roundtrip, all jointly aligned values, one bounded
    # variable at a time. No independent coordinate ordering or draw mapping.
    for group,original in (('posterior',posterior),('sample_stats',stats)):
        with xr.open_dataset(path,engine='netcdf4',group=group,cache=False) as saved:
            for name in schema[group]:
                check()
                if not np.array_equal(original[name].values,saved[name].values):
                    raise ValueError('S2_producer_binary_roundtrip_value_changed')
    return validate(directory,product,check=check)


def header(path,product):
    """Inspect raw dimension/dtype declarations before xarray allocates data."""
    from netCDF4 import Dataset
    cutoff=product.initial.export.provenance.cutoff_day
    schema=variable_schema(cutoff);sizes=dimensions(product)
    with Dataset(path,'r') as root:
        if (set(root.groups)!={'posterior','sample_stats'} or root.variables or root.dimensions
                or set(root.ncattrs())!=set(attrs(product))
                or any(root.getncattr(k)!=v for k,v in attrs(product).items())):
            raise ValueError('S2_closed_NetCDF_groups_or_identity_attrs_changed')
        for group,variables in schema.items():
            value=root.groups[group]
            coordinates=set().union(*(set(v['dims']) for v in variables.values()))
            string_axes={'patient_label_byte','feature_label_byte'} if group=='posterior' else set()
            if (value.groups or value.ncattrs() or set(value.variables)!=set(variables)|coordinates
                    or set(value.dimensions)!=coordinates|string_axes
                    or any(value.dimensions[n].isunlimited() or len(value.dimensions[n])!=sizes[n] for n in coordinates)
                    or any(value.dimensions[n].isunlimited() or len(value.dimensions[n])!=128 for n in string_axes)):
                raise ValueError('S2_closed_NetCDF_variable_or_axis_bound_changed')
            for name,expected in variables.items():
                actual=value.variables[name]
                if any(bool(v) for k,v in actual.filters().items() if k!='complevel'):
                    raise ValueError('S2_uncompressed_artifact_policy_required')
                dtype=str(actual.dtype)
                # NetCDF4 encodes xarray bool as int8 with dtype='bool'.
                is_bool=(dtype=='int8' and getattr(actual,'dtype',None) is not None
                    and 'dtype' in actual.ncattrs() and actual.getncattr('dtype')=='bool')
                expected_attrs={'unit','dtype'} if expected['dtype']=='bool' else {'unit'}
                if (list(actual.dimensions)!=expected['dims'] or set(actual.ncattrs())!=expected_attrs
                        or actual.getncattr('unit')!=expected['unit']
                        or (not is_bool if expected['dtype']=='bool' else dtype!=expected['dtype'])):
                    raise ValueError('S2_NetCDF_variable_dtype_dims_units_changed')
            for name in coordinates:
                value_coordinate=value.variables[name]
                expected_dims=(name,name+'_label_byte') if name in ('patient','feature') else (name,)
                if value_coordinate.dimensions!=expected_dims or value_coordinate.ncattrs():
                    raise ValueError('S2_NetCDF_coordinate_declaration_changed')
                if name not in ('patient','feature') and str(value_coordinate.dtype)!='int64':
                    raise ValueError('S2_NetCDF_original_coordinate_dtype_changed')
                if name in ('patient','feature') and str(value_coordinate.dtype)!='|S1':
                    raise ValueError('S2_NetCDF_fixed_width_ASCII_coordinate_required')


def validate(directory,product, *, check):
    import numpy as np
    import xarray as xr
    cutoff=product.initial.export.provenance.cutoff_day
    bound=dimension_bound(cutoff,product.draws)
    path=directory/'posterior.nc'
    check();before,length=file_digest(path,bound['file_cap']);header(path,product);check()
    labels=coordinate_labels(product);schema=variable_schema(cutoff)
    for group,variables in schema.items():
        with xr.open_dataset(path,engine='netcdf4',group=group,cache=False) as dataset:
            coordinates=set().union(*(set(v['dims']) for v in variables.values()))
            if set(dataset.data_vars)!=set(variables) or set(dataset.coords)!=coordinates:
                raise ValueError('S2_binary_group_inventory_changed')
            for name in coordinates:
                check();coordinate=np.asarray(dataset.coords[name].values)
                if name in ('patient','feature'):
                    if coordinate.dtype!=np.dtype('S128'):raise ValueError('S2_fixed_width_coordinate_dtype_changed')
                    actual=[v.decode('ascii') for v in coordinate.tolist()]
                else:actual=coordinate.tolist()
                if actual!=labels[name]:raise ValueError('S2_joint_chain_draw_patient_feature_night_labels_changed')
            for name,expected in variables.items():
                check();value=dataset[name]
                # One bounded variable at a time; never load the full posterior.
                array=np.asarray(value.values)
                if (list(value.dims)!=expected['dims'] or str(array.dtype)!=expected['dtype']
                        or value.attrs!={'unit':expected['unit']} or not np.all(np.isfinite(array))):
                    raise ValueError('S2_binary_finite_dtype_axes_units_required')
                if name in ('s_alpha','s_tau','s_e','s_Q') and np.any(array<=0):
                    raise ValueError('S2_scale_outside_original_prior_support')
                if name=='rho' and np.any((array<=-.95)|(array>=.95)):
                    raise ValueError('S2_continuous_rho_prior_support_changed')
                if name=='tree_depth' and np.any((array<0)|(array>12)):
                    raise ValueError('S2_sampler_depth_out_of_bounds')
    # Validate hierarchy/current-error ownership using aligned slices from the
    # same file. This detects rehashed reorders of derived joint quantities.
    with xr.open_dataset(path,engine='netcdf4',group='posterior',cache=False) as posterior:
        for i in range(12):
            check()
            for name,mu,scale,latent in (('alpha','mu_alpha','s_alpha','z'),('tau','mu_tau','s_tau','u')):
                expected=posterior[mu].values+posterior[scale].values*posterior[latent].isel(patient=i).values
                if not np.allclose(posterior[name].isel(patient=i).values,expected,rtol=1e-12,atol=1e-12):
                    raise ValueError('S2_joint_hierarchy_alignment_corruption')
            error=posterior['error_'+str(i)]
            if not np.array_equal(posterior['e_T'].isel(patient=i).values,error.isel({'night_'+str(i):-1}).values):
                raise ValueError('S2_frozen_terminal_error_alignment_corruption')
            previous=np.zeros((4,product.draws),dtype=np.float64)
            for night in range(cutoff):
                expected=posterior['rho'].values*previous+posterior['s_e'].values*posterior['epsilon_'+str(i)].isel({'night_'+str(i):night}).values
                actual=error.isel({'night_'+str(i):night}).values
                if not np.allclose(actual,expected,rtol=1e-10,atol=1e-10):
                    raise ValueError('S2_joint_latent_recurrence_alignment_corruption')
                previous=actual
    check();after,after_length=file_digest(path,bound['file_cap'])
    if (before,length)!=(after,after_length):raise ValueError('S2_artifact_changed_during_binary_roundtrip')
    return BinarySemantics.model_validate(dict(schema_version='s2-native-binary-v1',posterior_schema=SCHEMA_REF,
        input_sha256=attrs(product)['input_sha256'],ownership_sha256=attrs(product)['ownership_sha256'],
        chains=4,draws=product.draws,cutoff=cutoff,artifact=dict(path='posterior.nc',bytes=length,
            sha256=after,uncompressed_bytes=bound['uncompressed_bytes']),roundtrip=True))


def corruption_controls(directory,product, *, check,retained_bytes):
    """Future isolated qualification: mutate actual worker bytes, rehash, refuse.

    Each copy is temporary and bounded; exactly one exists at a time. No host
    invocation is authorized. Accepted original posterior is never overwritten.
    """
    import shutil
    import tempfile
    from pathlib import Path
    from netCDF4 import Dataset
    from contracts.domain.support_s2_native import TOTAL_CAP,RESULT_CAP
    bound=dimension_bound(product.initial.export.provenance.cutoff_day,product.draws)
    _,original_bytes=file_digest(directory/'posterior.nc',bound['file_cap'])
    # Caller supplies owned total custody for all retained attempt products.
    # Reserve a full bounded copy before creating it. If a large extension
    # leaves no scratch allowance, refuse; never enlarge the operation cap.
    if (type(retained_bytes) is not int or retained_bytes<original_bytes
            or retained_bytes+bound['file_cap']+2*RESULT_CAP>TOTAL_CAP):
        raise ValueError('S2_corruption_control_retained_plus_scratch_cap')
    results={}
    for case in ('units','chain_labels','patient_labels','nonfinite','joint_alignment','extra_variable'):
        check()
        with tempfile.TemporaryDirectory(prefix='s2-corruption-',dir=directory) as tmp:
            candidate=Path(tmp);shutil.copyfile(directory/'posterior.nc',candidate/'posterior.nc')
            with Dataset(candidate/'posterior.nc','r+') as root:
                group=root.groups['posterior']
                if case=='units':group.variables['tau'].setncattr('unit','wrong')
                elif case=='chain_labels':group.variables['chain'][0]=7
                elif case=='patient_labels':group.variables['patient'][0,:]=b'X'
                elif case=='nonfinite':group.variables['rho'][0,0]=float('nan')
                elif case=='joint_alignment':group.variables['e_T'][0,0,0]+=1
                else:group.createVariable('foreign','f8',('chain','draw'))
            # A new digest alone must not make any semantic corruption admissible.
            file_digest(candidate/'posterior.nc',bound['file_cap'])
            try:validate(candidate,product,check=check)
            except ValueError:results[case]='refused'
            else:raise ValueError('S2_binary_corruption_was_admitted')
    return results
