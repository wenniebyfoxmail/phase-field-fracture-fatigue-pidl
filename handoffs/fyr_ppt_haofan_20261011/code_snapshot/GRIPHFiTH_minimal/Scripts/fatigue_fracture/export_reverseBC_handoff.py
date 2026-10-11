"""
Export reverseBC snapshots for Mac Request 15.
Destination: ~/Downloads/_pidl_handoff_v2/reverseBC_u12/
Cycles exported: 1, 40, 70, 74 (fracture)
Fields: psi_elem, alpha_bar_elem, f_alpha_elem, d_elem  (+ cycle number)
Also: mesh_geometry.mat, timeseries CSV, README.md
"""

import os, shutil
import numpy as np
import scipy.io as sio

# ── paths ──────────────────────────────────────────────────────────────────
RUN_DIR   = r'C:/Users/xw436/GRIPHFiTH/Scripts/fatigue_fracture/SENT_PIDL_12_reverseBC'
PSI_DIR   = os.path.join(RUN_DIR, 'psi_fields')
MESH_SRC  = r'C:/Users/xw436/GRIPHFiTH/Scripts/fatigue_fracture/mesh_geometry.mat'
OUT_DIR   = r'C:/Users/xw436/Downloads/_pidl_handoff_v2/reverseBC_u12'
os.makedirs(OUT_DIR, exist_ok=True)

EXPORT_CYCLES = [1, 40, 70, 74]

# ── 1. per-cycle snapshots ──────────────────────────────────────────────────
for cyc in EXPORT_CYCLES:
    src = os.path.join(PSI_DIR, f'cycle_{cyc:04d}.mat')
    if not os.path.exists(src):
        print(f'[WARN] missing cycle {cyc:04d}.mat — skipped')
        continue
    m = sio.loadmat(src)
    out = {
        'cycle':           np.array([[cyc]], dtype=np.int32),
        'psi_elem':        m['psi_elem'].astype(np.float32),
        'alpha_bar_elem':  m['alpha_elem'].astype(np.float32),   # alias
        'f_alpha_elem':    m['f_alpha_elem'].astype(np.float32),
        'd_elem':          m['d_elem'].astype(np.float32),
    }
    fname = os.path.join(OUT_DIR, f'u12_reverseBC_cycle_{cyc:04d}.mat')
    sio.savemat(fname, out, format='5', do_compression=True)
    d_max = float(out['d_elem'].max())
    a_max = float(out['alpha_bar_elem'].max())
    f_min = float(out['f_alpha_elem'].min())
    print(f'[OK] cycle {cyc:04d}  d_max={d_max:.4f}  alpha_bar_max={a_max:.4f}  f_min={f_min:.4f}  -> {fname}')

# ── 2. mesh_geometry ───────────────────────────────────────────────────────
mg = sio.loadmat(MESH_SRC)
n_elem = mg['element_centroids'].shape[0]
n_node = mg['node_coords'].shape[0]
shutil.copy2(MESH_SRC, os.path.join(OUT_DIR, 'mesh_geometry.mat'))
print(f'[OK] mesh_geometry.mat copied  ({n_elem} elem, {n_node} nodes)')

# ── 3. timeseries CSV ──────────────────────────────────────────────────────
# monitorcycle.dat: n, dn, ||u||_1..inf, ||d||_1..inf, ||fat||_1..inf
mon_path = os.path.join(RUN_DIR, 'monitorcycle.dat')
rows = []
with open(mon_path) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('n'):   # skip header
            continue
        cols = line.split()
        if len(cols) < 11:
            continue
        n    = int(cols[0])
        d_max_mon = float(cols[7])
        a_max_mon = float(cols[10])
        rows.append((n, d_max_mon, a_max_mon))

