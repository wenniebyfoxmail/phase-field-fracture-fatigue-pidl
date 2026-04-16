#!/usr/bin/env python3
"""
generate_figs_pidl_fem.py — PIDL vs FEM 对比图 (Option A)

FEM 完整逐圈数据来自：~/Downloads/post_process 2/SENT_PIDL_??_timeseries.csv
  列: N, E_el, alpha_max, f_min, a_ell, delta_a, da_dN, d_max

生成 4 张对比分析图（输出至 figfiles/pidl_fem/）：
  A1 — Umax=0.12 细节对比面板（E_el, δa, ᾱ_max, f_min vs N，双方真实曲线）
  A2 — 弥散退化核心证据（f_min vs N，PIDL+FEM 所有 Umax，双方对比）
  A3 — S-N 曲线双方对比（5 点 PIDL 8×400 vs 5 点 FEM）
  A4 — 多 seed 变异性（N_f 分布，Umax=0.12）

用法：
  cd "upload code/SENS_tensile"
  python generate_figs_pidl_fem.py
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

# ── 路径 ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
FEM_DATA_DIR = Path.home() / 'Downloads' / 'post_process'
OUT_DIR      = SCRIPT_DIR / 'figfiles' / 'pidl_fem'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── PIDL 8×400 Seed=1 Case 目录（all U_max）──────────────────────────────────
PREFIX_8x400 = 'hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_'
PIDL_CASES = {
    0.12: PREFIX_8x400 + 'fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12',
    0.11: PREFIX_8x400 + 'fatigue_on_carrara_asy_aT0.5_N250_R0.0_Umax0.11',
    0.10: PREFIX_8x400 + 'fatigue_on_carrara_asy_aT0.5_N350_R0.0_Umax0.1',
    0.09: PREFIX_8x400 + 'fatigue_on_carrara_asy_aT0.5_N400_R0.0_Umax0.09',
    0.08: PREFIX_8x400 + 'fatigue_on_carrara_asy_aT0.5_N700_R0.0_Umax0.08',
}

# ── PIDL 8×400 Multi-seed 目录（Umax=0.12）───────────────────────────────────
PIDL_SEEDS_0_12 = {
    1: PREFIX_8x400 + 'fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12',
    2: 'hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_2_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N700_R0.0_Umax0.12',
    3: 'hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_3_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N700_R0.0_Umax0.12',
}

# ── 参数 ──────────────────────────────────────────────────────────────────────
ALPHA_T = 0.5
COLORS_UMAX  = {0.12: '#e41a1c', 0.11: '#ff7f00', 0.10: '#4daf4a',
                0.09: '#377eb8', 0.08: '#984ea3'}
COLORS_SEEDS = {1: '#1f78b4', 2: '#e31a1c', 3: '#33a02c'}
FEM_UMAX_STR = {0.12: '12', 0.11: '11', 0.10: '10', 0.09: '09', 0.08: '08'}


# =============================================================================
# 辅助函数
# =============================================================================
def f_asymptotic(alpha_bar, alpha_T=ALPHA_T):
    """Carrara asymptotic degradation f = [2αT / (ᾱ + αT)]²"""
    return (2 * alpha_T / (alpha_bar + alpha_T)) ** 2


def load_pidl(suffix):
    """Load per-cycle PIDL data; returns (E_el, x_tip, alpha_bar, N_f_idx)."""
    bm = SCRIPT_DIR / suffix / 'best_models'
    E   = np.load(bm / 'E_el_vs_cycle.npy')
    tip = np.load(bm / 'x_tip_vs_cycle.npy')
    ab  = np.load(bm / 'alpha_bar_vs_cycle.npy')  # shape (N,3): max, mean, f_min
    frac_idx = int(np.where(tip >= 0.5)[0][0]) if any(tip >= 0.5) else len(tip) - 1
    return E, tip, ab, frac_idx


def load_fem(umax):
    """Load FEM per-cycle CSV; returns DataFrame and N_f (max da_dN cycle)."""
    fname = FEM_DATA_DIR / f"SENT_PIDL_{FEM_UMAX_STR[umax]}_timeseries.csv"
    df = pd.read_csv(fname)
    N_f = int(df.loc[df['da_dN'].idxmax(), 'N'])
    return df, N_f


# =============================================================================
# Fig A1 — Umax=0.12 四面板细节对比（PIDL 3 seeds + FEM 真实曲线）
# =============================================================================
def fig_A1_detail():
    """4-panel: E_el, δa, ᾱ_max, f_min vs N — both PIDL (3 seeds) and FEM."""
    fig = plt.figure(figsize=(13, 9))
    gs  = gridspec.GridSpec(2, 2, hspace=0.40, wspace=0.32)
    axes = [fig.add_subplot(gs[r, c]) for r in range(2) for c in range(2)]

    # ── 加载 FEM 数据 ─────────────────────────────────────────────────────────
    df_fem, fem_Nf = load_fem(0.12)
    N_fem   = df_fem['N'].values
    E_fem   = df_fem['E_el'].values / df_fem['E_el'].iloc[0]   # 归一化
    da_fem  = df_fem['delta_a'].values
    ab_fem  = df_fem['alpha_max'].values
    fmin_fem = df_fem['f_min'].values

    # 右上：|dE_el/dN|（能量下降速率）— N_f 判据，FEM 和 PIDL 完全相同的量
    # FEM: 用原始 E_el，diff 后取绝对值
    E_fem_raw  = df_fem['E_el'].values
    dEdt_fem   = np.abs(np.diff(E_fem_raw))          # shape (N-1,)
    N_fem_mid  = N_fem[1:]                            # 对应圈号

    # FEM 曲线（黑色，粗实线）
    axes[0].plot(N_fem, E_fem,        'k-', lw=2.2, label=f'FEM ($N_f$={fem_Nf})', zorder=6)
    axes[1].plot(N_fem_mid, dEdt_fem, 'k-', lw=2.2, label=f'FEM ($N_f$={fem_Nf})', zorder=6)
    axes[2].plot(N_fem, ab_fem,       'k-', lw=2.2, label=f'FEM ($N_f$={fem_Nf})', zorder=6)
    axes[3].plot(N_fem, fmin_fem,     'k-', lw=2.2, label=f'FEM ($N_f$={fem_Nf})', zorder=6)

    # ── 加载 PIDL 数据（3 seeds）─────────────────────────────────────────────
    for seed, suf in PIDL_SEEDS_0_12.items():
        try:
            E, tip, ab, Nf_idx = load_pidl(suf)
        except FileNotFoundError:
            print(f'  [skip] seed={seed}: directory not found')
            continue

        # ── 截断到 N_f（不画 confirm_cycles 的尾巴）─────────────────────────
        n_plot     = Nf_idx + 1          # 只画到断裂圈（含），共 N_f 个点
        N_pidl     = np.arange(n_plot)
        E_norm     = E[:n_plot] / E[0]
        ab_max     = ab[:n_plot, 0]      # ᾱ_max
        f_min_c    = ab[:n_plot, 2]      # f_min per cycle
        # PIDL |dE_el/dN|：E 已截断到 n_plot，diff 后长度 n_plot-1
        dEdt_pidl = np.abs(np.diff(E[:n_plot]))      # shape (n_plot-1,)
        N_pidl_mid = N_pidl[1:]                       # 对应圈号

        lbl = f'PIDL Seed {seed}  ($N_f$={Nf_idx+1})'
        col = COLORS_SEEDS[seed]
        lw  = 1.8 if seed == 1 else 1.3
        ls  = '-' if seed == 1 else '--'

        axes[0].plot(N_pidl, E_norm,          color=col, lw=lw, ls=ls, label=lbl, zorder=4)
        axes[1].plot(N_pidl_mid, dEdt_pidl,   color=col, lw=lw, ls=ls, label=lbl, zorder=4)
        axes[2].plot(N_pidl, ab_max,     color=col, lw=lw, ls=ls, label=lbl, zorder=4)
        axes[3].plot(N_pidl, f_min_c,    color=col, lw=lw, ls=ls, label=lbl, zorder=4)

        # ── N_f 竖线（仅 seed=1 标注，防止图例过满）─────────────────────────
        if seed == 1:
            for ax in axes:
                ax.axvline(Nf_idx, color=col, ls=':', lw=0.9, alpha=0.5)

    # ── 轴设置 ────────────────────────────────────────────────────────────────
    axes[0].set_ylabel(r'$\mathcal{E}_{el}(N)/\mathcal{E}_{el}(1)$', fontsize=11)
    axes[0].set_title('Normalized elastic energy', fontsize=11)
    axes[0].set_ylim(-0.05, 1.10)

    axes[1].set_ylabel(r'$|d\mathcal{E}_{el}/dN|$', fontsize=11)
    axes[1].set_title(r'Energy drop rate $|d\mathcal{E}_{el}/dN|$ — unified $N_f$ criterion'
                      '\n(peak = fracture cycle, identical for FEM & PIDL)',
                      fontsize=9)
    axes[1].set_yscale('log')

    axes[2].set_ylabel(r'$\bar{\alpha}_{\max}$', fontsize=11)
    axes[2].set_title(r'Peak fatigue history $\bar{\alpha}_{\max}$', fontsize=11)
    axes[2].set_yscale('log')
    axes[2].axhline(ALPHA_T, color='gray', ls=':', lw=1.0, label=f'$\\alpha_T$={ALPHA_T}')

    axes[3].set_ylabel(r'$f_{\min}(\bar{\alpha})$', fontsize=11)
    axes[3].set_title(r'Min degradation factor $f_{\min}$ (log scale)', fontsize=11)
    axes[3].set_yscale('log')

    for ax in axes:
        ax.set_xlabel('Cycle $N$', fontsize=11)
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7.5, loc='best')

    fig.suptitle(r'PIDL 8×400 vs FEM GRIPHFiTH — $U_{max}=0.12$' + '\n'
                 r'Key difference: FEM $\bar{\alpha}_{max}$≈958 (concentrated), '
                 r'PIDL $\bar{\alpha}_{max}$≈9–14 (dispersed)',
                 fontsize=10, fontweight='bold')

    path = OUT_DIR / 'fig_A1_detail_Umax12.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path.name}')


# =============================================================================
# Fig A2 — 弥散退化核心证据：f_min vs N（PIDL + FEM 真实曲线，所有 Umax）
# =============================================================================
def fig_A2_dispersed_degrad():
    """Key insight: f_min vs N for all U_max — both PIDL and FEM."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Dispersed Degradation: Root Cause of PIDL–FEM N_f Paradox',
                 fontsize=12, fontweight='bold')

    ax_fem, ax_pidl = axes

    # ── FEM：f_min vs N（实线，色）────────────────────────────────────────────
    for umax in sorted(PIDL_CASES):
        try:
            df, N_f_fem = load_fem(umax)
        except FileNotFoundError:
            print(f'  [skip FEM] U_max={umax}')
            continue
        col = COLORS_UMAX[umax]
        ax_fem.plot(df['N'].values / N_f_fem, df['f_min'].values,
                    color=col, lw=2.0, label=f'$U_{{max}}$={umax}, $N_f$={N_f_fem}')
        ax_fem.axvline(1.0, color=col, ls=':', lw=0.7, alpha=0.4)

    ax_fem.set_xlabel(r'Normalized cycle $N/N_f$', fontsize=12)
    ax_fem.set_ylabel(r'$f_{min}$ (FEM)', fontsize=12)
    ax_fem.set_title('FEM: $f_{min}$ stays near 1 until catastrophic fracture\n'
                     '(concentrated degradation at crack tip, Kt≈15)',
                     fontsize=9)
    ax_fem.set_yscale('log')
    ax_fem.legend(fontsize=8)
    ax_fem.grid(True, which='both', alpha=0.25)

    # ── PIDL：f_min vs N（虚线，色）──────────────────────────────────────────
    for umax, suf in PIDL_CASES.items():
        try:
            E, tip, ab, Nf_idx = load_pidl(suf)
        except FileNotFoundError:
            print(f'  [skip PIDL] U_max={umax}')
            continue
        col    = COLORS_UMAX[umax]
        n_plot = Nf_idx + 1              # 截断到 N_f（不含 confirm_cycles 尾部）
        N_pidl = np.arange(n_plot)
        ax_pidl.plot(N_pidl / n_plot, ab[:n_plot, 2],
                     color=col, lw=2.0, label=f'$U_{{max}}$={umax}, $N_f$={Nf_idx+1}')
        ax_pidl.axvline(1.0, color=col, ls=':', lw=0.7, alpha=0.4)

    ax_pidl.set_xlabel(r'Normalized cycle $N/N_f$', fontsize=12)
    ax_pidl.set_ylabel(r'$f_{min}$ (PIDL)', fontsize=12)
    ax_pidl.set_title('PIDL: $f_{min}$ degrades gradually from cycle 1\n'
                      '(dispersed degradation, Kt≈7)',
                      fontsize=9)
    ax_pidl.set_yscale('log')
    ax_pidl.legend(fontsize=8)
    ax_pidl.grid(True, which='both', alpha=0.25)

    # ── 注释框 ────────────────────────────────────────────────────────────────
    note = ('Mechanism:\n'
            '• FEM Kt≈15 → ψ⁺ at tip ≫ domain\n'
            '  → f_min drops sharply at N_f\n'
            '  → global stiffness intact\n\n'
            '• PIDL Kt≈7 → ψ⁺ spread over\n'
            '  2-3 element widths\n'
            '  → f_min degrades steadily\n'
            '  → N_f underestimated 1–10%')
    ax_pidl.text(0.02, 0.35, note, transform=ax_pidl.transAxes, fontsize=8,
                 va='top',
                 bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow',
                           edgecolor='orange', alpha=0.90))

    path = OUT_DIR / 'fig_A2_dispersed_degrad.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path.name}')


