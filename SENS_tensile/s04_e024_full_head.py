"""D012: full fixed-head convex proxies, sparse native tangent, dual solve."""
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.linalg.blas import dgemm
from scipy.optimize import minimize
from scipy.optimize import brentq
from scipy.sparse import coo_matrix


def gram(x):
    x = np.asarray(x, dtype=np.float64, order='F')
    return dgemm(1., x, x, trans_a=True)


def tangent_support(mechanics, phi):
    """All elements incident on a nonzero feature row, including force halo."""
    active_nodes = np.any(phi != 0, axis=1)
    elements = np.flatnonzero(np.any(active_nodes[mechanics.conn], axis=1))
    if not len(elements):
        raise ValueError('empty fixed-feature support')
    nodes, inverse = np.unique(mechanics.conn[elements], return_inverse=True)
    conn = inverse.reshape(-1, 4)
    ndof = 2*len(nodes)
    dofs = (2*conn[..., None]+np.arange(2)).reshape(-1, 8)
    stiffness = np.zeros((len(elements), 8, 8))
    mu, bulk = 1/2.6, 1/1.2
    for j, (grad_all, det_all, damage_g_all) in enumerate(mechanics.geo):
        grad, det, damage_g = grad_all[elements], det_all[elements], damage_g_all[elements]
        volume = bulk*np.where(mechanics.branches[elements, j], damage_g, 1.)
        constitutive = np.zeros((len(elements), 3, 3))
        constitutive[:, 0, 0] = constitutive[:, 1, 1] = 4*mu*damage_g/3+volume
        constitutive[:, 0, 1] = constitutive[:, 1, 0] = -2*mu*damage_g/3+volume
        constitutive[:, 2, 2] = mu*damage_g
        b = np.zeros((len(elements), 3, 8))
        b[:, 0, 0::2] = grad[:, 0]
        b[:, 1, 1::2] = grad[:, 1]
        b[:, 2, 0::2] = grad[:, 1]
        b[:, 2, 1::2] = grad[:, 0]
        stiffness += np.einsum('eai,eab,ebj,e->eij', b, constitutive, b, det)
    rows = np.broadcast_to(dofs[:, :, None], stiffness.shape).ravel()
    cols = np.broadcast_to(dofs[:, None, :], stiffness.shape).ravel()
    k = coo_matrix((stiffness.ravel(), (rows, cols)), shape=(ndof, ndof)).tocsr()
    return elements, nodes, k


