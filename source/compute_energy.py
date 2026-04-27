"""
=============================================================================
compute_energy.py - 能量计算 ⭐ 最核心的文件
=============================================================================
学习顺序: 4️⃣ 这是整个方法的核心

本文件实现了相场断裂的能量计算，是Deep Ritz Method的核心。

总能量泛函（论文公式1，无量纲化后公式18）：
    E(u, α) = E_elastic + E_damage + E_irreversibility

其中：
    E_elastic = ∫_Ω [g(α)Ψ⁺(ε) + Ψ⁻(ε)] dΩ
    E_damage  = f(ᾱ) · (1/c_w) ∫_Ω [w(α) + l²|∇α|²] dΩ   ← ★ 疲劳修改
    E_irr     = (1/2) γ_ir ∫_Ω ⟨α - α_{n-1}⟩²₋ dΩ

★ 疲劳修改（Carrara 2020, Eq.20）：
    E_damage 乘以疲劳退化函数 f(ᾱ) ∈ [0,1]
    f = 1.0 时完全恢复 Manav 原始行为（fatigue_on=False 时自动如此）

关键创新：使用FEM形状函数数值计算梯度，而非自动微分
这避免了自动微分导致的Gibbs现象和错误的裂纹路径

参考论文第3.2.3节: "Gradient computation and quadrature"
=============================================================================

★ 相比 Manav 原始版本的修改：
   1. compute_energy()        → 新增 f_fatigue=1.0 参数，传入 compute_energy_per_elem
   2. compute_energy_per_elem() → 新增 f_fatigue=1.0，E_d 乘以 f_fatigue
   3. get_psi_plus_per_elem()  → ★ 全新函数，供 model_train.py 计算疲劳累积量 ψ⁺
"""

import torch
import torch.nn as nn

# Computes the total strain energy, damage energy and irreversibility penalty
def compute_energy(inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_elem, T_conn=None,
                   f_fatigue=1.0, crack_tip_weights=None):
    """
    计算总能量

    这是Deep Ritz Method的损失函数的核心：
        Loss = log(E_el + E_d + E_hist)

    ★ 新增参数 f_fatigue：
        - 标量 1.0（默认）：完全恢复 Manav 原始行为
        - Tensor (n_elem,)：逐元素退化，由 fatigue_history.compute_fatigue_degrad() 提供

    ★ 新增参数 crack_tip_weights（方向3：裂尖自适应损失加权）：
        - None（默认）：均匀权重，与原始完全一致
        - Tensor (n_elem,)：逐元素权重 w_e ≥ 1，裂尖区域 w 大
          w_e = 1 + β·(ψ⁺_e / ψ⁺_mean)^p
          效果：强制 NN 把更多"表达能力"分配给裂尖，改善 Kt 偏低问题
          不改变物理模型，只改变优化优先级

    参数：
    ------
    inp : torch.Tensor, shape (n_points, 2)
        节点/高斯点坐标 (x, y)
    u, v : torch.Tensor, shape (n_points,)
        位移分量
    alpha : torch.Tensor, shape (n_points,)
        相场变量（当前步）
    hist_alpha : torch.Tensor, shape (n_points,)
        相场历史（上一步），用于不可逆性约束
    matprop : MaterialProperties
        材料属性
    pffmodel : PFFModel
        相场模型（AT1/AT2）
    area_elem : torch.Tensor, shape (n_elements,)
        每个单元的面积
    T_conn : torch.Tensor or None
        单元连接关系，shape (n_elements, 3)
    f_fatigue : float or torch.Tensor, shape (n_elements,)   ← ★ 新增
        疲劳退化函数值。默认 1.0 = 无疲劳（完全等价原始代码）
    crack_tip_weights : torch.Tensor or None, shape (n_elements,)   ← ★ 新增
        裂尖自适应权重。None = 均匀（完全等价原始代码）

    返回：
    ------
    E_el_sum, E_d_sum, E_hist_sum : torch.Tensor  （与原始接口相同）
    """
    # 计算每个单元的能量
    E_el, E_d, E_hist_penalty = compute_energy_per_elem(
        inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_elem, T_conn,
        f_fatigue=f_fatigue   # ★ 传入退化函数
    )

    # ★ 方向3：裂尖自适应加权（crack_tip_weights=None 时完全等价原始代码）
    if crack_tip_weights is not None:
        # w_e ≥ 1，裂尖附近权重大 → 优化优先级高
        E_el_sum   = torch.sum(crack_tip_weights * E_el)
        E_d_sum    = torch.sum(crack_tip_weights * E_d)
        E_hist_sum = torch.sum(crack_tip_weights * E_hist_penalty)
    else:
        E_el_sum   = torch.sum(E_el)
        E_d_sum    = torch.sum(E_d)
        E_hist_sum = torch.sum(E_hist_penalty)

    return E_el_sum, E_d_sum, E_hist_sum


