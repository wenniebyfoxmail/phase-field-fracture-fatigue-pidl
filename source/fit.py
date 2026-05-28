import math
import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm

from compute_energy import compute_energy, gradients, strain_energy_with_split


# =============================================================================
# Algorithm 1 — Wang, Teng & Perdikaris (2020) arXiv:2001.04536
# Adaptive learning-rate annealing for PINN composite loss functions.
#
# Balances gradient magnitudes across loss terms so that BC/supervision
# signals are not drowned out by the Deep Ritz physics loss.
#
# State dict keys (mutable, persists across cycles via model_train.py):
#   enable        : bool  — master switch
#   alpha_mom     : float — EMA momentum (paper default 0.9)
#   update_every  : int   — update lambdas every N epochs (paper default 10)
#   lambda_sup    : float — running weight for supervised loss (init 1.0)
#   lambda_sym    : float — running weight for symmetry penalty (init 1.0)
#   lambda_strac  : float — running weight for side-traction penalty (init 1.0)
#   print_every   : int   — print gradient diagnostics every N Algo1 updates
#   _step         : int   — internal update counter
#   grad_stats_last : dict — latest raw gradient diagnostics
# =============================================================================

def _algo1_update(field_comp, inp_train, hist_alpha, matprop, pffmodel,
                  area_T, T_conn, f_fatigue, supervised_dict, symmetry_dict,
                  side_traction_dict, state, element_mask=None):
    """Wang 2020 Algo 1: update λ_i = (1-α)λ_i + α·(max|∇L_r| / mean|∇L_i|).

    Uses torch.autograd.grad (not .backward) to avoid polluting .grad buffers.
    Each BC term gets its own forward pass — adds ~N_terms extra passes per
    update_every epochs (overhead < 30% for update_every=10).
    """
    alpha_mom = float(state.get('alpha_mom', 0.9))
    params = [p for p in field_comp.parameters() if p.requires_grad]
    if not params:
        return

    def _probe(loss_scalar, retain_graph=False):
        """Gradient of loss_scalar w.r.t. params; returns list of grad tensors."""
        if not torch.is_tensor(loss_scalar) or not loss_scalar.requires_grad:
            return []
        return torch.autograd.grad(
            loss_scalar, params, allow_unused=True, retain_graph=retain_graph)

    def _max_grad(grads):
        vals = [g.abs().max().item() for g in grads if g is not None]
        return max(vals, default=1e-30)

    def _mean_grad(grads):
        vals = [g.abs().mean().item() for g in grads if g is not None]
        return float(np.mean(vals)) if vals else 1e-30

    def _ema(key, lhat):
        old = float(state.get(key, 1.0))
        raw = (1.0 - alpha_mom) * old + alpha_mom * float(lhat)
        lmax = float(state.get('lambda_max', float('inf')))
        state[key] = min(raw, lmax)

    def _record_grad_stats(stats, name, grads):
        stats[f'{name}_gmax'] = _max_grad(grads)
        stats[f'{name}_gmean'] = _mean_grad(grads)

    # ── Probe 1: Deep Ritz physics loss ──────────────────────────────────────
    if T_conn is None:
        inp_p = inp_train.detach().clone().requires_grad_(True)
    else:
        inp_p = inp_train
    u_p, v_p, a_p = field_comp.fieldCalculation(inp_p)
    el, ed, eh = compute_energy(inp_p, u_p, v_p, a_p, hist_alpha,
                                matprop, pffmodel, area_T, T_conn, f_fatigue,
                                element_mask=element_mask)
    eps = torch.as_tensor(1e-30, dtype=el.dtype, device=el.device)
    lv_el = torch.log10(el + eps)
    lv_ed = torch.log10(ed + eps)
    lv_eh = torch.log10(eh + eps)
    lv = torch.log10(el + ed + eh + eps)

    grad_stats = {
        'E_el': float(el.detach().item()),
        'E_d': float(ed.detach().item()),
        'E_hist': float(eh.detach().item()),
        'E_total': float((el + ed + eh).detach().item()),
    }
    _record_grad_stats(grad_stats, 'logE_el', _probe(lv_el, retain_graph=True))
    _record_grad_stats(grad_stats, 'logE_d', _probe(lv_ed, retain_graph=True))
    _record_grad_stats(grad_stats, 'logE_hist', _probe(lv_eh, retain_graph=True))
    g_phys = _probe(lv)
    _record_grad_stats(grad_stats, 'logE_total', g_phys)
    max_phys = max(grad_stats['logE_total_gmax'], 1e-30)

    # ── Probe 2: supervised ψ⁺ / α term ─────────────────────────────────────
    if supervised_dict is not None and supervised_dict.get('lambda', 0.0) > 0:
        _tk = supervised_dict.get('target_kind', 'psi')
        if T_conn is None:
            inp_p2 = inp_train.detach().clone().requires_grad_(True)
        else:
            inp_p2 = inp_train
        u2, v2, a2 = field_comp.fieldCalculation(inp_p2)
        if _tk == 'psi':
            psi2 = _compute_psi_raw_per_elem(inp_p2, u2, v2, a2,
                                             matprop, pffmodel, area_T, T_conn)
            l_sup = supervised_dict['fem_sup'].supervised_loss(
                psi2, cycle_idx=supervised_dict['cycle_idx'],
                pidl_centroids=supervised_dict['pidl_centroids'],
                lambda_sup=1.0,
                loss_kind=supervised_dict.get('loss_kind', 'mse_log'),
                mask=supervised_dict.get('mask', None))
        else:  # 'alpha'
            a_elem = a2[T_conn].mean(dim=1) if T_conn is not None else a2
            l_sup = supervised_dict['fem_sup'].alpha_supervised_loss(
                a_elem, cycle_idx=supervised_dict['cycle_idx'],
                pidl_centroids=supervised_dict['pidl_centroids'],
                lambda_sup=1.0,
                loss_kind=supervised_dict.get('loss_kind', 'mse_lin'),
                mask=supervised_dict.get('mask', None))
        g_sup = _probe(l_sup)
        _record_grad_stats(grad_stats, 'sup', g_sup)
        mean_sup = max(_mean_grad(g_sup), 1e-30)
        _ema('lambda_sup', max_phys / mean_sup)

    # ── Probe 3: soft symmetry penalty ───────────────────────────────────────
    if symmetry_dict is not None and symmetry_dict.get('enable', False):
        l_sym = _compute_symmetry_penalty(field_comp, inp_train, 1.0, 1.0, 1.0)
        g_sym = _probe(l_sym)
        _record_grad_stats(grad_stats, 'sym', g_sym)
        mean_sym = max(_mean_grad(g_sym), 1e-30)
        _ema('lambda_sym', max_phys / mean_sym)

    # ── Probe 4: side-traction penalty ───────────────────────────────────────
    if side_traction_dict is not None and side_traction_dict.get('enable', False):
        l_strac = _compute_side_traction_penalty(
            field_comp, matprop, 1.0, 1.0,
            side_traction_dict.get('sigma_ref', 1.0),
            side_traction_dict.get('n_bdy_pts', 51))
        g_strac = _probe(l_strac)
        _record_grad_stats(grad_stats, 'strac', g_strac)
        mean_strac = max(_mean_grad(g_strac), 1e-30)
        _ema('lambda_strac', max_phys / mean_strac)

    state['_step'] = state.get('_step', 0) + 1
    state['grad_stats_last'] = grad_stats

    print_every = max(1, int(state.get('print_every', 1)))
    if state['_step'] % print_every == 0:
        def _fmt(name):
            return (f"{grad_stats.get(name + '_gmax', 0.0):.3e}/"
                    f"{grad_stats.get(name + '_gmean', 0.0):.3e}")

        print(f"  [Algo1] update#{state['_step']:04d} | "
              f"gmax/gmean logE total/el/ed/hist="
              f"{_fmt('logE_total')} {_fmt('logE_el')} "
              f"{_fmt('logE_d')} {_fmt('logE_hist')} | "
              f"soft sup/sym/strac={_fmt('sup')} {_fmt('sym')} {_fmt('strac')} | "
              f"λ_sup={state.get('lambda_sup',1.0):.2f} "
              f"λ_sym={state.get('lambda_sym',1.0):.2f} "
              f"λ_strac={state.get('lambda_strac',1.0):.2f}")


