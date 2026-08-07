#!/usr/bin/env python3
"""Audit candidate identifiability for the frozen LTPP exploratory weak systems."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.linalg import pinvh


FORCING_COLUMNS = (
    "low_temp_exposure_10_C_day_per_year",
    "abs_temperature_change_C_per_year",
    "precipitation_mm_per_year",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def normalized_condition(matrix: np.ndarray) -> tuple[int, float]:
    norms = np.linalg.norm(matrix, axis=0)
    active = norms > np.finfo(float).eps
    normalized = matrix[:, active] / norms[active]
    return int(np.linalg.matrix_rank(normalized)), float(np.linalg.cond(normalized))


def vif_values(matrix: np.ndarray, names: list[str]) -> dict[str, float]:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    standard_deviation = centered.std(axis=0)
    scale_floor = max(float(np.max(standard_deviation)) * 1e-10, np.finfo(float).eps)
    variable = standard_deviation > scale_floor
    variable = np.asarray(
        [keep and name != "constant" for name, keep in zip(names, variable)],
        dtype=bool,
    )
    scaled = centered[:, variable] / standard_deviation[variable]
    variable_names = [name for name, keep in zip(names, variable) if keep]
    output = {name: float("nan") for name in names}
    if not variable_names:
        return output
    correlation = (scaled.T @ scaled) / float(scaled.shape[0])
    precision = pinvh(correlation, rtol=np.sqrt(np.finfo(float).eps), check_finite=True)
    for target_index, target_name in enumerate(variable_names):
        output[target_name] = float(max(precision[target_index, target_index], 1.0))
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--climate-features", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result_path = args.result_root / "result.json"
    result = load_json(result_path)
    if result.get("protocol_id") != "ltpp_06_1253_single_annotator_freeze_select_v1":
        raise SystemExit("unexpected v1 result protocol")
    systems = sorted(args.result_root.glob("weak_system__*.csv"))
    if len(systems) != 48:
        raise SystemExit(f"expected 48 frozen weak systems, found {len(systems)}")

    climate = load_json(args.climate_features)
    intervals = [
        row for row in climate.get("intervals", [])
        if row.get("confirmatory_forcing_authorized") is True
    ]
    if len(intervals) != 7:
        raise SystemExit("expected seven authorized climate intervals")
    forcing = np.asarray(
        [[float(row[name]) for name in FORCING_COLUMNS] for row in intervals],
        dtype=np.float64,
    )
    forcing_scaled = (forcing - forcing.mean(axis=0)) / forcing.std(axis=0)
    forcing_rank = int(np.linalg.matrix_rank(forcing_scaled))
    forcing_correlation = np.corrcoef(forcing_scaled, rowvar=False)
    forcing_max_correlation = float(
        np.max(np.abs(forcing_correlation[np.triu_indices(len(FORCING_COLUMNS), 1)]))
    )

    system_rows = []
    vif_rows = []
    term_names: list[str] | None = None
    for path in systems:
        frame = pd.read_csv(path)
        current_names = [column.removeprefix("theta__") for column in frame if column.startswith("theta__")]
        if term_names is None:
            term_names = current_names
        elif current_names != term_names:
            raise SystemExit("weak systems do not share one candidate library")
        matrix = frame[[f"theta__{name}" for name in current_names]].to_numpy(float)
        rank, condition = normalized_condition(matrix)
        system_rows.append(
            {
                "system": path.name,
                "rank": rank,
                "candidate_count": len(current_names),
                "full_rank": rank == len(current_names),
                "normalized_condition_number": condition,
                "sha256": sha256(path),
            }
        )
        for name, value in vif_values(matrix, current_names).items():
            vif_rows.append({"system": path.name, "term": name, "vif": value})

    system_frame = pd.DataFrame(system_rows)
    vif_frame = pd.DataFrame(vif_rows)
    term_summary = (
        vif_frame[np.isfinite(vif_frame["vif"])]
        .groupby("term", as_index=False)
        .agg(median_vif=("vif", "median"), p90_vif=("vif", lambda values: np.quantile(values, 0.90)))
        .sort_values("p90_vif", ascending=False)
    )
    full_rank_fraction = float(system_frame["full_rank"].mean())
    median_condition = float(system_frame["normalized_condition_number"].median())
    p90_condition = float(system_frame["normalized_condition_number"].quantile(0.90))
    max_median_vif = float(term_summary["median_vif"].max())
    max_p90_vif = float(term_summary["p90_vif"].max())
    time_environment_counts = {"early": 5, "middle": 5, "late": 5, "all": 7}

    checks = {
        "forcing_rank_3": forcing_rank == 3,
        "forcing_max_abs_correlation_lt_0p95": forcing_max_correlation < 0.95,
        "full_rank_system_fraction_ge_0p90": full_rank_fraction >= 0.90,
        "median_condition_le_1e3": median_condition <= 1e3,
        "p90_condition_le_1e4": p90_condition <= 1e4,
        "all_term_median_vif_le_20": max_median_vif <= 20.0,
        "all_term_p90_vif_le_50": max_p90_vif <= 50.0,
        "time_windows_have_at_least_four_environments": min(time_environment_counts.values()) >= 4,
        "full_route_has_at_least_seven_environments": time_environment_counts["all"] >= 7,
    }
    decision = "FULL_LIBRARY_IDENTIFIABLE" if all(checks.values()) else "FULL_LIBRARY_NOT_IDENTIFIABLE"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    systems_path = args.output_dir / "system_conditioning.csv"
    vif_path = args.output_dir / "term_vif_summary.csv"
    system_frame.to_csv(systems_path, index=False)
    term_summary.to_csv(vif_path, index=False)
    payload = {
        "protocol_id": "ltpp_06_1253_post_v1_identifiability_gate_v4_scipy_pinvh",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_grade": "post_v1_diagnostic",
        "numeric_fix": (
            "Near-constant intercept columns are excluded with a relative scale tolerance; "
            "VIF is computed with scipy.linalg.pinvh on the standardized correlation matrix. "
            "Frozen thresholds are unchanged."
        ),
        "decision": decision,
        "checks": checks,
        "metrics": {
            "forcing_rank": forcing_rank,
            "forcing_max_abs_correlation": forcing_max_correlation,
            "full_rank_system_fraction": full_rank_fraction,
            "median_normalized_condition_number": median_condition,
            "p90_normalized_condition_number": p90_condition,
            "maximum_term_median_vif": max_median_vif,
            "maximum_term_p90_vif": max_p90_vif,
            "time_environment_counts": time_environment_counts,
        },
        "forcing_correlation_matrix": {
            left: {right: float(forcing_correlation[i, j]) for j, right in enumerate(FORCING_COLUMNS)}
            for i, left in enumerate(FORCING_COLUMNS)
        },
        "boundary": (
            "Failure permits only an explicitly post-v1 reduced-library diagnostic; "
            "it cannot overwrite the frozen v1 result or support causal claims."
        ),
        "inputs": {
            "v1_result": str(result_path.resolve()),
            "v1_result_sha256": sha256(result_path),
            "climate_features": str(args.climate_features.resolve()),
            "climate_features_sha256": sha256(args.climate_features),
        },
        "outputs": {
            "system_conditioning": str(systems_path.resolve()),
            "system_conditioning_sha256": sha256(systems_path),
            "term_vif_summary": str(vif_path.resolve()),
            "term_vif_summary_sha256": sha256(vif_path),
        },
    }
    output_path = args.output_dir / "identifiability_result.json"
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "checks": checks, "metrics": payload["metrics"]}))
    return 0 if decision == "FULL_LIBRARY_IDENTIFIABLE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
