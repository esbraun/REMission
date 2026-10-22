"""Byte-sensitive SQLite table snapshot for explicit offline migration proofs."""
import hashlib
import json


def snapshot(db):
    result={}
    for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        table=row[0]
        rows=[[{'bytes':bytes(v).hex()} if isinstance(v,bytes) else v for v in r] for r in db.execute('SELECT * FROM "'+table.replace('"','""')+'" ORDER BY rowid')]
        raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
        result[table]=dict(rows=len(rows),sha256=hashlib.sha256(raw).hexdigest())
    return result
