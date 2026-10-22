"""Image-installed, immutable PA3 artifacts. HTTP selects an ID, never a path."""
from pathlib import Path
from contracts.domain.analysis import sha
from contracts.domain.borrowing import APPROVED_BUNDLES,SourceBundle

ROOT=Path(__file__).with_name('studies')


def load_source(bundle_id,cutoff):
    if bundle_id not in APPROVED_BUNDLES:raise ValueError('Unsupported synthetic source bundle ID.')
    path=ROOT/(bundle_id+'.json')
    if path.is_symlink() or not path.is_file():raise ValueError('Approved source artifact is missing.')
    bundle=SourceBundle.model_validate_json(path.read_bytes())
    if sha(bundle.model_dump(mode='json'))!=APPROVED_BUNDLES[bundle_id]:raise ValueError('Approved source artifact checksum changed.')
    return bundle.at_cutoff(cutoff)


def catalog(cutoff):
    result=[]
    for number,bundle_id in enumerate(APPROVED_BUNDLES,1):
        bundle=load_source(bundle_id,cutoff)
        result.append(dict(label=f'Fictional source bundle {number}',**bundle.model_dump(mode='json')))
    return result
