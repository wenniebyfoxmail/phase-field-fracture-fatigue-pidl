#!/usr/bin/env python3
"""
extract_f_mean.py — Compute f_mean (domain average of fatigue degradation
function f(ᾱ)) per cycle from checkpoint files.

Our existing alpha_bar_vs_cycle.npy only stores [alpha_bar_max, alpha_bar_mean,
f_min] — the column "f_mean" is NOT saved. This script reads hist_fat (ᾱ
field) from each checkpoint_step_{j}.pt and computes f_mean post-hoc using
the Carrara asymptotic formula:

    f(ᾱ) = 1                          for ᾱ ≤ α_T
    f(ᾱ) = [2 α_T / (ᾱ + α_T)]^2      for ᾱ > α_T

Output:
    <model_dir>/best_models/f_mean_vs_cycle.npy   shape (N,)
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

import numpy as np
import torch


def compute_f_mean(hist_fat: torch.Tensor, alpha_T: float) -> float:
    """Carrara asymptotic fatigue degradation, mean over all elements."""
    f = torch.where(
        hist_fat <= alpha_T,
        torch.ones_like(hist_fat),
        (2.0 * alpha_T / (hist_fat + alpha_T)) ** 2
    )
    return float(f.mean().item())


def run_one(model_dir: Path, alpha_T: float = 0.5) -> np.ndarray:
    bm = model_dir / "best_models"
    ckpt_files = sorted(bm.glob("checkpoint_step_*.pt"),
                        key=lambda p: int(p.stem.split("_")[-1]))
    if not ckpt_files:
        raise FileNotFoundError(f"No checkpoint_step_*.pt in {bm}")

    results = []
    for p in ckpt_files:
        j = int(p.stem.split("_")[-1])
        try:
            data = torch.load(str(p), map_location='cpu', weights_only=True)
        except Exception:
            data = torch.load(str(p), map_location='cpu')
        hist_fat = data.get('hist_fat')
        if hist_fat is None:
            print(f"  cycle {j}: no hist_fat → skip")
            continue
        f_mean = compute_f_mean(hist_fat, alpha_T)
        a_max = float(hist_fat.max().item())
        a_mean = float(hist_fat.mean().item())
        results.append([j, f_mean, a_max, a_mean])

    arr = np.array(results)
    out_file = bm / "f_mean_vs_cycle.npy"
    np.save(str(out_file), arr)
    print(f"  → saved {out_file.name}  ({len(arr)} cycles)")
    return arr


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model-dir", required=True)
    p.add_argument("--alpha-T", type=float, default=0.5)
    args = p.parse_args()

    d = Path(args.model_dir)
    if not d.is_dir():
        d = Path(__file__).parent / args.model_dir
    if not d.is_dir():
        print(f"Directory not found: {args.model_dir}")
        return 1

    print(f"Processing {d.name}")
    arr = run_one(d, args.alpha_T)

    # Summary
    print(f"\nSummary (cycle, f_mean, α_max, α_mean):")
    for i in [0, len(arr)//4, len(arr)//2, 3*len(arr)//4, len(arr)-1]:
        if 0 <= i < len(arr):
            r = arr[i]
            print(f"  cycle {int(r[0]):>3}: f_mean={r[1]:.4f}  α_max={r[2]:>7.2f}  α_mean={r[3]:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