def _compute_symmetry_penalty(field_comp, inp, lam_alpha, lam_u, lam_v):
    """Soft mirror-symmetry penalty for SENT (y → -y geometry symmetry).

    Penalizes on NN raw correction (NOT total field), so the affine v_BC
    `(y+0.5)·sin(θ)·λ` is NOT constrained to be odd. The variational
    symmetric solution under such affine BC has even u_x correction +
    odd u_y correction + even α correction.

    Three terms:
      L_alpha = ‖α(x,y) − α(x,−y)‖²   (even, after alpha_constraint)
      L_u     = ‖u_x_corr(x,y) − u_x_corr(x,−y)‖²
      L_v     = ‖u_y_corr(x,y) + u_y_corr(x,−y)‖²

    Single forward pass via batch doubling to amortize CUDA launch cost.

    Only valid when williams_enabled=False (Williams branch uses 8D θ
    feature, not raw 2D input).
    """
    if getattr(field_comp, 'williams_enabled', False):
        return torch.tensor(0.0, device=inp.device)

    inp_m = inp.clone()
    inp_m[:, 1] = -inp_m[:, 1]
    inp_doubled = torch.cat([inp, inp_m], dim=0)
    raw_doubled = field_comp.net(inp_doubled)
    N = inp.shape[0]
    raw, raw_m = raw_doubled[:N], raw_doubled[N:]

    L_u = ((raw[:, 0] - raw_m[:, 0]) ** 2).mean()
    L_v = ((raw[:, 1] + raw_m[:, 1]) ** 2).mean()
    a   = field_comp.alpha_constraint(raw[:, 2])
    a_m = field_comp.alpha_constraint(raw_m[:, 2])
    L_alpha = ((a - a_m) ** 2).mean()

    return lam_alpha * L_alpha + lam_u * L_u + lam_v * L_v