def build_proxies(phi, error, node_weights, mechanics, reference, radius_us, driver0, driver_stress):
    """Seven original-error-normalized Gram models in row-major (feature,u/v)."""
    if phi.ndim != 2 or error.shape != (len(phi), 2) or not np.isfinite(phi).all():
        raise ValueError('fixed head schema')
    p = phi.shape[1]; n = 2*p
    constants, gradients, hessians = [], [], []
    for weight in node_weights.values():
        c = float(np.sum(weight[:, None]*error**2))
        g = radius_us/abs(reference['US'])*np.einsum('np,n,nd->pd', phi, weight, error)
        q = gram(phi*np.sqrt(weight)[:, None])*(radius_us/abs(reference['US']))**2
        h = np.zeros((n, n)); h[0::2, 0::2] = h[1::2, 1::2] = q
        constants.append(c); gradients.append(g.ravel()/c); hessians.append(h/c)
    elements, nodes, k = tangent_support(mechanics, phi)
    local_velocity = np.zeros((2*len(nodes), n))
    local_velocity[0::2, 0::2] = radius_us*phi[nodes]
    local_velocity[1::2, 1::2] = radius_us*phi[nodes]
    force_columns = k@local_velocity
    free = np.repeat(mechanics.free[nodes], 2)
    weights = np.repeat(mechanics.mass[nodes], 2)[free]
    jforce = force_columns[free]/np.sqrt(weights[:, None])
    original_force = reference['origin_force']
    f0 = original_force[nodes].ravel()[free]/np.sqrt(weights)
    c = float(np.sum(mechanics.dual(original_force)**2))  # WHOLE domain denominator
    constants.append(c); gradients.append(np.einsum('ni,n->i', jforce, f0)/c); hessians.append(gram(jforce)/c)
    # The support operator is saved only through exact 3D contractions, not a new basis.
    contracted = np.einsum('ni,ki->nk', force_columns, reference['basis_flat'])
    expected = []
    for basis in reference['basis_flat']:
        uv = radius_us*dgemm(1., np.asarray(phi, order='F'), basis.reshape(p, 2))
        native = mechanics.force(uv, tangent=True)
        outside = np.ones(len(phi), bool); outside[nodes] = False
        if np.any(native[outside] != 0):
            raise ValueError('missing sparse force halo')
        expected.append(native[nodes].ravel())
    force_gap = float(np.max(abs(contracted-np.stack(expected, axis=1))))
    if force_gap > 1e-11:
        raise ValueError('sparse incident-element tangent mismatch')
    del local_velocity, force_columns, jforce
    # Driver derivatives only on incident elements; all origin error integrals remain global.
    driver_error = driver0-reference['driver_reference']
    g_driver = np.zeros((2, n)); h_driver = np.zeros((2, n, n))
    driver_constants = [float(np.sum(reference['weights']*mask*driver_error**2)) for mask in reference['driver_masks']]
    element_phi = phi[mechanics.conn[elements]]
    for j, (grad, _, _) in enumerate(mechanics.geo):
        derivative = radius_us*np.einsum('ean,enp->eap', grad[elements], element_phi)
        stress = driver_stress[elements, j]
        columns = np.empty((len(elements), n))
        columns[:, 0::2] = stress[:, 0, None]*derivative[:, 0]+stress[:, 2, None]*derivative[:, 1]
        columns[:, 1::2] = stress[:, 1, None]*derivative[:, 1]+stress[:, 2, None]*derivative[:, 0]
        for region, mask in enumerate(reference['driver_masks']):
            weight = reference['weights'][elements, j]*mask[elements, j]
            g_driver[region] += np.einsum('n,ni,n->i', weight, columns, driver_error[elements, j])
            h_driver[region] += gram(columns*np.sqrt(weight)[:, None])
    for region, c in enumerate(driver_constants):
        constants.append(c); gradients.append(g_driver[region]/c); hessians.append(h_driver[region]/c)
    c, g, h = np.array(constants), np.array(gradients), np.array(hessians)
    if not all(np.isfinite(x).all() for x in (c, g, h)) or c.min() <= 0:
        raise ValueError('invalid full-head proxies')
    return c, g, h, dict(parameters=n,features=p,incident_elements=len(elements),halo_nodes=len(nodes),
                         sparse_tangent_3D_max_abs=force_gap)


def dual_value_gradient(multipliers, g, h, return_primal=False, ball=None):
    """Minimize negative dual: six half-error constraints plus half unit ball."""
    lam, mu = multipliers[:-1], multipliers[-1]
    ball = np.eye(h.shape[-1]) if ball is None else ball
    a = h[0]+np.einsum('k,kij->ij', lam, h[1:])+mu*ball
    b = g[0]+np.einsum('k,ki->i', lam, g[1:])
    z = -cho_solve(cho_factor(a, lower=True, check_finite=True), b, check_finite=True)
    constraints = np.einsum('ki,i->k', g[1:], z)+.5*np.einsum('i,kij,j->k', z, h[1:], z)
    dual = .5*float(np.dot(b, z))-.5*mu
    gradient = -np.r_[constraints, .5*(np.einsum('i,ij,j', z, ball, z)-1)]
    if not np.isfinite(np.r_[z, dual, gradient]).all():
        raise ValueError('nonfinite dual return')
    return (float(-dual), gradient, z, a, b) if return_primal else (float(-dual), gradient)


