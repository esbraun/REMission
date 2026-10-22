"""Conditional Gaussian integration and independent adherence batches.

All times below are future nights relative to the frozen cutoff. ISI is one
measurement of the average burden of future nights 29..42, not 14 measures.
"""
import time
import numpy as np
from scipy.special import ndtr, log_ndtr
from contracts.domain.analysis import CONFIG


def bin_logprob(value, mean, sd, step=1., maximum=28.):
    """Independent numerical reference for the actual rounded/clipped likelihood."""
    lo = (np.asarray(value)-step/2-mean)/sd
    hi = (np.asarray(value)+step/2-mean)/sd
    a = np.where(lo > 0, log_ndtr(-lo), log_ndtr(hi))
    b = np.where(lo > 0, log_ndtr(-hi), log_ndtr(lo))
    with np.errstate(divide="ignore", invalid="ignore"):
        interior = a+np.log(-np.expm1(b-a))
    return np.where(np.asarray(value) == 0, log_ndtr(hi),
                    np.where(np.asarray(value) == maximum, log_ndtr(-lo), interior))


def rounded_isi_mean(mean, sd):
    mean, sd = np.broadcast_arrays(np.asarray(mean), np.asarray(sd))
    if np.any(sd < 0):
        raise ValueError("negative normal SD")
    if np.all(sd > 0):
        return ndtr((mean[..., None]-np.arange(.5, 28))/sd[..., None]).sum(axis=-1)
    safe = np.where(sd==0,1.,sd)
    return np.where(sd == 0, np.clip(np.floor(mean+.5), 0, 28),
                    ndtr((mean[..., None]-np.arange(.5, 28))/safe[..., None]).sum(axis=-1))


def endpoint_weights(decay):
    """Innovation/treatment impulse weights, including late-window partial tails."""
    return np.array([sum(decay**(h-j) for h in range(max(29,j),43))/14 for j in range(1,43)])


def conditional_endpoint(b, a, rho, sigma_e, sigma_isi, current_e, beta_c, beta_e, current_c, current_e_exposure, day):
    h = np.arange(29,43)
    mean = (b+a*np.sin(2*np.pi*(day+h)/21).mean()+current_e*np.mean(rho**h)
            -beta_c*current_c*np.mean(.65**h)-beta_e*current_e_exposure*np.mean(.8**h))
    sd = np.sqrt(sigma_e**2*np.sum(endpoint_weights(rho)**2)+sigma_isi**2)
    return mean, sd


def integration_bounds(batches, *, seed=CONFIG["bootstrap_seed"],deadline=None):
    """Whole 20-draw within-chain block bootstrap, retaining all eight batches.

    Sums are sufficient for the two prespecified variances, so bootstrapping
    these block sums is exactly equivalent to carrying all batch rows.
    """
    chains, draws, count = batches.shape
    block = CONFIG["bootstrap_block"]
    if count != 8 or draws % block:
        raise ValueError("integration coordinates must preserve whole chain blocks")
    delta = batches.mean(axis=-1)
    v = batches.var(axis=-1, ddof=1)/8
    m = delta.size
    nb = draws//block
    sums = np.stack([delta.reshape(chains,nb,block).sum(-1),
                     (delta**2).reshape(chains,nb,block).sum(-1),
                     v.reshape(chains,nb,block).sum(-1)],axis=-1)
    rng = np.random.default_rng(seed)
    u, lower = [], []
    for _ in range(CONFIG["bootstrap_resamples"]):
        if deadline is not None and time.monotonic()>deadline:
            raise TimeoutError('whole-integration-deadline')
        selected = sums[np.arange(chains)[:,None], rng.integers(nb,size=(chains,nb))].sum(axis=(0,1))
        vbar = selected[2]/m
        s2 = (selected[1]-selected[0]**2/m)/(m-1)
        u.append(vbar)
        lower.append(max(0., s2-vbar))
    upper = float(np.quantile(u,.95))
    low = float(np.quantile(lower,.05))
    floor = CONFIG["sd_floor"]
    se = float(np.sqrt(upper/m))
    return dict(U=upper, L=low, residual_variance=float(v.mean()),
                raw_effect_variance=float(delta.var(ddof=1)),
                uninflated_effect_variance=max(0.,float(delta.var(ddof=1)-v.mean())),
                mean_integration_se=se,
                variance_pass=bool(upper <= .01*max(low,floor**2)),
                mean_pass=bool(se <= min(CONFIG["mean_se"], .1*max(np.sqrt(low),floor))))


