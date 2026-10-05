"""Frozen multi-cycle same-field FEM/PIDL residual audit for S04-E005.

This is analysis only.  It evaluates native FEM peak fields with the exact
predecessor PIDL histories declared in the input manifest.  It never advances
history, trains a network, or solves for a new field.
"""
import argparse
import csv
import hashlib
import json
import os
import time
from pathlib import Path

from windows_runtime import configure

configure()

import h5py
import numpy as np
import torch

from audit_inputs import mesh_signature
from cross_residual import CFG, compute_fatigue_degrad, evaluate, q4_shape_data
from weak_form import assemble, assert_native_gp_shape


TAU = 1.0e-3
VECTOR_GATE = 1.0e-9
LOCAL_GROWTH_GATE = 3.0
EXPECTED_NODES = 86756
EXPECTED_ELEMENTS = 86408


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blocked_uv(values):
    values = np.asarray(values).reshape(-1)
    return values.reshape(2, -1).T.copy()


def norm_mass(values, mass):
    return float(np.sqrt(np.sum(values * values / mass)))


def compare_vectors(candidate, reference, mass, force_scale):
    difference = candidate - reference
    error = norm_mass(difference, mass)
    ref = norm_mass(reference, mass)
    denominator = max(ref, force_scale)
    return {
        "max_abs": float(np.max(np.abs(difference))),
        "l2_diff": float(np.linalg.norm(difference)),
        "mass_dual_diff": error,
        "mass_dual_ref": ref,
        "denominator": denominator,
        "scaled_difference": error / denominator,
        "threshold": VECTOR_GATE,
        "status": "PASS" if error <= VECTOR_GATE * denominator else "FAIL",
    }


def verify_file(root, record, key):
    path = root / record[key]
    expected = record[key + "_sha256"]
    if not path.is_file() or sha256(path) != expected:
        raise ValueError(f"Fingerprint mismatch: {key} for c{record['cycle']}")
    return path


def qualify_checkpoint(checkpoint, xy, conn):
    expected_signature = mesh_signature(xy.astype(np.float32), conn)
    if checkpoint.get("mesh_state_signature") != expected_signature:
        raise ValueError("Checkpoint/target mesh signature mismatch")
    required = {
        "history_storage": "q4_gp4",
        "damage_history_storage": "previous_accepted_nodal",
        "history_driver_mode": "current_active",
    }
    for key, value in required.items():
        if checkpoint.get(key) != value:
            raise ValueError(f"Wrong checkpoint state semantic: {key}")
    if tuple(checkpoint["hist_alpha"].shape) != (EXPECTED_NODES,):
        raise ValueError("Wrong checkpoint damage-history shape")
    for key in ("hist_fat", "psi_plus_prev"):
        if tuple(checkpoint[key].shape) != (EXPECTED_ELEMENTS, 4):
            raise ValueError(f"Wrong checkpoint {key} shape")
    if not all(torch.isfinite(checkpoint[k]).all() for k in ("hist_alpha", "hist_fat", "psi_plus_prev")):
        raise ValueError("Nonfinite checkpoint state")
    return expected_signature


