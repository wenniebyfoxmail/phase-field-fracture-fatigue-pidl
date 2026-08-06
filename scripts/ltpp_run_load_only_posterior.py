#!/usr/bin/env python3
"""Run the frozen 29-row LTPP load-only G versus G+L posterior fit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ltpp_run_enriched_posterior import (
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_SEED,
    aggregate,
    cluster_bootstrap,
    fit_with_locked_retry,
    load_outcomes,
    persistence_rows,
    posterior_predictive_draws,
    prediction_rows,
    section_mae,
    sha256,
    standardize_fold,
    write_csv,
)


AUTHORIZATION_SHA256 = "fddf3fbbde85c0b955db6b60080a8804abdf4f0a7bc60d2186c6571f99f16601"
MANIFEST_STATUS = "PASS_29_BY_4_LOAD_ONLY_INPUT_PREFLIGHT__NO_OUTCOMES__NO_FIT"
FEATURES = {
    "G": (
        "G1_source_crack_length_m",
        "G2_source_crack_area_m2",
        "G3_forecast_horizon_years",
    ),
    "G+L": (
        "G1_source_crack_length_m",
        "G2_source_crack_area_m2",
        "G3_forecast_horizon_years",
        "T1_annual_esal_trend",
    ),
}
EXCLUDED = ["06-1253-T07"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def require(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"missing {label}: {path}")
    return path.resolve()


def contrast_load_only(challenger: list[dict], reference: list[dict]) -> dict:
    challenger_summary = aggregate(challenger)
    reference_summary = aggregate(reference)
    challenger_sections = section_mae(challenger)
    reference_sections = section_mae(reference)
    reduction = (reference_summary["mae_m"] - challenger_summary["mae_m"]) / reference_summary["mae_m"]
    improved = sum(challenger_sections[name] < reference_sections[name] for name in challenger_sections)
    crps_change = (challenger_summary["mean_crps_m"] - reference_summary["mean_crps_m"]) / reference_summary["mean_crps_m"]
    coverage = challenger_summary["coverage_count"]
    gates = {
        "mae_reduction_at_least_10pct": reduction >= 0.10,
        "section_improvement_at_least_4_of_6": improved >= 4,
        "coverage_exactly_25_to_27": 25 <= coverage <= 27,
        "crps_worsening_no_more_than_5pct": crps_change <= 0.05,
    }
    return {
        "challenger": "G+L",
        "reference": "G",
        "overall_contrast": True,
        "mae_reduction_fraction": reduction,
        "improved_section_count": improved,
        "crps_change_fraction": crps_change,
        "gates": gates,
        "passed": all(gates.values()),
        "section_mae_challenger": challenger_sections,
        "section_mae_reference": reference_sections,
        "bootstrap": cluster_bootstrap(challenger, reference),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--transitions", type=Path, required=True)
    parser.add_argument("--transition-manifest", type=Path, required=True)
    parser.add_argument("--environment-lock", type=Path, required=True)
    parser.add_argument("--fit-authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = require(args.input_manifest, "input manifest")
    transitions_path = require(args.transitions, "transitions")
    transition_manifest_path = require(args.transition_manifest, "transition manifest")
    environment_lock = require(args.environment_lock, "environment lock")
    authorization = require(args.fit_authorization, "fit authorization")
    if sha256(authorization) != AUTHORIZATION_SHA256:
        raise ValueError("fit authorization hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != MANIFEST_STATUS:
        raise ValueError("input manifest is not the approved outcome-free preflight")
    if manifest.get("transition_count") != 29 or manifest.get("excluded_transition_ids") != EXCLUDED:
        raise ValueError("input manifest row set mismatch")
    feature_path = manifest_path.parent / manifest["feature_table"]
    split_path = manifest_path.parent / manifest["split_receipt"]
    join_path = manifest_path.parent / manifest["t1_join_receipt"]
    if sha256(feature_path) != manifest["feature_table_sha256"]:
        raise ValueError("feature table hash mismatch")
    if sha256(split_path) != manifest["split_receipt_sha256"]:
        raise ValueError("split receipt hash mismatch")
    if sha256(join_path) != manifest["t1_join_receipt_sha256"]:
        raise ValueError("T1 join receipt hash mismatch")
    split = json.loads(split_path.read_text(encoding="utf-8"))
    if split["transition_count"] != 29 or split["excluded_transition_ids"] != EXCLUDED:
        raise ValueError("split row set mismatch")
    feature_rows = read_csv(feature_path)
    if len(feature_rows) != 29:
        raise ValueError("expected 29 feature rows")
    rows_by_id = {row["transition_id"]: row for row in feature_rows}
    qualified_ids = split["transition_ids"]
    if set(rows_by_id) != set(qualified_ids):
        raise ValueError("feature/split IDs differ")
    transition_manifest = json.loads(transition_manifest_path.read_text(encoding="utf-8"))
    if transition_manifest.get("status") != "PASS_31_ADJUDICATED_LEAKAGE_SAFE_TRANSITIONS":
        raise ValueError("transition manifest is not qualified")
    if sha256(transitions_path) != transition_manifest["transitions_sha256"]:
        raise ValueError("transition outcome source hash mismatch")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    posterior_root = output / "posterior_netcdf"
    posterior_root.mkdir()
    outcomes, outcome_receipt = load_outcomes(transitions_path, qualified_ids)
    outcome_path = output / "sealed_outcomes_29.csv"
    write_csv(outcome_path, outcome_receipt)
    prediction_rows_all = []
    prediction_rows_all.extend(persistence_rows("LOSO", qualified_ids, rows_by_id, outcomes))
    prediction_rows_all.extend(persistence_rows("future_time", split["future_time"]["test_transition_ids"], rows_by_id, outcomes))
    diagnostics = []
    for model_index, (model_name, features) in enumerate(FEATURES.items()):
        designs = [
            {
                "name": "LOSO",
                "fold_index": index,
                "train_ids": fold["train_transition_ids"],
                "eval_ids": fold["test_transition_ids"],
                "unseen_section": True,
                "held_out_section": fold["held_out_section"],
            }
            for index, fold in enumerate(split["loso"])
        ]
        designs.append({
            "name": "future_time",
            "fold_index": 6,
            "train_ids": split["future_time"]["train_transition_ids"],
            "eval_ids": split["future_time"]["test_transition_ids"],
            "unseen_section": False,
            "held_out_section": None,
        })
        for design in designs:
            seed = 260906 + model_index * 100 + design["fold_index"]
            train_x, eval_x, zero_variance = standardize_fold(rows_by_id, design["train_ids"], design["eval_ids"], features)
            train_y = np.log1p([outcomes[row_id]["positive_growth_m"] for row_id in design["train_ids"]])
            train_sections = [rows_by_id[row_id]["section"] for row_id in design["train_ids"]]
            eval_sections = [rows_by_id[row_id]["section"] for row_id in design["eval_ids"]]
            idata, diagnostic = fit_with_locked_retry(train_x, train_y, train_sections, seed)
            diagnostic.update({
                "model": model_name,
                "model_index": model_index,
                "design": design["name"],
                "fold_index": design["fold_index"],
                "held_out_section": design["held_out_section"],
                "train_count": len(design["train_ids"]),
                "evaluation_count": len(design["eval_ids"]),
                "zero_variance_features": zero_variance,
                "active_features": list(features),
            })
            diagnostics.append(diagnostic)
            idata.to_netcdf(posterior_root / f"{model_name.replace('+','plus')}__{design['name']}__fold{design['fold_index']}.nc")
            if not diagnostic["final_passed"]:
                raise RuntimeError(f"sampler diagnostics failed for {model_name} {design['name']} fold {design['fold_index']}")
            final_attempt = diagnostic["attempts"][-1]
            draws = posterior_predictive_draws(idata, eval_x, eval_sections, final_attempt["section_names"], final_attempt["active_column_indices"], design["unseen_section"], seed)
            prediction_rows_all.extend(prediction_rows(model_name, design["name"], design["fold_index"], design["eval_ids"], rows_by_id, outcomes, draws))

    predictions_path = output / "sealed_predictions.csv"
    write_csv(predictions_path, prediction_rows_all)
    diagnostics_path = output / "sampler_diagnostics.json"
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8")
    loso = {name: [row for row in prediction_rows_all if row["model"] == name and row["design"] == "LOSO"] for name in ("B0", "G", "G+L")}
    future = {name: [row for row in prediction_rows_all if row["model"] == name and row["design"] == "future_time"] for name in ("B0", "G", "G+L")}
    summaries = {
        "LOSO": {name: {**aggregate(rows), "section_mae_m": section_mae(rows)} for name, rows in loso.items()},
        "future_time": {name: {**aggregate(rows), "section_mae_m": section_mae(rows)} for name, rows in future.items()},
    }
    contrast = contrast_load_only(loso["G+L"], loso["G"])
    evaluation = {
        "status": "SEALED_LOAD_ONLY_EVALUATION_COMPLETE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "summaries": summaries,
        "contrast": contrast,
        "claim_boundary": "Six-section, 29-transition separately reviewed sensitivity experiment; G+L incremental predictive value only, not causality or crack placement.",
        "excluded_transition_ids": EXCLUDED,
    }
    evaluation_path = output / "sealed_evaluation.json"
    evaluation_path.write_text(json.dumps(evaluation, indent=2) + "\n", encoding="utf-8")
    posterior_manifest = [{"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size} for path in sorted(posterior_root.glob("*.nc"))]
    posterior_manifest_path = output / "posterior_netcdf_manifest.json"
    posterior_manifest_path.write_text(json.dumps(posterior_manifest, indent=2) + "\n", encoding="utf-8")
    provenance = {
        "status": evaluation["status"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner": str(Path(__file__).resolve()),
        "runner_sha256": sha256(Path(__file__).resolve()),
        "imported_posterior_runner": str(Path(__file__).with_name("ltpp_run_enriched_posterior.py").resolve()),
        "fit_authorization": str(authorization),
        "fit_authorization_sha256": sha256(authorization),
        "input_manifest": str(manifest_path),
        "input_manifest_sha256": sha256(manifest_path),
        "feature_table_sha256": sha256(feature_path),
        "join_receipt_sha256": sha256(join_path),
        "split_receipt_sha256": sha256(split_path),
        "transition_manifest_sha256": sha256(transition_manifest_path),
        "transitions_sha256": sha256(transitions_path),
        "environment_lock_sha256": sha256(environment_lock),
        "outcome_receipt_sha256": sha256(outcome_path),
        "git_commit": __import__("subprocess").run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True).stdout.strip(),
        "model_contract": {"models": {name: list(features) for name, features in FEATURES.items()}, "likelihood": "StudentT(nu=4)", "priors": "v4 approved scales", "chains": 4, "draws_per_chain": 2000, "warmup": 2000, "retry_warmup": 4000, "target_accept": 0.90, "retry_target_accept": 0.95},
        "outputs": {"sealed_predictions_sha256": sha256(predictions_path), "sampler_diagnostics_sha256": sha256(diagnostics_path), "sealed_evaluation_sha256": sha256(evaluation_path), "posterior_netcdf_manifest_sha256": sha256(posterior_manifest_path), "posterior_netcdf_count": len(posterior_manifest)},
    }
    provenance_path = output / "RUN_PROVENANCE.json"
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    files = sorted(path for path in output.iterdir() if path.is_file())
    (output / "derived_files.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="ascii")
    print(json.dumps({"status": evaluation["status"], "contrast_passed": contrast["passed"], "loso_G_mae_m": summaries["LOSO"]["G"]["mae_m"], "loso_GL_mae_m": summaries["LOSO"]["G+L"]["mae_m"], "sealed_evaluation_sha256": sha256(evaluation_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
