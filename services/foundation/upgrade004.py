"""Explicit stopped schema4→5 upgrade; startup never runs this operation."""
from contextlib import closing
from pathlib import Path
import sqlite3
from .admission import AdmissionGate, AdmissionError
from .cutover import assert_quiescent
from .store import Store, validate_bundle


def upgrade004(database, installed, *, clock=None):
    database = Path(database).resolve(strict=True)
    validate_bundle(installed)
    assert_quiescent(database)
    # Validate physical identity/control and all existing migrations before DDL.
    with AdmissionGate(database).hold(), closing(sqlite3.connect(database,isolation_level=None)) as db:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        row=db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone()
        ds,ls=database.stat(),Path(str(database)+'.admission.lock').stat()
        if (row is None or any(row[k]!=v for k,v in installed.control.model_dump().items())
            or (row['database_device'],row['database_inode'],row['lock_device'],row['lock_inode']) != (ds.st_dev,ds.st_ino,ls.st_dev,ls.st_ino)
            or {r[0] for r in db.execute('SELECT version FROM schema_migrations')} != {1,2,3,4}):
            raise AdmissionError('service_generation_mismatch')
        sql=Path(__file__).with_name('migrations').joinpath('005_analysis.sql').read_text(encoding='utf-8')
        try:
            db.executescript('BEGIN IMMEDIATE;\n'+sql)
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('upgrade_foreign_key_failure')
            db.commit()
        except BaseException:
            db.rollback()
            raise
    return Store(database,installed,**({'clock':clock} if clock else {}))