def evaluate_cycle(root, record):
    cycle = int(record["cycle"])
    target_path = verify_file(root, record, "target")
    native_path = verify_file(root, record, "native")
    checkpoint_path = verify_file(root, record, "checkpoint")

    with h5py.File(target_path) as handle:
        state = handle["cycle_state"]
        xy = state["node_coords"][()].T
        conn = state["connectivity_q4"][()].T.astype(np.int64) - 1
        uv = state["u_node"][()].T
        damage = state["d_node"][()].ravel()
    if (len(xy), len(conn)) != (EXPECTED_NODES, EXPECTED_ELEMENTS):
        raise ValueError(f"Unexpected native-Q4 dimensions at c{cycle}")

    with h5py.File(native_path) as handle:
        current = handle["converged_peak_solution"]
        previous = handle["pre_phase_input"]
        oracle = handle["matlab_residual"]
        if int(current["cycle"][0, 0]) != cycle or int(current["step"][0, 0]) != 4:
            raise ValueError(f"Wrong native state label at c{cycle}")
        if int(previous["cycle"][0, 0]) != cycle or int(previous["step"][0, 0]) != 4:
            raise ValueError(f"Wrong pre-phase label at c{cycle}")
        if int(previous["staggered_iteration"][0, 0]) != int(current["staggered_iteration"][0, 0]):
            raise ValueError(f"Pre-phase iteration mismatch at c{cycle}")
        for name, value in (("u", uv[:, 0]), ("v", uv[:, 1]), ("d", damage)):
            if not np.array_equal(current[name][()].ravel(), value):
                raise ValueError(f"v1/v2.1 current-field mismatch: c{cycle} {name}")
        if not np.array_equal(previous["p_field_old"][()], oracle["p_field_old"][()]):
            raise ValueError(f"Old damage/oracle mismatch at c{cycle}")
        if not np.array_equal(previous["history_vars_old"][()], oracle["history_vars_old"][()]):
            raise ValueError(f"Old history/oracle mismatch at c{cycle}")
        matlab_uv = blocked_uv(oracle["R_u_full"][()])
        matlab_damage = oracle["R_d_full"][()].ravel()
        free_uv = oracle["free_dof_u"][()].ravel().astype(np.int64) - 1
        free_damage = oracle["free_dof_d"][()].ravel().astype(np.int64) - 1
        if not np.array_equal(oracle["R_u_free"][()].ravel(), matlab_uv.T.ravel()[free_uv]):
            raise ValueError(f"Archived free UV partition mismatch at c{cycle}")
        if not np.array_equal(oracle["R_d_free"][()].ravel(), matlab_damage[free_damage]):
            raise ValueError(f"Archived free damage partition mismatch at c{cycle}")
        staggered_iterations = int(current["staggered_iteration"][0, 0])

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    signature = qualify_checkpoint(checkpoint, xy, conn)
    tensor = lambda value: torch.tensor(value, dtype=torch.float64)
    checkpoint_fatigue = compute_fatigue_degrad(checkpoint["hist_fat"], CFG).detach().double()
    rows, scalars, arrays = evaluate(
        tensor(xy),
        torch.tensor(conn),
        tensor(uv),
        tensor(damage),
        checkpoint["hist_alpha"].clamp(0, 1).double(),
        checkpoint_fatigue,
        float(record["nominal_displacement"]),
    )
    total = rows[-1]

    weak = assemble(xy, conn, uv, damage)
    mass = weak["mass"]
    torch_shape, _, torch_det = q4_shape_data(tensor(xy), torch.tensor(conn))
    assert_native_gp_shape(weak["shape"])
    assert_native_gp_shape(torch_shape.numpy())
    np.testing.assert_allclose(weak["det"], torch_det.numpy(), rtol=1e-12, atol=1e-15)
    np.testing.assert_allclose(arrays["nodal_mass_fraction"], mass, rtol=1e-12, atol=1e-15)

    height = float(xy[:, 1].max() - xy[:, 1].min())
    displacement_scale = float(record["nominal_displacement"])
    energy_scale = float(weak["det"].sum()) * displacement_scale**2 / height**2
    force_scale = energy_scale / displacement_scale
    if abs(scalars["energy_scale"] - energy_scale) > 1e-12:
        raise ValueError(f"Energy-scale drift at c{cycle}")

    interior_nodes = np.flatnonzero((xy[:, 1] != xy[:, 1].min()) & (xy[:, 1] != xy[:, 1].max()))
    expected_free_uv = np.r_[interior_nodes, interior_nodes + len(xy)]
    if not np.array_equal(np.sort(free_uv), expected_free_uv):
        raise ValueError(f"Free UV mask mismatch at c{cycle}")
    if len(free_uv) != 172916 or len(free_damage) != 86505:
        raise ValueError(f"Unexpected free-DOF count at c{cycle}")

    pidl_uv = arrays["total_grad_uv"]
    uv_mass = np.tile(mass, 2)[free_uv]
    vector_check = compare_vectors(
        pidl_uv.T.ravel()[free_uv],
        matlab_uv.T.ravel()[free_uv],
        uv_mass,
        force_scale,
    )
    if vector_check["status"] != "PASS":
        raise ValueError(f"Same-field UV vector gate failed at c{cycle}")

    projected_damage = arrays["projected_damage_residual"]
    cross_box_common = float(np.sqrt(np.sum(mass[free_damage] * projected_damage[free_damage] ** 2)))
    normalized_matlab_damage = matlab_damage / energy_scale
    matlab_projected = damage - np.clip(damage - normalized_matlab_damage / mass, 0.0, 1.0)
    matlab_box_all = float(np.sqrt(np.sum(mass * matlab_projected**2)))
    matlab_box_common = float(np.sqrt(np.sum(mass[free_damage] * matlab_projected[free_damage] ** 2)))
    matlab_rho_u = norm_mass(matlab_uv.T.ravel()[free_uv] * displacement_scale / energy_scale, uv_mass)

    pidl_uv_scaled = pidl_uv * displacement_scale / energy_scale
    matlab_uv_scaled = matlab_uv * displacement_scale / energy_scale
    free_node_mask = arrays["free_uv_mask"].astype(bool)
    pidl_uv_density = np.zeros(len(xy))
    matlab_uv_density = np.zeros(len(xy))
    pidl_uv_density[free_node_mask] = np.sqrt(
        np.sum(pidl_uv_scaled[free_node_mask] ** 2, axis=1) / mass[free_node_mask]
    )
    matlab_uv_density[free_node_mask] = np.sqrt(
        np.sum(matlab_uv_scaled[free_node_mask] ** 2, axis=1) / mass[free_node_mask]
    )

    result = {
        "cycle": cycle,
        "loading_branch": "peak_s4",
        "target_step": int(record["target_step"]),
        "predecessor_step": int(record["predecessor_step"]),
        "pairing_status": "PASS",
        "numerical_equivalence": vector_check["status"],
        "rho_u": float(total["rho_u"]),
        "matlab_rho_u": matlab_rho_u,
        "box_rho_d_all": float(total["box_projected_damage_residual"]),
        "box_rho_d_common_free": cross_box_common,
        "matlab_box_rho_d_all": matlab_box_all,
        "matlab_box_rho_d_common_free": matlab_box_common,
        "uv_stationarity": "PASS" if float(total["rho_u"]) <= TAU else "FAIL",
        "damage_stationarity": "PASS" if cross_box_common <= TAU else "FAIL",
        "stationarity_threshold": TAU,
        "feasibility": "PASS" if scalars["healing_gp_max"] <= 1e-12 else "FAIL",
        "healing_gp_max": float(scalars["healing_gp_max"]),
        "healing_gp_rms": float(scalars["healing_gp_rms"]),
        "energy_scale": energy_scale,
        "force_scale": force_scale,
        "total_area": float(weak["det"].sum()),
        "free_uv_dofs": len(free_uv),
        "common_free_damage_dofs": len(free_damage),
        "staggered_iterations": staggered_iterations,
        "mesh_signature": signature,
        "vector_scaled_difference": vector_check["scaled_difference"],
        "vector_mass_dual_difference": vector_check["mass_dual_diff"],
        "vector_max_abs_difference": vector_check["max_abs"],
    }
    fields = {
        "xy": xy,
        "conn": conn,
        "damage": damage,
        "mass": mass,
        "free_uv_node_mask": free_node_mask,
        "free_damage": free_damage,
        "pidl_uv_scaled": pidl_uv_scaled,
        "matlab_uv_scaled": matlab_uv_scaled,
        "pidl_uv_density": pidl_uv_density,
        "matlab_uv_density": matlab_uv_density,
        "pidl_projected_damage": projected_damage,
        "matlab_projected_damage": matlab_projected,
        "healing_gp": arrays["healing_gp"],
    }
    return result, vector_check, fields


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    started = time.time()
    manifest = json.loads((args.inputs / "manifest.json").read_text())
    if manifest["protocol_revision"] != "20261005-r1-frozen":
        raise ValueError("Wrong protocol revision")
    if manifest["stationarity_threshold"] != TAU or manifest["vector_gate"] != VECTOR_GATE:
        raise ValueError("Frozen threshold mismatch")

    pairing_rows = manifest["candidates"]
    write_csv(args.out / "state_pairing.csv", pairing_rows)
    eligible = [row for row in pairing_rows if row["qualification"] == "ELIGIBLE"]
    if [int(row["cycle"]) for row in eligible] != [76, 82, 83]:
        raise ValueError("Eligible cycle set drift")

    cycle_rows = []
    comparisons = {}
    field_payload = {}
    for record in eligible:
        row, comparison, fields = evaluate_cycle(args.inputs, record)
        cycle_rows.append(row)
        comparisons[str(row["cycle"])] = comparison
        for key, value in fields.items():
            field_payload[f"c{row['cycle']}_{key}"] = value
    write_csv(args.out / "cycle_residuals.csv", cycle_rows)
    np.savez_compressed(args.out / "spatial_fields.npz", **field_payload)

    by_cycle = {row["cycle"]: row for row in cycle_rows}
    local = {}
    for channel, key in (("uv", "rho_u"), ("damage", "box_rho_d_common_free")):
        bridge = by_cycle[76][key]
        terminal = min(by_cycle[82][key], by_cycle[83][key])
        ratio = terminal / max(TAU, bridge)
        local[channel] = {
            "bridge_cycle": 76,
            "terminal_cycles": [82, 83],
            "bridge_value": bridge,
            "terminal_minimum": terminal,
            "ratio": ratio,
            "threshold": LOCAL_GROWTH_GATE,
            "status": "PASS" if ratio >= LOCAL_GROWTH_GATE else "FAIL",
        }
    intervals = []
    for left, right in ((76, 82), (82, 83)):
        item = {"left": left, "right": right, "delta_cycle": right - left}
        for key in ("rho_u", "box_rho_d_common_free"):
            delta = by_cycle[right][key] - by_cycle[left][key]
            item["delta_" + key] = delta
            item["per_cycle_" + key] = delta / (right - left)
        intervals.append(item)
    write_csv(args.out / "interval_changes.csv", intervals)

    trend = {
        "protocol_revision": manifest["protocol_revision"],
        "full_early_terminal_comparison": {
            "status": "NOT_EVALUABLE",
            "reason": "c20/c40/c60 lack same-contract native pre-phase inputs and MATLAB oracle",
            "required_early_cycles": [20, 40, 60],
            "required_terminal_cycles": [82, 83],
        },
        "early_presence": {
            "status": "NOT_EVALUABLE",
            "reason": "No c20/c40/c60 point is qualified under the frozen contract",
        },
        "local_c76_to_terminal": local,
        "local_joint_status": "PASS" if all(v["status"] == "PASS" for v in local.values()) else "FAIL",
        "interpretation_boundary": "Local bridge-to-terminal diagnostic only; cannot locate onset before c76.",
        "numerical_comparisons": comparisons,
        "training": False,
        "optimizer_calls": 0,
        "history_commits": 0,
        "producer_pid": os.getpid(),
        "torch_version": torch.__version__,
        "elapsed_seconds": time.time() - started,
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (args.out / "trend_summary.json").write_text(json.dumps(trend, indent=2) + "\n")
    print(json.dumps({"cycles": cycle_rows, "trend": trend}, indent=2), flush=True)


if __name__ == "__main__":
    main()
