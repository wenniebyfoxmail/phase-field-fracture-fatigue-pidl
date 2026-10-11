from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check 2")
FEM_CASE = BASE / "FEM cyclic 012/cases/standard"
PIDL_CASE = BASE / "PIDL cyclic 012/cases/stateTiming_substeps025_untilFrac_Nphys120_Nstep600"
OUTDIR = BASE / "PIDL cyclic 012/figures/most_aligned_pidl_vs_standard_fem"
OUTDIR.mkdir(parents=True, exist_ok=True)

FEM_MAT = FEM_CASE / "raw_data/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat"
PIDL_ALPHA_DIR = PIDL_CASE / "raw_data/taobo_archive/alpha_snapshots"
FRONT_DIR = BASE / "PIDL cyclic 012/figures/protocol_comparison"
ENERGY_TIERS = BASE / "PIDL cyclic 012/analysis/aligned_fem_pidl_energy_tiers.csv"


def structured_grid_from_points(x, y, values):
    """Return X, Y, V arrays from a structured point cloud sorted by y then x."""
    order = np.lexsort((x, y))
    xs = np.unique(np.round(x, 12))
    ys = np.unique(np.round(y, 12))
    nx, ny = len(xs), len(ys)
    if nx * ny != len(values):
        raise ValueError(f"Point cloud is not a full structured grid: {nx} x {ny} != {len(values)}")
    X = x[order].reshape(ny, nx)
    Y = y[order].reshape(ny, nx)
    V = values[order].reshape(ny, nx)
    return X, Y, V


def load_fem_fields(cycles):
    with h5py.File(FEM_MAT, "r") as f:
        cent = np.array(f["element_centroids"]).T
        d = np.array(f["d_elem"])

    # FEM exports centroids in [0, 1] x [0, 1]. PIDL snapshots are centred in
    # [-0.5, 0.5] x [-0.5, 0.5], so shift both axes for a fair visual comparison.
    x = cent[:, 0] - 0.5
    y = cent[:, 1] - 0.5
    fields = {}
    for cycle in cycles:
        X, Y, V = structured_grid_from_points(x, y, np.clip(d[cycle - 1], 0.0, 1.0))
        fields[cycle] = (X, Y, V)
    return fields


def load_pidl_field(snapshot):
    arr = np.load(PIDL_ALPHA_DIR / f"alpha_cycle_{snapshot:04d}.npy")
    x, y, alpha = arr[:, 0], arr[:, 1], np.clip(arr[:, 2], 0.0, 1.0)
    return structured_grid_from_points(x, y, alpha)


