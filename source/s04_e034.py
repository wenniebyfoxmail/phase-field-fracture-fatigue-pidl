"""E034 finite raw comparison. Import-safe; callers supply all IO and physics.

The F8 and F802 solvers share actual finite metrics, frozen cone denominators,
cache/accounting, first-target termination and exact-zero fallback semantics.
"""
import time
import numpy as np
import torch
from scipy.optimize import minimize
import s04_e033 as parent

PROTOCOL = 'S04-E034/v1-finite-raw-reaction-F8-F802-20261019'
METRICS = parent.METRICS + ('top_error_squared', 'bottom_error_squared')
KAPPA = .04418604213300339
RADIUS = .039821608331992005
REACTION_REF = (.07200967241856504, -.07200967241856562)
REACTION_ZERO = (.0731321809384512, -.08084317325301768)
REACTION_SCALE = tuple(abs(a-b) for a, b in zip(REACTION_ZERO, REACTION_REF))


def finite(a, name):
    if not np.isfinite(a).all():
        raise ValueError('nonfinite ' + name)
    return a


class Geometry:
    def __init__(self, basis, gradients, radius=RADIUS):
        self.basis = finite(np.asarray(basis, dtype=np.float64).reshape(8, 802), 'B8')
        g = finite(np.asarray(gradients, dtype=np.float64), 'saved gradients')
        if g.shape != (11, 802) or radius != RADIUS:
            raise ValueError('frozen geometry schema/radius')
        if not np.allclose(np.einsum('ij,kj->ik', self.basis, self.basis), np.eye(8), atol=1e-12, rtol=0):
            raise ValueError('B8 orthonormality')
        rg = radius*g
        denominators = np.linalg.norm(np.einsum('ij,kj->ik', rg, self.basis), axis=1)
        if np.any(denominators <= 0):
            raise ValueError('positive frozen8 cone denominators required')
        self.cone = rg/denominators[:, None]

    def matrix(self, arm):
        if arm == 'F8':
            return self.basis
        if arm == 'F802':
            return np.eye(802)
        raise ValueError('two fixed arms only')

    def constraints(self, x, arm):
        matrix = self.matrix(arm)
        h = np.einsum('i,ij->j', x, matrix)
        norm = float(np.linalg.norm(h))
        cone = -np.einsum('ij,j->i', self.cone, h)-KAPPA*norm
        radial = h/norm if norm else np.zeros(802)
        jac = -np.einsum('ij,kj->ik', self.cone+KAPPA*radial[None, :], matrix)
        return np.r_[1-norm*norm, cone], np.vstack((-2*x, jac))

    def decompose(self, h):
        z = np.einsum('ij,j->i', self.basis, h)
        projected = np.einsum('i,ij->j', z, self.basis)
        outside = h-projected
        return z, dict(outside_norm=float(np.linalg.norm(outside)),
                       outside_fraction=float(np.linalg.norm(outside)/np.linalg.norm(h)) if np.linalg.norm(h) else 0.,
                       reconstruction_max_abs=float(abs(outside).max()))


def actual_constraints(ratios):
    """Thirteen nonincrease inequalities plus a strict resolved UV decrease.

    The strict comparison is enforced at acceptance; SLSQP uses its closure.
    """
    # Zero is feasible for the search's closed nonincrease constraints. Resolved
    # strict UV descent, like the raw target, is a first-target acceptance test.
    return 1-ratios


def meets_target(ratios, geometric):
    finite(ratios, 'ratios'); finite(geometric, 'geometry')
    return bool(np.all(ratios >= 0) and np.all(ratios <= 1) and
                ratios[0] < (1-1e-8)**2 and ratios[2] <= .998001 and
                np.min(geometric) >= 0)


class TargetReached(Exception):
    pass


