"""Explicit sparse consistent-Jacobian/regularity provider; no primal driver.

Invocation requires caller-supplied resource limits and scaling. This module
does not run at import, read physical arrays, change the primal solver, retry,
or fall back to a dense inverse. Sparse LU cannot be interrupted internally;
any later native invocation requires an external process/memory watchdog.
"""
from dataclasses import dataclass
import hashlib
from time import monotonic

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu

from damage_conditioned_equilibrium import plane_strain_tensors
from hybrid_history import frozen_array
from q4_inverse_derivatives import RegularityEvidence, _array


class SparsePreparationFailure(RuntimeError):
    def __init__(self, stage, reason, evidence=None):
        super().__init__(f"{stage}: {reason}")
        self.stage, self.reason = stage, reason
        self.evidence = {} if evidence is None else dict(evidence)


@dataclass(frozen=True)
class SparseLimits:
    max_unknowns: int
    max_elements: int
    max_matrix_nnz: int
    max_factor_nnz: int
    max_product_work: int
    chunk_elements: int
    wall_seconds: float

    def __post_init__(self):
        for name, value in vars(self).items():
            if name == "wall_seconds":
                if not np.isfinite(value) or value <= 0:
                    raise ValueError("positive finite wall limit required")
            elif type(value) is not int or value <= 0:
                raise ValueError(f"positive integer {name} required")


def _check_time(started, limits, stage):
    if monotonic()-started > limits.wall_seconds:
        raise SparsePreparationFailure(stage, "wall budget exhausted")


def assemble_consistent_sparse(step, limits, *, started=None):
    """Assemble reduced J directly from 12x12 element blocks in chunks.

    Includes trial-f derivatives in Kdu/Kdd. It never probes every global basis
    vector or calls a primal solve. The supplied step already enforces the
    stable classical branch and KKT contract.
    """
    started = monotonic() if started is None else started
    r, m = step.r, step.r.material
    if not 0 < step.size <= limits.max_unknowns or r.e > limits.max_elements:
        raise SparsePreparationFailure("assembly", "declared dimension budget exceeded")
    p = r.evaluate(step.u, step.d)
    zero = r.zero_variation()
    r.directional(step.u, step.d, zero.displacement, zero.damage, margins=step.margins)
    reduced = np.full(3*r.n, -1, dtype=np.int64)
    reduced[step.free_u] = np.arange(len(step.free_u))
    reduced[2*r.n+step.interior] = len(step.free_u)+np.arange(len(step.interior))
    C, vol, dev, bulk, shear = plane_strain_tensors(m.youngs_modulus, m.poisson_ratio)
    result = sparse.csr_matrix((step.size, step.size))
    for start in range(0, r.e, limits.chunk_elements):
        _check_time(started, limits, "assembly")
        stop = min(start+limits.chunk_elements, r.e)
        B = r.B[start:stop]
        local_u = step.u[r.dofs[start:stop]]
        local_d = step.d[r.cells[start:stop]]
        eps = np.einsum("egai,ei->ega", B, local_u)
        grad_d = np.einsum("egai,ei->ega", r.grad[start:stop], local_d)
        local = np.zeros((stop-start, 12, 12))
        for gp in range(4):
            N = r.shape[gp]
            b = B[:, gp]
            tr = eps[:, gp, 0]+eps[:, gp, 1]
            cp = np.where((tr > 0)[:, None, None], C, 2*shear*dev)
            cm = np.where((tr > 0)[:, None, None], 0., bulk*vol)
            sp = np.einsum("eab,eb->ea", cp, eps[:, gp])
            v = np.einsum("eai,ea->ei", b, sp)
            dg = local_d @ N
            g = (1-dg)**2
            psi = p.raw[start:stop, gp]
            f = p.fatigue[start:stop, gp]
            A = p.accumulated[start:stop, gp]
            increasing = p.driver[start:stop, gp] > r.old.driver[start:stop, gp]
            fA = np.where(A > m.alpha_t, -m.power*f/(A+m.alpha_t), 0.)
            dfdu = (fA*increasing*g)[:, None]*v
            dfdd = (fA*increasing*(-2*(1-dg)*psi))[:, None]*N
            grad = r.grad[start:stop, gp]
            fracture = N[None, :]/m.length_scale+2*m.length_scale*np.einsum("eai,ea->ei", grad, grad_d[:, gp])
            kuu = np.einsum("eai,eab,ebj->eij", b, g[:, None, None]*cp+cm, b)
            kud = (-2*(1-dg))[:, None, None]*v[:, :, None]*N[None, None, :]
            kdu = 2*(dg-1)[:, None, None]*N[None, :, None]*v[:, None, :]
            kdu += m.gc/(8/3)*fracture[:, :, None]*dfdu[:, None, :]
            kdd = 2*psi[:, None, None]*N[None, :, None]*N[None, None, :]
            kdd += (2*m.gc*m.length_scale*f/(8/3))[:, None, None]*np.einsum("eai,eaj->eij", grad, grad)
            kdd += m.gc/(8/3)*fracture[:, :, None]*dfdd[:, None, :]
            w = r.weights[start:stop, gp, None, None]
            local[:, :8, :8] += w*kuu
            local[:, :8, 8:] += w*kud
            local[:, 8:, :8] += w*kdu
            local[:, 8:, 8:] += w*kdd
        indices = reduced[np.c_[r.dofs[start:stop], 2*r.n+r.cells[start:stop]]]
        row = np.repeat(indices, 12, axis=1).ravel()
        col = np.tile(indices, (1, 12)).ravel()
        keep = (row >= 0) & (col >= 0)
        data = local.ravel()[keep]
        if not np.isfinite(data).all():
            raise SparsePreparationFailure("assembly", "nonfinite element Jacobian")
        piece = sparse.coo_matrix((data, (row[keep], col[keep])), shape=result.shape).tocsr()
        result = result+piece
        result.eliminate_zeros()
        if result.nnz > limits.max_matrix_nnz:
            raise SparsePreparationFailure("assembly", "matrix nnz budget exceeded")
    return result.tocsc()