# load_displ: step, u_x, F_x, u_y, F_y — peak-load row = last step per cycle
ld_path = os.path.join(RUN_DIR, 'load_displ_SENT_PIDL_12_reverseBC.out')
fy_by_cycle = {}
cyc_idx = 0
prev_step = 99
with open(ld_path) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('step'):
            continue
        cols = line.split()
        if len(cols) < 5:
            continue
        step = int(cols[0])
        fy   = float(cols[4])
        uy   = float(cols[3])
        if step < prev_step:   # new cycle
            cyc_idx += 1
        fy_by_cycle[cyc_idx] = fy   # keep overwriting → last step = peak
        prev_step = step

csv_path = os.path.join(OUT_DIR, 'SENT_PIDL_12_reverseBC_timeseries.csv')
with open(csv_path, 'w') as f:
    f.write('cycle,d_max,alpha_bar_max,f_min_est,reaction_Fy\n')
    for (n, d_m, a_m) in rows:
        # f_min estimate from alpha_bar_max (alpha_T=0.5, p=2)
        alpha_T, p = 0.5, 2.0
        f_est = min(1.0, (2*alpha_T / (a_m + alpha_T))**p)
        fy_val = fy_by_cycle.get(n, float('nan'))
        f.write(f'{n},{d_m:.6e},{a_m:.6e},{f_est:.6f},{fy_val:.6e}\n')
print(f'[OK] timeseries CSV: {len(rows)} cycles -> {csv_path}')

# ── 4. README ──────────────────────────────────────────────────────────────
readme = """# reverseBC FEM handoff (Request 15, 2026-05-22)

## Setup
- Run: SENT_PIDL_12_reverseBC (GRIPHFiTH `devel`, outbox `2ce76ec`)
- BC: fix_X on ALL top+bottom nodes (mimics old PIDL default horizontal clamp)
- Material: AT1 + AMOR + PENALTY, E=1, Gc=0.01, ell=0.01, alpha_T=0.5, p=2
- Load: uy_final=0.12, R=0, n_step=8, cyclic
- Mesh: SENT_mesh.inp, 77730 quad elements, 77900 nodes (same as baseline PIDL_12)
- N_f = 74  (baseline fix_X bottom_left: N_f = 82, -10%)

## Files
| File | Description |
|---|---|
| `mesh_geometry.mat` | element_centroids (77730×2), connectivity (77730×4), node_coords (77900×2) |
| `u12_reverseBC_cycle_0001.mat` | c1  fields |
| `u12_reverseBC_cycle_0040.mat` | c40 fields |
| `u12_reverseBC_cycle_0070.mat` | c70 fields |
| `u12_reverseBC_cycle_0074.mat` | c74 fracture/final |
| `SENT_PIDL_12_reverseBC_timeseries.csv` | cycle, d_max, alpha_bar_max, f_min_est, reaction_Fy |

## Per-cycle .mat keys
- `cycle`          : int scalar
- `psi_elem`       : (77730,1) float32, peak strain energy density [toy-unit]
- `alpha_bar_elem` : (77730,1) float32, cumulative fatigue variable
- `f_alpha_elem`   : (77730,1) float32, fatigue degradation function f(alpha_bar)
- `d_elem`         : (77730,1) float32, damage field

## Note on u_node
Peak-load nodal displacement is NOT in this handoff. The cyclic solver saves
checkpoint at unloaded state (u=0). To get peak-load u for J-integral
(Request 14), a brittle-solver post-run at each cycle's damage IC is needed
(see GRIPHFiTH standing notes). Can be done if Mac confirms it unblocks J.

## Key findings (outbox 2ce76ec)
- N_f = 74 vs baseline 82 (-10%): BC change shifts N_f modestly
- V4 mirror symmetry unchanged (~0.6% RMS at c70)
- V7 side-boundary residual = 5.85% (48x baseline 0.12%): non-physical
  sigma_xx from blocked Poisson contraction — reverseBC is a different BVP
- Conclusion: BC mismatch is NOT the root cause of FEM/PIDL field gap
"""
with open(os.path.join(OUT_DIR, 'README.md'), 'w') as f:
    f.write(readme)
print('[OK] README.md written')
print(f'\nHandoff complete: {OUT_DIR}')
print('Files:', sorted(os.listdir(OUT_DIR)))
