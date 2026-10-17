"""Leakage-safe synthetic road-section dynamics and forecast benchmark helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from dataclasses import replace
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from .library import DYNAMIC_TERM_NAMES, build_candidate_library
from .selectors import fit_stlsq, stability_validated_select, validation_select_support
from .structured_adapter import AdapterConfig, StructuredFieldAdapter, hash_frozen_arrays
from .weak_system import assemble_dynamic_weak_system
from .schema import validate_frozen_snapshots


TRUE_DYNAMIC_BETA = {
    "damage_hplus_log_traffic": 0.0030,
    "damage_hplus_moisture": 0.0400,
    "damage_hplus_low_temp_log_traffic": 0.0030,
}


@dataclass(frozen=True)
class ForecastConfig:
    nx: int = 48
    ny: int = 24
    n_times: int = 41
    n_sections: int = 8
    cutoff_index: int = 24
    dt: float = 0.25
    observation_rate: float = 0.20
    noise_sigma: float = 0.01
    seed: int = 11
    n_trials: int = 64
    n_windows: int = 384
    diffusion: float = 0.018
    base_drive: float = 0.020
    event_area_fraction: float = 0.08
    excitation_design: str = "legacy"


def _laplacian(field: np.ndarray) -> np.ndarray:
    padded = np.pad(field, 1, mode="edge")
    return (
        padded[1:-1, 2:]
        + padded[1:-1, :-2]
        + padded[2:, 1:-1]
        + padded[:-2, 1:-1]
        - 4.0 * field
    )


def _covariates(
    config: ForecastConfig,
    section: int,
    time_index: int,
    x_grid: np.ndarray,
    y_grid: np.ndarray,
) -> dict[str, np.ndarray]:
    progress = time_index / max(config.n_times - 1, 1)
    if config.excitation_design == "balanced_2pow3":
        if section < 0 or section >= 8:
            raise ValueError("balanced_2pow3 requires section ids in [0, 7]")
        traffic_high = bool(section & 1)
        cold_high = bool(section & 2)
        moisture_high = bool(section & 4)
        phase = 2.0 * np.pi * ((3 * section) % 8) / 8.0
        traffic_scale = 1.25 if traffic_high else 0.55
        traffic_rate = traffic_scale * (
            1.0
            + 0.07 * np.sin(2.0 * np.pi * progress + phase)
            + 0.04 * np.sin(3.0 * x_grid + phase)
        )
        traffic_cum = np.full_like(
            x_grid, 15.0 + 42.0 * traffic_scale * time_index
        )
        temperature_center = 4.0 if cold_high else 20.0
        temperature = (
            temperature_center
            + 3.0 * np.sin(2.0 * np.pi * progress + 0.7 * phase)
            + 1.5 * x_grid
        )
        next_progress = min(time_index + 1, config.n_times - 1) / max(
            config.n_times - 1, 1
        )
        next_temperature = (
            temperature_center
            + 3.0 * np.sin(2.0 * np.pi * next_progress + 0.7 * phase)
            + 1.5 * x_grid
        )
        temp_delta = (next_temperature - temperature) / config.dt
        moisture_center = 0.72 if moisture_high else 0.16
        moisture = np.clip(
            moisture_center
            + 0.045 * np.cos(2.0 * np.pi * progress + 1.3 * phase)
            + 0.025 * y_grid,
            0.02,
            0.95,
        )
        rain_pulse = np.maximum(
            0.0, np.sin(4.0 * np.pi * progress + 1.7 * phase)
        )
        rain = np.maximum(0.0, 10.0 * (moisture - 0.22) + 2.5 * rain_pulse)
        freeze = np.maximum(0.0, 6.0 - temperature) * progress
        front = 0.08 + 0.70 * progress
        wheel = np.exp(-np.square(y_grid / 0.22))
        tip = np.exp(-np.square((x_grid - front) / 0.18) - np.square(y_grid / 0.16))
        hplus = 0.08 + 0.38 * wheel + 0.62 * tip + 0.03 * np.cos(4.0 * x_grid + phase)
        return {
            "psi_plus": np.maximum(hplus, 1e-6),
            "traffic_esal_cum": traffic_cum,
            "traffic_esal_rate": traffic_rate,
            "temperature": temperature,
            "temp_delta": temp_delta,
            "temp_gradient": np.full_like(x_grid, 1.5),
            "moisture": moisture,
            "rain_7d": rain,
            "freeze_thaw_count": freeze,
        }
    if config.excitation_design != "legacy":
        raise ValueError(f"unknown excitation design: {config.excitation_design}")
    phase = 0.55 * section
    traffic_scale = 0.75 + 0.11 * section
    traffic_cum = np.full_like(x_grid, 15.0 + 42.0 * traffic_scale * time_index)
    traffic_rate = traffic_scale * (1.0 + 0.12 * np.sin(3.0 * x_grid + phase))
    temperature = 14.0 + 12.0 * np.sin(2.0 * np.pi * progress + phase) + 1.5 * x_grid
    next_progress = min(time_index + 1, config.n_times - 1) / max(config.n_times - 1, 1)
    next_temperature = 14.0 + 12.0 * np.sin(2.0 * np.pi * next_progress + phase) + 1.5 * x_grid
    temp_delta = (next_temperature - temperature) / config.dt
    moisture = np.clip(
        0.18 + 0.075 * section + 0.16 * np.cos(np.pi * progress + phase) + 0.06 * y_grid,
        0.02,
        0.95,
    )
    rain = np.maximum(0.0, 18.0 * (moisture - 0.28))
    freeze = np.maximum(0.0, 6.0 - temperature) * progress
    front = 0.08 + 0.70 * progress
    wheel = np.exp(-np.square(y_grid / 0.22))
    tip = np.exp(-np.square((x_grid - front) / 0.18) - np.square(y_grid / 0.16))
    hplus = 0.08 + 0.38 * wheel + 0.62 * tip + 0.03 * np.cos(4.0 * x_grid + phase)
    return {
        "psi_plus": np.maximum(hplus, 1e-6),
        "traffic_esal_cum": traffic_cum,
        "traffic_esal_rate": traffic_rate,
        "temperature": temperature,
        "temp_delta": temp_delta,
        "temp_gradient": np.full_like(x_grid, 1.5),
        "moisture": moisture,
        "rain_7d": rain,
        "freeze_thaw_count": freeze,
    }


def _candidate_frame(damage: np.ndarray, covariates: dict[str, np.ndarray]) -> pd.DataFrame:
    data = {"d": damage.reshape(-1)}
    data.update({name: values.reshape(-1) for name, values in covariates.items()})
    return pd.DataFrame(data)


def _known_rate(
    damage: np.ndarray,
    hplus: np.ndarray,
    config: ForecastConfig,
) -> np.ndarray:
    return config.diffusion * _laplacian(damage) + config.base_drive * hplus * (1.0 - damage)


def _correction_rate(
    damage: np.ndarray,
    covariates: dict[str, np.ndarray],
    beta: dict[str, float],
) -> np.ndarray:
    library = build_candidate_library(_candidate_frame(damage, covariates), DYNAMIC_TERM_NAMES)
    out = np.zeros(damage.size, dtype=float)
    for name, coefficient in beta.items():
        out += coefficient * library[name].to_numpy(float)
    return out.reshape(damage.shape)


def generate_dynamic_truth(
    config: ForecastConfig,
    *,
    beta: dict[str, float] | None = None,
) -> pd.DataFrame:
    beta = TRUE_DYNAMIC_BETA if beta is None else beta
    x = np.linspace(0.0, 1.0, config.nx)
    y = np.linspace(-0.5, 0.5, config.ny)
    x_grid, y_grid = np.meshgrid(x, y)
    cell_area = (x[1] - x[0]) * (y[1] - y[0])
    rows: list[pd.DataFrame] = []
    for section in range(config.n_sections):
        damage = np.clip(
            0.62 * np.exp(-np.square((x_grid - 0.035) / 0.055) - np.square(y_grid / 0.10)),
            0.0,
            0.92,
        )
        for time_index in range(config.n_times):
            covariates = _covariates(config, section, time_index, x_grid, y_grid)
            known = _known_rate(damage, covariates["psi_plus"], config)
            correction = _correction_rate(damage, covariates, beta)
            if time_index < config.n_times - 1:
                next_damage = np.clip(
                    np.maximum(damage, damage + config.dt * (known + correction)), 0.0, 1.0
                )
                realized_residual = (next_damage - damage) / config.dt - known
            else:
                next_damage = damage
                realized_residual = correction
            flat = pd.DataFrame(
                {
                    "trajectory_id": f"synthetic_section_{section}",
                    "source_kind": "synthetic_dynamic_section",
                    "physics_family": "synthetic_pf_dynamic_v1",
                    "protocol_id": "freeze_select_stage_a2_v1",
                    "snapshot_id": f"t{time_index:03d}",
                    "time": time_index * config.dt,
                    "cycle": time_index,
                    "substep": 0,
                    "cell_id": np.arange(config.nx * config.ny),
                    "x": x_grid.reshape(-1),
                    "y": y_grid.reshape(-1),
                    "cell_area": cell_area,
                    "known_residual": -realized_residual.reshape(-1),
                    "known_rate": known.reshape(-1),
                    "d": damage.reshape(-1),
                    "u": 1e-3 * x_grid.reshape(-1) * (1.0 - damage.reshape(-1)),
                    "v": 1e-3 * y_grid.reshape(-1) * (1.0 - damage.reshape(-1)),
                    "psi_plus": covariates["psi_plus"].reshape(-1),
                    "psi_active": (covariates["psi_plus"] * np.square(1.0 - damage)).reshape(-1),
                    "alpha_bar": (time_index * config.dt * covariates["psi_plus"]).reshape(-1),
                    "f_alpha": (1.0 / (1.0 + time_index * config.dt * covariates["psi_plus"])).reshape(-1),
                    "g_stiffness": (np.square(1.0 - damage) + 1e-6).reshape(-1),
                    "ell": 0.02,
                    "Gc_base": 1.0,
                    "traffic_esal_cum": covariates["traffic_esal_cum"].reshape(-1),
                    "traffic_esal_rate": covariates["traffic_esal_rate"].reshape(-1),
                    "temperature": covariates["temperature"].reshape(-1),
                    "temp_delta": covariates["temp_delta"].reshape(-1),
                    "temp_gradient": covariates["temp_gradient"].reshape(-1),
                    "moisture": covariates["moisture"].reshape(-1),
                    "rain_7d": covariates["rain_7d"].reshape(-1),
                    "freeze_thaw_count": covariates["freeze_thaw_count"].reshape(-1),
                    "field_uncertainty": 0.0,
                    "missingness_flags": "none",
                }
            )
            rows.append(flat)
            damage = next_damage
    frame = pd.concat(rows, ignore_index=True)
    validate_frozen_snapshots(frame, claim_class="tooling-only")
    return frame


def sample_sparse_observations(truth: pd.DataFrame, config: ForecastConfig) -> pd.DataFrame:
    pre = truth[truth["cycle"] <= config.cutoff_index].copy()
    rng = np.random.default_rng(config.seed)
    selected = rng.random(len(pre)) < config.observation_rate
    observations = pre.loc[selected, ["trajectory_id", "cycle", "time", "x", "y", "d"]].copy()
    observations["damage_observed"] = np.clip(
        observations["d"].to_numpy(float)
        + rng.normal(0.0, config.noise_sigma, len(observations)),
        0.0,
        1.0,
    )
    observations = observations.drop(columns="d")
    if observations["trajectory_id"].nunique() != config.n_sections:
        raise ValueError("Sparse sampling removed an entire section")
    if (observations["cycle"] > config.cutoff_index).any():
        raise AssertionError("Future damage leaked into observations")
    return observations.reset_index(drop=True)


def fit_frozen_adapter(
    truth: pd.DataFrame,
    observations: pd.DataFrame,
    config: ForecastConfig,
    adapter_config: AdapterConfig,
) -> tuple[pd.DataFrame, dict[str, object]]:
    pre = truth[truth["cycle"] <= config.cutoff_index].copy().reset_index(drop=True)
    pre["d_true_audit"] = pre["d"]
    manifests: dict[str, object] = {}
    predicted = np.zeros(len(pre), dtype=float)
    derivative = np.zeros(len(pre), dtype=float)
    cutoff_time = config.cutoff_index * config.dt
    for trajectory_id, idx in pre.groupby("trajectory_id", sort=True).groups.items():
        obs = observations[observations["trajectory_id"] == trajectory_id]
        adapter = StructuredFieldAdapter(adapter_config, cutoff_time=cutoff_time)
        adapter.fit(obs)
        query = pre.loc[idx, ["x", "y", "time"]]
        section_prediction = adapter.predict(query).reshape(
            config.cutoff_index + 1, config.ny * config.nx
        )
        section_prediction = np.maximum.accumulate(section_prediction, axis=0)
        section_derivative = np.gradient(
            section_prediction, config.dt, axis=0, edge_order=2
        )
        predicted[np.asarray(idx)] = section_prediction.reshape(-1)
        derivative[np.asarray(idx)] = section_derivative.reshape(-1)
        manifests[str(trajectory_id)] = adapter.manifest()
    pre["d"] = predicted
    pre["g_stiffness"] = np.square(1.0 - predicted) + 1e-6
    pre["psi_active"] = pre["psi_plus"].to_numpy(float) * np.square(1.0 - predicted)
    pre["field_uncertainty"] = config.noise_sigma
    known_rate = np.zeros(len(pre), dtype=float)
    for _, idx in pre.groupby(["trajectory_id", "cycle"], sort=False).groups.items():
        block = pre.loc[idx].sort_values("cell_id")
        damage = block["d"].to_numpy(float).reshape(config.ny, config.nx)
        hplus = block["psi_plus"].to_numpy(float).reshape(config.ny, config.nx)
        values = _known_rate(damage, hplus, config).reshape(-1)
        known_rate[block.index.to_numpy()] = values
    pre["known_residual"] = -(derivative - known_rate)
    pre["known_rate"] = known_rate
    return pre, manifests


def bootstrap_adapter_ensemble(
    truth: pd.DataFrame,
    observations: pd.DataFrame,
    config: ForecastConfig,
    adapter_config: AdapterConfig,
    *,
    n_adapters: int,
) -> tuple[list[pd.DataFrame], list[dict[str, object]], list[str]]:
    """Fit independent pre-cutoff adapters with stratified block bootstraps."""

    members: list[pd.DataFrame] = []
    manifests: list[dict[str, object]] = []
    hashes: list[str] = []
    base = observations.copy()
    base["damage_stratum"] = pd.cut(
        base["damage_observed"],
        bins=[-np.inf, 0.05, 0.25, np.inf],
        labels=["background", "tip_proxy", "crack_body"],
    ).astype(str)
    block_width = max(1, config.cutoff_index // 5)
    base["time_block"] = (base["cycle"] // block_width).astype(int)
    for member in range(n_adapters):
        rng = np.random.default_rng(config.seed + 10000 + member)
        sampled_parts = []
        for _, block in base.groupby(
            ["trajectory_id", "time_block", "damage_stratum"], sort=False
        ):
            sampled_parts.append(
                block.iloc[rng.choice(len(block), size=len(block), replace=True)]
            )
        sampled = pd.concat(sampled_parts, ignore_index=True)
        sampled["damage_observed"] = np.clip(
            sampled["damage_observed"].to_numpy(float)
            + rng.normal(0.0, 0.5 * config.noise_sigma, len(sampled)),
            0.0,
            1.0,
        )
        jittered = replace(
            adapter_config,
            defect_center_x=adapter_config.defect_center_x + rng.uniform(-0.01, 0.01),
            ridge=adapter_config.ridge * 10.0 ** rng.uniform(-0.25, 0.25),
        )
        frozen, manifest = fit_frozen_adapter(
            truth,
            sampled.drop(columns=["damage_stratum", "time_block"]),
            config,
            jittered,
        )
        digest = hashlib.sha256(
            frozen[["d", "known_residual"]].to_numpy(float).tobytes()
        ).hexdigest()
        members.append(frozen)
        manifests.append(manifest)
        hashes.append(digest)
    if len(set(hashes)) != n_adapters:
        raise ValueError("Adapter ensemble did not produce unique frozen hashes")
    return members, manifests, hashes


def _support_metrics(support: set[str]) -> dict[str, float | bool]:
    truth = set(TRUE_DYNAMIC_BETA)
    intersection = support & truth
    union = support | truth
    precision = 1.0 if not support else len(intersection) / len(support)
    recall = len(intersection) / len(truth)
    return {
        "exact_support": support == truth,
        "support_jaccard": len(intersection) / len(union),
        "support_precision": precision,
        "support_recall": recall,
        "support_f1": 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall),
    }


def _beta_dict(term_names: tuple[str, ...], coefficients: np.ndarray) -> dict[str, float]:
    return {name: float(value) for name, value in zip(term_names, coefficients) if abs(value) > 1e-12}


def _rollout_section(
    initial: np.ndarray,
    section: int,
    config: ForecastConfig,
    beta: dict[str, float],
) -> np.ndarray:
    x = np.linspace(0.0, 1.0, config.nx)
    y = np.linspace(-0.5, 0.5, config.ny)
    x_grid, y_grid = np.meshgrid(x, y)
    damage = initial.copy()
    states = [damage.copy()]
    for time_index in range(config.cutoff_index, config.n_times - 1):
        covariates = _covariates(config, section, time_index, x_grid, y_grid)
        rate = _known_rate(damage, covariates["psi_plus"], config)
        rate += _correction_rate(damage, covariates, beta)
        damage = np.clip(np.maximum(damage, damage + config.dt * rate), 0.0, 1.0)
        states.append(damage.copy())
    return np.stack(states)


def _mask_iou(predicted: np.ndarray, truth: np.ndarray, threshold: float) -> float:
    left = predicted >= threshold
    right = truth >= threshold
    union = np.logical_or(left, right).sum()
    return 1.0 if union == 0 else float(np.logical_and(left, right).sum() / union)


def _tip(field: np.ndarray, x_grid: np.ndarray, threshold: float = 0.5) -> float:
    mask = field >= threshold
    return 0.0 if not mask.any() else float(x_grid[mask].max())


def _event_index(states: np.ndarray, area_fraction: float) -> int:
    for index, state in enumerate(states):
        if float(np.mean(state >= 0.5)) >= area_fraction:
            return index
    return len(states)


def run_stage_a2(
    config: ForecastConfig,
    output_dir: Path,
    *,
    adapter_config: AdapterConfig | None = None,
) -> dict[str, object]:
    adapter_config = AdapterConfig() if adapter_config is None else adapter_config
    output_dir.mkdir(parents=True, exist_ok=True)
    truth = generate_dynamic_truth(config)
    observations = sample_sparse_observations(truth, config)
    reconstructed, adapter_manifests = fit_frozen_adapter(
        truth, observations, config, adapter_config
    )
    train_ids = [f"synthetic_section_{index}" for index in range(config.n_sections - 3)]
    validation_id = f"synthetic_section_{config.n_sections - 3}"
    holdout_ids = [
        f"synthetic_section_{config.n_sections - 2}",
        f"synthetic_section_{config.n_sections - 1}",
    ]
    selection_truth = truth[
        truth["trajectory_id"].isin(train_ids) & (truth["cycle"] <= config.cutoff_index)
    ].copy()
    selection_recon = reconstructed[
        reconstructed["trajectory_id"].isin(train_ids)
        & (reconstructed["cycle"] <= config.cutoff_index)
    ].copy()
    validation_truth = truth[
        (truth["trajectory_id"] == validation_id)
        & (truth["cycle"] <= config.cutoff_index)
    ].copy()
    validation_recon = reconstructed[
        (reconstructed["trajectory_id"] == validation_id)
        & (reconstructed["cycle"] <= config.cutoff_index)
    ].copy()
    oracle_system = assemble_dynamic_weak_system(
        selection_truth,
        term_names=DYNAMIC_TERM_NAMES,
        n_windows=config.n_windows,
        seed=config.seed,
    )
    recon_system = assemble_dynamic_weak_system(
        selection_recon,
        term_names=DYNAMIC_TERM_NAMES,
        n_windows=config.n_windows,
        seed=config.seed,
    )
    validation_windows = max(96, config.n_windows // 2)
    oracle_validation_system = assemble_dynamic_weak_system(
        validation_truth,
        term_names=DYNAMIC_TERM_NAMES,
        n_windows=validation_windows,
        seed=config.seed + 1000,
    )
    recon_validation_system = assemble_dynamic_weak_system(
        validation_recon,
        term_names=DYNAMIC_TERM_NAMES,
        n_windows=validation_windows,
        seed=config.seed + 1000,
    )
    oracle = stability_validated_select(
        oracle_system, n_trials=config.n_trials, seed=config.seed
    )
    recon = stability_validated_select(
        recon_system, n_trials=config.n_trials, seed=config.seed
    )
    oracle_validated = validation_select_support(
        oracle, oracle_system, oracle_validation_system
    )
    recon_validated = validation_select_support(
        recon, recon_system, recon_validation_system
    )
    single_beta_array = fit_stlsq(recon_system.A, recon_system.b)
    single_support = {
        name for name, value in zip(recon_system.term_names, single_beta_array) if abs(value) > 1e-12
    }
    beta_by_method = {
        "oracle_svws": _beta_dict(
            oracle_system.term_names, oracle_validated.coefficients.to_numpy(float)
        ),
        "reconstructed_svws": _beta_dict(
            recon_system.term_names, recon_validated.coefficients.to_numpy(float)
        ),
        "reconstructed_single_shot": _beta_dict(
            recon_system.term_names, single_beta_array
        ),
        "fixed_physics_only": {},
    }

    x = np.linspace(0.0, 1.0, config.nx)
    y = np.linspace(-0.5, 0.5, config.ny)
    x_grid, _ = np.meshgrid(x, y)
    metric_rows: list[dict[str, object]] = []
    for trajectory_id in holdout_ids:
        section = int(trajectory_id.rsplit("_", 1)[1])
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
        for method, beta in beta_by_method.items():
            initial = true_cutoff if method == "oracle_svws" else recon_cutoff
            predicted = _rollout_section(initial, section, config, beta)
            metric_rows.append(
                {
                    "trajectory_id": trajectory_id,
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
                    "final_area_error": abs(
                        float(np.mean(predicted[-1] >= 0.5))
                        - float(np.mean(true_states[-1] >= 0.5))
                    ),
                }
            )
    section_metrics = pd.DataFrame(metric_rows)
    forecast_metrics = section_metrics.groupby("method", as_index=False).mean(numeric_only=True)

    validation = reconstructed[reconstructed["trajectory_id"] == validation_id]
    adapter_rmse = float(
        np.sqrt(np.mean(np.square(validation["d"] - validation["d_true_audit"])))
    )
    cutoff_validation = validation[validation["cycle"] == config.cutoff_index]
    adapter_cutoff_iou = _mask_iou(
        cutoff_validation["d"].to_numpy(float),
        cutoff_validation["d_true_audit"].to_numpy(float),
        0.5,
    )
    support_metrics = {
        "oracle_svws": _support_metrics(set(oracle_validated.support)),
        "reconstructed_svws": _support_metrics(set(recon_validated.support)),
        "reconstructed_single_shot": _support_metrics(single_support),
    }

    observations_payload = {
        name: observations[name].to_numpy()
        for name in ["trajectory_id", "cycle", "time", "x", "y", "damage_observed"]
    }
    np.savez_compressed(output_dir / "observations.npz", **observations_payload)
    truth_array = truth.sort_values(["trajectory_id", "cycle", "cell_id"])["d"].to_numpy(float)
    np.savez_compressed(
        output_dir / "synthetic_truth_hidden_until_metrics.npz",
        damage=truth_array,
        true_beta_json=json.dumps(TRUE_DYNAMIC_BETA, sort_keys=True),
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
            "adapters": adapter_manifests,
        },
    )
    (output_dir / "freeze_snapshot_hash.txt").write_text(frozen_hash + "\n")
    np.savez_compressed(
        output_dir / "weak_system_train.npz",
        A=recon_system.A,
        b=recon_system.b,
        term_names=np.asarray(recon_system.term_names),
    )
    recon.trial_coefficients.to_csv(output_dir / "selection_trials.csv", index=False)
    support_summary = recon.support_summary.copy()
    support_summary["validation_selected"] = support_summary["term"].isin(
        recon_validated.support
    )
    support_summary.to_csv(output_dir / "support_summary.csv", index=False)
    recon_validated.trace.to_csv(output_dir / "support_validation_trace.csv", index=False)
    oracle_validated.trace.to_csv(
        output_dir / "oracle_support_validation_trace.csv", index=False
    )
    section_metrics.to_csv(output_dir / "section_metrics.csv", index=False)
    forecast_metrics.to_csv(output_dir / "forecast_metrics.csv", index=False)
    split_manifest = {
        "train_sections": train_ids,
        "validation_section": validation_id,
        "holdout_sections": holdout_ids,
        "forecast_cutoff_index": config.cutoff_index,
        "future_damage_used_by_adapter": False,
        "future_damage_used_by_selector": False,
    }
    (output_dir / "split_manifest.json").write_text(json.dumps(split_manifest, indent=2) + "\n")
    (output_dir / "config.yaml").write_text(json.dumps(asdict(config), indent=2) + "\n")
    (output_dir / "claim_boundary.md").write_text(
        "# Claim Boundary\n\nThis package is synthetic and tooling-only. It does not validate a real road, "
        "a neural PIDL field adapter, causal traffic/environment mechanisms, or the real joint-training baseline.\n"
    )
    provenance = {
        "benchmark": "FTS-A2_sparse_structured_forecast_synthetic",
        "claim_class": "tooling-only",
        "observations_sha256": hashlib.sha256((output_dir / "observations.npz").read_bytes()).hexdigest(),
        "freeze_snapshot_sha256": frozen_hash,
        "joint_training_baseline_executed": False,
    }
    (output_dir / "RUN_PROVENANCE.txt").write_text(json.dumps(provenance, indent=2) + "\n")

    fixed = forecast_metrics[forecast_metrics["method"] == "fixed_physics_only"].iloc[0]
    svws = forecast_metrics[forecast_metrics["method"] == "reconstructed_svws"].iloc[0]
    adapter_gate = adapter_rmse <= max(0.06, 1.5 * config.noise_sigma) and adapter_cutoff_iou >= 0.65
    oracle_gate = float(support_metrics["oracle_svws"]["support_jaccard"]) >= 0.90
    support_gate = float(support_metrics["reconstructed_svws"]["support_jaccard"]) >= 0.75
    forecast_gate = (
        float(svws["final_iou_d050"] - fixed["final_iou_d050"]) >= 0.08
        and float(svws["final_tip_error"]) <= 0.85 * float(fixed["final_tip_error"])
        and float(svws["event_time_error"]) <= 2.0
    )
    limitation = (
        "oracle-limited" if not oracle_gate else
        "adapter-limited" if not adapter_gate else
        "selection-limited" if not support_gate else
        "forecast-limited" if not forecast_gate else
        "stage-a2-pass"
    )
    result = {
        "claim_class": "tooling-only",
        "limitation": limitation,
        "adapter_pre_cutoff_validation_rmse": adapter_rmse,
        "adapter_cutoff_iou_d050": adapter_cutoff_iou,
        "support_metrics": support_metrics,
        "frozen_snapshot_sha256": frozen_hash,
        "oracle_gate": oracle_gate,
        "adapter_gate": adapter_gate,
        "support_gate": support_gate,
        "forecast_gate": forecast_gate,
        "joint_training_baseline_executed": False,
    }
    (output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    (output_dir / "decision.md").write_text(
        "# Stage A2 Decision\n\n"
        f"- Classification: **{limitation}**\n"
        "- Claim class: `tooling-only`\n"
        f"- Oracle support Jaccard: `{support_metrics['oracle_svws']['support_jaccard']:.3f}`\n"
        f"- Reconstructed SVWS support Jaccard: `{support_metrics['reconstructed_svws']['support_jaccard']:.3f}`\n"
        f"- Single-shot support Jaccard: `{support_metrics['reconstructed_single_shot']['support_jaccard']:.3f}`\n"
        f"- Adapter validation RMSE: `{adapter_rmse:.6f}`\n"
        f"- Adapter cutoff IoU d>=0.5: `{adapter_cutoff_iou:.3f}`\n"
        "- Boundary: no real-road, neural PIDL, causal mechanism, or real joint-training claim is allowed.\n"
    )
    return result
