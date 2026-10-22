"""Proposed native PyMC joint N hierarchy. No production dispatcher calls it."""
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt

from contracts.domain.nof1_config import configuration
from methods.measurement import log_bin
from .data import CohortData, Unavailable

F = np.float64


def _ar_error(innovation, rho, sigma_e, n):
    """Same finite AR convolution, without a chain of scalar products."""
    # Positive integer powers preserve negative rho. Keep the lag-zero term
    # constant so differentiation at rho=0 never forms 0 * rho**(-1).
    powers = pt.concatenate([np.ones(1, dtype=np.float64),
        pt.power(rho, np.arange(1, n, dtype=np.int64))])
    lag = np.arange(n)[:, None] - np.arange(n)[None, :]
    transition = (lag >= 0) * powers[np.maximum(lag, 0)]
    return sigma_e * pt.dot(transition, innovation)


def build(data):
    if not isinstance(data, CohortData) or data.readiness != "eligible":
        raise Unavailable("inconclusive", "target needs two completed randomized blocks per arm")
    if pytensor.config.floatX != "float64":
        raise ValueError("N model requires float64")
    ids = [p.patient_id for p in data.patients]
    coords = dict(patient=ids, coefficient=["C", "E", "A", "B", "R"])
    coords.update({"night_" + str(i): p.nights for i, p in enumerate(data.patients)})
    with pm.Model(coords=coords) as model:
        mu_b = pm.Normal("mu_b", F(19.), F(5.))
        sd_b = pm.HalfNormal("sd_b", F(3.))
        b_raw = pm.Normal("b_raw", F(0.), F(1.), dims="patient")
        baseline = pm.Deterministic("b", mu_b + sd_b * b_raw, dims="patient")
        population = pm.Normal("population_amplitude", F(0.), np.array([4., 4., 3., 3., 3.], dtype=np.float64), dims="coefficient")
        sd_amplitude = pm.HalfNormal("sd_amplitude", F(1.), dims="coefficient")
        raw = pm.Normal("amplitude_raw", F(0.), F(1.), dims=("patient", "coefficient"))
        amplitude = pm.Deterministic("patient_amplitude", population + sd_amplitude * raw, dims=("patient", "coefficient"))
        a = pm.Normal("a", F(0.), F(1.))
        rho = pm.Uniform("rho", F(-.95), F(.95))
        sigma_e = pm.HalfNormal("sigma_e", F(2.))
        sigma_isi = pm.HalfNormal("sigma_isi", F(2.))
        sigma_quality = pm.HalfNormal("sigma_quality", F(1.))
        errors = []
        for i, patient in enumerate(data.patients):
            suffix, n = str(i), len(patient.nights)
            innovation = pm.Normal("innovation_" + suffix, F(0.), F(1.), dims="night_" + suffix)
            error = pm.Deterministic("error_" + suffix, _ar_error(innovation, rho, sigma_e, n), dims="night_" + suffix)
            burden = pm.Deterministic("burden_" + suffix,
                baseline[i] + a * np.sin(2 * np.pi * patient.nights / 21) + error
                - amplitude[i, 0] * patient.c - amplitude[i, 2] * patient.medication[:, 0]
                - amplitude[i, 3] * patient.medication[:, 1] + amplitude[i, 4] * patient.path.rebound,
                dims="night_" + suffix)
            pm.Potential("isi_likelihood_" + suffix,
                log_bin(patient.isi, pt.mean(burden[patient.recall], axis=1), sigma_isi, 1., 28.).sum())
            if len(patient.quality):
                pm.Potential("quality_likelihood_" + suffix,
                    log_bin(patient.quality, F(10.) - burden[patient.qindex] / F(3.), sigma_quality, .001, 10.).sum())
            errors.append(error[-1])
        pm.Deterministic("current_error", pt.stack(errors), dims="patient")
        counts = [p.counts for p in data.patients]
        # These are the conjugate posterior factors ONCE, equivalent to the
        # independent Beta(1,1) priors times resolved Bernoulli likelihoods.
        for name, successes, failures in [
            ("p_C", [c["C_success"] for c in counts], [c["C_total"] - c["C_success"] for c in counts]),
            ("p_M", [c["M_success"] for c in counts], [c["M_total"] - c["M_success"] for c in counts]),
            ("q", [c["observed"] for c in counts], [c["missing"] for c in counts])]:
            # Own the dtype of count-derived constants as well as floatX.
            alpha = np.float64(1.) + np.asarray(successes, dtype=np.float64)
            beta = np.float64(1.) + np.asarray(failures, dtype=np.float64)
            pm.Beta(name, alpha, beta, dims="patient")
    return model


def sample(model, seed, *, purpose, extended=False):
    """Explicit original parameterization/native NUTS; calling needs admission."""
    settings = configuration(purpose)
    with model:
        return pm.sample(draws=settings["extension_draws"] if extended else settings["draws"],
            tune=settings["extension_tune"] if extended else settings["tune"], chains=settings["chains"],
            cores=settings["cores"], random_seed=seed, nuts_sampler="pymc", target_accept=settings["target_accept"],
            nuts={"max_treedepth": settings["max_treedepth"]}, blas_cores=settings["blas_cores"],
            progressbar=False, return_inferencedata=True)


def diagnostics(trace, *, purpose, variables=None):
    import arviz_stats as azs

    settings = configuration(purpose)
    variables = variables or ["mu_b", "sd_b", "b", "population_amplitude", "sd_amplitude",
        "patient_amplitude", "a", "rho", "sigma_e", "sigma_isi", "sigma_quality", "current_error", "p_C", "p_M", "q"]
    result = {}
    for name, fn, kwargs in [("rhat", azs.rhat, {"method": "rank"}),
            ("ess_bulk", azs.ess, {"method": "bulk"}), ("ess_tail", azs.ess, {"method": "tail"}),
            ("mcse", azs.mcse, {"method": "mean"})]:
        summary = {}
        for key, value in fn(trace, var_names=variables, **kwargs).data_vars.items():
            array = np.asarray(value.values)
            extreme = np.max(array) if name in ("rhat", "mcse") else np.min(array)
            summary[key] = float(extreme) if np.all(np.isfinite(array)) else None
        result[name] = summary
    stats = trace["sample_stats"]
    result["divergences"] = int(stats["diverging"].sum())
    result["maximum_tree_depth"] = int(stats["tree_depth"].max())
    energy = np.asarray(stats["energy"].transpose("chain", "draw"))
    result["energy_bfmi"] = (np.mean(np.diff(energy, axis=1) ** 2, axis=1) / np.var(energy, axis=1)).tolist()
    finite = all(v is not None for name in ("rhat", "ess_bulk", "ess_tail", "mcse") for v in result[name].values())
    result["accepted"] = bool(finite and all(v < settings["rhat_max_exclusive"] for v in result["rhat"].values())
        and all(v >= settings["ess_bulk_min"] for v in result["ess_bulk"].values())
        and all(v >= settings["ess_tail_min"] for v in result["ess_tail"].values())
        and result["divergences"] == 0 and result["maximum_tree_depth"] < settings["max_treedepth"]
        and all(np.isfinite(v) and v > settings["bfmi_min_exclusive"] for v in result["energy_bfmi"]))
    return result
