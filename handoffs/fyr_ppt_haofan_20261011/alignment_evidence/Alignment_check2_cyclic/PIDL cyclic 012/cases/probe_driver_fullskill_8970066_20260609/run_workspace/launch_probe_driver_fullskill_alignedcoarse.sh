#!/usr/bin/env bash
set -u
REMOTE_ROOT='/mnt/data2/drtao/wennie/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404'
ARCHIVE_ROOT='/mnt/data2/drtao/pidl_archives/pf_probe_driver_fullskill_alignedcoarse_8970066_20260609_174404'
GPU=2
cd "$REMOTE_ROOT/code/SENS_tensile"
export CUDA_VISIBLE_DEVICES="$GPU"
export PIDL_ARCHIVE_DIR="$ARCHIVE_ROOT"
echo "[launch] date=$(date -Iseconds) host=$(hostname) gpu=$GPU"
echo "[launch] cwd=$(pwd)"
echo "[launch] archive_root=$ARCHIVE_ROOT"
echo "[launch] command=/usr/bin/python3 -u run_fem_mesh_probe_driver_umax.py 0.12 --n-cycles-physical 120 --seed 1 --mesh-file meshed_geom_fem_soft_hist0.msh --coarse-mesh-file meshed_geom_fem_soft_hist0.msh --fracture-confirm-cycles 3 --plot-every 20"
/usr/bin/python3 -u run_fem_mesh_probe_driver_umax.py 0.12 --n-cycles-physical 120 --seed 1 --mesh-file meshed_geom_fem_soft_hist0.msh --coarse-mesh-file meshed_geom_fem_soft_hist0.msh --fracture-confirm-cycles 3 --plot-every 20
train_status=$?
echo "[train_exit] status=$train_status date=$(date -Iseconds)"
if [ "$train_status" -eq 0 ]; then
  archive_dir=$(find "$ARCHIVE_ROOT" -maxdepth 1 -mindepth 1 -type d -name 'probeDriver_*' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
  echo "[posthoc] archive_dir=$archive_dir"
  if [ -n "$archive_dir" ] && [ -d "$archive_dir" ]; then
    /usr/bin/python3 -u export_pidl_mapped_state_fields.py --archive "$archive_dir" --out-dir "$archive_dir/mapped_state_fields_skill" --cycles 1,2,3,20,40,60,69 --umax 0.12 --device cuda --pidl-mesh meshed_geom_fem_soft_hist0.msh
    echo "[posthoc_exit] status=$? date=$(date -Iseconds)"
  else
    echo "[posthoc_skip] no archive_dir found"
  fi
fi
exit "$train_status"
