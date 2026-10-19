"""Verify an already saved head solution without optimisation or selection."""
import numpy as np
from s04_e024_full_head import dual_value_gradient


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
