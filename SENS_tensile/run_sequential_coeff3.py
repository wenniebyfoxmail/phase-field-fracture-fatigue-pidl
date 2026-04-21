#!/usr/bin/env python3
"""
run_sequential_coeff3.py — 串行跑 coeff=3.0 下 Umax={0.11, 0.10, 0.09, 0.08}
其他参数与 Umax=0.12 baseline 完全一致:
  hl=8, Neurons=400, Seed=1, TrainableReLU, AT1, carrara/asym, aT=0.5, R=0.0

每个 case 有自动断裂检测（crack_length >= 0.46 + E_el 下降）会提前停止，
所以 n_cycles 仅为上限。

用法（在 SENS_tensile/ 目录下）:
  nohup python run_sequential_coeff3.py > run_sequential_coeff3.log 2>&1 &
"""

import sys
import numpy as np
import torch
from pathlib import Path
from torch.utils.tensorboard import SummaryWriter

SCRIPT_DIR = Path(__file__).parent
SOURCE_DIR = SCRIPT_DIR.parent / 'source'
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SOURCE_DIR))

from field_computation import FieldComputation
from construct_model   import construct_model
from model_train       import train

# ── 固定参数（与 Umax=0.12 baseline 一致，仅 init_coeff 改为 3.0）──────────────
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"device: {device}")

network_dict = {
    "model_type"  : 'MLP',
    "hidden_layers": 8,
    "neurons"     : 400,
    "seed"        : 1,
    "activation"  : 'TrainableReLU',
    "init_coeff"  : 3.0,              # ★ coeff=3
}
optimizer_dict = {
    "weight_decay"         : 1e-5,
    "n_epochs_RPROP"       : 10000,
    "n_epochs_LBFGS"       : 0,
    "optim_rel_tol_pretrain": 1e-6,
    "optim_rel_tol"        : 5e-7,
}
training_dict  = {"save_model_every_n": 100}
PFF_model_dict = {"PFF_model": 'AT1', "se_split": 'volumetric', "tol_ir": 5e-3}
mat_prop_dict  = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
numr_dict      = {"alpha_constraint": 'nonsmooth', "gradient_type": 'numerical'}

domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
loading_angle  = torch.tensor([np.pi / 2])
crack_dict     = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}

coarse_mesh_file = str(SCRIPT_DIR / 'meshed_geom1.msh')
fine_mesh_file   = str(SCRIPT_DIR / 'meshed_geom2.msh')

williams_dict = {"enable": False, "theta_mode": "atan2", "r_min": 1e-6}

# ── Case 定义 ─────────────────────────────────────────────────────────────────
CASES = [
    {"disp_max": 0.12, "n_cycles": 300},   # 与 coeff=1.0 baseline 对标
    {"disp_max": 0.11, "n_cycles": 300},
    {"disp_max": 0.10, "n_cycles": 400},
    {"disp_max": 0.09, "n_cycles": 500},
    {"disp_max": 0.08, "n_cycles": 600},
]

# ── 路径生成（与 config.py 命名规则完全一致）─────────────────────────────────
def make_fatigue_dict(disp_max, n_cycles):
    return {
        "fatigue_on"             : True,
        "loading_type"           : "cyclic",
        "n_cycles"               : n_cycles,
        "disp_max"               : disp_max,
        "R_ratio"                : 0.0,
        "accum_type"             : "carrara",
        "n_power"                : 2.0,
        "alpha_n"                : 0.1,
        "degrad_type"            : "asymptotic",
        "fracture_E_drop_ratio"  : 0.1,
        "fracture_confirm_cycles": 10,
        "crack_length_threshold" : 0.46,
        "x_tip_alpha_thr"        : 0.90,
        "plot_every_n_cycles"    : 20,
        "alpha_T"                : 0.5,
        "kappa"                  : 1.0,
        "tip_weight_cfg"         : {"enable": False, "beta": 2.0, "power": 1.0, "start_cycle": 1},
    }

def make_model_path(fatigue_dict):
    _fat = fatigue_dict
    tag = (f"_fatigue_on"
           f"_{_fat['accum_type']}"
           f"_{_fat['degrad_type'][:3]}"
           f"_aT{_fat['alpha_T']}"
           f"_N{_fat['n_cycles']}"
           f"_R{_fat['R_ratio']}"
           f"_Umax{_fat['disp_max']}")
    name = (f"hl_{network_dict['hidden_layers']}"
            f"_Neurons_{network_dict['neurons']}"
            f"_activation_{network_dict['activation']}"
            f"_coeff_{network_dict['init_coeff']}"
            f"_Seed_{network_dict['seed']}"
            f"_PFFmodel_{PFF_model_dict['PFF_model']}"
            f"_gradient_{numr_dict['gradient_type']}"
            f"{tag}")
    return SCRIPT_DIR / name

# ── 主循环 ────────────────────────────────────────────────────────────────────
for case_cfg in CASES:
    disp_max = case_cfg["disp_max"]
    n_cycles = case_cfg["n_cycles"]

    fatigue_dict = make_fatigue_dict(disp_max, n_cycles)
    model_path   = make_model_path(fatigue_dict)
    trainedModel_path      = model_path / 'best_models'
    intermediateModel_path = model_path / 'intermediate_models'
    model_path.mkdir(parents=True, exist_ok=True)
    trainedModel_path.mkdir(parents=True, exist_ok=True)
    intermediateModel_path.mkdir(parents=True, exist_ok=True)

    with open(model_path / 'model_settings.txt', 'w') as f:
        f.write(f"hidden_layers: {network_dict['hidden_layers']}\n")
        f.write(f"neurons: {network_dict['neurons']}\n")
        f.write(f"seed: {network_dict['seed']}\n")
        f.write(f"activation: {network_dict['activation']}\n")
        f.write(f"coeff: {network_dict['init_coeff']}\n")
        f.write(f"PFF_model: {PFF_model_dict['PFF_model']}\n")
        f.write(f"se_split: {PFF_model_dict['se_split']}\n")
        f.write(f"gradient_type: {numr_dict['gradient_type']}\n")
        f.write(f"device: {device}\n")
        f.write("--- fatigue ---\n")
        for k, v in fatigue_dict.items():
            f.write(f"{k}: {v}\n")
        f.write("--- williams ---\n")
        for k, v in williams_dict.items():
            f.write(f"williams_{k}: {v}\n")

    writer = SummaryWriter(log_dir=str(model_path / 'TBruns'))

    print(f"\n{'='*60}")
    print(f"Starting: Umax={disp_max}, n_cycles={n_cycles}, coeff={network_dict['init_coeff']}")
    print(f"Output  : {model_path.name}")
    print(f"{'='*60}\n", flush=True)

    disp_cyclic = np.ones(n_cycles) * disp_max

    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
        williams_dict=williams_dict)
    field_comp = FieldComputation(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.0], device=device),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=williams_dict,
        l0=mat_prop_dict["l0"])
    field_comp.net            = field_comp.net.to(device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(device)
    field_comp.theta          = field_comp.theta.to(device)

    train(field_comp, disp_cyclic, pffmodel, matprop, crack_dict, numr_dict,
          optimizer_dict, training_dict, coarse_mesh_file, fine_mesh_file,
          device, trainedModel_path, intermediateModel_path, writer,
          fatigue_dict=fatigue_dict)

    writer.close()
    print(f"\nFinished: Umax={disp_max}\n", flush=True)

print("\nAll cases complete.")
