from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from freeze_select.library import DEFAULT_TERM_NAMES, DYNAMIC_TERM_NAMES
from freeze_select.multi_environment import active_measure_normalize
from freeze_select.schema import validate_frozen_snapshots
from freeze_select.selectors import stability_validated_select
from freeze_select.structured_adapter import AdapterConfig, StructuredFieldAdapter, hash_frozen_arrays
from freeze_select.weak_system import assemble_weak_system


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_observations(frame: pd.DataFrame, rate: float, seed: int) -> tuple[pd.DataFrame, str]:
    rng = np.random.default_rng(seed)
    selected: list[np.ndarray] = []
    for _, indices in frame.groupby(["trajectory_id", "snapshot_id"], sort=True).groups.items():
        values = np.asarray(indices, dtype=int)
        count = max(32, int(np.ceil(rate * len(values))))
        selected.append(np.sort(rng.choice(values, size=min(count, len(values)), replace=False)))
    rows = frame.loc[np.concatenate(selected)].copy().sort_values(
        ["trajectory_id", "time", "cell_id"]
    )
    identities = "\n".join(
        rows["trajectory_id"].astype(str)
        + "|"
        + rows["snapshot_id"].astype(str)
        + "|"
        + rows["cell_id"].astype(str)
    )
    return rows, hashlib.sha256(identities.encode()).hexdigest()


def fit_field(
    observations: pd.DataFrame,
    query: pd.DataFrame,
    field: str,
    cutoff: float,
    noise_sigma: float,
    seed: int,
) -> tuple[np.ndarray, dict[str, object]]:
    rng = np.random.default_rng(seed)
    observed = observations[["x", "y", "time", field]].copy()
    scale = max(float(np.quantile(np.abs(query[field].to_numpy(float)), 0.95)), 1e-8)
    values = observed[field].to_numpy(float) + rng.normal(0.0, noise_sigma * scale, len(observed))
    if field in {"d", "psi_plus"}:
        values = np.clip(values, 0.0, 1.0 if field == "d" else None)
    target_transform = "identity"
    if field == "psi_plus":
        values = np.sqrt(values)
        target_transform = "sqrt_then_square"
        threshold = float(observations[field].quantile(0.90))
        localized = observations[observations[field] >= threshold]
        x_modes, y_modes = 16, 10
        defect_scales = (0.01, 0.02, 0.04, 0.08, 0.16)
        ridge = 1e-8
    else:
        localized = observations[observations["d"] >= 0.5]
        x_modes, y_modes = 8, 6
        defect_scales = (0.02, 0.05, 0.10, 0.20)
        ridge = 1e-7
    observed["value"] = values
    if localized.empty:
        center_x, center_y = float(observations["x"].mean()), float(observations["y"].mean())
    else:
        center_x, center_y = float(localized["x"].mean()), float(localized["y"].mean())
    temporal_basis = max(4, min(7, int(query["time"].nunique())))
    config = AdapterConfig(
        x_modes=x_modes,
        y_modes=y_modes,
        temporal_basis=temporal_basis,
        spline_degree=min(3, temporal_basis - 1),
        ridge=ridge,
        defect_center_x=center_x,
        defect_center_y=center_y,
        defect_scales=defect_scales,
        wheelpath_scales=(0.08, 0.20),
    )
    adapter = StructuredFieldAdapter(config, cutoff_time=cutoff)
    adapter.fit(observed, value_column="value")
    prediction = adapter.predict(query)
    if target_transform == "sqrt_then_square":
        prediction = np.square(prediction)
    manifest = adapter.manifest()
    manifest.update(
        {
            "field": field,
            "observation_count": len(observed),
            "noise_sigma_relative_to_q95": noise_sigma,
            "noise_scale": scale,
            "target_transform": target_transform,
        }
    )
    return prediction, manifest


