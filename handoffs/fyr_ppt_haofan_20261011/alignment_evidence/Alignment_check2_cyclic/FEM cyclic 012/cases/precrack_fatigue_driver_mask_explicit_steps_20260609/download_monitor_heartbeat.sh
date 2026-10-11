#!/usr/bin/env bash
set -u

SRC="/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_20260609"
SRC_MANIFEST="/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_MANIFEST_20260610"
CASE_DIR="/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check 2/FEM cyclic 012/cases/precrack_fatigue_driver_mask_explicit_steps_20260609"
DEST="$CASE_DIR/raw_data/state_field_exports/latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_20260609"
DEST_MANIFEST="$CASE_DIR/raw_data/state_field_exports/latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_MANIFEST_20260610"
LOG="$CASE_DIR/logs/download_heartbeat.log"

MAT_NAME="latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_fields.mat"
INDEX_NAME="latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_index.csv"

mkdir -p "$DEST" "$DEST_MANIFEST" "$(dirname "$LOG")"

bytes_or_zero() {
  local path="$1"
  if [ -e "$path" ]; then
    stat -f '%z' "$path" 2>/dev/null || printf '0'
  else
    printf '0'
  fi
}

resident_or_zero() {
  local path="$1"
  if [ -e "$path" ]; then
    du -k "$path" 2>/dev/null | awk '{print $1 * 1024}'
  else
    printf '0'
  fi
}

log_status() {
  local now src_mat dst_mat src_logical src_resident dst_logical dst_resident
  now="$(date '+%Y-%m-%d %H:%M:%S %Z')"
  src_mat="$SRC/$MAT_NAME"
  dst_mat="$DEST/$MAT_NAME"
  src_logical="$(bytes_or_zero "$src_mat")"
  src_resident="$(resident_or_zero "$src_mat")"
  dst_logical="$(bytes_or_zero "$dst_mat")"
  dst_resident="$(resident_or_zero "$dst_mat")"
  {
    printf '[%s] src_logical=%s src_resident=%s dst_logical=%s dst_resident=%s\n' \
      "$now" "$src_logical" "$src_resident" "$dst_logical" "$dst_resident"
    if [ -e "$SRC/$INDEX_NAME" ]; then
      printf '[%s] state_index_rows=%s\n' "$now" "$(wc -l < "$SRC/$INDEX_NAME" | tr -d ' ')"
    fi
  } >> "$LOG"
}

copy_once() {
  log_status
  {
    printf '\n[%s] starting rsync package copy\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
    printf 'SRC=%s\nDEST=%s\n' "$SRC" "$DEST"
  } >> "$LOG"

  rsync -a --partial --inplace --progress "$SRC/" "$DEST/" >> "$LOG" 2>&1 &
  local rsync_pid=$!

  while kill -0 "$rsync_pid" 2>/dev/null; do
    log_status
    sleep 60
  done

  wait "$rsync_pid"
  local rc=$?
  log_status
  {
    printf '[%s] rsync package exit=%s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$rc"
  } >> "$LOG"
  return "$rc"
}

wait_for_materialized_mat() {
  local src_mat src_logical src_resident
  src_mat="$SRC/$MAT_NAME"
  while true; do
    log_status
    src_logical="$(bytes_or_zero "$src_mat")"
    src_resident="$(resident_or_zero "$src_mat")"
    if [ "$src_logical" != "0" ] && [ "$src_resident" -ge "$src_logical" ]; then
      {
        printf '[%s] source MAT appears fully resident: %s bytes\n' \
          "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$src_resident"
      } >> "$LOG"
      return 0
    fi
    {
      printf '[%s] waiting for OneDrive materialization before copying MAT\n' \
        "$(date '+%Y-%m-%d %H:%M:%S %Z')"
    } >> "$LOG"
    sleep 60
  done
}

{
  printf 'heartbeat_start=%s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
  printf 'case_dir=%s\n' "$CASE_DIR"
  printf 'source=%s\n' "$SRC"
  printf 'manifest_source=%s\n' "$SRC_MANIFEST"
} >> "$LOG"

attempt=1
wait_for_materialized_mat
while true; do
  {
    printf '\n[%s] attempt=%s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$attempt"
  } >> "$LOG"
  if copy_once; then
    src_size="$(bytes_or_zero "$SRC/$MAT_NAME")"
    dst_size="$(bytes_or_zero "$DEST/$MAT_NAME")"
    if [ "$src_size" = "$dst_size" ] && [ "$dst_size" != "0" ] && [ -e "$DEST/$INDEX_NAME" ]; then
      rsync -a "$SRC_MANIFEST/" "$DEST_MANIFEST/" >> "$LOG" 2>&1 || true
      {
        printf '[%s] DONE package copied and size matched: %s bytes\n' \
          "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$dst_size"
        printf 'dest=%s\n' "$DEST"
        printf 'dest_manifest=%s\n' "$DEST_MANIFEST"
      } >> "$LOG"
      exit 0
    fi
    {
      printf '[%s] copy incomplete after successful rsync; src_size=%s dst_size=%s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$src_size" "$dst_size"
    } >> "$LOG"
  fi
  attempt=$((attempt + 1))
  sleep 60
done
