#!/usr/bin/env bash
# E022 deployment only; scientific checkout remains the reviewed a540888 source.
set -Eeuo pipefail
ROOT=/mnt/data2/drtao/wennie/S04-E022-last-leak-a540888-20261016-v1
BASE19=/mnt/data2/drtao/wennie/S04-E019-frozen-ae23871-20261014-v1
BASE21=/mnt/data2/drtao/wennie/S04-E021-coordinate-98c6206-20261015-v2
COMMIT=a540888497d1838a6aa202f59a884e6930e50fb4
BUNDLE_SHA=ead5a95d9877a9ad521007536504617392245541501f042d1bf949168717cfc4
[[ "$(uname -s)" == Linux ]]
mountpoint -q /mnt/data2
[[ "$(id -un)" == drtao ]]
[[ "$(hostname)" == GPUServer8 ]]
[[ "$PWD" == "$ROOT" ]]
[[ ! -e "$ROOT/code" && ! -e "$ROOT/aggregate" ]]
[[ "$(sha256sum "$ROOT/E022_a540888.bundle" | cut -d ' ' -f 1)" == "$BUNDLE_SHA" ]]
# Atomic one-shot marker: failures remain inspectable and are never retried.
mkdir "$ROOT/DISPATCH_ONCE"
mkdir -p "$ROOT/logs"
phase=initial_preflight
trap 'rc=$?; printf "FAILED rc=%s phase=%s utc=%s\n" "$rc" "$phase" "$(date -u +%FT%TZ)" > "$ROOT/dispatcher.status"; exit "$rc"' ERR
printf 'RUNNING pid=%s utc=%s\n' "$$" "$(date -u +%FT%TZ)" > "$ROOT/dispatcher.status"
printf '%s\n' "$$" > "$ROOT/dispatcher.pid"
export E022_ROOT="$ROOT" E022_BASE19="$BASE19" E022_BASE21="$BASE21" E022_COMMIT="$COMMIT"
export CUDA_VISIBLE_DEVICES=0 CUBLAS_WORKSPACE_CONFIG=:4096:8
export TMPDIR="$ROOT/cache/tmp" XDG_CACHE_HOME="$ROOT/cache/xdg"
export TORCH_HOME="$ROOT/cache/torch" TORCH_EXTENSIONS_DIR="$ROOT/cache/torch_extensions"
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH PYTHONHOME

