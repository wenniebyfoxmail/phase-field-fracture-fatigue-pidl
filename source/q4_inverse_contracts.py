"""Initial-state and observable identity contracts; pure supplied-array helpers."""
from dataclasses import dataclass
import hashlib
import json

import numpy as np

from hybrid_history import frozen_array
from q4_inverse_derivatives import _array, _indices


def backend_physics_id(material):
    """Same pure dictionary identity as the frozen NativeQ4Backend source."""
    m = material
    payload = dict(youngs_modulus=m.youngs_modulus, poisson_ratio=m.poisson_ratio,
        residual_stiffness=0., thickness=m.thickness, gc=m.gc, ell=m.length_scale,
        alpha_t=m.alpha_t, power=m.power, law="AT1-Amor-Carrara-nodalK-v1")
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def matlab_block_dofs_to_interleaved(dofs, n_nodes):
    """MATLAB 1-based [ux_all;uy_all] -> Python 0-based [ux0,uy0,...]."""
    x = np.asarray(dofs)
    if type(n_nodes) is not int or n_nodes <= 0 or not np.isfinite(x).all() or np.any(x != np.floor(x)):
        raise ValueError("integer MATLAB DOFs and positive node count required")
    ids = _indices(x.astype(np.int64).ravel()-1, 2*n_nodes, "MATLAB DOFs")
    return np.where(ids < n_nodes, 2*ids, 2*(ids-n_nodes)+1)


def matlab_block_displacement_to_interleaved(block, n_nodes):
    x = _array(np.asarray(block).reshape(-1), (2*n_nodes,), "MATLAB displacement")
    return np.column_stack((x[:n_nodes], x[n_nodes:])).ravel()


def hdf_native_history_to_logical(hdf_history, n_elements):
    """HDF [channel,GP,element] -> logical [element,GP,channel].

    GP order is NOT permuted. Channels 2/3/4 in MATLAB remain A/qprev/f;
    channel1 is preserved opaque, not renamed as a qualified physical H.
    """
    h = _array(hdf_history, (4, 4, n_elements), "HDF native history")
    return np.transpose(h, (2, 1, 0)).copy()


@dataclass(frozen=True)
class InitialBinding:
    source_id: str
    mesh_id: str
    physics_id: str
    recovery_load_id: str
    policy: str
    source_phase: str = "post_zero_load_recovery_reset_before_c1s1"

    def validate(self, state, material):
        if (not all(isinstance(x, str) and x for x in vars(self).values())
                or self.policy not in ("fixed_recovered_profile", "differentiate_recovery")
                or self.source_phase != "post_zero_load_recovery_reset_before_c1s1"
                or state.mesh_id != self.mesh_id or state.physics_id != self.physics_id
                or state.physics_id != backend_physics_id(material)
                or state.load_id != self.recovery_load_id
                or state.version != 0 or state.load_index != 0):
            raise ValueError("initial-state/source/material identity mismatch")
        if (np.any(state.displacement != 0) or np.any(state.accumulated != 0)
                or np.any(state.driver != 0) or np.any(state.fatigue != 1)):
            raise ValueError("source zero-load recovery/reset convention not met")
        # Full damage/opaque arrays must come from the bound source state, not
        # synthesized from an element average. This method does not read files.
        if self.policy == "differentiate_recovery":
            raise ValueError("recovery tangent requires separately reviewed recovery equations; never silently zero it")
        return dict(initial_state_id=state.fingerprint(), source_id=self.source_id,
                    policy=self.policy, recovery_counted_as_physical_step=False)


@dataclass(frozen=True)
class ReactionBinding:
    model_family: str
    boundary_id: str
    source_id: str
    state_phase: str
    force_phase: str
    displacement_unit: str
    force_unit: str
    dofs: np.ndarray
    weights: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "dofs", np.asarray(self.dofs).copy())
        self.dofs.flags.writeable = False
        object.__setattr__(self, "weights", frozen_array(self.weights))
        text = (self.model_family, self.boundary_id, self.source_id, self.state_phase,
                self.force_phase, self.displacement_unit, self.force_unit)
        if not all(isinstance(x, str) and x for x in text):
            raise ValueError("explicit reaction identity, phase and units required")

    def project(self, full_force, *, current_family, current_boundary_id,
                current_state_phase, require_fresh_derivative=True):
        force = np.asarray(full_force, dtype=float)
        if force.ndim != 1 or not np.isfinite(force).all():
            raise ValueError("finite internal force vector required")
        ids = _indices(self.dofs, len(force), "reaction boundary")
        w = _array(self.weights, (len(ids),), "reaction weights")
        if (self.model_family != current_family or self.boundary_id != current_boundary_id
                or self.state_phase != current_state_phase):
            raise ValueError("mixed-model, boundary or solve/commit reaction identity")
        if require_fresh_derivative and self.force_phase != "fresh_at_exact_given_ud":
            raise ValueError("legacy cached/other-phase response is not a fresh given-state derivative")
        return float(w @ force[ids])
