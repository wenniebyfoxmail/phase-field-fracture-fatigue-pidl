"""
fourier_features.py  —  Direction 2.1 Option A Alternative: Random Fourier Features
=======================================================================
将 2D 物理坐标 (x, y) 通过随机高斯投影映射成高频正弦/余弦特征，作为 NN 的附加输入。

物理 / 数学背景
---------------
标准 MLP 因谱偏差（Rahaman et al., ICML 2019）偏向学习低频函数，无法表示
裂尖 r^(1/2) 奇异性，导致 Kt_PIDL ≈ 7 << Kt_FEM ≈ 15。

Tancik 等（NeurIPS 2020）提出："Fourier features let networks learn high
frequency functions in low dimensional domains"。核心做法是把输入坐标 v 映射成

    γ(v) = [sin(2π Bᵀ v), cos(2π Bᵀ v)]

其中 B ∈ R^{2 × n_freq}，每列 b_k ~ N(0, σ² I_2)，σ 控制频率带宽。
理论上等价于一个高斯核 NTK，使 NN 可以无偏学习高频成分。

与 Williams 方案的区别
----------------------
  - Williams：物理先验，提供裂尖渐近场基函数（√r、sin(θ/2) 等），针对性强
  - Fourier ：纯数学先验，提供随机高频投影，无物理偏好，对任意奇异性都有改进
两者互斥（输入特征二选一），通过 config.fourier_dict.enable / williams_dict.enable
独立切换。在 config.py 启动期间用 assert 检查互斥性。

输入特征集
----------
返回维度 = 2 + 2 · n_freq
    [x, y, sin(2π b_1·v), cos(2π b_1·v), …, sin(2π b_{nf}·v), cos(2π b_{nf}·v)]

  - 保留 [x, y]   : 让 NN 仍能学全局低频趋势（Tancik 实现里的标准做法，
                    称为 "concat" 模式，比纯 Fourier 模式更稳定）
  - sin / cos     : 高频投影，每对 (sin, cos) 来自同一个频率向量 b_k

参数选择经验
------------
  - n_freq = 16, σ = 1.0 → 输入维 34，Tancik 论文典型设置（"强力版"）
  - n_freq = 3,  σ = 1.0 → 输入维 8，与 Williams 严格同维（"公平对比版"）
  - σ 太大（>10）会引入过高频噪声，σ 太小（<0.1）退化为线性

参考
----
Tancik, M. et al. (2020). Fourier features let networks learn high frequency
    functions in low dimensional domains. NeurIPS 33.
Rahaman, N. et al. (2019). On the spectral bias of neural networks. ICML.
"""

import math
import torch


def make_fourier_B(n_freq, sigma, seed, device='cpu'):
    """
    生成固定的随机投影矩阵 B ∈ R^{2 × n_freq}，按 seed 复现。

    参数
    ----
    n_freq : int    — 频率向量个数；NN 输入维 = 2 + 2 · n_freq
    sigma  : float  — 高斯标准差；B 的每个元素 ~ N(0, σ²)
    seed   : int    — 固定 B 随机性的种子（独立于 NN 初始化 seed，避免与训练随机性耦合）
    device : str    — 'cpu' 或 'cuda'；返回张量所在设备

    返回
    ----
    B : Tensor, shape (2, n_freq)，dtype=float32
    """
    # 显式用 CPU generator + seed 生成，再迁移到 device
    # 这样无论 device 是 cpu 还是 cuda，结果都完全一致
    g = torch.Generator(device='cpu').manual_seed(int(seed))
    B = torch.randn((2, int(n_freq)), generator=g) * float(sigma)
    return B.to(device)


def compute_fourier_features(inp, B):
    """
    计算 Random Fourier Features 增强的 NN 输入特征。

    参数
    ----
    inp : Tensor, shape (N, 2)        — 节点物理坐标 [x, y]
    B   : Tensor, shape (2, n_freq)   — 固定的随机投影矩阵（make_fourier_B 生成）

    返回
    ----
    inp_nn : Tensor, shape (N, 2 + 2·n_freq)
        [x, y, sin(2π inp·B), cos(2π inp·B)]

    说明
    ----
    - inp @ B 形状 (N, n_freq)；2π 因子是 Tancik 论文 Eq.(2) 的标准写法
    - 保留 inp 在前两维（concat 模式），让 NN 仍可学全局低频
    - B 不参与训练（detach by construction，因为 randn 出来的 leaf 没有 requires_grad）
    """
    # 投影：(N, 2) @ (2, n_freq) → (N, n_freq)
    proj = 2 * math.pi * (inp @ B)
    return torch.cat([inp, proj.sin(), proj.cos()], dim=1)
