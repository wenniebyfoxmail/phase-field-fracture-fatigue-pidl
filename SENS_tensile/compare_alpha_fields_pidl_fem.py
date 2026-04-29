#!/usr/bin/env python3
"""
compare_alpha_fields_pidl_fem.py — directly test Hyp #3 (override-zone amplification mechanism).

Hyp #3 statement: PIDL α_PIDL is shallower than FEM α_FEM in the override zone B_r=0.02
around (0,0). Consequence: g(α_PIDL) ≈ 1 stays large for many cycles where g(α_FEM) → 0,
so PIDL Carrara accumulator over-integrates Δᾱ = g(α_PIDL)·ψ⁺_FEM.

This script loads PIDL Oracle 0.12 alpha snapshots and FEM v2 alpha fields at matched
cycles (1, 40, 70, 82), restricts to override zone, and compares the distributions.

Also computes:
- g(α) = (1-α)² + tol (AT1 quadratic degradation function)
- f(ᾱ) — would need ᾱ field per element, which is NOT in saved snapshots; report
  global max from alpha_bar_vs_cycle.npy as proxy
"""
import numpy as np
import scipy.io as sio
from pathlib import Path

PIDL_ARCHIVE = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_oracle_zone0.02")
FEM_V2 = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent")

ZONE_RADIUS = 0.02       # override zone B_r
ZONE_CX, ZONE_CY = 0.0, 0.0
ALPHA_T = 0.5            # Carrara α_T
ALPHA_TOL = 1e-3         # g(α) = (1-α)² + tol stabilization (AT1)


def g_alpha(alpha):
    """AT1 degradation: g(α) = (1-α)² (use clipped α to avoid neg)."""
    a = np.clip(alpha, 0.0, 1.0)
    return (1.0 - a) ** 2 + ALPHA_TOL


def f_alphabar(ab):
    """Carrara asymptotic fatigue degradation, p=2."""
    # f(ᾱ) = min(1, [2·α_T/(ᾱ + α_T)]²)
    return np.minimum(1.0, (2.0 * ALPHA_T / (ab + ALPHA_T)) ** 2)


# ---------- FEM mesh geometry ----------
mesh = sio.loadmat(FEM_V2 / "mesh_geometry.mat")
print(f"FEM mesh keys: {[k for k in mesh.keys() if not k.startswith('__')]}")
fem_centroids = None
for key in ["element_centroids", "centroids", "elem_centroids", "centroid", "cx_cy"]:
    if key in mesh:
        fem_centroids = mesh[key]
        print(f"  Using key '{key}', shape={fem_centroids.shape}")
        break
if fem_centroids is None:
    # Try to compute from nodes + connectivity
    nodes = mesh.get("nodes", mesh.get("Nodes", mesh.get("xy", None)))
    conn = mesh.get("conn", mesh.get("connectivity", mesh.get("T_conn", None)))
    if nodes is not None and conn is not None:
        # zero-based index?
        ci = conn.astype(int)
        if ci.min() == 1:
            ci = ci - 1
        fem_centroids = nodes[ci].mean(axis=1)
        print(f"  Computed from nodes+conn, shape={fem_centroids.shape}")

if fem_centroids is None:
    raise RuntimeError("Could not get FEM element centroids")

# Override zone mask in FEM
fem_r = np.sqrt((fem_centroids[:, 0] - ZONE_CX) ** 2 + (fem_centroids[:, 1] - ZONE_CY) ** 2)
fem_zone_mask = fem_r <= ZONE_RADIUS
print(f"FEM elements in zone (r<={ZONE_RADIUS}): {fem_zone_mask.sum()} of {len(fem_centroids)}")


# ---------- Match cycles: FEM has snapshots at 1, 40, 70, 82 for u12 ----------
fem_cycle_files = {
    1:  FEM_V2 / "u12_cycle_0001.mat",
    40: FEM_V2 / "u12_cycle_0040.mat",
    70: FEM_V2 / "u12_cycle_0070.mat",
    82: FEM_V2 / "u12_cycle_0082.mat",
}

# PIDL has snapshots at 0, 20, 40, 60, 80, 83, 84, ...
# Match nearest available
pidl_avail = sorted([int(p.stem.split("_")[-1])
                     for p in (PIDL_ARCHIVE / "alpha_snapshots").glob("alpha_cycle_*.npy")])
print(f"\nPIDL snapshot cycles available: {pidl_avail[:10]} ... {pidl_avail[-10:]}")

def nearest(cyc, avail):
    return min(avail, key=lambda c: abs(c - cyc))

pidl_cycle_match = {fc: nearest(fc, pidl_avail) for fc in fem_cycle_files}
print(f"FEM→PIDL cycle match: {pidl_cycle_match}")


# ---------- Compare alpha at matched cycles in override zone ----------
print(f"\n{'='*82}")
print(f"α field comparison in override zone (B_r={ZONE_RADIUS} around ({ZONE_CX},{ZONE_CY}))")
print(f"{'='*82}")
print(f"{'cycle':>6} | {'PIDL_α stats (zone)':<32} | {'FEM_α stats (zone)':<32} | g(αP)/g(αF)")
print(f"{'(FEM)':>6} | mean        max        > 0.5   | mean        max        > 0.5   | mean ratio")
print(f"{'-'*82}")

