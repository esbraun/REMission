"""Read-only repaired qualification checks; --record deliberately saves evidence."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
BASE="b24c3c0fb78bf19928750eae29e852141bd649a7"
ORIGINAL="d9ad54e899b2f38b286bd100aff037625edf160b"
IMAGE="sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7"


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--record",action="store_true");args=parser.parse_args()
    commands=[[sys.executable,"-m","pip","check"],
        [sys.executable,"-m","contracts.domain.export","--check"],
        [sys.executable,"-m","unittest","discover","-s","tests/contracts","-v"],
        [sys.executable,"-m","unittest","discover","-s","tests/library","-v"],
        [sys.executable,"docs/implementation/check-ledger-20261020.py"],
        ["docker","run","--rm","--mount",f"type=bind,source={ROOT.as_posix()},target=/workspace,readonly",IMAGE,
         "python","-c","import subprocess;subprocess.check_call(['python','-m','pip','check']);subprocess.check_call(['python','-m','tooling.library.check-runtime'])"],
        ["git","diff","--quiet",ORIGINAL,"--","docs/implementation/evidence/G0-LIB",":!docs/implementation/evidence/G0-LIB/R1/**"],
        ["git","diff","--quiet",BASE,"--","contracts/domain","docs/spec/01-estimands-and-contracts.md","docs/spec/dgp-reference.md"],
        ["git","diff","--check",BASE]]
    results=[]
    for command in commands:
        started=datetime.now(timezone.utc).isoformat()
        result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        results.append({"command":command,"started_utc":started,"finished_utc":datetime.now(timezone.utc).isoformat(),
                        "exit_code":result.returncode,"stdout":result.stdout,"stderr":result.stderr})
        print("PASS" if result.returncode==0 else "FAIL"," ".join(command[1:]))
    if args.record:
        paths=subprocess.check_output(["git","diff","--name-only",BASE],cwd=ROOT,text=True).splitlines()
        sources={p:hashlib.sha256((ROOT/p).read_bytes().replace(b"\r\n",b"\n")).hexdigest()
                 for p in paths if (ROOT/p).is_file() and not p.endswith("check-results.json") and "/exchange/" not in p and not p.endswith((".log",".gz",".nc",".png"))}
        Path(__file__).with_name("check-results.json").write_text(json.dumps({"package":"G0-LIB-R1","base":BASE,
            "candidate":"Exact SHA in independent review/handoff, avoiding self-reference",
            "created_utc":datetime.now(timezone.utc).isoformat(),"python":platform.python_version(),"platform":platform.platform(),
            "packages":subprocess.check_output([sys.executable,"-m","pip","freeze"],cwd=ROOT,text=True).splitlines(),
            "source_sha256_LF_normalized":sources,"checks":results,
            "limits":["No DR implementation/qualification; proposal unaccepted","No expensive fit rerun, pilot or final statistical/human/G0 acceptance",
                      "Source hashes normalize LF; manifest payload/input hashes cover exact bytes"]},indent=2)+"\n",encoding="utf-8")
    if any(r["exit_code"] for r in results):raise SystemExit(1)


if __name__=="__main__":main()
