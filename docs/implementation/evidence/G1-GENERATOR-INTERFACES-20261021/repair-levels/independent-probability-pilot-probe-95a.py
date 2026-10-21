"""Independent raw-admission reference mutation; no producer execution."""
import copy,json,sys
sys.path.insert(0,'tests/run_contracts')
import test_probability_admission as suite
from contracts.runs.common import canonical,sha256
from contracts.runs.private_admission import verify_truth
class Done(Exception):pass
def wrapper(reqraw,resraw,root,**kwargs):
 verify_truth(reqraw,resraw,root,**kwargs)
 print('VALID_RAW_CONTROL_ADMITTED',flush=True)
 bad=json.loads(resraw)
 for p in bad['interruption_precision']:
  if not p['component'].endswith('conditional_isi'):
   p['matched_pilot'].update(id='unrelated-pilot',path='missing/probability-pilot.json',sha256='f'*64,bytes=123)
 raw=canonical(bad)
 try:verify_truth(reqraw,raw,root,**(kwargs|dict(response_sha256=sha256(raw))))
 except Exception as e:print('MISSING_PROBABILITY_MATCHED_PILOT_REJECTED',repr(e),flush=True)
 else:print('MISSING_PROBABILITY_MATCHED_PILOT_ADMITTED',flush=True)
 raise Done()
suite.verify_truth=wrapper
try:suite.ProbabilityAdmission().test_authenticated_complete_paired_fixture_roundtrip_and_binding_faults()
except Done:pass
