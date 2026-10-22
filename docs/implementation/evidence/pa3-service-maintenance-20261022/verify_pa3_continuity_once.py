"""Existing public-fixture login and read-only owned history continuity check."""
import ast
import copy
from datetime import datetime
import hashlib
import http.cookiejar
import json
from pathlib import Path
import subprocess
import sqlite3
import urllib.request

from audit_pa3_native_readiness import SERVICE
from maintain_pa3_service_once import PRIVATE, ROOT, command, database, equal_database, save

PATIENT='POC-cc502a55230e4ab6a6b86f406d6c2208'
ATTEMPT='analysis-4ff86193058d4d13a1600f0423e91f12'
URL='http://127.0.0.1:8780'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    # Actual owner/credential/cookie/CSRF values stay in memory, without capture.
    code="""import sqlite3,json
db=sqlite3.connect('file:/data/remission.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
patient='POC-cc502a55230e4ab6a6b86f406d6c2208'
owner=db.execute('SELECT owner_id FROM patients WHERE id=?',(patient,)).fetchone()[0]
username=db.execute('SELECT username FROM accounts WHERE id=?',(owner,)).fetchone()[0]
history=[dict(r) for r in db.execute('SELECT id,approved_at,display_sha256 FROM bundles WHERE patient_id=? ORDER BY approved_at,id',(patient,))]
print(json.dumps({'owner':owner,'username':username,'history':history}));db.rollback();db.close()"""
    private=subprocess.run(['docker','exec',SERVICE,'python','-c',code],capture_output=True)
    if private.returncode:raise RuntimeError('private owner lookup failed; no streams persisted')
    expected=json.loads(private.stdout)
    tree=ast.parse(Path('services/foundation/cli.py').read_text())
    passwords=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEMO_PASSWORDS' for t in n.targets))
    cookies=http.cookiejar.CookieJar()
    client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

    def api(path,payload=None,csrf=None):
        headers={'Origin':URL}
        if payload is not None:headers.update({'Content-Type':'application/json','x-csrf-token':csrf})
        request=urllib.request.Request(URL+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        with client.open(request,timeout=10) as response:
            assert response.status==200
            return json.load(response)

    initial=api('/api/session')
    signed=api('/api/login',{'username':expected['username'],'password':passwords[expected['username']]},initial['csrf'])
    assert signed['principal']['id']==expected['owner']
    session=api('/api/session');assert session['principal']==signed['principal']
    panel=api('/api/patients')
    assert any(p['id']==PATIENT for p in panel['patients'])
    workspace=api('/api/patients/'+PATIENT)
    assert workspace['history']==expected['history']
    historical=[]
    for bundle in expected['history']:
        value=api('/api/patients/'+PATIENT+'/history/'+bundle['id'])
        assert value['display_sha256']==bundle['display_sha256']
        later=api('/api/patients/'+PATIENT+'/history/'+bundle['id']+'/later-outcomes')
        historical.append({'bundle_id':bundle['id'],'display_sha256':bundle['display_sha256'],'later_outcomes_count':len(later['records']),'later_outcomes_sha256':digest(later)})
    attempt=api('/api/patients/'+PATIENT+'/analyses/'+ATTEMPT)
    assert attempt['id']==ATTEMPT and attempt['status']=='queued'
    reloaded=api('/api/patients/'+PATIENT)
    assert reloaded['history']==expected['history']
    before=json.loads((ROOT/'post-database.json').read_text())
    after=database(SERVICE)
    with sqlite3.connect('file:'+str((PRIVATE/'remission-pre-pa3.sqlite').as_posix())+'?mode=ro',uri=True) as backup:
        backup.row_factory=sqlite3.Row
        original_control=dict(backup.execute('SELECT * FROM service_control WHERE singleton=1').fetchone())
    control_code="import sqlite3,json;db=sqlite3.connect('file:/data/remission.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');print(json.dumps(dict(db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone())))"
    private=subprocess.run(['docker','exec',SERVICE,'python','-c',control_code],capture_output=True)
    if private.returncode:raise RuntimeError('private control lookup failed; no streams persisted')
    current_control=json.loads(private.stdout)
    differences=[key for key in original_control if original_control[key]!=current_control[key]]
    assert differences==['last_receipt_at']
    assert datetime.fromisoformat(current_control['last_receipt_at']) >= datetime.fromisoformat(original_control['last_receipt_at'])
    assert after['protected_tables']['service_control']['rows_sha256']==digest([digest(current_control)])
    # Ordinary bootstrap/login is authorized; Store.receive advances this clock.
    # Check that exact single-field exception before comparing every other row.
    comparison=copy.deepcopy(before)
    comparison['protected_tables']['service_control']=after['protected_tables']['service_control']
    equal_database(comparison,after)
    save('post-login-database.json',after)
    save('api-continuity.json',{'normal_existing_fixture_login':True,'same_owner_sha256':digest(expected['owner']),'owned_panel_count':len(panel['patients']),'same_patient':PATIENT,'same_queued_attempt':ATTEMPT,'existing_history_count':len(historical),'existing_history':historical,'history_reload_equal':True,'all_other_protected_rows_equal':True,'service_control_changed_fields':differences,'receipt_clock_monotonic':True,'authority_control_other_fields_equal_count':len(current_control)-1,'credentials_cookies_csrf_or_full_responses_persisted':False,'auth_only_mutations':'ordinary bootstrap/login changes sessions/login_attempts and service_control.last_receipt_at; all other protected rows equal'})
    print(json.dumps({'ordinary_login':True,'owned_panel_count':len(panel['patients']),'history_count':len(historical),'target_queued':True,'all_other_protected_rows_equal':True,'service_control_changed_fields':differences}))


if __name__=='__main__':
    main()
