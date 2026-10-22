"""Bounded file-only learner. No service, database, generator or network access."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import resource
import os
import time
import traceback

import numpy as np
import xarray as xr
import pymc as pm
from contracts.domain.analysis import AnalysisInput, AnalysisResult, CONFIG_REF, ESTIMAND_REF, canonical, sha
from methods.visit.model import build, inputs, sample, diagnostics
from methods.visit.numerics import integrate, predictive


def publish(path,value):
    temporary = path.with_suffix(".partial")
    temporary.write_text(canonical(value)+"\n",encoding="utf-8")
    temporary.replace(path)


def run(source, out):
    started = time.monotonic()
    out.mkdir(parents=True,exist_ok=True)
    raw = source.read_bytes()
    product = AnalysisInput.model_validate_json(raw)
    input_hash = sha(product.model_dump(mode="json"))
    seed = int(hashlib.sha256(canonical(product.request.context.seed.model_dump()).encode()).hexdigest()[:8],16)
    result = dict(schema_version="1.0.0",synthetic=True,kind="poc_visit_result",attempt_id=product.attempt_id,
        input_sha256=input_hash,history_sha256=product.history_sha256,cutoff=product.history.cutoff.isoformat(),
        configuration=CONFIG_REF,estimand=ESTIMAND_REF,status="failed",reason="worker-incomplete",effect=None,
        diagnostics={},artifacts=[],limitations=["Fictional synthetic model; no clinical validation or calibrated superiority claim.",
            "One-patient compatible projection; no cross-patient or external borrowing.",
            "Physician-selected treatment; exploratory conditional model predictions require exchangeability and model assumptions.",
            "Quality/ISI reduced H* only; function and diary excluded. MCAR observation assumption.",
            "Population and individual treatment effects can remain prior-driven with limited local arm support."])
    def stage(value):
        publish(out/"progress.json",dict(attempt_id=product.attempt_id,input_sha256=input_hash,**value))
    try:
        stage(dict(stage="fitting"))
        data = inputs(product.history)
        result["diagnostics"]["data"] = dict(day=data["day"],quality=len(data["quality"]),isi=len(data["isi"]),
            deliveries=data["deliveries"],taken=data["taken"],local_arm_support=data["arms"],
            consumed_ids=data["record_ids"],likelihood_blocks=data["likelihood_blocks"],likelihood="one total ISI per14-night recall plus available quality")
        if len(data["arms"])<2:
            result["limitations"].append("Only one or zero local treatment arms observed; the other arm relies on the declared prior.")
        model = build(data)
        with model:
            prior=pm.sample_prior_predictive(draws=64,random_seed=seed+313, var_names=['burden','sigma_isi','sigma_quality'])
        def observed_predictive(group,seed_suffix):
            rng=np.random.default_rng(np.random.SeedSequence([seed,seed_suffix]))
            burden=np.asarray(group['burden'].values)
            isi_mu=burden[...,data['recall']].mean(axis=-1)
            isi=np.clip(np.floor(isi_mu+rng.normal(size=isi_mu.shape)*group['sigma_isi'].values[...,None]+.5),0,28)
            quality_mu=10-burden[...,data['qindex']]/3
            quality=np.round(np.clip(quality_mu+rng.normal(size=quality_mu.shape)*group['sigma_quality'].values[...,None],0,10),3)
            return isi,quality
        prior_isi,prior_quality=observed_predictive(prior['prior'],314)
        np.savez_compressed(out/'prior-predictive.npz',isi=prior_isi,quality=prior_quality)
        result['diagnostics']['prior_predictive']=dict(draws=64,isi_range=[float(prior_isi.min()),float(prior_isi.max())],
            note='Prior simulation at actual observed grid; descriptive model check, not calibration')
        attempts = []
        trace = None
        for extension in (False,True):
            fit_start = time.monotonic()
            trace = sample(model,seed+int(extension),extended=extension)
            stage(dict(stage="diagnostics"))
            fit_diagnostics = diagnostics(trace)
            filename = "posterior-extension.nc" if extension else "posterior.nc"
            trace.to_netcdf(out/filename,engine="netcdf4")
            attempts.append(dict(extension=extension,seconds=time.monotonic()-fit_start,diagnostics=fit_diagnostics,artifact=filename))
            result["diagnostics"]["fits"] = attempts
            publish(out/"diagnostics.json",result["diagnostics"])
            if fit_diagnostics["accepted"]:
                break
            stage(dict(stage="fitting",extension=True))
        if not fit_diagnostics["accepted"]:
            result.update(status="abstained",reason="nuts-diagnostics-unmet")
        else:
            posterior = trace["posterior"]
            replicated_isi,replicated_quality=observed_predictive(posterior,315)
            np.savez_compressed(out/'observed-posterior-predictive.npz',isi=replicated_isi,quality=replicated_quality)
            result['diagnostics']['observed_posterior_predictive']=dict(isi_mean=replicated_isi.mean(axis=(0,1)).tolist(),observed_isi=data['isi'].tolist(),
                quality_mean=replicated_quality.mean(axis=(0,1)).tolist(),observed_quality=data['quality'].tolist(),note='Descriptive fit check; excludes function and diary')
            parameters = {k:np.asarray(posterior[k].values) for k in ("b","a","rho","sigma_e","sigma_isi","p_adherence")}
            parameters.update(beta_c=posterior["patient_beta"].values[...,0],beta_e=posterior["patient_beta"].values[...,1],current_e=posterior["error"].values[...,-1])
            stage(dict(stage="rollouts"))
            effect, integration = integrate(parameters,day=data["day"],current_c=data["c"][-1],current_e=data["e"][-1],seed=seed,stage=stage)
            result["diagnostics"]["integration"] = integration
            if effect is None:
                result.update(status="abstained",reason="numerical-precision-unmet")
            else:
                effect_trace = xr.DataTree.from_dict({"posterior":xr.Dataset({"effect":(("chain","draw"),effect)})})
                effect_diagnostics = diagnostics(effect_trace,variables=["effect"])
                result["diagnostics"]["effect_mcmc"] = effect_diagnostics
                np.savez_compressed(out/"expected-effect.npz",effect=effect,chain=np.arange(effect.shape[0]),draw=np.arange(effect.shape[1]))
                predictive_draws = predictive(parameters,day=data["day"],current_c=data["c"][-1],current_e=data["e"][-1],seed=seed)
                np.savez_compressed(out/"predictive-endpoint.npz",endpoint=predictive_draws,arm=np.array(["continue","escalate"]))
                result["diagnostics"]["predictive_endpoint"] = dict(label="Future ISI predictive intervals; include future adherence/process/measurement randomness",
                    continue_interval=np.quantile(predictive_draws[...,0],[.025,.975]).tolist(),
                    escalate_interval=np.quantile(predictive_draws[...,1],[.025,.975]).tolist())
                if not effect_diagnostics["accepted"]:
                    result.update(status="abstained",reason="effect-mcmc-diagnostics-unmet")
                else:
                    result.update(status="completed",reason=None,effect=dict(mean=float(effect.mean()),sd=float(effect.std(ddof=1)),
                        lower=float(np.quantile(effect,.025)),upper=float(np.quantile(effect,.975)),unit="ISI_points",kind="conditional_expected_assignment_contrast"))
    except Exception as error:
        (out/"failure.log").write_text(traceback.format_exc(),encoding="utf-8")
        result.update(status="failed",reason=f"{type(error).__name__}: {str(error)[:180]}")
    peak=Path('/sys/fs/cgroup/memory.peak')
    result["diagnostics"].update(seconds=time.monotonic()-started,peak_memory_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        cgroup_peak_memory_bytes=int(peak.read_text()) if peak.exists() else None,
        runtime=dict(packages={name:metadata.version(name) for name in ("pymc","pytensor","arviz","arviz-stats","numpy","scipy","xarray")},
                     backend="pymc",sampler="native_nuts",precision="float64",cpu_limit=2,memory_gib=2,
                     learner_image=os.environ.get('REMISSION_LEARNER_IMAGE','not-recorded'),source_commit=os.environ.get('REMISSION_SOURCE_COMMIT','not-recorded')))
    publish(out/"diagnostics.json",result["diagnostics"])
    result["artifacts"] = [dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.iterdir()) if p.is_file() and p.name not in ("result.json","progress.json") and p.suffix!=".partial"]
    parsed = AnalysisResult.model_validate_json(canonical(result))
    publish(out/"result.json",parsed.model_dump(mode="json"))
    stage(dict(stage="complete" if result["status"]=="completed" else result["status"]))
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--input",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    print(canonical(run(args.input,args.output)))


if __name__ == "__main__":
    main()
