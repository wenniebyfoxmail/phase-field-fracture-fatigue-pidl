#!/usr/bin/env python3
"""Evaluate a preselected sealed c86 degradation reconstruction against FEM.

The architecture/seed selection lock must exist before this script runs.  Only
then are c86 diffuse damage, c87/c89 targets, and the frozen temporal operator
opened.  The selected element field is mapped to a bounded nodal field, passed
through eta0 equilibrium, and replayed to the unchanged c87 raw/c89 active
gates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

import meshio
import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from damage_conditioned_equilibrium import (  # noqa: E402
    Q4Kinematics,
    build_q4_kinematics,
    equilibrium_internal_force,
    sens_displacement_boundary_conditions,
    solve_amor_equilibrium,
)
from run_damage_conditioned_equilibrium_gate import (  # noqa: E402
    metric_row,
    rollout,
)
from run_damage_observation_equilibrium_gate import (  # noqa: E402
    build_observation_assimilated_state,
)
from run_fem_mechanism_assimilation_gate import checkpoint_model  # noqa: E402
from spatial_degradation_reconstruction import (  # noqa: E402
    damage_to_z,
    z_to_damage,
)
from train_fem_mechanism_mesh_operator import (  # noqa: E402
    area_weighted_quantile,
    choose_device,
    derived_active_log10,
    load_dataset,
)


PRIOR_CYCLE = 84
OBSERVATION_CYCLE = 86
PROJECTED_CYCLE = 87
TEST_CYCLE = 89
CORE_DAMAGE = 0.95
STEPS_PER_CYCLE = 8
PEAK_STEP = 4
POSTPEAK_STEPS = (5, 6, 7)
FIELD_GATES = {
    "log_mae_max": 0.30,
    "correlation_min": 0.90,
    "absolute_p99_iou_min": 0.70,
    "support_area_ratio_min": 0.50,
    "support_area_ratio_max": 2.00,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def weighted_correlation(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
    normalized = weights / weights.sum()
    a0 = a - np.sum(normalized * a)
    b0 = b - np.sum(normalized * b)
    denominator = np.sqrt(np.sum(normalized * a0 * a0) * np.sum(normalized * b0 * b0))
    return float(np.sum(normalized * a0 * b0) / denominator) if denominator else np.nan


def weighted_iou(
    prediction: np.ndarray,
    target: np.ndarray,
    weights: np.ndarray,
    threshold: float,
    domain: np.ndarray,
) -> tuple[float, float]:
    pred = (prediction >= threshold) & domain
    truth = (target >= threshold) & domain
    intersection = float(weights[pred & truth].sum())
    union = float(weights[pred | truth].sum())
    truth_area = float(weights[truth].sum())
    return (
        intersection / union if union else np.nan,
        float(weights[pred].sum()) / truth_area if truth_area else np.nan,
    )


def element_z_to_nodal_damage(
    element_z: np.ndarray,
    connectivity: np.ndarray,
    element_areas: np.ndarray,
    prior_nodal_damage: np.ndarray,
    visible_nodal_core: np.ndarray,
) -> np.ndarray:
    """Area-average element degradation depth and impose known constraints."""
    element_z = np.asarray(element_z, dtype=np.float64).reshape(-1)
    if len(element_z) != len(connectivity):
        raise ValueError("element z does not match the FEM connectivity")
    weighted_sum = np.zeros(len(prior_nodal_damage), dtype=np.float64)
    weight_sum = np.zeros(len(prior_nodal_damage), dtype=np.float64)
    contribution = np.repeat(element_areas / 4.0, 4)
    np.add.at(
        weighted_sum, connectivity.reshape(-1), np.repeat(element_z, 4) * contribution
    )
    np.add.at(weight_sum, connectivity.reshape(-1), contribution)
    nodal_z = weighted_sum / np.maximum(weight_sum, np.finfo(float).eps)
    prior_z = np.asarray(damage_to_z(prior_nodal_damage), dtype=np.float64)
    nodal_z = np.maximum(nodal_z, prior_z)
    core_z = float(damage_to_z(np.asarray(CORE_DAMAGE)))
    nodal_z[np.asarray(visible_nodal_core, dtype=bool)] = np.maximum(
        nodal_z[np.asarray(visible_nodal_core, dtype=bool)], core_z
    )
    return np.asarray(z_to_damage(nodal_z), dtype=np.float64)


def c86_metrics(
    name: str,
    prediction: np.ndarray,
    target: np.ndarray,
    prior: np.ndarray,
    observed_core: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
) -> dict[str, object]:
    noncore = ~np.asarray(observed_core, dtype=bool)
    weights = areas[noncore]
    weights /= weights.sum()
    pred_d = prediction[noncore]
    target_d = target[noncore]
    pred_z = np.asarray(damage_to_z(prediction))[noncore]
    target_z = np.asarray(damage_to_z(target))[noncore]
    row: dict[str, object] = {
        "method": name,
        "cycle": OBSERVATION_CYCLE,
        "comparison": "postlock_c86_hidden_diffuse_noncore",
        "damage_mae": float(np.sum(weights * np.abs(pred_d - target_d))),
        "damage_rmse": float(np.sqrt(np.sum(weights * (pred_d - target_d) ** 2))),
        "damage_correlation": weighted_correlation(pred_d, target_d, weights),
        "z_mae": float(np.sum(weights * np.abs(pred_z - target_z))),
        "z_rmse": float(np.sqrt(np.sum(weights * (pred_z - target_z) ** 2))),
        "z_correlation": weighted_correlation(pred_z, target_z, weights),
    }
    for threshold in (0.25, 0.50, 0.75):
        iou, ratio = weighted_iou(prediction, target, areas, threshold, noncore)
        row[f"damage_iou_{threshold:.2f}"] = iou
        row[f"damage_area_ratio_{threshold:.2f}"] = ratio

    target_increment = np.asarray(damage_to_z(target)) - np.asarray(damage_to_z(prior))
    pred_increment = np.asarray(damage_to_z(prediction)) - np.asarray(
        damage_to_z(prior)
    )
    support_threshold = 0.02
    iou, ratio = weighted_iou(
        pred_increment, target_increment, areas, support_threshold, noncore
    )
    row["diffuse_increment_iou"] = iou
    row["diffuse_increment_area_ratio"] = ratio
    for label, mask in (
        ("prediction", (pred_increment >= support_threshold) & noncore),
        ("fem", (target_increment >= support_threshold) & noncore),
    ):
        selected_area = areas[mask]
        if selected_area.sum():
            centroid = (
                np.sum(centroids[mask] * selected_area[:, None], axis=0)
                / selected_area.sum()
            )
            row[f"diffuse_{label}_centroid_x"] = float(centroid[0])
            row[f"diffuse_{label}_centroid_y"] = float(centroid[1])
        else:
            row[f"diffuse_{label}_centroid_x"] = np.nan
            row[f"diffuse_{label}_centroid_y"] = np.nan
    return row


def absolute_support(
    prediction: np.ndarray,
    target: np.ndarray,
    areas: np.ndarray,
) -> tuple[float, float, float]:
    threshold = area_weighted_quantile(target, areas, 0.99)
    truth = target >= threshold
    pred = prediction >= threshold
    intersection = float(areas[truth & pred].sum())
    union = float(areas[truth | pred].sum())
    target_area = float(areas[truth].sum())
    return (
        intersection / union if union else np.nan,
        float(areas[pred].sum()) / target_area if target_area else np.nan,
        threshold,
    )


def gate_pass(log_mae: float, correlation: float, iou: float, ratio: float) -> bool:
    return bool(
        log_mae <= FIELD_GATES["log_mae_max"]
        and correlation >= FIELD_GATES["correlation_min"]
        and iou >= FIELD_GATES["absolute_p99_iou_min"]
        and FIELD_GATES["support_area_ratio_min"]
        <= ratio
        <= FIELD_GATES["support_area_ratio_max"]
    )


def top_reaction(
    kinematics: Q4Kinematics,
    nodal_damage: np.ndarray,
    displacement: np.ndarray,
    youngs_modulus: float,
    poisson_ratio: float,
) -> float:
    force = equilibrium_internal_force(
        kinematics,
        nodal_damage,
        displacement,
        youngs_modulus=youngs_modulus,
        poisson_ratio=poisson_ratio,
        residual_stiffness=0.0,
    )
    top = np.flatnonzero(
        np.isclose(kinematics.points[:, 1], kinematics.points[:, 1].max())
    )
    return float(force[2 * top + 1].sum())


def solve_candidate(
    kinematics: Q4Kinematics,
    damage: np.ndarray,
    displacement: float,
    args: argparse.Namespace,
) -> tuple[object, float, float]:
    dofs, values = sens_displacement_boundary_conditions(
        kinematics.points, displacement
    )
    started = time.perf_counter()
    result = solve_amor_equilibrium(
        kinematics,
        damage,
        dofs,
        values,
        youngs_modulus=args.youngs_modulus,
        poisson_ratio=args.poisson_ratio,
        residual_stiffness=0.0,
        max_iterations=args.max_equilibrium_iterations,
        tolerance=args.equilibrium_tolerance,
        residual_tolerance=args.equilibrium_residual_tolerance,
        minimum_pivot_ratio=args.minimum_pivot_ratio,
    )
    reaction = top_reaction(
        kinematics,
        damage,
        result.displacement,
        args.youngs_modulus,
        args.poisson_ratio,
    )
    return result, reaction, time.perf_counter() - started


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-lock", type=Path, required=True)
    parser.add_argument("--prelock-dataset", type=Path, required=True)
    parser.add_argument("--full-mechanism-dataset", type=Path, required=True)
    parser.add_argument("--prior-damage-vtk", type=Path, required=True)
    parser.add_argument("--true-c86-damage-vtk", type=Path, required=True)
    parser.add_argument("--sealed-c86-observation", type=Path, required=True)
    parser.add_argument("--historical-candidates", type=Path, default=None)
    parser.add_argument("--reaction-calibration-lock", type=Path, default=None)
    parser.add_argument("--dic-candidate-manifest", type=Path, default=None)
    parser.add_argument("--background-mode-manifest", type=Path, default=None)
    parser.add_argument("--front-translation-manifest", type=Path, default=None)
    parser.add_argument("--load-displacement", type=Path, required=True)
    parser.add_argument("--multiscale-checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--youngs-modulus", type=float, default=1.0)
    parser.add_argument("--poisson-ratio", type=float, default=0.3)
    parser.add_argument("--max-equilibrium-iterations", type=int, default=50)
    parser.add_argument("--equilibrium-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--equilibrium-residual-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--minimum-pivot-ratio", type=float, default=1.0e-14)
    parser.add_argument("--allow-single-trajectory-diagnostic", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.allow_single_trajectory_diagnostic:
        raise ValueError("single-trajectory scope requires explicit acknowledgement")
    args.out.mkdir(parents=True, exist_ok=True)
    selection = json.loads(args.selection_lock.read_text(encoding="utf-8"))
    reconstruction_path = Path(selection["primary_reconstruction"])
    if not reconstruction_path.is_absolute():
        reconstruction_path = args.selection_lock.parent / reconstruction_path
    if sha256(reconstruction_path) != selection["primary_reconstruction_sha256"]:
        raise RuntimeError("selected c86 reconstruction hash mismatch")
    reconstruction = np.load(reconstruction_path, allow_pickle=False)
    if int(np.asarray(reconstruction["cycle"]).item()) != OBSERVATION_CYCLE:
        raise ValueError("selected reconstruction is not c86")

    prelock = np.load(args.prelock_dataset, allow_pickle=False)
    if int(np.asarray(prelock["hidden_target_max_cycle"]).item()) != 85:
        raise ValueError("prelock dataset contains an invalid hidden-target boundary")
    connectivity = np.asarray(prelock["connectivity"], dtype=np.int32)
    areas = np.asarray(prelock["areas"], dtype=np.float64)
    centroids = np.asarray(prelock["centroids"], dtype=np.float64)

    prior_mesh = meshio.read(args.prior_damage_vtk)
    points = np.asarray(prior_mesh.points, dtype=np.float64)[:, :2]
    prior_connectivity = np.asarray(prior_mesh.cells_dict["quad"], dtype=np.int32)
    prior_nodal_damage = np.clip(
        np.asarray(prior_mesh.point_data["d"], dtype=np.float64).reshape(-1),
        0.0,
        1.0,
    )
    if not np.array_equal(connectivity, prior_connectivity):
        raise ValueError("prelock dataset and prior VTK connectivity differ")
    sealed = np.load(args.sealed_c86_observation, allow_pickle=False)
    visible_nodal_core = np.asarray(sealed["core95"], dtype=bool)
    observed_reaction = float(np.asarray(sealed["peak_reaction"]).item())
    postpeak_displacements = np.asarray(sealed["postpeak_displacement"], dtype=float)
    postpeak_reactions = np.asarray(sealed["postpeak_reaction"], dtype=float)

    predicted_nodal_damage = element_z_to_nodal_damage(
        np.asarray(reconstruction["element_z"]),
        connectivity,
        areas,
        prior_nodal_damage,
        visible_nodal_core,
    )
    selected_element_damage = predicted_nodal_damage[connectivity].mean(axis=1)
    primary_name = selection["primary_tag"]
    candidates: dict[str, np.ndarray] = {
        selection["primary_tag"]: predicted_nodal_damage,
        "c84_persistence": prior_nodal_damage,
    }
    if args.reaction_calibration_lock:
        calibration = json.loads(
            args.reaction_calibration_lock.read_text(encoding="utf-8")
        )
        calibrated_path = args.reaction_calibration_lock.parent / (
            "reaction_calibrated_c86_damage.npz"
        )
        if sha256(calibrated_path) != calibration["field_sha256"]:
            raise RuntimeError("reaction-calibrated damage hash mismatch")
        calibrated = np.load(calibrated_path, allow_pickle=False)
        calibrated_damage = np.asarray(calibrated["nodal_damage"], dtype=float)
        if calibrated_damage.shape != prior_nodal_damage.shape:
            raise ValueError("reaction-calibrated nodal damage shape mismatch")
        primary_name = "reaction_calibrated_" + selection["primary_tag"]
        candidates[primary_name] = calibrated_damage
    if args.dic_candidate_manifest:
        dic_manifest = json.loads(
            args.dic_candidate_manifest.read_text(encoding="utf-8")
        )
        dic_path = args.dic_candidate_manifest.parent / (
            "dic_conditioned_nodal_damage.npz"
        )
        expected_hash = dic_manifest["output_sha256"][dic_path.name]
        if sha256(dic_path) != expected_hash:
            raise RuntimeError("DIC-conditioned nodal damage hash mismatch")
        dic_candidate = np.load(dic_path, allow_pickle=False)
        dic_damage = np.asarray(dic_candidate["nodal_damage"], dtype=float)
        if dic_damage.shape != prior_nodal_damage.shape:
            raise ValueError("DIC-conditioned nodal damage shape mismatch")
        primary_name = "dic_conditioned_nodal_inverse"
        candidates[primary_name] = dic_damage
    if args.background_mode_manifest:
        background_manifest = json.loads(
            args.background_mode_manifest.read_text(encoding="utf-8")
        )
        background_path = args.background_mode_manifest.parent / (
            "background_mode_assimilated_nodal_damage.npz"
        )
        expected_hash = background_manifest["output_sha256"][background_path.name]
        if sha256(background_path) != expected_hash:
            raise RuntimeError("background-mode assimilated damage hash mismatch")
        background_candidate = np.load(background_path, allow_pickle=False)
        background_damage = np.asarray(
            background_candidate["nodal_damage"], dtype=float
        )
        if background_damage.shape != prior_nodal_damage.shape:
            raise ValueError("background-mode nodal damage shape mismatch")
        primary_name = "local_gnn_global_background_assimilation"
        candidates[primary_name] = background_damage
    if args.front_translation_manifest:
        translation_manifest = json.loads(
            args.front_translation_manifest.read_text(encoding="utf-8")
        )
        translation_path = args.front_translation_manifest.parent / (
            "front_translated_nodal_damage.npz"
        )
        expected_hash = translation_manifest["output_sha256"][translation_path.name]
        if sha256(translation_path) != expected_hash:
            raise RuntimeError("front-translated damage hash mismatch")
        translation_candidate = np.load(translation_path, allow_pickle=False)
        translation_damage = np.asarray(
            translation_candidate["nodal_damage"], dtype=float
        )
        if translation_damage.shape != prior_nodal_damage.shape:
            raise ValueError("front-translated nodal damage shape mismatch")
        primary_name = "dic_selected_front_translation"
        candidates[primary_name] = translation_damage
    if args.historical_candidates:
        historical = np.load(args.historical_candidates, allow_pickle=False)
        for name in (
            "beta1_merged_c84_prior",
            "inferred_aligned_merged_c84_prior",
        ):
            candidates[name] = np.asarray(historical[f"damage_{name}"], dtype=float)

    primary_nodal_damage = candidates[primary_name]
    primary_element_damage = primary_nodal_damage[connectivity].mean(axis=1)

    # Post-lock truth opens only after the selection and reconstruction hashes
    # above have been verified.
    true_mesh = meshio.read(args.true_c86_damage_vtk)
    true_damage = np.clip(
        np.asarray(true_mesh.point_data["d"], dtype=float).reshape(-1), 0.0, 1.0
    )
    true_element_damage = true_damage[connectivity].mean(axis=1)
    candidates["full_c86_damage_oracle"] = true_damage
    observed_element_core = visible_nodal_core[connectivity].all(axis=1)
    c84_element_damage = prior_nodal_damage[connectivity].mean(axis=1)

    c86_rows = []
    for name, nodal_damage in candidates.items():
        c86_rows.append(
            c86_metrics(
                name,
                nodal_damage[connectivity].mean(axis=1),
                true_element_damage,
                c84_element_damage,
                observed_element_core,
                centroids,
                areas,
            )
        )
    write_rows(args.out / "c86_reconstruction_metrics.csv", c86_rows)

    kinematics = build_q4_kinematics(points, connectivity)
    equilibrium_rows: list[dict[str, object]] = []
    equilibrium_results = {}
    for name, nodal_damage in candidates.items():
        result, reaction, wall = solve_candidate(
            kinematics,
            nodal_damage,
            float(np.asarray(sealed["peak_displacement"]).item()),
            args,
        )
        equilibrium_results[name] = result
        equilibrium_rows.append(
            {
                "method": name,
                "step": PEAK_STEP,
                "predicted_reaction": reaction,
                "observed_reaction": observed_reaction,
                "relative_reaction_error": abs(reaction - observed_reaction)
                / abs(observed_reaction),
                "iterations": result.iterations,
                "active_set_stable": result.active_set_stable,
                "normalized_residual": result.normalized_residual,
                "minimum_pivot_ratio": result.minimum_pivot_ratio,
                "wall_seconds": wall,
            }
        )

    primary_postpeak_errors = []
    for step, displacement, observed in zip(
        POSTPEAK_STEPS, postpeak_displacements, postpeak_reactions
    ):
        result, reaction, wall = solve_candidate(
            kinematics, primary_nodal_damage, float(displacement), args
        )
        error = abs(reaction - observed) / abs(observed)
        primary_postpeak_errors.append(error)
        equilibrium_rows.append(
            {
                "method": primary_name,
                "step": step,
                "predicted_reaction": reaction,
                "observed_reaction": observed,
                "relative_reaction_error": error,
                "iterations": result.iterations,
                "active_set_stable": result.active_set_stable,
                "normalized_residual": result.normalized_residual,
                "minimum_pivot_ratio": result.minimum_pivot_ratio,
                "wall_seconds": wall,
            }
        )
    write_rows(args.out / "c86_reaction_metrics.csv", equilibrium_rows)

    device = choose_device(args.device)
    data, states, graph = load_dataset(args.full_mechanism_dataset, device)
    state_np = states.detach().cpu().numpy()
    floor = float(np.asarray(data["log_floor"]).item())
    if not np.array_equal(np.asarray(data["connectivity"]), connectivity):
        raise ValueError("full mechanism dataset connectivity differs")
    model, statistics, checkpoint = checkpoint_model(args.multiscale_checkpoint, device)
    if checkpoint.get("args", {}).get("model") != "multiscale":
        raise ValueError("frozen checkpoint is not the multiscale operator")

    downstream_rows: list[dict[str, object]] = []
    predictions: dict[str, np.ndarray] = {
        "selected_nodal_damage": primary_nodal_damage,
        "selected_element_damage": primary_element_damage,
        "uncalibrated_selected_element_damage": selected_element_damage,
        "true_c86_element_damage": true_element_damage,
    }
    gate_results = {}
    for name, nodal_damage in candidates.items():
        result = equilibrium_results[name]
        history_state = (
            state_np[OBSERVATION_CYCLE - 1]
            if name == "full_c86_damage_oracle"
            else state_np[PRIOR_CYCLE - 1]
        )
        element_damage = nodal_damage[connectivity].mean(axis=1)
        generated_c87 = build_observation_assimilated_state(
            history_state,
            element_damage,
            result.tensile_energy_element,
            floor,
        )
        c87_row = metric_row(
            name,
            PROJECTED_CYCLE,
            generated_c87,
            state_np[PROJECTED_CYCLE - 1],
            areas,
        )
        raw_iou, raw_ratio, raw_threshold = absolute_support(
            generated_c87[:, 3], state_np[PROJECTED_CYCLE - 1, :, 3], areas
        )
        c87_pass = gate_pass(
            float(c87_row["log10_psi_raw_mae"]),
            float(c87_row["log10_psi_raw_correlation"]),
            raw_iou,
            raw_ratio,
        )
        c87_row.update(
            {
                "phase": "generated_c87",
                "history_semantics": (
                    "true_c86_oracle"
                    if name == "full_c86_damage_oracle"
                    else "c84_prior"
                ),
                "gate_field": "raw",
                "gate_log_mae": c87_row["log10_psi_raw_mae"],
                "gate_correlation": c87_row["log10_psi_raw_correlation"],
                "gate_absolute_p99_iou": raw_iou,
                "gate_support_area_ratio": raw_ratio,
                "gate_absolute_p99_threshold": raw_threshold,
                "gate_pass": c87_pass,
            }
        )
        downstream_rows.append(c87_row)
        predicted_c89 = rollout(
            model,
            statistics,
            generated_c87,
            PROJECTED_CYCLE,
            TEST_CYCLE,
            graph,
            device,
            states.dtype,
        )
        c89_row = metric_row(
            name, TEST_CYCLE, predicted_c89, state_np[TEST_CYCLE - 1], areas
        )
        active_iou = float(c89_row["absolute_p99_iou"])
        active_ratio = float(c89_row["absolute_support_area_ratio"])
        active_threshold = area_weighted_quantile(
            derived_active_log10(states[TEST_CYCLE - 1].detach().cpu()).numpy(),
            areas,
            0.99,
        )
        c89_pass = gate_pass(
            float(c89_row["derived_active_log_mae"]),
            float(c89_row["derived_active_correlation"]),
            active_iou,
            active_ratio,
        )
        c89_row.update(
            {
                "phase": "multiscale_c89",
                "gate_field": "active",
                "gate_log_mae": c89_row["derived_active_log_mae"],
                "gate_correlation": c89_row["derived_active_correlation"],
                "gate_absolute_p99_iou": active_iou,
                "gate_support_area_ratio": active_ratio,
                "gate_absolute_p99_threshold": active_threshold,
                "gate_pass": c89_pass,
            }
        )
        downstream_rows.append(c89_row)
        predictions[f"{name}_c87"] = generated_c87
        predictions[f"{name}_c89"] = predicted_c89
        gate_results[name] = {
            "c87_raw_pass": c87_pass,
            "c89_active_pass": c89_pass,
            "full_gate_pass": bool(c87_pass and c89_pass),
        }

    # Isolate any remaining history dependence for the selected damage field.
    selected_result = equilibrium_results[primary_name]
    selected_oracle_history_c87 = build_observation_assimilated_state(
        state_np[OBSERVATION_CYCLE - 1],
        primary_element_damage,
        selected_result.tensile_energy_element,
        floor,
    )
    selected_oracle_history_c89 = rollout(
        model,
        statistics,
        selected_oracle_history_c87,
        PROJECTED_CYCLE,
        TEST_CYCLE,
        graph,
        device,
        states.dtype,
    )
    predictions["selected_true_c86_history_control_c87"] = selected_oracle_history_c87
    predictions["selected_true_c86_history_control_c89"] = selected_oracle_history_c89
    for cycle, predicted in (
        (PROJECTED_CYCLE, selected_oracle_history_c87),
        (TEST_CYCLE, selected_oracle_history_c89),
    ):
        control_row = metric_row(
            primary_name + "_true_c86_history_control",
            cycle,
            predicted,
            state_np[cycle - 1],
            areas,
        )
        control_iou = float(control_row["absolute_p99_iou"])
        control_ratio = float(control_row["absolute_support_area_ratio"])
        control_pass = gate_pass(
            float(control_row["derived_active_log_mae"]),
            float(control_row["derived_active_correlation"]),
            control_iou,
            control_ratio,
        )
        control_row.update(
            {
                "phase": "true_c86_history_control",
                "history_semantics": "true_c86_oracle",
                "gate_field": "active",
                "gate_log_mae": control_row["derived_active_log_mae"],
                "gate_correlation": control_row["derived_active_correlation"],
                "gate_absolute_p99_iou": control_iou,
                "gate_support_area_ratio": control_ratio,
                "gate_pass": control_pass,
            }
        )
        downstream_rows.append(control_row)

    write_rows(args.out / "downstream_mechanism_metrics.csv", downstream_rows)
    predictions["state_names"] = np.asarray(
        ["damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw"]
    )
    predictions_path = args.out / "spatial_reconstruction_predictions.npz"
    np.savez_compressed(predictions_path, **predictions)
    primary = primary_name
    primary_peak_error = next(
        float(row["relative_reaction_error"])
        for row in equilibrium_rows
        if row["method"] == primary and row["step"] == PEAK_STEP
    )
    manifest = {
        "claim_class": "observable-conditioned hidden-state identification",
        "fem_reference": "eta0 SENS FEM",
        "selection_lock": str(args.selection_lock.resolve()),
        "selection_lock_sha256": sha256(args.selection_lock),
        "primary_tag": primary,
        "primary_reconstruction_sha256": selection["primary_reconstruction_sha256"],
        "reaction_calibration_lock": (
            str(args.reaction_calibration_lock.resolve())
            if args.reaction_calibration_lock
            else None
        ),
        "reaction_calibration_lock_sha256": (
            sha256(args.reaction_calibration_lock)
            if args.reaction_calibration_lock
            else None
        ),
        "dic_candidate_manifest": (
            str(args.dic_candidate_manifest.resolve())
            if args.dic_candidate_manifest
            else None
        ),
        "dic_candidate_manifest_sha256": (
            sha256(args.dic_candidate_manifest)
            if args.dic_candidate_manifest
            else None
        ),
        "background_mode_manifest": (
            str(args.background_mode_manifest.resolve())
            if args.background_mode_manifest
            else None
        ),
        "background_mode_manifest_sha256": (
            sha256(args.background_mode_manifest)
            if args.background_mode_manifest
            else None
        ),
        "front_translation_manifest": (
            str(args.front_translation_manifest.resolve())
            if args.front_translation_manifest
            else None
        ),
        "front_translation_manifest_sha256": (
            sha256(args.front_translation_manifest)
            if args.front_translation_manifest
            else None
        ),
        "execution_firewall": {
            "architecture_and_seed_locked_before_truth": True,
            "c86_diffuse_damage_opened_postlock": True,
            "c87_c89_targets_opened_postlock": True,
        },
        "primary_c86_peak_reaction_error": primary_peak_error,
        "primary_c86_postpeak_max_reaction_error": max(primary_postpeak_errors),
        "primary_reaction_gate_pass": bool(
            max([primary_peak_error, *primary_postpeak_errors]) <= 0.01
        ),
        "field_gates": FIELD_GATES,
        "gate_results": gate_results,
        "primary_full_gate_pass": gate_results[primary]["full_gate_pass"],
        "trajectory_generalization": False,
        "quarantine": (
            "single FEM trajectory and noiseless FEM-derived visible crack core; "
            "not deployment or cross-case evidence"
        ),
        "artifacts": {
            "c86_metrics": "c86_reconstruction_metrics.csv",
            "reaction_metrics": "c86_reaction_metrics.csv",
            "downstream_metrics": "downstream_mechanism_metrics.csv",
            "predictions": predictions_path.name,
        },
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
