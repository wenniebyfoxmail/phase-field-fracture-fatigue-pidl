"""
=============================================================================
network.py - 神经网络架构
=============================================================================
学习顺序: 3️⃣ 理解了物理模型后，学习网络架构

本文件定义了论文中使用的神经网络架构，关键创新包括：
1. TrainableReLU：可训练系数的ReLU激活函数（论文核心创新）
2. 单一网络同时输出位移和相场（促进耦合学习）
3. Xavier初始化

参考论文第3.2节: "Construction and training of the NN"
=============================================================================
"""

import torch
import torch.nn as nn
import numpy as np
import warnings

# =============================================================================
# 激活函数类
# =============================================================================

class SteepTanh(nn.Module):
    """
        陡峭Tanh激活函数

        公式: σ(x) = tanh(coeff × x)

        当 coeff > 1 时，函数变得更陡峭，梯度更集中在原点附近
        当 coeff = 1 时，等同于标准tanh

        注意：论文发现tanh激活会导致能量面缺少屏障，
        从而无法阻止裂纹向错误方向传播（见论文Appendix B）
    """

    def __init__(self, coeff):
        super(SteepTanh, self).__init__()
        self.coeff = coeff
        
    def forward(self, x):
        activation = nn.Tanh()
        return activation(self.coeff*x)
    
class SteepReLU(nn.Module):
    """
        陡峭ReLU激活函数

        公式: σ(x) = max(0, coeff × x)

        与标准ReLU相比，输出被放大了coeff倍

        参数：
        ------
        coeff : float
            放大系数，固定不可训练
        """
    def __init__(self, coeff):
        super(SteepReLU, self).__init__()
        self.coeff = coeff
        
    def forward(self, x):
        activation = nn.ReLU()
        return activation(self.coeff*x)
    
class TrainableTanh(nn.Module):
    """
        可训练系数的Tanh激活函数

        公式: σ(x) = tanh(m × x)

        其中 m 是可学习参数，会在训练中自动调整 coeff
        """
    def __init__(self, init_coeff):
        super(TrainableTanh, self).__init__()
        self.coeff = nn.Parameter(torch.tensor(init_coeff))
    def forward(self, x):
        activation = nn.Tanh()
        return activation(self.coeff*x)
    
class TrainableReLU(nn.Module):
    """
    可训练系数的ReLU激活函数 ⭐ 论文核心创新

    公式（论文公式24）:
        z_{k+1} = max{0, m_k × (W_k × z_k + b_k)}

    关键特点：
    1. 每一层有自己的可训练系数 m_k
    2. 在初始化时设置 m_k = m_0（统一初始值）
    3. 训练时 m_k 会自动调整，但论文发现变化不大
    4. 选择合适的 m_0 对学习关键加载非常重要

    推荐设置（论文4.1节）：
    - L型板裂纹萌生: m_0 = 2
    - 其他2D问题: m_0 = 3

    物理意义：
    - m_k 控制激活函数的"陡峭程度"
    - 较大的 m_k 可以帮助网络学习更尖锐的应力集中
    """
    def __init__(self, init_coeff):
        super(TrainableReLU, self).__init__()
        # nn.Parameter 使 coeff 成为可训练参数！
        self.coeff = nn.Parameter(torch.tensor(init_coeff))

    def forward(self, x):
        activation = nn.ReLU()
        return activation(self.coeff*x)  # 乘以可学习系数
    
# =============================================================================
# 神经网络主体
# =============================================================================


