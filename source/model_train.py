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
from fatigue_history import update_fatigue_history, compute_fatigue_degrad

# ★ Direction 4: Williams ψ⁺ 重心估计裂尖坐标（可选，仅在 williams_enabled=True 时调用）
from williams_features import compute_x_tip_psi


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
          mit8_dict=None):                           # ★ MIT-8 supervised warmup
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
        inp, T_conn, area_T, hist_alpha = prep_input_data(
            matprop, pffmodel, crack_dict, numr_dict,
            mesh_file=coarse_mesh_file, device=device
        )
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
            intermediateModel_path=None, writer=writer, training_dict=training_dict
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
            intermediateModel_path=None, writer=writer, training_dict=training_dict
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
        mesh_file=fine_mesh_file, device=device
    )
    outp = torch.zeros(inp.shape[0], 1).to(device)
    training_set = DataLoader(
        torch.utils.data.TensorDataset(inp, outp),
        batch_size=inp.shape[0], shuffle=False
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

        # ★ Direction 6.1: 预计算元素形心，供 spatial α_T 使用（tensor 版本）
        _sp_cfg = fatigue_dict.get('spatial_alpha_T', {})
        if _sp_cfg.get('enable', False) and T_conn is not None:
            _Tc = T_conn if isinstance(T_conn, torch.Tensor) else torch.as_tensor(T_conn, device=device)
            _cx_t = (inp[_Tc[:,0], 0] + inp[_Tc[:,1], 0] + inp[_Tc[:,2], 0]) / 3.0
            _cy_t = (inp[_Tc[:,0], 1] + inp[_Tc[:,1], 1] + inp[_Tc[:,2], 1]) / 3.0
            elem_centroids = torch.stack([_cx_t, _cy_t], dim=1).detach()
            print(f"[spAlphaT] Spatial α_T enabled: "
                  f"β={_sp_cfg.get('beta',0.0)}, r_T={_sp_cfg.get('r_T',0.1)}, "
                  f"tip=({_sp_cfg.get('x_tip',0.0)},{_sp_cfg.get('y_tip',0.0)}) | "
                  f"n_elem={n_elem}")
        else:
            elem_centroids = None
            if _sp_cfg.get('enable', False):
                print("[spAlphaT] WARNING: enable=True but T_conn is None "
                      "(autodiff mode); fallback to scalar α_T")
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

    # -------------------------------------------------------------------------
    # ★ 检测最新 step checkpoint，实现断点续训
    # -------------------------------------------------------------------------
    _step_ckpts = sorted(
        trainedModel_path.glob('checkpoint_step_*.pt'),
        key=lambda p: int(p.stem.rsplit('_', 1)[-1])
    )
    start_j = 0
    _did_restore = False   # ★ 标志位：True → 后续 history lists 从 .npy 初始化
    if _step_ckpts:
        _latest = _step_ckpts[-1]
        _last_j = int(_latest.stem.rsplit('_', 1)[-1])
        _net_file = trainedModel_path / Path(f'trained_1NN_{_last_j}.pt')
        if _net_file.exists():
            _ckpt = torch.load(_latest, map_location=device)
            field_comp.net.load_state_dict(
                torch.load(_net_file, map_location=device))
            hist_alpha = _ckpt['hist_alpha'].to(device)
            if fatigue_on:
                hist_fat      = _ckpt['hist_fat'].to(device)
                psi_plus_prev = _ckpt['psi_plus_prev'].to(device)
                f_fatigue     = compute_fatigue_degrad(
                    hist_fat, fatigue_dict, elem_centroids=elem_centroids
                )
            start_j = _last_j + 1
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

    # ★ Direction 4: Williams 特征开关 & ψ⁺ 重心裂尖历史
    # 通过 field_comp.williams_enabled 检测是否启用（无需额外参数传递）
    _williams_enabled = getattr(field_comp, 'williams_enabled', False)
    _x_tip_psi_history = _restore_hist('x_tip_psi_vs_cycle.npy')   # ★ 续训时从 .npy 恢复

    # ★ α-3 XFEM-jump (Apr 29) — Heaviside discontinuity at moving x_tip
    # Detect: NN has update_tip method (XFEMJumpNN; same hook as α-2 MultiHeadNN)
    _xfem_enabled = hasattr(field_comp.net, 'update_tip')
    # ★ α-3 T4 stationarity diagnostic (mirror of α-2 to allow direct comparison)
    _psi_argmax_history = _restore_hist('psi_argmax_vs_cycle.npy')

    # ★ 每圈耗时记录（增量保存到 time_vs_cycle.npy）
    _time_history = _restore_hist('time_vs_cycle.npy')   # ★ 续训时从 .npy 恢复

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
    for j, disp_i in enumerate(disp[start_j:], start=start_j):
        field_comp.lmbda = torch.tensor(disp_i).to(device)
        if (j % _log_every == 0) or _frac_detected or _dense_sampling:
            print(f'idx: {j}; displacement/amplitude: {field_comp.lmbda}')
        loss_data = list()
        start = time.time()

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

        # ------------------------------------------------------------------
        # 训练（与 Manav 完全相同的结构；仅多传 f_fatigue 和 crack_tip_weights）
        # ------------------------------------------------------------------
        if j == 0 or optimizer_dict["n_epochs_LBFGS"] > 0:
            n_epochs = max(optimizer_dict["n_epochs_LBFGS"], 1)
            NNparams  = field_comp.parameters()
            optimizer = get_optimizer(NNparams, "LBFGS")
            loss_data1 = fit(
                field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
                optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
                intermediateModel_path=None, writer=writer, training_dict=training_dict,
                f_fatigue=f_fatigue,              # ★ 传入疲劳退化函数
                supervised_dict=_supervised_dict, # ★ MIT-8
            )
            loss_data = loss_data + loss_data1

        if optimizer_dict["n_epochs_RPROP"] > 0:
            n_epochs  = optimizer_dict["n_epochs_RPROP"]
            NNparams  = field_comp.parameters()
            optimizer = get_optimizer(NNparams, "RPROP")
            loss_data2 = fit_with_early_stopping(
                field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
                optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
                min_delta=optimizer_dict["optim_rel_tol"],
                intermediateModel_path=intermediateModel_path,
                writer=writer, training_dict=training_dict,
                f_fatigue=f_fatigue,              # ★ 传入疲劳退化函数
                supervised_dict=_supervised_dict, # ★ MIT-8
            )
            loss_data = loss_data + loss_data2

        end = time.time()
        _cycle_seconds = end - start
        print(f"Execution time: {_cycle_seconds/60:.03f}minutes")
        _time_history.append([j, _cycle_seconds])

        # ------------------------------------------------------------------
        # Manav 原始：更新相场不可逆性历史变量 hist_alpha
        # ------------------------------------------------------------------
        hist_alpha = field_comp.update_hist_alpha(inp)

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

            # ★ α-3 XFEM-jump: compute x_tip from ψ⁺ for Heaviside anchoring
            # Same hook as α-2 multi-head — opt-in via hasattr(net, 'update_tip')
            if _xfem_enabled and T_conn is not None:
                if not _frac_detected:
                    if j > 0:
                        _x_tip_new = compute_x_tip_psi(inp, psi_plus_elem, T_conn, top_k=10)
                        _x_tip_floor = _crack_mouth_x - 0.02
                        if _x_tip_new >= _x_tip_floor:
                            field_comp.x_tip = _x_tip_new
                    field_comp.net.update_tip(field_comp.x_tip, 0.0)
                    if (j % _log_every == 0) or _frac_detected or _dense_sampling:
                        _eps = getattr(field_comp.net, 'heaviside_eps', float('nan'))
                        print(f"  [XFEM-jump]  x_tip={field_comp.x_tip:.4f}  H_eps={_eps:.4g}")
                # fracture confirmed: tip stays frozen at last position

            # ★ 每圈 Kt 计算（复用已有 psi_plus_elem，零额外前向传播）
            if _nominal_mask is not None:
                _psi0      = psi_plus_elem.detach().cpu().numpy()
                _top10_idx = np.argsort(_psi0)[-10:]
                _psi_tip   = float(_psi0[_top10_idx].mean())
                _psi_nom   = (float(_psi0[_nominal_mask].mean())
                               if _n_nominal > 0 else float(_psi0.mean()))
                _Kt        = (_psi_tip / _psi_nom) ** 0.5 if _psi_nom > 1e-20 else float('nan')
                _Kt_history.append(_Kt)

            # ★ α-3 T4 stationarity diagnostic: argmax(ψ⁺) per cycle
            _psi_argmax_history.append(int(np.argmax(psi_plus_elem.detach().cpu().numpy())))

            # 更新疲劳历史变量 ᾱ（Carrara Eq.39 或 Golahmar Eq.31）
            hist_fat = update_fatigue_history(
                hist_fat, psi_plus_elem, psi_plus_prev, fatigue_dict
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
            _ckpt_data['hist_fat']      = hist_fat
            _ckpt_data['psi_plus_prev'] = psi_plus_prev
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
            if _psi_argmax_history:                                              # ★ α-3 T4
                np.save(str(trainedModel_path / 'psi_argmax_vs_cycle.npy'),
                        np.array(_psi_argmax_history))
            if _ansatz_enabled and _c_singular_history:                     # ★ Direction 5
                np.save(str(trainedModel_path / 'c_singular_vs_cycle.npy'),
                        np.array(_c_singular_history))   # shape (N,2): [cycle_idx, c_val]
            if _time_history:
                np.save(str(trainedModel_path / 'time_vs_cycle.npy'),
                        np.array(_time_history))   # shape (N,2): [cycle_idx, seconds]

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
            if _psi_argmax_history:                                              # ★ α-3 T4
                np.save(str(trainedModel_path / 'psi_argmax_vs_cycle.npy'),
                        np.array(_psi_argmax_history))
            if _ansatz_enabled and _c_singular_history:                    # ★ Direction 5
                np.save(str(trainedModel_path / 'c_singular_vs_cycle.npy'),
                        np.array(_c_singular_history))
            if _time_history:
                np.save(str(trainedModel_path / 'time_vs_cycle.npy'),
                        np.array(_time_history))
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
    if fatigue_on and _psi_argmax_history:                                  # ★ α-3 T4
        np.save(str(trainedModel_path / 'psi_argmax_vs_cycle.npy'),
                np.array(_psi_argmax_history))
    if fatigue_on and _ansatz_enabled and _c_singular_history:             # ★ Direction 5
        np.save(str(trainedModel_path / 'c_singular_vs_cycle.npy'),
                np.array(_c_singular_history))
    if fatigue_on and _time_history:
        np.save(str(trainedModel_path / 'time_vs_cycle.npy'),
                np.array(_time_history))
