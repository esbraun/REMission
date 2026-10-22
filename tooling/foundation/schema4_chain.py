"""Run ONLY in the pinned complete schema4 SERVICE environment, offline."""
import hashlib
import json
from pathlib import Path
import shutil
from test_live_upgrade import StoppedUpgradeTests,NOW
from services.foundation.upgrade003 import upgrade_checkpoint003
from migration_snapshot import snapshot


def main():
    root=Path('/chain');root.mkdir(exist_ok=True)
    StoppedUpgradeTests.setUpClass()
    case=StoppedUpgradeTests();case.setUp()
    try:
        source_hash=hashlib.sha256(case.source.read_bytes()).hexdigest()
        shutil.copyfile(case.source,root/'source003-backup.sqlite')
        (root/'old-bundle.json').write_bytes(case.previous)
        (root/'new-bundle.json').write_text(case.new.model_dump_json())
        for name in ['normal','before-commit','after-commit']:
            directory=root/name;directory.mkdir()
            target=directory/'upgraded.sqlite'
            store=upgrade_checkpoint003(target,case.source,case.previous,case.new,clock=lambda:NOW)
            with store.transaction() as db:
                before=dict(tables=snapshot(db),control=dict(db.execute('SELECT * FROM service_control').fetchone()),
                    migrations=[r[0] for r in db.execute('SELECT version FROM schema_migrations')],
                    patient_versions=[list(r) for r in db.execute('SELECT id,version,state_version,consent_version,eligibility_version FROM patients ORDER BY id')],
                    task_ids=[r[0] for r in db.execute('SELECT id FROM live_hold_tasks')],
                    review_ids=[r[0] for r in db.execute('SELECT id FROM live_hold_reviews')],
                    foreign_keys=[list(r) for r in db.execute('PRAGMA foreign_key_check')])
            # Explicit stopped backup is evidence/recovery input, not silently
            # admitted at another inode under the original control binding.
            shutil.copyfile(target,directory/'before005-backup.sqlite')
            before['database_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
            (directory/'before005.json').write_text(json.dumps(before,indent=2)+'\n')
        assert hashlib.sha256(case.source.read_bytes()).hexdigest()==source_hash
        (root/'phase4.json').write_text(json.dumps(dict(status='three-actual-003-to004-intermediates',source_sha256=source_hash,
            pinned_service_image='sha256:a92d7bda327ce7eb06a1d8ee03193d4090f148f48034bee63655d3cd8402dbcb',
            source_head='ef71ae01953462e65be5d1bd7d6c6359c84a3139',generation=case.new.control.authority_generation,
            original_task_ids=case.results['entry']['task_ids']),indent=2)+'\n')
        print((root/'phase4.json').read_text())
    finally:
        case.tearDown();StoppedUpgradeTests.tearDownClass()


if __name__=='__main__':main()