def solve_full(g, h):
    """One bounded full-dimensional convex-dual optimisation, no head training."""
    g, h = np.asarray(g), np.asarray(h)
    if g.ndim != 2 or g.shape[0] != 7 or h.shape != (7, g.shape[1], g.shape[1]):
        raise ValueError('full-head seven-proxy schema')
    if not np.isfinite(g).all() or not np.isfinite(h).all():
        raise ValueError('nonfinite full-head proxy')
    spectra = np.linalg.eigvalsh(h)
    if np.any(spectra[:, 0] < -1e-10*np.maximum(1., spectra[:, -1])):
        raise ValueError('non-PSD Gram')
    values, vectors = np.linalg.eigh(h[0])
    if values[-1] <= 0:
        raise ValueError('zero full-head UV curvature')
    floor = values[-1]*1e-8
    transform = vectors/np.sqrt(np.maximum(values, floor))[None, :]
    # All coordinates retained; this is an invertible change of variables only.
    gt = dgemm(1., np.asarray(g, order='F'), np.asarray(transform, order='F'))
    ht = np.stack([dgemm(1., transform, dgemm(1., matrix, transform), trans_a=True) for matrix in h])
    ball = gram(transform)
    # Ball-only secular multiplier supplies the dual coordinate scale and a
    # declared UV-only relaxation bound, not an actual admitted field candidate.
    projected = np.einsum('ij,i->j', vectors, g[0])
    lower_mu = max(1e-12, -values[0]+64*np.finfo(float).eps*max(1., values[-1]))
    def secular(mu):
        return float(np.linalg.norm(projected/(values+mu)))-1.
    if secular(lower_mu)>0:
        upper_mu = max(float(np.linalg.norm(g[0]))*2, lower_mu*2)
        if secular(upper_mu)>0:
            raise ValueError('UV ball secular bracket')
        mu_start = brentq(secular, lower_mu, upper_mu, xtol=1e-24, rtol=1e-12, maxiter=250)
    else:
        mu_start = lower_mu
    mu_scale = mu_start
    start = np.r_[np.zeros(6), 1.]
    trace = []
    def objective(x):
        multipliers = x*np.r_[np.ones(6), mu_scale]
        val, grad = dual_value_gradient(multipliers, gt, ht, ball=ball)
        trace.append(dict(dual_lower_bound=-val, multipliers=multipliers.tolist(), gradient=grad.tolist()))
        return val, grad*np.r_[np.ones(6), mu_scale]
    result = minimize(objective, start, method='L-BFGS-B', jac=True,
                      bounds=[(0., None)]*6+[(1e-12/mu_scale, None)],
                      options=dict(maxiter=400, maxfun=2000, maxls=40, ftol=1e-14, gtol=1e-9))
    multipliers = result.x*np.r_[np.ones(6), mu_scale]
    val, grad, inner, _, _ = dual_value_gradient(multipliers, gt, ht, True, ball)
    raw = np.einsum('ij,j->i', transform, inner)
    a = h[0]+np.einsum('k,kij->ij', multipliers[:-1], h[1:])+multipliers[-1]*np.eye(g.shape[1])
    b = g[0]+np.einsum('k,ki->i', multipliers[:-1], g[1:])
    raw_norm = np.linalg.norm(raw)
    # Prospective norm-only repair, no new direction or extra solve; actual checks stay strict.
    z = raw*min(1., (1-1e-12)/raw_norm) if raw_norm>0 else raw.copy()
    half_changes = np.einsum('ki,i->k', g, z)+.5*np.einsum('i,kij,j->k', z, h, z)
    primal = float(half_changes[0]); lower = -val
    gap = primal-lower
    stationarity = float(np.linalg.norm(np.einsum('ij,j->i', a, raw)+b)/max(np.linalg.norm(b), 1e-300))
    feasible = bool(half_changes.max() <= 1e-8 and np.linalg.norm(z) <= 1+1e-12)
    sufficient = bool(feasible and gap >= -1e-9 and gap <= 1e-6 and stationarity<=1e-8)
    return z, raw, dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),
                       function_evaluations=int(result.nfev),feasible=feasible,numerically_resolved=sufficient,
                       primal_half_relative_change=primal,dual_lower_bound=lower,primal_dual_gap=gap,
                       half_proxy_changes=half_changes.tolist(),raw_ball=float(np.dot(raw, raw)),
                       candidate_ball=float(np.dot(z, z)),multipliers=multipliers.tolist(),
                       dual_mu_coordinate_scale=float(mu_scale),
                       UV_only_relaxation_half_dual=float(-.5*np.sum(projected**2/(values+mu_start))-.5*mu_start),
                       linear_solve_stationarity_relative=stationarity,
                       hessian_spectra_extremes=spectra[:, [0,-1]].tolist(),
                       full_uv_rank_relative_1e12=int(np.sum(values>values[-1]*1e-12)),
                       preconditioner_floor=float(floor),all_coordinates_retained=True,
                       mu_search_floor=1e-12,domain='original untruncated head coordinates',
                       scope='convex tangent/GN proxy certificate, not true nonlinear attainable ceiling'),trace
