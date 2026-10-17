from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from .multi_environment import (
    balanced_stack,
    forcing_correlation,
    shared_support_select,
)
from .selectors import fit_stlsq, stability_validated_select, validation_select_support
from .structured_adapter import AdapterConfig, hash_frozen_arrays
from .synthetic_forecast import (
    DYNAMIC_TERM_NAMES,
    TRUE_DYNAMIC_BETA,
    ForecastConfig,
    _beta_dict,
    _event_index,
    _mask_iou,
    _rollout_section,
    _support_metrics,
    _tip,
    fit_frozen_adapter,
    generate_dynamic_truth,
    sample_sparse_observations,
)
from .weak_system import WeakSystem, assemble_dynamic_weak_system


def loso_split(holdout: int, n_environments: int = 8) -> tuple[list[int], int, int]:
    if n_environments < 4:
        raise ValueError("LOSO requires at least four environments")
    if holdout < 0 or holdout >= n_environments:
        raise ValueError("holdout is outside the environment range")
    validation = (holdout + 1) % n_environments
    train = [index for index in range(n_environments) if index not in {holdout, validation}]
    return train, validation, holdout


def _systems_by_section(
    frame: pd.DataFrame,
    config: ForecastConfig,
    *,
    n_windows: int,
    seed_offset: int,
) -> dict[int, WeakSystem]:
    systems: dict[int, WeakSystem] = {}
    for section in range(config.n_sections):
        trajectory_id = f"synthetic_section_{section}"
        block = frame[
            (frame["trajectory_id"] == trajectory_id)
            & (frame["cycle"] <= config.cutoff_index)
        ].copy()
        systems[section] = assemble_dynamic_weak_system(
            block,
            term_names=DYNAMIC_TERM_NAMES,
            n_windows=n_windows,
            seed=config.seed + seed_offset + 101 * section,
        )
    return systems


def _fit_columns(system: WeakSystem, columns: np.ndarray, l2: float = 1e-8) -> np.ndarray:
    beta = np.zeros(system.A.shape[1], dtype=float)
    if columns.size:
        selected = system.A[:, columns]
        gram = np.einsum("ni,nj->ij", selected, selected, optimize=False)
        rhs = np.einsum("ni,n->i", selected, system.b, optimize=False)
        beta[columns] = np.linalg.solve(gram + l2 * np.eye(columns.size), rhs)
    return beta


def _pairwise_support_jaccard(supports: list[set[str]]) -> float:
    values: list[float] = []
    for left in range(len(supports)):
        for right in range(left + 1, len(supports)):
            union = supports[left] | supports[right]
            values.append(len(supports[left] & supports[right]) / max(len(union), 1))
    return float(np.median(values)) if values else 1.0


def _confounded_pair_correlation(system: WeakSystem) -> float:
    left = system.term_names.index("damage_hplus_moisture_log_traffic")
    right = system.term_names.index("damage_hplus_low_temp_log_traffic")
    return float(abs(np.corrcoef(system.A[:, left], system.A[:, right])[0, 1]))


def _false_frequency(supports: list[set[str]]) -> float:
    false_terms = set(DYNAMIC_TERM_NAMES) - set(TRUE_DYNAMIC_BETA)
    if not supports:
        return 1.0
    return max(
        sum(term in support for support in supports) / len(supports)
        for term in false_terms
    )


def _forecast_row(
    *,
    method: str,
    beta: dict[str, float],
    initial: np.ndarray,
    true_states: np.ndarray,
    section: int,
    config: ForecastConfig,
    x_grid: np.ndarray,
) -> dict[str, object]:
    predicted = _rollout_section(initial, section, config, beta)
    return {
        "fold": section,
        "method": method,
        "final_iou_d025": _mask_iou(predicted[-1], true_states[-1], 0.25),
        "final_iou_d050": _mask_iou(predicted[-1], true_states[-1], 0.50),
        "final_iou_d075": _mask_iou(predicted[-1], true_states[-1], 0.75),
        "final_tip_error": abs(_tip(predicted[-1], x_grid) - _tip(true_states[-1], x_grid)),
        "event_time_error": abs(
            _event_index(predicted, config.event_area_fraction)
            - _event_index(true_states, config.event_area_fraction)
        ),
        "forecast_rmse": float(np.sqrt(np.mean(np.square(predicted - true_states)))),
    }


