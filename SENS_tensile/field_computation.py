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
    l0: float
        相场长度参数，用于特征无量纲化（默认 0.01）

    fieldCalculation: applies BCs and constraint on alpha (needs to be customized for each problem)
    update_hist_alpha: alpha_field for use in the next loading step to enforce irreversibility
    '''
    def __init__(self, net, domain_extrema, lmbda, theta,
                 alpha_constraint='nonsmooth',
                 williams_dict=None,
                 l0=0.01):
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

        if alpha_constraint == 'smooth':
            self.alpha_constraint = torch.sigmoid
        else:
            self.alpha_constraint = NonsmoothSigmoid(2.0, 1e-3)

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
        else:
            inp_nn = inp   # 原始行为，无开销

        out = self.net(inp_nn)     # 神经网络输出（8D 或 2D 输入）
        out_disp = out[:, 0:2]    # 位移部分

        # 约束相场在 [0, 1] 范围内
        alpha = self.alpha_constraint(out[:, 2])

        # 边界条件强制（使用物理坐标 inp，不受 Williams 特征影响）
        # (y-y0)(yL-y) 在边界 y=y0 和 y=yL 处为 0
        u = ((inp[:, -1]-y0)*(yL-inp[:, -1])*out_disp[:, 0] +
             (inp[:, -1]-y0)/(yL-y0)*torch.cos(self.theta)) * self.lmbda
        v = ((inp[:, -1]-y0)*(yL-inp[:, -1])*out_disp[:, 1] +
             (inp[:, -1]-y0)/(yL-y0)*torch.sin(self.theta)) * self.lmbda

        return u, v, alpha
    
    def update_hist_alpha(self, inp):
        _, _, pred_alpha = self.fieldCalculation(inp)
        pred_alpha = pred_alpha.detach()
        return pred_alpha
    

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