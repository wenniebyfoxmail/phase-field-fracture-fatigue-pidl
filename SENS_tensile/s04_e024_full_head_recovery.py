"""Verify an already saved head solution without optimisation or selection."""
import numpy as np
from s04_e024_full_head import dual_value_gradient
from s04_e024_three_head import admit_finite


def remaining_seconds(elapsed, prior, cap=900.):
    if not np.isfinite([elapsed, prior, cap]).all() or min(elapsed, prior)<0:
        raise ValueError('invalid cumulative clock')
    remaining = cap-prior-elapsed
    if remaining <= 0:
        raise TimeoutError('combined diagnostic budget exhausted')
    return float(remaining)


def restore_solution(cache, solver):
    full, raw = cache['full_z'].copy(), cache['raw_z'].copy()
    if solver['function_evaluations'] != 1:
        raise ValueError('only the pinned single-evaluation c20 return is recoverable')
    value, gradient, checked, _, _ = dual_value_gradient(
        np.array(solver['multipliers']), cache['quadratic_gradients'],
        cache['quadratic_hessians'], True)
    np.testing.assert_allclose(checked, raw, rtol=1e-8, atol=1e-8)
    np.testing.assert_allclose(-value, solver['dual_lower_bound'], rtol=1e-8, atol=1e-10)
    if not np.isfinite(full).all() or np.linalg.norm(full)>1+1e-12:
        raise ValueError('saved candidate parameter ball')
    trace = [dict(source='recomputed at sole saved original multiplier; no optimisation',
                  dual_lower_bound=-value, multipliers=solver['multipliers'], gradient=gradient.tolist())]
    return full, raw, solver, trace


def revalidate_once(cache, forward, actual_values, baseline, delta_relative):
    """One saved point only; any failure propagates, with no backtracking."""
    decoded = forward(cache['head_coefficients'])
    np.testing.assert_allclose(decoded, cache['uv'], rtol=0, atol=1e-12)
    values = actual_values(cache['uv'])
    ok, failures = admit_finite(values, baseline, delta_relative)
    if not ok:
        raise ValueError('cached c20 failed actual revalidation: '+','.join(failures))
    return cache['uv'].copy(), values
