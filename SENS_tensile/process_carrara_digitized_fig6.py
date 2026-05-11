#!/usr/bin/env python3
"""
Process user-downloaded Carrara Fig.6(a) digitized CSVs.

This script produces two layers of outputs:
1. Cleaned raw digitized coordinates, with no physical-unit claim.
2. A transparent first-pass physical estimate for quick FEM-vs-paper checks.

The input CSVs currently look like manually sampled x(y) slices from Fig.6(a),
not fully calibrated physical coordinates. We therefore keep the raw layer and
make the physical layer explicitly assumption-driven.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import math

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code")
DOWNLOADS = Path("/Users/wenxiaofang/Downloads")
OUTDIR = ROOT / "docs" / "generated" / "carrara_fig6_digitized"

RAW_FILES = {
    1.5: DOWNLOADS / "1.5_10_-3.csv",
    2.0: DOWNLOADS / "2.0_10_-3.csv",
    2.5: DOWNLOADS / "2.5_10_-3.csv",
    3.0: DOWNLOADS / "3.0_10_-3.csv",
    4.0: DOWNLOADS / "4.0_10_-3.csv",
    5.0: DOWNLOADS / "5.0_10_-3.csv",
}

# Current repo-side FEM summary values (AMOR complete, MIEHE partial).
FEM_AMOR_NF = {
    1.5: 1111,
    2.0: 425,
    2.5: 195,
    3.0: 98,
    4.0: 26,
    5.0: 1,
}
FEM_MIEHE_NF = {
    1.5: 1132,
    2.0: 435,
    2.5: 200,
    3.0: 102,
    4.0: math.nan,
    5.0: math.nan,
}


@dataclass
class Curve:
    du_milli: float
    x_raw: np.ndarray
    y_raw: np.ndarray


def load_curve(path: Path, du_milli: float) -> Curve:
    rows: list[tuple[float, float]] = []
    with path.open("r", newline="") as f:
        reader = csv.reader(f, skipinitialspace=True)
        for row in reader:
            if not row:
                continue
            rows.append((float(row[0]), float(row[1])))

    arr = np.array(rows, dtype=float)

    # Sort by y first; the 2.5e-3 file contains one wraparound point at the end.
    order = np.argsort(arr[:, 1], kind="mergesort")
    arr = arr[order]

    # Drop exact/near-duplicate low-y wraparound artifacts, keeping the median x.
    y_round = np.round(arr[:, 1], 6)
    cleaned: list[tuple[float, float]] = []
    for y in np.unique(y_round):
        group = arr[y_round == y]
        if len(group) == 1:
            cleaned.append((group[0, 0], group[0, 1]))
            continue
        xs = np.sort(group[:, 0])
        cleaned.append((xs[len(xs) // 2], float(np.median(group[:, 1]))))

    arr = np.array(cleaned, dtype=float)
    return Curve(du_milli=du_milli, x_raw=arr[:, 0], y_raw=arr[:, 1])


def fit_basquin(du_vals: np.ndarray, nf_vals: np.ndarray) -> tuple[float, float]:
    coeff = np.polyfit(np.log(du_vals), np.log(nf_vals), 1)
    m = -coeff[0]
    c = float(np.exp(coeff[1]))
    return c, float(m)


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    curves = [load_curve(path, du) for du, path in sorted(RAW_FILES.items())]

    global_x_min = min(float(np.min(c.x_raw)) for c in curves)
    global_x_max = max(float(np.max(c.x_raw)) for c in curves)
    global_y_min = min(float(np.min(c.y_raw)) for c in curves)
    top_y_ref = float(np.median([c.y_raw[-1] for c in curves]))

    raw_rows: list[list[object]] = []
    est_rows: list[list[object]] = []
    endpoint_rows: list[list[object]] = []

    for curve in curves:
        x_norm = (curve.x_raw - global_x_min) / (global_x_max - global_x_min)
        y_norm = (curve.y_raw - global_y_min) / (top_y_ref - global_y_min)
        y_norm = np.clip(y_norm, 0.0, 1.0)

        # First-pass estimate:
        # - x-axis in Fig.6(a) spans 0..9000 cycles
        # - failure crack length visually clusters around a ~= 0.5 mm
        n_est = 9000.0 * x_norm
        a_est = 0.5 * y_norm

        for idx, (xr, yr, xn, yn, ne, ae) in enumerate(
            zip(curve.x_raw, curve.y_raw, x_norm, y_norm, n_est, a_est)
        ):
            raw_rows.append([
                curve.du_milli, idx, xr, yr, xn, yn
            ])
            est_rows.append([
                curve.du_milli, idx, xr, yr, ne, ae
            ])

        nf_est = float(n_est[-1])
        fem_amor = FEM_AMOR_NF[curve.du_milli]
        fem_miehe = FEM_MIEHE_NF[curve.du_milli]
        endpoint_rows.append([
            curve.du_milli,
            nf_est,
            fem_amor,
            "" if math.isnan(fem_miehe) else fem_miehe,
            nf_est / fem_amor if fem_amor else "",
            "" if math.isnan(fem_miehe) else nf_est / fem_miehe,
        ])

    # Outputs: cleaned raw and first-pass physical estimate.
    write_csv(
        OUTDIR / "carrara_fig6a_cleaned_raw.csv",
        ["du_times_1e-3_mm", "point_id", "x_raw", "y_raw", "x_norm_global", "y_norm_to_failure"],
        raw_rows,
    )
    write_csv(
        OUTDIR / "carrara_fig6a_estimated_physical.csv",
        ["du_times_1e-3_mm", "point_id", "x_raw", "y_raw", "N_cycle_est", "a_mm_est"],
        est_rows,
    )
    write_csv(
        OUTDIR / "carrara_fig6a_endpoint_comparison.csv",
        [
            "du_times_1e-3_mm",
            "Carrara_digitized_Nf_est",
            "FEM_AMOR_Nf",
            "FEM_MIEHE_Nf",
            "paper_over_FEM_AMOR",
            "paper_over_FEM_MIEHE",
        ],
        endpoint_rows,
    )

    # Basquin fits.
    du_vals = np.array([r[0] for r in endpoint_rows], dtype=float)
    paper_nf = np.array([r[1] for r in endpoint_rows], dtype=float)
    fem_amor_nf = np.array([r[2] for r in endpoint_rows], dtype=float)
    _, m_paper = fit_basquin(du_vals, paper_nf)
    _, m_fem_amor = fit_basquin(du_vals, fem_amor_nf)
    hcf_mask = du_vals <= 3.0
    _, m_paper_hcf = fit_basquin(du_vals[hcf_mask], paper_nf[hcf_mask])
    _, m_fem_amor_hcf = fit_basquin(du_vals[hcf_mask], fem_amor_nf[hcf_mask])

    # Plot raw digitized curves.
    plt.figure(figsize=(6.2, 4.5))
    for curve in curves:
        plt.plot(curve.x_raw, curve.y_raw, marker="o", ms=3, lw=1.2,
                 label=fr"$\Delta u={curve.du_milli}\times10^{{-3}}$")
    plt.xlabel("raw x")
    plt.ylabel("raw y")
    plt.title("Carrara Fig.6(a) digitized curves: cleaned raw coordinates")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUTDIR / "carrara_fig6a_cleaned_raw.png", dpi=220)
    plt.close()

    # Plot estimated physical curves.
    plt.figure(figsize=(6.2, 4.5))
    for curve in curves:
        mask = [row[0] == curve.du_milli for row in est_rows]
        rows = np.array([est_rows[i] for i, keep in enumerate(mask) if keep], dtype=float)
        plt.plot(rows[:, 4], rows[:, 5], marker="o", ms=3, lw=1.2,
                 label=fr"$\Delta u={curve.du_milli}\times10^{{-3}}$")
    plt.xlabel("N (estimated from plot span)")
    plt.ylabel("a [mm] (estimated)")
    plt.title("Carrara Fig.6(a): first-pass estimated physical curves")
    plt.xlim(left=0)
    plt.ylim(bottom=0, top=0.55)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUTDIR / "carrara_fig6a_estimated_physical.png", dpi=220)
    plt.close()

    # Endpoint comparison plot.
    plt.figure(figsize=(6.0, 4.3))
    plt.loglog(du_vals, paper_nf, "o-", lw=1.5, label=f"Carrara digitized est. all-point m={m_paper:.2f}")
    plt.loglog(du_vals, fem_amor_nf, "s--", lw=1.5, label=f"FEM AMOR summary all-point m={m_fem_amor:.2f}")
    plt.gca().invert_xaxis()
    plt.xlabel(r"$\Delta u \; [10^{-3}\,\mathrm{mm}]$")
    plt.ylabel(r"$N_f$")
    plt.title("Carrara paper-side estimate vs current FEM summary")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUTDIR / "carrara_fig6a_endpoint_comparison.png", dpi=220)
    plt.close()

    notes = f"""# Carrara Fig.6(a) digitized processing

