"""
=============================================================================
fatigue_history.py  ★ 新增文件（Manav 原始代码中不存在）
=============================================================================
实现 Carrara 2020 疲劳相场框架的两个核心函数：

  1. update_fatigue_history()  —— 更新疲劳历史变量 ᾱ
  2. compute_fatigue_degrad()  —— 计算疲劳退化函数 f(ᾱ)

两者均可通过 fatigue_dict 中的参数灵活切换策略：

  累积策略（accum_type）:
    'carrara'  → Carrara Eq.39:  Δᾱ = H(Δψ⁺)·Δψ⁺           （线性，加载时累积）
    'golahmar' → Golahmar Eq.31: Δᾱ = H(Δψ⁺)·(ψ⁺/αₙ)^(n-1)·Δψ⁺ （幂律）

  退化函数（degrad_type）:
    'asymptotic'  → Carrara Eq.41: f = [2α_T/(ᾱ+α_T)]²       （渐近，永不到0）
    'logarithmic' → Carrara Eq.42: f = [1-κ·log10(ᾱ/α_T)]²   （有限步归零）

当 fatigue_dict['fatigue_on'] = False 时，model_train.py 会跳过调用，
compute_energy.py 中 f_fatigue 默认为 1.0，完全恢复 Manav 原始行为。
=============================================================================
"""

import torch


def update_fatigue_history(hist_fat, psi_plus_elem, psi_plus_prev, fatigue_dict):
    """
    更新疲劳历史变量 ᾱ（逐元素）

    核心思想：ᾱ 只在拉伸应变能 ψ⁺ 增加时（加载阶段）累积，
    卸载时 H(Δψ⁺) = 0，故 ᾱ 保持不变。

    参数：
    ------
    hist_fat : torch.Tensor, shape (n_elem,)
        当前各元素的疲劳历史变量 ᾱ
    psi_plus_elem : torch.Tensor, shape (n_elem,)
        当前步各元素的退化拉伸应变能密度 g(α)·ψ⁺
    psi_plus_prev : torch.Tensor, shape (n_elem,)
        上一加载步各元素的 g(α)·ψ⁺
    fatigue_dict : dict
        疲劳参数（需含 'accum_type'；Golahmar 还需 'n_power', 'alpha_n'）

    返回：
    ------
    torch.Tensor, shape (n_elem,)  —— 更新后的 ᾱ（detached，不参与反向传播）
    """
    # ★ Seleš/Golahmar 修复：单调加载不累积疲劳历史变量
    # 疲劳由定义是循环现象；单调加载下 f ≡ 1，退化回标准相场
    # 效果：mono + fatigue_on == mono + fatigue_off（Case C 验证目标）
    loading_type = fatigue_dict.get('loading_type', 'cyclic')
    if loading_type == 'monotonic':
        return hist_fat   # ᾱ 不变，f 将保持 1.0

    accum_type = fatigue_dict.get('accum_type', 'carrara')

    # H(Δψ⁺)·Δψ⁺ ≥ 0  ——  relu 实现：只保留正增量（加载阶段）
    delta_psi = torch.relu(psi_plus_elem - psi_plus_prev)

    if accum_type == 'carrara':
        # ── Carrara Eq.39：线性累积 ──────────────────────────────────────────
        delta_alpha = delta_psi

    elif accum_type == 'golahmar':
        # ── Golahmar Eq.31：幂律累积 ─────────────────────────────────────────
        # Δᾱ = H(Δψ⁺) · (ψ⁺/αₙ)^(n-1) · Δψ⁺
        n       = fatigue_dict.get('n_power', 1.0)
        alpha_n = fatigue_dict.get('alpha_n', 1.0)   # 归一化能量密度（量纲与 ψ⁺ 相同）
        power_factor = (psi_plus_elem.clamp(min=1e-12) / alpha_n).pow(n - 1.0)
        delta_alpha  = power_factor * delta_psi

    else:
        raise ValueError(
            f"Unknown accum_type='{accum_type}'. Choose 'carrara' or 'golahmar'."
        )

    return (hist_fat + delta_alpha).detach()


