#!/usr/bin/env python3
"""analyze_fwhm_band.py — Layer-2 morphology audit: PIDL α-band vs FEM d-band width

Per user protocol (May 18):
  - morphology variable: d (FEM) / α (PIDL), NOT ᾱ
  - take transverse profile d(y) at fixed x (multiple x: tip-near + wake)
  - two width metrics: FWHM (y-width where d ≥ 0.5·d_max) + effective width (∫d dy / max(d))
  - report at several cycles
  - GATE: do not use "FEM diffuse process zone" framing unless FEM width is ≥ 1.5× PIDL width

Tests Umax = 0.12 by default (richest data). Outputs a table + a multi-panel figure
showing d(y) profile and the two width metrics vs cycle.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
import scipy.io as sio
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
FEM_BASE = Path.home() / "Downloads" / "_pidl_handoff_v2"


UMAX_CFG = {
    0.12: dict(
        fem_csv_tag="12",
        snap_cycles=[1, 40, 70, 82],
        baseline_rel=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
                      "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
                      "N300_R0.0_Umax0.12"),
        sdf_rel=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
                 "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
                 "N100_R0.0_Umax0.12_sdfRibbon_eps0.001_uv_only"),
    ),
    0.08: dict(
        fem_csv_tag="08",
        snap_cycles=[1, 150, 350, 396],
        baseline_rel=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
                      "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
                      "N700_R0.0_Umax0.08"),
        sdf_rel=("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
                 "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
                 "N400_R0.0_Umax0.08_sdfRibbon_eps0.001_uv_only"),
    ),
}


def find_archive(rel: str) -> Path | None:
    for c in [HERE / rel,
              Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile") / rel]:
        if (c / "best_models" / "alpha_bar_vs_cycle.npy").is_file():
            return c
    return None


def fwhm_and_effwidth(y: np.ndarray, f: np.ndarray) -> tuple[float, float, float]:
    """Return (FWHM, effective_width, peak) where:
       FWHM = width of region where f >= 0.5 * f.max()
       effective_width = ∫ f dy / max(f)
       peak = max(f)
    """
    if len(y) < 3 or f.max() <= 0:
        return float("nan"), float("nan"), float(f.max() if len(f) else 0.0)
    peak = float(f.max())
    # FWHM (linear interpolation on threshold crossings)
    thresh = 0.5 * peak
    above = f >= thresh
    if above.sum() < 2:
        fwhm = 0.0
    else:
        idx = np.where(above)[0]
        # interpolate left crossing
        i_lo = idx[0]
        if i_lo == 0 or f[i_lo-1] >= thresh:
            y_lo = y[i_lo]
        else:
            t = (thresh - f[i_lo-1]) / (f[i_lo] - f[i_lo-1])
            y_lo = y[i_lo-1] + t * (y[i_lo] - y[i_lo-1])
        i_hi = idx[-1]
        if i_hi == len(f) - 1 or f[i_hi+1] >= thresh:
            y_hi = y[i_hi]
        else:
            t = (thresh - f[i_hi]) / (f[i_hi+1] - f[i_hi])
            y_hi = y[i_hi] + t * (y[i_hi+1] - y[i_hi])
        fwhm = float(y_hi - y_lo)
    # effective width
    eff = float(np.trapezoid(f, y) / peak)
    return fwhm, eff, peak


def fem_profile_at_x(d_elem: np.ndarray, centroids: np.ndarray,
                     x_target: float, y_min: float = -0.5, y_max: float = 0.5,
                     n_y: int = 201, dx_band: float = 0.01) -> tuple[np.ndarray, np.ndarray]:
    """Extract FEM d(y) at fixed x by averaging element centroids within |x-x_target| < dx_band,
    then binning along y. dx_band kept small relative to ℓ=0.01."""
    mask = np.abs(centroids[:, 0] - x_target) < dx_band
    if mask.sum() < 5:
        return np.array([]), np.array([])
    xs = centroids[mask]
    ds = d_elem[mask]
    # bin by y
    y_grid = np.linspace(y_min, y_max, n_y)
    binsize = (y_max - y_min) / (n_y - 1)
    d_y = np.full(n_y, np.nan)
    for i, yt in enumerate(y_grid):
        sel = np.abs(xs[:, 1] - yt) < 1.5 * binsize
        if sel.any():
            d_y[i] = ds[sel].mean()
    # interpolate NaNs (small mesh gaps)
    valid = ~np.isnan(d_y)
    if valid.sum() < 2:
        return y_grid, d_y
    d_y = np.interp(y_grid, y_grid[valid], d_y[valid])
    return y_grid, d_y


def pidl_profile_at_x(fc, inp, x_target: float, ckpt_path: Path,
                      y_min: float = -0.5, y_max: float = 0.5, n_y: int = 201,
                      x_tip_override: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Forward-eval PIDL α at a y-grid line at fixed x. Uses the existing FieldComputation
    network from fc and the input grid (we replace it with a 1D line of (x_target, y) points)."""
    sd = torch.load(str(ckpt_path), map_location='cpu', weights_only=True)
    fc.net.load_state_dict(sd); fc.net.eval()
    if x_tip_override is not None and getattr(fc, "sdf_ribbon_enabled", False):
        fc.x_tip = float(x_tip_override)
    y_grid = np.linspace(y_min, y_max, n_y)
    xy = torch.tensor(np.stack([np.full(n_y, x_target), y_grid], axis=1), dtype=torch.float32)
    with torch.no_grad():
        _, _, alpha = fc.fieldCalculation(xy)
    a = alpha.detach().cpu().numpy().flatten()
    return y_grid, a