def compute_energy_per_elem(inp, u, v, alpha, hist_alpha, matprop, pffmodel, area_elem, T_conn=None,
                             f_fatigue=1.0):
    '''
    计算每个单元的能量。

    ★ 相比原始：E_d 一行乘以 f_fatigue（疲劳退化函数）。
       f_fatigue=1.0 时与原始完全一致。

    T_conn = None: 输入点是高斯点，autodiff 计算梯度
    T_conn ≠ None: 输入点是节点，FEM 形状函数计算梯度（论文推荐）
    '''

    # =========================================================================
    # 步骤1: 计算应变和相场梯度
    # =========================================================================
    strain_11, strain_22, strain_12, grad_alpha_x, grad_alpha_y = \
        gradients(inp, u, v, alpha, area_elem, T_conn)

    # =========================================================================
    # 步骤2: 计算单元中心的相场值（一点高斯积分近似）
    # =========================================================================
    if T_conn is None:
        alpha_elem = alpha
    else:
        alpha_elem = (alpha[T_conn[:, 0]] + alpha[T_conn[:, 1]] + alpha[T_conn[:, 2]]) / 3

    # =========================================================================
    # 步骤3: 获取相场模型参数
    # =========================================================================
    damageFn, _, c_w = pffmodel.damageFun(alpha_elem)   # w(α), w'(α), c_w
    weight_penalty   = pffmodel.irrPenalty()             # γ_ir

    # =========================================================================
    # 步骤4: 弹性能 E_el = ∫ [g(α)Ψ⁺ + Ψ⁻] dΩ
    # =========================================================================
    E_el_elem, _ = strain_energy_with_split(
        strain_11, strain_22, strain_12, alpha_elem, matprop, pffmodel
    )
    E_el = area_elem * E_el_elem

    # =========================================================================
    # 步骤5: 损伤能 E_d = f(ᾱ) · (w1/c_w) · ∫ [w(α)/l + l|∇α|²] dΩ
    #
    # ★ 疲劳修改：乘以 f_fatigue（Carrara 2020, Eq.20）
    #    f_fatigue = 1.0 时与 Manav 原始代码完全等价
    # =========================================================================
    E_d = f_fatigue * (
        matprop.w1 / c_w * (damageFn + matprop.l0**2 * (grad_alpha_x**2 + grad_alpha_y**2))
    ) * area_elem

    # =========================================================================
    # 步骤6: 不可逆性惩罚 E_irr = (1/2)γ_ir ∫ ⟨α - α_{n-1}⟩²₋ dΩ
    # =========================================================================
    dAlpha = alpha - hist_alpha
    if T_conn is None:
        dAlpha_elem = dAlpha
    else:
        dAlpha_elem = (dAlpha[T_conn[:, 0]] + dAlpha[T_conn[:, 1]] + dAlpha[T_conn[:, 2]]) / 3

    hist_penalty  = nn.ReLU()(-dAlpha_elem)          # ⟨-Δα⟩₊ = ⟨Δα⟩₋
    E_hist_penalty = 0.5 * matprop.w1 * weight_penalty * hist_penalty**2 * area_elem

    return E_el, E_d, E_hist_penalty