def compute_fatigue_degrad(hist_fat, fatigue_dict, elem_centroids=None):
    """
    计算疲劳退化函数 f(ᾱ) ∈ [0, 1]（逐元素）

    当 ᾱ ≤ α_T 时 f = 1（无疲劳效应）；
    当 ᾱ > α_T 时 f 随 ᾱ 单调递减，模拟断裂韧性下降。

    ★ Direction 6.1: Spatial α_T modulation
    ---------------------------------------
    若 fatigue_dict['spatial_alpha_T'].enable=True 且提供 elem_centroids，
    α_T 变为空间相关：α_T_local(r) = α_T_base · (1 - β · exp(-r/r_T))
    裂尖单元 α_T 降低 → 更早进入 f<1 区域 → 应力重分布正反馈推高局部 α_max。
    当 enable=False 或 elem_centroids is None → α_T 统一为 scalar α_T_base，
    数值等价 baseline。

    参数：
    ------
    hist_fat : torch.Tensor, shape (n_elem,)
        各元素疲劳历史变量 ᾱ
    fatigue_dict : dict
        疲劳参数（需含 'degrad_type', 'alpha_T'；对数型还需 'kappa'）
        可选 'spatial_alpha_T' 子 dict：{'enable','beta','r_T','x_tip','y_tip'}
    elem_centroids : torch.Tensor, shape (n_elem, 2), optional
        各元素形心坐标 (x, y)。仅 spatial_alpha_T.enable=True 时需要。
        device/dtype 需与 hist_fat 一致。

    返回：
    ------
    torch.Tensor, shape (n_elem,)  —— f(ᾱ)（detached）
    """
    degrad_type  = fatigue_dict.get('degrad_type', 'asymptotic')
    alpha_T_base = fatigue_dict.get('alpha_T', 1.0)

    # ── Direction 6.1: 空间调制 α_T ─────────────────────────────────────────
    # 裂尖附近（r≪r_T）α_T 显著降低；远场（r≫r_T）回到 α_T_base。
    sp_cfg = fatigue_dict.get('spatial_alpha_T', {})
    if sp_cfg.get('enable', False) and elem_centroids is not None:
        beta  = sp_cfg.get('beta', 0.0)
        r_T   = sp_cfg.get('r_T', 0.1)
        x_tip = sp_cfg.get('x_tip', 0.0)
        y_tip = sp_cfg.get('y_tip', 0.0)
        dx    = elem_centroids[:, 0] - x_tip
        dy    = elem_centroids[:, 1] - y_tip
        r     = torch.sqrt(dx * dx + dy * dy + 1e-12)
        alpha_T = alpha_T_base * (1.0 - beta * torch.exp(-r / r_T))
    else:
        alpha_T = torch.full_like(hist_fat, float(alpha_T_base))

    f    = torch.ones_like(hist_fat)   # 默认 f = 1（ᾱ ≤ α_T 区域）
    mask = hist_fat > alpha_T          # 需要退化的元素

    if degrad_type == 'asymptotic':
        # ── Carrara Eq.41：渐近型，永远 > 0 ─────────────────────────────────
        # f = [2α_T / (ᾱ + α_T)]²
        f[mask] = (2.0 * alpha_T[mask] / (hist_fat[mask] + alpha_T[mask])).pow(2)

    elif degrad_type == 'logarithmic':
        # ── Carrara Eq.42：对数型，有限步归零 ────────────────────────────────
        # f = [1 - κ·log10(ᾱ/α_T)]²     for α_T < ᾱ ≤ α_T·10^(1/κ)
        # f = 0                           for ᾱ > α_T·10^(1/κ)
        kappa = fatigue_dict.get('kappa', 1.0)
        upper = alpha_T * (10.0 ** (1.0 / kappa))   # ᾱ 达到此值时 f → 0
        mask1 = mask & (hist_fat <= upper)
        mask2 = hist_fat > upper
        f[mask1] = (1.0 - kappa * torch.log10(hist_fat[mask1] / alpha_T[mask1])).pow(2)
        f[mask2] = 0.0                               # 完全疲劳退化

    else:
        raise ValueError(
            f"Unknown degrad_type='{degrad_type}'. Choose 'asymptotic' or 'logarithmic'."
        )

    return f.detach()
