# Local native payload preparation

`prepare_native_payload.py` only creates local text/config/ZIP artifacts. It
does not SSH, launch MATLAB, compile, solve, compare physical arrays or train.
Outputs must be new. ZIP members are checked by byte readback.

`support` reads the two exact pinned original scripts, creates `overlay_02`
using the reviewed overlay builder, and emits `native_inventory_02.ps1`.
The latter only inventories SHA256 hashes of existing native snapshot files;
the root executor chooses whether and when to run it remotely.

```text
python tools/s04_e036_fem/prepare_native_payload.py support
  --audited-source-dir /absolute/local_archive/pidl_cyclic_audit_20261021/fem_live
  --run-root C:/Users/xw436/jobs/E036_A_20261021_2142
  --output /absolute/run_workspace/native_support_02
```

After the root retrieves the actual inventory, preparation result, fresh
build receipt and completion marker, `finalize` creates one mode's manifest,
config, entry and a separately supplied attempt authority. It refuses absent
or mismatched build hashes, wrong task roots, changed overlay helpers, and
preparation receipts from another config. It binds the original snapshot's
support MEX files and the two fresh-built kernels separately. Runtime paths
retain Windows path semantics; MATLAB uses canonical path comparisons.

```text
python tools/s04_e036_fem/prepare_native_payload.py finalize
  --support /absolute/run_workspace/native_support_02
  --inventory /absolute/retrieved/native_inventory_02.json
  --snapshot-receipt /absolute/logs/stage_snapshot_continuation_01.json
  --prepare-config /absolute/run_workspace/prepare_02_config.json
  --prepare-manifest /absolute/run_workspace/prepare_02_manifest.json
  --prepare-result /absolute/retrieved/prepare_result.json
  --build-receipt /absolute/retrieved/build_receipt.json
  --build-completion /absolute/retrieved/completion.json
  --authority-file /absolute/run_workspace/disabled_02_authority.json
  --label disabled_02 --mode disabled
  --output /absolute/run_workspace/disabled_02_payload
```

Commands are split for readability; use shell continuation or one line. Use
the exact deployed preparation config/manifest revision. The inventory and
snapshot receipt may be plain JSON or a successful root-command receipt with
JSON in `stdout`. Build and preparation JSON files must be exact retrieved
bytes, because their hashes enter the next config.

The supplied authority must use `e036-stage-a-authority-v1`, stage A, this
run root and producer, exactly the requested `allowed_labels=[label]`, a
human instruction reference and timestamp, and explicit finite positive
per-job timeout. Disabled mode also requires a positive arm timeout. A null
global deadline is permitted. The generator never constructs approval and
does not inherit the preparation attempt's label/authority.

The five permitted modes are `disabled`, `frozen_c1`, `frozen_c20`,
`frozen_c60`, `frozen_c83`. Their archived s3/s4 pairs come only from the
original snapshot input receipt. The output config uses `code_root`,
`native_snapshot`, and `build_root` from the successful preparation config,
`overlay_02`, and a fresh `output/<label>` directory. Manifest paths are
relative to the run root. Uploading/unpacking and invoking a launcher remain
root-executor actions; generating a payload is not execution evidence.
