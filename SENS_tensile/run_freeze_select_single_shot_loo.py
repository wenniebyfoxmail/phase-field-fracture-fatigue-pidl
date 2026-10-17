#!/usr/bin/env python3
"""Leakage-safe leave-one-environment-out single-shot STLSQ baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from freeze_select.selectors import fit_stlsq


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_environment(value: str) -> tuple[str, Path]:
    parts = value.split("|")
    if len(parts) != 2 or not parts[0]:
        raise argparse.ArgumentTypeError("environment must be name|weak_system.csv")
    return parts[0], Path(parts[1])


def rmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((observed - predicted) ** 2)))


def mean_pairwise_jaccard(supports: list[set[str]]) -> float:
    values: list[float] = []
    for left_index, left in enumerate(supports):
        for right in supports[left_index + 1 :]:
            union = left | right
            values.append(1.0 if not union else len(left & right) / len(union))
    return float(np.mean(values)) if values else 1.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", action="append", type=parse_environment, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--relative-threshold", type=float, default=0.08)
    args = parser.parse_args()
    if len(args.environment) < 3:
        raise ValueError("At least three environments are required")

    environments: dict[str, dict[str, object]] = {}
    term_names: tuple[str, ...] | None = None
    for name, path in args.environment:
        if name in environments:
            raise ValueError(f"Duplicate environment: {name}")
        frame = pd.read_csv(path)
        terms = tuple(column.removeprefix("theta__") for column in frame if column.startswith("theta__"))
        if term_names is None:
            term_names = terms
        elif terms != term_names:
            raise ValueError(f"Candidate library mismatch for {name}")
        environments[name] = {"frame": frame, "weak_sha256": sha256(path)}
    assert term_names is not None
    theta_columns = [f"theta__{name}" for name in term_names]

    rows: list[dict[str, object]] = []
    fold_supports: list[set[str]] = []
    for holdout_name, holdout in environments.items():
        train_names = sorted(name for name in environments if name != holdout_name)
        train_frames = [environments[name]["frame"] for name in train_names]
        A_train = np.vstack([frame[theta_columns].to_numpy(float) for frame in train_frames])
        b_train = np.concatenate([frame["lhs_b"].to_numpy(float) for frame in train_frames])
        beta = fit_stlsq(A_train, b_train, relative_threshold=args.relative_threshold)
        support = {name for name, value in zip(term_names, beta) if abs(value) > 1e-12}
        fold_supports.append(support)
        holdout_frame = holdout["frame"]
        A_holdout = holdout_frame[theta_columns].to_numpy(float)
        b_holdout = holdout_frame["lhs_b"].to_numpy(float)
        holdout_rmse = rmse(b_holdout, A_holdout @ beta)
        null_rmse = rmse(b_holdout, np.zeros_like(b_holdout))
        rows.append(
            {
                "holdout_environment": holdout_name,
                "train_environments": "|".join(train_names),
                "selected_support": "|".join(name for name in term_names if name in support),
                "support_size": len(support),
                "relative_threshold": args.relative_threshold,
                "train_rows": len(b_train),
                "holdout_rows": len(b_holdout),
                "train_rmse": rmse(b_train, A_train @ beta),
                "holdout_rmse": holdout_rmse,
                "null_holdout_rmse": null_rmse,
                "holdout_improvement_vs_null": 1.0 - holdout_rmse / max(null_rmse, np.finfo(float).eps),
                "coefficients_json": json.dumps(dict(zip(term_names, map(float, beta))), sort_keys=True),
                "holdout_used_for_support": False,
                "holdout_used_for_fit": False,
            }
        )

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    folds = pd.DataFrame(rows)
    folds.to_csv(output / "folds.csv", index=False)
    metrics = {
        "protocol_id": "freeze_select_single_shot_loo_v1",
        "relative_threshold": args.relative_threshold,
        "environment_count": len(environments),
        "candidate_terms": list(term_names),
        "fold_count": len(folds),
        "mean_pairwise_fold_support_jaccard": mean_pairwise_jaccard(fold_supports),
        "minimum_holdout_improvement_vs_null": float(folds["holdout_improvement_vs_null"].min()),
        "maximum_holdout_rmse": float(folds["holdout_rmse"].max()),
        "holdout_used_for_support_any": bool(folds["holdout_used_for_support"].any()),
        "holdout_used_for_fit_any": bool(folds["holdout_used_for_fit"].any()),
        "environment_weak_sha256": {
            name: data["weak_sha256"] for name, data in environments.items()
        },
    }
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
