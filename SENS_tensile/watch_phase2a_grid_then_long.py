#!/usr/bin/env python3
from __future__ import annotations
import math
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

ROOT = Path('/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile')
GPU = '0'
ALPHA_T = 100.0
MAX_N = 2000
MIN_N = 800
TARGET_ALPHA_MULT = 4.0
PREFIX = 'hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_pcc_dispR{r}_aT100.0_N{n}_R0.0_seed1_AT1_baseline'
LOG = ROOT / 'watch_phase2a_grid_then_long.log'

def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open('a') as f:
        f.write(line + '\n')

def sh(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)

def active_grid() -> str:
    try:
        return sh("ps -eo pid,etime,cmd | grep -E 'run_pcc_baseline_umax.py (0.50|1.00) --n-cycles 20' | grep -v grep || true").strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()

def arr_for(r: str, n: int):
    p = ROOT / PREFIX.format(r=r, n=n) / 'best_models' / 'alpha_bar_vs_cycle.npy'
    if not p.exists():
        return None, p
    return np.asarray(np.load(p, allow_pickle=True), dtype=float), p

def metrics(r: str, n: int):
    a, p = arr_for(r, n)
    if a is None:
        return None
    alpha = a if a.ndim == 1 else a[:, 0]
    fmin = np.full_like(alpha, np.nan, dtype=float) if a.ndim == 1 or a.shape[1] < 3 else a[:, 2]
    return {
        'path': str(p),
        'len': int(len(alpha)),
        'alpha0': float(alpha[0]),
        'alpha_end': float(alpha[-1]),
        'fmin_end': float(fmin[-1]) if len(fmin) else float('nan'),
        'nan': int(np.isnan(alpha).sum()),
        'slope_all': float((alpha[-1] - alpha[0]) / max(len(alpha) - 1, 1)),
        'mono_bad': int(np.sum(np.diff(alpha) < -1e-6)),
    }

def wait_for_grid():
    while True:
        m05 = metrics('0.5', 20)
        m10 = metrics('1.0', 20)
        active = active_grid()
        if m05 and m10 and m05['len'] >= 20 and m10['len'] >= 20 and not active:
            return m05, m10
        log(f"waiting grid: active={bool(active)} r05_len={m05 and m05['len']} r10_len={m10 and m10['len']}")
        time.sleep(120)

def main():
    log('watcher start: wait for Phase2A N20 grid, then maybe launch long dispR1.00')
    m05, m10 = wait_for_grid()
    m075_arr, _ = arr_for('0.75', 50)
    if m075_arr is None or len(m075_arr) < 20:
        log('FAIL: missing existing dispR0.75 N50 reference; not launching long run')
        return
    alpha075 = np.asarray(m075_arr, dtype=float)[:20, 0]
    m075 = {
        'len': int(len(alpha075)),
        'alpha0': float(alpha075[0]),
        'alpha_end': float(alpha075[-1]),
        'slope_all': float((alpha075[-1] - alpha075[0]) / max(len(alpha075) - 1, 1)),
        'nan': int(np.isnan(alpha075).sum()),
        'mono_bad': int(np.sum(np.diff(alpha075) < -1e-6)),
    }
    log(f"grid metrics r0.5={m05}")
    log(f"grid metrics r0.75(first20)={m075}")
    log(f"grid metrics r1.0={m10}")

    ok = True
    reasons = []
    for name, m in [('0.5', m05), ('0.75', m075), ('1.0', m10)]:
        if m['nan']:
            ok = False; reasons.append(f'{name}: NaN in alpha')
        if m['alpha_end'] <= m['alpha0']:
            ok = False; reasons.append(f'{name}: alpha did not grow')
        if m['mono_bad'] > 2:
            ok = False; reasons.append(f'{name}: too many alpha decreases')
    if not (m05['alpha_end'] < m075['alpha_end'] < m10['alpha_end']):
        ok = False; reasons.append('alpha_end is not monotone with dispR')
    norm_slopes = {
        '0.5': m05['slope_all'] / (0.5**2),
        '0.75': m075['slope_all'] / (0.75**2),
        '1.0': m10['slope_all'],
    }
    spread = max(norm_slopes.values()) / max(min(norm_slopes.values()), 1e-12)
    log(f"normalized slope by dispR^2={norm_slopes}, spread={spread:.2f}")
    if spread > 3.0:
        ok = False; reasons.append(f'slope/R^2 spread too large: {spread:.2f}')

    if not ok:
        log('GRID NOT GOOD ENOUGH: ' + '; '.join(reasons))
        return

    slope = m10['slope_all']
    est_alphaT = ALPHA_T / max(slope, 1e-12)
    n_long = int(math.ceil(TARGET_ALPHA_MULT * est_alphaT))
    n_long = max(MIN_N, min(MAX_N, n_long))
    log(f"GRID PASS: est cycles to alpha_T at dispR1.00 = {est_alphaT:.1f}; launching N={n_long}")

    src = ROOT / PREFIX.format(r='1.0', n=20)
    dst = ROOT / PREFIX.format(r='1.0', n=n_long)
    if not src.exists():
        log(f'FAIL: source archive missing {src}')
        return
    if not dst.exists():
        log(f'copy archive {src.name} -> {dst.name}')
        shutil.copytree(src, dst)
    else:
        log(f'destination archive exists, will reuse/resume: {dst.name}')

    long_log = ROOT / f'run_phase2a_pcc_AT1_N{n_long}_dispR1.00.log'
    cmd = f"cd {ROOT} && CUDA_VISIBLE_DEVICES={GPU} python3 -u run_pcc_baseline_umax.py 1.00 --n-cycles {n_long} --seed 1 --pff-model AT1 > {long_log} 2>&1"
    log(f'launch long command: {cmd}')
    p = subprocess.Popen(['bash', '-lc', cmd], start_new_session=True)
    log(f'long run launched pid={p.pid}, log={long_log}')

if __name__ == '__main__':
    main()
