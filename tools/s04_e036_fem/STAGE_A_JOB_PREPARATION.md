# Stage A native job preparation

`prepare_stage_a_job.py` generates files locally. It does not connect to a host,
start a process remotely, call MATLAB, assemble an FE system or train a model.
There is no Stage B mode. The current human division leaves B/training to its
other owner.

The helper calls the existing metadata-only `prepare_native_payload.finalize`.
It requires actual successful preparation, native inventory and fresh-build
receipts; it cannot turn a failed preparation into a successful one. In particular,
prepare03's observed EOF software failure is not a usable preparation result.

All code/build/result directories come from `--prepare-config`, so the helper
does not assume a successful prepare02, prepare03 or prepare04. Keep previous
outputs and failed logs unchanged.

```text
python tools/s04_e036_fem/prepare_stage_a_job.py
  --support /absolute/run_workspace/native_support_02
  --inventory /absolute/retrieved/native_inventory.json
  --snapshot-receipt /absolute/logs/stage_snapshot_continuation_01.json
  --prepare-config /absolute/exact_deployed_prepare_config.json
  --prepare-manifest /absolute/exact_deployed_prepare_source_manifest.json
  --prepare-result /absolute/retrieved/prepare_result.json
  --build-receipt /absolute/retrieved/build_receipt.json
  --build-completion /absolute/retrieved/completion.json
  --authority-file /absolute/new_attempt_authority.json
  --control-deployment /absolute/control_payload/deployment.json
  --control-directory /absolute/control_payload
  --label disabled_04 --mode disabled
  --output /absolute/run_workspace/disabled_04_job
```

Combine the displayed lines into one shell command or use shell continuation.
Change only the explicit label/mode/authority/output for another approved Stage A
job; allowed modes are `disabled`, `frozen_c1`, `frozen_c20`, `frozen_c60`,
`frozen_c83`. Labels are never reused.

`--control-deployment` must contain exactly one native
`stage_a_watchdog_v4.ps1` entry. Its relative path is resolved under
`--control-directory` for the local bytes and under the configured remote task
root for the eventual control file. This may reference the already staged
`control_03` directory even when the subsequent successful preparation is a new
label; only the exact v4 control bytes are reused. The helper validates this hash
against the current independently reviewed v4 source. It does not deploy controls.

Each authority is supplied separately. It must bind Stage A, the producer and
task root, exactly the new label, <=4 threads and an explicit positive per-job
hang guard; disabled mode also requires its arm guard. The helper never creates
or broadens authority.

The fresh output contains:

- `native_payload/`, its ZIP and receipt: unchanged standalone finalizer artifacts.
- `deploy/`: four native authority/config/manifest/entry files, the existing
  overlay, and generated deployment/preflight/launch scripts.
- `<label>_job_payload.zip` and `job_receipt.json`: exact member hashes, runtime
  dependencies, dynamic code/build/result roots and generator/control hashes.

The root executor can inspect and stage the ZIP once into a fresh incoming
directory. Run `stage_<label>.ps1 -PayloadDirectory <incoming>` only when authorized
to stage that package. It validates all source bytes and destinations first;
new attempt files must be absent, while an existing overlay is reused only when
its exact hash matches. Copies never replace files. Partial staging failures stay
visible and do not start a process.

The generated `<label>_preflight.ps1` is read-only. It verifies the full native
manifest, actual runtime bindings (including CHOLMOD), fresh kernel source/staged
source hashes, preparation/build receipts, launcher/v4 watchdog and the new
attempt files. It checks unused outputs/log names and producer resources. This
is a software/deployment check, not numerical evidence.

`launch_<label>.ps1` repeats that exact hashed preflight, records a fresh launch
request, and submits a detached `cmd` → full x64 Windows PowerShell → reviewed
launcher → v4 watchdog chain with outer stdout/stderr capture. The disabled mode
adds `-RequireArms`. ExecutionPolicy Bypass is scoped to child processes; no
global policy is changed. A WMI creation receipt is not a MATLAB/FEM result.
Unknown creation outcomes keep their request/receipt and never trigger a retry.

Root must independently verify the actual supervisor/watchdog/driver outcomes.
No earlier tests, generated package, static review or process-creation result
establishes Stage A numerical agreement.
