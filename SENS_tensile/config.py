import numpy as np
import torch
from pathlib import Path
import sys
from torch.utils.tensorboard import SummaryWriter




'''
## ############################################################################
Refer to the paper 
"Phase-field modeling of fracture with physics-informed deep learning"
for details of the model.
## ############################################################################

'''

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(device)



## ############################################################################
## customized for each problem ################################################
## ############################################################################
'''
network_dict:
parameters to construct an MLP
seed: seed to initialize the network
activation: choose from {SteepTanh, SteepReLU, TrainableTanh, TrainableReLU}
init_coeff: initial coefficient in activation function 
setting init_coeff = 1 in SteepTanh/SteepReLU gives standard Tanh/ReLU activation
'''

network_dict = {"model_type": 'MLP',
                "hidden_layers": int(sys.argv[1]) if len(sys.argv) > 1 else 6,
                "neurons": int(sys.argv[2]) if len(sys.argv) > 2 else 100,
                "seed": int(sys.argv[3]) if len(sys.argv) > 3 else 1,
                "activation": str(sys.argv[4]) if len(sys.argv) > 4 else 'TrainableReLU',
                "init_coeff": float(sys.argv[5]) if len(sys.argv) > 5 else 1.0}

'''
optimizer_dict:
weight_decay: weighing of neural network weight regularization
optim_rel_tol_pretrain: relative tolerance of loss in pretraining as an stopping criteria
optim_rel_tol: relative tolerance of loss in main training as an stopping criteria
'''

optimizer_dict = {"weight_decay": 1e-5,
                  "n_epochs_RPROP": 10000,
                  "n_epochs_LBFGS": 0,
                  "optim_rel_tol_pretrain": 1e-6,
                  "optim_rel_tol": 5e-7}


# save intermediate model during training every "save_model_every_n" steps
training_dict = {"save_model_every_n": 100}

'''
numr_dict:
"alpha_constraint" in {'nonsmooth', 'smooth'}
"gradient_type" in {'numerical', 'autodiff'}

PFF_model_dict:
PFF_model in {'AT1', 'AT2'} 
se_split in {'volumetric', None}
tol_ir: irreversibility tolerance

mat_prop_dict:
w1: Gc/l0, where Gc is energy release rate.
In the normalized formulation, mat_E=1, w1=1, and only nu and l0 are the properties to be set.
'''
numr_dict = {"alpha_constraint": 'nonsmooth', "gradient_type": 'numerical'}
PFF_model_dict = {"PFF_model" : 'AT1', "se_split" : 'volumetric', "tol_ir" : 5e-3}
mat_prop_dict = {"mat_E" : 1.0, "mat_nu" : 0.3, "w1" : 1.0, "l0" : 0.01}

