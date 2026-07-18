#!/usr/bin/env python3
"""Sealed c87->c89 observation ladder for fracture-state estimation.

This is an *analysis-only* single-trajectory diagnostic.  It makes a sharp
distinction between (a) a c87 observation operator used to construct an
analysis state and (b) the c89 FEM state, which is indexed only after the
forecast artifact and a pre-evaluation lock have been written.

The state is ``[damage, alpha_bar, fatigue_degradation, log10_psi_raw]``.
Only channels supported by each declared observation are updated.  Thus a pass
cannot be read as full material-parameter identification: the unobserved
history/fatigue channels remain a transition-prior conditional estimate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
import sys
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from evaluate_spatial_degradation_reconstruction_gate import FIELD_GATES, gate_pass  # noqa: E402
from run_damage_conditioned_equilibrium_gate import metric_row, rollout  # noqa: E402
from run_fem_mechanism_assimilation_gate import checkpoint_model  # noqa: E402
from train_fem_mechanism_mesh_operator import choose_device  # noqa: E402


OBSERVATION_CYCLE = 87
FORECAST_CYCLE = 89
DAMAGE, HISTORY, FATIGUE, RAW = range(4)
FRACTIONS = (1.0, 0.25, 0.10, 0.05, 0.02, 0.01, 0.005)
NOISE_LEVELS = (0.0, 0.01, 0.03, 0.05, 0.10)


@dataclass(frozen=True)
class Config:
    observation_set: str
    fraction: float
    placement: str
    noise_fraction: float
    method: str
    seed: int = 42

    @property
    def label(self) -> str:
        return (
            f"{self.observation_set}__{self.method}__{self.placement}"
            f"__p{self.fraction:g}__n{self.noise_fraction:g}__s{self.seed}"
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def graph_from_dataset(data: np.lib.npyio.NpzFile, device: torch.device) -> dict[str, torch.Tensor]:
    names = (
        "coordinates", "log_area", "areas", "edge_index", "edge_attr",
        "cluster_index", "coarse_edge_index", "coarse_edge_attr",
    )
    graph = {name: torch.from_numpy(np.asarray(data[name])).to(device) for name in names}
    graph["edge_index"] = graph["edge_index"].long()
    graph["cluster_index"] = graph["cluster_index"].long()
    graph["coarse_edge_index"] = graph["coarse_edge_index"].long()
    return graph


def neighbours(edge_index: np.ndarray, count: int) -> tuple[np.ndarray, np.ndarray]:
    """Undirected edge representation for a transparent graph-Laplacian prior."""
    left, right = np.asarray(edge_index, dtype=np.int64)
    return np.concatenate((left, right)), np.concatenate((right, left))


def select_mask(
    coordinates: np.ndarray,
    prior: np.ndarray,
    edge_index: np.ndarray,
    fraction: float,
    placement: str,
    seed: int,
) -> np.ndarray:
    """Choose locations from c87-or-earlier prior only; never from FEM c89."""
    count = len(coordinates)
    selected = max(1, int(round(count * fraction)))
    if selected >= count:
        return np.ones(count, dtype=bool)
    rng = np.random.default_rng(seed)
    x, y = coordinates[:, 0], coordinates[:, 1]
    if placement == "random":
        indices = rng.choice(count, size=selected, replace=False)
    elif placement == "uniform":
        # A deterministic spatial grid avoids the high-variance clustering of
        # iid probes.  One point per occupied bin, then a reproducible fill.
        aspect = max(float(np.ptp(x)) / max(float(np.ptp(y)), 1.0e-12), 1.0)
        nx = max(1, int(round(np.sqrt(selected * aspect))))
        ny = max(1, int(np.ceil(selected / nx)))
        bx = np.minimum(nx - 1, ((x - x.min()) / max(np.ptp(x), 1e-12) * nx).astype(int))
        by = np.minimum(ny - 1, ((y - y.min()) / max(np.ptp(y), 1e-12) * ny).astype(int))
        bins = bx + nx * by
        indices = []
        for bin_id in np.unique(bins):
            members = np.flatnonzero(bins == bin_id)
            centre = np.array([x[members].mean(), y[members].mean()])
            local = members[np.argmin((x[members] - centre[0]) ** 2 + (y[members] - centre[1]) ** 2)]
            indices.append(int(local))
        if len(indices) < selected:
            available = np.setdiff1d(np.arange(count), np.asarray(indices), assume_unique=False)
            indices.extend(rng.choice(available, size=selected - len(indices), replace=False).tolist())
        indices = np.asarray(indices[:selected], dtype=int)
    else:
        source, target = neighbours(edge_index, count)
        raw = prior[:, RAW]
        sums = np.bincount(target, weights=raw[source], minlength=count)
        degree = np.bincount(target, minlength=count).clip(1)
        local_gradient = np.abs(raw - sums / degree)
        damage_edge = prior[:, DAMAGE] * (1.0 - prior[:, DAMAGE])
        if placement == "process_zone":
            score = 0.7 * damage_edge + 0.3 * local_gradient / max(float(local_gradient.max()), 1e-12)
        elif placement == "adaptive":
            # A prior-only uncertainty proxy: local raw disagreement times the
            # diffuse damage edge.  This is deliberately not an oracle error map.
            score = local_gradient * (0.1 + damage_edge)
        else:
            raise ValueError(f"unknown placement: {placement}")
        indices = np.argpartition(score, -selected)[-selected:]
    mask = np.zeros(count, dtype=bool)
    mask[indices] = True
    return mask


def noisy_log_raw(values: np.ndarray, fraction: float, rng: np.random.Generator) -> np.ndarray:
    """Log-domain multiplicative sensor error; fraction is relative raw scale."""
    if fraction == 0.0:
        return values.copy()
    scale = max(float(np.nanstd(values)), 1.0e-6)
    return values + rng.normal(0.0, fraction * scale, size=len(values))


def laplacian_analysis(
    prior: np.ndarray,
    mask: np.ndarray,
    observed: np.ndarray,
    edge_index: np.ndarray,
    iterations: int = 24,
    smoothness: float = 1.5,
) -> np.ndarray:
    """Fixed-hyperparameter MAP state analysis.

    It minimizes observed raw residual plus a c86->c87 transition-prior term
    and a graph smoothness term.  The fixed 24 iterations are the transparent
    variational baseline; no c89 score is used to tune them.
    """
    result = prior.copy()
    result[mask, RAW] = observed[mask]
    source, target = neighbours(edge_index, len(result))
    free = ~mask
    for _ in range(iterations):
        values = result[:, RAW]
        averaged = np.bincount(target, weights=values[source], minlength=len(values))
        degree = np.bincount(target, minlength=len(values)).clip(1)
        neighbour_mean = averaged / degree
        result[free, RAW] = (prior[free, RAW] + smoothness * neighbour_mean[free]) / (1.0 + smoothness)
        result[mask, RAW] = observed[mask]
    return result


def direct_analysis(prior: np.ndarray, mask: np.ndarray, observed: np.ndarray) -> np.ndarray:
    result = prior.copy()
    result[mask, RAW] = observed[mask]
    return result


def reaction_mask_analysis(prior: np.ndarray, truth_c87: np.ndarray, noise: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic crack image + reaction observation, deliberately no raw field.

    The image is a binary damage mask.  The reaction proxy is the area-free
    mean degradation, a legal c87 global scalar here.  A one-dimensional
    bracket matches that scalar; it cannot reveal the local raw-energy nullspace.
    """
    image = truth_c87[:, DAMAGE] >= 0.5
    if noise:
        flip = rng.random(len(image)) < noise
        image = np.logical_xor(image, flip)
    observed_reaction = float(np.mean((1.0 - truth_c87[:, DAMAGE]) ** 2))
    observed_reaction *= float(1.0 + rng.normal(0.0, noise))
    low, high = 0.0, 1.0
    for _ in range(32):
        beta = 0.5 * (low + high)
        candidate = np.maximum(prior[:, DAMAGE], beta * image.astype(float))
        reaction = float(np.mean((1.0 - candidate) ** 2))
        if reaction > observed_reaction:
            low = beta
        else:
            high = beta
    result = prior.copy()
    result[:, DAMAGE] = np.maximum(prior[:, DAMAGE], high * image.astype(float))
    return result, image


