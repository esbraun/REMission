"""Subprocess fixture: execute frozen1096 service, never rewrite a current DB."""
import json,sys
from pathlib import Path
from datetime import datetime,timezone

frozen,root=map(Path,sys.argv[1:3])
sys.path[:0]=[str(frozen),str(frozen/'tests/integration/replay')]
from live_helpers import live_fixture,fresh_store
from services.foundation.app import Settings,create_app
from services.foundation.cli import seed,DEMO_PASSWORDS
from services.foundation.store import canonical
from fastapi.testclient import TestClient

now=datetime(2026,10,21,12,tzinfo=timezone.utc)
fixture,authority,installed,command=live_fixture(root)
store=fresh_store(root/'old.sqlite',installed);seed(store)
settings=Settings(store.path,installed,clock=lambda:now,observed_archives={'fixture':(fixture['raw'],root/'staging',authority)})
origin='http://127.0.0.1:8765'
with TestClient(create_app(settings),base_url=origin) as client:
    csrf=client.get('/api/session').json()['csrf']
    login=client.post('/api/login',json=dict(username='alice',password=DEMO_PASSWORDS['alice']),headers={'Origin':origin,'X-CSRF-Token':csrf});assert login.status_code==200,login.text
    def headers(key):return {'Origin':origin,'X-CSRF-Token':client.get('/api/session').json()['csrf'],'Idempotency-Key':key}
    s=client.get('/api/patients/SYN-02').json()['snapshot']
    approval=dict(decision_id=s['record_id'],expected_patient_version=s['patient_version'],expected_state_version=s['state_version'],expected_consent_version=s['consent_version'],expected_eligibility_version=s['eligibility_version'],mode='current',option='usual_care',rationale='Frozen003 ordinary synthetic choice',follow_up_at='2026-10-22T12:00:00+00:00',purpose='ordinary_treatment')
    saved=client.post('/api/patients/SYN-02/approve',json=approval,headers=headers('old-approval'));assert saved.status_code==200,saved.text
    archived=client.post('/api/observed-archives/fixture',json={'mode':'archive_only'},headers=headers('old-archive'));assert archived.status_code==200,archived.text
    entered=client.post('/api/patients/SYN-02/live-holds',json=command,headers=headers('old-entry'));assert entered.status_code==200,entered.text
    episode=client.get('/api/patients/SYN-02/live-holds').json()['episodes'][0];s=client.get('/api/patients/SYN-02').json()['snapshot']
    review=dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,mode='current',decision_id=s['record_id'],expected_patient_version=s['patient_version'],expected_state_version=s['state_version'],expected_consent_version=s['consent_version'],expected_eligibility_version=s['eligibility_version'],expected_episode_generation=episode['generation'],trigger_set_sha256=episode['trigger_set_sha256'],review_rules=episode['review_rules'],rationale='Frozen003 authenticated synthetic review',current_assessment_attested=True,items=[dict(requirement_id=r['requirement_id'],definition=r['definition'],evidence_refs=episode['trigger_refs'],finding='Structural fixture reviewed',result='satisfied') for r in episode['obligations']])
    reviewed=client.post('/api/patients/SYN-02/live-holds/'+entered.json()['episode_id']+'/reviews',json=review,headers=headers('old-review'));assert reviewed.status_code==200,reviewed.text
    result=dict(entry=entered.json(),review=reviewed.json(),approval=saved.json(),command=command)
root.joinpath('old-bundle.json').write_text(installed.model_dump_json())
root.joinpath('old-results.json').write_text(canonical(result))
print(canonical(dict(status='actual_frozen003_checkpoint',source='1096d6da86048e7a53f98ed70abdd85f6f497aed',database=str(store.path),entry=entered.json()['operation_id'])))
