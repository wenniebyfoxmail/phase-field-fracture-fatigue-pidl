"""D011: exact-UV-curvature coordinates for a fixed three-head convex proxy."""
import numpy as np
from scipy.optimize import minimize


def quadratic_terms(error, columns, weights):
    """Return origin error² and relative half-error gradient/Hessian.

    Squared error ratio = 1 + 2*g.z + z.H.z. Columns include the fixed R.
    """
    e, v, w = (np.asarray(x, dtype=np.float64) for x in (error, columns, weights))
    if v.shape != (3,) + e.shape or w.shape != e.shape:
        raise ValueError('three-column quadratic schema')
    if not all(np.isfinite(x).all() for x in (e, v, w)) or np.any(w < 0):
        raise ValueError('nonfinite/negative quadratic input')
    e, v, w = e.ravel(), v.reshape(3, -1), w.ravel()
    c = float(np.einsum('n,n,n->', w, e, e))
    if not np.isfinite(c) or c <= 0:
        raise ValueError('positive original squared error required')
    g = np.einsum('n,n,in->i', w, e, v) / c
    h = np.einsum('n,in,jn->ij', w, v, v) / c
    if not np.isfinite(g).all() or not np.isfinite(h).all():
        raise ValueError('quadratic overflow')
    return c, g, h


def solve_joint(gradients, hessians):
    """One deterministic convex 3D QCQP from zero, seven no-increase proxies.

    Change of inner coordinates only; original z-ball and all Hessians retained.
    No new head axis, physical D calibration, training, or true-field admission.
    """
    g, h = np.asarray(gradients), np.asarray(hessians)
    if g.shape != (7, 3) or h.shape != (7, 3, 3):
        raise ValueError('seven fixed three-coordinate proxies required')
    if not np.isfinite(g).all() or not np.isfinite(h).all():
        raise ValueError('nonfinite proxy')
    for matrix in h:
        if not np.allclose(matrix, matrix.T, rtol=0, atol=1e-12*max(1., abs(matrix).max())):
            raise ValueError('asymmetric Hessian')
        eig = np.linalg.eigvalsh(matrix)
        if eig[0] < -1e-12*max(1., eig[-1]):
            raise ValueError('nonconvex proxy')
    eigenvalues, eigenvectors = np.linalg.eigh(h[0])
    if eigenvalues[0] <= 0:
        raise ValueError('full UV curvature not positive definite')
    floor = eigenvalues[-1]*1e-12  # preconditioner only; NOT a truncated objective
    transform = eigenvectors / np.sqrt(np.maximum(eigenvalues, floor))[None, :]
    gt = np.einsum('ki,ij->kj', g, transform)
    ht = np.einsum('ia,kij,jb->kab', transform, h, transform)
    ball = np.einsum('ia,ib->ab', transform, transform)
    scales = np.maximum(1., np.maximum(abs(gt).max(1), abs(ht).max((1, 2))))
    ball_scale = max(1., float(abs(ball).max()))

    def values(y):
        return 2*np.einsum('ki,i->k', gt, y)+np.einsum('i,kij,j->k', y, ht, y)

    constraints = [dict(type='ineq', fun=lambda y: -values(y)/scales,
                        jac=lambda y: -(2*gt+2*np.einsum('kij,j->ki', ht, y))/scales[:, None]),
                   dict(type='ineq', fun=lambda y: (1-np.einsum('i,ij,j', y, ball, y))/ball_scale,
                        jac=lambda y: -2*np.einsum('ij,j->i', ball, y)/ball_scale)]
    result = minimize(lambda y: float(np.dot(gt[0], y)+.5*np.einsum('i,ij,j', y, ht[0], y)),
                      np.zeros(3), jac=lambda y: gt[0]+np.einsum('ij,j->i', ht[0], y),
                      method='SLSQP', constraints=constraints,
                      options=dict(maxiter=200, ftol=1e-12))
    z = np.einsum('ij,j->i', transform, result.x)
    changes = 2*np.einsum('ki,i->k', g, z)+np.einsum('i,kij,j->k', z, h, z)
    finite = bool(np.isfinite(z).all() and np.isfinite(changes).all())
    if not finite:
        raise ValueError('nonfinite solver return; not a backtracking candidate')
    feasible = bool(finite and np.dot(z, z) <= 1+1e-9 and changes.max() <= 1e-9)
    return z, dict(success=bool(result.success), feasible=feasible, message=str(result.message),
                   iterations=int(result.nit), objective_half_relative_change=float(changes[0]/2),
                   proxy_squared_relative_changes=changes.tolist(), ball=float(np.dot(z, z)),
                   full_uv_eigenvalues=eigenvalues.tolist(), full_uv_condition=float(eigenvalues[-1]/eigenvalues[0]),
                   numerical_rank_relative_1e12=int(np.sum(eigenvalues>floor)),
                   preconditioner_floor=float(floor), coordinate_transform=transform.tolist(),
                   constraint_scales=scales.tolist(), ball_scale=ball_scale,
                   scope='convex proxy only; actual seven nonlinear/UV checks remain authoritative')
