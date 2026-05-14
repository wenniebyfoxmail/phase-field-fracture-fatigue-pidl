#!/usr/bin/env python3
"""analyze_sdf_ribbon_smoke.py — sphere-of-influence + N=5 GO/NO-GO gate

Compares one or more SDF ribbon smoke archives against the locked baseline
(u=0.12, seed=1, N=300) at:
  hl_8_..._fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12 / best_models /

Gate criteria (per design_sdf_dedem_may14.md, May-14 verified):

  GO      : α_bar_max(c5) ≥ 2.7945  OR
            (Kt(c5) ≥ 9.7544 AND ψ_tip(c5) ≥ 0.4979)
  NO-GO   : ≥ 3 of 4 scalar metrics ≤ 1.1× baseline  AND visual α broken
  gray    : everything else — adjudicate via seed-2 sign consistency

Caveats baked in (see design memo for derivation):
  - baseline Kt drops slightly through c0..c5 (slope −0.011/cyc); the
    Kt(c5)/Kt(c0) ratio gate (≥ 1.20) is checked alongside the single-point.
  - baseline x_tip stays at 0 through c5; x_tip(c5) ≥ 0.02 = strong-positive,
    but x_tip stuck near 0 is NOT a NO-GO at this short cycle count.
  - ψ_tip = psi_peak_vs_cycle.npy column 1 (col 0 = cycle_idx).

Usage:
    python3 analyze_sdf_ribbon_smoke.py <archive_path> [<archive_path> ...]

Example:
    python3 analyze_sdf_ribbon_smoke.py \\
        hl_8_..._sdfRibbon_eps0.001_uv_only \\
        hl_8_..._sdfRibbon_eps0.0005_uv_only \\
        hl_8_..._sdfRibbon_eps0.002_uv_only \\
        hl_8_..._sdfRibbon_eps0.001_uv_only_seed2
"""
import sys
from pathlib import Path
import numpy as np


# ─── locked baseline ──────────────────────────────────────────────────────
BASE_REL = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
            "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
            "N300_R0.0_Umax0.12")
# Cycle to read the gate at:
C_GATE = 5


def load_metrics(archive_path: Path):
    """Return dict of per-cycle arrays. Raises if any required file missing."""
    bm = archive_path / "best_models"
    if not bm.is_dir():
        raise FileNotFoundError(f"{bm} does not exist")
    out = {}
    out["alpha_bar"] = np.load(bm / "alpha_bar_vs_cycle.npy")    # (N, 3) cols [max, mean, ?]
    out["Kt"]        = np.load(bm / "Kt_vs_cycle.npy")           # (N,)
    psi_path = bm / "psi_peak_vs_cycle.npy"
    if psi_path.exists():
        psi              = np.load(psi_path)                     # (N, 5) col1 = ψ_tip
        out["psi_tip"]   = psi[:, 1]
    else:
        out["psi_tip"]   = None                                  # ribbon archives lack this
    # x_tip — baseline has only x_tip_vs_cycle.npy; ribbon has
    # x_tip_alpha_vs_cycle.npy + x_tip_psi_vs_cycle.npy
    xt = None
    for fn in ("x_tip_alpha_vs_cycle.npy", "x_tip_vs_cycle.npy",
               "x_tip_psi_vs_cycle.npy"):
        p = bm / fn
        if p.exists():
            xt = np.load(p)
            break
    if xt is None:
        raise FileNotFoundError(f"no x_tip*.npy in {bm}")
    out["x_tip"] = xt
    return out


