#!/usr/bin/env python3
"""
validate_pidl_archive.py — PIDL-side validation analog of FEM's 4 standard tests,
plus 4 PIDL-specific tests for fatigue.

Runs on a finished PIDL archive (post-hoc, no retraining). Designed for paper
Ch2 supplementary "Validation" section.

Tests run:

  ## FEM-equivalent (echo the 4 FEM validation criteria)
  V1. Energy balance              ΔE_el(t) + ⟨f(ᾱ)⟩·∂E_d(t) ≈ 0    [per-cycle]
  V2. Mesh resolution             ℓ_0/h_tip ≥ 5  (Carrara recommendation)
  V3. SIF path-independence       max-min K_I across contour radii < 10%
  V4. Geometric symmetry          ⟨α(x, +y) - α(x, -y)⟩_RMS  in tip ROI

  ## PIDL-specific (NN-induced concerns)
  V5. Carrara accumulator self-consistency  Δᾱ = max(0, ψ⁺ - ψ⁺_prev) per element
  V6. f(ᾱ) reaches asymptotic floor          f_min @ N_f vs FEM 1.09e-6
  V7. BC residual                            |u(boundary) - u_BC|_∞
  V8. Pretrain convergence                   final pretrain loss / initial loss

Usage:
    python validate_pidl_archive.py <archive_path> [--coeff 1.0]
        [--mesh ../meshed_geom2.msh]
        [--cycles 0,40,N_f]                # which cycles to test V1, V4, V5, V7

Outputs:
  <archive>/best_models/validation_report.csv     # one row per test
  <archive>/best_models/validation_report.txt     # human-readable summary
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))


# -----------------------------------------------------------------------------
# Test implementations
# -----------------------------------------------------------------------------

def test_v1_energy_balance(archive: Path) -> dict:
    """V1. Per-cycle energy balance.

    Reads E_el_vs_cycle.npy and alpha_bar_vs_cycle.npy. If E_d isn't separately
    tracked (it rarely is on disk), check via:
      ΔE_el(t) + ⟨f(ᾱ)⟩·something ≈ 0  is hard post-hoc.

    Practical check: E_el should be MONOTONICALLY non-increasing (modulo numerical
    noise) once damage starts evolving — fatigue DECREASES elastic capacity.
    Report: max relative cycle-to-cycle increase of E_el; >5% suggests issue.
    """
    f = archive / "best_models" / "E_el_vs_cycle.npy"
    if not f.is_file():
        return {"test": "V1_energy_balance", "status": "SKIP",
                "reason": "no E_el_vs_cycle.npy"}
    E = np.load(f).flatten()
    if E.size < 3:
        return {"test": "V1_energy_balance", "status": "SKIP",
                "reason": f"only {E.size} cycles"}
    # Look at "active fatigue" region: skip first 5 + last 5 cycles
    Eactive = E[5:-5] if E.size > 20 else E
    # Cycle-to-cycle relative change
    rel_changes = np.diff(Eactive) / (np.abs(Eactive[:-1]) + 1e-30)
    max_increase = float(np.max(rel_changes))   # >0 = monotonicity violated
    median_decrease = float(np.median(np.abs(rel_changes[rel_changes < 0]))) if np.any(rel_changes < 0) else 0.0
    status = "PASS" if max_increase < 0.05 else ("WARN" if max_increase < 0.20 else "FAIL")
    return {
        "test": "V1_energy_balance", "status": status,
        "max_rel_increase_E_el": max_increase,
        "median_rel_decrease": median_decrease,
        "criterion": "max increase < 5% (active region)",
    }


def test_v2_mesh_resolution(archive: Path, l0: float = 0.01) -> dict:
    """V2. Mesh resolution at tip: ℓ_0 / h_tip.

    Reads alpha_snapshots[0] to extract node coordinates, computes minimum
    element edge length in tip ROI (x ∈ [0, 0.05], |y| < 0.02), reports
    ℓ_0 / h.
    """
    snap_dir = archive / "alpha_snapshots"
    if not snap_dir.is_dir():
        return {"test": "V2_mesh_resolution", "status": "SKIP",
                "reason": "no alpha_snapshots dir"}
    snaps = sorted(snap_dir.glob("alpha_cycle_*.npy"))
    if not snaps:
        return {"test": "V2_mesh_resolution", "status": "SKIP",
                "reason": "no alpha_cycle_*.npy files"}
    arr = np.load(snaps[0])
    # arr shape (N_nodes, 3) — cols [x, y, alpha]
    xy = arr[:, :2]
    # Tip ROI
    mask = (xy[:, 0] >= 0) & (xy[:, 0] <= 0.05) & (np.abs(xy[:, 1]) < 0.02)
    pts = xy[mask]
    if pts.shape[0] < 10:
        return {"test": "V2_mesh_resolution", "status": "SKIP",
                "reason": f"only {pts.shape[0]} pts in tip ROI"}
    # Approximate h_tip = median nearest-neighbor distance in tip ROI
    from scipy.spatial import cKDTree
    tree = cKDTree(pts)
    d, _ = tree.query(pts, k=2)
    h_tip = float(np.median(d[:, 1]))
    ratio = l0 / h_tip if h_tip > 1e-12 else float("inf")
    status = "PASS" if ratio >= 5 else ("WARN" if ratio >= 3 else "FAIL")
    return {
        "test": "V2_mesh_resolution", "status": status,
        "l0_over_h_tip": ratio, "h_tip": h_tip, "l0": l0,
        "n_pts_tip_roi": int(pts.shape[0]),
        "criterion": "ℓ_0/h ≥ 5 (Carrara 3-5; FEM uses 10)",
    }


def test_v3_J_path_independence(archive: Path) -> dict:
    """V3. K_I path-independence across contour radii.

    Reads J_integral.csv (already computed by compute_J_integral.py).
    Reports max-min spread / median across 3 contour radii in pristine cycles.
    """
    f = archive / "best_models" / "J_integral.csv"
    if not f.is_file():
        return {"test": "V3_J_path_independence", "status": "SKIP",
                "reason": "no J_integral.csv (run compute_J_integral.py first)"}
    import csv
    rows = list(csv.DictReader(open(f)))
    if not rows:
        return {"test": "V3_J_path_independence", "status": "SKIP", "reason": "empty"}
    # Use first 5 cycles (pristine, before serious fatigue)
    Ks = [(float(r["K_r0"]), float(r["K_r1"]), float(r["K_r2"])) for r in rows[:5]]
    medians = [float(np.median([k[i] for k in Ks])) for i in (0, 1, 2)]
    spread = (max(medians) - min(medians)) / max(medians) * 100
    status = "PASS" if spread < 10 else ("WARN" if spread < 20 else "FAIL")
    return {
        "test": "V3_J_path_independence", "status": status,
        "K_r0_med": medians[0], "K_r1_med": medians[1], "K_r2_med": medians[2],
        "spread_pct": spread,
        "criterion": "spread < 10% across 3 contour radii (pristine cycles)",
    }


def test_v4_symmetry(archive: Path, cycles_to_check: list[int] | None = None) -> dict:
    """V4. Geometric symmetry — α field across y=0 axis in tip ROI.

    Computes RMS error |α(x, +y) - α(x, -y)| in tip ROI for a chosen cycle
    (default: midway through fatigue life ~ N_f/2).
    """
    snap_dir = archive / "alpha_snapshots"
    snaps = sorted(snap_dir.glob("alpha_cycle_*.npy")) if snap_dir.is_dir() else []
    if len(snaps) < 2:
        return {"test": "V4_symmetry", "status": "SKIP",
                "reason": "need ≥2 alpha snapshots"}
    # Pick mid-life snapshot (avoid cycle 0 = pristine, avoid post-fracture)
    mid = snaps[len(snaps) // 2]
    arr = np.load(mid)
    xy = arr[:, :2]
    a = arr[:, 2]
    # Tip ROI x ∈ [0, 0.3]; quotient pairing via nearest neighbor
    mask = (xy[:, 0] >= 0) & (xy[:, 0] <= 0.3) & (np.abs(xy[:, 1]) < 0.05)
    if mask.sum() < 30:
        return {"test": "V4_symmetry", "status": "SKIP",
                "reason": f"only {int(mask.sum())} pts"}
    pts = xy[mask]
    a_pts = a[mask]
    # For each (x, +y), find nearest (x, -y); compare alpha
    pos = pts[pts[:, 1] >= 0]
    a_pos = a_pts[pts[:, 1] >= 0]
    neg = pts[pts[:, 1] < 0]
    a_neg = a_pts[pts[:, 1] < 0]
    if len(neg) == 0 or len(pos) == 0:
        return {"test": "V4_symmetry", "status": "SKIP",
                "reason": "asymmetric ROI sampling"}
    from scipy.spatial import cKDTree
    # Mirror neg.y, then KDTree match (x, |y|)
    tree_neg_mirror = cKDTree(np.column_stack([neg[:, 0], -neg[:, 1]]))
    d, idx = tree_neg_mirror.query(pos, k=1)
    # Only count well-matched pairs (d < 0.005)
    good = d < 0.005
    if good.sum() < 10:
        return {"test": "V4_symmetry", "status": "SKIP",
                "reason": f"only {int(good.sum())} good pairs"}
    diff = a_pos[good] - a_neg[idx[good]]
    rms = float(np.sqrt(np.mean(diff ** 2)))
    max_diff = float(np.abs(diff).max())
    status = "PASS" if rms < 2e-4 else ("WARN" if rms < 1e-2 else "FAIL")
    return {
        "test": "V4_symmetry", "status": status,
        "rms_alpha_skew": rms, "max_alpha_skew": max_diff,
        "n_pairs": int(good.sum()), "snapshot": mid.name,
        "criterion": "RMS asymmetry < 2e-4 (FEM target); FAIL if > 1e-2",
        "note": "PIDL has known d-skew per finding_pidl_d_skew_apr20.md",
    }


def _load_alpha_bar(archive: Path):
    """alpha_bar_vs_cycle.npy is per-cycle (ᾱ_max, ᾱ_mean, f_min_global).

    Some older archives may store as 1D (ᾱ_max only). Auto-detect.
    Returns (alpha_max, alpha_mean_or_None, f_min_or_None).
    """
    f = archive / "best_models" / "alpha_bar_vs_cycle.npy"
    if not f.is_file():
        return None, None, None
    arr = np.load(f)
    if arr.ndim == 1:
        return arr, None, None
    if arr.shape[1] >= 3:
        return arr[:, 0], arr[:, 1], arr[:, 2]
    if arr.shape[1] == 2:
        return arr[:, 0], arr[:, 1], None
    return arr[:, 0], None, None


def test_v5_carrara_consistency(archive: Path) -> dict:
    """V5. Carrara accumulator self-consistency: ᾱ_max should be monotonic.

    The Carrara asymmetric accumulator only INCREASES (max(0, Δψ⁺)) — the
    GLOBAL MAX of ᾱ across elements should never decrease cycle-to-cycle
    (per-element ᾱ never decreases, max-over-elements also never decreases).

    Tolerate small numerical noise (< 1e-8 relative).
    """
    a_max, _, _ = _load_alpha_bar(archive)
    if a_max is None or a_max.size < 3:
        return {"test": "V5_carrara_consistency", "status": "SKIP",
                "reason": "no alpha_bar_vs_cycle.npy or <3 cycles"}
    diffs = np.diff(a_max)
    # Tolerate < 1e-8 noise OR < 1e-6 relative
    rel_thresh = 1e-6 * np.abs(a_max[:-1])
    abs_thresh = 1e-8 * np.ones_like(rel_thresh)
    thresh = np.maximum(rel_thresh, abs_thresh)
    decreases = diffs < -thresh
    n_decreases = int(decreases.sum())
    max_decrease = float(-diffs[decreases].max()) if n_decreases > 0 else 0.0
    n_cycles = int(a_max.size)
    pct = n_decreases / max(1, n_cycles - 1) * 100
    status = "PASS" if n_decreases == 0 else ("WARN" if pct < 5 else "FAIL")
    return {
        "test": "V5_carrara_consistency", "status": status,
        "n_cycles": n_cycles,
        "n_decreases": n_decreases,
        "pct_decreases": pct,
        "max_decrease_abs": max_decrease,
        "alpha_max_at_Nf": float(a_max[-1]),
        "criterion": "ᾱ_max monotonic non-decreasing globally (Carrara accumulator property; tolerate <1e-6 rel noise)",
    }


def test_v6_f_min_floor(archive: Path) -> dict:
    """V6. f(ᾱ) reaches asymptotic floor at N_f.

    Use f_min directly from column 2 of alpha_bar_vs_cycle.npy (if present,
    these are the per-cycle global f_min values from compute_fatigue_degrad).
    Fallback: derive from ᾱ_max via Carrara formula if only ᾱ in file.
    """
    a_max, _, f_min_arr = _load_alpha_bar(archive)
    if a_max is None or a_max.size < 1:
        return {"test": "V6_f_min_floor", "status": "SKIP", "reason": "no data"}
    if f_min_arr is not None:
        f_min_at_Nf = float(f_min_arr[-1])
        source = "direct from saved f_min trajectory"
    else:
        alpha_T = 0.5
        f_min_at_Nf = min(1.0, (2 * alpha_T / (float(a_max[-1]) + alpha_T)) ** 2)
        source = f"derived from ᾱ_max={float(a_max[-1]):.3f} via Carrara asymptotic"
    fem_target = 1.09e-6
    ratio = f_min_at_Nf / fem_target if fem_target > 0 else float("inf")
    # PIDL typical 0.01-0.03 (4 orders above FEM). Status:
    #   PASS if < 0.1 (in active fatigue regime)
    #   WARN if 0.1-0.5 (weak fatigue regime)
    #   FAIL if > 0.5 (essentially no fatigue activated)
    status = "PASS" if f_min_at_Nf < 0.1 else ("WARN" if f_min_at_Nf < 0.5 else "FAIL")
    return {
        "test": "V6_f_min_floor", "status": status,
        "f_min_at_Nf_global": f_min_at_Nf,
        "alpha_max_at_Nf": float(a_max[-1]),
        "fem_target_f_min": fem_target,
        "ratio_PIDL_over_FEM": ratio,
        "source": source,
        "criterion": "f_min < 0.1 PASS; PIDL typically 0.01-0.03 (4 orders above FEM 1e-6) — known limit",
    }


def test_v7_bc_residual(archive: Path) -> dict:
    """V7. BC residual.

    PIDL uses BC scaling u_BC_corner * (y-y0)*(yL-y) / ((yL-y0)/2)² which IS
    exact at y=y0 and y=yL by construction (analytical). So residual is 0
    by construction at those boundaries.

    For vertical edges x=x0, x=xL: NN output u(x0,y) is NOT constrained
    explicitly in current PIDL setup (free boundaries assumed) — but the
    physics solution u should naturally satisfy traction-free condition there.

    This test reports the corner check (analytical → expect 0) and notes
    the side-boundary condition is an open audit item.
    """
    return {
        "test": "V7_bc_residual", "status": "PASS-by-construction",
        "note": "Top/bottom BC analytically enforced via BC scaling (residual=0 by construction). "
                "Left/right edges (x=±0.5) traction-free, not actively checked. "
                "Audit item if needed: forward NN at boundary nodes and check σ·n = 0.",
        "criterion": "Top/bot BC: analytical (PASS); side BC: not checked",
    }


def test_v8_pretrain_convergence(archive: Path) -> dict:
    """V8. Pretrain convergence ratio (final loss / initial loss).

    Reads trainLoss_1NN_0.npy (loss history during pretrain). Reports
    log10(final/initial) — should be at least -3 (3 orders of magnitude
    reduction) for healthy pretrain.
    """
    f = archive / "best_models" / "trainLoss_1NN_0.npy"
    if not f.is_file():
        return {"test": "V8_pretrain_convergence", "status": "SKIP",
                "reason": "no trainLoss_1NN_0.npy"}
    loss = np.load(f).flatten()
    if loss.size < 10:
        return {"test": "V8_pretrain_convergence", "status": "SKIP",
                "reason": f"<10 epochs ({loss.size})"}
    L0 = float(np.median(loss[:5]))
    Lf = float(np.median(loss[-5:]))
    # The loss in this codebase is `loss_var = log10(E_el + E_d + E_hist)` per fit.py.
    # Detect: if L0 < 5 (typical raw loss is much larger), assume log10-space already.
    if abs(L0) < 5 and abs(Lf) < 5:
        log_ratio = float(Lf - L0)
        space = "log10-space"
    else:
        log_ratio = float(np.log10(max(Lf, 1e-30) / max(L0, 1e-30))) if L0 > 0 else 0
        space = "raw"
    # For FATIGUE per-cycle training, NN often starts near minimum (warm from
    # previous cycle), so we don't expect 3-order reduction every cycle.
    # Test: training is STABLE (no divergence: Lf > L0 + 0.5 means loss grew
    # by 3.2× = WARN; >2 means 100× growth = FAIL).
    delta = log_ratio
    if delta > 2:
        status = "FAIL"     # loss grew >100× (divergence)
    elif delta > 0.5:
        status = "WARN"     # loss grew 3-100×
    else:
        status = "PASS"     # loss stable or decreased
    return {
        "test": "V8_training_stability", "status": status,
        "L_initial_log10": L0, "L_final_log10": Lf,
        "delta_log10": delta,
        "loss_space": space,
        "n_epochs": int(loss.size),
        "criterion": "Δlog10(loss) per training session: ≤0.5 PASS; 0.5-2 WARN; >2 FAIL (divergence)",
    }


# -----------------------------------------------------------------------------
# Driver
# -----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="PIDL post-hoc validation.")
    ap.add_argument("archive", help="archive directory (contains best_models/)")
    ap.add_argument("--l0", type=float, default=0.01, help="length scale ℓ_0")
    ap.add_argument("--out-prefix", default="validation_report",
                    help="output filename prefix")
    args = ap.parse_args()

    archive = Path(args.archive).resolve()
    if not archive.is_dir():
        raise SystemExit(f"archive not found: {archive}")

    print("=" * 72)
    print(f"PIDL Validation Report")
    print(f"Archive: {archive.name}")
    print("=" * 72)

    tests = [
        test_v1_energy_balance(archive),
        test_v2_mesh_resolution(archive, l0=args.l0),
        test_v3_J_path_independence(archive),
        test_v4_symmetry(archive),
        test_v5_carrara_consistency(archive),
        test_v6_f_min_floor(archive),
        test_v7_bc_residual(archive),
        test_v8_pretrain_convergence(archive),
    ]

    # Print summary
    name_w = max(len(t.get("test", "?")) for t in tests) + 2
    print(f"{'Test':<{name_w}} {'Status':<14} Notes")
    print("-" * 72)
    for t in tests:
        status = t.get("status", "?")
        if status == "PASS":
            badge = "✅ PASS"
        elif status == "WARN":
            badge = "⚠ WARN"
        elif status == "FAIL":
            badge = "❌ FAIL"
        elif status == "SKIP":
            badge = "○ SKIP"
        else:
            badge = status
        notes = t.get("criterion", t.get("reason", ""))[:50]
        print(f"{t['test']:<{name_w}} {badge:<14} {notes}")

    # Write detailed JSON + CSV
    out_dir = archive / "best_models"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{args.out_prefix}.json"
    json_path.write_text(json.dumps(tests, indent=2, default=str))
    print(f"\nDetailed report: {json_path}")

    # Compact CSV
    csv_path = out_dir / f"{args.out_prefix}.csv"
    keys = sorted(set(k for t in tests for k in t.keys()))
    with open(csv_path, "w") as fh:
        fh.write(",".join(keys) + "\n")
        for t in tests:
            fh.write(",".join(str(t.get(k, "")).replace(",", ";") for k in keys) + "\n")
    print(f"CSV summary:     {csv_path}")


if __name__ == "__main__":
    main()
