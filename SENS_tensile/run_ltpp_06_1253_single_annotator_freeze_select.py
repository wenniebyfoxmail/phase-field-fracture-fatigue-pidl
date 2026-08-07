#!/usr/bin/env python3
"""Exploratory stability-validated weak selection on frozen LTPP observations."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from freeze_select.road_observation import (
    LTPP_06_1253_CANDIDATE_STATUS,
    FrozenRoadTransition,
    ObservedForcing,
    build_observed_candidate_library,
)
from freeze_select.selectors import fit_stlsq, stability_validated_select
from freeze_select.weak_system import WeakSystem


TERM_NAMES = (
    "constant",
    "damage",
    "damage_sq",
    "low_temp_exposure",
    "temp_variation_rate",
    "precipitation_rate",
    "damage_x_low_temp_exposure",
    "damage_x_temp_variation_rate",
    "damage_x_precipitation_rate",
)
FORCING_SPECS = {
    "low_temp_exposure": ("low_temp_exposure_10_C_day_per_year", "C day/year"),
    "temp_variation_rate": ("abs_temperature_change_C_per_year", "C/year"),
    "precipitation_rate": ("precipitation_mm_per_year", "mm/year"),
}
TIME_WINDOWS = {
    "early": tuple(range(0, 5)),
    "middle": tuple(range(1, 6)),
    "late": tuple(range(2, 7)),
    "all": tuple(range(0, 7)),
}
TEST_FAMILY_SETS = {
    "hat": ("hat",),
    "quartic": ("quartic",),
    "cosine": ("cosine",),
    "mixed": ("hat", "quartic", "cosine"),
}


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return hashlib.sha256(contiguous.view(np.uint8)).hexdigest()


def compact_weight(r: np.ndarray, family: str) -> np.ndarray:
    q = np.clip(np.abs(r), 0.0, 1.0)
    if family == "hat":
        return np.maximum(1.0 - q, 0.0)
    if family == "quartic":
        return np.square(np.maximum(1.0 - q * q, 0.0))
    if family == "cosine":
        output = np.zeros_like(q)
        inside = q < 1.0
        output[inside] = np.cos(0.5 * np.pi * q[inside]) ** 2
        return output
    raise ValueError(f"unsupported weak-test family: {family}")


def build_transitions(
    fields_path: Path,
    fields_manifest: dict,
    climate_path: Path,
) -> list[FrozenRoadTransition]:
    archive = np.load(fields_path)
    x_values = archive["x_m"].astype(np.float64)
    y_values = archive["y_m"].astype(np.float64)
    damage = archive["combined_damage"].astype(np.float64)
    dates = [date.fromisoformat(str(value)) for value in archive["survey_dates"].tolist()]
    authorized = archive["authorized_transition_indices"].astype(int).tolist()
    if authorized != list(range(7)):
        raise ValueError("frozen fields must authorize only transitions 0 through 6")
    if damage.shape != (9, len(y_values), len(x_values)):
        raise ValueError("frozen field shape mismatch")
    climate = load_json(climate_path)
    intervals = climate.get("intervals", [])
    if len(intervals) != 8:
        raise ValueError("climate package must contain eight intervals")
    grid_x, grid_y = np.meshgrid(x_values, y_values)
    flat_x = grid_x.ravel()
    flat_y = grid_y.ravel()
    dx = float(x_values[1] - x_values[0])
    dy = float(y_values[1] - y_values[0])
    cell_area = np.full(flat_x.shape, dx * dy, dtype=np.float64)
    valid = np.ones(flat_x.shape, dtype=bool)
    climate_hash = sha256(climate_path)
    adapter_hash = fields_manifest["outputs"]["fields_npz_sha256"]
    transitions = []
    for index in authorized:
        interval = intervals[index]
        if interval.get("confirmatory_forcing_authorized") is not True:
            raise ValueError(f"transition {index} forcing is not authorized")
        if date.fromisoformat(interval["source_survey"]) != dates[index]:
            raise ValueError(f"transition {index} source date mismatch")
        if date.fromisoformat(interval["target_survey"]) != dates[index + 1]:
            raise ValueError(f"transition {index} target date mismatch")
        forcing = {}
        for name, (source_key, unit) in FORCING_SPECS.items():
            forcing[name] = ObservedForcing(
                name=name,
                values=np.asarray([float(interval[source_key])], dtype=np.float64),
                unit=unit,
                source_sha256=climate_hash,
                coverage_start=dates[index],
                coverage_end=dates[index + 1],
            )
        transition = FrozenRoadTransition(
            section_id="06-1253",
            transition_id=str(interval["interval_id"]),
            start_date=dates[index],
            end_date=dates[index + 1],
            x_m=flat_x,
            y_m=flat_y,
            cell_area_m2=cell_area,
            damage_start=damage[index].ravel(),
            damage_end=damage[index + 1].ravel(),
            valid_mask=valid,
            forcing=forcing,
            candidate_status=LTPP_06_1253_CANDIDATE_STATUS,
            field_hash_start=array_sha256(damage[index]),
            field_hash_end=array_sha256(damage[index + 1]),
            adapter_hash=adapter_hash,
            adapter_fit_dates=(dates[index], dates[index + 1]),
            fields_frozen=True,
            future_geometry_used=False,
            evidence_label="exploratory_single_annotator_observation_only",
        )
        transition.validate(strict_forecast=False)
        transitions.append(transition)
    return transitions


def assemble_spatial_weak_system(
    transitions: list[FrozenRoadTransition],
    indices: tuple[int, ...],
    *,
    n_windows: int,
    seed: int,
    families: tuple[str, ...],
) -> WeakSystem:
    prepared = []
    for index in indices:
        transition = transitions[index]
        candidate, names = build_observed_candidate_library(transition, TERM_NAMES)
        duration_years = (transition.end_date - transition.start_date).days / 365.2425
        rate = (transition.damage_end - transition.damage_start) / duration_years
        prepared.append((transition, candidate, rate))
    rng = np.random.default_rng(seed)
    rows_a = []
    rows_b = []
    metadata = []
    attempts = 0
    while len(rows_b) < n_windows and attempts < n_windows * 50:
        attempts += 1
        local_index = int(rng.integers(0, len(prepared)))
        transition, candidate, rate = prepared[local_index]
        x = transition.x_m
        y = transition.y_m
        x_range = float(x.max() - x.min())
        y_range = float(y.max() - y.min())
        hx = x_range * rng.uniform(0.08, 0.22)
        hy = y_range * rng.uniform(0.18, 0.42)
        cx = rng.uniform(float(x.min()) + hx, float(x.max()) - hx)
        cy = rng.uniform(float(y.min()) + hy, float(y.max()) - hy)
        family = str(rng.choice(families))
        weight = compact_weight((x - cx) / hx, family) * compact_weight((y - cy) / hy, family)
        weight *= transition.cell_area_m2
        active = weight > 0.0
        if int(active.sum()) < 48 or float(weight.sum()) <= 0.0:
            continue
        normalized = weight / weight.sum()
        rows_a.append(np.sum(normalized[:, None] * candidate, axis=0))
        rows_b.append(float(np.sum(normalized * rate)))
        spatial_section = min(4, int(np.floor(5.0 * cx / max(float(x.max()), 1e-12))))
        metadata.append(
            {
                "window_id": f"rw{len(rows_b) - 1:04d}",
                "trajectory_id": transition.transition_id,
                "split_group": f"{transition.transition_id}::xs{spatial_section}",
                "test_function_id": family,
                "center_x": cx,
                "center_y": cy,
                "halfwidth_x": hx,
                "halfwidth_y": hy,
                "point_count": int(active.sum()),
                "spatial_section": spatial_section,
                "start_date": transition.start_date.isoformat(),
                "end_date": transition.end_date.isoformat(),
                "evidence_grade": transition.evidence_label,
            }
        )
    if len(rows_b) != n_windows:
        raise ValueError(f"assembled {len(rows_b)} of {n_windows} weak windows")
    return WeakSystem(
        A=np.vstack(rows_a),
        b=np.asarray(rows_b, dtype=np.float64),
        term_names=tuple(names),
        metadata=pd.DataFrame(metadata),
    )


def support_jaccard(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    return 1.0 if not union else len(left_set & right_set) / len(union)


def mean_pairwise_jaccard(supports: list[tuple[str, ...]]) -> float:
    values = [
        support_jaccard(supports[i], supports[j])
        for i in range(len(supports))
        for j in range(i + 1, len(supports))
    ]
    return 1.0 if not values else float(np.mean(values))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fields-manifest", type=Path, required=True)
    parser.add_argument("--climate-features", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--n-windows", type=int, default=192)
    parser.add_argument("--n-trials", type=int, default=32)
    parser.add_argument("--seeds", type=int, default=3)
    args = parser.parse_args()

    fields_manifest = load_json(args.fields_manifest)
    if fields_manifest.get("evidence_grade") != "exploratory_single_annotator":
        raise SystemExit("fields are not declared exploratory_single_annotator")
    fields_path = Path(fields_manifest["outputs"]["fields_npz"])
    if sha256(fields_path) != fields_manifest["outputs"]["fields_npz_sha256"]:
        raise SystemExit("frozen observation field hash mismatch")
    transitions = build_transitions(fields_path, fields_manifest, args.climate_features)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    run_rows = []
    support_rows = []
    fts_supports = []
    single_supports = []
    for time_name, indices in TIME_WINDOWS.items():
        for family_name, families in TEST_FAMILY_SETS.items():
            for seed in range(args.seeds):
                run_id = f"{time_name}__{family_name}__s{seed}"
                system = assemble_spatial_weak_system(
                    transitions,
                    indices,
                    n_windows=args.n_windows,
                    seed=seed,
                    families=families,
                )
                system_path = args.output_dir / f"weak_system__{run_id}.csv"
                system.as_frame().to_csv(system_path, index=False)
                selected = stability_validated_select(
                    system,
                    n_trials=args.n_trials,
                    seed=seed,
                )
                single_beta = fit_stlsq(system.A, system.b)
                single_support = tuple(
                    name
                    for name, value in zip(system.term_names, single_beta)
                    if abs(float(value)) > 1e-12
                )
                fts_supports.append(tuple(selected.stable_support))
                single_supports.append(single_support)
                run_rows.append(
                    {
                        "run_id": run_id,
                        "time_window": time_name,
                        "weak_test_family": family_name,
                        "seed": seed,
                        "transition_indices": "|".join(map(str, indices)),
                        "fts_support": "|".join(selected.stable_support),
                        "single_shot_support": "|".join(single_support),
                        "fts_internal_trial_jaccard": selected.metrics["mean_pairwise_trial_support_jaccard"],
                        "fts_grouped_holdout_rmse": selected.metrics["mean_grouped_holdout_rmse"],
                        "single_shot_holdout_rmse": selected.metrics["single_shot_holdout_rmse"],
                        "null_holdout_rmse": selected.metrics["mean_null_holdout_rmse"],
                        "median_condition_number": selected.metrics["median_normalized_condition_number"],
                        "weak_system_sha256": sha256(system_path),
                    }
                )
                for _, row in selected.support_summary.iterrows():
                    support_rows.append(
                        {
                            "run_id": run_id,
                            "term": str(row["term"]),
                            "selection_frequency": float(row["selection_frequency"]),
                            "sign_consistency": float(row["sign_consistency"]),
                            "stable": bool(row["stable"]),
                        }
                    )

    runs = pd.DataFrame(run_rows)
    support = pd.DataFrame(support_rows)
    runs_path = args.output_dir / "run_summary.csv"
    support_path = args.output_dir / "support_frequency_by_run.csv"
    runs.to_csv(runs_path, index=False)
    support.to_csv(support_path, index=False)
    aggregate = (
        support.groupby("term", as_index=False)
        .agg(
            mean_selection_frequency=("selection_frequency", "mean"),
            minimum_selection_frequency=("selection_frequency", "min"),
            stable_run_fraction=("stable", "mean"),
            mean_sign_consistency=("sign_consistency", "mean"),
        )
        .sort_values(["stable_run_fraction", "mean_selection_frequency"], ascending=False)
    )
    aggregate_path = args.output_dir / "aggregate_support_stability.csv"
    aggregate.to_csv(aggregate_path, index=False)
    result = {
        "protocol_id": "ltpp_06_1253_single_annotator_freeze_select_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_grade": "exploratory_single_annotator",
        "n_runs": len(runs),
        "n_transitions_available": len(transitions),
        "candidate_terms": list(TERM_NAMES),
        "fts_cross_run_support_jaccard": mean_pairwise_jaccard(fts_supports),
        "single_shot_cross_run_support_jaccard": mean_pairwise_jaccard(single_supports),
        "median_fts_internal_trial_jaccard": float(runs["fts_internal_trial_jaccard"].median()),
        "mean_fts_grouped_holdout_rmse": float(runs["fts_grouped_holdout_rmse"].mean()),
        "mean_single_shot_holdout_rmse": float(runs["single_shot_holdout_rmse"].mean()),
        "mean_null_holdout_rmse": float(runs["null_holdout_rmse"].mean()),
        "prohibited_claims": [
            "ground-truth support accuracy",
            "causal climate mechanism discovery",
            "confirmatory real-road validation",
            "joint-training superiority before a genuine joint baseline is run",
            "traffic, moisture, mechanics, phase-field teacher, or cross-road generalization",
        ],
        "inputs": {
            "fields_manifest": str(args.fields_manifest.resolve()),
            "fields_manifest_sha256": sha256(args.fields_manifest),
            "climate_features": str(args.climate_features.resolve()),
            "climate_features_sha256": sha256(args.climate_features),
        },
        "outputs": {
            "run_summary": str(runs_path.resolve()),
            "run_summary_sha256": sha256(runs_path),
            "support_frequency_by_run": str(support_path.resolve()),
            "support_frequency_by_run_sha256": sha256(support_path),
            "aggregate_support_stability": str(aggregate_path.resolve()),
            "aggregate_support_stability_sha256": sha256(aggregate_path),
        },
    }
    result_path = args.output_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "result": str(result_path),
                "n_runs": result["n_runs"],
                "fts_cross_run_support_jaccard": result["fts_cross_run_support_jaccard"],
                "single_shot_cross_run_support_jaccard": result["single_shot_cross_run_support_jaccard"],
                "mean_fts_grouped_holdout_rmse": result["mean_fts_grouped_holdout_rmse"],
                "mean_single_shot_holdout_rmse": result["mean_single_shot_holdout_rmse"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
