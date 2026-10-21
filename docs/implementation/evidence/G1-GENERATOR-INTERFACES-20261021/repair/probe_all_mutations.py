"""Supplemental postrepair adapter; original independent script stays exact.

The original stops at its newly rejected IID call. This separate adapter keeps
all four original mutation labels observable using the repaired valid fixture.
"""
import copy
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'tests/run_contracts'))
import test_probability_admission as suite
from contracts.runs.common import canonical,sha256
from contracts.runs.private_admission import verify_truth as original_verify
from contracts.runs.probability import truth_statistics


def main():
    observations=[];done=False
    counts=np.repeat((5000+np.tile([-1,1],16))[:,None],6,axis=1)
    for epsilon in (.0001,.001):
        try:truth_statistics(counts,conditional=False,epsilon=np.repeat(epsilon,6))
        except Exception as error:observations.append(dict(probe='original_iid_counts',epsilon=epsilon,admitted=False,error=repr(error)))
        else:observations.append(dict(probe='original_iid_counts',epsilon=epsilon,admitted=True))
    def wrapper(raw_request,raw_response,root,**kwargs):
        nonlocal done
        if not done:
            done=True;base=json.loads(raw_response)
            for label in ('missing_symptom_pilot','unbound_symptom_se','wrong_event_times','wrong_symptom_reported_se'):
                bad=copy.deepcopy(base)
                for p in bad['interruption_precision']:
                    if p['component'].endswith('conditional_isi'):
                        if label=='missing_symptom_pilot':p['matched_pilot'].update(id='never-executed',path='missing/symptom-pilot.json',sha256='f'*64,bytes=123)
                        if label=='unbound_symptom_se':p['smallest_estimator_se']=1000000.
                if label=='wrong_event_times':
                    for arm in ('intervention','comparator'):
                        bad['result'][arm]['death_times_days']=[999.];bad['result'][arm]['admission_times_days']=[]
                if label=='wrong_symptom_reported_se':
                    for arm in ('intervention','comparator'):bad['result'][arm]['conditional_isi']['isi']['standard_error']=999.
                raw=canonical(bad)
                try:original_verify(raw_request,raw,root,**(kwargs|dict(response_sha256=sha256(raw))))
                except Exception as error:observations.append(dict(probe=label,admitted=False,error=repr(error)))
                else:observations.append(dict(probe=label,admitted=True))
        return original_verify(raw_request,raw_response,root,**kwargs)
    suite.verify_truth=wrapper
    suite.ProbabilityAdmission().test_authenticated_complete_paired_fixture_roundtrip_and_binding_faults()
    print(json.dumps(dict(kind='supplemental_adapter_not_original_probe',original_script_blob='7b16ef9cfb52cfd9304c6802eb2c8a8e8463ff3f',pure_wire_fixture=True,observations=observations),indent=2))
    if any(row['admitted'] for row in observations):raise SystemExit(1)


if __name__=='__main__':main()
