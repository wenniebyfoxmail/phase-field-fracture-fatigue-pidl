#!/usr/bin/env python3
"""
generate_figs_sn_full.py — 完整 S-N 曲线（Option B）

包含所有 5 个 U_max 的 8×400 PIDL 结果（含 Umax=0.08），
与 FEM GRIPHFiTH 的 S-N 数据双方对比。

输出（figfiles/sn_full/）：
  B1 — 完整 S-N 曲线（5 点 PIDL + 5 点 FEM + 幂律拟合）
  B2 — ᾱ_max 和 f_min vs N 全案例面板（5×Umax）
  B3 — 相对误差条形图（PIDL/FEM N_f error per U_max）

用法：
  cd "upload code/SENS_tensile"
  python generate_figs_sn_full.py
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ── 路径 ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
FEM_DATA_DIR = Path.home() / 'Downloads' / 'post_process 2'
OUT_DIR      = SCRIPT_DIR / 'figfiles' / 'sn_full'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── FEM CSV 文件名映射 ────────────────────────────────────────────────────────
FEM_UMAX_STR = {0.12: '12', 0.11: '11', 0.10: '10', 0.09: '09', 0.08: '08'}


def load_fem(umax):
    """Load FEM per-cycle CSV; returns (DataFrame, N_f) where N_f = cycle of max da_dN."""
    fname = FEM_DATA_DIR / f"SENT_PIDL_{FEM_UMAX_STR[umax]}_timeseries.csv"
    df = pd.read_csv(fname)
    N_f = int(df.loc[df['da_dN'].idxmax(), 'N'])
    return df, N_f

# ── PIDL 8×400 Seed=1 Case 目录 ───────────────────────────────────────────────
PREFIX = 'hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_'
PIDL_DIRS = {
    0.12: PREFIX + 'fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12',
    0.11: PREFIX + 'fatigue_on_carrara_asy_aT0.5_N250_R0.0_Umax0.11',
    0.10: PREFIX + 'fatigue_on_carrara_asy_aT0.5_N350_R0.0_Umax0.1',
    0.09: PREFIX + 'fatigue_on_carrara_asy_aT0.5_N400_R0.0_Umax0.09',
    0.08: PREFIX + 'fatigue_on_carrara_asy_aT0.5_N700_R0.0_Umax0.08',
}

ALPHA_T = 0.5
COLORS  = {0.12: '#e41a1c', 0.11: '#ff7f00', 0.10: '#4daf4a',
           0.09: '#377eb8', 0.08: '#984ea3'}


def f_asymptotic(abar, aT=ALPHA_T):
    return (2 * aT / (abar + aT)) ** 2


def load_pidl(umax):
    bm = SCRIPT_DIR / PIDL_DIRS[umax] / 'best_models'
    tip = np.load(bm / 'x_tip_vs_cycle.npy')
    ab  = np.load(bm / 'alpha_bar_vs_cycle.npy')
    E   = np.load(bm / 'E_el_vs_cycle.npy')
    frac = np.where(tip >= 0.5)[0]
    Nf = frac[0] + 1 if len(frac) else len(tip)
    return tip, ab, E, Nf


# =============================================================================
# Fig B1 — 完整 S-N 曲线
# =============================================================================
def fig_B1_sn_full():
    fig, ax = plt.subplots(figsize=(7, 5))

    # ── 收集 PIDL N_f ─────────────────────────────────────────────────────────
    pidl_u, pidl_nf = [], []
    for umax in sorted(PIDL_DIRS):
        try:
            _, _, _, Nf = load_pidl(umax)
            pidl_u.append(umax)
            pidl_nf.append(Nf)
        except FileNotFoundError:
            print(f'  [skip] U_max={umax}: directory not found')

    pidl_u  = np.array(pidl_u)
    pidl_nf = np.array(pidl_nf, dtype=float)

    # ── 收集 FEM N_f（与 PIDL 对齐的 U_max 集合）──────────────────────────────
    fem_u, fem_nf_list = [], []
    for umax in sorted(PIDL_DIRS):
        if umax not in pidl_u:
            continue
        try:
            _, nf_f = load_fem(umax)
            fem_u.append(umax)
            fem_nf_list.append(nf_f)
        except FileNotFoundError:
            print(f'  [skip FEM] U_max={umax}: CSV not found')
    fem_u  = np.array(fem_u)
    fem_nf = np.array(fem_nf_list, dtype=float)

    # 只保留 PIDL 和 FEM 都有数据的 U_max
    common_mask = np.isin(pidl_u, fem_u)
    pidl_u   = pidl_u[common_mask]
    pidl_nf  = pidl_nf[common_mask]

    # ── 幂律拟合 ──────────────────────────────────────────────────────────────
    m_pidl, lnC_pidl = np.polyfit(np.log(pidl_u), np.log(pidl_nf), 1)
    m_fem,  lnC_fem  = np.polyfit(np.log(fem_u),  np.log(fem_nf),  1)
    C_pidl, C_fem    = np.exp(lnC_pidl), np.exp(lnC_fem)

    u_fit = np.linspace(0.075, 0.135, 300)

    # ── 绘图 ──────────────────────────────────────────────────────────────────
    for i, (umax, nf_p, nf_f) in enumerate(zip(pidl_u, pidl_nf, fem_nf)):
        col = COLORS[umax]
        ax.scatter(nf_f, umax, color=col, marker='s', s=80, zorder=6,
                   edgecolors='k', linewidths=0.7)
        ax.scatter(nf_p, umax, color=col, marker='o', s=80, zorder=6,
                   edgecolors='k', linewidths=0.7)
        # 连接线
        ax.plot([nf_f, nf_p], [umax, umax], color=col, lw=0.8, ls='-', alpha=0.4)

    # 幂律拟合曲线
    ax.plot(C_fem  * u_fit ** m_fem,  u_fit, 'r-', lw=2.0,
            label=f'FEM fit:  $N_f = {C_fem:.3f}\\,U^{{{m_fem:.2f}}}$')
    ax.plot(C_pidl * u_fit ** m_pidl, u_fit, 'b--', lw=2.0,
            label=f'PIDL fit: $N_f = {C_pidl:.3f}\\,U^{{{m_pidl:.2f}}}$')

    # 图例替代 scatter
    ax.scatter([], [], color='gray', marker='s', s=80, label='FEM (GRIPHFiTH)')
    ax.scatter([], [], color='gray', marker='o', s=80, label='PIDL 8×400 (seed 1)')

    # Umax 标注
    for umax, nf_p, nf_f in zip(pidl_u, pidl_nf, fem_nf):
        ax.annotate(f'{umax}', xy=(nf_f, umax), xytext=(-14, 5),
                    textcoords='offset points', fontsize=8, color=COLORS[umax])

    ax.set_xscale('log')
    ax.set_xlabel('Cycles to failure $N_f$', fontsize=12)
    ax.set_ylabel('Displacement amplitude $U_{max}$', fontsize=12)
    ax.set_title('Complete S-N Curve (Wöhler): PIDL 8×400 vs FEM\n'
                 f'PIDL exponent={m_pidl:.2f}  vs  FEM exponent={m_fem:.2f}',
                 fontsize=11)
    ax.legend(fontsize=9, loc='upper right')
    ax.grid(True, which='both', alpha=0.25)

    # 数据表
    header = 'Umax | FEM Nf | PIDL Nf | Error'
    rows = [f'{u:.2f} |  {int(nf):4d}  |   {int(np)   :4d}   | {100*(np-nf)/nf:+.1f}%'
            for u, np, nf in zip(pidl_u, pidl_nf, fem_nf)]
    ax.text(0.02, 0.32, header + '\n' + '\n'.join(rows),
            transform=ax.transAxes, fontsize=7, va='top',
            fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='gray', alpha=0.9))

    plt.tight_layout()
    path = OUT_DIR / 'fig_B1_SN_full.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path.name}')


# =============================================================================
# Fig B2 — ᾱ_max & f_min vs N 全案例面板
# =============================================================================
def fig_B2_alpha_panel():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(r'Fatigue history: $\bar{\alpha}_{max}$ and $f_{min}$ — all $U_{max}$ (8×400 seed 1)',
                 fontsize=11, fontweight='bold')
    ax_a, ax_f = axes

    for umax in sorted(PIDL_DIRS):
        try:
            tip, ab, E, Nf = load_pidl(umax)
        except FileNotFoundError:
            continue
        N   = np.arange(len(ab))
        col = COLORS[umax]

        ax_a.plot(N, ab[:, 0], color=col, lw=1.8,
                  label=f'$U_{{max}}$={umax}, $N_f$={Nf}')
        ax_f.plot(N, ab[:, 2], color=col, lw=1.8,
                  label=f'$U_{{max}}$={umax}, $N_f$={Nf}')

        # N_f 竖线
        ax_a.axvline(Nf, color=col, ls=':', lw=0.8, alpha=0.5)
        ax_f.axvline(Nf, color=col, ls=':', lw=0.8, alpha=0.5)

    ax_a.axhline(ALPHA_T, color='k', ls='--', lw=1.0, label=f'$\\alpha_T$={ALPHA_T}')
    ax_a.set_xlabel('Cycle $N$', fontsize=12)
    ax_a.set_ylabel(r'$\bar{\alpha}_{max}$', fontsize=12)
    ax_a.set_title(r'Peak fatigue accumulation $\bar{\alpha}_{max}$', fontsize=11)
    ax_a.set_yscale('log')
    ax_a.legend(fontsize=8)
    ax_a.grid(True, which='both', alpha=0.25)

    ax_f.set_xlabel('Cycle $N$', fontsize=12)
    ax_f.set_ylabel(r'$f_{min}(\bar{\alpha})$', fontsize=12)
    ax_f.set_title(r'Min degradation factor $f_{min}$', fontsize=11)
    ax_f.set_yscale('log')
    ax_f.legend(fontsize=8)
    ax_f.grid(True, which='both', alpha=0.25)

    # FEM 参考
    ax_f.axhline(1e-6, color='r', ls='--', lw=1.0, alpha=0.5,
                 label='FEM $f_{min}$@$N_f$ ≈ $10^{-6}$')
    ax_f.legend(fontsize=8)

    plt.tight_layout()
    path = OUT_DIR / 'fig_B2_alpha_panel.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path.name}')


# =============================================================================
# Fig B3 — 相对误差条形图
# =============================================================================
def fig_B3_error_bar():
    u_list, err_list, nf_pidl_list, nf_fem_list = [], [], [], []
    for umax in sorted(PIDL_DIRS):
        try:
            _, _, _, Nf_pidl = load_pidl(umax)
        except FileNotFoundError:
            continue
        try:
            _, Nf_fem = load_fem(umax)
        except FileNotFoundError:
            print(f'  [skip FEM] U_max={umax}: CSV not found')
            continue
        err = 100.0 * (Nf_pidl - Nf_fem) / Nf_fem
        u_list.append(umax)
        err_list.append(err)
        nf_pidl_list.append(Nf_pidl)
        nf_fem_list.append(Nf_fem)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.suptitle('PIDL 8×400 vs FEM — N_f comparison', fontsize=11, fontweight='bold')

    xlabels = [f'{u:.2f}' for u in u_list]
    cols = [COLORS[u] for u in u_list]

    # Error bars
    bars = ax1.bar(xlabels, err_list, color=cols, alpha=0.85,
                   edgecolor='k', linewidth=0.8)
    ax1.axhline(0, color='k', lw=1.0)
    for bar, val in zip(bars, err_list):
        y_pos = val + 0.3 if val >= 0 else val - 2.5
        ax1.text(bar.get_x() + bar.get_width()/2, y_pos,
                 f'{val:+.1f}%', ha='center', va='bottom', fontsize=9)
    ax1.set_xlabel('$U_{max}$', fontsize=12)
    ax1.set_ylabel('Relative error $(N_{f,PIDL} - N_{f,FEM}) / N_{f,FEM}$ (%)', fontsize=10)
    ax1.set_title('PIDL underestimates N_f at low U_max\n'
                  '(dispersed degradation → faster global stiffness loss)', fontsize=9)
    ax1.grid(True, axis='y', alpha=0.3)

    # Absolute N_f
    x = np.arange(len(u_list))
    w = 0.35
    ax2.bar(x - w/2, nf_fem_list,  w, label='FEM',      color='#e41a1c', alpha=0.8, edgecolor='k', lw=0.7)
    ax2.bar(x + w/2, nf_pidl_list, w, label='PIDL 8×400', color='#377eb8', alpha=0.8, edgecolor='k', lw=0.7)
    ax2.set_xticks(x)
    ax2.set_xticklabels(xlabels)
    ax2.set_xlabel('$U_{max}$', fontsize=12)
    ax2.set_ylabel('$N_f$', fontsize=12)
    ax2.set_title('Absolute N_f comparison', fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    path = OUT_DIR / 'fig_B3_error_bar.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path.name}')


# =============================================================================
# 主程序
# =============================================================================
if __name__ == '__main__':
    print('=== Fig B1: Full S-N curve ===')
    fig_B1_sn_full()

    print('\n=== Fig B2: alpha_bar panel (all U_max) ===')
    fig_B2_alpha_panel()

    print('\n=== Fig B3: Error bar chart ===')
    fig_B3_error_bar()

    print(f'\nAll figures saved to: {OUT_DIR}')