def _compute_side_traction_penalty(field_comp, matprop, lam_xx, lam_xy,
                                    sigma_ref=1.0, n_bdy_pts=51):
    """Soft side-traction penalty: enforce σ_xx ≈ 0, σ_xy ≈ 0 on x=±0.5.

    The side edges of the SENT specimen are traction-free by the problem statement,
    but PIDL does not enforce this explicitly (FEM satisfies it via natural BC).
    This penalty penalises σ_xx and σ_xy on the side boundaries using AD-mode
    gradients at a fixed set of query points — independent of whether the main
    training loop uses numerical or AD gradients.

    Args:
        field_comp:  FieldComputation instance (NN + BC layers).
        matprop:     MaterialProperties (provides mat_lmbda, mat_mu).
        lam_xx:      Penalty weight for σ_xx term.
        lam_xy:      Penalty weight for σ_xy term.
        sigma_ref:   Stress normalisation (default 1.0 = material-unit scale, E=1).
        n_bdy_pts:   Number of y-sample points per side edge (default 51).

    Returns:
        Scalar penalty tensor (graph-attached for backward).
    """
    device = next(field_comp.net.parameters()).device

    # Sample y ∈ (−0.495, 0.495) to avoid corners (y0=−0.5, yL=+0.5 are BC nodes)
    y_vals = torch.linspace(-0.495, 0.495, n_bdy_pts, dtype=torch.float32, device=device)
    x_left  = torch.full((n_bdy_pts,), -0.5, dtype=torch.float32, device=device)
    x_right = torch.full((n_bdy_pts,),  0.5, dtype=torch.float32, device=device)

    pts_left  = torch.stack([x_left,  y_vals], dim=1)
    pts_right = torch.stack([x_right, y_vals], dim=1)
    xy_bdy = torch.cat([pts_left, pts_right], dim=0)   # (2*n_bdy_pts, 2)
    xy_bdy = xy_bdy.requires_grad_(True)

    # Forward pass at boundary (always AD-mode, graph required for backward)
    u_bdy, v_bdy, _ = field_comp.fieldCalculation(xy_bdy)

    # ∂u/∂x, ∂u/∂y — retain graph so v_bdy can be differentiated next
    grads_u = torch.autograd.grad(u_bdy.sum(), xy_bdy,
                                  create_graph=True, retain_graph=True)[0]
    du_dx = grads_u[:, 0]
    du_dy = grads_u[:, 1]

    # ∂v/∂x, ∂v/∂y
    grads_v = torch.autograd.grad(v_bdy.sum(), xy_bdy, create_graph=True)[0]
    dv_dx = grads_v[:, 0]
    dv_dy = grads_v[:, 1]

    # Plane-strain isotropic stress (small-strain, undegraded for boundary check)
    lmbda = matprop.mat_lmbda   # Lame first parameter (E*nu / ((1+nu)(1-2nu)))
    mu    = matprop.mat_mu      # Shear modulus (E / (2*(1+nu)))
    eps11 = du_dx
    eps22 = dv_dy
    eps12 = 0.5 * (du_dy + dv_dx)

    sig_xx = lmbda * (eps11 + eps22) + 2.0 * mu * eps11   # normal stress on x-face
    sig_xy = 2.0 * mu * eps12                               # shear stress on x-face

    L_xx = (sig_xx / sigma_ref).pow(2).mean()
    L_xy = (sig_xy / sigma_ref).pow(2).mean()

    return lam_xx * L_xx + lam_xy * L_xy


