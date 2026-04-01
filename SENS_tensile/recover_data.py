#!/usr/bin/env python3
"""
recover_data.py — 从 trained_1NN_j.pt 批量恢复 E_el 和 x_tip 数据

用法:
  python recover_data.py <model_dir> <disp_max> [e_start] [x_start]

参数:
  model_dir : 模型目录（含 best_models/）
  disp_max  : 峰值位移
  e_start   : E_el 从哪圈开始重算（默认 0 = 全部重算）
  x_start   : x_tip 从哪圈开始重算（默认 0 = 全部重算）

示例（见文末 run_all 注释）
"""
import sys
import numpy as np
import torch
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SOURCE_DIR  = SCRIPT_DIR.parent / 'source'
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SOURCE_DIR))

from construct_model       import construct_model
from input_data_from_mesh  import prep_input_data
from compute_energy        import compute_energy
from field_computation     import FieldComputation
from model_train           import get_crack_tip   # ★ 复用已有函数

# ── 参数解析 ─────────────────────────────────────────────────────────────────
if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

model_dir = Path(sys.argv[1])
disp_max  = float(sys.argv[2])
e_start   = int(sys.argv[3]) if len(sys.argv) > 3 else 0
x_start   = int(sys.argv[4]) if len(sys.argv) > 4 else 0

print(f"model_dir = {model_dir.name}")
print(f"disp_max  = {disp_max}  |  e_start={e_start}  x_start={x_start}")

best_models_dir = model_dir / 'best_models'

# ── 固定参数（与 config.py / 所有 SENS_tensile case 一致）────────────────────
device        = 'cpu'
network_dict  = {"model_type": 'MLP', "hidden_layers": 6, "neurons": 100,
                 "seed": 1, "activation": 'TrainableReLU', "init_coeff": 1.0}
PFF_model_dict = {"PFF_model": 'AT1', "se_split": 'volumetric', "tol_ir": 5e-3}
mat_prop_dict  = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
numr_dict      = {"alpha_constraint": 'nonsmooth', "gradient_type": 'numerical'}
domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
loading_angle  = torch.tensor([np.pi / 2])
crack_dict     = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
fine_mesh_file = str(SCRIPT_DIR / 'meshed_geom2.msh')

_crack_mouth   = torch.tensor([0.0, 0.0])
_alpha_thr     = 0.90
_crack_mouth_x = 0.0

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
field_comp.net            = field_comp.net.to(device)
field_comp.domain_extrema = field_comp.domain_extrema.to(device)
field_comp.theta          = field_comp.theta.to(device)

# ── 找出所有模型文件，按 cycle 排序 ─────────────────────────────────────────
model_files = sorted(
    [p for p in best_models_dir.glob('trained_1NN_*.pt') if 'init' not in p.stem],
    key=lambda p: int(p.stem.split('_')[-1]))
all_cycles  = [int(p.stem.split('_')[-1]) for p in model_files]

# 需要重算的圈
need_E = set(c for c in all_cycles if c >= e_start)
need_x = set(c for c in all_cycles if c >= x_start)
need   = need_E | need_x
cycles_to_run = sorted(need)

print(f"Models found: {len(all_cycles)}  ({all_cycles[0]}–{all_cycles[-1]})")
print(f"E_el: recompute {len(need_E)} cycles (from {e_start})")
print(f"x_tip: recompute {len(need_x)} cycles (from {x_start})")

# ── 主循环 ───────────────────────────────────────────────────────────────────
new_E_el  = {}
new_x_tip = {}

for i, cycle in enumerate(cycles_to_run):
    state = torch.load(str(best_models_dir / f'trained_1NN_{cycle}.pt'),
                       map_location='cpu', weights_only=True)
    field_comp.net.load_state_dict(state)
    field_comp.net.eval()

    with torch.no_grad():
        u_el, v_el, alpha_el = field_comp.fieldCalculation(inp)

        if cycle in need_E:
            E_val, _, _ = compute_energy(
                inp, u_el, v_el, alpha_el, hist_alpha,
                matprop, pffmodel, area_T, T_conn, f_fatigue=1.0)
            new_E_el[cycle] = float(E_val.item())

        if cycle in need_x:
            _, crack_length = get_crack_tip(
                alpha_el.flatten(), inp, _crack_mouth,
                threshold=_alpha_thr, x_min=_crack_mouth_x)
            new_x_tip[cycle] = crack_length

    if (i + 1) % 50 == 0 or i == len(cycles_to_run) - 1:
        e_str = f"E_el={new_E_el.get(cycle, '-'):.3e}" if cycle in need_E else ""
        x_str = f"x_tip={new_x_tip.get(cycle, '-'):.4f}" if cycle in need_x else ""
        print(f"  [{i+1}/{len(cycles_to_run)}] cycle {cycle}: {e_str}  {x_str}")

# ── 合并并保存 ────────────────────────────────────────────────────────────────
def _merge_and_save(existing_file, backup_file, new_data_dict, label):
    """将已有数据 + 新计算数据合并，保存到 existing_file。"""
    # 加载已有数据（优先 backup，backup 是续跑时自动保存的 0~N-1 段）
    if backup_file.exists():
        existing = np.load(str(backup_file))
        print(f"  [{label}] loaded backup {backup_file.name}: shape={existing.shape}")
    elif existing_file.exists():
        existing = np.load(str(existing_file))
        print(f"  [{label}] loaded existing {existing_file.name}: shape={existing.shape}")
    else:
        existing = np.array([])

    if not new_data_dict:
        print(f"  [{label}] nothing to update.")
        return

    max_cycle = max(new_data_dict.keys())
    n_total   = max(max_cycle + 1, len(existing))
    combined  = np.zeros(n_total)
    combined[:len(existing)] = existing
    for c, v in new_data_dict.items():
        combined[c] = v

    np.save(str(existing_file), combined)
    print(f"  [{label}] saved → {existing_file.name}  shape={combined.shape}"
          f"  [{combined[0]:.4e} … {combined[-1]:.4e}]")

print("\n── Saving ──")
_merge_and_save(
    best_models_dir / 'E_el_vs_cycle.npy',
    best_models_dir / 'E_el_vs_cycle_0_299.npy',
    new_E_el, 'E_el')

_merge_and_save(
    best_models_dir / 'x_tip_vs_cycle.npy',
    best_models_dir / 'x_tip_vs_cycle_0_299.npy',
    new_x_tip, 'x_tip')

print("Done.")

# ── 各 case 调用方式 ──────────────────────────────────────────────────────────
# N50  (aT0.167):  python recover_data.py <N50_dir>   0.08  0  0   (E_el OK, x_tip全缺)
# Case D (Umax0.12): python recover_data.py <D_dir>   0.12  122 0  (E_el补122+, x_tip全缺)
# Case F (Umax0.1):  python recover_data.py <F_dir>   0.10  206 62 (E_el OK, x_tip补62+)
# Case E (Umax0.08): python recover_data.py <E_dir>   0.08  742 311(E_el OK, x_tip补311+)
