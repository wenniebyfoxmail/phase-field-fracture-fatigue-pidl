#!/usr/bin/env python3
"""
generate_figs_summary.py — 多 case 汇总图

输出 4 张图（保存至 figfiles/summary/）：
  Fig 1 — S-N 曲线（5 点 + 幂律拟合）
  Fig 2 — a-N 曲线（5 个循环 case 裂缝长度 vs 循环数）
  Fig 3 — E_el vs N 归一化对比（5 个循环 case）
  Fig 4 — Case C vs 0B 对比（单调加载，Seleš 一致性验证）

用法（在 upload code/SENS_tensile/ 目录下运行）：
  python generate_figs_summary.py
"""

import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent                   # upload code/SENS_tensile/
SOURCE_DIR  = SCRIPT_DIR.parent / 'source'            # upload code/source/
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SOURCE_DIR))

# ── 输出目录 ──────────────────────────────────────────────────────────────────
OUT_DIR = SCRIPT_DIR / 'figfiles' / 'summary'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Case 定义 ─────────────────────────────────────────────────────────────────
PREFIX = 'hl_6_Neurons_100_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_'

CYCLIC_CASES = [
    # (label,  umax, N_f,  directory_suffix)
    ('$U_{max}$=0.12', 0.12, 109, 'fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12'),
    ('$U_{max}$=0.11', 0.11, 130, 'fatigue_on_carrara_asy_aT0.5_N200_R0.0_Umax0.11'),
    ('$U_{max}$=0.10', 0.10, 199, 'fatigue_on_carrara_asy_aT0.5_N600_R0.0_Umax0.1'),
    ('$U_{max}$=0.09', 0.09, 276, 'fatigue_on_carrara_asy_aT0.5_N500_R0.0_Umax0.09'),
    ('$U_{max}$=0.08', 0.08, 720, 'fatigue_on_carrara_asy_aT0.5_N800_R0.0_Umax0.08'),
]

DIR_CASE_C  = PREFIX + 'fatigue_on_carrara_asy_aT0.5_N1000_R0.0_Umax0.08_mono'
DIR_CASE_0B = PREFIX + 'fatigue_off'

# 单调加载位移序列（与 config.py 一致）
DISP_MONO = np.concatenate(
    (np.linspace(0.0, 0.075, 4), np.linspace(0.1, 0.2, 21)), axis=0
)[1:]   # 24 steps: 0.025, 0.050, ..., 0.200

COLORS = ['#e41a1c', '#ff7f00', '#4daf4a', '#377eb8', '#984ea3']  # ColorBrewer Set1
MARKERS = ['o', 's', '^', 'D', 'v']


# =============================================================================
# 辅助：加载 cyclic case 数据
# =============================================================================
def load_cyclic(suffix):
    bm = SCRIPT_DIR / (PREFIX + suffix) / 'best_models'
    E  = np.load(str(bm / 'E_el_vs_cycle.npy'))
    x  = np.load(str(bm / 'x_tip_vs_cycle.npy'))
    return E, x


# =============================================================================
# Fig 1 — S-N 曲线
# =============================================================================
def fig_sn_curve():
    umax_arr = np.array([c[1] for c in CYCLIC_CASES])
    nf_arr   = np.array([c[2] for c in CYCLIC_CASES], dtype=float)

    # 幂律拟合 log(N_f) = a + b * log(U_max)
    log_u = np.log(umax_arr)
    log_n = np.log(nf_arr)
    b, a  = np.polyfit(log_u, log_n, 1)   # slope=b, intercept=a
    C     = np.exp(a)
    print(f'[S-N fit] N_f = {C:.2f} × U_max^({b:.2f})')

    u_fit = np.linspace(0.075, 0.13, 200)
    n_fit = C * u_fit ** b

    fig, ax = plt.subplots(figsize=(5, 4))
    for i, (label, umax, nf, _) in enumerate(CYCLIC_CASES):
        ax.scatter(nf, umax, color=COLORS[i], marker=MARKERS[i],
                   s=60, zorder=5, label=label)
    ax.plot(n_fit, u_fit, 'k--', linewidth=1.4,
            label=f'Power-law fit\n$N_f = {C:.1f}\\,U_{{max}}^{{{b:.1f}}}$')

    ax.set_xscale('log')
    ax.set_xlabel('Number of cycles to failure $N_f$', fontsize=12)
    ax.set_ylabel('Displacement amplitude $U_{max}$', fontsize=12)
    ax.set_title('S-N curve (Wöhler curve)', fontsize=12)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, which='both', alpha=0.3)
    plt.tight_layout()
    path = OUT_DIR / 'fig1_SN_curve.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path}')


