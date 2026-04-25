import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm

from compute_energy import compute_energy, gradients, strain_energy_with_split


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
        supervised_dict=None):
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

                # ★ MIT-8 supervised term (Apr 25): joint physics + FEM ψ⁺ supervision
                if supervised_dict is not None and supervised_dict.get('lambda', 0.0) > 0:
                    psi_raw_pidl = _compute_psi_raw_per_elem(
                        inp_train, u, v, alpha, matprop, pffmodel, area_T, T_conn)
                    loss_sup = supervised_dict['fem_sup'].supervised_loss(
                        psi_raw_pidl,
                        cycle_idx=supervised_dict['cycle_idx'],
                        pidl_centroids=supervised_dict['pidl_centroids'],
                        lambda_sup=supervised_dict['lambda'],
                        loss_kind=supervised_dict.get('loss_kind', 'mse_log'))
                    loss = loss + loss_sup

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
                            supervised_dict=None):
    # ★ MIT-8 supervised_dict (Apr 25, optional, default None → identical behavior):
    #    {'fem_sup': FEMSupervision, 'cycle_idx': int, 'lambda': float,
    #     'pidl_centroids': np.ndarray, 'loss_kind': 'mse_log'|'mse_lin'|'mse_rel'}
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

            # ★ MIT-8 supervised term (Apr 25): joint physics + FEM ψ⁺ supervision
            if supervised_dict is not None and supervised_dict.get('lambda', 0.0) > 0:
                psi_raw_pidl = _compute_psi_raw_per_elem(
                    inp_train, u, v, alpha, matprop, pffmodel, area_T, T_conn)
                loss_sup = supervised_dict['fem_sup'].supervised_loss(
                    psi_raw_pidl,
                    cycle_idx=supervised_dict['cycle_idx'],
                    pidl_centroids=supervised_dict['pidl_centroids'],
                    lambda_sup=supervised_dict['lambda'],
                    loss_kind=supervised_dict.get('loss_kind', 'mse_log'))
                loss = loss + loss_sup

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
