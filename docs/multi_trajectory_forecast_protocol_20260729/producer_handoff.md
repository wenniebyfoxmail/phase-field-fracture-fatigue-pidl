# Producer handoff: factorial LOCO matrix

## Current blocker

No producer job has launched.

At `2026-07-29T16:39:51+01:00`:

- Taobo `172.16.100.2:22` accepted TCP but reset both explicit and configured
  SSH sessions during key exchange.
- CSD3 reached the login banner but rejected the current credentials with
  `Permission denied (publickey,keyboard-interactive,hostbased)`.

There is therefore no legitimate remote run directory, GPU, PID or log to
report. This is a producer-access blocker, not a readiness or training result.

## Immutable inputs

- Branch: `codex/temporal-graph-transformer`
- Producer-ready commit: `b05180d07595498f605ab19039c281fc80509f35`
- Agent2 source commit: `90cf8a3703d03609ad7daf066d04ab051c2f7500`
- Agent2 contract file SHA: `c32b594559362bf7b7a7b4892e74f8d1001bb8d5ac88c3a3776a8e8333aa57df`
- Internal LOCO lock: `5904af500cde315d8ee9f9087d3f5088c03b59b76cf23f8fbf7b80f6c3fb1691`
- Local materialised data:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/factorial_loco_temporal_dataset_20260729`
- Data size: 398 MB; all seven entries in its `HASHES.sha256` pass.
- Matrix: 4 folds x 3 models x 3 seeds = 36 jobs, fixed 3000 steps.

## Taobo recovery sequence

Use a fresh directory. Do not pull into an existing shared checkout.

```bash
RUN_ID=pf_factorial_loco_b05180d_20260729
REMOTE_ROOT=/mnt/data2/drtao/wennie/$RUN_ID
ARCHIVE_ROOT=/mnt/data2/drtao/pidl_archives/$RUN_ID

ssh -F /dev/null drtao@172.16.100.2 "mkdir -p '$REMOTE_ROOT' '$ARCHIVE_ROOT'"
ssh -F /dev/null drtao@172.16.100.2 "
  cd '$REMOTE_ROOT' &&
  git clone --branch codex/temporal-graph-transformer \
    https://github.com/wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git code &&
  cd code && git checkout b05180d07595498f605ab19039c281fc80509f35 &&
  test -z \"\$(git status --short)\"
"

rsync -avP -e "ssh -F /dev/null" \
  /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/factorial_loco_temporal_dataset_20260729/ \
  drtao@172.16.100.2:"$REMOTE_ROOT/data/"
```

Verify before any optimisation:

```bash
ssh -F /dev/null drtao@172.16.100.2 "
  cd '$REMOTE_ROOT/data' && shasum -a 256 -c HASHES.sha256 &&
  cd '$REMOTE_ROOT/code' &&
  test \"\$(git rev-parse HEAD)\" = b05180d07595498f605ab19039c281fc80509f35 &&
  test -z \"\$(git status --short)\" &&
  nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader &&
  /usr/bin/python3 -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
"
```

Select only explicitly free GPUs after the occupancy check. Then launch the
detached dispatcher, replacing `<FREE_GPUS>` with that explicit list:

```bash
ssh -F /dev/null drtao@172.16.100.2 "
  mkdir -p '$ARCHIVE_ROOT/logs' '$REMOTE_ROOT/tmp' &&
  cd '$REMOTE_ROOT/code' &&
  TMPDIR='$REMOTE_ROOT/tmp' nohup /usr/bin/python3 -u \
    SENS_tensile/dispatch_factorial_loco_matrix.py \
    --manifest docs/multi_trajectory_forecast_protocol_20260729/producer_gate_20260729/producer_experiment_manifest.json \
    --data-root '$REMOTE_ROOT/data' \
    --out-root '$ARCHIVE_ROOT' \
    --gpus '<FREE_GPUS>' \
    > '$ARCHIVE_ROOT/logs/dispatcher.log' 2>&1 &
  echo PID=\$!
"
```

Immediately record the returned dispatcher PID, exact free-GPU list, remote
cwd and log. The dispatcher records each child GPU/PID/command in
`dispatcher_state.json`; never use broad `pkill`.

## Completion and analysis

The matrix is complete only when `dispatcher_state.json` reports 36 completed
jobs and zero failures. Download the full archive, verify per-run manifests,
then run:

```bash
python3 SENS_tensile/analyze_factorial_loco_results.py \
  --runs <DOWNLOADED_ARCHIVE> \
  --producer-manifest docs/multi_trajectory_forecast_protocol_20260729/producer_gate_20260729/producer_experiment_manifest.json \
  --out <DOWNLOADED_ARCHIVE>/analysis
```

Do not publish partial-fold rankings. Keep road-like LOTO, real-road,
geometry/material generalisation and calibrated hazard/RUL blocked.

