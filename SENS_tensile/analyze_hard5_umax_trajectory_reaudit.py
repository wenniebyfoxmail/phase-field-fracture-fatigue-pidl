#!/usr/bin/env python3
"""FEM-centred audit for the Hard5 eta=0 Umax trajectory package.

This is a post-processing tool. It does not train a model and it does not
modify the source FEM archives. The audit keeps same-cycle and own-event
comparisons separate, and treats the older eight-step Umax=0.12 case as a
protocol comparator rather than interchangeable ground truth.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat


EPS = 1.0e-12


@dataclass(frozen=True)
class Case:
    label: str
    umax: float
    root: Path
    first_hit: int
    confirmed: int
    substeps: int


def read_table(path: Path) -> np.ndarray:
    """Read a whitespace table with one header row."""
    return np.loadtxt(path, skiprows=1)


def read_state(case: Case, cycle: int) -> dict[str, np.ndarray]:
    path = case.root / "psi_fields" / f"cycle_{cycle:04d}.mat"
    data = loadmat(path)
    damage = np.asarray(data["d_elem"], dtype=float).reshape(-1)
    history = np.asarray(data["alpha_bar_elem"], dtype=float).reshape(-1)
    fatigue = np.asarray(data["f_alpha_elem"], dtype=float).reshape(-1)
    raw = np.asarray(data["psi_elem"], dtype=float).reshape(-1)
    degradation = np.square(1.0 - damage)
    active = degradation * raw
    return {
        "damage": damage,
        "history": history,
        "fatigue": fatigue,
        "raw": raw,
        "degradation": degradation,
        "active": active,
    }


def weighted_mean(values: np.ndarray, areas: np.ndarray) -> float:
    return float(np.sum(values * areas) / np.sum(areas))


def weighted_rmse(values: np.ndarray, areas: np.ndarray) -> float:
    return float(np.sqrt(weighted_mean(np.square(values), areas)))


def weighted_corr(a: np.ndarray, b: np.ndarray, areas: np.ndarray) -> float:
    ma = weighted_mean(a, areas)
    mb = weighted_mean(b, areas)
    da = a - ma
    db = b - mb
    denom = np.sqrt(np.sum(areas * da * da) * np.sum(areas * db * db))
    if denom <= 0:
        return float("nan")
    return float(np.sum(areas * da * db) / denom)


def support_metrics(
    reference: np.ndarray,
    candidate: np.ndarray,
    areas: np.ndarray,
    centroids: np.ndarray,
) -> dict[str, float]:
    """Area-weighted FEM-p99 and own-p99 support metrics.

    The p99 threshold itself follows the established cell-quantile convention;
    all set measures are then weighted by physical cell area.
    """
    threshold_ref = float(np.quantile(reference, 0.99))
    threshold_own = float(np.quantile(candidate, 0.99))
    ref_mask = reference >= threshold_ref
    abs_mask = candidate >= threshold_ref
    own_mask = candidate >= threshold_own

    def area(mask: np.ndarray) -> float:
        return float(np.sum(areas[mask]))

    def iou(a: np.ndarray, b: np.ndarray) -> float:
        union = area(a | b)
        return area(a & b) / union if union > 0 else float("nan")

    def centroid(mask: np.ndarray) -> np.ndarray:
        w = areas[mask]
        if not np.any(mask) or np.sum(w) <= 0:
            return np.array([np.nan, np.nan])
        return np.sum(centroids[mask] * w[:, None], axis=0) / np.sum(w)

    ref_area = area(ref_mask)
    abs_area = area(abs_mask)
    own_area = area(own_mask)
    return {
        "reference_p99": threshold_ref,
        "candidate_p99": threshold_own,
        "absolute_iou": iou(ref_mask, abs_mask),
        "own_p99_iou": iou(ref_mask, own_mask),
        "absolute_area_ratio": abs_area / ref_area if ref_area > 0 else float("nan"),
        "own_area_ratio": own_area / ref_area if ref_area > 0 else float("nan"),
        "absolute_centroid_offset": float(np.linalg.norm(centroid(abs_mask) - centroid(ref_mask))),
        "own_centroid_offset": float(np.linalg.norm(centroid(own_mask) - centroid(ref_mask))),
    }


def compare_states(
    reference: dict[str, np.ndarray],
    candidate: dict[str, np.ndarray],
    areas: np.ndarray,
    centroids: np.ndarray,
) -> dict[str, float]:
    out: dict[str, float] = {}
    for name in ("damage", "fatigue", "degradation"):
        residual = candidate[name] - reference[name]
        out[f"{name}_mae"] = weighted_mean(np.abs(residual), areas)
        out[f"{name}_rmse"] = weighted_rmse(residual, areas)
        out[f"{name}_corr"] = weighted_corr(reference[name], candidate[name], areas)
    for name in ("history", "raw", "active"):
        ref_log = np.log10(np.maximum(reference[name], 0.0) + EPS)
        cand_log = np.log10(np.maximum(candidate[name], 0.0) + EPS)
        residual = cand_log - ref_log
        out[f"{name}_log_mae"] = weighted_mean(np.abs(residual), areas)
        out[f"{name}_log_rmse"] = weighted_rmse(residual, areas)
        out[f"{name}_log_corr"] = weighted_corr(ref_log, cand_log, areas)
    out.update(support_metrics(reference["active"], candidate["active"], areas, centroids))
    return out


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def load_geometry(graph_npz: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(graph_npz, allow_pickle=False)
    return np.asarray(data["areas"], dtype=float), np.asarray(data["centroids"], dtype=float)


def plot_life_trajectories(cases: Iterable[Case], output: Path) -> None:
    cases = list(cases)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    colors = {0.11: "#3264a8", 0.12: "#c43c35", 0.13: "#218c74"}
    for case in cases:
        crack = read_table(case.root / "crack_regularized.dat")
        cycle = crack[:, 0]
        a_ell = crack[:, 2]
        style = "--" if case.label.startswith("old") else "-"
        color = "#6c6c6c" if case.label.startswith("old") else colors[case.umax]
        axes[0].plot(cycle, a_ell, style, lw=2.0, color=color, label=case.label)
        axes[1].plot(cycle / case.confirmed, a_ell, style, lw=2.0, color=color, label=case.label)
        axes[0].axvline(case.confirmed, color=color, lw=0.8, alpha=0.3)
    axes[0].set(xlabel="Physical cycle", ylabel=r"Regularized crack length $a_\ell$", title="Absolute-cycle trajectory")
    axes[1].set(xlabel=r"Cycle / own confirmed event", ylabel=r"Regularized crack length $a_\ell$", title="Life-normalized trajectory")
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def scatter_field(ax: plt.Axes, centroids: np.ndarray, values: np.ndarray, **kwargs: object) -> None:
    ax.scatter(centroids[:, 0], centroids[:, 1], c=values, s=0.55, linewidths=0, rasterized=True, **kwargs)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def plot_event_mechanisms(cases: list[Case], centroids: np.ndarray, output: Path) -> None:
    states = [read_state(case, case.first_hit) for case in cases]
    raw_logs = [np.log10(state["raw"] + EPS) for state in states]
    active_logs = [np.log10(state["active"] + EPS) for state in states]
    raw_limits = np.quantile(np.concatenate(raw_logs), [0.02, 0.995])
    active_limits = np.quantile(np.concatenate(active_logs), [0.02, 0.995])
    fig, axes = plt.subplots(len(cases), 4, figsize=(13.5, 3.15 * len(cases)), constrained_layout=True)
    for row, (case, state) in enumerate(zip(cases, states)):
        scatter_field(axes[row, 0], centroids, np.log10(state["raw"] + EPS), cmap="magma", vmin=raw_limits[0], vmax=raw_limits[1])
        scatter_field(axes[row, 1], centroids, state["degradation"], cmap="viridis", vmin=0, vmax=1)
        scatter_field(axes[row, 2], centroids, np.log10(state["active"] + EPS), cmap="magma", vmin=active_limits[0], vmax=active_limits[1])
        threshold = np.quantile(state["active"], 0.99)
        scatter_field(axes[row, 3], centroids, state["active"] >= threshold, cmap="binary", vmin=0, vmax=1)
        axes[row, 0].set_ylabel(f"{case.label}\nfirst hit c{case.first_hit}", fontsize=9)
    titles = [r"$\log_{10}\psi_{raw}$", r"$g(d)=(1-d)^2$", r"$\log_{10}\psi_{active}$", "Own top-1% active support"]
    for ax, title in zip(axes[0], titles):
        ax.set_title(title)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def pidl_state_from_npz(path: Path) -> dict[str, np.ndarray]:
    data = np.load(path, allow_pickle=False)
    raw = np.asarray(data["pidl_raw"], dtype=float)
    active = np.asarray(data["pidl_active"], dtype=float)
    return {
        "damage": np.asarray(data["pidl_damage"], dtype=float),
        "history": np.asarray(data["pidl_history"], dtype=float),
        "fatigue": np.asarray(data["pidl_fatigue"], dtype=float),
        "raw": raw,
        "active": active,
        # Projection and multiplication do not commute. Use the exported
        # projected active/raw ratio rather than recomputing from projected d.
        "degradation": np.clip(active / (raw + EPS), 0.0, 1.0),
    }


def plot_event_phase_realigned_fem_pidl(
    fem: dict[str, np.ndarray],
    pidl: dict[str, np.ndarray],
    centroids: np.ndarray,
    output: Path,
) -> None:
    cmap_overlap = plt.matplotlib.colors.ListedColormap(["#d9d9d9", "#377eb8", "#ff7f00", "#ffd92f"])
    fig, axes = plt.subplots(2, 4, figsize=(13.5, 6.4), constrained_layout=True)
    for row, field in enumerate(("raw", "active")):
        fem_log = np.log10(fem[field] + EPS)
        pidl_log = np.log10(pidl[field] + EPS)
        limits = np.quantile(np.concatenate([fem_log, pidl_log]), [0.02, 0.995])
        scatter_field(axes[row, 0], centroids, fem_log, cmap="magma", vmin=limits[0], vmax=limits[1])
        scatter_field(axes[row, 1], centroids, pidl_log, cmap="magma", vmin=limits[0], vmax=limits[1])
        scatter_field(axes[row, 2], centroids, pidl_log - fem_log, cmap="coolwarm", vmin=-3, vmax=3)
        scatter_field(axes[row, 3], centroids, overlap_codes(fem[field], pidl[field]), cmap=cmap_overlap, vmin=0, vmax=3)
        axes[row, 0].set_ylabel("raw driver" if field == "raw" else "active driver")
    titles = ["FEM first-hit c83", "PIDL first-hit c89", "PIDL - FEM log residual", "FEM-ref p99 overlap"]
    for row in range(2):
        for ax, title in zip(axes[row], titles):
            ax.set_title(title, fontsize=9)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def overlap_codes(reference: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    threshold = np.quantile(reference, 0.99)
    ref_mask = reference >= threshold
    cand_mask = candidate >= threshold
    # 0 neither, 1 reference only, 2 candidate only, 3 overlap.
    return ref_mask.astype(np.int8) + 2 * cand_mask.astype(np.int8)


def plot_old_new_same_cycle(
    old_case: Case,
    new_case: Case,
    cycles: list[int],
    centroids: np.ndarray,
    output: Path,
) -> None:
    pairs = [(read_state(old_case, cycle), read_state(new_case, cycle)) for cycle in cycles]
    all_logs = np.concatenate([np.log10(state["active"] + EPS) for pair in pairs for state in pair])
    limits = np.quantile(all_logs, [0.02, 0.995])
    cmap_overlap = plt.matplotlib.colors.ListedColormap(["#d9d9d9", "#377eb8", "#ff7f00", "#ffd92f"])
    fig, axes = plt.subplots(len(cycles), 4, figsize=(13.5, 2.55 * len(cycles)), constrained_layout=True)
    for row, (cycle, (old, new)) in enumerate(zip(cycles, pairs)):
        old_log = np.log10(old["active"] + EPS)
        new_log = np.log10(new["active"] + EPS)
        scatter_field(axes[row, 0], centroids, old_log, cmap="magma", vmin=limits[0], vmax=limits[1])
        scatter_field(axes[row, 1], centroids, new_log, cmap="magma", vmin=limits[0], vmax=limits[1])
        scatter_field(axes[row, 2], centroids, new_log - old_log, cmap="coolwarm", vmin=-2, vmax=2)
        scatter_field(axes[row, 3], centroids, overlap_codes(old["active"], new["active"]), cmap=cmap_overlap, vmin=0, vmax=3)
        axes[row, 0].set_ylabel(f"same cycle c{cycle}")
    titles = ["Old 8-step active", "New 5-step active", "New - old log residual", "Old-ref p99 overlap"]
    for ax, title in zip(axes[0], titles):
        ax.set_title(title)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def plot_old_new_own_event(
    old_case: Case,
    new_case: Case,
    centroids: np.ndarray,
    output: Path,
) -> None:
    old = read_state(old_case, old_case.confirmed)
    new = read_state(new_case, new_case.confirmed)
    cmap_overlap = plt.matplotlib.colors.ListedColormap(["#d9d9d9", "#377eb8", "#ff7f00", "#ffd92f"])
    fig, axes = plt.subplots(2, 4, figsize=(13.5, 6.3), constrained_layout=True)
    scatter_field(axes[0, 0], centroids, old["damage"], cmap="viridis", vmin=0, vmax=1)
    scatter_field(axes[0, 1], centroids, new["damage"], cmap="viridis", vmin=0, vmax=1)
    scatter_field(axes[0, 2], centroids, new["damage"] - old["damage"], cmap="coolwarm", vmin=-0.5, vmax=0.5)
    scatter_field(axes[0, 3], centroids, np.log10(new["history"] + EPS) - np.log10(old["history"] + EPS), cmap="coolwarm", vmin=-1, vmax=1)
    scatter_field(axes[1, 0], centroids, np.log10(old["active"] + EPS), cmap="magma")
    scatter_field(axes[1, 1], centroids, np.log10(new["active"] + EPS), cmap="magma")
    scatter_field(axes[1, 2], centroids, np.log10(new["active"] + EPS) - np.log10(old["active"] + EPS), cmap="coolwarm", vmin=-2, vmax=2)
    scatter_field(axes[1, 3], centroids, overlap_codes(old["active"], new["active"]), cmap=cmap_overlap, vmin=0, vmax=3)
    titles = [
        f"Old damage c{old_case.confirmed}",
        f"New damage c{new_case.confirmed}",
        "Damage residual",
        "History log residual",
        f"Old active c{old_case.confirmed}",
        f"New active c{new_case.confirmed}",
        "Active log residual",
        "Old-ref p99 overlap",
    ]
    for ax, title in zip(axes.flat, titles):
        ax.set_title(title, fontsize=9)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-root", type=Path, required=True)
    parser.add_argument("--old-u012", type=Path, required=True)
    parser.add_argument("--graph-npz", type=Path, required=True)
    parser.add_argument("--pidl-projected-c89", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    new_cases = [
        Case("new FEM Umax=0.11", 0.11, args.new_root / "u011" / "SENS_hard5_u011_eta0_canonical_v1", 122, 125, 5),
        Case("new FEM Umax=0.12", 0.12, args.new_root / "u012" / "SENS_hard5_u012_eta0_formal_pidl_native_q4_v1", 83, 86, 5),
        Case("new FEM Umax=0.13", 0.13, args.new_root / "u013" / "SENS_hard5_u013_eta0_canonical_v1", 59, 62, 5),
    ]
    old_case = Case("old FEM Umax=0.12 (8-step)", 0.12, args.old_u012, 86, 89, 8)
    new_u012 = new_cases[1]
    areas, centroids = load_geometry(args.graph_npz)

    for case in [*new_cases, old_case]:
        state = read_state(case, min(case.confirmed, 89))
        if any(values.size != areas.size for values in state.values()):
            raise ValueError(f"Mesh cardinality mismatch for {case.label}")

    same_cycle_rows: list[dict[str, object]] = []
    for cycle in (1, 20, 40, 60, 76, 80, 83, 86):
        metrics = compare_states(read_state(old_case, cycle), read_state(new_u012, cycle), areas, centroids)
        same_cycle_rows.append({"comparison": "new5_vs_old8_same_cycle", "reference_cycle": cycle, "candidate_cycle": cycle, **metrics})
    own_event_rows = []
    for event_name, old_cycle, new_cycle in (
        ("first_hit", old_case.first_hit, new_u012.first_hit),
        ("confirmed", old_case.confirmed, new_u012.confirmed),
    ):
        metrics = compare_states(
            read_state(old_case, old_cycle),
            read_state(new_u012, new_cycle),
            areas,
            centroids,
        )
        own_event_rows.append({
            "comparison": f"new5_vs_old8_own_{event_name}",
            "reference_cycle": old_cycle,
            "candidate_cycle": new_cycle,
            **metrics,
        })
    write_rows(args.output / "old_new_u012_same_cycle_metrics.csv", same_cycle_rows)
    write_rows(args.output / "old_new_u012_own_event_metrics.csv", own_event_rows)

    descriptor_rows: list[dict[str, object]] = []
    for case in new_cases:
        for state_label, cycle in (("first_hit", case.first_hit), ("confirmed", case.confirmed)):
            state = read_state(case, cycle)
            support = support_metrics(state["active"], state["active"], areas, centroids)
            descriptor_rows.append({
                "case": case.label,
                "umax": case.umax,
                "state": state_label,
                "cycle": cycle,
                "damage_area_mean": weighted_mean(state["damage"], areas),
                "history_area_mean": weighted_mean(state["history"], areas),
                "fatigue_area_mean": weighted_mean(state["fatigue"], areas),
                "raw_area_mean": weighted_mean(state["raw"], areas),
                "active_area_mean": weighted_mean(state["active"], areas),
                "active_p99": support["reference_p99"],
            })
    write_rows(args.output / "new_umax_event_descriptors.csv", descriptor_rows)

    plot_life_trajectories([*new_cases, old_case], args.output / "figure_1_life_and_trajectory.png")
    plot_event_mechanisms(new_cases, centroids, args.output / "figure_2_umax_first_hit_mechanism.png")
    plot_old_new_same_cycle(old_case, new_u012, [20, 40, 60, 80, 86], centroids, args.output / "figure_3_new_old_u012_same_cycle.png")
    plot_old_new_own_event(old_case, new_u012, centroids, args.output / "figure_4_new_old_u012_own_event.png")

    if args.pidl_projected_c89:
        pidl = pidl_state_from_npz(args.pidl_projected_c89)
        reference_states = [
            ("new5_first_hit_c83", new_u012, new_u012.first_hit),
            ("new5_confirmed_c86", new_u012, new_u012.confirmed),
            ("old8_first_hit_c86", old_case, old_case.first_hit),
            ("old8_confirmed_c89_legacy", old_case, old_case.confirmed),
        ]
        pidl_rows: list[dict[str, object]] = []
        for label, reference_case, cycle in reference_states:
            reference = read_state(reference_case, cycle)
            pidl_rows.append({
                "reference_state": label,
                "reference_cycle": cycle,
                "pidl_state": "formal_pidl_first_hit_c89_step444",
                **compare_states(reference, pidl, areas, centroids),
            })
        write_rows(args.output / "formal_pidl_event_phase_metrics.csv", pidl_rows)

        fem_first = read_state(new_u012, new_u012.first_hit)
        fem_top1 = fem_first["active"] >= np.quantile(fem_first["active"], 0.99)
        diagnostic_rows = []
        for field in ("raw", "degradation", "active"):
            diagnostic_rows.append({
                "field": field,
                "fem_global_p99": float(np.quantile(fem_first[field], 0.99)),
                "pidl_global_p99": float(np.quantile(pidl[field], 0.99)),
                "fem_top1_median_fem": float(np.median(fem_first[field][fem_top1])),
                "fem_top1_median_pidl": float(np.median(pidl[field][fem_top1])),
                "fem_top1_mean_fem": float(np.mean(fem_first[field][fem_top1])),
                "fem_top1_mean_pidl": float(np.mean(pidl[field][fem_top1])),
            })
        write_rows(args.output / "event_phase_support_diagnostics.csv", diagnostic_rows)
        plot_event_phase_realigned_fem_pidl(
            fem_first,
            pidl,
            centroids,
            args.output / "figure_5_event_phase_realigned_fem_pidl.png",
        )

    manifest = {
        "analysis": "Hard5 eta0 Umax FEM trajectory reaudit",
        "new_source": str(args.new_root.resolve()),
        "old_u012_source": str(args.old_u012.resolve()),
        "pidl_projected_c89_source": str(args.pidl_projected_c89.resolve()) if args.pidl_projected_c89 else None,
        "geometry_source": str(args.graph_npz.resolve()),
        "reference_rule": "FEM-centred; old 8-step Umax=0.12 is the reference only for the protocol-drift audit",
        "state_rules": {
            "same_cycle": "old 8-step cN vs new 5-step cN",
            "own_event": "old confirmed c89 vs new confirmed c86",
            "active": "(1-d)^2 * cycle-peak raw psi_elem, eta=0",
        },
        "cases": [case.__dict__ | {"root": str(case.root.resolve())} for case in [*new_cases, old_case]],
    }
    (args.output / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
