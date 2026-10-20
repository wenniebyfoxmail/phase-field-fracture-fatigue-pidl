#!/usr/bin/env bash
# LOCAL orchestrator: preparation only, requires a separately approved R002 decision.
set -euo pipefail
MD03_PY=/Users/wenxiaofang/miniconda3/bin/python3
MD03_CTL=/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/docs/research/S03/S03-E049-MD03/recovery_20261020
MD03_OLD_PAYLOAD=/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020/deployment_20261020
MD03_PAYLOAD=/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020/recovery_20261020_R002
MD03_ROOT=/mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002
MD03_SSH=(ssh -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o ControlMaster=no -o ControlPath=none -o ServerAliveInterval=10 -o ServerAliveCountMax=2 gpu-taobo)
test -f "$MD03_PAYLOAD/approved_decision.json"
"$MD03_PY" - "$MD03_CTL" "$MD03_PAYLOAD" "$MD03_OLD_PAYLOAD" <<'PY'
import hashlib,json,pathlib,sys
ctl,payload,old=map(pathlib.Path,sys.argv[1:])
template=json.loads((ctl/'decision_template.json').read_text())
decision=json.loads((payload/'approved_decision.json').read_text())
assert template['approval_source'] is None
assert set(template)==set(decision)
assert all(decision[k]==v for k,v in template.items() if k!='approval_source')
assert isinstance(decision['approval_source'],str) and decision['approval_source'].strip()
expected={
 'remote_contract.json':'f737cfd0673861b6ddf815e43be0cdcea1498bb0f767106006ff7c1d7548f057',
 'run_cpu.sh':'c9365dce790f42eeba7880bbcede0c46c81d74aafd6cd3438a970870a7c75a7b',
 'first_admission.sh':'ce83f1c018189eb9c62258da36c3ff70056fc765d09b2067521495d8f645072d',
 'stage_and_launch.sh':'fefdf9ece2e794023cd7b22b53ab80981764c6aceccacfe14f28c4bccb4d5675',
 'source_snapshot.json':'1ed64881731b27baf56ffdc2269515fa4f2edf34de92c395dbe51cabf91a40e4',
 'decision_template.json':'a5880ade82dabb1f61050d93700ac270802f6617d720b77d6e503367484538b3',
 'collect_once.py':'773d33383614e60ae1bbda245ba7c70f76185c43ea0fe27ddb4275783a100a5e',
}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024**2),b''): h.update(chunk)
    return h.hexdigest()
assert all(sha(ctl/name)==digest for name,digest in expected.items())
assert (old/'input_assets.tar.gz').stat().st_size==113514186
assert sha(old/'input_assets.tar.gz')=='6ce79a5e1cd75615d2bf1b1712349409210244a878b4d5123e3059bd81279240'
raw=(ctl/'remote_contract.json').read_bytes()
assert raw==json.dumps(json.loads(raw),indent=2,allow_nan=False).encode()
print('Local approval/path/hash binding verified; no remote action yet')
PY
# Exclusive local attempt marker; never reset after any partial/failed attempt.
mkdir "$MD03_PAYLOAD/attempt"
MD03_ATTEMPT="$MD03_PAYLOAD/attempt"
cp -p "$MD03_PAYLOAD/approved_decision.json" "$MD03_ATTEMPT/approved_decision.json"
bounded() {
  "$MD03_PY" -c '
import os,signal,subprocess,sys
child=subprocess.Popen(sys.argv[2:],start_new_session=True)
try:
    code=child.wait(timeout=int(sys.argv[1]))
except subprocess.TimeoutExpired:
    # Only this freshly spawned local process group, never a remote/shared PID.
    try: os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError: pass
    try: child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try: os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError: pass
        child.wait()
    print("TIMEOUT: local task stopped; remote state unknown; NO RETRY",file=sys.stderr)
    sys.exit(124)
sys.exit(code if code>=0 else 128-code)
' "$@"
}
step() {
  local MD03_LABEL=$1 MD03_SECONDS=$2
  shift 2
  printf '%s\t%s\tstart\n' "$(date -u +%FT%TZ)" "$MD03_LABEL" >> "$MD03_ATTEMPT/stages.tsv"
  bounded "$MD03_SECONDS" "$@" > "$MD03_ATTEMPT/$MD03_LABEL.stdout" 2> "$MD03_ATTEMPT/$MD03_LABEL.stderr"
  printf '%s\t%s\tcompleted\n' "$(date -u +%FT%TZ)" "$MD03_LABEL" >> "$MD03_ATTEMPT/stages.tsv"
  printf 'Completed %s\n' "$MD03_LABEL"
}
step admission 60 "${MD03_SSH[@]}" 'bash -s' < "$MD03_CTL/first_admission.sh"
step fresh_root_and_code_copy 60 "${MD03_SSH[@]}" 'set -e; test "$(hostname)" = GPUServer8; test "$(id -un)" = drtao; test ! -e /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002; test ! -L /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002; test "$(sha256sum /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/code_snapshot.tar.gz | cut -d" " -f1)" = f6fabf39e12355e87d4711b734217b0bbac3d491ea4c86ee653f68d4443e81e3; mkdir /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002; mkdir -p /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002/control /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002/inputs /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002/logs /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002/tmp /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002/cache/matplotlib; cp --no-clobber /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R001/code_snapshot.tar.gz /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002/code_snapshot.tar.gz; test "$(sha256sum /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002/code_snapshot.tar.gz | cut -d" " -f1)" = f6fabf39e12355e87d4711b734217b0bbac3d491ea4c86ee653f68d4443e81e3'
# No append/inplace/delete, no R001 destination, no code-archive upload.
step input_transfer 900 /usr/bin/rsync -a --partial --timeout=120 --stats -e 'ssh -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o ControlMaster=no -o ControlPath=none -o ServerAliveInterval=10 -o ServerAliveCountMax=2' "$MD03_OLD_PAYLOAD/input_assets.tar.gz" "gpu-taobo:$MD03_ROOT/"
step control_transfer 120 /usr/bin/rsync -a --partial --timeout=120 --stats -e 'ssh -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o ControlMaster=no -o ControlPath=none -o ServerAliveInterval=10 -o ServerAliveCountMax=2' "$MD03_CTL/remote_contract.json" "$MD03_CTL/source_snapshot.json" "$MD03_CTL/run_cpu.sh" "$MD03_PAYLOAD/approved_decision.json" "gpu-taobo:$MD03_ROOT/control/"
step verify_extract_dispatch 180 "${MD03_SSH[@]}" 'bash -s' < "$MD03_CTL/stage_and_launch.sh"
printf 'Dispatch acknowledged only. Reconcile R002 receipts; never reissue launch.\n'
"$MD03_PY" "$MD03_CTL/collect_once.py"