class NeuralNet(nn.Module):
    """
        全连接前馈神经网络（多层感知机）

        网络结构：
            Input(2) → Hidden_1(400) → ... → Hidden_8(400) → Output(3)
                            ↓                      ↓
                       Activation             Activation

        输入: (x, y) 坐标，2维
        输出: (û, v̂, α̂) 原始网络输出，3维
              - û, v̂: 位移分量的原始输出（需要后处理满足BC）
              - α̂: 相场的原始输出（需要约束到[0,1]）

        论文推荐配置：
        - hidden_layers: 8（2D问题）或4（1D问题）
        - neurons: 400（2D问题）或50（1D问题）
        - activation: 'TrainableReLU'
        - init_coeff: 2.0 或 3.0

        参数：
        ------
        input_dimension : int
            输入维度（2D问题为2，1D问题为1）
        output_dimension : int
            输出维度（2D: 3，1D: 2）
        n_hidden_layers : int
            隐藏层数量
        neurons : int
            每个隐藏层的神经元数
        activation : str
            激活函数类型: 'SteepTanh', 'SteepReLU', 'TrainableTanh', 'TrainableReLU'
        init_coeff : float
            激活函数的初始系数
        """

    def __init__(self, input_dimension, output_dimension, n_hidden_layers, neurons, activation, init_coeff=1.0):
        super(NeuralNet, self).__init__()

        # 保存配置
        self.input_dimension = input_dimension
        self.output_dimension = output_dimension
        self.neurons = neurons
        self.n_hidden_layers = n_hidden_layers

        # Activation function
        self.name_activation = activation
        self.init_coeff = init_coeff
        self.trainable_activation = False # 标记激活函数是否可训练

        # =====================================================================
        # 构建网络层
        # =====================================================================

        # 输入层: input_dim → neurons
        self.input_layer = nn.Linear(self.input_dimension, self.neurons)

        # 隐藏层: neurons → neurons (重复 n_hidden_layers-1 次)
        self.hidden_layers = nn.ModuleList([nn.Linear(self.neurons, self.neurons) for _ in range(n_hidden_layers - 1)])

        # 输出层: neurons → output_dim
        self.output_layer = nn.Linear(self.neurons, self.output_dimension)

        # 激活函数
        self.activations, self.trainable_activation = activations(activation, init_coeff, n_hidden_layers)

    def forward(self, x):
        if self.trainable_activation:
            # 每一层使用独立的可训练激活函数
            x = self.activations[0](self.input_layer(x))
            for j, l in enumerate(self.hidden_layers):
                x = self.activations[j+1](l(x))
            return self.output_layer(x)
        else:
            # 所有层共享同一个激活函数
            x = self.activations(self.input_layer(x))
            for j, l in enumerate(self.hidden_layers):
                x = self.activations(l(x))
            # 输出层不使用激活函数
            return self.output_layer(x)


# ★ 2026-05-11 C10: Fourier feature input wrapper for spectral-bias mitigation.
#   Anchor: Tancik et al. 2020 NeurIPS; Xu et al. 2025 JCP review §4.2.
#   γ(x) = [cos(2π B·x), sin(2π B·x)],  B ∈ R^{n_features × input_dim},  B_ij ~ N(0, σ²)
#   Effective frequencies covered: up to ~σ·5 (Gaussian 5σ tail).
#   For our problem: FEM peak width ~ h_FEM = 0.001 (toy units, domain [-0.5, 0.5]),
#                    frequency 1/h ≈ 1000 → set σ so 2π·σ·5 ≈ 1000 → σ ≈ 30-100.
#   Per Xu 2025 review, the canonical formulation; σ choice is the only hyperparameter.
class FourierFeatureNet(nn.Module):
    """Wrap NeuralNet with a frozen random Fourier feature input layer.

    Input dim 2 → 2·n_features (after sin/cos expansion).
    NN inner layers see the expanded representation; output unchanged.

    Args:
      input_dimension : int   spatial input dim (2 for SENT)
      output_dimension : int  NN output channels (3 for u_x, u_y, α)
      n_features : int        number of Fourier frequencies (after expansion = 2·n_features)
      sigma : float           standard deviation of B; sets effective frequency band
      ...                     other args forwarded to inner NeuralNet
    """

    def __init__(self, input_dimension, output_dimension, n_hidden_layers, neurons,
                 activation, init_coeff=1.0, n_features=128, sigma=30.0, seed=0):
        super().__init__()
        self.input_dimension = input_dimension
        self.output_dimension = output_dimension
        self.n_features = n_features
        self.sigma = sigma
        # Sample B once at init, register as buffer (frozen, moves with .to(device))
        g = torch.Generator()
        g.manual_seed(seed)
        B = sigma * torch.randn(n_features, input_dimension, generator=g)
        self.register_buffer('B', B)
        # Inner NN takes 2·n_features input
        self.inner = NeuralNet(2 * n_features, output_dimension, n_hidden_layers,
                               neurons, activation, init_coeff)
        # Expose introspection attributes used by init_xavier and outer code
        self.name_activation = self.inner.name_activation
        self.trainable_activation = self.inner.trainable_activation
        self.init_coeff = self.inner.init_coeff
        # Also expose layer attrs so init_xavier's `init_weights` traversal finds nn.Linear
        # (init_xavier calls self.apply(init_weights); since FourierFeatureNet wraps
        # NeuralNet, .apply walks into inner.* sub-modules and gets all Linear layers)

    def forward(self, x):
        # x: (N, input_dimension) e.g. (N, 2)
        proj = 2.0 * torch.pi * (x @ self.B.T)            # (N, n_features)
        feat = torch.cat([torch.cos(proj), torch.sin(proj)], dim=-1)  # (N, 2·n_features)
        return self.inner(feat)