# ★ 新增函数：计算各元素退化拉伸应变能密度，供疲劳历史变量更新使用
def get_psi_plus_per_elem(inp, u, v, alpha, matprop, pffmodel, area_elem, T_conn=None,
                          psi_hack_dict=None, fem_oracle_dict=None):
    """
    ★ 新增函数（Manav 原始代码中不存在）

    计算各元素的退化拉伸应变能密度：ψ⁺_elem = g(α)·ψ⁺_0 (per element, 能量密度)

    用途：model_train.py 在每个加载步训练完成后调用，
          为 fatigue_history.update_fatigue_history() 提供 psi_plus_elem。

    参数：（与 compute_energy_per_elem 相同的前缀参数）
    ------
    inp, u, v, alpha : 同 compute_energy
    matprop, pffmodel, area_elem, T_conn : 同 compute_energy
    psi_hack_dict : dict or None (★ E2 sanity hack, Apr 23 2026)
        若非 None 且 enable=True，在裂尖邻域用 Gaussian 乘以 multiplier 放大 ψ⁺_elem，
        模拟 FEM-like 应力集中。keys: {enable, x_tip, y_tip, r_hack, multiplier}。
        默认 None 时行为与原始一致。

    返回：
    ------
    psi_plus_elem : torch.Tensor, shape (n_elements,)
        各元素退化拉伸应变能密度（已 detach，不参与反向传播）
    """
    strain_11, strain_22, strain_12, _, _ = gradients(inp, u, v, alpha, area_elem, T_conn)

    if T_conn is None:
        alpha_elem = alpha
    else:
        alpha_elem = (alpha[T_conn[:, 0]] + alpha[T_conn[:, 1]] + alpha[T_conn[:, 2]]) / 3

    _, E_el_p = strain_energy_with_split(
        strain_11, strain_22, strain_12, alpha_elem, matprop, pffmodel
    )
    # E_el_p = ψ⁺_0（未退化拉伸应变能密度）
    # Carrara Eq.39 要求累积退化能 g(α)·ψ⁺_0，避免裂尖奇异性
    g_alpha, _ = pffmodel.Edegrade(alpha_elem)
    psi_plus_elem = (g_alpha * E_el_p).detach()

    # ★ E2 sanity hack (Apr 23 2026) — 验证 ψ⁺ 集中是否是 ᾱ_max ceiling 根因
    # 在裂尖邻域用 Gaussian 衰减乘子放大 ψ⁺，模拟 FEM 的应力集中能力
    if psi_hack_dict is not None and psi_hack_dict.get('enable', False) \
            and T_conn is not None:
        x_tip = float(psi_hack_dict.get('x_tip', 0.0))
        y_tip = float(psi_hack_dict.get('y_tip', 0.0))
        r_hack = float(psi_hack_dict.get('r_hack', 0.02))
        mult = float(psi_hack_dict.get('multiplier', 1000.0))
        # element centroids
        cx = (inp[T_conn[:, 0], 0] + inp[T_conn[:, 1], 0] + inp[T_conn[:, 2], 0]) / 3.0
        cy = (inp[T_conn[:, 0], 1] + inp[T_conn[:, 1], 1] + inp[T_conn[:, 2], 1]) / 3.0
        r_elem = torch.sqrt((cx - x_tip) ** 2 + (cy - y_tip) ** 2 + 1e-12)
        # 平滑 Gaussian 放大: 中心 mult，远场 1，半峰在 r_hack
        scale = 1.0 + (mult - 1.0) * torch.exp(-(r_elem / r_hack) ** 2)
        psi_plus_elem = (psi_plus_elem * scale).detach()

    # ★ Apr 27 — Oracle-driver MIT-8b: REPLACE PIDL ψ⁺ with FEM-projected ψ⁺
    # 在 process zone B_2ℓ₀(tip) 内用 FEM-interpolated ψ⁺ 替换 PIDL 自己算的值。
    # 用途：测 single-element peak ψ⁺ amplitude 是否 sufficient cause for ᾱ_max。
    # fem_oracle_dict keys:
    #   enable: bool
    #   psi_target: torch.Tensor (n_elem,) — pre-projected FEM ψ⁺ at PIDL elements
    #              (interpolated by runner; tensor on same device as psi_plus_elem)
    #   override_mask: torch.Tensor (n_elem,) bool — which elements to override
    #              (typically r_to_tip <= 2*ℓ₀; precomputed by runner)
    #   apply_g: bool (default True) — multiply by g(α) before substituting
    #              (matches degraded ψ⁺ that fatigue accumulator expects)
    if fem_oracle_dict is not None and fem_oracle_dict.get('enable', False) \
            and T_conn is not None:
        psi_target = fem_oracle_dict['psi_target']    # raw FEM ψ⁺ at PIDL elems
        mask = fem_oracle_dict['override_mask']
        apply_g = fem_oracle_dict.get('apply_g', True)
        if apply_g:
            override_value = (g_alpha * psi_target).detach()
        else:
            override_value = psi_target.detach()
        # In-place override on the masked elements
        psi_plus_elem = torch.where(mask, override_value, psi_plus_elem)
    return psi_plus_elem


# Computes the components of strain and gradients of alpha
def gradients(inp, u, v, alpha, area_elem, T_conn=None):
    """
    计算应变分量和相场梯度（无修改，与 Manav 原始完全一致）

    应变张量（小变形假设）：
        ε_11 = ∂u/∂x,  ε_22 = ∂v/∂y,  ε_12 = (1/2)(∂u/∂y + ∂v/∂x)
    """
    grad_u_x, grad_u_y = field_grads(inp, u, area_elem, T_conn)
    grad_v_x, grad_v_y = field_grads(inp, v, area_elem, T_conn)
    grad_alpha_x, grad_alpha_y = field_grads(inp, alpha, area_elem, T_conn)

    strain_11 = grad_u_x
    strain_22 = grad_v_y
    strain_12 = 0.5 * (grad_u_y + grad_v_x)

    return strain_11, strain_22, strain_12, grad_alpha_x, grad_alpha_y


