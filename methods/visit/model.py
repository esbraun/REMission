"""Actual restricted native PyMC NUTS model; observed H* is its only data."""
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt
import arviz_stats as azs
from contracts.domain.analysis import CONFIG


def inputs(history):
    day = (history.cutoff-history.origin).days
    nights = np.arange(-13,day+1)
    c,e = np.zeros(len(nights)),np.zeros(len(nights))
    deliveries = {int((r.event_at-history.origin).total_seconds()//86400)+1:r for r in history.records if r.kind == "delivery"}
    for i,t in enumerate(nights):
        r = deliveries.get(t)
        c[i] = .65*(c[i-1] if i else 0)+.35*int(r is not None and r.option == "behavioral_continue" and r.stage == "taken")
        e[i] = .8*(e[i-1] if i else 0)+.2*int(r is not None and r.option == "behavioral_escalate" and r.stage == "taken")
    quality = sorted((r for r in history.records if r.kind == "daily_report" and r.sleep_quality is not None),key=lambda r:r.event_at)
    isi = sorted((r for r in history.records if r.kind == "isi"),key=lambda r:r.recall_end)
    qindex = [int(round((r.event_at-history.origin).total_seconds()/86400))+13 for r in quality]
    recall = []
    for r in isi:
        last = int(round((r.recall_end-history.origin).total_seconds()/86400))
        recall.append([int(t+13) for t in range(last-13,last+1)])
    return dict(day=day,nights=nights,c=c,e=e,quality=np.array([r.sleep_quality for r in quality]),
                qindex=qindex,isi=np.array([r.total for r in isi]),recall=np.asarray(recall),
                taken=sum(r.stage == "taken" for r in deliveries.values()), deliveries=len(deliveries),
                record_ids=[r.record_id for r in quality+isi],
                arms=sorted({r.option for r in deliveries.values()}))


def log_bin(value, mean, sd, step, maximum):
    lo = (value-step/2-mean)/sd
    hi = (value+step/2-mean)/sd
    normal = pm.Normal.dist(0,1)
    # Use the survival difference in the positive tail to avoid cancellation.
    a = pt.switch(lo>0, pm.logcdf(normal,-lo),pm.logcdf(normal,hi))
    b = pt.switch(lo>0, pm.logcdf(normal,-hi),pm.logcdf(normal,lo))
    interior = a+pt.log(-pt.expm1(b-a))
    return pt.switch(pt.eq(value,0),pm.logcdf(normal,hi),
                     pt.switch(pt.eq(value,maximum),pm.logcdf(normal,-lo),interior))


def build(data):
    if pytensor.config.floatX != "float64":
        raise ValueError("float64 required")
    n = len(data["nights"])
    with pm.Model(coords={"night":data["nights"],"arm":["continue","escalate"]}) as model:
        mu_b = pm.Normal("mu_b",19,5)
        sd_b = pm.HalfNormal("sd_b",3)
        b = pm.Deterministic("b",mu_b+sd_b*pm.Normal("b_raw",0,1))
        beta = pm.Normal("population_beta",0,4,dims="arm")
        sd_beta = pm.HalfNormal("sd_beta",1,dims="arm")
        individual = pm.Deterministic("patient_beta",beta+sd_beta*pm.Normal("beta_raw",0,1,dims="arm"),dims="arm")
        a = pm.Normal("a",0,1)
        rho = pm.Uniform("rho",-.95,.95)
        sigma_e = pm.HalfNormal("sigma_e",2)
        sigma_isi = pm.HalfNormal("sigma_isi",2)
        sigma_quality = pm.HalfNormal("sigma_quality",1)
        lag = np.arange(n)[:,None]-np.arange(n)[None,:]
        transition = (lag>=0)*pt.power(rho,np.maximum(lag,0))
        error = pm.Deterministic("error", sigma_e*pt.dot(transition,pm.Normal("innovation",0,1,dims="night")),dims="night")
        z = pm.Deterministic("burden",b+a*np.sin(2*np.pi*data["nights"]/21)+error-individual[0]*data["c"]-individual[1]*data["e"],dims="night")
        pm.Potential("isi_likelihood",log_bin(data["isi"],pt.mean(z[data["recall"]],axis=1),sigma_isi,1.,28.).sum())
        if len(data["quality"]):
            pm.Potential("quality_likelihood",log_bin(data["quality"],10-z[data["qindex"]]/3,sigma_quality,.001,10.).sum())
        pm.Beta("p_adherence",1+data["taken"],1+data["deliveries"]-data["taken"])
        reports = data["day"]
        pm.Beta("observation_rate",1+len(data["quality"]),1+reports-len(data["quality"]))
    return model


def diagnostics(trace, *, variables=None):
    result = {}
    for name,fn,kwargs in [("rhat",azs.rhat,{"method":"rank"}), ("ess_bulk",azs.ess,{"method":"bulk"}),
                           ("ess_tail",azs.ess,{"method":"tail"}), ("mcse",azs.mcse,{"method":"mean"})]:
        values = fn(trace,var_names=variables,**kwargs)
        summary = {}
        for key in values.data_vars:
            array = np.asarray(values[key].values)
            value = np.max(array) if name in ("rhat","mcse") else np.min(array)
            summary[key] = float(value) if np.isfinite(value) else None
        result[name] = summary
    stats = trace["sample_stats"] if "sample_stats" in trace else None
    if stats is not None:
        result["divergences"] = int(stats["diverging"].sum())
        result["maximum_tree_depth"] = int(stats["tree_depth"].max())
        energy = np.asarray(stats["energy"])
        result["energy_bfmi"] = (np.mean(np.diff(energy,axis=1)**2,axis=1)/np.var(energy,axis=1)).tolist()
    finite = all(v is not None for values in [result["rhat"],result["ess_bulk"],result["ess_tail"]] for v in values.values())
    result["accepted"] = bool(finite and all(v<1.01 for v in result["rhat"].values())
        and all(v>=400 for k in ("ess_bulk","ess_tail") for v in result[k].values())
        and result.get("divergences",0)==0 and result.get("maximum_tree_depth",0)<CONFIG["max_treedepth"]
        and all(v>.3 for v in result.get("energy_bfmi",[1.])))
    return result


def sample(model, seed, *, extended=False):
    with model:
        return pm.sample(draws=CONFIG["extension_draws"] if extended else CONFIG["draws"],
            tune=CONFIG["extension_tune"] if extended else CONFIG["tune"],chains=4,cores=1,
            random_seed=seed,nuts_sampler="pymc",target_accept=CONFIG["target_accept"],
            nuts={"max_treedepth":CONFIG["max_treedepth"]},blas_cores=1,progressbar=False,return_inferencedata=True)
