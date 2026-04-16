#!/usr/bin/env python3
"""
extract_Kt.py — 从已训练模型中提取每圈的应力集中因子 Kt

定义：
    Kt = sqrt( ψ⁺_tip / ψ⁺_nominal )

    ψ⁺_tip     : top-10 最高能量单元的 g(α)·ψ⁺_0（退化拉伸应变能密度）均值
                  使用退化值：g(1)=0 → 预裂缝面单元自动排除，top-10 自动定位到裂尖
    ψ⁺_nominal : 远场单元（|y| > 0.3, x > -0.3）的 g(α)·ψ⁺_0 均值
                  （远离裂缝路径，α≈0，g≈1，退化 ≈ 未退化）
    Kt 定义为应力集中比的平方根：Kt = σ_tip/σ_nominal，
    因 ψ⁺ ∝ σ²，故 Kt = sqrt(ψ⁺_tip / ψ⁺_nominal)

用法：
    cd 'upload code/SENS_tensile'
    python extract_Kt.py <model_dir>

支持：
    - 6×100 / 8×400 等任意网络规格（自动从 model_settings.txt 读取）
    - 单调加载 / 循环加载（自动检测）
    - Williams 特征（自动检测；需要 x_tip_psi_vs_cycle.npy 以正确还原场）

示例（baseline）：
    python extract_Kt.py hl_8_Neurons_400_...Umax0.12

示例（Williams）：
    python extract_Kt.py hl_8_Neurons_400_...Umax0.12_williams_std

输出：
    best_models/Kt_vs_cycle.npy   — shape (N_cycles,)，每圈 Kt 值
    best_models/Kt_vs_cycle.png   — Kt 随 cycle 的折线图
"""

import sys
import numpy as np
import torch
from pathlib import Path

# ── 路径设置 ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
SOURCE_DIR  = SCRIPT_DIR.parent / 'source'
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SOURCE_DIR))

from construct_model      import construct_model
from input_data_from_mesh import prep_input_data
from compute_energy       import get_psi_plus_per_elem
from field_computation    import FieldComputation

# ── 解析参数 ──────────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

model_dir = Path(sys.argv[1])
if not model_dir.is_absolute():
    model_dir = SCRIPT_DIR / model_dir

best_models_dir = model_dir / 'best_models'
print(f"model_dir = {model_dir}")

# ── 读取 model_settings.txt ───────────────────────────────────────────────────
def parse_settings(mdir):
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
      f"coeff={network_dict['init_coeff']}")

# ── Williams 特征 ─────────────────────────────────────────────────────────────
williams_enabled = cfg.get('williams_enable', 'False') == 'True'
williams_dict = None
if williams_enabled:
    williams_dict = {
        "enable"     : True,
        "theta_mode" : cfg.get('williams_theta_mode', 'atan2'),
        "r_min"      : float(cfg.get('williams_r_min', 1e-6)),
    }
    print("Williams features: ENABLED")
else:
    print("Williams features: disabled (baseline)")

# ── 加载方式 ──────────────────────────────────────────────────────────────────
loading_type = cfg.get('loading_type', 'monotonic')
disp_max     = float(cfg.get('disp_max', 0.12))
print(f"Loading: {loading_type}, disp_max={disp_max}")

disp_mono = np.concatenate((np.linspace(0.0, 0.075, 4), np.linspace(0.1, 0.2, 21)), axis=0)
disp_mono = disp_mono[1:]   # shape (24,)，单调序列

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

