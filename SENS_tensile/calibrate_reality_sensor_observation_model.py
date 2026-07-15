#!/usr/bin/env python3
"""Fit a versioned DIC/strain and AE observation model from paired data.

Calibration uncertainty is estimated from leave-one-calibration-group-out
predictions, never from the in-sample residual. The generated model is not
automatically approved for real inference; review is an explicit separate gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from reality_assimilation import SensorObservationModel


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def design_matrix(frame: pd.DataFrame, sources: Sequence[str]) -> np.ndarray:
    return np.column_stack(
        [np.ones(len(frame), dtype=float)]
        + [pd.to_numeric(frame[name], errors="coerce").to_numpy(float) for name in sources]
    )


def fit_channel_group_cv(
    frame: pd.DataFrame,
    *,
    output_name: str,
    source_names: Sequence[str],
    group_column: str,
    min_groups: int = 3,
) -> tuple[dict[str, object], dict[str, float | str]]:
    columns = [group_column, output_name, *source_names]
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"Calibration data are missing columns: {missing}")
    clean = frame[columns].copy()
    for name in [output_name, *source_names]:
        clean[name] = pd.to_numeric(clean[name], errors="coerce")
    clean = clean.dropna()
    groups = clean[group_column].astype(str).to_numpy()
    unique_groups = np.unique(groups)
    if len(unique_groups) < min_groups:
        raise ValueError(
            f"Channel {output_name} has {len(unique_groups)} groups; need at least {min_groups}"
        )
    if len(clean) <= len(source_names) + 1:
        raise ValueError(f"Channel {output_name} has too few finite paired rows")
    target = clean[output_name].to_numpy(float)
    matrix = design_matrix(clean, source_names)
    cross_validated = np.full(len(clean), np.nan, dtype=float)
    for group in unique_groups:
        test = groups == group
        train = ~test
        if np.count_nonzero(train) <= len(source_names) + 1:
            raise ValueError(f"Leaving out group {group} leaves too few training rows")
        coefficients, *_ = np.linalg.lstsq(matrix[train], target[train], rcond=None)
        cross_validated[test] = matrix[test] @ coefficients
    if not np.isfinite(cross_validated).all():
        raise RuntimeError(f"Channel {output_name} produced incomplete cross-validated predictions")
    residual = target - cross_validated
    sigma = float(np.sqrt(np.mean(residual**2)))
    if not np.isfinite(sigma) or sigma <= 0.0:
        sigma = float(np.finfo(float).eps)
    coefficients, *_ = np.linalg.lstsq(matrix, target, rcond=None)
    total = float(np.sum((target - np.mean(target)) ** 2))
    residual_sum = float(np.sum(residual**2))
    r2 = float(1.0 - residual_sum / total) if total > 0.0 else float("nan")
    channel = {
        "sources": {
            name: float(value) for name, value in zip(source_names, coefficients[1:])
        },
        "offset": float(coefficients[0]),
        "sigma": sigma,
    }
    report: dict[str, float | str] = {
        "channel": output_name,
        "sources": ",".join(source_names),
        "n_rows": float(len(clean)),
        "n_groups": float(len(unique_groups)),
        "group_cv_rmse": sigma,
        "group_cv_mae": float(np.mean(np.abs(residual))),
        "group_cv_r2": r2,
    }
    return channel, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-csv", required=True, type=Path)
    parser.add_argument("--channel-spec-json", required=True, type=Path)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--group-column", default="calibration_group")
    parser.add_argument("--min-groups", type=int, default=3)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    if args.min_groups < 3:
        raise ValueError("--min-groups must be at least 3 for grouped calibration")
    frame = pd.read_csv(args.paired_csv)
    specification = json.loads(args.channel_spec_json.read_text(encoding="utf-8"))
    requested: Mapping[str, Mapping[str, object]] = specification["channels"]
    channels: dict[str, object] = {}
    reports = []
    for output_name, channel_spec in requested.items():
        sources = list(channel_spec["sources"])
        channel, report = fit_channel_group_cv(
            frame,
            output_name=output_name,
            source_names=sources,
            group_column=args.group_column,
            min_groups=args.min_groups,
        )
        channels[output_name] = channel
        reports.append(report)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(reports).to_csv(args.out_dir / "calibration_report.csv", index=False)
    model = {
        "model_id": args.model_id,
        "calibration_status": "lab_calibrated",
        "approved_for_inference": False,
        "calibration_metadata": {
            "paired_csv": str(args.paired_csv.resolve()),
            "paired_csv_sha256": sha256(args.paired_csv),
            "channel_spec_json": str(args.channel_spec_json.resolve()),
            "channel_spec_sha256": sha256(args.channel_spec_json),
            "group_column": args.group_column,
            "min_groups": args.min_groups,
            "validation": "leave-one-calibration-group-out",
        },
        "channels": channels,
    }
    SensorObservationModel(
        model_id=args.model_id,
        calibration_status="lab_calibrated",
        channels=channels,
        approved_for_inference=False,
        calibration_metadata=model["calibration_metadata"],
    )
    model_path = args.out_dir / "sensor_observation_model.json"
    model_path.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "claim_class": "framework-validation",
        "training_launched": False,
        "model_path": model_path.name,
        "calibration_report": "calibration_report.csv",
        "approved_for_inference": False,
        "review_required": True,
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Sensor Observation Calibration Decision",
        "",
        "Grouped calibration completed without in-sample uncertainty leakage.",
        "",
        "| channel | groups | rows | CV RMSE | CV MAE | CV R2 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in reports:
        lines.append(
            f"| `{row['channel']}` | {row['n_groups']:.0f} | {row['n_rows']:.0f} | "
            f"{row['group_cv_rmse']:.4g} | {row['group_cv_mae']:.4g} | {row['group_cv_r2']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "- The file is a fitted laboratory calibration candidate, not an approved deployment model.",
            "- `approved_for_inference=false`; independent review must inspect group definitions, registration, residual structure, and extrapolation range before changing it.",
            "- No FEM/PIDL/surrogate training was launched.",
        ]
    )
    (args.out_dir / "decision.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote grouped sensor calibration package to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
