#!/usr/bin/env python3
"""plot_Rbc_residual_field.py — spatial V7 boundary-residual field along the
traction-free right edge x=+0.5 (and optionally left edge x=-0.5), for
multiple PIDL methods at u=0.12.

V7 (Mandal et al.) is the scalar |σ_xx| residual at x=+0.5 normalized by σ_ref.
F2 already shows the scalar per method. This figure decomposes that scalar in
space: σ_xx(y) and σ_xy(y) sampled near the right edge.

Sampling: take element centroids with x_centroid > x_thresh (default 0.45),
sort by y, plot. Uses the same FEM gradient via compute_energy.gradients.
σ = (λδ_ij ε_kk + 2μ ε_ij) * g(α) (effective stress with degradation).

Usage:
    python plot_Rbc_residual_field.py                       # default 6 methods, last cycle
    python plot_Rbc_residual_field.py --cycle 80            # at specific cycle
    python plot_Rbc_residual_field.py --x-thresh 0.40       # widen sampling band
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent / "source"))

from render_late_cycles import parse_settings, detect_exact_bc, detect_fourier
from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from compute_energy import gradients

ROOT_PREFIX = (
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N300_R0.0_Umax0.12")

METHODS = [
    ("baseline",    f"{ROOT_PREFIX}",                                              "#0B4992", "-"),
    ("Williams v4", f"{ROOT_PREFIX}_williams_std_v4_cycle87_Nf77_real_fracture",   "#1F77B4", "--"),
    ("Fourier v1",  f"{ROOT_PREFIX}_fourier_nf16_sig1.0_v1_cycle94_Nf84_real_fracture", "#9467BD", "-"),
    ("Enriched v1", f"{ROOT_PREFIX}_enriched_ansatz_modeI_v1_cycle94_Nf84_real_fracture", "#FF7F0E", "-"),
    ("psiHack",     f"{ROOT_PREFIX}_psiHack_m1000_r0.02_cycle91_Nf81_real_fracture", "#8C564B", "--"),
    ("Oracle z0.02", f"{ROOT_PREFIX}_oracle_zone0.02",                             "#0B7A0B", "-"),
    ("spAlphaT b0.8", f"{ROOT_PREFIX}_spAlphaT_b0.8_r0.03_cycle90_Nf80_real_fracture", "#2CA02C", "--"),
    ("MIT8 K5",     f"{ROOT_PREFIX}_mit8_K5_lam1.0",                               "#7F7F7F", "-"),
]


def last_cycle(archive: Path) -> int | None:
    best = archive / "best_models"
    if not best.is_dir():
        return None
    cycs = []
    for p in best.glob("trained_1NN_*.pt"):
        s = p.stem.rsplit("_", 1)[-1]
        try:
            cycs.append(int(s))
        except ValueError:
            continue
    return max(cycs) if cycs else None


def degradation(alpha, model="AT1"):
    """g(α) for AT1: (1-α)² (clip to [0,1])."""
    a = torch.clamp(alpha, 0.0, 1.0)
    return (1.0 - a) ** 2


def sigma_at_edge(archive: Path, cycle: int, x_thresh: float, device="cpu"):
    """Load trained model at cycle, compute σ_xx and σ_xy on elements whose
    centroid has x > x_thresh. Returns (y_sorted, sxx_sorted, sxy_sorted).
    """
    settings = parse_settings(archive / "model_settings.txt")
    exact_bc_dict = detect_exact_bc(archive)
    fourier_dict = detect_fourier(archive)
    disp_max = float(settings.get("disp_max", 0.12))

    PFF_model_dict = {"PFF_model": "AT1", "se_split": "volumetric", "tol_ir": 5e-3}
    mat_prop_dict = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
    network_dict = {"hidden_layers": 8, "neurons": 400, "activation": "TrainableReLU",
                    "init_coeff": float(settings.get("coeff", 1.0)),
                    "seed": int(settings.get("seed", 1)), "compile": False}
    numr_dict = {"alpha_constraint": "nonsmooth", "gradient_type": "numerical"}

    domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
    loading_angle = torch.tensor([np.pi / 2])
    crack_dict = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
    mesh_file = str(SCRIPT_DIR / "meshed_geom2.msh")

    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
        williams_dict=None, fourier_dict=fourier_dict)
    inp, T_conn, area_T, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict, mesh_file=mesh_file, device=device)
    fc = FieldComputation(net=network, domain_extrema=domain_extrema,
                          lmbda=torch.tensor([disp_max], device=device),
                          theta=loading_angle,
                          alpha_constraint=numr_dict["alpha_constraint"],
                          l0=mat_prop_dict["l0"],
                          exact_bc_dict=exact_bc_dict)
    for attr in ("net", "domain_extrema", "theta"):
        setattr(fc, attr, getattr(fc, attr).to(device))

    ckpt = archive / "best_models" / f"trained_1NN_{cycle}.pt"
    sd = torch.load(str(ckpt), map_location=device, weights_only=True)
    fc.net.load_state_dict(sd)
    fc.net.eval()

    with torch.no_grad():
        u, v, alpha = fc.fieldCalculation(inp)
        e11, e22, e12, _, _ = gradients(inp, u, v, alpha, area_T, T_conn)
        alpha_e = (alpha[T_conn[:, 0]] + alpha[T_conn[:, 1]] + alpha[T_conn[:, 2]]) / 3.0
        g = degradation(alpha_e)
        lam, mu = matprop.mat_lmbda, matprop.mat_mu
        sxx = g * (lam * (e11 + e22) + 2 * mu * e11)
        sxy = g * (2 * mu * e12)

    Tnp = T_conn.detach().cpu().numpy()
    pts = inp.detach().cpu().numpy()
    cx = pts[Tnp].mean(axis=1)[:, 0]
    cy = pts[Tnp].mean(axis=1)[:, 1]

    mask = cx > x_thresh
    sxx_np = sxx.detach().cpu().numpy()[mask]
    sxy_np = sxy.detach().cpu().numpy()[mask]
    y_np = cy[mask]
    order = np.argsort(y_np)
    return y_np[order], sxx_np[order], sxy_np[order], disp_max


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", type=int, default=None,
                    help="Cycle to extract (default: last available per archive)")
    ap.add_argument("--x-thresh", type=float, default=0.45,
                    help="Centroid x-threshold for 'near right edge' (default 0.45)")
    ap.add_argument("--out", type=Path, default=SCRIPT_DIR / "fig_l_Rbc_residual_multimethod.pdf")
    args = ap.parse_args()

    sigma_ref = None  # use E * u_max / L = 1 * 0.12 / 1 = 0.12 below

    fig, axes = plt.subplots(2, 1, figsize=(9, 7.5), sharex=True)
    ax_xx, ax_xy = axes

    for name, arch_name, color, ls in METHODS:
        archive = SCRIPT_DIR / arch_name
        if not archive.is_dir():
            print(f"[skip] {name}: archive missing")
            continue
        cyc = args.cycle if args.cycle is not None else last_cycle(archive)
        if cyc is None or not (archive / "best_models" / f"trained_1NN_{cyc}.pt").is_file():
            print(f"[skip] {name}: no checkpoint at c={cyc}")
            continue
        try:
            y, sxx, sxy, disp_max = sigma_at_edge(archive, cyc, args.x_thresh)
        except Exception as exc:
            print(f"[skip] {name}: {exc}")
            continue
        if sigma_ref is None:
            sigma_ref = 1.0 * disp_max / 1.0    # E · ε_applied
            print(f"[setup] σ_ref = E·u_max/L = {sigma_ref:.3f}")

        rms_xx = float(np.sqrt(np.mean(sxx ** 2)) / sigma_ref)
        rms_xy = float(np.sqrt(np.mean(sxy ** 2)) / sigma_ref)
        ax_xx.plot(y, sxx / sigma_ref, ls, color=color, lw=1.4, alpha=0.85,
                   label=f"{name} (rms={rms_xx*100:.1f}%, c={cyc})")
        ax_xy.plot(y, sxy / sigma_ref, ls, color=color, lw=1.4, alpha=0.85,
                   label=f"{name} (rms={rms_xy*100:.1f}%)")
        print(f"[ok] {name} c={cyc}: σ_xx rms={rms_xx*100:.2f}%  σ_xy rms={rms_xy*100:.2f}%")

    for ax, lab, title in [
        (ax_xx, r"$\sigma_{xx}/\sigma_{\mathrm{ref}}$",
         "(a) σ_xx along right edge (x>0.45), traction-free target = 0"),
        (ax_xy, r"$\sigma_{xy}/\sigma_{\mathrm{ref}}$",
         "(b) σ_xy along right edge, traction-free target = 0"),
    ]:
        ax.axhline(0.0, color="k", lw=0.7)
        ax.axhspan(-0.002, 0.002, color="green", alpha=0.10, label="FEM ref ±0.2%")
        ax.set_ylabel(lab)
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.3)
    ax_xy.set_xlabel("y (along right edge)")
    ax_xx.legend(fontsize=7, ncol=2, loc="best")

    plt.tight_layout()
    plt.savefig(args.out, dpi=150)
    plt.savefig(args.out.with_suffix(".png"), dpi=150)
    plt.close()
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()