# ★ 新增：疲劳参数字典（所有新功能均可独立开关）
# -------------------------------------------------------------------------
# 总开关  fatigue_on=False → f_fatigue ≡ 1.0，完全等价 Manav 原始代码
# -------------------------------------------------------------------------
fatigue_dict = {
    # ── 总开关 ──────────────────────────────────────────────────────────────
    "fatigue_on"   : True,           # True: 开启疲劳 | False: 恢复 Manav 原始

    # ── 加载方式（fatigue_on=True 时生效）───────────────────────────────────
    "loading_type" : "cyclic",     # 'monotonic': 单调加载（Case C 验证用）
                                     # 'cyclic'   : 循环加载（Case D 疲劳模拟）

    # ── 循环加载参数 ─────────────────────────────────────────────────────────
    "n_cycles"     : 300,           # Direction3 对比：与 baseline 8×400 seed=1 Umax=0.12 N300 一致
    "disp_max"     : 0.12,          # 峰值位移振幅（Umax=0.12）
    "R_ratio"      : 0.0,            # 应力比 R = σ_min/σ_max；R=0 → 拉-拉循环

    # ── 历史变量累积策略 ─────────────────────────────────────────────────────
    "accum_type"   : "carrara",      # 'carrara'  → Carrara Eq.39：线性累积 Δᾱ = H(Δψ⁺)·Δψ⁺
                                     # 'golahmar' → Golahmar Eq.31：幂律累积

    # Golahmar 幂律参数（accum_type='golahmar' 时有效）
    "n_power"      : 2.0,            # 幂律指数 n；控制 S-N 斜率（n=1 退化为 Carrara）
    "alpha_n"      : 0.1,            # 归一化能量密度 αₙ（与 ψ⁺ 量纲相同）

    # ── 疲劳退化函数类型 ─────────────────────────────────────────────────────
    "degrad_type"  : "asymptotic",   # 'asymptotic'  → Carrara Eq.41：f=[2α_T/(ᾱ+α_T)]²（永不到0）
                                     # 'logarithmic' → Carrara Eq.42：f=[1-κ·log10(ᾱ/α_T)]²（有限步归零）

    # ── 断裂检测参数（cyclic 模式自动停止）─────────────────────────────────
    # Run #4 fix: Williams 等易产生 NN 数值尖峰的实验下 E_el fallback 不可靠
    # （cycle 58 尖峰让 cycle 69 错停；主判据 α>0.95@boundary 未误触）
    # SENT 几何主判据已足够，关掉 fallback。其他几何或 baseline 需要时打开。
    "enable_E_fallback"      : False, # False: 只用主判据（α>0.95@boundary）| True: 保留 E_el fallback
    "fracture_E_drop_ratio"  : 0.1,  # E_el < ratio × E_el_max 时触发检测（仅 enable_E_fallback=True 时生效）
    "fracture_confirm_cycles": 10,   # 触发后再观察 N 圈确认（防数值扰动）
    "crack_length_threshold" : 0.46, # 裂缝贯通判据：crack_length >= 此值 → 停止
                                     # 定义：L∞ 距离 = max(|Δx|, |Δy|) from crack_mouth=(0,0)
                                     # 等价于：x 或 y 方向投影任意一个达到 92% × 0.5
                                     # 适用于任意裂缝路径（水平/斜/剪切），无需预设方向
    "x_tip_alpha_thr"        : 0.90, # α > 此值认为是裂缝带内
    "plot_every_n_cycles"    : 20,   # 每 N 圈保存一张 α 场快照

    # ── 疲劳阈值 ────────────────────────────────────────────────────────────
    "alpha_T"      : 0.5,            # 疲劳阈值（归一化）；ᾱ > α_T 时 f 开始下降
                                     # 推导：GRIPHFiTH α_T/ψ_c ≈ 0.25
                                     #       Manav AT1 ψ_c ≈ w1/(8*l0)*(3/8*sqrt(3/8))...
                                     #       近似取 α_T = 0.25 × (3w1/16) ≈ 0.047；
                                     #       建议调参范围：0.05 ~ 0.5

    # ── 对数退化参数（degrad_type='logarithmic' 时有效）────────────────────
    "kappa"        : 1.0,            # κ > 0；控制疲劳寿命上限：ᾱ_max = α_T·10^(1/κ)

    # ── 方向3：裂尖自适应损失加权（Crack-Tip Adaptive Loss Weighting）─────
    # 原理：w_e = 1 + β·(ψ⁺_e / ψ⁺_mean)^p
    #   裂尖 ψ⁺ 高 → w_e 大 → 该单元损失贡献增大 → NN 分配更多表达能力
    # enable=False 时完全等价原始行为（crack_tip_weights=None）
    "tip_weight_cfg": {
        "enable"      : False,       # Direction 3 负结果 → 已关闭；True 时追加 _tipw_ 目录标签
        "beta"        : 2.0,         # 加权强度；beta=0 → 均匀；推荐范围 1~5
        "power"       : 1.0,         # ψ⁺ 比值的幂次；1.0 = 线性加权；2.0 = 平方增强
        "start_cycle" : 1,           # 从第几圈开始加权（0 = 从预训练完成后第1圈就加权）
    },
}

