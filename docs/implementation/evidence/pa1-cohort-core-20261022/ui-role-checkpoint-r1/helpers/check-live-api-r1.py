"""Real owned copied-service HTTP negatives, memory-only sessions, no fits."""
import ast,copy,http.cookiejar,json,urllib.error,urllib.request
from pathlib import Path
root=Path('artifacts/cohort/live-api-r1');root.mkdir(exist_ok=False)
url='http://127.0.0.1:8784';passwords=None
for node in ast.parse(Path('services/foundation/cli.py').read_text()).body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEMO_PASSWORDS' for t in node.targets):passwords=ast.literal_eval(node.value)
out=[]
class Client:
    def __init__(self,user):
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        status,_=self.call('/api/login',dict(username=user,password=passwords[user]),record=False);assert status==200
    def call(self,path,payload=None,*,key=None,csrf=True,record=True):
        headers={}
        if payload is not None:
            headers={'Content-Type':'application/json','Origin':url}
            if csrf:headers['X-CSRF-Token']=self.call('/api/session',record=False)[1]['csrf']
            if key:headers['Idempotency-Key']=key
        request=urllib.request.Request(url+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        try:
            with self.opener.open(request,timeout=10) as response:status=response.status;value=json.load(response)
        except urllib.error.HTTPError as error:status=error.code;value=json.load(error)
        if record:out.append(dict(path=path,status=status))
        return status,value
alice=Client('alice');bob=Client('bob')
patients=json.loads(Path('artifacts/cohort/ui-fixture-r1/public-setup.json').read_text())['panel']['patient_ids']
workspaces={p:alice.call('/api/patients/'+p)[1] for p in patients}
assert all(w['simulation']['day']==14 for w in workspaces.values())
selection=dict(cohort_id='cohort-live-api-r1',patient_versions={p:w['snapshot']['patient_version'] for p,w in workspaces.items()},
    cutoff=next(iter(workspaces.values()))['snapshot']['cutoff'],source_bundle_id=None,research_run_id=None)
assert alice.call('/api/cohort-analyses/preview',selection,csrf=False)[0]==403
assert bob.call('/api/cohort-analyses/preview',selection)[0]==404
status,v0=alice.call('/api/cohort-analyses/preview',selection);assert status==200 and not v0['executable']
sources=alice.call('/api/patients/'+patients[0]+'/analysis-sources')[1]['bundles'];assert sources
v1selection=dict(selection,source_bundle_id=sources[0]['bundle_id'])
status,v1=alice.call('/api/cohort-analyses/preview',v1selection);assert status==200 and not v1['executable']
assert v0['manifest_sha256']==v1['manifest_sha256'] and v0['cohort_sha256']==v1['cohort_sha256']
assert v0['configuration']!=v1['configuration'] and v0['source_set_sha256'] is None and v1['source_set_sha256']
payload=dict(selection,approved_manifest_sha256=v0['manifest_sha256'])
status,closed=alice.call('/api/cohort-analyses',payload,key='cohort-live-api-closed-r1');assert status==409 and 'qualification' in closed['detail']
assert alice.call('/api/cohort-analyses',payload,key='cohort-live-api-closed-r1')[0]==409
tampered=dict(payload,approved_manifest_sha256='0'*64)
assert alice.call('/api/cohort-analyses',tampered,key='cohort-live-api-tamper-r1')[0]==409
assert alice.call('/api/cohort-analyses/preview',dict(selection,research_run_id='untrusted-caller-string'))[0]==409
incomplete=copy.deepcopy(selection);incomplete['patient_versions'].pop(patients[0])
assert alice.call('/api/cohort-analyses/preview',incomplete)[0]==422
stale=copy.deepcopy(selection);stale['patient_versions'][patients[0]]-=1
assert alice.call('/api/cohort-analyses/preview',stale)[0]==409
# Actual intervening clinical-data update through ordinary API, never direct DB injection.
path='/api/patients/'+patients[0]
before=workspaces[patients[0]]['snapshot']['patient_version']
status,advanced=alice.call(path+'/advance',dict(expected_version=before,mode='day'),key='cohort-live-api-stale-update-r1')
assert status==200 and advanced['day']==15
assert alice.call('/api/cohort-analyses/preview',selection)[0]==409
after=alice.call(path)[1]['snapshot']['patient_version'];assert after>before
result=dict(source='78c01ca6fe1dc46ec6a2e2afcce6ce297d573fdc',real_http_checks=out,
    v0=dict(manifest_sha256=v0['manifest_sha256'],cohort_sha256=v0['cohort_sha256'],configuration=v0['configuration'],executable=False),
    v1=dict(manifest_sha256=v1['manifest_sha256'],cohort_sha256=v1['cohort_sha256'],configuration=v1['configuration'],source_set_sha256=v1['source_set_sha256'],executable=False),
    stale_update=dict(patient=patients[0],before_version=before,after_version=after,day=15),
    limitations='No executable bypass, claim, fitted result or positive completed comparison. Sessions/CSRF/cookies never persisted.')
(root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status='PASS',csrf=403,owner=404,closed=409,incomplete=422,stale_update=result['stale_update'],v0_v1_same_H=True)),flush=True)
