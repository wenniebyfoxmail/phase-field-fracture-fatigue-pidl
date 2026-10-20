"""Accepted-state Carrara trial map. No solver iteration accumulates history."""
from dataclasses import dataclass
import hashlib
import json

import numpy as np


def frozen_array(value, *, ndim=None):
    a = np.array(value, dtype=np.float64, copy=True)
    if (ndim is not None and a.ndim != ndim) or not np.all(np.isfinite(a)):
        raise ValueError("invalid shape or nonfinite state")
    # Immutable bytes backing prevents callers from re-enabling writes.
    return np.frombuffer(a.tobytes(), dtype=a.dtype).reshape(a.shape)


def fatigue_factor(accumulated, alpha_t, power):
    if not np.isfinite([alpha_t, power]).all() or min(alpha_t, power) <= 0:
        raise ValueError("positive finite fatigue parameters required")
    a = np.asarray(accumulated, dtype=float)
    if not np.isfinite(a).all() or np.any(a < 0):
        raise ValueError("invalid accumulated fatigue")
    return np.where(a <= alpha_t, 1., (2 * alpha_t / (a + alpha_t)) ** power)


@dataclass(frozen=True)
class AcceptedState:
    displacement: np.ndarray
    damage: np.ndarray
    accumulated: np.ndarray
    driver: np.ndarray
    fatigue: np.ndarray
    opaque: np.ndarray
    version: int
    load_index: int
    mesh_id: str
    physics_id: str
    load_id: str

    def __post_init__(self):
        for key, dim in (("displacement", 1), ("damage", 1),
                         ("accumulated", 2), ("driver", 2), ("fatigue", 2)):
            object.__setattr__(self, key, frozen_array(getattr(self, key), ndim=dim))
        object.__setattr__(self, "opaque", frozen_array(self.opaque))
        if (self.displacement.size != 2 * self.damage.size or not self.damage.size
                or self.accumulated.shape != self.driver.shape
                or self.accumulated.shape != self.fatigue.shape
                or self.accumulated.shape[1] != 4 or not self.accumulated.size):
            raise ValueError("state dimensions do not match native Q4")
        if (np.any(self.damage < 0) or np.any(self.damage > 1)
                or np.any(self.accumulated < 0) or np.any(self.driver < 0)
                or np.any(self.fatigue < 0) or np.any(self.fatigue > 1)):
            raise ValueError("infeasible accepted state; no implicit projection")
        if (type(self.version) is not int or type(self.load_index) is not int
                or self.version < 0 or self.load_index < 0
                or not all(isinstance(x, str) and x for x in
                           (self.mesh_id, self.physics_id, self.load_id))):
            raise ValueError("invalid state identity")

    def fingerprint(self):
        digest = hashlib.sha256()
        for key in ("displacement", "damage", "accumulated", "driver", "fatigue", "opaque"):
            a = getattr(self, key)
            digest.update(str(a.shape).encode())
            digest.update(a.tobytes())
        digest.update(json.dumps([self.version, self.load_index, self.mesh_id,
                                  self.physics_id, self.load_id]).encode())
        return digest.hexdigest()


@dataclass(frozen=True)
class TrialHistory:
    accumulated: np.ndarray
    driver: np.ndarray
    fatigue: np.ndarray


def trial_history(state, damage_gp, tensile_gp, *, alpha_t, power):
    d = np.asarray(damage_gp, dtype=float)
    psi = np.asarray(tensile_gp, dtype=float)
    if (d.shape != state.accumulated.shape or psi.shape != d.shape
            or not np.isfinite(d).all() or not np.isfinite(psi).all()
            or np.any(d < 0) or np.any(d > 1) or np.any(psi < 0)):
        raise ValueError("invalid native-GP trial field")
    if not np.allclose(state.fatigue, fatigue_factor(state.accumulated, alpha_t, power),
                       rtol=0., atol=1.e-14):
        raise ValueError("accepted fatigue inconsistent with accumulated state")
    driver = (1 - d) ** 2 * psi
    accumulated = state.accumulated + np.maximum(driver - state.driver, 0.)
    return TrialHistory(*(frozen_array(x) for x in
                          (accumulated, driver, fatigue_factor(accumulated, alpha_t, power))))
