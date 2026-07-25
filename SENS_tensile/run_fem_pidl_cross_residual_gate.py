#!/usr/bin/env python3
"""Evaluate FEM AT1 phase residuals on FEM and PIDL candidate states.

The input is an explicit exchange NPZ.  Missing nodal geometry or state
semantics are hard failures: cell-centroid reconstruction and nearest-neighbour
surrogates are not accepted as FEM residual evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_at1_history_fatigue import (
    AT1FatigueParameters,
    assemble_at1_phase_residual_given_state,
    residual_summary,
)


REQUIRED = {
    "points",
    "cells",
    "cycles",
    "free_phase_nodes",
    "fem_pfield",
    "fem_history_gp",
    "fem_fatigue_gp",
    "pidl_pfield_on_fem_nodes",
    "pidl_raw_gp_on_fem",
    "pidl_fatigue_gp_on_fem",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_exchange(path: Path) -> dict[str, np.ndarray]:
    archive = np.load(path, allow_pickle=False)
    missing = sorted(REQUIRED - set(archive.files))
    if missing:
        raise ValueError(
            "exchange package lacks exact cross-residual assets: " + ", ".join(missing)
        )
    data = {key: np.asarray(archive[key]) for key in archive.files}
    points = data["points"]
    cells = data["cells"].astype(np.int64)
    cycles = data["cycles"].reshape(-1)
    if cells.size and cells.min() == 1 and cells.max() == len(points):
        cells = cells - 1
        data["cells"] = cells
    n_cycle, n_node, n_elem = len(cycles), len(points), len(cells)
    expected = {
        "fem_pfield": (n_cycle, n_node),
        "fem_history_gp": (n_cycle, n_elem, 4),
        "fem_fatigue_gp": (n_cycle, n_elem, 4),
        "pidl_pfield_on_fem_nodes": (n_cycle, n_node),
        "pidl_raw_gp_on_fem": (n_cycle, n_elem, 4),
        "pidl_fatigue_gp_on_fem": (n_cycle, n_elem, 4),
    }
    for key, shape in expected.items():
        if data[key].shape != shape:
            raise ValueError(f"{key} shape {data[key].shape} != required {shape}")
    if data["free_phase_nodes"].ndim != 1:
        raise ValueError("free_phase_nodes must be a one-dimensional index array")
    if "state_kind" in data:
        kinds = {str(value) for value in data["state_kind"].reshape(-1)}
        if kinds != {"peak"}:
            raise ValueError(f"cross-residual package must contain peak states, got {kinds}")
    return data


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exchange-npz", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--gc", type=float, required=True)
    parser.add_argument("--length-scale", type=float, required=True)
    parser.add_argument("--alpha-t", type=float, required=True)
    parser.add_argument("--fatigue-power", type=float, default=2.0)
    parser.add_argument("--residual-stiffness", type=float, default=0.0)
    parser.add_argument("--recovery-penalty", type=float, default=0.0)
    parser.add_argument("--thickness", type=float, default=1.0)
    args = parser.parse_args()

    source = args.exchange_npz.expanduser().resolve()
    output = args.out_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    data = load_exchange(source)
    parameters = AT1FatigueParameters(
        gc=args.gc,
        length_scale=args.length_scale,
        alpha_t=args.alpha_t,
        fatigue_power=args.fatigue_power,
        residual_stiffness=args.residual_stiffness,
        recovery_penalty=args.recovery_penalty,
        thickness=args.thickness,
    )

    points = data["points"]
    cells = data["cells"]
    free = data["free_phase_nodes"].astype(np.int64)
    rows: list[dict] = []
    residual_payload: dict[str, np.ndarray] = {"cycles": data["cycles"]}
    for index, cycle in enumerate(data["cycles"].reshape(-1)):
        candidates = {
            "fem_field__fem_history": (
                data["fem_pfield"][index],
                data["fem_history_gp"][index],
                data["fem_fatigue_gp"][index],
            ),
            "pidl_field__fem_history": (
                data["pidl_pfield_on_fem_nodes"][index],
                data["fem_history_gp"][index],
                data["fem_fatigue_gp"][index],
            ),
            "pidl_field__pidl_current_driver": (
                data["pidl_pfield_on_fem_nodes"][index],
                data["pidl_raw_gp_on_fem"][index],
                data["pidl_fatigue_gp_on_fem"][index],
            ),
            "fem_field__pidl_current_driver": (
                data["fem_pfield"][index],
                data["pidl_raw_gp_on_fem"][index],
                data["pidl_fatigue_gp_on_fem"][index],
            ),
        }
        for label, (pfield, history, fatigue) in candidates.items():
            residual, element = assemble_at1_phase_residual_given_state(
                points, cells, pfield, history, fatigue, parameters
            )
            summary = residual_summary(residual, free)
            rows.append({"cycle": int(cycle), "candidate": label, **summary})
            residual_payload[f"c{int(cycle)}_{label}_nodal"] = residual
            residual_payload[f"c{int(cycle)}_{label}_element"] = element

        difference = data["pidl_pfield_on_fem_nodes"][index] - data["fem_pfield"][index]
        rows[-4]["pidl_vs_fem_damage_rmse"] = float(np.sqrt(np.mean(difference**2)))
        rows[-4]["pidl_vs_fem_damage_linf"] = float(np.max(np.abs(difference)))

    write_csv(output / "cross_residual_summary.csv", rows)
    np.savez_compressed(output / "cross_residual_fields.npz", **residual_payload)
    manifest = {
        "exchange_npz": str(source),
        "exchange_sha256": sha256(source),
        "cycles": [int(value) for value in data["cycles"].reshape(-1)],
        "state_semantics": "cycle-peak; exact Q4 geometry; zero-based connectivity after validation",
        "parameters": parameters.__dict__,
        "candidate_meanings": {
            "fem_field__fem_history": "FEM self residual control",
            "pidl_field__fem_history": "PIDL damage under FEM history and fatigue degradation",
            "pidl_field__pidl_current_driver": "PIDL damage under PIDL current raw driver and degradation",
            "fem_field__pidl_current_driver": "FEM damage under PIDL current raw driver and degradation",
        },
        "important_boundary": "Residual magnitudes are comparable within this common FEM assembly only; PIDL loss values are not numerically compared to FEM residual norms.",
    }
    (output / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
