"""
=============================================================================
model_train.py  ★ 相比 Manav 原始版本的修改
=============================================================================
★ 修改点（与原始对比）：
   1. train() 新增 fatigue_dict=None 参数
   2. 新增 from compute_energy import get_psi_plus_per_elem
   3. 新增 from fatigue_history import update_fatigue_history, compute_fatigue_degrad
   4. 主训练循环末尾：当 fatigue_on=True 时
        - 计算当前步各单元 ψ⁺
        - 更新疲劳历史变量 ᾱ
        - 重新计算疲劳退化函数 f(ᾱ)
   5. fit() / fit_with_early_stopping() 调用时传入 f_fatigue

   当 fatigue_dict=None 或 fatigue_on=False 时：
        f_fatigue 始终为标量 1.0，行为与 Manav 原始代码完全一致。
=============================================================================
"""

import numpy as np
import torch
from torch.utils.data import DataLoader
import time
from pathlib import Path
import matplotlib
matplotlib.use('Agg')          # 非交互后端，训练中安全调用
import matplotlib.pyplot as plt
import matplotlib.tri as tri

from input_data_from_mesh import prep_input_data
from fit import fit, fit_with_early_stopping
from optim import *
from plotting import plot_field

# ★ 新增：疲劳相关函数（仅在 fatigue_on=True 时实际调用）
from compute_energy import get_psi_plus_per_elem, compute_energy
from fatigue_history import (update_fatigue_history, compute_fatigue_degrad,
                              mirror_y_indices, mirror_alpha_y)

# ★ Direction 4: Williams ψ⁺ 重心估计裂尖坐标（可选，仅在 williams_enabled=True 时调用）
from williams_features import compute_x_tip_psi

# ★ 2026-05-13 Branch 2 C6: FI-PINN adaptive sampling via full-residual reweight
from adaptive_sampling import compute_adaptive_weights


# ── α 场快照辅助函数 ────────────────────────────────────────────────────────
def _save_alpha_snapshot(inp, alpha, T_conn, cycle, snapshot_dir):
    """保存第 cycle 圈的 α 场：
    - PNG  → alpha_snapshots/alpha_cycle_{cycle:04d}.png  （可视化）
    - npy  → alpha_snapshots/alpha_cycle_{cycle:04d}.npy  （数值，供 FEM 对比）
              shape (N_nodes, 3)，列: [x, y, alpha]
    """
    inp_np   = inp.detach().cpu().numpy()
    alpha_np = alpha.detach().cpu().numpy().flatten()
    T_np     = T_conn.detach().cpu().numpy() if torch.is_tensor(T_conn) else T_conn

    # ── PNG ───────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.set_aspect('equal')
    if T_np is not None:
        tpc = ax.tripcolor(inp_np[:, 0], inp_np[:, 1], T_np, alpha_np,
                           shading='gouraud', vmin=0, vmax=1, cmap='plasma')
    else:
        tpc = ax.tripcolor(inp_np[:, 0], inp_np[:, 1], alpha_np,
                           shading='gouraud', vmin=0, vmax=1, cmap='plasma')
    plt.colorbar(tpc, ax=ax, label='α')
    ax.set_title(f'α field – cycle {cycle:04d}')
    plt.tight_layout()
    plt.savefig(snapshot_dir / f'alpha_cycle_{cycle:04d}.png', dpi=200)
    plt.close(fig)

    # ── npy: (N_nodes, 3) → [x, y, alpha] ────────────────────────────────────
    field_data = np.column_stack([inp_np[:, 0], inp_np[:, 1], alpha_np])
    np.save(snapshot_dir / f'alpha_cycle_{cycle:04d}.npy', field_data)


# ── 裂缝尖端检测（通用，基于 L∞ 距离）──────────────────────────────────────
def get_crack_tip(alpha_vals, node_coords, crack_mouth_xy, threshold=0.9,
                  x_min=None):
    """
    返回裂缝尖端坐标和 L∞ 裂缝长度（max(|Δx|, |Δy|)）。

    参数
    ----
    alpha_vals    : torch.Tensor, shape (N,)   — 各节点相场值
    node_coords   : torch.Tensor, shape (N, 2) — 各节点 (x, y) 坐标
    crack_mouth_xy: torch.Tensor, shape (2,)   — 初始裂缝尖端坐标（SENS: [0.0, 0.0]）
    threshold     : float                      — α > threshold 认为属于裂缝带
    x_min         : float | None               — 只搜索 x > x_min 的节点（排除预制裂缝）
                                                 SENS: 传入 crack_mouth_xy[0] = 0.0

    返回
    ----
    crack_tip_xy  : torch.Tensor, shape (2,)   — 裂缝尖端坐标（L∞意义下最远点）
    crack_length  : float                      — L∞ 裂缝长度 = max(|Δx|, |Δy|)

    说明
    ----
    使用 L∞（Chebyshev）距离而非欧式距离：
      - 欧式距离对斜裂缝偏大（到对角 ≈0.707），会导致阈值不一致
      - L∞ 距离等价于"在 x 或 y 方向的最大投影"，与域边界距离（0.5）直接可比
      - 判据 crack_length >= 0.46 意味着：任意方向投影达到 92% 域半宽 → 贯通
    x_min 过滤原因：
      - 预制裂缝节点（x ∈ [-0.5, 0]）在 t=0 就是 α≈1 的永久损伤
      - 不加过滤时 L∞(crack_mouth → 预制裂缝左端) = 0.5，从第1圈就误触发
      - 只搜索 x > crack_mouth_x 确保只追踪新扩展部分
    """
    damaged = alpha_vals > threshold
    # 排除预制裂缝：只保留 x > x_min 的受损节点
    if x_min is not None:
        forward = node_coords[:, 0] > x_min
        damaged = damaged & forward
    if damaged.sum() == 0:
        return crack_mouth_xy, 0.0
    d_coords  = node_coords[damaged]
    delta     = (d_coords - crack_mouth_xy).abs()          # |Δx|, |Δy| per node
    linf_dist = delta.max(dim=1).values                    # max(|Δx|, |Δy|) per node
    idx       = linf_dist.argmax()
    return d_coords[idx], linf_dist[idx].item()