resource_check() {
 local tag=$1 available_kb free_mem gpu_uuid apps
 mountpoint -q /mnt/data2 || return 1
 df -h / /mnt/data2 /mnt/data3 > "$ROOT/logs/${tag}_disk.txt" || return 1
 available_kb=$(df -Pk /mnt/data2 | awk 'NR==2 {print $4}') || return 1
 [[ "$available_kb" -gt 8388608 ]] || return 1
 nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader > "$ROOT/logs/${tag}_gpu.txt" || return 1
 nvidia-smi pmon -c 1 > "$ROOT/logs/${tag}_processes.txt" || return 1
 free_mem=$(nvidia-smi -i 0 --query-gpu=memory.free --format=csv,noheader,nounits) || return 1
 [[ "$free_mem" -gt 8192 ]] || return 1
 gpu_uuid=$(nvidia-smi -i 0 --query-gpu=uuid --format=csv,noheader) || return 1
 apps=$(nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader) || return 1
 printf '%s\n' "$apps" > "$ROOT/logs/${tag}_compute_apps.txt" || return 1
 # Shared GPU0 allowed: log existing contexts; keep the >8GiB free-memory gate.
 if [[ -e "$ROOT/gpu0.uuid" ]]; then
  [[ "$(cat "$ROOT/gpu0.uuid")" == "$gpu_uuid" ]] || return 1
 else
  printf '%s\n' "$gpu_uuid" > "$ROOT/gpu0.uuid" || return 1
 fi
}
resource_check initial
mkdir "$ROOT/inputs" "$ROOT/backbones" "$ROOT/controls" "$ROOT/coordinate_controls" "$ROOT/runs"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$TORCH_HOME" "$TORCH_EXTENSIONS_DIR"
command -v python3 > "$ROOT/logs/python_executable.txt"
[[ "$(git -C "$BASE19/code" rev-parse HEAD)" == ae23871366158c5e9a98fcca9fe2353675d997ec ]]
[[ "$(git -C "$BASE21/code" rev-parse HEAD)" == 98c620637b2b2ef06ec86983220a4e7f9f1053b7 ]]
phase=source_checkout
git clone --no-hardlinks --no-checkout "$BASE21/code" "$ROOT/code"
cd "$ROOT/code"
git bundle verify "$ROOT/E022_a540888.bundle"
git fetch "$ROOT/E022_a540888.bundle" refs/heads/codex/e022-producer-snapshot-20261016
git checkout --detach "$COMMIT"
[[ "$(git rev-parse HEAD)" == "$COMMIT" && -z "$(git status --porcelain)" ]]
phase=copy_existing_assets
python3 - <<'COPY'
import hashlib,json,os,shutil
from pathlib import Path
root=Path(os.environ['E022_ROOT']);old=Path(os.environ['E022_BASE19']);previous=Path(os.environ['E022_BASE21'])
locks=json.loads(Path('docs/research/S04/S04-E020/control_locks.json').read_text())
direct_locks=json.loads(Path('docs/research/S04/S04-E022/e021_control_locks.json').read_text())
files=[]
for state in ('c20s4','c60s4','c83s4'):
    lock=locks[state]
    pairs=[(old/'inputs'/f'{state}.npz',root/'inputs'/f'{state}.npz')]
    for name in ('final_step_10000.pt','prediction.npz','metrics.json','monitoring.json','RUN_RECEIPT.json'):
        pairs.append((old/'backbones'/state/name,root/'backbones'/state/name))
    for name in lock['files']:
        pairs.append((old/'runs'/lock['run_id']/name,root/'controls'/lock['run_id']/name))
    direct=direct_locks[state]
    for name in direct['files']:
        pairs.append((previous/'runs'/direct['run_id']/name,root/'coordinate_controls'/direct['run_id']/name))
    for source,dest in pairs:
        if not source.is_file() or source.is_symlink() or dest.exists():
            raise RuntimeError(f'asset is absent, a symlink or destination reused: {source} -> {dest}')
        dest.parent.mkdir(parents=True,exist_ok=True)
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copy2(source,dest)
        after=hashlib.sha256(dest.read_bytes()).hexdigest()
        if before!=after or hashlib.sha256(source.read_bytes()).hexdigest()!=before:
            raise RuntimeError(f'asset copy differs: {source}')
        files.append(dict(source=str(source),destination=str(dest),bytes=dest.stat().st_size,sha256=after))
(root/'asset_copy_manifest.json').write_text(json.dumps(files,indent=2)+'\n')
print(f'Copied and verified {len(files)} existing assets; no upload of raw training data.')
COPY
phase=all_state_cuda_preflight
python3 - <<'PREFLIGHT'
import copy,json,os,socket,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,'SENS_tensile')
from aggregate_s04_e022_last_leak_screen import prepare_baseline
from run_s04_e022_last_leak_screen import predict_in_chunks,final_metrics,state_digest,anchor_component_geometry
from s04_e022_screen import CONTROL_LOCKS,DIRECT_LOCKS,ACTIVATION_RULE,build_candidate,validate_activation,validate_coordinate_buffers,check_runtime_identity,check_pair_identity,native_replay,schedule_identity,require_direct_native_profile
root=Path(os.environ['E022_ROOT']);rows=[]
if not torch.cuda.is_available() or torch.cuda.device_count()!=1:
    raise RuntimeError('Exactly one visible CUDA device required')
torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
runtime=dict(torch_version=str(torch.__version__),numpy_version=np.__version__,cuda_version=torch.version.cuda,gpu=torch.cuda.get_device_name(0),hostname=socket.gethostname(),cuda_visible_devices=os.environ['CUDA_VISIBLE_DEVICES'],cublas_workspace_config=os.environ['CUBLAS_WORKSPACE_CONFIG'])
# Check every pinned runtime before expensive asset decoding.
for state in ('c20s4','c60s4','c83s4'):
    check_runtime_identity(state,runtime)
    require_direct_native_profile(state,root/'coordinate_controls'/DIRECT_LOCKS[state]['run_id'])
