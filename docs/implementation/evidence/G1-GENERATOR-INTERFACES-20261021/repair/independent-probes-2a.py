import copy,json,sys
import numpy as np
sys.path.insert(0,'tests/run_contracts')
from contracts.runs.probability import pilot_statistics,truth_statistics
from contracts.runs.common import canonical,sha256
from contracts.runs.private_admission import verify_truth as original_verify
import test_probability_admission as suite

k=np.zeros((1000,6),dtype=int);k[:30]=1
s=pilot_statistics(k/30,k,30)
print('ORACLE',json.dumps({v:s[v].tolist() for v in ['mean','sd','sd_mcse','lower','analytic_lower']}))
counts=np.repeat((5000+np.tile([-1,1],16))[:,None],6,axis=1)
t=truth_statistics(counts,conditional=False,epsilon=np.repeat(.0001,6))
print('DISPERSION_ADMITTED',json.dumps({v:t[v].tolist() for v in ['mean','mcse','pooled_iid_mcse']}))

done=False
def wrapper(raw_request,raw_response,root,**kw):
 global done
 if not done:
  done=True
  base=json.loads(raw_response)
  for label in ['missing_symptom_pilot','unbound_symptom_se','wrong_event_times','wrong_symptom_reported_se']:
   bad=copy.deepcopy(base)
   for p in bad['interruption_precision']:
    if p['component'].endswith('conditional_isi'):
     if label=='missing_symptom_pilot':
      p['matched_pilot'].update(id='never-executed',path='missing/symptom-pilot.json',sha256='f'*64,bytes=123)
     if label=='unbound_symptom_se':p['smallest_estimator_se']=1000000.0
   if label=='wrong_event_times':
    for arm in ['intervention','comparator']:
     bad['result'][arm]['death_times_days']=[999.0]
     bad['result'][arm]['admission_times_days']=[]
   if label=='wrong_symptom_reported_se':
    for arm in ['intervention','comparator']:bad['result'][arm]['conditional_isi']['isi']['standard_error']=999.0
   raw=canonical(bad);args={**kw,'response_sha256':sha256(raw)}
   try:original_verify(raw_request,raw,root,**args)
   except Exception as e:print(label,'REJECTED',type(e).__name__,str(e))
   else:print(label,'ADMITTED')
 return original_verify(raw_request,raw_response,root,**kw)
suite.verify_truth=wrapper
suite.ProbabilityAdmission('test_authenticated_complete_paired_fixture_roundtrip_and_binding_faults').test_authenticated_complete_paired_fixture_roundtrip_and_binding_faults()
print('Bounded fixture mutation probes completed; no production execution')