# ★ Direction 4: Williams 裂尖增强输入特征
# ────────────────────────────────────────────────────────────────────────────
# 背景：PIDL Kt≈7 vs FEM Kt≈15 → 根因：MLP 谱偏差无法表示 r^(1/2) 奇异性
# 方案：将 Williams 展开基函数作为 NN 附加输入特征（8D 标准集）
#   [x, y, √(r/l₀), r/l₀, sin(θ/2), cos(θ/2), sin(3θ/2), cos(3θ/2)]
# 关键：只改输入特征，不改 Deep Ritz 能量泛函 → 安全（不重蹈 Direction 3 覆辙）
# ────────────────────────────────────────────────────────────────────────────
williams_dict = {
    "enable"     : True,         # True: 启用 8D 特征; False: 原始 2D（完全等价 baseline）
    "theta_mode" : "atan2",      # θ = atan2(dy, dx) ∈ (-π, π]（预留接口，未来可扩展）
    "r_min"      : 1e-6,         # r 下限，防止裂尖节点处除零
}


# Domain definition
'''
domain_extrema: tensor([[x_min, x_max], [y_min, y_max]])
x_init: list of x-coordinates of one end of cracks
y_init: list of y-coordinates of one end of cracks
L_crack: list of crack lengths
angle_crack: list of angles of cracks from the x-axis with the origin shifted to (x_init[i], y_init[i])
'''
domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
crack_dict = {"x_init" : [-0.5], "y_init" : [0], "L_crack" : [0.5], "angle_crack" : [0]}


# Prescribed incremental displacement
loading_angle = torch.tensor([np.pi/2])

# ── 单调加载（Manav 原始 / fatigue_on=False 验证用）────────────────────────
disp = np.concatenate((np.linspace(0.0, 0.075, 4), np.linspace(0.1, 0.2, 21)), axis=0)
disp = disp[1:]

# ★ 循环加载位移序列（fatigue_on=True + loading_type='cyclic' 时由 main.py 选用）
# 等幅循环：每步幅值均为 disp_max，步数 = n_cycles
# R=0 → 每个"步"代表一个完整的 0→disp_max 峰值（卸载时 ψ⁺ 不累积，无需显式建模）
disp_cyclic = np.ones(fatigue_dict["n_cycles"]) * fatigue_dict["disp_max"]

## ############################################################################
## ############################################################################



## ############################################################################
## Domain discretization ######################################################
## ############################################################################
'''
Current implementation only accepts discretization with triangular elements.
coarse_mesh_file: mesh is fine only where crack is initially present (for efficient pretraining)
fine_mesh_file: fine discretization also where crack is expected to propagate.
'''
coarse_mesh_file = "meshed_geom1.msh"
fine_mesh_file = "meshed_geom2.msh"

## #############################################################################
## #############################################################################




## ############################################################################
## Setting output directory ###################################################
## ############################################################################
PATH_ROOT = Path(__file__).parents[0]

# ★ 疲劳标签：不同 case 保存到不同目录，防止覆盖
# fatigue_on=False → '_fatigue_off'
# fatigue_on=True  → '_fatigue_on_<accum>_<degrad>_aT<alpha_T>_N<n_cycles>'
_fat = fatigue_dict
if not _fat.get("fatigue_on", False):
    _fatigue_tag = "_fatigue_off"
