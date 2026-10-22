"""Joint standard-normal coordinates, usable without importing a sampler."""
import numpy as np


def coordinate_slices(patient_ids, nights):
    if list(patient_ids) != sorted(set(patient_ids)) or not patient_ids or nights < 14:
        raise ValueError('distinct sorted patients and complete baseline grid required')
    width = nights+3
    return dict(shared=slice(0, 4), patients={patient: slice(4+i*width, 4+(i+1)*width)
        for i, patient in enumerate(patient_ids)}, dimension=4+len(patient_ids)*width)


def embed_basis(shared, local, index, count, *, concatenate=np.concatenate, zeros=np.zeros):
    """Shared four columns occur once, with disjoint local columns per patient."""
    if not 0 <= index < count:
        raise ValueError('invalid patient coordinate index')
    rows, width = local.shape
    return concatenate([shared, zeros((rows, index*width)), local,
                        zeros((rows, (count-index-1)*width))], axis=1)


def patient_parameters(posterior, patient_id):
    """Preserve chain/draw axes; never average effects across cohort members."""
    selected = posterior.sel(patient=patient_id)
    result = {name: np.asarray(selected[name].transpose('chain', 'draw').values)
              for name in ('b', 'a', 'rho', 'sigma_e', 'sigma_isi', 'p_adherence')}
    beta = selected['patient_beta'].transpose('chain', 'draw', 'arm').values
    result.update(beta_c=beta[..., 0], beta_e=beta[..., 1],
        current_e=selected['error'].transpose('chain', 'draw', 'night').values[..., -1])
    return result
