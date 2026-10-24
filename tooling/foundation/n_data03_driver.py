"""Fixed N-DATA03 container consumer. No server, fit, queue or production change.

Default mode owns one direct Python child. The child alone imports the installed
app, performs authenticated routes and retains private observed exports. This
module is safe to import for scalar/source controls; execution needs root GO.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib.abc
import json
import math
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time

LABEL='poc-n-app-dev-n12-20261023-r1'
SEED=91731023
COUNT=12
TARGET_INDEX=6
ORIGIN='https://remission.example.org'
ASSERTIONS=('both_options_acceptable','stable_regimen_reviewed','interactions_reviewed',
    'fall_risk_reviewed','rescue_stop_plan_reviewed','patient_agrees')
VERSION_KEYS=('patient_version','state_version','consent_version','eligibility_version')
PRIVATE_NAMES=frozenset(('credentials.json','declaration.json','generation-response.json',
    'selection.json','commands.jsonl','observed-day36.json','observed-day72.json'))
FILE_CAP=64*1024*1024
EXPORT_CAP=128*1024*1024
STDOUT_CAP=256*1024
DRIVER_CAP=STDOUT_CAP-4096  # Reserved parent identity/custody/error rows included.
STDERR_CAP=64*1024
# Exact ordinary (non-analysis) placeholder from foundation/replay.py. Ordinary
# follow-up tasks live in tasks and are independently required, never zeroed.
ORDINARY_UNAVAILABLE_REASON='New observed data; statistical worker unavailable'
PHASES=frozenset(('initialized','cohort_frozen','member_authorized','member_day36',
    'member_day72','receipt36','receipt72'))
ERRORS=frozenset(('driver_failed','unknown_mutation','request_deadline','lease_deadline',
    'output_limit','identity_rejected','child_failed'))


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


class Data03Error(RuntimeError):
    def __init__(self,code='driver_failed'):
        if code not in ERRORS:raise ValueError('fixed_error_required')
        self.code=code
        super().__init__(code)


def require(value):
    if not value:raise Data03Error()


def validate_generation(value):
    require(type(value) is dict and set(value)=={'status','panel_id','seed','count','patient_ids'})
    ids=value['patient_ids']
    require(value['status']=='generated' and value['seed']==SEED and type(value['seed']) is int
        and value['count']==COUNT and type(value['count']) is int and type(ids) is list
        and len(ids)==COUNT and len(set(ids))==COUNT
        and all(type(p) is str and p.startswith('POC-') and len(p)==36 for p in ids)
        and type(value['panel_id']) is str and value['panel_id'].startswith('panel-') and len(value['panel_id'])==38)
    return dict(label=LABEL,seed=SEED,count=COUNT,family='nof1_med',activation_day=0,
        target_ordinal=TARGET_INDEX+1,generation_order=list(ids),cohort=sorted(ids),
        target_id=ids[TARGET_INDEX],panel_id=value['panel_id'])


class Exports:
    """Only the seven declared private export files count toward this quota.

    Store DB/WAL/bootstrap are separate application state. No tree walk or
    database/bundle/credential digest is used to enforce an export quota.
    """
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(mode=0o700)
        self.sizes={}

    def reserve(self,name,size):
        require(name in PRIVATE_NAMES and type(size) is int and size>=0)
        if size>FILE_CAP or sum(self.sizes.values())-self.sizes.get(name,0)+size>EXPORT_CAP:
            raise Data03Error('output_limit')

    def once(self,name,value,*,raw=False):
        data=value if raw else encoded(value)
        require(type(data) is bytes and name not in self.sizes)
        self.reserve(name,len(data))
        fd=os.open(self.root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        self.sizes[name]=len(data)

    def command(self,stage,ordinal,step,key):
        name='commands.jsonl'
        if name not in self.sizes:self.once(name,b'',raw=True)
        data=encoded(dict(stage=stage,ordinal=ordinal,step=step,key=key))
        self.reserve(name,self.sizes[name]+len(data))
        with (self.root/name).open('ab') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        self.sizes[name]+=len(data)


def validate_public(row):
    """Strict public transport shape; no arbitrary dictionary projection."""
    require(type(row) is dict)
    kind=row.get('kind')
    if kind=='n_data03_phase':
        require(set(row)=={'kind','stage','ordinal','day','seconds'} and row['stage'] in PHASES
            and type(row['ordinal']) is int and 0<=row['ordinal']<=12
            and type(row['day']) is int and row['day'] in (0,36,72)
            and type(row['seconds']) in (float,int) and math.isfinite(row['seconds']) and 0<=row['seconds']<=7140)
    elif kind=='n_data03_identity':
        require(set(row)=={'kind','pid','ppid','nonce'} and all(type(row[k]) is int and row[k]>0 for k in ('pid','ppid'))
            and type(row['nonce']) is str and len(row['nonce'])==32 and all(c in '0123456789abcdef' for c in row['nonce']))
    elif kind=='n_data03_error':
        require(set(row)=={'kind','code'} and row['code'] in ERRORS)
    elif kind=='n_data03_custody':
        require(set(row)=={'kind','pid','reaped','returncode','identity_matched','reason','stdout_bytes','stderr_bytes','broader_descendants'}
            and type(row['pid']) is int and row['pid']>0 and type(row['reaped']) is bool
            and (type(row['returncode']) is int if row['reaped'] else row['returncode'] is None) and type(row['identity_matched']) is bool
            and row['reason'] in ERRORS|{'completed'} and row['broader_descendants']=='UNKNOWN'
            and type(row['stdout_bytes']) is int and 0<=row['stdout_bytes']<=DRIVER_CAP+1
            and type(row['stderr_bytes']) is int and 0<=row['stderr_bytes']<=STDERR_CAP+1)
    elif kind=='n_data03_result':
        require(set(row)=={'kind','status','synthetic','declaration','receipts','advances','nightly_increments','no_analysis_jobs','historical36_equal'}
            and row['status'] in ('complete_eligible','complete_inconclusive') and row['synthetic'] is True
            and row['advances']==180 and type(row['advances']) is int and row['nightly_increments']==864
            and type(row['nightly_increments']) is int and row['no_analysis_jobs'] is True and row['historical36_equal'] is True)
        declaration=row['declaration']
        require(type(declaration) is dict and set(declaration)=={'label','seed','count','family','activation_day','target_ordinal','generation_order','cohort','target_id','panel_id'})
        rebuilt=validate_generation(dict(status='generated',panel_id=declaration['panel_id'],seed=declaration['seed'],count=declaration['count'],patient_ids=declaration['generation_order']))
        require(declaration==rebuilt and type(row['receipts']) is list and len(row['receipts'])==2)
        for day,receipt in zip((36,72),row['receipts']):
            require(type(receipt) is dict and set(receipt)=={'day','cutoff','history_sha256','members','readiness'}
                and receipt['day']==day and type(receipt['cutoff']) is str and len(receipt['cutoff'])<=40
                and type(receipt['members']) is list and len(receipt['members'])==12)
            def ishash(v):return type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v)
            require(ishash(receipt['history_sha256']))
            require([m['patient_id'] for m in receipt['members']]==declaration['cohort'])
            for member in receipt['members']:
                require(type(member) is dict and set(member)=={'patient_id','patient_version','history_sha256','provenance_sha256'}
                    and type(member['patient_version']) is int and member['patient_version']>=1
                    and ishash(member['history_sha256']) and ishash(member['provenance_sha256']))
            ready=receipt['readiness']
            require(type(ready) is dict and set(ready)=={'status','review_day','arm_blocks'} and ready['review_day']==day
                and ready['status'] in ('eligible','inconclusive') and set(ready['arm_blocks'])==set(declaration['cohort']))
            for counts in ready['arm_blocks'].values():
                require(type(counts) is dict and set(counts)=={'MED_A','MED_B'}
                    and all(type(v) is int and 0<=v<=8 for v in counts.values()) and sum(counts.values())==day//9)
        require(row['status']=='complete_'+row['receipts'][-1]['readiness']['status'])
    else:raise Data03Error()
    return row


class Public:
    def __init__(self,sink,clock=time.monotonic):self.sink=sink;self.clock=clock;self.started=clock();self.bytes=0;self.phases=0
    def send(self,row):
        validate_public(row);data=encoded(row)
        if row['kind']=='n_data03_phase':
            if len(data)>512 or self.phases>=256:raise Data03Error('output_limit')
            self.phases+=1
        elif row['kind']=='n_data03_result' and len(data)>128*1024:raise Data03Error('output_limit')
        if self.bytes+len(data)>DRIVER_CAP:raise Data03Error('output_limit')
        self.bytes+=len(data);self.sink(data)
    def phase(self,stage,ordinal=0,day=0):
        self.send(dict(kind='n_data03_phase',stage=stage,ordinal=ordinal,day=day,seconds=self.clock()-self.started))


class RequestLimit:
    """Linux whole-process hard stop; never catch a timed-out TestClient thread."""
    def __init__(self,lease_unix,*,wall=time.time,arm=None,exit_process=os._exit,write=os.write):
        self.lease=lease_unix;self.wall=wall;self.arm=arm if arm is not None else getattr(signal,'setitimer',None)
        self.exit_process=exit_process;self.write=write
        require(callable(self.arm))
    def expired(self,_signum=None,_frame=None):
        try:self.write(1,encoded(dict(kind='n_data03_error',code='request_deadline')))
        finally:self.exit_process(124)
    @contextmanager
    def hold(self):
        remaining=self.lease-self.wall()
        if remaining<=0:raise Data03Error('lease_deadline')
        self.arm(0,min(180.0,remaining))
        try:yield
        finally:self.arm(0,0)


def instant(value):
    import re
    require(not re.search(r'[.,]\d{7}',value))
    require(not re.search(r'[+-]\d{2}(?::?\d{2}){0,2}[.,]',value))
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(result.tzinfo is not None and result.utcoffset() is not None)
    return result.astimezone(timezone.utc)


def admit_rows(rows,selection,snapshots,owner,day,law,protocol):
    require(day in (36,72) and len(rows)==COUNT and {r['id'] for r in rows}==set(selection['cohort'])
        and set(snapshots)==set(selection['cohort']) and selection['target_id']==selection['generation_order'][TARGET_INDEX])
    origins=set();cutoffs=set()
    for row in rows:
        s=snapshots[row['id']];state=json.loads(row['state_json']);sim=state.get('simulation',{});loop=sim.get('nof1',{})
        cutoff=instant(row['cutoff']);snapshot_cutoff=instant(s['cutoff']);origin=instant(sim['origin'])
        require(row['owner_id']==owner and row['current_decision']==s['record_id']
            and all(row['version' if k=='patient_version' else k]==s[k] for k in VERSION_KEYS)
            and cutoff==snapshot_cutoff and sim.get('day')==day and sim.get('family')=='nof1_med'
            and sim.get('law_version')==law['id'] and sim.get('law')==law and sim.get('protocol')==protocol
            and sim.get('panel_id')==selection['panel_id'] and sim.get('seed')==SEED
            and sim.get('index')==selection['generation_order'].index(row['id']) and sim.get('research_run_id') is None
            and loop.get('start_day')==0 and loop.get('uninterrupted') is True
            and loop.get('status')==('active' if day==36 else 'completed'))
        require(cutoff==origin+timedelta(days=day));origins.add(origin);cutoffs.add(cutoff)
    require(len(origins)==len(cutoffs)==1)
    return next(iter(cutoffs))


def no_analysis_jobs(attempts,pending):
    require(type(attempts) is int and attempts==0 and len(pending)<=1024)
    require(all(len(row)==2 and type(row[0]) is str and type(row[1]) is str
        and row[0]=='unavailable' and row[1]==ORDINARY_UNAVAILABLE_REASON for row in pending))


def receipt(store,owner,selection,snapshots,day):
    from contracts.domain.analysis import canonical,reference,sha
    from contracts.domain.nof1_app import readiness
    from contracts.domain.protocol import LAW_REF,NOF1_REF
    from services.foundation.nof1 import guard
    from services.foundation.protocol import export_histories
    with store.transaction(write=False) as db:
        db.execute('PRAGMA query_only=ON')
        require(db.execute('PRAGMA query_only').fetchone()[0]==1)
        rows=list(db.execute('SELECT id,owner_id,version,state_version,consent_version,eligibility_version,state_json,cutoff,current_decision FROM patients WHERE owner_id=? ORDER BY id',(owner,)))
        cutoff=admit_rows(rows,selection,snapshots,owner,day,LAW_REF,NOF1_REF)
        for row in rows:require(not guard(db,row['id'],json.loads(row['state_json']),cutoff,datetime.now(timezone.utc)))
        no_analysis_jobs(db.execute('SELECT COUNT(*) FROM analysis_attempts').fetchone()[0],
            list(db.execute('SELECT status,reason FROM pending_work LIMIT 1025')))
        require(db.execute('SELECT COUNT(*) FROM tasks WHERE owner_id=?',(owner,)).fetchone()[0]==12)
        histories=export_histories(db,owner,selection['cohort'],cutoff)
        require([h.patient_id for h in histories]==selection['cohort'] and all(h.cutoff==cutoff for h in histories))
        ready=readiness(histories,selection['target_id']);require(ready['status'] in ('eligible','inconclusive') and ready['review_day']==day)
        frozen=[h.model_dump(mode='json') for h in histories]
        require([h.model_dump(mode='json') for h in export_histories(db,owner,selection['cohort'],cutoff)]==frozen)
        historical=None
        if day==72:
            original=cutoff-timedelta(days=36)
            historical=[h.model_dump(mode='json') for h in export_histories(db,owner,selection['cohort'],original)]
        members=[dict(patient_id=h.patient_id,patient_version=snapshots[h.patient_id]['patient_version'],
            history_sha256=sha(h.model_dump(mode='json')),provenance_sha256=sha([r.model_dump(mode='json') for r in h.provenance])) for h in histories]
    run=reference('poc-nof1-app-run-'+sha(selection['panel_id'])[:16],dict(generation_id=selection['panel_id'],law=LAW_REF,protocol=NOF1_REF))
    public=dict(day=day,cutoff=cutoff.isoformat(),history_sha256=sha(frozen),members=members,
        readiness=dict(status=ready['status'],review_day=day,arm_blocks=ready['arm_blocks']))
    private=dict(kind='N-DATA03-observed-readiness',declaration=selection,run=run,public=public,histories=frozen)
    return private,historical


class Physician:
    def __init__(self,store,client,foreign,anonymous,passwords,exports,limit,public):
        self.store=store;self.client=client;self.foreign=foreign;self.anonymous=anonymous
        self.passwords=passwords;self.exports=exports;self.limit=limit;self.public=public;self.advances=0

    def call(self,client,method,path,*,expected=200,consume=None,mutation=False,**kwargs):
        with self.limit.hold():
            try:response=client.request(method,path,**kwargs)
            except Exception:raise Data03Error('unknown_mutation' if mutation else 'driver_failed') from None
            if response.status_code>=500:raise Data03Error('unknown_mutation' if mutation else 'driver_failed')
            require(response.status_code==expected and len(response.content)<=FILE_CAP)
            # Receipt/persistence checks run before disarming the same timer.
            return consume(response) if consume else None

    def login(self,client,name):
        csrf=self.call(client,'GET','/api/session',consume=lambda r:r.json()['csrf'])
        self.call(client,'POST','/api/login',json=self.passwords[name],headers={'Origin':ORIGIN,'X-CSRF-Token':csrf},mutation=True)

    def live(self,client,name):
        def session(response):return response.status_code,response.json()
        with self.limit.hold():
            try:r=client.get('/api/session')
            except Exception:raise Data03Error() from None
            require(r.status_code in (200,401) and len(r.content)<=FILE_CAP)
            status,value=session(r)
        if status==401:self.login(client,name);return self.live_once(client)
        # An anonymous200 response has no principal, even if it has CSRF.
        if value.get('principal') is None:self.login(client,name);return self.live_once(client)
        return value

    def live_once(self,client):
        value=self.call(client,'GET','/api/session',consume=lambda r:r.json())
        require(value.get('principal') is not None)
        return value

    def workspace(self,patient):
        self.live(self.client,'owner')
        value=self.call(self.client,'GET','/api/patients/'+patient,consume=lambda r:r.json())
        # Never retain a full workspace or auth_generation in an export/public row.
        return {'snapshot':value['snapshot'],'simulation':value['simulation'],'nof1':value['nof1']}

    def command(self,client,name,path,body,stage,ordinal,step,*,expected=200,key=None,consume=None,headers_override=None):
        self.live(client,name)  # Reauthenticate only before constructing a NEW command.
        if callable(body):body=body()
        # Do not silently reauthenticate after a versioned payload was built.
        # A race to expiry stops before dispatch instead of rebasing/retrying.
        session=self.live_once(client)
        key=key or f'ndata03-r1-{stage}-{ordinal}-{step}'
        self.exports.command(stage,ordinal,step,key)
        headers={'Origin':ORIGIN,'X-CSRF-Token':session['csrf'],'Idempotency-Key':key}
        if headers_override is not None:headers=headers_override
        return self.call(client,'POST',path,json=body,headers=headers,expected=expected,consume=consume,mutation=True)

    def state_counts(self):
        with self.store.transaction(write=False) as db:
            db.execute('PRAGMA query_only=ON')
            versions=[tuple(r) for r in db.execute('SELECT id,version,state_version,consent_version,eligibility_version,current_decision FROM patients ORDER BY id')]
            counts=tuple(db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in
                ('patients','events','bundles','state_changes','analysis_attempts','pending_work','tasks'))
            assignments=db.execute("SELECT COUNT(*) FROM events WHERE kind='assignment'").fetchone()[0]
        return versions,counts,assignments

    def denied(self,operation):
        before=self.state_counts();operation();require(self.state_counts()==before)

    def nof1_payload(self,patient,action):
        s=self.workspace(patient)['snapshot']
        body=dict(mode='current',action=action,decision_id=s['record_id'],expected_version=s['patient_version'],
            expected_state_version=s['state_version'],expected_consent_version=s['consent_version'],
            expected_eligibility_version=s['eligibility_version'],rationale='Fixed fictional DATA03 authorization')
        if action=='review':body['assertions']=list(ASSERTIONS)
        if action=='approve':
            from contracts.domain.protocol import NOF1_REF
            body.update(permitted_options=['MED_A','MED_B'],template=NOF1_REF)
        return body

    def ordinary_payload(self,patient):
        s=self.workspace(patient)['snapshot']
        return dict(mode='current',purpose='ordinary_treatment',option='behavioral_continue',decision_id=s['record_id'],
            rationale='Fixed fictional DATA03 ordinary continuation',follow_up_at=(datetime.fromisoformat(s['cutoff'])+timedelta(days=14)).isoformat(),
            **{'expected_'+k:s[k] for k in VERSION_KEYS})

    def authorize(self,patient,ordinal):
        w=self.workspace(patient);s=w['snapshot'];require(w['simulation']['day']==0)
        path='/api/patients/'+patient
        if ordinal==1:
            ordinary=self.ordinary_payload(patient)
            self.denied(lambda:self.call(self.foreign,'GET',path,expected=404))
            self.denied(lambda:self.command(self.foreign,'foreign',path+'/approve',ordinary,'denied',ordinal,'owner',expected=404))
        self.command(self.client,'owner',path+'/approve',lambda:self.ordinary_payload(patient),'authorize',ordinal,'ordinary')
        if ordinal==1:
            start=self.nof1_payload(patient,'start')
            self.denied(lambda:self.command(self.client,'owner',path+'/nof1',start,'denied',ordinal,'start',expected=409))
        for action in ('consent','review','approve','start'):
            if ordinal==1 and action in ('review','approve'):
                bad=self.nof1_payload(patient,action)
                bad['assertions' if action=='review' else 'permitted_options']=(list(ASSERTIONS[:-1]) if action=='review' else ['MED_A'])
                self.denied(lambda:self.command(self.client,'owner',path+'/nof1',bad,'denied',ordinal,action,expected=422))
            self.command(self.client,'owner',path+'/nof1',lambda:self.nof1_payload(patient,action),'authorize',ordinal,action)
        w=self.workspace(patient);loop=w['nof1']['loop']
        require(w['simulation']['day']==0 and loop['status']=='active' and loop['start_day']==0
            and len(loop['draws'])==1 and loop['draws'][0]['day']==0
            and loop['draws'][0]['probabilities']=={'MED_A':.5,'MED_B':.5})
        self.public.phase('member_authorized',ordinal)

    def advance(self,patient,ordinal,day):
        expected=(14,28,*range(29,37)) if day==36 else (42,56,70,71,72)
        modes=('visit','visit',*('day',)*8) if day==36 else ('visit','visit','visit','day','day')
        for step,(target,mode) in enumerate(zip(expected,modes),1):
            body=lambda:dict(expected_version=self.workspace(patient)['snapshot']['patient_version'],mode=mode)
            self.command(self.client,'owner','/api/patients/'+patient+'/advance',body,'day'+str(day),ordinal,str(step),
                consume=lambda r:require(r.json()['day']==target))
            self.advances+=1
        require(self.workspace(patient)['simulation']['day']==day)
        self.public.phase('member_day'+str(day),ordinal,day)

    def barrier(self,selection,owner,day):
        snapshots={p:self.workspace(p)['snapshot'] for p in selection['cohort']}
        return receipt(self.store,owner,selection,snapshots,day)


class NoFits(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'pymc','pytensor','arviz','scipy','statsmodels','pandas','xarray','methods'} or fullname.startswith('services.generator'):
            raise Data03Error()


def run_driver(lease_unix,public,limit):
    sys.meta_path.insert(0,NoFits())
    sys.path.insert(0,'/app');sys.path.insert(1,'/carrier')
    ready_until=min(time.monotonic()+30,time.monotonic()+max(0,lease_unix-time.time()))
    while True:
        require(time.monotonic()<ready_until)
        try:
            with socket.create_connection(('generator',8780),timeout=min(1,ready_until-time.monotonic())):break
        except OSError:time.sleep(min(.1,max(0,ready_until-time.monotonic())))
    from fastapi.testclient import TestClient
    import admin
    from contracts.service.live_hold import InstalledBundle
    from contracts.domain.protocol import LAW_REF,NOF1_REF
    from contracts.domain.analysis import canonical
    from services.foundation.app import Settings,create_app,HASHER
    from services.foundation.store import Store
    import services.foundation.app as app_module
    require(Path(admin.__file__).resolve()==Path('/carrier/admin.py') and Path(app_module.__file__).resolve()==Path('/app/services/foundation/app.py'))
    root=Path('/data');require(not (root/'remission.sqlite').exists() and not (root/'bootstrap').exists())
    os.umask(0o077);exports=Exports(root/'exports')
    declaration=dict(label=LABEL,seed=SEED,count=COUNT,family='nof1_med',activation_day=0,target_ordinal=7,law=LAW_REF,protocol=NOF1_REF)
    exports.once('declaration.json',declaration)
    passwords={role:{'username':'ndata03-'+role+'-'+secrets.token_hex(8),'password':secrets.token_urlsafe(32)} for role in ('owner','foreign')}
    exports.once('credentials.json',passwords)
    deployment=json.loads(Path('/carrier/deployment.json').read_bytes());bootstrap=root/'bootstrap';bootstrap.mkdir(mode=0o700)
    admin.initialize(root/'remission.sqlite',bootstrap,deployment)
    installed=InstalledBundle.model_validate_json((bootstrap/'bundle.json').read_bytes())
    require(installed.control.enabled is False and not installed.authority.enabled and not installed.authority.grants)
    store=Store(root/'remission.sqlite',installed)
    for role,value in passwords.items():admin.create_account(store,value['username'],'Synthetic DATA03 '+role,value['password'],HASHER)
    settings=Settings(store.path,installed,origin=ORIGIN,generator_url='http://generator:8780',source_commit=deployment['source_commit'])
    app=create_app(settings)
    clients=[TestClient(app,base_url=ORIGIN) for _ in range(3)]
    physician=Physician(store,*clients,passwords,exports,limit,public)
    try:
        first,foreign,anonymous=clients
        physician.login(first,'owner');physician.login(foreign,'foreign')
        owner=physician.live_once(first)['principal']['id'];public.phase('initialized')
        panel=dict(schema_version='2.0.0',kind='poc_protocol_panel',seed=SEED,count=COUNT,family='nof1_med',law=LAW_REF,protocol=NOF1_REF)
        physician.denied(lambda:physician.call(anonymous,'GET','/api/patients',expected=401))
        physician.denied(lambda:physician.command(first,'owner','/api/panels/generate',panel,'denied',0,'csrf',expected=403,headers_override={'Origin':ORIGIN}))
        csrf=physician.live_once(first)['csrf']
        physician.denied(lambda:physician.command(first,'owner','/api/panels/generate',panel,'denied',0,'origin',expected=403,headers_override={'Origin':'https://denied.example.org','X-CSRF-Token':csrf}))
        def freeze_generation(response):
            selected=validate_generation(response.json())
            exports.once('generation-response.json',response.content,raw=True)
            exports.once('selection.json',selected)
            return selected,response.content
        selection,original=physician.command(first,'owner','/api/panels/generate',panel,'generate',0,'panel',consume=freeze_generation)
        physician.command(first,'owner','/api/panels/generate',panel,'generate',0,'known-success-replay',key='ndata03-r1-generate-0-panel',consume=lambda r:require(r.json()==json.loads(original)))
        physician.call(foreign,'GET','/api/patients',consume=lambda r:require(r.json()['denominator']==0))
        public.phase('cohort_frozen')
        for ordinal,patient in enumerate(selection['generation_order'],1):physician.authorize(patient,ordinal)
        receipts=[];receipt36=None
        for day in (36,72):
            for ordinal,patient in enumerate(selection['generation_order'],1):physician.advance(patient,ordinal,day)
            private,historical=physician.barrier(selection,owner,day)
            if day==36:receipt36=private
            else:
                # Compare the original persisted receipt, retaining its old
                # versions. Current72 admission above is a separate check.
                saved=(exports.root/'observed-day36.json').read_bytes()
                require(len(saved)<=FILE_CAP and json.loads(saved)==receipt36)
                require(canonical(historical)==canonical(receipt36['histories']))
            exports.once('observed-day'+str(day)+'.json',private)
            receipts.append(private['public']);public.phase('receipt'+str(day),0,day)
        require(physician.advances==180)
        public.send(dict(kind='n_data03_result',status='complete_'+receipts[-1]['readiness']['status'],synthetic=True,
            declaration=selection,receipts=receipts,advances=180,nightly_increments=864,
            no_analysis_jobs=True,historical36_equal=True))
    finally:
        for client in clients:client.close()


def parse_rows(raw):
    if len(raw)>STDOUT_CAP or (raw and not raw.endswith(b'\n')):raise Data03Error('output_limit')
    def pairs(items):
        value={}
        for key,item in items:
            require(key not in value);value[key]=item
        return value
    def nonfinite(_value):raise Data03Error()
    rows=[validate_public(json.loads(line,object_pairs_hook=pairs,parse_constant=nonfinite)) for line in raw.splitlines()]
    require(len([r for r in rows if r['kind']=='n_data03_phase'])<=256)
    require(len([r for r in rows if r['kind']=='n_data03_identity'])<=1 and len([r for r in rows if r['kind']=='n_data03_result'])<=1)
    for line,row in zip(raw.splitlines(),rows):
        if row['kind']=='n_data03_phase':require(len(line)+1<=512)
        if row['kind']=='n_data03_result':require(len(line)+1<=128*1024)
    return rows


def terminate_child(process):
    """Only the returned Popen object is authority for kill/wait."""
    if process.poll() is None:process.kill()
    try:return process.wait(timeout=2),True
    except subprocess.TimeoutExpired:return None,False


def entry(lease_unix):
    require(sys.platform=='linux' and math.isfinite(lease_unix) and 0<lease_unix-time.time()<=7140)
    nonce=secrets.token_hex(16);stdout=Path('/tmp/n-data03-child.stdout');stderr=Path('/tmp/n-data03-child.stderr')
    process=None;matched=False;reason='child_failed';reaped=False;returncode=None
    with stdout.open('xb') as out,stderr.open('xb') as err:
        process=subprocess.Popen([sys.executable,'-P','-B',str(Path(__file__).resolve()),'--child',
            '--lease-unix',str(lease_unix),'--nonce',nonce],stdin=subprocess.PIPE,stdout=out,stderr=err)
        try:
            arm_until=min(lease_unix,time.time()+5)
            while time.time()<arm_until and process.poll() is None:
                with stdout.open('rb') as stream:first=stream.readline(513)
                if first.endswith(b'\n'):
                    rows=parse_rows(first);require(len(rows)==1)
                    require(rows[0]==dict(kind='n_data03_identity',pid=process.pid,ppid=os.getpid(),nonce=nonce))
                    matched=True;break
                time.sleep(.05)
            if not matched:raise Data03Error('identity_rejected')
            process.stdin.write((nonce+'\n').encode());process.stdin.flush();process.stdin.close()
            while process.poll() is None:
                if time.time()>=lease_unix:raise Data03Error('lease_deadline')
                if stdout.stat().st_size>DRIVER_CAP or stderr.stat().st_size>STDERR_CAP:raise Data03Error('output_limit')
                time.sleep(.1)
            returncode=process.wait(timeout=2);reaped=True
            require(stdout.stat().st_size<=DRIVER_CAP and stderr.stat().st_size<=STDERR_CAP)
            raw=stdout.read_bytes();rows=parse_rows(raw)
            require(rows and rows[0]==dict(kind='n_data03_identity',pid=process.pid,ppid=os.getpid(),nonce=nonce))
            require(returncode==0 and rows[-1]['kind']=='n_data03_result')
            reason='completed'
        except BaseException as error:
            reason=error.code if type(error) is Data03Error else 'child_failed'
        finally:
            if process.stdin and not process.stdin.closed:process.stdin.close()
            if not reaped:returncode,reaped=terminate_child(process)
    # Never forward an unvalidated row or any child stderr/error body. Captures
    # remain in this retained container's tmpfs; only fixed public rows travel.
    with stdout.open('rb') as stream:raw=stream.read(DRIVER_CAP+1)
    try:
        require(len(raw)<=DRIVER_CAP);parse_rows(raw)
    except BaseException:
        reason='output_limit' if len(raw)>DRIVER_CAP else 'child_failed';raw=b''
    custody=dict(kind='n_data03_custody',pid=process.pid,reaped=reaped,returncode=returncode,
        identity_matched=matched,reason=reason,stdout_bytes=min(stdout.stat().st_size,DRIVER_CAP+1),
        stderr_bytes=min(stderr.stat().st_size,STDERR_CAP+1),broader_descendants='UNKNOWN')
    validate_public(custody)
    tail=encoded(custody)
    if reason!='completed':tail=encoded(dict(kind='n_data03_error',code=reason))+tail
    require(len(raw)+len(tail)<=STDOUT_CAP)
    sys.stdout.buffer.write(raw+tail);sys.stdout.buffer.flush()
    return 0 if reason=='completed' and reaped and returncode==0 else 125


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lease-unix',type=float,required=True)
    parser.add_argument('--child',action='store_true');parser.add_argument('--nonce')
    args=parser.parse_args()
    if not args.child:return entry(args.lease_unix)
    require(type(args.nonce) is str and len(args.nonce)==32)
    public=Public(lambda data:(sys.stdout.buffer.write(data),sys.stdout.buffer.flush()))
    limit=RequestLimit(args.lease_unix);signal.signal(signal.SIGALRM,limit.expired)
    public.send(dict(kind='n_data03_identity',pid=os.getpid(),ppid=os.getppid(),nonce=args.nonce))
    # No app imports, private writes, generation or credentials before this ACK.
    signal.setitimer(signal.ITIMER_REAL,min(5,max(.001,args.lease_unix-time.time())))
    require(sys.stdin.buffer.readline(34)==(args.nonce+'\n').encode())
    signal.setitimer(signal.ITIMER_REAL,0)
    try:run_driver(args.lease_unix,public,limit)
    except BaseException as error:
        public.send(dict(kind='n_data03_error',code=error.code if type(error) is Data03Error else 'driver_failed'))
        return 1
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except BaseException as error:
        if type(error) is SystemExit:raise
        sys.stdout.buffer.write(encoded(dict(kind='n_data03_error',code=error.code if type(error) is Data03Error else 'driver_failed')))
        sys.stdout.buffer.flush();sys.exit(1)
