#!/usr/bin/env python3
"""
analyze_peak_dwell.py — 量化每个 element 在 top-K peak ψ⁺ 集合里"驻留"的总 cycle 数。

目的
----
recompute_peak_elem_stability.py 给出了"两个连续 cycle 之间 peak set 重叠率"
（Jaccard），但发现 baseline 和 Williams 的 peak 都极度漂移（Jaccard ≈ 0.1-0.25）。

更深一步的问题：**某个 element 在整个训练过程中累计有多少 cycle 在 top-K**？
- 如果某些 element 经常在 top-K（dwell 多）→ 它们持续吃 ψ⁺ → ᾱ 累积多 → α_max 高
- 如果 dwell 均匀分布在很多 element 上（每个只待几次）→ 没有 element 持续累积

预期对应关系：
    max(dwell_count) ↑   →   α_max ↑   （某 element 长期被砸）
    unique_elements_ever_in_top_K ↑   →   α_max ↓   （turnover 高）

输入
----
读取 model_dir/best_models/peak_elem_ids_vs_cycle.npy （shape (N, 10)）
    by recompute_peak_elem_stability.py

可选读取 alpha_bar_vs_cycle.npy 拿 α_max 时间序列做对照。

输出
----
打印对比表 + 保存 dwell histogram 数据（每个 element 在 top-K 出现的次数分布）：
    model_dir/best_models/peak_dwell_distribution.npy
    shape (n_unique_elems, 4)   columns: [elem_id, dwell_top1, dwell_top3, dwell_top10]
"""
from __future__ import annotations
from pathlib import Path
import sys

import numpy as np


def analyze_one(model_dir: Path, label: str, exclude_post_fracture: int = 5):
    """读取一个 dir 的 peak_elem_ids 并算 dwell 分布。"""
    best = model_dir / "best_models"
    ids_file = best / "peak_elem_ids_vs_cycle.npy"
    if not ids_file.exists():
        print(f"[{label}] missing {ids_file.name}, skip")
        return None

    ids = np.load(str(ids_file))   # shape (N, K)
    if ids.ndim != 2 or ids.size == 0:
        print(f"[{label}] peak_elem_ids has shape {ids.shape} — no usable data, skip")
        return None
    N, K = ids.shape
    if K < 10 or N < 3:
        print(f"[{label}] need K>=10 and N>=3, got shape {ids.shape}")
        return None

    # 排除尾部 N_f 后的伪解 cycle（N_f 后 ψ⁺ 数值崩塌，peak 元素是 noise）
    body = ids[:-exclude_post_fracture] if N > exclude_post_fracture + 5 else ids
    Nb = len(body)

    # 每个 element 在 top-1 / top-3 / top-10 出现的次数
    from collections import Counter
    cnt_top1  = Counter(body[:, 0].tolist())
    cnt_top3  = Counter(body[:, :3].flatten().tolist())
    cnt_top10 = Counter(body[:, :10].flatten().tolist())

    # 合并所有曾出现过的 element
    all_elems = set(cnt_top10.keys())
    rows = []
    for e in sorted(all_elems):
        rows.append([int(e),
                     int(cnt_top1.get(e, 0)),
                     int(cnt_top3.get(e, 0)),
                     int(cnt_top10.get(e, 0))])
    arr = np.array(rows, dtype=np.int32)

    # 关键统计
    n_unique_top1  = len(cnt_top1)
    n_unique_top3  = len(set(body[:, :3].flatten()))
    n_unique_top10 = len(all_elems)
    max_dwell_top1  = max(cnt_top1.values())
    max_dwell_top10 = max(cnt_top10.values())

    # α_max 末尾值（如果有的话）
    abar_file = best / "alpha_bar_vs_cycle.npy"
    alpha_max_at_Nf = float('nan')
    if abar_file.exists():
        abar = np.load(str(abar_file))   # shape (N, 3): [α_max, α_mean, f_min]
        if len(abar) >= Nb:
            alpha_max_at_Nf = float(abar[Nb-1, 0])

    out_file = best / "peak_dwell_distribution.npy"
    np.save(str(out_file), arr)

    print(f"\n[{label}]  body cycles = {Nb}  (excluded last {exclude_post_fracture})")
    print(f"  top1:   {n_unique_top1:>4} unique elems ever held peak;  "
          f"max dwell = {max_dwell_top1:>3}  ({max_dwell_top1/Nb*100:.1f}% of cycles)")
    print(f"  top3:   {n_unique_top3:>4} unique elems ever in top-3")
    print(f"  top10:  {n_unique_top10:>4} unique elems ever in top-10;  "
          f"max dwell = {max_dwell_top10:>3}  ({max_dwell_top10/Nb*100:.1f}% of cycles)")
    print(f"  α_max @ end of body = {alpha_max_at_Nf:.3f}")
    print(f"  → saved {out_file.name}")

    # 高频 element 列表（top-10 dwell ≥ 25% of cycles）
    threshold = max(int(0.25 * Nb), 3)
    high = [(e, c) for e, c in cnt_top10.items() if c >= threshold]
    high.sort(key=lambda x: -x[1])
    if high:
        print(f"  elements with dwell ≥ {threshold} cycles:")
        for e, c in high[:8]:
            print(f"    elem {int(e):>5}:  in top-10 for {c:>3} cycles  ({c/Nb*100:.1f}%)")

    return {
        "label": label,
        "Nb": Nb,
        "alpha_max_at_Nf": alpha_max_at_Nf,
        "n_unique_top1": n_unique_top1,
        "n_unique_top3": n_unique_top3,
        "n_unique_top10": n_unique_top10,
        "max_dwell_top1": max_dwell_top1,
        "max_dwell_top10": max_dwell_top10,
    }


def main():
    main_tensile = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile")
    fourier_dir  = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/.claude/worktrees/exp/fourier-feature/SENS_tensile")
    tag = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1"
           "_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5"
           "_N300_R0.0_Umax0.12")

    candidates = [
        ("baseline",     main_tensile / tag),
        ("williams_v4",  main_tensile / f"{tag}_williams_std_v4_cycle87_Nf77_real_fracture"),
        ("fourier_nf16", fourier_dir  / f"{tag}_fourier_nf16_sig1.0"),
    ]

    summaries = []
    for label, d in candidates:
        if not (d / "best_models" / "peak_elem_ids_vs_cycle.npy").exists():
            print(f"[{label}] no peak_elem_ids_vs_cycle.npy yet, skip")
            continue
        s = analyze_one(d, label)
        if s:
            summaries.append(s)

    # ────────── 总结对比表 ──────────
    if len(summaries) >= 2:
        print("\n" + "=" * 70)
        print("SUMMARY (low n_unique = peak focused; high max_dwell = element favored)")
        print("=" * 70)
        print(f"{'label':<14}  {'Nb':>4}  {'α_max':>7}  "
              f"{'uniq_top1':>10}  {'uniq_top10':>10}  "
              f"{'max_dwell_top1':>15}  {'max_dwell_top10':>16}")
        for s in summaries:
            print(f"{s['label']:<14}  {s['Nb']:>4}  {s['alpha_max_at_Nf']:>7.2f}  "
                  f"{s['n_unique_top1']:>10}  {s['n_unique_top10']:>10}  "
                  f"{s['max_dwell_top1']:>15}  {s['max_dwell_top10']:>16}")


if __name__ == "__main__":
    main()
