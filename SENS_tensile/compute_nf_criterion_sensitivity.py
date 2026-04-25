#!/usr/bin/env python3
"""
compute_nf_criterion_sensitivity.py — N_f sensitivity analysis (G4 / expert review Apr 25)

For each existing PIDL archive with `alpha_bar_vs_cycle.npy` + `E_el_vs_cycle.npy`,
compute N_f under multiple alternative criteria and tabulate:

  C1 ᾱ_max ≥ 5         (early plastic indicator)
  C2 ᾱ_max ≥ 10        (memory-default informal threshold)
  C3 f_min ≤ 0.1       (10% degradation at hottest element)
  C4 f_min ≤ 0.01      (1% degradation, near-fracture)
  C5 E_el ≤ 0.7·E_el,max (energy drop 30%)
  C6 E_el ≤ 0.5·E_el,max (energy drop 50%)
  C7 archive name suffix `_NfXX_real_fracture` (the runtime-confirmed N_f)

If trends across criteria are consistent, the N_f-based S-N comparison is
robust. If criteria disagree by >20%, the comparison depends on choice.

Usage:
    cd "upload code/SENS_tensile"
    python compute_nf_criterion_sensitivity.py [--csv out.csv]
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent


def parse_archive_nf(name: str) -> int | None:
    """Extract N_f from archive directory name suffix `_NfXX_real_fracture`."""
    m = re.search(r"_Nf(\d+)_", name)
    return int(m.group(1)) if m else None


def first_index_meeting(arr: np.ndarray, condition_fn) -> int | None:
    """Return first index where condition_fn(arr[i]) is True; None otherwise."""
    mask = condition_fn(arr)
    if not mask.any():
        return None
    return int(np.argmax(mask))   # first True


def analyze_archive(archive_dir: Path) -> dict | None:
    """Compute N_f under various criteria for one archive directory."""
    abar_p = archive_dir / "best_models" / "alpha_bar_vs_cycle.npy"
    eel_p = archive_dir / "best_models" / "E_el_vs_cycle.npy"
    if not abar_p.exists():
        return None
    abar = np.load(str(abar_p))
    if abar.ndim != 2 or abar.shape[1] < 3:
        return None
    a_max = abar[:, 0]
    a_mean = abar[:, 1]
    f_min = abar[:, 2]

    eel = None
    if eel_p.exists():
        eel = np.load(str(eel_p))
        if eel.ndim > 1:
            eel = eel.ravel()

    result = {
        "archive": archive_dir.name,
        "n_save": len(a_max),
        "name_Nf": parse_archive_nf(archive_dir.name),
        # ᾱ_max-based
        "C1_amax_ge_5":  first_index_meeting(a_max, lambda x: x >= 5),
        "C2_amax_ge_10": first_index_meeting(a_max, lambda x: x >= 10),
        # f_min-based
        "C3_fmin_le_0.1":  first_index_meeting(f_min, lambda x: x <= 0.1),
        "C4_fmin_le_0.01": first_index_meeting(f_min, lambda x: x <= 0.01),
    }
    if eel is not None and len(eel) > 5:
        eel_max = float(eel.max())
        result["E_el_max"] = eel_max
        result["C5_E_drop_30pct"] = first_index_meeting(eel, lambda x: x <= 0.7 * eel_max)
        result["C6_E_drop_50pct"] = first_index_meeting(eel, lambda x: x <= 0.5 * eel_max)
    else:
        result["C5_E_drop_30pct"] = None
        result["C6_E_drop_50pct"] = None
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="nf_criterion_sensitivity.csv",
                        help="Output CSV filename")
    parser.add_argument("--filter", default="",
                        help="Only include archives whose name contains this substring")
    args = parser.parse_args()

    archives = [d for d in HERE.iterdir()
                if d.is_dir() and "fatigue_on" in d.name and "Umax" in d.name
                and "fatigue_off" not in d.name and "_mono" not in d.name]
    if args.filter:
        archives = [a for a in archives if args.filter in a.name]

    rows = []
    for a in sorted(archives):
        res = analyze_archive(a)
        if res is not None:
            rows.append(res)

    # Print summary table
    if not rows:
        print("No archives with required data found.")
        return 1

    keys = ["archive", "n_save", "name_Nf",
            "C1_amax_ge_5", "C2_amax_ge_10",
            "C3_fmin_le_0.1", "C4_fmin_le_0.01",
            "C5_E_drop_30pct", "C6_E_drop_50pct"]
    print(f"\n{'Archive (last 60 chars)':<60} "
          f"{'n':>4} {'name':>5} {'C1':>4} {'C2':>4} {'C3':>4} {'C4':>4} {'C5':>4} {'C6':>4}")
    print("=" * 110)
    for r in rows:
        archive_short = r["archive"][-60:]
        line = f"{archive_short:<60} {r['n_save']:>4} "
        for k in keys[2:]:
            v = r.get(k)
            line += f"{(v if v is not None else '--'):>5}"
        print(line)

    # Per-archive: spread between criteria
    print("\nCriterion spread per archive (max - min over C1-C6, ignoring None):")
    print(f"{'Archive':<60} {'min':>5} {'max':>5} {'spread':>7} {'%spread':>8}")
    print("=" * 90)
    spreads = []
    for r in rows:
        crit_vals = [r[k] for k in ("C1_amax_ge_5", "C2_amax_ge_10",
                                    "C3_fmin_le_0.1", "C4_fmin_le_0.01",
                                    "C5_E_drop_30pct", "C6_E_drop_50pct")
                     if r.get(k) is not None]
        if not crit_vals:
            continue
        cmin, cmax = min(crit_vals), max(crit_vals)
        spread = cmax - cmin
        pct = 100 * spread / max(cmax, 1)
        spreads.append((r["archive"][-60:], cmin, cmax, spread, pct))
        print(f"{r['archive'][-60:]:<60} {cmin:>5} {cmax:>5} {spread:>7} {pct:>7.1f}%")

    print(f"\nMedian criterion spread: {np.median([s[4] for s in spreads]):.1f}%")
    print(f"Max criterion spread:    {max(s[4] for s in spreads):.1f}%")
    print(f"Min criterion spread:    {min(s[4] for s in spreads):.1f}%")

    # Save CSV
    csv_path = HERE / args.csv
    with open(csv_path, "w") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            f.write(",".join(str(r.get(k, "")) for k in keys) + "\n")
    print(f"\n→ CSV saved to {csv_path}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
