"""Actual service dependency API/storage probe, before source consumption."""
import importlib.metadata as metadata
import json
from pathlib import Path
import sqlite3
import tempfile
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import FastAPI
from fastapi.testclient import TestClient


def main():
    app = FastAPI()

    @app.get("/probe")
    def probe():
        return {"status": "ok"}

    assert TestClient(app).get("/probe").json() == {"status": "ok"}
    hasher = PasswordHasher()
    encoded = hasher.hash("synthetic-runtime-probe")
    assert hasher.verify(encoded, "synthetic-runtime-probe")
    try:
        hasher.verify(encoded, "wrong")
        raise AssertionError("bad password accepted")
    except VerifyMismatchError:
        pass
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "probe.sqlite"
        first = sqlite3.connect(path, isolation_level=None)
        second = sqlite3.connect(path, isolation_level=None)
        for db in [first, second]:
            assert db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA busy_timeout=25")
        first.execute("CREATE TABLE record (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        first.execute("BEGIN IMMEDIATE")
        first.execute("INSERT INTO record VALUES (1, 'rollback')")
        try:
            second.execute("BEGIN IMMEDIATE")
            raise AssertionError("concurrent writer unexpectedly admitted")
        except sqlite3.OperationalError:
            pass
        first.rollback()
        assert second.execute("SELECT count(*) FROM record").fetchone()[0] == 0
        first.close()
        second.close()
    print(json.dumps(dict(status="pass", sqlite_version=sqlite3.sqlite_version,
                          sqlite_source_id=sqlite3.connect(":memory:").execute("select sqlite_source_id()").fetchone()[0],
                          packages={name: metadata.version(name) for name in ["fastapi", "starlette", "uvicorn", "argon2-cffi", "httpx", "pydantic"]},
                          checks=["actual ASGI route", "Argon2 correct/wrong password", "WAL/FULL/foreign_keys", "two-connection writer exclusion", "rollback"]), indent=2))


if __name__ == "__main__":
    main()
