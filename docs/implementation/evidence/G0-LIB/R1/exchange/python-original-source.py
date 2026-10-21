"""Bounded real APIs/serialization only; never a pilot/statistical gate."""
import csv
import importlib.metadata as md
import inspect
import json
import math
import platform
import subprocess
import time
from pathlib import Path

import arviz as az
import arviz_stats as azs
import numpy as np
import pymc as pm
import pytensor
import pytensor.tensor as pt
import scipy.stats as st
import statsmodels.api as sm
import xarray as xr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from stochtree import BCFModel

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tooling/library/__pycache__/outputs"
EVIDENCE = ROOT / "docs/implementation/evidence/G0-LIB"
OUT.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)
started = time.perf_counter()
result = {"scope": "bounded API qualification, not calibration/recovery/20-fit pilot",
          "platform": platform.platform(), "python": platform.python_version(),
          "packages": {d.metadata["Name"]: d.version for d in md.distributions()}}
assert pytensor.config.floatX == "float64"
host = pytensor.function([], pt.constant(np.array([1., 2.], dtype=np.float64)))()
assert isinstance(host, np.ndarray) and host.dtype == np.float64
result["runtime"] = {"buffer": type(host).__name__, "dtype": str(host.dtype), "cxx": pytensor.config.cxx,
                     "cpu": True, "threads": subprocess.check_output(["sh", "-c", "printf '%s %s %s' \"$OMP_NUM_THREADS\" \"$OPENBLAS_NUM_THREADS\" \"$MKL_NUM_THREADS\""], text=True)}
y = np.linspace(-0.4, 1.0, 20, dtype=np.float64)
(OUT / "fit-input.json").write_text(json.dumps({"fixture": "normal-normal API probe only", "y": y.tolist(), "seed": 73142}) + "\n")
with pm.Model() as model:
    mu = pm.Normal("mu", mu=0, sigma=2)
    pm.Normal("y", mu=mu, sigma=1, observed=y)
    prior = pm.sample_prior_predictive(draws=8, random_seed=73141)
    trace = pm.sample(draws=200, tune=200, chains=4, cores=1, random_seed=73142,
                      nuts_sampler="pymc", target_accept=0.9, progressbar=False,
                      blas_cores=1, return_inferencedata=True)
    posterior_predictive = pm.sample_posterior_predictive(trace, random_seed=73143, progressbar=False)
draws = trace["posterior"]["mu"].values
assert draws.shape == (4, 200) and draws.dtype == np.float64 and np.isfinite(draws).all()
exact_variance = 1 / (0.25 + y.size)
exact_mean = exact_variance * y.sum()
diagnostics = {}
for name, fn, kwargs in [("rhat", azs.rhat, {"method": "rank"}), ("ess_bulk", azs.ess, {"method": "bulk"}),
                         ("ess_tail", azs.ess, {"method": "tail"}), ("mcse", azs.mcse, {"method": "mean"})]:
    value = fn(trace, var_names=["mu"], **kwargs)
    diagnostics[name] = float(value["mu"].values.reshape(-1)[0])
trace.to_netcdf(OUT / "posterior.nc", engine="netcdf4")
restored = xr.open_datatree(OUT / "posterior.nc", engine="netcdf4")
np.testing.assert_array_equal(restored["posterior"]["mu"].values, draws)
with (OUT / "pymc-draws.csv").open("w", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n"); writer.writerow(["chain", "draw", "quantity", "value"])
    for chain in range(4):
        for draw in range(200): writer.writerow([chain, draw, "mu", repr(float(draws[chain, draw]))])
result["native_nuts"] = {"sampler": "native_pymc_nuts", "seed": 73142, "chains": 4, "draws": 200, "tune": 200,
                         "container": type(trace).__name__, "shape": list(draws.shape), "dtype": str(draws.dtype),
                         "mean": float(draws.mean()), "analytic_mean": float(exact_mean), "analytic_variance": exact_variance,
                         "diagnostics": diagnostics, "divergences": int(trace["sample_stats"]["diverging"].sum()),
                         "roundtrip_exact": True, "prior_predictive": type(prior).__name__,
                         "posterior_predictive": type(posterior_predictive).__name__,
                         "claim_limit": "Short qualification run; these are actual diagnostics, not G2 final acceptance"}
assert abs(draws.mean() - exact_mean) < 0.25  # broad API sanity, not calibrated numerical acceptance
figure = az.plot_trace(trace, var_names=["mu"])
import matplotlib.pyplot as plt
plt.savefig(OUT / "trace.png"); plt.close("all")
result["arviz"] = {"api": "arviz_stats.rhat/ess/mcse on PyMC6 DataTree; arviz.plot_trace", "plot_saved": True}

# Fully observed reference design; the R small-sample correction is reported separately.
rows = []
for patient in range(12):
    for time_index in range(6):
        action = (patient + time_index) % 2
        x = (patient - 5.5) / 6 + time_index / 20
        outcome = 1 + 0.2*x + 2*(action-0.5) + 0.1*math.sin(patient+2*time_index)
        rows.append([patient, time_index, outcome, action, 0.5, 0.5, 1, x])
with (OUT / "wcls-input.csv").open("w", newline="") as stream:
    writer=csv.writer(stream, lineterminator="\n"); writer.writerow(["id","time","y","action","logging_probability","numerator_probability","availability","x"]);writer.writerows(rows)
array=np.array(rows, dtype=np.float64)
design=sm.add_constant(np.column_stack([array[:,7], array[:,3]-0.5]))
fit=sm.WLS(array[:,2],design,weights=np.ones(len(array))).fit(cov_type="cluster",cov_kwds={"groups":array[:,0],"use_correction":True})
result["wcls_python"]={"coefficients":fit.params.tolist(),"se":fit.bse.tolist(),"variance":"statsmodels cluster correction, not R hat-matrix correction","n":len(rows)}
splits=list(GroupKFold(n_splits=3).split(design,array[:,2],groups=array[:,0]))
for train,test in splits:assert not set(array[train,0]) & set(array[test,0])
ridge=Ridge(alpha=1.0).fit(design[splits[0][0]],array[splits[0][0],2]);assert np.isfinite(ridge.predict(design[splits[0][1]])).all()
result["numerical_ml"]={"normal_cdf":float(st.norm.cdf(0)),"ridge_grouped_split":True,"seedsequence":[int(s.generate_state(1)[0]) for s in np.random.SeedSequence(73142).spawn(2)]}
rng=np.random.default_rng(73144);X=rng.normal(size=(48,2));Z=rng.binomial(1,.5,size=(48,1));Y=1+X[:,0]-.5*Z[:,0]+rng.normal(0,.2,48)
bcf=BCFModel()
bcf.sample(X_train=X,Z_train=Z,y_train=Y,propensity_train=np.full((48,1),.5),num_gfr=2,num_burnin=2,num_mcmc=4,
           general_params={"random_seed":73144},prognostic_forest_params={"num_trees":10},treatment_effect_forest_params={"num_trees":5})
prediction=bcf.predict(X=X[:4],Z=Z[:4],propensity=np.full((4,1),.5))
result["bcf"]={"fixture":"matched single decision; no longitudinal claim","prediction_shapes":{k:None if v is None else list(np.asarray(v).shape) for k,v in prediction.items()}}
assert all(np.isfinite(v).all() for v in prediction.values() if v is not None)
result["seconds"]=time.perf_counter()-started
(EVIDENCE/"python-probes.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
