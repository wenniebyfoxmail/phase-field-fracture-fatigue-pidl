"""Small active-set linear geometry; no model parameters or optimizer steps."""
from itertools import combinations
import numpy as np
from scipy.linalg import lstsq


def unit_rows(a):
    a = np.asarray(a, dtype=np.float64)
    if a.ndim != 2 or not np.isfinite(a).all():
        raise ValueError('finite row matrix required')
    norms = np.linalg.norm(a, axis=1)
    return np.divide(a, norms[:, None], out=np.zeros_like(a), where=norms[:, None] > 0), norms


def cone_projection(g, normals):
    """Project -g onto {v: normals@v<=0}; enumerate at most four normals."""
    g = np.asarray(g, dtype=np.float64)
    a, norms = unit_rows(normals)
    if g.ndim != 1 or a.shape[1] != len(g) or not np.isfinite(g).all() or not 1 <= len(a) <= 4:
        raise ValueError('cone schema')
    ng = np.linalg.norm(g)
    if not np.isfinite(ng) or ng == 0:
        raise ValueError('nonzero finite objective gradient required')
    b = -g
    candidates = []
    tol = 1e-10 * ng
    for count in range(len(a) + 1):
        for active in combinations(range(len(a)), count):
            multipliers = np.zeros(len(a))
            if active:
                lam = lstsq(a[list(active)].T, b, cond=1e-12, lapack_driver='gelsd')[0]
                multipliers[list(active)] = lam
            p = b - np.einsum('i,ij->j', multipliers, a)
            slopes = np.einsum('ij,j->i', a, p)
            if multipliers.min() < -tol or slopes.max() > tol:
                continue
            if active and np.max(abs(slopes[list(active)])) > tol:
                continue
            candidates.append((float(np.linalg.norm(p - b)), active, p, multipliers))
    if not candidates:
        raise ValueError('no numerically admissible cone projection')
    _, active, p, lam = min(candidates, key=lambda r: r[0])
    pn = float(np.linalg.norm(p))
    direction = p / pn if pn / ng > 1e-8 else np.zeros_like(p)
    stationarity = p + g + np.einsum('i,ij->j', lam, a)
    info = dict(active=list(active), projected_norm=pn, objective_gradient_norm=float(ng),
                retained_descent_fraction=pn / ng, resolved_nonzero=bool(pn / ng > 1e-8),
                multipliers_unit_normals=lam.tolist(), normal_norms=norms.tolist(),
                projected_guard_max_relative=float(np.max(a @ p) / ng),
                kkt_stationarity_relative=float(np.linalg.norm(stationarity) / ng),
                complementarity_relative=float(np.max(abs(lam * (a @ p))) / ng**2),
                moreau_relative=float(abs(np.dot(g, p) + pn**2) / ng**2))
    if max(info['kkt_stationarity_relative'], info['complementarity_relative'], info['moreau_relative']) > 1e-8:
        raise ValueError('cone numerical KKT failed')
    return direction, p, info


def common_descent(gradients):
    """Min-norm convex hull of <=5 unit gradients; nonzero q gives common descent."""
    a, norms = unit_rows(gradients)
    if not 1 <= len(a) <= 5 or np.any(norms == 0):
        raise ValueError('common descent requires 1..5 nonzero gradients')
    candidates = []
    for count in range(1, len(a) + 1):
        for active in combinations(range(len(a)), count):
            sub = a[list(active)]
            if count == 1:
                weights = np.ones(1)
            else:
                beta = lstsq((sub[1:] - sub[0]).T, -sub[0], cond=1e-12, lapack_driver='gelsd')[0]
                weights = np.r_[1 - beta.sum(), beta]
            if weights.min() < -1e-10:
                continue
            q = np.einsum('i,ij->j', weights, sub)
            q2 = float(np.dot(q, q))
            gaps = a @ q - q2
            if gaps.min() < -1e-10 or np.max(abs(gaps[list(active)])) > 1e-10:
                continue
            full = np.zeros(len(a)); full[list(active)] = weights
            candidates.append((q2, q, full, active, gaps))
    if not candidates:
        raise ValueError('convex hull certificate not resolved')
    q2, q, weights, active, gaps = min(candidates, key=lambda r: r[0])
    margin = float(np.sqrt(q2))
    direction = -q / margin if margin > 1e-8 else np.zeros_like(q)
    return direction, q, dict(unit_gradient_margin=margin, resolved_strict=bool(margin > 1e-8),
                             weights=weights.tolist(), active=list(active), normal_norms=norms.tolist(),
                             simplex_sum=float(weights.sum()), min_weight=float(weights.min()),
                             certificate_min_gap=float(gaps.min()),
                             largest_unit_slope=float(np.max(a @ direction)))


def strain_adjoint(mechanics, stress):
    """Native Q4 integral B^T stress; engineering gamma uses shear stress."""
    if stress.shape != (len(mechanics.conn), 4, 3) or not np.isfinite(stress).all():
        raise ValueError('GP stress schema')
    result = np.zeros((mechanics.n, 2))
    for j, (grad, det, _) in enumerate(mechanics.geo):
        sx, sy, ss = stress[:, j].T
        local = np.stack([grad[:, 0] * sx[:, None] + grad[:, 1] * ss[:, None],
                          grad[:, 1] * sy[:, None] + grad[:, 0] * ss[:, None]], axis=2)
        np.add.at(result, mechanics.conn.ravel(), (local * det[:, None, None]).reshape(-1, 2))
    return result


def elastic_driver(mechanics, uv, gp_damage):
    eps = mechanics.strains(uv)
    ex, ey, gamma = np.moveaxis(eps, -1, 0)
    trace = ex + ey
    mu, bulk = 1 / 2.6, 1 / 1.2
    psi = mu * (ex**2 + ey**2 - trace**2 / 3 + gamma**2 / 2) + .5 * bulk * np.maximum(trace, 0)**2
    sigma_plus = np.stack([2 * mu * (ex - trace / 3) + bulk * np.maximum(trace, 0),
                           2 * mu * (ey - trace / 3) + bulk * np.maximum(trace, 0), mu * gamma], axis=-1)
    return 2 * (1 - gp_damage) * psi, 2 * (1 - gp_damage)[..., None] * sigma_plus