# =============================================================================
# Fig 2 — a-N 曲线
# =============================================================================
def fig_an_curve():
    fig, ax = plt.subplots(figsize=(6, 4))

    for i, (label, umax, nf, suffix) in enumerate(CYCLIC_CASES):
        E, x = load_cyclic(suffix)
        cycles = np.arange(len(x))
        ax.plot(cycles, x, color=COLORS[i], linewidth=1.5, label=label)
        # 标记 N_f
        if nf < len(x):
            ax.scatter(nf, x[nf], color=COLORS[i], marker='x', s=80, zorder=5)

    ax.axhline(0.46, color='gray', linestyle=':', linewidth=1.2,
               label='Fracture threshold $a$ = 0.46')
    ax.axhline(0.02, color='lightgray', linestyle=':', linewidth=1.0,
               label='Initiation threshold $a$ = 0.02')

    ax.set_xlabel('Cycle $N$', fontsize=12)
    ax.set_ylabel(r'Crack length $a$ ($L^\infty$ from crack mouth)', fontsize=11)
    ax.set_title('a-N curves (crack propagation under cyclic loading)', fontsize=11)
    ax.legend(fontsize=8, loc='upper left')
    ax.set_ylim(-0.02, 0.55)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = OUT_DIR / 'fig2_aN_curves.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path}')


# =============================================================================
# Fig 3 — E_el vs N（归一化）
# =============================================================================
def fig_eel_vs_N():
    fig, ax = plt.subplots(figsize=(6, 4))

    for i, (label, umax, nf, suffix) in enumerate(CYCLIC_CASES):
        E, _ = load_cyclic(suffix)
        E0     = E[0]
        E_norm = E / E0
        cycles = np.arange(len(E))
        ax.plot(cycles, E_norm, color=COLORS[i], linewidth=1.5, label=label)
        # 标记 N_f（竖线）
        if nf < len(E):
            ax.axvline(nf, color=COLORS[i], linestyle='--', linewidth=0.8, alpha=0.5)

    ax.axhline(0.5,  color='dimgray', linestyle=':',  linewidth=1.2,
               label=r'$N_p$ threshold (50%)')
    ax.axhline(0.2,  color='black',   linestyle='--', linewidth=1.2,
               label=r'$N_f$ threshold (20%)')

    ax.set_xlabel('Cycle $N$', fontsize=12)
    ax.set_ylabel(r'$\mathcal{E}_{el}(N)\,/\,\mathcal{E}_{el}(0)$', fontsize=12)
    ax.set_title('Normalized elastic energy degradation', fontsize=11)
    ax.legend(fontsize=8, loc='upper right')
    ax.set_ylim(-0.05, 1.10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = OUT_DIR / 'fig3_Eel_vs_N.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path}')


