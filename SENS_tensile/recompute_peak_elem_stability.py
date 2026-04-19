#!/usr/bin/env python3
"""
recompute_peak_elem_stability.py — 测量 peak ψ⁺ element 在连续 cycle 之间的位置稳定性。

研究背景
--------
Williams Run #4 的关键发现：Williams 在每个瞬时确实集中了 ψ⁺（peak ψ⁺ ~5×
baseline at cycle 30），但 α_max 反而比 baseline 低 → damage 更分散。

假说：因为 `field_comp.x_tip` 每圈用 ψ⁺ centroid 更新 → Williams features 的
参考点漂移 → peak ψ⁺ element 在不同 cycle 之间漂移 → 没有任何单个 element
持续累积 ᾱ。Baseline 的 peak 更宽但站着不动 → 特定 element 持续吃 ᾱ。

本脚本量化"peak 漂移程度"：

    For K ∈ {1, 3, 10}:
        Jaccard(top_K@cycle_n, top_K@cycle_{n-1}) ∈ [0, 1]
        1.0 = peak 完全站着不动
        0.0 = peak 完全跳到不同位置

预期：
    Baseline:  Jaccard 高（~0.8+），peak 稳定
    Williams:  Jaccard 低（~0.3-0.5），peak 随 x_tip 漂
    Fourier:   未知 — 关键 falsification test
        - 如果 Jaccard 高且 α_max 高 → 假说成立，stationary basis 是关键
        - 如果 Jaccard 高但 α_max 不高 → 假说被推翻，是其他机制
        - 如果 Jaccard 低 → 即使 fixed B，34D 高频基函数本身让 NN 预测不稳

用法
----
    cd "upload code/SENS_tensile"   # 或 worktree 内的对应目录
    python recompute_peak_elem_stability.py [--model-dir <path>]

不传 --model-dir：处理三个默认 dir（baseline + williams_v4 + 当前 fourier）
传 --model-dir：单独处理一个

输出（每个 model_dir 的 best_models/ 内）：
    peak_elem_ids_vs_cycle.npy           shape (N, 10)
        每行：cycle j 的 top-10 peak ψ⁺ element 编号（按 ψ⁺ 降序）
    peak_elem_stability_vs_cycle.npy     shape (N-1, 4)
        列：[cycle_j, top1_persisted, top3_jaccard, top10_jaccard]
        cycle_j 是 jaccard 比较的"右端"圈号（即 j vs j-1）
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

import numpy as np
import torch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "source"))

# config.py 读 sys.argv 拿网络规模，这里给固定的 8x400 seed=1
_saved_argv = sys.argv
sys.argv = ["recompute_peak_elem_stability.py", "8", "400", "1", "TrainableReLU", "1.0"]
from config import (domain_extrema, loading_angle, network_dict, mat_prop_dict,
                    numr_dict, PFF_model_dict, crack_dict,
                    device, fatigue_dict)
sys.argv = _saved_argv

from field_computation import FieldComputation
from construct_model import construct_model
from compute_energy import get_psi_plus_per_elem
from input_data_from_mesh import prep_input_data

fine_mesh_file = str(HERE / 'meshed_geom2.msh')


def detect_run_type(model_dir: Path) -> str:
    """从目录名推断 run 类型：baseline / williams / fourier"""
    name = model_dir.name.lower()
    if "fourier" in name:
        return "fourier"
    if "williams" in name:
        return "williams"
    return "baseline"


def list_default_dirs(fourier_worktree_root: Path | None) -> list[tuple[str, Path]]:
    """返回默认要处理的 (label, dir) — 主仓库 baseline + williams_v4 archive，
    以及（如果 fourier_worktree_root 存在）worktree 里的 Fourier 当前 run dir。"""
    main_tensile = HERE if HERE.name == "SENS_tensile" and "worktrees" not in str(HERE) \
                   else Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile")
    tag = ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1"
           "_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5"
           "_N300_R0.0_Umax0.12")
    candidates = [
        ("baseline",   main_tensile / tag),
        ("williams_v4", main_tensile / f"{tag}_williams_std_v4_cycle87_Nf77_real_fracture"),
    ]
    if fourier_worktree_root is not None:
        candidates.append(
            ("fourier_nf16",
             fourier_worktree_root / "SENS_tensile" / f"{tag}_fourier_nf16_sig1.0")
        )
    return [(lbl, p) for lbl, p in candidates if (p / "best_models").is_dir()]


def build_run_context(run_type: str, model_dir: Path):
    """根据 run_type 构造与训练时一致的 FieldComputation + 物理对象。

    返回：(field_comp, pffmodel, matprop, inp, T_conn, area_T, x_tip_history)
        x_tip_history: Williams 时是 ndarray，否则 None
    """
    williams_dict = None
    fourier_dict_local = None
    if run_type == "williams":
        williams_dict = {"enable": True, "theta_mode": "atan2", "r_min": 1e-6}
    elif run_type == "fourier":
        b_file = model_dir / "best_models" / "fourier_B.pt"
        if not b_file.exists():
            raise FileNotFoundError(f"Fourier run missing fourier_B.pt: {b_file}")
        fourier_dict_local = {"enable": True, "n_freq": 16, "sigma": 1.0, "seed": 42}

    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
        williams_dict=williams_dict,
        fourier_dict=fourier_dict_local,
    )

    inp, T_conn, area_T, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict,
        mesh_file=fine_mesh_file, device=device)

    fc = FieldComputation(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.0], device=device),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=williams_dict,
        l0=mat_prop_dict["l0"],
        fourier_dict=fourier_dict_local,
        device=device,
    )
    fc.net = fc.net.to(device)
    fc.domain_extrema = fc.domain_extrema.to(device)
    fc.theta = fc.theta.to(device)

    # 强制覆盖 fourier_B 为训练时落盘的那个（确保 byte-identical）
    if run_type == "fourier":
        fc.fourier_B = torch.load(str(model_dir / "best_models" / "fourier_B.pt"),
                                   map_location='cpu', weights_only=True).to(device)

    # Williams: 加载 x_tip 历史
    x_tip_history = None
    if run_type == "williams":
        for fname in ("x_tip_psi_vs_cycle.npy", "x_tip_alpha_vs_cycle.npy",
                      "x_tip_vs_cycle.npy"):
            p = model_dir / "best_models" / fname
            if p.exists():
                x_tip_history = np.load(str(p))
                break

    return fc, pffmodel, matprop, inp, T_conn, area_T, x_tip_history


def collect_peak_elem_ids(model_dir: Path, run_type: str, top_K: int = 10,
                          max_cycles: int | None = None) -> np.ndarray:
    """遍历 trained_1NN_j.pt，每圈计算 ψ⁺_per_elem 并记录 top-K element id（按 ψ⁺ 降序）。

    返回 shape (N_cycles, top_K) ndarray of int。
    """
    best = model_dir / "best_models"
    fc, pffmodel, matprop, inp, T_conn, area_T, x_tip_history = build_run_context(run_type, model_dir)

    lmbda_val = float(fatigue_dict.get('disp_max', 0.12))

    rows = []
    j = 0
    while True:
        ckpt = best / f"trained_1NN_{j}.pt"
        if not ckpt.is_file():
            break
        if max_cycles is not None and j >= max_cycles:
            break

        # Williams: 用每圈 saved x_tip
        if run_type == "williams" and x_tip_history is not None and j < len(x_tip_history):
            fc.x_tip = float(x_tip_history[j])

        fc.lmbda = torch.tensor(lmbda_val, device=device)
        fc.net.load_state_dict(
            torch.load(str(ckpt), map_location='cpu', weights_only=True))
        fc.net.eval()

        with torch.no_grad():
            u, v, alpha = fc.fieldCalculation(inp)
            psi_plus = get_psi_plus_per_elem(
                inp, u, v, alpha, matprop, pffmodel, area_T, T_conn)

        psi_np = psi_plus.cpu().numpy()
        # 按 ψ⁺ 降序取 top_K element 编号
        top_ids = np.argsort(psi_np)[::-1][:top_K].astype(np.int32)
        rows.append(top_ids)

        if j % 10 == 0 or j < 5:
            print(f"  cycle {j:>3}: top1_id={top_ids[0]}  "
                  f"psi[top1]={psi_np[top_ids[0]]:.3e}")

        j += 1

    arr = np.array(rows, dtype=np.int32)
    out = best / "peak_elem_ids_vs_cycle.npy"
    np.save(str(out), arr)
    print(f"  → saved {out.name}  shape={arr.shape}")
    return arr


def compute_stability(ids: np.ndarray) -> np.ndarray:
    """ids shape (N, K). 返回 stability shape (N-1, 4) = [cycle_j, top1_persisted, top3_jaccard, top10_jaccard]"""
    N, K = ids.shape
    assert K >= 10, f"need top_K >= 10, got {K}"
    out = np.zeros((N - 1, 4), dtype=np.float32)
    for j in range(1, N):
        prev = ids[j - 1]
        curr = ids[j]
        # top-1: 二值（同一 element 即 1，否则 0）
        top1 = float(curr[0] == prev[0])
        # top-3: Jaccard
        s_p3, s_c3 = set(prev[:3]), set(curr[:3])
        top3 = len(s_p3 & s_c3) / max(len(s_p3 | s_c3), 1)
        # top-10: Jaccard
        s_p10, s_c10 = set(prev[:10]), set(curr[:10])
        top10 = len(s_p10 & s_c10) / max(len(s_p10 | s_c10), 1)
        out[j - 1] = [j, top1, top3, top10]
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default=None,
                        help="单独处理一个 dir；不传则跑默认三个")
    parser.add_argument("--max-cycles", type=int, default=None,
                        help="限制处理的 cycle 数（debug 用）")
    parser.add_argument("--top-k", type=int, default=10,
                        help="记录 top-K element ID（默认 10，需 >= 10）")
    parser.add_argument("--fourier-worktree",
                        default="/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/.claude/worktrees/exp/fourier-feature",
                        help="Fourier worktree 根目录（用来定位默认的 Fourier output dir）")
    args = parser.parse_args()

    if args.model_dir:
        d = Path(args.model_dir).resolve()
        targets = [(d.name, d)]
    else:
        ft_root = Path(args.fourier_worktree) if args.fourier_worktree else None
        targets = list_default_dirs(ft_root)

    if not targets:
        print("没找到任何 model dir。")
        return 1

    for label, d in targets:
        print(f"\n=== {label}: {d.name} ===")
        run_type = detect_run_type(d)
        print(f"  run_type = {run_type}")

        # 1. collect peak elem IDs
        ids_file = d / "best_models" / "peak_elem_ids_vs_cycle.npy"
        if ids_file.exists():
            print(f"  reusing existing {ids_file.name}")
            ids = np.load(str(ids_file))
        else:
            ids = collect_peak_elem_ids(d, run_type, top_K=max(args.top_k, 10),
                                         max_cycles=args.max_cycles)

        if len(ids) < 2:
            print(f"  too few cycles ({len(ids)}) for stability — skip")
            continue

        # 2. compute stability
        stab = compute_stability(ids)
        out = d / "best_models" / "peak_elem_stability_vs_cycle.npy"
        np.save(str(out), stab)
        print(f"  → saved {out.name}  shape={stab.shape}")

        # 3. 简短摘要
        # 排除尾部几圈（fracture 后伪解 → ψ⁺ 数值假象）
        tail_cut = 5
        body = stab[:-tail_cut] if len(stab) > tail_cut + 5 else stab
        print(f"  [body, excl. last {tail_cut} cycles]")
        print(f"    top1_persisted   mean={body[:,1].mean():.3f}  "
              f"(fraction of cycles where peak elem stays put)")
        print(f"    top3_jaccard     mean={body[:,2].mean():.3f}")
        print(f"    top10_jaccard    mean={body[:,3].mean():.3f}")

    print("\nDone. 三组都跑完后用 plot_peak_elem_stability.py 画对比图。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
