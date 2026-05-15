#!/usr/bin/env python3
"""run_a0_smoke.py — A0 diagnostic smoke for POU local-patch / domain decomposition.

Protocol locked at notes/03_A0_protocol.md. This is a kill experiment.

What it does:
  1. Loads the SENT coarse mesh (override absolute path so we don't depend on cwd).
  2. Builds a POU model: bulk_net + tip_net combined via fixed sigmoid window
     centered at the known initial crack tip (0, 0).
  3. Builds a baseline single-net with parameter count matched to bulk+tip.
  4. Trains both with the same Deep Ritz elastic loss at lmbda = Umax (default 0.12),
     SAME #iterations, SAME optimizer, SAME seed, SAME mesh, SAME hist_alpha.
  5. Computes the three pre-registered gates and writes a JSON report + plots.

Single-cycle elastic only. No fatigue. No history accumulation. No exact_bc /
Williams / Fourier / ansatz / symmetry stacked.

Usage:
    python run_a0_smoke.py [--umax 0.12] [--seed 1] [--epochs 5000]
                           [--bulk-neurons 100] [--bulk-layers 6]
                           [--baseline-neurons 143] [--r-patch 0.10]
                           [--sigma-window 0.02] [--out-name a0_default]

The runner does NOT touch config.py — it overrides what it needs at runtime.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))                   # for `import config`
sys.path.insert(0, str(ROOT / "source"))        # for source modules

# --- imports from project ----------------------------------------------------
from network import NeuralNet, init_xavier
from pff_model import PFFModel
from material_properties import MaterialProperties
from field_computation import FieldComputation
from utils import parse_mesh, hist_alpha_init
from compute_energy import (compute_energy, get_psi_plus_per_elem, stress,
                             gradients, strain_energy_with_split)
from pou_decomposition import TwoNetPOU, region_masks, sigmoid_window_tip, count_params


# =============================================================================
# Helpers (mirrors fit.py:_compute_psi_raw_per_elem and the autodiff side-stress
# pattern from fit.py:_compute_side_traction_penalty, but written here so the
# runner is self-contained.)
# =============================================================================

def compute_psi_raw_per_elem(inp, u, v, alpha, matprop, pffmodel, area_T, T_conn):
    """UNDEGRADED ψ⁺_0 per element. Gate 2 must use this, not the g(α)-degraded
    `get_psi_plus_per_elem` from compute_energy.py — otherwise sharper-α (which is
    what we want POU to deliver) would shrink g(α)·ψ⁺_0 and Gate 2 could fail
    for the wrong reason.
    """
    s11, s22, s12, _, _ = gradients(inp, u, v, alpha, area_T, T_conn)
    if T_conn is None:
        alpha_elem = alpha
    else:
        alpha_elem = (alpha[T_conn[:, 0]] + alpha[T_conn[:, 1]]
                      + alpha[T_conn[:, 2]]) / 3
    _, E_el_p = strain_energy_with_split(s11, s22, s12, alpha_elem,
                                          matprop, pffmodel)
    return E_el_p.detach()


def boundary_traction_rms(field_comp, matprop, n_bdy_pts=51):
    """Free-edge traction RMS at x = ±0.5 via autodiff at exact boundary points.

    Mirrors fit.py:_compute_side_traction_penalty so V7 is comparable to the
    project's existing convention. Returns (rms_xx, rms_xy) over both side edges.
    """
    device = next(field_comp.net.parameters()).device
    y_vals = torch.linspace(-0.495, 0.495, n_bdy_pts, dtype=torch.float32, device=device)
    x_left  = torch.full((n_bdy_pts,), -0.5, dtype=torch.float32, device=device)
    x_right = torch.full((n_bdy_pts,),  0.5, dtype=torch.float32, device=device)
    pts_left  = torch.stack([x_left,  y_vals], dim=1)
    pts_right = torch.stack([x_right, y_vals], dim=1)
    xy_bdy = torch.cat([pts_left, pts_right], dim=0).requires_grad_(True)

    u_b, v_b, _ = field_comp.fieldCalculation(xy_bdy)
    grads_u = torch.autograd.grad(u_b.sum(), xy_bdy, create_graph=False, retain_graph=True)[0]
    grads_v = torch.autograd.grad(v_b.sum(), xy_bdy, create_graph=False)[0]
    du_dx, du_dy = grads_u[:, 0], grads_u[:, 1]
    dv_dx, dv_dy = grads_v[:, 0], grads_v[:, 1]

    lmbda = matprop.mat_lmbda
    mu    = matprop.mat_mu
    eps11 = du_dx
    eps22 = dv_dy
    eps12 = 0.5 * (du_dy + dv_dx)
    sig_xx = lmbda * (eps11 + eps22) + 2.0 * mu * eps11
    sig_xy = 2.0 * mu * eps12

    rms_xx = float(sig_xx.pow(2).mean().sqrt().detach())
    rms_xy = float(sig_xy.pow(2).mean().sqrt().detach())
    return rms_xx, rms_xy


# Default mesh location (parent repo's examples folder, NOT the worktree).
DEFAULT_MESH_PATH = (
    "/Users/wenxiaofang/phase-field-fracture-with-pidl/examples/SENS_tensile/meshed_geom1.msh"
)


# =============================================================================
# Helpers
# =============================================================================

def build_neural_net(in_dim, out_dim, n_layers, neurons, activation, init_coeff, seed):
    torch.manual_seed(seed)
    net = NeuralNet(input_dimension=in_dim, output_dimension=out_dim,
                    n_hidden_layers=n_layers, neurons=neurons,
                    activation=activation, init_coeff=init_coeff)
    init_xavier(net)
    return net


def build_field_comp(net, domain_extrema, lmbda_val, theta, alpha_constraint,
                     l0, device):
    """FieldComputation with all stack flags OFF (A0 protocol)."""
    fc = FieldComputation(
        net=net,
        domain_extrema=domain_extrema,
        lmbda=torch.tensor([lmbda_val], device=device),
        theta=theta,
        alpha_constraint=alpha_constraint,
        williams_dict={"enable": False},
        ansatz_dict={"enable": False},
        l0=l0,
        symmetry_prior=False,
        exact_bc_dict={"enable": False},
    )
    fc.net = fc.net.to(device)
    fc.domain_extrema = fc.domain_extrema.to(device)
    fc.theta = fc.theta.to(device)
    return fc


def train_elastic(field_comp, inp, T_conn, area_T, hist_alpha, matprop, pffmodel,
                  n_epochs, weight_decay, log_every=200, tag=""):
    """Single-load-step elastic Deep Ritz minimization with RPROP.

    Why RPROP only: LBFGS uses `max_iter=20` per outer epoch (project default),
    so `--epochs 5000` would mean ~100k inner iterations vs RPROP's 5000 — not
    a comparable epoch budget for the gate experiment.
    """
    params = list(field_comp.net.parameters())
    opt = torch.optim.Rprop(params, lr=1e-5, step_sizes=(1e-10, 50))

    losses = []
    t0 = time.time()
    for epoch in range(n_epochs):
        opt.zero_grad()
        u, v, alpha = field_comp.fieldCalculation(inp)
        E_el, E_d, E_h = compute_energy(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
            f_fatigue=1.0, crack_tip_weights=None,
        )
        loss_var = torch.log10(E_el + E_d + E_h)
        loss_reg = 0.0
        if weight_decay != 0:
            for name, p in field_comp.net.named_parameters():
                if "weight" in name:
                    loss_reg = loss_reg + torch.sum(p ** 2)
        loss = loss_var + weight_decay * loss_reg
        loss.backward()
        opt.step()

        losses.append(float(loss.detach().cpu()))
        if (epoch + 1) % log_every == 0 or epoch == 0:
            print(f"  [{tag}] epoch {epoch+1:5d}/{n_epochs} | loss={losses[-1]:+.5f} | "
                  f"elapsed={time.time()-t0:.1f}s")

    return losses


# =============================================================================
# Gate evaluation
# =============================================================================

def evaluate_gates(field_comp_pou, field_comp_baseline, inp, T_conn, area_T,
                   hist_alpha, matprop, pffmodel,
                   center, r_patch, sigma_window):
    """Evaluate Gates 1, 2, 3. Returns dict of metrics + per-gate pass/fail."""

    masks = region_masks(inp, T_conn, center, r_patch, sigma_window,
                         tip_core_thr=0.9, overlap_low=0.1, overlap_high=0.9)
    n_tip_core = int(masks['tip_core'].sum())
    n_overlap  = int(masks['overlap'].sum())
    n_bulk     = int(masks['bulk'].sum())

    # ---- POU evaluation: raw ψ⁺_0 (Gate 2 fix per code red-team) ---------
    # Why raw not degraded: hist_alpha along the SENT pre-crack drives non-zero
    # α near the tip (irreversibility). If POU sharpens α (the *desired*
    # behavior), g(α) shrinks and degraded ψ⁺ would *decrease* even when raw
    # ψ⁺_0 is larger. Use raw ψ⁺_0 to test sharpening at the strain level.
    with torch.no_grad():
        u_p, v_p, a_p = field_comp_pou.fieldCalculation(inp)
        psi_pou = compute_psi_raw_per_elem(inp, u_p, v_p, a_p,
                                           matprop, pffmodel, area_T, T_conn)
    E_pos_elem_pou = (psi_pou * area_T).detach()
    E_pos_overlap_pou = float(E_pos_elem_pou[masks['overlap']].sum())
    E_pos_tip_pou    = float(E_pos_elem_pou[masks['tip_core']].sum())
    E_pos_bulk_pou   = float(E_pos_elem_pou[masks['bulk']].sum())
    R1 = E_pos_overlap_pou / max(E_pos_tip_pou, 1e-30)

    psi_max_in_tip_pou = float(psi_pou[masks['tip_core']].max()) if n_tip_core > 0 else float("nan")
    if n_tip_core >= 10:
        topk = torch.topk(psi_pou[masks['tip_core']], k=10).values
        psi_top10_mean_pou = float(topk.mean())
    else:
        psi_top10_mean_pou = float("nan")

    # ---- Baseline evaluation: raw ψ⁺_0 (same physical mask, same metric) -
    with torch.no_grad():
        u_b, v_b, a_b = field_comp_baseline.fieldCalculation(inp)
        psi_base = compute_psi_raw_per_elem(inp, u_b, v_b, a_b,
                                            matprop, pffmodel, area_T, T_conn)
    psi_max_in_tip_base = float(psi_base[masks['tip_core']].max()) if n_tip_core > 0 else float("nan")
    if n_tip_core >= 10:
        topk_b = torch.topk(psi_base[masks['tip_core']], k=10).values
        psi_top10_mean_base = float(topk_b.mean())
    else:
        psi_top10_mean_base = float("nan")

    # ---- V7: project-convention 51-pt boundary autodiff (Gate 3 fix) -----
    # Per-protocol "free-edge traction RMS at x = ±0.5 per existing project
    # convention" → mirror fit.py:_compute_side_traction_penalty: 51 pts on
    # each side edge (y ∈ (-0.495, 0.495)), σ_xx and σ_xy via autodiff at the
    # exact boundary location. Earlier centroid-strip variant could PASS
    # Gate 3 while still worsening true boundary traction.
    rms_xx_pou,  rms_xy_pou  = boundary_traction_rms(field_comp_pou,  matprop, n_bdy_pts=51)
    rms_xx_base, rms_xy_base = boundary_traction_rms(field_comp_baseline, matprop, n_bdy_pts=51)
    v7_pou  = float(np.sqrt(rms_xx_pou ** 2 + rms_xy_pou ** 2))
    v7_base = float(np.sqrt(rms_xx_base ** 2 + rms_xy_base ** 2))
    R3 = v7_pou / max(v7_base, 1e-30)

    # ---- Gate decisions ---------------------------------------------------
    valid_gate1 = n_tip_core >= 20
    gate1_pass  = (R1 <= 0.5) and valid_gate1
    gate2_pass  = (psi_max_in_tip_pou / max(psi_max_in_tip_base, 1e-30)) >= 1.20
    gate3_pass  = R3 <= 1.5

    if (not gate1_pass) and (not valid_gate1):
        gate1_decision = "INVALID (n_tip_core < 20 — redo geometry)"
    elif gate1_pass:
        gate1_decision = "PASS"
    else:
        gate1_decision = "FAIL"

    if not gate1_pass:
        overall = "NO-GO (Gate 1)"
    elif not gate2_pass:
        overall = "NO-GO (Gate 2)"
    elif gate3_pass:
        overall = "GO Phase A"
    else:
        overall = "FORK (Gate 3 fail — only viable as FBPINN + hard BC stacked)"

    return {
        "regions": {
            "n_tip_core": n_tip_core,
            "n_overlap":  n_overlap,
            "n_bulk":     n_bulk,
            "valid_gate1": valid_gate1,
        },
        "gate1": {
            "R1":               R1,
            "E_pos_overlap":    E_pos_overlap_pou,
            "E_pos_tip_core":   E_pos_tip_pou,
            "E_pos_bulk":       E_pos_bulk_pou,
            "threshold":        0.5,
            "decision":         gate1_decision,
        },
        "gate2": {
            "psi_max_tip_pou":   psi_max_in_tip_pou,
            "psi_max_tip_base":  psi_max_in_tip_base,
            "ratio":             psi_max_in_tip_pou / max(psi_max_in_tip_base, 1e-30),
            "psi_top10_mean_pou":  psi_top10_mean_pou,
            "psi_top10_mean_base": psi_top10_mean_base,
            "threshold":         1.20,
            "decision":          "PASS" if gate2_pass else "FAIL",
        },
        "gate3": {
            "v7_pou":         v7_pou,
            "v7_baseline":    v7_base,
            "rms_xx_pou":     rms_xx_pou,
            "rms_xy_pou":     rms_xy_pou,
            "rms_xx_baseline": rms_xx_base,
            "rms_xy_baseline": rms_xy_base,
            "R3":             R3,
            "threshold":      1.5,
            "decision":       "PASS" if gate3_pass else "FAIL",
        },
        "overall": overall,
    }


# =============================================================================
# Plots
# =============================================================================

def save_plots(out_dir, inp, T_conn, field_comp_pou, field_comp_baseline,
               center, r_patch, sigma_window):
    inp_np = inp.detach().cpu().numpy()
    T_np = T_conn.detach().cpu().numpy()
    triang = mtri.Triangulation(inp_np[:, 0], inp_np[:, 1], T_np)

    with torch.no_grad():
        u_p, v_p, a_p = field_comp_pou.fieldCalculation(inp)
        u_b, v_b, a_b = field_comp_baseline.fieldCalculation(inp)
        # ψ⁺ at element centroids → for tripcolor we need node values; use NN α at nodes
        psi_p_node = a_p.detach().cpu().numpy()  # use α as proxy field for visual
        psi_b_node = a_b.detach().cpu().numpy()
        # Window weight at nodes
        w_tip_node = sigmoid_window_tip(inp, field_comp_pou.net.center if hasattr(field_comp_pou.net, 'center') else center,
                                        r_patch, sigma_window).detach().cpu().numpy()

    # 1) α field heatmaps side-by-side
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, vals, title in [(axes[0], psi_p_node, "POU α"),
                            (axes[1], psi_b_node, "baseline α")]:
        tpc = ax.tripcolor(triang, vals, shading="gouraud",
                            vmin=0, vmax=max(0.05, float(np.max([psi_p_node, psi_b_node]))),
                            cmap="plasma")
        ax.set_aspect("equal")
        ax.set_title(title)
        plt.colorbar(tpc, ax=ax)
    fig.tight_layout()
    fig.savefig(out_dir / "alpha_compare.png", dpi=150)
    plt.close(fig)

    # 2) Window weight overlay
    fig, ax = plt.subplots(figsize=(5, 4))
    tpc = ax.tripcolor(triang, w_tip_node, shading="gouraud",
                       vmin=0, vmax=1, cmap="viridis")
    # overlay overlap region outline (centroids 0.1<w<0.9 marked as scatter)
    centroids = inp[T_conn].mean(dim=1).detach().cpu().numpy()
    wc = sigmoid_window_tip(inp[T_conn].mean(dim=1).to(inp.device),
                            center if torch.is_tensor(center) else torch.tensor(center, dtype=torch.float32, device=inp.device),
                            r_patch, sigma_window).detach().cpu().numpy()
    overlap_idx = (wc > 0.1) & (wc < 0.9)
    tip_idx = wc >= 0.9
    ax.scatter(centroids[overlap_idx, 0], centroids[overlap_idx, 1], s=2, c="white", label="overlap centroid")
    ax.scatter(centroids[tip_idx, 0], centroids[tip_idx, 1], s=2, c="red", label="tip-core centroid")
    ax.set_aspect("equal")
    ax.set_title(f"w_tip(x,y) — center={tuple(center)}, r={r_patch}, σ={sigma_window}")
    ax.legend(loc="upper right", fontsize=7)
    plt.colorbar(tpc, ax=ax)
    fig.tight_layout()
    fig.savefig(out_dir / "window_overlay.png", dpi=150)
    plt.close(fig)


# =============================================================================
# Main
# =============================================================================

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--umax",            type=float, default=0.12)
    p.add_argument("--seed",            type=int,   default=1)
    p.add_argument("--epochs",          type=int,   default=5000)
    p.add_argument("--bulk-neurons",    type=int,   default=100)
    p.add_argument("--bulk-layers",     type=int,   default=6)
    p.add_argument("--baseline-neurons", type=int,  default=142,
                   help="matched parameter count for default bulk=tip=(L=6,N=100); "
                        "L=6,N=142 → 102,391 params, POU=102,218, mismatch 0.17%")
    p.add_argument("--baseline-layers", type=int,   default=6)
    p.add_argument("--activation",      type=str,   default="TrainableReLU")
    p.add_argument("--init-coeff",      type=float, default=1.0)
    p.add_argument("--r-patch",         type=float, default=0.10)
    p.add_argument("--sigma-window",    type=float, default=0.02)
    p.add_argument("--x-tip",           type=float, default=0.0)
    p.add_argument("--y-tip",           type=float, default=0.0)
    p.add_argument("--mesh",            type=str,   default=DEFAULT_MESH_PATH)
    p.add_argument("--out-name",        type=str,   default="a0_default")
    p.add_argument("--device",          type=str,   default="auto",
                   choices=["auto", "cpu", "cuda", "mps"])
    args = p.parse_args()

    # ---- device ----------------------------------------------------------
    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    print(f"[A0] device={device}")

    # ---- output dir ------------------------------------------------------
    out_dir = HERE.parent / "notes" / "a0_runs" / args.out_name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[A0] out_dir={out_dir}")

    # ---- mesh + initial alpha -------------------------------------------
    mesh_file = Path(args.mesh)
    if not mesh_file.exists():
        raise FileNotFoundError(f"mesh file not found: {mesh_file}")
    print(f"[A0] mesh={mesh_file}")

    # use 'numerical' gradient mode (FEM shape functions) — matches project default
    X, Y, T_conn_np, area_T_np = parse_mesh(filename=str(mesh_file),
                                             gradient_type="numerical")
    inp = torch.from_numpy(np.column_stack([X, Y])).to(torch.float).to(device)
    T_conn = torch.from_numpy(T_conn_np).to(torch.long).to(device)
    area_T = torch.from_numpy(area_T_np).to(torch.float).to(device)
    print(f"[A0] mesh nodes={inp.shape[0]} elements={T_conn.shape[0]}")

    # ---- material + pff model -------------------------------------------
    # Mirror SENS_tensile/config.py defaults (toy units E=1, ν=0.3, w1=1, l0=0.01,
    # AT1, volumetric split, nonsmooth alpha constraint).
    matprop = MaterialProperties(
        mat_E=torch.tensor(1.0,  device=device),
        mat_nu=torch.tensor(0.3, device=device),
        w1=torch.tensor(1.0,    device=device),
        l0=torch.tensor(0.01,   device=device),
    )
    pffmodel = PFFModel(PFF_model="AT1", se_split="volumetric",
                        tol_ir=torch.tensor(5e-3, device=device))

    # initial pre-crack hist_alpha (SENT predefined crack: x ∈ [-0.5, 0], y = 0)
    crack_dict = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
    hist_alpha = hist_alpha_init(inp, matprop, pffmodel, crack_dict)

    # ---- domain + theta --------------------------------------------------
    domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
    theta = torch.tensor([np.pi / 2])
    alpha_constraint = "nonsmooth"
    l0 = float(matprop.l0.item())

    # ---- region pre-check (Gate 1 validity guard before training) -------
    center_tensor = torch.tensor([args.x_tip, args.y_tip], dtype=torch.float32, device=device)
    masks = region_masks(inp, T_conn, center_tensor, args.r_patch, args.sigma_window)
    print(f"[A0] regions: tip_core={int(masks['tip_core'].sum())} "
          f"overlap={int(masks['overlap'].sum())} bulk={int(masks['bulk'].sum())}")
    if int(masks['tip_core'].sum()) < 20:
        print(f"[A0] WARNING: n_tip_core < 20 — Gate 1 will be INVALID. "
              f"Increase --r-patch or --sigma-window.")

    # ---- POU model -------------------------------------------------------
    print("[A0] building POU model (bulk + tip)…")
    net_bulk = build_neural_net(in_dim=2, out_dim=3,
                                n_layers=args.bulk_layers, neurons=args.bulk_neurons,
                                activation=args.activation, init_coeff=args.init_coeff,
                                seed=args.seed)
    net_tip  = build_neural_net(in_dim=2, out_dim=3,
                                n_layers=args.bulk_layers, neurons=args.bulk_neurons,
                                activation=args.activation, init_coeff=args.init_coeff,
                                seed=args.seed + 1000)   # different seed so tip ≠ bulk at init
    pou_net = TwoNetPOU(net_bulk, net_tip,
                        x_tip=args.x_tip, y_tip=args.y_tip,
                        r_patch=args.r_patch, sigma_window=args.sigma_window).to(device)

    field_comp_pou = build_field_comp(pou_net, domain_extrema, args.umax, theta,
                                       alpha_constraint, l0, device)

    n_params_pou = count_params(pou_net)
    print(f"[A0] POU params = {n_params_pou:,} "
          f"(bulk={count_params(net_bulk):,} + tip={count_params(net_tip):,})")

    # ---- baseline (matched param count) ---------------------------------
    print("[A0] building baseline (matched params)…")
    net_base = build_neural_net(in_dim=2, out_dim=3,
                                 n_layers=args.baseline_layers, neurons=args.baseline_neurons,
                                 activation=args.activation, init_coeff=args.init_coeff,
                                 seed=args.seed)
    n_params_base = count_params(net_base)
    ratio = n_params_pou / n_params_base
    print(f"[A0] baseline params = {n_params_base:,}  "
          f"(POU/baseline ratio = {ratio:.4f})")
    # Per protocol: matched parameter count, POU must not get a free 2× capacity.
    assert abs(ratio - 1.0) < 0.02, (
        f"Parameter mismatch {abs(ratio-1)*100:.2f}% > 2% — adjust "
        f"--baseline-neurons (current default {142} → 102,391 for "
        f"bulk=tip=100). POU={n_params_pou} baseline={n_params_base}."
    )

    field_comp_base = build_field_comp(net_base, domain_extrema, args.umax, theta,
                                        alpha_constraint, l0, device)

    # ---- train both -----------------------------------------------------
    weight_decay = 1e-5
    print(f"\n[A0] training POU ({args.epochs} epochs, optimizer=RPROP)…")
    losses_pou = train_elastic(field_comp_pou, inp, T_conn, area_T, hist_alpha,
                                matprop, pffmodel,
                                n_epochs=args.epochs,
                                weight_decay=weight_decay, log_every=500, tag="POU")

    print(f"\n[A0] training baseline ({args.epochs} epochs, optimizer=RPROP)…")
    losses_base = train_elastic(field_comp_base, inp, T_conn, area_T, hist_alpha,
                                 matprop, pffmodel,
                                 n_epochs=args.epochs,
                                 weight_decay=weight_decay, log_every=500, tag="BASE")

    # ---- gates ----------------------------------------------------------
    print("\n[A0] evaluating gates…")
    report = evaluate_gates(field_comp_pou, field_comp_base, inp, T_conn, area_T,
                            hist_alpha, matprop, pffmodel,
                            center=center_tensor, r_patch=args.r_patch,
                            sigma_window=args.sigma_window)

    # bundle config and final losses into the report
    report["config"] = vars(args)
    report["params"] = {"pou": n_params_pou, "baseline": n_params_base,
                        "ratio_pou_over_base": n_params_pou / n_params_base}
    report["losses"] = {"pou_final": losses_pou[-1], "base_final": losses_base[-1],
                        "pou_first": losses_pou[0],  "base_first": losses_base[0]}

    # ---- save -----------------------------------------------------------
    with open(out_dir / "A0_run.json", "w") as f:
        json.dump(report, f, indent=2)
    np.save(out_dir / "loss_pou.npy", np.array(losses_pou))
    np.save(out_dir / "loss_base.npy", np.array(losses_base))

    print("\n[A0] saving plots…")
    save_plots(out_dir, inp, T_conn, field_comp_pou, field_comp_base,
               center=center_tensor, r_patch=args.r_patch,
               sigma_window=args.sigma_window)

    # ---- print summary --------------------------------------------------
    print("\n" + "=" * 72)
    print(f"  A0 RESULT: {report['overall']}")
    print("=" * 72)
    print(f"  Gate 1 (overlap energy):  {report['gate1']['decision']}  "
          f"R1={report['gate1']['R1']:.4f} (threshold ≤ 0.5)")
    print(f"  Gate 2 (tip sharpening):  {report['gate2']['decision']}  "
          f"ψ⁺_max ratio={report['gate2']['ratio']:.3f} (threshold ≥ 1.20)")
    print(f"  Gate 3 (V7 not worse):    {report['gate3']['decision']}  "
          f"R3={report['gate3']['R3']:.3f} (threshold ≤ 1.5)")
    print(f"  Region counts: tip_core={report['regions']['n_tip_core']} "
          f"overlap={report['regions']['n_overlap']} bulk={report['regions']['n_bulk']}")
    print(f"  Saved: {out_dir}/A0_run.json")


if __name__ == "__main__":
    main()