def _up(x):
    return np.nextafter(float(x), np.inf)


def _gamma(n):
    # Classical positive-sum/product rounding allowance; fail closed if invalid.
    u = np.finfo(float).eps
    if n*u >= .25:
        raise SparsePreparationFailure("bound", "rounding allowance not usable")
    return _up(n*u/(1-n*u))


def _norm_upper(a, axis):
    totals = np.asarray(abs(a).sum(axis=axis)).ravel()
    return _up(np.max(totals, initial=0.)*(1+_gamma(max(a.shape)+2)))


def _comparison_inverse_inf(t, lower, started, limits):
    """Upper bound on ||T^-1||inf by positive triangular comparison solves.

    Monotone arithmetic is inflated upwards at products/sums/divisions. This
    is conservative floating-point numerical evidence, not a theorem prover
    or an interval-arithmetic certification of a native factorization.
    """
    t = t.tocsr(); n = t.shape[0]
    y = np.empty(n)
    for i in (range(n) if lower else range(n-1, -1, -1)):
        if i % 256 == 0:
            _check_time(started, limits, "comparison_bound")
        sl = slice(t.indptr[i], t.indptr[i+1])
        js, values = t.indices[sl], abs(t.data[sl])
        diagonal = values[js == i]
        off = js < i if lower else js > i
        if (len(diagonal) != 1 or diagonal[0] <= 0
                or np.any(values[~off & (js != i)] != 0)):
            raise SparsePreparationFailure("comparison_bound", "invalid triangular factor")
        terms = np.nextafter(values[off]*y[js[off]], np.inf)
        summed = _up(np.sum(terms)*(1+_gamma(len(terms)+2)))
        y[i] = _up(_up(1+summed)/diagonal[0])
        if not np.isfinite(y[i]):
            raise SparsePreparationFailure("comparison_bound", "inverse bound overflow")
    return _up(np.max(y, initial=0.))


