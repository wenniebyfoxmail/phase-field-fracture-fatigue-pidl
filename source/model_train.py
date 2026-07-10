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
import time
from pathlib import Path
from contextlib import contextmanager
import matplotlib
matplotlib.use('Agg')          # 非交互后端，训练中安全调用
import matplotlib.pyplot as plt
import matplotlib.tri as tri

from input_data_from_mesh import prep_input_data
from fit import fit, fit_with_early_stopping
from optim import *
from plotting import plot_field

# ★ 新增：疲劳相关函数（仅在 fatigue_on=True 时实际调用）
from compute_energy import (get_psi_plus_per_elem, compute_energy,
                            compute_energy_per_elem, gradients,
                            stress as effective_stress)
from fatigue_history import (update_fatigue_history, compute_fatigue_degrad,
                              mirror_y_indices, mirror_alpha_y)

# ★ Direction 4: Williams ψ⁺ 重心估计裂尖坐标（可选，仅在 williams_enabled=True 时调用）
from williams_features import compute_x_tip_psi

# ★ 2026-05-13 Branch 2 C6: FI-PINN adaptive sampling via full-residual reweight
from adaptive_sampling import compute_adaptive_weights

from inverse_params import TrainablePositiveScalar, scalar_value


def _resolve_f_fatigue(f_fatigue):
    """Evaluate dynamic fatigue degradation callables inside each fresh graph."""
    return f_fatigue() if callable(f_fatigue) else f_fatigue


