#!/usr/bin/env python3
"""Read-only offline diagnostics for the completed D-T2 c5/s4 iterate capture."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import h5py
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def q4_geometry(coords: np.ndarray, conn: np.ndarray):
    points = [
        (1 / math.sqrt(3), 1 / math.sqrt(3)),
        (-1 / math.sqrt(3), 1 / math.sqrt(3)),
        (1 / math.sqrt(3), -1 / math.sqrt(3)),
        (-1 / math.sqrt(3), -1 / math.sqrt(3)),
    ]
    element_coords = coords[conn]
    shape, gradients, determinants = [], [], []
    for xi, eta in points:
        n = 0.25 * np.array([
            (1 - xi) * (1 - eta), (1 + xi) * (1 - eta),
            (1 + xi) * (1 + eta), (1 - xi) * (1 + eta),
        ])
        dn = 0.25 * np.array([
            [-(1 - eta), -(1 - xi)], [1 - eta, -(1 + xi)],
            [1 + eta, 1 + xi], [-(1 + eta), 1 - xi],
        ]).T
        jac = np.einsum("ij,ejk->eik", dn, element_coords)
        det = np.linalg.det(jac)
        inv = np.linalg.inv(jac)
        grad = np.einsum("eij,jk->eik", inv, dn)
        shape.append(n)
        gradients.append(grad)
        determinants.append(det)
    return np.asarray(shape), np.asarray(gradients), np.asarray(determinants)


def tensile_energy(u: np.ndarray, conn: np.ndarray, gradients: np.ndarray) -> np.ndarray:
    nnode = u.size // 2
    ux, uy = u[:nnode], u[nnode:]
    ex = ux[conn]
    ey = uy[conn]
    young, nu = 1.0, 0.3
    shear = young / (2 * (1 + nu))
    lame = young * nu / ((1 + nu) * (1 - 2 * nu))
    cc = np.array([[lame + 2 * shear, lame, 0], [lame, lame + 2 * shear, 0], [0, 0, shear]])
    idev = np.array([[2 / 3, -1 / 3, 0], [-1 / 3, 2 / 3, 0], [0, 0, 0.5]])
    cc_dev = 2 * shear * idev
    result = np.empty((conn.shape[0], 4))
    for gp in range(4):
        grad = gradients[gp]
        strain = np.column_stack((
            np.einsum("ei,ei->e", grad[:, 0, :], ex),
            np.einsum("ei,ei->e", grad[:, 1, :], ey),
            np.einsum("ei,ei->e", grad[:, 1, :], ex) + np.einsum("ei,ei->e", grad[:, 0, :], ey),
        ))
        positive = np.einsum("ei,ij,ej->e", strain, cc, strain)
        deviatoric = np.einsum("ei,ij,ej->e", strain, cc_dev, strain)
        result[:, gp] = 0.5 * np.where(strain[:, 0] + strain[:, 1] >= 0, positive, deviatoric)
    return result


def objective_components(d: np.ndarray, u: np.ndarray, conn: np.ndarray, shape: np.ndarray,
                         gradients: np.ndarray, det: np.ndarray, history_h: np.ndarray,
                         alpha_pre: np.ndarray, prior_degraded: np.ndarray) -> dict:
    d_el = d[conn]
    d_gp = np.column_stack([d_el @ shape[gp] for gp in range(4)])
    grad_sq = np.column_stack([
        np.sum(np.einsum("eij,ej->ei", gradients[gp], d_el) ** 2, axis=1)
        for gp in range(4)
    ])
    psi = tensile_energy(u, conn, gradients)
    h = np.maximum(history_h, psi)
    degraded = (1 - d_gp) ** 2 * psi
    alpha = alpha_pre + np.maximum(degraded - prior_degraded, 0)
    fatigue = np.minimum(1.0, (1 - (alpha - 0.5) / (alpha + 0.5)) ** 2)
    weights = det.T
    gc, ell = 0.008, 0.01
    driving = float(np.sum(weights * h * (1 - d_gp) ** 2))
    local = float(np.sum(weights * (3 / 8) * fatigue * gc / ell * d_gp))
    gradient = float(np.sum(weights * (3 / 8) * fatigue * gc * ell * grad_sq))
    return {
        "history_driving": driving,
        "fatigue_local_fracture": local,
        "fatigue_gradient_fracture": gradient,
        "phase_objective_total": driving + local + gradient,
        "fatigue_factor_min": float(fatigue.min()),
        "fatigue_factor_mean": float(fatigue.mean()),
    }


def analyze(run_root: Path, output_root: Path) -> dict[str, object]:
    run, out = run_root.resolve(), output_root.resolve()
    if out == run or run in out.parents:
        raise SystemExit("output_root must be external to the immutable run")
    out.mkdir(parents=True, exist_ok=False)

    iterate_path = run / "output/qualification/DT2_C5_ITERATES.mat"
    mesh_path = run / "output/mesh_geometry.mat"
    trace_path = run / "output/qualification/C5_STAGGER_TRACE.csv"
    result_path = run / "output/RUN_RESULT.json"
    with h5py.File(mesh_path, "r") as mesh_file:
        coords = mesh_file["mesh_geometry/node_coords"][:].T
        conn = mesh_file["mesh_geometry/connectivity"][:].T.astype(np.int64) - 1
    shape, gradients, det = q4_geometry(coords, conn)
    if np.any(det <= 0):
        raise RuntimeError("nonpositive Q4 Jacobian")

    with h5py.File(run / "output/substeps/cycle_0004.mat", "r") as shard:
        prior_degraded = shard["shard/psi_active_gp"][4, :, :].T
    history_h = np.zeros_like(prior_degraded)
    for cycle in range(1, 5):
        with h5py.File(run / f"output/substeps/cycle_{cycle:04d}.mat", "r") as shard:
            raw = shard["shard/psi_raw_gp"][:]
            history_h = np.maximum(history_h, np.max(raw, axis=0).T)

    rows = []
    process_rows = []
    objective_rows = []
    with h5py.File(iterate_path, "r") as store:
        completed = store["completed_rows"][:].ravel()
        if completed.size != 1000 or not np.all(completed == 1):
            raise RuntimeError("iterate capture is incomplete")
        # MATLAB's v7.3 layout chunks these arrays along node columns.  A single
        # bulk read avoids re-reading every 1000-row HDF5 chunk per iteration.
        dset = store["d_iterates"][:]
        uset = store["u_iterates"][:]
        d_lb = store["d_lb"][0]
        alpha_pre = store["history_pre"][:].T
        previous_delta = None
        previous_support = None
        previous_bound = None
        states = [dset[0]]
        for k in range(1, 1001):
            state = dset[k]
            delta = state - states[-1]
            norm = float(np.linalg.norm(delta))
            bound = np.abs(state - d_lb) <= 1e-10
            if previous_delta is None:
                cosine, angle, jaccard, bound_jaccard = math.nan, math.nan, math.nan, math.nan
            else:
                denom = np.linalg.norm(previous_delta) * norm
                cosine = float(np.dot(previous_delta, delta) / denom) if denom else math.nan
                cosine = min(1.0, max(-1.0, cosine)) if math.isfinite(cosine) else cosine
                angle = math.degrees(math.acos(cosine)) if math.isfinite(cosine) else math.nan
                support = np.abs(delta) >= max(1e-8, 0.01 * np.max(np.abs(delta)))
                union = np.count_nonzero(support | previous_support)
                jaccard = float(np.count_nonzero(support & previous_support) / union) if union else 1.0
                bound_union = np.count_nonzero(bound | previous_bound)
                bound_jaccard = float(np.count_nonzero(bound & previous_bound) / bound_union) if bound_union else 1.0
            support = np.abs(delta) >= max(1e-8, 0.01 * np.max(np.abs(delta)))
            weight = np.abs(delta)
            total_weight = weight.sum()
            if total_weight:
                centroid = np.sum(coords * weight[:, None], axis=0) / total_weight
                width = math.sqrt(float(np.sum(weight * np.sum((coords - centroid) ** 2, axis=1)) / total_weight))
            else:
                centroid, width = np.array([math.nan, math.nan]), math.nan
            lag2 = float(np.linalg.norm(state - states[-2])) if len(states) >= 2 else math.nan
            lag3 = float(np.linalg.norm(state - states[-3])) if len(states) >= 3 else math.nan
            rows.append({"iteration": k, "delta_l2": norm, "adjacent_delta_cosine": cosine,
                         "adjacent_delta_angle_deg": angle, "lag2_state_l2": lag2,
                         "lag3_state_l2": lag3, "update_support_jaccard": jaccard,
                         "lower_bound_active_jaccard": bound_jaccard,
                         "lower_bound_active_count": int(bound.sum())})
            process_rows.append({"iteration": k, "centroid_x": float(centroid[0]),
                                 "centroid_y": float(centroid[1]), "rms_width": width,
                                 "support_count": int(support.sum()),
                                 "support_threshold": float(max(1e-8, 0.01 * np.max(np.abs(delta))))})
            states.append(state)
            if len(states) > 4:
                states.pop(0)
            previous_delta, previous_support, previous_bound = delta, support, bound

        selected = sorted(set([1, 2, 5, 10, 20, 50, 100, 200, 500, 900, 950, 975, 980, 985, 990, 995, 996, 997, 998, 999, 1000]))
        for k in selected:
            item = objective_components(dset[k], uset[k - 1], conn, shape, gradients, det,
                                        history_h, alpha_pre, prior_degraded)
            item["iteration"] = k
            objective_rows.append(item)

    def write_csv(name: str, records: list[dict]):
        with (out / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader(); writer.writerows(records)

    write_csv("iterate_geometry.csv", rows)
    write_csv("process_zone.csv", process_rows)
    write_csv("fatigue_phase_objective.csv", objective_rows)
    tail = rows[-100:]
    med_cos = float(np.nanmedian([r["adjacent_delta_cosine"] for r in tail]))
    med_adj = float(np.median([r["delta_l2"] for r in tail]))
    med_lag2 = float(np.nanmedian([r["lag2_state_l2"] for r in tail]))
    med_lag3 = float(np.nanmedian([r["lag3_state_l2"] for r in tail]))
    if med_cos < -0.8 and med_lag2 < 0.35 * med_adj:
        classification = "NEAR_PERIOD_2_SWITCHING_CONSISTENT_WITH_NEGATIVE_MODE"
    elif med_cos < -0.5:
        classification = "NEGATIVE_MODE_OSCILLATION_WITHOUT_TIGHT_PERIOD_2_CLOSURE"
    else:
        classification = "NONPERIODIC_NONCONTRACTION"
    summary = {
        "schema_version": "toy_road_dt2_offline_diagnostic_v1",
        "run_root": str(run), "run_result": json.loads(result_path.read_text(encoding="utf-8")),
        "classification": classification, "completed_rows": 1000,
        "tail_100": {"median_adjacent_delta_cosine": med_cos,
                     "median_adjacent_delta_angle_deg": float(np.nanmedian([r["adjacent_delta_angle_deg"] for r in tail])),
                     "median_adjacent_delta_l2": med_adj, "median_lag2_state_l2": med_lag2,
                     "median_lag3_state_l2": med_lag3, "lag2_to_adjacent_ratio": med_lag2 / med_adj,
                     "median_update_support_jaccard": float(np.nanmedian([r["update_support_jaccard"] for r in tail])),
                     "median_lower_bound_active_jaccard": float(np.nanmedian([r["lower_bound_active_jaccard"] for r in tail]))},
        "final": {**rows[-1], **process_rows[-1], **objective_rows[-1]},
        "definitions": {
            "process_zone": "abs(delta_d) weighted; support abs(delta_d)>=max(1e-8,0.01*max(abs(delta_d)))",
            "phase_objective": "integral H(1-d)^2 + 3/8*f*Gc/ell*d + 3/8*f*Gc*ell*|grad d|^2; H and f reassembled from locked history and u/d iterates",
            "tot_en": "auxiliary monitor only; excluded from classification and fatigue-consistent objective",
        },
        "source_sha256": {str(p.relative_to(run)): sha256(p) for p in [iterate_path, mesh_path, trace_path, result_path]},
    }
    (out / "diagnostic_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    inventory = {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out / "SHA256SUMS.json").write_text(json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    summary = analyze(args.run_root, args.output_root)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