results = []
for fcyc, fpath in fem_cycle_files.items():
    pcyc = pidl_cycle_match[fcyc]
    # PIDL α
    pidl = np.load(PIDL_ARCHIVE / "alpha_snapshots" / f"alpha_cycle_{pcyc:04d}.npy")
    pidl_xy = pidl[:, :2]
    pidl_alpha = pidl[:, 2]
    pidl_r = np.sqrt((pidl_xy[:, 0] - ZONE_CX) ** 2 + (pidl_xy[:, 1] - ZONE_CY) ** 2)
    pidl_zone = pidl_r <= ZONE_RADIUS
    pa_zone = pidl_alpha[pidl_zone]

    # FEM α
    fem_data = sio.loadmat(fpath)
    fem_alpha_key = None
    for k in ["alpha_elem", "alpha_e", "alpha", "phi_elem", "d_elem"]:
        if k in fem_data:
            fem_alpha_key = k
            break
    if fem_alpha_key is None:
        print(f"  ! cycle {fcyc}: no alpha key in FEM .mat (have: {[k for k in fem_data.keys() if not k.startswith('__')]})")
        continue
    fa = fem_data[fem_alpha_key].squeeze()
    fa_zone = fa[fem_zone_mask]

    # Compute g(α) means
    gP_mean = g_alpha(pa_zone).mean()
    gF_mean = g_alpha(fa_zone).mean()
    g_ratio = gP_mean / gF_mean if gF_mean > 1e-12 else float("inf")

    print(f"{fcyc:>6} | {pa_zone.mean():>6.3f}    {pa_zone.max():>6.3f}    {(pa_zone>0.5).sum():>4}/{len(pa_zone):<3} | "
          f"{fa_zone.mean():>6.3f}    {fa_zone.max():>6.3f}    {(fa_zone>0.5).sum():>4}/{len(fa_zone):<3} | {g_ratio:>6.3f}")

    results.append({
        "fcyc": fcyc, "pcyc": pcyc,
        "pidl_alpha_mean": pa_zone.mean(), "pidl_alpha_max": pa_zone.max(),
        "fem_alpha_mean": fa_zone.mean(), "fem_alpha_max": fa_zone.max(),
        "g_pidl_mean": gP_mean, "g_fem_mean": gF_mean, "g_ratio": g_ratio,
        "fem_alpha_key": fem_alpha_key,
    })


# ---------- Global ᾱ comparison from saved arrays ----------
print(f"\n{'='*82}")
print(f"Global ᾱ_max trajectory comparison (already in memory but for cross-check)")
print(f"{'='*82}")
pidl_ab = np.load(PIDL_ARCHIVE / "best_models" / "alpha_bar_vs_cycle.npy")
print(f"PIDL Oracle 0.12 ᾱ_max @ cycle: c40={pidl_ab[40] if len(pidl_ab)>40 else 'NA':.3f}  c70={pidl_ab[70] if len(pidl_ab)>70 else 'NA':.3f}  c82={pidl_ab[82] if len(pidl_ab)>82 else 'NA':.3f}")
print(f"  (These are GLOBAL max across all elements, not zone-restricted)")


# ---------- Diagnosis ----------
print(f"\n{'='*82}")
print(f"Diagnosis (Hyp #3 test)")
print(f"{'='*82}")
if results:
    last = results[-1]
    if last["fem_alpha_mean"] > last["pidl_alpha_mean"] * 2:
        print(f"  ✅ Hyp #3 SUPPORTED: at cycle {last['fcyc']} (~N_f),")
        print(f"     FEM α_mean in zone = {last['fem_alpha_mean']:.3f} >> PIDL α_mean = {last['pidl_alpha_mean']:.3f}")
        print(f"     → g(α_PIDL) ≈ {last['g_pidl_mean']:.3f} >> g(α_FEM) ≈ {last['g_fem_mean']:.3f}")
        print(f"     → PIDL Carrara accumulator integrates a {last['g_ratio']:.1f}× larger active driver each cycle")
        print(f"     → over-shoot mechanism CONFIRMED")
    elif last["pidl_alpha_mean"] > last["fem_alpha_mean"] * 0.5:
        print(f"  ⚠ Hyp #3 NOT SUPPORTED: PIDL α in zone is comparable to FEM α")
        print(f"     PIDL α_mean = {last['pidl_alpha_mean']:.3f}, FEM α_mean = {last['fem_alpha_mean']:.3f}")
        print(f"     g_ratio = {last['g_ratio']:.3f} — over-shoot must come from a different mechanism")
    else:
        print(f"  ? Mixed: g_ratio = {last['g_ratio']:.3f} — partial support")
print(f"\nNote: ψ⁺ field comparison + ᾱ per-element field would require checkpoint forward pass.")
print(f"This script tests the load-bearing α-shape mismatch only.")
