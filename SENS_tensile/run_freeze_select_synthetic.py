#!/usr/bin/env python3
"""Mac-safe manufactured gate for Freeze-Then-Select; no PIDL training."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from freeze_select import (
    DEFAULT_TERM_NAMES,
    assemble_weak_system,
    build_candidate_library,
    stability_validated_select,
    validate_frozen_snapshots,
)


TRUE_BETA = {
    "hplus_log_traffic": 0.75,
    "hplus_moisture": -4.00,
    "hplus_low_temp_log_traffic": 0.22,
}


def manufactured_snapshots(seed: int = 7, noise_fraction: float = 0.025) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    x_values = np.linspace(0.0, 1.0, 14)
    y_values = np.linspace(-0.12, 0.12, 7)
    times = np.linspace(0.0, 1.0, 14)
    for trajectory_index in range(5):
        phase = 0.7 * trajectory_index
        for time_index, time in enumerate(times):
            temperature_base = 16.0 + 10.0 * np.sin(2.0 * np.pi * time + phase)
            moisture_base = np.clip(0.15 + 0.13 * trajectory_index + 0.18 * np.cos(np.pi * time + phase), 0.02, 0.95)
            traffic_scale = 0.65 + 0.22 * trajectory_index
            for iy, y in enumerate(y_values):
                for ix, x in enumerate(x_values):
                    cell_id = f"c{iy:02d}_{ix:02d}"
                    spatial = np.exp(-((x - 0.18 - 0.42 * time) ** 2) / 0.045 - (y**2) / 0.006)
                    psi_plus = 0.12 + 0.95 * spatial + 0.09 * np.cos(3.0 * x + phase)
                    temperature = temperature_base + 2.5 * x - 1.5 * y
                    moisture = np.clip(moisture_base + 0.10 * y / 0.12 + 0.04 * np.sin(5.0 * x), 0.01, 0.99)
                    traffic_cum = 20.0 + 1500.0 * traffic_scale * time + 10.0 * x
                    traffic_rate = traffic_scale * (1.0 + 0.12 * np.sin(4.0 * x + phase))
                    d = np.clip(spatial * (0.12 + 0.82 * time), 0.0, 1.0)
                    rows.append(
                        {
                            "trajectory_id": f"manufactured_{trajectory_index}",
                            "source_kind": "manufactured_frozen_snapshot",
                            "physics_family": "manufactured_pf_residual_v1",
                            "protocol_id": "freeze_select_stage_a_v1",
                            "snapshot_id": f"t{time_index:03d}",
                            "time": time,
                            "cycle": time_index,
                            "substep": 0,
                            "cell_id": cell_id,
                            "x": x,
                            "y": y,
                            "cell_area": (x_values[1] - x_values[0]) * (y_values[1] - y_values[0]),
                            "known_residual": 0.0,
                            "d": d,
                            "u": 1e-3 * x * (1.0 - d),
                            "v": 1e-3 * y * (1.0 - d),
                            "psi_plus": max(psi_plus, 1e-6),
                            "psi_active": max(psi_plus, 1e-6) * (1.0 - d) ** 2,
                            "alpha_bar": time * max(psi_plus, 0.0),
                            "f_alpha": 1.0 / (1.0 + time * max(psi_plus, 0.0)),
                            "g_stiffness": (1.0 - d) ** 2 + 1e-6,
                            "ell": 0.01,
                            "Gc_base": 1.0,
                            "traffic_esal_cum": traffic_cum,
                            "traffic_esal_rate": traffic_rate,
                            "temperature": temperature,
                            "temp_delta": 10.0 * 2.0 * np.pi * np.cos(2.0 * np.pi * time + phase),
                            "temp_gradient": 2.5,
                            "moisture": moisture,
                            "rain_7d": max(0.0, 30.0 * (moisture - 0.25)),
                            "freeze_thaw_count": max(0.0, 8.0 - temperature) * time,
                            "field_uncertainty": noise_fraction,
                            "missingness_flags": "none",
                            "true_support_json": json.dumps(sorted(TRUE_BETA)),
                            "true_beta_json": json.dumps(TRUE_BETA, sort_keys=True),
                            "manufactured_residual_id": "declared_three_term_v1",
                        }
                    )
    frame = pd.DataFrame(rows)
    library = build_candidate_library(frame)
    signal = sum(TRUE_BETA[name] * library[name].to_numpy(float) for name in TRUE_BETA)
    noise = rng.normal(0.0, noise_fraction * np.std(signal), size=len(frame))
    frame["known_residual"] = -(signal + noise)
    return frame


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return 1.0 if not union else len(left & right) / len(union)


def run(output_dir: Path, *, seed: int, n_trials: int, n_windows: int) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshots = manufactured_snapshots(seed=seed)
    report = validate_frozen_snapshots(snapshots, claim_class="tooling-only")
    system = assemble_weak_system(snapshots, n_windows=n_windows, seed=seed)
    result = stability_validated_select(system, n_trials=n_trials, seed=seed)
    truth = set(TRUE_BETA)
    stable = set(result.stable_support)
    single = set(result.metrics["single_shot_support"])
    metrics = dict(result.metrics)
    sensitivity = {}
    for frequency_threshold in (0.60, 0.70, 0.80, 0.90):
        selected = result.support_summary[
            (result.support_summary["selection_frequency"] >= frequency_threshold)
            & (result.support_summary["sign_consistency"] >= 0.85)
        ]["term"]
        sensitivity[f"{frequency_threshold:.2f}"] = sorted(selected.astype(str).tolist())
    metrics.update(
        {
            "claim_class": "tooling-only",
            "truth_support": sorted(truth),
            "stable_support_jaccard": _jaccard(stable, truth),
            "single_shot_support_jaccard": _jaccard(single, truth),
            "schema_report": report.__dict__,
            "stable_support_by_frequency_threshold": sensitivity,
            "road_mechanism_claim_allowed": False,
        }
    )
    snapshots.to_csv(output_dir / "frozen_snapshots.csv", index=False)
    system.as_frame().to_csv(output_dir / "weak_system.csv", index=False)
    result.trial_coefficients.to_csv(output_dir / "trial_coefficients.csv", index=False)
    result.support_summary.to_csv(output_dir / "support_summary.csv", index=False)
    result.final_coefficients.rename_axis("term").reset_index().to_csv(
        output_dir / "final_coefficients.csv", index=False
    )
    snapshot_hash = hashlib.sha256((output_dir / "frozen_snapshots.csv").read_bytes()).hexdigest()
    manifest = {
        "protocol_id": "freeze_select_stage_a_v1",
        "claim_class": "tooling-only",
        "source_kind": "manufactured_frozen_snapshot",
        "physics_family": "manufactured_pf_residual_v1",
        "known_phase_field_terms_selectable": False,
        "joint_training_baseline_executed": False,
        "frozen_snapshot_sha256": snapshot_hash,
        "seed": seed,
        "n_trials": n_trials,
        "n_windows": n_windows,
        "candidate_terms": list(DEFAULT_TERM_NAMES),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    exact = stable == truth
    improved = float(metrics["mean_holdout_improvement_vs_null"]) >= 0.05
    verdict = "PASS tooling gate" if exact and improved else "FAIL tooling gate"
    (output_dir / "decision.md").write_text(
        "# Freeze-Then-Select Stage A Decision\n\n"
        f"- Verdict: **{verdict}**\n"
        "- Claim class: `tooling-only`\n"
        f"- Declared true support: `{sorted(truth)}`\n"
        f"- Stability-selected support: `{sorted(stable)}`\n"
        f"- Single-shot support: `{sorted(single)}`\n"
        f"- Mean grouped holdout improvement over PF-only residual: "
        f"`{float(metrics['mean_holdout_improvement_vs_null']):.3f}`\n"
        "- Boundary: this manufactured result does not validate a road mechanism, "
        "joint PIDL training, or real-observation performance.\n"
    )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--n-trials", type=int, default=64)
    parser.add_argument("--n-windows", type=int, default=256)
    args = parser.parse_args()
    metrics = run(args.output_dir, seed=args.seed, n_trials=args.n_trials, n_windows=args.n_windows)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
