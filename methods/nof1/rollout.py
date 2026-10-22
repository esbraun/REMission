"""Paired seven-night reported-quality futures from one posterior state."""
from dataclasses import dataclass

import numpy as np

from .data import CohortData
from .observation import rounded_quality


FIELDS = ("b", "a", "rho", "sigma_e", "sigma_quality", "current_error", "beta_C", "beta_A", "beta_B", "gamma", "p_C", "p_M", "q")


@dataclass(frozen=True)
class TargetDraws:
    target_id: str
    purpose: str
    day: int
    current_c: float
    current_medication: tuple
    current_rebound: float
    parameters: dict


def target_draws(trace, data):
    """Select by validated target label, preserving chain/draw axes explicitly."""
    if not isinstance(data, CohortData) or data.readiness != "eligible":
        raise ValueError("eligible bound N target required")
    posterior = trace.posterior
    ids = [p.patient_id for p in data.patients]
    if list(posterior.coords["patient"].values) != ids:
        raise ValueError("posterior patient axes must match the frozen ordered cohort")
    patient = data.patients[data.target_index]
    values = {}
    for field in FIELDS:
        if field.startswith("beta_") or field == "gamma":
            coefficient = "R" if field == "gamma" else field[-1]
            value = posterior["patient_amplitude"].sel(patient=data.target_id, coefficient=coefficient)
        else:
            value = posterior[field]
            if "patient" in value.dims:
                value = value.sel(patient=data.target_id)
        if set(value.dims) != {"chain", "draw"}:
            raise ValueError("unexpected posterior parameter coordinates")
        values[field] = np.asarray(value.transpose("chain", "draw").values, dtype=np.float64)
    result = TargetDraws(data.target_id, data.purpose, patient.day, float(patient.c[-1]),
        tuple(patient.path.medication[-1]), float(patient.path.rebound[-1]), values)
    validate_draws(result)
    return result


def validate_draws(draws):
    if not isinstance(draws, TargetDraws) or draws.purpose not in ("N0", "N1") or not draws.target_id:
        raise ValueError("explicit bound target posterior required")
    if set(draws.parameters) != set(FIELDS):
        raise ValueError("complete N posterior parameter state required")
    shapes = {np.asarray(v).shape for v in draws.parameters.values()}
    if len(shapes) != 1 or len(next(iter(shapes))) != 2 or 0 in next(iter(shapes)):
        raise ValueError("identical nonempty chain/draw axes required")
    if any(not np.all(np.isfinite(v)) for v in draws.parameters.values()):
        raise ValueError("nonfinite posterior state")
    for field in ("p_C", "p_M", "q"):
        value = np.asarray(draws.parameters[field])
        if np.any((value < 0) | (value > 1)):
            raise ValueError("invalid probability state")
    if np.any(np.abs(draws.parameters["rho"]) >= 1) or any(np.any(np.asarray(draws.parameters[k]) < 0) for k in ("sigma_e", "sigma_quality")):
        raise ValueError("invalid AR/noise state")
    state = np.asarray([draws.current_c, *draws.current_medication, draws.current_rebound])
    if state.shape != (4,) or not np.all(np.isfinite(state)) or np.any(state < 0):
        raise ValueError("invalid residual exposure state")


def paired_futures(theta, *, purpose, day, current_c, current_medication,
                   current_rebound, adherence_uniforms, process_normals,
                   measurement_normals, previous_assigned=None):
    """Return rollout/arm/night QUALITY, using supplied exogenous draws.

    Component uniforms have final axis C,M. The two hypothetical assignments
    share future randomness for precision, but retain their own M/R state.
    Observed scheduled review always ends in washout, so previous_assigned=None.
    An explicit alternative is useful for independent cessation controls.
    """
    if (set(theta) != set(FIELDS) or not np.all(np.isfinite(list(theta.values())))
            or any(not 0 <= theta[k] <= 1 for k in ("p_C", "p_M", "q"))
            or abs(theta["rho"]) >= 1 or theta["sigma_e"] < 0 or theta["sigma_quality"] < 0):
        raise ValueError("valid complete scalar posterior state required")
    u = np.asarray(adherence_uniforms, dtype=np.float64)
    process, measurement = np.asarray(process_normals), np.asarray(measurement_normals)
    if (purpose not in ("N0", "N1") or u.ndim != 3 or u.shape[1:] != (7, 2)
            or process.shape != u.shape[:2] or measurement.shape != u.shape[:2]
            or np.any((u < 0) | (u >= 1)) or not np.all(np.isfinite(u))
            or not np.all(np.isfinite(process)) or not np.all(np.isfinite(measurement))
            or previous_assigned not in (None, "MED_A", "MED_B")):
        raise ValueError("finite paired seven-night exogenous arrays required")
    count = len(u)
    quality = np.empty((count, 2, 7))
    for arm, action in enumerate(("MED_A", "MED_B")):
        c = np.full(count, current_c, dtype=np.float64)
        ma, mb = [np.full(count, x, dtype=np.float64) for x in current_medication]
        rebound, error = np.full(count, current_rebound), np.full(count, theta["current_error"])
        prior = previous_assigned
        for h in range(7):
            tc, tm = u[:, h, 0] < theta["p_C"], u[:, h, 1] < theta["p_M"]
            c = .65 * c + .35 * tc
            ma = .5 * ma + .5 * tm * (arm == 0)
            mb = .5 * mb + .5 * tm * (arm == 1)
            rebound = .5 * rebound + (prior == "MED_B" and action != "MED_B")
            error = theta["rho"] * error + theta["sigma_e"] * process[:, h]
            da, db = (ma, mb) if purpose == "N1" else (tm * (arm == 0), tm * (arm == 1))
            burden = (theta["b"] + theta["a"] * np.sin(2 * np.pi * (day + h + 1) / 21) + error
                - theta["beta_C"] * c - theta["beta_A"] * da - theta["beta_B"] * db + theta["gamma"] * rebound)
            quality[:, arm, h] = rounded_quality(10 - burden / 3 + theta["sigma_quality"] * measurement[:, h])
            prior = action
    return quality


def simulate(theta, draws, rng, count):
    return paired_futures(theta, purpose=draws.purpose, day=draws.day,
        current_c=draws.current_c, current_medication=draws.current_medication,
        current_rebound=draws.current_rebound, adherence_uniforms=rng.random((count, 7, 2)),
        process_normals=rng.normal(size=(count, 7)), measurement_normals=rng.normal(size=(count, 7)))


def predictive(draws, *, seed):
    """One random trajectory/draw, labeled separately from expected effects."""
    validate_draws(draws)
    shape = draws.parameters["b"].shape
    flat = {k: np.asarray(v).reshape(-1) for k, v in draws.parameters.items()}
    quality = np.empty((flat["b"].size, 2, 7))
    available = np.empty((len(quality), 7), dtype=bool)
    for i in range(len(quality)):
        rng = np.random.default_rng(np.random.SeedSequence([seed, i, 8102]))
        theta = {k: v[i] for k, v in flat.items()}
        quality[i] = simulate(theta, draws, rng, 1)[0]
        available[i] = rng.random(7) < theta["q"]
    return dict(target_ids=[draws.target_id], unit="reported_quality_points",
        quality=quality.reshape(*shape, 1, 2, 7), available=available.reshape(*shape, 1, 7),
        axes=("chain", "draw", "target", "arm", "night"), arms=("MED_A", "MED_B"),
        nights=np.arange(draws.day + 1, draws.day + 8), kind="predictive_trajectory")
