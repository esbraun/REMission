import copy,json,math,statistics,sys
import numpy as np
sys.path.insert(0,'tests/run_contracts')
import contracts.runs.private as private
import test_repair_precision as suite
from fixtures import load,wire_investigation
from contracts.runs.probability import symptom_pilot_statistics,truth_statistics

rows=[[12.,16.]]*500+[[10.,14.,18.]]*500
ses=[statistics.stdev(x)/math.sqrt(len(x)) for x in rows]
rms=math.sqrt(statistics.mean([x*x for x in ses]));mc=statistics.stdev([x*x for x in ses])/(2*rms*math.sqrt(1000))
actual=symptom_pilot_statistics(rows)
expected=dict(rms_se=rms,rms_mcse=mc,rms_lower=rms-1.645*mc,binding=min(min(ses),rms-1.645*mc))
assert all(abs(actual[k]-v)<1e-12 for k,v in expected.items())
print('INDEPENDENT_SYMPTOM_ORACLE',json.dumps(expected))
counts=np.repeat((5000+np.tile([-1,1],16))[:,None],6,axis=1)
for epsilon,evidence in [(.0001,wire_investigation(counts)),(.001,None)]:
 try:truth_statistics(counts,conditional=False,epsilon=np.repeat(epsilon,6),investigation=evidence)
 except ValueError as e:print('IID_EXPECTED_REJECTION',epsilon,str(e))
 else:raise AssertionError('IID fault admitted')

original=private.validate_truth_response;observed=False
def wrapper(request,response,**kwargs):
 global observed
 result=original(request,response,**kwargs)
 if not observed and response.status=='computed' and response.conditional_accuracy is not None:
  observed=True
  changed=response.model_dump(mode='json')
  changed['conditional_accuracy']['particle_levels']=[1024,4096,16384,65536]
  changed=load(private.TruthResponse,changed)
  try:original(request,changed,**kwargs)
  except ValueError as e:print('MISMATCHED_SYMPTOM_LEVELS_REJECTED',str(e))
  else:print('MISMATCHED_SYMPTOM_LEVELS_ADMITTED',json.dumps(dict(symptom_pilot_levels=3,response_accuracy_levels=changed.conditional_accuracy.particle_levels)))
 return result
private.validate_truth_response=wrapper
suite.RepairPrecision().test_conditional_symptom_accuracy_and_later_actual_se_use_isi_epsilon()
assert observed
print('Completed bounded post-authentication validator probe, no producer execution')
