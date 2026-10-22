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
                record_ids=[r.record_id for r in history.records],
                likelihood_blocks=dict(isi=[r.record_id for r in isi],quality=[r.record_id for r in quality],
                    adherence=[r.record_id for r in deliveries.values()],
                    observation_indicators=[r.record_id for r in history.records if r.kind=='daily_report']),
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


def gaussian_guide(design, variance, centered, eta):
    """Exact coordinate change; the guide is never the observation likelihood.

    Prior u~N(0,I), pseudo-data y|u~N(Au,R). Sample independent eta and
    u=m+chol(I+A'R^-1 A)^-T eta. The exact prior-density ratio plus Jacobian
    equals -logL_guide+logZ_guide; this algebra avoids subtracting Gaussian
    pseudo-likelihood terms. Use one identity, never both corrections.
    """
    dimension=design.shape[1]
    precision=pt.eye(dimension)+pt.dot(design.T/variance,design)
    cholesky=pt.linalg.cholesky(precision)
    h=pt.dot(design.T,centered/variance)
    intermediate=pt.linalg.solve_triangular(cholesky,h,lower=True)
    mean=pt.linalg.solve_triangular(cholesky.T,intermediate,lower=False)
    u=mean+pt.linalg.solve_triangular(cholesky.T,eta,lower=False)
    log_jacobian=-pt.log(pt.diag(cholesky)).sum()
    correction=-.5*(pt.sum(u**2)-pt.sum(eta**2))+log_jacobian
    return u,correction,log_jacobian


def build(data, *, guide=True):
    if pytensor.config.floatX != "float64":
        raise ValueError("float64 required")
    n = len(data["nights"])
    with pm.Model(coords={"night":data["nights"],"arm":["continue","escalate"],"latent":np.arange(n+7)}) as model:
        sd_b = pm.HalfNormal("sd_b",3)
        sd_beta = pm.HalfNormal("sd_beta",1,dims="arm")
        rho = pm.Uniform("rho",-.95,.95)
        sigma_e = pm.HalfNormal("sigma_e",2)
        sigma_isi = pm.HalfNormal("sigma_isi",2)
        sigma_quality = pm.HalfNormal("sigma_quality",1)
        lag = np.arange(n)[:,None]-np.arange(n)[None,:]
        # Multiplication recurrence has a finite derivative at rho=0. A tensor
        # power with zero exponents can generate0/rho in PyTensor's gradient.
        powers=[pt.as_tensor_variable(np.float64(1.))]
        for _ in range(1,n):
            powers.append(powers[-1]*rho)
        transition = (lag>=0)*pt.stack(powers)[np.maximum(lag,0)]
        if guide:
            # Original independent normal coordinates, including BOTH hierarchy
            # levels. No marginal-prior or population simplification is made.
            basis=pt.concatenate([pt.stack([pt.full((n,),5.),pt.ones(n)*sd_b,
                -4*data['c'],-4*data['e'],-sd_beta[0]*data['c'],-sd_beta[1]*data['e'],
                np.sin(2*np.pi*data['nights']/21)],axis=1),sigma_e*transition],axis=1)
            isi_design=pt.mean(basis[data['recall']],axis=1)
            quality_design=-basis[data['qindex']]/3
            design=pt.concatenate([isi_design,quality_design],axis=0)
            centered=pt.as_tensor_variable(np.concatenate([data['isi']-19.,data['quality']-(10-19/3)]))
            variance=pt.concatenate([pt.ones(len(data['isi']))*(sigma_isi**2+CONFIG['guide_isi_variance_floor']),
                pt.ones(len(data['quality']))*(sigma_quality**2+CONFIG['guide_quality_variance_floor'])])
            eta=pm.Normal('guide_innovation',0,1,dims='latent')
            u,correction,log_jacobian=gaussian_guide(design,variance,centered,eta)
            pm.Deterministic('prior_normal_coordinates',u,dims='latent')
            pm.Deterministic('guide_log_jacobian',log_jacobian)
            pm.Potential('exact_guide_correction',correction)
            mu_b=pm.Deterministic('mu_b',19+5*u[0])
            b_raw=pm.Deterministic('b_raw',u[1])
            beta=pm.Deterministic('population_beta',4*u[2:4],dims='arm')
            beta_raw=pm.Deterministic('beta_raw',u[4:6],dims='arm')
            a=pm.Deterministic('a',u[6])
            innovation=pm.Deterministic('innovation',u[7:],dims='night')
        else:
            # Prior predictive must use this ORIGINAL parameterization. PyMC
            # ignores Potentials in sample_prior_predictive, so the guide's
            # uncorrected eta draws would instead be data-conditioned draws.
            mu_b=pm.Normal('mu_b',19,5)
            b_raw=pm.Normal('b_raw',0,1)
            beta=pm.Normal('population_beta',0,4,dims='arm')
            beta_raw=pm.Normal('beta_raw',0,1,dims='arm')
            a=pm.Normal('a',0,1)
            innovation=pm.Normal('innovation',0,1,dims='night')
        b=pm.Deterministic('b',mu_b+sd_b*b_raw)
        individual=pm.Deterministic('patient_beta',beta+sd_beta*beta_raw,dims='arm')
        error = pm.Deterministic("error", sigma_e*pt.dot(transition,innovation),dims="night")
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
