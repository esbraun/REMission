"""Future disposable genuine archive intake, never invoked during preparation.

Credentials, cookies, DBs and bundle bytes never enter public output/evidence.
"""
import importlib.abc,json,os,sys,tempfile
import time
from datetime import datetime,timedelta,timezone
from pathlib import Path

class DenyScience(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'numpy','scipy','statsmodels','pymc','pytensor','arviz','pandas','xarray','methods'} or fullname.startswith('services.generator'):
   raise AssertionError('science/generator import forbidden')
sys.meta_path.insert(0,DenyScience())

_PROGRESS_STARTED=time.monotonic()
_DIAGNOSTIC=None
_COUNT_PASS=0
def progress(phase,state,*,member_id=None,mode=None,cutoff_day=None,completed_replays=0):
 value=dict(kind='p2_phase_progress',phase=phase,state=state,
     elapsed_seconds=time.monotonic()-_PROGRESS_STARTED,completed_replays=completed_replays)
 if member_id is not None:value['member_id']=member_id
 if mode is not None:value['mode']=mode
 if cutoff_day is not None:value['cutoff_day']=cutoff_day
 raw=json.dumps(value,sort_keys=True)
 if len(raw.encode())+1>320:raise ValueError('p2_progress_bound')
 print(raw,flush=True)

