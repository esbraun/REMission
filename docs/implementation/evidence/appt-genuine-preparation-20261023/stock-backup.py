import sqlite3,pathlib,hashlib,json
source=sqlite3.connect('file:/data/remission.sqlite?mode=ro',uri=True);source.execute('PRAGMA query_only=ON')
destination=pathlib.Path('/backup/remission-pre-appt.sqlite');assert not destination.exists()
target=sqlite3.connect(destination);source.backup(target);target.close()
assert source.total_changes==0 and source.execute('PRAGMA query_only').fetchone()[0]==1
source.close()
backup=sqlite3.connect('file:'+str(destination)+'?mode=ro',uri=True);backup.execute('PRAGMA query_only=ON')
assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
tables={}
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
backup.row_factory=sqlite3.Row
for row in backup.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
 name=row[0];records=[]
 for record in backup.execute('SELECT * FROM "'+name.replace('"','""')+'"'):
  records.append(sha({k:({'blob_bytes':len(record[k]),'blob_sha256':hashlib.sha256(record[k]).hexdigest()} if isinstance(record[k],bytes) else record[k]) for k in record.keys()}))
 tables[name]={'rows':len(records),'rows_sha256':sha(sorted(records))}
backup.close();print(canonical({'method':'SQLite Online Backup API from mode=ro/query_only source; committed WAL included','integrity_check':'ok','bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'tables':tables}))