# =============================================================================
# Fig 4 — Case C vs 0B（单调加载 Seleš 一致性验证）
# 需要从 trained_1NN_j.pt 重新计算 Case 0B 各步 E_el
# =============================================================================
def fig_caseC_vs_0B():
    # ── Case C：直接读 E_el_vs_cycle.npy ──────────────────────────────────────
    bm_C = SCRIPT_DIR / DIR_CASE_C / 'best_models'
    E_C  = np.load(str(bm_C / 'E_el_vs_cycle.npy'))   # 24 values

    # ── Case 0B：从各步 trained_1NN_j.pt 重算 E_el ───────────────────────────
    bm_0B = SCRIPT_DIR / DIR_CASE_0B / 'best_models'
    model_files_0B = sorted(
        [p for p in bm_0B.glob('trained_1NN_*.pt')
         if p.stem != 'trained_1NN_initTraining'],
        key=lambda p: int(p.stem.split('_')[-1])
    )
    n_steps_0B = len(model_files_0B)
    print(f'[Case 0B] {n_steps_0B} model files found, recomputing E_el ...')

    # 延迟导入（仅 Fig4 需要）
    import torch
    from construct_model     import construct_model
    from input_data_from_mesh import prep_input_data
    from compute_energy      import compute_energy
    from field_computation   import FieldComputation

    device = 'cpu'
    network_dict   = {"model_type": 'MLP', "hidden_layers": 6, "neurons": 100,
                      "seed": 1, "activation": 'TrainableReLU', "init_coeff": 1.0}
    PFF_model_dict = {"PFF_model": 'AT1', "se_split": 'volumetric', "tol_ir": 5e-3}
    mat_prop_dict  = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
    numr_dict      = {"alpha_constraint": 'nonsmooth', "gradient_type": 'numerical'}
    domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
    loading_angle  = torch.tensor([np.pi / 2])
    crack_dict     = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}
    fine_mesh      = str(SCRIPT_DIR / 'meshed_geom2.msh')

    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, device)
    inp, T_conn, area_T, hist_alpha = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict, mesh_file=fine_mesh, device=device)
    field_comp = FieldComputation(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.0]), theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"])
    field_comp.net            = field_comp.net.to(device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(device)
    field_comp.theta          = field_comp.theta.to(device)

    E_0B = np.zeros(n_steps_0B)
    for idx, model_path in enumerate(model_files_0B):
        j = int(model_path.stem.split('_')[-1])
        state = torch.load(str(model_path), map_location='cpu', weights_only=True)
        field_comp.net.load_state_dict(state)
        field_comp.net.eval()
        # 设置对应加载步的位移（关键：单调加载每步 lmbda 不同）
        field_comp.lmbda = torch.tensor(DISP_MONO[j], device=device)
        with torch.no_grad():
            u_el, v_el, alpha_el = field_comp.fieldCalculation(inp)
            E_val, _, _ = compute_energy(
                inp, u_el, v_el, alpha_el, hist_alpha,
                matprop, pffmodel, area_T, T_conn, f_fatigue=1.0)
        E_0B[idx] = float(E_val.item())
        if (idx + 1) % 6 == 0 or idx == n_steps_0B - 1:
            print(f'  [{idx+1}/{n_steps_0B}] step {j} (U={DISP_MONO[j]:.3f}): E_el={E_0B[idx]:.4e}')

    # ── 绘图 ──────────────────────────────────────────────────────────────────
    steps   = np.arange(len(DISP_MONO))
    disp_24 = DISP_MONO

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(disp_24[:len(E_C)], E_C,  color='#e41a1c', linewidth=2.0,
            label='Case C  (fatigue_on=True, monotonic)', zorder=3)
    ax.plot(disp_24[:len(E_0B)], E_0B, color='#377eb8', linewidth=1.5,
            linestyle='--', label='Case 0B (fatigue_off, monotonic)', zorder=2)

    ax.set_xlabel('Applied displacement $U$', fontsize=12)
    ax.set_ylabel(r'Elastic energy $\mathcal{E}_{el}$', fontsize=12)
    ax.set_title('Seleš consistency: Case C vs Case 0B\n'
                 r'(fatigue_on=True, monotonic $\Rightarrow$ $\bar{\alpha}\equiv 0$, $f\equiv 1$)',
                 fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = OUT_DIR / 'fig4_CaseC_vs_0B.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path}')


# =============================================================================
# 主程序
# =============================================================================
if __name__ == '__main__':
    print('=== Fig 1: S-N curve ===')
    fig_sn_curve()

    print('\n=== Fig 2: a-N curves ===')
    fig_an_curve()

    print('\n=== Fig 3: E_el vs N (normalized) ===')
    fig_eel_vs_N()

    print('\n=== Fig 4: Case C vs 0B ===')
    fig_caseC_vs_0B()

    print(f'\nAll figures saved to: {OUT_DIR}')
