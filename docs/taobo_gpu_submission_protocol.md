# Taobo GPU Submission Protocol

Status: Current operational protocol for Taobo GPU job submission, monitoring
and shared-account safety. This is not a PIDL/FEM evidence-analysis protocol.

Purpose: prevent accidental Mac training, dirty-repo launches, untracked Taobo jobs, and shared-account collisions.

## Canonical storage naming

`/mnt/data` is project shorthand for Taobo's large-data mount family. On the
current host, the actual primary mount is `/mnt/data2` and the secondary mount
is `/mnt/data3`; literal `/mnt/data` and `/mnt/data1` do not exist. Use
`/mnt/data2/drtao/wennie/<fresh_run_id>/` for new project runs and
`/mnt/data2/drtao/pidl_archives/<fresh_run_id>/` for archives. Keep task-owned
`TMPDIR`, `.jitcache`, and `XDG_CACHE_HOME` under the fresh run root. Never
write large data to `/`, `/tmp`, or `/home/drtao`, and never silently create a
fallback on the root filesystem. Check all three mounts with `df -h` before
launch.

Taobo: `drtao@172.16.100.2`, 8x RTX 4090, shared account. Network/VPN is flaky. Design the workflow so SSH drops are harmless.

## 1. Decide Whether The Task Belongs On Taobo

Run on **Mac** only:

- code edits
- lightweight import/unit sanity
- analysis and plotting that does not enter the training loop
- git commit/push

Run on **Taobo GPU / CSD3 / Windows-PIDL**:

- any command that enters `main.py` or a PIDL training loop
- training smoke, even 1 cycle
- baseline/adaptive sweeps and production cases

If an agent is about to launch training on Mac, stop. That is a routing error.

## 2. Prepare Code On Mac First

From Mac:

```bash
cd "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code"
git status --short
git rev-parse HEAD
```

For code/runner/rule changes:

```bash
python3 -m py_compile SENS_tensile/<runner>.py source/<changed_file>.py
git add <files>
git commit -m "<clear message>"
git push origin <branch>
```

Do not expect a Taobo-local commit to be shared. Shared code state comes from GitHub or a Mac-prepared snapshot tied to a Mac commit SHA.

## 3. Choose A Fresh Remote Run Directory

Prefer a unique, attributable directory:

```bash
RUN_ID=pf_<short-topic>_<commit>_$(date +%Y%m%d_%H%M%S)
REMOTE_ROOT=/mnt/data2/drtao/wennie/$RUN_ID
ARCHIVE_ROOT=/mnt/data2/drtao/pidl_archives/$RUN_ID
```

Do not reuse and clean an old partial folder before launch. Old partial folders can be cleaned later, after the run is launched/completed and coordination is safe.

Existing historical checkouts under `/mnt/data2/drtao/projects/...` may be dirty or research-line-specific. Do not pull into them unless you have inspected and intentionally chosen that repo.

## 4. Sync Code

Preferred when Taobo to GitHub is stable:

```bash
ssh -F /dev/null drtao@172.16.100.2 "mkdir -p '$REMOTE_ROOT'"
ssh -F /dev/null drtao@172.16.100.2 "
  cd '$REMOTE_ROOT' &&
  git clone --depth 1 --branch <branch> https://github.com/wenniebyfoxmail/phase-field-fracture-fatigue-pidl.git code &&
  cd code &&
  git fetch --depth 1 origin <commit> &&
  git checkout <commit>
"
```

Preferred when GitHub clone/pull is flaky:

```bash
ssh -F /dev/null drtao@172.16.100.2 "mkdir -p '$REMOTE_ROOT/code'"
rsync -avP -e "ssh -F /dev/null" \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pt' \
  --exclude 'hl_*' \
  --exclude 'run_logs/' \
  "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/" \
  drtao@172.16.100.2:"$REMOTE_ROOT/code/"
```

For rsync snapshots, write a provenance file on Taobo:

