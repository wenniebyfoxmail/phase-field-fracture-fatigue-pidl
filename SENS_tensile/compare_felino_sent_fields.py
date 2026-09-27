#!/usr/bin/env python3
"""Compare one PIDL checkpoint with an exported Felino field checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


def _mapping(src_x, src_y, target_x, target_y, tolerance=1e-9):
    tree = cKDTree(np.column_stack([src_x, src_y]))
    distance, index = tree.query(np.column_stack([target_x, target_y]), k=1)
    if float(np.max(distance)) > tolerance:
        raise ValueError(f"coordinate mapping exceeds tolerance: {np.max(distance)}")
    if len(np.unique(index)) != len(index):
        raise ValueError("coordinate mapping is not one-to-one")
    return index, float(np.max(distance))


def _metrics(pred, ref):
    pred = np.asarray(pred, dtype=float)
    ref = np.asarray(ref, dtype=float)
    err = pred - ref
    pred_std = float(np.std(pred))
    ref_std = float(np.std(ref))
    corr = None
    if pred_std > 0 and ref_std > 0:
        corr = float(np.corrcoef(pred, ref)[0, 1])
    return {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err * err))),
        "max_abs_error": float(np.max(np.abs(err))),
        "correlation": corr,
        "reference_min": float(np.min(ref)),
        "reference_max": float(np.max(ref)),
        "prediction_min": float(np.min(pred)),
        "prediction_max": float(np.max(pred)),
    }


def compare_fields(pidl_path: Path, reference_path: Path) -> dict:
    with np.load(pidl_path) as pidl, np.load(reference_path) as ref:
        node_map, node_distance = _mapping(
            pidl["node_x"], pidl["node_y"], ref["node_x"], ref["node_y"]
        )
        elem_map, elem_distance = _mapping(
            pidl["elem_x"], pidl["elem_y"], ref["elem_x"], ref["elem_y"]
        )
        cycle = int(ref["physical_cycle"][0])
        pidl_cycle = int(round(float(pidl["physical_cycle"][0])))
        if pidl_cycle != cycle:
            raise ValueError(
                f"physical-cycle mismatch: PIDL={pidl_cycle}, Felino={cycle}"
            )
        result = {
            "status": "DIAGNOSTIC_ONLY_NO_PROMOTION_GATE",
            "physical_cycle": cycle,
            "mapping": {
                "node_max_distance": node_distance,
                "element_max_distance": elem_distance,
                "nodes": len(node_map),
                "elements": len(elem_map),
            },
            "fields": {
                "disp_x": _metrics(pidl["disp_x_node"][node_map], ref["disp_x_node"]),
                "disp_y": _metrics(pidl["disp_y_node"][node_map], ref["disp_y_node"]),
                "damage": _metrics(pidl["alpha_node"][node_map], ref["damage_node"]),
                "alpha_bar": _metrics(
                    pidl["hist_fat_elem"][elem_map], ref["alpha_bar_elem"]
                ),
                "fatigue_factor": _metrics(
                    pidl["f_fatigue_elem"][elem_map], ref["fatigue_factor_elem"]
                ),
                "stress_yy": _metrics(
                    pidl["sigma_effective_yy_elem"][elem_map], ref["stress_yy_elem"]
                ),
            },
            "claim_boundary": (
                "Field errors compare a small-strain PIDL state with the locked "
                "finite-strain Felino numerical state; no physical or teacher claim."
            ),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pidl_checkpoint", type=Path)
    parser.add_argument("felino_checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = compare_fields(args.pidl_checkpoint, args.felino_checkpoint)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