def _oracle_cycle_scale(step_idx, cfg):
    """Map a PIDL training step to a FEM physical cycle and load-scale."""
    mode = cfg.get("cycle_mode", "training_step")
    if mode == "training_step":
        return int(step_idx), 1.0, 0, True
    if mode != "explicit_cycle_peak_scaled":
        raise ValueError(
            "oracle cycle_mode must be 'training_step' or "
            f"'explicit_cycle_peak_scaled', got {mode!r}"
        )

    factors = cfg.get("explicit_cycle_factors")
    n_substeps = int(cfg.get(
        "explicit_cycle_substeps",
        len(factors) if factors is not None else 1,
    ))
    if n_substeps <= 0:
        raise ValueError("oracle explicit_cycle_substeps must be positive")
    if factors is None:
        factors = [1.0] * n_substeps
    if len(factors) != n_substeps:
        raise ValueError(
            "oracle explicit_cycle_factors length must match "
            "explicit_cycle_substeps"
        )

    substep = int(step_idx % n_substeps)
    cycle_start = int(cfg.get("cycle_start", 1))
    cycle_idx = int(step_idx // n_substeps) + cycle_start
    load_factor = float(factors[substep])
    scale_power = float(cfg.get("load_factor_power", 2.0))
    scale = float(cfg.get("target_scale", 1.0)) * (load_factor ** scale_power)
    peak_substep = int(cfg.get("peak_substep_index", n_substeps - 2))
    return cycle_idx, scale, substep, substep == peak_substep


def _adaptive_lambda_hist_update(field_comp, inp, hist_alpha, matprop, pffmodel,
                                 area_T, T_conn, f_fatigue, current_lambda,
                                 cfg, element_mask=None,
                                 g_stiffness_override=None,
                                 irreversibility_penalty_cfg=None):
    """Balance the irreversibility penalty gradient against elastic/damage terms."""
    params = [p for p in field_comp.parameters() if p.requires_grad]
    if not params:
        return float(current_lambda), {
            "lambda_hat": float(current_lambda),
            "grad_E_el": 0.0,
            "grad_E_d": 0.0,
            "grad_E_hist": 0.0,
        }

    u, v, alpha = field_comp.fieldCalculation(inp)
    loss_E_el, loss_E_d, loss_hist = compute_energy(
        inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
        _resolve_f_fatigue(f_fatigue), element_mask=element_mask,
        g_stiffness_override=g_stiffness_override,
        irreversibility_penalty_cfg=irreversibility_penalty_cfg,
    )
    eps = torch.as_tensor(1.0e-30, dtype=loss_E_el.dtype, device=loss_E_el.device)

    def _grad_l2(loss_scalar, retain_graph=True):
        grads = torch.autograd.grad(
            torch.log10(loss_scalar + eps),
            params,
            allow_unused=True,
            retain_graph=retain_graph,
        )
        total = torch.zeros((), dtype=loss_E_el.dtype, device=loss_E_el.device)
        for grad in grads:
            if grad is not None:
                total = total + grad.detach().pow(2).sum()
        return float(torch.sqrt(total).detach().cpu().item())

    grad_E_el = _grad_l2(loss_E_el, retain_graph=True)
    grad_E_d = _grad_l2(loss_E_d, retain_graph=True)
    grad_E_hist = _grad_l2(loss_hist, retain_graph=False)

    lam_min = float(cfg.get("lambda_hist_min", 1.0e-3))
    lam_max = float(cfg.get("lambda_hist_max", 1.0))
    smooth = float(cfg.get("lambda_hist_smooth", 0.0))
    denom = max(grad_E_hist, 1.0e-30)
    lambda_hat = max(grad_E_el, grad_E_d) / denom
    lambda_hat = min(max(lambda_hat, lam_min), lam_max)
    new_lambda = (smooth * float(current_lambda)) + ((1.0 - smooth) * lambda_hat)
    new_lambda = min(max(new_lambda, lam_min), lam_max)

    return float(new_lambda), {
        "lambda_hat": float(lambda_hat),
        "grad_E_el": float(grad_E_el),
        "grad_E_d": float(grad_E_d),
        "grad_E_hist": float(grad_E_hist),
    }


def _energy_gradient_diagnostics(field_comp, inp, hist_alpha, matprop, pffmodel,
                                 area_T, T_conn, f_fatigue, element_mask=None,
                                 g_stiffness_override=None,
                                 irreversibility_penalty_cfg=None):
    """Measure pre-history-refresh energy-term gradient norms."""
    params = [p for p in field_comp.parameters() if p.requires_grad]
    if not params:
        return {
            "E_el": 0.0,
            "E_d": 0.0,
            "E_hist": 0.0,
            "grad_E_el": 0.0,
            "grad_E_d": 0.0,
            "grad_E_hist": 0.0,
        }

    u, v, alpha = field_comp.fieldCalculation(inp)
    loss_E_el, loss_E_d, loss_hist = compute_energy(
        inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
        _resolve_f_fatigue(f_fatigue), element_mask=element_mask,
        g_stiffness_override=g_stiffness_override,
        irreversibility_penalty_cfg=irreversibility_penalty_cfg,
    )
    eps = torch.as_tensor(1.0e-30, dtype=loss_E_el.dtype, device=loss_E_el.device)

    def _grad_l2(loss_scalar, retain_graph=True):
        grads = torch.autograd.grad(
            torch.log10(loss_scalar + eps),
            params,
            allow_unused=True,
            retain_graph=retain_graph,
        )
        total = torch.zeros((), dtype=loss_E_el.dtype, device=loss_E_el.device)
        for grad in grads:
            if grad is not None:
                total = total + grad.detach().pow(2).sum()
        return float(torch.sqrt(total).detach().cpu().item())

    return {
        "E_el": float(loss_E_el.detach().cpu().item()),
        "E_d": float(loss_E_d.detach().cpu().item()),
        "E_hist": float(loss_hist.detach().cpu().item()),
        "grad_E_el": _grad_l2(loss_E_el, retain_graph=True),
        "grad_E_d": _grad_l2(loss_E_d, retain_graph=True),
        "grad_E_hist": _grad_l2(loss_hist, retain_graph=False),
    }


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


def _parse_cycle_set(raw_cycles):
    if raw_cycles is None:
        return set()
    if isinstance(raw_cycles, str):
        raw_cycles = [c.strip() for c in raw_cycles.split(",") if c.strip()]
    return {int(c) for c in raw_cycles}


def _tensor_to_numpy(value, like_tensor=None):
    if torch.is_tensor(value):
        return value.detach().cpu().numpy()
    if like_tensor is not None:
        n = int(like_tensor.numel())
        return np.full(n, float(value), dtype=np.float32)
    return np.asarray(value)


def _element_to_node_projection(elem_values, T_conn, n_nodes, reduce="max"):
    """Project element oracle values to nodes for hard hist_alpha floors."""
    if T_conn is None:
        return elem_values
    conn = T_conn.to(device=elem_values.device, dtype=torch.long)
    flat_nodes = conn.reshape(-1)
    flat_vals = elem_values.reshape(-1).repeat_interleave(conn.shape[1])
    if reduce == "mean":
        out = torch.zeros(n_nodes, dtype=elem_values.dtype, device=elem_values.device)
        cnt = torch.zeros(n_nodes, dtype=elem_values.dtype, device=elem_values.device)
        out.scatter_add_(0, flat_nodes, flat_vals)
        cnt.scatter_add_(0, flat_nodes, torch.ones_like(flat_vals))
        return out / cnt.clamp(min=1.0)
    if reduce != "max":
        raise ValueError(f"unknown element-to-node reduce={reduce!r}")
    out = torch.full(
        (n_nodes,), -torch.inf, dtype=elem_values.dtype, device=elem_values.device
    )
    out.scatter_reduce_(0, flat_nodes, flat_vals, reduce="amax", include_self=True)
    return torch.where(torch.isfinite(out), out, torch.zeros_like(out))


def _element_mean_from_nodes(node_values, T_conn):
    if T_conn is None:
        return node_values.reshape(-1)
    return (
        node_values[T_conn[:, 0]]
        + node_values[T_conn[:, 1]]
        + node_values[T_conn[:, 2]]
    ) / 3.0


def _save_pre_step0_baseline_diagnostics(
    inp,
    T_conn,
    area_T,
    field_comp,
    hist_alpha,
    hist_fat,
    f_fatigue,
    psi_plus_prev,
    disp0,
    out_path,
    protocol_metadata=None,
):
    """Save the actual post-pretraining, pre-step0 history baseline."""
    protocol_metadata = protocol_metadata or {}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    old_lambda = field_comp.lmbda
    try:
        field_comp.lmbda = torch.tensor([float(disp0)], device=inp.device, dtype=inp.dtype)
        with torch.no_grad():
            _, _, alpha_pretrain = field_comp.fieldCalculation(inp)
            alpha_pretrain = alpha_pretrain.reshape(-1).detach()
            hist_alpha = hist_alpha.reshape(-1).detach()
            hist_fat = hist_fat.reshape(-1).detach()
            psi_plus_prev = psi_plus_prev.reshape(-1).detach()
            f_current = _resolve_f_fatigue(f_fatigue)
            if not torch.is_tensor(f_current):
                f_current = torch.full_like(hist_fat, float(f_current))
            f_current = f_current.reshape(-1).detach()
            hist_alpha_elem = _element_mean_from_nodes(hist_alpha, T_conn)
            alpha_pretrain_elem = _element_mean_from_nodes(alpha_pretrain, T_conn)
            if T_conn is None:
                elem_x = inp[:, 0]
                elem_y = inp[:, 1]
                conn_np = np.empty((0, 3), dtype=np.int64)
            else:
                elem_x = (
                    inp[T_conn[:, 0], 0]
                    + inp[T_conn[:, 1], 0]
                    + inp[T_conn[:, 2], 0]
                ) / 3.0
                elem_y = (
                    inp[T_conn[:, 0], 1]
                    + inp[T_conn[:, 1], 1]
                    + inp[T_conn[:, 2], 1]
                ) / 3.0
                conn_np = _tensor_to_numpy(T_conn).astype(np.int64)
    finally:
        field_comp.lmbda = old_lambda
    np.savez_compressed(
        out_path,
        state_label=np.array("pre_step0_post_pretraining_baseline"),
        step_index=np.array([-1], dtype=np.int32),
        next_step_index=np.array([0], dtype=np.int32),
        next_step_displacement=np.array([float(disp0)], dtype=np.float32),
        nodes=_tensor_to_numpy(inp).astype(np.float32),
        connectivity=conn_np,
        element_centroids=np.column_stack([
            _tensor_to_numpy(elem_x).reshape(-1),
            _tensor_to_numpy(elem_y).reshape(-1),
        ]).astype(np.float32),
        element_area=_tensor_to_numpy(area_T).reshape(-1).astype(np.float32),
        hist_alpha_node=_tensor_to_numpy(hist_alpha).reshape(-1).astype(np.float32),
        hist_alpha_elem=_tensor_to_numpy(hist_alpha_elem).reshape(-1).astype(np.float32),
        alpha_pretrain_node=_tensor_to_numpy(alpha_pretrain).reshape(-1).astype(np.float32),
        alpha_pretrain_elem=_tensor_to_numpy(alpha_pretrain_elem).reshape(-1).astype(np.float32),
        alpha_pretrain_minus_hist_node=(
            _tensor_to_numpy(alpha_pretrain - hist_alpha).reshape(-1).astype(np.float32)
        ),
        alpha_pretrain_minus_hist_elem=(
            _tensor_to_numpy(alpha_pretrain_elem - hist_alpha_elem).reshape(-1).astype(np.float32)
        ),
        hist_fat_elem=_tensor_to_numpy(hist_fat).reshape(-1).astype(np.float32),
        f_fatigue_elem=_tensor_to_numpy(f_current).reshape(-1).astype(np.float32),
        psi_plus_prev_elem=_tensor_to_numpy(psi_plus_prev).reshape(-1).astype(np.float32),
        initial_alpha_protocol=np.array(
            str(protocol_metadata.get("initial_alpha_protocol", "none"))
        ),
        initial_alpha_target=np.array(
            [float(protocol_metadata.get("initial_alpha_target", np.nan))],
            dtype=np.float32,
        ),
        histories_preserved=np.array(
            [bool(protocol_metadata.get("histories_preserved", True))]
        ),
    )
    print(f"[PreStep0Baseline] saved {out_path}")


def _principal_2d(xx, yy, xy):
    mean = 0.5 * (xx + yy)
    radius = torch.sqrt((0.5 * (xx - yy)) ** 2 + xy**2)
    return mean + radius, mean - radius


def _full_linear_stress(eps_xx, eps_yy, eps_xy, matprop):
    trace = eps_xx + eps_yy
    sig_xx = matprop.mat_lmbda * trace + 2.0 * matprop.mat_mu * eps_xx
    sig_yy = matprop.mat_lmbda * trace + 2.0 * matprop.mat_mu * eps_yy
    sig_xy = 2.0 * matprop.mat_mu * eps_xy
    return sig_xx, sig_yy, sig_xy


def _save_element_diagnostics(inp, T_conn, u, v, alpha, hist_alpha, hist_fat,
                              f_fatigue, psi_plus_elem, psi_plus_prev,
                              matprop, pffmodel, area_T, cycle, out_dir,
                              psi_history_elem=None,
                              history_increment_elem=None,
                              alpha_feedback_target_elem=None,
                              alpha_feedback_mask_elem=None,
                              oracle_target_elem=None,
                              oracle_mask_elem=None,
                              g_stiffness_override_elem=None,
                              irreversibility_penalty_cfg=None):
    """Save cycle-end element fields for FEM/PIDL mechanism comparison."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with torch.no_grad():
        if T_conn is not None:
            alpha_elem = (
                alpha[T_conn[:, 0]] + alpha[T_conn[:, 1]] + alpha[T_conn[:, 2]]
            ) / 3.0
            hist_alpha_elem = (
                hist_alpha[T_conn[:, 0]]
                + hist_alpha[T_conn[:, 1]]
                + hist_alpha[T_conn[:, 2]]
            ) / 3.0
            elem_x = (
                inp[T_conn[:, 0], 0] + inp[T_conn[:, 1], 0] + inp[T_conn[:, 2], 0]
            ) / 3.0
            elem_y = (
                inp[T_conn[:, 0], 1] + inp[T_conn[:, 1], 1] + inp[T_conn[:, 2], 1]
            ) / 3.0
        else:
            alpha_elem = alpha.flatten()
            hist_alpha_elem = hist_alpha.flatten()
            elem_x = inp[:, 0]
            elem_y = inp[:, 1]

        E_el_elem, E_d_elem, E_hist_elem = compute_energy_per_elem(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
            f_fatigue=f_fatigue,
            g_stiffness_override=g_stiffness_override_elem,
            irreversibility_penalty_cfg=irreversibility_penalty_cfg,
        )
        _, _, E_hist_legacy_elem = compute_energy_per_elem(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
            f_fatigue=f_fatigue,
            g_stiffness_override=g_stiffness_override_elem,
            irreversibility_penalty_cfg=None,
        )
        _, _, E_hist_fem_gp_tri3_elem = compute_energy_per_elem(
            inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
            f_fatigue=f_fatigue,
            g_stiffness_override=g_stiffness_override_elem,
            irreversibility_penalty_cfg={
                "enable": True,
                "mode": "fem_gp_tri3",
            },
        )
        eps_xx, eps_yy, eps_xy, _, _ = gradients(
            inp, u, v, alpha, area_T, T_conn
        )
        eps_trace = eps_xx + eps_yy
        eps_eq = torch.sqrt(eps_xx**2 + eps_yy**2 + 2.0 * eps_xy**2)
        eps_1, eps_2 = _principal_2d(eps_xx, eps_yy, eps_xy)
        sig_raw_xx, sig_raw_yy, sig_raw_xy = _full_linear_stress(
            eps_xx, eps_yy, eps_xy, matprop
        )
        sig_raw_1, sig_raw_2 = _principal_2d(sig_raw_xx, sig_raw_yy, sig_raw_xy)
        sig_eff_xx, sig_eff_yy, sig_eff_xy = effective_stress(
            eps_xx, eps_yy, eps_xy, alpha_elem, matprop, pffmodel,
            g_stiffness_override=g_stiffness_override_elem,
        )
        sig_eff_1, sig_eff_2 = _principal_2d(sig_eff_xx, sig_eff_yy, sig_eff_xy)

    hist_fat_np = _tensor_to_numpy(hist_fat, like_tensor=alpha_elem).reshape(-1)
    f_fatigue_np = _tensor_to_numpy(f_fatigue, like_tensor=alpha_elem).reshape(-1)
    psi_plus_np = _tensor_to_numpy(psi_plus_elem).reshape(-1)
    psi_prev_np = _tensor_to_numpy(psi_plus_prev).reshape(-1)
    psi_history_np = _tensor_to_numpy(
        psi_history_elem if psi_history_elem is not None else psi_plus_elem
    ).reshape(-1)
    history_increment_np = _tensor_to_numpy(
        history_increment_elem
        if history_increment_elem is not None
        else torch.relu((psi_history_elem if psi_history_elem is not None else psi_plus_elem)
                        - psi_plus_prev)
    ).reshape(-1)
    E_el_np = _tensor_to_numpy(E_el_elem).reshape(-1)
    E_d_np = _tensor_to_numpy(E_d_elem).reshape(-1)
    E_hist_np = _tensor_to_numpy(E_hist_elem).reshape(-1)
    E_hist_legacy_np = _tensor_to_numpy(E_hist_legacy_elem).reshape(-1)
    E_hist_fem_gp_tri3_np = _tensor_to_numpy(E_hist_fem_gp_tri3_elem).reshape(-1)
    if alpha_feedback_target_elem is None:
        alpha_feedback_target_np = np.full_like(E_el_np, np.nan, dtype=np.float32)
    else:
        alpha_feedback_target_np = _tensor_to_numpy(
            alpha_feedback_target_elem, like_tensor=alpha_elem
        ).reshape(-1).astype(np.float32)
    if alpha_feedback_mask_elem is None:
        alpha_feedback_mask_np = np.zeros_like(E_el_np, dtype=np.float32)
    else:
        alpha_feedback_mask_np = _tensor_to_numpy(
            alpha_feedback_mask_elem, like_tensor=alpha_elem
        ).reshape(-1).astype(np.float32)
    if oracle_target_elem is None:
        oracle_target_np = np.full_like(E_el_np, np.nan, dtype=np.float32)
    else:
        oracle_target_np = _tensor_to_numpy(
            oracle_target_elem, like_tensor=alpha_elem
        ).reshape(-1).astype(np.float32)
    if oracle_mask_elem is None:
        oracle_mask_np = np.zeros_like(E_el_np, dtype=np.float32)
    else:
        oracle_mask_np = _tensor_to_numpy(
            oracle_mask_elem, like_tensor=alpha_elem
        ).reshape(-1).astype(np.float32)
    # `psi_plus_elem` is the active fatigue driver g(alpha)*psi0.  Save both
    # the active value and the raw undegraded psi0 approximation to avoid the
    # recurring FEM/PIDL comparison ambiguity.
    with torch.no_grad():
        g_alpha, _ = pffmodel.Edegrade(alpha_elem)
    g_alpha_np = _tensor_to_numpy(g_alpha).reshape(-1)
    if g_stiffness_override_elem is None:
        g_solver_np = g_alpha_np
        g_override_np = np.full_like(E_el_np, np.nan, dtype=np.float32)
    else:
        g_solver_np = _tensor_to_numpy(
            g_stiffness_override_elem, like_tensor=alpha_elem
        ).reshape(-1)
        g_override_np = g_solver_np.astype(np.float32)
    psi_raw_from_g_alpha_np = psi_plus_np / np.maximum(g_alpha_np, 1e-30)
    psi_raw_from_g_solver_np = psi_plus_np / np.maximum(g_solver_np, 1e-30)

    np.savez_compressed(
        out_dir / f"element_fields_cycle_{cycle:04d}.npz",
        cycle=np.array([cycle], dtype=np.int32),
        elem_x=_tensor_to_numpy(elem_x).reshape(-1).astype(np.float32),
        elem_y=_tensor_to_numpy(elem_y).reshape(-1).astype(np.float32),
        area_elem=_tensor_to_numpy(area_T).reshape(-1).astype(np.float32),
        alpha_elem=_tensor_to_numpy(alpha_elem).reshape(-1).astype(np.float32),
        hist_alpha_elem=_tensor_to_numpy(hist_alpha_elem).reshape(-1).astype(np.float32),
        alpha_minus_hist_alpha_elem=(
            _tensor_to_numpy(alpha_elem - hist_alpha_elem).reshape(-1).astype(np.float32)
        ),
        alpha_feedback_target_elem=alpha_feedback_target_np,
        alpha_feedback_mask_elem=alpha_feedback_mask_np,
        oracle_target_elem=oracle_target_np,
        oracle_mask_elem=oracle_mask_np,
        hist_fat_elem=hist_fat_np.astype(np.float32),
        f_fatigue_elem=f_fatigue_np.astype(np.float32),
        psi_plus_elem=psi_plus_np.astype(np.float32),  # backward-compatible active driver
        psi_active_elem=psi_plus_np.astype(np.float32),
        psi_history_driver_elem=psi_history_np.astype(np.float32),
        delta_alpha_bar_input_elem=history_increment_np.astype(np.float32),
        psi_raw_elem=psi_raw_from_g_alpha_np.astype(np.float32),
        psi_raw_from_g_alpha_elem=psi_raw_from_g_alpha_np.astype(np.float32),
        psi_raw_from_g_solver_elem=psi_raw_from_g_solver_np.astype(np.float32),
        g_alpha_elem=g_alpha_np.astype(np.float32),
        g_solver_elem=g_solver_np.astype(np.float32),
        g_stiffness_override_elem=g_override_np,
        g_solver_override_active=np.array(
            [g_stiffness_override_elem is not None],
            dtype=np.bool_,
        ),
        psi_plus_prev_elem=psi_prev_np.astype(np.float32),
        E_el_elem=E_el_np.astype(np.float32),
        E_d_elem=E_d_np.astype(np.float32),
        E_hist_elem=E_hist_np.astype(np.float32),
        E_hist_legacy_elem=E_hist_legacy_np.astype(np.float32),
        E_hist_fem_gp_tri3_elem=E_hist_fem_gp_tri3_np.astype(np.float32),
        eps_xx_elem=_tensor_to_numpy(eps_xx).reshape(-1).astype(np.float32),
        eps_yy_elem=_tensor_to_numpy(eps_yy).reshape(-1).astype(np.float32),
        eps_xy_elem=_tensor_to_numpy(eps_xy).reshape(-1).astype(np.float32),
        eps_trace_elem=_tensor_to_numpy(eps_trace).reshape(-1).astype(np.float32),
        eps_eq_elem=_tensor_to_numpy(eps_eq).reshape(-1).astype(np.float32),
        eps_principal_1_elem=_tensor_to_numpy(eps_1).reshape(-1).astype(np.float32),
        eps_principal_2_elem=_tensor_to_numpy(eps_2).reshape(-1).astype(np.float32),
        sigma_raw_xx_elem=_tensor_to_numpy(sig_raw_xx).reshape(-1).astype(np.float32),
        sigma_raw_yy_elem=_tensor_to_numpy(sig_raw_yy).reshape(-1).astype(np.float32),
        sigma_raw_xy_elem=_tensor_to_numpy(sig_raw_xy).reshape(-1).astype(np.float32),
        sigma_raw_principal_1_elem=_tensor_to_numpy(sig_raw_1).reshape(-1).astype(np.float32),
        sigma_raw_principal_2_elem=_tensor_to_numpy(sig_raw_2).reshape(-1).astype(np.float32),
        sigma_effective_xx_elem=_tensor_to_numpy(sig_eff_xx).reshape(-1).astype(np.float32),
        sigma_effective_yy_elem=_tensor_to_numpy(sig_eff_yy).reshape(-1).astype(np.float32),
        sigma_effective_xy_elem=_tensor_to_numpy(sig_eff_xy).reshape(-1).astype(np.float32),
        sigma_effective_principal_1_elem=_tensor_to_numpy(sig_eff_1).reshape(-1).astype(np.float32),
        sigma_effective_principal_2_elem=_tensor_to_numpy(sig_eff_2).reshape(-1).astype(np.float32),
        residual_abs_Eel_Ed=(np.abs(E_el_np) + np.abs(E_d_np)).astype(np.float32),
    )


def _resolve_output_layer(net):
    """Return the final 3-row output layer for plain/Fourier nets."""
    raw_net = getattr(net, "_orig_mod", net)  # torch.compile wrapper, if present
    if hasattr(raw_net, "output_layer"):
        return raw_net.output_layer
    if hasattr(raw_net, "inner") and hasattr(raw_net.inner, "output_layer"):
        return raw_net.inner.output_layer
    raise AttributeError("Could not locate output_layer for staged head training")


def _raw_alpha_value_for_target(field_comp, target_alpha):
    """Invert the configured alpha constraint for a uniform initialization."""
    target = float(np.clip(target_alpha, 1.0e-6, 1.0 - 1.0e-6))
    constraint = field_comp.alpha_constraint
    support = getattr(constraint, "support", None)
    if support is not None:
        return 2.0 * float(support) * (target - 0.5)
    return float(np.log(target / (1.0 - target)))


def _preset_uniform_current_alpha(field_comp, target_alpha):
    """Set only the current NN alpha head to a spatially uniform target."""
    output_layer = _resolve_output_layer(field_comp.net)
    raw_alpha = _raw_alpha_value_for_target(field_comp, target_alpha)
    with torch.no_grad():
        output_layer.weight[2, :].zero_()
        output_layer.bias[2].fill_(raw_alpha)
    return raw_alpha


@contextmanager
def _head_only_phase(field_comp, rows, label):
    """Temporarily optimise only selected rows of the final output head."""
    output_layer = _resolve_output_layer(field_comp.net)
    row_mask = torch.zeros_like(output_layer.weight)
    row_mask[list(rows), :] = 1.0
    bias_mask = torch.zeros_like(output_layer.bias)
    bias_mask[list(rows)] = 1.0

    old_requires_grad = {p: p.requires_grad for p in field_comp.parameters()}
    hooks = []
    try:
        for p in old_requires_grad:
            p.requires_grad_(False)
        output_layer.weight.requires_grad_(True)
        output_layer.bias.requires_grad_(True)
        hooks.append(output_layer.weight.register_hook(lambda grad: grad * row_mask))
        hooks.append(output_layer.bias.register_hook(lambda grad: grad * bias_mask))
        print(f"  [StagedAlpha] {label}: output rows {list(rows)} active")
        yield [output_layer.weight, output_layer.bias]
    finally:
        for hook in hooks:
            hook.remove()
        for p, requires_grad in old_requires_grad.items():
            p.requires_grad_(requires_grad)


@contextmanager
def _local_patch_only_phase(field_comp):
    """Temporarily optimise only the compact local patch parameters."""
    patch_params = list(field_comp.local_patch_parameters())
    if not patch_params:
        raise RuntimeError("local_patch_training requested but local patch is disabled")

    old_requires_grad = {p: p.requires_grad for p in field_comp.parameters()}
    try:
        for p in old_requires_grad:
            p.requires_grad_(False)
        for p in patch_params:
            p.requires_grad_(True)
        print(f"  [LocalPatch] patch-only warm-up: {len(patch_params)} tensors active")
        yield patch_params
    finally:
        for p, requires_grad in old_requires_grad.items():
            p.requires_grad_(requires_grad)


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
          sidecar_S1_dict=None,                      # ★ forward-compat: static sidecar sampler
          sidecar_S2_dict=None,                      # ★ forward-compat: adaptive sidecar sampler
          grad_annealing_state=None,                 # ★ 2026-05-19 Algorithm 1 (Wang 2020)
          delta1_dict=None,                          # ★ 2026-05-20 C6 δ-1 element-level IS
          j_path_dict=None,                          # ★ 2026-05-20 J path-independence reg
          inverse_dict=None):                        # ★ inverse scalar calibration
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
    _irreversibility_penalty_cfg = (numr_dict or {}).get(
        "irreversibility_penalty", {}
    ) or {}
    _irr_cfg_enabled = (
        bool(_irreversibility_penalty_cfg)
        if isinstance(_irreversibility_penalty_cfg, bool)
        else bool(_irreversibility_penalty_cfg.get("enable", False))
    )
    if _irr_cfg_enabled:
        _irr_mode = (
            _irreversibility_penalty_cfg.get("mode", "fem_gp_tri3")
            if isinstance(_irreversibility_penalty_cfg, dict)
            else "fem_gp_tri3"
        )
        if _irr_mode != "fem_gp_tri3":
            raise ValueError(
                "numr_dict['irreversibility_penalty']['mode'] must be "
                f"'fem_gp_tri3', got {_irr_mode!r}"
            )
        print(f"[IrreversibilityPenalty] FEM-like triangle quadrature enabled: mode={_irr_mode}")
    inverse_dict = inverse_dict or {}
    _inverse_alpha_T = None
    if inverse_dict.get("enable", False):
        target = inverse_dict.get("target", "alpha_T")
        if target != "alpha_T":
            raise ValueError(f"unsupported inverse target {target!r}; expected 'alpha_T'")
        _inverse_alpha_T = TrainablePositiveScalar(
            float(inverse_dict.get("initial_value", fatigue_dict.get("alpha_T", 0.5))),
            min_value=float(inverse_dict.get("min_value", 1.0e-4)),
            max_value=inverse_dict.get("max_value", None),
            device=device,
        )
        field_comp.extra_trainable_params = list(_inverse_alpha_T.parameters())
        fatigue_dict["alpha_T"] = _inverse_alpha_T
        print(
            f"[Inverse] trainable alpha_T enabled | init={scalar_value(_inverse_alpha_T):.6g} "
            f"| min={_inverse_alpha_T.min_value:.3g} | max={_inverse_alpha_T.max_value}"
        )
    if (sidecar_S1_dict or {}).get("enable", False) or (sidecar_S2_dict or {}).get("enable", False):
        raise NotImplementedError(
            "This model_train.py build accepts sidecar_S1/S2 arguments for "
            "runner compatibility, but does not implement sidecar sampling."
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
        inp, T_conn, area_T, hist_alpha = prep_input_data(
            matprop, pffmodel, crack_dict, numr_dict,
            mesh_file=coarse_mesh_file, device=device
        )
        outp = torch.zeros(inp.shape[0], 1).to(device)
        # full-batch (batch_size=N) + shuffle=False: a DataLoader here just tore the
        # tensor into N rows via __getitem__ and re-collated every optimizer step
        # (profiled at ~50-70% of wall). Feed the single full batch directly instead.
        training_set = [(inp, outp)]
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
            irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
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
            irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
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
    # full-batch (batch_size=N) + shuffle=False: DataLoader was pure overhead here
    # (tore tensor into N rows + re-collated every optimizer step, ~50-70% of wall).
    training_set = [(inp, outp)]

    # ★ δ-1 element-level IS: create ElementDataset (uniform p_e init)
    _d1_cfg = delta1_dict if (delta1_dict and delta1_dict.get('enable', False)) else None
    _d1_dataset = None
    if _d1_cfg is not None:
        from dataset_element import ElementDataset, compute_residual_proxy
        n_elem_tmp = area_T.shape[0]
        _d1_dataset = ElementDataset(n_elem_tmp)
        _d1_dataset.samples_per_epoch = _d1_cfg.get('samples_per_epoch', None)
        _d1_start_cycle = int(_d1_cfg.get('start_cycle', 1))
        print(f"[δ-1] ElementDataset ready: n_elem={n_elem_tmp}, "
              f"K={_d1_dataset.samples_per_epoch or 'full'}, start_cycle={_d1_start_cycle}")

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
              f"alpha_T={scalar_value(fatigue_dict.get('alpha_T', 1.0)):.4g}")

        # ★ Direction 6.1 + 2026-05-08 A1: 预计算元素形心
        # Used by: (a) spatial α_T modulation; (b) post-hoc mirror α ratchet break
        _sp_cfg     = fatigue_dict.get('spatial_alpha_T', {})
        _mirror_cfg = fatigue_dict.get('mirror_alpha_y',  {})
        _void_cfg   = fatigue_dict.get('void_notch_mask', {})
        _need_centroids = (
            (_sp_cfg.get('enable', False) and T_conn is not None) or
            (_mirror_cfg.get('enable', False) and T_conn is not None) or
            (_void_cfg.get('enable', False) and T_conn is not None)
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
            if _void_cfg.get('enable', False):
                print(f"[void-notch] enabled: x <= {_void_cfg.get('x_max', 0.0)}, "
                      f"|y| <= {_void_cfg.get('half_width', 0.02)}")
        else:
            elem_centroids = None
            if _sp_cfg.get('enable', False):
                print("[spAlphaT] WARNING: enable=True but T_conn is None "
                      "(autodiff mode); fallback to scalar α_T")
            if _mirror_cfg.get('enable', False):
                print("[mirrorα] WARNING: enable=True but T_conn is None "
                      "(autodiff mode); mirror α NOT applied")
            if _void_cfg.get('enable', False):
                print("[void-notch] WARNING: enable=True but T_conn is None "
                      "(autodiff mode); void-like mask NOT applied")

        _void_notch_mask = None
        _void_energy_mask = None
        if _void_cfg.get('enable', False) and elem_centroids is not None:
            _vn_xmax = float(_void_cfg.get('x_max', 0.0))
            _vn_hw = float(_void_cfg.get('half_width', 0.02))
            _void_notch_mask = (
                (elem_centroids[:, 0] <= _vn_xmax)
                & (elem_centroids[:, 1].abs() <= _vn_hw)
            )
            if _void_cfg.get('mask_energy', True):
                _void_energy_mask = (~_void_notch_mask).to(dtype=area_T.dtype)
            print(f"[void-notch] mask elements: void_like={int(_void_notch_mask.sum().item())} "
                  f"active={int((~_void_notch_mask).sum().item())} "
                  f"mask_energy={_void_cfg.get('mask_energy', True)} "
                  f"mask_fatigue={_void_cfg.get('mask_fatigue', True)}")
        else:
            _void_energy_mask = None

        # Pre-compute mirror index map once (mesh fixed across cycles)
        _mirror_idx = None
        if _mirror_cfg.get('enable', False) and elem_centroids is not None:
            _mirror_idx = mirror_y_indices(elem_centroids)
            _resid = ((elem_centroids[_mirror_idx, 1] + elem_centroids[:, 1]).abs().mean().item())
            print(f"[mirrorα] mirror_idx pre-computed; mean |y_i + y_mirror[i]| = {_resid:.3e}")

        def _make_f_fatigue(hist_snapshot):
            f_val = compute_fatigue_degrad(
                hist_snapshot, fatigue_dict, elem_centroids=elem_centroids
            )
            if (_void_notch_mask is not None
                    and _void_cfg.get('mask_fatigue', True)):
                f_val = f_val.clone()
                f_val[_void_notch_mask] = 1.0
            return f_val

        def _fatigue_for_fit(hist_snapshot):
            if _inverse_alpha_T is not None:
                return lambda hist=hist_snapshot: _make_f_fatigue(hist)
            return _make_f_fatigue(hist_snapshot)

        f_fatigue = _fatigue_for_fit(hist_fat)
        _history_driver_mode = fatigue_dict.get('history_driver_mode', 'current_active')
        _valid_history_driver_modes = {'current_active', 'lagged_g', 'raw'}
        if _history_driver_mode not in _valid_history_driver_modes:
            raise ValueError(
                "fatigue_dict['history_driver_mode'] must be one of "
                f"{sorted(_valid_history_driver_modes)}, got {_history_driver_mode!r}"
            )
        _history_driver_reduction = fatigue_dict.get('history_driver_reduction', {})
        if (_history_driver_reduction or {}).get('enable', False) \
                and _history_driver_mode != 'current_active':
            raise ValueError(
                "fatigue_dict['history_driver_reduction'] is currently valid only "
                "with history_driver_mode='current_active'."
            )
        if (_history_driver_reduction or {}).get('enable', False):
            _hdr_mode = _history_driver_reduction.get('mode', 'probe_g_mean')
            _valid_hdr_modes = {'probe_g_mean', 'fem_gp_tri3_g_mean'}
            if _hdr_mode not in _valid_hdr_modes:
                raise ValueError(
                    "fatigue_dict['history_driver_reduction']['mode'] must be "
                    f"one of {sorted(_valid_hdr_modes)}, got {_hdr_mode!r}"
                )
        print(f"[HistoryDriver] mode={_history_driver_mode}")
        if (_history_driver_reduction or {}).get('enable', False):
            print(
                "[HistoryDriverReduction] "
                f"mode={_history_driver_reduction.get('mode', 'probe_g_mean')}"
            )
        _lagged_stiffness_cfg = fatigue_dict.get('lagged_stiffness', {}) or {}
        _lagged_stiffness_enabled = bool(
            _lagged_stiffness_cfg.get('enable', False)
        )
        _lagged_stiffness_history_policy = _lagged_stiffness_cfg.get(
            'history_policy', 'coupled'
        )
        _valid_lagged_stiffness_policies = {'coupled', 'solver_only'}
        if (
            _lagged_stiffness_enabled
            and _lagged_stiffness_history_policy
            not in _valid_lagged_stiffness_policies
        ):
            raise ValueError(
                "fatigue_dict['lagged_stiffness']['history_policy'] must be "
                f"one of {sorted(_valid_lagged_stiffness_policies)}, got "
                f"{_lagged_stiffness_history_policy!r}"
            )
        if _lagged_stiffness_enabled:
            print(
                "[LaggedStiffness] solver g uses previous hist_alpha; "
                f"history_policy={_lagged_stiffness_history_policy}"
            )

        _initial_state_cfg = fatigue_dict.get("initial_state_oracle", {}) or {}
        if _initial_state_cfg.get("enable", False):
            def _restart_tensor(value, like, name):
                if value is None:
                    return None
                if torch.is_tensor(value):
                    out = value.to(device=like.device, dtype=like.dtype).reshape(-1)
                else:
                    out = torch.as_tensor(
                        value, device=like.device, dtype=like.dtype
                    ).reshape(-1)
                if out.numel() != like.numel():
                    raise ValueError(
                        f"initial_state_oracle['{name}'] has {out.numel()} values; "
                        f"expected {like.numel()}"
                    )
                return out.detach().reshape_as(like)

            _restart_cycle = _initial_state_cfg.get("fem_cycle", "unknown")
            _hist_alpha0 = _restart_tensor(
                _initial_state_cfg.get("hist_alpha", None),
                hist_alpha,
                "hist_alpha",
            )
            if _hist_alpha0 is not None:
                hist_alpha = torch.maximum(hist_alpha, _hist_alpha0).detach()

            _hist_fat0 = _restart_tensor(
                _initial_state_cfg.get("hist_fat", None),
                hist_fat,
                "hist_fat",
            )
            if _hist_fat0 is not None:
                _hist_fat_policy = _initial_state_cfg.get(
                    "hist_fat_policy", "replace"
                )
                if _hist_fat_policy == "replace":
                    hist_fat = _hist_fat0.detach()
                elif _hist_fat_policy == "max":
                    hist_fat = torch.maximum(hist_fat, _hist_fat0).detach()
                else:
                    raise ValueError(
                        "initial_state_oracle['hist_fat_policy'] must be "
                        f"'replace' or 'max', got {_hist_fat_policy!r}"
                    )

            _psi_prev0 = _restart_tensor(
                _initial_state_cfg.get("psi_plus_prev", None),
                psi_plus_prev,
                "psi_plus_prev",
            )
            if _psi_prev0 is not None:
                psi_plus_prev = _psi_prev0.detach()

            _f_fatigue0 = _restart_tensor(
                _initial_state_cfg.get("f_fatigue", None),
                hist_fat,
                "f_fatigue",
            )
            if _f_fatigue0 is not None:
                f_fatigue = _f_fatigue0.detach()
            else:
                f_fatigue = _fatigue_for_fit(hist_fat)
            _f0 = _resolve_f_fatigue(f_fatigue)
            print(
                f"[InitialStateOracle] FEM c={_restart_cycle} | "
                f"hist_alpha max={hist_alpha.max().item():.6e} | "
                f"hist_fat max={hist_fat.max().item():.6e} | "
                f"psi_plus_prev max={psi_plus_prev.max().item():.6e} | "
                f"f_min={_f0.min().item():.6e}"
            )
    else:
        f_fatigue = 1.0
        elem_centroids = None
        _void_notch_mask = None
        _void_energy_mask = None
        _history_driver_mode = 'off'
        _history_driver_reduction = {}
        _lagged_stiffness_enabled = False
        _lagged_stiffness_history_policy = 'off'

        def _make_f_fatigue(_hist_snapshot):
            return f_fatigue

        def _fatigue_for_fit(_hist_snapshot):
            return f_fatigue

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

    # ★ 2026-06-03: adaptive lambda for the irreversibility/history penalty.
    # This is intentionally separate from C6 adaptive sampling: it changes only
    # the scalar multiplier on E_hist in the objective.
    _lambda_hist_cfg = fatigue_dict.get("adaptive_lambda_hist", {}) if fatigue_on else {}
    _lambda_hist_enabled = bool(_lambda_hist_cfg.get("enable", False))
    _lambda_hist_weight = float(_lambda_hist_cfg.get("lambda_hist_initial", 1.0))
    _lambda_hist_start_cycle = int(_lambda_hist_cfg.get("start_cycle", 1))
    if _lambda_hist_enabled:
        print(
            "[AdaptiveLambdaHist] enabled | "
            f"initial={_lambda_hist_weight:.3e} | "
            f"bounds=[{float(_lambda_hist_cfg.get('lambda_hist_min', 1.0e-3)):.3e}, "
            f"{float(_lambda_hist_cfg.get('lambda_hist_max', 1.0)):.3e}] | "
            f"smooth={float(_lambda_hist_cfg.get('lambda_hist_smooth', 0.0)):.3f} | "
            f"start_cycle={_lambda_hist_start_cycle}"
        )

    # ★ 2026-05-30: controlled staged-alpha discriminator.
    # This does not change the variational objective.  It only changes the
    # optimiser path inside each cycle: uv output head -> alpha output head ->
    # normal joint solve.  Because the current MLP has one shared trunk, this is
    # deliberately a low-risk head-staging proxy for FEM alternate minimisation.
    _staged_cfg = fatigue_dict.get('staged_alpha', {}) if fatigue_on else {}
    _staged_alpha = bool(_staged_cfg.get('enable', False))
    if _staged_alpha:
        print(f"[StagedAlpha] enabled | uv_head={_staged_cfg.get('uv_head_epochs', 0)} "
              f"| alpha_head={_staged_cfg.get('alpha_head_epochs', 0)} "
              f"| joint={optimizer_dict.get('n_epochs_RPROP', 0)}")

    # ★ 2026-05-30: local-patch authority discriminator.
    # This freezes the global NN briefly and lets the compact support patch fit
    # the same variational loss.  It changes optimiser authority only; the
    # energy terms and fatigue/history update remain exactly the usual ones.
    _patch_train_cfg = fatigue_dict.get('local_patch_training', {}) if fatigue_on else {}
    _local_patch_training = bool(_patch_train_cfg.get('enable', False))
    if _local_patch_training:
        if not getattr(field_comp, 'local_patch_enabled', False):
            raise ValueError("fatigue_dict['local_patch_training'] enabled but local_patch_dict is off")
        print(f"[LocalPatch] training enabled | warm_epochs="
              f"{_patch_train_cfg.get('warm_epochs', 0)} "
              f"| joint={optimizer_dict.get('n_epochs_RPROP', 0)}")

    # -------------------------------------------------------------------------
    # ★ 检测最新 step checkpoint，实现断点续训
    # -------------------------------------------------------------------------
    _step_ckpts = sorted(
        trainedModel_path.glob('checkpoint_step_*.pt'),
        key=lambda p: int(p.stem.rsplit('_', 1)[-1])
    )
    start_j = 0
    _did_restore = False   # ★ 标志位：True → 后续 history lists 从 .npy 初始化
    _frac_state_from_ckpt = {}  # stash for fracture detection state from checkpoint
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
                f_fatigue     = _fatigue_for_fit(hist_fat)
                if _lambda_hist_enabled and 'lambda_hist_weight' in _ckpt:
                    _lambda_hist_weight = float(_ckpt['lambda_hist_weight'])
                # ★ Stash fracture detection state (backwards-compat: old ckpts lack these keys)
                _frac_state_from_ckpt = {
                    'detected':  _ckpt.get('_frac_detected',          False),
                    'cycle':     _ckpt.get('_frac_cycle',             None),
                    'remaining': _ckpt.get('_frac_confirm_remaining', 0),
                }
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

    _lambda_hist_history = _restore_hist('lambda_hist_vs_cycle.npy')
    if _lambda_hist_enabled and _lambda_hist_history:
        try:
            _lambda_hist_weight = float(_lambda_hist_history[-1][1])
            print(f"[AdaptiveLambdaHist] restored lambda_hist={_lambda_hist_weight:.6e}")
        except (TypeError, IndexError, ValueError):
            print("[AdaptiveLambdaHist] WARNING: could not parse restored lambda history")

    # ★ 每圈 Kt 日志：预计算元素形心 + 远场掩码（仅数值梯度模式有效）
    _Kt_history = _restore_hist('Kt_vs_cycle.npy')       # ★ 续训时从 .npy 恢复
    _Kt         = float('nan')   # 当前圈 Kt（初始化为 nan，日志安全输出）

    # ★ Direction 5: Enriched Ansatz 每圈记录可学习标量 c_singular
    _ansatz_enabled     = getattr(field_comp, 'ansatz_enabled', False)
    _c_singular_history = _restore_hist('c_singular_vs_cycle.npy')   # ★ 续训时从 .npy 恢复
    _inverse_alpha_T_history = _restore_hist('inverse_alpha_T_vs_cycle.npy')
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

    _initial_alpha_protocol_cfg = (
        fatigue_dict.get("initial_alpha_protocol", {}) if fatigue_on else {}
    ) or {}
    _initial_alpha_protocol_active = bool(
        _initial_alpha_protocol_cfg.get("enable", False)
    )
    _initial_alpha_protocol_metadata = {
        "initial_alpha_protocol": "none",
        "histories_preserved": True,
    }
    if _initial_alpha_protocol_active:
        if start_j != 0:
            print(
                "[InitialAlphaProtocol] resume detected; skipping hard-alpha preset "
                f"because start_j={start_j}"
            )
            _initial_alpha_protocol_active = False
        else:
            _mode_init_alpha = _initial_alpha_protocol_cfg.get(
                "mode", "uniform_current_alpha"
            )
            if _mode_init_alpha != "uniform_current_alpha":
                raise ValueError(
                    "fatigue_dict['initial_alpha_protocol']['mode'] must be "
                    f"'uniform_current_alpha', got {_mode_init_alpha!r}"
                )
            if (
                _initial_alpha_protocol_cfg.get(
                    "requires_first_displacement_zero", True
                )
                and abs(float(disp[0])) > 1.0e-12
            ):
                raise ValueError(
                    "initial_alpha_protocol requires the first training step to "
                    f"be U=0, got disp[0]={float(disp[0]):.6e}"
                )
            _target_alpha0 = float(
                _initial_alpha_protocol_cfg.get("target_alpha", 1.0)
            )
            _raw_alpha0 = _preset_uniform_current_alpha(
                field_comp, _target_alpha0
            )
            with torch.no_grad():
                _, _, _alpha0_check = field_comp.fieldCalculation(inp)
            _initial_alpha_protocol_metadata = {
                "initial_alpha_protocol": _mode_init_alpha,
                "initial_alpha_target": _target_alpha0,
                "histories_preserved": bool(
                    _initial_alpha_protocol_cfg.get("preserve_histories", True)
                ),
            }
            print(
                "[InitialAlphaProtocol] current NN alpha preset before step0 | "
                f"mode={_mode_init_alpha} target={_target_alpha0:.6e} "
                f"raw={_raw_alpha0:.6e} | alpha min/max="
                f"{_alpha0_check.min().item():.6e}/"
                f"{_alpha0_check.max().item():.6e} | "
                "hist_alpha/hist_fat/f_fatigue/psi_plus_prev preserved"
            )

    # α 快照目录（与 best_models/ 同级）
    _snapshot_dir = trainedModel_path.parent / Path('alpha_snapshots')
    if fatigue_on:
        _snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Optional full element-field diagnostics for cycle-matched FEM/PIDL studies.
    # Default is off because saving every cycle can produce large archives.
    _elem_diag_cfg = fatigue_dict.get('element_diagnostics', {}) or {}
    _elem_diag_enabled = fatigue_on and _elem_diag_cfg.get('enable', False)
    _elem_diag_cycles = _parse_cycle_set(_elem_diag_cfg.get('cycles', []))
    _elem_diag_every = _elem_diag_cfg.get('every_n_cycles', None)
    _elem_diag_dense = _elem_diag_cfg.get('dense_sampling', True)
    _elem_diag_on_fracture = _elem_diag_cfg.get('on_fracture', True)
    _elem_diag_dir = trainedModel_path.parent / Path(
        _elem_diag_cfg.get('dir', 'element_diagnostics')
    )
    if _elem_diag_enabled:
        _elem_diag_dir.mkdir(parents=True, exist_ok=True)
        _every_msg = _elem_diag_every if _elem_diag_every else "off"
        print(f"[ElementDiagnostics] enabled | cycles={sorted(_elem_diag_cycles)} "
              f"| every={_every_msg} | dense={_elem_diag_dense} "
              f"| out={_elem_diag_dir}")

    # Optional pre-history-refresh gradient diagnostics.  These are separate
    # from adaptive lambda so fixed-energy experiments still record whether
    # E_el, E_d, and E_hist have comparable optimisation authority.
    _grad_diag_cfg = fatigue_dict.get('gradient_diagnostics', {}) or {}
    _grad_diag_enabled = fatigue_on and _grad_diag_cfg.get('enable', False)
    _grad_diag_cycles = _parse_cycle_set(_grad_diag_cfg.get('cycles', []))
    _grad_diag_every = _grad_diag_cfg.get('every_n_cycles', None)
    _grad_diag_dense = _grad_diag_cfg.get('dense_sampling', True)
    _grad_diag_on_fracture = _grad_diag_cfg.get('on_fracture', True)
    _grad_diag_history = _restore_hist('energy_gradient_terms_vs_cycle.npy')
    if _grad_diag_enabled:
        _every_msg = _grad_diag_every if _grad_diag_every else "off"
        print(f"[GradientDiagnostics] enabled | cycles={sorted(_grad_diag_cycles)} "
              f"| every={_every_msg} | dense={_grad_diag_dense}")

    _g_stiffness_override_current = None
    _f_fatigue_override_current = None

    if fatigue_on and start_j == 0:
        _save_pre_step0_baseline_diagnostics(
            inp,
            T_conn,
            area_T,
            field_comp,
            hist_alpha,
            hist_fat,
            f_fatigue,
            psi_plus_prev,
            disp[0],
            trainedModel_path.parent / Path("pre_step0_baseline_diagnostics.npz"),
            protocol_metadata=_initial_alpha_protocol_metadata,
        )

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
        _alpha_feedback_target_elem = None
        _alpha_feedback_mask_elem = None
        _oracle_target_elem = None
        _oracle_mask_elem = None
        if _lagged_stiffness_enabled:
            if T_conn is None:
                _alpha_lag_elem = hist_alpha.flatten()
            else:
                _alpha_lag_elem = (
                    hist_alpha[T_conn[:, 0]]
                    + hist_alpha[T_conn[:, 1]]
                    + hist_alpha[T_conn[:, 2]]
                ) / 3.0
            _target_g_lag, _ = pffmodel.Edegrade(_alpha_lag_elem)
            _g_stiffness_override_current = _target_g_lag.detach()
            _oracle_target_elem = _g_stiffness_override_current
            _oracle_mask_elem = torch.ones_like(
                _g_stiffness_override_current, dtype=torch.bool
            )
            print(
                f"  [LaggedStiffness] pidl j={j}: solver g(prev hist_alpha) "
                f"min/max={_g_stiffness_override_current.min().item():.3e}/"
                f"{_g_stiffness_override_current.max().item():.3e}; "
                f"history_policy={_lagged_stiffness_history_policy}"
            )
        if mit8_dict is not None and mit8_dict.get('enable', False):
            _K = int(mit8_dict.get('K', 0))
            _fem_cycle = j + int(mit8_dict.get('fem_cycle_offset', 0))
            if 1 <= _fem_cycle <= _K:
                _supervised_dict = {
                    'fem_sup': mit8_dict['fem_sup'],
                    'cycle_idx': _fem_cycle,
                    'lambda': float(mit8_dict.get('lambda', 1.0)),
                    'pidl_centroids': mit8_dict['pidl_centroids'],
                    'loss_kind': mit8_dict.get('loss_kind', 'mse_log'),
                    'target_kind': mit8_dict.get('target_kind', 'psi'),
                    'every_n_epochs': int(mit8_dict.get('every_n_epochs', 1)),
                    'mask': mit8_dict.get('mask', None),
                }
                print(f"  [MIT-8] pidl j={j}, FEM c={_fem_cycle}/{_K}: "
                      f"supervised lambda={_supervised_dict['lambda']}")

        # FEM soft-feedback oracle: force the NN field toward a mapped FEM
        # alpha or psi target at peak substeps.  The target is pre-projected
        # once per PIDL step, then reused inside all optimizer epochs.
        _alpha_fb_cfg = (
            fatigue_dict.get('alpha_feedback_oracle', None)
            if fatigue_on else None
        )
        if _alpha_fb_cfg is not None and _alpha_fb_cfg.get('enable', False):
            _mode_fb = _alpha_fb_cfg.get('mode', 'peak_supervised_alpha')
            if _mode_fb not in {'peak_supervised_alpha', 'peak_supervised_psi_raw'}:
                raise ValueError(
                    "alpha_feedback_oracle mode must be "
                    "'peak_supervised_alpha' or 'peak_supervised_psi_raw', "
                    f"got {_mode_fb!r}"
                )
            _fem_cycle_fb, _, _substep_fb, _is_peak_fb = _oracle_cycle_scale(
                int(j), _alpha_fb_cfg
            )
            _max_cycle_fb = int(_alpha_fb_cfg.get('max_cycle', 0))
            _cycle_in_range_fb = (
                _max_cycle_fb <= 0 or _fem_cycle_fb <= _max_cycle_fb
            )
            if _is_peak_fb and _cycle_in_range_fb:
                if _supervised_dict is not None:
                    raise ValueError(
                        "alpha_feedback_oracle cannot be combined with another "
                        "supervised_dict in the same step"
                    )
                _fem_sup_fb = _alpha_fb_cfg['fem_sup']
                _pidl_centroids_fb = _alpha_fb_cfg['pidl_centroids']
                if _mode_fb == 'peak_supervised_alpha':
                    _target_fb = _fem_sup_fb.alpha_target_at_cycle(
                        _fem_cycle_fb, _pidl_centroids_fb,
                        device=inp.device, dtype=torch.float32,
                    ).detach()
                    _target_kind_fb = 'alpha'
                    _default_loss_fb = 'mse_lin'
                else:
                    _target_fb = _fem_sup_fb.psi_target_at_cycle(
                        _fem_cycle_fb, _pidl_centroids_fb,
                        device=inp.device, dtype=torch.float32,
                    ).detach()
                    _target_kind_fb = 'psi'
                    _default_loss_fb = 'mse_log'
                _alpha_feedback_target_elem = _target_fb
                _base_mask_fb = _alpha_fb_cfg.get('override_mask', None)
                if _base_mask_fb is None:
                    _alpha_feedback_mask_elem = torch.ones_like(
                        _target_fb, dtype=torch.bool
                    )
                else:
                    _alpha_feedback_mask_elem = _base_mask_fb.to(inp.device).bool()
                _target_min_fb = _alpha_fb_cfg.get('target_mask_min', None)
                if _target_min_fb is not None:
                    _alpha_feedback_mask_elem = (
                        _alpha_feedback_mask_elem
                        & (_target_fb >= float(_target_min_fb))
                    )
                _supervised_dict = {
                    'fem_sup': _fem_sup_fb,
                    'cycle_idx': _fem_cycle_fb,
                    'lambda': float(_alpha_fb_cfg.get('lambda', 1.0)),
                    'pidl_centroids': _pidl_centroids_fb,
                    'loss_kind': _alpha_fb_cfg.get('loss_kind', _default_loss_fb),
                    'target_kind': _target_kind_fb,
                    'target': _target_fb,
                    'every_n_epochs': int(_alpha_fb_cfg.get('every_n_epochs', 1)),
                    'mask': _alpha_feedback_mask_elem,
                }
                _oracle_target_elem = _target_fb
                _oracle_mask_elem = _alpha_feedback_mask_elem
                print(
                    f"  [AlphaFeedback] pidl j={j} substep={_substep_fb}, "
                    f"FEM c={_fem_cycle_fb}: {_target_kind_fb} supervision "
                    f"lambda={_supervised_dict['lambda']}, "
                    f"mask={int(_alpha_feedback_mask_elem.sum().item())}/"
                    f"{int(_alpha_feedback_mask_elem.numel())}"
                )

        _g_oracle_cfg = (
            fatigue_dict.get('g_stiffness_oracle', None)
            if fatigue_on else None
        )
        if _g_oracle_cfg is not None and _g_oracle_cfg.get('enable', False):
            _fem_cycle_g, _, _substep_g, _is_peak_g = _oracle_cycle_scale(
                int(j), _g_oracle_cfg
            )
            _max_cycle_g = int(_g_oracle_cfg.get('max_cycle', 0))
            _cycle_in_range_g = _max_cycle_g <= 0 or _fem_cycle_g <= _max_cycle_g
            if _is_peak_g and _cycle_in_range_g:
                _target_g = _g_oracle_cfg['fem_sup'].g_stiffness_target_at_cycle(
                    _fem_cycle_g, _g_oracle_cfg['pidl_centroids'],
                    residual_stiffness=float(_g_oracle_cfg.get(
                        'fem_residual_stiffness',
                        getattr(pffmodel, 'residual_stiffness', 0.0),
                    )),
                    device=inp.device, dtype=torch.float32,
                ).detach()
                _mask_g = _g_oracle_cfg.get('override_mask', None)
                if _mask_g is not None:
                    _mask_g = _mask_g.to(inp.device).bool()
                    _base_g = (
                        _g_stiffness_override_current
                        if _g_stiffness_override_current is not None
                        else torch.ones_like(_target_g)
                    )
                    _g_stiffness_override_current = torch.where(
                        _mask_g, _target_g, _base_g
                    ).detach()
                else:
                    _mask_g = torch.ones_like(_target_g, dtype=torch.bool)
                    _g_stiffness_override_current = _target_g
                _oracle_target_elem = _target_g
                _oracle_mask_elem = _mask_g
                print(
                    f"  [GStiffnessOracle] pidl j={j} substep={_substep_g}, "
                    f"FEM c={_fem_cycle_g}: g override "
                    f"min/max={_target_g.min().item():.3e}/"
                    f"{_target_g.max().item():.3e}"
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
                supervised_dict=_supervised_dict,       # ★ MIT-8
                symmetry_dict=_symmetry_dict,           # ★ B path soft sym
                side_traction_dict=_side_traction_dict, # ★ side-traction penalty
                grad_annealing_state=grad_annealing_state,  # ★ Algo1 (applies pre-computed λ; no update in LBFGS)
                element_mask=_void_energy_mask,         # ★ void-like notch diagnostic
                j_path_dict=j_path_dict,                # ★ J path-independence reg
                hist_loss_weight=_lambda_hist_weight,
                g_stiffness_override=_g_stiffness_override_current,
                irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
            )
            loss_data = loss_data + loss_data1

        if _staged_alpha:
            _symmetry_dict = fatigue_dict.get('symmetry_soft', None)
            _side_traction_dict = fatigue_dict.get('side_traction_soft', None)
            _d1_active_cycle = (
                _d1_dataset is not None and j >= _d1_start_cycle
            )
            _stage_min_delta = float(_staged_cfg.get(
                'optim_rel_tol', optimizer_dict["optim_rel_tol"]
            ))

            def _run_staged_head(_label, _rows, _epochs):
                if int(_epochs) <= 0:
                    return []
                with _head_only_phase(field_comp, _rows, _label) as _params:
                    _optim = get_optimizer(_params, "RPROP")
                    return fit_with_early_stopping(
                        field_comp, training_set, T_conn, area_T, hist_alpha,
                        matprop, pffmodel,
                        optimizer_dict["weight_decay"], num_epochs=int(_epochs),
                        optimizer=_optim, min_delta=_stage_min_delta,
                        intermediateModel_path=None, writer=writer,
                        training_dict=training_dict,
                        f_fatigue=f_fatigue,
                        crack_tip_weights=crack_tip_weights,
                        supervised_dict=_supervised_dict,
                        symmetry_dict=_symmetry_dict,
                        side_traction_dict=_side_traction_dict,
                        grad_annealing_state=grad_annealing_state,
                        delta1_dataset=_d1_dataset if _d1_active_cycle else None,
                        element_mask=_void_energy_mask,
                        j_path_dict=j_path_dict,
                        hist_loss_weight=_lambda_hist_weight,
                        g_stiffness_override=_g_stiffness_override_current,
                        irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
                    )

            loss_data = loss_data + _run_staged_head(
                "uv-head stage", (0, 1), _staged_cfg.get('uv_head_epochs', 0)
            )
            loss_data = loss_data + _run_staged_head(
                "alpha-head stage", (2,), _staged_cfg.get('alpha_head_epochs', 0)
            )

        if _local_patch_training:
            _patch_epochs = int(_patch_train_cfg.get('warm_epochs', 0))
            if _patch_epochs > 0:
                _symmetry_dict = fatigue_dict.get('symmetry_soft', None)
                _side_traction_dict = fatigue_dict.get('side_traction_soft', None)
                _d1_active_cycle = (
                    _d1_dataset is not None and j >= _d1_start_cycle
                )
                _patch_min_delta = float(_patch_train_cfg.get(
                    'optim_rel_tol', optimizer_dict["optim_rel_tol"]
                ))
                with _local_patch_only_phase(field_comp) as _patch_params:
                    _patch_optim = get_optimizer(_patch_params, "RPROP")
                    loss_data_patch = fit_with_early_stopping(
                        field_comp, training_set, T_conn, area_T, hist_alpha,
                        matprop, pffmodel,
                        optimizer_dict["weight_decay"], num_epochs=_patch_epochs,
                        optimizer=_patch_optim, min_delta=_patch_min_delta,
                        intermediateModel_path=None, writer=writer,
                        training_dict=training_dict,
                        f_fatigue=f_fatigue,
                        crack_tip_weights=crack_tip_weights,
                        supervised_dict=_supervised_dict,
                        symmetry_dict=_symmetry_dict,
                        side_traction_dict=_side_traction_dict,
                        grad_annealing_state=grad_annealing_state,
                        delta1_dataset=_d1_dataset if _d1_active_cycle else None,
                        element_mask=_void_energy_mask,
                        j_path_dict=j_path_dict,
                        hist_loss_weight=_lambda_hist_weight,
                        g_stiffness_override=_g_stiffness_override_current,
                        irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
                    )
                loss_data = loss_data + loss_data_patch

        if optimizer_dict["n_epochs_RPROP"] > 0:
            n_epochs  = optimizer_dict["n_epochs_RPROP"]
            NNparams  = field_comp.parameters()
            optimizer = get_optimizer(NNparams, "RPROP")
            _symmetry_dict = fatigue_dict.get('symmetry_soft', None)
            _side_traction_dict = fatigue_dict.get('side_traction_soft', None)
            # ★ δ-1: pass ElementDataset when IS is active for this cycle
            _d1_active_cycle = (
                _d1_dataset is not None and j >= _d1_start_cycle
            )
            loss_data2 = fit_with_early_stopping(
                field_comp, training_set, T_conn, area_T, hist_alpha, matprop, pffmodel,
                optimizer_dict["weight_decay"], num_epochs=n_epochs, optimizer=optimizer,
                min_delta=optimizer_dict["optim_rel_tol"],
                intermediateModel_path=intermediateModel_path,
                writer=writer, training_dict=training_dict,
                f_fatigue=f_fatigue,                    # ★ 传入疲劳退化函数
                crack_tip_weights=crack_tip_weights,    # ★ 2026-05-13 P0 fix: thread C6/Dir3 reweight into RPROP
                supervised_dict=_supervised_dict,       # ★ MIT-8
                symmetry_dict=_symmetry_dict,           # ★ B path soft sym
                side_traction_dict=_side_traction_dict, # ★ side-traction penalty
                grad_annealing_state=grad_annealing_state,  # ★ Algo1 (updates λ every update_every epochs)
                delta1_dataset=_d1_dataset if _d1_active_cycle else None,  # ★ δ-1
                element_mask=_void_energy_mask,         # ★ void-like notch diagnostic
                j_path_dict=j_path_dict,                # ★ J path-independence reg
                hist_loss_weight=_lambda_hist_weight,
                g_stiffness_override=_g_stiffness_override_current,
                irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
            )
            loss_data = loss_data + loss_data2

        end = time.time()
        _cycle_seconds = end - start
        print(f"Execution time: {_cycle_seconds/60:.03f}minutes")
        _time_history.append([j, _cycle_seconds])

        _grad_diag_due = False
        if _grad_diag_enabled:
            _grad_diag_due = (
                j in _grad_diag_cycles
                or (_grad_diag_every is not None
                    and int(_grad_diag_every) > 0
                    and j % int(_grad_diag_every) == 0)
                or (_grad_diag_dense and _dense_sampling)
                or (_grad_diag_on_fracture and _frac_detected)
            )
        if _grad_diag_due:
            _grad_stats = _energy_gradient_diagnostics(
                field_comp, inp, hist_alpha, matprop, pffmodel,
                area_T, T_conn, f_fatigue, element_mask=_void_energy_mask,
                g_stiffness_override=_g_stiffness_override_current,
                irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
            )
            _grad_diag_history.append([
                int(j),
                float(_grad_stats["E_el"]),
                float(_grad_stats["E_d"]),
                float(_grad_stats["E_hist"]),
                float(_grad_stats["grad_E_el"]),
                float(_grad_stats["grad_E_d"]),
                float(_grad_stats["grad_E_hist"]),
            ])
            print(
                f"  [GradientDiagnostics step {j} pre-history-refresh] "
                f"E=({_grad_stats['E_el']:.6e}, {_grad_stats['E_d']:.6e}, "
                f"{_grad_stats['E_hist']:.6e}) | "
                f"grad=({_grad_stats['grad_E_el']:.6e}, "
                f"{_grad_stats['grad_E_d']:.6e}, "
                f"{_grad_stats['grad_E_hist']:.6e})"
            )

        # ------------------------------------------------------------------
        # Manav 原始：更新相场不可逆性历史变量 hist_alpha
        # ------------------------------------------------------------------
        hist_alpha_prev_for_driver = hist_alpha.clone() if fatigue_on else None
        if (
            fatigue_on
            and _lambda_hist_enabled
            and j >= (_lambda_hist_start_cycle - 1)
        ):
            _lambda_hist_weight, _lambda_stats = _adaptive_lambda_hist_update(
                field_comp, inp, hist_alpha, matprop, pffmodel, area_T, T_conn,
                f_fatigue, _lambda_hist_weight, _lambda_hist_cfg,
                element_mask=_void_energy_mask,
                g_stiffness_override=_g_stiffness_override_current,
                irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
            )
            _lambda_hist_history.append([
                int(j),
                float(_lambda_hist_weight),
                float(_lambda_stats["lambda_hat"]),
                float(_lambda_stats["grad_E_el"]),
                float(_lambda_stats["grad_E_d"]),
                float(_lambda_stats["grad_E_hist"]),
            ])
            print(
                f"  [AdaptiveLambdaHist cycle {j}] "
                f"lambda_hist={_lambda_hist_weight:.6e} "
                f"lambda_hat={_lambda_stats['lambda_hat']:.6e} | "
                f"grad_E_el={_lambda_stats['grad_E_el']:.6e} "
                f"grad_E_d={_lambda_stats['grad_E_d']:.6e} "
                f"grad_E_hist={_lambda_stats['grad_E_hist']:.6e}"
            )
        hist_alpha_new = field_comp.update_hist_alpha(inp)
        hist_alpha = torch.maximum(hist_alpha, hist_alpha_new).detach()
        _hist_alpha_oracle_cfg = (
            fatigue_dict.get('hist_alpha_oracle', None)
            if fatigue_on else None
        )
        if (_hist_alpha_oracle_cfg is not None
                and _hist_alpha_oracle_cfg.get('enable', False)):
            _fem_cycle_ha, _, _substep_ha, _is_peak_ha = _oracle_cycle_scale(
                int(j), _hist_alpha_oracle_cfg
            )
            _max_cycle_ha = int(_hist_alpha_oracle_cfg.get('max_cycle', 0))
            _cycle_in_range_ha = (
                _max_cycle_ha <= 0 or _fem_cycle_ha <= _max_cycle_ha
            )
            if _is_peak_ha and _cycle_in_range_ha:
                _target_alpha_elem = _hist_alpha_oracle_cfg[
                    'fem_sup'
                ].alpha_target_at_cycle(
                    _fem_cycle_ha, _hist_alpha_oracle_cfg['pidl_centroids'],
                    device=inp.device, dtype=torch.float32,
                ).detach()
                _mask_ha = _hist_alpha_oracle_cfg.get('override_mask', None)
                if _mask_ha is not None:
                    _mask_ha = _mask_ha.to(inp.device).bool()
                    _target_for_nodes = torch.where(
                        _mask_ha, _target_alpha_elem, torch.zeros_like(_target_alpha_elem)
                    )
                else:
                    _mask_ha = torch.ones_like(_target_alpha_elem, dtype=torch.bool)
                    _target_for_nodes = _target_alpha_elem
                _node_target = _element_to_node_projection(
                    _target_for_nodes, T_conn, int(inp.shape[0]),
                    reduce=_hist_alpha_oracle_cfg.get('node_reduce', 'max'),
                )
                hist_alpha = torch.maximum(hist_alpha, _node_target).detach()
                _oracle_target_elem = _target_alpha_elem
                _oracle_mask_elem = _mask_ha
                print(
                    f"  [HistAlphaOracle] pidl j={j} substep={_substep_ha}, "
                    f"FEM c={_fem_cycle_ha}: projected hist_alpha floor "
                    f"target max={_target_alpha_elem.max().item():.3e}"
                )

        # ★ δ-1: update element sampling probabilities p_e from residual proxy
        if _d1_dataset is not None and j >= (_d1_start_cycle - 1):
            _d1_proxy = compute_residual_proxy(
                inp, field_comp, hist_alpha, matprop, pffmodel,
                area_T, T_conn, _resolve_f_fatigue(f_fatigue), device)
            _d1_dataset.update_weights(_d1_proxy)
            _d1_Keff = _d1_dataset.samples_per_epoch or _d1_dataset.n_elem
            print(f"  [δ-1] p_e updated: proxy max={_d1_proxy.max():.3e}, "
                  f"K={_d1_Keff}, eff. top-10%={(_d1_proxy > _d1_proxy.quantile(0.9)).sum().item()} elems")

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
                _target_kind = _fem_oracle_cfg.get('target_kind', 'raw')
                _device = inp.device
                _fem_cycle, _target_scale, _, _ = _oracle_cycle_scale(
                    int(j), _fem_oracle_cfg
                )
                if _target_kind == 'raw':
                    _psi_target = _fem_sup.psi_target_at_cycle(
                        _fem_cycle, _pidl_centroids,
                        device=_device, dtype=torch.float32)
                elif _target_kind == 'active':
                    _psi_target = _fem_sup.active_target_at_cycle(
                        _fem_cycle, _pidl_centroids,
                        residual_stiffness=float(_fem_oracle_cfg.get(
                            'fem_residual_stiffness',
                            getattr(pffmodel, 'residual_stiffness', 0.0),
                        )),
                        device=_device, dtype=torch.float32)
                else:
                    raise ValueError(
                        "fatigue_dict['fem_oracle']['target_kind'] must be "
                        f"'raw' or 'active', got {_target_kind!r}"
                    )
                _psi_target = (_psi_target * float(_target_scale)).detach()
                _fem_oracle = {
                    'enable': True, 'psi_target': _psi_target,
                    'override_mask': _override_mask, 'apply_g': _apply_g,
                }
                for _key in ('moving_zone', 'moving_zone_alpha_thr', 'zone_radius'):
                    if _key in _fem_oracle_cfg:
                        _fem_oracle[_key] = _fem_oracle_cfg[_key]
            _g_history_override_current = _g_stiffness_override_current
            if (
                _lagged_stiffness_enabled
                and _lagged_stiffness_history_policy == 'solver_only'
            ):
                _g_history_override_current = None
            if T_conn is not None:
                with torch.no_grad():
                    u_eval, v_eval, alpha_eval = field_comp.fieldCalculation(inp)
                psi_plus_elem = get_psi_plus_per_elem(
                    inp, u_eval, v_eval, alpha_eval,
                    matprop, pffmodel, area_T, T_conn,
                    psi_hack_dict=_psi_hack,
                    fem_oracle_dict=_fem_oracle,
                    history_driver_reduction_dict=_history_driver_reduction,
                    g_stiffness_override=_g_history_override_current,
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
                    history_driver_reduction_dict=_history_driver_reduction,
                    g_stiffness_override=_g_history_override_current,
                )

            if (_void_notch_mask is not None
                    and _void_cfg.get('mask_fatigue', True)):
                psi_plus_elem = psi_plus_elem.clone()
                psi_plus_prev = psi_plus_prev.clone()
                psi_plus_elem[_void_notch_mask] = 0.0
                psi_plus_prev[_void_notch_mask] = 0.0

            psi_history_elem = psi_plus_elem
            if _history_driver_mode != 'current_active':
                if T_conn is not None:
                    alpha_current_elem = (
                        alpha_eval[T_conn[:, 0]]
                        + alpha_eval[T_conn[:, 1]]
                        + alpha_eval[T_conn[:, 2]]
                    ) / 3.0
                else:
                    alpha_current_elem = alpha_eval.flatten()
                g_current, _ = pffmodel.Edegrade(alpha_current_elem)
                psi_raw_elem = (psi_plus_elem / g_current.clamp(min=1e-30)).detach()
                if _history_driver_mode == 'raw':
                    psi_history_elem = psi_raw_elem
                elif _history_driver_mode == 'lagged_g':
                    if T_conn is not None:
                        alpha_lag_elem = (
                            hist_alpha_prev_for_driver[T_conn[:, 0]]
                            + hist_alpha_prev_for_driver[T_conn[:, 1]]
                            + hist_alpha_prev_for_driver[T_conn[:, 2]]
                        ) / 3.0
                    else:
                        alpha_lag_elem = hist_alpha_prev_for_driver.flatten()
                    g_lag, _ = pffmodel.Edegrade(alpha_lag_elem)
                    psi_history_elem = (g_lag * psi_raw_elem).detach()

            history_increment_elem = torch.relu(psi_history_elem - psi_plus_prev).detach()
            _hist_inc_oracle_cfg = fatigue_dict.get('history_increment_oracle', None)
            if (_hist_inc_oracle_cfg is not None
                    and _hist_inc_oracle_cfg.get('enable', False)):
                _fem_sup_inc = _hist_inc_oracle_cfg['fem_sup']
                _pidl_centroids_inc = _hist_inc_oracle_cfg['pidl_centroids']
                _fem_cycle_inc, _target_scale_inc, _substep_inc, _is_peak_inc = _oracle_cycle_scale(
                    int(j), _hist_inc_oracle_cfg
                )
                _mode_inc = _hist_inc_oracle_cfg.get('mode', 'cycle_delta_at_peak')
                if _mode_inc not in {'cycle_delta_at_peak', 'active_delta_substep'}:
                    raise ValueError(
                        "history_increment_oracle mode must be "
                        "'cycle_delta_at_peak' or 'active_delta_substep', "
                        f"got {_mode_inc!r}"
                    )
                if _mode_inc == 'active_delta_substep':
                    _active_base = _fem_sup_inc.active_target_at_cycle(
                        _fem_cycle_inc, _pidl_centroids_inc,
                        residual_stiffness=float(_hist_inc_oracle_cfg.get(
                            'fem_residual_stiffness',
                            getattr(pffmodel, 'residual_stiffness', 0.0),
                        )),
                        device=inp.device, dtype=torch.float32,
                    ).detach()
                    _factors_inc = _hist_inc_oracle_cfg.get('explicit_cycle_factors')
                    _power_inc = float(_hist_inc_oracle_cfg.get('load_factor_power', 2.0))
                    _base_scale_inc = float(_hist_inc_oracle_cfg.get('target_scale', 1.0))
                    if _factors_inc is None:
                        _prev_scale_inc = 0.0
                    elif _substep_inc <= 0:
                        _prev_scale_inc = 0.0
                    else:
                        _prev_scale_inc = _base_scale_inc * (
                            float(_factors_inc[_substep_inc - 1]) ** _power_inc
                        )
                    _current_active = (_active_base * float(_target_scale_inc)).detach()
                    _previous_active = (_active_base * float(_prev_scale_inc)).detach()
                    history_increment_elem = torch.relu(
                        _current_active - _previous_active
                    ).detach()
                    _mask_inc = _hist_inc_oracle_cfg.get('override_mask', None)
                    if _mask_inc is not None:
                        _mask_inc = _mask_inc.to(inp.device).bool()
                        history_increment_elem = torch.where(
                            _mask_inc,
                            history_increment_elem,
                            torch.zeros_like(history_increment_elem),
                        )
                    else:
                        _mask_inc = torch.ones_like(history_increment_elem, dtype=torch.bool)
                    psi_history_elem = _current_active
                    _oracle_target_elem = _current_active
                    _oracle_mask_elem = _mask_inc
                elif _is_peak_inc:
                    history_increment_elem = _fem_sup_inc.alpha_bar_delta_target_at_cycle(
                        _fem_cycle_inc, _pidl_centroids_inc,
                        initial_zero=bool(_hist_inc_oracle_cfg.get('initial_zero', True)),
                        device=inp.device, dtype=torch.float32,
                    )
                    history_increment_elem = (
                        history_increment_elem
                        * float(_hist_inc_oracle_cfg.get('delta_scale', 1.0))
                    ).detach()
                    _mask_inc = _hist_inc_oracle_cfg.get('override_mask', None)
                    if _mask_inc is not None:
                        _mask_inc = _mask_inc.to(inp.device).bool()
                        history_increment_elem = torch.where(
                            _mask_inc,
                            history_increment_elem,
                            torch.zeros_like(history_increment_elem),
                        )
                    else:
                        _mask_inc = torch.ones_like(history_increment_elem, dtype=torch.bool)
                    psi_history_elem = (psi_plus_prev + history_increment_elem).detach()
                    _oracle_target_elem = history_increment_elem
                    _oracle_mask_elem = _mask_inc
                else:
                    history_increment_elem = torch.zeros_like(hist_fat)

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
            if (_hist_inc_oracle_cfg is not None
                    and _hist_inc_oracle_cfg.get('enable', False)):
                hist_fat = (hist_fat + history_increment_elem).detach()
            else:
                hist_fat = update_fatigue_history(
                    hist_fat, psi_history_elem, psi_plus_prev, fatigue_dict
                )
            if (_void_notch_mask is not None
                    and _void_cfg.get('mask_fatigue', True)):
                hist_fat = hist_fat.clone()
                hist_fat[_void_notch_mask] = 0.0

            _alpha_bar_state_cfg = fatigue_dict.get('alpha_bar_state_oracle', None)
            if (_alpha_bar_state_cfg is not None
                    and _alpha_bar_state_cfg.get('enable', False)):
                _fem_cycle_ab, _, _substep_ab, _is_peak_ab = _oracle_cycle_scale(
                    int(j), _alpha_bar_state_cfg
                )
                _max_cycle_ab = int(_alpha_bar_state_cfg.get('max_cycle', 0))
                _cycle_in_range_ab = (
                    _max_cycle_ab <= 0 or _fem_cycle_ab <= _max_cycle_ab
                )
                if _is_peak_ab and _cycle_in_range_ab:
                    _hist_before_ab = hist_fat
                    _target_ab = _alpha_bar_state_cfg[
                        'fem_sup'
                    ].alpha_bar_target_at_cycle(
                        _fem_cycle_ab, _alpha_bar_state_cfg['pidl_centroids'],
                        device=inp.device, dtype=torch.float32,
                    ).detach()
                    _mask_ab = _alpha_bar_state_cfg.get('override_mask', None)
                    if _mask_ab is not None:
                        _mask_ab = _mask_ab.to(inp.device).bool()
                        hist_fat = torch.where(_mask_ab, _target_ab, hist_fat).detach()
                    else:
                        _mask_ab = torch.ones_like(_target_ab, dtype=torch.bool)
                        hist_fat = _target_ab
                    history_increment_elem = torch.relu(hist_fat - _hist_before_ab).detach()
                    _oracle_target_elem = _target_ab
                    _oracle_mask_elem = _mask_ab
                    print(
                        f"  [AlphaBarStateOracle] pidl j={j} substep={_substep_ab}, "
                        f"FEM c={_fem_cycle_ab}: alpha_bar state max="
                        f"{_target_ab.max().item():.3e}"
                    )

            # ★ 2026-05-08 A1: post-hoc mirror α — break Carrara ratchet
            # Symmetrize ᾱ about y=0 BEFORE f(ᾱ) is computed for next cycle.
            # Resets the asymmetric memory build-up; SENT geometry is symmetric
            # under symmetric BCs so this is physically defensible.
            if _mirror_idx is not None:
                hist_fat = mirror_alpha_y(hist_fat, _mirror_idx)

            # 更新疲劳退化函数 f(ᾱ)（Carrara Eq.41 或 Eq.42）
            # ★ Direction 6.1: 传入 elem_centroids 支持空间调制 α_T
            _f_fatigue_oracle_cfg = fatigue_dict.get('f_fatigue_oracle', None)
            if (_f_fatigue_oracle_cfg is not None
                    and _f_fatigue_oracle_cfg.get('enable', False)):
                _fem_cycle_ff, _, _substep_ff, _is_peak_ff = _oracle_cycle_scale(
                    int(j), _f_fatigue_oracle_cfg
                )
                _max_cycle_ff = int(_f_fatigue_oracle_cfg.get('max_cycle', 0))
                _cycle_in_range_ff = (
                    _max_cycle_ff <= 0 or _fem_cycle_ff <= _max_cycle_ff
                )
                if _is_peak_ff and _cycle_in_range_ff:
                    _target_ff = _f_fatigue_oracle_cfg[
                        'fem_sup'
                    ].f_fatigue_target_at_cycle(
                        _fem_cycle_ff, _f_fatigue_oracle_cfg['pidl_centroids'],
                        device=inp.device, dtype=torch.float32,
                    ).detach()
                    _mask_ff = _f_fatigue_oracle_cfg.get('override_mask', None)
                    if _mask_ff is not None:
                        _mask_ff = _mask_ff.to(inp.device).bool()
                        _base_ff = (
                            _f_fatigue_override_current
                            if _f_fatigue_override_current is not None
                            else _fatigue_for_fit(hist_fat)
                        )
                        _f_fatigue_override_current = torch.where(
                            _mask_ff, _target_ff, _base_ff
                        ).detach()
                    else:
                        _mask_ff = torch.ones_like(_target_ff, dtype=torch.bool)
                        _f_fatigue_override_current = _target_ff
                    _oracle_target_elem = _target_ff
                    _oracle_mask_elem = _mask_ff
                    print(
                        f"  [FFatigueOracle] pidl j={j} substep={_substep_ff}, "
                        f"FEM c={_fem_cycle_ff}: f min/max="
                        f"{_target_ff.min().item():.3e}/"
                        f"{_target_ff.max().item():.3e}"
                    )
                f_fatigue = (
                    _f_fatigue_override_current
                    if _f_fatigue_override_current is not None
                    else _fatigue_for_fit(hist_fat)
                )
            else:
                f_fatigue = _fatigue_for_fit(hist_fat)

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
            # Controlled alignment Variant 4:
            # explicit-cycle runners provide real load substeps inside each cycle,
            # so the previous ψ⁺ should advance from substep to substep instead of
            # being reset after every training step. Default behavior is unchanged.
            if fatigue_dict.get('explicit_cycle_substeps', None):
                psi_plus_prev = psi_history_elem.clone()
            else:
                psi_plus_prev = (R ** 2) * psi_history_elem.clone()

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
                        f_fatigue=_resolve_f_fatigue(f_fatigue),
                        beta=_as_beta, power=_as_power,
                        residual_source=_as_source,
                    )
                else:
                    crack_tip_weights = None   # warmup cycles unweighted

            # ★ Direction 5: 记录 c_singular 当前值（每圈训练完毕后）
            if _ansatz_enabled and field_comp.c_singular is not None:
                _c_val = float(field_comp.c_singular.detach().cpu().item())
                _c_singular_history.append([j, _c_val])
            else:
                _c_val = None

            # 日志输出
            _f_current = _resolve_f_fatigue(f_fatigue)
            f_min = _f_current.min().item()
            f_mean = _f_current.mean().item()
            alpha_bar_max = hist_fat.max().item()
            if (j % _log_every == 0) or _frac_detected or _dense_sampling:
                _Kt_str = f"{_Kt:.2f}" if not np.isnan(_Kt) else "N/A"
                _c_str  = f" | c={_c_val:+.4e}" if _c_val is not None else ""
                print(f"  [Fatigue step {j}] ᾱ_max={alpha_bar_max:.4e} | "
                      f"f_min={f_min:.4f} | f_mean={f_mean:.4f} | Kt={_Kt_str}{_c_str}")
            alpha_bar_history.append([alpha_bar_max,
                                       hist_fat.mean().item(),
                                       float(f_min)])
            if _inverse_alpha_T is not None:
                _inverse_alpha_T_history.append([j, scalar_value(_inverse_alpha_T)])

            # ── E_el 计算（用于断裂检测和后处理曲线）─────────────────────
            with torch.no_grad():
                u_el, v_el, alpha_el = field_comp.fieldCalculation(inp)
                E_el_val, _, _ = compute_energy(
                    inp, u_el, v_el, alpha_el, hist_alpha,
                    matprop, pffmodel, area_T, T_conn, _f_current,
                    element_mask=_void_energy_mask,
                    g_stiffness_override=_g_stiffness_override_current,
                    irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
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

            _elem_diag_due = False
            if _elem_diag_enabled:
                _elem_diag_due = (
                    j in _elem_diag_cycles
                    or (_elem_diag_every is not None
                        and int(_elem_diag_every) > 0
                        and j % int(_elem_diag_every) == 0)
                    or (_elem_diag_dense and _dense_sampling)
                    or (_elem_diag_on_fracture and _frac_detected)
                )
            if _elem_diag_due:
                _save_element_diagnostics(
                    inp, T_conn, u_el, v_el, alpha_el, hist_alpha, hist_fat,
                    _f_current, psi_plus_elem, psi_plus_prev,
                    matprop, pffmodel, area_T, j, _elem_diag_dir,
                    psi_history_elem=psi_history_elem,
                    history_increment_elem=history_increment_elem,
                    alpha_feedback_target_elem=_alpha_feedback_target_elem,
                    alpha_feedback_mask_elem=_alpha_feedback_mask_elem,
                    oracle_target_elem=_oracle_target_elem,
                    oracle_mask_elem=_oracle_mask_elem,
                    g_stiffness_override_elem=_g_stiffness_override_current,
                    irreversibility_penalty_cfg=_irreversibility_penalty_cfg,
                )

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
            _ckpt_data['history_driver_mode']      = _history_driver_mode
            _ckpt_data['lagged_stiffness_enabled'] = _lagged_stiffness_enabled
            _ckpt_data['lagged_stiffness_history_policy'] = (
                _lagged_stiffness_history_policy
            )
            _ckpt_data['psi_history_elem']         = psi_history_elem
            _ckpt_data['_frac_detected']           = _frac_detected
            _ckpt_data['_frac_cycle']              = _frac_cycle
            _ckpt_data['_frac_confirm_remaining']  = _frac_confirm_remaining
            if _lambda_hist_enabled:
                _ckpt_data['lambda_hist_weight'] = float(_lambda_hist_weight)
            if _inverse_alpha_T is not None:
                _ckpt_data['inverse_alpha_T'] = scalar_value(_inverse_alpha_T)
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
            if _lambda_hist_history:
                np.save(str(trainedModel_path / 'lambda_hist_vs_cycle.npy'),
                        np.array(_lambda_hist_history))
            if _grad_diag_history:
                np.save(str(trainedModel_path / 'energy_gradient_terms_vs_cycle.npy'),
                        np.array(_grad_diag_history))
            if _inverse_alpha_T_history:
                np.save(str(trainedModel_path / 'inverse_alpha_T_vs_cycle.npy'),
                        np.array(_inverse_alpha_T_history))

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
            if _lambda_hist_history:
                np.save(str(trainedModel_path / 'lambda_hist_vs_cycle.npy'),
                        np.array(_lambda_hist_history))
            if _grad_diag_history:
                np.save(str(trainedModel_path / 'energy_gradient_terms_vs_cycle.npy'),
                        np.array(_grad_diag_history))
            if _inverse_alpha_T_history:
                np.save(str(trainedModel_path / 'inverse_alpha_T_vs_cycle.npy'),
                        np.array(_inverse_alpha_T_history))
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
    if fatigue_on and _lambda_hist_history:
        np.save(str(trainedModel_path / 'lambda_hist_vs_cycle.npy'),
                np.array(_lambda_hist_history))
    if fatigue_on and _grad_diag_history:
        np.save(str(trainedModel_path / 'energy_gradient_terms_vs_cycle.npy'),
                np.array(_grad_diag_history))
    if fatigue_on and _inverse_alpha_T_history:
        np.save(str(trainedModel_path / 'inverse_alpha_T_vs_cycle.npy'),
                np.array(_inverse_alpha_T_history))
