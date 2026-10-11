"""
enriched_ansatz.py  —  Direction 5: Output-side Mode-I Williams enrichment
=======================================================================
将 Williams 展开的位移主奇异项作为 NN 输出端的显式附加项（XFEM 式增强），
而非 Direction 4 的输入端特征。

动机
----
Direction 4 (Williams 输入特征) + Direction 2.1 (Fourier 特征) 的三方对比表明：
输入端谱扩展无法闭合 PIDL-FEM α_max 100× 的差距（两者都停在 α_max ≈ 5-9）。
下一手段：把 r^(1/2) 奇异形函数直接加到输出位移上，让 NN 只需学习光滑
"修正"部分 —— 类似 XFEM 的富集位移插值。

Ansatz 形式
----------
    u_x(x,y) = BC_scale_u · [ NN_u(x,y) + c · χ(r) · F_x^I(r,θ) ]
    u_y(x,y) = BC_scale_v · [ NN_v(x,y) + c · χ(r) · F_y^I(r,θ) ]

其中：
  - c             : 可学习标量（nn.Parameter），代表平均 K_I 强度
  - χ(r) = exp(-r/r_cutoff)
                  : 局部截断函数，r_cutoff ≈ 10·l₀ = 0.1
  - (r, θ)        : 相对 FIXED (x_tip, y_tip) = (0, 0) 的极坐标
  - F_x^I, F_y^I  : Mode-I Williams 主奇异位移项（见下）
  - F_x^II, F_y^II: Mode-II Williams 主奇异位移项（预留，SENT 不启用）

Mode-I 平面应变位移渐近场 (Williams, 1957)：
    F_x^I(r,θ) = √r · cos(θ/2) · (κ - 1 + 2·sin²(θ/2))
    F_y^I(r,θ) = √r · sin(θ/2) · (κ + 1 - 2·cos²(θ/2))
    κ = 3 - 4ν  (平面应变)

Mode-II 平面应变位移渐近场 (Williams, 1957)：
    F_x^II(r,θ) = √r · sin(θ/2) · (κ + 1 + 2·cos²(θ/2))
    F_y^II(r,θ) = -√r · cos(θ/2) · (κ - 1 - 2·sin²(θ/2))

关键设计决策
-----------
1. **模块化 Mode I / II**       : 本文件同时定义两者，SENT 默认只启用 I
2. **局部截断 χ(r)**            : 富集仅在 r < 数倍 r_cutoff 生效，避免远场污染
3. **固定 x_tip = (0, 0)**       : 不随 cycle 更新（Williams v4 移动 x_tip 的
                                   峰元素漂移是损伤不积累的主因；固定 x_tip 让
                                   原点附近单元稳定累积 ᾱ）
4. **单个可学习标量 c**          : 代表平均 K_I，nn.Parameter，初值 0.01
5. **BC 由 BC_scale 兜底**       : 富集项乘以与 NN 输出相同的 BC_scale，
                                   自动满足 Dirichlet 边界

参考
----
Williams, M. L. (1957). On the stress distribution at the base of a stationary crack.
    J. Appl. Mech., 24(1), 109-114.
Moës, N. et al. (1999). A finite element method for crack growth without remeshing.
    Int. J. Numer. Methods Eng., 46(1), 131-150.  (XFEM)
Belytschko, T., Black, T. (1999). Elastic crack growth in finite elements with
    minimal remeshing. Int. J. Numer. Methods Eng., 45(5), 601-620.
"""

import torch


# -----------------------------------------------------------------------
# Mode-I 主奇异位移项
# -----------------------------------------------------------------------
def mode_I_singular(r, theta, kappa):
    """
    Williams Mode-I leading singular term.

    参数
    ----
    r     : Tensor, shape (N,) — 相对裂尖的径向距离（已 clamp min 以防 0）
    theta : Tensor, shape (N,) — 相对裂尖的角坐标 ∈ (-π, π]
    kappa : float              — Kolosov 常数；平面应变 κ = 3 - 4ν

    返回
    ----
    (u_x_sing, v_y_sing) : 两个 Tensor, 各 shape (N,)
    """
    sqrt_r = r.sqrt()
    half_theta = 0.5 * theta
    sin_h = half_theta.sin()
    cos_h = half_theta.cos()

    u_x = sqrt_r * cos_h * (kappa - 1.0 + 2.0 * sin_h * sin_h)
    v_y = sqrt_r * sin_h * (kappa + 1.0 - 2.0 * cos_h * cos_h)

    return u_x, v_y


