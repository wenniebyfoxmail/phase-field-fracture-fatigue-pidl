"""Read-only streaming audit of two explicit, identity-bound FEM archives.

Uses existing native decoders. NumPy scans the current float64 contract
predicates; this is not execution of the PyTorch loader or teacher validation.
Only JSONL is written to stdout. No solver, training, repair or archive writes.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import re
import time

import h5py
import numpy as np

from s09_stage0a_capability import (
    S09_E008_CONTEXT, load_state_index, decode_native_static, _mat_numeric,
)
from s09_stage0a_packet import decode_payload, preflight_rows, _reject_external_hdf5_storage

LOCKS = {
    "hard5_u0115_stage0b": (103, .115,
        "hard5_u0115_stage0b_c23cede2bec94515a393aa291c3d6d92",
        "eb1cbacb52252891cb1039ec8df3bcb5cb4ce7ea2fe451476e0e241def10855a",
        "a7edb0e430ae84669e3326f777360e7d73488fa41fad8fa09a038e6bbd26985e",
        "0075cb117676aeb334e185b4149ea7ceefc5799e01b68d0303a56533e86ea7b5"),
    "hard5_u0125_stage0b": (73, .125, S09_E008_CONTEXT.run_id,
        S09_E008_CONTEXT.state_index_sha256, S09_E008_CONTEXT.static_sha256,
        "c4ee5a79831c7a2a327eec976d36a7ae96945ad1cbf67071e38b8d98ddd511de"),
}


def emit(kind, **values):
    print(json.dumps({"kind": kind, **values}, allow_nan=False), flush=True)


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def array_delta(a, b):
    delta = a - b
    return {"minimum": float(delta.min()), "negative_count": int((delta < 0).sum())}


def check_fields(u, d, history, xy, load, alpha_t=.5, power=2.):
    """Strict float64 predicates; no clipping, tolerances added, or mutations."""
    assert all(a.dtype == np.float64 for a in (u, d, history, xy))
    bottom, top = xy[:, 1] == xy[:, 1].min(), xy[:, 1] == xy[:, 1].max()
    eps, tiny = np.finfo(np.float64).eps, np.finfo(np.float64).tiny
    tol = 8 * eps * max(abs(load), tiny)
    bc = {}
    for name, values in (("bottom_ux", u[bottom, 0]), ("bottom_uy", u[bottom, 1]),
                         ("top_ux", u[top, 0]), ("top_uy", u[top, 1] - load)):
        node_ids = np.flatnonzero(bottom if name.startswith("bottom") else top)
        bc[name] = {"max_abs": float(np.abs(values).max()),
                    "count_over_tolerance": int((np.abs(values) > tol).sum()),
                    "argmax_node": int(node_ids[np.abs(values).argmax()])}
    alpha = history[..., 1]
    factor = np.ones_like(alpha)
    active = alpha > alpha_t
    factor[active] = (2 * alpha_t / (alpha[active] + alpha_t)) ** power
    diff = np.abs(history[..., 3] - factor)
    tolerance = 8 * eps * np.abs(factor)
    return {
        "finite": bool(all(np.isfinite(a).all() for a in (u, d, history))),
        "d_min": float(d.min()), "d_max": float(d.max()),
        "d_out_of_bounds": int(((d < 0) | (d > 1)).sum()),
        "history_min": [float(history[..., i].min()) for i in range(3)],
        "history_max": [float(history[..., i].max()) for i in range(3)],
        "history_negative_counts": [int((history[..., i] < 0).sum()) for i in range(3)],
        "bc_tolerance": float(tol), "bc": bc,
        "f_violation_count": int((diff > tolerance).sum()),
        "f_max_abs_error": float(diff.max()),
        "f_max_relative_error": float(np.max(diff / np.maximum(np.abs(factor), tiny))),
        "f_argmax_element_gp": [int(x) for x in np.unravel_index(diff.argmax(), diff.shape)],
    }


def audit(root):
    start = time.monotonic()
    cycles, amplitude, run_id, index_hash, static_hash, config_hash = LOCKS[root.name]
    context = replace(S09_E008_CONTEXT, run_id=run_id,
                      state_index_sha256=index_hash, static_sha256=static_hash)
    rows = load_state_index(root / "state_index.csv", context)
    expected = [f"c{c:04d}_s{s:02d}" for c in range(1, cycles + 1) for s in range(6)]
    assert [r["state_key"] for r in rows] == expected
    by_key = {r["state_key"]: r for r in rows}
    for r in rows:
        c, s = int(r["cycle"]), int(r["substep"])
        assert r["state_key"] == f"c{c:04d}_s{s:02d}"
        alias = s == 0 and c > 1
        key = f"c{c - 1:04d}_s05" if alias else r["state_key"]
        assert r["source_state_key"] == key and r["is_alias"] == str(int(alias))
        assert r["timing"] == ("pre_cycle_committed" if s == 0 else "post_history_commit")
        assert r["converged"] == "1"
        assert float(r["nominal_load_factor"]) == [0, .25, .5, .75, 1, 0][s]
        if alias:
            assert all(r[k] == by_key[key][k] for k in
                       ("payload_file", "payload_sha256", "imposed_displacement"))
    # Whole original manifest: existence only, then dynamic payload hash/decode.
    missing, members = [], []
    for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?(.+)", line)
        assert match, "unrecognized manifest line"
        rel = match[2].replace("\\", "/")
        p = root / rel
        assert p.resolve().is_relative_to(root.resolve()), "manifest path escape"
        members.append(rel)
        if not p.is_file(): missing.append(rel)
    actual = {p.name for p in (root / "states").iterdir() if p.is_file()}
    wanted = {Path(r["payload_file"]).name for r in rows}
    assert actual == wanted, "state directory/index membership mismatch"
    emit("inventory", run=run_id, logical_rows=len(rows), unique_states=len(wanted),
         manifest_members=len(members), missing_manifest_members=missing)
    inventory = preflight_rows(root / "states", rows)
    emit("hash_preflight", run=run_id, verified=len(inventory),
         total_bytes=sum(x["bytes"] for x in inventory), elapsed=time.monotonic()-start)
    static_path = root / "static" / context.static_filename
    static, static_receipt = decode_native_static(static_path, context)
    xy, conn = static["xy"], static["conn"]
    assert np.unique(conn).size == len(xy)
    assert np.all(np.diff(np.sort(conn, axis=1), axis=1) > 0)
    config_bytes = (root / "provenance/config_receipt.mat").read_bytes()
    assert hashlib.sha256(config_bytes).hexdigest() == config_hash
    with h5py.File(static_path, "r") as f, h5py.File(io.BytesIO(config_bytes), "r") as cf:
        _reject_external_hdf5_storage(cf)
        st, cfg = f["stage0b_static"], cf["config_receipt"]
        material = {k: float(_mat_numeric(f, st["material_parameters"], k).item())
                    for k in ("E", "ni", "Gc", "ell", "alpha_T", "p", "res_stiff")}
        material["thickness"] = static["thickness"]
        assert list(material.values()) == [1, .3, .01, .01, .5, 2, 0, 1]
        numeric_config = {}
        for k in ("u_max", "R", "alpha_T", "res_stiff", "n_step", "effective_uy",
                  "nominal_load_factor", "reset_fatigue_after_recovery"):
            a, b = _mat_numeric(f, st["case_config"], k), _mat_numeric(cf, cfg, k)
            assert np.array_equal(a, b), f"config/static mismatch {k}"
            numeric_config[k] = a.reshape(-1).tolist()
        assert numeric_config["u_max"] == [amplitude]
        material_ids = _mat_numeric(f, st["mesh"]["native_mesh"], "elem_material_id")
        assert np.array_equal(np.unique(material_ids), [1.]), "mixed material IDs"
        bottom, top = xy[:, 1] == xy[:, 1].min(), xy[:, 1] == xy[:, 1].max()
        masks = {}
        for k, wanted_mask in (("fix_X", bottom | top), ("fix_Y", bottom), ("disp_Y", top)):
            a = _mat_numeric(f, st["boundary_node_masks"], k).reshape(-1)
            assert np.equal(a, np.floor(a)).all()
            ids = a.astype(np.int64) - 1
            masks[k] = {"count": len(ids), "matches_contract": bool(np.array_equal(
                np.sort(ids), np.flatnonzero(wanted_mask)))}
        # Compare native GP basis/order with q4_shape_data, including native roundoff.
        g = 1 / np.sqrt(3.)
        loc = ((g,g),(-g,g),(g,-g),(-g,-g))
        N = np.array([[.25*(1-x)*(1-y),.25*(1+x)*(1-y),
                       .25*(1+x)*(1+y),.25*(1-x)*(1+y)] for x,y in loc])
        D = np.array([[[-.25*(1-y),.25*(1-y),.25*(1+y),-.25*(1+y)],
                       [-.25*(1-x),-.25*(1+x),.25*(1+x),.25*(1-x)]] for x,y in loc])
        basis_errors = {"N_max_abs": float(np.abs(N-static["shape"]).max()),
                        "dN_max_abs": float(np.abs(D-static["reference_derivative"]).max()),
                        "gauss_points_max_abs": float(np.abs(np.array(loc) -
                            _mat_numeric(f, st["quadrature"], "gauss_pts")).max())}
    source = json.loads((root / "provenance/source_receipt.json").read_text())
    summary = json.loads((root / "run_summary.json").read_text())
    assert source["source_commit"] == context.producer_commit and source["source_dirty"] is False
    assert summary["provenance"]["run_id"] == run_id and summary["sealed"] is True
    assert summary["unique_payload_count"] == len(inventory)
    emit("static", run=run_id, receipt=static_receipt, material=material,
         numeric_config=numeric_config, boundary_masks=masks, basis_errors=basis_errors,
         static_file_sha256=static_hash, config_file_sha256=config_hash,
         minimum_native_gp_weight=float(static["gp_weight"].min()), material_ids=[1])
    previous = None
    for i, row in enumerate(r for r in rows if r["is_alias"] == "0"):
        if time.monotonic()-start > 1200: raise TimeoutError("20-minute audit cap")
        path = root / row["payload_file"]
        kwargs = dict(expected_nodes=len(xy), expected_elements=len(conn))
        strict_error = None
        try:
            state = decode_payload(path, row, **kwargs)
        except ValueError as exc:
            strict_error = str(exc)
            if strict_error != "scalar mismatch: state_metadata/imposed_displacement":
                emit("decode_error", run=run_id, key=row["state_key"], error=strict_error)
                previous = None
                continue
            # Diagnostic only: preserve strict decoder failure, use the exact,
            # hash-bound payload scalar to inspect otherwise available fields.
            payload = path.read_bytes()
            assert hashlib.sha256(payload).hexdigest() == row["payload_sha256"]
            with h5py.File(io.BytesIO(payload), "r") as f:
                _reject_external_hdf5_storage(f)
                raw_load = float(np.asarray(f["state_metadata/imposed_displacement"]).item())
            state = decode_payload(path, {**row, "imposed_displacement": repr(raw_load)}, **kwargs)
        report = check_fields(state.u_node, state.d_node, state.history_gp, xy,
                              state.imposed_displacement)
        s = int(row["substep"])
        intended = 0. if s == 0 else numeric_config["effective_uy"][s-1]
        report.update(raw_load=state.imposed_displacement,
                      index_load=float(row["imposed_displacement"]),
                      load_equals_config=state.imposed_displacement == intended,
                      strict_decoder_error=strict_error,
                      H_vs_undgr_max_abs=float(np.abs(state.history_gp[...,0]-state.strain_en_undgr_gp).max()),
                      q_vs_degr_max_abs=float(np.abs(state.history_gp[...,2]-state.strain_en_degr_gp).max()))
        if previous is not None:
            report["d_delta"] = array_delta(state.d_node, previous.d_node)
            report["alpha_delta"] = array_delta(state.history_gp[...,1], previous.history_gp[...,1])
            expected_increment = np.maximum(state.history_gp[...,2]-previous.history_gp[...,2], 0.)
            report["alpha_update_max_abs_error"] = float(np.abs(
                state.history_gp[...,1]-previous.history_gp[...,1]-expected_increment).max())
        if i == 0:
            report["initial"] = {"u_max_abs": float(np.abs(state.u_node).max()),
                                 "history_max_abs": [float(np.abs(state.history_gp[...,j]).max()) for j in range(4)],
                                 "u_hash": digest(state.u_node), "d_hash": digest(state.d_node),
                                 "history_hash": digest(state.history_gp)}
        emit("state", run=run_id, key=row["state_key"], timing=row["timing"], **report)
        previous = state
    emit("complete", run=run_id, elapsed_seconds=time.monotonic()-start,
         scan="numpy-float64 predicates; not PyTorch loader execution",
         archive_modified=False, training_started=False, solver_started=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", type=Path)
    args = parser.parse_args()
    for root in args.roots:
        audit(root)
