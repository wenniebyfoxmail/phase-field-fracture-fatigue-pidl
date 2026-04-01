#!/usr/bin/env python3
"""
recover_E_el.py — 从 checkpoint 重建 E_el_vs_cycle.npy

用法:
  python recover_E_el.py <model_dir> <disp_max> [start_cycle]

参数:
  model_dir   : 模型目录（含 best_models/checkpoint_step_*.pt）
  disp_max    : 峰值位移（Case F=0.10, Case E=0.08）
  start_cycle : 从哪圈开始重算（跳过已有数据），默认=0

示例:
  # Case F: 重算所有 206 圈
  python recover_E_el.py \
    hl_6_.../fatigue_on_carrara_asy_aT0.5_N600_R0.0_Umax0.1 0.10

  # Case E N800: 只重算 cycle 311-741（0-310 已有）
  python recover_E_el.py \
    hl_6_.../fatigue_on_carrara_asy_aT0.5_N800_R0.0_Umax0.08 0.08 311
"""

import sys
import numpy as np
import torch
from pathlib import Path

# ── 路径设置 ─────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent                   # upload code/SENS_tensile/
SOURCE_DIR  = SCRIPT_DIR.parent / 'source'            # upload code/source/
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SOURCE_DIR))

from construct_model    import construct_model
from input_data_from_mesh import prep_input_data
from compute_energy     import compute_energy
from field_computation  import FieldComputation

# ── 解析参数 ─────────────────────────────────────────────────────────────────
if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

model_dir   = Path(sys.argv[1])
disp_max    = float(sys.argv[2])
start_cycle = int(sys.argv[3]) if len(sys.argv) > 3 else 0

print(f"model_dir   = {model_dir}")
print(f"disp_max    = {disp_max}")
print(f"start_cycle = {start_cycle}")

best_models_dir = model_dir / 'best_models'

# ── 模型参数（与 config.py 一致）────────────────────────────────────────────
device = 'cpu'

network_dict  = {"model_type": 'MLP', "hidden_layers": 6, "neurons": 100,
                 "seed": 1, "activation": 'TrainableReLU', "init_coeff": 1.0}
PFF_model_dict = {"PFF_model": 'AT1', "se_split": 'volumetric', "tol_ir": 5e-3}
mat_prop_dict  = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
numr_dict      = {"alpha_constraint": 'nonsmooth', "gradient_type": 'numerical'}

domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
loading_angle  = torch.tensor([np.pi / 2])
crack_dict     = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
fine_mesh_file = str(SCRIPT_DIR / 'meshed_geom2.msh')

# ── 构建模型 + 网格 ──────────────────────────────────────────────────────────
pffmodel, matprop, network = construct_model(
    PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device)

inp, T_conn, area_T, hist_alpha = prep_input_data(
    matprop, pffmodel, crack_dict, numr_dict, mesh_file=fine_mesh_file, device=device)

field_comp = FieldComputation(
    net=network, domain_extrema=domain_extrema,
    lmbda=torch.tensor([disp_max], device=device),
    theta=loading_angle,
    alpha_constraint=numr_dict["alpha_constraint"])
field_comp.net             = field_comp.net.to(device)
field_comp.domain_extrema  = field_comp.domain_extrema.to(device)
field_comp.theta           = field_comp.theta.to(device)

# ── 找出所有 checkpoint 文件 ─────────────────────────────────────────────────
model_files = sorted(
    [p for p in best_models_dir.glob('trained_1NN_*.pt')
     if p.stem != 'trained_1NN_initTraining'],
    key=lambda p: int(p.stem.split('_')[-1]))

cycles_available = [int(p.stem.split('_')[-1]) for p in model_files]
cycles_to_compute = [c for c in cycles_available if c >= start_cycle]

print(f"Model files found : {len(model_files)}  ({cycles_available[0]}–{cycles_available[-1]})")
print(f"Cycles to compute : {len(cycles_to_compute)}  ({cycles_to_compute[0]}–{cycles_to_compute[-1]})")

# ── 重算 E_el ────────────────────────────────────────────────────────────────
new_E_el = {}   # cycle → E_el value

for i, cycle in enumerate(cycles_to_compute):
    model_path = best_models_dir / f'trained_1NN_{cycle}.pt'
    state = torch.load(str(model_path), map_location='cpu', weights_only=True)
    field_comp.net.load_state_dict(state)
    field_comp.net.eval()

    with torch.no_grad():
        u_el, v_el, alpha_el = field_comp.fieldCalculation(inp)
        E_el_val, _, _ = compute_energy(
            inp, u_el, v_el, alpha_el, hist_alpha,
            matprop, pffmodel, area_T, T_conn, f_fatigue=1.0
        )
    new_E_el[cycle] = float(E_el_val.item())

    if (i + 1) % 20 == 0 or i == len(cycles_to_compute) - 1:
        print(f"  [{i+1}/{len(cycles_to_compute)}] cycle {cycle}: E_el={new_E_el[cycle]:.4e}")

# ── 合并已有数据 + 新计算数据 ─────────────────────────────────────────────────
existing_file  = best_models_dir / 'E_el_vs_cycle.npy'
backup_file    = best_models_dir / 'E_el_vs_cycle_0_299.npy'

if start_cycle > 0:
    # 有已有数据需要合并
    if backup_file.exists():
        existing_E_el = np.load(str(backup_file))
        print(f"Loaded backup: {backup_file.name}  shape={existing_E_el.shape}")
    elif existing_file.exists():
        existing_E_el = np.load(str(existing_file))
        print(f"Loaded existing: {existing_file.name}  shape={existing_E_el.shape}")
    else:
        existing_E_el = np.array([])
        print("No existing E_el data found.")

    # existing covers cycles 0..(len-1), new covers start_cycle..max_cycle
    # build full array indexed by cycle number
    max_cycle = max(new_E_el.keys())
    full = np.zeros(max_cycle + 1)
    full[:len(existing_E_el)] = existing_E_el
    for c, v in new_E_el.items():
        full[c] = v
    combined = full
else:
    max_cycle = max(new_E_el.keys())
    combined = np.zeros(max_cycle + 1)
    for c, v in new_E_el.items():
        combined[c] = v

# ── 保存 ─────────────────────────────────────────────────────────────────────
out_path = best_models_dir / 'E_el_vs_cycle.npy'
# 备份旧文件
if out_path.exists() and not backup_file.exists():
    import shutil
    shutil.copy(str(out_path), str(best_models_dir / 'E_el_vs_cycle_backup.npy'))
    print(f"Backed up old E_el to E_el_vs_cycle_backup.npy")

np.save(str(out_path), combined)
print(f"\nSaved combined E_el: {out_path}")
print(f"  shape = {combined.shape}  |  E_el[0]={combined[0]:.4e}  E_el[-1]={combined[-1]:.4e}")
print("Done.")
