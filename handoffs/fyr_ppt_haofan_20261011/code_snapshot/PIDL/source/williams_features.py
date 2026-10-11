"""
williams_features.py  —  Direction 4: Tip-Enriched Input Features
=======================================================================
将裂尖相对极坐标 (r, θ) 转换为 Williams 展开基函数，作为 NN 的附加输入特征。

物理背景
--------
Mode-I 平面应变裂尖渐近位移场（Williams 1957）：
    u_x ~ √r · [cos(θ/2)·(κ-1+2sin²(θ/2))]
    u_y ~ √r · [sin(θ/2)·(κ+1-2cos²(θ/2))]
其中 κ = 3-4ν（平面应变），θ ∈ (-π, π] 以 atan2 定义。

标准 MLP 因谱偏差（Rahaman et al., ICML 2019）无法表示 r^(1/2) 奇异性，
导致 Kt_PIDL ≈ 7 << Kt_FEM ≈ 15。
通过在 NN 输入中显式提供 Williams 基函数，使 NN 的第一层无需"重新发现"奇异性形式。

输入特征集（8 维，"标准集"）
----------------------------
[x, y, √(r/l₀), r/l₀, sin(θ/2), cos(θ/2), sin(3θ/2), cos(3θ/2)]

  - x, y          : 全局空间坐标，保留物理语义
  - √(r/l₀)       : 主奇异项（KI 相关）；无量纲化，l₀ 为相场长度参数
  - r/l₀          : 二次项（T-stress、KII 贡献）
  - sin/cos(θ/2)  : Mode-I 角函数（主项）
  - sin/cos(3θ/2) : Mode-I 角函数（高阶项）

说明
----
- theta_mode='atan2' : θ = atan2(dy, dx) ∈ (-π, π]，裂缝面（θ=±π）有不连续跳变，
                       物理上正确（位移在裂缝面不连续），网格预制裂缝处 NN 不需要拟合跳变
- theta_mode 接口预留，将来可扩展为 'learnable_freq' 等形式
- r_min 参数防止裂尖正好与节点重合时出现 0/0

参考
----
Williams, M. L. (1957). On the stress distribution at the base of a stationary crack.
    J. Appl. Mech., 24(1), 109–114.
Tancik, M. et al. (2020). Fourier features let networks learn high frequency functions.
    NeurIPS 33.
Rahaman, N. et al. (2019). On the spectral bias of neural networks. ICML.
"""

import torch


def compute_williams_features(inp, x_tip, l0,
                               y_tip=0.0,
                               r_min=1e-6,
                               theta_mode="atan2"):
    """
    计算 Williams 展开增强的 NN 输入特征（8 维）。

    参数
    ----
    inp        : Tensor, shape (N, 2)  — 节点坐标 [x, y]
    x_tip      : float                — 当前裂尖 x 坐标（每圈从 psi⁺ 重心估计）
    l0         : float                — 相场长度参数（无量纲化用，默认 0.01）
    y_tip      : float                — 裂尖 y 坐标（SENS 几何始终为 0）
    r_min      : float                — r 的下限，防止除零（默认 1e-6）
    theta_mode : str                  — 角度计算方式
                                        'atan2'  : θ = atan2(dy, dx) ∈ (-π, π]

    返回
    ----
    inp_nn : Tensor, shape (N, 8)
        [x, y, √(r/l₀), r/l₀, sin(θ/2), cos(θ/2), sin(3θ/2), cos(3θ/2)]
    """
    dx = inp[:, 0] - x_tip
    dy = inp[:, 1] - y_tip
    r  = (dx**2 + dy**2).sqrt().clamp(min=r_min)

    if theta_mode == "atan2":
        theta = torch.atan2(dy, dx)          # θ ∈ (-π, π]
    else:
        raise NotImplementedError(
            f"theta_mode='{theta_mode}' 尚未实现。"
            f"当前支持: 'atan2'。"
        )

    r_norm = r / l0                          # 无量纲半径

    inp_nn = torch.stack([
        inp[:, 0],               # x        — 全局坐标
        inp[:, 1],               # y        — 全局坐标
        r_norm.sqrt(),           # √(r/l₀)  — 主奇异项
        r_norm,                  # r/l₀     — 二次项
        (theta / 2).sin(),       # sin(θ/2) — Mode-I 主项
        (theta / 2).cos(),       # cos(θ/2) — Mode-I 主项
        (1.5 * theta).sin(),     # sin(3θ/2)— Mode-I 高阶
        (1.5 * theta).cos(),     # cos(3θ/2)— Mode-I 高阶
    ], dim=1)                    # shape (N, 8)

    return inp_nn


def compute_x_tip_psi(inp, psi_plus_elem, T_conn, top_k=10):
    """
    用 ψ⁺ 加权重心估计裂尖 x 坐标。

    取 psi_plus_elem 最大的 top_k 个单元的形心 x 坐标均值。

    参数
    ----
    inp           : Tensor, shape (N_nodes, 2) — 节点坐标
    psi_plus_elem : Tensor, shape (N_elem,)    — 各单元 ψ⁺（能量密度）
    T_conn        : Tensor / ndarray,
                    shape (N_elem, 3)          — 三角形单元节点编号
    top_k         : int                        — 取前 k 个高能量单元（默认 10）

    返回
    ----
    x_tip_psi : float — ψ⁺ 重心估计的裂尖 x 坐标

    说明
    ----
    - 三角形形心 x = (x₀ + x₁ + x₂) / 3
    - top_k 用于平滑：单个最大单元可能是数值噪声，10 个均值更稳定
    - 此函数仅在 fatigue_on=True（有 psi_plus_elem）且 Williams 启用时调用
    """
    # 三角形形心 x 坐标：取三个顶点 x 的均值
    x_cent = (inp[T_conn[:, 0], 0]
              + inp[T_conn[:, 1], 0]
              + inp[T_conn[:, 2], 0]) / 3.0   # shape (N_elem,)

    k = min(top_k, psi_plus_elem.shape[0])
    top_idx = psi_plus_elem.topk(k).indices   # 能量最大的 k 个单元索引

    x_tip_psi = float(x_cent[top_idx].mean().item())
    return x_tip_psi
