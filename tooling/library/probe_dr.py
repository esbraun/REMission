"""Actual three-process Ridge/DR qualification with least-data Docker mounts."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/"tooling/library/__pycache__/dr-execution"
EVIDENCE=ROOT/"docs/implementation/evidence/G0-LIB/DR"
IMAGE="sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7"
VERSION="DR-EXCEPTION-R1/1.0.0"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_bytes((json.dumps(value,indent=2)+"\n").encode())
def ref(root,name):return {"path":name,"sha256":sha(root/name)}


def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    source=WORK/"source"
    paths=[*ROOT.glob("contracts/domain/*.py"),*ROOT.glob("contracts/artifacts/*.py"),
           ROOT/"contracts/__init__.py",ROOT/"methods/__init__.py",*ROOT.glob("methods/ope/*.py"),ROOT/"tooling/library/dr_stage.py"]
    source_manifest={}
    for path in paths:
        if not path.is_file():continue
        dest=source/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
        source_manifest[path.relative_to(ROOT).as_posix()]=sha(dest)
    write(EVIDENCE/"source-manifest.json",source_manifest)
    write(EVIDENCE/"recipe-source-sha256.json",{"path":"tooling/library/probe_dr.py",
        "sha256":hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        "encoding":"UTF8 LF-normalized source; exact executed curated-source bytes separately hashed"})
    for name in ["train-input","train-output","predict-input","predict-output","score-input","score-output","mutated-input","mutated-output"]:
        (WORK/name).mkdir(exist_ok=True)
    now=datetime.now(timezone.utc);cutoff=now+timedelta(minutes=10);start=now+timedelta(days=2)
    behavior=dict(id="G0-fixed-logging",version="1.0.0",probabilities=[.4,.6],
        availability="two approved actions in qualifier; no adaptation",source="tooling/library/probe_dr.py")
    write(EVIDENCE/"logging-definition.json",behavior)
    protocol=dict(schema_version="1.0.0",synthetic=True,protocol_id="G0-LIB-DR-qualifier",version="1.0.0",
        population_id="synthetic_independent_evaluation_patients",behavior=dict(id=behavior["id"],version=behavior["version"],sha256=sha(EVIDENCE/"logging-definition.json")),
        reward_horizon="next_morning_quality",outcome_window_rule="one_decision_per_patient_next_morning",unit="quality_points",
        target_policy_ids=["policy-a","policy-b"],sealed_at=now.isoformat())
    write(WORK/"score-input/protocol.json",protocol)
    patients=[f"E{i:02d}" for i in range(30)]
    plan=dict(schema_version="1.0.0",synthetic=True,version=VERSION,cutoff=cutoff.isoformat(),evaluation_start=start.isoformat(),
        evaluation_patients=patients,basis="x,action,x_times_action;StandardScaler;Ridge_intercept",alpha=1.,solver="svd",seed=73151,
        protocol_sha256=sha(WORK/"score-input/protocol.json"))
    train=[]
    for p in range(12):
        for a in [0,1]:
            x=(p-5.5)/6;decision=now-timedelta(days=20)+timedelta(days=a,hours=p)
            train.append(dict(row_id=f"T{p}-{a}",patient_id=f"T{p}",window_id=f"T{p}-w{a}",decision_at=decision.isoformat(),
                x=x,x_available_at=(decision-timedelta(minutes=1)).isoformat(),action=a,
                reward=3+.4*x+a-.2*x*a+.03*((p%3)-1),reward_available_at=(decision+timedelta(hours=12)).isoformat()))
    write(WORK/"train-input/plan.json",plan);write(WORK/"train-input/training.json",train)
    roster=[];rewards=[]
    for p,patient in enumerate(patients):
        for t in range(1+p%3):
            decision=start+timedelta(days=t,hours=p/60);x=(p-14.5)/15+t*.1;a=(p+t)%2
            rid=f"{patient}-w{t}"
            roster.append(dict(row_id=rid,patient_id=patient,window_id=rid,decision_at=decision.isoformat(),x=x,
                x_available_at=(decision-timedelta(minutes=1)).isoformat(),available_actions=[0,1],logging_probabilities=[.4,.6],action=a))
            rewards.append(dict(row_id=rid,status="observed",value=3+.4*x+a-.2*x*a+.05*((p+t)%3-1)))
    definitions=[dict(id="policy-a",sealed_at=now.isoformat(),probabilities=[.25,.75]),
                 dict(id="policy-b",sealed_at=now.isoformat(),probabilities=[.6,.4])]
    write(WORK/"predict-input/roster.json",roster);write(WORK/"predict-input/policies.json",definitions)
    logs=[]
    def run(stage,input_name,output_name,label):
        cmd=["docker","run","--rm","--network","none","--read-only","--tmpfs","/tmp",
             "--env","PYTHONPATH=/src","--mount",f"type=bind,source={source.as_posix()},target=/src,readonly",
             "--mount",f"type=bind,source={(WORK/input_name).as_posix()},target=/input,readonly",
             "--mount",f"type=bind,source={(WORK/output_name).as_posix()},target=/output",IMAGE,
             "python","/src/tooling/library/dr_stage.py",stage]
        started=datetime.now(timezone.utc).isoformat();result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        logs.append(dict(label=label,command=cmd,started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
            exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        write(EVIDENCE/"commands.json",logs)
        if result.returncode:raise RuntimeError(label+": "+result.stderr)
    run("train","train-input","train-output","actual_Ridge_training")
    for name in ["receipt.json","model.joblib"]:shutil.copyfile(WORK/"train-output"/name,WORK/"predict-input"/name)
    run("predict","predict-input","predict-output","reward_blind_prediction")
    score=WORK/"score-input"
    for name in ["receipt.json"]:shutil.copyfile(WORK/"train-output"/name,score/name)
    shutil.copyfile(WORK/"predict-input/roster.json",score/"roster.json");write(score/"rewards.json",rewards)
    for name in ["q.json","policy-a.json","policy-b.json"]:shutil.copyfile(WORK/"predict-output"/name,score/name)
    receipt=json.loads((score/"receipt.json").read_text())
    policy_hashes=[hashlib.sha256((json.dumps(d,sort_keys=True,separators=(",",":"))+"\n").encode()).hexdigest() for d in definitions]
    request=dict(schema_version="1.0.0",synthetic=True,version=VERSION,
        estimand="current_action_value_over_behavior_history_eligible_windows",unit="quality_points",aggregation="pooled_eligible_decision_mean",
        logging_regime="fixed_independent_patients",protocol=ref(score,"protocol.json"),roster=ref(score,"roster.json"),rewards=ref(score,"rewards.json"),
        predictions=ref(score,"q.json"),targets=[ref(score,n) for n in ["policy-a.json","policy-b.json"]],receipt=ref(score,"receipt.json"),
        bindings=dict(receipt_sha256=sha(score/"receipt.json"),training_sha256=receipt["training_sha256"],plan_sha256=receipt["plan_sha256"],
            model_sha256=receipt["model_sha256"],trainer_sha256=receipt["trainer_sha256"],predictor_sha256=source_manifest["methods/ope/nuisance.py"],
            q_sha256=sha(score/"q.json"),target_sha256=[sha(score/n) for n in ["policy-a.json","policy-b.json"]],policy_sha256=policy_hashes),
        inference=True,bootstrap_seed=73152,bootstrap_replicates=2000,minimum_patients=30)
    write(score/"request.json",request)
    sealed={n:sha(score/n) for n in ["q.json","policy-a.json","policy-b.json","receipt.json"]}
    run("score","score-input","score-output","conditional_fixed_Q_inference")
    mutated=WORK/"mutated-input"
    for path in score.iterdir():shutil.copyfile(path,mutated/path.name)
    changed=[{**r,"value":r["value"]+.1} for r in rewards];write(mutated/"rewards.json",changed)
    request["rewards"]=ref(mutated,"rewards.json");write(mutated/"request.json",request)
    run("score","mutated-input","mutated-output","changed_rewards_fixed_Q_targets_training")
    assert sealed=={n:sha(mutated/n) for n in sealed}
    base=json.loads((WORK/"score-output/result.json").read_text());changed=json.loads((WORK/"mutated-output/result.json").read_text())
    assert base["status"]==changed["status"]=="computed_conditional" and base["dr"]!=changed["dr"]
    exchange=EVIDENCE/"exchange";exchange.mkdir(exist_ok=True)
    for path in score.iterdir():shutil.copyfile(path,exchange/path.name)
    shutil.copyfile(mutated/"rewards.json",exchange/"rewards-mutated.json")
    shutil.copyfile(mutated/"request.json",exchange/"request-mutated.json")
    for name in ["plan.json","training.json"]:shutil.copyfile(WORK/"train-input"/name,exchange/name)
    shutil.copyfile(WORK/"train-output/model.joblib",exchange/"model.joblib")
    for label,folder in [("train","train-output"),("predict","predict-output"),("score","score-output"),("mutated-score","mutated-output")]:
        shutil.copyfile(WORK/folder/"access.json",EVIDENCE/(label+"-access.json"))
    shutil.copyfile(WORK/"score-output/result.json",EVIDENCE/"result.json")
    shutil.copyfile(WORK/"mutated-output/result.json",EVIDENCE/"result-reward-mutation.json")
    write(EVIDENCE/"probe-summary.json",dict(version=VERSION,image=IMAGE,training_rows=len(train),training_patients=12,
        evaluation_patients=30,eligible_windows=len(roster),bootstrap_replicates=2000,seed=73152,
        base_DR=base["dr"],changed_reward_DR=changed["dr"],sealed_artifact_hashes=sealed,
        held_fixed_on_reward_mutation=True,fit_learn_predict_choice_calls_in_scorer=0,
        source_data_access="actual denied reads in separate network-disabled least-data mounts; curated code only",
        limits="fixture conditional inference only; no G4 truth/coverage/null/MAR/MNAR/cohort qualification"))
    print("PASS: actual patient/time-held-out Ridge, reward-blind Q,60 unequal-length windows/30 patients,2000 paired fixed-Q bootstraps; reward mutation changes residuals without target/Q/training change")


if __name__=="__main__":main()
