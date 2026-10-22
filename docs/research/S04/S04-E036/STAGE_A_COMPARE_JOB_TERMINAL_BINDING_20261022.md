# Stage A comparison job: terminal receipt binding

Status: prepared source only, not executed. No comparison is authorised by this
document. The required actual frozen export and its successful terminal receipts
must exist before this helper can generate a comparison job.

The earlier source lock `stage_a_control_hash_repair_lock.json` is preserved
unchanged (SHA-256 `831ad63ce8f73f39ebd53dabeda6256906e8483cb9783bc3eeee9b5fb99e37ad`).
Its comparison helper entry refers to the historical source version
`845f3103a78fed743b9061f02676393a448ed6d23b2d718864eb0c87134da4c5`.

The revised `tools/s04_e036_fem/prepare_stage_a_compare_job.py` is identified by
SHA-256 `e3d88b6b55f173ed799990e3dc4de1875aedec6e5a58aff821d916d205259aa2`.
It additionally requires `--native-finished` and `--native-supervisor`, pointing
to the retrieved `logs/<nativeLabel>_finished.json` and
`logs/<nativeLabel>_supervisor_finished.json`.

The native watchdog must report the same label and authority identity/hash as
the native config/report, exit code 0, `stop_reason=exited`, no wrapper error,
and its own Job Object closed. The supervisor must report that label,
`completed`, watchdog exit code 0 and stopped, no failure, the same authority
hash and the reviewed native v4 watchdog hash. Its before/after global policy
records must both contain the four recorded scopes, compare equal, and report
`global_policy_unchanged=true`. Both actual receipt hashes are included in the
generated remote preflight dependencies and the local job receipt.

This closes the gap where `native_driver_result.json` can exist before the
driver's final clock check or process failure. It adds no numerical work,
tolerance change, retry, source deployment, Stage B or training behaviour.
The helper still preserves creation-outcome-unknown receipts and refuses to
reuse a consumed label or output directory. Only source editing and static
review have been performed for this revision.
