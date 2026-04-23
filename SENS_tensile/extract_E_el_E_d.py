#!/usr/bin/env python3
"""
extract_E_el_E_d.py — 从已训练模型中提取每圈的 E_el 和 E_d

用法:
    cd 'upload code/SENS_tensile'
    python extract_E_el_E_d.py <model_dir>

支持：
    - 6×100 / 8×400 等任意网络规格（自动从 model_settings.txt 读取）
    - 单调加载 / 循环加载（自动检测）
    - Williams 特征（自动检测并启用）

示例（baseline 8×400）:
    python extract_E_el_E_d.py \\
      hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_..._Umax0.12

示例（Williams）:
    python extract_E_el_E_d.py \\
      hl_8_Neurons_400_activation_TrainableReLU_coeff_3.0_..._Umax0.12_williams_std

输出：
    best_models/E_el_E_d_vs_Up.npy   shape (N, 3): [U_p/cycle_idx, E_el, E_d]
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

# ── 从 model_settings.txt 自动读取配置 ────────────────────────────────────────
def parse_settings(mdir):
    """读取 model_settings.txt，返回 key->value 字典。"""
    f = mdir / 'model_settings.txt'
    if not f.exists():
        return {}
    cfg = {}
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('---'):
            continue
        if ':' in line:
            k, v = line.split(':', 1)
            cfg[k.strip()] = v.strip()
    return cfg

cfg = parse_settings(model_dir)

# ── 网络参数 ──────────────────────────────────────────────────────────────────
device = 'cpu'

network_dict = {
    "model_type"   : 'MLP',
    "hidden_layers": int(cfg.get('hidden_layers', 6)),
    "neurons"      : int(cfg.get('neurons', 100)),
    "seed"         : int(cfg.get('seed', 1)),
    "activation"   : cfg.get('activation', 'TrainableReLU'),
    "init_coeff"   : float(cfg.get('coeff', 1.0)),
}
print(f"Network: {network_dict['hidden_layers']}×{network_dict['neurons']}, "
      f"coeff={network_dict['init_coeff']}, seed={network_dict['seed']}")

# ── Williams 特征 ─────────────────────────────────────────────────────────────
williams_enabled = cfg.get('williams_enable', 'False') == 'True'
williams_dict = None
if williams_enabled:
    williams_dict = {
        "enable"     : True,
        "theta_mode" : cfg.get('williams_theta_mode', 'atan2'),
        "r_min"      : float(cfg.get('williams_r_min', 1e-6)),
    }
    print(f"Williams features: ENABLED (theta_mode={williams_dict['theta_mode']})")
else:
    print("Williams features: disabled")

# ── 加载方式 ──────────────────────────────────────────────────────────────────
loading_type = cfg.get('loading_type', 'monotonic')
disp_max     = float(cfg.get('disp_max', 0.12))
print(f"Loading: {loading_type}, disp_max={disp_max}")

# 单调加载位移序列（与 config.py 一致）
disp_mono = np.concatenate((np.linspace(0.0, 0.075, 4), np.linspace(0.1, 0.2, 21)), axis=0)
disp_mono = disp_mono[1:]   # shape (24,)

# ── 固定参数（与 config.py 一致）────────────────────────────────────────────
PFF_model_dict = {"PFF_model": 'AT1', "se_split": 'volumetric', "tol_ir": 5e-3}
mat_prop_dict  = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
numr_dict      = {"alpha_constraint": 'nonsmooth', "gradient_type": 'numerical'}

domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
loading_angle  = torch.tensor([np.pi / 2])
crack_dict     = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
fine_mesh_file = str(SCRIPT_DIR / 'meshed_geom2.msh')

# ── 构建模型 + 网格 ───────────────────────────────────────────────────────────
pffmodel, matprop, network = construct_model(
    PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device,
    williams_dict=williams_dict)

inp, T_conn, area_T, hist_alpha = prep_input_data(
    matprop, pffmodel, crack_dict, numr_dict, mesh_file=fine_mesh_file, device=device)

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

# ── 加载 x_tip（Williams 模式下需要正确还原特征）────────────────────────────
x_tip_per_cycle = None
if williams_enabled:
    for fname in ('x_tip_psi_vs_cycle.npy', 'x_tip_alpha_vs_cycle.npy', 'x_tip_vs_cycle.npy'):
        p = best_models_dir / fname
        if p.exists():
            x_tip_per_cycle = np.load(str(p))
            print(f"Loaded x_tip: {fname}  ({len(x_tip_per_cycle)} cycles)")
            break
    if x_tip_per_cycle is None:
        print("WARNING: Williams enabled but x_tip files not found — using x_tip=0 for all cycles.")
        print("         Re-run after training completes for accurate results.")

# ── 遍历所有 checkpoint，提取 E_el 和 E_d ────────────────────────────────────
results = []   # list of (label, E_el, E_d)

print(f"\n{'Cycle':<7} {'U_p':<10} {'E_el':<20} {'E_d':<20} {'E_el+E_d'}")
print("-" * 73)

j = 0
while True:
    model_file = best_models_dir / f'trained_1NN_{j}.pt'
    if not model_file.is_file():
        break

    # 设置 x_tip（Williams 模式）
    if williams_enabled and x_tip_per_cycle is not None and j < len(x_tip_per_cycle):
        field_comp.x_tip = float(x_tip_per_cycle[j])

    # 设置加载位移
    if loading_type == 'cyclic':
        lmbda_val = disp_max
    else:
        if j >= len(disp_mono):
            break
        lmbda_val = float(disp_mono[j])

    field_comp.lmbda = torch.tensor(lmbda_val, device=device)

    field_comp.net.load_state_dict(
        torch.load(str(model_file), map_location='cpu', weights_only=True))
    field_comp.net.eval()

    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
        # hist_alpha = alpha：令不可逆惩罚 = 0（与 plot_energy 逻辑一致）
        E_el, E_d, _ = compute_energy(
            inp, u, v, alpha, alpha,
            matprop, pffmodel, area_T, T_conn, f_fatigue=1.0)

    E_el_val = float(E_el.item())
    E_d_val  = float(E_d.item())

    results.append((lmbda_val, E_el_val, E_d_val))
    print(f"{j:<7} {lmbda_val:<10.4f} {E_el_val:<20.6e} {E_d_val:<20.6e} {E_el_val+E_d_val:.6e}")
    j += 1

# ── 保存结果 ──────────────────────────────────────────────────────────────────
if results:
    arr = np.array(results)   # shape (N, 3): [U_p_or_cycle, E_el, E_d]
    out_path = best_models_dir / 'E_el_E_d_vs_Up.npy'
    np.save(str(out_path), arr)
    print(f"\nSaved: {out_path}  shape={arr.shape}")
    print(f"  Columns: [U_p (or disp_max for cyclic), E_el, E_d]")
    print(f"  E_el range: {arr[:,1].min():.4e} ~ {arr[:,1].max():.4e}")
    print(f"  E_d  range: {arr[:,2].min():.4e} ~ {arr[:,2].max():.4e}")
else:
    print("No trained models found.")