def mask_iou(predicted: np.ndarray, truth: np.ndarray, threshold: float) -> float:
    left = predicted >= threshold
    right = truth >= threshold
    union = np.logical_or(left, right).sum()
    return 1.0 if union == 0 else float(np.logical_and(left, right).sum() / union)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sparse structured-field adapter then frozen weak-selection sentinel")
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cutoff-time", type=float, default=15.0)
    parser.add_argument("--observation-rate", type=float, default=0.20)
    parser.add_argument("--noise-sigma", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--n-trials", type=int, default=16)
    parser.add_argument("--n-windows", type=int, default=128)
    parser.add_argument("--state-phase", choices=("all", "peak_only"), default="all")
    parser.add_argument(
        "--field-policy",
        choices=("reconstruct_d_and_psi", "reconstruct_d_fixed_psi"),
        default="reconstruct_d_and_psi",
    )
    parser.add_argument(
        "--candidate-library", choices=("static", "damage_weighted"), default="static"
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(args.input_csv)
    schema = validate_frozen_snapshots(frame, claim_class="tooling-only")
    eligible = frame["time"] <= args.cutoff_time
    if args.state_phase == "peak_only":
        eligible &= frame["substep"].isin([0, 4])
    cutoff = frame[eligible].copy().reset_index(drop=True)
    future_rows = int((frame["time"] > args.cutoff_time).sum())
    state_rows_excluded = int((~eligible & (frame["time"] <= args.cutoff_time)).sum())
    observations, observation_hash = sample_observations(
        cutoff, args.observation_rate, args.seed
    )
    reconstructed_blocks: list[pd.DataFrame] = []
    adapter_manifests: list[dict[str, object]] = []
    reconstruction_rows: list[dict[str, object]] = []
    for trajectory_index, (trajectory_id, block) in enumerate(
        cutoff.groupby("trajectory_id", sort=True)
    ):
        block = block.copy().sort_values(["time", "cell_id"])
        observed = observations[observations["trajectory_id"] == trajectory_id]
        d_prediction, d_manifest = fit_field(
            observed, block, "d", args.cutoff_time, args.noise_sigma, args.seed + 101 * trajectory_index
        )
        if args.field_policy == "reconstruct_d_and_psi":
            psi_prediction, psi_manifest = fit_field(
                observed, block, "psi_plus", args.cutoff_time, args.noise_sigma, args.seed + 101 * trajectory_index + 1
            )
        else:
            psi_prediction = block["psi_plus"].to_numpy(float).copy()
            psi_manifest = {
                "field": "psi_plus",
                "representation": "qualified_ferrite_fixed_physics_feature",
                "future_damage_access": False,
                "source_sha256": sha256(args.input_csv),
            }
        d_truth = block["d"].to_numpy(float)
        psi_truth = block["psi_plus"].to_numpy(float)
        block["d"] = d_prediction
        block["psi_plus"] = psi_prediction
        reconstructed_blocks.append(block)
        adapter_manifests.extend(
            [
                {"trajectory_id": str(trajectory_id), **d_manifest},
                {"trajectory_id": str(trajectory_id), **psi_manifest},
            ]
        )
        for snapshot_id, indices in block.groupby("snapshot_id", sort=True).groups.items():
            local = block.index.get_indexer(indices)
            reconstruction_rows.append(
                {
                    "trajectory_id": str(trajectory_id),
                    "snapshot_id": str(snapshot_id),
                    "d_rmse": float(np.sqrt(np.mean(np.square(d_prediction[local] - d_truth[local])))),
                    "d_iou_d050": mask_iou(d_prediction[local], d_truth[local], 0.5),
                    "psi_relative_rmse": float(
                        np.sqrt(np.mean(np.square(psi_prediction[local] - psi_truth[local])))
                        / max(np.sqrt(np.mean(np.square(psi_truth[local]))), 1e-12)
                    ),
                    "psi_true_rms": float(np.sqrt(np.mean(np.square(psi_truth[local])))),
                }
            )
    reconstructed = pd.concat(reconstructed_blocks, ignore_index=True)
    frozen_path = args.output_dir / "frozen_reconstructed_fields.npz"
    frozen_hash = hash_frozen_arrays(
        frozen_path,
        {
            "d": reconstructed["d"].to_numpy(float),
            "psi_plus": reconstructed["psi_plus"].to_numpy(float),
        },
        {
            "input_sha256": sha256(args.input_csv),
            "observation_ids_sha256": observation_hash,
            "cutoff_time": args.cutoff_time,
            "future_rows_excluded": future_rows,
            "adapter_manifests": adapter_manifests,
        },
    )
    term_names = DEFAULT_TERM_NAMES if args.candidate_library == "static" else DYNAMIC_TERM_NAMES
    system = active_measure_normalize(
        assemble_weak_system(
            reconstructed,
            term_names=term_names,
            n_windows=args.n_windows,
            seed=args.seed,
        )
    )
    selection = stability_validated_select(
        system, n_trials=args.n_trials, seed=args.seed
    )
    reconstruction = pd.DataFrame(reconstruction_rows)
    active_psi = reconstruction[reconstruction["psi_true_rms"] > 1e-10]
    reconstruction.to_csv(args.output_dir / "reconstruction_metrics.csv", index=False)
    selection.support_summary.to_csv(args.output_dir / "support_summary.csv", index=False)
    selection.trial_coefficients.to_csv(args.output_dir / "trial_coefficients.csv", index=False)
    metrics = {
        "claim_class": "tooling-only_sparse_adapter_sentinel",
        "input_sha256": sha256(args.input_csv),
        "observation_ids_sha256": observation_hash,
        "observation_rate": args.observation_rate,
        "noise_sigma": args.noise_sigma,
        "cutoff_time": args.cutoff_time,
        "future_rows_excluded": future_rows,
        "state_rows_excluded": state_rows_excluded,
        "state_phase": args.state_phase,
        "field_policy": args.field_policy,
        "candidate_library": args.candidate_library,
        "future_damage_access": False,
        "field_frozen_before_selection": True,
        "frozen_field_sha256": frozen_hash,
        "trajectory_count": schema.trajectory_count,
        "median_d_rmse": float(reconstruction["d_rmse"].median()),
        "median_d_iou_d050": float(reconstruction["d_iou_d050"].median()),
        "median_psi_relative_rmse": float(reconstruction["psi_relative_rmse"].median()),
        "median_active_psi_relative_rmse": float(active_psi["psi_relative_rmse"].median()),
        "stable_support": list(selection.stable_support),
        **selection.metrics,
        "adapter_manifests": adapter_manifests,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps({key: value for key, value in metrics.items() if key != "adapter_manifests"}, indent=2))


if __name__ == "__main__":
    main()
