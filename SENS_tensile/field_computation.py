import sys
from pathlib import Path
import torch
import torch.nn as nn

# ★ Direction 4: Williams 特征模块（源码在 source/ 目录）
# 只在 williams_dict["enable"]=True 时实际调用，否则无影响
_SOURCE_PATH = Path(__file__).parents[1] / 'source'
if str(_SOURCE_PATH) not in sys.path:
    sys.path.insert(0, str(_SOURCE_PATH))
from williams_features import compute_williams_features
# ★ Direction 5: Enriched Ansatz —— 输出端 Williams 主奇异项增强
from enriched_ansatz import compute_enrichment
from network import NeuralNet, init_xavier


class FieldComputation:
    '''
    This class constructs the displacement and phase fields from the NN outputs by baking in the
    Dirichlet boundary conditions (BCs) and other constraints.

    net: neural network
    domain_extrema: tensor([[x_min, x_max], [y_min, y_max]])
    lmbda: prescribed displacement
    theta: Angle of the direction of loading from the x-axis (not used in all problems)
    alpha_ansatz: type of function to constrain alpha in {'smooth', 'nonsmooth'}

    ★ Direction 4 新增参数
    williams_dict: dict | None
        None 或 {"enable": False} → 原始行为（2D 输入）
        {"enable": True, "theta_mode": "atan2", "r_min": 1e-6} → 8D Williams 特征输入

    ★ Direction 5 新增参数
    ansatz_dict: dict | None
        None 或 {"enable": False} → 原始行为（无富集项）
        {"enable": True, "x_tip": 0.0, "y_tip": 0.0, "r_cutoff": 0.1,
         "nu": 0.3, "c_init": 0.01, "modes": ["I"]}
          → 在 NN 输出上叠加 c · χ(r) · F^mode(r,θ)，其中 c 是可学习标量
    l0: float
        相场长度参数，用于特征无量纲化（默认 0.01）

    ★ 2026-05-06 新增 — symmetry_prior（geometry-aware mirror symmetry prior）
    symmetry_prior: bool
        False (default) → 原始行为（保留所有 caller 的现有结果）
        True → 对 NN raw correction 强制 y-mirror parity，仅在 baseline 分支
        （非 Williams branch）生效。Williams 分支的 8D feature 不受影响。
        实现：input 用 (x, y²) 让 NN raw output 自动 even；disp_v_raw 再乘
        y 让 correction odd。alpha + disp_u correction 自动 even。
        v_BC 仍是 affine in y（非 odd）；约束作用于 NN correction，不约束总场。
        见 docs/.../paper §4 reframe + 设计 caveat（Wu 2026 conceptual grounding，
        Carrara framework requires symmetric solution under symmetric BCs）。
        Phase 3 非对称几何关闭此 flag。

    ★ 2026-05-11 新增 — exact_bc_dict（C4 hard side-traction branch）
    exact_bc_dict: dict | None
        None 或 {"enable": False} → 原始 BC ansatz
        {"enable": True, "mode": "sent_plane_strain", "nu": 0.3}
          → use a SENT-specific exact-BC trial space:
             - particular solution = uniform plane-strain uniaxial extension
               with zero σ_xx, σ_xy on x=±0.5,
             - NN correction multiplied by top-bottom bubble × side-distance²,
               so correction and its x-derivative vanish on the side edges.
        这是 Sukumar-style exact trial 的项目定制版，不是通用 ADF 库。

        {"enable": True, "mode": "fem_anchor"}
          → GRIPHFiTH-style essential BC alignment:
             - v=0 on bottom and v=lambda on top,
             - u is fixed only at bottom-left anchor (x_min, y_min),
             - horizontal displacement is free on the rest of top/bottom.

    fieldCalculation: applies BCs and constraint on alpha (needs to be customized for each problem)
    update_hist_alpha: alpha_field for use in the next loading step to enforce irreversibility
    '''
    def __init__(self, net, domain_extrema, lmbda, theta,
                 alpha_constraint='nonsmooth',
                 williams_dict=None,
                 ansatz_dict=None,
                 l0=0.01,
                 symmetry_prior=False,
                 exact_bc_dict=None,
                 local_patch_dict=None):
        self.net = net
        self.domain_extrema = domain_extrema
        self.theta = theta
        self.lmbda = lmbda

        # ★ Direction 4: Williams 特征配置
        _wd = williams_dict or {}
        self.williams_enabled  = _wd.get('enable', False)
        self.williams_theta_mode = _wd.get('theta_mode', 'atan2')
        self.williams_r_min    = _wd.get('r_min', 1e-6)
        self.l0   = float(l0)
        self.x_tip = 0.0   # 当前裂尖 x 坐标；由 model_train.py 每圈更新
        self.y_tip = 0.0   # SENS 几何中裂尖始终在 y=0

        # ★ Direction 5: Enriched Ansatz 配置 —— 输出端主奇异位移项
        _ad = ansatz_dict or {}
        self.ansatz_enabled = _ad.get('enable', False)
        self.ansatz_x_tip   = float(_ad.get('x_tip', 0.0))   # FIXED（不随 cycle 更新）
        self.ansatz_y_tip   = float(_ad.get('y_tip', 0.0))
        self.ansatz_r_cutoff = float(_ad.get('r_cutoff', 0.1))
        self.ansatz_nu      = float(_ad.get('nu', 0.3))
        self.ansatz_modes   = tuple(_ad.get('modes', ("I",)))
        if self.ansatz_enabled:
            # nn.Parameter 自动 requires_grad=True；device 由 main.py 外部移动
            self.c_singular = nn.Parameter(
                torch.tensor([float(_ad.get('c_init', 0.01))], dtype=torch.float32)
            )
        else:
            self.c_singular = None

        if alpha_constraint == 'smooth':
            self.alpha_constraint = torch.sigmoid
        else:
            self.alpha_constraint = NonsmoothSigmoid(2.0, 1e-3)

        # ★ 2026-05-06 mirror symmetry prior (only for baseline branch, not Williams)
        self.symmetry_prior = bool(symmetry_prior)
        if self.symmetry_prior and self.williams_enabled:
            print("[FieldComputation] WARNING: symmetry_prior=True ignored when williams_enabled=True "
                  "(Williams 8D feature 已包含 r,θ 几何信息，不叠加 y² 变换)")

        # ★ 2026-05-11 C4 exact-BC branch
        _eb = exact_bc_dict or {}
        self.exact_bc_enabled = bool(_eb.get('enable', False))
        self.exact_bc_mode = str(_eb.get('mode', 'sent_plane_strain'))
        self.exact_bc_nu = float(_eb.get('nu', 0.3))
        # ★ 2026-05-14: configurable side-bubble power.
        # side^2 (default, V7 PASS by construction) — historical C4.
        # side^1 (linear gating) — V7 may WARN/FAIL but less aggressive NN damping,
        #   diagnostic for "is side² over-constraining crack propagation?"
        self.exact_bc_side_power = float(_eb.get('side_power', 2.0))
        if self.exact_bc_enabled and self.exact_bc_mode not in ('sent_plane_strain', 'fem_anchor'):
            raise ValueError(f"Unsupported exact_bc_mode={self.exact_bc_mode!r}")

        # ★ 2026-05-30: local patch representation discriminator.
        # This keeps the variational objective unchanged.  It only enriches the
        # raw NN output by adding a compact-support local network near the crack
        # tip.  The patch net is registered as a child of self.net so existing
        # checkpoint files (field_comp.net.state_dict()) include its weights.
        _lp = local_patch_dict or {}
        self.local_patch_enabled = bool(_lp.get('enable', False))
        self.local_patch_x_tip = float(_lp.get('x_tip', 0.0))
        self.local_patch_y_tip = float(_lp.get('y_tip', 0.0))
        self.local_patch_wr = float(_lp.get('wr', 0.1))
        self.local_patch_scale = float(_lp.get('scale', 1.0))
        self.local_patch_output_mode = str(_lp.get('output_mode', 'all'))
        self.local_patch_blend_mode = str(_lp.get('blend_mode', 'additive'))
        self.local_patch_n_patches = int(_lp.get('n_patches', 1))
        if self.local_patch_enabled:
            if self.local_patch_wr <= 0.0:
                raise ValueError("local_patch_dict['wr'] must be positive")
            if self.local_patch_output_mode not in ('all', 'alpha_only', 'uv_only'):
                raise ValueError(
                    "local_patch_dict['output_mode'] must be 'all', 'alpha_only', or 'uv_only'"
                )
            if self.local_patch_blend_mode not in ('additive', 'partition'):
                raise ValueError("local_patch_dict['blend_mode'] must be 'additive' or 'partition'")
            if self.local_patch_n_patches < 1:
                raise ValueError("local_patch_dict['n_patches'] must be >= 1")

            if 'x_centers' in _lp:
                x_centers = [float(x) for x in _lp['x_centers']]
            elif self.local_patch_n_patches == 1:
                x_centers = [self.local_patch_x_tip]
            else:
                x0 = float(_lp.get('x_start', 0.0))
                x1 = float(_lp.get('x_end', 0.45))
                x_centers = torch.linspace(x0, x1, self.local_patch_n_patches).tolist()
            if 'y_centers' in _lp:
                y_centers = [float(y) for y in _lp['y_centers']]
            else:
                y_centers = [self.local_patch_y_tip] * len(x_centers)
            if len(x_centers) != len(y_centers):
                raise ValueError("local_patch x_centers/y_centers length mismatch")
            self.local_patch_centers = tuple(zip(x_centers, y_centers))
            self.local_patch_n_patches = len(self.local_patch_centers)

            def _make_patch_net():
                patch_net = NeuralNet(
                    input_dimension=2,
                    output_dimension=3,
                    n_hidden_layers=int(_lp.get('hidden_layers', 3)),
                    neurons=int(_lp.get('neurons', 80)),
                    activation=str(_lp.get('activation', 'TrainableReLU')),
                    init_coeff=float(_lp.get('init_coeff', 1.0)),
                )
                init_xavier(patch_net)
                return patch_net

            if self.local_patch_n_patches == 1:
                self.net.add_module('local_patch_net', _make_patch_net())
            else:
                self.net.add_module(
                    'local_patch_nets',
                    nn.ModuleList([_make_patch_net() for _ in self.local_patch_centers])
                )
            print("[LocalPatch] enabled | "
                  f"mode={self.local_patch_output_mode} "
                  f"blend={self.local_patch_blend_mode} "
                  f"n={self.local_patch_n_patches} "
                  f"wr={self.local_patch_wr:.4f} "
                  f"centers={self.local_patch_centers} "
                  f"scale={self.local_patch_scale:.3g}")

    def _local_patch_output(self, inp):
        if not self.local_patch_enabled:
            return None
        patches = []
        chis = []
        if self.local_patch_n_patches == 1:
            patch_nets = [self.net.local_patch_net]
        else:
            patch_nets = list(self.net.local_patch_nets)
        for patch_net, (x_c, y_c) in zip(patch_nets, self.local_patch_centers):
            dx = (inp[:, 0] - x_c) / self.local_patch_wr
            dy = (inp[:, 1] - y_c) / self.local_patch_wr
            local_inp = torch.stack([dx, dy], dim=1)
            r2 = dx.square() + dy.square()
            chi = torch.clamp(1.0 - r2, min=0.0).square()
            patches.append(patch_net(local_inp))
            chis.append(chi)
        chi_stack = torch.stack(chis, dim=1)
        patch_stack = torch.stack(patches, dim=1)
        chi_sum = chi_stack.sum(dim=1).clamp(min=0.0)
        patch = (
            chi_stack.unsqueeze(2) * patch_stack
        ).sum(dim=1) / chi_sum.clamp(min=1e-12).unsqueeze(1)

        if self.local_patch_output_mode == 'alpha_only':
            mask = torch.tensor([0.0, 0.0, 1.0], dtype=patch.dtype, device=patch.device)
            patch = patch * mask
        elif self.local_patch_output_mode == 'uv_only':
            mask = torch.tensor([1.0, 1.0, 0.0], dtype=patch.dtype, device=patch.device)
            patch = patch * mask

        beta = chi_sum.clamp(max=1.0).unsqueeze(1)
        return {
            'patch': self.local_patch_scale * patch,
            'beta': beta,
        }

    def _normalized_tb_bubble(self, inp, y0, yL):
        """Top-bottom bubble in [0, 1], zero on y=y0 and y=yL."""
        H = yL - y0
        return 4.0 * (inp[:, 1] - y0) * (yL - inp[:, 1]) / (H * H)

    def _normalized_side_bubble(self, inp, x0, xL):
        """Side-distance bubble in [0, 1], zero on x=x0 and x=xL."""
        W = xL - x0
        return 4.0 * (inp[:, 0] - x0) * (xL - inp[:, 0]) / (W * W)

    def fieldCalculation(self, inp):
        """
        将神经网络的原始输出转换为满足边界条件的物理场。

        ★ Direction 4 修改：
          - williams_enabled=True  → inp_nn = Williams 8D 特征（送入 NN）
          - williams_enabled=False → inp_nn = inp（原始 2D，与原始行为完全一致）
          - 边界条件强制仍使用物理坐标 inp（不变）
        """
        x0 = self.domain_extrema[0, 0]
        xL = self.domain_extrema[0, 1]
        y0 = self.domain_extrema[1, 0]
        yL = self.domain_extrema[1, 1]

        # ★ Direction 4: 计算 NN 输入（Williams 特征 or 原始坐标）
        if self.williams_enabled:
            inp_nn = compute_williams_features(
                inp,
                x_tip=self.x_tip,
                l0=self.l0,
                y_tip=self.y_tip,
                r_min=self.williams_r_min,
                theta_mode=self.williams_theta_mode,
            )
        elif self.symmetry_prior:
            # ★ 2026-05-06 mirror symmetry prior:
            # NN sees (x, y²) instead of (x, y). NN raw output is automatically
            # even in y (function of y²). Below we apply odd parity to disp_v_raw
            # by multiplying by y, so the NN correction has the right symmetry
            # for the SENT geometry. v_BC and bubble are unaffected (BC and
            # bubble may not be odd; the prior is on the NN correction only,
            # consistent with the variational symmetric solution).
            # ★ 2026-05-07 input feature scaling fix: map [0, 0.25] → [-1, 1] so
            # the y-axis input has the same scale + sign range as x ∈ [-0.5, 0.5]
            # rescaled. Without this rescale, RPROP sign-based step updates were
            # ill-conditioned in the y direction, causing 6-15× slowdown vs baseline.
            # NN raw output is still even in y (function of y² only).
            y_col = inp[:, 1:2]
            inp_nn = torch.cat([inp[:, 0:1], 8.0 * y_col**2 - 1.0], dim=1)
        else:
            inp_nn = inp   # 原始行为，无开销

        out = self.net(inp_nn)     # 神经网络输出（8D 或 2D 输入）
        patch_out = self._local_patch_output(inp)
        if patch_out is not None:
            if self.local_patch_blend_mode == 'partition':
                out = (1.0 - patch_out['beta']) * out + patch_out['beta'] * patch_out['patch']
            else:
                out = out + patch_out['beta'] * patch_out['patch']

        # ★ 2026-05-06 mirror symmetry: enforce odd parity on disp_v_raw correction
        # disp_u_raw: even (NN raw output already even via y² input) — pass through
        # disp_v_raw: even via y² → multiply by y to get odd (and disp_v(x,0)=0 automatic)
        # alpha_raw:  even (passes through alpha_constraint downstream)
        if self.symmetry_prior and not self.williams_enabled:
            y_col1d = inp[:, 1]                  # shape [N], y in [-0.5, 0.5]
            out_disp = torch.stack([
                out[:, 0],                       # disp_u correction: even
                y_col1d * out[:, 1],             # disp_v correction: odd
            ], dim=1)
        else:
            out_disp = out[:, 0:2]              # 位移部分（原始行为）

        # ★ Direction 5: Enriched Ansatz —— 输出端叠加 c·χ(r)·F^mode(r,θ)
        # 使用 FIXED (x_tip, y_tip) = (0, 0) 避免 Williams v4 的峰元素漂移问题
        if self.ansatz_enabled:
            u_sing, v_sing = compute_enrichment(
                inp,
                x_tip=self.ansatz_x_tip,
                y_tip=self.ansatz_y_tip,
                r_cutoff=self.ansatz_r_cutoff,
                nu=self.ansatz_nu,
                modes=self.ansatz_modes,
            )
            disp_u = out_disp[:, 0] + self.c_singular * u_sing
            disp_v = out_disp[:, 1] + self.c_singular * v_sing
        else:
            disp_u = out_disp[:, 0]
            disp_v = out_disp[:, 1]

        # 约束相场在 [0, 1] 范围内
        alpha = self.alpha_constraint(out[:, 2])

        # 边界条件强制（使用物理坐标 inp，不受 Williams / Enriched Ansatz 影响）
        if self.exact_bc_enabled:
            if not torch.allclose(torch.cos(self.theta), torch.zeros_like(self.theta), atol=1e-7):
                raise ValueError("exact_bc sent_plane_strain currently supports vertical loading only")
            if not torch.allclose(torch.sin(self.theta), torch.ones_like(self.theta), atol=1e-7):
                raise ValueError("exact_bc sent_plane_strain currently expects theta=pi/2")

            H = yL - y0
            if self.exact_bc_mode == 'fem_anchor':
                W = xL - x0
                anchor_gate = ((inp[:, 0] - x0) / W).square() + ((inp[:, 1] - y0) / H).square()
                v_bubble = (inp[:, -1] - y0) * (yL - inp[:, -1])
                u = anchor_gate * disp_u * self.lmbda
                v = (v_bubble * disp_v + (inp[:, -1] - y0) / H) * self.lmbda
            else:
                # Plane-strain uniaxial extension particular solution:
                # eps_xx = -nu/(1-nu) * eps_yy  →  sigma_xx = 0, sigma_xy = 0.
                epsxx_over_lambda = -self.exact_bc_nu / ((1.0 - self.exact_bc_nu) * H)
                u_lift = epsxx_over_lambda * inp[:, 0]
                v_lift = (inp[:, 1] - y0) / H

                tb = self._normalized_tb_bubble(inp, y0, yL)
                side = self._normalized_side_bubble(inp, x0, xL)
                # ★ 2026-05-14: side_power configurable (default 2.0 = historical C4)
                if self.exact_bc_side_power == 2.0:
                    correction_bubble = tb * side.square()
                else:
                    correction_bubble = tb * side.pow(self.exact_bc_side_power)

                u = (u_lift + correction_bubble * disp_u) * self.lmbda
                v = (v_lift + correction_bubble * disp_v) * self.lmbda
        else:
            # (y-y0)(yL-y) 在边界 y=y0 和 y=yL 处为 0
            u = ((inp[:, -1]-y0)*(yL-inp[:, -1])*disp_u +
                 (inp[:, -1]-y0)/(yL-y0)*torch.cos(self.theta)) * self.lmbda
            v = ((inp[:, -1]-y0)*(yL-inp[:, -1])*disp_v +
                 (inp[:, -1]-y0)/(yL-y0)*torch.sin(self.theta)) * self.lmbda

        return u, v, alpha

    def update_hist_alpha(self, inp):
        _, _, pred_alpha = self.fieldCalculation(inp)
        pred_alpha = pred_alpha.detach()
        return pred_alpha

    def parameters(self):
        """
        ★ Direction 5: 收集所有可训练参数（NN + c_singular）。
        optim 需要的参数迭代器；model_train.py 用它替代 field_comp.net.parameters()。
        """
        params = list(self.net.parameters())
        if self.c_singular is not None:
            params.append(self.c_singular)
        params.extend(getattr(self, "extra_trainable_params", []))
        return params

    def local_patch_parameters(self):
        if not self.local_patch_enabled:
            return []
        if self.local_patch_n_patches == 1:
            return list(self.net.local_patch_net.parameters())
        return list(self.net.local_patch_nets.parameters())
    

class NonsmoothSigmoid(nn.Module):
    '''
    Constructs a continuous piecewise linear increasing function with the
    central part valid in (-support, support) and its value going from 0 to 1. 
    Outside this region, the slope equals coeff.

    '''
    """
        确保 α ∈ [0, 1]，但比sigmoid更有利于裂纹萌生

        在中间区域是线性的，两端有小斜率的延伸
        """
    def __init__(self, support=2.0, coeff=1e-3):
        super(NonsmoothSigmoid, self).__init__()
        self.support = support
        self.coeff =  coeff
    def forward(self, x):
        a = x>self.support
        b = x<-self.support
        c = torch.logical_not(torch.logical_or(a, b))
        out = a*(self.coeff*(x-self.support)+1.0)+ \
                b*(self.coeff*(x+self.support))+ \
                c*(x/2.0/self.support+0.5)
        return out
