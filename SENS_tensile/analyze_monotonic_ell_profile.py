#!/usr/bin/env python3
"""Build a reaction-only l0 inverse profile from completed forward runs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_run(directory: Path) -> tuple[dict, dict[str, np.ndarray]]:
    manifest_path = directory / "forward_manifest.json"
    run_status = json.loads((directory / "run_status.json").read_text(encoding="utf-8"))
    reaction_status = json.loads(
        (directory / "reaction_status.json").read_text(encoding="utf-8")
    )
    curve_path = directory / "reaction_curve.csv"
    if run_status.get("status") != "COMPLETE":
        raise RuntimeError(f"run is not COMPLETE: {directory}")
    if reaction_status.get("status") != "COMPLETE":
        raise RuntimeError(f"reaction extraction is not COMPLETE: {directory}")
    manifest_hash = sha256(manifest_path)
    if run_status.get("manifest_sha256") != manifest_hash:
        raise RuntimeError(f"manifest hash mismatch: {directory}")
    if reaction_status.get("forward_manifest_sha256") != manifest_hash:
        raise RuntimeError(f"reaction/manifest hash mismatch: {directory}")
    if reaction_status.get("reaction_curve_sha256") != sha256(curve_path):
        raise RuntimeError(f"reaction curve hash mismatch: {directory}")
    if Path(reaction_status.get("reaction_curve", "")).name != curve_path.name:
        raise RuntimeError(
            f"reaction status points to an unexpected curve: {directory}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with curve_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(manifest["displacements"]):
        raise RuntimeError(f"reaction row count mismatch: {directory}")
    if reaction_status.get("row_count") != len(rows) or not rows:
        raise RuntimeError(f"reaction status row count mismatch: {directory}")
    curve = {
        key: np.asarray([float(row[key]) for row in rows], dtype=np.float64)
        for key in rows[0]
        if key != "step"
    }
    if not all(np.all(np.isfinite(values)) for values in curve.values()):
        raise RuntimeError(f"non-finite reaction data: {directory}")
    declared_disp = np.asarray(manifest["displacements"], dtype=np.float64)
    if not np.array_equal(curve["displacement"], declared_disp):
        raise RuntimeError(f"curve/manifest displacement mismatch: {directory}")
    return manifest, curve


def nrmse(pred: np.ndarray, truth: np.ndarray, scale: float) -> float:
    return float(np.sqrt(np.mean((pred - truth) ** 2)) / scale)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--truth-repeat", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    truth_manifest, truth = read_run(args.truth)
    repeat_manifest, repeat = read_run(args.truth_repeat)
    identity_keys = [
        "base_source_commit",
        "executed_commit",
        "executed_worktree_dirty",
        "gc_bar",
        "mat_E",
        "mat_nu",
        "PFF_model",
        "se_split",
        "tol_ir",
        "fatigue_on",
        "loading_type",
        "hidden_layers",
        "neurons",
        "activation",
        "init_coeff",
        "rprop_epochs",
        "lbfgs_epochs",
        "coarse_mesh_sha256",
        "fine_mesh_sha256",
        "diagnostic_prefix_only",
    ]
    if any(truth_manifest[key] != repeat_manifest[key] for key in identity_keys):
        raise ValueError("truth and truth-repeat fixed settings differ")
    if truth_manifest["l0"] != repeat_manifest["l0"]:
        raise ValueError("truth repeat must use the same l0")
    if truth_manifest["seed"] == repeat_manifest["seed"]:
        raise ValueError("truth repeat must use an independent seed")
    if truth_manifest["executed_worktree_dirty"]:
        raise ValueError("inverse profile refuses evidence from a dirty worktree")
    if not np.isclose(
        truth_manifest["w1"] * truth_manifest["l0"],
        truth_manifest["gc_bar"],
        rtol=0,
        atol=1e-12,
    ):
        raise ValueError("truth violates fixed-Gc invariant")
    if truth_manifest["diagnostic_prefix_only"]:
        raise ValueError("inverse profile requires the full monotonic path")
    if not np.allclose(truth["displacement"], repeat["displacement"]):
        raise ValueError("truth and truth-repeat displacement grids differ")
    scale = float(np.max(np.abs(truth["reaction"])))
    if not np.isfinite(scale) or scale <= np.finfo(float).eps:
        raise ValueError("truth reaction scale must be positive and finite")
    indices = np.arange(len(truth["reaction"]))
    fit_mask = indices % 2 == 0
    held_mask = ~fit_mask
    if not np.any(fit_mask) or not np.any(held_mask):
        raise ValueError("profile requires nonempty fit and held-out step sets")
    repeat_nrmse = nrmse(repeat["reaction"], truth["reaction"], scale)

    rows = []
    seen_l0: set[float] = set()
    for directory in args.candidate:
        manifest, curve = read_run(directory)
        if any(truth_manifest[key] != manifest[key] for key in identity_keys):
            raise ValueError(f"candidate fixed settings differ: {directory}")
        if not np.isclose(
            manifest["w1"] * manifest["l0"], manifest["gc_bar"], rtol=0, atol=1e-12
        ):
            raise ValueError(f"candidate violates fixed-Gc invariant: {directory}")
        if float(manifest["l0"]) in seen_l0:
            raise ValueError(f"duplicate candidate l0: {manifest['l0']}")
        seen_l0.add(float(manifest["l0"]))
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
    if not rows:
        raise ValueError("at least one candidate is required")
    best = min(rows, key=lambda row: row["fit_nrmse"])
    summary = {
        "truth_run": str(args.truth.resolve()),
        "truth_l0": float(truth_manifest["l0"]),
        "truth_seed": int(truth_manifest["seed"]),
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
    with (args.out / "ell_profile.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
