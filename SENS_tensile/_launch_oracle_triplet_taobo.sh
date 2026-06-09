#!/usr/bin/env bash
set -euo pipefail

# Producer-side launcher for the three Alignment check 2 oracle discriminators.
# Run this on Taobo/CSD3/Windows-PIDL, not on Mac-PIDL.

UMAX="${UMAX:-0.12}"
N_CYCLES="${N_CYCLES:-80}"
PYTHON="${PYTHON:-/usr/bin/python3}"
GPU_RAW="${GPU_RAW:-0}"
GPU_ACTIVE="${GPU_ACTIVE:-1}"
GPU_DELTA="${GPU_DELTA:-2}"
STAMP="${STAMP:-$(date +%Y%m%d_%H%M%S)}"

FEM_DATA_DIR="${FEM_DATA_DIR:-/mnt/data2/drtao/pidl_fem_handoff/reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28}"
PIDL_ARCHIVE_DIR="${PIDL_ARCHIVE_DIR:-/mnt/data2/drtao/pidl_archives/oracle_triplet_${STAMP}}"
LOG_DIR="${LOG_DIR:-$(pwd)/run_logs/oracle_triplet_${STAMP}}"

mkdir -p "$LOG_DIR" "$PIDL_ARCHIVE_DIR"

echo "oracle_triplet_start=$(date)"
echo "cwd=$(pwd)"
echo "python=$PYTHON"
echo "umax=$UMAX"
echo "n_cycles=$N_CYCLES"
echo "fem_data_dir=$FEM_DATA_DIR"
echo "archive_root=$PIDL_ARCHIVE_DIR"
echo "log_dir=$LOG_DIR"
echo "gpus raw=$GPU_RAW active=$GPU_ACTIVE delta=$GPU_DELTA"

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader || true
fi

launch_one() {
  local kind="$1"
  local gpu="$2"
  local log="$LOG_DIR/${kind}.log"
  echo "launching kind=$kind gpu=$gpu log=$log"
  CUDA_VISIBLE_DEVICES="$gpu" \
  PIDL_ARCHIVE_DIR="$PIDL_ARCHIVE_DIR" \
  FEM_DATA_DIR="$FEM_DATA_DIR" \
  nohup "$PYTHON" -u run_fem_mesh_oracle_field_umax.py "$UMAX" \
    --oracle-kind "$kind" \
    --n-cycles-physical "$N_CYCLES" \
    --fem-data-dir "$FEM_DATA_DIR" \
    > "$log" 2>&1 &
  local pid=$!
  echo "$kind pid=$pid gpu=$gpu log=$log"
}

launch_one raw_pidl_g "$GPU_RAW"
launch_one active_fem "$GPU_ACTIVE"
launch_one delta_alpha_bar "$GPU_DELTA"

echo "oracle_triplet_launched=$(date)"