def train(field_comp, disp, pffmodel, matprop, crack_dict, numr_dict,
          optimizer_dict, training_dict, coarse_mesh_file, fine_mesh_file,
          device, trainedModel_path, intermediateModel_path, writer,
          fatigue_dict=None,                         # ★ 新增参数
          mit8_dict=None,                            # ★ MIT-8 supervised warmup
          adaptive_sampling_dict=None,               # ★ 2026-05-13 Branch 2 C6
          sidecar_S1_dict=None,                      # ★ 2026-05-12 sidecar S1 (static-tip oversample)
          sidecar_S2_dict=None):                     # ★ 2026-05-13 sidecar S2 (adaptive / tip-following / score-driven)
    '''
    Neural network training: pretraining with a coarser mesh in the first
    stage before the main training proceeds.

    ★ 新增 fatigue_dict 参数：
        None 或 fatigue_on=False → 完全等价 Manav 原始行为。
        fatigue_on=True          → 循环加载 + 疲劳历史变量更新。

    fatigue_dict 字段说明：
        fatigue_on    : bool  – 总开关
        loading_type  : str   – 'monotonic' | 'cyclic'
        accum_type    : str   – 'carrara' | 'golahmar'
        degrad_type   : str   – 'asymptotic' | 'logarithmic'
        alpha_T       : float – 疲劳阈值（归一化）
        n_power       : float – Golahmar 幂律指数
        alpha_n       : float – Golahmar 归一化能量密度
        kappa         : float – 对数退化参数
    '''

    # =========================================================================
    # 解析 fatigue_dict（若未传入或 fatigue_on=False，疲劳功能静默关闭）
    # =========================================================================
    if fatigue_dict is None:
        fatigue_dict = {}
    fatigue_on = fatigue_dict.get('fatigue_on', False)
    _hard_irr_cfg = fatigue_dict.get('hard_irreversibility', {})
    _hard_irr_enabled = bool(_hard_irr_cfg.get('enable', False))
    if hasattr(field_comp, 'set_hard_irreversibility'):
        field_comp.set_hard_irreversibility(_hard_irr_enabled)
    if _hard_irr_enabled:
        print(
            "[HardIrreversibility] enabled: "
            "alpha = hist_alpha + (1 - hist_alpha) * alpha_free; E_hist weight = 0"
        )

    def _set_hard_irrev_floor(hist_alpha_t, label):
        if _hard_irr_enabled and hasattr(field_comp, 'set_hist_alpha_floor'):
            field_comp.set_hist_alpha_floor(hist_alpha_t)
            print(
                f"[HardIrreversibility] floor set ({label}): "
                f"nodes={hist_alpha_t.numel()} max={hist_alpha_t.max().item():.4f} "
                f"mean={hist_alpha_t.mean().item():.4e}"
            )

    # =========================================================================
    # ★ Early mutex guards for sidecar S2 (added 2026-05-14, expert review).
    # Fires before any pretrain compute so a misconfigured config fails fast.
    # The runner already disables conflicting variants, but callers who edit
    # config directly (bypassing the runner) would otherwise silently train
    # for one cycle before crashing inside fit() on a shape-mismatched
    # crack_tip_weights tensor.
    # =========================================================================
    _S2_check = sidecar_S2_dict is not None and sidecar_S2_dict.get('enable', False)
    if _S2_check:
        if sidecar_S1_dict is not None and sidecar_S1_dict.get('enable', False):
            raise ValueError(
                "sidecar S1 and S2 are mutually exclusive — both refine the "
                "fine mesh. Disable one in config or the runner."
            )
        _adapt_chk = (adaptive_sampling_dict if adaptive_sampling_dict is not None
                      else fatigue_dict.get('adaptive_sampling', {}))
        if isinstance(_adapt_chk, dict) and _adapt_chk.get('enable', False):
            raise ValueError(
                "sidecar S2 and adaptive_sampling_dict (C6 FI-PINN reweight) "
                "are mutually exclusive: S2 changes mesh size per cycle while "
                "C6 writes per-element crack_tip_weights → next cycle shape "
                "mismatch in compute_energy. Disable one."
            )
        _tipw_chk = fatigue_dict.get('tip_weight_cfg', {})
        if isinstance(_tipw_chk, dict) and _tipw_chk.get('enable', False):
            raise ValueError(
                "sidecar S2 and fatigue_dict.tip_weight_cfg (Direction 3) are "
                "mutually exclusive: both touch crack_tip_weights on a mesh "
                "that S2 mutates per cycle. Disable one."
            )

    # =========================================================================
    # 阶段1：预训练（粗网格，fatigue 始终关闭，与 Manav 原始完全一致）
    # ★ 若已有预训练权重（中断续训），直接加载并跳过预训练
    # =========================================================================
    _init_ckpt = trainedModel_path / Path('trained_1NN_initTraining.pt')
    if _init_ckpt.exists():
        # ── 断点续训：跳过预训练 ──────────────────────────────────────────────
        print(f"[Checkpoint] 检测到预训练权重，跳过预训练")
        field_comp.net.load_state_dict(
            torch.load(_init_ckpt, map_location=device))
    else:
        # ── 从头训练：执行预训练 ──────────────────────────────────────────────
        # Pretrain stays on the unrefined coarse mesh — S1 targets the main
        # fatigue stage on the fine mesh only (the coarse mesh is already
        # fine near the initial crack and refining it adds no signal while
        # slowing pretrain).
        inp, T_conn, area_T, hist_alpha = prep_input_data(
            matprop, pffmodel, crack_dict, numr_dict,
            mesh_file=coarse_mesh_file, device=device,
            sidecar_S1_dict=None, sidecar_label="coarse"
        )
        _set_hard_irrev_floor(hist_alpha, "coarse pretrain")
        outp = torch.zeros(inp.shape[0], 1).to(device)
        training_set = DataLoader(
            torch.utils.data.TensorDataset(inp, outp),
            batch_size=inp.shape[0], shuffle=False
        )
        field_comp.lmbda = torch.tensor(disp[0]).to(device)

        loss_data = list()
        start = time.time()

        # L-BFGS 快速收敛 + RPROP 精细调整
        n_epochs = max(optimizer_dict["n_epochs_LBFGS"], 1)
        NNparams = field_comp.parameters()
        optimizer = get_optimizer(NNparams, "LBFGS")
        loss_data1 = fit(
            field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
            optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
            intermediateModel_path=None, writer=writer, training_dict=training_dict,
            hist_loss_weight=0.0 if _hard_irr_enabled else 1.0,
            # 预训练不传 f_fatigue，使用默认值 1.0
        )
        loss_data = loss_data + loss_data1

        n_epochs = optimizer_dict["n_epochs_RPROP"]
        NNparams = field_comp.parameters()
        optimizer = get_optimizer(NNparams, "RPROP")
        loss_data2 = fit_with_early_stopping(
            field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
            optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
            min_delta=optimizer_dict["optim_rel_tol_pretrain"],
            intermediateModel_path=None, writer=writer, training_dict=training_dict,
            hist_loss_weight=0.0 if _hard_irr_enabled else 1.0,
        )
        loss_data = loss_data + loss_data2

        end = time.time()
        print(f"Execution time: {(end-start)/60:.03f}minutes")

        torch.save(field_comp.net.state_dict(), _init_ckpt)
        with open(trainedModel_path / Path('trainLoss_1NN_initTraining.npy'), 'wb') as f:
            np.save(f, np.asarray(loss_data))

    # =========================================================================
    # 阶段2：主训练（细网格 + 增量/循环加载）
    # =========================================================================

    inp, T_conn, area_T, hist_alpha = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict,
        mesh_file=fine_mesh_file, device=device,
        sidecar_S1_dict=sidecar_S1_dict, sidecar_label="fine"
    )
    _set_hard_irrev_floor(hist_alpha, "fine initial")
    outp = torch.zeros(inp.shape[0], 1).to(device)
    training_set = DataLoader(
        torch.utils.data.TensorDataset(inp, outp),
        batch_size=inp.shape[0], shuffle=False
    )

    # =========================================================================
    # ★ 2026-05-13 sidecar S2 (adaptive refinement) — stash original mesh
    # and initialize per-original-mesh state buffers. The actual per-cycle
    # mesh swap happens at the TOP of the for-loop body (see below).
    # =========================================================================
    # ★ 2026-05-14 expert review v2: hist_fat / psi_plus_prev are now maintained
    # in CURRENT (refined) mesh coordinates throughout the run, and carried
    # across cycle swaps via centroid-nearest transport (preserves sub-parent
    # variation, unlike aggregate-then-expand). Only the S2b score still
    # aggregates to ORIGINAL coords (needed so select_top_score_elements
    # operates on the canonical reference mesh — refinement is always
    # one-step from original to keep mesh size bounded).
    _S2_enabled = _S2_check   # already validated by early mutex guards above
    _S2_state = None
    if _S2_enabled:
        if numr_dict['gradient_type'] != 'numerical':
            raise NotImplementedError(
                "sidecar S2 currently only supports gradient_type='numerical' "
                f"(got {numr_dict['gradient_type']!r})"
            )
        from utils import parse_mesh as _parse_mesh
        _Xo, _Yo, _To, _ao = _parse_mesh(filename=str(fine_mesh_file), gradient_type='numerical')
        _n_orig = int(_To.shape[0])
        _hyst_frac = float(sidecar_S2_dict.get('hysteresis_fraction', 0.25))
        _hyst = _hyst_frac * float(sidecar_S2_dict.get('r_tip_sample', 0.05))
        _S2_state = {
            # Original (canonical reference) mesh — never mutated
            'X_orig': _Xo, 'Y_orig': _Yo, 'T_orig': _To, 'area_orig': _ao,
            'n_elem_orig': _n_orig,
            # Current refined mesh — starts as identity (= original unrefined)
            'X_curr': _Xo.copy(), 'Y_curr': _Yo.copy(),
            'T_curr': _To.copy(), 'area_curr': _ao.copy(),
            'parent_curr': np.arange(_n_orig, dtype=np.int64),  # identity mapping
            'tip_at_refine': None,    # forces first refinement on cycle 0
            # Per-element accumulated state in CURRENT mesh coords
            'hist_fat_curr': np.zeros(_n_orig, dtype=np.float64),
            'psi_plus_prev_curr': np.zeros(_n_orig, dtype=np.float64),
            # ★ v3.2 (2026-05-15): per-NODE irreversibility floor in CURRENT mesh
            # coords. Initialized lazily on first swap (cycle 0 uses hist_alpha_init).
            # Carried across subsequent REFINE swaps via conservative
            # edge-lineage transport + NN-max floor, so retained nodes preserve
            # built-up α and new midpoint nodes take max(endpoint_a, endpoint_b).
            # Previously v2 re-evaluated hist_alpha via NN.fieldCalculation each
            # swap; theoretically equivalent (NN is smooth so midpoint ≈ avg of
            # endpoints), but in practice S2a N=100 plateaued at -42% vs S1 from
            # cycle 20 onward. Explicit conservative transport rules out any
            # subtle NN-snapshot vs accumulated-floor mismatch as the cause.
            'hist_alpha_curr': None,
            'X_curr_nodes': _Xo.copy(),  # node coords at last refine; for transport
            'Y_curr_nodes': _Yo.copy(),
            # v4 cumulative add-only memory.  This is the monotone union of
            # accepted tip disks; it must survive resume.
            'past_tips': [],
            # S2b: detached score aggregated to ORIGINAL for next cycle's top-K
            'score_orig_for_next': None,
            'score_curr': None,
            # Hysteresis: skip re-refinement when tip hasn't moved by this L¹ distance
            'hysteresis': _hyst,
            # Stats
            'n_swaps': 0, 'n_skips': 0,
        }
        print(
            f"[sidecar-S2] enabled (mode={sidecar_S2_dict.get('mode','tip_following')}); "
            f"refine_mode={sidecar_S2_dict.get('refine_mode','cumulative')}; "
            f"r_tip_sample={sidecar_S2_dict.get('r_tip_sample',0.05)}; "
            f"target_fraction={sidecar_S2_dict.get('target_fraction',0.07)}; "
            f"hysteresis_frac={_hyst_frac} -> threshold={_hyst:.4f}; "
            f"original mesh: {_n_orig} elem | transport: nearest-element (KDTree)"
        )

    # -------------------------------------------------------------------------
    # ★ 疲劳变量初始化（仅 fatigue_on=True 时使用；否则下面 if 块永不执行）
    # -------------------------------------------------------------------------
    n_elem = area_T.shape[0]
    if fatigue_on:
        hist_fat      = torch.zeros(n_elem, device=device)
        psi_plus_prev = torch.zeros(n_elem, device=device)
        f_fatigue     = torch.ones(n_elem, device=device)
        print(f"[Fatigue] fatigue_on=True | accum='{fatigue_dict.get('accum_type','carrara')}' | "
              f"degrad='{fatigue_dict.get('degrad_type','asymptotic')}' | "
              f"alpha_T={fatigue_dict.get('alpha_T', 1.0):.4g}")

        # ★ Direction 6.1 + 2026-05-08 A1: 预计算元素形心
        # Used by: (a) spatial α_T modulation; (b) post-hoc mirror α ratchet break
        _sp_cfg     = fatigue_dict.get('spatial_alpha_T', {})
        _mirror_cfg = fatigue_dict.get('mirror_alpha_y',  {})
        _need_centroids = (
            (_sp_cfg.get('enable', False) and T_conn is not None) or
            (_mirror_cfg.get('enable', False) and T_conn is not None)
        )
        if _need_centroids:
            _Tc = T_conn if isinstance(T_conn, torch.Tensor) else torch.as_tensor(T_conn, device=device)
            _cx_t = (inp[_Tc[:,0], 0] + inp[_Tc[:,1], 0] + inp[_Tc[:,2], 0]) / 3.0
            _cy_t = (inp[_Tc[:,0], 1] + inp[_Tc[:,1], 1] + inp[_Tc[:,2], 1]) / 3.0
            elem_centroids = torch.stack([_cx_t, _cy_t], dim=1).detach()
            if _sp_cfg.get('enable', False):
                print(f"[spAlphaT] Spatial α_T enabled: "
                      f"β={_sp_cfg.get('beta',0.0)}, r_T={_sp_cfg.get('r_T',0.1)}, "
                      f"tip=({_sp_cfg.get('x_tip',0.0)},{_sp_cfg.get('y_tip',0.0)}) | "
                      f"n_elem={n_elem}")
            if _mirror_cfg.get('enable', False):
                print(f"[mirrorα] Post-hoc mirror α (A1) enabled: "
                      f"hist_fat symmetrized about y=0 each cycle | n_elem={n_elem}")
        else:
            elem_centroids = None
            if _sp_cfg.get('enable', False):
                print("[spAlphaT] WARNING: enable=True but T_conn is None "
                      "(autodiff mode); fallback to scalar α_T")
            if _mirror_cfg.get('enable', False):
                print("[mirrorα] WARNING: enable=True but T_conn is None "
                      "(autodiff mode); mirror α NOT applied")

        # Pre-compute mirror index map once (mesh fixed across cycles)
        _mirror_idx = None
        if _mirror_cfg.get('enable', False) and elem_centroids is not None:
            _mirror_idx = mirror_y_indices(elem_centroids)
            _resid = ((elem_centroids[_mirror_idx, 1] + elem_centroids[:, 1]).abs().mean().item())
            print(f"[mirrorα] mirror_idx pre-computed; mean |y_i + y_mirror[i]| = {_resid:.3e}")
    else:
        f_fatigue = 1.0
        elem_centroids = None
        print("[Fatigue] fatigue_on=False → 等价 Manav 原始行为")

    # ★ 方向3：裂尖自适应权重初始化
    # tip_weight_cfg = None 或 fatigue_dict 内的子字典 "tip_weight_cfg"
    # 初始 cycle（pretraining 完成后第 1 圈）无权重（均匀），之后从 psi_plus_elem 计算
    _tip_w_cfg         = fatigue_dict.get('tip_weight_cfg', None)   # None → 关闭
    crack_tip_weights  = None   # 当前循环的权重（None = 均匀）
    if _tip_w_cfg and _tip_w_cfg.get('enable', False):
        print(f"[TipWeight] 裂尖自适应加权已启用: β={_tip_w_cfg.get('beta',2.0)}, "
              f"p={_tip_w_cfg.get('power',1.0)}, "
              f"从 cycle {_tip_w_cfg.get('start_cycle',1)} 开始")
    else:
        _tip_w_cfg = None   # 统一置 None，后续只需判断 if _tip_w_cfg

    # ★ 2026-05-13 Branch 2 C6: FI-PINN adaptive sampling (reweight variant)
    # Mutually exclusive with tip_weight_cfg (both write into crack_tip_weights).
    _adapt_cfg = adaptive_sampling_dict if (
        adaptive_sampling_dict and adaptive_sampling_dict.get('enable', False)
    ) else None
    if _adapt_cfg is not None and _tip_w_cfg is not None:
        raise ValueError(
            "Mutual-exclusion violation: fatigue_dict['tip_weight_cfg'] and "
            "adaptive_sampling_dict cannot both be enabled (both write into "
            "crack_tip_weights). Disable one in config or the runner."
        )
    if _adapt_cfg is not None:
        print(f"[AdaptiveSampling] C6 FI-PINN reweight enabled: "
              f"β={_adapt_cfg.get('beta',2.0)}, p={_adapt_cfg.get('power',1.0)}, "
              f"residual={_adapt_cfg.get('residual_source','full')}, "
              f"从 cycle {_adapt_cfg.get('start_cycle',1)} 开始")

    # ★ 2026-05-20 Wang-style gradient balancing for the irreversibility term.
    # Default is off, so the historical Deep Ritz loss is unchanged:
    # log10(E_el + E_d + E_hist).  When enabled by a runner, REFINE diagnostics
    # update lambda_hist from the ratio of physical-gradient norm to hist-term
    # gradient norm, then subsequent fit() calls use
    # log10(E_el + E_d + lambda_hist * E_hist).
    _alh_cfg = fatigue_dict.get('adaptive_lambda_hist', {})
    _alh_enabled = bool(_alh_cfg.get('enable', False))
    if _hard_irr_enabled and _alh_enabled:
        raise ValueError(
            "hard_irreversibility and adaptive_lambda_hist are mutually exclusive: "
            "hard irreversibility removes the soft E_hist penalty."
        )
    _lambda_hist = float(_alh_cfg.get('initial', 1.0))
    _lambda_hist_min = float(_alh_cfg.get('min', 1e-3))
    _lambda_hist_max = float(_alh_cfg.get('max', 1.0))
    _lambda_hist_smooth = float(_alh_cfg.get('smooth', 1.0))
    _lambda_hist_update_every = int(_alh_cfg.get('update_every', 0) or 0)
    _lambda_hist_start_cycle = int(_alh_cfg.get('start_cycle', 0) or 0)
    _lambda_hist_eps = float(_alh_cfg.get('eps', 1e-30))
    _lambda_hist_history = []
    if _lambda_hist_min <= 0 or _lambda_hist_max <= 0 or _lambda_hist_min > _lambda_hist_max:
        raise ValueError(
            "adaptive_lambda_hist requires 0 < min <= max "
            f"(got min={_lambda_hist_min}, max={_lambda_hist_max})"
        )
    _lambda_hist = float(np.clip(_lambda_hist, _lambda_hist_min, _lambda_hist_max))
    _lambda_hist_smooth = float(np.clip(_lambda_hist_smooth, 0.0, 1.0))
    if _alh_enabled:
        print(
            f"[AdaptiveLambdaHist] enabled: initial={_lambda_hist:.6g}, "
            f"clip=[{_lambda_hist_min:.3g}, {_lambda_hist_max:.3g}], "
            f"smooth={_lambda_hist_smooth:.3g}, "
            f"update_every={_lambda_hist_update_every}, "
            f"start_cycle={_lambda_hist_start_cycle}"
        )

    def _current_hist_loss_weight():
        return 0.0 if _hard_irr_enabled else _lambda_hist

    _reeq_cfg = sidecar_S2_dict.get('post_refine_reeq', {}) if _S2_enabled else {}
    _reeq_enabled = bool(_reeq_cfg.get('enable', False))
    _reeq_optimizer_name = str(_reeq_cfg.get('optimizer', 'RPROP')).upper()
    _reeq_n_epochs = int(_reeq_cfg.get('n_epochs', 3000))
    _reeq_history = []
    if _reeq_enabled:
        if _reeq_optimizer_name != 'RPROP':
            raise NotImplementedError(
                "post_refine_reeq currently supports optimizer='RPROP' only"
            )
        if _reeq_n_epochs <= 0:
            raise ValueError("post_refine_reeq requires n_epochs > 0")
        print(
            f"[PostRefineReeq] enabled: optimizer={_reeq_optimizer_name}, "
            f"max_epochs={_reeq_n_epochs}; no fatigue-history update during reeq"
        )

    # -------------------------------------------------------------------------
    # ★ 检测最新 step checkpoint，实现断点续训
    # -------------------------------------------------------------------------
    _step_ckpts = sorted(
        trainedModel_path.glob('checkpoint_step_*.pt'),
        key=lambda p: int(p.stem.rsplit('_', 1)[-1])
    )
    start_j = 0
    _did_restore = False   # ★ 标志位：True → 后续 history lists 从 .npy 初始化
    _S2_resume_restored = False
    _frac_state_from_ckpt = {}  # stash for fracture detection state from checkpoint
    if _step_ckpts:
        _latest = _step_ckpts[-1]
        _last_j = int(_latest.stem.rsplit('_', 1)[-1])
        _net_file = trainedModel_path / Path(f'trained_1NN_{_last_j}.pt')
        if _net_file.exists():
            _ckpt = torch.load(_latest, map_location=device, weights_only=False)
            field_comp.net.load_state_dict(
                torch.load(_net_file, map_location=device))
            hist_alpha = _ckpt['hist_alpha'].to(device)
            if fatigue_on:
                hist_fat      = _ckpt['hist_fat'].to(device)
                psi_plus_prev = _ckpt['psi_plus_prev'].to(device)
                f_fatigue     = compute_fatigue_degrad(
                    hist_fat, fatigue_dict, elem_centroids=elem_centroids
                )
                # ★ Stash fracture detection state (backwards-compat: old ckpts lack these keys)
                _frac_state_from_ckpt = {
                    'detected':  _ckpt.get('_frac_detected',          False),
                    'cycle':     _ckpt.get('_frac_cycle',             None),
                    'remaining': _ckpt.get('_frac_confirm_remaining', 0),
                }
            if _S2_enabled:
                _s2_ckpt = _ckpt.get('_S2_state', None)
                if _s2_ckpt is not None:
                    for _key in (
                        'X_curr', 'Y_curr', 'T_curr', 'area_curr',
                        'parent_curr', 'hist_fat_curr', 'psi_plus_prev_curr',
                        'hist_alpha_curr', 'X_curr_nodes', 'Y_curr_nodes',
                    ):
                        if _key in _s2_ckpt:
                            _S2_state[_key] = np.asarray(_s2_ckpt[_key])
                    for _key in ('score_curr', 'score_orig_for_next'):
                        if _key in _s2_ckpt and _s2_ckpt[_key] is not None:
                            _S2_state[_key] = np.asarray(_s2_ckpt[_key])
                    for _key in ('tip_at_refine', 'n_swaps', 'n_skips'):
                        if _key in _s2_ckpt:
                            _S2_state[_key] = _s2_ckpt[_key]
                    if 'past_tips' in _s2_ckpt:
                        _S2_state['past_tips'] = [
                            (float(_p[0]), float(_p[1])) for _p in _s2_ckpt['past_tips']
                        ]
                    elif (
                        sidecar_S2_dict.get('refine_mode', 'cumulative') == 'cumulative'
                        and int(_S2_state.get('n_swaps', 0)) > 0
                    ):
                        if int(_S2_state.get('n_swaps', 0)) == 1 and _S2_state.get('tip_at_refine') is not None:
                            _p = _S2_state['tip_at_refine']
                            _S2_state['past_tips'] = [(float(_p[0]), float(_p[1]))]
                        else:
                            raise NotImplementedError(
                                "cumulative sidecar S2 checkpoint is missing 'past_tips'. "
                                "This old v4 checkpoint cannot be safely resumed because "
                                "the add-only refined-tube memory would be incomplete."
                            )

                    _Xc = _S2_state['X_curr']
                    _Yc = _S2_state['Y_curr']
                    _Tc = _S2_state['T_curr']
                    _Ac = _S2_state['area_curr']
                    inp = torch.from_numpy(np.column_stack((_Xc, _Yc))).to(torch.float).to(device)
                    T_conn = torch.from_numpy(_Tc).to(torch.long).to(device)
                    area_T = torch.from_numpy(_Ac).to(torch.float).to(device)
                    n_elem = int(_Tc.shape[0])
                    _cx_c = (_Xc[_Tc[:, 0]] + _Xc[_Tc[:, 1]] + _Xc[_Tc[:, 2]]) / 3.0
                    _cy_c = (_Yc[_Tc[:, 0]] + _Yc[_Tc[:, 1]] + _Yc[_Tc[:, 2]]) / 3.0
                    elem_centroids = torch.from_numpy(
                        np.column_stack((_cx_c, _cy_c))
                    ).to(torch.float).to(device).detach()
                    hist_alpha = hist_alpha.reshape(-1).to(device)
                    if fatigue_on:
                        hist_fat = hist_fat.reshape(-1).to(device)
                        psi_plus_prev = psi_plus_prev.reshape(-1).to(device)
                        f_fatigue = compute_fatigue_degrad(
                            hist_fat, fatigue_dict, elem_centroids=elem_centroids
                        )
                    outp = torch.zeros(inp.shape[0], 1).to(device)
                    training_set = DataLoader(
                        torch.utils.data.TensorDataset(inp, outp),
                        batch_size=inp.shape[0], shuffle=False,
                    )
                    _set_hard_irrev_floor(hist_alpha, "S2 checkpoint restore")
                    _S2_resume_restored = True
                    print(
                        f"[sidecar-S2 restore] restored current mesh: "
                        f"{inp.shape[0]} nodes, {n_elem} elem | "
                        f"swaps={_S2_state['n_swaps']} skips={_S2_state['n_skips']} | "
                        f"tip_at_refine={_S2_state['tip_at_refine']}"
                    )
            if _alh_enabled and '_lambda_hist' in _ckpt:
                _lambda_hist = float(np.clip(
                    float(_ckpt['_lambda_hist']), _lambda_hist_min, _lambda_hist_max
                ))
                print(f"[AdaptiveLambdaHist] restored lambda_hist={_lambda_hist:.6g}")
            start_j = _last_j + 1
            _set_hard_irrev_floor(hist_alpha, "checkpoint restore")
            _did_restore = True
            print(f"[Checkpoint] 从 step {_last_j} 恢复，继续 step {start_j}/{len(disp)-1}")

    # -------------------------------------------------------------------------
    # ★ Helper: 从 .npy 恢复逐 cycle history list（修正长期 bug）
    # 之前 restore 只恢复 NN 权重 + hist_alpha/hist_fat，逐 cycle history lists
    # 从空 [] 开始 → 下次 save 会覆盖 .npy 丢失 cycle 0..start_j-1 的数据。
    # 本 helper：若 .npy 存在则 load + truncate 到 start_j，保证 history/NN 同步。
    # -------------------------------------------------------------------------
    def _restore_hist(fname):
        if not _did_restore:
            return []
        p = trainedModel_path / fname
        if not p.exists():
            return []
        lst = np.load(p).tolist()
        if len(lst) > start_j:
            print(f"[Restore] {fname}: truncated {len(lst)} → {start_j} cycles")
            lst = lst[:start_j]
        else:
            print(f"[Restore] {fname}: loaded {len(lst)} cycles")
        return lst

    # -------------------------------------------------------------------------
    # ★ 断裂检测 & 可视化参数（仅 fatigue_on=True 时有意义）
    # -------------------------------------------------------------------------
    E_el_history       = _restore_hist('E_el_vs_cycle.npy')      # ★ 续训时从 .npy 恢复
    E_el_max           = max(E_el_history) if E_el_history else 0.0  # ★ 从恢复的 history 算 max
    alpha_bar_history  = _restore_hist('alpha_bar_vs_cycle.npy')  # ★ 每圈 [ᾱ_max, ᾱ_mean, f_min]
    _frac_detected          = False   # 是否已触发断裂检测
    _frac_cycle             = None    # 首次检测到断裂的圈号
    _frac_confirm_remaining = 0       # 剩余确认圈数（>0 时持续观察）
    _dense_sampling         = False   # 是否进入逐圈密集采样模式
    # ★ Restore fracture detection state from checkpoint (expert rec, May-5 2026).
    # Without this, a run interrupted mid-confirmation-window would restart the counter
    # from 0, adding up to _confirm_cycles extra cycles before stopping.
    if _frac_state_from_ckpt.get('detected', False):
        _frac_detected          = True
        _frac_cycle             = _frac_state_from_ckpt['cycle']
        _frac_confirm_remaining = _frac_state_from_ckpt['remaining']
        print(f"[Checkpoint] 恢复断裂检测状态: detected at cycle {_frac_cycle}, "
              f"confirm remaining = {_frac_confirm_remaining}")

    _E_drop_ratio   = fatigue_dict.get('fracture_E_drop_ratio',   0.5)
    _confirm_cycles = fatigue_dict.get('fracture_confirm_cycles',  3)   # 边界判据已很明确，3圈即可
    _plot_every     = fatigue_dict.get('plot_every_n_cycles',      20)
    # ★ Fix A: E_el fallback 判据 warmup 期
    # 原因：cycle 0-1 NN 可能产生伪解（尤其 Williams features 下 x_tip 尚未稳定），
    # E_el 尖峰会抬高 E_el_max 基线，导致后续正常 E_el 被误判为"骤降 → 断裂"
    _E_fallback_warmup = fatigue_dict.get('E_fallback_warmup_cycles', 5)
    # ★ Run #4 fix: E_el fallback 判据总开关
    # Run #3 在 cycle 58 出现 late-cycle NN 数值尖峰（E_el 9.9e-2 vs 正常 4e-3），
    # warmup 无法防住 mid-training 的单点尖峰。对 SENT 几何，主判据 α>0.95@boundary
    # 已经足够精确（Run #2, #3 都没有误触）。默认保留 fallback 以向后兼容；
    # 对含 Williams features 或其他易产生数值尖峰的实验，应在 config 里设 False。
    _E_fallback_enabled = fatigue_dict.get('enable_E_fallback', True)

    # ★ 右边界 α 判据参数（主判据：替代旧的 L∞ 距离判据）
    # 物理含义：当目标边界面上有足够多节点的 α 超过阈值时认为贯穿
    _alpha_bdy_warn  = fatigue_dict.get('alpha_bdy_warn',      0.90)  # 触发密集采样的预警阈值
    _alpha_bdy_frac  = fatigue_dict.get('alpha_bdy_threshold', 0.95)  # 贯穿判据阈值（与 FEM 对齐）
    _alpha_bdy_nmin  = fatigue_dict.get('alpha_bdy_nmin',      3)     # 最少节点数（防单点噪声）
    # ★ 速度优化：日志降频（关键事件 Fracture?/Dense sampling/Fracture confirmed 不受控）
    _log_every       = fatigue_dict.get('log_every_n_cycles',  1)     # 默认 1 = 每步打印（旧行为）
    # 右边界节点掩码（预计算，避免每圈重复判断）
    # SENS 几何：右边界 x ≈ 0.5，取 x > 0.48 覆盖边界层节点
    _right_bdy_x_min = fatigue_dict.get('right_bdy_x_min',    0.48)
    _right_bdy_mask  = inp[:, 0] > _right_bdy_x_min           # shape (N_nodes,)，bool

    # ★ L∞ 裂缝尖端（保留用于日志和后处理，不再作为停止判据）
    _alpha_crack_thr = fatigue_dict.get('x_tip_alpha_thr', 0.90)
    _crack_mouth     = torch.tensor([0.0, 0.0], device=device)  # SENS: 预裂缝尖端
    _crack_mouth_x   = _crack_mouth[0].item()
    _x_tip_history   = _restore_hist('x_tip_alpha_vs_cycle.npy')    # ★ 续训时从 .npy 恢复

    # ★ Post-restore sanity guard: abort if the inherited checkpoint is already post-fracture.
    # Scenario: run_baseline_umax.py (buggy version) accidentally points config.model_path at
    # a DIFFERENT run's archive → step N of a u=0.12 run gets loaded as "step N of u=0.14".
    # The restore succeeds silently; without this guard the loop would just run the confirmation
    # window and produce a garbage N_f.  Fix: check crack_length from restored history.
    if _did_restore and fatigue_on and _x_tip_history:
        _restored_crack_len = float(_x_tip_history[-1])
        if _restored_crack_len >= _right_bdy_x_min:
            print(
                f"\n[Checkpoint] ABORT — restored crack tip L∞={_restored_crack_len:.4f} "
                f">= right-boundary threshold {_right_bdy_x_min} at step {_last_j}.\n"
                f"  The loaded checkpoint was saved AFTER fracture, or belongs to a "
                f"different run (archive path mismatch).\n"
                f"  Delete best_models/ for a clean start, or check config.model_path."
            )
            return

    # ★ Direction 4: Williams 特征开关 & ψ⁺ 重心裂尖历史
    # 通过 field_comp.williams_enabled 检测是否启用（无需额外参数传递）
    _williams_enabled = getattr(field_comp, 'williams_enabled', False)
    _x_tip_psi_history = _restore_hist('x_tip_psi_vs_cycle.npy')   # ★ 续训时从 .npy 恢复

    # ★ 每圈耗时记录（增量保存到 time_vs_cycle.npy）
    _time_history = _restore_hist('time_vs_cycle.npy')   # ★ 续训时从 .npy 恢复
    _lambda_hist_history = _restore_hist('lambda_hist_vs_cycle.npy') if _alh_enabled else []
    _reeq_history = _restore_hist('post_refine_reeq_vs_cycle.npy') if _reeq_enabled else []

    # ★ 每圈 Kt 日志：预计算元素形心 + 远场掩码（仅数值梯度模式有效）
    _Kt_history = _restore_hist('Kt_vs_cycle.npy')       # ★ 续训时从 .npy 恢复
    _Kt         = float('nan')   # 当前圈 Kt（初始化为 nan，日志安全输出）

    # ★ Direction 5: Enriched Ansatz 每圈记录可学习标量 c_singular
    _ansatz_enabled     = getattr(field_comp, 'ansatz_enabled', False)
    _c_singular_history = _restore_hist('c_singular_vs_cycle.npy')   # ★ 续训时从 .npy 恢复
    if fatigue_on and T_conn is not None:
        _inp_np = inp.detach().cpu().numpy()
        _T_np   = T_conn.cpu().numpy() if isinstance(T_conn, torch.Tensor) else T_conn
        _cx = (_inp_np[_T_np[:,0],0] + _inp_np[_T_np[:,1],0] + _inp_np[_T_np[:,2],0]) / 3.0
        _cy = (_inp_np[_T_np[:,0],1] + _inp_np[_T_np[:,1],1] + _inp_np[_T_np[:,2],1]) / 3.0
        _nominal_mask = (np.abs(_cy) > 0.3) & (_cx > -0.3)
        _n_nominal    = int(_nominal_mask.sum())
        print(f"[Kt logging] Nominal elements: {_n_nominal} (|y|>0.3, x>-0.3)")
    else:
        _nominal_mask = None
        _n_nominal    = 0

    # α 快照目录（与 best_models/ 同级）
    _snapshot_dir = trainedModel_path.parent / Path('alpha_snapshots')
    if fatigue_on:
        _snapshot_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 主循环：每次迭代对应一个加载步（单调模式）或一个完整循环（疲劳模式）
    # =========================================================================
    # ★ S2 + resume guard: v3.2+ checkpoints must carry the current refined mesh.
    if _S2_enabled and _did_restore and not _S2_resume_restored:
        raise NotImplementedError(
            "sidecar S2 checkpoint is missing '_S2_state'. The saved hist_fat / "
            "psi_plus_prev live in a previous cycle's refined-mesh coords and "
            "cannot be safely resumed without the current mesh snapshot."
        )

    def _s2_elem_field_diag(values_np, X_np, Y_np, T_np):
        """Compact spatial stats for S2 transport diagnostics."""
        vals = np.asarray(values_np, dtype=np.float64).ravel()
        if vals.size == 0:
            return "empty"
        imax = int(np.argmax(vals))
        cx = (X_np[T_np[:, 0]] + X_np[T_np[:, 1]] + X_np[T_np[:, 2]]) / 3.0
        cy = (Y_np[T_np[:, 0]] + Y_np[T_np[:, 1]] + Y_np[T_np[:, 2]]) / 3.0
        return (
            f"max={vals[imax]:.4f}@({cx[imax]:+.4f},{cy[imax]:+.4f}) | "
            f"p99={np.percentile(vals, 99):.4f} | mean={vals.mean():.4f}"
        )

    def _s2_elem_tensor_diag(values_t, centroids_t):
        vals = values_t.detach().cpu().numpy().ravel()
        pts = centroids_t.detach().cpu().numpy()
        if vals.size == 0:
            return "empty"
        imax = int(np.argmax(vals))
        return (
            f"max={vals[imax]:.4e}@({pts[imax, 0]:+.4f},{pts[imax, 1]:+.4f}) | "
            f"p99={np.percentile(vals, 99):.4e} | mean={vals.mean():.4e}"
        )

    def _s2_print_post_refine_grad_diag(cycle_idx, label="post-REFINE"):
        """Print per-term gradient stats before fitting."""
        params = [p for p in field_comp.parameters() if p.requires_grad]
        with torch.enable_grad():
            u_g, v_g, alpha_g = field_comp.fieldCalculation(inp)
            loss_E_el, loss_E_d, loss_hist = compute_energy(
                inp, u_g, v_g, alpha_g, hist_alpha, matprop, pffmodel,
                area_T, T_conn=T_conn, f_fatigue=f_fatigue,
                crack_tip_weights=crack_tip_weights,
            )
            total = loss_E_el + loss_E_d + _current_hist_loss_weight() * loss_hist
            terms = [
                ("E_el", loss_E_el),
                ("E_d", loss_E_d),
                ("E_hist", loss_hist),
                ("log10_total", torch.log10(total.clamp(min=1e-30))),
            ]
            print(f"  [GradDiag cycle {cycle_idx}] {label} grad norms (pre-fit)")
            stats = {}
            for name, term in terms:
                grads = torch.autograd.grad(
                    term, params, retain_graph=True, allow_unused=True
                )
                abs_sum = 0.0
                sq_sum = 0.0
                abs_max = 0.0
                n_val = 0
                for grad in grads:
                    if grad is None:
                        continue
                    g = grad.detach()
                    abs_g = g.abs()
                    abs_sum += float(abs_g.sum().item())
                    sq_sum += float((g * g).sum().item())
                    abs_max = max(abs_max, float(abs_g.max().item()))
                    n_val += int(g.numel())
                mean_abs = abs_sum / max(n_val, 1)
                l2 = sq_sum ** 0.5
                print(
                    f"    {name}: value={float(term.detach().item()):.6e} | "
                    f"grad_l2={l2:.6e} | grad_mean_abs={mean_abs:.6e} | "
                    f"grad_max_abs={abs_max:.6e}"
                )
                stats[name] = {
                    "value": float(term.detach().item()),
                    "grad_l2": l2,
                    "grad_mean_abs": mean_abs,
                    "grad_max_abs": abs_max,
                }
            del u_g, v_g, alpha_g, loss_E_el, loss_E_d, loss_hist, total
            return stats

    def _update_lambda_hist_from_grad_stats(cycle_idx, label):
        """Update lambda_hist using Wang-style per-term parameter-gradient balance."""
        nonlocal _lambda_hist
        _grad_stats = _s2_print_post_refine_grad_diag(cycle_idx, label=label)
        _phys_grad = max(
            _grad_stats.get("E_el", {}).get("grad_l2", 0.0),
            _grad_stats.get("E_d", {}).get("grad_l2", 0.0),
        )
        _hist_grad = _grad_stats.get("E_hist", {}).get("grad_l2", 0.0)
        _lambda_hat = _phys_grad / max(_hist_grad, _lambda_hist_eps)
        _lambda_hat = float(np.clip(
            _lambda_hat, _lambda_hist_min, _lambda_hist_max
        ))
        _lambda_prev = _lambda_hist
        _lambda_hist = (
            (1.0 - _lambda_hist_smooth) * _lambda_hist
            + _lambda_hist_smooth * _lambda_hat
        )
        _lambda_hist = float(np.clip(
            _lambda_hist, _lambda_hist_min, _lambda_hist_max
        ))
        print(
            f"  [AdaptiveLambdaHist cycle {cycle_idx}] {label} | "
            f"phys_grad=max(E_el,E_d)={_phys_grad:.6e} | "
            f"hist_grad={_hist_grad:.6e} | "
            f"lambda_hat={_lambda_hat:.6e} | "
            f"lambda_hist {_lambda_prev:.6e}->{_lambda_hist:.6e}"
        )
        return _grad_stats

    for j, disp_i in enumerate(disp[start_j:], start=start_j):
        field_comp.lmbda = torch.tensor(disp_i).to(device)
        if (j % _log_every == 0) or _frac_detected or _dense_sampling:
            print(f'idx: {j}; displacement/amplitude: {field_comp.lmbda}')
        loss_data = list()
        start = time.time()
        _s2_refined_this_cycle = False

        # ------------------------------------------------------------------
        # ★ 2026-05-14 sidecar S2 v2 (expert review): per-cycle mesh
        # decision = hysteresis on tip motion. When tip has moved past
        # `hysteresis` (L¹ distance), build a NEW refined mesh and TRANSPORT
        # hist_fat / psi_plus_prev from the previous refined mesh via
        # centroid-nearest lookup (preserves sub-parent variation). Otherwise
        # keep the current mesh + state (no swap, no transport cost, no
        # smoothing loss). First cycle always swaps to initialize.
        # ------------------------------------------------------------------
        if _S2_enabled and fatigue_on:
            from sidecar_sampling import (adaptive_refine_for_cycle,
                                          nearest_element_transport)
            _refine_mode = sidecar_S2_dict.get('refine_mode', 'cumulative')
            _tip_xy_now = (
                (float(_x_tip_history[-1]), 0.0)
                if _x_tip_history else
                tuple(sidecar_S2_dict.get('tip_xy', (0.0, 0.0)))
            )
            _last_tip = _S2_state['tip_at_refine']

            # ==============================================================
            # ★ v4 (2026-05-20): cumulative add-only incremental refinement.
            # Refines the CURRENT persistent mesh in place (NOT a rebuild from
            # original), only on elements not yet covered by a past tip disk.
            # History transport is parent-index based: lossless on retained
            # elements, one-time direct-parent inherit on new children → no
            # repeated diffusion (the failure mode behind the ~4.4 plateau of
            # the rebuild-from-original variants, confirmed by the AMR /
            # state-variable-transfer literature, see references/adaptive_sampling/).
            # ==============================================================
            if _refine_mode == 'cumulative':
                from sidecar_sampling import (cumulative_refine_step,
                                              remap_element_field,
                                              edge_lineage_transport)
                from utils import hist_alpha_init as _hist_alpha_init
                if _S2_state.get('past_tips') is None:
                    _S2_state['past_tips'] = []
                _r_tip = float(sidecar_S2_dict.get('r_tip_sample', 0.05))
                _mode_v4 = sidecar_S2_dict.get('mode', 'tip_following')
                _force_first_refine = _last_tip is None
                _tip_drift = (
                    float('inf') if _force_first_refine else
                    abs(_tip_xy_now[0] - _last_tip[0]) + abs(_tip_xy_now[1] - _last_tip[1])
                )
                _hyst_gate_open = _force_first_refine or (_tip_drift >= float(_S2_state['hysteresis']))
                if _hyst_gate_open:
                    _out = cumulative_refine_step(
                        _S2_state['X_curr'], _S2_state['Y_curr'],
                        _S2_state['T_curr'], _S2_state['area_curr'],
                        _tip_xy_now, _r_tip, _S2_state['past_tips'],
                        score_curr=_S2_state.get('score_curr'),
                        mode=_mode_v4,
                        target_fraction=float(sidecar_S2_dict.get('target_fraction', 0.07)),
                        min_count=int(sidecar_S2_dict.get('min_count', 50)),
                    )
                    _refined_v4 = _out[0]
                else:
                    _out = None
                    _refined_v4 = False
                if _refined_v4:
                    (_, _X_new, _Y_new, _T_new, _area_new, _parent_v4, _mp_v4, _s2_diag) = _out
                    _first_refine = _S2_state['hist_alpha_curr'] is None
                    _hist_fat_new = remap_element_field(_S2_state['hist_fat_curr'], _parent_v4)
                    _psi_pp_new = remap_element_field(_S2_state['psi_plus_prev_curr'], _parent_v4)
                    inp = torch.from_numpy(np.column_stack((_X_new, _Y_new))).to(torch.float).to(device)
                    T_conn = torch.from_numpy(_T_new).to(torch.long).to(device)
                    area_T = torch.from_numpy(_area_new).to(torch.float).to(device)
                    n_elem = int(_T_new.shape[0])
                    _cx_v4 = (_X_new[_T_new[:, 0]] + _X_new[_T_new[:, 1]] + _X_new[_T_new[:, 2]]) / 3.0
                    _cy_v4 = (_Y_new[_T_new[:, 0]] + _Y_new[_T_new[:, 1]] + _Y_new[_T_new[:, 2]]) / 3.0
                    elem_centroids = torch.from_numpy(np.column_stack((_cx_v4, _cy_v4))).to(torch.float).to(device).detach()
                    hist_fat = torch.from_numpy(_hist_fat_new).to(torch.float).to(device)
                    psi_plus_prev = torch.from_numpy(_psi_pp_new).to(torch.float).to(device)
                    if _first_refine:
                        hist_alpha = _hist_alpha_init(inp, matprop, pffmodel, crack_dict)
                        _ha_diag_v4 = "first-refine = hist_alpha_init"
                    else:
                        _ha_xfer = edge_lineage_transport(
                            _S2_state['hist_alpha_curr'], _mp_v4,
                            _s2_diag['n_old_nodes'], reduce='max',
                        )
                        _ha_floor = _hist_alpha_init(inp, matprop, pffmodel, crack_dict).detach().cpu().numpy().ravel()
                        with torch.no_grad():
                            _, _, _a_nn_v4 = field_comp.fieldCalculation(inp)
                        _ha_nn_v4 = _a_nn_v4.detach().cpu().numpy().ravel()
                        _ha_new_v4 = np.clip(np.maximum.reduce([_ha_xfer, _ha_floor, _ha_nn_v4]), 0.0, 1.0)
                        hist_alpha = torch.from_numpy(_ha_new_v4).to(torch.float).to(device)
                        _ha_diag_v4 = (f"L2+NNmax max {_S2_state['hist_alpha_curr'].max():.3f}→{_ha_new_v4.max():.3f} | "
                                       f"mean {_S2_state['hist_alpha_curr'].mean():.4f}→{_ha_new_v4.mean():.4f}")
                    _set_hard_irrev_floor(hist_alpha, f"S2 cumulative refine cycle {j}")
                    # persist mesh + state
                    _S2_state['X_curr'], _S2_state['Y_curr'] = _X_new, _Y_new
                    _S2_state['T_curr'], _S2_state['area_curr'] = _T_new, _area_new
                    _S2_state['X_curr_nodes'], _S2_state['Y_curr_nodes'] = _X_new, _Y_new
                    _S2_state['hist_fat_curr'] = _hist_fat_new
                    _S2_state['psi_plus_prev_curr'] = _psi_pp_new
                    _S2_state['hist_alpha_curr'] = hist_alpha.detach().cpu().numpy().ravel()
                    _S2_state['parent_curr'] = _parent_v4
                    _S2_state['tip_at_refine'] = _tip_xy_now
                    _S2_state['past_tips'].append(_tip_xy_now)
                    _S2_state['n_swaps'] += 1
                    _s2_refined_this_cycle = True
                    _right_bdy_mask = (inp[:, 0] > _right_bdy_x_min).detach()
                    _nominal_mask = (np.abs(_cy_v4) > 0.3) & (_cx_v4 > -0.3)
                    _n_nominal = int(_nominal_mask.sum())
                    outp = torch.zeros(inp.shape[0], 1).to(device)
                    training_set = DataLoader(
                        torch.utils.data.TensorDataset(inp, outp),
                        batch_size=inp.shape[0], shuffle=False,
                    )
                    f_fatigue = compute_fatigue_degrad(hist_fat, fatigue_dict, elem_centroids=elem_centroids)
                    print(
                        f"  [sidecar-S2 cycle {j}] CUMUL-REFINE tip={_tip_xy_now} | "
                        f"elem {_s2_diag['n_elem_before']}→{_s2_diag['n_elem_after']} | "
                        f"new={_s2_diag['n_new_marked']} already={_s2_diag['n_already']} | "
                        f"swaps={_S2_state['n_swaps']} | hist_alpha {_ha_diag_v4}"
                    )
                else:
                    _S2_state['n_skips'] += 1
                    if (j == start_j) or (j % 5 == 0):
                        if _out is None:
                            _reason = f"hysteresis gate | drift={_tip_drift:.4g} < {_S2_state['hysteresis']:.4g}"
                        else:
                            _reason = f"in_zone={_out[7]['n_in_zone']} all already refined"
                        print(
                            f"  [sidecar-S2 cycle {j}] CUMUL-SKIP tip={_tip_xy_now} "
                            f"({_reason}) | reuse {n_elem} elem | "
                            f"swaps={_S2_state['n_swaps']} skips={_S2_state['n_skips']}"
                        )

            _should_refine = (
                _refine_mode != 'cumulative'
                and (_last_tip is None
                     or (abs(_tip_xy_now[0] - _last_tip[0]) + abs(_tip_xy_now[1] - _last_tip[1])
                         > _S2_state['hysteresis']))
            )
            if _should_refine:
                _X_new, _Y_new, _T_new, _area_new, _parent_new, _s2_diag = adaptive_refine_for_cycle(
                    _S2_state['X_orig'], _S2_state['Y_orig'],
                    _S2_state['T_orig'], _S2_state['area_orig'],
                    sidecar_S2_dict,
                    tip_xy=_tip_xy_now,
                    score=_S2_state['score_orig_for_next'],
                )
                _hf_old_diag = _s2_elem_field_diag(
                    _S2_state['hist_fat_curr'],
                    _S2_state['X_curr'], _S2_state['Y_curr'], _S2_state['T_curr'],
                )
                # Transport from CURRENT refined mesh to NEW refined mesh
                _hist_fat_new = nearest_element_transport(
                    _S2_state['hist_fat_curr'],
                    _S2_state['X_curr'], _S2_state['Y_curr'], _S2_state['T_curr'],
                    _X_new, _Y_new, _T_new,
                )
                _psi_pp_new = nearest_element_transport(
                    _S2_state['psi_plus_prev_curr'],
                    _S2_state['X_curr'], _S2_state['Y_curr'], _S2_state['T_curr'],
                    _X_new, _Y_new, _T_new,
                )
                _hf_new_diag = _s2_elem_field_diag(
                    _hist_fat_new, _X_new, _Y_new, _T_new,
                )
                # Update state to new mesh
                _S2_state['X_curr'], _S2_state['Y_curr'] = _X_new, _Y_new
                _S2_state['T_curr'], _S2_state['area_curr'] = _T_new, _area_new
                _S2_state['parent_curr'] = _parent_new
                _S2_state['tip_at_refine'] = _tip_xy_now
                _S2_state['hist_fat_curr'] = _hist_fat_new
                _S2_state['psi_plus_prev_curr'] = _psi_pp_new
                _S2_state['n_swaps'] += 1
                # Rebuild torch tensors on new mesh
                inp = torch.from_numpy(np.column_stack((_X_new, _Y_new))).to(torch.float).to(device)
                T_conn = torch.from_numpy(_T_new).to(torch.long).to(device)
                area_T = torch.from_numpy(_area_new).to(torch.float).to(device)
                n_elem = int(_T_new.shape[0])
                _cx_new = (_X_new[_T_new[:, 0]] + _X_new[_T_new[:, 1]] + _X_new[_T_new[:, 2]]) / 3.0
                _cy_new = (_Y_new[_T_new[:, 0]] + _Y_new[_T_new[:, 1]] + _Y_new[_T_new[:, 2]]) / 3.0
                elem_centroids = torch.from_numpy(np.column_stack((_cx_new, _cy_new))).to(torch.float).to(device).detach()
                hist_fat = torch.from_numpy(_hist_fat_new).to(torch.float).to(device)
                psi_plus_prev = torch.from_numpy(_psi_pp_new).to(torch.float).to(device)
                # hist_alpha at start of new cycle (v3.2 transport semantics):
                # - FIRST swap (n_swaps==1): hist_alpha_init from crack geometry
                #   (α=1 at initial crack nodes, 0 elsewhere). Identical to S1's
                #   prep_input_data path.
                # - SUBSEQUENT swaps: L2 edge-lineage transport (preserves kept
                #   nodes exactly; new midpoints take max(endpoint_a, endpoint_b)
                #   of the split edge — conservative for irreversibility, avoids
                #   the L1 nearest-node tie-randomness that the expert flagged).
                #   Then take MAX with three other lower bounds:
                #     a) hist_alpha_init at new nodes — never undo initial crack
                #     b) NN.fieldCalculation at new nodes — NN's current α IS the
                #        irreversibility floor (the trained-state lower bound);
                #        transport must NEVER be below NN, because the NN was
                #        already constrained by hist_alpha (penalty) up to this
                #        point. NN can only LIFT, never RESET. Belt-and-suspenders
                #        against any subtle transport gap.
                #   Clamp [0, 1].
                #   v2.1 used pure NN re-eval here; theoretically equivalent under
                #   smooth NN but practically left S2a N=100 stalled at -42%.
                #   v3 was L1 nearest-node, expert flagged tie-randomness.
                #   v3.2 = L2 edge-lineage + NN-max floor = conservative on all axes.
                from utils import hist_alpha_init as _hist_alpha_init
                if _S2_state['n_swaps'] == 1:
                    hist_alpha = _hist_alpha_init(inp, matprop, pffmodel, crack_dict)
                    _ha_diag = "first-swap = hist_alpha_init"
                else:
                    from sidecar_sampling import edge_lineage_transport as _elt
                    _mp = _s2_diag.get('midpoint_parents')
                    _n_old_nodes = _s2_diag.get('n_old_nodes', len(_S2_state['X_curr_nodes']))
                    # NB: edge_lineage_transport requires values_old indexed by
                    # the SAME mesh that was passed into adaptive_refine_for_cycle.
                    # That mesh is X_orig/Y_orig (refinement is always one-step
                    # from canonical original). But hist_alpha_curr lives on the
                    # CURRENT refined mesh which may differ from X_orig. So we
                    # transport in two stages: (1) collapse hist_alpha_curr to
                    # original-mesh nodes via nearest-node from curr→orig; (2)
                    # then edge_lineage to new refined mesh. Step (1) is cheap
                    # (small mesh-overlap delta only at the moving-tip zone).
                    from sidecar_sampling import nearest_node_transport as _nnt
                    _ha_on_orig = _nnt(
                        _S2_state['hist_alpha_curr'],
                        _S2_state['X_curr_nodes'], _S2_state['Y_curr_nodes'],
                        _S2_state['X_orig'], _S2_state['Y_orig'],
                    )
                    if _mp is not None and _mp.size > 0:
                        _ha_transferred = _elt(_ha_on_orig, _mp, _n_old_nodes, reduce='max')
                    else:
                        # No new midpoints (rare: zero red elements); identity
                        _ha_transferred = _ha_on_orig
                    _ha_floor = _hist_alpha_init(inp, matprop, pffmodel, crack_dict).detach().cpu().numpy().ravel()
                    # NN-max floor: NN.fieldCalculation gives the trained-state
                    # smooth α, which is itself bounded below by accumulated
                    # irreversibility. So max(transport, NN) is at least NN.
                    with torch.no_grad():
                        _, _, _alpha_nn_new = field_comp.fieldCalculation(inp)
                    _ha_nn = _alpha_nn_new.detach().cpu().numpy().ravel()
                    _ha_new_np = np.clip(
                        np.maximum.reduce([_ha_transferred, _ha_floor, _ha_nn]),
                        0.0, 1.0,
                    )
                    _ha_old_stats = (_S2_state['hist_alpha_curr'].max(),
                                     float(np.percentile(_S2_state['hist_alpha_curr'], 99)),
                                     _S2_state['hist_alpha_curr'].mean())
                    _ha_new_stats = (_ha_new_np.max(),
                                     float(np.percentile(_ha_new_np, 99)),
                                     _ha_new_np.mean())
                    _ha_nn_max = float(_ha_nn.max())
                    _ha_nn_p99 = float(np.percentile(_ha_nn, 99))
                    hist_alpha = torch.from_numpy(_ha_new_np).to(torch.float).to(device)
                    _ha_diag = (f"L2+NN-max max {_ha_old_stats[0]:.3f}→{_ha_new_stats[0]:.3f} | "
                                f"p99 {_ha_old_stats[1]:.3f}→{_ha_new_stats[1]:.3f} | "
                                f"mean {_ha_old_stats[2]:.4f}→{_ha_new_stats[2]:.4f} | "
                                f"NN p99={_ha_nn_p99:.3f}")
                _set_hard_irrev_floor(hist_alpha, f"S2 rebuild refine cycle {j}")
                # Stash current-mesh node coords + post-transport hist_alpha (numpy) for next swap
                _S2_state['hist_alpha_curr'] = hist_alpha.detach().cpu().numpy().ravel()
                _S2_state['X_curr_nodes'] = _X_new
                _S2_state['Y_curr_nodes'] = _Y_new
                _s2_refined_this_cycle = True
                _right_bdy_mask = (inp[:, 0] > _right_bdy_x_min).detach()
                _nominal_mask = (np.abs(_cy_new) > 0.3) & (_cx_new > -0.3)
                _n_nominal = int(_nominal_mask.sum())
                outp = torch.zeros(inp.shape[0], 1).to(device)
                training_set = DataLoader(
                    torch.utils.data.TensorDataset(inp, outp),
                    batch_size=inp.shape[0], shuffle=False,
                )
                f_fatigue = compute_fatigue_degrad(
                    hist_fat, fatigue_dict, elem_centroids=elem_centroids
                )
                # Always print REFINE events (low-frequency; helps audit
                # whether the transport preserves hist_alpha across swaps).
                print(
                    f"  [sidecar-S2 cycle {j}] REFINE tip={_tip_xy_now} | "
                    f"elem {_s2_diag['n_elem_before']}→{_s2_diag['n_elem_after']} | "
                    f"marked={_s2_diag['n_marked']} | area_drift={_s2_diag['area_drift']:.1e} | "
                    f"swaps={_S2_state['n_swaps']} skips={_S2_state['n_skips']} | "
                    f"hist_alpha {_ha_diag}"
                )
                print(
                    f"  [sidecar-S2 cycle {j}] hist_fat transport | "
                    f"old {_hf_old_diag} -> new {_hf_new_diag}"
                )
                if _alh_enabled:
                    _s2_grad_stats = _update_lambda_hist_from_grad_stats(j, "post-REFINE")
                else:
                    _s2_grad_stats = _s2_print_post_refine_grad_diag(j, label="post-REFINE")
            elif _refine_mode != 'cumulative':
                _S2_state['n_skips'] += 1
                if (j == start_j) or (j % 5 == 0):
                    _dt = abs(_tip_xy_now[0] - _last_tip[0]) + abs(_tip_xy_now[1] - _last_tip[1])
                    print(
                        f"  [sidecar-S2 cycle {j}] SKIP-REFINE tip={_tip_xy_now} "
                        f"(|Δtip|={_dt:.4f} ≤ {_S2_state['hysteresis']:.4f}) | "
                        f"reuse mesh {n_elem} elem | "
                        f"swaps={_S2_state['n_swaps']} skips={_S2_state['n_skips']}"
                    )

        if (
            fatigue_on and _alh_enabled and _lambda_hist_update_every > 0
            and j >= _lambda_hist_start_cycle
            and ((j - _lambda_hist_start_cycle) % _lambda_hist_update_every == 0)
            and not _s2_refined_this_cycle
        ):
            _update_lambda_hist_from_grad_stats(j, "scheduled")

        # ★ MIT-8: build per-cycle supervised_dict (None outside [1, K])
        _supervised_dict = None
        if mit8_dict is not None and mit8_dict.get('enable', False):
            _K = int(mit8_dict.get('K', 0))
            if 1 <= j <= _K:
                _supervised_dict = {
                    'fem_sup': mit8_dict['fem_sup'],
                    'cycle_idx': j,
                    'lambda': float(mit8_dict.get('lambda', 1.0)),
                    'pidl_centroids': mit8_dict['pidl_centroids'],
                    'loss_kind': mit8_dict.get('loss_kind', 'mse_log'),
                }
                print(f"  [MIT-8] cycle {j}/{_K}: supervised lambda={_supervised_dict['lambda']}")

        if _reeq_enabled and _s2_refined_this_cycle:
            _reeq_start = time.time()
            _symmetry_dict = fatigue_dict.get('symmetry_soft', None)
            _side_traction_dict = fatigue_dict.get('side_traction_soft', None)
            NNparams = field_comp.parameters()
            optimizer = get_optimizer(NNparams, _reeq_optimizer_name)
            print(
                f"  [PostRefineReeq cycle {j}] start | "
                f"optimizer={_reeq_optimizer_name} max_epochs={_reeq_n_epochs} | "
                f"lambda_hist={_lambda_hist:.6e} | no hist_fat/psi_plus_prev update"
            )
            _reeq_loss = fit_with_early_stopping(
                field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
                optimizer_dict["weight_decay"], num_epochs=_reeq_n_epochs, optimizer=optimizer,
                min_delta=optimizer_dict["optim_rel_tol"],
                intermediateModel_path=None,
                writer=writer, training_dict=training_dict,
                f_fatigue=f_fatigue,
                crack_tip_weights=crack_tip_weights,
                hist_loss_weight=_current_hist_loss_weight(),
                supervised_dict=_supervised_dict,
                symmetry_dict=_symmetry_dict,
                side_traction_dict=_side_traction_dict,
            )
            _reeq_seconds = time.time() - _reeq_start
            _reeq_last_loss = float(_reeq_loss[-1]) if _reeq_loss else float('nan')
            _reeq_history.append([j, _reeq_seconds, len(_reeq_loss), _reeq_last_loss])
            loss_data = loss_data + _reeq_loss
            print(
                f"  [PostRefineReeq cycle {j}] done | "
                f"time={_reeq_seconds/60:.3f} min | "
                f"steps={len(_reeq_loss)} | last_loss={_reeq_last_loss:.6e}"
            )

        # ------------------------------------------------------------------
        # 训练（与 Manav 完全相同的结构；仅多传 f_fatigue 和 crack_tip_weights）
        # ------------------------------------------------------------------
        if j == 0 or optimizer_dict["n_epochs_LBFGS"] > 0:
            n_epochs = max(optimizer_dict["n_epochs_LBFGS"], 1)
            NNparams  = field_comp.parameters()
            optimizer = get_optimizer(NNparams, "LBFGS")
            # ★ 2026-05-07 Soft mirror-symmetry penalty (B path) — read from fatigue_dict
            _symmetry_dict = fatigue_dict.get('symmetry_soft', None)
            # ★ 2026-05-08 Soft side-traction penalty — read from fatigue_dict
            _side_traction_dict = fatigue_dict.get('side_traction_soft', None)
            loss_data1 = fit(
                field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
                optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
                intermediateModel_path=None, writer=writer, training_dict=training_dict,
                f_fatigue=f_fatigue,                    # ★ 传入疲劳退化函数
                crack_tip_weights=crack_tip_weights,    # ★ 2026-05-13 P0 fix: thread C6/Dir3 reweight into LBFGS
                hist_loss_weight=_current_hist_loss_weight(),  # optional adaptive/hard irreversibility
                supervised_dict=_supervised_dict,       # ★ MIT-8
                symmetry_dict=_symmetry_dict,           # ★ B path soft sym
                side_traction_dict=_side_traction_dict, # ★ side-traction penalty
            )
            loss_data = loss_data + loss_data1

        if optimizer_dict["n_epochs_RPROP"] > 0:
            n_epochs  = optimizer_dict["n_epochs_RPROP"]
            NNparams  = field_comp.parameters()
            optimizer = get_optimizer(NNparams, "RPROP")
            _symmetry_dict = fatigue_dict.get('symmetry_soft', None)
            _side_traction_dict = fatigue_dict.get('side_traction_soft', None)
            loss_data2 = fit_with_early_stopping(
                field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
                optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
                min_delta=optimizer_dict["optim_rel_tol"],
                intermediateModel_path=intermediateModel_path,
                writer=writer, training_dict=training_dict,
                f_fatigue=f_fatigue,                    # ★ 传入疲劳退化函数
                crack_tip_weights=crack_tip_weights,    # ★ 2026-05-13 P0 fix: thread C6/Dir3 reweight into RPROP
                hist_loss_weight=_current_hist_loss_weight(),  # optional adaptive/hard irreversibility
                supervised_dict=_supervised_dict,       # ★ MIT-8
                symmetry_dict=_symmetry_dict,           # ★ B path soft sym
                side_traction_dict=_side_traction_dict, # ★ side-traction penalty
            )
            loss_data = loss_data + loss_data2

        end = time.time()
        _cycle_seconds = end - start
        print(f"Execution time: {_cycle_seconds/60:.03f}minutes")
        _time_history.append([j, _cycle_seconds])
        if _alh_enabled:
            _lambda_hist_history.append([j, _lambda_hist])

        # ------------------------------------------------------------------
        # Manav 原始：更新相场不可逆性历史变量 hist_alpha
        # ------------------------------------------------------------------
        hist_alpha = field_comp.update_hist_alpha(inp)
        _set_hard_irrev_floor(hist_alpha, f"post-cycle {j}")

        # ★ v3 (2026-05-15): sync per-node hist_alpha to _S2_state so the next
        # REFINE event has the post-cycle floor available for nearest-node
        # transport. No-op when S2 disabled or before any swap has occurred.
        if _S2_enabled and _S2_state is not None and _S2_state['hist_alpha_curr'] is not None:
            _S2_state['hist_alpha_curr'] = hist_alpha.detach().cpu().numpy().ravel()

        # ------------------------------------------------------------------
        # ★ 疲劳历史变量更新（仅 fatigue_on=True 时执行）
        #   流程：
        #     1. 用训练好的 NN 计算当前步各单元 ψ⁺
        #     2. update_fatigue_history: ᾱ ← ᾱ + H(Δψ⁺)·Δψ⁺（或幂律版本）
        #     3. compute_fatigue_degrad: 更新 f(ᾱ) ∈ [0,1]
        #   当 fatigue_on=False：此块完全跳过，f_fatigue 保持 1.0
        # ------------------------------------------------------------------
        if fatigue_on:
            # 计算当前步各单元退化拉伸应变能密度 ψ⁺
            # 数值梯度模式（T_conn is not None）：不需要 inp.requires_grad
            # 自动微分模式（T_conn is None）    ：需要 inp.requires_grad
            # ★ E2 sanity hack (Apr 23 2026): 如果 fatigue_dict 里有 psi_hack 子 dict，透传
            _psi_hack = fatigue_dict.get('psi_hack', None)
            # ★ Apr 27 — Oracle-driver MIT-8b: build per-cycle FEM ψ⁺ override dict
            _fem_oracle = None
            _fem_oracle_cfg = fatigue_dict.get('fem_oracle', None)
            if _fem_oracle_cfg is not None and _fem_oracle_cfg.get('enable', False):
                _fem_sup = _fem_oracle_cfg['fem_sup']  # FEMSupervision instance
                _pidl_centroids = _fem_oracle_cfg['pidl_centroids']  # np.ndarray
                _override_mask = _fem_oracle_cfg['override_mask']    # torch.bool tensor
                _apply_g = _fem_oracle_cfg.get('apply_g', True)
                _device = inp.device
                # Linear-interp FEM ψ⁺ at this fatigue cycle j → tensor on device
                _psi_target = _fem_sup.psi_target_at_cycle(
                    int(j), _pidl_centroids, device=_device, dtype=torch.float32)
                _fem_oracle = {
                    'enable': True, 'psi_target': _psi_target,
                    'override_mask': _override_mask, 'apply_g': _apply_g,
                }
            if T_conn is not None:
                with torch.no_grad():
                    u_eval, v_eval, alpha_eval = field_comp.fieldCalculation(inp)
                psi_plus_elem = get_psi_plus_per_elem(
                    inp, u_eval, v_eval, alpha_eval,
                    matprop, pffmodel, area_T, T_conn,
                    psi_hack_dict=_psi_hack,
                    fem_oracle_dict=_fem_oracle,
                )
            else:
                # 自动微分模式：需要 inp 开启梯度
                inp_tmp = inp.detach().clone().requires_grad_(True)
                u_eval, v_eval, alpha_eval = field_comp.fieldCalculation(inp_tmp)
                psi_plus_elem = get_psi_plus_per_elem(
                    inp_tmp, u_eval, v_eval, alpha_eval,
                    matprop, pffmodel, area_T, T_conn=None,
                    psi_hack_dict=_psi_hack,
                    fem_oracle_dict=_fem_oracle,
                )

            # ★ Direction 4: 用 ψ⁺ 重心估计裂尖坐标 → 更新 field_comp.x_tip
            # 必须在 update_fatigue_history 之前，确保本圈 psi_plus_elem 是峰值状态
            # ★ Fix B: cycle 0 保持初始 x_tip（α 场未收敛，ψ⁺ 分布被预裂缝污染，
            #   给出非物理的 x_tip 估计，如 -0.17，导致 cycle 1 Williams features 失真 → NN 伪解）
            # ★ Fix B: sanity check — 如果 ψ⁺ centroid 跑进预裂缝内部超过 0.02，拒绝更新
            # ★ Fix:   断裂确认期间冻结 x_tip，防止裂尖跳到右边界导致 Williams 特征失真
            if _williams_enabled and T_conn is not None:
                if not _frac_detected:
                    if j == 0:
                        # Cycle 0: 保持 __init__ 时的初始值（crack_mouth 附近，物理先验）
                        print(f"  [Williams]  x_tip_psi={field_comp.x_tip:.4f} "
                              f"(cycle 0, keep initial — psi+ unreliable before alpha converges)")
                    else:
                        _x_tip_psi_val = compute_x_tip_psi(inp, psi_plus_elem, T_conn, top_k=10)
                        _x_tip_floor   = _crack_mouth_x - 0.02   # 下界：不允许跑进预裂缝内
                        if _x_tip_psi_val < _x_tip_floor:
                            print(f"  [Williams]  x_tip_psi={_x_tip_psi_val:.4f} "
                                  f"rejected (< floor {_x_tip_floor:.4f}), "
                                  f"keep {field_comp.x_tip:.4f}")
                        else:
                            field_comp.x_tip = _x_tip_psi_val
                            print(f"  [Williams]  x_tip_psi={_x_tip_psi_val:.4f}")
                else:
                    print(f"  [Williams]  x_tip_psi={field_comp.x_tip:.4f} (frozen, fracture confirmed)")
                _x_tip_psi_history.append(field_comp.x_tip)
            elif _williams_enabled:
                # 自动微分模式：T_conn=None，形心计算不可用，暂保持上一圈值
                _x_tip_psi_history.append(field_comp.x_tip)

            # ★ 每圈 Kt 计算（复用已有 psi_plus_elem，零额外前向传播）
            if _nominal_mask is not None:
                _psi0      = psi_plus_elem.detach().cpu().numpy()
                _top10_idx = np.argsort(_psi0)[-10:]
                _psi_tip   = float(_psi0[_top10_idx].mean())
                _psi_nom   = (float(_psi0[_nominal_mask].mean())
                               if _n_nominal > 0 else float(_psi0.mean()))
                _Kt        = (_psi_tip / _psi_nom) ** 0.5 if _psi_nom > 1e-20 else float('nan')
                _Kt_history.append(_Kt)

            # 更新疲劳历史变量 ᾱ（Carrara Eq.39 或 Golahmar Eq.31）
            _hist_fat_before_update = (
                hist_fat.detach().clone()
                if (_S2_enabled and fatigue_on) else None
            )
            hist_fat = update_fatigue_history(
                hist_fat, psi_plus_elem, psi_plus_prev, fatigue_dict
            )

            # ★ 2026-05-08 A1: post-hoc mirror α — break Carrara ratchet
            # Symmetrize ᾱ about y=0 BEFORE f(ᾱ) is computed for next cycle.
            # Resets the asymmetric memory build-up; SENT geometry is symmetric
            # under symmetric BCs so this is physically defensible.
            if _mirror_idx is not None:
                hist_fat = mirror_alpha_y(hist_fat, _mirror_idx)

            if _hist_fat_before_update is not None:
                _delta_hist_fat = hist_fat - _hist_fat_before_update
                print(
                    f"  [sidecar-S2 cycle {j}] Δhist_fat | "
                    f"{_s2_elem_tensor_diag(_delta_hist_fat, elem_centroids)}"
                )

            # 更新疲劳退化函数 f(ᾱ)（Carrara Eq.41 或 Eq.42）
            # ★ Direction 6.1: 传入 elem_centroids 支持空间调制 α_T
            f_fatigue = compute_fatigue_degrad(
                hist_fat, fatigue_dict, elem_centroids=elem_centroids
            )

            # ★ 重置 psi_plus_prev，正确模拟循环加载的卸载阶段
            # 原因：NN 只求解峰值状态，不显式模拟卸载。
            #   - 单调加载：loading_type='monotonic' 在 update_fatigue_history 里已提前返回，
            #               此处不会执行到，但为安全起见仍做差分保存。
            #   - 循环加载（R=0，拉-拉）：卸载后 ψ⁺_min = 0，
            #               下一圈应从 0 开始累积 → prev 重置为 0
            #   - 循环加载（R>0）：ψ⁺_min = R²·ψ⁺_max（位移控制）
            #               → prev 重置为 R²·ψ⁺_peak
            # 修复前：prev = ψ⁺_peak → 第2圈起 Δᾱ = 0（不再累积！）
            # 修复后：prev = R²·ψ⁺_peak → 每圈累积 (1-R²)·ψ⁺_peak ✅
            R = fatigue_dict.get('R_ratio', 0.0)
            psi_plus_prev = (R ** 2) * psi_plus_elem.clone()

            # ★ 方向3：计算下一圈的裂尖自适应权重
            # 在当前圈 psi_plus_elem 更新后立即计算，供下一圈的 fit() 使用
            # w_e = 1 + β·(ψ⁺_e / ψ⁺_mean)^p  （均匀加 1 确保 w_e ≥ 1）
            if _tip_w_cfg is not None:
                _tw_beta        = _tip_w_cfg.get('beta', 2.0)
                _tw_power       = _tip_w_cfg.get('power', 1.0)
                _tw_start_cycle = _tip_w_cfg.get('start_cycle', 1)
                if j >= _tw_start_cycle:
                    psi_mean = psi_plus_elem.mean().clamp(min=1e-30)
                    crack_tip_weights = (
                        1.0 + _tw_beta * (psi_plus_elem / psi_mean).pow(_tw_power)
                    ).detach()
                else:
                    crack_tip_weights = None   # 还未到启用圈数，本圈均匀

            # ★ 2026-05-13 Branch 2 C6: Deep Ritz residual adaptive reweight
            # Timing: weights are computed at END of cycle j from current α field,
            # applied during cycle (j+1)'s fit() via crack_tip_weights.
            # Semantics of start_cycle (post-P2 fix): `start_cycle=N` means weights
            # are ACTIVE in cycle N's fit() — so we need to compute them at end of
            # cycle N-1, i.e. condition `j+1 >= start_cycle` ⇔ `j >= start_cycle-1`.
            # Residual proxy: |E_el_e| + |E_d_e| (Deep Ritz residual). E_hist
            # (irreversibility penalty) is intentionally dropped — it's a regularizer
            # not a physics residual, and is ≈ 0 here anyway (hist_alpha was refreshed
            # at line 538 above). See source/adaptive_sampling.py module docstring
            # for option-B variant if E_hist sensitivity ever matters.
            # Difference from Direction 3: residual source includes E_d (dissipation
            # term, dominant once d > 0), whereas Direction 3 uses ψ⁺ only.
            if _adapt_cfg is not None:
                _as_beta        = _adapt_cfg.get('beta', 2.0)
                _as_power       = _adapt_cfg.get('power', 1.0)
                _as_start_cycle = _adapt_cfg.get('start_cycle', 1)
                _as_source      = _adapt_cfg.get('residual_source', 'full')
                # j+1 = next cycle's index; weights are active when next_cycle >= start_cycle
                if (j + 1) >= _as_start_cycle:
                    # Explicit no-grad forward here (the cycle-end forward downstream of
                    # this block computes the same fields for the E_el log; we don't
                    # share the result to keep this block self-contained for review).
                    # Cost is one extra forward per cycle (negligible vs training cost).
                    with torch.no_grad():
                        _u_as, _v_as, _alpha_as = field_comp.fieldCalculation(inp)
                    crack_tip_weights = compute_adaptive_weights(
                        inp, _u_as, _v_as, _alpha_as, hist_alpha,
                        matprop, pffmodel, area_T, T_conn=T_conn,
                        f_fatigue=f_fatigue,
                        beta=_as_beta, power=_as_power,
                        residual_source=_as_source,
                    )
                else:
                    crack_tip_weights = None   # warmup cycles unweighted

            # ------------------------------------------------------------------
            # ★ 2026-05-14 sidecar S2 v2 (expert review): hist_fat /
            # psi_plus_prev now live in CURRENT refined-mesh coords and travel
            # cycle-to-cycle via centroid-nearest transport — no aggregate-then-
            # expand round-trip, no sub-parent smoothing loss. Sync the tensor
            # state back to numpy so the next cycle's transport sees the
            # post-cycle values.
            # ------------------------------------------------------------------
            if _S2_enabled and _S2_state is not None:
                _S2_state['hist_fat_curr'] = hist_fat.detach().cpu().numpy()
                _S2_state['psi_plus_prev_curr'] = psi_plus_prev.detach().cpu().numpy()
                _area_np_cur = area_T.detach().cpu().numpy()
                _S2_state['area_curr'] = _area_np_cur
                # S2b only: compute next cycle's selection score in ORIGINAL
                # mesh coords. Score is a point-evaluated DENSITY (not a
                # cumulative integral), so aggregate_to_original is the
                # correct operation here — sub-parent variation in score
                # density is small for a smooth Deep-Ritz residual, and the
                # round-trip is exact under uniform refinement (P1 fix unit
                # test). select_top_score_elements then ranks ORIGINAL-mesh
                # elements by local error density for next cycle's top-K mask.
                if sidecar_S2_dict.get('mode') == 'score_driven':
                    from sidecar_sampling import aggregate_to_original as _agg_to_orig
                    from residual_score import compute_residual_score as _res_score
                    with torch.no_grad():
                        _u_s2, _v_s2, _a_s2 = field_comp.fieldCalculation(inp)
                        _score_s2 = _res_score(
                            inp, _u_s2, _v_s2, _a_s2, hist_alpha,
                            matprop, pffmodel, area_T, T_conn=T_conn,
                            f_fatigue=f_fatigue,
                            include_hist=False,
                        )
                    _score_density_cur = _score_s2.score_density.detach().cpu().numpy()
                    if sidecar_S2_dict.get('refine_mode', 'cumulative') == 'cumulative':
                        # v4: cumulative_refine_step selects top-K directly on the
                        # CURRENT mesh, so keep the density score in current-mesh
                        # coords (no aggregate-to-original; parent_curr maps to the
                        # previous mesh, not original).
                        _S2_state['score_curr'] = _score_density_cur
                    else:
                        _S2_state['score_orig_for_next'] = _agg_to_orig(
                            _score_density_cur, _area_np_cur,
                            _S2_state['parent_curr'], _S2_state['n_elem_orig'],
                        )

            # ★ Direction 5: 记录 c_singular 当前值（每圈训练完毕后）
            if _ansatz_enabled and field_comp.c_singular is not None:
                _c_val = float(field_comp.c_singular.detach().cpu().item())
                _c_singular_history.append([j, _c_val])
            else:
                _c_val = None

            # 日志输出
            f_min = f_fatigue.min().item()
            f_mean = f_fatigue.mean().item()
            alpha_bar_max = hist_fat.max().item()
            if (j % _log_every == 0) or _frac_detected or _dense_sampling:
                _Kt_str = f"{_Kt:.2f}" if not np.isnan(_Kt) else "N/A"
                _c_str  = f" | c={_c_val:+.4e}" if _c_val is not None else ""
                print(f"  [Fatigue step {j}] ᾱ_max={alpha_bar_max:.4e} | "
                      f"f_min={f_min:.4f} | f_mean={f_mean:.4f} | Kt={_Kt_str}{_c_str}")
            alpha_bar_history.append([alpha_bar_max,
                                       hist_fat.mean().item(),
                                       float(f_min)])

            # ── E_el 计算（用于断裂检测和后处理曲线）─────────────────────
            with torch.no_grad():
                u_el, v_el, alpha_el = field_comp.fieldCalculation(inp)
                E_el_val, _, _ = compute_energy(
                    inp, u_el, v_el, alpha_el, hist_alpha,
                    matprop, pffmodel, area_T, T_conn, f_fatigue
                )
            E_el_scalar = float(E_el_val.item())
            E_el_history.append(E_el_scalar)
            # ★ Fix: 断裂确认期间冻结 E_el_max，防止 NN 伪解抬高基线导致判据失效
            if not _frac_detected:
                E_el_max = max(E_el_max, E_el_scalar)

            # ── 右边界 α 检测（主判据）──────────────────────────────────────
            alpha_bdy     = alpha_el.flatten()[_right_bdy_mask]
            alpha_bdy_max = float(alpha_bdy.max().item()) if _right_bdy_mask.sum() > 0 else 0.0
            n_bdy_frac    = int((alpha_bdy > _alpha_bdy_frac).sum().item())

            # 预警：α > 0.90 → 开始逐圈密集采样
            if not _dense_sampling and alpha_bdy_max >= _alpha_bdy_warn:
                _dense_sampling = True
                print(f"  [Dense sampling ON] cycle {j}: α_max@bdy={alpha_bdy_max:.4f} "
                      f">= {_alpha_bdy_warn} → 开始逐圈保存快照")

            # ── α 场快照：常规每 _plot_every 圈；密集采样期或断裂确认期每圈保存 ──
            if j % _plot_every == 0 or _dense_sampling or _frac_detected:
                _save_alpha_snapshot(inp, alpha_el, T_conn, j, _snapshot_dir)

            # ── 裂缝尖端 L∞（仅用于日志和后处理，不再作为停止判据）──────────
            crack_tip_xy, crack_length = get_crack_tip(
                alpha_el.flatten(), inp, _crack_mouth, threshold=_alpha_crack_thr,
                x_min=_crack_mouth_x
            )
            _x_tip_history.append(crack_length)
            _tip_x = crack_tip_xy[0].item()
            _tip_y = crack_tip_xy[1].item()
            if (j % _log_every == 0) or _frac_detected or _dense_sampling:
                print(f"  [crack_tip]    = ({_tip_x:.4f}, {_tip_y:.4f})  "
                      f"L∞_length = {crack_length:.4f}  "
                      f"α_max@bdy={alpha_bdy_max:.4f}  N_bdy>{_alpha_bdy_frac}={n_bdy_frac}")

            # ── 断裂检测：α>0.95 @ 右边界（主）OR E_el 骤降（兜底）──────────
            _bdy_triggered = (n_bdy_frac >= _alpha_bdy_nmin)
            # ★ Fix A (warmup) + Run #4 fix (enable_E_fallback): 双层保护
            # - enable_E_fallback=False：完全禁用 fallback（Williams 等易尖峰的实验用）
            # - enable_E_fallback=True + warmup：fallback 仅在 cycle >= warmup 生效
            _E_triggered   = (_E_fallback_enabled
                              and j >= _E_fallback_warmup
                              and E_el_max > 0
                              and E_el_scalar < _E_drop_ratio * E_el_max)

            if not _frac_detected and (_bdy_triggered or _E_triggered):
                _frac_detected = True
                _frac_cycle    = j
                _frac_confirm_remaining = _confirm_cycles
                _reasons = []
                if _bdy_triggered:
                    _reasons.append(f"α_bdy={alpha_bdy_max:.4f} >= {_alpha_bdy_frac} "
                                    f"({n_bdy_frac} nodes)")
                if _E_triggered:
                    _reasons.append(f"E_el={E_el_scalar:.3e} < "
                                    f"{_E_drop_ratio}×{E_el_max:.3e}")
                print(f"  [Fracture?] cycle {j}: {' | '.join(_reasons)}. "
                      f"Continuing {_confirm_cycles} confirmation cycles...")
            elif _frac_detected:
                _frac_confirm_remaining -= 1
                # 两个判据都失效时才重置（防数值波动误重置）
                if (not _bdy_triggered) and (E_el_scalar >= _E_drop_ratio * E_el_max):
                    print(f"  [Fracture reset] cycle {j}: both criteria recovered → reset.")
                    _frac_detected  = False
                    _frac_cycle     = None
                    _dense_sampling = False

        # ------------------------------------------------------------------
        # 保存模型和损失（与 Manav 完全相同）
        # ------------------------------------------------------------------
        torch.save(field_comp.net.state_dict(),
                   trainedModel_path / Path('trained_1NN_' + str(j) + '.pt'))
        with open(trainedModel_path / Path('trainLoss_1NN_' + str(j) + '.npy'), 'wb') as f:
            np.save(f, np.asarray(loss_data))

        # ★ 保存断点续训 checkpoint（含 hist_alpha 及疲劳变量）
        _ckpt_data = {'hist_alpha': hist_alpha}
        if fatigue_on:
            _ckpt_data['hist_fat']                 = hist_fat
            _ckpt_data['psi_plus_prev']            = psi_plus_prev
            _ckpt_data['_frac_detected']           = _frac_detected
            _ckpt_data['_frac_cycle']              = _frac_cycle
            _ckpt_data['_frac_confirm_remaining']  = _frac_confirm_remaining
        if _alh_enabled:
            _ckpt_data['_lambda_hist'] = _lambda_hist
        if _S2_enabled and _S2_state is not None:
            _ckpt_data['_S2_state'] = {
                'X_curr': _S2_state['X_curr'],
                'Y_curr': _S2_state['Y_curr'],
                'T_curr': _S2_state['T_curr'],
                'area_curr': _S2_state['area_curr'],
                'parent_curr': _S2_state['parent_curr'],
                'hist_fat_curr': _S2_state['hist_fat_curr'],
                'psi_plus_prev_curr': _S2_state['psi_plus_prev_curr'],
                'hist_alpha_curr': _S2_state['hist_alpha_curr'],
                'X_curr_nodes': _S2_state['X_curr_nodes'],
                'Y_curr_nodes': _S2_state['Y_curr_nodes'],
                'tip_at_refine': _S2_state['tip_at_refine'],
                'past_tips': _S2_state.get('past_tips', []),
                'n_swaps': _S2_state['n_swaps'],
                'n_skips': _S2_state['n_skips'],
            }
            if _S2_state.get('score_curr') is not None:
                _ckpt_data['_S2_state']['score_curr'] = _S2_state['score_curr']
            if _S2_state.get('score_orig_for_next') is not None:
                _ckpt_data['_S2_state']['score_orig_for_next'] = _S2_state['score_orig_for_next']
        torch.save(_ckpt_data,
                   trainedModel_path / Path(f'checkpoint_step_{j}.pt'))

        # ★ 每圈增量保存历史数组（防 crash/kill 导致数据丢失）
        # np.save 写 .npy 耗时 < 1 ms，对总训练时间无影响
        if fatigue_on:
            if E_el_history:
                np.save(str(trainedModel_path / 'E_el_vs_cycle.npy'),
                        np.array(E_el_history))
            if _x_tip_history:
                _xt = np.array(_x_tip_history)
                np.save(str(trainedModel_path / 'x_tip_alpha_vs_cycle.npy'), _xt)
                np.save(str(trainedModel_path / 'x_tip_vs_cycle.npy'),       _xt)
            if _williams_enabled and _x_tip_psi_history:
                np.save(str(trainedModel_path / 'x_tip_psi_vs_cycle.npy'),
                        np.array(_x_tip_psi_history))
            if alpha_bar_history:
                np.save(str(trainedModel_path / 'alpha_bar_vs_cycle.npy'),
                        np.array(alpha_bar_history))
            if _Kt_history:
                np.save(str(trainedModel_path / 'Kt_vs_cycle.npy'),
                        np.array(_Kt_history))
            if _ansatz_enabled and _c_singular_history:                     # ★ Direction 5
                np.save(str(trainedModel_path / 'c_singular_vs_cycle.npy'),
                        np.array(_c_singular_history))   # shape (N,2): [cycle_idx, c_val]
            if _time_history:
                np.save(str(trainedModel_path / 'time_vs_cycle.npy'),
                        np.array(_time_history))   # shape (N,2): [cycle_idx, seconds]
            if _alh_enabled and _lambda_hist_history:
                np.save(str(trainedModel_path / 'lambda_hist_vs_cycle.npy'),
                        np.array(_lambda_hist_history))   # shape (N,2): [cycle_idx, lambda_hist]
            if _reeq_enabled and _reeq_history:
                np.save(str(trainedModel_path / 'post_refine_reeq_vs_cycle.npy'),
                        np.array(_reeq_history))   # [cycle_idx, seconds, n_loss, last_loss]

        # ── 断裂确认：判据持续满足 confirm_cycles 圈 → 停止 ──────────────
        if fatigue_on and _frac_detected and _frac_confirm_remaining <= 0:
            print(f"  [Fracture confirmed] Stopping at cycle {j}. "
                  f"First detected at cycle {_frac_cycle}.")
            np.save(str(trainedModel_path / 'E_el_vs_cycle.npy'),
                    np.array(E_el_history))
            np.save(str(trainedModel_path / 'x_tip_alpha_vs_cycle.npy'),   # ★ α 基准名称更新
                    np.array(_x_tip_history))
            np.save(str(trainedModel_path / 'x_tip_vs_cycle.npy'),         # ★ 保留旧名称（向后兼容）
                    np.array(_x_tip_history))
            if _williams_enabled and _x_tip_psi_history:                    # ★ Direction 4
                np.save(str(trainedModel_path / 'x_tip_psi_vs_cycle.npy'),
                        np.array(_x_tip_psi_history))
            np.save(str(trainedModel_path / 'alpha_bar_vs_cycle.npy'),
                    np.array(alpha_bar_history))
            if _Kt_history:
                np.save(str(trainedModel_path / 'Kt_vs_cycle.npy'),
                        np.array(_Kt_history))
            if _ansatz_enabled and _c_singular_history:                    # ★ Direction 5
                np.save(str(trainedModel_path / 'c_singular_vs_cycle.npy'),
                        np.array(_c_singular_history))
            if _time_history:
                np.save(str(trainedModel_path / 'time_vs_cycle.npy'),
                        np.array(_time_history))
            if _alh_enabled and _lambda_hist_history:
                np.save(str(trainedModel_path / 'lambda_hist_vs_cycle.npy'),
                        np.array(_lambda_hist_history))
            if _reeq_enabled and _reeq_history:
                np.save(str(trainedModel_path / 'post_refine_reeq_vs_cycle.npy'),
                        np.array(_reeq_history))
            break

    # 循环正常结束（跑完所有圈）也保存历史
    if fatigue_on and E_el_history:
        np.save(str(trainedModel_path / 'E_el_vs_cycle.npy'),
                np.array(E_el_history))
    if fatigue_on and _x_tip_history:
        np.save(str(trainedModel_path / 'x_tip_alpha_vs_cycle.npy'),       # ★ α 基准名称更新
                np.array(_x_tip_history))
        np.save(str(trainedModel_path / 'x_tip_vs_cycle.npy'),             # ★ 保留旧名称（向后兼容）
                np.array(_x_tip_history))
    if fatigue_on and _williams_enabled and _x_tip_psi_history:            # ★ Direction 4
        np.save(str(trainedModel_path / 'x_tip_psi_vs_cycle.npy'),
                np.array(_x_tip_psi_history))
    if fatigue_on and alpha_bar_history:
        np.save(str(trainedModel_path / 'alpha_bar_vs_cycle.npy'),
                np.array(alpha_bar_history))
    if fatigue_on and _Kt_history:
        np.save(str(trainedModel_path / 'Kt_vs_cycle.npy'),
                np.array(_Kt_history))
    if fatigue_on and _ansatz_enabled and _c_singular_history:             # ★ Direction 5
        np.save(str(trainedModel_path / 'c_singular_vs_cycle.npy'),
                np.array(_c_singular_history))
    if fatigue_on and _time_history:
        np.save(str(trainedModel_path / 'time_vs_cycle.npy'),
                np.array(_time_history))
    if fatigue_on and _alh_enabled and _lambda_hist_history:
        np.save(str(trainedModel_path / 'lambda_hist_vs_cycle.npy'),
                np.array(_lambda_hist_history))
    if fatigue_on and _reeq_enabled and _reeq_history:
        np.save(str(trainedModel_path / 'post_refine_reeq_vs_cycle.npy'),
                np.array(_reeq_history))
