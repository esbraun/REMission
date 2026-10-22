"""Administrative synthetic seed, password-reset and observed replay commands."""
import argparse
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
            create_decision(db,identifier,instant(CUTOFF))
        db.execute("INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)",("SYN-B01","bob","Synthetic patient B01",1,1,1,1,canonical(state_for("ASSIGN-02")),None,CUTOFF))
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
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=["seed","reset-password","replay","replay-export"])
    parser.add_argument("--database",type=Path,required=True);parser.add_argument("--username");parser.add_argument("--password")
    parser.add_argument("--manifest",type=Path);parser.add_argument("--run-id");parser.add_argument("--cutoff")
    parser.add_argument("--artifact-root",type=Path);parser.add_argument("--authority",type=Path)
    args=parser.parse_args();store=Store(args.database)
    if args.command=="seed":print(json.dumps(seed(store)))
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
