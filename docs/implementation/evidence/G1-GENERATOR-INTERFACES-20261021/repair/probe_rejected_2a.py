"""Reproduce independent adverse mutations on unchanged rejected2a source."""
import copy
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'tests/run_contracts'))
import test_probability_admission as fixture
from contracts.runs.common import canonical,sha256
from contracts.runs.probability import truth_statistics


def main():
    original=fixture.verify_truth;observations=[];done=False
    def wrapper(request_raw,response_raw,root,**kwargs):
        nonlocal done
        result=original(request_raw,response_raw,root,**kwargs)
        data=json.loads(response_raw)
        if not done and data['status']=='computed':
            done=True
            mutations=[]
            bad=copy.deepcopy(data)
            for index in (3,7):
                bad['interruption_precision'][index]['smallest_estimator_se']=999.
                bad['interruption_precision'][index]['matched_pilot'].update(path='missing/pilot.json',sha256='f'*64)
            mutations.append(('nonexistent_symptom_pilot_and_inflated_se',bad))
            bad=copy.deepcopy(data)
            for arm in ('intervention','comparator'):
                bad['result'][arm]['death_times_days']=[999.]
                bad['result'][arm]['admission_times_days']=[]
                bad['result'][arm]['conditional_isi']['isi']['standard_error']=999.
            mutations.append(('conflicting_public_event_times_and_symptom_se',bad))
            for name,bad in mutations:
                raw=canonical(bad)
                try:original(request_raw,raw,root,**(kwargs|dict(response_sha256=sha256(raw))))
                except Exception as error:observations.append(dict(probe=name,admitted=False,error=repr(error)))
                else:observations.append(dict(probe=name,admitted=True))
        return result
    fixture.verify_truth=wrapper
    fixture.ProbabilityAdmission().test_authenticated_complete_paired_fixture_roundtrip_and_binding_faults()
    counts=np.repeat((5000+np.tile([-1,1],16))[:,None],6,axis=1)
    try:
        result=truth_statistics(counts,conditional=False,epsilon=np.repeat(.0001,6))
        observations.append(dict(probe='iid_dispersion_disagreement',admitted=True,mcse=result['mcse'].tolist(),pooled_iid_mcse=result['pooled_iid_mcse'].tolist(),epsilon=.0001))
    except Exception as error:observations.append(dict(probe='iid_dispersion_disagreement',admitted=False,error=repr(error)))
    print(json.dumps(dict(rejected_head='2a7726be23864cf9c933295f1d33da3d6fbedd1b',fixture_only=True,observations=observations),indent=2))


if __name__=='__main__':main()