def _compute_j_path_penalty(field_comp, matprop, x_tip=0.0,
                            radii=(0.05, 0.08, 0.12), n_theta=100,
                            delta_face=0.05, eps=1e-12):
    """Differentiable J-integral path-independence penalty.

    For a valid elastic field the J-integral is contour-independent. We compute
    J on several circular contours around the (moving) crack tip at (x_tip, 0)
    and penalise their spread — squared coefficient of variation. No FEM target;
    this is a self-consistency regulariser that improves near-tip field quality.

    Contours sit at r ∈ {5ℓ, 8ℓ, 12ℓ}, outside the phase-field damage band, so
    raw (undegraded) Hooke σ is LEFM-meaningful there. Open contour over
    θ ∈ (−π+δ, π−δ) avoids the crack faces.

    Returns a scalar penalty tensor (graph-attached for backward).
    """
    device = next(field_comp.net.parameters()).device
    theta = torch.linspace(-math.pi + delta_face, math.pi - delta_face, n_theta,
                           dtype=torch.float32, device=device)
    cos_t, sin_t = torch.cos(theta), torch.sin(theta)

    lmbda = matprop.mat_lmbda
    mu    = matprop.mat_mu

    J_per_r = []
    for r in radii:
        x = x_tip + r * cos_t
        y = r * sin_t
        xy = torch.stack([x, y], dim=1).requires_grad_(True)   # (n_theta, 2)
        u, v, _ = field_comp.fieldCalculation(xy)

        grad_u = torch.autograd.grad(u.sum(), xy, create_graph=True, retain_graph=True)[0]
        grad_v = torch.autograd.grad(v.sum(), xy, create_graph=True, retain_graph=True)[0]
        du_dx, du_dy = grad_u[:, 0], grad_u[:, 1]
        dv_dx, dv_dy = grad_v[:, 0], grad_v[:, 1]

        eps11 = du_dx
        eps22 = dv_dy
        eps12 = 0.5 * (du_dy + dv_dx)
        sig11 = lmbda * (eps11 + eps22) + 2.0 * mu * eps11
        sig22 = lmbda * (eps11 + eps22) + 2.0 * mu * eps22
        sig12 = 2.0 * mu * eps12
        W = 0.5 * (sig11 * eps11 + sig22 * eps22 + 2.0 * sig12 * eps12)

        t1 = sig11 * cos_t + sig12 * sin_t      # σ_1j n_j
        t2 = sig12 * cos_t + sig22 * sin_t      # σ_2j n_j
        integrand = W * cos_t - t1 * du_dx - t2 * dv_dx
        J = r * torch.trapz(integrand, theta)
        J_per_r.append(J)

    J_stack = torch.stack(J_per_r)
    J_mean = J_stack.mean()
    # squared coefficient of variation: dimensionless, scale-invariant
    return J_stack.var(unbiased=False) / (J_mean.pow(2) + eps)


def _compute_psi_raw_per_elem(inp, u, v, alpha, matprop, pffmodel, area_T, T_conn):
    """Compute UNDEGRADED ψ⁺_0 per element (E_el_p before g(α) multiply).

    Used by MIT-8 supervised-warmup loss. Differs from
    compute_energy.get_psi_plus_per_elem (which returns g·E_el_p).
    """
    s11, s22, s12, _, _ = gradients(inp, u, v, alpha, area_T, T_conn)
    if T_conn is None:
        alpha_elem = alpha
    else:
        alpha_elem = (alpha[T_conn[:, 0]] + alpha[T_conn[:, 1]]
                      + alpha[T_conn[:, 2]]) / 3
    _, E_el_p = strain_energy_with_split(s11, s22, s12, alpha_elem,
                                         matprop, pffmodel)
    return E_el_p   # graph-attached, so backward through u, v works


