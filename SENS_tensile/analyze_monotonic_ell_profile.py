#!/usr/bin/env python3
"""Build a reaction-only l0 inverse profile from completed forward runs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def read_curve(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        key: np.asarray([float(row[key]) for row in rows], dtype=np.float64)
        for key in rows[0]
        if key != "step"
    }


def nrmse(pred: np.ndarray, truth: np.ndarray, scale: float) -> float:
    return float(np.sqrt(np.mean((pred - truth) ** 2)) / scale)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--truth-repeat", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    truth = read_curve(args.truth / "reaction_curve.csv")
    repeat = read_curve(args.truth_repeat / "reaction_curve.csv")
    if not np.allclose(truth["displacement"], repeat["displacement"]):
        raise ValueError("truth and truth-repeat displacement grids differ")
    scale = max(float(np.max(np.abs(truth["reaction"]))), np.finfo(float).eps)
    indices = np.arange(len(truth["reaction"]))
    fit_mask = indices % 2 == 0
    held_mask = ~fit_mask
    repeat_nrmse = nrmse(repeat["reaction"], truth["reaction"], scale)

    rows = []
    for directory in args.candidate:
        manifest = json.loads(
            (directory / "forward_manifest.json").read_text(encoding="utf-8")
        )
        curve = read_curve(directory / "reaction_curve.csv")
        if not np.allclose(truth["displacement"], curve["displacement"]):
            raise ValueError(f"candidate displacement grid differs: {directory}")
        rows.append(
            {
                "run": str(directory.resolve()),
                "l0": float(manifest["l0"]),
                "w1": float(manifest["w1"]),
                "gc_bar": float(manifest["gc_bar"]),
                "seed": int(manifest["seed"]),
                "fit_nrmse": nrmse(
                    curve["reaction"][fit_mask], truth["reaction"][fit_mask], scale
                ),
                "heldout_nrmse": nrmse(
                    curve["reaction"][held_mask], truth["reaction"][held_mask], scale
                ),
                "all_nrmse": nrmse(curve["reaction"], truth["reaction"], scale),
            }
        )
    rows.sort(key=lambda row: row["l0"])
    best = min(rows, key=lambda row: row["fit_nrmse"])
    summary = {
        "truth_run": str(args.truth.resolve()),
        "truth_repeat_run": str(args.truth_repeat.resolve()),
        "reaction_scale": scale,
        "truth_repeat_nrmse": repeat_nrmse,
        "fit_indices": indices[fit_mask].tolist(),
        "heldout_indices": indices[held_mask].tolist(),
        "best_profile_row": best,
        "profile": rows,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "ell_profile.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.out / "ell_profile.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
