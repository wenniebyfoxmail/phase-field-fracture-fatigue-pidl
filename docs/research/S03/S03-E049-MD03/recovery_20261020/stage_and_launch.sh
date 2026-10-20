#!/usr/bin/env bash
# R002 preparation only. Stream to the selected host only after exact approval.
set -euo pipefail
MD03_ROOT=/mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002
test "$(hostname)" = GPUServer8
test "$(id -un)" = drtao
test -d "$MD03_ROOT"
test ! -L "$MD03_ROOT"
cd "$MD03_ROOT"
for MD03_PATH in input_assets.tar.gz code_snapshot.tar.gz control/remote_contract.json control/run_cpu.sh control/source_snapshot.json control/approved_decision.json; do
  test -f "$MD03_PATH"
  test ! -L "$MD03_PATH"
done
test "$(sha256sum input_assets.tar.gz | cut -d' ' -f1)" = 6ce79a5e1cd75615d2bf1b1712349409210244a878b4d5123e3059bd81279240
test "$(stat -c %s input_assets.tar.gz)" = 113514186
test "$(sha256sum code_snapshot.tar.gz | cut -d' ' -f1)" = f6fabf39e12355e87d4711b734217b0bbac3d491ea4c86ee653f68d4443e81e3
test "$(sha256sum control/remote_contract.json | cut -d' ' -f1)" = f737cfd0673861b6ddf815e43be0cdcea1498bb0f767106006ff7c1d7548f057
test "$(sha256sum control/run_cpu.sh | cut -d' ' -f1)" = c9365dce790f42eeba7880bbcede0c46c81d74aafd6cd3438a970870a7c75a7b
test "$(sha256sum control/source_snapshot.json | cut -d' ' -f1)" = 1ed64881731b27baf56ffdc2269515fa4f2edf34de92c395dbe51cabf91a40e4
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 - <<'PY'
import json,pathlib
root=pathlib.Path('/mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002')
d=json.loads((root/'control/approved_decision.json').read_text())
expected=dict(candidate='D3_controlled_opening_20261020',
 contract_sha256='f737cfd0673861b6ddf815e43be0cdcea1498bb0f767106006ff7c1d7548f057',
 host='GPUServer8',output=str(root/'inputs/D3_controlled_opening_20261020/runs'/root.name),
 wall_seconds=600,run_id=root.name)
assert set(d)==set(expected)|{'approval_source'}
assert all(d[k]==v for k,v in expected.items())
assert isinstance(d['approval_source'],str) and d['approval_source'].strip()
PY
for MD03_PATH in code launch.request launch.claim logs/driver.log inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R002; do
  test ! -e "$MD03_PATH"
  test ! -L "$MD03_PATH"
done
# Trusted, byte-identical archives only; never read the R001 partial input.
timeout 120 tar -xzf input_assets.tar.gz -C inputs
timeout 30 tar -xzf code_snapshot.tar.gz
test "$(git -C code rev-parse HEAD)" = fb29771a2d972180c2d57b1fa6345dd4dbb684fe
test -z "$(git -C code status --porcelain)"
# Separate single-use dispatch marker: even an uncertain acknowledgment is not reissued.
mkdir launch.request
nohup bash control/run_cpu.sh > logs/driver.log 2>&1 < /dev/null &
MD03_DRIVER_PID=$!
printf 'dispatch_pid=%s\n' "$MD03_DRIVER_PID"
printf 'dispatch_utc=%s\n' "$(date -u +%FT%TZ)"
# This acknowledges dispatch only; actual start/worker/terminal receipts decide execution state.