# -----------------------------------------------------------------------
# Mode-II 主奇异位移项（预留：SENT Mode-I-dominant，默认不启用）
# -----------------------------------------------------------------------
def mode_II_singular(r, theta, kappa):
    """
    Williams Mode-II leading singular term.

    参数
    ----
    r     : Tensor, shape (N,)
    theta : Tensor, shape (N,)
    kappa : float — 平面应变 κ = 3 - 4ν

    返回
    ----
    (u_x_sing, v_y_sing) : 两个 Tensor, 各 shape (N,)
    """
    sqrt_r = r.sqrt()
    half_theta = 0.5 * theta
    sin_h = half_theta.sin()
    cos_h = half_theta.cos()

    u_x =  sqrt_r * sin_h * (kappa + 1.0 + 2.0 * cos_h * cos_h)
    v_y = -sqrt_r * cos_h * (kappa - 1.0 - 2.0 * sin_h * sin_h)

    return u_x, v_y


_MODE_FN = {
    "I":  mode_I_singular,
    "II": mode_II_singular,
}


# -----------------------------------------------------------------------
# 主入口：计算富集位移（已叠加 local cutoff χ(r)）
# -----------------------------------------------------------------------
def compute_enrichment(inp, x_tip=0.0, y_tip=0.0,
                       r_cutoff=0.1, nu=0.3,
                       modes=("I",),
                       r_min=1e-6):
    """
    计算 Williams 主奇异项位移增量（未乘 c，也未乘 BC_scale）。

    参数
    ----
    inp      : Tensor, shape (N, 2)   — 节点坐标 [x, y]
    x_tip    : float                  — 裂尖 x 坐标（建议固定为 0，不随 cycle 更新）
    y_tip    : float                  — 裂尖 y 坐标（SENT 几何为 0）
    r_cutoff : float                  — χ(r)=exp(-r/r_cutoff) 的衰减尺度；
                                        推荐 ~10·l₀ = 0.1
    nu       : float                  — Poisson 比，κ = 3 - 4ν（平面应变）
    modes    : tuple[str]             — 启用的模式列表；默认 ("I",)，
                                        可扩展 ("I","II")
    r_min    : float                  — r 下限防零

    返回
    ----
    u_sing, v_sing : Tensor, shape (N,)
        每个模式贡献相加；c * χ(r) * F(r,θ) 已内含 χ(r) 因子。
        调用方仍需乘 c（nn.Parameter）和 BC_scale（物理坐标函数）。
    """
    dx = inp[:, 0] - x_tip
    dy = inp[:, 1] - y_tip
    r = (dx * dx + dy * dy).sqrt().clamp(min=r_min)
    theta = torch.atan2(dy, dx)         # ∈ (-π, π]

    kappa = 3.0 - 4.0 * nu               # 平面应变 Kolosov 常数

    chi = (-r / r_cutoff).exp()          # 局部截断 χ(r) = exp(-r/r_cutoff)

    u_sing = torch.zeros_like(r)
    v_sing = torch.zeros_like(r)
    for mode in modes:
        if mode not in _MODE_FN:
            raise NotImplementedError(
                f"mode='{mode}' not implemented. Supported: {list(_MODE_FN)}"
            )
        u_m, v_m = _MODE_FN[mode](r, theta, kappa)
        u_sing = u_sing + u_m
        v_sing = v_sing + v_m

    # 乘上截断函数
    u_sing = chi * u_sing
    v_sing = chi * v_sing

    return u_sing, v_sing
