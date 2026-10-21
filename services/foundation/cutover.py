"""Explicit offline activation into a new deployment-private path only."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import uuid
from contracts.service.live_hold import CAPABILITY, ControlBinding, InstalledBundle, LiveHoldAuthority, ReviewRules
from .admission import AdmissionError, AdmissionGate
from .store import Store, canonical, digest, timestamp

IMMUTABLE = ['events', 'decisions', 'bundles', 'tasks', 'receipts', 'ingestion_receipts',
             'state_changes', 'observed_archives', 'observed_archive_entries', 'observed_archive_artifacts',
             'live_authority_history', 'live_hold_operations', 'live_hold_reviews', 'live_hold_tasks',
             'live_hold_task_events', 'live_hold_keys', 'live_patient_journals', 'live_safety_facts',
             'live_projection_receipts', 'live_export_receipts']


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
        with closing(sqlite3.connect(f'file:{source}?mode=ro', uri=True)) as old, closing(sqlite3.connect(target)) as new:
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
        scripts = Path(__file__).with_name('migrations')
        # One explicit offline transaction, including all schema/bootstrap facts.
        sql = '\n'.join((scripts/name).read_text(encoding='utf-8') for name in ['001_foundation.sql','002_observed_archive.sql','003_live_hold.sql'])
        db.executescript('BEGIN IMMEDIATE;\n'+sql)
        try:
            c = installed.control
            db.execute('INSERT INTO service_control VALUES(1,?,?,?,?,?,?,?,?,?,?)',
                (c.database_instance_id,c.capability,c.minimum_reader_writer_capability,c.authority_generation,
                 c.authority_sha256,c.review_rules_sha256,int(c.enabled),c.activation_id,clock,clock))
            db.execute('INSERT INTO live_authority_history VALUES(?,?,?,?,?,?,?)',
                (c.authority_generation,c.authority_sha256,c.review_rules_sha256,
                 canonical(installed.authority.model_dump(mode='json')),canonical(installed.review_rules.model_dump(mode='json')),c.activation_id,clock))
            from .live_journal import initialize_journal
            for row in db.execute('SELECT id FROM patients').fetchall():
                initialize_journal(db,row['id'],at)
            for table in IMMUTABLE:
                for operation in ['UPDATE','DELETE']:
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_record'); END")
            if fault:
                fault('before_cutover_commit')
            db.commit()
        except BaseException:
            db.rollback()
            raise
    if fault:
        fault('after_cutover_commit')
    return Store(target, installed)