Generated by:
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile/process_carrara_digitized_fig6.py`

## Inputs
- Six CSVs from `/Users/wenxiaofang/Downloads`
- Source figure: Carrara 2020, Fig.6(a) on page 14 of
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/references/ .pdf`

## What was cleaned
- Sorted each file by `y`
- Removed wraparound duplicate rows at the same `y` level
- Kept the cleaned raw coordinates verbatim in `carrara_fig6a_cleaned_raw.csv`

## Important interpretation
These CSVs do **not** look like directly calibrated physical coordinates.
Instead, they look like manually sampled x(y) traces on a normalized plot box:
- `y` levels are nearly shared across all six files
- one file (`2.5e-3`) contains a wraparound point, typical of manual extraction

Therefore the raw layer is the trustworthy artifact.

## First-pass physical estimate assumptions
For quick FEM-vs-paper screening, the script also builds an estimated physical layer:
- global left edge maps to `N = 0`
- global rightmost sampled point maps to `N = 9000`
- global lowest sampled `y` maps to `a = 0`
- median top sampled `y` maps to `a = 0.5 mm`

This estimate is useful for trend checks, but it is **not yet publication-grade**.
If you later provide the exact WebPlotDigitizer calibration or the `.json/.wpg`
project file, re-running with true axis anchors will upgrade the numbers directly.

## Current quick comparison
- Estimated paper-side Basquin slope, all six points: `m = {m_paper:.2f}`
- Current FEM AMOR summary slope, all six points: `m = {m_fem_amor:.2f}`
- Estimated paper-side Basquin slope, HCF-only (`Δu <= 3.0e-3`): `m = {m_paper_hcf:.2f}`
- Current FEM AMOR summary slope, HCF-only (`Δu <= 3.0e-3`): `m = {m_fem_amor_hcf:.2f}`
- Use `carrara_fig6a_endpoint_comparison.csv` for direct ratio checks.
"""
    (OUTDIR / "README.md").write_text(notes)

    print(f"Wrote outputs to: {OUTDIR}")


if __name__ == "__main__":
    main()
