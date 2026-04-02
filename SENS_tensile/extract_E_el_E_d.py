#!/usr/bin/env python3
"""
extract_E_el_E_d.py — 从已训练模型中提取每步的 E_el 和 E_d

用法:
    cd 'upload code/SENS_tensile'
    python extract_E_el_E_d.py <model_dir>

示例:
    python extract_E_el_E_d.py \
      hl_6_Neurons_100_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_off

逻辑与 plotting.plot_energy() 完全一致:
    - 遍历 best_models/trained_1NN_0.pt ~ trained_1NN_N.pt
    - compute_energy(inp, u, v, alpha, hist_alpha=alpha, ...) → hist 惩罚=0，纯 E_el + E_d
    - 打印每步结果并保存为 best_models/E_el_E_d_vs_Up.npy
"""

import sys
import numpy as np
import torch
from pathlib import Path

# ── 路径设置 ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent                   # upload code/SENS_tensile/
SOURCE_DIR = SCRIPT_DIR.parent / 'source'            # upload code/source/
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SOURCE_DIR))

from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from compute_energy import compute_energy
from field_computation import FieldComputation

# ── 解析参数 ──────────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

model_dir = Path(sys.argv[1])
if not model_dir.is_absolute():
    model_dir = SCRIPT_DIR / model_dir

best_models_dir = model_dir / 'best_models'
print(f"model_dir = {model_dir}")

# ── 模型参数（与 config.py 一致）─────────────────────────────────────────────
device = 'cpu'

network_dict   = {"model_type": 'MLP', "hidden_layers": 6, "neurons": 100,
                  "seed": 1, "activation": 'TrainableReLU', "init_coeff": 1.0}
PFF_model_dict = {"PFF_model": 'AT1', "se_split": 'volumetric', "tol_ir": 5e-3}
mat_prop_dict  = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
numr_dict      = {"alpha_constraint": 'nonsmooth', "gradient_type": 'numerical'}

domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
loading_angle  = torch.tensor([np.pi / 2])
crack_dict     = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
fine_mesh_file = str(SCRIPT_DIR / 'meshed_geom2.msh')

# disp 序列与 config.py 完全一致
disp = np.concatenate((np.linspace(0.0, 0.075, 4), np.linspace(0.1, 0.2, 21)), axis=0)
disp = disp[1:]   # shape (24,): [0.025, 0.05, 0.075, 0.1, 0.105, ..., 0.2]

# ── 构建模型 + 网格 ───────────────────────────────────────────────────────────
pffmodel, matprop, network = construct_model(
    PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device)

inp, T_conn, area_T, hist_alpha = prep_input_data(
    matprop, pffmodel, crack_dict, numr_dict, mesh_file=fine_mesh_file, device=device)

field_comp = FieldComputation(
    net=network, domain_extrema=domain_extrema,
    lmbda=torch.tensor([0.0], device=device),
    theta=loading_angle,
    alpha_constraint=numr_dict["alpha_constraint"])
field_comp.net            = field_comp.net.to(device)
field_comp.domain_extrema = field_comp.domain_extrema.to(device)
field_comp.theta          = field_comp.theta.to(device)

# ── 遍历所有 checkpoint，提取 E_el 和 E_d ────────────────────────────────────
results = []   # list of (U_p, E_el, E_d)

print(f"\n{'Step':<6} {'U_p':<10} {'E_el':<20} {'E_d':<20} {'E_el+E_d'}")
print("-" * 72)

j = 0
while True:
    model_file = best_models_dir / f'trained_1NN_{j}.pt'
    if not model_file.is_file():
        break

    field_comp.net.load_state_dict(
        torch.load(str(model_file), map_location='cpu', weights_only=True))
    field_comp.net.eval()
    field_comp.lmbda = torch.tensor(disp[j], device=device)

    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
        # hist_alpha = alpha：令不可逆惩罚 = 0，与 plot_energy 逻辑一致
        E_el, E_d, _ = compute_energy(
            inp, u, v, alpha, alpha,
            matprop, pffmodel, area_T, T_conn, f_fatigue=1.0)

    E_el_val = float(E_el.item())
    E_d_val  = float(E_d.item())
    U_p      = float(disp[j])

    results.append((U_p, E_el_val, E_d_val))
    print(f"{j:<6} {U_p:<10.4f} {E_el_val:<20.6e} {E_d_val:<20.6e} {E_el_val+E_d_val:.6e}")
    j += 1

# ── 保存结果 ──────────────────────────────────────────────────────────────────
if results:
    arr = np.array(results)   # shape (N, 3): columns = [U_p, E_el, E_d]
    out_path = best_models_dir / 'E_el_E_d_vs_Up.npy'
    np.save(str(out_path), arr)
    print(f"\nSaved: {out_path}  shape={arr.shape}")
    print(f"  Columns: [U_p, E_el, E_d]")
    print(f"  U_p range : {arr[:,0].min():.4f} ~ {arr[:,0].max():.4f}")
    print(f"  E_el range: {arr[:,1].min():.4e} ~ {arr[:,1].max():.4e}")
    print(f"  E_d  range: {arr[:,2].min():.4e} ~ {arr[:,2].max():.4e}")
else:
    print("No trained models found.")
