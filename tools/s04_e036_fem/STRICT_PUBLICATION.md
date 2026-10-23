# Published main steps as strict/oracle predecessors

`verified_window_step` retains its existing `main_window_result_file` /
`main_window_result_sha256` path for a completed main window. Alternatively,
strict/oracle c1 or c83 s2/s4 may supply **all five** file/hash pairs:

- `main_config_file`, `main_config_sha256`
- `main_driver_binding_file`, `main_driver_binding_sha256`
- `main_input_binding_file`, `main_input_binding_sha256`
- `main_authority_file`, `main_authority_sha256`
- `main_manifest_file`, `main_manifest_sha256`

The two proof forms are mutually exclusive. The existing `path` / `sha256`,
`proposal_file` / `proposal_sha256`, `completion_file` / `completion_sha256`
and `state_key` still select exactly main s1 for s2, or main s3 for s4.
No target or future physics fields are added.

Stage byte-identical proof copies below the new strict task root:

```text
main_source/<original_label>_config.json
main_source/<original_label>_authority.json
main_source/<original_label>_manifest.json
main_source/output/<original_label>/driver_binding.mat
main_source/output/<original_label>/window/input_binding.mat
main_source/output/<original_label>/window/cCCCC_sSS/{completion,proposal,readback}.mat
main_source/output/<original_label>/window/cCCCC_sSS/step_checkpoint.mat
```

Include each published step from s1 through the selected predecessor. Original
paths inside the JSON/MAT bytes stay unchanged. The new config/manifest bind
the staged copies; the original config must exactly match the original saved
driver config, and the original authority must match its saved approval.
The original manifest hash and original run label remain mandatory.

The loader checks the original main five-step request and its actual input
authority, then verifies every old-step completion, proposal, checkpoint and
readback. Each proposal's old u/d/lower/history/version/key must exactly equal
the preceding published state; c1's input arrays must also equal the already
bound stored U0. `e036_verify_persisted` and current native predecessor
admission remain mandatory. No fields are clipped, filled, repaired or solved
by the publication reader. No parent-window completion is inferred.

## Direct consistency check, 2026-10-23

One h5py/NumPy I/O check used the existing local main_c1_01 terminal retrieval
and source manifest `analysis/main_c1_published_prefix_sources_20261023.json`.
It checked original config/driver and authority equality, exact U0/input
arrays, actual s1–s3 completion/proposal/checkpoint/readback chains, and the
new generator validator for relocated strict c1s2/c1s4 specs. These checks
passed. The final failure-label assertion initially expected the wrong label;
only that assertion was corrected against the actual records:
`E036:OuterExhausted`, c1s4, outer 1500, three commits, no `window_result.mat`.
The parent failure is unchanged.

Original main config SHA256:
`4fc4c4d4bf1e00e681cbf4e214c7ea4d1455129b9713bb885df787fee1ba7457`.
Selected main s1 checkpoint:
`275096dafc587d94383744104272b07d97ca49e47781a1846a417e01bfa32da4`.
Selected main s3 checkpoint:
`36193d74aba9b0d894524a391271412068bd8ebd220ce5d8b074d795f7eb937b`.

This check performed zero native calls, MATLAB executions, optimizations or
history updates. The MATLAB branch and c83 data were not executed. The strict
joint/u tolerances remain 4e-6 / 1e-8. No main dispatch source was modified.
