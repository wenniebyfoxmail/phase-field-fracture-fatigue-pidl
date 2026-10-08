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
    return {
        "raw_uv_l2": float(np.linalg.norm(free_force)),
        "rho_u": float((us / energy_scale) * np.sqrt(np.sum(free_force**2 / mass_uv[interleaved_free]))),
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
                 e011: dict[str, dict[str, str]]) -> dict:
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
        if (identity.get("cycle"), identity.get("substep"), identity.get("qualified_sha")) != (
                82, 4, EXPECTED_SHA256["qualified"]):
            raise AssertionError("c0082_s04 parent summary identity mismatch")
    elif state == "c0083_s04":
        identity = summary.get("identity", {})
        expected = (len(xy), len(conn), "production accepted step413 -> c83 peak step414")
        actual = (identity.get("nodes"), identity.get("elements"), identity.get("state_transition"))
        if actual != expected:
            raise AssertionError(f"c0083_s04 parent summary identity mismatch: {actual}")
        close(identity.get("top_v_min"), US, name="c0083_s04 top_v_min")
        close(identity.get("top_v_max"), US, name="c0083_s04 top_v_max")
    original = uv_metrics(xy, conn, fields["original_uv"], fields["damage"], qualified["free_uv"], US)
    derived = uv_metrics(xy, conn, fields["equilibrated_uv"], fields["damage"], qualified["free_uv"], US)
    close(original["rho_u"], summary["before"]["rho_u"], name=f"{state} original rho_u")
    close(derived["rho_u"], summary["after"]["rho_u"], name=f"{state} derived rho_u")
    source = e011[state]
    close(original["raw_uv_l2"], float(source["raw_uv_l2"]), name=f"{state} original raw_uv_l2")
    if derived["rho_u"] > 1e-3:
        raise AssertionError(f"{state}: derived rho_u fails frozen gate")
    before_hard = summary["before"].get("hard_kkt")
    after_hard = summary["after"].get("hard_kkt")
    if state == "c0083_s04":
        before_hard = c83_hard_kkt(xy, conn, fields["original_uv"], fields["damage"], qualified)
        after_hard = c83_hard_kkt(xy, conn, fields["equilibrated_uv"], fields["damage"], qualified)
        hard_kkt_provenance = "recomputed_from_locked_E003_prior_and_target_ftrial"
    else:
        hard_kkt_provenance = "parent_S04-E008_reported_not_recomputed"
    return {
        "state": state,
        "role": "uv_rebalanced_derived_reference",
        "action": "reuse_existing_no_new_solve",
        "parent_experiment": parent_experiment,
        "parent_run": parent_run,
        "parent_fields_sha256": sha256(fields_path),
        "original_raw_uv_l2": original["raw_uv_l2"],
        "derived_raw_uv_l2": derived["raw_uv_l2"],
        "original_native_phase_residual": float(source["phase_residual"]),
        "original_native_stagger_sum": float(source["native_stagger_sum"]),
        "derived_native_phase_residual": "NOT_EVALUABLE_NO_PHASE_SOLVE_OR_NATIVE_REASSEMBLY",
        "original_rho_u": original["rho_u"],
        "derived_rho_u": derived["rho_u"],
        "uv_screen_before": "PASS" if original["rho_u"] <= 1e-3 else "FAIL",
        "uv_screen_after": "PASS",
        "box_before": summary["before"]["rho_d_all"],
        "box_after": summary["after"]["rho_d_all"],
        "hard_kkt_raw_before": None if before_hard is None else before_hard["hard_kkt_raw_l2"],
        "hard_kkt_raw_after": None if after_hard is None else after_hard["hard_kkt_raw_l2"],
        "hard_kkt_status_before": "NOT_REPORTED" if before_hard is None else before_hard["status"],
        "hard_kkt_status_after": "NOT_REPORTED" if after_hard is None else after_hard["status"],
        "hard_kkt_provenance": hard_kkt_provenance,
        "delta_uv_mass_rms_over_Us": summary["delta_uv_mass_rms_over_Us"],
        "strain_relative_l2": summary["strain_tensor"]["value"],
        "active_relative_l2": summary["active"]["value"],
        "full_teacher": "NOT_QUALIFIED",
    }


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
        "parent_experiment": "S04-E010",
        "parent_run": "S04-E010-R001",
        "parent_fields_sha256": "",
        "original_raw_uv_l2": float(source["raw_uv_l2"]),
        "derived_raw_uv_l2": "NOT_APPLICABLE",
        "original_native_phase_residual": float(source["phase_residual"]),
        "original_native_stagger_sum": float(source["native_stagger_sum"]),
        "derived_native_phase_residual": "NOT_APPLICABLE",
        "original_rho_u": control["rho_u"],
        "derived_rho_u": "NOT_APPLICABLE",
        "uv_screen_before": "PASS",
        "uv_screen_after": "NOT_APPLICABLE",
        "box_before": control["box"],
        "box_after": "NOT_APPLICABLE",
        "hard_kkt_raw_before": control["hard_kkt"]["hard_kkt_raw_l2"],
        "hard_kkt_raw_after": "NOT_APPLICABLE",
        "hard_kkt_status_before": control["hard_kkt"]["status"],
        "hard_kkt_status_after": "NOT_APPLICABLE",
        "hard_kkt_provenance": "parent_S04-E010_reported_read_only_control",
        "delta_uv_mass_rms_over_Us": 0.0,
        "strain_relative_l2": 0.0,
        "active_relative_l2": 0.0,
        "full_teacher": "NOT_QUALIFIED",
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
    }
    for name, path in locked_paths.items():
        actual = sha256(path)
        if actual != EXPECTED_SHA256[name]:
            raise AssertionError(f"{name} SHA256 mismatch: {actual}")
    args.out.mkdir(parents=True, exist_ok=False)
    figures = args.out / "figures"
    figures.mkdir()

    qualified = np.load(args.qualified)
    with args.e011_metrics.open(newline="", encoding="utf-8") as handle:
        e011 = {row["state"]: row for row in csv.DictReader(handle)}
    required_states = {"c0082_s04", "c0083_s04", "c0082_s05"}
    if not required_states.issubset(e011):
        raise AssertionError(f"E011 metrics missing states: {sorted(required_states - set(e011))}")
    rows = [
        polished_row("c0082_s04", "S04-E008", "S04-E008-R001", args.c82_summary, args.c82_fields, qualified, e011),
        polished_row("c0083_s04", "S04-E006", "S04-E006-R001", args.c83_summary, args.c83_fields, qualified, e011),
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
        }.items()},
        "rows": len(rows),
        "new_solves": 0,
        "training": False,
        "full_teacher": "NOT_QUALIFIED",
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    plot(rows, figures / "uv_rebalanced_reference_audit.png")
    print(json.dumps({"status": "PASS", "rows": len(rows), "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
