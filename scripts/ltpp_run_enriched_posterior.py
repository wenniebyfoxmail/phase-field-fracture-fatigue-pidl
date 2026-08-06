#!/usr/bin/env python3
"""Run the frozen LTPP enriched-input posterior and sealed primary evaluation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import arviz as az
import numpy as np
import pymc as pm
import pytensor.tensor as pt

from ltpp_run_enriched_prior_predictive import MODELS, transform


V2_SHA256 = "3b93cdb71be7c32ea6a7524d14ab2b3d3a619a13fcbed9be596d9e2d5c824992"
V3_SHA256 = "f2490cd99b07912567ab52aabcf2ba9472b9514de3dd0fe1c1b1bba4e85ec70d"
V4_SHA256 = "d8fa9840581b1aa0ad9a19a11bd892fdf3ac6d5325ecacb1454f2c9a7f955565"
FIT_AUTHORIZATION_SHA256 = (
    "4ba696915bc85c7b2d656fb3b0c1d3bf3f4572c6037629811a37908ed7bbe27f"
)
FEATURE_MANIFEST_SHA256 = (
    "e17313471628e28573c62f27c84f1fdca197bb20e6d477d28afb60358989aaf3"
)
SPLIT_RECEIPT_SHA256 = (
    "1cb574e0d9e7cb2976f043ad5c83b718c017bff9dff508f1798b603aac4e4a2b"
)
V4_PREFLIGHT_SHA256 = (
    "8689fec9d6644bc3f62a77cdcae3e1409139b5aad095498cb578b8cabde1d644"
)

CHAINS = 4
DRAWS = 2000
TUNE = 2000
TARGET_ACCEPT = 0.90
RETRY_TUNE = 4000
RETRY_TARGET_ACCEPT = 0.95
NU = 4.0
ALPHA_SCALE = 1.0
BETA_SCALE = 0.1
SIGMA_SCALE = 0.5
SIGMA_SECTION_SCALE = 0.5
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 260806


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> Path:
    resolved = path.resolve()
    observed = sha256(resolved)
    if observed != expected:
        raise ValueError(f"{label} hash mismatch: {observed} != {expected}")
    return resolved


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_and_load_inputs(args: argparse.Namespace) -> dict:
    v2 = require_hash(args.v2, V2_SHA256, "v2")
    v3 = require_hash(args.v3, V3_SHA256, "v3")
    v4 = require_hash(args.v4, V4_SHA256, "v4")
    authorization = require_hash(
        args.fit_authorization, FIT_AUTHORIZATION_SHA256, "fit authorization"
    )
    feature_manifest_path = require_hash(
        args.feature_manifest, FEATURE_MANIFEST_SHA256, "feature manifest"
    )
    preflight_path = require_hash(
        args.v4_preflight_report, V4_PREFLIGHT_SHA256, "v4 preflight"
    )
    feature_manifest = json.loads(feature_manifest_path.read_text(encoding="utf-8"))
    if feature_manifest.get("status") != "PASS_30_BY_11_ENRICHED_INPUTS_FROZEN__NO_OUTCOMES__NO_FIT":
        raise ValueError("Feature manifest status is not qualified")
    feature_path = feature_manifest_path.parent / feature_manifest["feature_table"]
    split_path = feature_manifest_path.parent / feature_manifest["split_receipt"]
    if sha256(feature_path) != feature_manifest["feature_table_sha256"]:
        raise ValueError("Feature table hash mismatch")
    if sha256(split_path) != SPLIT_RECEIPT_SHA256:
        raise ValueError("Split receipt hash mismatch")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS_PRIOR_PREDICTIVE_PREFLIGHT__NO_OUTCOME_FIT":
        raise ValueError("V4 prior preflight did not pass")
    if preflight.get("failed_model_folds"):
        raise ValueError("V4 prior preflight contains failed folds")
    if preflight.get("outcome_fields_read") or preflight.get("fit_performed"):
        raise ValueError("V4 preflight boundary is invalid")
    transition_manifest_path = args.transition_manifest.resolve()
    transition_manifest = json.loads(
        transition_manifest_path.read_text(encoding="utf-8")
    )
    if transition_manifest.get("status") != "PASS_31_ADJUDICATED_LEAKAGE_SAFE_TRANSITIONS":
        raise ValueError("Transition manifest is not qualified")
    transitions_path = args.transitions.resolve()
    if sha256(transitions_path) != transition_manifest["transitions_sha256"]:
        raise ValueError("Transition outcome source does not match its manifest")
    feature_rows = read_csv(feature_path)
    split = json.loads(split_path.read_text(encoding="utf-8"))
    if len(feature_rows) != 30 or split.get("transition_count") != 30:
        raise ValueError("Expected exact 30-row v3 set")
    if split.get("excluded_transition_ids") != ["06-2041-T01"]:
        raise ValueError("Split receipt does not contain the sole approved exclusion")
    feature_ids = sorted(row["transition_id"] for row in feature_rows)
    if feature_ids != split["transition_ids"]:
        raise ValueError("Feature and split row sets differ")
    return {
        "paths": {
            "v2": v2,
            "v3": v3,
            "v4": v4,
            "authorization": authorization,
            "feature_manifest": feature_manifest_path,
            "feature_table": feature_path,
            "split_receipt": split_path,
            "v4_preflight": preflight_path,
            "transition_manifest": transition_manifest_path,
            "transitions": transitions_path,
        },
        "feature_manifest": feature_manifest,
        "feature_rows": feature_rows,
        "split": split,
    }


def load_outcomes(
    transitions_path: Path, qualified_ids: list[str]
) -> tuple[dict[str, dict], list[dict]]:
    transitions = json.loads(transitions_path.read_text(encoding="utf-8"))
    source = {row["transition_id"]: row for row in transitions}
    if sorted(set(qualified_ids) - set(source)):
        raise ValueError("Qualified transition is absent from outcome source")
    outcomes = {}
    receipt = []
    for transition_id in qualified_ids:
        row = source[transition_id]
        source_length = float(row["source_geometry"]["crack_line_length_m"])
        target_length = float(row["target_geometry"]["crack_line_length_m"])
        signed = target_length - source_length
        positive = max(0.0, signed)
        frozen_positive = float(row["positive_total_crack_length_increment_m"])
        frozen_signed = float(row["raw_total_crack_length_change_m"])
        if not math.isclose(positive, frozen_positive, abs_tol=1e-9):
            raise ValueError(f"Positive endpoint mismatch for {transition_id}")
        if not math.isclose(signed, frozen_signed, abs_tol=1e-9):
            raise ValueError(f"Signed endpoint mismatch for {transition_id}")
        outcomes[transition_id] = {
            "positive_growth_m": positive,
            "signed_growth_m": signed,
        }
        receipt.append(
            {
                "transition_id": transition_id,
                "section": row["section"],
                "source_crack_length_m": source_length,
                "target_crack_length_m": target_length,
                "signed_growth_m": signed,
                "positive_growth_m": positive,
            }
        )
    return outcomes, receipt


def standardize_fold(
    rows_by_id: dict[str, dict[str, str]],
    train_ids: list[str],
    eval_ids: list[str],
    features: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    train = np.asarray(
        [
            [transform(name, float(rows_by_id[row_id][name])) for name in features]
            for row_id in train_ids
        ],
        dtype=float,
    )
    evaluation = np.asarray(
        [
            [transform(name, float(rows_by_id[row_id][name])) for name in features]
            for row_id in eval_ids
        ],
        dtype=float,
    )
    means = train.mean(axis=0)
    standard_deviations = train.std(axis=0, ddof=0)
    zero_variance = [
        name
        for name, value in zip(features, standard_deviations)
        if math.isclose(float(value), 0.0, abs_tol=1e-15)
    ]
    safe_sd = np.where(standard_deviations == 0.0, 1.0, standard_deviations)
    train_z = (train - means) / safe_sd
    eval_z = (evaluation - means) / safe_sd
    for index, name in enumerate(features):
        if name in zero_variance:
            train_z[:, index] = 0.0
            eval_z[:, index] = 0.0
    return train_z, eval_z, zero_variance


def diagnostic_values(idata: az.InferenceData, variable_names: list[str]) -> dict:
    def extrema(dataset: object, operation: str) -> float:
        values = np.asarray(dataset.to_array().values, dtype=float)
        values = values[np.isfinite(values)]
        if not len(values):
            return math.nan
        return float(np.max(values) if operation == "max" else np.min(values))

    posterior = idata.posterior.dataset
    rhat = extrema(az.rhat(posterior, var_names=variable_names), "max")
    bulk = extrema(
        az.ess(posterior, var_names=variable_names, method="bulk"), "min"
    )
    tail = extrema(
        az.ess(posterior, var_names=variable_names, method="tail"), "min"
    )
    divergences = int(
        np.asarray(idata.sample_stats.dataset["diverging"]).sum()
    )
    passed = (
        math.isfinite(rhat)
        and rhat < 1.01
        and bulk >= 400
        and tail >= 400
        and divergences == 0
    )
    return {
        "rhat_max": rhat,
        "bulk_ess_min": bulk,
        "tail_ess_min": tail,
        "post_warmup_divergences": divergences,
        "passed": passed,
    }


def fit_once(
    train_x: np.ndarray,
    train_y: np.ndarray,
    train_sections: list[str],
    seed: int,
    tune: int,
    target_accept: float,
) -> tuple[az.InferenceData, dict]:
    section_names = sorted(set(train_sections))
    section_lookup = {name: index for index, name in enumerate(section_names)}
    section_index = np.asarray([section_lookup[name] for name in train_sections])
    active_columns = np.flatnonzero(np.any(train_x != 0.0, axis=0))
    active_x = train_x[:, active_columns]
    started = time.monotonic()
    with pm.Model() as model:
        alpha = pm.Normal("alpha", mu=0.0, sigma=ALPHA_SCALE)
        sigma = pm.HalfNormal("sigma", sigma=SIGMA_SCALE)
        sigma_section = pm.HalfNormal(
            "sigma_section", sigma=SIGMA_SECTION_SCALE
        )
        b_raw = pm.Normal("b_raw", mu=0.0, sigma=1.0, shape=len(section_names))
        b = pm.Deterministic("b", b_raw * sigma_section)
        if len(active_columns):
            beta = pm.Normal(
                "beta", mu=0.0, sigma=BETA_SCALE, shape=len(active_columns)
            )
            linear = pt.dot(active_x, beta)
        else:
            linear = pt.zeros(train_x.shape[0])
        mu = alpha + linear + b[section_index]
        pm.StudentT("y", nu=NU, mu=mu, sigma=sigma, observed=train_y)
        idata = pm.sample(
            draws=DRAWS,
            tune=tune,
            chains=CHAINS,
            cores=CHAINS,
            random_seed=seed,
            target_accept=target_accept,
            return_inferencedata=True,
            progressbar=False,
            compute_convergence_checks=False,
        )
    variable_names = ["alpha", "sigma", "sigma_section", "b_raw"]
    if len(active_columns):
        variable_names.append("beta")
    diagnostics = diagnostic_values(idata, variable_names)
    diagnostics.update(
        {
            "elapsed_seconds": time.monotonic() - started,
            "tune": tune,
            "draws_per_chain": DRAWS,
            "chains": CHAINS,
            "target_accept": target_accept,
            "seed": seed,
            "section_names": section_names,
            "active_column_indices": active_columns.tolist(),
        }
    )
    return idata, diagnostics


def fit_with_locked_retry(
    train_x: np.ndarray,
    train_y: np.ndarray,
    train_sections: list[str],
    seed: int,
) -> tuple[az.InferenceData, dict]:
    attempts = []
    idata, first = fit_once(
        train_x, train_y, train_sections, seed, TUNE, TARGET_ACCEPT
    )
    attempts.append(first)
    if first["passed"]:
        return idata, {"attempts": attempts, "final_passed": True, "retry_used": False}
    idata, retry = fit_once(
        train_x, train_y, train_sections, seed, RETRY_TUNE, RETRY_TARGET_ACCEPT
    )
    attempts.append(retry)
    return idata, {
        "attempts": attempts,
        "final_passed": retry["passed"],
        "retry_used": True,
    }


def flatten_posterior(idata: az.InferenceData, name: str) -> np.ndarray:
    values = np.asarray(idata.posterior.dataset[name].values)
    return values.reshape((-1,) + values.shape[2:])


def posterior_predictive_draws(
    idata: az.InferenceData,
    eval_x: np.ndarray,
    eval_sections: list[str],
    training_section_names: list[str],
    active_columns: list[int],
    unseen_section: bool,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    alpha = flatten_posterior(idata, "alpha")
    sigma = flatten_posterior(idata, "sigma")
    sigma_section = flatten_posterior(idata, "sigma_section")
    b = flatten_posterior(idata, "b")
    sample_count = len(alpha)
    if active_columns:
        beta = flatten_posterior(idata, "beta")
        linear = beta @ eval_x[:, active_columns].T
    else:
        linear = np.zeros((sample_count, len(eval_x)))
    if unseen_section:
        if len(set(eval_sections)) != 1:
            raise ValueError("LOSO evaluation must contain exactly one unseen section")
        section_effect = rng.normal(0.0, sigma_section)[:, None]
    else:
        lookup = {name: index for index, name in enumerate(training_section_names)}
        if set(eval_sections) - set(lookup):
            raise ValueError("Future-time evaluation contains an unseen section")
        section_effect = np.column_stack([b[:, lookup[name]] for name in eval_sections])
    mu = alpha[:, None] + linear + section_effect
    noise = rng.standard_t(NU, size=mu.shape) * sigma[:, None]
    y_draws = mu + noise
    with np.errstate(over="ignore", invalid="ignore"):
        growth = np.maximum(0.0, np.expm1(y_draws))
    return growth


def empirical_crps(draws: np.ndarray, observed: float) -> float:
    ordered = np.sort(np.asarray(draws, dtype=float))
    if not np.all(np.isfinite(ordered)):
        raise ValueError("Non-finite posterior-predictive draw")
    count = len(ordered)
    first = float(np.mean(np.abs(ordered - observed)))
    coefficients = 2 * np.arange(1, count + 1) - count - 1
    half_pairwise = float(np.sum(coefficients * ordered) / (count * count))
    return first - half_pairwise


def prediction_rows(
    model: str,
    design: str,
    fold_index: int,
    eval_ids: list[str],
    rows_by_id: dict[str, dict[str, str]],
    outcomes: dict[str, dict],
    draws: np.ndarray,
) -> list[dict]:
    rows = []
    for column, transition_id in enumerate(eval_ids):
        values = draws[:, column]
        actual = outcomes[transition_id]["positive_growth_m"]
        median = float(np.median(values))
        q05 = float(np.quantile(values, 0.05))
        q95 = float(np.quantile(values, 0.95))
        rows.append(
            {
                "model": model,
                "design": design,
                "fold_index": fold_index,
                "transition_id": transition_id,
                "section": rows_by_id[transition_id]["section"],
                "actual_positive_growth_m": actual,
                "actual_signed_growth_m": outcomes[transition_id]["signed_growth_m"],
                "prediction_median_m": median,
                "prediction_q05_m": q05,
                "prediction_q95_m": q95,
                "absolute_error_m": abs(median - actual),
                "squared_error_m2": (median - actual) ** 2,
                "covered_90": int(q05 <= actual <= q95),
                "crps_m": empirical_crps(values, actual),
                "posterior_predictive_draw_count": len(values),
            }
        )
    return rows


def persistence_rows(
    design: str,
    transition_ids: list[str],
    rows_by_id: dict[str, dict[str, str]],
    outcomes: dict[str, dict],
) -> list[dict]:
    rows = []
    for transition_id in transition_ids:
        actual = outcomes[transition_id]["positive_growth_m"]
        rows.append(
            {
                "model": "B0",
                "design": design,
                "fold_index": -1,
                "transition_id": transition_id,
                "section": rows_by_id[transition_id]["section"],
                "actual_positive_growth_m": actual,
                "actual_signed_growth_m": outcomes[transition_id]["signed_growth_m"],
                "prediction_median_m": 0.0,
                "prediction_q05_m": 0.0,
                "prediction_q95_m": 0.0,
                "absolute_error_m": actual,
                "squared_error_m2": actual * actual,
                "covered_90": int(actual == 0.0),
                "crps_m": actual,
                "posterior_predictive_draw_count": 1,
            }
        )
    return rows


def aggregate(rows: list[dict]) -> dict:
    return {
        "count": len(rows),
        "mae_m": float(np.mean([row["absolute_error_m"] for row in rows])),
        "rmse_m": float(
            math.sqrt(np.mean([row["squared_error_m2"] for row in rows]))
        ),
        "mean_crps_m": float(np.mean([row["crps_m"] for row in rows])),
        "coverage_count": int(sum(row["covered_90"] for row in rows)),
        "coverage_fraction": float(np.mean([row["covered_90"] for row in rows])),
    }


def section_mae(rows: list[dict]) -> dict[str, float]:
    sections = sorted({row["section"] for row in rows})
    return {
        section: float(
            np.mean(
                [row["absolute_error_m"] for row in rows if row["section"] == section]
            )
        )
        for section in sections
    }


def cluster_bootstrap(
    challenger: list[dict], reference: list[dict]
) -> dict[str, float | int]:
    challenger_by_id = {row["transition_id"]: row for row in challenger}
    reference_by_id = {row["transition_id"]: row for row in reference}
    if set(challenger_by_id) != set(reference_by_id):
        raise ValueError("Bootstrap comparisons require matched rows")
    sections = sorted({row["section"] for row in challenger})
    ids_by_section = {
        section: [
            transition_id
            for transition_id, row in challenger_by_id.items()
            if row["section"] == section
        ]
        for section in sections
    }
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    differences = np.empty(BOOTSTRAP_DRAWS)
    for draw in range(BOOTSTRAP_DRAWS):
        sampled = rng.choice(sections, size=len(sections), replace=True)
        ids = [transition_id for section in sampled for transition_id in ids_by_section[section]]
        differences[draw] = np.mean(
            [
                challenger_by_id[transition_id]["absolute_error_m"]
                - reference_by_id[transition_id]["absolute_error_m"]
                for transition_id in ids
            ]
        )
    return {
        "draws": BOOTSTRAP_DRAWS,
        "seed": BOOTSTRAP_SEED,
        "mae_difference_challenger_minus_reference_m": float(
            np.mean(differences)
        ),
        "q025_m": float(np.quantile(differences, 0.025)),
        "q975_m": float(np.quantile(differences, 0.975)),
    }


def contrast(
    challenger_name: str,
    reference_name: str,
    rows_by_model: dict[str, list[dict]],
    overall: bool = False,
) -> dict:
    challenger = rows_by_model[challenger_name]
    reference = rows_by_model[reference_name]
    challenger_summary = aggregate(challenger)
    reference_summary = aggregate(reference)
    challenger_sections = section_mae(challenger)
    reference_sections = section_mae(reference)
    reduction = (
        reference_summary["mae_m"] - challenger_summary["mae_m"]
    ) / reference_summary["mae_m"]
    improved_sections = sum(
        challenger_sections[name] < reference_sections[name]
        for name in challenger_sections
    )
    crps_change = (
        challenger_summary["mean_crps_m"] - reference_summary["mean_crps_m"]
    ) / reference_summary["mean_crps_m"]
    gates = {
        "mae_reduction_at_least_10pct": reduction >= 0.10,
        "section_improvement_at_least_4_of_6": improved_sections >= 4,
        "coverage_exactly_26_to_28": 26
        <= challenger_summary["coverage_count"]
        <= 28,
        "crps_worsening_no_more_than_5pct": crps_change <= 0.05,
    }
    return {
        "challenger": challenger_name,
        "reference": reference_name,
        "overall_contrast": overall,
        "mae_reduction_fraction": reduction,
        "improved_section_count": improved_sections,
        "crps_change_fraction": crps_change,
        "gates": gates,
        "passed": all(gates.values()),
        "section_mae_challenger": challenger_sections,
        "section_mae_reference": reference_sections,
        "bootstrap": cluster_bootstrap(challenger, reference),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2", type=Path, required=True)
    parser.add_argument("--v3", type=Path, required=True)
    parser.add_argument("--v4", type=Path, required=True)
    parser.add_argument("--fit-authorization", type=Path, required=True)
    parser.add_argument("--feature-manifest", type=Path, required=True)
    parser.add_argument("--v4-preflight-report", type=Path, required=True)
    parser.add_argument("--transitions", type=Path, required=True)
    parser.add_argument("--transition-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = verify_and_load_inputs(args)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    posterior_root = output / "posterior_netcdf"
    posterior_root.mkdir()
    script_path = Path(__file__).resolve()
    dependency_path = Path(__file__).with_name("ltpp_run_enriched_prior_predictive.py").resolve()

    rows_by_id = {row["transition_id"]: row for row in inputs["feature_rows"]}
    qualified_ids = inputs["split"]["transition_ids"]
    outcomes, outcome_receipt = load_outcomes(
        inputs["paths"]["transitions"], qualified_ids
    )
    outcome_path = output / "sealed_outcomes_30.csv"
    write_csv(outcome_path, outcome_receipt)

    provenance = {
        "status": "FIT_AUTHORIZED__RUNNING",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner": str(script_path),
        "runner_sha256": sha256(script_path),
        "dependency": str(dependency_path),
        "dependency_sha256": sha256(dependency_path),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "pymc_version": pm.__version__,
        "arviz_version": az.__version__,
        "numpy_version": np.__version__,
        "argv": sys.argv,
        "input_hashes": {name: sha256(path) for name, path in inputs["paths"].items()},
        "outcome_receipt": outcome_path.name,
        "outcome_receipt_sha256": sha256(outcome_path),
        "model_contract": {
            "likelihood": "StudentT(nu=4,mu,sigma)",
            "priors": {
                "alpha": "Normal(0,1)",
                "beta": "Normal(0,0.1)",
                "sigma": "HalfNormal(0.5)",
                "sigma_section": "HalfNormal(0.5)",
            },
            "chains": CHAINS,
            "draws_per_chain": DRAWS,
            "warmup": TUNE,
            "target_accept": TARGET_ACCEPT,
            "retry_warmup": RETRY_TUNE,
            "retry_target_accept": RETRY_TARGET_ACCEPT,
        },
    }
    provenance_path = output / "RUN_PROVENANCE.json"
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    prediction_output = []
    diagnostics_output = []
    primary_loso_ids = qualified_ids
    future_ids = inputs["split"]["future_time"]["test_transition_ids"]
    prediction_output.extend(
        persistence_rows("LOSO", primary_loso_ids, rows_by_id, outcomes)
    )
    prediction_output.extend(
        persistence_rows("future_time", future_ids, rows_by_id, outcomes)
    )

    for model_index, (model_name, features) in enumerate(MODELS.items()):
        designs = [
            {
                "name": "LOSO",
                "fold_index": fold_index,
                "train_ids": fold["train_transition_ids"],
                "eval_ids": fold["test_transition_ids"],
                "unseen_section": True,
                "held_out_section": fold["held_out_section"],
            }
            for fold_index, fold in enumerate(inputs["split"]["loso"])
        ]
        future = inputs["split"]["future_time"]
        designs.append(
            {
                "name": "future_time",
                "fold_index": 6,
                "train_ids": future["train_transition_ids"],
                "eval_ids": future["test_transition_ids"],
                "unseen_section": False,
                "held_out_section": None,
            }
        )
        for design in designs:
            seed = 260806 + design["fold_index"]
            train_x, eval_x, zero_variance = standardize_fold(
                rows_by_id,
                design["train_ids"],
                design["eval_ids"],
                features,
            )
            train_y = np.log1p(
                [outcomes[row_id]["positive_growth_m"] for row_id in design["train_ids"]]
            )
            train_sections = [rows_by_id[row_id]["section"] for row_id in design["train_ids"]]
            eval_sections = [rows_by_id[row_id]["section"] for row_id in design["eval_ids"]]
            idata, diagnostic = fit_with_locked_retry(
                train_x, train_y, train_sections, seed
            )
            diagnostic.update(
                {
                    "model": model_name,
                    "model_index": model_index,
                    "design": design["name"],
                    "fold_index": design["fold_index"],
                    "held_out_section": design["held_out_section"],
                    "train_count": len(design["train_ids"]),
                    "evaluation_count": len(design["eval_ids"]),
                    "zero_variance_features": zero_variance,
                }
            )
            diagnostics_output.append(diagnostic)
            netcdf_path = posterior_root / (
                f"{model_name}__{design['name']}__fold{design['fold_index']}.nc"
            )
            idata.to_netcdf(netcdf_path)
            if not diagnostic["final_passed"]:
                diagnostics_path = output / "sampler_diagnostics.json"
                diagnostics_path.write_text(
                    json.dumps(diagnostics_output, indent=2) + "\n", encoding="utf-8"
                )
                print(
                    json.dumps(
                        {
                            "status": "INVALID_SAMPLER_DIAGNOSTICS",
                            "model": model_name,
                            "design": design["name"],
                            "fold_index": design["fold_index"],
                        }
                    )
                )
                return 4
            final_attempt = diagnostic["attempts"][-1]
            draws = posterior_predictive_draws(
                idata,
                eval_x,
                eval_sections,
                final_attempt["section_names"],
                final_attempt["active_column_indices"],
                design["unseen_section"],
                seed,
            )
            prediction_output.extend(
                prediction_rows(
                    model_name,
                    design["name"],
                    design["fold_index"],
                    design["eval_ids"],
                    rows_by_id,
                    outcomes,
                    draws,
                )
            )

    predictions_path = output / "sealed_predictions.csv"
    write_csv(predictions_path, prediction_output)
    diagnostics_path = output / "sampler_diagnostics.json"
    diagnostics_path.write_text(
        json.dumps(diagnostics_output, indent=2) + "\n", encoding="utf-8"
    )
    loso_by_model = {
        model: [
            row
            for row in prediction_output
            if row["model"] == model and row["design"] == "LOSO"
        ]
        for model in ("B0", "M0", "M1", "M2", "M3")
    }
    future_by_model = {
        model: [
            row
            for row in prediction_output
            if row["model"] == model and row["design"] == "future_time"
        ]
        for model in ("B0", "M0", "M1", "M2", "M3")
    }
    summaries = {
        "LOSO": {
            model: {**aggregate(rows), "section_mae_m": section_mae(rows)}
            for model, rows in loso_by_model.items()
        },
        "future_time": {
            model: {**aggregate(rows), "section_mae_m": section_mae(rows)}
            for model, rows in future_by_model.items()
        },
    }
    contrasts = [
        contrast("M1", "M0", loso_by_model),
        contrast("M2", "M1", loso_by_model),
        contrast("M3", "M2", loso_by_model),
        contrast("M3", "B0", loso_by_model, overall=True),
    ]
    status = "SEALED_PRIMARY_EVALUATION_COMPLETE__ORACLE_PENDING"
    evaluation = {
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "summaries": summaries,
        "contrasts": contrasts,
        "signed_growth_descriptive": {
            "count_negative": sum(
                outcomes[row_id]["signed_growth_m"] < 0 for row_id in qualified_ids
            ),
            "minimum_m": min(
                outcomes[row_id]["signed_growth_m"] for row_id in qualified_ids
            ),
            "maximum_m": max(
                outcomes[row_id]["signed_growth_m"] for row_id in qualified_ids
            ),
        },
        "claim_boundary": "Six-section, 30-transition separately reviewed sensitivity protocol; predictive information value only, not causality or crack placement.",
    }
    evaluation_path = output / "sealed_evaluation.json"
    evaluation_path.write_text(
        json.dumps(evaluation, indent=2) + "\n", encoding="utf-8"
    )
    posterior_manifest = [
        {
            "file": path.name,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(posterior_root.glob("*.nc"))
    ]
    posterior_manifest_path = output / "posterior_netcdf_manifest.json"
    posterior_manifest_path.write_text(
        json.dumps(posterior_manifest, indent=2) + "\n", encoding="utf-8"
    )
    provenance["status"] = status
    provenance["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    provenance["outputs"] = {
        "sealed_predictions": predictions_path.name,
        "sealed_predictions_sha256": sha256(predictions_path),
        "sampler_diagnostics": diagnostics_path.name,
        "sampler_diagnostics_sha256": sha256(diagnostics_path),
        "sealed_evaluation": evaluation_path.name,
        "sealed_evaluation_sha256": sha256(evaluation_path),
        "posterior_netcdf_manifest": posterior_manifest_path.name,
        "posterior_netcdf_manifest_sha256": sha256(posterior_manifest_path),
        "posterior_netcdf_count": len(posterior_manifest),
    }
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    hashed = sorted(path for path in output.iterdir() if path.is_file())
    (output / "derived_files.sha256").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in hashed), encoding="ascii"
    )
    print(
        json.dumps(
            {
                "status": status,
                "contrasts": [
                    {
                        "challenger": row["challenger"],
                        "reference": row["reference"],
                        "passed": row["passed"],
                    }
                    for row in contrasts
                ],
                "sealed_evaluation_sha256": sha256(evaluation_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
