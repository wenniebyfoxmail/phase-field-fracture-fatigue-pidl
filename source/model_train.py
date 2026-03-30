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


# ── α 场快照辅助函数 ────────────────────────────────────────────────────────
def _save_alpha_snapshot(inp, alpha, T_conn, cycle, snapshot_dir):
    """保存第 cycle 圈的 α 场 PNG，固定色轴 [0,1]，用于观察疲劳裂缝演化。"""
    inp_np   = inp.detach().cpu().numpy()
    alpha_np = alpha.detach().cpu().numpy().flatten()
    T_np     = T_conn.detach().cpu().numpy() if torch.is_tensor(T_conn) else T_conn

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


# ── 裂缝尖端检测（通用，基于与 crack_mouth 的距离）────────────────────────────
def get_crack_tip(alpha_vals, node_coords, crack_mouth_xy, threshold=0.9):
    """
    返回裂缝尖端坐标和裂缝长度（从 crack_mouth 到最远受损节点的距离）。

    参数
    ----
    alpha_vals    : torch.Tensor, shape (N,)   — 各节点相场值
    node_coords   : torch.Tensor, shape (N, 2) — 各节点 (x, y) 坐标
    crack_mouth_xy: torch.Tensor, shape (2,)   — 初始裂缝尖端坐标（SENS: [0.0, 0.0]）
    threshold     : float                      — α > threshold 认为属于裂缝带

    返回
    ----
    crack_tip_xy  : torch.Tensor, shape (2,)   — 裂缝尖端坐标
    crack_length  : float                      — 裂缝长度（距离量纲）
    """
    damaged = alpha_vals > threshold
    if damaged.sum() == 0:
        return crack_mouth_xy, 0.0
    d_coords = node_coords[damaged]
    dist = torch.norm(d_coords - crack_mouth_xy, dim=1)
    idx  = dist.argmax()
    return d_coords[idx], dist[idx].item()