def evaluate(name: str, m: dict, base: dict):
    """Print 7-row comparison + verdict."""
    n = min(C_GATE + 1, len(m["alpha_bar"]))
    if n <= C_GATE:
        print(f"  [{name}] only {len(m['alpha_bar'])} cycles available; "
              f"reading last cycle {n-1} instead of c{C_GATE}")
    c = n - 1
    # Use the LAST cycle of this archive, not a hard-coded C_GATE.
    # If archive has n cycles, last = n-1. baseline ref also at n-1 for fair compare.
    c_run  = len(m["alpha_bar"]) - 1
    c_ref  = c_run                              # compare to baseline at same cycle index
    a_b   = float(m["alpha_bar"][c_run, 0])
    kt_5  = float(m["Kt"][c_run])
    kt_0  = float(m["Kt"][0])
    psi_5 = float(m["psi_tip"][c_run]) if m["psi_tip"] is not None else None
    xt_5  = float(m["x_tip"][c_run])

    a_b_base   = float(base["alpha_bar"][c_ref, 0])
    kt_5_base  = float(base["Kt"][c_ref])
    kt_0_base  = float(base["Kt"][0])
    psi_5_base = float(base["psi_tip"][c_ref])  if base["psi_tip"] is not None else None
    xt_5_base  = float(base["x_tip"][c_ref])

    print(f"  archive: {name}")
    print(f"    (comparing at c{c_run}; archive has {c_run+1} cycles)")

    ratios = {
        f"α_bar_max(c{c_run})":     a_b / a_b_base   if a_b_base   else float("nan"),
        f"Kt(c{c_run})":            kt_5 / kt_5_base if kt_5_base  else float("nan"),
        f"Kt(c{c_run})/Kt(c0)":     (kt_5 / kt_0) / (kt_5_base / kt_0_base),
    }
    if psi_5 is not None and psi_5_base is not None:
        ratios[f"ψ_tip(c{c_run})"] = psi_5 / psi_5_base if psi_5_base else float("nan")

    print(f"    α_bar_max  = {a_b:7.4f}   (base {a_b_base:7.4f}, "
          f"ratio {ratios[f'α_bar_max(c{c_run})']:5.2f}×)  thr ≥ {a_b_base*1.3:.4f}")
    print(f"    Kt(c{c_run})     = {kt_5:7.4f}  (base {kt_5_base:7.4f}, "
          f"ratio {ratios[f'Kt(c{c_run})']:5.2f}×)  thr ≥ {kt_5_base*1.3:.4f}")
    print(f"    Kt(c{c_run})/Kt(c0) = {(kt_5/kt_0):5.3f}  (base "
          f"{kt_5_base/kt_0_base:5.3f}, normalized ratio {ratios[f'Kt(c{c_run})/Kt(c0)']:5.2f}×)  thr ≥ 1.20")
    if psi_5 is not None and psi_5_base is not None:
        print(f"    ψ_tip      = {psi_5:7.4f}  (base {psi_5_base:7.4f}, "
              f"ratio {ratios[f'ψ_tip(c{c_run})']:5.2f}×)  thr ≥ {psi_5_base*1.3:.4f}")
    else:
        print(f"    ψ_tip      = N/A (psi_peak_vs_cycle.npy not in ribbon archive)")
    print(f"    x_tip(c{c_run})  = {xt_5:7.4f}  (base {xt_5_base:7.4f})  "
          f"strong+ ≥ 0.02; <0.005 is NOT NO-GO")

    # ─── combined verdict ────────────────────────────────────────────────
    a_go   = ratios[f"α_bar_max(c{c_run})"] >= 1.30
    kt_go  = ratios[f"Kt(c{c_run})"]        >= 1.30
    psi_go = (ratios.get(f"ψ_tip(c{c_run})", 0) >= 1.30)
    has_psi = f"ψ_tip(c{c_run})" in ratios

    n_low = sum(r <= 1.10 for r in ratios.values())

    if a_go or (kt_go and (psi_go if has_psi else True)):
        verdict = "GO" if has_psi else "GO (ψ_tip absent; based on α_bar_max + Kt only)"
    elif n_low >= len(ratios) - 1:
        verdict = f"NO-GO ({n_low}/{len(ratios)} scalar metrics ≤ 1.1×; please confirm with visual α inspection)"
    else:
        verdict = "GRAY (adjudicate via seed-2 / visual)"

    print(f"    >>> verdict: {verdict}")
    print()
    return ratios, verdict


def find_baseline(here: Path) -> Path:
    """Look for the locked baseline archive.

    Search order (worktree-aware):
      1. ./<BASE_REL>                                  (same SENS_tensile)
      2. <repo-root>/SENS_tensile/<BASE_REL>           (up to git root)
      3. walk parents up to 6 levels, look for "SENS_tensile/<BASE_REL>"
    """
    candidates = [here / BASE_REL]
    for n in range(1, 7):
        candidates.append(here.parents[n] / "SENS_tensile" / BASE_REL)
        if (here.parents[n] / ".git").exists():
            break
    for c in candidates:
        if (c / "best_models").is_dir():
            return c
    raise FileNotFoundError(
        f"could not locate baseline archive {BASE_REL!r} anywhere from {here}; "
        f"tried: " + ", ".join(str(c) for c in candidates))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    here = Path(__file__).resolve().parent
    base_archive = find_baseline(here)
    print("=" * 78)
    print("SDF ribbon smoke — sphere-of-influence + N=5 gate")
    print(f"baseline: {base_archive.name}")
    print("=" * 78)
    base = load_metrics(base_archive)

    print(f"\nbaseline cycle reference (c0..c{C_GATE}):")
    print(f"  cycle | α_bar_max |   Kt    | ψ_tip  | x_tip")
    for c in range(C_GATE + 1):
        print(f"  c{c}    | {base['alpha_bar'][c,0]:8.4f}  | "
              f"{base['Kt'][c]:7.4f} | {base['psi_tip'][c]:6.4f} | "
              f"{base['x_tip'][c]:6.4f}")
    print()

    results = {}
    for arch_arg in sys.argv[1:]:
        # Try abs / cwd-relative / script-dir-relative / baseline-sibling.
        candidates = [Path(arch_arg).resolve()]
        rel = Path(arch_arg)
        if not rel.is_absolute():
            candidates += [(here / rel).resolve(),
                           (base_archive.parent / rel).resolve()]
        p = next((c for c in candidates if (c / "best_models").is_dir()),
                 candidates[0])
        try:
            m = load_metrics(p)
        except FileNotFoundError as e:
            print(f"  SKIP {arch_arg}: {e}\n")
            continue
        results[p.name] = evaluate(p.name, m, base)

    # ─── seed consistency (when GPU3 + GPU6 both present) ────────────────
    s1 = [n for n in results if "_uv_only" in n and "seed2" not in n
                                                and "s2" not in n]
    s2 = [n for n in results if ("seed2" in n or "s2" in n) and "_uv_only" in n]
    if s1 and s2:
        print("=" * 78)
        print("seed reproducibility check (GPU3 vs GPU6 — same ε=1e-3, uv_only)")
        print("=" * 78)
        rs1, vs1 = results[s1[0]]
        rs2, vs2 = results[s2[0]]
        same_sign = True
        for k in rs1:
            sgn1 = 1 if rs1[k] > 1.0 else -1
            sgn2 = 1 if rs2[k] > 1.0 else -1
            ok = sgn1 == sgn2
            same_sign &= ok
            mark = "✓" if ok else "✗"
            print(f"  {mark} {k}: s1={rs1[k]:5.2f}×  s2={rs2[k]:5.2f}×")
        print(f"  overall sign-consistent: {same_sign}")


if __name__ == "__main__":
    main()
