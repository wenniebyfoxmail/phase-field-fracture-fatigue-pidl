#!/usr/bin/env python3
"""Leave-one-environment-out validation for independently stable supports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_environment(value: str) -> tuple[str, Path, Path]:
    parts = value.split("|")
    if len(parts) != 3 or not parts[0]:
        raise argparse.ArgumentTypeError("environment must be name|weak_system.csv|support_summary.csv")
    return parts[0], Path(parts[1]), Path(parts[2])


def stable_terms(path: Path) -> set[str]:
    frame = pd.read_csv(path)
    stable = frame["stable"]
    if stable.dtype != bool:
        stable = stable.astype(str).str.lower().isin({"true", "1", "yes"})
    return set(frame.loc[stable, "term"].astype(str))


def normalized_ridge(A: np.ndarray, b: np.ndarray, l2: float = 1e-8) -> np.ndarray:
    scales = np.linalg.norm(A, axis=0)
    scales[scales <= np.finfo(float).eps] = 1.0
    X = A / scales
    beta_scaled = np.linalg.solve(X.T @ X + l2 * np.eye(X.shape[1]), X.T @ b)
    return beta_scaled / scales


def rmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((observed - predicted) ** 2)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", action="append", type=parse_environment, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if len(args.environment) < 3:
        raise ValueError("At least three environments are required")

    environments: dict[str, dict[str, object]] = {}
    common_terms: tuple[str, ...] | None = None
    for name, weak_path, support_path in args.environment:
        if name in environments:
            raise ValueError(f"Duplicate environment: {name}")
        weak = pd.read_csv(weak_path)
        terms = tuple(column.removeprefix("theta__") for column in weak if column.startswith("theta__"))
        if common_terms is None:
            common_terms = terms
        elif terms != common_terms:
            raise ValueError(f"Candidate library mismatch for {name}")
        environments[name] = {
            "weak": weak,
            "stable": stable_terms(support_path),
            "weak_sha256": sha256(weak_path),
            "support_sha256": sha256(support_path),
        }
    assert common_terms is not None

    rows: list[dict[str, object]] = []
    for holdout_name, holdout in environments.items():
        train_names = sorted(name for name in environments if name != holdout_name)
        consensus = set.intersection(*(environments[name]["stable"] for name in train_names))
        selected = [name for name in common_terms if name in consensus]
        if not selected:
            raise ValueError(f"Empty train-only consensus for holdout {holdout_name}")
        columns = [f"theta__{name}" for name in selected]
        train_frames = [environments[name]["weak"] for name in train_names]
        A_train = np.vstack([frame[columns].to_numpy(float) for frame in train_frames])
        b_train = np.concatenate([frame["lhs_b"].to_numpy(float) for frame in train_frames])
        beta = normalized_ridge(A_train, b_train)
        holdout_frame = holdout["weak"]
        A_holdout = holdout_frame[columns].to_numpy(float)
        b_holdout = holdout_frame["lhs_b"].to_numpy(float)
        holdout_rmse = rmse(b_holdout, A_holdout @ beta)
        null_rmse = rmse(b_holdout, np.zeros_like(b_holdout))
        rows.append(
            {
                "holdout_environment": holdout_name,
                "train_environments": "|".join(train_names),
                "consensus_support": "|".join(selected),
                "support_size": len(selected),
                "train_rows": len(b_train),
                "holdout_rows": len(b_holdout),
                "train_rmse": rmse(b_train, A_train @ beta),
                "holdout_rmse": holdout_rmse,
                "null_holdout_rmse": null_rmse,
                "holdout_improvement_vs_null": 1.0 - holdout_rmse / max(null_rmse, np.finfo(float).eps),
                "coefficients_json": json.dumps(dict(zip(selected, map(float, beta))), sort_keys=True),
                "holdout_used_for_support": False,
                "holdout_used_for_fit": False,
            }
        )

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    folds = pd.DataFrame(rows)
    folds.to_csv(output / "folds.csv", index=False)
    metrics = {
        "protocol_id": "freeze_select_environment_consensus_v1",
        "environment_count": len(environments),
        "candidate_terms": list(common_terms),
        "fold_count": len(folds),
        "minimum_holdout_improvement_vs_null": float(folds["holdout_improvement_vs_null"].min()),
        "maximum_holdout_rmse": float(folds["holdout_rmse"].max()),
        "holdout_used_for_support_any": bool(folds["holdout_used_for_support"].any()),
        "holdout_used_for_fit_any": bool(folds["holdout_used_for_fit"].any()),
        "environment_assets": {
            name: {
                "weak_sha256": data["weak_sha256"],
                "support_sha256": data["support_sha256"],
                "stable_support": sorted(data["stable"]),
            }
            for name, data in environments.items()
        },
    }
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
