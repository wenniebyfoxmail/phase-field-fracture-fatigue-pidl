#!/usr/bin/env bash
set -eu
: "${AL_TASKROOT:?Set owned fresh task root}"
: "${AL_SOURCE_COMMIT:?Set reviewed source commit}"
case "$AL_TASKROOT" in /mnt/data2/drtao/wennie/pf_s04e037_al_*) ;; *) exit 90;; esac
mkdir "$AL_TASKROOT/launch_once"
export CUDA_VISIBLE_DEVICES=5
export TMPDIR="$AL_TASKROOT/tmp"
export XDG_CACHE_HOME="$AL_TASKROOT/cache"
export TORCH_EXTENSIONS_DIR="$AL_TASKROOT/.jitcache"
export MPLCONFIGDIR="$AL_TASKROOT/cache/matplotlib"
export PYTHONPATH="$AL_TASKROOT/deps"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4
export PIDL_ARCHIVE_DIR="/mnt/data2/drtao/pidl_archives/$(basename "$AL_TASKROOT")"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$TORCH_EXTENSIONS_DIR" "$MPLCONFIGDIR"
mkdir "$PIDL_ARCHIVE_DIR"
cd "$AL_TASKROOT/code"
date -u +%Y-%m-%dT%H:%M:%SZ > "$AL_TASKROOT/started_utc.txt"
set +e
/usr/bin/python3 - <<'PY'
import json, os, subprocess
from pathlib import Path
root=Path(os.environ['AL_TASKROOT'])
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True)
apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader,nounits'],text=True)
row=[x.strip().split(', ') for x in gpu.splitlines() if x.startswith('5,')][0]
uuid='GPU-5622bd47-1050-3003-246d-3cabe2b4791b'
ready=(row[1]==uuid and int(row[2])<256 and int(row[3])==0 and uuid not in apps)
(root/'admission.json').write_text(json.dumps(dict(gpu=gpu,processes=apps,ready=ready),indent=2)+'\n')
raise SystemExit(0 if ready else 91)
PY
AL_EXIT=$?
if [ "$AL_EXIT" -eq 0 ]; then
  timeout --signal=TERM --kill-after=10s 1300s /usr/bin/python3 -u scripts/run_s04_e037_al.py \
    --baseline /mnt/data2/drtao/pidl_archives/pf_hard_d1_u0_recovery_e9dc263_20260630_043100/probeDriver_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc120_Nstep601_U0.12_hard_d1_u0_recovery_current_active_fem_gp_tri3_g_mean_femIrrGP3_hardAlphaRecoverU0_s0.25-0.5-0.75-1-0 \
    --physics-root "$AL_TASKROOT/physics" --output "$PIDL_ARCHIVE_DIR/results" --source-commit "$AL_SOURCE_COMMIT"
  AL_EXIT=$?
fi
printf '%s\n' "$AL_EXIT" > "$AL_TASKROOT/exit_code.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$AL_TASKROOT/finished_utc.txt"
exit "$AL_EXIT"
