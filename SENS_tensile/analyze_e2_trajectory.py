#!/usr/bin/env python3
"""
analyze_e2_trajectory.py — MIT-4 audit mitigation (Apr 25 2026)

Reload the Mac E2 archive (warm-start cycle 50, mult=1000, r_hack=0.02,
Umax=0.12 → ᾱ_max=457, N_f=81) and extract per-cycle TIP trajectories
of:

  ψ⁺_raw(tip, N)         = E_el_p at tip element (NN's native u-field, no hack)
  g(α)·ψ⁺_raw(tip, N)    = NN's native degraded ψ⁺ (no hack)
  ψ⁺_with_hack(tip, N)   = ψ⁺_raw · [1 + 999·exp(-(r/0.02)²)] (what fatigue saw)
  α_tip(N), ᾱ_tip(N)     = per-cycle damage + fatigue history at tip element

Question this answers (Auditor Hit 3): does PIDL's NATIVE u-field show
FEM-like endogenous ψ⁺_raw growth (redistribution physics), or does it
stay flat while only the hack provides accumulation (amplifier masks
attenuation; no redistribution)?

  - If ψ⁺_raw_native(tip, N) GROWS with N (matching FEM trajectory shape)
    → NN can express redistribution; E2 supports Claim 1.
  - If ψ⁺_raw_native(tip, N) is FLAT and only the hack grows the
    accumulated value → NN landscape destroys redistribution; E2 is
    "sufficient for ᾱ accumulation" but not "the sufficient condition
    an architectural fix needs."

Output:
  e2_trajectory_<archive>.npz    — per-cycle table of all quantities
  figures/audit/e2_vs_fem_mechanism.png  — 4-panel comparison vs FEM

Usage:
    cd "upload code/SENS_tensile"
    python analyze_e2_trajectory.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import torch
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# config.py reads sys.argv; pass dummy
_saved = sys.argv
sys.argv = ["analyze_e2_trajectory.py", "8", "400", "1", "TrainableReLU", "1.0"]
from config import (domain_extrema, loading_angle, network_dict, mat_prop_dict,
                    numr_dict, PFF_model_dict, crack_dict, fatigue_dict)
sys.argv = _saved

from field_computation import FieldComputation
from construct_model import construct_model
from compute_energy import gradients, strain_energy_with_split
from input_data_from_mesh import prep_input_data

DEVICE = torch.device("cpu")
FINE_MESH = str(HERE / "meshed_geom2.msh")

import os as _os
_ARCHIVE_NAME = _os.environ.get("MIT4_ARCHIVE",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1"
    "_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5"
    "_N300_R0.0_Umax0.12_psiHack_m1000_r0.02_cycle91_Nf81_real_fracture")
E2_ARCHIVE = HERE / _ARCHIVE_NAME

# E2 hack parameters (from training-time config)
HACK = {"x_tip": 0.0, "y_tip": 0.0, "r_hack": 0.02, "mult": 1000.0}


def compute_psi_raw_and_degraded(field_comp, inp, T_conn, area_T, matprop, pffmodel):
    """Run a forward pass and return (psi_raw, psi_degraded, alpha_elem, centroids).

    psi_raw[i]      = E_el_p at element i (undegraded ψ⁺_0)
    psi_degraded[i] = g(α_elem[i]) · psi_raw[i]
    alpha_elem[i]   = damage at element centroid (centroid average of nodal α)
    centroids       = element centroids (n_elem, 2)
    """
    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
        s11, s22, s12, _, _ = gradients(inp, u, v, alpha, area_T, T_conn)
        if T_conn is None:
            alpha_elem = alpha
        else:
            alpha_elem = (alpha[T_conn[:, 0]] + alpha[T_conn[:, 1]]
                          + alpha[T_conn[:, 2]]) / 3
        _, E_el_p = strain_energy_with_split(s11, s22, s12, alpha_elem,
                                             matprop, pffmodel)
        g_alpha, _ = pffmodel.Edegrade(alpha_elem)

    psi_raw = E_el_p.detach().cpu().numpy()
    g_arr = g_alpha.detach().cpu().numpy()
    psi_degraded = g_arr * psi_raw
    a_elem = alpha_elem.detach().cpu().numpy()

    cx = ((inp[T_conn[:, 0], 0] + inp[T_conn[:, 1], 0]
           + inp[T_conn[:, 2], 0]) / 3.0).cpu().numpy()
    cy = ((inp[T_conn[:, 0], 1] + inp[T_conn[:, 1], 1]
           + inp[T_conn[:, 2], 1]) / 3.0).cpu().numpy()
    centroids = np.stack([cx, cy], axis=1)
    return psi_raw, psi_degraded, a_elem, centroids, g_arr


def hack_scale(centroids, hack):
    r = np.sqrt((centroids[:, 0] - hack["x_tip"]) ** 2
                + (centroids[:, 1] - hack["y_tip"]) ** 2 + 1e-12)
    return 1.0 + (hack["mult"] - 1.0) * np.exp(-(r / hack["r_hack"]) ** 2)


def main():
    archive = E2_ARCHIVE
    if not archive.is_dir():
        print(f"ERROR: archive not found: {archive}")
        return 1
    best = archive / "best_models"
    # Use a coeff_<value>_<last-80-chars> tag to disambiguate coeff variants
    # that otherwise share the same N/Umax tail.
    _coeff = "coeff1"
    if "coeff_3.0" in archive.name:
        _coeff = "coeff3"
    elif "coeff_1.0" not in archive.name:
        _coeff = "coeffX"
    _tag = archive.name[-80:].replace("/", "_")
    out_npz = HERE / f"trajectory_{_coeff}_{_tag}.npz"

    # Build NN + field once (reused, just reload weights)
    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, DEVICE,
        williams_dict=None)
    inp, T_conn, area_T, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict, mesh_file=FINE_MESH,
        device=DEVICE)
    field_comp = FieldComputation(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.0], device=DEVICE), theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=None, l0=mat_prop_dict["l0"])
    # Extract Umax from archive name (handles Umax0.12, Umax0.08, etc.)
    _umax_str = archive.name.split("Umax")[-1].split("_")[0]
    _umax = float(_umax_str)
    print(f"  Loading amplitude (extracted from name): Umax={_umax}")
    field_comp.lmbda = torch.tensor(_umax, device=DEVICE)

    # Pre-compute centroid distance to tip (0, 0) once
    inp_np = inp.detach().cpu().numpy()
    T_np = T_conn.cpu().numpy() if isinstance(T_conn, torch.Tensor) else T_conn
    cx = (inp_np[T_np[:, 0], 0] + inp_np[T_np[:, 1], 0] + inp_np[T_np[:, 2], 0]) / 3.0
    cy = (inp_np[T_np[:, 0], 1] + inp_np[T_np[:, 1], 1] + inp_np[T_np[:, 2], 1]) / 3.0
    centroids_np = np.stack([cx, cy], axis=1)
    r_to_tip = np.sqrt(cx ** 2 + cy ** 2)
    hack_scale_arr = hack_scale(centroids_np, HACK)

    # ★ Apr 25 expert review G1: process-zone integrated metrics
    # ℓ₀ = mat_prop_dict['l0'] = 0.01
    L0 = 0.01
    area_T_np = area_T.detach().cpu().numpy() if hasattr(area_T, "detach") else np.asarray(area_T)
    pz_l0_mask  = r_to_tip <= L0       # process zone of radius ℓ₀
    pz_2l0_mask = r_to_tip <= 2 * L0   # 2·ℓ₀ for sensitivity
    print(f"  Process-zone: |B_ℓ₀(tip)|={pz_l0_mask.sum()} elems, "
          f"|B_2ℓ₀(tip)|={pz_2l0_mask.sum()} elems")

    # Load existing alpha_bar trajectory
    abar = np.load(best / "alpha_bar_vs_cycle.npy")  # may be (N,) or (N,2)
    print(f"alpha_bar_vs_cycle.npy shape: {abar.shape}")

    rows = []
    j = 0
    while True:
        ckpt = best / f"trained_1NN_{j}.pt"
        if not ckpt.is_file():
            break
        field_comp.net.load_state_dict(
            torch.load(str(ckpt), map_location=DEVICE, weights_only=True))
        field_comp.net.eval()

        psi_raw, psi_deg, a_elem, _, g_arr = compute_psi_raw_and_degraded(
            field_comp, inp, T_conn, area_T, matprop, pffmodel)

        # ---- Three candidate "tip" definitions ----
        # (A) max ψ⁺_raw — the most singular STRAIN point (often saturated α=1)
        i_A = int(np.argmax(psi_raw))
        # (B) max g(α)·ψ⁺_raw — the actual fatigue ACCUMULATOR driver (no hack)
        i_B = int(np.argmax(psi_deg))
        # (C) max g(α)·ψ⁺_raw · hack_scale — what fatigue saw DURING training
        psi_with_hack = psi_deg * hack_scale_arr
        i_C = int(np.argmax(psi_with_hack))

        # field stats
        psi_raw_max = float(psi_raw.max())
        psi_deg_max = float(psi_deg.max())
        psi_with_hack_max = float(psi_with_hack.max())

        # ★ Process-zone integrated metrics (G1)
        # ∫_{B_r(tip)} ψ⁺ dA, computed as sum over elements with centroid in B_r
        pz_l0_psi_raw_int = float((psi_raw[pz_l0_mask] * area_T_np[pz_l0_mask]).sum())
        pz_l0_psi_deg_int = float((psi_deg[pz_l0_mask] * area_T_np[pz_l0_mask]).sum())
        pz_2l0_psi_raw_int = float((psi_raw[pz_2l0_mask] * area_T_np[pz_2l0_mask]).sum())
        pz_2l0_psi_deg_int = float((psi_deg[pz_2l0_mask] * area_T_np[pz_2l0_mask]).sum())
        # Top-percentile metrics (more stable than max under mesh refinement)
        psi_raw_p99 = float(np.percentile(psi_raw, 99.0))   # top-1% threshold
        psi_raw_p95 = float(np.percentile(psi_raw, 95.0))   # top-5% threshold
        psi_deg_p99 = float(np.percentile(psi_deg, 99.0))
        psi_deg_p95 = float(np.percentile(psi_deg, 95.0))
        # Mean of top-1% / top-5% (more representative than threshold)
        idx_top1 = np.argpartition(psi_raw, -max(1, len(psi_raw) // 100))[-max(1, len(psi_raw) // 100):]
        idx_top5 = np.argpartition(psi_raw, -max(1, len(psi_raw) // 20))[-max(1, len(psi_raw) // 20):]
        psi_raw_top1pct_mean = float(psi_raw[idx_top1].mean())
        psi_raw_top5pct_mean = float(psi_raw[idx_top5].mean())
        psi_deg_top1pct_mean = float(psi_deg[idx_top1].mean())
        psi_deg_top5pct_mean = float(psi_deg[idx_top5].mean())

        # element nearest (0, 0)
        i_near = int(np.argmin(r_to_tip))

        rows.append([j,
                     # (A) max-ψ⁺_raw element
                     float(psi_raw[i_A]), float(psi_deg[i_A]),
                     float(a_elem[i_A]), float(g_arr[i_A]),
                     float(psi_with_hack[i_A]),
                     # (B) max-g·ψ⁺_raw element (fatigue driver, no hack)
                     float(psi_raw[i_B]), float(psi_deg[i_B]),
                     float(a_elem[i_B]), float(g_arr[i_B]),
                     float(psi_with_hack[i_B]),
                     # (C) max-with-hack element (fatigue driver, with hack)
                     float(psi_raw[i_C]), float(psi_deg[i_C]),
                     float(a_elem[i_C]), float(g_arr[i_C]),
                     float(psi_with_hack[i_C]),
                     # near-origin element
                     float(psi_raw[i_near]), float(psi_deg[i_near]),
                     float(a_elem[i_near]),
                     # field stats
                     psi_raw_max, psi_deg_max, psi_with_hack_max,
                     # element coords for tracking
                     float(centroids_np[i_A, 0]), float(centroids_np[i_A, 1]),
                     float(centroids_np[i_B, 0]), float(centroids_np[i_B, 1]),
                     float(centroids_np[i_C, 0]), float(centroids_np[i_C, 1]),
                     # ★ Process-zone metrics (G1) cols 28-39
                     pz_l0_psi_raw_int, pz_l0_psi_deg_int,
                     pz_2l0_psi_raw_int, pz_2l0_psi_deg_int,
                     psi_raw_p99, psi_raw_p95,
                     psi_deg_p99, psi_deg_p95,
                     psi_raw_top1pct_mean, psi_raw_top5pct_mean,
                     psi_deg_top1pct_mean, psi_deg_top5pct_mean])

        if j % 5 == 0 or j < 3 or j >= 80:
            print(f"  c{j:>3d}: "
                  f"A:ψ_raw={float(psi_raw[i_A]):8.2e} α={float(a_elem[i_A]):.3f} | "
                  f"B:ψ_raw={float(psi_raw[i_B]):7.2e} g·ψ={float(psi_deg[i_B]):7.2e} α={float(a_elem[i_B]):.3f} | "
                  f"C:hack·g·ψ={float(psi_with_hack[i_C]):7.2e} α={float(a_elem[i_C]):.3f}")
        j += 1

    arr = np.array(rows)
    cols = ["cycle",
            # (A) max-ψ⁺_raw element  cols 1-5
            "A_psi_raw", "A_psi_deg", "A_alpha", "A_g", "A_psi_hack",
            # (B) max-g·ψ⁺_raw element  cols 6-10
            "B_psi_raw", "B_psi_deg", "B_alpha", "B_g", "B_psi_hack",
            # (C) max-with-hack element  cols 11-15
            "C_psi_raw", "C_psi_deg", "C_alpha", "C_g", "C_psi_hack",
            # near origin  cols 16-18
            "near0_psi_raw", "near0_psi_deg", "near0_alpha",
            # field stats  cols 19-21
            "psi_raw_max", "psi_deg_max", "psi_with_hack_max",
            # coords of A/B/C  cols 22-27
            "A_x", "A_y", "B_x", "B_y", "C_x", "C_y",
            # ★ Process-zone metrics (G1) cols 28-39
            "pz_l0_psi_raw_int", "pz_l0_psi_deg_int",
            "pz_2l0_psi_raw_int", "pz_2l0_psi_deg_int",
            "psi_raw_p99", "psi_raw_p95",
            "psi_deg_p99", "psi_deg_p95",
            "psi_raw_top1pct_mean", "psi_raw_top5pct_mean",
            "psi_deg_top1pct_mean", "psi_deg_top5pct_mean"]
    np.savez(str(out_npz), data=arr, columns=np.array(cols),
             alpha_bar_vs_cycle=abar)
    print(f"\n→ saved {out_npz.name}  ({len(arr)} cycles)")

    # Plot 4-panel mechanism figure
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), tight_layout=True)
    cycles = arr[:, 0]
    # Column indices (0=cycle):
    # A_psi_raw=1, A_alpha=3, A_psi_hack=5
    # B_psi_raw=6, B_psi_deg=7, B_alpha=8, B_psi_hack=10
    # C_psi_raw=11, C_psi_deg=12, C_alpha=13, C_psi_hack=15

    # ── Panel 1: ψ⁺_raw at three "tip" elements
    ax = axes[0, 0]
    ax.semilogy(cycles, arr[:, 1], "b-o", label="(A) max ψ⁺_raw elem (saturated)",
                markersize=3)
    ax.semilogy(cycles, arr[:, 6], "g-s", label="(B) max g·ψ⁺_raw elem (no-hack driver)",
                markersize=3)
    ax.semilogy(cycles, arr[:, 11], "r-^", label="(C) max hack·g·ψ⁺_raw elem (with-hack driver)",
                markersize=3)
    ax.axhline(9750, color="k", linestyle="--", alpha=0.5,
               label="FEM ψ⁺_raw @ c50")
    ax.set_xlabel("cycle N"); ax.set_ylabel("ψ⁺_raw  (undegraded, log)")
    ax.set_title("ψ⁺_raw at three tip-element definitions vs FEM")
    ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)

    # ── Panel 2: degraded ψ⁺ (what fatigue accumulator integrated)
    ax = axes[0, 1]
    ax.semilogy(cycles, arr[:, 7], "g-s", label="(B) g·ψ⁺_raw at no-hack driver",
                markersize=3)
    ax.semilogy(cycles, arr[:, 15], "r-^", label="(C) hack·g·ψ⁺_raw at with-hack driver",
                markersize=3)
    ax.semilogy(cycles, arr[:, 21], "k:", alpha=0.7, label="field max(hack·g·ψ⁺_raw)")
    ax.set_xlabel("cycle N")
    ax.set_ylabel("integrand of Δᾱ  (log)")
    ax.set_title("What fatigue accumulator integrated each cycle")
    ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)

    # ── Panel 3: α at the three tip elements
    ax = axes[1, 0]
    ax.plot(cycles, arr[:, 3], "b-o", label="α at (A) max-ψ⁺_raw elem",
            markersize=3)
    ax.plot(cycles, arr[:, 8], "g-s", label="α at (B) no-hack driver",
            markersize=3)
    ax.plot(cycles, arr[:, 13], "r-^", label="α at (C) with-hack driver",
            markersize=3)
    ax.set_xlabel("cycle N"); ax.set_ylabel("α (damage)")
    ax.set_title("Damage at the three candidate tip elements")
    ax.legend(fontsize=8, loc="best"); ax.grid(alpha=0.3)
    ax.set_ylim([-0.05, 1.1])

    # ── Panel 4: ᾱ_max trajectory + driver-element x-tracking
    # alpha_bar_vs_cycle.npy schema: [ᾱ_max, ᾱ_mean, f_min] per cycle
    ax = axes[1, 1]
    if abar.ndim == 1:
        ax.plot(np.arange(len(abar)), abar, "m-o",
                label="ᾱ_max (whole field)", markersize=3)
    else:
        ax.plot(np.arange(len(abar)), abar[:, 0], "m-o",
                label="ᾱ_max (whole field)", markersize=3)
    ax.set_xlabel("cycle N"); ax.set_ylabel("ᾱ_max", color="m")
    ax.tick_params(axis="y", colors="m")
    ax.set_title("ᾱ_max accumulation + driver-element x-coord")
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3)
    # secondary axis: x-coords of B (no-hack) and C (with-hack) drivers
    ax2 = ax.twinx()
    ax2.plot(cycles, arr[:, 24], "g--", alpha=0.7,
             label="(B) no-hack driver x")
    ax2.plot(cycles, arr[:, 26], "r:", alpha=0.7,
             label="(C) hack-pinned driver x")
    ax2.set_ylabel("x-coord", color="dimgray")
    ax2.tick_params(axis="y", colors="dimgray")
    ax2.legend(fontsize=7, loc="lower right")

    out_dir = HERE / "figures" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_path = out_dir / "e2_vs_fem_mechanism.png"
    fig.savefig(fig_path, dpi=140)
    print(f"→ saved {fig_path}")

    # Print summary table at key cycles for the THREE tip definitions
    print("\n=== Summary table — three candidate tip-element definitions ===")
    print("cycle |  (B) max g·ψ⁺_raw           |  (C) max hack·g·ψ⁺_raw")
    print("      | ψ⁺_raw   g·ψ⁺   α   x       | ψ⁺_raw   hack·g·ψ⁺   α   x")
    for i in [0, 5, 10, 20, 30, 40, 50, 60, 70, 80, len(arr) - 1]:
        if i < len(arr):
            r = arr[i]
            print(f"  {int(r[0]):>3} | {r[6]:.2e}  {r[7]:.2e}  "
                  f"{r[8]:.2f}  {r[24]:+.3f} | "
                  f"{r[11]:.2e}  {r[15]:.2e}  {r[13]:.2f}  {r[26]:+.3f}")
    print(f"\nE2 archive: ᾱ_max growth driver = element (C) — its α stays "
          f"intermediate (not 1.0) so g(α)·ψ⁺ doesn't collapse, AND it's "
          f"close enough to (0,0) for hack to amplify. Its x-coord shows "
          f"whether the driver tracks an advancing tip or stays pinned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