# =============================================================================
# 辅助函数
# =============================================================================
def activations(activation, init_coeff, n_hidden_layers=1):
    """
        创建激活函数实例

        参数：
        ------
        activation : str
            激活函数类型
        init_coeff : float
            初始系数
        n_hidden_layers : int
            隐藏层数量（用于可训练激活函数）

        返回：
        ------
        activations : nn.Module or nn.ModuleList
            激活函数实例
        trainable_activation : bool
            是否是可训练激活函数
        """
    if activation == 'SteepTanh':
        activations = SteepTanh(init_coeff)
        trainable_activation = False
    elif activation == 'SteepReLU':
        activations = SteepReLU(init_coeff)
        trainable_activation = False
    elif activation == 'TrainableTanh':
        activations = nn.ModuleList([TrainableTanh(init_coeff) for _ in range(n_hidden_layers)])
        trainable_activation = True
    elif activation == 'TrainableReLU':
        activations = nn.ModuleList([TrainableReLU(init_coeff) for _ in range(n_hidden_layers)])
        trainable_activation = True
    else:
        warnings.warn('Prescribed activation does not match the available choices. The default activation Tanh is in use.')
        activations = nn.Tanh()
        trainable_activation = False

    return activations, trainable_activation


class SplitUVAlphaNet(nn.Module):
    """
    ★ 2026-05-14 C8 v1 (uv_only): two-headed NN to isolate SDF embedding effect.

    uv-net    : input (x, y, γ) → output (u_raw, v_raw)
    alpha-net : input (x, y)    → output (α_raw,)

    Why: the SDF ribbon γ is meant to give the NN a strong displacement
    discontinuity feature. Feeding γ to the α head (all-head v2) lets α
    "lock onto" the γ jump and over-localize → V4 d-skew failure mode.
    The split keeps the experiment as a clean test of "does giving u-field
    a discontinuity prior help reproduce ψ⁺-tip and downstream α-evolution",
    without conflating with "α also sees the prior".

    Output contract: concatenated (u_raw, v_raw, α_raw) shape (N, 3) so the
    downstream FieldComputation contract is unchanged.

    Caller is responsible for init (init_xavier on each sub-net separately
    — `name_activation` and `init_coeff` live on NeuralNet, not on this wrapper).
    """
    def __init__(self, uv_net, alpha_net):
        super().__init__()
        self.uv_net    = uv_net
        self.alpha_net = alpha_net

    def forward(self, inp_with_gamma):
        # inp_with_gamma shape (N, 3): columns [x, y, γ]
        uv = self.uv_net(inp_with_gamma)            # (N, 2)
        xy = inp_with_gamma[:, 0:2]                 # (N, 2) — drop γ for α head
        a  = self.alpha_net(xy)                     # (N, 1)
        return torch.cat([uv, a], dim=1)            # (N, 3)


def init_xavier(model):
    """
        Xavier初始化

        根据激活函数类型选择合适的增益(gain)：
        - ReLU: 使用 leaky_relu 增益
        - Tanh: 使用 tanh 增益

        Xavier初始化的目的是保持各层的方差稳定，
        防止梯度消失或爆炸。

        论文使用Xavier uniform初始化，并将偏置初始化为0。
        """
    # 使用 Xavier 初始化来设置网络权重的初始值。这种方法让信号能够稳定地在深层网络中传播，避免梯度消失或爆炸。
    activation = model.name_activation
    init_coeff = model.init_coeff
    def init_weights(m):
        if type(m) == nn.Linear and m.weight.requires_grad and m.bias.requires_grad:
            if activation == 'TrainableReLU' or activation == 'SteepReLU':
                # ReLU类激活函数的增益计算
                # 使用 leaky_relu 增益近似
                g = nn.init.calculate_gain('leaky_relu', np.sqrt(init_coeff**2-1.0))
                torch.nn.init.xavier_uniform_(m.weight, gain=g)
                # torch.nn.init.xavier_normal_(m.weight, gain=g)
                m.bias.data.fill_(0)

            if activation == 'TrainableTanh' or activation == 'SteepTanh':
                g = nn.init.calculate_gain('tanh')/init_coeff
                torch.nn.init.xavier_uniform_(m.weight, gain=g)
                # torch.nn.init.xavier_normal_(m.weight, gain=g)
                m.bias.data.fill_(0)

    model.apply(init_weights)