profile=np.asarray(native_replay(),dtype='<f8')
if profile.shape!=(10000,) or not np.isfinite(profile).all():
    raise RuntimeError('Invalid native actual-update LR vector')
np.save(root/'preflight_learning_rates.npy',profile,allow_pickle=False)
for state in ('c20s4','c60s4','c83s4'):
    lock=CONTROL_LOCKS[state]
    data=prepare_baseline(state,root/'inputs'/f'{state}.npz',root/'backbones'/state,root/'controls'/lock['run_id'],root/'coordinate_controls'/DIRECT_LOCKS[state]['run_id'])
    geometry=anchor_component_geometry(data['xy'],data['damage'],data['conn'],data['mass'])
    candidate=build_candidate(7,'localized',geometry,copy.deepcopy(data['base_model']),data['coordinate_mapping']).to(device='cuda',dtype=torch.float64)
    validate_activation(candidate)
    validate_coordinate_buffers(candidate,data['coordinate_mapping'])
    check_pair_identity(state,geometry,state_digest(candidate.backbone),state_digest(candidate.residual))
    xy=torch.tensor(data['xy'],device='cuda',dtype=torch.float64)
    base=predict_in_chunks(candidate.backbone,xy).cpu().numpy()
    initial=predict_in_chunks(candidate,xy).cpu().numpy()
    with np.load(root/'backbones'/state/'prediction.npz') as saved:
        saved_uv=saved['uv'].copy()
    np.testing.assert_allclose(base,saved_uv,rtol=0,atol=1e-12)
    np.testing.assert_allclose(initial,base,rtol=0,atol=0)
    bm=final_metrics(data,base);sm=final_metrics(data,saved_uv)
    np.testing.assert_allclose(bm['displacement_mass_rms_over_abs_Us'],sm['displacement_mass_rms_over_abs_Us'],rtol=0,atol=1e-14)
    if not all(type(bm[k]) is bool and bm[k] for k in ('gate_finite','gate_essential_bc')):
        raise RuntimeError('Initial prediction is nonfinite or violates essential BC')
    rows.append(dict(state=state,paired_e021_run_id=DIRECT_LOCKS[state]['run_id'],activation_rule=ACTIVATION_RULE,direct_regions=data['e021_direct_control']['regions'],paired_control_run_id=lock['run_id'],reference_sha256=data['reference_sha256'],backbone_digest=data['base_digest'],initial_residual_digest=data['initial_residual_digest'],initial_model_digest=state_digest(candidate),coordinate_mapping=data['coordinate_mapping'],cache_max_abs_difference=float(np.max(np.abs(base-saved_uv))),zero_output_max_abs_difference=float(np.max(np.abs(initial-base))),baseline_metrics=bm,control_regions=data['paired_control']['regions']))
    del candidate,xy,initial,base,data
    torch.cuda.empty_cache()
