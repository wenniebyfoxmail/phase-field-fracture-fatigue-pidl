"""Explicit source arithmetic adapter; never overwrites a decoded archive.

Admission is restricted to the identity-bound native archives in the runner.
The generic Stage-0A adapter and its numerical thresholds remain unchanged.
"""
from __future__ import annotations

import numpy as np
import torch

from fixed_weight_contract import (
    State, StateKey, RecoveredInitialKey, RecoveredInitialState, _require,
)
from fixed_weight_roundoff import certify_negative_energy
from s09_stage0a_transition import carrara_f

PRODUCER = "862992a60edc7f59335365beacb5c71fc8592a7a"
RULE = "native862992_recovered_load_source_f_certified_energy_v1"
LEGACY_PRODUCER = "53ce560b6d20b336d6ec92ccf56ed2b230e804ce"
LEGACY_RULE = "native53ce_recovered_load_source_f_no_negative_energy_v1"
# Exact index tokens, bound to the two immutable index hashes in the runner.
# This is an explicit archive mapping, not an assumed MATLAB print precision.
CSV_LOADS = {
    "hard5_u0115_stage0b": ("0", "0.028749885", "0.057499885", "0.086249885", "0.114999885", "0"),
    "hard5_u0125_stage0b": ("0", "0.031249875", "0.062499875", "0.093749875", "0.124999875", "0"),
    # The 53ce archives are a separately bound source profile.  Their index
    # tokens are retained verbatim; they are not rounded to their nominal
    # load factors or relabelled as the newer 862992 producer.
    "hard5_u011_stage0b": ("0", "0.02749989", "0.05499989", "0.08249989", "0.10999989", "0"),
    "hard5_u012_stage0b": ("0", "0.02999988", "0.05999988", "0.08999988", "0.11999988", "0"),
    "hard5_u013_stage0b": ("0", "0.03249987", "0.06499987", "0.09749987", "0.12999987", "0"),
}
BINARY_LOADS = {
    "hard5_u0115_stage0b": (.028749885000000003, .05749988500000001, .086249885, .114999885, 0.),
    "hard5_u0125_stage0b": (.031249875, .062499875, .093749875, .124999875, 0.),
    # Do not substitute the decimal-print literals below for the source
    # binary64 values captured in the original config receipts.  `fromhex` makes
    # that exact source binary binding visible and portable.
    "hard5_u011_stage0b": (.02749989, .05499989,
                            float.fromhex("0x1.51eb679793daep-4"), .10999989, 0.),
    "hard5_u012_stage0b": (.02999988, .05999988,
                            float.fromhex("0x1.70a3b6d3e71d5p-4"),
                            float.fromhex("0x1.eb84fe81fb983p-4"), 0.),
    "hard5_u013_stage0b": (.03249987, .06499987, .09749987, .12999987, 0.),
}
NEGATIVE_POINTS = {
    ("hard5_u0115_stage0b", "c0058_s05"): {(84858, 1)},
    ("hard5_u0115_stage0b", "c0087_s05"): {(79606, 2), (79606, 3)},
    ("hard5_u0125_stage0b", "c0058_s05"): {(77296, 1), (77296, 2)},
}

# Admission stays finite and explicit.  The 53ce profile carries the recorded
# historical source-audit conclusion for the relevant AMOR, fatigue-update, and
# post-iteration identifiers; the legacy runner reports those identifiers only
# and does not reopen a producer checkout at runtime.  Its three named archives
# had zero H<0 and q<0 support over every hash-verified physical payload, so no
# roundoff repair is licensed for that profile.
ARCHIVE_PRODUCERS = {
    "hard5_u0115_stage0b": PRODUCER,
    "hard5_u0125_stage0b": PRODUCER,
    "hard5_u011_stage0b": LEGACY_PRODUCER,
    "hard5_u012_stage0b": LEGACY_PRODUCER,
    "hard5_u013_stage0b": LEGACY_PRODUCER,
}
ARCHIVE_RULES = {
    "hard5_u0115_stage0b": RULE,
    "hard5_u0125_stage0b": RULE,
    "hard5_u011_stage0b": LEGACY_RULE,
    "hard5_u012_stage0b": LEGACY_RULE,
    "hard5_u013_stage0b": LEGACY_RULE,
}


def precision_bound_row(row, *, archive, schedule):
    """Retain CSV separately; decoder must match the bound config exactly."""
    _require(archive in CSV_LOADS, "unsupported native archive")
    s = int(row["substep"])
    _require(0 <= s <= 5 and len(schedule) == 5, "invalid native substep/schedule")
    _require(tuple(schedule) == BINARY_LOADS[archive], "full precision schedule mismatch")
    _require(row["imposed_displacement"] == CSV_LOADS[archive][s], "unrecognized CSV load token")
    exact = 0. if s == 0 else float(schedule[s-1])
    _require(np.isfinite(exact), "nonfinite load")
    return {**row, "imposed_displacement": repr(exact)}


