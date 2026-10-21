#!/usr/bin/env bash
set -eu
TASKROOT=/mnt/data2/drtao/wennie/pf_s04e035_l2_r1_20261021_1842
export CUDA_VISIBLE_DEVICES=5
export TMPDIR="$TASKROOT/tmp"
export XDG_CACHE_HOME="$TASKROOT/cache"
export TORCH_EXTENSIONS_DIR="$TASKROOT/.jitcache"
export MPLCONFIGDIR="$TASKROOT/cache/matplotlib"
export PIDL_ARCHIVE_DIR=/mnt/data2/drtao/pidl_archives/pf_s04e035_l2_r1_20261021_1842
export OMP_NUM_THREADS=4
mkdir -p "$PIDL_ARCHIVE_DIR"
cd "$TASKROOT/code"
date -u +%Y-%m-%dT%H:%M:%SZ > "$TASKROOT/started_utc.txt"
set +e
timeout --signal=TERM --kill-after=10s 3550s /usr/bin/python3 -u scripts/run_s04_e035_l2_pairs.py --baseline /mnt/data2/drtao/pidl_archives/pf_hard_d1_u0_recovery_e9dc263_20260630_043100/probeDriver_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc120_Nstep601_U0.12_hard_d1_u0_recovery_current_active_fem_gp_tri3_g_mean_femIrrGP3_hardAlphaRecoverU0_s0.25-0.5-0.75-1-0 --output "$PIDL_ARCHIVE_DIR/results" --source-commit 5f5428d7586f68bd6cace033f99737c2b5d334c4 --arm-seconds 240 --total-seconds 3300
TASKEXIT=$?
printf '%s\n' "$TASKEXIT" > "$TASKROOT/exit_code.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$TASKROOT/finished_utc.txt"
exit "$TASKEXIT"
