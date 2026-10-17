from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

import numpy as np
import pandas as pd

from .multi_environment import (
    active_measure_normalize,
    forcing_correlation,
    shared_support_select,
)
from .structured_adapter import hash_frozen_arrays
from .synthetic_forecast import (
    DYNAMIC_TERM_NAMES,
    TRUE_DYNAMIC_BETA,
    ForecastConfig,
    _support_metrics,
    generate_dynamic_truth,
)
from .synthetic_multi_environment import _systems_by_section, loso_split


def _pairwise_jaccard(supports: list[set[str]]) -> float:
    values: list[float] = []
    for left in range(len(supports)):
        for right in range(left + 1, len(supports)):
            union = supports[left] | supports[right]
            values.append(len(supports[left] & supports[right]) / max(len(union), 1))
    return float(np.median(values)) if values else 1.0


def _term_frequency(supports: list[set[str]], terms: set[str]) -> dict[str, float]:
    return {
        term: sum(term in support for support in supports) / len(supports)
        for term in sorted(terms)
    }


def run_stage_a5_oracle(config: ForecastConfig, output_dir: Path) -> dict[str, object]:
    if config.n_sections != 8 or config.excitation_design != "balanced_2pow3":
        raise ValueError("Stage A5 requires eight balanced_2pow3 environments")
    output_dir.mkdir(parents=True, exist_ok=True)
    truth = generate_dynamic_truth(config)
    raw_systems = _systems_by_section(
        truth, config, n_windows=config.n_windows, seed_offset=0
    )
    normalized_systems = {
        section: active_measure_normalize(system)
        for section, system in raw_systems.items()
    }
    fold_rows: list[dict[str, object]] = []
    raw_supports: list[set[str]] = []
    normalized_supports: list[set[str]] = []
    for holdout in range(config.n_sections):
        train_ids, validation_id, _ = loso_split(holdout, config.n_sections)
        raw = shared_support_select(
            [raw_systems[index] for index in train_ids],
            raw_systems[validation_id],
            n_trials=config.n_trials,
            seed=config.seed + 60000 + holdout,
        )
        normalized = shared_support_select(
            [normalized_systems[index] for index in train_ids],
            normalized_systems[validation_id],
            n_trials=config.n_trials,
            seed=config.seed + 60000 + holdout,
        )
        raw_support = set(raw.support)
        normalized_support = set(normalized.support)
        raw_supports.append(raw_support)
        normalized_supports.append(normalized_support)
        raw_rows = sum(raw_systems[index].A.shape[0] for index in train_ids)
        normalized_rows = sum(normalized_systems[index].A.shape[0] for index in train_ids)
        fold_rows.append(
            {
                "fold": holdout,
                "selection_sections": ",".join(map(str, train_ids)),
                "validation_section": validation_id,
                "raw_row_count": raw_rows,
                "normalized_row_count": normalized_rows,
                "row_count_preserved": raw_rows == normalized_rows,
                "raw_support": ",".join(raw.support),
                "normalized_support": ",".join(normalized.support),
                "raw_support_jaccard": _support_metrics(raw_support)["support_jaccard"],
                "normalized_support_jaccard": _support_metrics(normalized_support)["support_jaccard"],
                "raw_max_correlation": raw.diagnostics.max_abs_correlation,
                "normalized_max_correlation": normalized.diagnostics.max_abs_correlation,
                "raw_condition_number": raw.diagnostics.condition_number,
                "normalized_condition_number": normalized.diagnostics.condition_number,
                "normalized_effective_rank": normalized.diagnostics.effective_rank,
                "normalized_max_environment_leverage": normalized.diagnostics.max_environment_leverage,
                "active_measure_floor": float(
                    normalized_systems[train_ids[0]].metadata["active_measure_floor"].iloc[0]
                ),
            }
        )
    folds = pd.DataFrame(fold_rows)
    true_terms = set(TRUE_DYNAMIC_BETA)
    false_terms = set(DYNAMIC_TERM_NAMES) - true_terms
    normalized_true_frequency = _term_frequency(normalized_supports, true_terms)
    normalized_false_frequency = _term_frequency(normalized_supports, false_terms)
    raw_median = float(folds["raw_support_jaccard"].median())
    normalized_median = float(folds["normalized_support_jaccard"].median())
    normalized_stability = _pairwise_jaccard(normalized_supports)
    exact_fraction = float(
        np.mean([support == true_terms for support in normalized_supports])
    )
    gate = bool(
        bool(folds["row_count_preserved"].all())
        and float(folds["normalized_max_correlation"].max()) <= 0.90
        and int(folds["normalized_effective_rank"].min()) >= 6
        and float(folds["normalized_condition_number"].max()) <= 1e6
        and float(folds["normalized_max_environment_leverage"].max()) <= 0.40
        and normalized_median >= 0.90
        and exact_fraction >= 0.75
        and normalized_stability >= 0.70
        and min(normalized_true_frequency.values()) >= 0.75
        and max(normalized_false_frequency.values()) <= 0.45
        and normalized_median - raw_median >= 0.15
    )
    frozen_hash = hash_frozen_arrays(
        output_dir / "oracle_weak_systems.npz",
        {
            "raw_A": np.vstack([raw_systems[index].A for index in range(8)]),
            "raw_b": np.concatenate([raw_systems[index].b for index in range(8)]),
            "normalized_A": np.vstack([normalized_systems[index].A for index in range(8)]),
            "normalized_b": np.concatenate([normalized_systems[index].b for index in range(8)]),
        },
        {
            "oracle_truth": True,
            "same_rows_before_after": True,
            "normalization": "divide A and b by max(active_measure, 0.1*median_positive)",
            "future_damage_used_for_selection": False,
        },
    )
    folds.to_csv(output_dir / "fold_metrics.csv", index=False)
    (output_dir / "config.yaml").write_text(json.dumps(asdict(config), indent=2) + "\n")
    result = {
        "claim_class": "oracle-tooling-only-development",
        "forcing_max_correlation": forcing_correlation(truth),
        "raw_median_support_jaccard": raw_median,
        "normalized_median_support_jaccard": normalized_median,
        "normalized_exact_support_fraction": exact_fraction,
        "normalized_support_stability": normalized_stability,
        "normalized_true_term_frequency": normalized_true_frequency,
        "normalized_false_term_frequency": normalized_false_frequency,
        "normalized_max_candidate_correlation": float(folds["normalized_max_correlation"].max()),
        "normalization_support_preserving_rows": bool(folds["row_count_preserved"].all()),
        "oracle_development_gate": gate,
        "oracle_weak_system_sha256": frozen_hash,
        "independent_methods_review_completed": False,
        "reconstructed_field_executed": False,
        "confirmation_seeds_used": False,
        "joint_training_baseline_executed": False,
    }
    (output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    (output_dir / "decision.md").write_text(
        "# Stage A5 oracle active-measure decision\n\n"
        f"- Oracle gate: **{'PASS' if gate else 'FAIL'}**\n"
        f"- Raw/normalized median support Jaccard: `{raw_median:.3f}` / `{normalized_median:.3f}`\n"
        f"- Normalized exact-support folds: `{exact_fraction:.3f}`\n"
        f"- Normalized support stability: `{normalized_stability:.3f}`\n"
        "- Boundary: no reconstructed-field, forecast, PIDL, road, or causal claim.\n"
        "- Review status: independent methods review still required before any next stage.\n"
    )
    return result
