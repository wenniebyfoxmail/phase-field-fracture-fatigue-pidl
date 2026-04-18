import torch.optim as optim
import numpy as np

def get_optimizer(params, optimizer_type: str="LBFGS"):
    if optimizer_type == "LBFGS":
        # ★ exp/fourier-feature C1 fix: tolerance_change=eps≈2e-16 让 LBFGS 在
        # 高维输入（Fourier 34D）下永远不退出 — Fourier smoke test 在 loss=-1.93
        # plateau 75+ min 后仍未触发。放宽到 1e-7 后，typical plateau 会立刻退出。
        # 对 Williams（已过 LBFGS）和 baseline（8D）无影响：它们 line search
        # 早就失败退出了，触不到 tolerance 限制。
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



