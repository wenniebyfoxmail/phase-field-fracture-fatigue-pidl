#!/usr/bin/env python3
"""
compute_SN_sensitivity.py — A3 (Apr 27 2026, external review G4)

S-N regression cross-criterion sensitivity test. For each archive, find
N_f via 5 different fracture criteria; for the baseline coeff=1.0 Umax
sweep, fit log(N_f) = m·log(Umax) + b for each criterion; tabulate
slope m + R² to test whether the headline S-N exponent is robust to
criterion choice.

Five criteria (operate on already-cached per-cycle .npy):

  C1 ("geometric"):    first cycle where x_tip ≥ 0.5
  C2 ("energy drop"):  argmax |dE_el / dN|
  C3 ("alpha-bar"):    first cycle where ᾱ_max ≥ 50  (Carrara saturation)
  C4 ("f-min"):        first cycle where f_min ≤ 0.05  (95% degraded somewhere)
  C5 ("Kt blowup"):    first cycle where Kt > 100  (numerical signature)

Per MEMORY (apr-15 unification), C1, C2 should give identical N_f for
SENT geometry — this script verifies that empirically across all archives.

Output:
  N_f_per_criterion.csv          per-archive table
  figures/audit/SN_regression_per_criterion.png
                                  4-panel: S-N curve per criterion
  SN_slopes_per_criterion.csv    slope, intercept, R² per criterion (Umax sweep)
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent

# All "discovered" archive dirs in SENS_tensile/ matching the trained pattern
ARCHIVE_GLOB = "*PFFmodel_AT1*fatigue_on_carrara*"

# Baseline coeff=1.0 Umax sweep — used for the S-N regression
BASELINE_UMAX_SWEEP = {
    0.09: "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N400_R0.0_Umax0.09",
    0.10: "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N350_R0.0_Umax0.1",
    0.11: "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N250_R0.0_Umax0.11",
    0.12: "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12",
}

# FEM reference S-N (per memory direction_6_2_golahmar_apr22.md):
# FEM N_f at (Umax 0.08, 0.09, 0.10, 0.11, 0.12) = (396, 254, 170, 117, 82)
FEM_NF = {0.08: 396, 0.09: 254, 0.10: 170, 0.11: 117, 0.12: 82}

# Thresholds (single source of truth)
TH_X_TIP = 0.5
TH_ALPHA_BAR = 50.0
TH_F_MIN = 0.05
TH_KT = 100.0

# Output column order
CRITERIA = ["C1_x_tip", "C2_dEel", "C3_alphabar", "C4_fmin", "C5_Kt"]


def find_Nf_per_criteria(archive_dir: Path):
    """Return dict {criterion → N_f or NaN if never reached}."""
    bm = archive_dir / "best_models"
    out = {c: np.nan for c in CRITERIA}

    # C1 — x_tip ≥ 0.5
    try:
        x = np.load(str(bm / "x_tip_vs_cycle.npy"))
        idx = np.where(x >= TH_X_TIP)[0]
        if len(idx) > 0:
            out["C1_x_tip"] = int(idx[0])
    except FileNotFoundError:
        pass

    # C2 — max|dE_el/dN|
    try:
        E = np.load(str(bm / "E_el_vs_cycle.npy"))
        if len(E) >= 3:
            dE = np.abs(np.diff(E))
            out["C2_dEel"] = int(np.argmax(dE) + 1)   # +1: dE_el[i] = E[i+1]-E[i]
    except FileNotFoundError:
        pass

    # C3 — ᾱ_max ≥ 50
    try:
        ab = np.load(str(bm / "alpha_bar_vs_cycle.npy"))
        if ab.ndim == 2:
            ab_max = ab[:, 0]
        else:
            ab_max = ab
        idx = np.where(ab_max >= TH_ALPHA_BAR)[0]
        if len(idx) > 0:
            out["C3_alphabar"] = int(idx[0])
    except FileNotFoundError:
        pass

    # C4 — f_min ≤ 0.05
    try:
        ab = np.load(str(bm / "alpha_bar_vs_cycle.npy"))
        if ab.ndim == 2 and ab.shape[1] >= 3:
            f_min_per_c = ab[:, 2]
            idx = np.where(f_min_per_c <= TH_F_MIN)[0]
            if len(idx) > 0:
                out["C4_fmin"] = int(idx[0])
    except FileNotFoundError:
        pass

    # C5 — Kt > 100 (numerical blowup; well past LEFM-valid regime)
    try:
        Kt = np.load(str(bm / "Kt_vs_cycle.npy"))
        idx = np.where(Kt > TH_KT)[0]
        if len(idx) > 0:
            out["C5_Kt"] = int(idx[0])
    except FileNotFoundError:
        pass

    return out


def linregress(x, y):
    """OLS y = m·x + b. Return (m, b, R²)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n = len(x)
    if n < 2:
        return np.nan, np.nan, np.nan
    m, b = np.polyfit(x, y, 1)
    pred = m * x + b
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return float(m), float(b), float(r2)


