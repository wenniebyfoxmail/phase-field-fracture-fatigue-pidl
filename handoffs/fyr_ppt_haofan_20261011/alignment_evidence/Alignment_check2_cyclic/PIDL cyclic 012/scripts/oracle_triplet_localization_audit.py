from __future__ import annotations

import csv
import json
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree


ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl")
FEM_DIR = ROOT / (
    "Alignment check 2/FEM cyclic 012/cases/standard/raw_data/"
    "state_field_exports/latest_align_soft_hist0_state_field_export_20260608"
)
FEM_MAT = FEM_DIR / "latest_align_soft_hist0_state_fields.mat"
FEM_INDEX = FEM_DIR / "latest_align_soft_hist0_state_index.csv"
PIDL_CASE_ROOT = ROOT / "Alignment check 2/PIDL cyclic 012/cases"
OUT = ROOT / "Alignment check 2/PIDL cyclic 012/analysis/oracle_triplet_localization_audit_20260610"
FIGURES = OUT / "figures"
TABLES = OUT / "tables"

CASES = {
    "raw_pidl_g": PIDL_CASE_ROOT / "oracle_raw_pidl_g_20260609",
    "active_fem": PIDL_CASE_ROOT / "oracle_active_fem_20260609",
    "delta_alpha_bar": PIDL_CASE_ROOT / "oracle_delta_alpha_bar_20260609",
}

STATES = ["c1_peak", "c20_peak", "c40_peak", "c60_peak", "c69_peak"]
FIELDS = {
    "alpha": {"direction": "high", "fem": "d_elem", "pidl": "alpha_elem"},
    "history": {"direction": "high", "fem": "alpha_bar_elem", "pidl": "hist_fat_elem"},
    "fatigue_depletion": {"direction": "low", "fem": "f_fatigue_elem", "pidl": "f_fatigue_elem"},
    "stiffness_degradation": {"direction": "low", "fem": "g_stiffness_elem", "pidl": "g_alpha_elem"},
    "psi_active": {"direction": "high", "fem": "f_g_psi_plus_elem", "pidl": "psi_active_elem"},
    "eps_yy": {"direction": "high", "fem": "epsilon_elem_yy", "pidl": "eps_yy_elem"},
    "sigma_effective_1": {
        "direction": "high",
        "fem": "principal_stress_degraded_effective_elem_1",
        "pidl": "sigma_effective_principal_1_elem",
    },
}

BANDS = {
    "whole_domain": lambda x, y: np.ones_like(x, dtype=bool),
    "crack_path_band": lambda x, y: (x >= 0.5) & (np.abs(y - 0.5) <= 0.06),
    "initial_tip_band": lambda x, y: (np.abs(x - 0.5) <= 0.04) & (np.abs(y - 0.5) <= 0.06),
    "right_half_path_band": lambda x, y: (x >= 0.75) & (np.abs(y - 0.5) <= 0.08),
    "right_boundary_band": lambda x, y: (x >= 0.98) & (np.abs(y - 0.5) <= 0.08),
}


def ensure_dirs() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)


def flat(arr: np.ndarray) -> np.ndarray:
    return np.asarray(arr).squeeze().reshape(-1).astype(float)


def load_fem_index() -> list[dict[str, str]]:
    with FEM_INDEX.open() as f:
        return list(csv.DictReader(f))


def state_to_step(label: str) -> int:
    cycle = int(label[1:].split("_", 1)[0])
    return 5 * (cycle - 1) + 3


def run_dir(case: Path) -> Path:
    matches = [p for p in (case / "raw_archive").iterdir() if p.is_dir() and (p / "best_models").exists()]
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one raw run directory under {case / 'raw_archive'}, found {len(matches)}")
    return matches[0]


