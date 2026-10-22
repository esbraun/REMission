"""Administrative synthetic seed, password-reset and observed replay commands."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
from .app import HASHER
from .replay import replay
from .store import Store, canonical, instant
from .workflow import STAGES, create_decision, state_for

SEED = "foundation-fixture-20261021-v1"
CUTOFF = "2026-10-21T09:00:00+00:00"
DEMO_PASSWORDS = {"alice": "Synthetic-Alice-2026!", "bob": "Synthetic-Bob-2026!"}


def seed(store: Store):
    with store.transaction(write=True) as db:
        if db.execute("SELECT count(*) FROM accounts").fetchone()[0]:
            raise ValueError("seed_requires_empty_database")
        for username,password in DEMO_PASSWORDS.items():
            db.execute("INSERT INTO accounts(id,username,display_name,password_hash) VALUES(?,?,?,?)",(username,username,"Dr "+username.title()+" (synthetic)",HASHER.hash(password)))
        for i,stage in enumerate(STAGES,1):
            identifier=f"SYN-{i:02d}"
            db.execute("INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)",(identifier,"alice",f"Synthetic patient {i:02d}",1,1,1,1,canonical(state_for(stage)),None,CUTOFF))
            from .live_journal import initialize_journal
            initialize_journal(db,identifier,store.clock())
            create_decision(db,identifier,instant(CUTOFF))
        db.execute("INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)",("SYN-B01","bob","Synthetic patient B01",1,1,1,1,canonical(state_for("ASSIGN-02")),None,CUTOFF))
        initialize_journal(db,'SYN-B01',store.clock())
        create_decision(db,"SYN-B01",instant(CUTOFF))
    return {"status":"seeded","seed":SEED,"cutoff":CUTOFF,"patients":11,"doctors":2}


def reset_password(store: Store, username: str, password: str):
    encoded=HASHER.hash(password)
    with store.transaction(write=True) as db:
        account=db.execute("SELECT id FROM accounts WHERE username=?",(username,)).fetchone()
        if not account:raise ValueError("account_not_found")
        db.execute("UPDATE accounts SET password_hash=?,auth_version=auth_version+1 WHERE id=?",(encoded,account[0]))
        db.execute("UPDATE sessions SET revoked=1 WHERE account_id=?",(account[0],))


def main():
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=["activate-new","upgrade-003","upgrade-004","change-authority","seed","reset-password","replay","replay-export"])
    parser.add_argument("--database",type=Path,required=True);parser.add_argument("--username");parser.add_argument("--password")
    parser.add_argument("--manifest",type=Path);parser.add_argument("--run-id");parser.add_argument("--cutoff")
    parser.add_argument("--artifact-root",type=Path);parser.add_argument("--authority",type=Path)
    parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--next-bundle',type=Path)
    parser.add_argument('--historical-source',type=Path)
    parser.add_argument('--archive-config',type=Path)
    args=parser.parse_args()
    from contracts.service.live_hold import InstalledBundle
    if args.command=='upgrade-003':
        parser.error('Schema003 requires the preserved schema4 SERVICE release sha256:a92d7bda327ce7eb06a1d8ee03193d4090f148f48034bee63655d3cd8402dbcb (accepted source a7ab7e60). Run its upgrade-003 command on a NEW private path with old --bundle and new --next-bundle after stopping all workers. Then run this release upgrade-004 on that target with the new --bundle before routing. See docs/implementation/poc-analysis-runbook.md. No database was opened or changed.')
    installed=InstalledBundle.model_validate_json(args.bundle.read_bytes())
    if args.command=='upgrade-004':
        from .upgrade004 import upgrade004
        upgraded=upgrade004(args.database,installed)
        print(json.dumps(dict(status='upgraded_004_to_005_unrouted',control=upgraded.installed.control.model_dump(mode='json'))));return
    if args.command=='activate-new':
        from .cutover import activate_new
        store=activate_new(args.database,installed,datetime.now(timezone.utc),source=args.historical_source)
        print(json.dumps(dict(status='activated_unrouted',control=store.installed.control.model_dump(mode='json'))));return
    store=Store(args.database,installed)
    if args.command=='change-authority':
        if args.next_bundle is None:parser.error('next-bundle required after draining all workers')
        from .cutover import change_generation
        from .app import Settings
        from .configuration import read_archives
        settings=Settings(args.database,installed,observed_archives=read_archives(args.archive_config))
        changed=change_generation(store,InstalledBundle.model_validate_json(args.next_bundle.read_bytes()),settings=settings)
        print(json.dumps(dict(status='generation_changed_unrouted',control=changed.installed.control.model_dump(mode='json'))))
    elif args.command=="seed":print(json.dumps(seed(store)))
    elif args.command=="reset-password":
        if not args.username or not args.password:parser.error("username/password required")
        reset_password(store,args.username,args.password);print(json.dumps({"status":"password_reset_sessions_revoked"}))
    elif args.command=="replay-export":
        if not args.manifest or not args.artifact_root or not args.authority:parser.error('manifest/artifact-root/trusted authority required')
        from contracts.runs.common import ExportAuthority
        from .replay import replay_export
        authority=ExportAuthority.model_validate_json(args.authority.read_bytes())
        print(json.dumps(replay_export(store,args.manifest.read_bytes(),args.artifact_root,authority)))
    else:
        if not args.manifest or not args.run_id or not args.cutoff:parser.error("manifest/run-id/cutoff required")
        print(json.dumps(replay(store,args.run_id,json.loads(args.manifest.read_text(encoding="utf-8")),args.cutoff)))


if __name__=="__main__":main()
