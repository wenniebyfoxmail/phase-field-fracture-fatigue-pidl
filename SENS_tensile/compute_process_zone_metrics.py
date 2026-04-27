#!/usr/bin/env python3
"""
compute_process_zone_metrics.py — A2 (Apr 27 2026, post external review G1)

Per-archive, per-cycle process-zone metric battery on existing PIDL checkpoints.
Pure post-processing: NO training. Reuses α-0 NN reload + field-compute pipeline.

For each cycle the script computes three ψ⁺ field variants:
  ψ⁺_raw   :  un-degraded positive strain energy (E_el_p)
  g·ψ⁺     :  active driver into Carrara fatigue accumulator
              (g(α)=(1-α)² applied; per Apr 23 FEM dump verification)
  f·ψ⁺     :  fatigue-weighted strain energy (G1 expert review ask)

For each variant, reductions over (a) full domain, (b) PZ_ℓ₀ ball at tip,
(c) PZ_2ℓ₀ ball: max, top-1%/5% mean, ∫ dA.

Also tracks process-zone topology:
  - alpha_bar_max / mean
  - alpha_max / mean
  - PZ-ᾱ volume (area where ᾱ > 0.5·α_T)
  - PZ-α volume (area where d > 0.5)

Output:
  <archive>/best_models/process_zone_metrics.npy    structured array
  <archive>/best_models/process_zone_metrics.csv    same, human-readable
  figures/audit/pz_metrics_<archive_short>.png      4-panel summary
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# config.py reads sys.argv; pass dummy
_saved_argv = sys.argv
sys.argv = ["pz_metrics", "8", "400", "1", "TrainableReLU", "1.0"]
from config import (domain_extrema, loading_angle, network_dict, mat_prop_dict,
                    numr_dict, PFF_model_dict, crack_dict)
sys.argv = _saved_argv

from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from compute_energy import gradients, strain_energy_with_split

DEVICE = torch.device("cpu")
FINE_MESH = str(HERE / "meshed_geom2.msh")
L0 = float(mat_prop_dict["l0"])     # process-zone characteristic length
ALPHA_T_DEFAULT = 0.5

# ---------------------------------------------------------------------------
# Curated archive list — paper-priority methods at Umax=0.12 + Umax sweep
# ---------------------------------------------------------------------------
PRIORITY_ARCHIVES = [
    # baselines
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12",
    # Dir 4 / 5 / 2.1 family at Umax=0.12
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_williams_std_v4_cycle87_Nf77_real_fracture",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_enriched_ansatz_modeI_v1_cycle94_Nf84_real_fracture",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_fourier_nf16_sig1.0_v1_cycle94_Nf84_real_fracture",
    # Dir 6.x family at Umax=0.12
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_spAlphaT_b0.5_r0.1_cycle86_Nf76_real_fracture",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_spAlphaT_b0.8_r0.03_cycle90_Nf80_real_fracture",
    # E2 ψ⁺ hack
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_psiHack_m1000_r0.02_cycle91_Nf81_real_fracture",
    # baseline Umax sweep (coeff=1.0)
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N250_R0.0_Umax0.11",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N350_R0.0_Umax0.1",
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N400_R0.0_Umax0.09",
]

OUT_COLUMNS = [
    "cycle",
    # primary fields
    "alpha_bar_max", "alpha_bar_mean", "alpha_max", "alpha_mean",
    # ψ⁺_raw reductions
    "psi_max", "psi_p99", "psi_top1pct", "psi_top5pct",
    # g·ψ⁺ reductions (active driver into accumulator)
    "gpsi_max", "gpsi_p99", "gpsi_top1pct", "gpsi_top5pct",
    # f·ψ⁺ reductions (fatigue-weighted; G1)
    "fpsi_max", "fpsi_p99", "fpsi_top1pct", "fpsi_top5pct",
    # PZ_ℓ₀ ball integrals
    "int_psi_l0", "int_gpsi_l0", "int_fpsi_l0",
    # PZ_2ℓ₀ ball integrals
    "int_psi_2l0", "int_gpsi_2l0", "int_fpsi_2l0",
    # full-domain integrals
    "int_psi_full", "int_gpsi_full", "int_fpsi_full",
    # process-zone topology
    "pz_alpha_area",          # area where d > 0.5
    "pz_alphabar_area",       # area where ᾱ > 0.5·α_T
    # mesh accounting
    "pz_l0_n_elem", "pz_2l0_n_elem",
]


def carrara_f(hist_fat: np.ndarray, alpha_T: float) -> np.ndarray:
    """Carrara asymptotic Eq. 41 — vectorized numpy version of source/fatigue_history.py."""
    f = np.ones_like(hist_fat, dtype=np.float64)
    mask = hist_fat > alpha_T
    f[mask] = (2.0 * alpha_T / (hist_fat[mask] + alpha_T)) ** 2
    return f


def compute_reductions(field: np.ndarray, area: np.ndarray,
                       pz_l0_mask: np.ndarray, pz_2l0_mask: np.ndarray):
    n = len(field)
    n_top1 = max(1, n // 100)
    n_top5 = max(1, n // 20)
    idx_top1 = np.argpartition(field, -n_top1)[-n_top1:]
    idx_top5 = np.argpartition(field, -n_top5)[-n_top5:]
    return {
        "max": float(field.max()),
        "p99": float(np.percentile(field, 99.0)),
        "top1pct": float(field[idx_top1].mean()),
        "top5pct": float(field[idx_top5].mean()),
        "int_full": float((field * area).sum()),
        "int_l0": float((field[pz_l0_mask] * area[pz_l0_mask]).sum()),
        "int_2l0": float((field[pz_2l0_mask] * area[pz_2l0_mask]).sum()),
    }


def setup_pidl_pipeline(coeff_str="1.0", mesh_file=None):
    if mesh_file is None:
        mesh_file = FINE_MESH
    """Build PIDL field computation pipeline once (mesh + NN structure are reused)."""
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
    inp_np = inp.detach().cpu().numpy()
    T_np = T_conn.cpu().numpy() if isinstance(T_conn, torch.Tensor) else T_conn
    cx = (inp_np[T_np[:, 0], 0] + inp_np[T_np[:, 1], 0] + inp_np[T_np[:, 2], 0]) / 3.0
    cy = (inp_np[T_np[:, 0], 1] + inp_np[T_np[:, 1], 1] + inp_np[T_np[:, 2], 1]) / 3.0
    pidl_areas = (area_T.detach().cpu().numpy()
                  if hasattr(area_T, "detach") else np.asarray(area_T))
    r_to_tip = np.sqrt(cx ** 2 + cy ** 2)
    return {
        "field_comp": field_comp, "inp": inp, "T_conn": T_conn,
        "area_T": area_T, "matprop": matprop, "pffmodel": pffmodel,
        "areas": pidl_areas, "r_to_tip": r_to_tip,
        "pz_l0_mask": r_to_tip <= L0,
        "pz_2l0_mask": r_to_tip <= 2 * L0,
    }


def compute_psi_at_cycle(ctx, ckpt_nn_path, lmbda):
    """Reload NN at one cycle and recompute (ψ⁺_raw, g·ψ⁺, alpha_elem) per element."""
    ctx["field_comp"].lmbda = torch.tensor(lmbda, device=DEVICE)
    ctx["field_comp"].net.load_state_dict(
        torch.load(str(ckpt_nn_path), map_location=DEVICE, weights_only=True))
    ctx["field_comp"].net.eval()
    with torch.no_grad():
        u, v, alpha = ctx["field_comp"].fieldCalculation(ctx["inp"])
        s11, s22, s12, _, _ = gradients(
            ctx["inp"], u, v, alpha, ctx["area_T"], ctx["T_conn"])
        if ctx["T_conn"] is None:
            alpha_elem = alpha
        else:
            T = ctx["T_conn"]
            alpha_elem = (alpha[T[:, 0]] + alpha[T[:, 1]] + alpha[T[:, 2]]) / 3
        _, E_el_p = strain_energy_with_split(
            s11, s22, s12, alpha_elem, ctx["matprop"], ctx["pffmodel"])
        g_alpha, _ = ctx["pffmodel"].Edegrade(alpha_elem)
    return (E_el_p.detach().cpu().numpy().astype(np.float64),
            g_alpha.detach().cpu().numpy().astype(np.float64),
            alpha_elem.detach().cpu().numpy().astype(np.float64))


def list_archive_cycles(archive_dir: Path):
    """Return sorted list of cycles for which BOTH NN ckpt and hist_fat ckpt exist."""
    bm = archive_dir / "best_models"
    nn_cycles = set()
    for p in bm.glob("trained_1NN_*.pt"):
        try:
            nn_cycles.add(int(p.stem.split("_")[-1]))
        except ValueError:
            continue
    fat_cycles = set()
    for p in bm.glob("checkpoint_step_*.pt"):
        try:
            fat_cycles.add(int(p.stem.split("_")[-1]))
        except ValueError:
            continue
    return sorted(nn_cycles & fat_cycles)


def parse_umax_from_archive(name: str) -> float:
    for tok in name.split("_"):
        if tok.startswith("Umax"):
            try:
                return float(tok[4:])
            except ValueError:
                pass
    return 0.12


def process_archive(archive_dir: Path, every: int = 5,
                    alpha_T: float = ALPHA_T_DEFAULT,
                    coeff_str: str = "1.0",
                    ctx=None, force: bool = False):
    out_npy = archive_dir / "best_models" / "process_zone_metrics.npy"
    out_csv = archive_dir / "best_models" / "process_zone_metrics.csv"
    if out_npy.is_file() and not force:
        prev = np.load(str(out_npy))
        print(f"  [cached] {out_npy.relative_to(HERE.parent)} ({len(prev)} cycles)")
        return prev

    if ctx is None:
        ctx = setup_pidl_pipeline(coeff_str=coeff_str)

    umax = parse_umax_from_archive(archive_dir.name)
    cycles = list_archive_cycles(archive_dir)
    if not cycles:
        print(f"  [skip] no checkpoints in {archive_dir.name}")
        return None
    selected = cycles[::every]
    if cycles[-1] not in selected:
        selected.append(cycles[-1])
    print(f"  Umax={umax}  total cycles={len(cycles)}  selected={len(selected)}  (every={every})")

    rows = []
    t0 = time.time()
    for i, c in enumerate(selected):
        nn_path = archive_dir / "best_models" / f"trained_1NN_{c}.pt"
        ck_path = archive_dir / "best_models" / f"checkpoint_step_{c}.pt"
        try:
            ck = torch.load(str(ck_path), map_location="cpu", weights_only=True)
        except Exception:
            ck = torch.load(str(ck_path), map_location="cpu")
        hist_fat = ck.get("hist_fat")
        if hist_fat is None:
            continue
        hist_fat_np = hist_fat.detach().cpu().numpy().astype(np.float64).ravel()

        psi_raw, g_alpha, alpha_elem = compute_psi_at_cycle(ctx, nn_path, umax)
        # ensure alignment
        if len(hist_fat_np) != len(psi_raw):
            print(f"  [warn] cycle {c}: hist_fat len {len(hist_fat_np)} != psi len {len(psi_raw)}; skip")
            continue
        f_field = carrara_f(hist_fat_np, alpha_T)
        gpsi = g_alpha * psi_raw
        fpsi = f_field * psi_raw

        red_psi = compute_reductions(psi_raw, ctx["areas"], ctx["pz_l0_mask"], ctx["pz_2l0_mask"])
        red_gpsi = compute_reductions(gpsi, ctx["areas"], ctx["pz_l0_mask"], ctx["pz_2l0_mask"])
        red_fpsi = compute_reductions(fpsi, ctx["areas"], ctx["pz_l0_mask"], ctx["pz_2l0_mask"])

        pz_alpha_area = float(ctx["areas"][alpha_elem > 0.5].sum())
        pz_alphabar_area = float(ctx["areas"][hist_fat_np > 0.5 * alpha_T].sum())

        rows.append([
            c,
            float(hist_fat_np.max()), float(hist_fat_np.mean()),
            float(alpha_elem.max()), float(alpha_elem.mean()),
            red_psi["max"], red_psi["p99"], red_psi["top1pct"], red_psi["top5pct"],
            red_gpsi["max"], red_gpsi["p99"], red_gpsi["top1pct"], red_gpsi["top5pct"],
            red_fpsi["max"], red_fpsi["p99"], red_fpsi["top1pct"], red_fpsi["top5pct"],
            red_psi["int_l0"], red_gpsi["int_l0"], red_fpsi["int_l0"],
            red_psi["int_2l0"], red_gpsi["int_2l0"], red_fpsi["int_2l0"],
            red_psi["int_full"], red_gpsi["int_full"], red_fpsi["int_full"],
            pz_alpha_area, pz_alphabar_area,
            int(ctx["pz_l0_mask"].sum()), int(ctx["pz_2l0_mask"].sum()),
        ])
        if (i + 1) % 5 == 0 or i == len(selected) - 1:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(selected) - i - 1) / max(rate, 1e-6)
            print(f"    [{i+1}/{len(selected)}] cycle={c}  ᾱ_max={hist_fat_np.max():.2f}  "
                  f"ψ⁺_max={red_psi['max']:.2e}  ∫g·ψ⁺_l0={red_gpsi['int_l0']:.2e}  "
                  f"({elapsed:.0f}s elapsed, ETA {eta:.0f}s)")

    arr = np.array(rows, dtype=np.float64)
    np.save(str(out_npy), arr)
    with open(out_csv, "w") as fh:
        fh.write(",".join(OUT_COLUMNS) + "\n")
        for row in arr:
            fh.write(",".join(f"{v:.6e}" if isinstance(v, float) else str(int(v))
                              for v in row) + "\n")
    print(f"  → {out_npy.relative_to(HERE.parent)}  ({len(arr)} cycles, {time.time()-t0:.0f}s)")
    return arr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", help="single archive name (directory under SENS_tensile/)")
    ap.add_argument("--all", action="store_true", help="run on PRIORITY_ARCHIVES list")
    ap.add_argument("--every", type=int, default=5,
                    help="cycle subsampling factor (default 5)")
    ap.add_argument("--alpha-T", type=float, default=ALPHA_T_DEFAULT)
    ap.add_argument("--force", action="store_true", help="recompute even if cached")
    ap.add_argument("--coeff", default="1.0", choices=["1.0", "3.0"])
    ap.add_argument("--mesh", default=None,
                    help="Mesh .msh file (default: meshed_geom2.msh; for "
                         "α-1 archives use meshed_geom_corridor_v1.msh)")
    args = ap.parse_args()

    if not args.archive and not args.all:
        ap.error("must pass --archive or --all")

    targets = []
    if args.archive:
        targets.append(args.archive)
    if args.all:
        targets.extend(PRIORITY_ARCHIVES)

    mesh_path = args.mesh if args.mesh else FINE_MESH
    print(f"Building PIDL pipeline (coeff={args.coeff}, mesh={Path(mesh_path).name})…")
    ctx = setup_pidl_pipeline(coeff_str=args.coeff, mesh_file=mesh_path)
    print(f"  PIDL elements: {len(ctx['areas'])}")
    print(f"  PZ_ℓ₀ elements: {ctx['pz_l0_mask'].sum()}")
    print(f"  PZ_2ℓ₀ elements: {ctx['pz_2l0_mask'].sum()}")

    skipped = []
    done = []
    for name in targets:
        print(f"\n[{name}]")
        adir = HERE / name
        if not adir.is_dir():
            print(f"  [missing] {adir}")
            skipped.append((name, "missing dir"))
            continue
        try:
            process_archive(adir, every=args.every, alpha_T=args.alpha_T,
                            coeff_str=args.coeff, ctx=ctx, force=args.force)
            done.append(name)
        except RuntimeError as e:
            msg = str(e)[:120]
            if "size mismatch" in msg or "Missing key" in msg or "Unexpected key" in msg:
                print(f"  [skip] non-baseline NN architecture: {msg}")
                skipped.append((name, "needs custom pipeline"))
            else:
                raise
    print("\n" + "=" * 60)
    print(f"Done {len(done)} archives; skipped {len(skipped)}")
    for n, why in skipped:
        print(f"  [SKIP] {why}: {n}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
