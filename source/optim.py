import torch.optim as optim
import numpy as np

def get_optimizer(params, optimizer_type: str="LBFGS"):
    if optimizer_type == "LBFGS":
        # ★ Direction 5: tolerance_change 放宽到 1e-7
        # 原值 ≈ 2.22e-16（np.finfo(float).eps）过严，高维输入/富集参数下
        # LBFGS 可能永不满足退出条件导致预训练卡住（Fourier 实验亦确认 1e-7 必要）
        optimizer = optim.LBFGS(params, lr=float(0.5), max_iter=20000, max_eval=20000000, history_size=250,
                             line_search_fn="strong_wolfe",
                             tolerance_change=1e-7, tolerance_grad=1.0*np.finfo(float).eps)
    elif optimizer_type == "ADAM":
        optimizer = optim.Adam(params, lr=5e-4, betas=(0.9, 0.999), eps=1.0*np.finfo(float).eps, weight_decay=0)
    elif optimizer_type == "RPROP":
        optimizer = optim.Rprop(params, lr=1e-5, step_sizes=(1e-10, 50))
    else:
        raise ValueError("Optimizer type not recognized. Please choose from LBFGS, ADAM, RPROP.")
    return optimizer



