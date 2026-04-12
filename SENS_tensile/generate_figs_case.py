#!/usr/bin/env python3
"""
generate_figs_case.py — 单个 case 的完整输出图

每个 case 目录下生成 figfiles/ 子目录，包含：
  case_fig1_Eel_vs_N.png     — E_el 归一化退化曲线
  case_fig2_aN_curve.png     — 裂纹长度 a vs cycle
  case_fig3_alpha_bar.png    — ᾱ 累积 & f(ᾱ) 退化因子
  case_fig4_alpha_fields.png — α 场快照（关键圈数）

用法：
  python generate_figs_case.py <case_dir>
  python generate_figs_case.py hl_8_Neurons_400_..._Umax0.12

如果不传参数，对当前目录下所有 hl_ 开头的 cyclic case 批量生成。
"""

import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def make_case_figs(case_dir: Path, alpha_T: float = 0.5):
    bm  = case_dir / 'best_models'
    out = case_dir / 'figfiles'
    out.mkdir(exist_ok=True)

    # ── 读取数据 ──────────────────────────────────────────────────────────────
    E_path  = bm / 'E_el_vs_cycle.npy'
    tip_path = bm / 'x_tip_vs_cycle.npy'
    ab_path  = bm / 'alpha_bar_vs_cycle.npy'

    if not E_path.exists() or not tip_path.exists():
        print(f'  [skip] missing E_el or x_tip in {case_dir.name}')
        return

    E   = np.load(str(E_path))
    tip = np.load(str(tip_path))
    N   = np.arange(len(E))
    E_norm = E / E[0]

    N_f_idx = int(np.where(tip >= 0.46)[0][0]) if any(tip >= 0.46) else len(tip) - 1
    N_f     = N_f_idx + 1

    # ── Fig 1: E_el 归一化 ────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(N, E_norm, 'steelblue', lw=2, label=r'$\mathcal{E}_{el}(N)/\mathcal{E}_{el}(0)$')
    n50 = int(np.where(E < 0.5 * E[0])[0][0]) + 1 if any(E < 0.5 * E[0]) else None
    n20 = int(np.where(E < 0.2 * E[0])[0][0]) + 1 if any(E < 0.2 * E[0]) else None
    if n50: ax.axhline(0.5, color='royalblue', ls='--', lw=1, label=f'50%% (N={n50})')
    if n20: ax.axhline(0.2, color='navy',      ls='--', lw=1, label=f'20%% (N={n20})')
    ax.axvline(N_f_idx, color='tomato', ls=':', lw=1.5, label=f'$N_f$={N_f} (a≥0.46)')
    ax.set_xlabel('Cycle $N$'); ax.set_ylabel(r'$\mathcal{E}_{el}(N)/\mathcal{E}_{el}(0)$')
    ax.set_title(f'Normalised elastic energy — {case_dir.name[:30]}...')
    ax.set_ylim(-0.05, 1.1); ax.legend(fontsize=9); ax.grid(alpha=0.3)
    plt.tight_layout()
    p = out / 'case_fig1_Eel_vs_N.png'
    fig.savefig(str(p), dpi=150, bbox_inches='tight'); plt.close(fig)
    print(f'  Saved: {p.name}')

    # ── Fig 2: a-N curve ──────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(N[:len(tip)], tip, 'steelblue', lw=2, label='crack length $a$')
    ax.axhline(0.46, color='tomato',    ls='--', lw=1.2, label='Fracture threshold $a$=0.46')
    ax.axhline(0.02, color='lightgray', ls=':',  lw=1.0, label='Initiation threshold $a$=0.02')
    ax.axvline(N_f_idx, color='tomato', ls=':', lw=1.5, label=f'$N_f$={N_f}')
    ax.set_xlabel('Cycle $N$'); ax.set_ylabel(r'Crack length $a$ ($L^\infty$)')
    ax.set_title(f'a-N curve — {case_dir.name[:30]}...')
    ax.set_ylim(-0.02, 0.55); ax.legend(fontsize=9); ax.grid(alpha=0.3)
    plt.tight_layout()
    p = out / 'case_fig2_aN_curve.png'
    fig.savefig(str(p), dpi=150, bbox_inches='tight'); plt.close(fig)
    print(f'  Saved: {p.name}')

    # ── Fig 3: alpha_bar & f ──────────────────────────────────────────────────
    if ab_path.exists():
        ab = np.load(str(ab_path))
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        fig.suptitle(f'Fatigue history — {case_dir.name[:40]}...', fontsize=10)

        ax = axes[0]
        ax.plot(N[:len(ab)], ab[:, 0], 'tomato',    lw=2, label=r'$\bar{\alpha}_{\max}$')
        ax.plot(N[:len(ab)], ab[:, 1], 'steelblue', lw=2, label=r'$\bar{\alpha}_{\rm mean}$')
        ax.axhline(alpha_T, color='k', ls='--', lw=1.2, label=f'$\\alpha_T$={alpha_T}')
        ax.axvline(N_f_idx, color='tomato', ls=':', lw=1.5, label=f'$N_f$={N_f}')
        ax.set_xlabel('Cycle $N$'); ax.set_ylabel(r'$\bar{\alpha}$')
        ax.set_title(r'Fatigue accumulation $\bar{\alpha}$')
        ax.legend(fontsize=9); ax.grid(alpha=0.3)

        ax = axes[1]
        ax.plot(N[:len(ab)], ab[:, 2], 'darkorange', lw=2, label=r'$f_{\min}(\bar{\alpha})$')
        ax.axhline(1.0, color='k', ls='--', lw=0.8, alpha=0.5)
        ax.axvline(N_f_idx, color='tomato', ls=':', lw=1.5, label=f'$N_f$={N_f}')
        ax.set_xlabel('Cycle $N$'); ax.set_ylabel(r'$f(\bar{\alpha})$')
        ax.set_title(r'Degradation factor $f(\bar{\alpha})$ [eff. $G_c = f \cdot G_c$]')
        ax.set_ylim(-0.02, 1.08); ax.legend(fontsize=9); ax.grid(alpha=0.3)

        plt.tight_layout()
        p = out / 'case_fig3_alpha_bar.png'
        fig.savefig(str(p), dpi=150, bbox_inches='tight'); plt.close(fig)
        print(f'  Saved: {p.name}')
    else:
        print(f'  [skip fig3] alpha_bar_vs_cycle.npy not found')

    # ── Fig 4: α 场快照（关键圈数的 npy）────────────────────────────────────
    snap_dir = case_dir / 'alpha_snapshots'
    npy_files = sorted(snap_dir.glob('alpha_cycle_*.npy')) if snap_dir.exists() else []

    if npy_files:
        # 选最多 6 张：均匀采样 + 最后一张
        indices = np.linspace(0, len(npy_files) - 1, min(6, len(npy_files)), dtype=int)
        selected = [npy_files[i] for i in indices]
        if npy_files[-1] not in selected:
            selected[-1] = npy_files[-1]

        n_plots = len(selected)
        fig, axes = plt.subplots(1, n_plots, figsize=(3.5 * n_plots, 3.5))
        if n_plots == 1:
            axes = [axes]
        fig.suptitle(f'α field snapshots — {case_dir.name[:40]}...', fontsize=10)

        for ax, npy_f in zip(axes, selected):
            cyc_num = int(npy_f.stem.split('_')[-1])
            data = np.load(str(npy_f))   # (N_nodes, 3): [x, y, alpha]
            tpc = ax.tripcolor(data[:, 0], data[:, 1], data[:, 2],
                               vmin=0, vmax=1, cmap='plasma')
            ax.set_aspect('equal')
            ax.set_title(f'Cycle {cyc_num}', fontsize=9)
            ax.set_xticks([]); ax.set_yticks([])
            plt.colorbar(tpc, ax=ax, fraction=0.046, pad=0.04, label='α')

        plt.tight_layout()
        p = out / 'case_fig4_alpha_fields.png'
        fig.savefig(str(p), dpi=150, bbox_inches='tight'); plt.close(fig)
        print(f'  Saved: {p.name}  ({n_plots} snapshots)')
    else:
        print(f'  [skip fig4] no alpha_cycle_*.npy in alpha_snapshots/')


# =============================================================================
# 主程序
# =============================================================================
if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 指定 case 目录
        targets = [SCRIPT_DIR / sys.argv[1]]
    else:
        # 批量：所有 hl_ 开头且含 fatigue_on 的 cyclic case
        targets = sorted([
            d for d in SCRIPT_DIR.iterdir()
            if d.is_dir()
            and d.name.startswith('hl_')
            and 'fatigue_on' in d.name
            and 'mono' not in d.name        # 跳过 monotonic case
            and (d / 'best_models' / 'E_el_vs_cycle.npy').exists()
        ])

    if not targets:
        print('No cases found.')
        sys.exit(0)

    for case_dir in targets:
        print(f'\n=== {case_dir.name} ===')
        make_case_figs(case_dir)

    print('\nDone.')
