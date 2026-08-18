#!/usr/bin/env python3
"""Audit fixed-calendar exposure inputs and hidden-state ordering only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
from scipy.io import loadmat
from scipy.stats import spearmanr


CASES = {
    "u011": (0.11, "u011/SENS_hard5_u011_eta0_canonical_v1"),
    "u012": (0.12, "u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1"),
    "u013": (0.13, "u013/SENS_hard5_u013_eta0_canonical_v1"),
}
CYCLES = (10, 20, 40)
ELL = 0.01


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def vtk_vector_max(path: Path, vector_name: str = "u") -> tuple[int, float]:
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    point_line = next(line for line in lines if line.strip().startswith("POINTS"))
    point_count = int(point_line.split()[1])
    marker = f"VECTORS {vector_name} "
    start = next(index for index, line in enumerate(lines) if line.strip().startswith(marker)) + 1
    values = np.fromstring("\n".join(lines[start : start + point_count]), sep=" ")
    if values.size != point_count * 3:
        raise ValueError(f"could not parse {vector_name} vectors from {path}")
    return point_count, float(np.max(np.linalg.norm(values.reshape(point_count, 3)[:, :2], axis=1)))


def request28_geometry(package: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    path = package / "data/u012/c0082_s005_post_commit.mat"
    with h5py.File(path, "r") as handle:
        group = handle["request28_snapshot"]
        xy = np.asarray(group["node_coords"]).T.astype(float)
        conn = np.asarray(group["connectivity_q4"]).T.astype(np.int64) - 1
    quad = xy[conn]
    centres = quad.mean(axis=1)
    x, y = quad[:, :, 0], quad[:, :, 1]
    area = 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))
    return xy, conn, centres, area


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--request28-package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = args.baseline_root.expanduser().resolve()
    package = args.request28_package.expanduser().resolve()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    _, _, centres, area = request28_geometry(package)
    h_e = float(np.median(np.sqrt(area)))
    h_roi = max(4.0 * ELL, 2.0 * h_e)
    roi = (centres[:, 0] >= 0.0) & (np.abs(centres[:, 1]) <= h_roi)
    if not np.any(roi):
        raise ValueError("empty frozen ligament ROI")

    asset_rows: list[dict[str, object]] = []
    hidden_rows: list[dict[str, object]] = []
    source_hashes: dict[str, str] = {}
    for case, (umax, relative) in CASES.items():
        case_root = baseline / relative
        c1 = case_root / "peak_load_c1.vtk"
        c1_nodes, c1_u_max = vtk_vector_max(c1)
        source_hashes[str(c1)] = sha256(c1)
        asset_rows.append({
            "case": case, "umax": umax, "cycle": 1, "substep": 4,
            "asset": "peak_load_c1.vtk", "exists": c1.exists(),
            "u_max_norm": c1_u_max, "node_count": c1_nodes,
            "formal_exposure_usable": False, "reason": "reference_only",
        })
        for cycle in CYCLES:
            unload = case_root / f"fields_{cycle:06d}_005.vtk"
            psi = case_root / "psi_fields" / f"cycle_{cycle:04d}.mat"
            unload_nodes, unload_u_max = vtk_vector_max(unload)
            source_hashes[str(unload)] = sha256(unload)
            source_hashes[str(psi)] = sha256(psi)
            asset_rows.append({
                "case": case, "umax": umax, "cycle": cycle, "substep": 5,
                "asset": unload.name, "exists": unload.exists(),
                "u_max_norm": unload_u_max, "node_count": unload_nodes,
                "formal_exposure_usable": False, "reason": "s5_unload_not_s4_peak",
            })
            fields = loadmat(psi, squeeze_me=True, struct_as_record=False)
            required = ("alpha_bar_elem", "d_elem", "f_alpha_elem", "psi_elem")
            if any(np.asarray(fields[key]).reshape(-1).size != area.size for key in required):
                raise ValueError(f"element count mismatch: {psi}")
            hidden_rows.append({
                "case": case, "umax": umax, "cycle": cycle,
                "h_roi": h_roi, "roi_cell_count": int(np.sum(roi)),
                "roi_area": float(np.sum(area[roi])),
                "H_alpha_bar_area_mean": float(np.sum(area[roi] * np.asarray(fields["alpha_bar_elem"]).reshape(-1)[roi]) / np.sum(area[roi])),
                "damage_area_mean": float(np.sum(area[roi] * np.asarray(fields["d_elem"]).reshape(-1)[roi]) / np.sum(area[roi])),
                "fatigue_f_area_mean": float(np.sum(area[roi] * np.asarray(fields["f_alpha_elem"]).reshape(-1)[roi]) / np.sum(area[roi])),
                "psi_area_mean": float(np.sum(area[roi] * np.asarray(fields["psi_elem"]).reshape(-1)[roi]) / np.sum(area[roi])),
            })
    write_csv(output / "asset_audit.csv", asset_rows)

    for cycle in CYCLES:
        selected = sorted((row for row in hidden_rows if row["cycle"] == cycle), key=lambda row: row["umax"])
        rho, _ = spearmanr([row["umax"] for row in selected], [row["H_alpha_bar_area_mean"] for row in selected])
        for row in selected:
            row["H_spearman_vs_umax_at_cycle"] = float(rho)
    write_csv(output / "hidden_state_descriptive.csv", hidden_rows)

    decision = [
        "# Fixed-calendar fatigue-exposure asset pre-gate", "",
        "Verdict: **FORMAL_GATE_BLOCKED_MISSING_S4_PEAK_DISPLACEMENT**", "",
        f"Frozen geometry-only ROI: `x>=0`, `|y|<={h_roi:.8f}`; `h_e={h_e:.8f}`, `ell={ELL}`.",
        "", "Existing c10/c20/c40 VTK files are s5 unload and cannot be used as",
        "displacement observations. Existing psi_fields support only a same-cycle hidden-state",
        "descriptive audit. No exposure coordinate or timing predictor was evaluated.", "",
    ]
    for cycle in CYCLES:
        selected = sorted((row for row in hidden_rows if row["cycle"] == cycle), key=lambda row: row["umax"])
        values = ", ".join(f"{row['case']}={row['H_alpha_bar_area_mean']:.8g}" for row in selected)
        decision.append(f"- c{cycle} H ordering: {values}; Spearman(Umax,H)={selected[0]['H_spearman_vs_umax_at_cycle']:.3f}")
    decision += ["", "Next action: Windows-FEM Request 29, exactly nine c10/c20/c40 s4 post-commit peak states.", ""]
    (output / "decision.md").write_text("\n".join(decision), encoding="utf-8")
    manifest = {
        "claim_class": "asset_and_hidden_state_descriptive_pre_gate_only",
        "formal_gate_run": False,
        "blocked_reason": "missing c10/c20/c40 s4 peak u_node for all Umax",
        "ell": ELL,
        "median_sqrt_q4_area": h_e,
        "h_roi": h_roi,
        "source_sha256": source_hashes,
        "outputs_sha256": {
            name: sha256(output / name)
            for name in ("asset_audit.csv", "hidden_state_descriptive.csv", "decision.md")
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": "FORMAL_GATE_BLOCKED_MISSING_S4_PEAK_DISPLACEMENT", "h_roi": h_roi}, sort_keys=True))


if __name__ == "__main__":
    main()