def run_stage_a4(
    config: ForecastConfig,
    output_dir: Path,
    *,
    adapter_config: AdapterConfig | None = None,
) -> dict[str, object]:
    if config.n_sections != 8 or config.excitation_design != "balanced_2pow3":
        raise ValueError("Stage A4 requires eight balanced_2pow3 environments")
    adapter_config = AdapterConfig() if adapter_config is None else adapter_config
    output_dir.mkdir(parents=True, exist_ok=True)
    truth = generate_dynamic_truth(config)
    forcing_max_correlation = forcing_correlation(truth)
    observations = sample_sparse_observations(truth, config)
    reconstructed, manifests = fit_frozen_adapter(truth, observations, config, adapter_config)
    oracle_systems = _systems_by_section(
        truth, config, n_windows=config.n_windows, seed_offset=0
    )
    recon_systems = _systems_by_section(
        reconstructed, config, n_windows=config.n_windows, seed_offset=0
    )
    rowmatched_systems = _systems_by_section(
        reconstructed,
        config,
        n_windows=config.n_windows * 6,
        seed_offset=5000,
    )

    x = np.linspace(0.0, 1.0, config.nx)
    y = np.linspace(-0.5, 0.5, config.ny)
    x_grid, _ = np.meshgrid(x, y)
    true_columns = np.asarray(
        [DYNAMIC_TERM_NAMES.index(term) for term in TRUE_DYNAMIC_BETA], dtype=int
    )
    fold_rows: list[dict[str, object]] = []
    forecast_rows: list[dict[str, object]] = []
    support_rows: list[pd.DataFrame] = []
    selected_supports: dict[str, list[set[str]]] = {
        "shared": [], "pooled_svws": [], "single": [], "rowmatched": [], "cloned": [], "oracle": []
    }
    split_manifest: list[dict[str, object]] = []

    for holdout in range(config.n_sections):
        train_ids, validation_id, test_id = loso_split(holdout, config.n_sections)
        train_oracle = [oracle_systems[index] for index in train_ids]
        train_recon = [recon_systems[index] for index in train_ids]
        validation_oracle = oracle_systems[validation_id]
        validation_recon = recon_systems[validation_id]
        oracle = shared_support_select(
            train_oracle,
            validation_oracle,
            n_trials=config.n_trials,
            seed=config.seed + 10000 + holdout,
        )
        shared = shared_support_select(
            train_recon,
            validation_recon,
            n_trials=config.n_trials,
            seed=config.seed + 20000 + holdout,
        )
        pooled_system = balanced_stack(train_recon)
        pooled = stability_validated_select(
            pooled_system, n_trials=config.n_trials, seed=config.seed + 30000 + holdout
        )
        pooled_validated = validation_select_support(
            pooled, pooled_system, validation_recon
        )
        single_beta = fit_stlsq(pooled_system.A, pooled_system.b)
        single_support = {
            term for term, value in zip(DYNAMIC_TERM_NAMES, single_beta) if abs(value) > 1e-12
        }
        control_id = train_ids[0]
        rowmatched_system = rowmatched_systems[control_id]
        rowmatched = stability_validated_select(
            rowmatched_system,
            n_trials=config.n_trials,
            seed=config.seed + 40000 + holdout,
        )
        rowmatched_validated = validation_select_support(
            rowmatched, rowmatched_system, validation_recon
        )
        cloned = shared_support_select(
            [recon_systems[control_id]] * len(train_ids),
            validation_recon,
            n_trials=config.n_trials,
            seed=config.seed + 50000 + holdout,
        )
        allterm_beta = _fit_columns(
            pooled_system, np.arange(len(DYNAMIC_TERM_NAMES), dtype=int)
        )
        true_support_beta = _fit_columns(pooled_system, true_columns)

        support_by_method = {
            "shared": set(shared.support),
            "pooled_svws": set(pooled_validated.support),
            "single": single_support,
            "rowmatched": set(rowmatched_validated.support),
            "cloned": set(cloned.support),
            "oracle": set(oracle.support),
        }
        for method, support in support_by_method.items():
            selected_supports[method].append(support)

        stacked = balanced_stack(train_recon)
        median_single_corr = float(
            np.median(shared.diagnostics.per_environment_max_abs_correlation)
        )
        confounded_single = float(
            np.median([_confounded_pair_correlation(system) for system in train_recon])
        )
        confounded_stacked = _confounded_pair_correlation(stacked)
        tip_fraction = float(
            np.mean(stacked.metadata["stratum"].to_numpy(str) == "tip")
        )
        fold_rows.append(
            {
                "fold": holdout,
                "train_sections": ",".join(map(str, train_ids)),
                "validation_section": validation_id,
                "test_section": test_id,
                "shared_support": ",".join(shared.support),
                "oracle_support_jaccard": _support_metrics(set(oracle.support))["support_jaccard"],
                "shared_support_jaccard": _support_metrics(set(shared.support))["support_jaccard"],
                "pooled_svws_support_jaccard": _support_metrics(set(pooled_validated.support))["support_jaccard"],
                "single_support_jaccard": _support_metrics(single_support)["support_jaccard"],
                "rowmatched_support_jaccard": _support_metrics(set(rowmatched_validated.support))["support_jaccard"],
                "cloned_support_jaccard": _support_metrics(set(cloned.support))["support_jaccard"],
                "max_abs_candidate_correlation": shared.diagnostics.max_abs_correlation,
                "median_single_environment_correlation": median_single_corr,
                "condition_number": shared.diagnostics.condition_number,
                "effective_rank": shared.diagnostics.effective_rank,
                "max_environment_leverage": shared.diagnostics.max_environment_leverage,
                "confounded_pair_correlation": confounded_stacked,
                "confounded_pair_correlation_drop": confounded_single - confounded_stacked,
                "tip_weight_fraction": tip_fraction,
            }
        )
        summary = shared.support_summary.copy()
        summary.insert(0, "fold", holdout)
        support_rows.append(summary)

        trajectory_id = f"synthetic_section_{holdout}"
        true_blocks = truth[truth["trajectory_id"] == trajectory_id].sort_values(
            ["cycle", "cell_id"]
        )
        true_states = true_blocks["d"].to_numpy(float).reshape(
            config.n_times, config.ny, config.nx
        )[config.cutoff_index :]
        recon_cutoff = reconstructed[
            (reconstructed["trajectory_id"] == trajectory_id)
            & (reconstructed["cycle"] == config.cutoff_index)
        ].sort_values("cell_id")["d"].to_numpy(float).reshape(config.ny, config.nx)
        true_cutoff = true_states[0]
        beta_by_method = {
            "oracle_shared": (_beta_dict(DYNAMIC_TERM_NAMES, oracle.coefficients.to_numpy(float)), true_cutoff),
            "reconstructed_shared": (_beta_dict(DYNAMIC_TERM_NAMES, shared.coefficients.to_numpy(float)), recon_cutoff),
            "pooled_svws": (_beta_dict(DYNAMIC_TERM_NAMES, pooled_validated.coefficients.to_numpy(float)), recon_cutoff),
            "pooled_single_shot": (_beta_dict(DYNAMIC_TERM_NAMES, single_beta), recon_cutoff),
            "rowmatched_one_environment": (_beta_dict(DYNAMIC_TERM_NAMES, rowmatched_validated.coefficients.to_numpy(float)), recon_cutoff),
            "cloned_environment": (_beta_dict(DYNAMIC_TERM_NAMES, cloned.coefficients.to_numpy(float)), recon_cutoff),
            "all_term_ridge": (_beta_dict(DYNAMIC_TERM_NAMES, allterm_beta), recon_cutoff),
            "true_support_fit": (_beta_dict(DYNAMIC_TERM_NAMES, true_support_beta), recon_cutoff),
            "fixed_physics_only": ({}, recon_cutoff),
        }
        for method, (beta, initial) in beta_by_method.items():
            forecast_rows.append(
                _forecast_row(
                    method=method,
                    beta=beta,
                    initial=initial,
                    true_states=true_states,
                    section=holdout,
                    config=config,
                    x_grid=x_grid,
                )
            )
        split_manifest.append(
            {
                "fold": holdout,
                "selection_sections": train_ids,
                "internal_validation_section": validation_id,
                "untouched_test_section": test_id,
                "future_damage_used_by_adapter": False,
                "test_weak_rows_used_by_selector": False,
                "test_response_used_for_coefficients": False,
            }
        )

    folds = pd.DataFrame(fold_rows)
    forecasts = pd.DataFrame(forecast_rows)
    support_table = pd.concat(support_rows, ignore_index=True)
    forecast_summary = forecasts.groupby("method", as_index=False).median(numeric_only=True)
    cutoff_rows: list[float] = []
    for section in range(config.n_sections):
        trajectory_id = f"synthetic_section_{section}"
        block = reconstructed[
            (reconstructed["trajectory_id"] == trajectory_id)
            & (reconstructed["cycle"] == config.cutoff_index)
        ]
        cutoff_rows.append(
            _mask_iou(block["d"].to_numpy(float), block["d_true_audit"].to_numpy(float), 0.5)
        )
    cutoff_iou = float(np.median(cutoff_rows))

    method_metrics = {
        method: forecast_summary[forecast_summary["method"] == method].iloc[0]
        for method in forecast_summary["method"]
    }
    shared_forecast = method_metrics["reconstructed_shared"]
    fixed_forecast = method_metrics["fixed_physics_only"]
    single_forecast = method_metrics["pooled_single_shot"]
    median_support = {
        method: float(np.median([_support_metrics(value)["support_jaccard"] for value in supports]))
        for method, supports in selected_supports.items()
    }
    true_frequency = {
        term: sum(term in support for support in selected_supports["shared"]) / len(selected_supports["shared"])
        for term in TRUE_DYNAMIC_BETA
    }
    false_frequency = _false_frequency(selected_supports["shared"])
    cloned_false_frequency = _false_frequency(selected_supports["cloned"])
    support_stability = _pairwise_support_jaccard(selected_supports["shared"])
    identifiability_gate = bool(
        forcing_max_correlation <= 0.35
        and float(folds["max_abs_candidate_correlation"].max()) <= 0.90
        and int(folds["effective_rank"].min()) >= 6
        and float(folds["condition_number"].max()) <= 1e6
        and float(folds["max_environment_leverage"].max()) <= 0.40
        and (
            float(folds["confounded_pair_correlation_drop"].median()) >= 0.20
            or float(folds["confounded_pair_correlation"].median()) <= 0.85
        )
    )
    support_gate = bool(
        median_support["oracle"] >= 0.90
        and median_support["shared"] >= 0.75
        and median_support["shared"] > median_support["pooled_svws"]
        and median_support["shared"] > median_support["single"]
        and support_stability >= 0.70
        and min(true_frequency.values()) >= 0.75
        and false_frequency <= 0.45
    )
    diversity_gate = bool(
        median_support["shared"] - median_support["rowmatched"] >= 0.15
        and median_support["shared"] - median_support["cloned"] >= 0.15
        and cloned_false_frequency - false_frequency >= 0.20
    )
    catastrophic = forecasts.pivot(index="fold", columns="method", values=["final_iou_d050", "event_time_error"])
    no_catastrophic = bool(
        np.all(
            catastrophic["final_iou_d050"]["reconstructed_shared"]
            >= catastrophic["final_iou_d050"]["fixed_physics_only"] - 0.10
        )
        and np.all(
            catastrophic["event_time_error"]["reconstructed_shared"]
            <= catastrophic["event_time_error"]["fixed_physics_only"] + 3.0
        )
    )
    forecast_gate = bool(
        cutoff_iou >= 0.65
        and float(shared_forecast["final_iou_d050"] - fixed_forecast["final_iou_d050"]) >= 0.08
        and float(shared_forecast["final_iou_d050"] - single_forecast["final_iou_d050"]) >= 0.04
        and float(shared_forecast["final_tip_error"]) <= 0.10
        and float(shared_forecast["final_tip_error"]) <= 0.85 * float(fixed_forecast["final_tip_error"]) + 1e-12
        and float(shared_forecast["final_tip_error"]) <= 0.90 * float(single_forecast["final_tip_error"]) + 1e-12
        and float(shared_forecast["event_time_error"]) <= 2.0
        and no_catastrophic
    )
    tip_gate = float(folds["tip_weight_fraction"].min()) >= 0.10
    development_gate = bool(
        identifiability_gate and support_gate and diversity_gate and forecast_gate and tip_gate
    )

    frozen_hash = hash_frozen_arrays(
        output_dir / "freeze_snapshot.npz",
        {
            "damage": reconstructed["d"].to_numpy(float),
            "known_residual": reconstructed["known_residual"].to_numpy(float),
            "trajectory_id": reconstructed["trajectory_id"].to_numpy(str),
            "cycle": reconstructed["cycle"].to_numpy(int),
            "cell_id": reconstructed["cell_id"].to_numpy(int),
        },
        {
            "cutoff_index": config.cutoff_index,
            "future_damage_access": False,
            "excitation_design": config.excitation_design,
            "adapters": manifests,
        },
    )
    folds.to_csv(output_dir / "fold_metrics.csv", index=False)
    forecasts.to_csv(output_dir / "section_forecast_metrics.csv", index=False)
    forecast_summary.to_csv(output_dir / "forecast_summary.csv", index=False)
    support_table.to_csv(output_dir / "shared_support_summary.csv", index=False)
    (output_dir / "split_manifest.json").write_text(json.dumps(split_manifest, indent=2) + "\n")
    (output_dir / "config.yaml").write_text(json.dumps(asdict(config), indent=2) + "\n")
    result = {
        "claim_class": "tooling-only-development",
        "forcing_max_correlation": forcing_max_correlation,
        "median_support_jaccard": median_support,
        "shared_support_stability": support_stability,
        "shared_true_term_frequency": true_frequency,
        "shared_false_term_max_frequency": false_frequency,
        "cloned_false_term_max_frequency": cloned_false_frequency,
        "median_cutoff_iou_d050": cutoff_iou,
        "median_forecast": {
            method: {
                key: float(value)
                for key, value in row.items()
                if key != "method" and np.isscalar(value)
            }
            for method, row in method_metrics.items()
        },
        "identifiability_gate": identifiability_gate,
        "support_gate": support_gate,
        "diversity_gate": diversity_gate,
        "forecast_gate": forecast_gate,
        "tip_gate": tip_gate,
        "mechanism_development_gate": development_gate,
        "frozen_snapshot_sha256": frozen_hash,
        "confirmation_seeds_used": False,
        "joint_training_baseline_executed": False,
    }
    (output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    (output_dir / "RUN_PROVENANCE.txt").write_text(
        json.dumps(
            {
                "benchmark": "FTS-A4_balanced_multi_environment_synthetic",
                "claim_class": "tooling-only-development",
                "freeze_snapshot_sha256": frozen_hash,
                "observations_sha256": hashlib.sha256(
                    observations.to_csv(index=False).encode("utf-8")
                ).hexdigest(),
                "confirmation_seeds_used": False,
                "joint_training_baseline_executed": False,
            },
            indent=2,
        )
        + "\n"
    )
    (output_dir / "decision.md").write_text(
        "# Stage A4 development decision\n\n"
        f"- Overall gate: **{'PASS' if development_gate else 'FAIL'}**\n"
        f"- Identifiability/support/diversity/forecast/tip: `{identifiability_gate}` / "
        f"`{support_gate}` / `{diversity_gate}` / `{forecast_gate}` / `{tip_gate}`\n"
        f"- Shared/pooled/single support Jaccard: `{median_support['shared']:.3f}` / "
        f"`{median_support['pooled_svws']:.3f}` / `{median_support['single']:.3f}`\n"
        "- Boundary: synthetic tooling only; no producer, PIDL, real-road, or causal claim.\n"
    )
    return result
