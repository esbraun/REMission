"""Independent finite-polynomial/recurrence algebra, not symbolic qualification."""
import json
from pathlib import Path
import numpy as np

rng = np.random.default_rng(20261022)
rows = []
for n in (1, 2, 50, 96, 98):
    innovation, weights = rng.normal(size=n), rng.normal(size=n)
    lag = np.arange(n)[:, None] - np.arange(n)[None, :]
    nonnegative = np.maximum(lag, 0)
    for rho in (-.949999, -.4, 0., .4, .949999):
        sigma = 2.2
        powers = np.r_[np.float64(1), np.power(rho, np.arange(1, n, dtype=np.int64))]
        derivative = np.r_[np.float64(0), np.arange(1, n) * np.power(rho, np.arange(n-1))]
        transition = (lag >= 0) * powers[nonnegative]
        derivative_transition = (lag >= 0) * derivative[nonnegative]
        actual = sigma * transition @ innovation
        actual_pullback = np.r_[weights @ (sigma*derivative_transition@innovation), weights @ (transition@innovation), sigma*weights@transition]
        expected, dr, ds = [], [], []
        previous = previous_rho = previous_sigma = 0.
        for eps in innovation:
            current = rho*previous + sigma*eps
            current_rho = previous + rho*previous_rho
            current_sigma = eps + rho*previous_sigma
            expected.append(current); dr.append(current_rho); ds.append(current_sigma)
            previous, previous_rho, previous_sigma = current, current_rho, current_sigma
        reverse = np.empty(n)
        following = 0.
        for index in range(n-1, -1, -1):
            following = weights[index] + rho*following
            reverse[index] = sigma*following
        expected_pullback = np.r_[weights@dr, weights@ds, reverse]
        value_error = float(np.max(np.abs(actual-expected)))
        gradient_error = float(np.max(np.abs(actual_pullback-expected_pullback)))
        assert value_error <= 1e-10 and gradient_error <= 1e-10
        rows.append(dict(nights=n, rho=rho, value_max_absolute_error=value_error, pullback_max_absolute_error=gradient_error))
record = dict(status='passed-algebra-only', numpy=np.__version__, initial_state='zero at public night -14, unchanged', tolerance=1e-10, rows=rows)
destination = Path(__file__).with_name('ar-algebra.json')
destination.write_text(json.dumps(record, sort_keys=True, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(cases=len(rows), value_max=max(r['value_max_absolute_error'] for r in rows), gradient_max=max(r['pullback_max_absolute_error'] for r in rows))))
