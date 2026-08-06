#!/usr/bin/env python3
"""Run the frozen non-confirmatory O3 realized-exposure diagnostic."""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from ltpp_run_enriched_posterior import (
    MODELS,
    aggregate,
    fit_with_locked_retry,
    git_receipt,
    load_outcomes,
    posterior_predictive_draws,
    prediction_rows,
    require_hash,
    section_mae,
    sha256,
    standardize_fold,
    write_csv,
)


PRIMARY_EVALUATION_SHA256 = (
    "f3a18f4fc9bdd186da8d1e42fad44d688030e5569f17f36a720f76e53e26c6d2"
)
PRIMARY_PREDICTIONS_SHA256 = (
    "465c0dff865ae6813b9da75ad16f8a108f2adcdeae17b862835bf9385311b67b"
)
RAW_MANIFEST_SHA256 = (
    "c8659bb66bc8820b6a65edd754ab16ca7fbeb7d02545574de9f44623a391a6bd"
)
ORACLE_EXCLUDED_IDS = {"06-1253-T07"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def realized_traffic(
    source: date,
    target: date,
    construction: int,
    rows: list[dict[str, str]],
) -> dict:
    total_days = (target - source).days
    if total_days <= 0:
        raise ValueError("Oracle interval must have positive duration")
    covered_days = 0
    esal = 0.0
    aadtt_days = 0.0
    yearly_receipt = []
    for year in range(source.year, target.year + 1):
        overlap_start = max(source, date(year, 1, 1))
        overlap_end = min(target, date(year + 1, 1, 1))
        overlap_days = max(0, (overlap_end - overlap_start).days)
        if overlap_days == 0:
            continue
        match = [
            row
            for row in rows
            if int(row["CONSTRUCTION_NO"]) == construction
            and int(row["YEAR"]) == year
        ]
        if len(match) != 1:
            yearly_receipt.append(
                {"year": year, "overlap_days": overlap_days, "status": "MISSING"}
            )
            continue
        row = match[0]
        if not row["ANNUAL_ESAL_TREND"].strip() or not row[
            "AADTT_ALL_TRUCKS_TREND"
        ].strip():
            yearly_receipt.append(
                {"year": year, "overlap_days": overlap_days, "status": "MISSING"}
            )
            continue
        annual_esal = float(row["ANNUAL_ESAL_TREND"])
        aadtt = float(row["AADTT_ALL_TRUCKS_TREND"])
        days_in_year = 366 if calendar.isleap(year) else 365
        esal += annual_esal * overlap_days / days_in_year
        aadtt_days += aadtt * overlap_days
        covered_days += overlap_days
        yearly_receipt.append(
            {
                "year": year,
                "overlap_days": overlap_days,
                "annual_esal": annual_esal,
                "aadtt": aadtt,
                "status": "PASS",
            }
        )
    coverage = covered_days / total_days
    if not math.isclose(coverage, 1.0, abs_tol=1e-12):
        raise ValueError(f"Oracle traffic coverage incomplete: {coverage}")
    return {
        "realized_esal": esal,
        "realized_mean_aadtt": aadtt_days / covered_days,
        "coverage_fraction": coverage,
        "yearly_receipt": yearly_receipt,
    }


def raw_traffic_by_section(raw_root: Path) -> tuple[dict[str, list[dict]], dict]:
    manifest_path = require_hash(
        raw_root / "raw_data_manifest.json", RAW_MANIFEST_SHA256, "raw manifest"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS_OFFICIAL_ENRICHED_TABLES_FROZEN":
        raise ValueError("Raw enriched package is not qualified")
    result = {}
    for section in manifest["sections"]:
        table = next(
            row for row in section["tables"] if row["table"] == "TRF_TREND"
        )
        path = raw_root / table["csv"]
        if sha256(path) != table["csv_sha256"]:
            raise ValueError(f"TRF_TREND hash mismatch for {section['section']}")
        result[section["section"]] = read_csv(path)
    return result, manifest


def build_oracle_rows(
    feature_rows: list[dict[str, str]],
    transitions: list[dict],
    raw_traffic: dict[str, list[dict]],
) -> tuple[list[dict], list[dict]]:
    transition_by_id = {row["transition_id"]: row for row in transitions}
    output = []
    receipts = []
    for feature in feature_rows:
        transition_id = feature["transition_id"]
        if transition_id in ORACLE_EXCLUDED_IDS:
            continue
        transition = transition_by_id[transition_id]
        climate = transition["climate"]
        if (
            climate["temperature_coverage_fraction"] != 1.0
            or climate["precipitation_coverage_fraction"] != 1.0
        ):
            raise ValueError(f"Oracle climate incomplete for {transition_id}")
        traffic = realized_traffic(
            date.fromisoformat(transition["source_survey"]),
            date.fromisoformat(transition["target_survey"]),
            int(transition["construction_number"]),
            raw_traffic[transition["section"]],
        )
        row = dict(feature)
        row["C1_trailing_temperature_C"] = climate["mean_temperature_C"]
        row["C2_trailing_precipitation_mm"] = (
            climate["precipitation_mm_per_year"] * transition["duration_years"]
        )
        row["T1_annual_esal_trend"] = traffic["realized_esal"]
        row["T2_aadtt_all_trucks_trend"] = traffic["realized_mean_aadtt"]
        output.append(row)
        receipts.append(
            {
                "transition_id": transition_id,
                "climate_temperature_C": row["C1_trailing_temperature_C"],
                "climate_accumulated_precipitation_mm": row[
                    "C2_trailing_precipitation_mm"
                ],
                "realized_esal": traffic["realized_esal"],
                "realized_mean_aadtt": traffic["realized_mean_aadtt"],
                "traffic_coverage_fraction": traffic["coverage_fraction"],
                "traffic_yearly_receipt": json.dumps(traffic["yearly_receipt"]),
            }
        )
    output.sort(key=lambda row: row["transition_id"])
    receipts.sort(key=lambda row: row["transition_id"])
    if len(output) != 29:
        raise ValueError(f"Expected fixed O3 set of 29 rows, found {len(output)}")
    return output, receipts


def filter_splits(split: dict, oracle_ids: set[str]) -> dict:
    loso = []
    for fold in split["loso"]:
        train = [row for row in fold["train_transition_ids"] if row in oracle_ids]
        test = [row for row in fold["test_transition_ids"] if row in oracle_ids]
        loso.append(
            {
                "held_out_section": fold["held_out_section"],
                "train_transition_ids": train,
                "test_transition_ids": test,
            }
        )
    future = split["future_time"]
    return {
        "loso": loso,
        "future_time": {
            "train_transition_ids": [
                row for row in future["train_transition_ids"] if row in oracle_ids
            ],
            "test_transition_ids": [
                row for row in future["test_transition_ids"] if row in oracle_ids
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-evaluation", type=Path, required=True)
    parser.add_argument("--primary-predictions", type=Path, required=True)
    parser.add_argument("--feature-manifest", type=Path, required=True)
    parser.add_argument("--transitions", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    primary_evaluation = require_hash(
        args.primary_evaluation, PRIMARY_EVALUATION_SHA256, "sealed primary evaluation"
    )
    primary_predictions = require_hash(
        args.primary_predictions, PRIMARY_PREDICTIONS_SHA256, "sealed primary predictions"
    )
    primary = json.loads(primary_evaluation.read_text(encoding="utf-8"))
    if primary.get("status") != "SEALED_PRIMARY_EVALUATION_COMPLETE__ORACLE_PENDING":
        raise ValueError("Primary evaluation is not sealed for O3")
    feature_manifest_path = args.feature_manifest.resolve()
    feature_manifest = json.loads(feature_manifest_path.read_text(encoding="utf-8"))
    feature_path = feature_manifest_path.parent / feature_manifest["feature_table"]
    split_path = feature_manifest_path.parent / feature_manifest["split_receipt"]
    if sha256(feature_path) != feature_manifest["feature_table_sha256"]:
        raise ValueError("Frozen feature-table hash mismatch")
    if sha256(split_path) != feature_manifest["split_receipt_sha256"]:
        raise ValueError("Frozen split hash mismatch")
    feature_rows = read_csv(feature_path)
    split = json.loads(split_path.read_text(encoding="utf-8"))
    transitions_path = args.transitions.resolve()
    transitions = json.loads(transitions_path.read_text(encoding="utf-8"))
    raw_traffic, raw_manifest = raw_traffic_by_section(args.raw_root.resolve())
    oracle_rows, oracle_receipts = build_oracle_rows(
        feature_rows, transitions, raw_traffic
    )
    oracle_ids = {row["transition_id"] for row in oracle_rows}
    oracle_split = filter_splits(split, oracle_ids)
    rows_by_id = {row["transition_id"]: row for row in oracle_rows}
    outcomes, _ = load_outcomes(transitions_path, sorted(oracle_ids))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    posterior_root = output / "posterior_netcdf"
    posterior_root.mkdir()
    oracle_features_path = output / "oracle_features_29x11.csv"
    write_csv(oracle_features_path, oracle_rows)
    oracle_receipt_path = output / "oracle_input_receipt.csv"
    write_csv(oracle_receipt_path, oracle_receipts)

    features = MODELS["M3"]
    predictions = []
    diagnostics = []
    designs = [
        {
            "name": "LOSO",
            "fold_index": index,
            "train_ids": fold["train_transition_ids"],
            "eval_ids": fold["test_transition_ids"],
            "unseen": True,
            "held_out_section": fold["held_out_section"],
        }
        for index, fold in enumerate(oracle_split["loso"])
    ]
    future = oracle_split["future_time"]
    designs.append(
        {
            "name": "future_time",
            "fold_index": 6,
            "train_ids": future["train_transition_ids"],
            "eval_ids": future["test_transition_ids"],
            "unseen": False,
            "held_out_section": None,
        }
    )
    for design in designs:
        seed = 260806 + design["fold_index"]
        train_x, eval_x, zero_variance = standardize_fold(
            rows_by_id, design["train_ids"], design["eval_ids"], features
        )
        train_y = [
            math.log1p(outcomes[row_id]["positive_growth_m"])
            for row_id in design["train_ids"]
        ]
        train_sections = [rows_by_id[row_id]["section"] for row_id in design["train_ids"]]
        eval_sections = [rows_by_id[row_id]["section"] for row_id in design["eval_ids"]]
        idata, diagnostic = fit_with_locked_retry(
            train_x,
            np.asarray(train_y),
            train_sections,
            seed,
        )
        diagnostic.update(
            {
                "model": "O3",
                "design": design["name"],
                "fold_index": design["fold_index"],
                "held_out_section": design["held_out_section"],
                "zero_variance_features": zero_variance,
            }
        )
        diagnostics.append(diagnostic)
        idata.to_netcdf(
            posterior_root / f"O3__{design['name']}__fold{design['fold_index']}.nc"
        )
        if not diagnostic["final_passed"]:
            (output / "sampler_diagnostics.json").write_text(
                json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps({"status": "INVALID_ORACLE_SAMPLER_DIAGNOSTICS"}))
            return 4
        final = diagnostic["attempts"][-1]
        draws = posterior_predictive_draws(
            idata,
            eval_x,
            eval_sections,
            final["section_names"],
            final["active_column_indices"],
            design["unseen"],
            seed,
        )
        predictions.extend(
            prediction_rows(
                "O3",
                design["name"],
                design["fold_index"],
                design["eval_ids"],
                rows_by_id,
                outcomes,
                draws,
            )
        )

    primary_rows = read_csv(primary_predictions)
    matched_m3 = [
        row
        for row in primary_rows
        if row["model"] == "M3" and row["transition_id"] in oracle_ids
    ]
    for row in matched_m3:
        for name in (
            "actual_positive_growth_m",
            "actual_signed_growth_m",
            "prediction_median_m",
            "prediction_q05_m",
            "prediction_q95_m",
            "absolute_error_m",
            "squared_error_m2",
            "crps_m",
        ):
            row[name] = float(row[name])
        row["covered_90"] = int(row["covered_90"])
    summary = {}
    for design in ("LOSO", "future_time"):
        o3 = [row for row in predictions if row["design"] == design]
        m3 = [row for row in matched_m3 if row["design"] == design]
        summary[design] = {
            "O3": {**aggregate(o3), "section_mae_m": section_mae(o3)},
            "M3_MATCHED29": {
                **aggregate(m3),
                "section_mae_m": section_mae(m3),
            },
        }
        summary[design]["O3_minus_M3"] = {
            "mae_difference_m": summary[design]["O3"]["mae_m"]
            - summary[design]["M3_MATCHED29"]["mae_m"],
            "crps_difference_m": summary[design]["O3"]["mean_crps_m"]
            - summary[design]["M3_MATCHED29"]["mean_crps_m"],
        }
    write_csv(output / "oracle_predictions.csv", predictions)
    predictions_path = output / "oracle_predictions.csv"
    diagnostics_path = output / "sampler_diagnostics.json"
    diagnostics_path.write_text(
        json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8"
    )
    posterior_manifest = [
        {"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(posterior_root.glob("*.nc"))
    ]
    posterior_manifest_path = output / "posterior_netcdf_manifest.json"
    posterior_manifest_path.write_text(
        json.dumps(posterior_manifest, indent=2) + "\n", encoding="utf-8"
    )
    script_path = Path(__file__).resolve()
    result = {
        "status": "ORACLE_CONDITIONAL_DIAGNOSTIC_COMPLETE__NON_CONFIRMATORY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary_evaluation_sha256": sha256(primary_evaluation),
        "primary_predictions_sha256": sha256(primary_predictions),
        "raw_manifest_sha256": sha256(
            args.raw_root.resolve() / "raw_data_manifest.json"
        ),
        "oracle_feature_table_sha256": sha256(oracle_features_path),
        "oracle_input_receipt_sha256": sha256(oracle_receipt_path),
        "oracle_predictions_sha256": sha256(predictions_path),
        "sampler_diagnostics_sha256": sha256(diagnostics_path),
        "posterior_netcdf_manifest_sha256": sha256(posterior_manifest_path),
        "posterior_netcdf_count": len(posterior_manifest),
        "runner_sha256": sha256(script_path),
        "posterior_runner_dependency_sha256": sha256(
            script_path.with_name("ltpp_run_enriched_posterior.py")
        ),
        "git": git_receipt(script_path.parents[1]),
        "oracle_transition_count": len(oracle_ids),
        "excluded_transition_ids": sorted(ORACLE_EXCLUDED_IDS | {"06-2041-T01"}),
        "summaries": summary,
        "claim_boundary": "Non-confirmatory realized-exposure diagnostic only; cannot rescue primary M3 or support deployment or causality.",
    }
    result_path = output / "oracle_result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "LOSO_mae_difference_m": summary["LOSO"]["O3_minus_M3"][
                    "mae_difference_m"
                ],
                "oracle_result_sha256": sha256(result_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
