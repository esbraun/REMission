"""Ordinary two-action IPS/DR; no fitting, policy learning or action sampling."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from pydantic import TypeAdapter

from contracts.artifacts.manifest import checked_file
from contracts.artifacts.ope import (Decision, OPEOutput, OPERequest, Predictions,
    Reward, Targets, TrainingReceipt, EvaluationProtocol)
from contracts.domain.boundaries import ContractViolation

VERSION="DR-EXCEPTION-R1/1.0.0"
TOL=1e-12


def deny(code, message):
    raise ContractViolation(code,message)


def validate_rows(decisions, rewards, targets, q):
    """Validate the complete batch before any score arithmetic."""
    ids=[r.row_id for r in decisions]
    if len(set(ids))!=len(ids) or len({(r.patient_id,r.window_id) for r in decisions})!=len(ids):
        deny("row_identity","Unique row/patient-outcome-window identities required")
    if len({(r.patient_id,r.decision_at.date()) for r in decisions})!=len(ids):
        deny("daily_window","At most one prespecified next-morning contribution per patient local day")
    if ([r.row_id for r in rewards]!=ids or [r.row_id for r in q]!=ids
            or any([r.row_id for r in t.rows]!=ids for t in targets)):
        deny("row_order","Roster/reward/Q/target row order must match exactly")
    for i,row in enumerate(decisions):
        eligible=row.available_actions;p=row.logging_probabilities
        if len(set(eligible))!=len(eligible) or eligible!=sorted(eligible):
            deny("availability","Action identities must be canonical unique 0/1 order")
        if any(not math.isfinite(x) or x<0 or x>1 for x in p):deny("propensity","Invalid logging probability")
        if any(p[a]!=0 for a in [0,1] if a not in eligible):deny("support","Logging mass on unavailable action")
        if eligible:
            if not math.isclose(math.fsum(p),1,abs_tol=TOL,rel_tol=0) or row.action not in eligible or p[row.action]<=0:
                deny("propensity","Executed action needs actual positive normalized logging probability")
            if len(eligible)==1 and p[eligible[0]]!=1:deny("support","Singleton must be deterministic")
        elif row.action is not None or p!=[0,0]:deny("availability","Unavailable window cannot contain assignment")
        if any(not math.isfinite(x) for x in q[i].values):deny("Q","Finite Q required")
        for target in targets:
            pi=target.rows[i].probabilities
            if any(not math.isfinite(x) or x<0 or x>1 for x in pi):deny("target","Invalid target probability")
            if eligible:
                if not math.isclose(math.fsum(pi),1,abs_tol=TOL,rel_tol=0):deny("target","Target not normalized")
                if any(pi[a]>0 and (a not in eligible or p[a]<=0) for a in [0,1]):
                    deny("support","Every positive target action must have authoritative logging support")
                if len(eligible)==1 and pi[eligible[0]]!=1:deny("target","Singleton target must be deterministic")
            elif pi!=[0,0]:deny("target","Unavailable window has no target distribution")


def score_rows(decisions, rewards, targets, q):
    """The sole DR implementation. Returns eligible row indices and float64 scores."""
    validate_rows(decisions,rewards,targets,q)
    indices=[i for i,d in enumerate(decisions) if d.available_actions]
    if any(rewards[i].status!="observed" or rewards[i].value is None for i in indices):
        deny("missing_reward","Do not delete or impute eligible rewards")
    values=np.empty((len(indices),len(targets)),dtype=np.float64)
    ips=np.empty_like(values)
    for k,i in enumerate(indices):
        d=decisions[i];a=d.action;r=rewards[i].value;p=d.logging_probabilities[a]
        for j,target in enumerate(targets):
            pi=target.rows[i].probabilities;Q=q[i].values
            values[k,j]=pi[0]*Q[0]+pi[1]*Q[1]+pi[a]/p*(r-Q[a])
            ips[k,j]=pi[a]/p*r
    if not np.isfinite(values).all() or not np.isfinite(ips).all():deny("numerics","Nonfinite score/overflow")
    return indices,values,ips


def patient_bootstrap(patients, scores, seed):
    """Conditional fixed-Q paired ratio bootstrap of whole-patient sums/counts."""
    if (scores.ndim!=2 or len(patients)!=len(scores) or scores.shape[1]<1
            or not np.isfinite(scores).all()):deny("bootstrap_shape","Finite aligned policy scores required")
    order=sorted(set(patients))
    if len(order)<30:deny("independent_units","At least30 independent evaluation patients required")
    sums=np.array([scores[np.array(patients)==p].sum(axis=0) for p in order],dtype=np.float64)
    counts=np.array([patients.count(p) for p in order],dtype=np.int64)
    rng=np.random.Generator(np.random.PCG64DXSM(seed))
    sampled=rng.integers(0,len(order),size=(2000,len(order)),dtype=np.int64)
    draws=sums[sampled].sum(axis=1)/counts[sampled].sum(axis=1)[:,None]
    intervals=np.quantile(draws,[.025,.975],axis=0,method="linear").T
    paired=np.quantile(draws[:,1:]-draws[:,[0]],[.025,.975],axis=0,method="linear").T if scores.shape[1]>1 else np.empty((0,2))
    return order,draws,intervals,paired,hashlib.sha256(sampled.astype("<i8").tobytes()).hexdigest()


def evaluate_files(root: Path, request: OPERequest):
    """Trusted caller pins request/bindings; validate files/provenance before score work."""
    request=OPERequest.model_validate(request)
    refs=[request.protocol,request.roster,request.rewards,request.predictions,*request.targets]
    if request.receipt is not None:refs.append(request.receipt)
    files={r.path:checked_file(root,r) for r in refs}
    def load(ref,adapter):return adapter.validate_json(files[ref.path].read_bytes())
    decisions=load(request.roster,TypeAdapter(list[Decision]))
    rewards=load(request.rewards,TypeAdapter(list[Reward]))
    q=load(request.predictions,TypeAdapter(Predictions))
    targets=[load(r,TypeAdapter(Targets)) for r in request.targets]
    protocol=load(request.protocol,TypeAdapter(EvaluationProtocol))
    validate_rows(decisions,rewards,targets,q.rows)
    bindings=request.bindings
    if (request.predictions.sha256!=bindings.q_sha256 or [r.sha256 for r in request.targets]!=bindings.target_sha256
            or [t.policy.definition_sha256 for t in targets]!=bindings.policy_sha256):
        deny("sealed_artifact","Target/Q/definition hashes must match trusted sealed bindings")
    if q.roster_sha256!=request.roster.sha256 or any(t.roster_sha256!=request.roster.sha256 for t in targets):
        deny("roster_binding","Q and policies must retain the exact feature/availability/propensity roster")
    if len({t.policy.policy_id for t in targets})!=len(targets):deny("policy_identity","Distinct fixed policy identities required")
    if protocol.target_policy_ids!=[t.policy.policy_id for t in targets]:deny("protocol_targets","Predeclared target/order mismatch")
    eligible=[i for i,d in enumerate(decisions) if d.available_actions]
    people=sorted({decisions[i].patient_id for i in eligible})
    def output(status,reason,**kwargs):
        raw=dict(schema_version="1.0.0",synthetic=True,version=VERSION,status=status,reason=reason,unit="quality_points",
            eligible_windows=len(eligible),unavailable_windows=len(decisions)-len(eligible),independent_patients=len(people),
            policies=[t.policy.policy_id for t in targets],dr=[],ips=[],intervals=[],paired_intervals=[],bootstrap_values=[],
            patient_order=[],patient_counts=[],patient_score_sums=[],bootstrap_indices_sha256=None,metadata={"estimand":request.estimand,"aggregation":request.aggregation,
                "Q_sha256":request.predictions.sha256,"receipt_sha256":bindings.receipt_sha256,
                "training_sha256":bindings.training_sha256,"model_sha256":bindings.model_sha256,
                "plan_sha256":bindings.plan_sha256,"trainer_sha256":bindings.trainer_sha256,
                "predictor_sha256":bindings.predictor_sha256,"roster_sha256":request.roster.sha256,
                "protocol_sha256":request.protocol.sha256,"population_id":protocol.population_id,
                "behavior_id":protocol.behavior.id,"behavior_version":protocol.behavior.version,
                "reward_horizon":protocol.reward_horizon,"outcome_window_rule":protocol.outcome_window_rule,
                "reward_sha256":request.rewards.sha256,"target_sha256":json.dumps(bindings.target_sha256),
                "seed":request.bootstrap_seed,"precision":"float64","fixed_nuisance":True,
                "logging_regime":request.logging_regime,
                "bootstrap_replicates":2000 if request.inference else 0,"attempted_windows":len(decisions),
                "learning_algorithm_inference":False})
        raw.update(kwargs)
        return OPEOutput.model_validate(raw)
    if not eligible:return output("undefined","no_eligible_windows")
    if request.receipt is None:return output("abstained","no_valid_earlier_training")
    if request.receipt.sha256!=bindings.receipt_sha256:deny("sealed_receipt","Trusted receipt hash mismatch")
    receipt=load(request.receipt,TypeAdapter(TrainingReceipt))
    if receipt.plan.protocol_sha256!=request.protocol.sha256 or protocol.sealed_at>receipt.plan.cutoff:
        deny("protocol_binding","Protocol must be sealed with training plan before evaluation")
    if (receipt.training_sha256,receipt.plan_sha256,receipt.model_sha256,receipt.trainer_sha256)!=(bindings.training_sha256,bindings.plan_sha256,bindings.model_sha256,bindings.trainer_sha256):
        deny("training_binding","Training/source/model/plan hash mismatch")
    if q.receipt_sha256!=request.receipt.sha256 or q.model_sha256!=bindings.model_sha256 or q.predictor_sha256!=bindings.predictor_sha256:
        deny("prediction_binding","Q must come from the sealed earlier model and prediction source")
    patients={d.patient_id for d in decisions}
    if patients!=set(receipt.plan.evaluation_patients):deny("patient_roster","Evaluation patient set differs from sealed training plan")
    if any(d.decision_at<receipt.plan.evaluation_start or d.decision_at<=receipt.plan.cutoff for d in decisions):
        deny("forward_time","All evaluation assignments must follow sealed training cutoff/start")
    if q.predicted_at<receipt.fit_at or any(t.policy.sealed_at>receipt.plan.cutoff for t in targets):
        deny("seal_time","Prediction follows fit and fixed targets must be sealed before evaluation")
    if any(rewards[i].status!="observed" for i in eligible):return output("abstained","eligible_reward_missing_pending_or_undefined")
    if request.inference and request.logging_regime!="fixed_independent_patients":
        deny("pooled_dependence","One pooled adaptive cohort is not independent-patient inference")
    if request.inference and len(people)<30:return output("abstained","fewer_than_30_independent_evaluation_patients")
    indices,values,ips=score_rows(decisions,rewards,targets,q.rows)
    kwargs=dict(dr=values.mean(axis=0).tolist(),ips=ips.mean(axis=0).tolist())
    patients=[decisions[i].patient_id for i in indices]
    kwargs.update(patient_order=people,patient_counts=[patients.count(p) for p in people],
        patient_score_sums=[values[np.array(patients)==p].sum(axis=0).tolist() for p in people])
    if request.inference:
        order,draws,intervals,paired,checksum=patient_bootstrap([decisions[i].patient_id for i in indices],values,request.bootstrap_seed)
        kwargs.update(patient_order=order,bootstrap_values=draws.tolist(),intervals=intervals.tolist(),paired_intervals=paired.tolist(),bootstrap_indices_sha256=checksum)
    return output("computed_conditional" if request.inference else "diagnostic_only",None,**kwargs)
