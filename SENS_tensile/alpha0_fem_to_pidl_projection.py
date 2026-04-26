#!/usr/bin/env python3
"""
alpha0_fem_to_pidl_projection.py — α-0 (Apr 25 2026, 2nd-expert review Level 0)

Project the FEM ψ⁺_raw field onto PIDL element centroids and compare three
quantities at each FEM snapshot cycle:

  (1) FEM native:    ψ⁺ on the original FEM mesh (77730 elements, tip-refined)
  (2) FEM projected: FEM ψ⁺ averaged within each PIDL element (area-weighted)
  (3) PIDL native:   ψ⁺ produced by PIDL trained NN on the same cycle

Diagnostic question — IS THE 2000× PIDL/FEM-fine GAP MESH-DRIVEN OR NN-DRIVEN?

  - If FEM-projected ≈ PIDL native → mesh resolution is the gap.
    PIDL gives the right value at ITS element resolution; the disparity
    against FEM-fine peak is just because PIDL mesh's coarser tip element
    spatially averages the singularity. Fix = local mesh refinement (α-1).
  - If FEM-projected >> PIDL native → NN representational limit.
    Even at PIDL's mesh resolution, NN can't produce what an oracle
    integrator would give over the same element. Fix = architectural
    redesign (α-2 XFEM-jump / α-3 multi-head NN).

For Umax=0.12 we have FEM snapshots at cycles 1, 40, 70, 82. Compare to PIDL
baseline coeff=1.0 trajectory at matched cycles (or nearest). Same for
Umax=0.08 (cycles 1, 150, 350, 396).

Output:
  - figures/audit/alpha0_fem_vs_pidl_projection_<umax>.png
  - alpha0_results_<umax>.csv with all metric variants
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import scipy.io as sio
import torch
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# config.py reads sys.argv; pass dummy
_saved = sys.argv
sys.argv = ["alpha0", "8", "400", "1", "TrainableReLU", "1.0"]
from config import (domain_extrema, loading_angle, network_dict, mat_prop_dict,
                    numr_dict, PFF_model_dict, crack_dict)
sys.argv = _saved

from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from compute_energy import gradients, strain_energy_with_split

DEVICE = torch.device("cpu")
FINE_MESH = str(HERE / "meshed_geom2.msh")
FEM_DIR = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent")
L0 = 0.01   # process-zone radius (mat_prop_dict.l0)

UMAX_CYCLES = {
    0.08: [1, 150, 350, 396],
    0.12: [1, 40, 70, 82],
}

# Map (coeff, Umax) → PIDL archive name
PIDL_ARCHIVES = {
    ("1.0", 0.08): "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N700_R0.0_Umax0.08",
    ("1.0", 0.12): "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12",
    ("3.0", 0.08): "hl_8_Neurons_400_activation_TrainableReLU_coeff_3.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N600_R0.0_Umax0.08",
    ("3.0", 0.12): "hl_8_Neurons_400_activation_TrainableReLU_coeff_3.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12",
}
# Backward-compat alias
PIDL_BASELINE = {u: PIDL_ARCHIVES[("1.0", u)] for u in (0.08, 0.12)}


def point_in_triangle(p, v1, v2, v3, tol=1e-12):
    """Barycentric containment test."""
    denom = (v2[1] - v3[1]) * (v1[0] - v3[0]) + (v3[0] - v2[0]) * (v1[1] - v3[1])
    if abs(denom) < tol:
        return False
    a = ((v2[1] - v3[1]) * (p[0] - v3[0]) + (v3[0] - v2[0]) * (p[1] - v3[1])) / denom
    b = ((v3[1] - v1[1]) * (p[0] - v3[0]) + (v1[0] - v3[0]) * (p[1] - v3[1])) / denom
    c = 1.0 - a - b
    return (a >= -tol) and (b >= -tol) and (c >= -tol)


def build_fem_to_pidl_assignment(fem_centroids, pidl_centroids, pidl_inp_np, T_np):
    """For each FEM element centroid, find the PIDL element containing it.

    Returns array assignment[fem_idx] = pidl_idx (or -1 if none found).
    Uses KDTree of PIDL centroids to prune containment tests.
    """
    n_fem = len(fem_centroids)
    pidl_tree = cKDTree(pidl_centroids)
    assignment = -np.ones(n_fem, dtype=np.int64)
    n_unassigned = 0
    K_NEIGHBORS = 20

    for i in range(n_fem):
        if i % 10000 == 0:
            print(f"  containment {i}/{n_fem}...")
        # find K nearest PIDL elements
        dists, ids = pidl_tree.query(fem_centroids[i], k=K_NEIGHBORS)
        found = False
        for pidl_idx in ids:
            v1 = pidl_inp_np[T_np[pidl_idx, 0]]
            v2 = pidl_inp_np[T_np[pidl_idx, 1]]
            v3 = pidl_inp_np[T_np[pidl_idx, 2]]
            if point_in_triangle(fem_centroids[i], v1, v2, v3):
                assignment[i] = pidl_idx
                found = True
                break
        if not found:
            # Fallback: nearest PIDL element (centroid)
            assignment[i] = ids[0]
            n_unassigned += 1
    print(f"  fallback (nearest, no triangle hit): {n_unassigned}/{n_fem} ({100*n_unassigned/n_fem:.1f}%)")
    return assignment


def project_fem_to_pidl(fem_psi, fem_areas, assignment, n_pidl):
    """Area-weighted average of FEM ψ⁺ within each PIDL element."""
    proj_sum = np.zeros(n_pidl)
    proj_area = np.zeros(n_pidl)
    counts = np.zeros(n_pidl, dtype=np.int64)
    for fem_idx in range(len(fem_psi)):
        pidl_idx = assignment[fem_idx]
        if pidl_idx >= 0:
            proj_sum[pidl_idx] += fem_psi[fem_idx] * fem_areas[fem_idx]
            proj_area[pidl_idx] += fem_areas[fem_idx]
            counts[pidl_idx] += 1
    # area-weighted average; skip empty PIDL elements
    proj = np.zeros(n_pidl)
    mask = proj_area > 0
    proj[mask] = proj_sum[mask] / proj_area[mask]
    return proj, counts


def compute_field_stats(psi, area, r_to_tip, label=""):
    """Standard battery: max, p99, p95, top-1%/top-5% mean, ∫_{B_ℓ₀}, ∫_{B_2ℓ₀}."""
    n = len(psi)
    n_top1 = max(1, n // 100)
    n_top5 = max(1, n // 20)
    psi_max = float(psi.max())
    p99 = float(np.percentile(psi, 99.0))
    p95 = float(np.percentile(psi, 95.0))
    idx_top1 = np.argpartition(psi, -n_top1)[-n_top1:]
    idx_top5 = np.argpartition(psi, -n_top5)[-n_top5:]
    psi_top1pct_mean = float(psi[idx_top1].mean())
    psi_top5pct_mean = float(psi[idx_top5].mean())
    pz_l0_mask = r_to_tip <= L0
    pz_2l0_mask = r_to_tip <= 2 * L0
    pz_l0_int = float((psi[pz_l0_mask] * area[pz_l0_mask]).sum())
    pz_2l0_int = float((psi[pz_2l0_mask] * area[pz_2l0_mask]).sum())
    return {
        "label": label,
        "max": psi_max,
        "p99": p99, "p95": p95,
        "top1pct_mean": psi_top1pct_mean,
        "top5pct_mean": psi_top5pct_mean,
        "pz_l0_int": pz_l0_int,
        "pz_2l0_int": pz_2l0_int,
        "pz_l0_n_elems": int(pz_l0_mask.sum()),
        "pz_2l0_n_elems": int(pz_2l0_mask.sum()),
    }


def fem_load_mesh():
    mesh = sio.loadmat(str(FEM_DIR / "mesh_geometry.mat"))
    fem_centroids = np.asarray(mesh["element_centroids"], dtype=np.float64)
    fem_node_coords = np.asarray(mesh["node_coords"], dtype=np.float64)
    fem_connectivity = np.asarray(mesh["connectivity"], dtype=np.int64) - 1   # 1-indexed → 0
    # FEM elements are 4-node quads; compute area via |cross| / 2 of 2 triangles
    # Actually let's just check if connectivity has 3 or 4 cols
    n_cols = fem_connectivity.shape[1]
    # Use shoelace formula
    if n_cols == 4:
        # quad: split into 2 triangles
        v1 = fem_node_coords[fem_connectivity[:, 0]]
        v2 = fem_node_coords[fem_connectivity[:, 1]]
        v3 = fem_node_coords[fem_connectivity[:, 2]]
        v4 = fem_node_coords[fem_connectivity[:, 3]]
        a1 = 0.5 * np.abs((v2[:, 0] - v1[:, 0]) * (v3[:, 1] - v1[:, 1])
                          - (v3[:, 0] - v1[:, 0]) * (v2[:, 1] - v1[:, 1]))
        a2 = 0.5 * np.abs((v3[:, 0] - v1[:, 0]) * (v4[:, 1] - v1[:, 1])
                          - (v4[:, 0] - v1[:, 0]) * (v3[:, 1] - v1[:, 1]))
        fem_areas = a1 + a2
    else:
        v1 = fem_node_coords[fem_connectivity[:, 0]]
        v2 = fem_node_coords[fem_connectivity[:, 1]]
        v3 = fem_node_coords[fem_connectivity[:, 2]]
        fem_areas = 0.5 * np.abs((v2[:, 0] - v1[:, 0]) * (v3[:, 1] - v1[:, 1])
                                  - (v3[:, 0] - v1[:, 0]) * (v2[:, 1] - v1[:, 1]))
    return fem_centroids, fem_areas


def fem_load_psi_at_cycle(umax: float, cycle: int):
    fname = FEM_DIR / f"u{int(round(umax * 100)):02d}_cycle_{cycle:04d}.mat"
    if not fname.is_file():
        return None
    data = sio.loadmat(str(fname))
    return np.asarray(data["psi_elem"], dtype=np.float64).ravel()


def get_pidl_native_at_cycle(umax: float, cycle: int, coeff: str = "1.0"):
    """Reload PIDL trained network at given cycle, recompute ψ⁺_raw per element."""
    archive = HERE / PIDL_ARCHIVES[(coeff, umax)]
    ckpt_path = archive / "best_models" / f"trained_1NN_{cycle}.pt"
    if not ckpt_path.is_file():
        # try nearest available cycle (skip non-numeric stems like initTraining)
        avail = []
        for p in (archive / "best_models").glob("trained_1NN_*.pt"):
            try:
                avail.append(int(p.stem.split("_")[-1]))
            except ValueError:
                continue
        avail = sorted(avail)
        if not avail:
            return None
        nearest = min(avail, key=lambda c: abs(c - cycle))
        ckpt_path = archive / "best_models" / f"trained_1NN_{nearest}.pt"
        print(f"  PIDL cycle {cycle} not found; using nearest cycle {nearest}")
        cycle = nearest

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
    field_comp.lmbda = torch.tensor(umax, device=DEVICE)
    field_comp.net.load_state_dict(
        torch.load(str(ckpt_path), map_location=DEVICE, weights_only=True))
    field_comp.net.eval()

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
    psi_raw = E_el_p.detach().cpu().numpy()

    # also pull centroids + areas
    inp_np = inp.detach().cpu().numpy()
    T_np = T_conn.cpu().numpy() if isinstance(T_conn, torch.Tensor) else T_conn
    cx = (inp_np[T_np[:, 0], 0] + inp_np[T_np[:, 1], 0] + inp_np[T_np[:, 2], 0]) / 3.0
    cy = (inp_np[T_np[:, 0], 1] + inp_np[T_np[:, 1], 1] + inp_np[T_np[:, 2], 1]) / 3.0
    pidl_centroids = np.stack([cx, cy], axis=1)
    pidl_areas = (area_T.detach().cpu().numpy()
                  if hasattr(area_T, "detach") else np.asarray(area_T))
    pidl_r_to_tip = np.sqrt(cx ** 2 + cy ** 2)
    return psi_raw, pidl_centroids, pidl_areas, pidl_r_to_tip, inp_np, T_np, cycle


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("umax", type=float, help="0.08 or 0.12")
    parser.add_argument("--coeff", default="1.0", choices=["1.0", "3.0"],
                        help="PIDL init_coeff variant (1.0 default; 3.0 needs Apr 25 OneDrive archives)")
    args = parser.parse_args()
    coeff_str = args.coeff

    if args.umax not in UMAX_CYCLES:
        raise SystemExit(f"No FEM data for Umax={args.umax}")

    print("=" * 72)
    print(f"α-0 Mesh-projection diagnostic — Umax={args.umax}")
    print("=" * 72)

    # Load FEM mesh once
    print("Loading FEM mesh...")
    fem_centroids, fem_areas = fem_load_mesh()
    fem_r_to_tip = np.linalg.norm(fem_centroids, axis=1)
    print(f"  FEM elements: {len(fem_centroids)}")
    print(f"  FEM area total: {fem_areas.sum():.4f}")

    # Load PIDL mesh once (use cycle 1 as reference; mesh doesn't change)
    print("Loading PIDL mesh + cycle-1 NN...")
    pidl_data = get_pidl_native_at_cycle(args.umax, 1, coeff=coeff_str)
    if pidl_data is None:
        raise SystemExit(f"PIDL cycle 1 not available")
    _, pidl_centroids, pidl_areas, pidl_r_to_tip, pidl_inp_np, T_np, _ = pidl_data
    print(f"  PIDL elements: {len(pidl_centroids)}")
    print(f"  PIDL area total: {pidl_areas.sum():.4f}")

    # Build assignment FEM → PIDL once (mesh doesn't change with cycle)
    print("Building FEM → PIDL containment assignment (slow, one-time)...")
    assignment = build_fem_to_pidl_assignment(
        fem_centroids, pidl_centroids, pidl_inp_np, T_np)

    # For each FEM cycle, run the 3-way comparison
    rows = []
    for cycle in UMAX_CYCLES[args.umax]:
        print(f"\n--- Cycle {cycle} ---")
        # FEM native
        fem_psi = fem_load_psi_at_cycle(args.umax, cycle)
        if fem_psi is None:
            print(f"  FEM cycle {cycle} NOT FOUND, skipping")
            continue
        fem_native_stats = compute_field_stats(
            fem_psi, fem_areas, fem_r_to_tip, label=f"FEM-fine c{cycle}")

        # FEM projected to PIDL
        fem_proj, n_per_pidl = project_fem_to_pidl(
            fem_psi, fem_areas, assignment, len(pidl_centroids))
        fem_proj_stats = compute_field_stats(
            fem_proj, pidl_areas, pidl_r_to_tip,
            label=f"FEM→PIDL projected c{cycle}")
        avg_n_fem_per_pidl = n_per_pidl[n_per_pidl > 0].mean()
        max_n_fem_per_pidl = n_per_pidl.max()
        print(f"  Avg FEM elements per PIDL: {avg_n_fem_per_pidl:.1f}")
        print(f"  Max FEM elements per PIDL (tip-region indicator): {max_n_fem_per_pidl}")

        # PIDL native at this cycle
        pidl_data_c = get_pidl_native_at_cycle(args.umax, cycle, coeff=coeff_str)
        if pidl_data_c is None:
            print(f"  PIDL cycle {cycle} NOT FOUND, skipping")
            continue
        pidl_psi, _, _, _, _, _, actual_pidl_cycle = pidl_data_c
        pidl_native_stats = compute_field_stats(
            pidl_psi, pidl_areas, pidl_r_to_tip,
            label=f"PIDL-native c{actual_pidl_cycle}")

        # Print 3-way table
        print(f"\n  {'metric':<22} {'FEM-fine':>14} {'FEM→PIDL':>14} {'PIDL-native':>14}  Verdict")
        print(f"  {'-'*22:<22} {'-'*14:>14} {'-'*14:>14} {'-'*14:>14}")
        for m in ["max", "p99", "p95", "top1pct_mean", "top5pct_mean",
                  "pz_l0_int", "pz_2l0_int"]:
            fem_v = fem_native_stats[m]
            proj_v = fem_proj_stats[m]
            pidl_v = pidl_native_stats[m]
            # verdict
            if proj_v > 0:
                ratio_proj_pidl = proj_v / max(pidl_v, 1e-12)
                ratio_fem_proj = fem_v / max(proj_v, 1e-12)
                if ratio_proj_pidl < 1.5:
                    v = "MESH (proj≈PIDL)"
                elif ratio_proj_pidl > 5:
                    v = "NN (proj>>PIDL)"
                else:
                    v = "MIXED"
            else:
                v = "?"
            print(f"  {m:<22} {fem_v:>14.3e} {proj_v:>14.3e} {pidl_v:>14.3e}  {v}")

        rows.append({
            "cycle": cycle, "actual_pidl_cycle": actual_pidl_cycle,
            **{f"fem_{k}": v for k, v in fem_native_stats.items() if k != "label"},
            **{f"proj_{k}": v for k, v in fem_proj_stats.items() if k != "label"},
            **{f"pidl_{k}": v for k, v in pidl_native_stats.items() if k != "label"},
            "avg_n_fem_per_pidl": avg_n_fem_per_pidl,
            "max_n_fem_per_pidl": int(max_n_fem_per_pidl),
        })

    # Save CSV (include coeff in filename to avoid collision with coeff=1)
    csv_suffix = f"_coeff{coeff_str}" if coeff_str != "1.0" else ""
    csv_path = HERE / f"alpha0_results_Umax{args.umax}{csv_suffix}.csv"
    if rows:
        keys = list(rows[0].keys())
        with open(csv_path, "w") as f:
            f.write(",".join(keys) + "\n")
            for r in rows:
                f.write(",".join(str(r[k]) for k in keys) + "\n")
        print(f"\n→ saved {csv_path.name}")

    # Plot
    if not rows:
        print("No data to plot.")
        return 0
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), tight_layout=True)
    cycles = [r["cycle"] for r in rows]
    metrics = [
        ("max", "ψ⁺ max-element value"),
        ("top1pct_mean", "ψ⁺ top-1% mean"),
        ("pz_l0_int", "∫_{B_ℓ₀} ψ⁺ dA  (process-zone integrated)"),
        ("pz_2l0_int", "∫_{B_2ℓ₀} ψ⁺ dA  (sensitivity radius)"),
    ]
    for idx, (m, title) in enumerate(metrics):
        ax = axes[idx // 2, idx % 2]
        fem_vals = [r[f"fem_{m}"] for r in rows]
        proj_vals = [r[f"proj_{m}"] for r in rows]
        pidl_vals = [r[f"pidl_{m}"] for r in rows]
        ax.semilogy(cycles, fem_vals, "k^-", linewidth=2, markersize=10,
                    label="FEM-fine (77730 elem)")
        ax.semilogy(cycles, proj_vals, "g-s", linewidth=2, markersize=8,
                    label="FEM→PIDL (projected, area-weighted)")
        ax.semilogy(cycles, pidl_vals, "b-o", linewidth=2, markersize=8,
                    label="PIDL native")
        ax.set_xlabel("FEM cycle"); ax.set_ylabel(title)
        ax.set_title(f"{title} — Umax={args.umax}")
        ax.legend(fontsize=9); ax.grid(alpha=0.3)

    out_dir = HERE / "figures" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_path = out_dir / f"alpha0_fem_vs_pidl_projection_Umax{args.umax}{csv_suffix}.png"
    fig.savefig(fig_path, dpi=140)
    print(f"→ saved {fig_path}")

    # Bottom-line verdict
    print("\n" + "=" * 72)
    print("DIAGNOSTIC INTERPRETATION:")
    print("=" * 72)
    last_row = rows[-1]
    proj_max = last_row["proj_max"]
    pidl_max = last_row["pidl_max"]
    fem_max = last_row["fem_max"]
    proj_pz = last_row["proj_pz_l0_int"]
    pidl_pz = last_row["pidl_pz_l0_int"]
    fem_pz = last_row["fem_pz_l0_int"]
    print(f"At final FEM cycle {last_row['cycle']}:")
    print(f"  ψ⁺ max:       FEM-fine={fem_max:.2e}  proj={proj_max:.2e}  "
          f"PIDL={pidl_max:.2e}")
    print(f"  ψ⁺ pz_ℓ₀ int: FEM-fine={fem_pz:.2e}  proj={proj_pz:.2e}  "
          f"PIDL={pidl_pz:.2e}")
    print()
    if pidl_max > 0:
        ratio = proj_max / pidl_max
        if ratio < 1.5:
            print(f"  → max ratio (proj/PIDL) = {ratio:.2f} → MESH-DOMINATED gap.")
            print(f"    PIDL gives ~right value at its mesh resolution; the")
            print(f"    'PIDL_native vs FEM-fine' gap is mostly a tip-refinement")
            print(f"    artifact. Fix prioritization: α-1 (mesh-adaptive collocation).")
        elif ratio > 5:
            print(f"  → max ratio (proj/PIDL) = {ratio:.2f} → NN-DOMINATED gap.")
            print(f"    Even when FEM is integrated over the same PIDL element,")
            print(f"    PIDL produces much lower value. NN cannot represent FEM-")
            print(f"    quality solution at PIDL's mesh resolution. Fix prioritization:")
            print(f"    α-2 (XFEM-jump) / α-3 (multi-head NN).")
        else:
            print(f"  → max ratio (proj/PIDL) = {ratio:.2f} → MIXED.")
            print(f"    Partial mesh + partial NN contribution. Both α-1 and α-2/3")
            print(f"    likely needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