def build_fc(archive: Path, sdf_ribbon: dict | None, device, umax: float):
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "source"))
    _saved = sys.argv
    sys.argv = ["fwhm", "8", "400", "1", "TrainableReLU", "1.0"]
    from config import (PFF_model_dict, mat_prop_dict, network_dict, numr_dict,
                        crack_dict, domain_extrema, loading_angle)
    sys.argv = _saved
    from construct_model import construct_model
    from input_data_from_mesh import prep_input_data
    from field_computation import FieldComputation
    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
        sdf_ribbon_dict=sdf_ribbon)
    inp, T_conn, _, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict,
        mesh_file=str(HERE / "meshed_geom2.msh"), device=device)
    fc_kw = dict(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([umax], device=device),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        l0=mat_prop_dict["l0"])
    if sdf_ribbon is not None:
        fc_kw["sdf_ribbon_dict"] = sdf_ribbon
    fc = FieldComputation(**fc_kw)
    return fc, inp, T_conn


def main(umax: float):
    cfg = UMAX_CFG[umax]
    device = torch.device("cpu")
    print(f"=== FWHM analysis at Umax={umax} ===")
    print(f"FEM snapshots: {cfg['snap_cycles']}")

    base_path = find_archive(cfg["baseline_rel"])
    sdf_path  = find_archive(cfg["sdf_rel"])
    print(f"baseline: {base_path}")
    print(f"SDF:      {sdf_path}")

    sdf_ribbon = dict(enable=True, epsilon=1e-3, apply_to="uv_only")
    fc_base, _, _ = build_fc(base_path, None, device, umax)
    fc_sdf,  _, _ = build_fc(sdf_path,  sdf_ribbon, device, umax)

    # SDF x_tip per cycle (for ribbon ansatz)
    sdf_xtip_arr = None
    for fn in ("x_tip_psi_vs_cycle.npy", "x_tip_alpha_vs_cycle.npy", "x_tip_vs_cycle.npy"):
        p = sdf_path / "best_models" / fn
        if p.exists():
            sdf_xtip_arr = np.load(p); break

    # FEM mesh
    mesh_geom = sio.loadmat(FEM_BASE / "psi_snapshots_for_agent" / "mesh_geometry.mat")
    centroids = mesh_geom['element_centroids']

    # For each FEM snapshot cycle, pick two x positions: tip-region and wake-region
    rows = []          # for table output
    profiles = {}      # for plotting: profiles[(cycle, x_label)] = dict(y, d_fem, a_base, a_sdf)

    for c in cfg["snap_cycles"]:
        fpath = FEM_BASE / "psi_snapshots_for_agent" / f"u{cfg['fem_csv_tag']}_cycle_{c:04d}.mat"
        if not fpath.is_file():
            print(f"  c{c}: FEM snapshot missing, skip"); continue
        m = sio.loadmat(fpath)
        d_elem = m['d_elem'].squeeze()

        # FEM tip-x = max x with d > 0.5 along y=0 strip
        y0_mask = np.abs(centroids[:, 1]) < 0.005
        if y0_mask.any():
            d_y0 = d_elem[y0_mask]
            x_y0 = centroids[y0_mask, 0]
            big = d_y0 > 0.5
            x_tip_fem = float(x_y0[big].max()) if big.any() else -0.5
        else:
            x_tip_fem = 0.0
        # PIDL x_tip (from saved tracker)
        x_tip_pidl = float(sdf_xtip_arr[c]) if (sdf_xtip_arr is not None and c < len(sdf_xtip_arr)) else 0.0

        # Two x positions: wake (-0.2) and tip-region (FEM tip x)
        # Use wake = x slightly behind PIDL tip, tip = FEM tip
        x_pos = {
            "wake": min(-0.1, x_tip_fem - 0.15) if x_tip_fem > -0.1 else -0.3,
            "tip":  x_tip_fem,
        }

        for lbl, x_t in x_pos.items():
            y_fem, d_fem = fem_profile_at_x(d_elem, centroids, x_t)
            # PIDL baseline (no SDF)
            ckpt_b = base_path / "best_models" / f"trained_1NN_{c}.pt"
            ckpt_s = sdf_path  / "best_models" / f"trained_1NN_{c}.pt"
            y_b, a_b = (None, None)
            y_s, a_s = (None, None)
            if ckpt_b.is_file():
                y_b, a_b = pidl_profile_at_x(fc_base, None, x_t, ckpt_b)
            if ckpt_s.is_file():
                y_s, a_s = pidl_profile_at_x(fc_sdf, None, x_t, ckpt_s,
                                             x_tip_override=x_tip_pidl)
            # widths
            def stats(y, f):
                if y is None or len(y) == 0: return (float("nan"),)*3
                return fwhm_and_effwidth(y, f)
            fw_f, ew_f, pk_f = stats(y_fem, d_fem)
            fw_b, ew_b, pk_b = stats(y_b, a_b)
            fw_s, ew_s, pk_s = stats(y_s, a_s)
            rows.append(dict(c=c, x_label=lbl, x=x_t,
                             fwhm_fem=fw_f, eff_fem=ew_f, peak_fem=pk_f,
                             fwhm_base=fw_b, eff_base=ew_b, peak_base=pk_b,
                             fwhm_sdf=fw_s, eff_sdf=ew_s, peak_sdf=pk_s))
            profiles[(c, lbl)] = dict(x=x_t, y_fem=y_fem, d_fem=d_fem,
                                      y_b=y_b, a_b=a_b, y_s=y_s, a_s=a_s)

    # ─── print table ─────────────────────────────────────────────────────────
    print(f"\n{'cycle':>6} {'where':>5} {'x':>7} | "
          f"{'FWHM_fem':>9} {'FWHM_base':>10} {'FWHM_sdf':>9} | "
          f"{'eff_fem':>8} {'eff_base':>9} {'eff_sdf':>8} | "
          f"{'pk_fem':>7} {'pk_base':>8} {'pk_sdf':>7}")
    print("-" * 130)
    for r in rows:
        print(f"{r['c']:6d} {r['x_label']:>5s} {r['x']:>7.3f} | "
              f"{r['fwhm_fem']:9.4f} {r['fwhm_base']:10.4f} {r['fwhm_sdf']:9.4f} | "
              f"{r['eff_fem']:8.4f} {r['eff_base']:9.4f} {r['eff_sdf']:8.4f} | "
              f"{r['peak_fem']:7.3f} {r['peak_base']:8.3f} {r['peak_sdf']:7.3f}")

    # ─── plot d(y) profiles + width-vs-cycle ─────────────────────────────────
    n_c = len(cfg["snap_cycles"])
    fig, axes = plt.subplots(2, n_c, figsize=(3.6 * n_c, 6.5), sharex=True)
    if n_c == 1:
        axes = axes.reshape(2, 1)
    for j, c in enumerate(cfg["snap_cycles"]):
        for row, lbl in enumerate(["wake", "tip"]):
            ax = axes[row, j]
            key = (c, lbl)
            if key not in profiles: continue
            pr = profiles[key]
            if len(pr['y_fem']):
                ax.plot(pr['y_fem'], pr['d_fem'], "r-", lw=2, label="FEM d")
            if pr['y_b'] is not None:
                ax.plot(pr['y_b'], pr['a_b'], "k-", lw=1.4, label="baseline α")
            if pr['y_s'] is not None:
                ax.plot(pr['y_s'], pr['a_s'], "-", color="tab:blue", lw=1.4, label="SDF α")
            ax.axhline(0.5, color="gray", ls=":", lw=0.7, alpha=0.6)
            ax.set_title(f"c{c} · {lbl} (x={pr['x']:+.3f})", fontsize=9)
            ax.set_xlim(-0.5, 0.5)
            ax.set_ylim(-0.05, 1.1)
            ax.grid(alpha=0.3)
            if row == 0 and j == n_c - 1:
                ax.legend(fontsize=7, loc="upper right")
            if row == 1: ax.set_xlabel("y")
            if j == 0: ax.set_ylabel(f"{lbl}\nd(y) or α(y)")

    fig.suptitle(f"FWHM Layer-2 audit · Umax = {umax} · {{wake, tip-region}} transverse profiles\n"
                 f"GATE: 'FEM diffuse process zone' framing valid only if FEM FWHM ≥ 1.5× PIDL FWHM",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    out_dir = HERE.parent / "references_local" / "sdf_ribbon_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / f"fwhm_band_audit_u{int(umax*100):02d}.png"
    fig.savefig(out_png, dpi=140)
    print(f"\nsaved: {out_png}")

    # ─── summary verdict ─────────────────────────────────────────────────────
    print(f"\n=== Verdict (Umax={umax}) ===")
    print("Per cycle ratio FEM_FWHM / PIDL_FWHM_baseline (at tip-region):")
    for r in rows:
        if r['x_label'] == 'tip' and r['fwhm_base'] > 1e-6:
            ratio_b = r['fwhm_fem'] / r['fwhm_base']
            ratio_s = r['fwhm_fem'] / r['fwhm_sdf'] if r['fwhm_sdf'] > 1e-6 else float("nan")
            if not np.isfinite(ratio_b):
                print(f"  c{r['c']:3d} tip: FEM/base=nan   FEM/SDF=nan    no FEM FWHM at this x, skip")
                continue
            verdict = "FEM wider ✓" if ratio_b >= 1.5 else ("similar" if 0.67 < ratio_b < 1.5 else "PIDL wider !")
            print(f"  c{r['c']:3d} tip: FEM/base={ratio_b:.2f}×  FEM/SDF={ratio_s:.2f}×   {verdict}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("umax", type=float, choices=sorted(UMAX_CFG.keys()))
    args = p.parse_args()
    main(args.umax)
