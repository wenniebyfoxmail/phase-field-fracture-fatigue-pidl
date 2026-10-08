"""Produce the S04-E013 c60s4 conditional UV-derived reference.

This is a fixed-damage, frozen-trial-fatigue solve.  It uses the qualified
Stage0b c60s3 prior and c60s4 accepted target, changes displacement only, and
never performs damage evolution, history refresh, or neural-network training.
The c60 archive has no stored MATLAB residual bridge; that absence is retained
explicitly and is not inferred from the common NumPy/Torch Q4 assembly.
"""
from __future__ import annotations

import argparse
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

from cross_residual import evaluate, q4_shape_data
from damage_conditioned_equilibrium import (
    build_q4_kinematics,
    sens_displacement_boundary_conditions,
    solve_amor_equilibrium,
)
from hard_kkt import assess as hard_assess
from weak_form import assemble, assert_native_gp_shape
from weak_history_audit import compare


US = 0.11999988
PERM = [2, 3, 1, 0]
LOCKS = {
    "qualified": "ecee498054293f66c881a7bcf08a51b1b0315b4e2d11fa20a50c7bbe204f16c5",
    "prior": "b673ac45979882a5b5ac9f8bbb31d293690cb3e9b419b213e948aaee756d81e2",
    "target": "267ea160d607a374359cd62851fe508a0939bbda4fbba24fc9fd83a15c772b65",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm_report(a: np.ndarray, b: np.ndarray, w: np.ndarray, nominal: float) -> dict:
    error = float(np.sqrt(np.sum(w * (a - b) ** 2)))
    reference = float(np.sqrt(np.sum(w * b**2)))
    small = reference <= 1e-12 * nominal
    return {
        "error_norm": error,
        "reference_norm": reference,
        "nominal_norm": nominal,
        "value": error / (nominal if small else reference),
        "kind": "nominal_scale" if small else "relative_l2",
    }


def weighted_quantile(x: np.ndarray, w: np.ndarray, q: float) -> float:
    order = np.argsort(x.ravel(), kind="stable")
    cumulative = np.cumsum(w.ravel()[order])
    return float(x.ravel()[order[np.searchsorted(cumulative, q * cumulative[-1])]])


def load_state(path: Path, cycle: int, substep: int) -> tuple[np.ndarray, ...]:
    expected = LOCKS["prior" if substep == 3 else "target"]
    if digest(path) != expected:
        raise AssertionError(f"unexpected {path.name} SHA256")
    with h5py.File(path) as handle:
        meta = handle["state_metadata"]
        if int(meta["cycle"][0, 0]) != cycle or int(meta["substep"][0, 0]) != substep:
            raise AssertionError("state identity mismatch")
        if not bool(meta["producer_metadata/converged"][0, 0]):
            raise AssertionError("state is not converged")
        values = (
            handle["u_node"][()].T,
            handle["d_node"][()].ravel(),
            handle["history_gp"][()].transpose(2, 1, 0),
            float(meta["imposed_displacement"][0, 0]),
        )
    if not all(np.isfinite(value).all() if isinstance(value, np.ndarray) else np.isfinite(value)
               for value in values):
        raise ValueError("nonfinite state input")
    return values


def run(args: argparse.Namespace) -> None:
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.mkdir(parents=True)
    torch.set_num_threads(1)
    if digest(args.qualified_fields) != LOCKS["qualified"]:
        raise AssertionError("unexpected qualified_fields SHA256")

    qualified = np.load(args.qualified_fields)
    xy = qualified["xy"].copy()
    conn = qualified["conn"].copy()
    free_damage = qualified["free_damage"].copy()
    target_uv, damage, target_history, imposed = load_state(args.target_state, 60, 4)
    _, prior_damage, prior_history, _ = load_state(args.prior_state, 60, 3)
    if target_history.shape != (86408, 4, 4) or prior_history.shape != target_history.shape:
        raise AssertionError("unexpected Q4 history shape")
    if not (np.all(prior_damage >= 0) and np.all(prior_damage <= damage) and np.all(damage <= 1)):
        raise AssertionError("damage feasibility failed")

    # Trial fatigue is reconstructed once from the correct c60s3 accepted history
    # and the original c60s4 target field, then frozen through the UV solve.
    original_weak = assemble(xy, conn, target_uv, damage)
    original_active = (1 - damage[conn] @ original_weak["shape"].T) ** 2 * original_weak["psi"]
    alpha_trial = prior_history[:, :, 1] + np.maximum(original_active - prior_history[:, :, 2], 0)
    fatigue = np.minimum(1.0, (1 - (alpha_trial - 0.5) / (alpha_trial + 0.5)) ** 2)
    immutable = (damage.copy(), prior_damage.copy(), fatigue.copy())

    us = imposed
    tensor = lambda value: torch.tensor(value, dtype=torch.float64)
    shape, _, det = q4_shape_data(tensor(xy), torch.tensor(conn))
    weights = det.numpy()
    energy_scale = float(weights.sum()) * US**2
    kin = build_q4_kinematics(xy, conn)
    assert_native_gp_shape(kin.shape_values[PERM])
    np.testing.assert_allclose(kin.det_jacobians[:, PERM], weights, rtol=1e-12, atol=1e-15)
    bc, bc_values = sens_displacement_boundary_conditions(xy, us)
    np.testing.assert_allclose(target_uv.ravel()[bc], bc_values, rtol=0, atol=1e-12)
    free = np.setdiff1d(np.arange(target_uv.size), bc)
    native_free = qualified["free_uv"]
    mapped_free = (native_free % len(xy)) * 2 + native_free // len(xy)
    np.testing.assert_array_equal(free, np.sort(mapped_free))

    def assess(uv: np.ndarray) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
        rows, _, fields = evaluate(
            tensor(xy), torch.tensor(conn), tensor(uv), tensor(damage),
            tensor(prior_damage), tensor(fatigue), US,
        )
        weak = assemble(xy, conn, uv, damage)
        mass = weak["mass"]
        np.testing.assert_allclose(mass, fields["nodal_mass_fraction"], rtol=1e-12, atol=1e-15)
        agreement = compare(
            weak["force"].ravel()[free], fields["total_grad_uv"].ravel()[free],
            np.repeat(mass, 2)[free], energy_scale / US,
        )
        projected = damage - np.clip(
            damage - fields["total_grad_damage"] / energy_scale / mass, 0, 1
        )
        hard = hard_assess(
            fields["total_grad_damage"], damage, prior_damage,
            free_damage, mass, energy_scale,
        )[0]
        strain = np.einsum(
            "egij,ej->egi", kin.b_matrices, uv.ravel()[kin.element_dofs]
        )[:, PERM, :]
        active = (1 - damage[conn] @ shape.numpy().T) ** 2 * weak["psi"]
        result = {
            "energy": rows[-1]["energy"],
            "elastic_energy": rows[0]["energy"],
            "fracture_energy": rows[1]["energy"],
            "history_energy": rows[2]["energy"],
            "rho_u": rows[-1]["rho_u"],
            "rho_d_all": rows[-1]["box_projected_damage_residual"],
            "rho_d_common": float(np.sqrt(np.sum(mass[free_damage] * projected[free_damage] ** 2))),
            "weak_gradient_agreement": agreement,
            "hard_kkt": hard,
            "archived_matlab_oracle": "NOT_AVAILABLE_C60",
        }
        return result, strain, active, mass

    before, strain_before, active_before, mass = assess(target_uv)
    if before["weak_gradient_agreement"]["status"] != "PASS":
        raise AssertionError("common Q4 UV assembly disagreement")
    solved = solve_amor_equilibrium(
        kin, damage, bc, bc_values, residual_stiffness=0.0,
        initial_displacement=target_uv.ravel(), max_iterations=50,
        tolerance=1e-9, residual_tolerance=1e-8, minimum_pivot_ratio=1e-14,
    )
    polished_uv = solved.displacement.reshape(-1, 2)
    after, strain_after, active_after, _ = assess(polished_uv)
    if after["weak_gradient_agreement"]["status"] != "PASS":
        raise AssertionError("polished common Q4 UV assembly disagreement")
    if not all(np.array_equal(x, y) for x, y in zip((damage, prior_damage, fatigue), immutable)):
        raise AssertionError("immutable state mutated")
    np.testing.assert_allclose(polished_uv.ravel()[bc], bc_values, rtol=0, atol=1e-12)
    if after["fracture_energy"] != before["fracture_energy"] or after["history_energy"] != before["history_energy"]:
        raise AssertionError("non-UV energy changed")

    threshold = weighted_quantile(active_before, weights, 0.99)
    mask = (active_before > 0) & (active_before >= threshold)
    arrays = {
        "xy": xy, "conn": conn, "original_uv": target_uv,
        "equilibrated_uv": polished_uv, "damage": damage,
        "prior_damage": prior_damage, "fatigue": fatigue,
        "strain_before": strain_before, "strain_after": strain_after,
        "active_before": active_before, "active_after": active_after,
        "gp_weights": weights, "original_p99_mask": mask,
    }
    if not all(np.isfinite(value).all() for value in arrays.values()):
        raise ValueError("nonfinite output")
    summary = {
        "schema": "s04-e013-c60-conditional-uv-reference-v1",
        "identity": {
            "cycle": 60, "substep": 4, "prior_substep": 3,
            "timing": "post_history_commit accepted target with own accepted prior",
            "qualified_sha256": LOCKS["qualified"],
            "prior_sha256": LOCKS["prior"], "target_sha256": LOCKS["target"],
            "oracle_kind": "reconstructed_not_archived_MATLAB",
        },
        "before": before, "after": after,
        "uv_block_screen": "PASS" if after["rho_u"] <= 1e-3 else "FAIL",
        "full_teacher": "NOT_QUALIFIED",
        "scope": "fixed accepted damage and frozen trial fatigue; UV block only",
        "delta_uv_mass_rms_over_Us": float(np.sqrt(np.sum(mass[:, None] * (polished_uv - target_uv) ** 2)) / US),
        "strain_tensor": norm_report(
            strain_after, strain_before,
            weights[:, :, None] * np.array([1.0, 1.0, 0.5]), US * np.sqrt(weights.sum()),
        ),
        "active": norm_report(active_after, active_before, weights, US**2 * np.sqrt(weights.sum())),
        "original_p99_threshold": threshold,
        "original_p99_area_fraction": float(weights[mask].sum() / weights.sum()),
        "iterations": solved.iterations,
        "active_set_stable": solved.active_set_stable,
        "solver_normalized_residual": solved.normalized_residual,
        "minimum_pivot_ratio": solved.minimum_pivot_ratio,
        "history_commits": 0, "damage_solves": 0, "training": False,
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pid": os.getpid(),
    }
    (args.out / "before.json").write_text(json.dumps(before, indent=2) + "\n")
    (args.out / "after.json").write_text(json.dumps(after, indent=2) + "\n")
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    np.savez_compressed(args.out / "fields.npz", **arrays)
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualified-fields", type=Path, required=True)
    parser.add_argument("--prior-state", type=Path, required=True)
    parser.add_argument("--target-state", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.qualified_fields, args.prior_state, args.target_state):
        if not path.is_file():
            raise FileNotFoundError(path)
    run(args)


if __name__ == "__main__":
    main()
