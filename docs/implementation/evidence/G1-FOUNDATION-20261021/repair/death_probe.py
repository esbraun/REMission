import sys,json
sys.path.insert(0,'/app/tests/integration/replay')
from test_foundation import FoundationTests, observed
x=FoundationTests();x.setUp()
try:
 out={}
 death=observed('review-death',kind='intercurrent_event',event='2026-10-21T11:00:00+00:00',available='2026-10-21T11:00:00+00:00',event_type='death')
 r=x.client.post('/api/patients/SYN-02/events',json=death,headers=x.headers(key='death'));out['death']=[r.status_code,r.json()]
 w=x.client.get('/api/patients/SYN-02').json();out['held']=w['permissions'];out['snapshot']=w['snapshot']
 r=x.client.post('/api/patients/SYN-02/state',json={'expected_version':w['snapshot']['patient_version'],'stage':'ASSIGN-02','reason':'Independent equal-time composition'},headers=x.headers(key='clear'));out['clear']=[r.status_code,r.json()]
 r=x.client.post('/api/patients/SYN-02/approve',json=x.approval(),headers=x.headers(key='approve-after-death'));out['approve']=[r.status_code,r.json()]
 print(json.dumps(out,indent=2))
finally:x.tearDown()
