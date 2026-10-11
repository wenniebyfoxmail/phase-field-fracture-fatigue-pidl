#!/usr/bin/env bash
set -euo pipefail

: "${RUN_ROOT:?set RUN_ROOT to a fresh /mnt/data2/drtao/wennie directory}"
: "${CODE_ROOT:?set CODE_ROOT to the exact checked-out commit}"
: "${Q4_ARCHIVE:?set Q4_ARCHIVE to the sealed Q4 archive}"
: "${T3_ARCHIVE:?set T3_ARCHIVE to the sealed T3 archive}"
: "${CUDA_VISIBLE_DEVICES:?set CUDA_VISIBLE_DEVICES explicitly}"
EXPORT_SCRIPT=${EXPORT_SCRIPT:-"$CODE_ROOT/tools/s04_e011_analysis/export_pidl_nodal_trajectory.py"}

export TMPDIR="$RUN_ROOT/tmp"
export XDG_CACHE_HOME="$RUN_ROOT/cache"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$RUN_ROOT/output"

python3 -u "$EXPORT_SCRIPT" \
  --code-root "$CODE_ROOT" --archive "$Q4_ARCHIVE" --topology q4 \
  --output "$RUN_ROOT/output/pidl_q4_nodal_trajectory.npz" --device cuda

python3 -u "$EXPORT_SCRIPT" \
  --code-root "$CODE_ROOT" --archive "$T3_ARCHIVE" --topology t3 \
  --output "$RUN_ROOT/output/pidl_t3_nodal_trajectory.npz" --device cuda

sha256sum "$RUN_ROOT/output"/* > "$RUN_ROOT/output/SHA256SUMS"
date -Is > "$RUN_ROOT/COMPLETED_AT.txt"