class SparseSensitivityProvider:
    """Sparse LU solution and exact-operator-bound conservative regularity.

    Constructor performs no primal work, but DOES perform tangent assembly and
    LU when explicitly invoked. This has only been exercised on unit arrays.
    Native factorization requires separately authorized measured resource work.
    """
    def __init__(self, step, *, row_scale, column_scale, limits: SparseLimits):
        started = monotonic(); self.operator = step.operator
        self.rows = frozen_array(_array(row_scale, (step.size,), "row scales"))
        self.cols = frozen_array(_array(column_scale, (step.size,), "column scales"))
        if np.any(self.rows <= 0) or np.any(self.cols <= 0):
            raise ValueError("positive prospective physical scaling required")
        self.matrix = assemble_consistent_sparse(step, limits, started=started)
        a = (sparse.diags(1/self.rows) @ self.matrix @ sparse.diags(self.cols)).tocsc()
        if not np.isfinite(a.data).all():
            raise SparsePreparationFailure("scaling", "nonfinite scaled matrix")
        _check_time(started, limits, "before_lu")
        try:
            lu = splu(a)
        except (RuntimeError, ValueError) as exc:
            raise SparsePreparationFailure("factorization", str(exc)) from exc
        _check_time(started, limits, "after_lu")
        if lu.L.nnz+lu.U.nnz > limits.max_factor_nnz:
            raise SparsePreparationFailure("factorization", "factor nnz budget exceeded")
        # Bound fill work BEFORE explicitly forming L@U for residual evidence.
        lcounts = np.diff(lu.L.tocsc().indptr)
        ucounts = np.diff(lu.U.tocsr().indptr)
        work = sum(int(x)*int(y) for x, y in zip(lcounts, ucounts))
        if work > limits.max_product_work:
            raise SparsePreparationFailure("factor_residual", "LU product work budget exceeded")
        permuted = a[np.argsort(lu.perm_r)][:, np.argsort(lu.perm_c)]
        difference = permuted-lu.L @ lu.U
        _check_time(started, limits, "factor_residual")
        a1, ai = _norm_upper(a, 0), _norm_upper(a, 1)
        # Account for roundoff in stored sparse product/subtraction and sums.
        e1 = _up(_norm_upper(difference, 0)+_gamma(step.size+2)*(_norm_upper(lu.L, 0)*_norm_upper(lu.U, 0)+a1))
        ei = _up(_norm_upper(difference, 1)+_gamma(step.size+2)*(_norm_upper(lu.L, 1)*_norm_upper(lu.U, 1)+ai))
        li = _comparison_inverse_inf(lu.L, True, started, limits)
        ui = _comparison_inverse_inf(lu.U, False, started, limits)
        l1 = _comparison_inverse_inf(lu.L.T, False, started, limits)
        u1 = _comparison_inverse_inf(lu.U.T, True, started, limits)
        bi, b1 = _up(li*ui), _up(l1*u1)
        beta_i, beta_1 = _up(bi*ei), _up(b1*e1)
        if not np.isfinite([bi, b1, beta_i, beta_1]).all() or max(beta_i, beta_1) >= 1:
            raise SparsePreparationFailure("regularity", "factor-error/inverse bound not conclusive")
        inverse_i = _up(bi/np.nextafter(1-beta_i, -np.inf))
        inverse_1 = _up(b1/np.nextafter(1-beta_1, -np.inf))
        sigma_min = np.nextafter(1/np.sqrt(_up(inverse_i*inverse_1)), 0.)
        sigma_max = _up(np.sqrt(_up(a1*ai)))
        if not np.isfinite([sigma_min, sigma_max]).all() or sigma_min <= 0:
            raise SparsePreparationFailure("regularity", "invalid conservative bounds")
        self.evidence = RegularityEvidence(step.operator, self.rows, self.cols,
                float(sigma_min), sigma_max, "sparse_lu_comparison_inverse_bound")
        self._factor = lu
        digest = hashlib.sha256()
        for x in (self.matrix.data, self.matrix.indices, self.matrix.indptr, self.rows, self.cols):
            digest.update(np.ascontiguousarray(x).tobytes())
        self.record = dict(method=self.evidence.method, operator_digest=digest.hexdigest(),
            unknowns=step.size, nnz=self.matrix.nnz, factor_nnz=lu.L.nnz+lu.U.nnz,
            product_work_bound=work, inverse_1_upper=inverse_1, inverse_inf_upper=inverse_i,
            factor_residual_1_upper=e1, factor_residual_inf_upper=ei,
            scaled_sigma_min_lower=float(sigma_min), scaled_sigma_max_upper=sigma_max,
            elapsed_seconds=monotonic()-started, limits=vars(limits),
            arithmetic="conservative float64 padding, not interval proof",
            native_size_execution_verified=False)
        for x in (self.matrix.data, self.matrix.indices, self.matrix.indptr):
            x.flags.writeable = False

    def __call__(self, operator, rhs):
        if operator is not self.operator:
            raise ValueError("provider belongs to a different exact operator")
        rhs = _array(rhs, (operator.shape[0],), "tangent RHS")
        value = self.cols*self._factor.solve(rhs/self.rows)
        if not np.isfinite(value).all():
            raise SparsePreparationFailure("linear_solve", "nonfinite tangent solution")
        return value
