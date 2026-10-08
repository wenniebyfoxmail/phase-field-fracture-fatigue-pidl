"""Adopt and independently recheck existing fixed-damage UV-polished fields.

This script performs no solve. It reassembles UV forces from the archived original
and polished arrays, verifies the frozen mass-dual metric against the parent run
summaries, and adds the c82s5 no-solve control.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch

from cross_residual import evaluate, q4_shape_data
from damage_conditioned_equilibrium import sens_displacement_boundary_conditions
from hard_kkt import assess as hard_assess
from weak_form import assemble


US = 0.11999988
EXPECTED_SHA256 = {
    "qualified": "ecee498054293f66c881a7bcf08a51b1b0315b4e2d11fa20a50c7bbe204f16c5",
    "e011_metrics": "055ebe0f7148a9407fe6487860fb71f7cec93979d3ae20ba26e8e676b2dab60b",
    "c82_summary": "d6ae7eaa36884b72cb71b9ce5d20d3564d8eb117956f8cb537d74455cda86df2",
    "c82_fields": "e079dfbb7243a15cf148bef3799ea56d1bcc10aea5890afd0ef65313566b24df",
    "c83_summary": "eeb38a3f620e2294426b60ac9a706f28c3352859cd2ba414c36cedee3c317206",
    "c83_fields": "24557eaad9ea09f925fdceb8079116427e2bf7602e9626841db46742d6371eae",
    "c82s5": "730a4f928a39de44b9b976cca558645c42dc5c64863b38fd85c6556a38e69691",
    "c83_qualification": "a16107dd44be0772cf06989f737ad0761fcaeb964a794ecda990a20a0ea87342",
    "c83_e010_arrays": "0869216f7e4a2f9e24c570935dacece96c6acde5e7be4ebabefe3a2da15fb6a5",
    "c83_e003_summary": "6fe044ba02640d486520cdda6c687224f838f309d4da10e16d82b2bfe50ada4b",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def close(actual: float, expected: float, *, name: str) -> None:
    if not np.isclose(actual, expected, rtol=1e-9, atol=1e-12):
        raise AssertionError(f"{name}: {actual} != {expected}")


def validate_mesh_and_free_set(xy: np.ndarray, conn: np.ndarray,
                               native_free_uv: np.ndarray) -> np.ndarray:
    if xy.ndim != 2 or xy.shape[1] != 2:
        raise AssertionError(f"xy must have shape (nnode, 2), got {xy.shape}")
    if conn.ndim != 2 or conn.shape[1] != 4 or not np.issubdtype(conn.dtype, np.integer):
        raise AssertionError(f"conn must be integer Q4 connectivity, got {conn.shape}/{conn.dtype}")
    nnode = len(xy)
    if conn.size == 0 or int(conn.min()) < 0 or int(conn.max()) >= nnode:
        raise AssertionError("conn contains an out-of-range node index")
    free = np.asarray(native_free_uv)
    if free.ndim != 1 or not np.issubdtype(free.dtype, np.integer):
        raise AssertionError("free_uv must be a one-dimensional integer array")
    if free.size == 0 or int(free.min()) < 0 or int(free.max()) >= 2 * nnode:
        raise AssertionError("free_uv contains an out-of-range blocked index")
    if np.unique(free).size != free.size:
        raise AssertionError("free_uv contains duplicate indices")
    # MATLAB stores [all-u, all-v]; NumPy force.ravel() stores [u0,v0,u1,v1,...].
    interleaved = (free % nnode) * 2 + free // nnode
    if np.unique(interleaved).size != free.size:
        raise AssertionError("blocked-to-interleaved free_uv mapping is not one-to-one")
    return np.sort(interleaved)


def uv_metrics(xy: np.ndarray, conn: np.ndarray, uv: np.ndarray, damage: np.ndarray,
               native_free_uv: np.ndarray, us: float) -> dict[str, float]:
    if not all(np.isfinite(value).all() for value in (xy, uv, damage)):
        raise ValueError("Nonfinite field passed to UV assembly")
    # macOS Accelerate can emit a spurious matmul RuntimeWarning for this
    # finite 4-entry interpolation; the assembled arrays are checked below.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*matmul.*")
        weak = assemble(xy, conn, uv, damage)
    if not np.isfinite(weak["force"]).all() or not np.isfinite(weak["mass"]).all():
        raise ValueError("Nonfinite UV assembly result")
    if uv.shape != xy.shape or damage.shape != (len(xy),):
        raise AssertionError(f"field shape mismatch: xy={xy.shape}, uv={uv.shape}, damage={damage.shape}")
    if weak["force"].shape != xy.shape or weak["mass"].shape != (len(xy),):
        raise AssertionError("UV assembly returned an unexpected force or mass shape")
    if np.any(weak["mass"] <= 0.0):
        raise AssertionError("UV assembly returned nonpositive nodal mass")
    force = weak["force"].ravel(order="C")
    nnode = len(xy)
    interleaved_free = validate_mesh_and_free_set(xy, conn, native_free_uv)
    mass_uv = np.repeat(weak["mass"], 2)
    tensor_xy = torch.tensor(xy, dtype=torch.float64)
    tensor_conn = torch.tensor(conn, dtype=torch.long)
    _, _, det = q4_shape_data(tensor_xy, tensor_conn)
    if not bool(torch.isfinite(det).all()) or not bool((det > 0.0).all()):
        raise AssertionError("Q4 quadrature contains nonfinite or nonpositive determinants")
    energy_scale = float(det.sum()) * us**2
    if not np.isfinite(energy_scale) or energy_scale <= 0.0:
        raise AssertionError("nonpositive UV energy scale")
    free_force = force[interleaved_free]
    raw_uv_l2 = float(np.linalg.norm(free_force))
    rho_u = float((us / energy_scale) * np.sqrt(np.sum(free_force**2 / mass_uv[interleaved_free])))
    if not np.isfinite(raw_uv_l2) or not np.isfinite(rho_u):
        raise ValueError("Nonfinite UV metric")
    return {"raw_uv_l2": raw_uv_l2, "rho_u": rho_u, "energy_scale": energy_scale}


def validate_target_and_bc(state: str, xy: np.ndarray, original_uv: np.ndarray,
                           derived_uv: np.ndarray, damage: np.ndarray,
                           native_free_uv: np.ndarray) -> dict:
    if original_uv.shape != xy.shape or derived_uv.shape != xy.shape:
        raise AssertionError(f"{state}: original/polished UV shape mismatch")
    if damage.shape != (len(xy),) or not np.isfinite(damage).all():
        raise AssertionError(f"{state}: invalid fixed-damage array")
    if np.any(damage < 0.0) or np.any(damage > 1.0):
        raise AssertionError(f"{state}: fixed damage is outside [0,1]")
    bc, prescribed = sens_displacement_boundary_conditions(xy, US)
    if bc.ndim != 1 or np.unique(bc).size != bc.size:
        raise AssertionError(f"{state}: invalid essential-BC index set")
    original_error = float(np.max(np.abs(original_uv.ravel(order="C")[bc] - prescribed)))
    derived_error = float(np.max(np.abs(derived_uv.ravel(order="C")[bc] - prescribed)))
    if original_error > 1e-12 or derived_error > 1e-12:
        raise AssertionError(
            f"{state}: essential BC mismatch original={original_error} derived={derived_error}"
        )
    expected_free = np.setdiff1d(np.arange(2 * len(xy)), bc)
    native_free = np.asarray(native_free_uv)
    if native_free.ndim != 1 or not np.issubdtype(native_free.dtype, np.integer):
        raise AssertionError(f"{state}: locked free_uv is not a one-dimensional integer array")
    if native_free.size == 0 or int(native_free.min()) < 0 or int(native_free.max()) >= 2 * len(xy):
        raise AssertionError(f"{state}: locked free_uv contains an out-of-range blocked index")
    mapped_free = np.sort((native_free % len(xy)) * 2 + native_free // len(xy))
    if not np.array_equal(expected_free, mapped_free):
        raise AssertionError(f"{state}: essential BC complement differs from locked free_uv")
    return {
        "essential_bc_gate": "PASS",
        "essential_bc_tolerance": 1e-12,
        "essential_bc_count": int(len(bc)),
        "original_bc_max_abs_error": original_error,
        "derived_bc_max_abs_error": derived_error,
        "fixed_damage_gate": "PASS",
    }


def validate_c83_damage_inputs(damage: np.ndarray, qualified: np.lib.npyio.NpzFile,
                               qualification: dict, e010_arrays: np.lib.npyio.NpzFile,
                               e003_summary: dict) -> dict:
    required = {"fem_previous_damage", "fem_ftrial", "free_damage"}
    if not required.issubset(qualified.files):
        raise AssertionError(f"qualified fields missing {sorted(required - set(qualified.files))}")
    previous = qualified["fem_previous_damage"]
    ftrial = qualified["fem_ftrial"]
    free_damage = qualified["free_damage"]
    if previous.shape != damage.shape or ftrial.shape != (86408, 4):
        raise AssertionError("c0083_s04 prior or target ftrial shape mismatch")
    if free_damage.ndim != 1 or not np.issubdtype(free_damage.dtype, np.integer):
        raise AssertionError("c0083_s04 free_damage must be a one-dimensional integer array")
    if free_damage.size == 0 or int(free_damage.min()) < 0 or int(free_damage.max()) >= len(damage):
        raise AssertionError("c0083_s04 free_damage contains an out-of-range index")
    if np.unique(free_damage).size != free_damage.size:
        raise AssertionError("c0083_s04 free_damage contains duplicate indices")
    if not all(np.isfinite(value).all() for value in (previous, damage, ftrial)):
        raise AssertionError("c0083_s04 prior/target/ftrial contains nonfinite values")
    if np.any(previous < 0.0) or np.any(previous > damage) or np.any(damage > 1.0):
        raise AssertionError("c0083_s04 violates exact 0 <= previous_damage <= damage <= 1")
    if "fatigue" not in e010_arrays.files or not np.array_equal(ftrial, e010_arrays["fatigue"]):
        raise AssertionError("c0083_s04 target ftrial differs from the locked E010 target array")
    expected_qualification = (
        "c83 s4 final staggered iteration24; frozen accepted prior history captured before damage/history commit",
        "pre_phase_input/p_field_old",
        "e4270ebd45bf35703dffa8375c2d9b474bdceb303448ddfa6d5fc453956309d4",
    )
    actual_qualification = (
        qualification.get("state"), qualification.get("prior_damage_field"),
        qualification.get("native_sha256"),
    )
    if actual_qualification != expected_qualification:
        raise AssertionError(f"c0083_s04 qualification identity mismatch: {actual_qualification}")
    e003_identity = e003_summary.get("identity", {})
    expected_e003 = (
        86756, 86408, 0.0, 0.0, US, US,
        "production accepted step413 -> c83 peak step414",
        "QUALIFIED_SAME_REPLAY_PRECOMMIT", len(free_damage),
    )
    actual_e003 = (
        e003_identity.get("nodes"), e003_identity.get("elements"),
        e003_identity.get("bottom_uv_max"), e003_identity.get("top_u_max"),
        e003_identity.get("top_v_min"), e003_identity.get("top_v_max"),
        e003_identity.get("state_transition"), e003_summary.get("history_control"),
        e003_summary.get("damage_free_dofs"),
    )
    if actual_e003 != expected_e003:
        raise AssertionError(f"c0083_s04 E003 role/DOF evidence mismatch: {actual_e003}")
    return {
        "strict_feasibility_gate": "PASS",
        "previous_damage_key": "qualified_fields.npz::fem_previous_damage",
        "target_ftrial_key": "qualified_fields.npz::fem_ftrial",
        "free_damage_key": "qualified_fields.npz::free_damage",
        "target_ftrial_crosscheck": "exact_vs_locked_S04-E010_c0083_s04.npz::fatigue",
        "qualification_record": "S04-E003/input_qualification.json + summary.json",
    }


def c83_hard_kkt(xy: np.ndarray, conn: np.ndarray, uv: np.ndarray, damage: np.ndarray,
                 qualified: np.lib.npyio.NpzFile) -> dict:
    tensor = lambda value: torch.tensor(value, dtype=torch.float64)
    _, _, det = q4_shape_data(tensor(xy), torch.tensor(conn, dtype=torch.long))
    energy_scale = float(det.sum()) * US**2
    _, _, fields = evaluate(
        tensor(xy), torch.tensor(conn, dtype=torch.long), tensor(uv), tensor(damage),
        tensor(qualified["fem_previous_damage"]), tensor(qualified["fem_ftrial"]), US,
    )
    return hard_assess(
        fields["total_grad_damage"], damage, qualified["fem_previous_damage"],
        qualified["free_damage"], fields["nodal_mass_fraction"], energy_scale,
    )[0]


def polished_row(state: str, parent_experiment: str, parent_run: str, summary_path: Path,
                 fields_path: Path, qualified: np.lib.npyio.NpzFile,
                 e011: dict[str, dict[str, str]], qualification: dict,
                 c83_e010_arrays: np.lib.npyio.NpzFile, e003_summary: dict) -> dict:
    summary = load_json(summary_path)
    fields = np.load(fields_path)
    required = {"xy", "conn", "original_uv", "equilibrated_uv", "damage"}
    if not required.issubset(fields.files):
        raise AssertionError(f"{fields_path}: missing {sorted(required - set(fields.files))}")
    xy, conn = fields["xy"], fields["conn"]
    if not np.array_equal(xy, qualified["xy"]) or not np.array_equal(conn, qualified["conn"]):
        raise AssertionError(f"{state}: mesh differs from the locked qualified mesh")
    if state == "c0082_s04":
        identity = summary.get("identity", {})
        if (identity.get("cycle"), identity.get("substep"), identity.get("native_sha"),
                identity.get("qualified_sha")) != (
                82, 4, "488c4dff334d8afa7c9c207202283699b89c19e0602b93f3e8eb10f472593e52",
                EXPECTED_SHA256["qualified"]):
            raise AssertionError("c0082_s04 parent summary identity mismatch")
        c83_damage_identity = None
    elif state == "c0083_s04":
        identity = summary.get("identity", {})
        expected = (len(xy), len(conn), "production accepted step413 -> c83 peak step414")
        actual = (identity.get("nodes"), identity.get("elements"), identity.get("state_transition"))
        if actual != expected:
            raise AssertionError(f"c0083_s04 parent summary identity mismatch: {actual}")
        close(identity.get("top_v_min"), US, name="c0083_s04 top_v_min")
        close(identity.get("top_v_max"), US, name="c0083_s04 top_v_max")
        c83_damage_identity = validate_c83_damage_inputs(
            fields["damage"], qualified, qualification, c83_e010_arrays, e003_summary,
        )
    target_bc = validate_target_and_bc(
        state, xy, fields["original_uv"], fields["equilibrated_uv"], fields["damage"],
        qualified["free_uv"],
    )
    original = uv_metrics(xy, conn, fields["original_uv"], fields["damage"], qualified["free_uv"], US)
    derived = uv_metrics(xy, conn, fields["equilibrated_uv"], fields["damage"], qualified["free_uv"], US)
    close(original["rho_u"], summary["before"]["rho_u"], name=f"{state} original rho_u")
    close(derived["rho_u"], summary["after"]["rho_u"], name=f"{state} derived rho_u")
    source = e011[state]
    close(original["raw_uv_l2"], float(source["raw_uv_l2"]), name=f"{state} original raw_uv_l2")
    if derived["rho_u"] > 1e-3:
        raise AssertionError(f"{state}: derived rho_u fails frozen gate")
    field_changes = (
        summary["delta_uv_mass_rms_over_Us"], summary["strain_tensor"]["value"],
        summary["active"]["value"],
    )
    if not all(np.isfinite(value) for value in field_changes):
        raise AssertionError(f"{state}: nonfinite field-change metric")
    before_hard = summary["before"].get("hard_kkt")
    after_hard = summary["after"].get("hard_kkt")
    if state == "c0083_s04":
        before_hard = c83_hard_kkt(xy, conn, fields["original_uv"], fields["damage"], qualified)
        after_hard = c83_hard_kkt(xy, conn, fields["equilibrated_uv"], fields["damage"], qualified)
        hard_kkt_provenance = "recomputed_from_locked_E003_prior_and_target_ftrial"
    else:
        hard_kkt_provenance = "parent_S04-E008_reported_not_recomputed"
    row = {
        "state": state,
        "role": "uv_rebalanced_derived_reference",
        "action": "reuse_existing_no_new_solve",
        "adoption_gate": "PASS",
        "parent_experiment": parent_experiment,
        "parent_run": parent_run,
        "parent_fields_sha256": sha256(fields_path),
        "parent_target_key": f"{state}:original_FEM_peak_s4",
        "original_uv_array_key": "fields.npz::original_uv",
        "derived_uv_array_key": "fields.npz::equilibrated_uv",
        "fixed_damage_array_key": "fields.npz::damage",
        "parent_identity_evidence": (
            "S04-E008 locked native target and qualified parent summary"
            if state == "c0082_s04" else
            "S04-E006 locked E003 qualified target and parent summary"
        ),
        "uv_residual_reference": "deterministic_reassembly_from_locked_parent_fields_and_commit",
        "normalization_Us": US,
        "physical_area": original["energy_scale"] / US**2,
        "energy_scale": original["energy_scale"],
        "original_raw_uv_l2": original["raw_uv_l2"],
        "derived_raw_uv_l2": derived["raw_uv_l2"],
        "original_native_phase_residual": float(source["phase_residual"]),
        "original_native_stagger_sum": float(source["native_stagger_sum"]),
        "derived_native_phase_residual": "NOT_EVALUATED_NO_NATIVE_PHASE_REASSEMBLY",
        "original_rho_u": original["rho_u"],
        "derived_rho_u": derived["rho_u"],
        "uv_screen_before": "PASS" if original["rho_u"] <= 1e-3 else "FAIL",
        "uv_screen_after": "PASS",
        "original_uv_gate": "PASS" if original["rho_u"] <= 1e-3 else "FAIL",
        "polished_conditional_uv_gate": "PASS",
        "box_before": summary["before"]["rho_d_all"],
        "box_after": summary["after"]["rho_d_all"],
        "hard_kkt_raw_before": None if before_hard is None else before_hard["hard_kkt_raw_l2"],
        "hard_kkt_raw_after": None if after_hard is None else after_hard["hard_kkt_raw_l2"],
        "hard_kkt_status_before": "NOT_REPORTED" if before_hard is None else before_hard["status"],
        "hard_kkt_status_after": "NOT_REPORTED" if after_hard is None else after_hard["status"],
        "hard_gate": "NOT_REPORTED" if after_hard is None else after_hard["status"],
        "hard_kkt_provenance": hard_kkt_provenance,
        "delta_uv_mass_rms_over_Us": summary["delta_uv_mass_rms_over_Us"],
        "strain_relative_l2": summary["strain_tensor"]["value"],
        "active_relative_l2": summary["active"]["value"],
        "native_joint_acceptance": "NOT_EVALUATED_FOR_POLISHED_FIELD",
        "full_teacher": "NOT_QUALIFIED",
    }
    row.update(target_bc)
    if c83_damage_identity is not None:
        row.update(c83_damage_identity)
    else:
        row.update({
            "strict_feasibility_gate": "PARENT_REPORTED_NOT_RECOMPUTED",
            "previous_damage_key": "NOT_AVAILABLE_IN_E012_C82_INPUT",
            "target_ftrial_key": "NOT_REQUIRED_FOR_UV_PARTIAL_DERIVATIVE",
            "free_damage_key": "NOT_AVAILABLE_IN_E012_C82_INPUT",
            "target_ftrial_crosscheck": "NOT_APPLICABLE",
            "qualification_record": "S04-E008 parent evidence",
        })
    return row


def control_row(control_path: Path, e011: dict[str, dict[str, str]]) -> dict:
    control = load_json(control_path)
    source = e011["c0082_s05"]
    close(control["rho_u"], float(source["rho_u"]), name="c0082_s05 rho_u")
    if control["uv_screen"] != "PASS":
        raise AssertionError("c0082_s05 must remain the passing no-solve control")
    return {
        "state": "c0082_s05",
        "role": "zero_load_read_only_control",
        "action": "read_only_no_solve",
        "adoption_gate": "PASS_READ_ONLY_CONTROL",
        "parent_experiment": "S04-E010",
        "parent_run": "S04-E010-R001",
        "parent_fields_sha256": "",
        "parent_target_key": "c0082_s05:locked_S04-E010_JSON_control",
        "original_uv_array_key": "NOT_AVAILABLE_PARENT_JSON_ONLY",
        "derived_uv_array_key": "NOT_APPLICABLE",
        "fixed_damage_array_key": "NOT_AVAILABLE_PARENT_JSON_ONLY",
        "parent_identity_evidence": "S04-E010 locked parent JSON; not independently reassembled in E012",
        "uv_residual_reference": "locked_S04-E010_parent_JSON_only",
        "normalization_Us": US,
        "physical_area": "NOT_AVAILABLE_PARENT_JSON_ONLY",
        "energy_scale": "NOT_AVAILABLE_PARENT_JSON_ONLY",
        "original_raw_uv_l2": float(source["raw_uv_l2"]),
        "derived_raw_uv_l2": "NOT_APPLICABLE",
        "original_native_phase_residual": float(source["phase_residual"]),
        "original_native_stagger_sum": float(source["native_stagger_sum"]),
        "derived_native_phase_residual": "NOT_APPLICABLE",
        "original_rho_u": control["rho_u"],
        "derived_rho_u": "NOT_APPLICABLE",
        "uv_screen_before": "PASS",
        "uv_screen_after": "NOT_APPLICABLE",
        "original_uv_gate": "PASS_PARENT_REPORTED",
        "polished_conditional_uv_gate": "NOT_APPLICABLE",
        "box_before": control["box"],
        "box_after": "NOT_APPLICABLE",
        "hard_kkt_raw_before": control["hard_kkt"]["hard_kkt_raw_l2"],
        "hard_kkt_raw_after": "NOT_APPLICABLE",
        "hard_kkt_status_before": control["hard_kkt"]["status"],
        "hard_kkt_status_after": "NOT_APPLICABLE",
        "hard_gate": control["hard_kkt"]["status"],
        "hard_kkt_provenance": "parent_S04-E010_reported_read_only_control",
        "delta_uv_mass_rms_over_Us": 0.0,
        "strain_relative_l2": 0.0,
        "active_relative_l2": 0.0,
        "native_joint_acceptance": "NOT_APPLICABLE_NO_POLISHED_FIELD",
        "full_teacher": "NOT_QUALIFIED",
        "essential_bc_gate": "NOT_REASSEMBLED_PARENT_JSON_ONLY",
        "essential_bc_tolerance": "NOT_APPLICABLE",
        "essential_bc_count": "NOT_APPLICABLE",
        "original_bc_max_abs_error": "NOT_APPLICABLE",
        "derived_bc_max_abs_error": "NOT_APPLICABLE",
        "fixed_damage_gate": "NOT_REASSEMBLED_PARENT_JSON_ONLY",
        "strict_feasibility_gate": "PARENT_REPORTED_NOT_RECOMPUTED",
        "previous_damage_key": "NOT_AVAILABLE_PARENT_JSON_ONLY",
        "target_ftrial_key": "NOT_AVAILABLE_PARENT_JSON_ONLY",
        "free_damage_key": "NOT_AVAILABLE_PARENT_JSON_ONLY",
        "target_ftrial_crosscheck": "NOT_APPLICABLE",
        "qualification_record": "S04-E010 parent evidence",
    }


def plot(rows: list[dict], out: Path) -> None:
    peaks = rows[:2]
    labels = ["c82s4", "c83s4"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    x = np.arange(2)
    axes[0].bar(x - 0.18, [r["original_rho_u"] for r in peaks], 0.36, label="original")
    axes[0].bar(x + 0.18, [r["derived_rho_u"] for r in peaks], 0.36, label="UV-rebalanced")
    axes[0].axhline(1e-3, color="black", linestyle="--", linewidth=1, label=r"$\rho_u=10^{-3}$")
    axes[0].scatter([1.65], [rows[2]["original_rho_u"]], marker="D", color="#2f855a", label="c82s5 control")
    axes[0].set_yscale("log")
    axes[0].set_xticks([0, 1, 1.65], labels + ["c82s5"])
    axes[0].set_ylabel(r"mass-dual $\rho_u$")
    axes[0].set_title("Frozen UV screen")
    axes[0].legend(fontsize=8)

    width = 0.24
    axes[1].bar(x - width, [100*r["delta_uv_mass_rms_over_Us"] for r in peaks], width, label="UV RMS / Us")
    axes[1].bar(x, [100*r["strain_relative_l2"] for r in peaks], width, label="strain rel. L2")
    axes[1].bar(x + width, [100*r["active_relative_l2"] for r in peaks], width, label="active-driver rel. L2")
    axes[1].set_xticks(x, labels)
    axes[1].set_yscale("log")
    axes[1].set_ylabel("change (%)")
    axes[1].set_title("Derived-field correction size")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualified", type=Path, required=True)
    parser.add_argument("--e011-metrics", type=Path, required=True)
    parser.add_argument("--c82-summary", type=Path, required=True)
    parser.add_argument("--c82-fields", type=Path, required=True)
    parser.add_argument("--c83-summary", type=Path, required=True)
    parser.add_argument("--c83-fields", type=Path, required=True)
    parser.add_argument("--c82s5", type=Path, required=True)
    parser.add_argument("--c83-qualification", type=Path, required=True)
    parser.add_argument("--c83-e010-arrays", type=Path, required=True)
    parser.add_argument("--c83-e003-summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    locked_paths = {
        "qualified": args.qualified,
        "e011_metrics": args.e011_metrics,
        "c82_summary": args.c82_summary,
        "c82_fields": args.c82_fields,
        "c83_summary": args.c83_summary,
        "c83_fields": args.c83_fields,
        "c82s5": args.c82s5,
        "c83_qualification": args.c83_qualification,
        "c83_e010_arrays": args.c83_e010_arrays,
        "c83_e003_summary": args.c83_e003_summary,
    }
    for name, path in locked_paths.items():
        actual = sha256(path)
        if actual != EXPECTED_SHA256[name]:
            raise AssertionError(f"{name} SHA256 mismatch: {actual}")
    args.out.mkdir(parents=True, exist_ok=False)
    figures = args.out / "figures"
    figures.mkdir()

    qualified = np.load(args.qualified)
    qualification = load_json(args.c83_qualification)
    c83_e010_arrays = np.load(args.c83_e010_arrays)
    c83_e003_summary = load_json(args.c83_e003_summary)
    with args.e011_metrics.open(newline="", encoding="utf-8") as handle:
        e011 = {row["state"]: row for row in csv.DictReader(handle)}
    required_states = {"c0082_s04", "c0083_s04", "c0082_s05"}
    if not required_states.issubset(e011):
        raise AssertionError(f"E011 metrics missing states: {sorted(required_states - set(e011))}")
    rows = [
        polished_row("c0082_s04", "S04-E008", "S04-E008-R001", args.c82_summary, args.c82_fields, qualified, e011, qualification, c83_e010_arrays, c83_e003_summary),
        polished_row("c0083_s04", "S04-E006", "S04-E006-R001", args.c83_summary, args.c83_fields, qualified, e011, qualification, c83_e010_arrays, c83_e003_summary),
        control_row(args.c82s5, e011),
    ]
    fields = list(rows[0])
    with (args.out / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "operation": "read-only adoption and independent UV reassembly; no solve",
        "inputs": {name: {"path": str(path), "sha256": sha256(path)} for name, path in {
            "qualified": args.qualified,
            "e011_metrics": args.e011_metrics,
            "c82_summary": args.c82_summary,
            "c82_fields": args.c82_fields,
            "c83_summary": args.c83_summary,
            "c83_fields": args.c83_fields,
            "c82s5": args.c82s5,
            "c83_qualification": args.c83_qualification,
            "c83_e010_arrays": args.c83_e010_arrays,
            "c83_e003_summary": args.c83_e003_summary,
        }.items()},
        "rows": len(rows),
        "new_solves": 0,
        "training": False,
        "history_commits": 0,
        "warning_policy": (
            "suppress only RuntimeWarning messages matching matmul inside the finite Q4 UV assembly; "
            "fail closed on nonfinite fields, assembled arrays, scales, and metrics"
        ),
        "metric_contract": {
            "Us": US,
            "Es": "physical_area * Us^2",
            "rho_u": "(Us/Es)*sqrt(sum(free_force^2/interleaved_nodal_mass))",
            "uv_gate": 1e-3,
            "hard_raw_l2_gate": 4e-4,
        },
        "full_teacher": "NOT_QUALIFIED",
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    plot(rows, figures / "uv_rebalanced_reference_audit.png")
    print(json.dumps({"status": "PASS", "rows": len(rows), "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