# Computes the gradient of fields using the shape functions of a triangular element in FEA
def field_grads(inp, field, area_elem, T=None):
    """
    计算场的梯度（无修改，与 Manav 原始完全一致）

    两种模式：
    1. 自动微分（T=None）
    2. 数值计算（T≠None）: 三角形单元形状函数 ⭐ 论文推荐
    """
    if T is None:
        grad_field = torch.autograd.grad(field.sum(), inp, create_graph=True)[0]
        grad_x = grad_field[:, 0]
        grad_y = grad_field[:, 1]
    else:
        grad_x = (inp[T[:, 1], -1] - inp[T[:, 2], -1]) * field[T[:, 0]] + \
                 (inp[T[:, 2], -1] - inp[T[:, 0], -1]) * field[T[:, 1]] + \
                 (inp[T[:, 0], -1] - inp[T[:, 1], -1]) * field[T[:, 2]]
        grad_y = (inp[T[:, 2], -2] - inp[T[:, 1], -2]) * field[T[:, 0]] + \
                 (inp[T[:, 0], -2] - inp[T[:, 2], -2]) * field[T[:, 1]] + \
                 (inp[T[:, 1], -2] - inp[T[:, 0], -2]) * field[T[:, 2]]
        grad_x = grad_x / area_elem / 2
        grad_y = grad_y / area_elem / 2

    return grad_x, grad_y


# Computes the element-wise strain energy density after applying the prescribed split
def strain_energy_with_split(strain_11, strain_22, strain_12, alpha, matprop, pffmodel):
    """
    计算应变能（含分解），无修改，与 Manav 原始完全一致。

    返回：
    ------
    E_el : 总弹性能（含退化）
    E_el_p : 退化拉伸弹性能 g(α)·ψ⁺  ← ★ get_psi_plus_per_elem 使用此返回值
    """
    fun_EDegrade, _ = pffmodel.Edegrade(alpha)

    if pffmodel.se_split == 'volumetric':
        mat_K = matprop.mat_lmbda + 2.0 / 3.0 * matprop.mat_mu
        strain_k = (strain_11 + strain_22) / 3.0
        strain_deviatoric_11 = strain_11 - strain_k
        strain_deviatoric_22 = strain_22 - strain_k
        strain_deviatoric_33 = 0 - strain_k
        E_elV_p = 0.5 * mat_K * (nn.ReLU()(3.0 * strain_k))**2
        E_elV_n = 0.5 * mat_K * (-nn.ReLU()(-3.0 * strain_k))**2
        E_el_dev = matprop.mat_mu * (
            strain_deviatoric_11**2 + strain_deviatoric_22**2 +
            strain_deviatoric_33**2 + 2 * strain_12**2
        )
        E_el_p = E_elV_p + E_el_dev
        E_el   = fun_EDegrade * E_el_p + E_elV_n
    else:
        E_el   = fun_EDegrade * (
            0.5 * matprop.mat_lmbda * (strain_11 + strain_22)**2 +
            matprop.mat_mu * (strain_11**2 + strain_22**2 + 2 * strain_12**2)
        )
        E_el_p = E_el

    return E_el, E_el_p


# Computes stress in each element
def stress(strain_11, strain_22, strain_12, alpha, matprop, pffmodel):
    """无修改，与 Manav 原始完全一致。"""
    fun_EDegrade, _ = pffmodel.Edegrade(alpha)

    if pffmodel.se_split == 'volumetric':
        mat_K = matprop.mat_lmbda + 2.0 / 3.0 * matprop.mat_mu
        strain_k = (strain_11 + strain_22) / 3.0
        strain_deviatoric_11 = strain_11 - strain_k
        strain_deviatoric_22 = strain_22 - strain_k
        stress_11 = fun_EDegrade * (mat_K * nn.ReLU()(3.0 * strain_k) + 2 * matprop.mat_mu * strain_deviatoric_11) \
                    + mat_K * (-nn.ReLU()(-3.0 * strain_k))
        stress_22 = fun_EDegrade * (mat_K * nn.ReLU()(3.0 * strain_k) + 2 * matprop.mat_mu * strain_deviatoric_22) \
                    + mat_K * (-nn.ReLU()(-3.0 * strain_k))
        stress_12 = fun_EDegrade * (2 * matprop.mat_mu * strain_12)
    else:
        stress_11 = fun_EDegrade * (matprop.mat_lmbda * (strain_11 + strain_22) + 2 * matprop.mat_mu * strain_11)
        stress_22 = fun_EDegrade * (matprop.mat_lmbda * (strain_11 + strain_22) + 2 * matprop.mat_mu * strain_22)
        stress_12 = fun_EDegrade * (2 * matprop.mat_mu * strain_12)

    return stress_11, stress_22, stress_12