inp, T_conn, area_T, _ = prep_input_data(
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

# ── 预计算元素形心坐标 ────────────────────────────────────────────────────────
# T_conn shape: (N_elem, 3)；inp shape: (N_nodes, 2)，[:,0]=x, [:,1]=y
T_np  = T_conn.cpu().numpy() if isinstance(T_conn, torch.Tensor) else T_conn
inp_np = inp.detach().cpu().numpy()

cx = (inp_np[T_np[:, 0], 0] + inp_np[T_np[:, 1], 0] + inp_np[T_np[:, 2], 0]) / 3.0
cy = (inp_np[T_np[:, 0], 1] + inp_np[T_np[:, 1], 1] + inp_np[T_np[:, 2], 1]) / 3.0

# 远场（nominal）元素：|y| > 0.3，x > -0.3（远离裂缝路径和左边界应力集中）
nominal_mask = (np.abs(cy) > 0.3) & (cx > -0.3)
n_nominal = nominal_mask.sum()
print(f"Nominal elements: {n_nominal} (|y|>0.3, x>-0.3)")
if n_nominal == 0:
    print("WARNING: no nominal elements found — will fall back to domain mean")

# ── 加载 x_tip per cycle（Williams 需要正确还原 8D 特征）────────────────────
x_tip_per_cycle = None
if williams_enabled:
    for fname in ('x_tip_psi_vs_cycle.npy', 'x_tip_alpha_vs_cycle.npy', 'x_tip_vs_cycle.npy'):
        p = best_models_dir / fname
        if p.exists():
            x_tip_per_cycle = np.load(str(p))
            print(f"Loaded x_tip: {fname}  ({len(x_tip_per_cycle)} cycles)")
            break
    if x_tip_per_cycle is None:
        print("WARNING: x_tip files not found — using x_tip=0 for all cycles.")
        print("         Results at cycle 0 are accurate; later cycles may differ slightly.")
        print("         Re-run after training completes for full accuracy.")

# ── 主循环：逐圈提取 Kt ───────────────────────────────────────────────────────
Kt_results = []   # list of float

print(f"\n{'Cycle':<7} {'x_tip':<8} {'ψ⁺_tip':<16} {'ψ⁺_nominal':<16} {'Kt':>6}")
print("-" * 58)

j = 0
while True:
    model_file = best_models_dir / f'trained_1NN_{j}.pt'
    if not model_file.is_file():
        break

    # 设置 x_tip（Williams 模式）
    if williams_enabled:
        if x_tip_per_cycle is not None and j < len(x_tip_per_cycle):
            field_comp.x_tip = float(x_tip_per_cycle[j])
        # else: 保持上一圈值（或初始 0）

    # 设置加载位移
    if loading_type == 'cyclic':
        lmbda_val = disp_max
    else:
        if j >= len(disp_mono):
            break
        lmbda_val = float(disp_mono[j])
    field_comp.lmbda = torch.tensor(lmbda_val, device=device)

    # 加载权重
    field_comp.net.load_state_dict(
        torch.load(str(model_file), map_location='cpu', weights_only=True))
    field_comp.net.eval()

    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)

        # ψ⁺_deg = g(α)·ψ⁺_0（退化拉伸应变能密度，每个单元）
        # 使用退化值：g(1)=0 → 预裂缝面单元自动排除，top-10 定位到裂尖
        psi_plus_0 = get_psi_plus_per_elem(
            inp, u, v, alpha, matprop, pffmodel, area_T, T_conn)

    psi0 = psi_plus_0.cpu().numpy()   # shape (N_elem,)

    # ψ⁺_tip：top-10 单元均值（自动定位裂尖，与 williams_features.compute_x_tip_psi 逻辑一致）
    top10_idx = np.argsort(psi0)[-10:]
    psi_tip = float(psi0[top10_idx].mean())

    # ψ⁺_nominal：远场均值
    if n_nominal > 0:
        psi_nominal = float(psi0[nominal_mask].mean())
    else:
        psi_nominal = float(psi0.mean())

    Kt = (psi_tip / psi_nominal) ** 0.5 if psi_nominal > 1e-20 else float('nan')
    Kt_results.append(Kt)

    x_tip_str = f"{field_comp.x_tip:.4f}" if williams_enabled else "  N/A "
    print(f"{j:<7} {x_tip_str:<8} {psi_tip:<16.4e} {psi_nominal:<16.4e} {Kt:>6.2f}")
    j += 1

# ── 保存 + 绘图 ───────────────────────────────────────────────────────────────
if not Kt_results:
    print("No trained models found.")
    sys.exit(0)

Kt_arr = np.array(Kt_results)
out_npy = best_models_dir / 'Kt_vs_cycle.npy'
np.save(str(out_npy), Kt_arr)
print(f"\nSaved: {out_npy}  shape={Kt_arr.shape}")
print(f"  Cycle 0  Kt = {Kt_arr[0]:.2f}")
print(f"  Median   Kt = {np.nanmedian(Kt_arr):.2f}")
print(f"  Max      Kt = {np.nanmax(Kt_arr):.2f}  (cycle {int(np.nanargmax(Kt_arr))})")

try:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    cycles = np.arange(len(Kt_arr))
    ax.plot(cycles, Kt_arr, 'b-o', markersize=2, linewidth=1.2, label='This run')

    # 参考线：FEM 和 baseline PIDL
    ax.axhline(y=15.3, color='red',  linestyle='--', linewidth=1,
               label='FEM Kt ≈ 15.3')
    ax.axhline(y=7.2,  color='gray', linestyle='--', linewidth=1,
               label='Baseline PIDL Kt ≈ 7.2')

    ax.set_xlabel('Cycle N')
    ax.set_ylabel(r'$K_t = \sqrt{\psi^+_{tip} / \psi^+_{nominal}}$')
    tag = model_dir.name
    ax.set_title(f'Stress Concentration Factor vs Cycle\n{tag[:70]}')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    out_png = best_models_dir / 'Kt_vs_cycle.png'
    plt.savefig(str(out_png), dpi=150)
    plt.close()
    print(f"Saved: {out_png}")
except ImportError:
    print("matplotlib not available — skipping plot.")