def plot_field_comparison():
    columns = [
        ("initial", 1, 0, "FEM c1 / PIDL s0"),
        ("c20", 20, 100, "physical c20"),
        ("c40", 40, 200, "physical c40"),
        ("c60", 60, 300, "physical c60"),
        ("near event", 69, 340, "FEM c69 / PIDL c68"),
    ]
    fem_fields = load_fem_fields([c[1] for c in columns])
    pidl_fields = {snap: load_pidl_field(snap) for _, _, snap, _ in columns}

    fig, axes = plt.subplots(2, len(columns), figsize=(15.6, 5.7), sharex=True, sharey=True)
    cmap = "magma"
    last_im = None
    for j, (_, fem_cycle, pidl_snapshot, title) in enumerate(columns):
        for row, method in enumerate(["FEM standard d", "PIDL FEM-like substep alpha"]):
            ax = axes[row, j]
            if row == 0:
                X, Y, V = fem_fields[fem_cycle]
            else:
                X, Y, V = pidl_fields[pidl_snapshot]
            last_im = ax.imshow(
                V,
                extent=(-0.5, 0.5, -0.5, 0.5),
                origin="lower",
                cmap=cmap,
                vmin=0,
                vmax=1,
                interpolation="nearest",
                aspect="equal",
            )
            try:
                ax.contour(X, Y, V, levels=[0.95], colors="cyan", linewidths=0.55)
            except Exception:
                pass
            ax.set_xlim(-0.5, 0.5)
            ax.set_ylim(-0.5, 0.5)
            if row == 0:
                ax.set_title(title, fontsize=10)
            if j == 0:
                ax.set_ylabel(method, fontsize=10)
            else:
                ax.set_yticklabels([])
            if row == 1:
                ax.set_xlabel("x")
            else:
                ax.set_xticklabels([])
            ax.tick_params(labelsize=8, length=2)

    fig.subplots_adjust(left=0.065, right=0.875, bottom=0.09, top=0.86, wspace=0.06, hspace=0.08)
    cbar_ax = fig.add_axes([0.895, 0.17, 0.016, 0.66])
    cbar = fig.colorbar(last_im, cax=cbar_ax)
    cbar.set_label("phase field: FEM d / PIDL alpha", fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    fig.suptitle("Most aligned PIDL field/front vs standard FEM, shared centred domain and colour scale", fontsize=14)
    for ext in ["png", "pdf"]:
        fig.savefig(OUTDIR / f"most_aligned_pidl_standard_fem_phase_field_shared_background_20260608.{ext}", dpi=300)
    plt.close(fig)


def plot_metric_comparison():
    fem_front = pd.read_csv(FRONT_DIR / "standard_fem_phase_front_metrics_20260608.csv")
    pidl_front = pd.read_csv(FRONT_DIR / "pidl_femlike_substep_phase_front_metrics_20260608.csv")
    one_peak_front = pd.read_csv(FRONT_DIR / "pidl_one_peak_phase_front_metrics_20260608.csv")
    energy = pd.read_csv(ENERGY_TIERS)
    energy = energy[energy["reference"] == "FEM standard"].copy()

    cycles = np.arange(20, 70)
    fem_interp = np.interp(cycles, fem_front["cycle"], fem_front["x_tip_d095_norm"])
    pidl_interp = np.interp(cycles, pidl_front["physical_cycle_est"], pidl_front["x_tip_alpha095"])
    one_peak_interp = np.interp(cycles, one_peak_front["physical_cycle_est"], one_peak_front["x_tip_alpha095"])
    summary = pd.DataFrame(
        [
            {
                "candidate": "PIDL FEM-like substeps",
                "front_rmse_c20_c69": np.sqrt(np.mean((pidl_interp - fem_interp) ** 2)),
                "front_mae_c20_c69": np.mean(np.abs(pidl_interp - fem_interp)),
                "front_x_at_c69_interp": pidl_interp[-1],
            },
            {
                "candidate": "PIDL one-peak baseline",
                "front_rmse_c20_c69": np.sqrt(np.mean((one_peak_interp - fem_interp) ** 2)),
                "front_mae_c20_c69": np.mean(np.abs(one_peak_interp - fem_interp)),
                "front_x_at_c69_interp": one_peak_interp[-1],
            },
        ]
    )
    summary.to_csv(OUTDIR / "most_aligned_pidl_selection_summary_20260608.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(13.8, 3.9))
    ax = axes[0]
    ax.plot(fem_front["cycle"], fem_front["x_tip_d095_norm"], color="#0072B2", lw=1.8, label="FEM standard")
    ax.plot(
        pidl_front["physical_cycle_est"],
        pidl_front["x_tip_alpha095"],
        color="#E69F00",
        lw=1.7,
        marker="s",
        ms=3.5,
        label="PIDL FEM-like substeps",
    )
    ax.set_title("Crack-front trajectory")
    ax.set_xlabel("physical cycle")
    ax.set_ylabel("rightmost front x, threshold 0.95")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, frameon=False)

    ax = axes[1]
    ax.plot(energy["cycle"], energy["fem_E_d"], color="#0072B2", lw=1.7, marker="o", ms=4, label="FEM standard")
    ax.plot(energy["cycle"], energy["pidl_E_d"], color="#E69F00", lw=1.7, marker="s", ms=4, label="PIDL aligned energy tiers")
    ax.set_title("Damage energy")
    ax.set_xlabel("cycle")
    ax.set_ylabel("E_d")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, frameon=False)

    ax = axes[2]
    ratio = energy.dropna(subset=["ratio_delta_E_d_pidl_over_fem"])
    ax.plot(
        ratio["cycle"],
        ratio["ratio_delta_E_d_pidl_over_fem"],
        color="#333333",
        lw=1.7,
        marker="o",
        ms=4,
    )
    ax.axhline(1.0, color="0.55", lw=0.9, ls="--")
    ax.axhline(0.25, color="0.55", lw=0.9, ls=":")
    ax.set_ylim(0, max(1.05, float(ratio["ratio_delta_E_d_pidl_over_fem"].max()) * 1.15))
    ax.set_title("Incremental damage-energy ratio")
    ax.set_xlabel("cycle")
    ax.set_ylabel("PIDL / FEM Delta E_d")
    ax.grid(alpha=0.25)

    fig.suptitle("Most aligned PIDL vs standard FEM: front and energy metrics", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    for ext in ["png", "pdf"]:
        fig.savefig(OUTDIR / f"most_aligned_pidl_standard_fem_metrics_20260608.{ext}", dpi=300)
    plt.close(fig)


def write_note():
    note = OUTDIR / "most_aligned_pidl_standard_fem_note_20260608.md"
    note.write_text(
        """# Most aligned PIDL vs standard FEM figure note - 2026-06-08

## Purpose

These figures compare the current most aligned PIDL field/front case against the standard FEM case.

The PIDL case selected for field/front alignment is:

```text
cases/stateTiming_substeps025_untilFrac_Nphys120_Nstep600
```

This is selected because its stored FEM-like substep alpha snapshots are the current until-fracture loading-step/timing control against standard FEM.

## Figure outputs

```text
most_aligned_pidl_standard_fem_phase_field_shared_background_20260608.png
most_aligned_pidl_standard_fem_phase_field_shared_background_20260608.pdf
most_aligned_pidl_standard_fem_metrics_20260608.png
most_aligned_pidl_standard_fem_metrics_20260608.pdf
most_aligned_pidl_selection_summary_20260608.csv
```

## Visual convention

The phase-field figure uses a shared centred domain:

```text
x in [-0.5, 0.5], y in [-0.5, 0.5]
```

FEM element centroids were exported in `[0, 1] x [0, 1]`, so both x and y are shifted by `-0.5` before plotting. PIDL alpha snapshots are already centred in `[-0.5, 0.5] x [-0.5, 0.5]`.

Both rows use the same colour scale, `0 <= phase field <= 1`, and the cyan contour marks the high-damage/front threshold 0.95.

## Why the earlier backgrounds looked different

The earlier FEM and PIDL phase-field plots were drawn from different stored field supports: FEM uses element-centroid fields, while PIDL uses nodal alpha snapshots. The earlier FEM visual convention also did not centre both axes consistently. The new figure fixes the visual comparison by using the same centred domain, extent, colour map, and colour limits.

## Why the new FEM fracture does not have the same apparent width as the notch

The plotted FEM crack is a diffuse phase-field damage zone, not a geometric slit. Its visible width depends on the regularisation length `ell=0.01`, the mesh/element display, interpolation, and the colour threshold used for viewing. The notch/precrack is the initial seeded damage region; the propagating fracture should be compared by a threshold contour or front position, not by expecting the coloured band to have the same apparent width as the notch aperture.

## Caveat

The field/front comparison uses the PIDL FEM-like substep snapshots. The energy panel uses the available aligned FEM/PIDL energy tiers in the organized PIDL analysis folder, which are sparse at c1, c20, c40, and c69.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    plot_field_comparison()
    plot_metric_comparison()
    write_note()
    print(f"Wrote figures and note to {OUTDIR}")
