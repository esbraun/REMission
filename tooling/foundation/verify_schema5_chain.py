"""Actual005 process-death/rollback/reopen checks against own physical004 paths."""
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from contracts.service.live_hold import InstalledBundle
from services.foundation.admission import AdmissionError
from services.foundation.store import Store
from services.foundation.upgrade004 import upgrade004
from migration_snapshot import snapshot


def main():
    root=Path('/chain');bundle=InstalledBundle.model_validate_json((root/'new-bundle.json').read_bytes())
    results=[]
    for name in ['normal','before-commit','after-commit']:
        path=root/name/'upgraded.sqlite'
        before=json.loads((path.parent/'before005.json').read_bytes())
        try:
            Store(path,bundle)
        except AdmissionError:
            pass
        else:
            raise AssertionError('normal startup admitted schema4')
        if name=='normal':
            upgraded=upgrade004(path,bundle)
        else:
            code="from pathlib import Path;import os;from contracts.service.live_hold import InstalledBundle;from services.foundation.upgrade004 import upgrade004;b=InstalledBundle.model_validate_json(Path('/chain/new-bundle.json').read_bytes());upgrade004(Path("+repr(str(path))+"),b,fault=lambda name:os._exit(83) if name=="+repr('before_005_upgrade_commit' if name=='before-commit' else 'after_005_upgrade_commit')+" else None)"
            process=subprocess.run([sys.executable,'-c',code],capture_output=True)
            assert process.returncode==83,(process.returncode,process.stdout,process.stderr)
            if name=='before-commit':
                with closing(sqlite3.connect(path)) as db:
                    assert {r[0] for r in db.execute('SELECT version FROM schema_migrations')}=={1,2,3,4}
                    assert db.execute("SELECT 1 FROM sqlite_master WHERE name='analysis_attempts'").fetchone() is None
                # A committed backup is retained; the actual rolled-back inode
                # can be upgraded directly without restoring/rebinding identity.
                upgraded=upgrade004(path,bundle)
            else:
                upgraded=Store(path,bundle)
        with upgraded.transaction() as db:
            after=snapshot(db)
            for table,identity in before['tables'].items():
                if table!='schema_migrations':
                    assert after[table]==identity,(name,table,after[table],identity)
            assert {r[0] for r in db.execute('SELECT version FROM schema_migrations')}=={1,2,3,4,5}
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
            assert dict(db.execute('SELECT * FROM service_control').fetchone())==before['control']
            assert [list(r) for r in db.execute('SELECT id,version,state_version,consent_version,eligibility_version FROM patients ORDER BY id')]==before['patient_versions']
        result=dict(case=name,status='passed',physical_identity_preserved=True,existing_table_bytes_preserved=True,
            authority_generation=bundle.control.authority_generation,after_tables=after)
        (path.parent/'after005.json').write_text(json.dumps(result,indent=2)+'\n')
        results.append({k:v for k,v in result.items() if k!='after_tables'})
    # Current historical CLI refuses BEFORE reading even a nonexistent bundle
    # or opening/creating a target path.
    refused=root/'must-not-exist.sqlite'
    process=subprocess.run([sys.executable,'-m','services.foundation.cli','upgrade-003','--database',str(refused),'--bundle','/does-not-exist.json'],capture_output=True)
    assert process.returncode!=0 and not refused.exists() and b'a92d7bda' in process.stderr
    summary=dict(status='passed',cases=results,old_cli_refuses_before_mutation=True,source004_generation_effects_not_replayed=True)
    (root/'phase5.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))


if __name__=='__main__':main()
