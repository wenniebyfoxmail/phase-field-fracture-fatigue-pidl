"""Derivative history transactions and nonsmooth directional equations.

No primal stepping or trajectory replay. Given-state sensitivities advance
once only after complete checks. Switches expose a directional complementarity
problem and STOP the tape; a residual-only directional candidate is never
silently accepted as a unique material derivative.
"""
from dataclasses import dataclass

import numpy as np

from hybrid_history import AcceptedState, frozen_array
from q4_inverse_derivatives import ImplicitStep, Margins, Variation, _array, _indices
from q4_inverse_contracts import backend_physics_id


def freeze_variation(v, n, e):
    return Variation(*[frozen_array(_array(x, shape, name)) for x, shape, name in (
        (v.displacement, (2*n,), "du"), (v.damage, (n,), "dd"),
        (v.accumulated, (e, 4), "dA"), (v.driver, (e, 4), "dq"))])


@dataclass(frozen=True)
class DirectionalCheck:
    equation_inf: float
    weak_primal_violation: float
    weak_dual_violation: float
    satisfies_directional_equations: bool
    derivative_unique: bool = False


class DirectionalTransitionProblem:
    """Right-direction equations at history/material/damage switches.

    For weak lower activity: dd-dd_old >=0, dRd>=0, product=0.
    For weak upper activity: -dd>=0, -dRd>=0, product=0.
    Fischer-Burmeister equations encode these conditions without pretending
    they are a fixed classical Jacobian. No complementarity solver is supplied.
    """
    def __init__(self, residual, u, d, prescribed_dofs, *, force_tolerance,
                 damage_tolerance, force_scale, damage_scale, history_scale, margins=Margins()):
        values = [force_tolerance, damage_tolerance, force_scale, damage_scale, history_scale]
        if not np.isfinite(values).all() or min(values) <= 0:
            raise ValueError("positive finite tolerances and fixed physical scales required")
        self.r = residual
        self.u, self.d = [frozen_array(x) for x in residual._fields(u, d)]
        self.bc = _indices(prescribed_dofs, 2*residual.n, "prescribed DOFs")
        self.free_u = np.setdiff1d(np.arange(2*residual.n), self.bc)
        self.margins, self.force_scale, self.damage_scale = margins, force_scale, damage_scale
        self.history_scale = history_scale
        p = residual.evaluate(self.u, self.d)
        self.fixed = residual.old.damage == 1
        lower = (self.d-residual.old.damage <= margins.bound) & ~self.fixed
        upper = (1-self.d <= margins.bound) & ~self.fixed
        if np.any(lower & upper):
            raise ValueError("near-coincident nonfixed bounds need a separately defined domain")
        self.interior = ~(lower | upper | self.fixed)
        q = p.damage_residual
        if (np.max(abs(p.force[self.free_u]), initial=0) > force_tolerance
                or np.any(abs(q[self.interior]) > damage_tolerance)
                or np.any(q[lower] < -damage_tolerance)
                or np.any(q[upper] > damage_tolerance)):
            raise ValueError("given primal point fails declared equilibrium/KKT")
        self.weak_lower = lower & (abs(q) <= margins.multiplier)
        self.weak_upper = upper & (abs(q) <= margins.multiplier)
        self.strong_lower = lower & ~self.weak_lower
        self.strong_upper = upper & ~self.weak_upper
        for name in ("free_u", "fixed", "interior", "weak_lower", "weak_upper", "strong_lower", "strong_upper"):
            a = np.ascontiguousarray(getattr(self, name))
            setattr(self, name, np.frombuffer(a.tobytes(), dtype=a.dtype).reshape(a.shape))

    def equations(self, variation, old_variation, *, parameters=(0., 0., 0.),
                  boundary_variation=None):
        v = freeze_variation(variation, self.r.n, self.r.e)
        old = freeze_variation(old_variation, self.r.n, self.r.e)
        bc = np.zeros(len(self.bc)) if boundary_variation is None else _array(boundary_variation, (len(self.bc),), "boundary tangent")
        if np.any(old.damage[self.fixed] != 0):
            raise ValueError("fixed crack initial tangent must remain zero")
        out = self.r.directional(self.u, self.d, v.displacement, v.damage,
                old_variation=old, parameters=parameters, strict=False, margins=self.margins)
        rd = out.damage_residual/self.damage_scale
        eqd = rd.copy()
        eqd[self.fixed | self.strong_upper] = v.damage[self.fixed | self.strong_upper]
        eqd[self.strong_lower] = v.damage[self.strong_lower]-old.damage[self.strong_lower]
        a = v.damage-old.damage
        wl, wu = self.weak_lower, self.weak_upper
        eqd[wl] = np.hypot(a[wl], rd[wl])-a[wl]-rd[wl]
        eqd[wu] = np.hypot(-v.damage[wu], -rd[wu])+v.damage[wu]+rd[wu]
        equations = np.r_[out.force[self.free_u]/self.force_scale,
                         v.displacement[self.bc]-bc, eqd,
                         ((v.accumulated-out.accumulated)/self.history_scale).ravel(),
                         ((v.driver-out.driver)/self.history_scale).ravel()]
        primal = max(np.max(-a[wl], initial=0.), np.max(v.damage[wu], initial=0.), 0.)
        dual = max(np.max(-rd[wl], initial=0.), np.max(rd[wu], initial=0.), 0.)
        return equations, out, float(primal), float(dual)

    def check(self, variation, old_variation, *, tolerance, **kwargs):
        if not np.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("positive finite directional residual tolerance required")
        equations, out, primal, dual = self.equations(variation, old_variation, **kwargs)
        norm = float(np.max(abs(equations), initial=0.))
        return DirectionalCheck(norm, primal, dual, max(norm, primal, dual) <= tolerance), out

    def stop_record(self):
        return dict(status="DIRECTIONAL_PROBLEM_PREPARED_TAPE_NOT_ADVANCED",
            weak_lower=int(self.weak_lower.sum()), weak_upper=int(self.weak_upper.sum()),
            derivative_unique=False, history_commits=0,
            requires="reviewed directional solver AND directional uniqueness/regularity evidence; no automatic fallback")