def diagnostics_dir(case: Path) -> Path:
    matches = list(run_dir(case).glob("element_diagnostics*"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one element diagnostics directory for {case.name}, found {len(matches)}")
    return matches[0]


def pidl_npz(case: Path, step: int) -> Path:
    path = diagnostics_dir(case) / f"element_fields_cycle_{step:04d}.npz"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def fem_field(fields: h5py.Group, state_i: int, field: str) -> np.ndarray:
    key = FIELDS[field]["fem"]
    if key == "epsilon_elem_yy":
        return flat(fields["epsilon_elem"][state_i, 1, :])
    if key == "principal_stress_degraded_effective_elem_1":
        return flat(fields["principal_stress_degraded_effective_elem"][state_i, 0, :])
    return flat(fields[key][state_i])


def pidl_field(npz: np.lib.npyio.NpzFile, field: str) -> np.ndarray:
    return flat(npz[FIELDS[field]["pidl"]])


def localization_score(values: np.ndarray, field: str) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if FIELDS[field]["direction"] == "low":
        return np.nanmax(values) - values
    return values


def weighted_top_mask(score: np.ndarray, weights: np.ndarray, frac: float) -> np.ndarray:
    score = np.asarray(score, dtype=float)
    weights = np.asarray(weights, dtype=float)
    valid = np.isfinite(score) & np.isfinite(weights) & (weights > 0)
    if not np.any(valid):
        return np.zeros_like(score, dtype=bool)
    order = np.argsort(score[valid])[::-1]
    valid_idx = np.flatnonzero(valid)
    sorted_idx = valid_idx[order]
    target = frac * float(np.sum(weights[valid]))
    cumsum = np.cumsum(weights[sorted_idx])
    keep_n = int(np.searchsorted(cumsum, target, side="left") + 1)
    mask = np.zeros_like(score, dtype=bool)
    mask[sorted_idx[: max(1, keep_n)]] = True
    return mask


def weighted_sum(values: np.ndarray, weights: np.ndarray, mask: np.ndarray) -> float:
    if not np.any(mask):
        return float("nan")
    return float(np.nansum(values[mask] * weights[mask]))


def weighted_mean(values: np.ndarray, weights: np.ndarray, mask: np.ndarray) -> float:
    if not np.any(mask):
        return float("nan")
    den = float(np.nansum(weights[mask]))
    if den <= 0:
        return float("nan")
    return float(np.nansum(values[mask] * weights[mask]) / den)


def centroid_of_score(x: np.ndarray, y: np.ndarray, score: np.ndarray, weights: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    if not np.any(mask):
        return float("nan"), float("nan")
    local_score = np.maximum(score[mask], 0)
    w = local_score * weights[mask]
    if float(np.nansum(w)) <= 0:
        w = weights[mask]
    den = float(np.nansum(w))
    return float(np.nansum(x[mask] * w) / den), float(np.nansum(y[mask] * w) / den)


def aggregate_to_fem(values: np.ndarray, nearest: np.ndarray, weights: np.ndarray, n_fem: int) -> np.ndarray:
    num = np.bincount(nearest, weights=values * weights, minlength=n_fem)
    den = np.bincount(nearest, weights=weights, minlength=n_fem)
    out = np.full(n_fem, np.nan)
    np.divide(num, den, out=out, where=den > 0)
    return out


def build_projection(case: Path, fem_x: np.ndarray, fem_y: np.ndarray) -> dict[str, np.ndarray]:
    with np.load(pidl_npz(case, 3)) as npz:
        pidl_x = flat(npz["elem_x"]) + 0.5
        pidl_y = flat(npz["elem_y"]) + 0.5
        pidl_area = flat(npz["area_elem"])
    tree = cKDTree(np.column_stack([fem_x, fem_y]))
    _dist, nearest = tree.query(np.column_stack([pidl_x, pidl_y]), k=1)
    return {"nearest": nearest, "weights": pidl_area, "pidl_x": pidl_x, "pidl_y": pidl_y}


def grid_image(values: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    ux = np.unique(np.round(x, 10))
    uy = np.unique(np.round(y, 10))
    xi = {v: i for i, v in enumerate(ux)}
    yi = {v: i for i, v in enumerate(uy)}
    grid = np.full((len(uy), len(ux)), np.nan)
    for value, xv, yv in zip(values, np.round(x, 10), np.round(y, 10)):
        grid[yi[yv], xi[xv]] = value
    return grid


def collect_data() -> tuple[list[dict[str, object]], list[dict[str, object]], dict[tuple[str, str, str], np.ndarray], np.ndarray, np.ndarray]:
    state_rows = load_fem_index()
    state_to_i = {row["state_label"]: i for i, row in enumerate(state_rows)}
    peak_rows: list[dict[str, object]] = []
    overlap_rows: list[dict[str, object]] = []
    fields_on_fem: dict[tuple[str, str, str], np.ndarray] = {}

    with h5py.File(FEM_MAT, "r") as h5:
        fem_x = flat(h5["element_centroids"][0])
        fem_y = flat(h5["element_centroids"][1])
        fem_area = flat(h5["element_area"])
        fields = h5["fields"]

        projections = {name: build_projection(case, fem_x, fem_y) for name, case in CASES.items()}

        for state in STATES:
            state_i = state_to_i[state]
            pidl_step = state_to_step(state)
            for field in FIELDS:
                fem_vals = fem_field(fields, state_i, field)
                fields_on_fem[("FEM", state, field)] = fem_vals
                add_peak_rows(peak_rows, "FEM", state, pidl_step, field, fem_vals, fem_x, fem_y, fem_area)

                fem_score = localization_score(fem_vals, field)
                fem_top1 = weighted_top_mask(fem_score, fem_area, 0.01)
                fem_top5 = weighted_top_mask(fem_score, fem_area, 0.05)

                for run_name, case in CASES.items():
                    projection = projections[run_name]
                    with np.load(pidl_npz(case, pidl_step)) as npz:
                        pidl_vals = pidl_field(npz, field)
                    projected = aggregate_to_fem(
                        pidl_vals,
                        projection["nearest"],
                        projection["weights"],
                        len(fem_x),
                    )
                    fields_on_fem[(run_name, state, field)] = projected
                    add_peak_rows(peak_rows, run_name, state, pidl_step, field, projected, fem_x, fem_y, fem_area)

                    pidl_score = localization_score(projected, field)
                    pidl_top1 = weighted_top_mask(pidl_score, fem_area, 0.01)
                    pidl_top5 = weighted_top_mask(pidl_score, fem_area, 0.05)
                    add_overlap_rows(
                        overlap_rows,
                        run_name,
                        state,
                        pidl_step,
                        field,
                        fem_top1,
                        pidl_top1,
                        fem_top5,
                        pidl_top5,
                        fem_area,
                    )

    return peak_rows, overlap_rows, fields_on_fem, fem_x, fem_y


def add_peak_rows(
    rows: list[dict[str, object]],
    source: str,
    state: str,
    pidl_step: int,
    field: str,
    values: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    area: np.ndarray,
) -> None:
    score = localization_score(values, field)
    valid = np.isfinite(score)
    if not np.any(valid):
        return
    idx = np.flatnonzero(valid)[int(np.nanargmax(score[valid]))]
    top1 = weighted_top_mask(score, area, 0.01)
    cx, cy = centroid_of_score(x, y, score, area, top1)
    base = {
        "source": source,
        "state_label": state,
        "mapped_pidl_step": pidl_step,
        "field": field,
        "direction": FIELDS[field]["direction"],
        "score_max": float(score[idx]),
        "field_value_at_score_max": float(values[idx]),
        "max_x": float(x[idx]),
        "max_y": float(y[idx]),
        "top1_score_centroid_x": cx,
        "top1_score_centroid_y": cy,
        "domain_integral": weighted_sum(values, area, np.ones_like(values, dtype=bool)),
        "domain_mean": weighted_mean(values, area, np.ones_like(values, dtype=bool)),
        "top1_integral": weighted_sum(values, area, top1),
        "top1_mean": weighted_mean(values, area, top1),
    }
    for band_name, band_fn in BANDS.items():
        mask = band_fn(x, y)
        base[f"{band_name}_integral"] = weighted_sum(values, area, mask)
        base[f"{band_name}_mean"] = weighted_mean(values, area, mask)
        base[f"{band_name}_score_max"] = float(np.nanmax(score[mask])) if np.any(mask) else float("nan")
    rows.append(base)


def add_overlap_rows(
    rows: list[dict[str, object]],
    run_name: str,
    state: str,
    pidl_step: int,
    field: str,
    fem_top1: np.ndarray,
    pidl_top1: np.ndarray,
    fem_top5: np.ndarray,
    pidl_top5: np.ndarray,
    area: np.ndarray,
) -> None:
    for label, fem_mask, pidl_mask in [
        ("top1_area", fem_top1, pidl_top1),
        ("top5_area", fem_top5, pidl_top5),
    ]:
        inter = fem_mask & pidl_mask
        union = fem_mask | pidl_mask
        fem_area = float(np.nansum(area[fem_mask]))
        pidl_area = float(np.nansum(area[pidl_mask]))
        inter_area = float(np.nansum(area[inter]))
        union_area = float(np.nansum(area[union]))
        rows.append(
            {
                "run": run_name,
                "state_label": state,
                "mapped_pidl_step": pidl_step,
                "field": field,
                "mask": label,
                "fem_area": fem_area,
                "pidl_area": pidl_area,
                "intersection_area": inter_area,
                "union_area": union_area,
                "iou": inter_area / union_area if union_area > 0 else float("nan"),
                "fem_capture_fraction": inter_area / fem_area if fem_area > 0 else float("nan"),
                "pidl_precision_fraction": inter_area / pidl_area if pidl_area > 0 else float("nan"),
            }
        )


def write_tables(peak_rows: list[dict[str, object]], overlap_rows: list[dict[str, object]]) -> None:
    with (TABLES / "localization_peak_metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(peak_rows[0].keys()))
        writer.writeheader()
        writer.writerows(peak_rows)
    with (TABLES / "process_zone_overlap_metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(overlap_rows[0].keys()))
        writer.writeheader()
        writer.writerows(overlap_rows)

    band_rows = [
        row
        for row in peak_rows
        if row["field"] in {"alpha", "history", "psi_active", "eps_yy", "sigma_effective_1"}
        and row["state_label"] in {"c20_peak", "c40_peak", "c60_peak", "c69_peak"}
    ]
    with (TABLES / "right_boundary_band_metrics.csv").open("w", newline="") as f:
        keys = [
            "source",
            "state_label",
            "mapped_pidl_step",
            "field",
            "right_boundary_band_integral",
            "right_boundary_band_mean",
            "right_boundary_band_score_max",
            "right_half_path_band_integral",
            "right_half_path_band_mean",
            "right_half_path_band_score_max",
            "max_x",
            "max_y",
            "top1_score_centroid_x",
            "top1_score_centroid_y",
        ]
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([{k: row[k] for k in keys} for row in band_rows])


def plot_overlap_heatmap(overlap_rows: list[dict[str, object]]) -> None:
    fields = ["alpha", "history", "psi_active", "eps_yy", "sigma_effective_1"]
    states = ["c20_peak", "c40_peak", "c60_peak", "c69_peak"]
    runs = list(CASES.keys())
    fig, axes = plt.subplots(len(fields), 1, figsize=(12, 12), constrained_layout=True)
    for ax, field in zip(axes, fields):
        mat = np.full((len(runs), len(states)), np.nan)
        for i, run in enumerate(runs):
            for j, state in enumerate(states):
                hits = [
                    row
                    for row in overlap_rows
                    if row["run"] == run
                    and row["state_label"] == state
                    and row["field"] == field
                    and row["mask"] == "top1_area"
                ]
                if hits:
                    mat[i, j] = float(hits[0]["iou"])
        im = ax.imshow(mat, vmin=0, vmax=1, cmap="viridis", aspect="auto")
        ax.set_title(f"Top-1% localization IoU: {field}")
        ax.set_xticks(np.arange(len(states)))
        ax.set_xticklabels(states)
        ax.set_yticks(np.arange(len(runs)))
        ax.set_yticklabels(runs)
        for i in range(len(runs)):
            for j in range(len(states)):
                value = mat[i, j]
                ax.text(j, i, "nan" if not np.isfinite(value) else f"{value:.2f}", ha="center", va="center", color="white" if np.isfinite(value) and value < 0.45 else "black", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    fig.suptitle("FEM/PIDL process-zone localization overlap on FEM grid")
    for ext in ["png", "pdf"]:
        fig.savefig(FIGURES / f"process_zone_overlap_iou.{ext}", dpi=220)
    plt.close(fig)


def plot_boundary_and_max_metrics(peak_rows: list[dict[str, object]]) -> None:
    states = ["c20_peak", "c40_peak", "c60_peak", "c69_peak"]
    sources = ["FEM", *CASES.keys()]
    fields = ["alpha", "history", "psi_active", "eps_yy", "sigma_effective_1"]
    fig, axes = plt.subplots(len(fields), 2, figsize=(14, 15), constrained_layout=True)
    colors = {"FEM": "black", "raw_pidl_g": "tab:red", "active_fem": "tab:blue", "delta_alpha_bar": "tab:green"}
    x = np.arange(len(states))
    for r, field in enumerate(fields):
        for source in sources:
            rows = [
                row
                for row in peak_rows
                if row["source"] == source and row["field"] == field and row["state_label"] in states
            ]
            rows = sorted(rows, key=lambda row: states.index(str(row["state_label"])))
            axes[r, 0].plot(x, [row["max_x"] for row in rows], marker="o", label=source, color=colors[source])
            axes[r, 1].plot(
                x,
                [row["right_boundary_band_score_max"] for row in rows],
                marker="o",
                label=source,
                color=colors[source],
            )
        axes[r, 0].set_title(f"{field}: x-location of localized maximum")
        axes[r, 0].set_ylabel("x")
        axes[r, 0].set_ylim(-0.02, 1.02)
        axes[r, 1].set_title(f"{field}: right-boundary-band localization score max")
        if field in {"history", "psi_active"}:
            axes[r, 1].set_yscale("symlog", linthresh=1e-8)
        for ax in axes[r]:
            ax.set_xticks(x)
            ax.set_xticklabels(states, rotation=30, ha="right")
            ax.grid(alpha=0.25)
            ax.legend(fontsize=7, ncol=2)
    fig.suptitle("Localization path and right-boundary evidence")
    for ext in ["png", "pdf"]:
        fig.savefig(FIGURES / f"localization_peak_and_boundary_metrics.{ext}", dpi=220)
    plt.close(fig)


def plot_c69_montage(fields_on_fem: dict[tuple[str, str, str], np.ndarray], fem_x: np.ndarray, fem_y: np.ndarray) -> None:
    sources = ["FEM", "raw_pidl_g", "active_fem", "delta_alpha_bar"]
    fields = ["alpha", "history", "psi_active", "sigma_effective_1"]
    state = "c69_peak"
    fig, axes = plt.subplots(len(sources), len(fields), figsize=(13, 10), constrained_layout=True)
    for c, field in enumerate(fields):
        all_vals = [fields_on_fem[(source, state, field)] for source in sources]
        if field in {"history", "psi_active"}:
            plot_vals = [np.log10(np.maximum(values, 0) + 1e-30) for values in all_vals]
            vmin = float(np.nanpercentile(np.concatenate(plot_vals), 1))
            vmax = float(np.nanpercentile(np.concatenate(plot_vals), 99.5))
            title_suffix = "log10"
        else:
            plot_vals = all_vals
            vmin = float(np.nanpercentile(np.concatenate(plot_vals), 1))
            vmax = float(np.nanpercentile(np.concatenate(plot_vals), 99.5))
            title_suffix = "linear"
        for r, source in enumerate(sources):
            ax = axes[r, c]
            img = grid_image(plot_vals[r], fem_x, fem_y)
            im = ax.imshow(img, origin="lower", extent=[fem_x.min(), fem_x.max(), fem_y.min(), fem_y.max()], cmap="viridis", vmin=vmin, vmax=vmax, aspect="equal")
            ax.axvline(0.5, color="white", lw=0.4, alpha=0.7)
            ax.axhline(0.5, color="white", lw=0.4, alpha=0.7)
            ax.set_xticks([])
            ax.set_yticks([])
            if r == 0:
                ax.set_title(f"{field}\n{title_suffix}", fontsize=9)
            if c == 0:
                ax.set_ylabel(source, fontsize=9)
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle("c69_peak localization fields on the FEM grid")
    for ext in ["png", "pdf"]:
        fig.savefig(FIGURES / f"c69_peak_localization_montage.{ext}", dpi=220)
    plt.close(fig)


def write_readme(peak_rows: list[dict[str, object]], overlap_rows: list[dict[str, object]]) -> None:
    def find_peak(source: str, state: str, field: str) -> dict[str, object]:
        return next(row for row in peak_rows if row["source"] == source and row["state_label"] == state and row["field"] == field)

    def find_iou(run: str, state: str, field: str) -> float:
        row = next(
            row
            for row in overlap_rows
            if row["run"] == run and row["state_label"] == state and row["field"] == field and row["mask"] == "top1_area"
        )
        return float(row["iou"])

    raw_h = find_peak("raw_pidl_g", "c69_peak", "history")
    active_h = find_peak("active_fem", "c69_peak", "history")
    delta_h = find_peak("delta_alpha_bar", "c69_peak", "history")
    fem_h = find_peak("FEM", "c69_peak", "history")
    text = f"""# Oracle Triplet Localization Audit

Purpose:

This is a separate post-hoc localization audit for the three oracle PIDL runs.
It uses the already downloaded archives and the corrected state mapping:

```text
cN_peak -> PIDL step 5*(N-1)+3
```

States audited:

```text
c1_peak, c20_peak, c40_peak, c60_peak, c69_peak
```

Fields audited:

```text
alpha, history/alpha_bar, fatigue depletion, stiffness degradation,
psi_active, eps_yy, sigma_effective_1
```

Method:

- PIDL triangle fields are shifted into the FEM frame with `x+0.5, y+0.5`.
- PIDL triangle fields are area-averaged onto the FEM quadrilateral centroid grid.
- The audit records global maxima, top-1% localization centroids, band means/integrals,
  right-boundary-band evidence, and FEM/PIDL top-1% and top-5% localization overlap.
- For `f_fatigue` and `g(alpha)`, localization means low values, so the score is based
  on depletion/degradation rather than the raw maximum.

Key c69 history evidence:

- FEM c69 history max: `{fem_h['field_value_at_score_max']:.6g}`
- raw_pidl_g c69 history max: `{raw_h['field_value_at_score_max']:.6g}`
- active_fem c69 history max: `{active_h['field_value_at_score_max']:.6g}`
- delta_alpha_bar c69 history max: `{delta_h['field_value_at_score_max']:.6g}`

Key interpretation:

- `raw_pidl_g` reaches the FEM fracture timing but with strongly over-amplified history.
- `active_fem` improves early active/history agreement but still does not localize enough
  boundary fracture at c69.
- `delta_alpha_bar` matches history almost exactly, including at c69, but still does not
  reproduce penetration; therefore history magnitude alone is not the missing ingredient.
- The remaining mechanism is the coupled localization loop: stress/strain localization,
  active driver, damage update, stiffness degradation, and next-cycle redistribution.

Selected c69 top-1% localization IoU:

| run | history IoU | psi_active IoU | sigma_effective_1 IoU |
|---|---:|---:|---:|
| raw_pidl_g | {find_iou('raw_pidl_g', 'c69_peak', 'history'):.4f} | {find_iou('raw_pidl_g', 'c69_peak', 'psi_active'):.4f} | {find_iou('raw_pidl_g', 'c69_peak', 'sigma_effective_1'):.4f} |
| active_fem | {find_iou('active_fem', 'c69_peak', 'history'):.4f} | {find_iou('active_fem', 'c69_peak', 'psi_active'):.4f} | {find_iou('active_fem', 'c69_peak', 'sigma_effective_1'):.4f} |
| delta_alpha_bar | {find_iou('delta_alpha_bar', 'c69_peak', 'history'):.4f} | {find_iou('delta_alpha_bar', 'c69_peak', 'psi_active'):.4f} | {find_iou('delta_alpha_bar', 'c69_peak', 'sigma_effective_1'):.4f} |

Outputs:

- `tables/localization_peak_metrics.csv`
- `tables/process_zone_overlap_metrics.csv`
- `tables/right_boundary_band_metrics.csv`
- `figures/process_zone_overlap_iou.png`
- `figures/localization_peak_and_boundary_metrics.png`
- `figures/c69_peak_localization_montage.png`
"""
    (OUT / "README_localization_audit.md").write_text(text)


def write_manifest() -> None:
    manifest = {
        "name": "oracle_triplet_localization_audit_20260610",
        "fem_reference": str(FEM_MAT),
        "cases": {name: str(path) for name, path in CASES.items()},
        "state_mapping": "cN_peak -> PIDL step 5*(N-1)+3",
        "states": STATES,
        "fields": list(FIELDS),
        "tables": [
            "tables/localization_peak_metrics.csv",
            "tables/process_zone_overlap_metrics.csv",
            "tables/right_boundary_band_metrics.csv",
        ],
        "figures": [
            "figures/process_zone_overlap_iou.png",
            "figures/localization_peak_and_boundary_metrics.png",
            "figures/c69_peak_localization_montage.png",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    ensure_dirs()
    peak_rows, overlap_rows, fields_on_fem, fem_x, fem_y = collect_data()
    write_tables(peak_rows, overlap_rows)
    plot_overlap_heatmap(overlap_rows)
    plot_boundary_and_max_metrics(peak_rows)
    plot_c69_montage(fields_on_fem, fem_x, fem_y)
    write_readme(peak_rows, overlap_rows)
    write_manifest()
    print(OUT)


if __name__ == "__main__":
    main()
