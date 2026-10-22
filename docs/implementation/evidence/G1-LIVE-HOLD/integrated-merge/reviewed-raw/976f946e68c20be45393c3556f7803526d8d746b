"""Explicit offline activation into a new deployment-private path only."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import uuid
from contracts.service.live_hold import CAPABILITY, ControlBinding, InstalledBundle, LiveHoldAuthority, ReviewRules
from .admission import AdmissionError, AdmissionGate
from .store import Store, canonical, digest, instant, timestamp

IMMUTABLE = ['events', 'decisions', 'bundles', 'tasks', 'receipts', 'ingestion_receipts',
             'state_changes', 'observed_archives', 'observed_archive_entries', 'observed_archive_artifacts',
             'live_authority_history', 'live_hold_operations', 'live_hold_reviews', 'live_hold_tasks',
             'live_hold_task_events', 'live_hold_keys', 'live_patient_journals', 'live_safety_facts',
             'live_projection_receipts', 'live_export_receipts']
IMMUTABLE.append('live_activation_receipts')


def protected_snapshot(db):
    """Exact SQL values, including original raw/display bytes; hashes expose no credentials."""
    tables=['accounts','patients','events','decisions','bundles','tasks','receipts','ingestion_receipts',
            'state_changes','observed_archives','observed_archive_entries','observed_archive_artifacts']
    result={}
    for table in tables:
        if db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',('table',table)).fetchone():
            rows=[[dict(bytes=bytes(value).hex()) if isinstance(value,bytes) else value for value in tuple(row)]
                  for row in db.execute('SELECT * FROM '+table+' ORDER BY rowid')]
            result[table]=dict(rows=len(rows),sha256=digest(canonical(rows)))
    return result


def bundle_for(authority: LiveHoldAuthority, rules: ReviewRules, *, generation=1, instance=None):
    return InstalledBundle(control=ControlBinding(database_instance_id=instance or str(uuid.uuid4()),
        capability=CAPABILITY, minimum_reader_writer_capability=CAPABILITY,
        authority_generation=generation, authority_sha256=digest(canonical(authority.model_dump(mode='json'))),
        review_rules_sha256=digest(canonical(rules.model_dump(mode='json'))),
        enabled=authority.enabled, activation_id='activation-'+uuid.uuid4().hex), authority=authority, review_rules=rules)


def assert_quiescent(source: Path):
    """Fail if any observable process has the old DB, WAL or SHM open."""
    targets = {str(source.resolve()), str(source.resolve())+'-wal', str(source.resolve())+'-shm'}
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            handles = list((process/'fd').iterdir())
        except FileNotFoundError:
            continue
        except PermissionError as error:
            raise AdmissionError('cutover_process_inventory_unavailable') from error
        for handle in handles:
            try:
                if os.readlink(handle).removesuffix(' (deleted)') in targets:
                    raise AdmissionError('cutover_old_database_handle_open')
            except FileNotFoundError:
                continue


def activate_new(target: Path, installed: InstalledBundle, at, *, source: Path | None = None, fault=None):
    """Operator must stop routing/restarts; this creates no service routing.

    New target must not exist. Copy via SQLite backup after inspecting old handles.
    Activation never mutates the historical source or silently restores its routing.
    """
    target = Path(target).absolute()
    if target.exists() or Path(str(target)+'.admission.lock').exists():
        raise ValueError('cutover_requires_new_private_path')
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if source is not None:
        source = source.resolve(strict=True)
        assert_quiescent(source)
        # This offline administrator briefly opens the quiesced original RW:
        # SQLite WAL readers may need a shared-memory file even for a backup.
        # Checkpoint all committed WAL frames, then take SQLite's consistent backup.
        with closing(sqlite3.connect(source)) as old, closing(sqlite3.connect(target)) as new:
            checkpoint=old.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            if checkpoint[0]!=0:
                raise AdmissionError('cutover_old_database_not_quiescent')
            old.backup(new)
    else:
        target.touch(mode=0o600)
    os.chmod(target, 0o600)
    lock = Path(str(target)+'.admission.lock')
    lock.touch(mode=0o600, exist_ok=False)
    gate = AdmissionGate(target)
    clock = timestamp(at)
    with gate.hold(), closing(sqlite3.connect(target, isolation_level=None)) as db:
        db.row_factory = sqlite3.Row
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='service_control'").fetchone():
            raise ValueError('capable_database_requires_generation_cutover')
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        preserved=protected_snapshot(db)
        scripts = Path(__file__).with_name('migrations')
        # One explicit offline transaction, including all schema/bootstrap facts.
        sql = '\n'.join((scripts/name).read_text(encoding='utf-8') for name in ['001_foundation.sql','002_observed_archive.sql','003_live_hold.sql'])
        db.executescript('BEGIN IMMEDIATE;\n'+sql)
        try:
            c = installed.control
            database_stat=target.stat();lock_stat=lock.stat()
            db.execute('INSERT INTO service_control VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (c.database_instance_id,c.capability,c.minimum_reader_writer_capability,c.authority_generation,
                 c.authority_sha256,c.review_rules_sha256,int(c.enabled),c.activation_id,clock,clock,
                 database_stat.st_dev,database_stat.st_ino,lock_stat.st_dev,lock_stat.st_ino))
            db.execute('INSERT INTO live_authority_history VALUES(?,?,?,?,?,?,?)',
                (c.authority_generation,c.authority_sha256,c.review_rules_sha256,
                 canonical(installed.authority.model_dump(mode='json')),canonical(installed.review_rules.model_dump(mode='json')),c.activation_id,clock))
            from .live_journal import initialize_journal
            for row in db.execute('SELECT id FROM patients').fetchall():
                initialize_journal(db,row['id'],at)
            for table in IMMUTABLE:
                for operation in ['UPDATE','DELETE']:
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_record'); END")
            after=protected_snapshot(db)
            if any(after.get(table)!=value for table,value in preserved.items()):
                raise ValueError('cutover_original_bytes_changed')
            receipt=canonical(dict(status='activated_unrouted',activation_id=c.activation_id,source_backup=bool(source),
                control=c.model_dump(mode='json'),activated_at=clock,preserved_tables=preserved,
                deployment_assumption='External supervisor stopped all old workers/restarts and routing; new private volume only'))
            db.execute('INSERT INTO live_activation_receipts VALUES(?,?,?)',(c.activation_id,receipt,digest(receipt)))
            if fault:
                fault('before_cutover_commit')
            db.commit()
        except BaseException:
            db.rollback()
            raise
    if fault:
        fault('after_cutover_commit')
    return Store(target, installed)


def change_generation(store,new_bundle,at,*,fault=None):
    """Offline stopped-worker administrative cutover; never an HTTP operation."""
    from .live_journal import active_episodes,append_fact,receive
    from .live_hold import object_hash,advance
    from .workflow import create_decision
    with store.transaction(write=True) as db:
        old=db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone();new=new_bundle.control
        if (new.database_instance_id!=old['database_instance_id'] or new.authority_generation!=old['authority_generation']+1
                or digest(canonical(new_bundle.authority.model_dump(mode='json')))!=new.authority_sha256
                or digest(canonical(new_bundle.review_rules.model_dump(mode='json')))!=new.review_rules_sha256):
            raise ValueError('invalid_generation_cutover')
        if at<instant(old['last_receipt_at']):
            raise ValueError('service_clock_regression')
        db.execute('UPDATE service_control SET authority_generation=?,authority_sha256=?,review_rules_sha256=?,enabled=?,activation_id=?,activated_at=? WHERE singleton=1',
            (new.authority_generation,new.authority_sha256,new.review_rules_sha256,int(new.enabled),new.activation_id,timestamp(at)))
        db.execute('INSERT INTO live_authority_history VALUES(?,?,?,?,?,?,?)',(new.authority_generation,new.authority_sha256,new.review_rules_sha256,
            canonical(new_bundle.authority.model_dump(mode='json')),canonical(new_bundle.review_rules.model_dump(mode='json')),new.activation_id,timestamp(at)))
        for patient in db.execute('SELECT id FROM patients').fetchall():
            pid=patient['id'];episodes=active_episodes(db,pid)
            if not episodes:continue
            operation_id='authority-'+uuid.uuid4().hex;resulting=[]
            for row in episodes:
                e=row['data'];obligations={r['requirement_id']:r for r in e['obligations']}
                for grant in new_bundle.authority.grants:
                    if grant.service_patient_id==pid and grant.episode_namespace in json.loads(row['source_key']):
                        for r in grant.required_reviews:
                            value=r.model_dump(mode='json')
                            if r.requirement_id in obligations and obligations[r.requirement_id]!=value:
                                raise ValueError('obligation_substitution_requires_reviewed_policy')
                            obligations[r.requirement_id]=value
                e['obligations']=sorted(obligations.values(),key=lambda r:r['requirement_id'])
                public=[{k:r[k] for k in ['requirement_id','definition']} for r in e['obligations']]
                e['obligation_set_sha256']=object_hash(public);e['current_review_id']=None
                db.execute('UPDATE live_hold_episodes SET payload=?,last_operation=? WHERE id=? AND generation=?',(canonical(e),operation_id,row['id'],row['generation']))
                resulting.append(dict(episode_id=row['id'],generation=row['generation'],obligations=public,obligation_set_sha256=e['obligation_set_sha256']))
                db.execute('INSERT INTO live_hold_task_events VALUES(?,?,?,?)',('task-event-'+uuid.uuid4().hex,e['task_id'],operation_id,canonical(dict(status='pending',reason='authority_changed',obligations=e['obligations']))))
            journal=db.execute('SELECT journal_id FROM live_patient_journals WHERE patient_id=?',(pid,)).fetchone()[0]
            append_fact(db,pid,operation_id,at,dict(type='authority_changed',old_generation=old['authority_generation'],new_generation=new.authority_generation,
                old_authority_sha256=old['authority_sha256'],new_authority_sha256=new.authority_sha256,old_review_rules_sha256=old['review_rules_sha256'],
                new_review_rules_sha256=new.review_rules_sha256,prior_journal_id=journal,active_episodes=resulting))
            advance(db,pid);decision_id=create_decision(db,pid,at)
            response=dict(status='committed',operation_id=operation_id,decision_id=decision_id,authority_generation=new.authority_generation)
            db.execute('INSERT INTO live_hold_operations(id,patient_id,family,semantic_sha256,received_at,payload,response) VALUES(?,?,?,?,?,?,?)',
                (operation_id,pid,'authority_changed',object_hash([operation_id,new.authority_generation]),timestamp(at),canonical(response),canonical(response)))
            db.execute('INSERT INTO state_changes VALUES(?,?,?,?,?)',('audit-'+uuid.uuid4().hex,pid,'offline-administrator',timestamp(at),canonical(response)))
            db.execute('DELETE FROM drafts WHERE patient_id=?',(pid,))
        receive(db,at)
        if fault:fault('before_generation_commit')
    if fault:fault('after_generation_commit')
    return Store(store.path,new_bundle,clock=store.clock)
