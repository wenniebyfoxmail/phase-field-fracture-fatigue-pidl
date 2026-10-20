#!/usr/bin/env bash
# Exact first remote read-only admission AFTER approval. No GPU query or images.
set -euo pipefail
test "$(hostname)" = GPUServer8
test "$(id -un)" = drtao
test ! -e /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002
test ! -L /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002
test -f /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/code_snapshot.tar.gz
test ! -L /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/code_snapshot.tar.gz
test "$(sha256sum /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/code_snapshot.tar.gz | cut -d" " -f1)" = f6fabf39e12355e87d4711b734217b0bbac3d491ea4c86ee653f68d4443e81e3
test -x /usr/bin/python3
command -v git
command -v taskset
command -v nohup
command -v tar
command -v rsync
command -v sha256sum
command -v cp
command -v timeout
df -h / /mnt/data2 /mnt/data3
CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg \
 /usr/bin/python3 - <<'PY'
import importlib.util,json,os,pathlib,platform,shutil,sys
assert platform.system()=='Linux' and sys.version_info>=(3,9)
assert pathlib.Path('/mnt/data2').is_mount(), 'No fallback mount'
assert shutil.disk_usage('/mnt/data2').free>=1024**3, 'Need 1GiB free staging/output space'
mem={r.split(':',1)[0]:int(r.split()[1]) for r in pathlib.Path('/proc/meminfo').read_text().splitlines()}
assert mem['MemAvailable']>=4*1024**2, 'Need at least 4GiB available, task cap is 2GiB address space'
allowed=sorted(os.sched_getaffinity(0)); load=os.getloadavg()[0]
assert allowed and load<=.75*(os.cpu_count() or 1), 'CPU busy: stop, do not kill or wait/retry'
import numpy,cv2
# Do not import Matplotlib until caches have a task-owned writable directory.
# Finding the installed module is read-only; actual Agg import is checked in launch.
assert importlib.util.find_spec('matplotlib') is not None
print(json.dumps(dict(host=platform.node(),runtime=sys.executable,python=sys.version,
 numpy=numpy.__version__,opencv=cv2.__version__,matplotlib_installed=True,
 allowed_cpu_count=len(allowed),load1=load,mem_available_kib=mem['MemAvailable'],
 raw_input_presence='not_checked_and_not_assumed',scientific_execution=False)))
PY