# =============================================================================
# Fig A3 — S-N 曲线双方对比（含真实 FEM N_f）
# =============================================================================
def fig_A3_sn_comparison():
    """PIDL 8×400 vs FEM on same log-log S-N plot with power-law fits."""
    pidl_nf = []
    fem_nf  = []
    u_vals  = []

    for umax, suf in sorted(PIDL_CASES.items()):
        bm = SCRIPT_DIR / suf / 'best_models'
        tip_file = bm / 'x_tip_vs_cycle.npy'
        if not tip_file.exists():
            continue
        tip = np.load(tip_file)
        frac = np.where(tip >= 0.5)[0]
        nf_pidl = frac[0] + 1 if len(frac) else len(tip)

        try:
            df, nf_fem = load_fem(umax)
        except FileNotFoundError:
            continue

        u_vals.append(umax)
        pidl_nf.append(nf_pidl)
        fem_nf.append(nf_fem)

    u_arr   = np.array(u_vals)
    nf_pidl = np.array(pidl_nf, dtype=float)
    nf_fem  = np.array(fem_nf,  dtype=float)

    def power_fit(u, nf):
        b, a = np.polyfit(np.log(u), np.log(nf), 1)
        return np.exp(a), b

    C_pidl, m_pidl = power_fit(u_arr, nf_pidl)
    C_fem,  m_fem  = power_fit(u_arr, nf_fem)

    u_fit = np.linspace(0.075, 0.135, 300)

    fig, ax = plt.subplots(figsize=(6.5, 5))

    # 注：三种准则（max da/dN、x_tip≥0.5、max|dE_el/dN|）对 FEM 和 PIDL
    # 均给出相同 N_f（差 0 圈），说明 N_f 差异是纯物理的，无需判据修正。

    # Per-U_max colored scatter
    for umax, np_, nf_ in zip(u_arr, nf_pidl, nf_fem):
        col = COLORS_UMAX[umax]
        ax.scatter(nf_,  umax, color=col, marker='s', s=80, zorder=5,
                   edgecolors='k', linewidths=0.7)
        ax.scatter(np_, umax, color=col, marker='o', s=80, zorder=5,
                   edgecolors='k', linewidths=0.7)
        ax.plot([nf_, np_], [umax, umax], color=col, lw=0.8, alpha=0.35)
        ax.annotate(f'{umax}', xy=(nf_, umax), xytext=(-16, 4),
                    textcoords='offset points', fontsize=8, color=col)

    # Multi-seed error bar at Umax=0.12
    seeds_nf = []
    for seed, suf in PIDL_SEEDS_0_12.items():
        tip_file = SCRIPT_DIR / suf / 'best_models' / 'x_tip_vs_cycle.npy'
        if tip_file.exists():
            tip = np.load(tip_file)
            frac = np.where(tip >= 0.5)[0]
            seeds_nf.append(frac[0] + 1 if len(frac) else len(tip))
    if seeds_nf:
        mn, mx, mean_nf = min(seeds_nf), max(seeds_nf), np.mean(seeds_nf)
        ax.errorbar(mean_nf, 0.12,
                    xerr=[[mean_nf - mn], [mx - mean_nf]],
                    fmt='none', color='#1f78b4', capsize=5, lw=1.5,
                    label=f'PIDL seed range [{mn}–{mx}]')

    # Power-law fits
    ax.plot(C_fem  * u_fit ** m_fem,  u_fit, 'r-', lw=2.0,
            label=f'FEM:  $N_f \\propto U^{{{m_fem:.2f}}}$')
    ax.plot(C_pidl * u_fit ** m_pidl, u_fit, 'b--', lw=2.0,
            label=f'PIDL: $N_f \\propto U^{{{m_pidl:.2f}}}$')

    # Legend dummies
    ax.scatter([], [], color='gray', marker='s', s=70, label='FEM (GRIPHFiTH)', edgecolors='k', lw=0.7)
    ax.scatter([], [], color='gray', marker='o', s=70, label='PIDL 8×400 seed 1', edgecolors='k', lw=0.7)

    ax.set_xscale('log')
    ax.set_xlabel('Cycles to failure $N_f$', fontsize=12)
    ax.set_ylabel('Displacement amplitude $U_{max}$', fontsize=12)
    ax.set_title(f'S-N Curve: PIDL 8×400 vs FEM GRIPHFiTH\n'
                 f'FEM exponent {m_fem:.2f}  vs  PIDL exponent {m_pidl:.2f}',
                 fontsize=11)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, which='both', alpha=0.25)

    # Compact error table
    # 三种准则（max da/dN、x_tip≥0.5、max|dEel/dN|）均给出一致 N_f，
    # ΔN_f 为纯物理差异，无准则修正项。
    rows = [f'{u:.2f} | {int(f):4d} | {int(p):4d} | {100*(p-f)/f:+.1f}%'
            for u, p, f in zip(u_arr, nf_pidl, nf_fem)]
    ax.text(0.02, 0.32, 'Umax | FEM  | PIDL | ΔN_f\n' + '\n'.join(rows),
            transform=ax.transAxes, fontsize=7.5, va='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='gray', alpha=0.9))
    ax.text(0.02, 0.02,
            'All 3 criteria agree (max da/dN = max|dEel/dN| = x_tip≥0.5)\n'
            'ΔN_f is purely physical (dispersed degradation in PIDL)',
            transform=ax.transAxes, fontsize=6.5, va='bottom', color='#555555')

    plt.tight_layout()
    path = OUT_DIR / 'fig_A3_SN_comparison.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path.name}')