def main():
 global _DIAGNOSTIC,_COUNT_PASS
 from services.foundation.support_diagnostics import IntakeDiagnostics,observe
 _DIAGNOSTIC=IntakeDiagnostics(lambda line:print(line,flush=True));_COUNT_PASS=0
 from fastapi.testclient import TestClient
 from contracts.runs.support_research import SupportArchiveAuthority
 from contracts.service.live_hold import LiveHoldAuthority,ReviewRules
 from services.foundation.app import Settings,create_app,HASHER
 from services.foundation.configuration import read_archives
 from services.foundation.cutover import activate_new,bundle_for
 from services.foundation.store import canonical,digest,timestamp
 from services.foundation.workflow import state_for
 from admin import create_account
 spec=json.loads(Path('/operation/p2-service-spec.json').read_bytes())
 credentials=json.loads(Path('/private/auth.json').read_bytes())
 configured=read_archives('/operation/archive-config.json')
 raw,public,authority=configured[spec['export_id']]
 assert type(authority) is SupportArchiveAuthority and authority.admission_sha256==spec['admission_sha256']
 assert authority.qualification_scope=='accepted_saved_producer'
 index=authority.descriptor;origin=spec['origin']
 service=json.loads(Path('/app/contracts/service/bindings-v1.json').read_bytes())
 runs=json.loads(Path('/app/contracts/runs/bindings-v2.json').read_bytes())
 description=dict(kind='disposable_s1_historical_application',synthetic=True,namespace=spec['namespace'],
     source_commit=spec['source_commit'],service_image=spec['images']['service'],live_authority_enabled=False)
 reference=dict(id='disposable-s1-live-authority-disabled',version='1.0.0',sha256=digest(canonical(description)))
 def installed():
  a=LiveHoldAuthority.model_validate(dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,
      authority_id=spec['namespace']+'-disabled',version=reference,service_contract=service['live_hold'],
      schema_binding=service['service_schema_set'],enabled=False,observed_binding=runs['observed_representation'],
      archive_verifier=reference,producer=reference,source_registry=reference,execution='synthetic_service',
      grants=[],follow_up_amendments=[]))
  rules=ReviewRules.model_validate(dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,rules=[]))
  return bundle_for(a,rules)
 def initialize(path):
  bundle=installed();store=activate_new(path,bundle,datetime.now(timezone.utc))
  for role,display in [('owner','Synthetic historical archive owner'),('foreign','Synthetic foreign fixture account')]:
   create_account(store,credentials[role]['username'],display,credentials[role]['password'],HASHER)
  return store,bundle
 def owner_id(store,role='owner'):
  with store.transaction() as db:return db.execute('SELECT id FROM accounts WHERE username=?',(credentials[role]['username'],)).fetchone()[0]
 def client(store,bundle):
  return TestClient(create_app(Settings(store.path,bundle,origin=origin,observed_archives=configured,
      source_commit=spec['source_commit'],support_intake_diagnostic=_DIAGNOSTIC)),base_url=origin)
 def login(c):
  pre=c.get('/api/session');assert pre.status_code==200,'preauth failed'
  result=c.post('/api/login',json=credentials['owner'],headers={'Origin':origin,'X-CSRF-Token':pre.json()['csrf']})
  assert result.status_code==200,'private authentication failed'
 def headers(c):return {'Origin':origin,'X-CSRF-Token':c.get('/api/session').json()['csrf']}
 def post(c):
  _DIAGNOSTIC.begin_request()
  response=c.post('/api/observed-archives/'+spec['export_id'],json={'mode':'archive_only'},headers=headers(c))
  _DIAGNOSTIC('post_return')
  return response
 def counts(store):
  global _COUNT_PASS
  _COUNT_PASS+=1;count_pass=_COUNT_PASS
  observe(_DIAGNOSTIC,'counts_before',count_pass=count_pass)
  with store.transaction() as db:
   result={}
   for table,name in enumerate(('patients','state_changes','observed_archives','observed_archive_entries','observed_archive_artifacts',
        'decisions','live_patient_journals','analysis_attempts','pending_work'),1):
    observe(_DIAGNOSTIC,'count_before',count_pass=count_pass,table=table)
    result[name]=db.execute('SELECT count(*) FROM '+name).fetchone()[0]
    observe(_DIAGNOSTIC,'count_after',count_pass=count_pass,table=table)
  observe(_DIAGNOSTIC,'counts_after',count_pass=count_pass)
  return result
 # Positive Store contains no seed/live/fake anchor patients. Only P2 may insert
 # the real marked historical twelve; this same Store is retained for P3/UI.
 progress('bootstrap','before')
 database=Path('/data/remission.sqlite');bootstrap=Path('/data/bootstrap')
 assert not database.exists() and not bootstrap.exists(),'fresh private volume required'
 positive,bundle=initialize(database);bootstrap.mkdir(mode=0o700)
 bundle_file=bootstrap/'bundle.json';bundle_file.write_text(bundle.model_dump_json(),encoding='utf-8');bundle_file.chmod(0o400)
 progress('bootstrap','after')
 with client(positive,bundle) as c:
  login(c)
  progress('initial_intake','before')
  first=post(c);assert first.status_code==200,'genuine intake failed'
  _DIAGNOSTIC('status_checked')
  receipt=first.json();_DIAGNOSTIC('json_decoded')
  before=counts(positive)
  progress('initial_intake','after')
  progress('idempotent_intake','before')
  second=post(c)
  assert second.status_code==200 and second.json()==receipt,'exact receipt idempotence failed'
  _DIAGNOSTIC('response_checked')
  assert counts(positive)==before,'idempotent historical row counts changed'
  progress('idempotent_intake','after')
  assert receipt['admission_sha256']==spec['admission_sha256'] and receipt['qualification_scope']=='accepted_saved_producer'
  assert receipt['members']==12 and receipt['partitions']==24 and receipt['projections']==72 and not receipt['live_authority_granted']
  assert before['patients']==before['state_changes']==12 and before['observed_archives']==1
  assert before['observed_archive_artifacts']==spec['expected']['artifacts'] and before['observed_archive_entries']==spec['expected']['record_count']
  panel=c.get('/api/patients');assert panel.status_code==200
  assert len(panel.json()['patients'])==12 and all(p['historical_support'] for p in panel.json()['patients'])
  replay=[]
  for trajectory in index.trajectories:
   for day in index.cuts:
    progress('saved_get','before',member_id=trajectory.member_id,mode=trajectory.mode,cutoff_day=day,completed_replays=len(replay))
    response=c.get('/api/patients/'+trajectory.member_id+'/observed-archives/'+receipt['archive_id'],params={'mode':trajectory.mode,'cutoff_day':day})
    assert response.status_code==200,'owned projection replay failed'
    value=response.json();artifact=trajectory.projections[str(day)];original=(public/artifact.path).read_bytes()
    assert value['projection']==json.loads(original) and value['projection_sha256']==artifact.sha256
    assert len(original)==artifact.bytes and digest(original)==artifact.sha256
    assert value['partition_id']==trajectory.partition_id and value['patient_id']==trajectory.member_id and value['mode']==trajectory.mode and value['cutoff_day']==day
    replay.append(dict(member_id=trajectory.member_id,partition_id=trajectory.partition_id,mode=trajectory.mode,cutoff_day=day,projection_sha256=artifact.sha256,bytes=artifact.bytes))
    progress('saved_get','after',member_id=trajectory.member_id,mode=trajectory.mode,cutoff_day=day,completed_replays=len(replay))
  assert len(replay)==72 and counts(positive)==before
 positive_owner=owner_id(positive)
 with positive.transaction() as db:
  rows=db.execute('SELECT id,owner_id,current_decision FROM patients').fetchall()
  assert {r['id'] for r in rows}==set(index.members) and all(r['owner_id']==positive_owner and r['current_decision'] is None for r in rows)
  assert before['decisions']==before['live_patient_journals']==before['analysis_attempts']==before['pending_work']==0
 # Explicit negative fixtures: independent fresh temporary Stores, not copies
 # of the admitted positive DB. The one conflicting unmarked row is intentional
 # malformed fixture state only; it never becomes a positive/live anchor.
 negatives=[]
 for case in ('foreign_owner_row','same_owner_unmarked_row'):
  with tempfile.TemporaryDirectory(prefix='s1-negative-') as folder:
   negative,negative_bundle=initialize(Path(folder)/'negative.sqlite')
   member=index.members[-1];who=owner_id(negative,'foreign' if case=='foreign_owner_row' else 'owner')
   with negative.transaction(write=True) as db:
    db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',(member,who,'NEGATIVE identity collision fixture',1,1,1,1,canonical(state_for('ASSIGN-01')),None,timestamp(index.origin+timedelta(days=index.horizon))))
   with client(negative,negative_bundle) as c:
    login(c);prior=counts(negative);rejected=post(c)
    assert rejected.status_code==409 and rejected.json()['code']=='archive_admission_rejected'
    _DIAGNOSTIC('response_checked')
    assert counts(negative)==prior and prior['patients']==1 and prior['state_changes']==prior['observed_archives']==0
   negatives.append(dict(case=case,status=409,rollback_counts_unchanged=True,isolated_temporary_store=True))
 assert counts(positive)==before,'negative fixture affected positive Store'
 result=dict(status='genuine_p2_intake_idempotence_72_replays_pass',synthetic=True,
     database_instance_id=bundle.control.database_instance_id,authority_generation=bundle.control.authority_generation,
     archive_id=receipt['archive_id'],receipt=receipt,counts=before,replays=replay,negative_cases=negatives,
     no_seed_patients=True,no_live_authority=True,no_job=True,positive_store_retained=True,scientific_imports=[])
 _DIAGNOSTIC.summary()
 encoded=json.dumps(result,sort_keys=True)
 if len(encoded.encode())+1>32768:raise ValueError('p2_result_bound')
 print(encoded)

if __name__=='__main__':
 try:main()
 except BaseException as error:
  if _DIAGNOSTIC is not None:_DIAGNOSTIC.summary()
  # Never expose request/session/login objects or credential-bearing traceback.
  print(json.dumps(dict(status='p2_operation_failed',error_type=type(error).__name__,private_details_withheld=True)))
  sys.exit(1)
