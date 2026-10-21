"""SQLite authority: separate connections and explicit rollback-safe transactions."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Iterator
from contracts.service.live_hold import CAPABILITY, InstalledBundle
from .admission import AdmissionError, AdmissionGate


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def instant(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone_required: supply an explicit UTC offset")
    return result.astimezone(timezone.utc)


def timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timezone_required")
    return value.astimezone(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str | Path, installed: InstalledBundle):
        # Normal startup never creates directories, DBs or runs legacy SQL.
        self.path = Path(path)
        self.installed = InstalledBundle.model_validate_json(installed.model_dump_json())
        self.gate = AdmissionGate(self.path)
        with self.gate.hold(), closing(self.connect()) as db:
            self.validate_control(db)

    def validate_control(self, db):
        try:
            row = db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone()
        except sqlite3.Error as error:
            raise AdmissionError('service_generation_mismatch') from error
        expected = self.installed.control.model_dump()
        if (row is None or any(row[k] != v for k, v in expected.items())
                or row['capability'] != CAPABILITY
                or digest(canonical(self.installed.authority.model_dump(mode='json'))) != row['authority_sha256']
                or digest(canonical(self.installed.review_rules.model_dump(mode='json'))) != row['review_rules_sha256']):
            raise AdmissionError('service_generation_mismatch')
        return row

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, isolation_level=None, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=5000")
        if db.execute("PRAGMA foreign_keys").fetchone()[0] != 1 or db.execute("PRAGMA synchronous").fetchone()[0] != 2:
            raise RuntimeError("required SQLite pragmas unavailable")
        return db

    @contextmanager
    def transaction(self, *, write: bool = False, prepare=None, authorize=None) -> Iterator[sqlite3.Connection]:
        with self.gate.hold():
            db = self.connect()
            try:
                self.validate_control(db)
                if prepare:
                    prepare(db)  # committed autocommit reads; sample R here.
                db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                self.validate_control(db)
                if authorize:
                    authorize(db)  # authentication rechecked after writer wait.
                yield db
                db.commit()
            except sqlite3.OperationalError as error:
                db.rollback()
                if 'locked' in str(error).lower() or 'busy' in str(error).lower():
                    raise AdmissionError('safety_admission_busy') from error
                raise
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()