def train(field_comp, disp, pffmodel, matprop, crack_dict, numr_dict,
          optimizer_dict, training_dict, coarse_mesh_file, fine_mesh_file,
          device, trainedModel_path, intermediateModel_path, writer,
          fatigue_dict=None):                        # ★ 新增参数
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
        NNparams = field_comp.net.parameters()
        optimizer = get_optimizer(NNparams, "LBFGS")
        loss_data1 = fit(
            field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
            optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
            intermediateModel_path=None, writer=writer, training_dict=training_dict
            # 预训练不传 f_fatigue，使用默认值 1.0
        )
        loss_data = loss_data + loss_data1

        n_epochs = optimizer_dict["n_epochs_RPROP"]
        NNparams = field_comp.net.parameters()
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
    else:
        f_fatigue = 1.0
        print("[Fatigue] fatigue_on=False → 等价 Manav 原始行为")

    # -------------------------------------------------------------------------
    # ★ 检测最新 step checkpoint，实现断点续训
    # -------------------------------------------------------------------------
    _step_ckpts = sorted(
        trainedModel_path.glob('checkpoint_step_*.pt'),
        key=lambda p: int(p.stem.rsplit('_', 1)[-1])
    )
    start_j = 0
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
                f_fatigue     = compute_fatigue_degrad(hist_fat, fatigue_dict)
            start_j = _last_j + 1
            print(f"[Checkpoint] 从 step {_last_j} 恢复，继续 step {start_j}/{len(disp)-1}")

    # -------------------------------------------------------------------------
    # ★ 断裂检测 & 可视化参数（仅 fatigue_on=True 时有意义）
    # -------------------------------------------------------------------------
    E_el_history  = []           # 每圈弹性能，供后处理画 E_el vs N 曲线
    E_el_max      = 0.0          # 历史最大弹性能（断裂判据基准）
    _frac_detected          = False   # 是否已触发骤降检测
    _frac_cycle             = None    # 首次检测到骤降的圈号
    _frac_confirm_remaining = 0       # 剩余确认圈数（>0 时持续观察）

    _E_drop_ratio   = fatigue_dict.get('fracture_E_drop_ratio',   0.5)
    _confirm_cycles = fatigue_dict.get('fracture_confirm_cycles',  10)
    _plot_every     = fatigue_dict.get('plot_every_n_cycles',      20)

    # ★ crack_length 判据参数（通用：距 crack_mouth 的距离，与加载方向无关）
    _crack_length_threshold = fatigue_dict.get('crack_length_threshold', 0.46)
    _alpha_crack_thr        = fatigue_dict.get('x_tip_alpha_thr', 0.90)
    _crack_mouth            = torch.tensor([0.0, 0.0], device=device)  # SENS: 预裂缝尖端
    _x_tip_history          = []    # 每圈 crack_length，供后处理（变量名保持兼容）

    # α 快照目录（与 best_models/ 同级）
    _snapshot_dir = trainedModel_path.parent / Path('alpha_snapshots')
    if fatigue_on:
        _snapshot_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 主循环：每次迭代对应一个加载步（单调模式）或一个完整循环（疲劳模式）
    # =========================================================================
    for j, disp_i in enumerate(disp[start_j:], start=start_j):
        field_comp.lmbda = torch.tensor(disp_i).to(device)
        print(f'idx: {j}; displacement/amplitude: {field_comp.lmbda}')
        loss_data = list()
        start = time.time()

        # ------------------------------------------------------------------
        # 训练（与 Manav 完全相同的结构；仅多传 f_fatigue）
        # ------------------------------------------------------------------
        if j == 0 or optimizer_dict["n_epochs_LBFGS"] > 0:
            n_epochs = max(optimizer_dict["n_epochs_LBFGS"], 1)
            NNparams  = field_comp.net.parameters()
            optimizer = get_optimizer(NNparams, "LBFGS")
            loss_data1 = fit(
                field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
                optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
                intermediateModel_path=None, writer=writer, training_dict=training_dict,
                f_fatigue=f_fatigue    # ★ 传入疲劳退化函数
            )
            loss_data = loss_data + loss_data1

        if optimizer_dict["n_epochs_RPROP"] > 0:
            n_epochs  = optimizer_dict["n_epochs_RPROP"]
            NNparams  = field_comp.net.parameters()
            optimizer = get_optimizer(NNparams, "RPROP")
            loss_data2 = fit_with_early_stopping(
                field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
                optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
                min_delta=optimizer_dict["optim_rel_tol"],
                intermediateModel_path=intermediateModel_path,
                writer=writer, training_dict=training_dict,
                f_fatigue=f_fatigue    # ★ 传入疲劳退化函数
            )
            loss_data = loss_data + loss_data2

        end = time.time()
        print(f"Execution time: {(end-start)/60:.03f}minutes")

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
            if T_conn is not None:
                with torch.no_grad():
                    u_eval, v_eval, alpha_eval = field_comp.fieldCalculation(inp)
                psi_plus_elem = get_psi_plus_per_elem(
                    inp, u_eval, v_eval, alpha_eval,
                    matprop, pffmodel, area_T, T_conn
                )
            else:
                # 自动微分模式：需要 inp 开启梯度
                inp_tmp = inp.detach().clone().requires_grad_(True)
                u_eval, v_eval, alpha_eval = field_comp.fieldCalculation(inp_tmp)
                psi_plus_elem = get_psi_plus_per_elem(
                    inp_tmp, u_eval, v_eval, alpha_eval,
                    matprop, pffmodel, area_T, T_conn=None
                )

            # 更新疲劳历史变量 ᾱ（Carrara Eq.39 或 Golahmar Eq.31）
            hist_fat = update_fatigue_history(
                hist_fat, psi_plus_elem, psi_plus_prev, fatigue_dict
            )

            # 更新疲劳退化函数 f(ᾱ)（Carrara Eq.41 或 Eq.42）
            f_fatigue = compute_fatigue_degrad(hist_fat, fatigue_dict)

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

            # 日志输出
            f_min = f_fatigue.min().item()
            f_mean = f_fatigue.mean().item()
            alpha_bar_max = hist_fat.max().item()
            print(f"  [Fatigue step {j}] ᾱ_max={alpha_bar_max:.4e} | "
                  f"f_min={f_min:.4f} | f_mean={f_mean:.4f}")

            # ── E_el 计算（用于断裂检测和后处理曲线）─────────────────────
            with torch.no_grad():
                u_el, v_el, alpha_el = field_comp.fieldCalculation(inp)
                E_el_val, _, _ = compute_energy(
                    inp, u_el, v_el, alpha_el, hist_alpha,
                    matprop, pffmodel, area_T, T_conn, f_fatigue
                )
            E_el_scalar = float(E_el_val.item())
            E_el_history.append(E_el_scalar)
            E_el_max = max(E_el_max, E_el_scalar)

            # ── α 场快照：每 _plot_every 圈保存一次，断裂确认期每圈都保存 ──
            if j % _plot_every == 0 or _frac_detected:
                _save_alpha_snapshot(inp, alpha_el, T_conn, j, _snapshot_dir)

            # ── 裂缝尖端位置计算（通用：距 crack_mouth 的最远受损节点距离）──────
            _, crack_length = get_crack_tip(
                alpha_el.flatten(), inp, _crack_mouth, threshold=_alpha_crack_thr
            )
            _x_tip_history.append(crack_length)
            print(f"  [crack_length] = {crack_length:.4f}")

            # ── 断裂检测：E_el 骤降 OR crack_length 超阈值（二者满足其一即触发）──
            _E_triggered    = (E_el_max > 0 and E_el_scalar < _E_drop_ratio * E_el_max)
            _xtip_triggered = (crack_length >= _crack_length_threshold)

            if not _frac_detected and (_E_triggered or _xtip_triggered):
                _frac_detected = True
                _frac_cycle    = j
                _frac_confirm_remaining = _confirm_cycles
                _reasons = []
                if _E_triggered:
                    _reasons.append(f"E_el={E_el_scalar:.3e} < "
                                    f"{_E_drop_ratio}×{E_el_max:.3e}")
                if _xtip_triggered:
                    _reasons.append(f"crack_length={crack_length:.4f} >= "
                                    f"{_crack_length_threshold}")
                print(f"  [Fracture?] cycle {j}: {' | '.join(_reasons)}. "
                      f"Continuing {_confirm_cycles} confirmation cycles...")
            elif _frac_detected:
                _frac_confirm_remaining -= 1
                # 两个判据都失效时才重置（防 E_el 数值波动误重置）
                _E_recovered    = (E_el_scalar >= _E_drop_ratio * E_el_max)
                _xtip_retracted = (crack_length < _crack_length_threshold)
                if _E_recovered and _xtip_retracted:
                    print(f"  [Fracture reset] cycle {j}: "
                          f"E_el recovered AND crack_length retracted → reset.")
                    _frac_detected = False
                    _frac_cycle    = None

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

        # ── 断裂确认：判据持续满足 confirm_cycles 圈 → 停止 ──────────────
        if fatigue_on and _frac_detected and _frac_confirm_remaining <= 0:
            print(f"  [Fracture confirmed] Stopping at cycle {j}. "
                  f"First detected at cycle {_frac_cycle}.")
            np.save(str(trainedModel_path / 'E_el_vs_cycle.npy'),
                    np.array(E_el_history))
            np.save(str(trainedModel_path / 'x_tip_vs_cycle.npy'),
                    np.array(_x_tip_history))
            break

    # 循环正常结束（跑完所有圈）也保存历史
    if fatigue_on and E_el_history:
        np.save(str(trainedModel_path / 'E_el_vs_cycle.npy'),
                np.array(E_el_history))
    if fatigue_on and _x_tip_history:
        np.save(str(trainedModel_path / 'x_tip_vs_cycle.npy'),
                np.array(_x_tip_history))
