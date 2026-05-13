import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm

from compute_energy import compute_energy, gradients, strain_energy_with_split


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
        side_traction_dict=None):
    # ★ MIT-8 supervised_dict — see fit_with_early_stopping signature
    # ★ 新增参数 f_fatigue：
    #    - 标量 1.0（默认）：完全等价 Manav 原始行为
    #    - Tensor (n_elem,)：逐元素疲劳退化函数，由 fatigue_history.compute_fatigue_degrad() 提供
    # ★ 新增参数 crack_tip_weights（方向3：裂尖自适应损失加权）：
    #    - None（默认）：均匀权重，完全等价原始代码
    #    - Tensor (n_elem,)：w_e = 1 + β·(ψ⁺_e/ψ⁺_mean)^p，裂尖附近 w 大
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
                                                                crack_tip_weights=crack_tip_weights)

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
                                lambda_sup=supervised_dict['lambda'],
                                loss_kind=supervised_dict.get('loss_kind', 'mse_log'),
                                mask=supervised_dict.get('mask', None))
                        elif _target_kind == 'alpha':
                            # α per-node → per-element via T_conn averaging
                            alpha_per_elem = alpha[T_conn].mean(dim=1)
                            loss_sup = supervised_dict['fem_sup'].alpha_supervised_loss(
                                alpha_per_elem,
                                cycle_idx=supervised_dict['cycle_idx'],
                                pidl_centroids=supervised_dict['pidl_centroids'],
                                lambda_sup=supervised_dict['lambda'],
                                loss_kind=supervised_dict.get('loss_kind', 'mse_lin'),
                                mask=supervised_dict.get('mask', None))
                        else:
                            raise ValueError(f"unknown supervised target_kind={_target_kind!r}; expected 'psi' or 'alpha'")
                        loss = loss + _every_n * loss_sup

                # ★ 2026-05-07 Soft mirror-symmetry penalty (B path)
                # Activated by symmetry_dict={'enable': True, 'lambda_alpha':..., ...}
                # Penalizes NN raw correction parity, NOT total field
                if symmetry_dict is not None and symmetry_dict.get('enable', False):
                    loss_sym = _compute_symmetry_penalty(
                        field_comp, inp_train,
                        lam_alpha=symmetry_dict.get('lambda_alpha', 1.0),
                        lam_u    =symmetry_dict.get('lambda_u',     1.0),
                        lam_v    =symmetry_dict.get('lambda_v',     1.0))
                    loss = loss + loss_sym
                    if writer is not None:
                        writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_sym', loss_sym.item(), epoch)

                # ★ 2026-05-08 Soft side-traction penalty
                # Activated by side_traction_dict={'enable': True, 'lam_xx':..., 'lam_xy':..., 'sigma_ref':...}
                # Enforces σ_xx ≈ 0, σ_xy ≈ 0 on x=±0.5 (traction-free side edges)
                if side_traction_dict is not None and side_traction_dict.get('enable', False):
                    loss_strac = _compute_side_traction_penalty(
                        field_comp, matprop,
                        lam_xx    =side_traction_dict.get('lam_xx',    1.0),
                        lam_xy    =side_traction_dict.get('lam_xy',    1.0),
                        sigma_ref =side_traction_dict.get('sigma_ref', 1.0),
                        n_bdy_pts =side_traction_dict.get('n_bdy_pts', 51))
                    loss = loss + loss_strac
                    if writer is not None:
                        writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_strac', loss_strac.item(), epoch)

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
                            side_traction_dict=None):
    # ★ MIT-8 supervised_dict (Apr 25, optional, default None → identical behavior):
    #    {'fem_sup': FEMSupervision, 'cycle_idx': int, 'lambda': float,
    #     'pidl_centroids': np.ndarray, 'loss_kind': 'mse_log'|'mse_lin'|'mse_rel',
    #     'every_n_epochs': int (default 1; >1 amortizes the supervised
    #         pass — supervised loss only added every N epochs to reduce
    #         per-cycle wall time while still biasing the trajectory)}
    # ★ 新增参数 f_fatigue（同 fit）
    # ★ 新增参数 crack_tip_weights（方向3，同 fit）
    loss_data = list()
    early_stopping = EarlyStopping(tol_steps=10, min_delta=min_delta, device=area_T.device)
    loss_prev = torch.tensor([0.0], device=area_T.device)

    # Loop over epochs
    for epoch in range(num_epochs):
        loop = tqdm(training_set_collocation, miniters=25, disable=True)
        # Loop over batches
        for j, (inp_train, outp_train)  in enumerate(loop):

            optimizer.zero_grad()
            if T_conn == None:
                inp_train.requires_grad = True
            u, v, alpha = field_comp.fieldCalculation(inp_train)
            # ★ 传入 f_fatigue 和 crack_tip_weights
            loss_E_el, loss_E_d, loss_hist = compute_energy(inp_train, u, v, alpha, hist_alpha, matprop, pffmodel, area_T, T_conn,
                                                            f_fatigue=f_fatigue,
                                                            crack_tip_weights=crack_tip_weights)
            loss_var = torch.log10(loss_E_el + loss_E_d + loss_hist)

            # weight regularization
            loss_reg = 0.0
            if weight_decay != 0:
                for name, param in field_comp.net.named_parameters():
                    if 'weight' in name:
                        loss_reg += torch.sum(param**2)

            loss = loss_var + weight_decay*loss_reg

            # ★ MIT-8 supervised term (Apr 25): joint physics + FEM ψ⁺ supervision.
            # Apr 26 amortization: supervised loss only computed every N epochs
            # to avoid 30× wall-time penalty per cycle. Default every_n=1
            # (every epoch); use every_n=10 to add supervision once per 10 epochs.
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
                            lambda_sup=supervised_dict['lambda'],
                            loss_kind=supervised_dict.get('loss_kind', 'mse_log'),
                            mask=supervised_dict.get('mask', None))
                    elif _target_kind == 'alpha':
                        alpha_per_elem = alpha[T_conn].mean(dim=1)
                        loss_sup = supervised_dict['fem_sup'].alpha_supervised_loss(
                            alpha_per_elem,
                            cycle_idx=supervised_dict['cycle_idx'],
                            pidl_centroids=supervised_dict['pidl_centroids'],
                            lambda_sup=supervised_dict['lambda'],
                            loss_kind=supervised_dict.get('loss_kind', 'mse_lin'),
                            mask=supervised_dict.get('mask', None))
                    else:
                        raise ValueError(f"unknown supervised target_kind={_target_kind!r}; expected 'psi' or 'alpha'")
                    # Scale up to compensate for the missed epochs
                    loss = loss + _every_n * loss_sup

            # ★ 2026-05-07 Soft mirror-symmetry penalty (B path)
            if symmetry_dict is not None and symmetry_dict.get('enable', False):
                loss_sym = _compute_symmetry_penalty(
                    field_comp, inp_train,
                    lam_alpha=symmetry_dict.get('lambda_alpha', 1.0),
                    lam_u    =symmetry_dict.get('lambda_u',     1.0),
                    lam_v    =symmetry_dict.get('lambda_v',     1.0))
                loss = loss + loss_sym
                if writer is not None:
                    writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_sym', loss_sym.item(), epoch)

            # ★ 2026-05-08 Soft side-traction penalty
            if side_traction_dict is not None and side_traction_dict.get('enable', False):
                loss_strac = _compute_side_traction_penalty(
                    field_comp, matprop,
                    lam_xx    =side_traction_dict.get('lam_xx',    1.0),
                    lam_xy    =side_traction_dict.get('lam_xy',    1.0),
                    sigma_ref =side_traction_dict.get('sigma_ref', 1.0),
                    n_bdy_pts =side_traction_dict.get('n_bdy_pts', 51))
                loss = loss + loss_strac
                if writer is not None:
                    writer.add_scalar('U_p_'+str(field_comp.lmbda.item())+'/loss_strac', loss_strac.item(), epoch)

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
