"""Exact numerical reference for clipped, .001-rounded reported quality."""
import numpy as np
from scipy.special import ndtr


def rounded_quality(value):
    """Match the producer's ties-to-even rounding after clipping to 0..10."""
    return np.round(np.clip(np.asarray(value, dtype=np.float64), 0., 10.), 3)


def expected_quality(mean, sd):
    """E[round(clip(N(mean,sd),0,10),3)], preserving all input axes.

    For positive SD, the tail-sum identity sums all 10,000 thresholds exactly
    up to floating-point CDF arithmetic. No clipping/rounding approximation or
    latent-burden substitution is made. The scalar loop bounds scratch memory;
    this is a reference routine, not an admitted production rollout algorithm.
    """
    mean, sd = np.broadcast_arrays(np.asarray(mean, dtype=np.float64),
                                  np.asarray(sd, dtype=np.float64))
    if not np.all(np.isfinite(mean)) or not np.all(np.isfinite(sd)) or np.any(sd < 0):
        raise ValueError("finite means and nonnegative finite SDs required")
    thresholds = (np.arange(10000, dtype=np.float64) + .5) * .001
    result = np.empty(mean.size)
    for i, (mu, sigma) in enumerate(zip(mean.flat, sd.flat)):
        result[i] = (rounded_quality(mu) if sigma == 0 else
                     .001 * ndtr((mu - thresholds) / sigma).sum())
    return result.reshape(mean.shape)