def observation_cost(config: Config, observed_count: int) -> float:
    # Relative units state the practical hierarchy, not a monetary quote.
    base = {
        "raw_full_field": 100.0,
        "process_zone_raw": 20.0,
        "dic_strain_grid": 12.0,
        "sparse_raw_probes": 4.0,
        "reaction_crack_mask": 1.0,
    }[config.observation_set]
    if config.observation_set == "reaction_crack_mask":
        return base
    return base * (0.05 + observed_count / 10000.0)


def configs() -> list[Config]:
    result = [Config("raw_full_field", 1.0, "uniform", 0.0, "direct")]
    result += [Config("process_zone_raw", p, "process_zone", 0.0, "variational") for p in FRACTIONS[1:]]
    result += [Config("dic_strain_grid", p, "uniform", 0.0, "variational") for p in FRACTIONS]
    result += [Config("sparse_raw_probes", p, place, 0.0, "variational")
               for p in (0.25, 0.10, 0.05, 0.02, 0.01, 0.005)
               for place in ("uniform", "random", "process_zone", "adaptive")]
    result.append(Config("reaction_crack_mask", 0.0, "process_zone", 0.0, "direct"))
    # Fixed robustness stress: no hyperparameter or layout retuning at c89.
    result += [Config(obs, frac, placement, noise, "variational")
               for obs, frac, placement in (
                    ("raw_full_field", 1.0, "uniform"),
                    ("process_zone_raw", 0.25, "process_zone"),
                    ("dic_strain_grid", 0.25, "uniform"),
                    ("sparse_raw_probes", 0.10, "adaptive"),
                    ("reaction_crack_mask", 0.0, "process_zone"),
               ) for noise in NOISE_LEVELS[1:]]
    return result