def main():
    print("Scanning archives…")
    archives = sorted(HERE.glob(ARCHIVE_GLOB))
    print(f"  {len(archives)} archive dirs found")

    # Per-archive table
    rows = []
    for adir in archives:
        if not adir.is_dir():
            continue
        Nf = find_Nf_per_criteria(adir)
        umax = ""
        for tok in adir.name.split("_"):
            if tok.startswith("Umax"):
                umax = tok[4:]
                break
        rows.append({"archive": adir.name, "umax": umax, **Nf})

    out_csv = HERE / "N_f_per_criterion.csv"
    cols = ["archive", "umax"] + CRITERIA
    with open(out_csv, "w") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(str(r[c]) if isinstance(r[c], (int, str)) else f"{r[c]}"
                              for c in cols) + "\n")
    print(f"  → {out_csv.relative_to(HERE.parent)}  ({len(rows)} archives)")

    # S-N regression on baseline coeff=1.0 Umax sweep
    print("\nFitting S-N regressions per criterion (baseline coeff=1.0)…")
    sweep_data = {c: {"u": [], "Nf": []} for c in CRITERIA}
    for u, name in BASELINE_UMAX_SWEEP.items():
        adir = HERE / name
        if not adir.is_dir():
            continue
        Nf = find_Nf_per_criteria(adir)
        for c in CRITERIA:
            if np.isfinite(Nf[c]):
                sweep_data[c]["u"].append(u)
                sweep_data[c]["Nf"].append(Nf[c])

    fit_rows = []
    for c in CRITERIA:
        u = np.array(sweep_data[c]["u"])
        Nf = np.array(sweep_data[c]["Nf"])
        if len(u) >= 2:
            m, b, r2 = linregress(np.log10(u), np.log10(Nf))
            fit_rows.append({"criterion": c, "n_points": len(u),
                             "slope": m, "intercept": b, "r2": r2,
                             "Nf_at_Umax_0.12": Nf[u == 0.12].tolist()})
        else:
            fit_rows.append({"criterion": c, "n_points": len(u),
                             "slope": np.nan, "intercept": np.nan, "r2": np.nan,
                             "Nf_at_Umax_0.12": []})

    # FEM reference fit
    u_fem = np.array(sorted(FEM_NF.keys()))
    Nf_fem = np.array([FEM_NF[u] for u in u_fem])
    m_fem, b_fem, r2_fem = linregress(np.log10(u_fem), np.log10(Nf_fem))
    fit_rows.append({"criterion": "FEM_reference", "n_points": len(u_fem),
                     "slope": m_fem, "intercept": b_fem, "r2": r2_fem,
                     "Nf_at_Umax_0.12": [FEM_NF[0.12]]})

    fit_csv = HERE / "SN_slopes_per_criterion.csv"
    cols = ["criterion", "n_points", "slope", "intercept", "r2", "Nf_at_Umax_0.12"]
    with open(fit_csv, "w") as fh:
        fh.write(",".join(cols) + "\n")
        for r in fit_rows:
            fh.write(",".join(str(r[c]) if isinstance(r[c], (str, int, list))
                              else f"{r[c]:.4f}"
                              for c in cols) + "\n")
    print(f"  → {fit_csv.relative_to(HERE.parent)}")

    # Print summary table
    print()
    print(f"{'criterion':<15} {'n_pts':>6} {'slope':>10} {'intercept':>11} "
          f"{'R²':>7} {'N_f@U=0.12':>12}")
    for r in fit_rows:
        nf_str = ",".join(str(int(x)) for x in r["Nf_at_Umax_0.12"]) or "—"
        print(f"{r['criterion']:<15} {r['n_points']:>6} "
              f"{r['slope']:>10.4f} {r['intercept']:>11.4f} {r['r2']:>7.4f}  "
              f"{nf_str:>12}")
    print(f"  (FEM memory ref slope -3.876;  PIDL memory ref -3.571)")

    # Plot
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5), tight_layout=True)
    panel = 0
    u_grid = np.linspace(np.log10(0.085), np.log10(0.125), 20)
    for c in CRITERIA + ["FEM_reference"]:
        ax = axes[panel // 3, panel % 3]
        if c == "FEM_reference":
            u, Nf = u_fem, Nf_fem
            lbl = f"FEM (memory)  m={m_fem:.3f}"
            color = "k"
        else:
            u = np.array(sweep_data[c]["u"])
            Nf = np.array(sweep_data[c]["Nf"])
            fit = next(r for r in fit_rows if r["criterion"] == c)
            lbl = f"PIDL  m={fit['slope']:.3f}  R²={fit['r2']:.3f}"
            color = "C0"
        if len(u) >= 1:
            ax.scatter(u, Nf, color=color, s=70, zorder=5, label=lbl)
            if len(u) >= 2:
                fit = next(r for r in fit_rows if r["criterion"] == c)
                u_g = np.logspace(np.log10(0.085), np.log10(0.125), 30)
                ax.plot(u_g, 10 ** (fit["slope"] * np.log10(u_g) + fit["intercept"]),
                        color=color, linestyle="--", alpha=0.6)
        # Always overlay FEM ref
        if c != "FEM_reference":
            ax.scatter(u_fem, Nf_fem, color="grey", s=40, marker="^",
                       label=f"FEM ref  m={m_fem:.3f}")
            u_g = np.logspace(np.log10(0.075), np.log10(0.125), 30)
            ax.plot(u_g, 10 ** (m_fem * np.log10(u_g) + b_fem),
                    color="grey", linestyle=":", alpha=0.5)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel(r"$U_{max}$"); ax.set_ylabel(r"$N_f$")
        ax.set_title(c.replace("_", " "))
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=8)
        panel += 1
    out_dir = HERE / "figures" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "SN_regression_per_criterion.png"
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {p.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