class EarlyStopping:
    '''
    If the relative decrease in the loss is < min_delta for # of consecutive steps = tolerance,
    then the training is stopped.
    '''
    def __init__(self, tol_steps=10, min_delta=1e-3, device='cpu'):
        self.tol_steps = torch.tensor([tol_steps], dtype=torch.int, device=device)
        self.min_delta = torch.tensor([min_delta], dtype=torch.float, device=device)
        self.counter = torch.tensor([0], dtype=torch.int, device=device)
        self.early_stop = False        
        
    def __call__(self, train_loss, train_loss_prev):
        delta = torch.abs(train_loss - train_loss_prev)/(torch.abs(train_loss_prev)+np.finfo(float).eps)
        if delta > self.min_delta:
            self.counter = self.counter * 0
        else:
            self.counter += 1
            if self.counter >= self.tol_steps:  
                self.early_stop = True



def fit(field_comp, training_set_collocation, T_conn, area_T, hist_alpha, matprop, pffmodel,
        weight_decay, num_epochs, optimizer, intermediateModel_path=None, writer=None, training_dict={},
        f_fatigue=1.0, crack_tip_weights=None,
        supervised_dict=None,
        symmetry_dict=None,
        side_traction_dict=None,
        grad_annealing_state=None,
        element_mask=None,
        j_path_dict=None):
    # ★ grad_annealing_state: if provided and enable=True, pre-computed λ values
    #   from Algorithm 1 (updated during RPROP phase) are applied here.
    #   LBFGS does not update λ — it uses whatever values RPROP computed last cycle.
    _a1 = grad_annealing_state or {}
    _lam_sup   = float(_a1.get('lambda_sup',   1.0))
    _lam_sym   = float(_a1.get('lambda_sym',   1.0))
    _lam_strac = float(_a1.get('lambda_strac', 1.0))
    loss_data = list()

    # Loop over epochs
    for epoch in range(num_epochs):
        loop = tqdm(training_set_collocation, miniters=25, disable=True)
        # Loop over batches
        for j, (inp_train, outp_train)  in enumerate(loop):

            def closure():
                optimizer.zero_grad()
                if T_conn == None:
                    inp_train.requires_grad = True

                # 1. 前向传播：计算位移和相场
                u, v, alpha = field_comp.fieldCalculation(inp_train)

                # 2. 计算能量（物理）
                # ★ 传入 f_fatigue（疲劳退化函数）；默认 1.0 与 Manav 原始完全一致
                # ★ 传入 crack_tip_weights（裂尖自适应加权）；None = 均匀
                loss_E_el, loss_E_d, loss_hist = compute_energy(inp_train, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
                                                                f_fatigue=f_fatigue,
                                                                crack_tip_weights=crack_tip_weights,
                                                                element_mask=element_mask)

                # 3. 损失函数 = log(总能量) ！！！
                loss_var = torch.log10(loss_E_el + loss_E_d + loss_hist)

                # 4. 权重正则化（防止过拟合）
                # weight regularization
                loss_reg = 0.0
                if weight_decay != 0:
                    for name, param in field_comp.net.named_parameters():
                        if 'weight' in name:
                            loss_reg += torch.sum(param**2)

                loss = loss_var + weight_decay*loss_reg

                # ★ MIT-8 supervised term (Apr 25 + Apr 26 amortization)
                # ★ 2026-05-14: target_kind='psi' (existing) or 'alpha' (new α-direct supervision)
                # ★ 2026-05-19 Algo1: lambda overridden by _lam_sup when grad_annealing active
                if supervised_dict is not None and supervised_dict.get('lambda', 0.0) > 0:
                    _every_n = max(1, int(supervised_dict.get('every_n_epochs', 1)))
                    if (epoch % _every_n) == 0:
                        _target_kind = supervised_dict.get('target_kind', 'psi')
                        if _target_kind == 'psi':
                            psi_raw_pidl = _compute_psi_raw_per_elem(
                                inp_train, u, v, alpha, matprop, pffmodel, area_T, T_conn)
                            loss_sup = supervised_dict['fem_sup'].supervised_loss(
                                psi_raw_pidl,
                                cycle_idx=supervised_dict['cycle_idx'],
                                pidl_centroids=supervised_dict['pidl_centroids'],
                                lambda_sup=_lam_sup,   # ★ Algo1-tuned or dict value
                                loss_kind=supervised_dict.get('loss_kind', 'mse_log'),
                                mask=supervised_dict.get('mask', None))
                        elif _target_kind == 'alpha':
                            alpha_per_elem = alpha[T_conn].mean(dim=1)
                            loss_sup = supervised_dict['fem_sup'].alpha_supervised_loss(
                                alpha_per_elem,
                                cycle_idx=supervised_dict['cycle_idx'],
                                pidl_centroids=supervised_dict['pidl_centroids'],
                                lambda_sup=_lam_sup,   # ★ Algo1-tuned or dict value
                                loss_kind=supervised_dict.get('loss_kind', 'mse_lin'),
                                mask=supervised_dict.get('mask', None))
                        else:
                            raise ValueError(f"unknown supervised target_kind={_target_kind!r}; expected 'psi' or 'alpha'")
                        loss = loss + _every_n * loss_sup

                # ★ 2026-05-07 Soft mirror-symmetry penalty (B path)
                if symmetry_dict is not None and symmetry_dict.get('enable', False):
                    loss_sym = _compute_symmetry_penalty(
                        field_comp, inp_train,
                        lam_alpha=_lam_sym * symmetry_dict.get('lambda_alpha', 1.0),
                        lam_u    =_lam_sym * symmetry_dict.get('lambda_u',     1.0),
                        lam_v    =_lam_sym * symmetry_dict.get('lambda_v',     1.0))
                    loss = loss + loss_sym
                    if writer is not None:
                        writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_sym', loss_sym.item(), epoch)

                # ★ 2026-05-08 Soft side-traction penalty
                if side_traction_dict is not None and side_traction_dict.get('enable', False):
                    loss_strac = _compute_side_traction_penalty(
                        field_comp, matprop,
                        lam_xx    =_lam_strac * side_traction_dict.get('lam_xx',    1.0),
                        lam_xy    =_lam_strac * side_traction_dict.get('lam_xy',    1.0),
                        sigma_ref =side_traction_dict.get('sigma_ref', 1.0),
                        n_bdy_pts =side_traction_dict.get('n_bdy_pts', 51))
                    loss = loss + loss_strac
                    if writer is not None:
                        writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_strac', loss_strac.item(), epoch)

                # ★ J-integral path-independence regulariser (no FEM target)
                if j_path_dict is not None and j_path_dict.get('enable', False):
                    loss_jpath = j_path_dict.get('lambda', 1.0) * _compute_j_path_penalty(
                        field_comp, matprop,
                        x_tip   =j_path_dict.get('x_tip', 0.0),
                        radii   =j_path_dict.get('radii', (0.05, 0.08, 0.12)),
                        n_theta =j_path_dict.get('n_theta', 100))
                    loss = loss + loss_jpath
                    if writer is not None:
                        writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_jpath', loss_jpath.item(), epoch)

                if writer is not None:
                    writer.add_scalars('U_p_'+str(field_comp.lmbda.item()), {'loss':loss.item(), "loss_E":loss_var.item()}, epoch)

                loop.set_description(f"U_p: {field_comp.lmbda}, Epoch [{epoch}/{num_epochs}]")
                loop.set_postfix(loss=loss.item(), loss_E=loss_var.item())
                
                loss_data.append(loss.item())
                if intermediateModel_path is not None:
                    idx = len(loss_data)
                    steps = training_dict["save_model_every_n"]
                    if steps > 0 and idx >= steps and idx % steps == 0:
                        intermModel_path = intermediateModel_path/Path('intermediate_1NN_' + str(int(field_comp.lmbda*1000000)) + 'by1000000_' + str(idx) + '.pt')
                        torch.save(field_comp.net.state_dict(), intermModel_path)

                # 5. 反向传播
                loss.backward()
                return loss
            
            optimizer.step(closure=closure)

    return loss_data