def c87_diagnostics(analysis: np.ndarray, truth: np.ndarray, areas: np.ndarray, observed_mask: np.ndarray, observed: np.ndarray) -> dict[str, float]:
    weights = areas / areas.sum()
    raw_error = analysis[:, RAW] - truth[:, RAW]
    return {
        "c87_raw_log_mae_diagnostic": float(np.sum(weights * np.abs(raw_error))),
        "c87_damage_mae_diagnostic": float(np.sum(weights * np.abs(analysis[:, DAMAGE] - truth[:, DAMAGE]))),
        "c87_history_mae_diagnostic": float(np.sum(weights * np.abs(analysis[:, HISTORY] - truth[:, HISTORY]))),
        "c87_degradation_mae_diagnostic": float(np.sum(weights * np.abs(analysis[:, FATIGUE] - truth[:, FATIGUE]))),
        "observation_log_residual": float(np.mean(np.abs(analysis[observed_mask, RAW] - observed[observed_mask]))) if observed_mask.any() else float("nan"),
    }


def lock_selection(rows: list[dict[str, object]]) -> list[str]:
    """Choose candidates using only observation-side diagnostics and cost.

    All rows are nevertheless evaluated on c89 for a complete negative-result
    record.  This function never reads a c89 metric.
    """
    eligible = []
    for row in rows:
        if row["observation_set"] == "reaction_crack_mask":
            continue
        residual = float(row["observation_log_residual"])
        if np.isfinite(residual) and residual <= 0.05 and float(row["observed_fraction"]) >= 0.01 and float(row["noise_fraction"]) == 0.0:
            eligible.append(row)
    eligible.sort(key=lambda row: (float(row["observation_cost_relative"]), str(row["config"])))
    return [str(row["config"])] if eligible else []


def plot_pareto(rows: list[dict[str, object]], out: Path) -> None:
    fig, axis = plt.subplots(figsize=(8, 5))
    for observation_set, group in _group(rows, "observation_set"):
        x = [float(row["observation_cost_relative"]) for row in group]
        y = [float(row["derived_active_log_mae"]) for row in group]
        axis.scatter(x, y, label=observation_set, alpha=0.75)
    axis.axhline(FIELD_GATES["log_mae_max"], color="black", linestyle="--", linewidth=1, label="log-MAE gate")
    axis.set_xscale("log")
    axis.set_xlabel("relative observation cost")
    axis.set_ylabel("sealed c89 active log-MAE")
    axis.legend(fontsize=7)
    axis.set_title("Observation cost versus held-out mechanism quality")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def _group(rows: Iterable[dict[str, object]], key: str):
    ordered: dict[object, list[dict[str, object]]] = {}
    for row in rows:
        ordered.setdefault(row[key], []).append(row)
    return ordered.items()


