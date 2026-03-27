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

from input_data_from_mesh import prep_input_data
from fit import fit, fit_with_early_stopping
from optim import *
from plotting import plot_field

# ★ 新增：疲劳相关函数（仅在 fatigue_on=True 时实际调用）
from compute_energy import get_psi_plus_per_elem
from fatigue_history import update_fatigue_history, compute_fatigue_degrad


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
    # =========================================================================

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

    torch.save(field_comp.net.state_dict(),
               trainedModel_path / Path('trained_1NN_initTraining.pt'))
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
        # hist_fat[e]     : 各单元疲劳历史变量 ᾱ（初始为 0）
        # psi_plus_prev[e]: 上一步各单元退化拉伸能密度 ψ⁺（初始为 0）
        # f_fatigue[e]    : 各单元疲劳退化函数 f(ᾱ)（初始为 1.0）
        hist_fat      = torch.zeros(n_elem, device=device)
        psi_plus_prev = torch.zeros(n_elem, device=device)
        f_fatigue     = torch.ones(n_elem, device=device)
        print(f"[Fatigue] fatigue_on=True | accum='{fatigue_dict.get('accum_type','carrara')}' | "
              f"degrad='{fatigue_dict.get('degrad_type','asymptotic')}' | "
              f"alpha_T={fatigue_dict.get('alpha_T', 1.0):.4g}")
    else:
        # fatigue 关闭：f_fatigue=1.0（标量），与 Manav 原始完全等价
        f_fatigue = 1.0
        print("[Fatigue] fatigue_on=False → 等价 Manav 原始行为")

    # =========================================================================
    # 主循环：每次迭代对应一个加载步（单调模式）或一个完整循环（疲劳模式）
    # =========================================================================
    for j, disp_i in enumerate(disp):
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

            # 保存本步 ψ⁺ 供下一步做差分
            psi_plus_prev = psi_plus_elem.clone()

            # 日志输出
            f_min = f_fatigue.min().item()
            f_mean = f_fatigue.mean().item()
            alpha_bar_max = hist_fat.max().item()
            print(f"  [Fatigue step {j}] ᾱ_max={alpha_bar_max:.4e} | "
                  f"f_min={f_min:.4f} | f_mean={f_mean:.4f}")

        # ------------------------------------------------------------------
        # 保存模型和损失（与 Manav 完全相同）
        # ------------------------------------------------------------------
        torch.save(field_comp.net.state_dict(),
                   trainedModel_path / Path('trained_1NN_' + str(j) + '.pt'))
        with open(trainedModel_path / Path('trainLoss_1NN_' + str(j) + '.npy'), 'wb') as f:
            np.save(f, np.asarray(loss_data))