def fit_with_early_stopping(field_comp, training_set_collocation, T_conn, area_T, hist_alpha, matprop, pffmodel,
                            weight_decay, num_epochs, optimizer, min_delta, intermediateModel_path=None, writer=None, training_dict={},
                            f_fatigue=1.0, crack_tip_weights=None,
                            supervised_dict=None,
                            symmetry_dict=None,
                            side_traction_dict=None,
                            grad_annealing_state=None,
                            delta1_dataset=None,
                            element_mask=None,
                            j_path_dict=None):
    # ★ grad_annealing_state (2026-05-19 Algorithm 1):
    #   Mutable dict passed from model_train.train(). Persists across cycles.
    #   Algo1 probes are run in RPROP only (not LBFGS) because RPROP's flat
    #   loop allows clean separate backward passes via torch.autograd.grad.
    _a1 = grad_annealing_state or {}
    _a1_enabled    = bool(_a1.get('enable', False))
    _a1_upd_every  = int(_a1.get('update_every', 10))

    # ★ δ-1 element-level IS setup
    _d1_active = delta1_dataset is not None
    _d1_K = getattr(delta1_dataset, 'samples_per_epoch', None) if _d1_active else None

    loss_data = list()
    early_stopping = EarlyStopping(tol_steps=10, min_delta=min_delta, device=area_T.device)
    loss_prev = torch.tensor([0.0], device=area_T.device)

    # Loop over epochs
    for epoch in range(num_epochs):
        loop = tqdm(training_set_collocation, miniters=25, disable=True)
        # Loop over batches
        for j, (inp_train, outp_train)  in enumerate(loop):

            # ── Algorithm 1 probe (before main step, no .grad pollution) ─────
            if _a1_enabled and epoch > 0 and epoch % _a1_upd_every == 0:
                _algo1_update(
                    field_comp, inp_train, hist_alpha, matprop, pffmodel,
                    area_T, T_conn, f_fatigue,
                    supervised_dict, symmetry_dict, side_traction_dict, _a1,
                    element_mask=element_mask)

            # Read current Algo1 weights (updated above or from previous cycle)
            _lam_sup   = float(_a1.get('lambda_sup',   1.0))
            _lam_sym   = float(_a1.get('lambda_sym',   1.0))
            _lam_strac = float(_a1.get('lambda_strac', 1.0))

            # ★ δ-1: sample element subset for this epoch (p_e may have been updated by model_train)
            if _d1_active:
                _d1_loader = delta1_dataset.make_loader(samples_per_epoch=_d1_K)
                _d1_elem_idx, _d1_imp_raw = next(iter(_d1_loader))
                # imp_raw = 1/(p_e * n_elem) from ElementDataset.__getitem__; scale to 1/p_e
                _d1_subset = _d1_elem_idx.long().to(area_T.device)
                _d1_imp_w  = (_d1_imp_raw.float() * delta1_dataset.n_elem).to(area_T.device)
            else:
                _d1_subset = None
                _d1_imp_w  = None

            optimizer.zero_grad()
            if T_conn == None:
                inp_train.requires_grad = True
            u, v, alpha = field_comp.fieldCalculation(inp_train)
            # ★ 传入 f_fatigue、crack_tip_weights、δ-1 element subset
            loss_E_el, loss_E_d, loss_hist = compute_energy(inp_train, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
                                                            f_fatigue=f_fatigue,
                                                            crack_tip_weights=crack_tip_weights,
                                                            element_subset=_d1_subset,
                                                            importance_weights=_d1_imp_w,
                                                            element_mask=element_mask)
            loss_var = torch.log10(loss_E_el + loss_E_d + loss_hist)

            # weight regularization
            loss_reg = 0.0
            if weight_decay != 0:
                for name, param in field_comp.net.named_parameters():
                    if 'weight' in name:
                        loss_reg += torch.sum(param**2)

            loss = loss_var + weight_decay*loss_reg

            # ★ MIT-8 supervised term (Apr 25 + Algo1 lambda override 2026-05-19)
            if supervised_dict is not None and supervised_dict.get('lambda', 0.0) > 0:
                _every_n = max(1, int(supervised_dict.get('every_n_epochs', 1)))
                if (epoch % _every_n) == 0:
                    _target_kind = supervised_dict.get('target_kind', 'psi')
                    if _target_kind == 'psi':
                        psi_raw_pidl = _compute_psi_raw_per_elem(
                            inp_train, u, v, alpha, matprop, pffmodel, area_T, T_conn)
                        loss_sup = supervised_dict['fem_sup'].supervised_loss(
                            psi_raw_pidl,
                            cycle_idx=supervised_dict['cycle_idx'],
                            pidl_centroids=supervised_dict['pidl_centroids'],
                            lambda_sup=_lam_sup,   # ★ Algo1-tuned
                            loss_kind=supervised_dict.get('loss_kind', 'mse_log'),
                            mask=supervised_dict.get('mask', None))
                    elif _target_kind == 'alpha':
                        alpha_per_elem = alpha[T_conn].mean(dim=1)
                        loss_sup = supervised_dict['fem_sup'].alpha_supervised_loss(
                            alpha_per_elem,
                            cycle_idx=supervised_dict['cycle_idx'],
                            pidl_centroids=supervised_dict['pidl_centroids'],
                            lambda_sup=_lam_sup,   # ★ Algo1-tuned
                            loss_kind=supervised_dict.get('loss_kind', 'mse_lin'),
                            mask=supervised_dict.get('mask', None))
                    else:
                        raise ValueError(f"unknown supervised target_kind={_target_kind!r}; expected 'psi' or 'alpha'")
                    loss = loss + _every_n * loss_sup

            # ★ 2026-05-07 Soft mirror-symmetry penalty (Algo1 lambda override)
            if symmetry_dict is not None and symmetry_dict.get('enable', False):
                loss_sym = _compute_symmetry_penalty(
                    field_comp, inp_train,
                    lam_alpha=_lam_sym * symmetry_dict.get('lambda_alpha', 1.0),
                    lam_u    =_lam_sym * symmetry_dict.get('lambda_u',     1.0),
                    lam_v    =_lam_sym * symmetry_dict.get('lambda_v',     1.0))
                loss = loss + loss_sym
                if writer is not None:
                    writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_sym', loss_sym.item(), epoch)

            # ★ 2026-05-08 Soft side-traction penalty (Algo1 lambda override)
            if side_traction_dict is not None and side_traction_dict.get('enable', False):
                loss_strac = _compute_side_traction_penalty(
                    field_comp, matprop,
                    lam_xx    =_lam_strac * side_traction_dict.get('lam_xx',    1.0),
                    lam_xy    =_lam_strac * side_traction_dict.get('lam_xy',    1.0),
                    sigma_ref =side_traction_dict.get('sigma_ref', 1.0),
                    n_bdy_pts =side_traction_dict.get('n_bdy_pts', 51))
                loss = loss + loss_strac
                if writer is not None:
                    writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_strac', loss_strac.item(), epoch)

            # ★ J-integral path-independence regulariser (no FEM target)
            if j_path_dict is not None and j_path_dict.get('enable', False):
                loss_jpath = j_path_dict.get('lambda', 1.0) * _compute_j_path_penalty(
                    field_comp, matprop,
                    x_tip   =j_path_dict.get('x_tip', 0.0),
                    radii   =j_path_dict.get('radii', (0.05, 0.08, 0.12)),
                    n_theta =j_path_dict.get('n_theta', 100))
                loss = loss + loss_jpath
                if writer is not None:
                    writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_jpath', loss_jpath.item(), epoch)

            if writer is not None:
                    writer.add_scalars('U_p_'+str(field_comp.lmbda.item()), {'loss':loss.item(), "loss_E":loss_var.item()}, epoch)

            loop.set_description(f"U_p: {field_comp.lmbda}, Epoch [{epoch}/{num_epochs}]")
            loop.set_postfix(loss=loss.item(), loss_E=loss_var.item())

            loss_data.append(loss.item())
            if intermediateModel_path is not None:
                idx = len(loss_data)
                steps = training_dict["save_model_every_n"]
                if steps > 0 and idx >= steps and idx % steps == 0:
                    intermModel_path = intermediateModel_path/Path('intermediate_1NN_' + str(int(field_comp.lmbda*1000000)) + 'by1000000_' + str(idx) + '.pt')
                    torch.save(field_comp.net.state_dict(), intermModel_path)

            loss.backward()
            optimizer.step()
            
        early_stopping(loss, loss_prev)
        if early_stopping.early_stop:
            break
        loss_prev = loss

    return loss_data