class PointCache:
    """One exact physical/Jacobian evaluation per distinct coefficient vector.

    No rounded keys. The 120th point is allowed; a 121st request is a hard stop.
    Observations are persisted before finite/acceptance assertions.
    """
    def __init__(self, arm, geometry, evaluate, verify, observe, guard, cap=120):
        self.arm, self.geometry = arm, geometry
        self.evaluate, self.verify, self.observe, self.guard = evaluate, verify, observe, guard
        self.cap, self.rows, self.cache = cap, [], {}
        self.calls = dict(objective=0, constraints=0, objective_jac=0, constraint_jac=0,
                          physical=0, physical_jac=0, actual_forward=0)
        self.winner = None

    def point(self, x):
        self.guard()
        x = finite(np.asarray(x, dtype=np.float64), 'coefficient').copy()
        expected = 8 if self.arm == 'F8' else 802
        if x.shape != (expected,):
            raise ValueError('arm coordinates')
        key = x.tobytes()
        if key in self.cache:
            return self.cache[key]
        if len(self.rows) >= self.cap:
            raise RuntimeError('distinct physical evaluation cap; no retry')
        # Count work on entry, including any evaluation that raises.
        self.calls['physical'] += 1
        self.calls['physical_jac'] += 1
        self.observe(dict(event='physical_evaluation_started', index=len(self.rows)+1,
                          x=x.tolist(), calls=self.calls.copy()))
        ratios, jac, extra = self.evaluate(x)
        ratios, jac = np.asarray(ratios), np.asarray(jac)
        geometric, gjac = self.geometry.constraints(x, self.arm)
        row = dict(index=len(self.rows)+1, x=x.tolist(), ratios=ratios.tolist(),
                   geometric=geometric.tolist(), extra=extra, calls=self.calls.copy())
        self.rows.append(row); self.observe(row)
        finite(ratios, 'actual metrics'); finite(jac, 'actual metric Jacobians')
        if ratios.shape != (13,) or jac.shape != (13, expected) or np.any(ratios < 0):
            raise ValueError('thirteen actual metric/Jacobian schema')
        constraint = np.r_[actual_constraints(ratios), geometric]
        cjac = np.vstack((-jac, gjac))
        result = (ratios, jac, constraint, cjac)
        self.cache[key] = result
        if meets_target(ratios, geometric):
            self.calls['actual_forward'] += 1
            self.verify(x, ratios)
            self.guard()
            self.winner = x.copy()
            raise TargetReached()
        return result

    def fun(self, x):
        self.calls['objective'] += 1
        return float(self.point(x)[0][2])

    def jac(self, x):
        self.calls['objective_jac'] += 1
        return self.point(x)[1][2]

    def con(self, x):
        self.calls['constraints'] += 1
        return self.point(x)[2]

    def conjac(self, x):
        self.calls['constraint_jac'] += 1
        return self.point(x)[3]


def solve_arm(cache, milestone=lambda iteration, x: None):
    """One deterministic zero-start SLSQP; no retries or alternate selection."""
    started = time.monotonic()
    n = 8 if cache.arm == 'F8' else 802
    iterations = []
    def callback(x):
        cache.guard()
        # Callback must reuse an evaluated point; it cannot hide extra work.
        key = np.asarray(x, dtype=np.float64).tobytes()
        if key not in cache.cache:
            cache.point(x)
        iterations.append(dict(iteration=len(iterations)+1, x=x.tolist()))
        if len(iterations) in (15, 30, 60):
            milestone(len(iterations), x.copy())
    try:
        result = minimize(cache.fun, np.zeros(n), jac=cache.jac, method='SLSQP',
                          constraints=[dict(type='ineq', fun=cache.con, jac=cache.conjac)],
                          callback=callback, options=dict(maxiter=60, ftol=1e-12))
        cache.guard()
        finite(result.x, 'solver endpoint')
        if result.status not in (0, 9):
            raise RuntimeError('unexpected SLSQP status '+str(result.status)+': '+str(result.message))
        status, message = int(result.status), str(result.message)
        accepted = False
    except TargetReached:
        status, message, accepted = 'first_actual_target', 'first verified actual target; arm terminated', True
    endpoint = cache.winner if accepted else np.zeros(n)
    return endpoint, dict(arm=cache.arm, accepted=accepted, status=status, message=message,
                          elapsed_seconds=time.monotonic()-started, iterations=iterations,
                          major_iterations=len(iterations), distinct_points=len(cache.rows), calls=cache.calls,
                          missing_milestones=[i for i in (15, 30, 60) if i > len(iterations)],
                          endpoint='first_verified_target' if accepted else 'exact_cached_E032')


def physical_values(problem, q, reference, force_norm):
    """Actual native Q4 eleven values and separate boundary reaction errors.

    Retains higher-order force chain for exact derivatives in head coordinates.
    """
    metrics = parent.metric_values(problem, q, reference, force_norm, True)
    force = problem.force(q, create_graph=True)
    vertical = force[len(q):]
    reactions = (vertical[problem.xy[:, 1] == .5].sum(),
                 vertical[problem.xy[:, 1] == -.5].sum())
    for name, reaction, ref, scale in zip(METRICS[-2:], reactions, REACTION_REF, REACTION_SCALE):
        metrics[name] = ((reaction-ref)/scale).square()
    return torch.stack([metrics[k] for k in METRICS]), reactions


def values_and_jacobian(problem, theta0, features, damage, matrix, x, baseline, reference, force_norm):
    z = torch.as_tensor(x, dtype=torch.float64, device=theta0.device).clone().requires_grad_(True)
    theta = theta0+RADIUS*torch.einsum('i,ij->j', z, matrix).reshape(theta0.shape)
    q = parent.fields(theta, features, problem, damage)
    values, reactions = physical_values(problem, q, reference, force_norm)
    ratios = values/baseline
    jac = torch.stack([torch.autograd.grad(value, z, retain_graph=True)[0] for value in ratios])
    return ratios.detach().cpu().numpy(), jac.detach().cpu().numpy(), dict(
        values=values.detach().cpu().tolist(), reactions=[float(r.detach()) for r in reactions])
