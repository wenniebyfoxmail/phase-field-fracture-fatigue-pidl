"""Explicit native blocked DOF <-> canonical interleaved state adapters."""
from pathlib import Path
import hashlib
import json

import numpy as np

from hybrid_history import AcceptedState
from hybrid_incremental import NativeQ4Backend
from native_q4_damage_qp import build_native_q4_kinematics
from hybrid_transaction import StateStore


def sha256(path):
    with Path(path).open("rb") as handle:
        digest=hashlib.sha256()
        for chunk in iter(lambda:handle.read(1024*1024),b""):
            digest.update(chunk)
        return digest.hexdigest()


def blocked_to_interleaved(value):
    a = np.asarray(value)
    if a.ndim != 1 or len(a) % 2:
        raise ValueError("blocked displacement/force must have even vector length")
    return a.reshape(2, -1).T.reshape(-1).copy()


def native_dofs_to_canonical(dofs, n):
    a = np.asarray(dofs)
    if (a.ndim != 1 or not np.issubdtype(a.dtype, np.integer)
            or np.any(a < 0) or np.any(a >= 2 * n)):
        raise ValueError("native zero-based DOF identity mismatch")
    return 2 * (a % n) + a // n


def load_backend(root, manifest):
    root = Path(root)
    for name, expected in manifest["assets"].items():
        if sha256(root / name) != expected:
            raise RuntimeError(f"input hash mismatch: {name}")
    with np.load(root / "mesh.npz", allow_pickle=False) as data:
        kin = build_native_q4_kinematics(data["points"], data["cells"])
        backend = NativeQ4Backend(kin, data["crack"], **manifest["material"])
        dofs, values = data["bc_dofs"].copy(), data["bc_unit_values"].copy()
    old, _ = StateStore(root / "state0.npz").load()
    backend.validate_state(old)
    if old.fingerprint() != manifest["state0_id"]:
        raise RuntimeError("prescribed state0 identity mismatch")
    if backend.mesh_id != manifest["mesh_id"] or backend.physics_id != manifest["physics_id"]:
        raise RuntimeError("canonical backend identity mismatch")
    return backend, old, dofs, values


def read_manifest(path):
    return json.loads(Path(path).read_text())


def state_from_native_group(group, backend, *, version, load_index, load_id):
    h = np.asarray(group["history"]).transpose(2, 1, 0)
    return AcceptedState(blocked_to_interleaved(np.asarray(group["u"]).ravel()),
                         np.asarray(group["d"]).ravel(), h[:, :, 1], h[:, :, 2], h[:, :, 3],
                         h[:, :, 0], version, load_index, backend.mesh_id, backend.physics_id, load_id)