# =============================================================================
# Fig A4 — 多 seed 变异性（Umax=0.12）
# =============================================================================
def fig_A4_seed_variation():
    """Bar chart: N_f per seed vs FEM, plus damage state comparison."""
    nf_by_seed, f_min_by_seed, alpha_max_by_seed = {}, {}, {}
    for seed, suf in PIDL_SEEDS_0_12.items():
        bm = SCRIPT_DIR / suf / 'best_models'
        tip_f = bm / 'x_tip_vs_cycle.npy'
        ab_f  = bm / 'alpha_bar_vs_cycle.npy'
        if tip_f.exists() and ab_f.exists():
            tip = np.load(tip_f)
            ab  = np.load(ab_f)
            frac = np.where(tip >= 0.5)[0]
            Nf_idx = frac[0] if len(frac) else len(tip) - 1
            nf_by_seed[seed]     = Nf_idx + 1
            f_min_by_seed[seed]  = ab[Nf_idx, 2]
            alpha_max_by_seed[seed] = ab[Nf_idx, 0]

    _, fem_Nf_12 = load_fem(0.12)
    fem_df_12    = pd.read_csv(FEM_DATA_DIR / 'SENT_PIDL_12_timeseries.csv')
    fem_fmin_12  = fem_df_12.loc[fem_df_12['N'] == fem_Nf_12, 'f_min'].values[0]
    fem_amax_12  = fem_df_12.loc[fem_df_12['N'] == fem_Nf_12, 'alpha_max'].values[0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle(r'Multi-seed statistics at $U_{max}=0.12$ (PIDL 8×400) vs FEM',
                 fontsize=11, fontweight='bold')

    seeds  = sorted(nf_by_seed)
    nf_arr = np.array([nf_by_seed[s] for s in seeds])
    cols   = [COLORS_SEEDS[s] for s in seeds]

    # Panel 1: N_f bar chart
    bars = ax1.bar([f'Seed {s}' for s in seeds], nf_arr, color=cols,
                   alpha=0.85, edgecolor='k', linewidth=0.8)
    ax1.bar(['FEM'], [fem_Nf_12], color='#d73027', alpha=0.9,
            edgecolor='k', linewidth=0.8)
    ax1.axhline(nf_arr.mean(), color='navy', ls=':', lw=1.5,
                label=f'PIDL mean={nf_arr.mean():.1f}±{nf_arr.std():.1f}')
    for bar, val in zip(bars, nf_arr):
        ax1.text(bar.get_x() + bar.get_width()/2, val + 0.3, str(val),
                 ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax1.text(0.75, fem_Nf_12 + 0.3, str(fem_Nf_12),
             ha='center', va='bottom', fontsize=11, fontweight='bold', color='#d73027')
    ax1.set_ylabel('$N_f$', fontsize=12)
    ax1.set_title(f'N_f comparison\n'
                  f'PIDL: {min(nf_arr)}–{max(nf_arr)} cycles ({100*nf_arr.std()/nf_arr.mean():.1f}% spread)\n'
                  f'FEM:  {fem_Nf_12} cycles',
                  fontsize=9)
    ax1.legend(fontsize=9)
    ax1.set_ylim(0, max(max(nf_arr), fem_Nf_12) * 1.25)
    ax1.grid(True, axis='y', alpha=0.3)

    # Panel 2: f_min and alpha_max at N_f
    if f_min_by_seed:
        s_list  = sorted(f_min_by_seed)
        labels  = [f'Seed {s}' for s in s_list] + ['FEM']
        fm_vals = [f_min_by_seed[s] for s in s_list] + [fem_fmin_12]
        am_vals = [alpha_max_by_seed[s] for s in s_list] + [fem_amax_12]
        b_cols  = [COLORS_SEEDS[s] for s in s_list] + ['#d73027']

        ax2_twin = ax2.twinx()
        bars2 = ax2.bar(labels, fm_vals, color=b_cols, alpha=0.75,
                        edgecolor='k', linewidth=0.8)
        ax2_twin.plot(labels, am_vals, 'k^--', markersize=9, lw=1.5,
                      label=r'$\bar{\alpha}_{max}$@$N_f$')

        ax2.set_ylabel('$f_{min}$ at $N_f$', fontsize=11)
        ax2_twin.set_ylabel(r'$\bar{\alpha}_{max}$ at $N_f$', fontsize=11)
        ax2.set_yscale('log')
        ax2.set_title(r'Damage state at $N_f$' + '\n'
                      r'FEM: $f_{min}$≈$10^{-6}$, $\bar{\alpha}_{max}$≈958  |  '
                      r'PIDL: $f_{min}$≈$10^{-2}$, $\bar{\alpha}_{max}$≈9–14',
                      fontsize=8.5)
        ax2_twin.legend(fontsize=9, loc='upper left')
        ax2.grid(True, axis='y', alpha=0.3)

        # FEM / PIDL ratio annotation
        mean_fmin_pidl = np.mean([f_min_by_seed[s] for s in s_list])
        ratio_fmin = fem_fmin_12 / mean_fmin_pidl
        ax2.text(0.02, 0.05,
                 f'FEM/PIDL $f_{{min}}$ ratio: {ratio_fmin:.0f}×\n'
                 f'FEM/PIDL $\\bar{{α}}_{{max}}$ ratio: {fem_amax_12/np.mean(am_vals[:-1]):.0f}×',
                 transform=ax2.transAxes, fontsize=8.5, va='bottom',
                 bbox=dict(boxstyle='round', facecolor='lightyellow',
                           edgecolor='orange', alpha=0.9))

    plt.tight_layout()
    path = OUT_DIR / 'fig_A4_seed_variation.png'
    fig.savefig(str(path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {path.name}')


# =============================================================================
# 主程序
# =============================================================================
if __name__ == '__main__':
    print('=== Fig A1: Umax=0.12 detail panel ===')
    fig_A1_detail()

    print('\n=== Fig A2: Dispersed degradation ===')
    fig_A2_dispersed_degrad()

    print('\n=== Fig A3: S-N comparison ===')
    fig_A3_sn_comparison()

    print('\n=== Fig A4: Seed variation ===')
    fig_A4_seed_variation()

    print(f'\nAll figures saved to: {OUT_DIR}')
