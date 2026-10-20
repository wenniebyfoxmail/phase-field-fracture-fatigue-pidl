#!/usr/bin/env bash
# Prepared launcher. Not run locally or remotely; requires actual exact approval.
set -euo pipefail
MD03_ROOT=/mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001
test "$(hostname)" = GPUServer8
test "$(id -un)" = drtao
test -d "$MD03_ROOT/code/.git"
test "$(git -C "$MD03_ROOT/code" rev-parse HEAD)" = fb29771a2d972180c2d57b1fa6345dd4dbb684fe
test -z "$(git -C "$MD03_ROOT/code" status --porcelain)"
cd "$MD03_ROOT/code"
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export TMPDIR="$MD03_ROOT/tmp" XDG_CACHE_HOME="$MD03_ROOT/cache"
export MPLCONFIGDIR="$MD03_ROOT/cache/matplotlib" PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1 MPLBACKEND=Agg
# Both runtime admission and descendants stay within this process-local ceiling.
ulimit -v 2097152
/usr/bin/python3 - "$MD03_ROOT" <<'PY'
import hashlib,json,pathlib,platform,sys
root=pathlib.Path(sys.argv[1])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
c=root/'control/remote_contract.json'
d=json.loads((root/'control/approved_decision.json').read_text())
assert sha(c)=='c11719e0301e13675caaeea8d03a80ff77351a73b43c3083d0998433f9eb2173'
assert d['contract_sha256']==sha(c) and d['approval_source'], 'Actual approval missing'
assert sha(root/'code/scripts/md03_controlled_opening.py')=='27ad7b5c23f77f626bebd7e6659c26258bea6be327989bd9dbc21584db4cf8ed'
assert sha(root/'code/docs/research/S03/S03-E049-MD03/controlled_opening_protocol.md')=='cbbb14a6e9e3916a4439a1a3d61ff4d7e3a3d75ba0fe83fedcfb7374b623a105'
assert platform.system()=='Linux' and sys.version_info>=(3,9)
import numpy,cv2,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot
print(json.dumps(dict(runtime=sys.executable,python=sys.version,numpy=numpy.__version__,
 opencv=cv2.__version__,matplotlib=matplotlib.__version__,scientific_execution=False)))
PY
# Atomic single-use claim. Existing/partial claim always stops, never resets.
mkdir "$MD03_ROOT/launch.claim"
printf '%s\n' "$$" > "$MD03_ROOT/launch.claim/driver.pid"
# Pin this task and descendants to one allowed logical CPU, not a GPU.
MD03_CPU=$(/usr/bin/python3 -c 'import os; print(min(os.sched_getaffinity(0)))')
exec taskset -c "$MD03_CPU" /usr/bin/python3 -u scripts/md03_controlled_opening.py run \
  --contract "$MD03_ROOT/control/remote_contract.json" \
  --decision "$MD03_ROOT/control/approved_decision.json" \
  --output "$MD03_ROOT/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R001"
