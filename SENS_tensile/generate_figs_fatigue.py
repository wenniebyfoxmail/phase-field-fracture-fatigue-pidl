#!/usr/bin/env python3
"""
generate_figs_fatigue.py
疲劳 Case 专用后处理图：
  Fig 1 – α 场演化面板图（最多 7 帧，含完全断裂帧）
  Fig 2 – E_el vs N 曲线（含完全断裂标注）

用法（在 upload code/SENS_tensile/ 目录下运行）:
  python generate_figs_fatigue.py              # 使用当前 config.py 中的 model_path
  python generate_figs_fatigue.py <model_dir>  # 手动指定目录

完全断裂判据: 首圈 E_el < 10% × E_el_max（与训练停止逻辑一致）
"""
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pathlib import Path

# ── 解析 model_dir ──────────────────────────────────────────────────────────
if len(sys.argv) > 1:
    model_dir = Path(sys.argv[1])
else:
    # 从当前目录的 config.py 读取 model_path
    sys.path.insert(0, str(Path(__file__).parent))
    from config import model_path
    model_dir = Path(model_path)

print(f"[Info] model_dir = {model_dir}")

snapshot_dir = model_dir / 'alpha_snapshots'
E_el_file    = model_dir / 'best_models' / 'E_el_vs_cycle.npy'
figdir       = model_dir / 'figfiles' / 'pngfigs'
figdir.mkdir(parents=True, exist_ok=True)

# ── 1. 加载 E_el 数据 & 确定完全断裂帧 ─────────────────────────────────────
E_THRESHOLD = 0.10   # 10% of E_el_max → 完全断裂判据

if not E_el_file.exists():
    print(f"[WARN] E_el_vs_cycle.npy not found. Skipping E_el plot.")
    E_el = None
    frac_cycle = None
else:
    E_el = np.load(str(E_el_file))
    E_el_max = float(E_el.max())
    below = np.where(E_el / E_el_max < E_THRESHOLD)[0]
    frac_cycle = int(below[0]) if len(below) > 0 else None
    print(f"E_el_max = {E_el_max:.6f}  (at cycle {int(E_el.argmax())})")
    if frac_cycle is not None:
        print(f"Complete fracture: cycle {frac_cycle}  "
              f"(E_el drops to {E_el[frac_cycle]/E_el_max*100:.1f}% of max)")
    else:
        print("Complete fracture not detected within recorded cycles.")

# ── 2. 确定面板用的 cycle 列表 ───────────────────────────────────────────────
panel_cycles_base = [0, 20, 40, 60, 80, 100]

# 如果完全断裂帧已在列表中就不重复加
if frac_cycle is not None and frac_cycle not in panel_cycles_base:
    panel_cycles = panel_cycles_base + [frac_cycle]
elif frac_cycle is not None:
    panel_cycles = panel_cycles_base      # 已在列表里，不重复
else:
    panel_cycles = panel_cycles_base

# 过滤掉实际不存在 snapshot 的帧
available = []
for cyc in panel_cycles:
    p = snapshot_dir / f'alpha_cycle_{cyc:04d}.png'
    if p.exists():
        available.append(cyc)
    else:
        print(f"[WARN] snapshot missing: alpha_cycle_{cyc:04d}.png  (skipped)")
panel_cycles = available
print(f"Panel cycles to plot: {panel_cycles}")

# ── 3. α 场面板图 ────────────────────────────────────────────────────────────
if panel_cycles:
    n = len(panel_cycles)
    fig, axes = plt.subplots(1, n, figsize=(2.6 * n, 3.2))
    if n == 1:
        axes = [axes]

    for ax, cyc in zip(axes, panel_cycles):
        png_path = snapshot_dir / f'alpha_cycle_{cyc:04d}.png'
        img = mpimg.imread(str(png_path))
        ax.imshow(img)
        ax.axis('off')

        if frac_cycle is not None and cyc == frac_cycle:
            ax.set_title(f'$N$ = {cyc}\n★ Complete fracture',
                         fontsize=8, color='crimson', fontweight='bold')
        else:
            ax.set_title(f'$N$ = {cyc}', fontsize=9)

    fig.suptitle(r'Phase-field $\alpha$ evolution under cyclic loading '
                 r'($U_\mathrm{max}$=const)', fontsize=10, y=1.02)
    plt.tight_layout()
    out_panel = figdir / 'alpha_panel_fatigue.png'
    fig.savefig(str(out_panel), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out_panel}")

# ── 4. E_el vs N 曲线 ────────────────────────────────────────────────────────
if E_el is not None:
    cycles = np.arange(len(E_el))
    E_norm = E_el / E_el_max

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.plot(cycles, E_norm, color='steelblue', linewidth=1.8,
             label=r'$\mathcal{E}_\mathrm{el}(N)\,/\,\mathcal{E}_\mathrm{el,max}$')
    ax2.axhline(E_THRESHOLD, color='dimgray', linestyle='--', linewidth=1.0,
                label=f'{int(E_THRESHOLD*100)}% threshold')

    if frac_cycle is not None:
        ax2.axvline(frac_cycle, color='crimson', linestyle='--', linewidth=1.5,
                    label=f'Complete fracture ($N$={frac_cycle})')
        # 标注文字：放在竖线右侧，y 在中间
        y_txt = 0.50
        ax2.annotate(f'★ $N_f$ = {frac_cycle}',
                     xy=(frac_cycle, E_THRESHOLD),
                     xytext=(frac_cycle + max(1, len(cycles)*0.03), y_txt),
                     fontsize=9, color='crimson',
                     arrowprops=dict(arrowstyle='->', color='crimson', lw=1.2))

    ax2.set_xlabel('Cycle $N$', fontsize=12)
    ax2.set_ylabel(r'$\mathcal{E}_\mathrm{el}\,/\,\mathcal{E}_\mathrm{el,max}$', fontsize=12)
    ax2.set_title('Elastic energy degradation vs. cycle number', fontsize=11)
    ax2.legend(fontsize=9, loc='upper right')
    ax2.set_ylim(-0.02, 1.08)
    ax2.set_xlim(0, len(cycles) - 1)
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()

    out_eel = figdir / 'E_el_vs_cycle.png'
    fig2.savefig(str(out_eel), dpi=200, bbox_inches='tight')
    plt.close(fig2)
    print(f"Saved: {out_eel}")

print("Done.")
