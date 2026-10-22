"""Fixed public medication kinetics, independent of fitting and private truth."""
from dataclasses import dataclass

import numpy as np


OPTIONS = (None, "MED_A", "MED_B")


@dataclass(frozen=True)
class ExposurePath:
    medication: np.ndarray
    rebound: np.ndarray
    taken: np.ndarray


def exposure_path(assigned, taken, *, initial_medication=(0., 0.),
                  initial_rebound=0., previous_assigned=None):
    """One row per consecutive night, including missing reports and washout.

    ``None`` means observed no medication assignment/dose, never an unknown
    delivery. Unknown status must be rejected by the typed history consumer.
    Assignment cessation, rather than dose omission, creates the rebound pulse.
    The initial states belong to the night immediately before the first row.
    """
    assigned, taken = tuple(assigned), tuple(taken)
    if len(assigned) != len(taken):
        raise ValueError("assignment/delivery grids must agree")
    if previous_assigned not in OPTIONS or any(x not in OPTIONS for x in assigned + taken):
        raise ValueError("unsupported medication option")
    if any(dose is not None and dose != action for action, dose in zip(assigned, taken)):
        raise ValueError("taken medication must match assigned medication")
    initial = np.asarray(initial_medication, dtype=np.float64)
    if initial.shape != (2,) or not np.all(np.isfinite(initial)) or np.any(initial < 0):
        raise ValueError("two finite nonnegative initial medication states required")
    if not np.isfinite(initial_rebound) or initial_rebound < 0:
        raise ValueError("finite nonnegative initial rebound required")
    indicators = np.array([[dose == arm for arm in OPTIONS[1:]] for dose in taken],
                          dtype=np.float64).reshape(len(taken), 2)
    medication, rebound = np.empty_like(indicators), np.empty(len(taken))
    state, r, prior = initial.copy(), float(initial_rebound), previous_assigned
    for i, action in enumerate(assigned):
        state = .5 * state + .5 * indicators[i]
        r = .5 * r + float(prior == "MED_B" and action != "MED_B")
        medication[i], rebound[i] = state, r
        prior = action
    return ExposurePath(medication, rebound, indicators)


def medication_design(path, purpose):
    """The sole canonical N0/N1 design difference; rebound is kept separately."""
    if purpose not in ("N0", "N1"):
        raise ValueError("N0 or N1 required")
    return (path.taken if purpose == "N0" else path.medication).copy()
