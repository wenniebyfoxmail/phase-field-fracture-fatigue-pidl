#!/usr/bin/env python3
"""Frozen Request 28 retrospective plain-versus-enriched observability gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
from scipy.spatial import cKDTree


CASES = {
    "u011": (0.11, "data/u011/c0121_s005_post_commit.mat", "data/u011/c0122_s004_post_commit.mat"),
    "u012": (0.12, "data/u012/c0082_s005_post_commit.mat", "data/u012/c0083_s004_post_commit.mat"),
    "u013": (0.13, "data/u013/c0058_s005_post_commit.mat", "data/u013/c0059_s004_post_commit.mat"),
}
LIGAMENT_LENGTH = 0.5
TARGET_DENOM_TOL = 1e-14
PAIR_UNMATCHED_AREA_MAX = 0.01
FIT_REL_TOL = 1e-14
HISTORY_EPS = 1e-12


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_snapshot(path: Path) -> dict[str, np.ndarray]:
    with h5py.File(path, "r") as handle:
        group = handle["request28_snapshot"]
        return {key: np.asarray(group[key]) for key in group.keys() if isinstance(group[key], h5py.Dataset)}


def mesh(snapshot: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    xy = snapshot["node_coords"].T.astype(float)
    conn = snapshot["connectivity_q4"].T.astype(np.int64) - 1
    quad = xy[conn]
    centres = quad.mean(axis=1)
    x = quad[:, :, 0]
    y = quad[:, :, 1]
    area = 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))
    if np.any(area <= 0) or conn.min() < 0 or conn.max() >= len(xy):
        raise ValueError("invalid native Q4 mesh")
    return xy, conn, centres, area


def q4_centre_strain_norm(xy: np.ndarray, conn: np.ndarray, u_node: np.ndarray) -> np.ndarray:
    xq = xy[conn]
    uq = u_node[conn]
    xc = xq.mean(axis=1, keepdims=True)
    uc = uq.mean(axis=1, keepdims=True)
    dx = xq - xc
    du = uq - uc
    moment = np.einsum("eki,ekj->eij", dx, dx)
    rhs = np.einsum("eki,ekj->eij", dx, du)
    # coefficients[:, coordinate, displacement component]
    coefficients = np.linalg.solve(moment, rhs)
    dux_dx = coefficients[:, 0, 0]
    dux_dy = coefficients[:, 1, 0]
    duy_dx = coefficients[:, 0, 1]
    duy_dy = coefficients[:, 1, 1]
    exy = 0.5 * (dux_dy + duy_dx)
    return np.sqrt(dux_dx**2 + duy_dy**2 + 2.0 * exy**2)


def hidden_targets(prior: dict[str, np.ndarray]) -> tuple[float, float, float]:
    _, _, centres, area = mesh(prior)
    region = centres[:, 0] >= 0.0
    damage = prior["d_elem"].reshape(-1).astype(float)
    history = prior["alpha_bar_elem"].reshape(-1).astype(float)
    weight = 4.0 * damage * (1.0 - damage)
    denom = float(np.sum(area[region] * weight[region]))
    if denom <= TARGET_DENOM_TOL:
        raise ValueError(f"undefined diffuse-process-zone target: sum(A*w)={denom:.17g}")
    z_h = float(np.sum(area[region] * weight[region] * history[region]) / denom)
    z_f = float(np.sum(area[region] * weight[region] * centres[region, 0]) / (LIGAMENT_LENGTH * denom))
    return z_h, z_f, denom


def displacement_representations(event: dict[str, np.ndarray]) -> dict[str, float]:
    xy, conn, centres, area = mesh(event)
    u = event["u_node"].T.astype(float)
    region = centres[:, 0] >= 0.0
    q = q4_centre_strain_norm(xy, conn, u)
    plain_mass = float(np.sum(area[region] * q[region] ** 2))
    if plain_mass <= 0:
        raise ValueError("undefined plain representation")
    p_h = float(np.sqrt(plain_mass / np.sum(area[region])))
    p_f = float(np.sum(area[region] * q[region] ** 2 * centres[region, 0]) / (LIGAMENT_LENGTH * plain_mass))

    positive = np.where(region & (centres[:, 1] > 0.0))[0]
    negative = np.where(region & (centres[:, 1] < 0.0))[0]
    mirrored = centres[positive] * np.array([1.0, -1.0])
    tree = cKDTree(centres[negative])
    distance, nearest_local = tree.query(mirrored, k=1)
    pair_tolerance = float(np.median(np.sqrt(area[region])))
    accepted = distance <= pair_tolerance
    unmatched_area_fraction = float(np.sum(area[positive[~accepted]]) / np.sum(area[positive]))
    if unmatched_area_fraction > PAIR_UNMATCHED_AREA_MAX:
        raise ValueError(
            f"pairing failed: unmatched area {unmatched_area_fraction:.6g} > {PAIR_UNMATCHED_AREA_MAX}"
        )
    plus = positive[accepted]
    minus = negative[nearest_local[accepted]]
    u_cell = u[conn].mean(axis=1)
    separation = np.linalg.norm(centres[plus] - centres[minus], axis=1)
    if np.any(separation <= 0):
        raise ValueError("zero crack-side pair separation")
    opening_density = (u_cell[plus, 1] - u_cell[minus, 1]) / separation
    energy = opening_density**2
    enriched_mass = float(np.sum(area[plus] * energy))
    if enriched_mass <= 0:
        raise ValueError("undefined enriched representation")
    e_h = float(np.sqrt(enriched_mass / np.sum(area[plus])))
    pair_x = 0.5 * (centres[plus, 0] + centres[minus, 0])
    e_f = float(np.sum(area[plus] * energy * pair_x) / (LIGAMENT_LENGTH * enriched_mass))
    return {
        "p_H": p_h,
        "p_F": p_f,
        "e_H": e_h,
        "e_F": e_f,
        "pair_tolerance": pair_tolerance,
        "pair_count": int(len(plus)),
        "unmatched_positive_area_fraction": unmatched_area_fraction,
    }


def affine_predict(train_x: np.ndarray, train_y: np.ndarray, test_x: float) -> tuple[float, float, str]:
    separation = float(train_x[1] - train_x[0])
    tol = FIT_REL_TOL * max(1.0, abs(float(train_x[0])), abs(float(train_x[1])))
    if abs(separation) <= tol:
        return float("nan"), float("nan"), "UNDEFINED_PREDICTOR_SEPARATION"
    slope = float((train_y[1] - train_y[0]) / separation)
    prediction = float(train_y[0] + slope * (test_x - train_x[0]))
    status = "OK" if slope > 0 else "NON_MONOTONE_REPRESENTATION"
    return prediction, slope, status


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(package: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    coordinates: list[dict[str, object]] = []
    inputs: dict[str, str] = {}
    for case, (umax, prior_rel, event_rel) in CASES.items():
        prior_path, event_path = package / prior_rel, package / event_rel
        inputs[str(prior_path)] = sha256(prior_path)
        inputs[str(event_path)] = sha256(event_path)
        # Representation is computed in a function that receives no hidden prior state.
        representation = displacement_representations(read_snapshot(event_path))
        z_h, z_f, target_mass = hidden_targets(read_snapshot(prior_path))
        coordinates.append({
            "case": case,
            "umax": umax,
            "z_H": z_h,
            "z_F": z_f,
            "target_diffuse_mass": target_mass,
            **representation,
        })
    write_csv(output / "physical_coordinates.csv", coordinates)

    rows: list[dict[str, object]] = []
    cases = [row["case"] for row in coordinates]
    for holdout_index, holdout in enumerate(coordinates):
        train = [row for index, row in enumerate(coordinates) if index != holdout_index]
        for target, plain_key, enriched_key in (("z_H", "p_H", "e_H"), ("z_F", "p_F", "e_F")):
            actual = float(holdout[target])
            for method, key in (("plain", plain_key), ("enriched", enriched_key), ("umax", "umax")):
                prediction, slope, status = affine_predict(
                    np.array([float(row[key]) for row in train]),
                    np.array([float(row[target]) for row in train]),
                    float(holdout[key]),
                )
                raw_error = abs(prediction - actual) if np.isfinite(prediction) else float("inf")
                score_error = raw_error / (abs(actual) + HISTORY_EPS) if target == "z_H" else raw_error
                rows.append({
                    "holdout": holdout["case"], "train_cases": "+".join(str(row["case"]) for row in train),
                    "target": target, "method": method, "actual": actual, "prediction": prediction,
                    "raw_absolute_error": raw_error, "score_error": score_error,
                    "slope": slope, "structural_status": status,
                })
            mean_prediction = float(np.mean([float(row[target]) for row in train]))
            raw_error = abs(mean_prediction - actual)
            rows.append({
                "holdout": holdout["case"], "train_cases": "+".join(str(row["case"]) for row in train),
                "target": target, "method": "training_mean", "actual": actual, "prediction": mean_prediction,
                "raw_absolute_error": raw_error,
                "score_error": raw_error / (abs(actual) + HISTORY_EPS) if target == "z_H" else raw_error,
                "slope": float("nan"), "structural_status": "OK",
            })
    write_csv(output / "fold_predictions.csv", rows)

    lookup = {(row["holdout"], row["target"], row["method"]): row for row in rows}
    comparisons = []
    enriched_structural = True
    for case in cases:
        for target in ("z_H", "z_F"):
            enriched = lookup[(case, target, "enriched")]
            plain = lookup[(case, target, "plain")]
            umax = lookup[(case, target, "umax")]
            structural = enriched["structural_status"] == "OK"
            enriched_structural &= structural
            comparisons.append({
                "holdout": case,
                "target": target,
                "enriched_structural_ok": structural,
                "enriched_beats_plain": float(enriched["score_error"]) < float(plain["score_error"]),
                "enriched_beats_umax": float(enriched["score_error"]) < float(umax["score_error"]),
            })
    write_csv(output / "decision_comparisons.csv", comparisons)
    beats_plain = sum(bool(row["enriched_beats_plain"]) for row in comparisons)
    beats_umax = sum(bool(row["enriched_beats_umax"]) for row in comparisons)
    passed = enriched_structural and beats_plain == 6 and beats_umax == 6
    verdict = "ENRICHED_RETROSPECTIVE_ENCODING_POSITIVE" if passed else "ENRICHED_RETROSPECTIVE_ENCODING_NEGATIVE"

    decision = [
        "# Request 28 plain-versus-enriched observability decision", "",
        f"Verdict: **{verdict}**", "",
        f"- Enriched structural calibrations valid and monotone: `{enriched_structural}`",
        f"- Enriched beats PLAIN: `{beats_plain}/6` fold-target comparisons",
        f"- Enriched beats Umax-only: `{beats_umax}/6` fold-target comparisons", "",
        "This is a retrospective event-observability diagnostic using c/s4 first-detect",
        "peak displacement to encode c-1/s5 hidden coordinates.  It is not an",
        "early-warning, transition, RUL, full-field inversion, or KAN result.", "",
    ]
    if passed:
        decision += [
            "The frozen enriched representation passes.  The only authorized next step",
            "is a sparse preregistered earlier-origin observability diagnostic; no learned",
            "model is authorized by this result.", "",
        ]
    else:
        decision += [
            "The combined two-coordinate hypothesis fails.  Per the stop rule, do not",
            "tune the pairing, add a Williams basis, try a second enriched variant, or",
            "escalate this route to KAN/PIDL training on these three trajectories.", "",
        ]
    (output / "decision.md").write_text("\n".join(decision), encoding="utf-8")
    manifest = {
        "experiment": "request28_xdem_observability_gate_20260818",
        "package": str(package),
        "inputs_sha256": inputs,
        "constants": {
            "ligament_length": LIGAMENT_LENGTH,
            "target_denom_tol": TARGET_DENOM_TOL,
            "pair_unmatched_area_max": PAIR_UNMATCHED_AREA_MAX,
            "fit_rel_tol": FIT_REL_TOL,
            "history_eps": HISTORY_EPS,
        },
        "verdict": verdict,
        "outputs_sha256": {name: sha256(output / name) for name in (
            "physical_coordinates.csv", "fold_predictions.csv", "decision_comparisons.csv", "decision.md"
        )},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "beats_plain": beats_plain, "beats_umax": beats_umax}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.package.expanduser().resolve(), args.output.expanduser().resolve())


if __name__ == "__main__":
    main()
