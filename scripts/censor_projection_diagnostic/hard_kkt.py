"""Archive-only nodal bound KKT; no assembly, optimization, or history update."""
import numpy as np

BOUND_TOL = 1e-12
RAW_SCREEN = 4e-4


def assess(residual, damage, previous, free, mass=None, energy_scale=None):
    r, d, lo = [np.asarray(x, dtype=float) for x in (residual, damage, previous)]
    if r.ndim != 1 or r.shape != d.shape or r.shape != lo.shape:
        raise ValueError('Expected same-size nodal vectors')
    if not all(np.isfinite(x).all() for x in (r, d, lo)):
        raise ValueError('Nonfinite nodal data')
    free = np.asarray(free)
    if free.ndim != 1 or free.dtype.kind not in 'iu' or len(np.unique(free)) != len(free) or not len(free) or free.min() < 0 or free.max() >= len(d):
        raise ValueError('Invalid free index set')
    active = np.zeros(len(d), dtype=bool); active[free] = True
    fixed = ~active
    # Do not turn a narrow but nonzero feasible interval into an equality.
    collapsed = active & (lo == 1.) & (d == 1.)
    exact_lower = active & (d == lo) & (lo < 1.)
    exact_upper = active & (d == 1.) & (lo < 1.)
    near_both = active & ~collapsed & ~exact_lower & ~exact_upper & (abs(d-lo) <= BOUND_TOL) & (abs(d-1) <= BOUND_TOL)
    lower = exact_lower | (active & ~collapsed & ~near_both & ~exact_upper & (abs(d-lo) <= BOUND_TOL))
    upper = exact_upper | (active & ~collapsed & ~near_both & ~lower & (abs(d-1) <= BOUND_TOL))
    interior = active & ~collapsed & ~near_both & ~lower & ~upper
    filtered = np.zeros_like(r)
    filtered[lower] = np.minimum(r[lower], 0.)
    filtered[upper] = np.maximum(r[upper], 0.)
    filtered[interior | near_both] = r[interior | near_both]
    # Legacy formula retained verbatim for transparent comparison.
    old_lower = active & (abs(d-lo) <= BOUND_TOL) & (d < 1.-BOUND_TOL)
    old_upper = active & (abs(d-1.) <= BOUND_TOL) & ~old_lower
    old_interior = active & ~old_lower & ~old_upper
    legacy = np.zeros_like(r)
    legacy[old_lower] = np.minimum(r[old_lower],0.)
    legacy[old_upper] = np.maximum(r[old_upper],0.)
    legacy[old_interior] = r[old_interior]
    violations = {'prior_below_zero':np.maximum(-lo,0.), 'prior_above_one':np.maximum(lo-1.,0.),
                  'damage_below_prior':np.maximum(lo-d,0.), 'damage_above_one':np.maximum(d-1.,0.),
                  'prescribed_damage':np.where(fixed,np.abs(d-1.),0.),
                  'prescribed_prior':np.where(fixed,np.abs(lo-1.),0.)}
    feasibility = {}
    for name,v in violations.items():
        idx=int(np.argmax(v)); feasibility[name]={'max':float(v[idx]),'node_zero_based':idx,
            'nonzero_count':int((v>0).sum()),'above_tolerance_count':int((v>BOUND_TOL).sum())}
    feasible = all(v['max'] <= BOUND_TOL for v in feasibility.values())
    exact_feasible = all(v['max'] == 0. for v in feasibility.values())
    raw=float(np.linalg.norm(filtered[free]))
    status='PASS' if feasible and not near_both.any() and raw <= RAW_SCREEN else 'FAIL'
    if near_both.any(): status='AMBIGUOUS_NEAR_BOTH_BOUNDS'
    if not exact_feasible: status='FEASIBILITY_TOLERANCE_ONLY'
    if not feasible: status='INFEASIBLE'
    result={'raw_l2':float(np.linalg.norm(r[free])), 'hard_kkt_raw_l2':raw,
        'legacy_raw_kkt_l2':float(np.linalg.norm(legacy[free])), 'raw_screen':RAW_SCREEN,
        'bound_tolerance':BOUND_TOL,'status':status,'feasible_within_tolerance':feasible,'exactly_feasible':exact_feasible,
        'counts':{k:int(v.sum()) for k,v in [('lower',lower),('upper',upper),('interior',interior),('collapsed',collapsed),('ambiguous',near_both),('fixed',fixed)]},
        'feasibility':feasibility,'max_kkt_node_zero_based':int(np.argmax(abs(filtered))),
        'max_kkt_abs':float(abs(filtered).max()),'full_teacher':'NOT_QUALIFIED'}
    if mass is not None:
        m=np.asarray(mass,dtype=float)
        if m.shape != d.shape or not np.isfinite(m).all() or (m<=0).any() or not np.isclose(m.sum(),1.,rtol=1e-12,atol=1e-12) or energy_scale is None or not np.isfinite(energy_scale) or energy_scale<=0:
            raise ValueError('Invalid mass/energy scale')
        box=d-np.clip(d-r/energy_scale/m,0.,1.)
        result['box_mass_rms_free']=float(np.sqrt(np.sum(m[free]*box[free]**2)))
        # Never clip/repair an invalid feasible interval to manufacture a map.
        if (lo>1).any() or (lo<0).any(): result['hard_mass_rms_free']=None
        else:
            hard=d-np.minimum(np.maximum(d-r/energy_scale/m,lo),1.)
            result['hard_mass_rms_free']=float(np.sqrt(np.sum(m[free]*hard[free]**2)))
        result['hard_normalized_threshold']=None
    return result,filtered,legacy