class SensitivityTape:
    """Pure in-memory derivative transaction; never writes/advances FEM state.

    Stable-step propagation is atomic: any exception leaves state, tangent and
    receipts unchanged. Exactly unloaded/weakly active states stop until the
    directional strategy has separately reviewed numerical support.
    """
    def __init__(self, initial_state: AcceptedState, variation: Variation, *,
                 initial_binding_id, initialization_policy):
        if not initial_binding_id or initialization_policy not in (
                "fixed_recovered_profile", "externally_verified_recovery_tangent"):
            raise ValueError("explicit initial binding and derivative policy required")
        self.state = initial_state
        n, e = initial_state.damage.size, len(initial_state.accumulated)
        self.variation = freeze_variation(variation, n, e)
        if initialization_policy == "fixed_recovered_profile" and any(np.any(x != 0) for x in vars(self.variation).values()):
            raise ValueError("fixed-profile convention requires zero initial tangents")
        self.initial_binding_id, self.initialization_policy = initial_binding_id, initialization_policy
        self.receipts = ()

    def advance_given(self, step, new_state, *, expected_load_id, transition_tolerance,
                      parameters=(0., 0., 0.), **solver_kwargs):
        if not isinstance(step, ImplicitStep):
            raise TypeError("only reviewed stable ImplicitStep may advance; switches stop")
        if not np.isfinite(transition_tolerance) or transition_tolerance <= 0:
            raise ValueError("positive transition tolerance required")
        old = self.state
        if (step.r.old.fingerprint() != old.fingerprint()
                or old.physics_id != backend_physics_id(step.r.material)
                or new_state.version != old.version+1 or new_state.load_index != old.load_index+1
                or new_state.mesh_id != old.mesh_id or new_state.physics_id != old.physics_id
                or new_state.load_id != expected_load_id or not expected_load_id
                or not np.array_equal(new_state.opaque, old.opaque)
                or not np.array_equal(new_state.displacement, step.u)
                or not np.array_equal(new_state.damage, step.d)):
            raise ValueError("stale, mixed-physics or mismatched given transition")
        point = step.r.evaluate(step.u, step.d)
        for name in ("accumulated", "driver", "fatigue"):
            if not np.allclose(getattr(new_state, name), getattr(point, name),
                               atol=transition_tolerance, rtol=0):
                raise ValueError("given committed history differs from fresh trial")
        variation, _ = step.propagate(self.variation, parameters=parameters, **solver_kwargs)
        variation = freeze_variation(variation, step.r.n, step.r.e)
        receipt = dict(previous_id=old.fingerprint(), state_id=new_state.fingerprint(),
            old_version=old.version, new_version=new_state.version,
            load_id=expected_load_id, parameters=tuple(float(x) for x in parameters),
            derivative_commits=1, primal_commits=0, source="given_states_only")
        receipts = self.receipts+(receipt,)
        # Sole state change after every check and sensitivity solve succeeded.
        self.state, self.variation, self.receipts = new_state, variation, receipts
        return receipt
