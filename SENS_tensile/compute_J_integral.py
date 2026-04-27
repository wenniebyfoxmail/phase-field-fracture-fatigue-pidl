#!/usr/bin/env python3
"""
compute_J_integral.py — A1 (Apr 27 2026, external review G2)

J-integral / K_I post-processing on existing PIDL checkpoints. Replaces the
"Kt proxy" used in earlier paper figures with a path-integral fracture
metric grounded in linear elastic fracture mechanics (LEFM).

J-integral on a circular contour Γ of radius r₀ around the crack tip at
origin (crack lies along x<0 side of x=0 axis):

  J = r₀ ∫₀^{2π} [W cos θ
                  − (σ₁₁ cos θ + σ₁₂ sin θ) ∂u/∂x
                  − (σ₁₂ cos θ + σ₂₂ sin θ) ∂v/∂x] dθ

where:
  W = ½ σ:ε   (strain energy density, computed from RAW strain — not
              degraded — because J-integral is a far-field quantity that
              ignores the crack band itself; degradation g(α) lives on
              elements where d→1, and r₀ is chosen to be OUTSIDE the
              saturated zone)
  ε from autograd of (u, v) wrt (x, y)
  σ via Hooke (plane stress; matches PIDL formulation)

K_I from J (plane stress):
  K_I = √(E · J)

Path-independence sanity check: run at r₀ ∈ {0.02, 0.04, 0.06} = {2ℓ₀, 4ℓ₀,
6ℓ₀}. For LEFM-valid regime, J should be similar at all three radii. Large
spread = either contour is inside saturated zone or contour is outside the
asymptotic K-dominated zone.

Output:
  <archive>/best_models/J_integral.npy        (cycles × cols)
  <archive>/best_models/J_integral.csv
  figures/audit/J_integral_method_comparison.png
  figures/audit/J_integral_path_independence.png

Cost reality: ~600 NN forwards per cycle (100 θ × 3 radii × 2 grad eval).
Per-cycle wall ~0.5 s on Mac CPU. For 50 cycles × 8 archives ≈ 3 min total.

FEM J-integral DEFERRED: FEM dump only stores element scalars (ψ⁺, ᾱ, f, d),
not σ_GP or u nodal. To compute FEM J-integral need additional Windows-FEM
export. Documented as G2-followup in shared_log.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# config.py reads sys.argv; pass dummy
_saved = sys.argv
sys.argv = ["J_integral", "8", "400", "1", "TrainableReLU", "1.0"]
from config import (domain_extrema, loading_angle, network_dict, mat_prop_dict,
                    numr_dict, PFF_model_dict, crack_dict)
sys.argv = _saved

from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation

DEVICE = torch.device("cpu")
FINE_MESH = str(HERE / "meshed_geom2.msh")
L0 = float(mat_prop_dict["l0"])
E_YOUNG = float(mat_prop_dict["mat_E"])
NU = float(mat_prop_dict["mat_nu"])
LMBDA = E_YOUNG * NU / ((1 + NU) * (1 - 2 * NU))   # Lamé λ (plane strain bulk-side)
MU = E_YOUNG / (2 * (1 + NU))                        # shear modulus

CONTOUR_RADII = [0.05, 0.08, 0.12]    # = 5ℓ₀, 8ℓ₀, 12ℓ₀
                                       # Chosen to sit OUTSIDE the phase-field
                                       # damage band (~2-3ℓ₀ wide). Inside the
                                       # damage band, NN displacement gradients
                                       # are not LEFM-asymptotic and σ via raw
                                       # Hooke is unphysical (g(α)≈0 zone).
N_THETA = 200                          # contour discretization (uniform in θ)
# Stop computing J past this fraction of the domain. Past this, the contour
# would clip the right edge and J loses meaning anyway (post-fracture regime).
X_TIP_MAX_FOR_J = 0.35                  # = 0.5 (right edge) − 0.15 (margin > max r)


# Curated archives — same set as A2 (compute_process_zone_metrics.PRIORITY_ARCHIVES)
PRIORITY_ARCHIVES = [
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_enriched_ansatz_modeI_v1_cycle94_Nf84_real_fracture",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_spAlphaT_b0.5_r0.1_cycle86_Nf76_real_fracture",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_spAlphaT_b0.8_r0.03_cycle90_Nf80_real_fracture",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_psiHack_m1000_r0.02_cycle91_Nf81_real_fracture",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N250_R0.0_Umax0.11",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N350_R0.0_Umax0.1",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N400_R0.0_Umax0.09",
]


def setup_pidl_pipeline(coeff_str="1.0", mesh_file=None):
    if mesh_file is None:
        mesh_file = FINE_MESH
    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, DEVICE,
        williams_dict=None,
    )
    inp, T_conn, area_T, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict,
        mesh_file=mesh_file, device=DEVICE,
    )
    field_comp = FieldComputation(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.0], device=DEVICE), theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=None, l0=mat_prop_dict["l0"],
    )
    return {"field_comp": field_comp, "matprop": matprop, "pffmodel": pffmodel}


def make_contour_points(radii, n_theta, delta_face=0.05, x_tip=0.0):
    """Open contour around the (moving) tip at (x_tip, 0), avoiding crack faces.

    Crack runs from x = −L to x = x_tip along y = 0; crack-face direction
    is θ = ±π relative to the tip. Use θ ∈ [−π + δ_face, π − δ_face]
    (uniform sampling, INCLUDING both endpoints) so the trapezoidal rule
    integrates the open contour from just above the crack (y=0⁺) round CCW
    through the un-cracked half-plane to just below (y=0⁻).

    Parameters
    ----------
    radii       : list of contour radii
    n_theta     : θ samples per radius
    delta_face  : padding (rad) excluding crack-face direction
    x_tip       : x-coordinate of crack tip (contour center). y_tip=0 fixed.
    """
    pts_list, rad_idx, theta_list = [], [], []
    theta = np.linspace(-np.pi + delta_face, np.pi - delta_face, n_theta,
                        endpoint=True)
    for ri, r in enumerate(radii):
        x = x_tip + r * np.cos(theta)
        y = r * np.sin(theta)
        pts_list.append(np.stack([x, y], axis=1))
        rad_idx.append(np.full(n_theta, ri, dtype=np.int64))
        theta_list.append(theta)
    pts = np.concatenate(pts_list, axis=0).astype(np.float64)
    return pts, np.concatenate(rad_idx), np.concatenate(theta_list)


def compute_J_at_cycle(ctx, nn_ckpt: Path, lmbda: float,
                       contour_xy: np.ndarray, rad_idx: np.ndarray,
                       theta_arr: np.ndarray, radii: list[float]):
    """Forward NN at contour points; autograd ε; Hooke σ; integrate J(r)."""
    fc = ctx["field_comp"]
    fc.lmbda = torch.tensor(lmbda, device=DEVICE)
    fc.net.load_state_dict(
        torch.load(str(nn_ckpt), map_location=DEVICE, weights_only=True))
    fc.net.eval()

    inp = torch.tensor(contour_xy, dtype=torch.float64, device=DEVICE,
                       requires_grad=True)
    # Cast network to float64 for stable autograd at small contour scale
    fc_net = fc.net.double()
    # field_calculation expects (N, 2) inputs; reuse it for consistency w/
    # the trained mapping (BC clamping + alpha constraint).
    u, v, alpha = fc.fieldCalculation(inp)

    # Per-point gradients: use vector-Jacobian via grad
    # ∂u/∂(x,y)
    grad_u = torch.autograd.grad(u.sum(), inp, create_graph=False, retain_graph=True)[0]
    grad_v = torch.autograd.grad(v.sum(), inp, create_graph=False, retain_graph=False)[0]

    eps11 = grad_u[:, 0]
    eps22 = grad_v[:, 1]
    eps12 = 0.5 * (grad_u[:, 1] + grad_v[:, 0])

    # Use RAW (un-degraded) Hooke for J-integral. Justification: J is a far-
    # field path integral; r₀ ≥ 2ℓ₀ should sit outside the saturated tip
    # band (where d→1), and any small in-band residual would be killed by
    # g(α)≈0 anyway — including or excluding g(α) here doesn't change J in
    # the LEFM-valid regime.
    sig11 = LMBDA * (eps11 + eps22) + 2.0 * MU * eps11
    sig22 = LMBDA * (eps11 + eps22) + 2.0 * MU * eps22
    sig12 = 2.0 * MU * eps12
    W = 0.5 * (sig11 * eps11 + sig22 * eps22 + 2.0 * sig12 * eps12)

    grad_u_np = grad_u.detach().cpu().numpy()
    grad_v_np = grad_v.detach().cpu().numpy()
    sig11_np = sig11.detach().cpu().numpy()
    sig22_np = sig22.detach().cpu().numpy()
    sig12_np = sig12.detach().cpu().numpy()
    W_np = W.detach().cpu().numpy()

    # Reset NN to float32 to leave context unchanged for next cycle
    fc.net.float()

    # Per-radius J integrand
    cos_t = np.cos(theta_arr)
    sin_t = np.sin(theta_arr)
    n_x = cos_t
    n_y = sin_t
    t1 = sig11_np * n_x + sig12_np * n_y      # σ_1j n_j
    t2 = sig12_np * n_x + sig22_np * n_y      # σ_2j n_j
    integrand = W_np * cos_t - t1 * grad_u_np[:, 0] - t2 * grad_v_np[:, 0]

    Js, Ks = [], []
    n_per = len(theta_arr) // len(radii)
    for ri, r in enumerate(radii):
        sl = slice(ri * n_per, (ri + 1) * n_per)
        th = theta_arr[sl]
        # Open contour: trapezoidal integration over θ in (−π+δ, π−δ).
        # NO wrap-around — excluding the spurious crack-face crossing.
        J = r * np.trapezoid(integrand[sl], x=th)
        Js.append(float(J))
        # Plane stress: K_I = √(E·J). Keep sign for diagnostic of NN artifacts.
        K = np.sign(J) * np.sqrt(abs(J) * E_YOUNG)
        Ks.append(float(K))
    return Js, Ks


def list_archive_cycles(archive_dir: Path):
    bm = archive_dir / "best_models"
    nn_cycles = set()
    for p in bm.glob("trained_1NN_*.pt"):
        try:
            nn_cycles.add(int(p.stem.split("_")[-1]))
        except ValueError:
            pass
    return sorted(nn_cycles)


def parse_umax(name: str) -> float:
    for tok in name.split("_"):
        if tok.startswith("Umax"):
            try:
                return float(tok[4:])
            except ValueError:
                pass
    return 0.12


def process_archive(archive_dir: Path, ctx, every: int = 5,
                    radii=CONTOUR_RADII, n_theta=N_THETA, force=False):
    out_npy = archive_dir / "best_models" / "J_integral.npy"
    out_csv = archive_dir / "best_models" / "J_integral.csv"
    if out_npy.is_file() and not force:
        prev = np.load(str(out_npy))
        print(f"  [cached] {out_npy.relative_to(HERE.parent)} ({len(prev)} cycles)")
        return prev

    umax = parse_umax(archive_dir.name)
    cycles = list_archive_cycles(archive_dir)
    if not cycles:
        print(f"  [skip] no NN ckpts in {archive_dir.name}")
        return None
    selected = cycles[::every]
    if cycles[-1] not in selected:
        selected.append(cycles[-1])
    print(f"  Umax={umax}  total={len(cycles)}  selected={len(selected)}  (every={every})")

    # Per-cycle x_tip lookup (contour follows the propagating tip).
    # If x_tip data is missing, fall back to fixed origin and warn once.
    x_tip_path = archive_dir / "best_models" / "x_tip_vs_cycle.npy"
    if x_tip_path.is_file():
        x_tip_per_cycle = np.load(str(x_tip_path))
        if len(x_tip_per_cycle) < max(cycles) + 1:
            x_tip_per_cycle = np.concatenate([
                x_tip_per_cycle,
                np.full(max(cycles) + 1 - len(x_tip_per_cycle),
                        x_tip_per_cycle[-1])])
        print(f"  x_tip range: {x_tip_per_cycle[0]:.3f} → {x_tip_per_cycle[-1]:.3f}")
    else:
        x_tip_per_cycle = None
        print("  [warn] x_tip_vs_cycle.npy missing — contour fixed at origin")

    rows = []
    skipped_post_fracture = 0
    t0 = time.time()
    for i, c in enumerate(selected):
        nn_path = archive_dir / "best_models" / f"trained_1NN_{c}.pt"
        x_tip_c = float(x_tip_per_cycle[c]) if x_tip_per_cycle is not None else 0.0
        if x_tip_c > X_TIP_MAX_FOR_J:
            skipped_post_fracture += 1
            continue
        # Contour must stay inside the un-cracked region. Cap each radius at
        # 0.5 - x_tip - small_margin. With X_TIP_MAX_FOR_J=0.35, full radii
        # always fit, so this is mostly a safety net.
        radii_eff = [min(r, max(0.01, 0.48 - x_tip_c)) for r in radii]
        contour_xy, rad_idx, theta_arr = make_contour_points(
            radii_eff, n_theta, x_tip=x_tip_c)
        try:
            Js, Ks = compute_J_at_cycle(ctx, nn_path, umax,
                                        contour_xy, rad_idx, theta_arr, radii_eff)
        except RuntimeError as e:
            if "size mismatch" in str(e) or "Missing key" in str(e):
                raise
            print(f"  [warn] cycle {c} failed: {e}")
            continue
        rows.append([c, x_tip_c] + radii_eff + Js + Ks)
        if (i + 1) % 5 == 0 or i == len(selected) - 1:
            elapsed = time.time() - t0
            eta = (len(selected) - i - 1) * elapsed / max(i + 1, 1)
            print(f"    [{i+1}/{len(selected)}] cyc={c}  x_tip={x_tip_c:.3f}  "
                  f"r_eff={radii_eff}  J(r₂)={Js[1]:.3e}  K(r₂)={Ks[1]:.3e}  "
                  f"({elapsed:.0f}s, ETA {eta:.0f}s)")

    cols = (["cycle", "x_tip"]
            + [f"r_eff_{i}" for i in range(len(radii))]
            + [f"J_r{i}" for i in range(len(radii))]
            + [f"K_r{i}" for i in range(len(radii))])
    arr = np.array(rows, dtype=np.float64)
    np.save(str(out_npy), arr)
    with open(out_csv, "w") as fh:
        fh.write(",".join(cols) + "\n")
        for r in arr:
            fh.write(",".join(f"{v:.6e}" if isinstance(v, float) else str(int(v))
                              for v in r) + "\n")
    print(f"  → {out_npy.relative_to(HERE.parent)}  ({len(arr)} cycles, "
          f"{time.time()-t0:.0f}s, {skipped_post_fracture} post-fracture skipped)")
    return arr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", help="single archive name")
    ap.add_argument("--all", action="store_true",
                    help="run on PRIORITY_ARCHIVES list")
    ap.add_argument("--every", type=int, default=5,
                    help="cycle subsampling factor")
    ap.add_argument("--force", action="store_true",
                    help="recompute even if cached")
    ap.add_argument("--mesh", default=None,
                    help="Mesh .msh file (default: meshed_geom2.msh; for "
                         "α-1 archives use meshed_geom_corridor_v1.msh)")
    args = ap.parse_args()

    if not args.archive and not args.all:
        ap.error("must pass --archive or --all")

    mesh_path = args.mesh if args.mesh else FINE_MESH
    print(f"Building PIDL pipeline (E={E_YOUNG}, ν={NU}, ℓ₀={L0}, mesh={Path(mesh_path).name})…")
    print(f"  contour radii: {CONTOUR_RADII}  n_theta={N_THETA}")
    ctx = setup_pidl_pipeline(mesh_file=mesh_path)

    targets = []
    if args.archive:
        targets.append(args.archive)
    if args.all:
        targets.extend(PRIORITY_ARCHIVES)

    skipped = []
    done = []
    for name in targets:
        print(f"\n[{name}]")
        adir = HERE / name
        if not adir.is_dir():
            skipped.append((name, "missing"))
            continue
        try:
            process_archive(adir, ctx, every=args.every, force=args.force)
            done.append(name)
        except RuntimeError as e:
            msg = str(e)[:120]
            if "size mismatch" in msg or "Missing key" in msg:
                print(f"  [skip] non-baseline architecture: {msg}")
                skipped.append((name, "needs custom pipeline"))
            else:
                raise
    print("\n" + "=" * 60)
    print(f"Done {len(done)}; skipped {len(skipped)}")
    for n, why in skipped:
        print(f"  [SKIP] {why}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
