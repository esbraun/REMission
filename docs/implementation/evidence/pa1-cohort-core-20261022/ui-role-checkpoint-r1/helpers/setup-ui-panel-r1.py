"""Owned fixture setup through normal API, not browser-flow acceptance."""
import ast,datetime,hashlib,http.cookiejar,json,urllib.request,uuid
from pathlib import Path
root=Path('artifacts/cohort/ui-fixture-r1');root.mkdir(exist_ok=False)
passwords=None
for node in ast.parse(Path('services/foundation/cli.py').read_text()).body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEMO_PASSWORDS' for t in node.targets):passwords=ast.literal_eval(node.value)
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
url='http://127.0.0.1:8784';calls=[]
def api(path,payload=None,key=None):
    headers={}
    if payload is not None:
        csrf=api('/api/session')['csrf'];headers.update({'Content-Type':'application/json','Origin':url,'X-CSRF-Token':csrf})
        if key:headers['Idempotency-Key']=key
    request=urllib.request.Request(url+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
    with opener.open(request,timeout=15) as response:value=json.load(response);status=response.status
    # Never capture login/session bodies, cookies, CSRF or auth_generation.
    calls.append(dict(path=path,status=status,mutation=payload is not None))
    return value
api('/api/login',dict(username='alice',password=passwords['alice']))
panel=api('/api/panels/generate',dict(seed=20261022,count=12),key='cohort-ui-fixture-panel-r1')
patient_ids=panel['patient_ids'];assert len(patient_ids)==12
public=[]
for patient in patient_ids[:-1]:
    path='/api/patients/'+patient;workspace=api(path);s=workspace['snapshot']
    assert workspace['permissions']['approve_ordinary']
    follow_up=(datetime.datetime.fromisoformat(s['cutoff'])+datetime.timedelta(days=14)).isoformat()
    approved=api(path+'/approve',dict(decision_id=s['record_id'],expected_patient_version=s['patient_version'],
        expected_state_version=s['state_version'],expected_consent_version=s['consent_version'],expected_eligibility_version=s['eligibility_version'],
        mode='current',option='behavioral_continue',rationale='Explicit synthetic fixture setup; not a randomized research enrollment or efficacy choice.',
        follow_up_at=follow_up,purpose='ordinary_treatment'),key='cohort-ui-fixture-approve-'+patient)
    workspace=api(path)
    advanced=api(path+'/advance',dict(expected_version=workspace['snapshot']['patient_version'],mode='visit'),key='cohort-ui-fixture-advance-'+patient)
    workspace=api(path)
    assert advanced['day']==14 and workspace['history']
    public.append(dict(patient_id=patient,version=workspace['snapshot']['patient_version'],cutoff=workspace['snapshot']['cutoff'],day=workspace['simulation']['day'],history_count=len(workspace['history'])))
browser_patient=api('/api/patients/'+patient_ids[-1])
assert browser_patient['simulation']['day']==0 and not browser_patient['history']
result=dict(source='45d35071036ca3b635ae60e97ca04e924d98f74e',url=url,panel=panel,prepared=public,
    browser_patient=patient_ids[-1],browser_precondition=dict(day=0,history_count=0),
    claim='Actual existing v1 generator invoked through ordinary API. Eleven ordinary API fixture approvals/advances only; browser still must exercise its own twelfth patient. Not a trusted research enrollment, fit or study.',
    calls=calls)
(root/'public-setup.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(panel_id=panel['panel_id'],patient_count=12,prepared_day14=len(public),browser_patient=patient_ids[-1],browser_day=0)),flush=True)