def integrate(parameters, *, day, current_c, current_e, seed, stage=lambda value:None, seconds=None):
    """Stream conditional expected contrasts on identical outer chain/draw axes."""
    started = time.monotonic()
    cap = CONFIG["integration_seconds"] if seconds is None else seconds
    shape = parameters["b"].shape
    if len(shape) != 2:
        raise ValueError("chain/draw axes required")
    flat = {k:np.asarray(v,dtype=np.float64).reshape(-1) for k,v in parameters.items()}
    m = flat["b"].size
    means, sds = np.empty(m), np.empty(m)
    for i in range(m):
        means[i],sds[i] = conditional_endpoint(*(flat[k][i] for k in ("b","a","rho","sigma_e","sigma_isi","current_e","beta_c","beta_e")),current_c,current_e,day)
    wc, we = .35*endpoint_weights(.65), .2*endpoint_weights(.8)
    # Independent across posterior draws and across the eight inner batches.
    streams = [[np.random.default_rng(np.random.SeedSequence([seed, i, batch, 7101])) for batch in range(8)] for i in range(m)]
    totals = np.zeros((m,8))
    previous = None
    reports = []
    n = 0
    accepted = False
    delta = None
    def timed_out():
        return None,dict(status="numerical-precision-unmet",attempted=reports,seconds=time.monotonic()-started,
                         cap_seconds=cap,reason="whole-integration-deadline")
    for k in [1024,2048,4096,8192,16384,32768,65536]:
        add = k//8-n
        for i in range(m):
            if time.monotonic()-started > cap:
                reports.append(dict(K=k,status='interrupted',completed_outer_draws=i))
                return timed_out()
            for batch,rng in enumerate(streams[i]):
                taken = rng.random((add,42)) < flat["p_adherence"][i]
                # Common adherence uniforms pair the two retained-plan branches.
                mc = means[i]-flat["beta_c"][i]*(taken@wc)
                me = means[i]-flat["beta_e"][i]*(taken@we)
                totals[i,batch] += np.sum(rounded_isi_mean(me,sds[i])-rounded_isi_mean(mc,sds[i]))
        n = k//8
        batches = (totals/n).reshape(*shape,8)
        delta = batches.mean(axis=-1)
        try:
            bounds = integration_bounds(batches,deadline=started+cap)
        except TimeoutError:
            reports.append(dict(K=k,status='precision-checks-interrupted'))
            return timed_out()
        summary = np.array([delta.std(ddof=1), *np.quantile(delta,[.025,.975])])
        tolerance = max(CONFIG["absolute_stability"], .02*np.sqrt(bounds["L"]))
        change = None if previous is None else np.abs(summary-previous)
        stable = change is not None and bool(np.all(change <= tolerance))
        record = dict(K=k, **bounds, sd=float(summary[0]), interval=summary[1:].tolist(),
                      changes=None if change is None else change.tolist(), stability_tolerance=tolerance,
                      stability_pass=stable, seconds=time.monotonic()-started)
        reports.append(record)
        stage(dict(stage="rollouts", K=k, checks=record))
        # Bootstrap, quantiles and progress publication belong to the same cap.
        if time.monotonic()-started>cap:
            return timed_out()
        if bounds["variance_pass"] and bounds["mean_pass"] and stable:
            accepted = True
            break
        previous = summary
    if time.monotonic()-started>cap:
        return timed_out()
    return (delta if accepted else None), dict(status="accepted" if accepted else "numerical-precision-unmet",
        attempted=reports, seconds=time.monotonic()-started, gaussian_integration="exact conditional AR plus endpoint measurement",
        bootstrap=dict(resamples=1000,block=20,seed=CONFIG["bootstrap_seed"]),
        memory="streamed eight adherence batches; no M x K x horizon allocation")


def predictive(parameters, *, day, current_c, current_e, seed):
    """Separate one-trajectory-per-posterior-draw predictive endpoint draws."""
    rng = np.random.default_rng(np.random.SeedSequence([seed,9182]))
    shape = parameters["b"].shape
    p = {k:v.reshape(-1) for k,v in parameters.items()}
    draws = np.empty((p["b"].size,2))
    for i in range(len(draws)):
        mean,sd = conditional_endpoint(*(p[k][i] for k in ("b","a","rho","sigma_e","sigma_isi","current_e","beta_c","beta_e")),current_c,current_e,day)
        adherence = rng.random(42)<p["p_adherence"][i]
        noise = rng.normal()*sd
        for arm,(beta,weights) in enumerate(((p["beta_c"][i],.35*endpoint_weights(.65)),(p["beta_e"][i],.2*endpoint_weights(.8)))):
            draws[i,arm] = np.clip(np.floor(mean-beta*(adherence@weights)+noise+.5),0,28)
    return draws.reshape(*shape,2)
