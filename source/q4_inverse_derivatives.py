"""Derivative-only adapter for the frozen native Q4 AT1/Amor/Carrara model.

No FEM stepping, optimization, remote access, or writes occur in this module.
Residuals reuse the original kernels. Only E, Gc and alpha_T are differentiated;
nu, ell, p, thickness, mesh, initial crack and prescribed-DOF set are fixed.
The consistent Jacobian includes trial fatigue, unlike the Picard QP Hessian.
Hard switches have one-sided directional derivatives but no assumed linear
Jacobian. Implicit sensitivities require a regular, strictly stable branch.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Callable

import numpy as np
from scipy.sparse.linalg import LinearOperator

from damage_conditioned_equilibrium import (
    equilibrium_internal_force, plane_strain_tensors, tensile_energy,
)
from hybrid_damage import assemble_nodal_qp
from hybrid_history import AcceptedState, fatigue_factor, frozen_array, trial_history
from hybrid_kinematics import build_portable_native_q4_kinematics


class NonregularBranch(ValueError):
    """A switch or degenerate constraint prevents a classical linearization."""


@dataclass(frozen=True)
class Material:
    youngs_modulus: float = 1.
    poisson_ratio: float = .3
    gc: float = .01
    length_scale: float = .01
    alpha_t: float = .5
    power: float = 2.
    thickness: float = 1.

    def __post_init__(self):
        vals = np.array([self.youngs_modulus, self.poisson_ratio, self.gc,
                         self.length_scale, self.alpha_t, self.power, self.thickness])
        if (not np.isfinite(vals).all() or np.any(vals[[0, 2, 3, 4, 5, 6]] <= 0)
                or not -1 < self.poisson_ratio < .5):
            raise ValueError("invalid fixed-plane-strain material")

    def backend_kwargs(self):
        """Instantiate a NEW original NativeQ4Backend for every candidate.

        No backend is imported or constructed here. Its fresh material-dependent
        element tensors, LU cache, physics identity and initial state belong to
        the future explicitly authorized forward driver.
        """
        return dict(vars(self))


@dataclass(frozen=True)
class Margins:
    strain: float = 1.e-12
    energy: float = 1.e-12
    bound: float = 1.e-10
    multiplier: float = 1.e-10

    def __post_init__(self):
        if any(not np.isfinite(v) or v <= 0 for v in vars(self).values()):
            raise ValueError("strictly positive, finite branch margins required")


@dataclass(frozen=True)
class Variation:
    displacement: np.ndarray
    damage: np.ndarray
    accumulated: np.ndarray
    driver: np.ndarray


@dataclass(frozen=True)
class Fields:
    force: np.ndarray
    damage_residual: np.ndarray
    raw: np.ndarray
    accumulated: np.ndarray
    driver: np.ndarray
    fatigue: np.ndarray


def _array(value, shape, name):
    a = np.asarray(value, dtype=np.float64)
    if a.shape != shape or not np.isfinite(a).all():
        raise ValueError(f"{name} must be finite with shape {shape}")
    return a


class Q4Residual:
    """Evaluate/differentiate supplied fields; never find a new primal state.

    ``old`` must belong to the caller's declared material and history problem.
    Its fatigue consistency is checked, but this adapter cannot authenticate an
    external physics_id or confer convergence on imported snapshots.
    """
    def __init__(self, kinematics, material: Material, old: AcceptedState):
        reference = build_portable_native_q4_kinematics(kinematics.points, kinematics.cells)
        for name in ("shape_values", "b_matrices", "det_jacobians", "element_dofs",
                     "assembly_rows", "assembly_cols"):
            if not np.array_equal(getattr(kinematics, name), getattr(reference, name)):
                raise ValueError("geometry or native GP ordering mismatch")
        arrays = {}
        for field in fields(kinematics):
            a = np.ascontiguousarray(getattr(kinematics, field.name))
            arrays[field.name] = np.frombuffer(a.tobytes(), dtype=a.dtype).reshape(a.shape)
        self.kin = kinematics = replace(kinematics, **arrays)
        self.material, self.old = material, old
        self.n = len(kinematics.points)
        self.e = len(kinematics.cells)
        if old.damage.shape != (self.n,) or old.accumulated.shape != (self.e, 4):
            raise ValueError("old state is not on the given native Q4 mesh")
        if not np.allclose(old.fatigue, fatigue_factor(old.accumulated,
                              material.alpha_t, material.power), atol=1.e-14, rtol=0):
            raise ValueError("old fatigue/material mismatch; rebuild candidate history")
        # Own immutable copies so later caller mutations cannot alter an operator.
        self.shape = frozen_array(kinematics.shape_values)
        self.B = frozen_array(kinematics.b_matrices)
        self.weights = frozen_array(material.thickness * kinematics.det_jacobians)
        self.cells = np.array(kinematics.cells, dtype=np.int32, copy=True)
        self.dofs = np.array(kinematics.element_dofs, dtype=np.int32, copy=True)
        self.grad = np.stack((self.B[:, :, 0, 0::2], self.B[:, :, 1, 1::2]), axis=2)

    def zero_variation(self):
        return Variation(np.zeros(2*self.n), np.zeros(self.n),
                         np.zeros((self.e, 4)), np.zeros((self.e, 4)))

    def _fields(self, u, d):
        u = _array(u, (2*self.n,), "displacement")
        d = _array(d, (self.n,), "damage")
        if np.any(d < self.old.damage) or np.any(d > 1):
            raise ValueError("supplied damage violates nodal irreversibility/bounds")
        return u, d

    def evaluate(self, u, d):
        u, d = self._fields(u, d)
        m = self.material
        raw, _ = tensile_energy(self.kin, u, youngs_modulus=m.youngs_modulus,
                                poisson_ratio=m.poisson_ratio)
        dg = np.einsum("gi,ei->eg", self.shape, d[self.cells])
        h = trial_history(self.old, dg, raw, alpha_t=m.alpha_t, power=m.power)
        crack = self.old.damage == 1.
        qp = assemble_nodal_qp(self.kin, raw, h.fatigue, self.old.damage, crack,
                              w1=m.gc/m.length_scale, length_scale=m.length_scale,
                              thickness=m.thickness)
        force = equilibrium_internal_force(self.kin, d, u,
                    youngs_modulus=m.youngs_modulus, poisson_ratio=m.poisson_ratio,
                    residual_stiffness=0., thickness=m.thickness)
        return Fields(force, np.asarray(qp.hessian @ d + qp.linear), raw,
                      h.accumulated, h.driver, h.fatigue)

    def directional(self, u, d, du, dd, *, old_variation=None,
                    parameters=(0., 0., 0.), strict=True, margins=Margins()):
        """JVP of fresh force/Rd/raw/A/q/f, including the preceding state.

        parameters = (dE, dGc, dAlphaT), in physical units. ``strict=False``
        selects right directional derivatives at exact switches; that map need
        not be linear and MUST NOT be passed as a classical implicit Jacobian.
        """
        u, d = self._fields(u, d)
        du = _array(du, (2*self.n,), "du")
        dd = _array(dd, (self.n,), "dd")
        oldv = self.zero_variation() if old_variation is None else old_variation
        _array(oldv.damage, (self.n,), "old damage tangent")
        da = _array(oldv.accumulated, (self.e, 4), "old A tangent")
        dqprev = _array(oldv.driver, (self.e, 4), "old q tangent")
        dE, dGc, dT = _array(parameters, (3,), "material tangent")
        m = self.material
        p = self.evaluate(u, d)
        eps = np.einsum("egij,ej->egi", self.B, u[self.dofs])
        deps = np.einsum("egij,ej->egi", self.B, du[self.dofs])
        tr = eps[:, :, 0] + eps[:, :, 1]
        dtr = deps[:, :, 0] + deps[:, :, 1]
        dg = np.einsum("gi,ei->eg", self.shape, d[self.cells])
        ddg = np.einsum("gi,ei->eg", self.shape, dd[self.cells])
        gap = p.driver - self.old.driver
        fgap = p.accumulated - m.alpha_t
        if strict and (np.any(abs(tr) <= margins.strain)
                       or np.any(abs(gap) <= margins.energy)
                       or np.any(abs(fgap) <= margins.energy)):
            raise NonregularBranch("Amor/history/fatigue switch: classical derivative unavailable")

        C, vol, dev, bulk, shear = plane_strain_tensors(m.youngs_modulus, m.poisson_ratio)
        positive = (tr > 0) | ((tr == 0) & (dtr >= 0))
        Cplus = np.where(positive[:, :, None, None], C, 2*shear*dev)
        stress_plus = np.einsum("egij,egj->egi", Cplus, eps)
        draw = np.einsum("egi,egi->eg", stress_plus, deps) + p.raw*dE/m.youngs_modulus
        g = (1-dg)**2
        dg_factor = -2*(1-dg)*ddg
        dq = dg_factor*p.raw + g*draw
        change = dq - dqprev
        dA = da + np.where(gap > 0, change, np.where(gap < 0, 0., np.maximum(change, 0.)))
        decay = p.fatigue*m.power*(dT/m.alpha_t-(dA+dT)/(p.accumulated+m.alpha_t))
        df = np.where(fgap > 0, decay, np.where(fgap < 0, 0., np.minimum(decay, 0.)))

        Cminus = np.where(positive[:, :, None, None], 0., bulk*vol)
        Ct = g[:, :, None, None]*Cplus + Cminus
        stress = np.einsum("egij,egj->egi", Ct, eps)
        dstress = (np.einsum("egij,egj->egi", Ct, deps)
                   + dg_factor[:, :, None]*stress_plus + stress*dE/m.youngs_modulus)
        local_force = np.einsum("egai,ega,eg->ei", self.B, dstress, self.weights)
        force = np.zeros(2*self.n)
        np.add.at(force, self.dofs.ravel(), local_force.ravel())

        grad_d = np.einsum("egai,ei->ega", self.grad, d[self.cells])
        grad_dd = np.einsum("egai,ei->ega", self.grad, dd[self.cells])
        fracture = (self.shape[None, :, :]/m.length_scale
                    + 2*m.length_scale*np.einsum("egai,ega->egi", self.grad, grad_d))
        dfracture = 2*m.length_scale*np.einsum("egai,ega->egi", self.grad, grad_dd)
        local_rd = np.einsum("eg,egi->ei", self.weights,
            (2*draw*(dg-1)+2*p.raw*ddg)[:, :, None]*self.shape[None, :, :]
            + ((dGc*p.fatigue+m.gc*df)/(8/3))[:, :, None]*fracture
            + (m.gc*p.fatigue/(8/3))[:, :, None]*dfracture)
        rd = np.zeros(self.n)
        np.add.at(rd, self.cells.ravel(), local_rd.ravel())
        return Fields(force, rd, draw, dA, dq, df)


def _indices(value, size, name):
    x = np.asarray(value)
    if (x.ndim != 1 or x.dtype.kind not in "iu" or np.any(x < 0)
            or np.any(x >= size) or len(np.unique(x)) != len(x)):
        raise ValueError(f"invalid {name}")
    return np.array(x, dtype=np.int64, copy=True)


class ImplicitStep:
    """Consistent free-u/interior-d operator at an externally accepted state.

    Also audits supplied equilibrium/KKT with caller-declared physical scales.
    It does not establish history/mesh provenance or create an acceptance file.
    Actual tangent solves require an explicit caller-supplied linear solver.
    """
    def __init__(self, residual: Q4Residual, u, d, prescribed_dofs, *,
                 force_tolerance, damage_tolerance, margins=Margins()):
        if not np.isfinite([force_tolerance, damage_tolerance]).all() or min(force_tolerance, damage_tolerance) <= 0:
            raise ValueError("positive externally declared absolute residual tolerances required")
        self.r, self.margins = residual, margins
        self.u, self.d = (frozen_array(x) for x in residual._fields(u, d))
        self.bc = _indices(prescribed_dofs, 2*residual.n, "prescribed DOFs")
        self.free_u = np.setdiff1d(np.arange(2*residual.n), self.bc)
        p = residual.evaluate(self.u, self.d)
        lower = residual.old.damage
        fixed = lower == 1.
        self.lower = (self.d-lower <= margins.bound) & ~fixed
        self.upper = (1-self.d <= margins.bound) & ~fixed
        if np.any(self.lower & self.upper):
            raise NonregularBranch("nearly coincident damage bounds")
        self.fixed = fixed
        self.interior = np.flatnonzero(~(fixed | self.lower | self.upper))
        q = p.damage_residual
        if (np.linalg.norm(p.force[self.free_u], ord=np.inf) > force_tolerance if len(self.free_u) else False):
            raise ValueError("supplied mechanical state is not equilibrated")
        if (np.any(abs(q[self.interior]) > damage_tolerance)
                or np.any(q[self.lower] < -damage_tolerance)
                or np.any(q[self.upper] > damage_tolerance)):
            raise ValueError("supplied damage state fails KKT")
        if (np.any(q[self.lower] <= margins.multiplier)
                or np.any(q[self.upper] >= -margins.multiplier)):
            raise NonregularBranch("weakly active damage constraint")
        # Reject constitutive switches even if a particular zero JVP hides them.
        z = residual.zero_variation()
        residual.directional(self.u, self.d, z.displacement, z.damage,
                             strict=True, margins=margins)
        self.size = len(self.free_u) + len(self.interior)
        self.operator = LinearOperator((self.size, self.size), matvec=self._matvec, dtype=float)

    def _reduced(self, fields):
        return np.r_[fields.force[self.free_u], fields.damage_residual[self.interior]]

    def _matvec(self, vector):
        x = _array(vector, (self.size,), "reduced vector")
        z = self.r.zero_variation()
        z.displacement[self.free_u] = x[:len(self.free_u)]
        z.damage[self.interior] = x[len(self.free_u):]
        return self._reduced(self.r.directional(self.u, self.d, z.displacement,
                            z.damage, strict=True, margins=self.margins))

    def propagate(self, old_variation: Variation, *, parameters=(0., 0., 0.),
                  boundary_variation=None, solve: Callable, linear_tolerance):
        """Carry preceding-state and parameter tangents through one given step.

        solve(operator, rhs) -> x is supplied by the authorized caller. No
        default FEM/tangent solve or driver is installed. The returned linear
        residual is audited independently, including a zero-RHS absolute scale.
        """
        if not np.isfinite(linear_tolerance) or linear_tolerance <= 0:
            raise ValueError("positive linear residual tolerance required")
        _array(old_variation.damage, (self.r.n,), "old damage tangent")
        if np.any(old_variation.damage[self.fixed] != 0):
            raise ValueError("fixed crack has a nonzero old tangent")
        z = self.r.zero_variation()
        if boundary_variation is not None:
            z.displacement[self.bc] = _array(boundary_variation, (len(self.bc),), "boundary tangent")
        z.damage[self.lower] = old_variation.damage[self.lower]
        source = self.r.directional(self.u, self.d, z.displacement, z.damage,
                old_variation=old_variation, parameters=parameters, margins=self.margins)
        rhs = -self._reduced(source)
        x = np.zeros(0) if not self.size else _array(solve(self.operator, rhs), (self.size,), "linear solution")
        error = np.linalg.norm(self.operator @ x-rhs, ord=np.inf) if self.size else 0.
        if error > linear_tolerance*max(1., np.max(abs(rhs), initial=0.)):
            raise RuntimeError("implicit sensitivity linear solve failed residual audit")
        z.displacement[self.free_u] = x[:len(self.free_u)]
        z.damage[self.interior] = x[len(self.free_u):]
        result = self.r.directional(self.u, self.d, z.displacement, z.damage,
                old_variation=old_variation, parameters=parameters, margins=self.margins)
        return Variation(z.displacement, z.damage, result.accumulated, result.driver), result


def observation_tangent(fields: Fields, variation: Variation, *, reaction_dofs,
                        displacement_dofs, reaction_weights=None):
    """Derivative of a declared force sum and sparse displacement observation.

    fields is the total directional result, so explicit dE and damage/history
    effects are retained. Prescribed displacements are controls, not automatic
    independent measurements. Unit/noise weighting belongs to the caller.
    """
    ids = _indices(reaction_dofs, len(fields.force), "reaction DOFs")
    sensors = _indices(displacement_dofs, len(variation.displacement), "sensor DOFs")
    w = np.ones(len(ids)) if reaction_weights is None else _array(reaction_weights, (len(ids),), "reaction weights")
    return float(w @ fields.force[ids]), variation.displacement[sensors].copy()