def plot_sparse_fields(coordinates: np.ndarray, truth: np.ndarray, analyses: dict[str, np.ndarray], masks: dict[str, np.ndarray], out: Path) -> None:
    candidates = [key for key in analyses if "sparse_raw_probes__variational__adaptive__p0.1__n0__" in key]
    if not candidates:
        candidates = list(analyses)[:1]
    key = candidates[0]
    fig, axes = plt.subplots(1, 4, figsize=(16, 4), constrained_layout=True)
    panels = (
        (truth[:, RAW], "FEM c87 log raw"),
        (analyses[key][:, RAW], "analysis c87 log raw"),
        (truth[:, RAW] - analyses[key][:, RAW], "raw residual"),
        (masks[key].astype(float), "probe mask"),
    )
    for axis, (values, title) in zip(axes, panels):
        scatter = axis.scatter(coordinates[:, 0], coordinates[:, 1], c=values, s=1, cmap="coolwarm")
        axis.set_title(title)
        axis.set_aspect("equal")
        fig.colorbar(scatter, ax=axis, shrink=0.75)
    fig.suptitle(f"Sparse state analysis: {key}", fontsize=9)
    fig.savefig(out, dpi=180)
    plt.close(fig)


def weighted_p99(values: np.ndarray, areas: np.ndarray) -> float:
    order = np.argsort(values)
    cumulative = np.cumsum(areas[order])
    index = int(np.searchsorted(cumulative, 0.99 * cumulative[-1], side="left"))
    return float(values[order[min(index, len(order) - 1)]])