def adapt_native(decoded, key, mesh, material, *, archive, source_commit,
                 source_timing, native_shape, native_derivative):
    """Check original f before deriving a stable f; certify only known negatives.

    Caller binds immutable index/static/config/payload and full native sequence.
    Every output tensor owns a copy; raw values remain available in decoded.
    """
    _require(archive in ARCHIVE_PRODUCERS, "unsupported native archive")
    _require(source_commit == ARCHIVE_PRODUCERS[archive], "unsupported producer arithmetic")
    _require(mesh.xy.dtype == torch.float64 and mesh.xy.device.type == "cpu",
             "native admission requires CPU float64")
    _require(tuple(getattr(material, n) for n in material.__dataclass_fields__) ==
             (1., .3, .01, .01, .5, 2., 0., 1.), "unsupported source material")
    key.validate()
    expected_key = f"c{key.cycle:04d}_s{key.substep:02d}"
    _require(decoded.source_state_key == expected_key and
             decoded.logical_cycle == key.cycle and decoded.logical_substep == key.substep,
             "native identity mismatch or alias")
    _require(decoded.imposed_displacement == key.load, "full precision load mismatch")
    initial = type(key) is RecoveredInitialKey
    _require(source_timing == ("pre_cycle_committed" if initial else "post_history_commit"),
             "native timing mismatch")
    _require(initial or (type(key) is StateKey and 1 <= key.substep <= 5), "non-native substep")
    for a in (decoded.u_node, decoded.d_node, decoded.history_gp,
              decoded.strain_en_undgr_gp, decoded.strain_en_degr_gp):
        _require(a.dtype == np.float64 and np.isfinite(a).all(), "raw native arrays must be finite float64")
    raw = decoded.history_gp
    _require(raw.shape == (len(mesh.conn), 4, 4), "raw history shape mismatch")
    _require(np.array_equal(raw[..., 0], decoded.strain_en_undgr_gp), "H differs from captured energy")
    _require(np.all(raw[..., 1] >= 0), "negative alpha_bar")
    history = torch.from_numpy(raw.copy())
    alpha = history[..., 1]
    source_f = torch.minimum(torch.ones_like(alpha),
                             (1. - (alpha-material.alpha_t)/(alpha+material.alpha_t)).pow(material.fatigue_power))
    _require(bool(torch.isclose(history[..., 3], source_f,
                               rtol=8*torch.finfo(torch.float64).eps, atol=0).all()),
             "raw f disagrees with producer expression")
    stable_f = carrara_f(alpha, material.alpha_t, material.fatigue_power)
    negative_H = {tuple(map(int, x)) for x in np.argwhere(raw[..., 0] < 0)}
    negative_q = {tuple(map(int, x)) for x in np.argwhere(raw[..., 2] < 0)}
    expected = NEGATIVE_POINTS.get((archive, expected_key), set())
    _require(negative_H == negative_q == expected, "unexpected negative energy support")
    repairs = []
    xy, conn = mesh.xy.numpy(), mesh.conn.numpy()
    for e, g in sorted(expected):
        ids = conn[e]
        proof = certify_negative_energy(xy[ids], decoded.u_node[ids], decoded.d_node[ids],
                                        native_shape[g], native_derivative[g],
                                        float(raw[e,g,0]), float(raw[e,g,2]))
        history[e,g,0] = proof["canonical_H"]
        history[e,g,2] = proof["canonical_q"]
        repairs.append({"element": e, "gp": g, **proof})
    ctor = RecoveredInitialState if initial else State
    u, d = torch.from_numpy(decoded.u_node.copy()), torch.from_numpy(decoded.d_node.copy())
    state = ctor(key, u, d, d.clone(), history[...,:3].clone())
    state.validate(mesh, material)
    # Verify the scope of every change, including bitwise unchanged alpha.
    wanted = raw[...,:3].copy()
    for item in repairs:
        e,g = item["element"], item["gp"]
        wanted[e,g,0], wanted[e,g,2] = item["canonical_H"], item["canonical_q"]
    _require(np.array_equal(state.history.numpy(), wanted), "unexpected history mutation")
    error = torch.abs(history[...,3]-source_f)/source_f
    stable_error = torch.abs(history[...,3]-stable_f)/stable_f
    receipt = {"rule": ARCHIVE_RULES[archive], "source_timing": source_timing, "payload_sha256": decoded.payload_sha256,
               "raw_f_source_max_relative_error": float(error.max()),
               "raw_f_stable_max_relative_error": float(stable_error.max()),
               "repairs": repairs, "raw_arrays_preserved": True}
    return state, receipt