else:
    # ★ 方向3：tip_weight 启用时在目录名追加 _tipw_bβ_pP 标签，便于区分
    _tw_cfg = _fat.get('tip_weight_cfg', {})
    _tipw_tag = (
        f"_tipw_b{_tw_cfg.get('beta',2.0)}_p{_tw_cfg.get('power',1.0)}"
        if _tw_cfg.get('enable', False) else ""
    )
    _fatigue_tag = (
        f"_fatigue_on"
        f"_{_fat.get('accum_type','carrara')}"
        f"_{_fat.get('degrad_type','asymptotic')[:3]}"   # asym/log 缩写
        f"_aT{_fat.get('alpha_T',0.094)}"
        f"_N{_fat.get('n_cycles',50)}"
        f"_R{_fat.get('R_ratio',0.0)}"
        f"_Umax{_fat.get('disp_max',0.12)}"
        + ("_mono" if _fat.get("loading_type") == "monotonic" else "")
        + _tipw_tag  # ★ 仅 enable=True 时追加，否则为空字符串
        # NOTE: _detLinf 标记在续跑期间注释掉，以保持目录名与 checkpoint 一致
        # 跑完后恢复：f"_detLinf"
    )

# ★ Direction 4: Williams 标签（enable=True 时追加 _williams_std，便于区分 baseline）
_williams_tag = "_williams_std" if williams_dict.get("enable", False) else ""

model_path = PATH_ROOT/Path('hl_'+str(network_dict["hidden_layers"])+
                            '_Neurons_'+str(network_dict["neurons"])+
                            '_activation_'+network_dict["activation"]+
                            '_coeff_'+str(network_dict["init_coeff"])+
                            '_Seed_'+str(network_dict["seed"])+
                            '_PFFmodel_'+str(PFF_model_dict["PFF_model"])+
                            '_gradient_'+str(numr_dict["gradient_type"])+
                            _fatigue_tag +
                            _williams_tag)         # ★ Direction 4 标签追加到路径末尾
model_path.mkdir(parents=True, exist_ok=True)
trainedModel_path = model_path/Path('best_models/')
trainedModel_path.mkdir(parents=True, exist_ok=True)
intermediateModel_path = model_path/Path('intermediate_models/')
intermediateModel_path.mkdir(parents=True, exist_ok=True)

with open(model_path/Path('model_settings.txt'), 'w') as file:
    file.write(f'hidden_layers: {network_dict["hidden_layers"]}')
    file.write(f'\nneurons: {network_dict["neurons"]}')
    file.write(f'\nseed: {network_dict["seed"]}')
    file.write(f'\nactivation: {network_dict["activation"]}')
    file.write(f'\ncoeff: {network_dict["init_coeff"]}')
    file.write(f'\nPFF_model: {PFF_model_dict["PFF_model"]}')
    file.write(f'\nse_split: {PFF_model_dict["se_split"]}')
    file.write(f'\ngradient_type: {numr_dict["gradient_type"]}')
    file.write(f'\ndevice: {device}')
    # ★ 疲劳参数也写入 model_settings.txt
    file.write(f'\n--- fatigue ---')
    file.write(f'\nfatigue_on: {_fat.get("fatigue_on")}')
    file.write(f'\nloading_type: {_fat.get("loading_type")}')
    file.write(f'\nn_cycles: {_fat.get("n_cycles")}')
    file.write(f'\ndisp_max: {_fat.get("disp_max")}')
    file.write(f'\nR_ratio: {_fat.get("R_ratio")}')
    file.write(f'\naccum_type: {_fat.get("accum_type")}')
    file.write(f'\nn_power: {_fat.get("n_power")}')
    file.write(f'\nalpha_n: {_fat.get("alpha_n")}')
    file.write(f'\ndegrad_type: {_fat.get("degrad_type")}')
    file.write(f'\nalpha_T: {_fat.get("alpha_T")}')
    file.write(f'\nkappa: {_fat.get("kappa")}')
    # ★ Direction 4: Williams 特征参数
    file.write(f'\n--- williams ---')
    file.write(f'\nwilliams_enable: {williams_dict.get("enable", False)}')
    file.write(f'\nwilliams_theta_mode: {williams_dict.get("theta_mode", "atan2")}')
    file.write(f'\nwilliams_r_min: {williams_dict.get("r_min", 1e-6)}')

## #############################################################################
## #############################################################################


# logging loss to tensorboard
writer = SummaryWriter(model_path/Path('TBruns'))
