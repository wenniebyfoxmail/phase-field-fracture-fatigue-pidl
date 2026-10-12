"""Candidate fixed weighted planar-rigid quotient; not exporter inversion."""
import numpy as np


def quotient_residual(xy, residual, area_weights):
    """Remove ONE global rigid field from a residual on declared support.

    xy and weights must be frozen from admissible geometry, not selected using
    response values. All comparators must use the same support/operator. There
    is no separate crack-side registration and no fitted model/gain parameter.
    """
    xy = np.asarray(xy, dtype=float)
    residual = np.asarray(residual, dtype=float)
    weights = np.asarray(area_weights, dtype=float)
    if xy.ndim != 2 or xy.shape[1] != 2 or residual.shape != xy.shape:
        raise ValueError("xy/residual shape mismatch")
    if weights.shape != (len(xy),) or len(xy) < 2:
        raise ValueError("weight shape or insufficient support")
    if not (np.isfinite(xy).all() and np.isfinite(residual).all() and
            np.isfinite(weights).all() and (weights > 0).all()):
        raise ValueError("nonfinite or nonpositive observation support")
    # Centering preserves the rigid span while improving numerical conditioning.
    center = np.average(xy, weights=weights, axis=0)
    p = xy - center
    R = np.zeros((2 * len(xy), 3))
    R[0::2, 0] = 1
    R[1::2, 1] = 1
    R[0::2, 2] = -p[:, 1]
    R[1::2, 2] = p[:, 0]
    sqrtw = np.repeat(np.sqrt(weights / weights.max()), 2)
    coeff, _, rank, singular = np.linalg.lstsq(
        R * sqrtw[:, None], residual.ravel() * sqrtw, rcond=1e-12)
    if rank != 3 or singular[-1] <= 0 or singular[0] / singular[-1] > 1e12:
        raise ValueError("rigid basis rank/conditioning failure")
    result = residual - (R @ coeff).reshape(-1, 2)
    if not np.isfinite(result).all():
        raise ValueError("nonfinite projected residual")
    return result