```bash
ssh -F /dev/null drtao@172.16.100.2 "
  cd '$REMOTE_ROOT/code' &&
  printf 'source=mac-rsync\ncommit=%s\nbranch=%s\ndate=%s\n' '<commit>' '<branch>' \"\$(date)\" > RUN_PROVENANCE.txt
"
```

## 5. Pre-Launch Sanity On Taobo

```bash
ssh -F /dev/null drtao@172.16.100.2 "
  cd '$REMOTE_ROOT/code' &&
  echo HEAD=\$(git rev-parse HEAD 2>/dev/null || sed -n 's/^commit=//p' RUN_PROVENANCE.txt) &&
  echo DIRTY=\$(git status --short 2>/dev/null | wc -l || true) &&
  df -h / /mnt/data2 &&
  nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader &&
  /usr/bin/python3 - <<'PY'
import torch
print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'count', torch.cuda.device_count())
PY
"
```

If `torch.cuda.is_available()` is false or `nvidia-smi` reports a device handle/NVML error, do not launch. Pause and diagnose GPU/driver state.

## 6. Launch

Rules:

- pick a specific free GPU
- set `CUDA_VISIBLE_DEVICES=N`
- set `PIDL_ARCHIVE_DIR`
- launch detached
- write logs under `/mnt/data2`
- use `pf_*` tmux names if interactive

Example:

```bash
GPU=3
LOG_DIR=$REMOTE_ROOT/logs
ssh -F /dev/null drtao@172.16.100.2 "
  mkdir -p '$LOG_DIR' '$ARCHIVE_ROOT' &&
  cd '$REMOTE_ROOT/code/SENS_tensile' &&
  CUDA_VISIBLE_DEVICES=$GPU \
  PIDL_ARCHIVE_DIR='$ARCHIVE_ROOT' \
  nohup /usr/bin/python3 -u <runner>.py <args> \
    > '$LOG_DIR/<job_tag>.log' 2>&1 &
  echo PID=\$!
"
```

For multiple jobs, use separate GPUs or a Taobo-resident dispatcher. Do not bind pending jobs to stale fixed waiters if other suitable GPUs are idle.

## 7. Track Every Job

Immediately record:

```text
run_id:
commit:
branch:
sync mode: git clone | mac rsync
remote code dir:
archive root:
gpu:
pid:
command:
log:
launch time:
initial health check:
```

For project work, put this into the relevant experiment folder, handover, or memory entry. Do not rely on terminal scrollback.

Useful remote checks:

```bash
ssh -F /dev/null drtao@172.16.100.2 "ps -p <PID> -o pid,etime,stat,cmd"
ssh -F /dev/null drtao@172.16.100.2 "tail -40 <log>"
ssh -F /dev/null drtao@172.16.100.2 "nvidia-smi pmon -c 1"
```

SSH failure means loss of visibility only. It does not prove the detached job stopped.

## 8. Shared Account Safety

The account `drtao` is shared. Before killing any process:

```bash
pid=<PID>
ps -p "$pid" -o pid,ppid,user,etime,stat,cmd
readlink /proc/"$pid"/cwd
tr '\0' ' ' < /proc/"$pid"/cmdline
```

Only kill if cmdline, elapsed time, and cwd clearly identify the process as yours. Never use broad `pkill`.

Machine-wide actions require prior coordination: reboot, root-service/docker changes, global sudo config edits, heavy disk IO, and anything likely to affect Haofan/Tao哥/other users.

## 9. Common Failure Modes

- **Port reachable, SSH negotiating slowly**: TCP can reach port 22, but SSH auth/shell is still exposed to VPN latency and server load.
- **Git clone/pull hangs**: Taobo to GitHub HTTPS is flaky. Use Mac rsync snapshot tied to a commit SHA.
- **Existing repo dirty**: do not pull into it. Use fresh `RUN_ID`.
- **`/` full**: outputs are going to the wrong place. Use `/mnt/data2` and `PIDL_ARCHIVE_DIR`.
- **`Can't initialize NVML` / `CUDA unknown error`**: GPU/driver problem. Do not launch new jobs until `nvidia-smi` and PyTorch CUDA are healthy.
