"""Read-only replay of committed actual artifacts and source/data checksums."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import numpy as np
from contracts.artifacts.ope import OPERequest
from methods.ope.functional import evaluate_files

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'docs/implementation/evidence/G0-LIB/DR'


def main():
    hashes=json.loads((E/'source-manifest.json').read_bytes())
    for name,digest in hashes.items():
        assert hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,name
    recipe=json.loads((E/'recipe-source-sha256.json').read_bytes())
    assert hashlib.sha256((ROOT/recipe['path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==recipe['sha256']
    root=E/'exchange';request=OPERequest.model_validate_json((root/'request.json').read_bytes())
    for path,snapshot in [('methods/ope/nuisance.py','nuisance-executed-source.py'),
                          ('methods/ope/functional.py','functional-executed-source.py'),
                          ('tooling/library/dr_stage.py','stage-executed-source.py')]:
        assert hashlib.sha256((root/snapshot).read_bytes()).hexdigest()==hashes[path]
    for filename,expected in [('training.json',request.bindings.training_sha256),('plan.json',request.bindings.plan_sha256),
                              ('model.joblib',request.bindings.model_sha256)]:
        assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==expected,filename
    protocol=json.loads((root/'protocol.json').read_bytes())
    assert hashlib.sha256((E/'logging-definition.json').read_bytes()).hexdigest()==protocol['behavior']['sha256']
    result=evaluate_files(root,request).model_dump(mode='json');recorded=json.loads((E/'result.json').read_bytes())
    assert result==recorded,'actual committed score/paired-bootstrap replay drift'
    assert sum(result['patient_counts'])==result['eligible_windows']==60
    np.testing.assert_allclose(np.sum(result['patient_score_sums'],axis=0)/60,result['dr'],atol=1e-12,rtol=0)
    with tempfile.TemporaryDirectory() as directory:
        mutated=Path(directory)
        for source in root.iterdir():shutil.copyfile(source,mutated/source.name)
        shutil.copyfile(root/'rewards-mutated.json',mutated/'rewards.json')
        req=OPERequest.model_validate_json((root/'request-mutated.json').read_bytes())
        assert evaluate_files(mutated,req).model_dump(mode='json')==json.loads((E/'result-reward-mutation.json').read_bytes())
    print('PASS: all actual raw input/model/source hashes,60-window pooled sums/counts and2000 paired fixed-seed replicates replay exactly')


if __name__=='__main__':main()
