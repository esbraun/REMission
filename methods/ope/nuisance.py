"""Approved fixture nuisance supplier; separate process from score evaluation."""
from datetime import datetime, timezone
import json
from pathlib import Path
import joblib
import numpy as np
from pydantic import TypeAdapter
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from contracts.artifacts.manifest import digest
from contracts.artifacts.ope import (Decision, Policy, Predictions, QRow, TargetRow,
    Targets, TrainingPlan, TrainingReceipt, TrainingRow, TrainingStamp)

VERSION="DR-EXCEPTION-R1/1.0.0"


def train(inputs: Path, output: Path):
    plan=TrainingPlan.model_validate_json((inputs/"plan.json").read_bytes())
    rows=TypeAdapter(list[TrainingRow]).validate_json((inputs/"training.json").read_bytes())
    stamps=[TrainingStamp.model_validate(r.model_dump(include=set(TrainingStamp.model_fields))) for r in rows]
    now=datetime.now(timezone.utc)
    fields=dict(schema_version="1.0.0",synthetic=True,version=VERSION,plan=plan,
        plan_sha256=digest(inputs/"plan.json"),training_sha256=digest(inputs/"training.json"),
        model_sha256="0"*64,trainer_sha256=digest(Path(__file__)),fit_at=now,rows=stamps)
    TrainingReceipt.model_validate(fields)  # guards execute before any fit
    X=np.array([[r.x,r.action,r.x*r.action] for r in rows],dtype=np.float64)
    y=np.array([r.reward for r in rows],dtype=np.float64)
    model=make_pipeline(StandardScaler(),Ridge(alpha=plan.alpha,solver=plan.solver,fit_intercept=True))
    model.fit(X,y)
    joblib.dump(model,output/"model.joblib")
    fields.update(model_sha256=digest(output/"model.joblib"),fit_at=datetime.now(timezone.utc))
    receipt=TrainingReceipt.model_validate(fields)
    (output/"receipt.json").write_text(receipt.model_dump_json(indent=2)+"\n")


def predict(inputs: Path, output: Path):
    receipt=TrainingReceipt.model_validate_json((inputs/"receipt.json").read_bytes())
    if digest(inputs/"model.joblib")!=receipt.model_sha256:raise ValueError("model hash mismatch")
    roster=TypeAdapter(list[Decision]).validate_json((inputs/"roster.json").read_bytes())
    if {d.patient_id for d in roster}!=set(receipt.plan.evaluation_patients):raise ValueError("patient plan mismatch")
    if any(d.decision_at<receipt.plan.evaluation_start or d.decision_at<=receipt.plan.cutoff for d in roster):
        raise ValueError("forward-time prediction required")
    # Only our hash-verified trusted model is loaded; arbitrary pickle import is unsupported.
    model=joblib.load(inputs/"model.joblib")
    rows=[]
    for d in roster:
        values=model.predict(np.array([[d.x,a,d.x*a] for a in [0,1]],dtype=np.float64))
        rows.append(QRow(row_id=d.row_id,values=values.tolist()))
    artifact=Predictions(schema_version="1.0.0",synthetic=True,version=VERSION,
        action_order="0=no_prompt,1=approved_prompt",roster_sha256=digest(inputs/"roster.json"),
        receipt_sha256=digest(inputs/"receipt.json"),model_sha256=receipt.model_sha256,
        predictor_sha256=digest(Path(__file__)),predicted_at=datetime.now(timezone.utc),rows=rows)
    (output/"q.json").write_text(artifact.model_dump_json(indent=2)+"\n")
    definitions=json.loads((inputs/"policies.json").read_text())
    for definition in definitions:
        encoded=(json.dumps(definition,sort_keys=True,separators=(",",":"))+"\n").encode()
        import hashlib
        policy=Policy(schema_version="1.0.0",synthetic=True,policy_id=definition["id"],version="1.0.0",
            sealed_at=datetime.fromisoformat(definition["sealed_at"]),action_order="0=no_prompt,1=approved_prompt",
            definition_sha256=hashlib.sha256(encoded).hexdigest(),availability_rule="singleton_deterministic_empty_unavailable")
        targets=[]
        for d in roster:
            pi=[0.,0.]
            if len(d.available_actions)==1:pi[d.available_actions[0]]=1.
            elif len(d.available_actions)==2:pi=definition["probabilities"]
            targets.append(TargetRow(row_id=d.row_id,probabilities=pi))
        value=Targets(schema_version="1.0.0",synthetic=True,policy=policy,
            roster_sha256=digest(inputs/"roster.json"),rows=targets)
        (output/(definition["id"]+".json")).write_text(value.model_dump_json(indent=2)+"\n")
