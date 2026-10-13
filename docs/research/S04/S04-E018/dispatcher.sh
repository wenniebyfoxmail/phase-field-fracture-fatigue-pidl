#!/usr/bin/env bash
set -euo pipefail
ROOT=/mnt/data2/drtao/wennie/S04-E018-global-local-e67d970-20261013T111326Z
COMMIT=e67d9701419fbb891ce570edd3530bf68aae5f4e
export CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export TMPDIR=$ROOT/cache/tmp
export XDG_CACHE_HOME=$ROOT/cache/xdg
export TORCH_HOME=$ROOT/cache/torch
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$TORCH_HOME" "$ROOT/runs"
cd "$ROOT/code"
test "$(git rev-parse HEAD)" = "$COMMIT"
test -z "$(git status --porcelain)"
mountpoint -q /mnt/data2
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader > "$ROOT/logs/gpu_launch.txt"
free_mem=$(nvidia-smi -i 0 --query-gpu=memory.free --format=csv,noheader,nounits)
test "$free_mem" -gt 8192
ordinal=0
for state in c20s4 c60s4 c83s4; do
 for arm in control localized; do
  ordinal=$((ordinal+1))
  suffix=$(printf 'R%03d' "$ordinal")
  run_id=$(basename "$ROOT")-$suffix-$state-$arm-s7
  out=$ROOT/runs/$run_id
  archive=/mnt/data2/drtao/pidl_archives/$run_id
  log=$ROOT/logs/$run_id.log
  test ! -e "$out"; test ! -e "$archive"
  echo START "$run_id"
  python3 -u SENS_tensile/run_s04_e018_global_local_screen.py --state "$state" --arm "$arm" --alpha 0.7 --seed 7 --reference "$ROOT/inputs/$state.npz" --out "$out" --run-id "$run_id" --expected-commit "$COMMIT" --archive-root "$archive" --log-path "$log" --device cuda > "$log" 2>&1
  echo COMPLETED "$run_id"
 done
done
python3 SENS_tensile/aggregate_s04_e018_global_local_screen.py --input-root "$ROOT/runs" --reference-root "$ROOT/inputs" --code-commit "$COMMIT" --out "$ROOT/aggregate" > "$ROOT/logs/aggregate.log" 2>&1
echo MATRIX_EXECUTION_COMPLETED
