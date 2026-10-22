"""Explicit unrouted 003-checkpoint backup/004 upgrade; never normal startup."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib,json,os,re,sqlite3
from pathlib import Path
from pydantic import AwareDatetime
from contracts.domain.common import StrictModel,Identifier,Name,VersionRef
from contracts.domain.observed_v2 import ExactRef
from contracts.service.live_hold import Header,ControlBinding,ReviewRules,Requirement,SourceGrant
from .admission import AdmissionGate
from .store import Store,canonical,digest,instant,timestamp,validate_bundle
from .cutover import IMMUTABLE,assert_quiescent,generation_effects
from .live_tasks import binding_value


class Grant003(StrictModel):
    account_id: Identifier
    service_patient_id: Identifier
    archive_patient_id: Identifier
    source_id: Identifier
    source_version: Name
    run_id: Identifier
    partition_id: Identifier
    archive_id: Identifier
    package_sha256: str
    archive_authority_sha256: str
    ownership_ref: ExactRef
    episode_namespace: Identifier
    allowed_operations: list[str]
    trigger_rules: list[VersionRef]
    required_reviews: list[Requirement]
    follow_up_owner_id: Identifier
    follow_up_policy: VersionRef
    due_at: AwareDatetime
    escalation_destination: Name


class Authority003(Header):
    authority_id: Identifier
    version: VersionRef
    enabled: bool
    observed_binding: VersionRef
    archive_verifier: VersionRef
    producer: VersionRef
    source_registry: VersionRef
    execution: str
    grants: list[Grant003]


class Bundle003(StrictModel):
    control: ControlBinding
    authority: Authority003
    review_rules: ReviewRules


def legacy_snapshot(db):
    return {table:[tuple(row) for row in db.execute('SELECT * FROM '+table+' ORDER BY rowid')]
        for table in IMMUTABLE if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()}


def verify_legacy_schema(db):
    folder=Path(__file__).with_name('migrations')
    expected={'001_foundation.sql':'e48f951e9a12991154bdff170645ae737f73adcb',
        '002_observed_archive.sql':'567152e7005837519003b62d9fc798c022cd0812','003_live_hold.sql':'56cbb7f8d710f5451e923ac8c2c52a613f23edb0'}
    scripts=[]
    for name,blob in expected.items():
        raw=(folder/name).read_bytes().replace(b'\r\n',b'\n')
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=blob:raise ValueError('unsupported_003_migration_source')
        scripts.append(raw.decode())
    def shape(connection):
        return [(r[0],r[1],re.sub(r'\s+',' ',r[2] or '').strip()) for r in connection.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY type,name")]
    with closing(sqlite3.connect(':memory:')) as expected_db:
        expected_db.executescript('\n'.join(scripts))
        if shape(db)!=shape(expected_db):raise ValueError('unsupported_003_database_schema')
    if {r[0] for r in db.execute('SELECT version FROM schema_migrations')}!={1,2,3}:raise ValueError('unsupported_003_database_schema')


def map_legacy_tasks(db):
    """Unique original exact binding only; no split/guess for an old aggregate."""
    mappings=[]
    for row in db.execute('SELECT * FROM live_hold_episodes ORDER BY id,generation').fetchall():
        e=json.loads(row['payload']);converted=[];all_values={}
        source_key=json.loads(row['source_key'])
        for original in e['grants']:
            old=Grant003.model_validate_json(canonical(original));bindings=[]
            for rule in old.trigger_rules:
                followups={}
                for bundle_ref in e['bundle_refs']:
                    if (bundle_ref['archive_id'],bundle_ref['partition_id'])!=(old.archive_id,old.partition_id):continue
                    stored=db.execute('SELECT * FROM observed_archives WHERE id=? AND owner_id=?',(old.archive_id,old.account_id)).fetchone()
                    if stored is None or stored['export_sha256']!=old.package_sha256:raise ValueError('legacy_task_package_mismatch')
                    bundle=db.execute('SELECT payload,payload_sha256 FROM observed_archive_entries WHERE archive_id=? AND partition_id=? AND patient_id=? AND record_id=?',
                        (old.archive_id,old.partition_id,row['patient_id'],bundle_ref['bundle_ref']['record_id'])).fetchone()
                    if bundle is None or bundle['payload_sha256']!=bundle_ref['bundle_ref']['payload_sha256']:raise ValueError('legacy_task_bundle_mismatch')
                    value=json.loads(bundle['payload'])
                    if (value['hold_episode_id'],value['run_id'],value['partition_id'],value['owner_id'])!=(source_key[3],old.run_id,old.partition_id,old.account_id):raise ValueError('legacy_task_episode_mismatch')
                    for trigger_ref in value['trigger_refs']:
                        trigger=db.execute('SELECT payload,payload_sha256 FROM observed_archive_entries WHERE archive_id=? AND partition_id=? AND record_id=?',
                            (old.archive_id,old.partition_id,trigger_ref['record_id'])).fetchone()
                        if trigger is None or trigger['payload_sha256']!=trigger_ref['payload_sha256']:raise ValueError('legacy_task_trigger_mismatch')
                        trigger=json.loads(trigger['payload'])
                        if trigger['rule']!=rule.model_dump(mode='json'):continue
                        for reference in trigger['follow_up_refs']:
                            if reference not in value['follow_up_refs']:raise ValueError('legacy_task_followup_scope')
                            task=db.execute('SELECT payload,payload_sha256 FROM observed_archive_entries WHERE archive_id=? AND partition_id=? AND patient_id=? AND record_id=?',
                                (old.archive_id,old.partition_id,row['patient_id'],reference['record_id'])).fetchone()
                            if task is None or task['payload_sha256']!=reference['payload_sha256']:raise ValueError('legacy_task_followup_mismatch')
                            task=json.loads(task['payload'])
                            if (task['owner'],instant(task['due_at']),task['escalation_destination'])!=(old.follow_up_owner_id,old.due_at,old.escalation_destination):raise ValueError('legacy_task_followup_mismatch')
                            follow=dict(reference=reference,owner_id=old.follow_up_owner_id,policy=old.follow_up_policy.model_dump(mode='json'),due_at=timestamp(old.due_at),escalation_destination=old.escalation_destination)
                            followups[canonical(follow)]=follow
                if followups:bindings.append(dict(trigger_rule=rule.model_dump(mode='json'),required_reviews=[r.model_dump(mode='json') for r in old.required_reviews],follow_ups=list(followups.values())))
            common=old.model_dump(mode='json')
            for key in ['trigger_rules','required_reviews','follow_up_owner_id','follow_up_policy','due_at','escalation_destination']:common.pop(key)
            common['trigger_bindings']=bindings
            grant=SourceGrant.model_validate_json(canonical(common));converted.append(grant.model_dump(mode='json'))
            for binding in grant.trigger_bindings:
                for follow in binding.follow_ups:
                    value=binding_value(grant,follow,source_key[3]);all_values[canonical(value)]=value
        task=db.execute('SELECT * FROM live_hold_tasks WHERE id=? AND episode_id=? AND generation=?',(e['task_id'],row['id'],row['generation'])).fetchone()
        if task is None:raise ValueError('legacy_task_unavailable')
        payload=json.loads(task['payload'])
        matching=[v for v in all_values.values() if v['follow_up']['owner_id']==task['owner_id']
            and instant(v['follow_up']['due_at'])==instant(task['due_at']) and v['follow_up']['policy']==payload['policy']
            and v['follow_up']['escalation_destination']==payload['escalation_destination']]
        if len(matching)!=1:raise ValueError('unsupported_ambiguous_003_task_mapping')
        e['legacy_003_grants']=e['grants'];e['grants']=converted;e['task_ids']=[e.pop('task_id')]
        mappings.append((dict(row),e,matching[0]))
    return mappings


def upgrade_checkpoint003(target,source,previous_raw,new_bundle,*,clock=lambda:datetime.now(timezone.utc),fault=None):
    """Supervisor must drain/stop old workers; this function never enables routing."""
    previous=Bundle003.model_validate_json(previous_raw);validate_bundle(new_bundle)
    old_control=previous.control;new=new_bundle.control
    if new.database_instance_id==old_control.database_instance_id or new.authority_generation!=old_control.authority_generation+1:
        raise ValueError('upgrade_requires_new_instance_and_generation')
    if new_bundle.authority.follow_up_amendments:raise ValueError('upgrade_then_separate_exact_followup_amendment')
    target=Path(target).absolute();source=Path(source).resolve(strict=True)
    if target.exists() or Path(str(target)+'.admission.lock').exists():raise ValueError('cutover_requires_new_private_path')
    assert_quiescent(source);target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with closing(sqlite3.connect(source)) as old,closing(sqlite3.connect(target)) as copied:
        old.row_factory=sqlite3.Row;row=old.execute('SELECT * FROM service_control WHERE singleton=1').fetchone()
        lock=Path(str(source)+'.admission.lock')
        if (row is None or any(row[k]!=v for k,v in old_control.model_dump().items())
                or digest(canonical(previous.authority.model_dump(mode='json')))!=row['authority_sha256']
                or digest(canonical(previous.review_rules.model_dump(mode='json')))!=row['review_rules_sha256']
                or (row['database_device'],row['database_inode'],row['lock_device'],row['lock_inode'])!=
                   (source.stat().st_dev,source.stat().st_ino,lock.stat().st_dev,lock.stat().st_ino)):
            raise ValueError('legacy_control_or_physical_identity_mismatch')
        verify_legacy_schema(old)
        if old.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]!=0:raise ValueError('legacy_database_not_quiescent')
        old.backup(copied)
    os.chmod(target,0o600);new_lock=Path(str(target)+'.admission.lock');new_lock.touch(mode=0o600,exist_ok=False)
    with AdmissionGate(target).hold(),closing(sqlite3.connect(target,isolation_level=None)) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA journal_mode=WAL')
        before=legacy_snapshot(db);mappings=map_legacy_tasks(db);at=clock()
        old=dict(db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone())
        if at<instant(old['last_receipt_at']):raise ValueError('service_clock_regression')
        db.executescript('BEGIN IMMEDIATE;\n'+Path(__file__).with_name('migrations').joinpath('004_live_hold_followups.sql').read_text())
        try:
            for row,e,value in mappings:
                task_id=e['task_ids'][0];encoded=canonical(value)
                db.execute('INSERT INTO live_hold_task_bindings VALUES(?,?,?,?,?,?,?)',(row['id'],row['generation'],digest(encoded),task_id,task_id,None,encoded))
                db.execute('UPDATE live_hold_episodes SET payload=? WHERE id=? AND generation=?',(canonical(e),row['id'],row['generation']))
            ds,ls=target.stat(),new_lock.stat()
            db.execute('UPDATE service_control SET database_instance_id=?,authority_generation=?,authority_sha256=?,review_rules_sha256=?,enabled=?,activation_id=?,activated_at=?,database_device=?,database_inode=?,lock_device=?,lock_inode=? WHERE singleton=1',
                (new.database_instance_id,new.authority_generation,new.authority_sha256,new.review_rules_sha256,int(new.enabled),new.activation_id,timestamp(at),ds.st_dev,ds.st_ino,ls.st_dev,ls.st_ino))
            db.execute('INSERT INTO live_authority_history VALUES(?,?,?,?,?,?,?)',(new.authority_generation,new.authority_sha256,new.review_rules_sha256,
                canonical(new_bundle.authority.model_dump(mode='json')),canonical(new_bundle.review_rules.model_dump(mode='json')),new.activation_id,timestamp(at)))
            generation_effects(db,old,new_bundle,at,[])
            for table in IMMUTABLE:
                for operation in ['UPDATE','DELETE']:
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_record'); END")
            for table,rows in before.items():
                if [tuple(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY rowid')][:len(rows)]!=rows:raise ValueError('legacy_immutable_bytes_changed')
            if db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('upgrade_foreign_key_failure')
            from .live_journal import receive
            receive(db,at)
            receipt=canonical(dict(status='upgraded_003_to_004_unrouted',activation_id=new.activation_id,source_instance=old_control.database_instance_id,
                control=new.model_dump(mode='json'),preserved_task_ids=[e['task_ids'][0] for _,e,_ in mappings],immutable_prefixes_unchanged=True))
            db.execute('INSERT INTO live_activation_receipts VALUES(?,?,?)',(new.activation_id,receipt,digest(receipt)))
            if fault:fault('before_004_upgrade_commit')
            db.commit()
        except BaseException:db.rollback();raise
    if fault:fault('after_004_upgrade_commit')
    return Store(target,new_bundle,clock=clock)