record=dict(scientific_source=os.environ['E022_COMMIT'],training=False,parameter_optimizer_steps=0,runtime=runtime,python_executable=sys.executable,lr_schedule=schedule_identity(native_replay()),actual_update_lr={str(k):float(profile[k-1]) for k in (1,1000,5000,8000,9999,10000)},rows=rows,finished_utc=datetime.now(timezone.utc).isoformat())
(root/'baseline_preflight.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2),flush=True)
PREFLIGHT
# Reserve no outputs; reject reused locations for all rows before any training.
ordinal=0
for state in c20s4 c60s4 c83s4; do
 ordinal=$((ordinal+1));suffix=$(printf 'R%03d' "$ordinal")
 run_id=$(basename "$ROOT")-$suffix-$state-localized-s7
 [[ ! -e "$ROOT/runs/$run_id" && ! -e "/mnt/data2/drtao/pidl_archives/$run_id" && ! -e "$ROOT/logs/$run_id.log" ]]
done
ordinal=0
for state in c20s4 c60s4 c83s4; do
 ordinal=$((ordinal+1));suffix=$(printf 'R%03d' "$ordinal")
 run_id=$(basename "$ROOT")-$suffix-$state-localized-s7
 phase="${suffix}_resource_check"
 resource_check "$suffix"
 [[ "$(git rev-parse HEAD)" == "$COMMIT" && -z "$(git status --porcelain)" ]]
 out=$ROOT/runs/$run_id
 archive=/mnt/data2/drtao/pidl_archives/$run_id
 log=$ROOT/logs/$run_id.log
 control_id=$(python3 -c 'import json,sys;print(json.load(open("docs/research/S04/S04-E020/control_locks.json"))[sys.argv[1]]["run_id"])' "$state")
 direct_id=$(python3 -c 'import json,sys;print(json.load(open("docs/research/S04/S04-E022/e021_control_locks.json"))[sys.argv[1]]["run_id"])' "$state")
 phase="${suffix}_training"
 printf 'START run=%s utc=%s\n' "$run_id" "$(date -u +%FT%TZ)"
 python3 -u SENS_tensile/run_s04_e022_last_leak_screen.py --state "$state" --arm localized --alpha 0.7 --seed 7 --reference "$ROOT/inputs/$state.npz" --backbone-dir "$ROOT/backbones/$state" --control-dir "$ROOT/controls/$control_id" --coordinate-control-dir "$ROOT/coordinate_controls/$direct_id" --out "$out" --run-id "$run_id" --expected-commit "$COMMIT" --archive-root "$archive" --log-path "$log" --device cuda > "$log" 2>&1 &
 child=$!
 printf '%s\n' "$child" > "$ROOT/logs/$run_id.pid"
 wait "$child"
 phase="${suffix}_verify_completion"
 export E022_STATE="$state" E022_RUN_ID="$run_id"
 python3 - <<'VERIFY'
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'SENS_tensile')
from aggregate_s04_e022_last_leak_screen import prepare_baseline,validate_record
from s04_e022_screen import CONTROL_LOCKS,DIRECT_LOCKS
root=Path(os.environ['E022_ROOT']);state=os.environ['E022_STATE'];rid=os.environ['E022_RUN_ID'];run=root/'runs'/rid
archive=Path('/mnt/data2/drtao/pidl_archives')/rid
lock=CONTROL_LOCKS[state]
data=prepare_baseline(state,root/'inputs'/f'{state}.npz',root/'backbones'/state,root/'controls'/lock['run_id'],root/'coordinate_controls'/DIRECT_LOCKS[state]['run_id'])
row=validate_record(run/'metrics.json',os.environ['E022_COMMIT'],{state:data})
receipt=json.loads((run/'RUN_RECEIPT.json').read_text())
for name,want in {**receipt['archive_file_hashes'],'RUN_RECEIPT.json':hashlib.sha256((run/'RUN_RECEIPT.json').read_bytes()).hexdigest()}.items():
    if hashlib.sha256((archive/name).read_bytes()).hexdigest()!=want:
        raise RuntimeError(f'Archive differs from output: {name}')
np.testing.assert_array_equal(np.load(run/'learning_rates.npy',allow_pickle=False),np.load(root/'preflight_learning_rates.npy',allow_pickle=False))
(root/'logs'/f'{rid}.verified.json').write_text(json.dumps(row,indent=2)+'\n')
print(f'COMPLETED_AND_VERIFIED {rid}',flush=True)
VERIFY
done
phase=final_aggregate
python3 SENS_tensile/aggregate_s04_e022_last_leak_screen.py --input-root "$ROOT/runs" --reference-root "$ROOT/inputs" --backbone-root "$ROOT/backbones" --control-root "$ROOT/controls" --coordinate-control-root "$ROOT/coordinate_controls" --code-commit "$COMMIT" --out "$ROOT/aggregate" > "$ROOT/logs/aggregate.log" 2>&1
[[ "$(git rev-parse HEAD)" == "$COMMIT" && -z "$(git status --porcelain)" ]]
printf 'MATRIX_EXECUTION_COMPLETED utc=%s\n' "$(date -u +%FT%TZ)" > "$ROOT/dispatcher.status"
cat "$ROOT/dispatcher.status"
