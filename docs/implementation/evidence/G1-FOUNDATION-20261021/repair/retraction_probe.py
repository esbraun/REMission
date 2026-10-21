import sys,json
from datetime import timedelta
sys.path.insert(0,'/app/tests/integration/replay')
from test_foundation import FoundationTests,observed
x=FoundationTests();x.setUp()
try:
 out={}
 def ingest(payload,key):
  r=x.client.post('/api/patients/SYN-02/events',json=payload,headers=x.headers(key=key));return [r.status_code,r.json()]
 out['fall']=ingest(observed('review-fall',kind='intercurrent_event'),'fall')
 x.clock.at+=timedelta(seconds=1)
 out['retract']=ingest(observed('review-retraction',kind='intercurrent_event',lineage_id='review-fall',revision=2,supersedes='review-fall',record_status='retracted'),'retract')
 x.clock.at+=timedelta(seconds=1)
 w=x.client.get('/api/patients/SYN-02').json()
 r=x.client.post('/api/patients/SYN-02/state',json={'expected_version':w['snapshot']['patient_version'],'stage':'ASSIGN-02','reason':'Correction reviewed; fall source retracted'},headers=x.headers(key='clear'))
 out['clear']=[r.status_code,r.json()]
 out['after_clear']=x.client.get('/api/patients/SYN-02').json()
 x.clock.at+=timedelta(seconds=1)
 out['unrelated_report']=ingest(observed('review-unrelated'),'unrelated')
 out['after_unrelated']=x.client.get('/api/patients/SYN-02').json()
 print(json.dumps(out,indent=2))
finally:x.tearDown()
