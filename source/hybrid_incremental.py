"""Coupled constrained incremental solver. Library API; no run/training entry.

Only zero-body-force displacement loading is implemented. Traction/body-force
contracts must not be silently mapped to this backend. No accepted state is
mutated: solve_step returns an audited proposal for a separate durable commit.
"""
from dataclasses import dataclass, asdict, replace, fields
import hashlib
import json
from time import perf_counter

import numpy as np

from damage_conditioned_equilibrium import (
    solve_amor_equilibrium, assemble_amor_stiffness, tensile_energy,
)
from hybrid_damage import assemble_nodal_qp, kkt_audit, solve_nodal_qp
from hybrid_history import AcceptedState, frozen_array, trial_history
from native_q4_damage_qp import gauss_interpolation_matrix


def digest_config(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class SolverSettings:
    # These are engineering defaults, NOT an authorized scientific run card.
    force_scale: float
    damage_gradient_scale: float
    force_tolerance: float = 1.e-8
    damage_tolerance: float = 1.e-7
    bound_tolerance: float = 1.e-10
    fatigue_tolerance: float = 1.e-8
    qp_precision: float = 1.e-10
    max_outer: int = 100
    max_mechanics: int = 50
    max_qp: int = 200000
    wall_seconds: float = 120.

    def __post_init__(self):
        for k, v in asdict(self).items():
            if not np.isfinite(v) or v <= 0:
                raise ValueError(f"invalid setting {k}")
        for k in ("max_outer", "max_mechanics", "max_qp"):
            if type(getattr(self, k)) is not int:
                raise ValueError("iteration caps must be integers")
        if self.qp_precision > self.bound_tolerance:
            raise ValueError("QP precision must not exceed bound tolerance")


class StepFailure(RuntimeError):
    def __init__(self, message, work):
        super().__init__(message)
        self.work = tuple(work)


@dataclass(frozen=True)
class StepProposal:
    previous_id: str
    state: AcceptedState
    certificate: dict
    work: tuple


class NativeQ4Backend:
    def __init__(self, kin, crack, *, youngs_modulus=1., poisson_ratio=.3,
                 gc=.01, length_scale=.01, alpha_t=.5, power=2., thickness=1.):
        setup_started = perf_counter()
        scalars = [youngs_modulus, poisson_ratio, gc, length_scale, alpha_t, power, thickness]
        if (not np.isfinite(scalars).all() or min(youngs_modulus, gc, length_scale,
                                                alpha_t, power, thickness) <= 0
                or not -1 < poisson_ratio < .5):
            raise ValueError("invalid physical coefficients")
        arrays = {}
        for field in fields(kin):
            a = np.ascontiguousarray(getattr(kin, field.name))
            arrays[field.name] = np.frombuffer(a.tobytes(), dtype=a.dtype).reshape(a.shape)
        self.kin = kin = replace(kin, **arrays)
        # The GP feature/state contract is native (+,+),(-,+),(+,-),(-,-).
        from native_q4_damage_qp import build_native_q4_kinematics
        reference = build_native_q4_kinematics(kin.points, kin.cells)
        if (np.any(kin.det_jacobians <= 0) or np.any(kin.shape_values < 0)
                or not np.array_equal(kin.shape_values, reference.shape_values)
                or not np.array_equal(kin.b_matrices, reference.b_matrices)
                or not np.array_equal(kin.det_jacobians, reference.det_jacobians)):
            raise ValueError("native GP/geometry identity mismatch")
        if np.asarray(crack).dtype != bool:
            raise ValueError("crack must be an explicit boolean identity mask")
        self.crack = np.frombuffer(np.asarray(crack).tobytes(), dtype=bool)
        if self.crack.shape != (len(kin.points),):
            raise ValueError("crack shape mismatch")
        self.material = dict(youngs_modulus=youngs_modulus, poisson_ratio=poisson_ratio,
                             residual_stiffness=0., thickness=thickness)
        self.gc, self.length_scale = gc, length_scale
        self.alpha_t, self.power = alpha_t, power
        self.gp = gauss_interpolation_matrix(kin)
        h = hashlib.sha256()
        for a in (kin.points, kin.cells, kin.shape_values, kin.b_matrices,
                  kin.det_jacobians, self.crack):
            h.update(np.ascontiguousarray(a).tobytes())
        self.mesh_id = h.hexdigest()
        self.physics_id = digest_config(dict(**self.material, gc=gc, ell=length_scale,
                                            alpha_t=alpha_t, power=power,
                                            law="AT1-Amor-Carrara-nodalK-v1"))
        self.setup_seconds = perf_counter() - setup_started

    def validate_state(self, state):
        if (state.mesh_id != self.mesh_id or state.physics_id != self.physics_id
                or state.damage.size != len(self.kin.points)
                or state.accumulated.shape != (len(self.kin.cells), 4)
                or np.any(state.damage[self.crack] != 1)):
            raise ValueError("accepted state/backend identity mismatch")

    def mechanics(self, d, dofs, values, settings):
        result = solve_amor_equilibrium(self.kin, d, dofs, values, **self.material,
                                       max_iterations=settings.max_mechanics,
                                       residual_tolerance=settings.force_tolerance)
        return result.displacement, {"iterations": result.iterations,
                                     "minimum_pivot_ratio": result.minimum_pivot_ratio,
                                     "stiffness_assemblies": result.iterations + 1,
                                     "factorizations": ((result.iterations + int(not result.active_set_stable))
                                                        if len(dofs) < len(result.displacement) else 0)}

    def trial(self, old, u, d):
        psi, _ = tensile_energy(self.kin, u, youngs_modulus=self.material["youngs_modulus"],
                               poisson_ratio=self.material["poisson_ratio"])
        q = trial_history(old, (self.gp @ d).reshape(-1, 4), psi,
                          alpha_t=self.alpha_t, power=self.power)
        return psi, q

    def damage_problem(self, psi, f, old):
        # Existing kernel's w1 = Gc / ell; never pass Gc as w1.
        return assemble_nodal_qp(self.kin, psi, f, old.damage, self.crack,
                                 w1=self.gc / self.length_scale,
                                 length_scale=self.length_scale,
                                 thickness=self.material["thickness"])

    def force_audit(self, u, d, dofs, values, settings):
        matrix = assemble_amor_stiffness(self.kin, d, u, **self.material)
        force = np.asarray(matrix @ u)
        free = np.ones(len(u), bool)
        free[dofs] = False
        free_force = force[free]
        return dict(force_inf=float(np.max(np.abs(free_force), initial=0.)),
                    force_l2=float(np.linalg.norm(free_force)),
                    force_scaled=float(np.max(np.abs(free_force), initial=0.)) / settings.force_scale,
                    boundary_inf=float(np.max(np.abs(u[dofs] - values), initial=0.)),
                    reaction_dofs=dofs.tolist(), reaction_values=force[dofs].tolist())


def solve_step(backend, old, prescribed_dofs, prescribed_values, *, next_load_id,
               settings, predictor=None, classical_initial=None):
    """One complete coupled physical substep; no retry, commit or training.

    ``predictor.predict(old, u_pred, psi_pred, next_load_id, dofs, values)``
    returns a nodal coefficient a, not an accepted state. It may be omitted.
    Settings, model and all identifiers must be frozen by the future run card.
    """
    work = []
    start = perf_counter()

    def remaining():
        t = settings.wall_seconds - (perf_counter() - start)
        if t <= 0:
            raise RuntimeError("physical-substep wall cap reached")
        return t

    def call(kind, fn):
        remaining()
        tick = perf_counter()
        row = dict(work_id=len(work), kind=kind, status="failed")
        work.append(row)
        try:
            result = fn()
            row["status"] = "returned"
            return result
        finally:
            row["wall_seconds"] = perf_counter() - tick
            # A native sparse solve cannot be preempted in-process. An external
            # producer watchdog is required for a hard process wall budget.

    try:
        backend.validate_state(old)
        previous_id = old.fingerprint()
        if not isinstance(next_load_id, str) or not next_load_id:
            raise ValueError("target load identity required")
        dofs = np.asarray(prescribed_dofs)
        values = np.asarray(prescribed_values, dtype=float)
        if (dofs.ndim != 1 or not np.issubdtype(dofs.dtype, np.integer)
                or values.shape != dofs.shape or not values.size
                or not np.isfinite(values).all() or len(np.unique(dofs)) != len(dofs)
                or np.any(dofs < 0) or np.any(dofs >= old.displacement.size)):
            raise ValueError("invalid prescribed displacement contract")
        dofs = dofs.astype(np.int64)
        lower = old.damage
        u_pred, info = call("common_mechanics_predictor",
                            lambda: backend.mechanics(lower, dofs, values, settings))
        work[-1]["solver"] = info
        d = lower.copy() if classical_initial is None else np.asarray(classical_initial, float).copy()
        if (d.shape != lower.shape or not np.isfinite(d).all()
                or np.any(d < lower) or np.any(d > 1)):
            raise ValueError("invalid classical feasible initial guess")
        if predictor is not None:
            psi_pred, _ = call("prediction_features", lambda: backend.trial(old, u_pred, lower))
            try:
                a = call("network_inference", lambda: predictor.predict(
                    old, frozen_array(u_pred), frozen_array(psi_pred), next_load_id,
                    frozen_array(dofs), frozen_array(values)))
                a = np.asarray(a, float)
                if a.shape != lower.shape or not np.isfinite(a).all():
                    raise ValueError("malformed neural prediction")
                d = lower + (1 - lower) * np.clip(a, 0., 1.)
                d[backend.crack] = 1.
            except (ValueError, RuntimeError) as exc:
                work.append(dict(work_id=len(work), kind="initial_guess_fallback",
                                 reason=str(exc), wall_seconds=0., status="baseline_initial"))
        # The common mechanics result is reusable only if d is identical.
        u_cache = u_pred if np.array_equal(d, lower) else None
        for outer in range(1, settings.max_outer + 1):
            if u_cache is None:
                u, info = call("mechanics", lambda: backend.mechanics(d, dofs, values, settings))
                work[-1]["solver"] = info
            else:
                u = u_cache
            psi, q = call("trial_history", lambda: backend.trial(old, u, d))
            qp = call("damage_assembly", lambda: backend.damage_problem(psi, q.fatigue, old))
            new_d, qp_info = call("damage_qp", lambda: solve_nodal_qp(
                qp, d, eps=settings.qp_precision, max_iter=settings.max_qp, time_limit=remaining()))
            work[-1]["solver"] = qp_info
            if np.array_equal(new_d, d):
                final_u = u
            else:
                final_u, info = call("mechanics_re_equilibration",
                                     lambda: backend.mechanics(new_d, dofs, values, settings))
                work[-1]["solver"] = info
            final_psi, final_q = call("final_trial_history", lambda: backend.trial(old, final_u, new_d))
            final_qp = call("fresh_final_damage_assembly",
                            lambda: backend.damage_problem(final_psi, final_q.fatigue, old))
            damage_audit = call("fresh_final_kkt", lambda: kkt_audit(
                final_qp, new_d, gradient_scale=settings.damage_gradient_scale,
                bound_tolerance=settings.bound_tolerance))
            force_audit = call("fresh_final_force", lambda: backend.force_audit(
                final_u, new_d, dofs, values, settings))
            fatigue_residual = float(np.max(np.abs(final_q.fatigue - q.fatigue)))
            scalars = list(damage_audit[k] for k in ("primal_inf", "kkt_scaled_inf", "projected_inf"))
            scalars += [force_audit[k] for k in ("force_inf", "force_l2", "force_scaled", "boundary_inf")]
            scalars += [fatigue_residual]
            passed = (np.isfinite(scalars).all()
                      and damage_audit["primal_inf"] <= settings.bound_tolerance
                      and max(damage_audit["kkt_scaled_inf"], damage_audit["projected_inf"]) <= settings.damage_tolerance
                      and force_audit["force_scaled"] <= settings.force_tolerance
                      and force_audit["boundary_inf"] <= settings.bound_tolerance
                      and fatigue_residual <= settings.fatigue_tolerance)
            remaining()
            if old.fingerprint() != previous_id:
                raise RuntimeError("accepted preimage mutated")
            if passed:
                state = AcceptedState(final_u, new_d, final_q.accumulated, final_q.driver,
                                      final_q.fatigue, old.opaque, old.version + 1,
                                      old.load_index + 1, old.mesh_id, old.physics_id, next_load_id)
                certificate = dict(passed=True, previous_id=previous_id,
                                   state_id=state.fingerprint(), outer=outer,
                                   settings_id=digest_config(asdict(settings)),
                                   damage=damage_audit, mechanics=force_audit,
                                   fatigue_residual=fatigue_residual,
                                   total_wall_seconds=perf_counter() - start,
                                   model_id=getattr(predictor, "model_id", "NN_OFF"))
                return StepProposal(previous_id, state, certificate, tuple(work))
            d, u_cache = new_d, final_u
        raise RuntimeError("joint iteration cap reached; no accepted proposal")
    except Exception as exc:
        if isinstance(exc, StepFailure):
            raise
        raise StepFailure(str(exc), work) from exc
