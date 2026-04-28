#!/usr/bin/env python3
"""
analyze_alpha2_t4.py — α-2 T4 stationarity diagnostic.

Reads psi_argmax_vs_cycle.npy from a training archive and computes:
  - peak_stability_modal = (cycles staying on most-frequent argmax) / total cycles
  - peak_stability_run   = longest consecutive run of same argmax / total
  - n_unique             = number of distinct argmax elements over the run
  - transitions          = count of cycle-to-cycle argmax changes

Targets per design_alpha2_multihead_apr28.md:
  baseline    ~5-10% modal
  α-1 mesh    ~10-20% modal
  α-2 (PASS)  ≥70% modal

Usage:
    python analyze_alpha2_t4.py <archive_dir>
    python analyze_alpha2_t4.py <archive_dir1> <archive_dir2> ...   # compare
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np


def analyze(archive_dir: Path):
    f = archive_dir / 'best_models' / 'psi_argmax_vs_cycle.npy'
    if not f.is_file():
        f = archive_dir / 'psi_argmax_vs_cycle.npy'
    if not f.is_file():
        return None, f"NOT FOUND: {f}"
    arr = np.load(f)
    n = len(arr)
    if n == 0:
        return None, "empty array"
    vals, counts = np.unique(arr, return_counts=True)
    modal = vals[np.argmax(counts)]
    modal_count = counts.max()
    # longest consecutive run
    run = best_run = 1
    for i in range(1, n):
        if arr[i] == arr[i-1]:
            run += 1
            best_run = max(best_run, run)
        else:
            run = 1
    transitions = int(np.sum(arr[1:] != arr[:-1]))
    metrics = {
        'archive': archive_dir.name,
        'n_cycles': n,
        'n_unique': len(vals),
        'modal_idx': int(modal),
        'modal_count': int(modal_count),
        'peak_stability_modal': modal_count / n,
        'peak_stability_run': best_run / n,
        'transitions': transitions,
        'first_5': arr[:5].tolist(),
        'last_5': arr[-5:].tolist(),
    }
    return metrics, None


def fmt(metrics):
    m = metrics
    pass_modal = "✅ PASS" if m['peak_stability_modal'] >= 0.70 else (
        "⚠ MARGINAL" if m['peak_stability_modal'] >= 0.50 else "❌ FAIL")
    return (
        f"  Archive:                {m['archive']}\n"
        f"  n_cycles:               {m['n_cycles']}\n"
        f"  n_unique argmax:        {m['n_unique']}\n"
        f"  modal element idx:      {m['modal_idx']} (count {m['modal_count']})\n"
        f"  peak_stability_modal:   {m['peak_stability_modal']:.3f}  {pass_modal}\n"
        f"  peak_stability_run:     {m['peak_stability_run']:.3f}\n"
        f"  transitions:            {m['transitions']}\n"
        f"  first 5 argmax:         {m['first_5']}\n"
        f"  last 5 argmax:          {m['last_5']}\n"
    )


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    print("=" * 60)
    print("α-2 T4 stationarity diagnostic")
    print("=" * 60)
    print("Targets: baseline ~5-10%; α-1 ~10-20%; α-2 PASS ≥70% modal\n")
    for arg in sys.argv[1:]:
        p = Path(arg)
        m, err = analyze(p)
        if err:
            print(f"[{p.name}] SKIP — {err}\n")
            continue
        print(fmt(m))


if __name__ == '__main__':
    main()