def plot_active_support(coordinates: np.ndarray, truth: np.ndarray, forecast: np.ndarray, areas: np.ndarray, out: Path) -> None:
    """FEM-centred absolute-p99 c89 support figure for the sparse passing tier."""
    truth_active = truth[:, RAW] + 2.0 * np.log10(np.maximum(1.0 - truth[:, DAMAGE], 1.0e-6))
    forecast_active = forecast[:, RAW] + 2.0 * np.log10(np.maximum(1.0 - forecast[:, DAMAGE], 1.0e-6))
    threshold = weighted_p99(truth_active, areas)
    fem_mask = truth_active >= threshold
    forecast_mask = forecast_active >= threshold
    category = np.zeros(len(truth), dtype=int)
    category[fem_mask] = 1
    category[forecast_mask] = 2
    category[fem_mask & forecast_mask] = 3
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
    for axis, values, title in (
        (axes[0], truth_active, "FEM c89 log active"),
        (axes[1], forecast_active, "10% adaptive-probe forecast"),
    ):
        scatter = axis.scatter(coordinates[:, 0], coordinates[:, 1], c=values, s=1, cmap="magma")
        axis.set_title(title)
        axis.set_aspect("equal")
        fig.colorbar(scatter, ax=axis, shrink=0.75)
    colours = np.array([[0.75, 0.75, 0.75], [0.10, 0.35, 0.85], [0.95, 0.40, 0.05], [0.98, 0.82, 0.10]])
    axes[2].scatter(coordinates[:, 0], coordinates[:, 1], c=colours[category], s=1)
    axes[2].set_title("absolute FEM-p99 support\nblue FEM-only, orange estimate-only, yellow overlap")
    axes[2].set_aspect("equal")
    fig.suptitle("Sealed c89 active-support comparison", fontsize=11)
    fig.savefig(out, dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-manifest", type=Path, required=True)
    parser.add_argument("--upstream-predictions", type=Path, required=True)
    parser.add_argument("--operator-dataset", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--upstream-method", default="dic_selected_front_translation")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--allow-single-trajectory-diagnostic", action="store_true")
    return parser.parse_args()


def make_analysis(
    config: Config,
    coordinates: np.ndarray,
    prior: np.ndarray,
    truth_c87: np.ndarray,
    edge_index: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply the declared c87 observation operator and analysis update."""
    rng = np.random.default_rng(config.seed)
    if config.observation_set == "reaction_crack_mask":
        analysis, mask = reaction_mask_analysis(prior, truth_c87, config.noise_fraction, rng)
        return analysis, mask, analysis[:, RAW]
    mask = select_mask(coordinates, prior, edge_index, config.fraction, config.placement, config.seed)
    observed = noisy_log_raw(truth_c87[:, RAW], config.noise_fraction, rng)
    if config.method == "direct":
        return direct_analysis(prior, mask, observed), mask, observed
    if config.method == "variational":
        return laplacian_analysis(prior, mask, observed, edge_index), mask, observed
    raise ValueError(f"unsupported method: {config.method}")


def uncertainty_rows(
    configs_to_stress: list[Config],
    ensemble_size: int,
    coordinates: np.ndarray,
    prior: np.ndarray,
    truth_c87: np.ndarray,
    truth_c89: np.ndarray,
    edge_index: np.ndarray,
    model: torch.nn.Module,
    statistics: object,
    graph: dict[str, torch.Tensor],
    device: torch.device,
    areas: np.ndarray,
) -> list[dict[str, object]]:
    """Noise ensemble for posterior spread and c89 active-field coverage."""
    rows = []
    for base in configs_to_stress:
        members = []
        for offset in range(ensemble_size):
            config = Config(base.observation_set, base.fraction, base.placement, base.noise_fraction, base.method, base.seed + offset)
            analysis, _, _ = make_analysis(config, coordinates, prior, truth_c87, edge_index)
            members.append(rollout(model, statistics, analysis, OBSERVATION_CYCLE, FORECAST_CYCLE, graph, device, torch.float32))
        stack = np.stack(members)
        low, high = np.quantile(stack[:, :, RAW], [0.05, 0.95], axis=0)
        coverage = float(np.mean((truth_c89[:, RAW] >= low) & (truth_c89[:, RAW] <= high)))
        rows.append({
            "observation_set": base.observation_set,
            "fraction": base.fraction,
            "placement": base.placement,
            "noise_fraction": base.noise_fraction,
            "method": base.method,
            "ensemble_size": ensemble_size,
            "c89_raw_90pct_coverage": coverage,
            "c89_raw_90pct_mean_width": float(np.mean(high - low)),
            "c89_raw_ensemble_std_mean": float(np.mean(np.std(stack[:, :, RAW], axis=0))),
            "interpretation": "coverage is synthetic same-trajectory calibration only; it is not external posterior calibration",
        })
    return rows


def main() -> None:
    args = parse_args()
    if not args.allow_single_trajectory_diagnostic:
        raise ValueError("single-trajectory diagnostic requires explicit acknowledgement")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "figures").mkdir(exist_ok=True)
    upstream = json.loads(args.upstream_manifest.read_text(encoding="utf-8"))
    if upstream.get("primary_tag") != args.upstream_method:
        raise ValueError("upstream method does not match locked manifest")
    with np.load(args.upstream_predictions, allow_pickle=False) as source:
        prior = np.asarray(source[f"{args.upstream_method}_c87"], dtype=np.float32)
        upstream_c89 = np.asarray(source[f"{args.upstream_method}_c89"], dtype=np.float32)

    device = choose_device(args.device)
    data = np.load(args.operator_dataset, allow_pickle=False)
    if int(np.asarray(data["trajectory_count"]).item()) != 1:
        raise ValueError("this sealed diagnostic expects exactly one trajectory")
    coordinates = np.asarray(data["coordinates"], dtype=np.float64)
    areas = np.asarray(data["areas"], dtype=np.float64)
    edge_index = np.asarray(data["edge_index"], dtype=np.int64)
    states = np.asarray(data["states"], dtype=np.float32)
    # c87 is a legal observation-time synthetic truth. c89 is intentionally
    # not indexed until the prediction lock below.
    truth_c87 = np.asarray(states[OBSERVATION_CYCLE - 1], dtype=np.float32)
    if prior.shape != truth_c87.shape:
        raise ValueError("upstream c87 state shape mismatch")
    graph = graph_from_dataset(data, device)
    model, statistics, checkpoint = checkpoint_model(args.checkpoint, device)
    if checkpoint.get("args", {}).get("model") != "multiscale":
        raise ValueError("only the locked multiscale c87->c89 operator is accepted")

    rows: list[dict[str, object]] = []
    analyses: dict[str, np.ndarray] = {}
    masks: dict[str, np.ndarray] = {}
    for config in configs():
        analysis, mask, observed = make_analysis(config, coordinates, prior, truth_c87, edge_index)
        # The only transition is a frozen forecast; no c89 value has been read.
        predicted_c89 = rollout(model, statistics, analysis, OBSERVATION_CYCLE, FORECAST_CYCLE, graph, device, torch.float32)
        row = {
            "config": config.label,
            **asdict(config),
            "observed_count": int(mask.sum()),
            "observed_fraction": float(mask.mean()),
            "observation_cost_relative": observation_cost(config, int(mask.sum())),
            "raw_observation_semantics": (
                "direct raw tensile-energy oracle" if config.observation_set in {"raw_full_field", "process_zone_raw", "sparse_raw_probes"}
                else "DIC displacement/strain reconstructed with declared tensile split" if config.observation_set == "dic_strain_grid"
                else "reaction force plus binary crack image; no local raw-energy observation"
            ),
            **c87_diagnostics(analysis, truth_c87, areas, mask, observed),
        }
        analyses[config.label] = analysis
        masks[config.label] = mask
        np.savez_compressed(args.out / f"analysis_{len(rows):03d}.npz", analysis_c87=analysis, observed_mask=mask, predicted_c89=predicted_c89)
        row["forecast_artifact"] = f"analysis_{len(rows):03d}.npz"
        rows.append(row)

    prelock = {
        "observation_cycle": OBSERVATION_CYCLE,
        "forecast_cycle": FORECAST_CYCLE,
        "c89_accessed_before_lock": False,
        "configurations": [asdict(config) for config in configs()],
        "selection_rule": "all locations, fractions, methods, and noise levels are predeclared; each c87 state is selected only by its local observation likelihood plus fixed transition/smoothness prior, never by c89",
        "candidate_configs_c87_only": [],
        "forecast_artifact_sha256": {row["forecast_artifact"]: sha256(args.out / str(row["forecast_artifact"])) for row in rows},
    }
    (args.out / "PRE_EVALUATION_LOCK.json").write_text(json.dumps(prelock, indent=2) + "\n", encoding="utf-8")

    # Held-out target opening occurs strictly after individual forecast files and
    # the selection lock are persisted. It contributes only evaluation metrics.
    truth_c89 = np.asarray(states[FORECAST_CYCLE - 1], dtype=np.float32)
    for row in rows:
        with np.load(args.out / str(row["forecast_artifact"]), allow_pickle=False) as result:
            metrics = metric_row(str(row["config"]), FORECAST_CYCLE, np.asarray(result["predicted_c89"]), truth_c89, areas)
        passed = gate_pass(float(metrics["derived_active_log_mae"]), float(metrics["derived_active_correlation"]), float(metrics["absolute_p99_iou"]), float(metrics["absolute_support_area_ratio"]))
        row["forecast_method"] = metrics.pop("method")
        row.update(metrics)
        row["c89_gate_pass"] = bool(passed)
        row["phase"] = "sealed_held_out_c89_forecast"

    # Add the upstream no-observation control under the same held-out metric.
    control = metric_row("upstream_without_c87_observation", FORECAST_CYCLE, upstream_c89, truth_c89, areas)
    control.update({"config": "upstream_without_c87_observation", "observation_set": "none", "method": "none", "placement": "none", "fraction": 0.0, "noise_fraction": 0.0, "observed_count": 0, "observed_fraction": 0.0, "observation_cost_relative": 0.0, "phase": "sealed_held_out_c89_forecast", "c89_gate_pass": False})
    rows.append(control)
    write_rows(args.out / "observation_ladder_metrics.csv", rows)
    uncertainty = uncertainty_rows(
        [
            Config("raw_full_field", 1.0, "uniform", 0.10, "variational"),
            Config("process_zone_raw", 0.25, "process_zone", 0.05, "variational"),
            Config("dic_strain_grid", 0.25, "uniform", 0.05, "variational"),
            Config("sparse_raw_probes", 0.10, "adaptive", 0.05, "variational"),
            Config("reaction_crack_mask", 0.0, "process_zone", 0.05, "variational"),
        ],
        8, coordinates, prior, truth_c87, truth_c89, edge_index, model, statistics, graph, device, areas,
    )
    write_rows(args.out / "uncertainty_calibration.csv", uncertainty)
    plot_pareto([row for row in rows if row["observation_set"] != "none"], args.out / "figures" / "observation_cost_mechanism_pareto.png")
    plot_sparse_fields(coordinates, truth_c87, analyses, masks, args.out / "figures" / "sparse_observation_fields.png")
    sparse_key = next(key for key in analyses if "sparse_raw_probes__variational__adaptive__p0.1__n0__" in key)
    sparse_row = next(row for row in rows if row.get("config") == sparse_key)
    with np.load(args.out / str(sparse_row["forecast_artifact"]), allow_pickle=False) as sparse_result:
        sparse_forecast = np.asarray(sparse_result["predicted_c89"], dtype=np.float32)
    plot_active_support(coordinates, truth_c89, sparse_forecast, areas, args.out / "figures" / "sparse_active_support_overlap.png")

    selected = prelock["candidate_configs_c87_only"]
    selected_rows = [row for row in rows if row.get("config") in selected]
    manifest = {
        "scope": "single_trajectory_synthetic_observation_ladder_diagnostic",
        "fem_reference": "eta0 SENS FEM",
        "state_definition": ["damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw"],
        "degradation_definition": "g(d)=(1-d)^2 used only as derived active diagnostic; not independently observed",
        "observation_cycle": OBSERVATION_CYCLE,
        "forecast_cycle": FORECAST_CYCLE,
        "c89_assimilated": False,
        "c89_target_opened_after_pre_evaluation_lock": True,
        "selection_is_c87_only": True,
        "c87_only_candidates": selected,
        "candidate_c89_results_are_evaluation_not_selection": [{key: row[key] for key in ("config", "c89_gate_pass", "derived_active_log_mae", "derived_active_correlation", "absolute_p99_iou", "absolute_support_area_ratio", "own_p99_iou")} for row in selected_rows],
        "observation_ladder": ["full-field raw", "process-zone raw", "structured DIC/strain grid", "sparse raw/energy probes", "reaction plus crack mask", "noise stress"],
        "noise_levels": list(NOISE_LEVELS),
        "placements": ["uniform", "random", "process_zone", "adaptive"],
        "methods": {
            "direct": "direct observed-channel replacement",
            "variational": "fixed-prior graph-Laplacian MAP analysis; a one-time latent-state optimisation, not a material inverse",
            "not_run": ["differentiable multitime 4D-Var", "EnKF/ensemble smoother", "learned observation encoder"],
            "not_run_reason": "one c87 inspection and one trajectory cannot identify/tune their additional degrees of freedom without creating an inverse-crime selection path",
        },
        "parameter_inverse": "not attempted and explicitly not identifiable from one fixed-parameter trajectory",
        "input_sha256": {"upstream_manifest": sha256(args.upstream_manifest), "upstream_predictions": sha256(args.upstream_predictions), "operator_dataset": sha256(args.operator_dataset), "checkpoint": sha256(args.checkpoint)},
        "output_sha256": {"pre_evaluation_lock": sha256(args.out / "PRE_EVALUATION_LOCK.json"), "metrics": sha256(args.out / "observation_ladder_metrics.csv"), "uncertainty": sha256(args.out / "uncertainty_calibration.csv")},
        "field_gates": FIELD_GATES,
        "trajectory_generalization": False,
        "quarantine": "synthetic same-trajectory sensor study; full hidden-state and material-parameter identifiability remain unproven",
    }
    (args.out / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(args.out / "RUN_MANIFEST.json"), "c87_only_candidates": selected, "tested_configs": len(rows) - 1}, indent=2))


if __name__ == "__main__":
    main()
