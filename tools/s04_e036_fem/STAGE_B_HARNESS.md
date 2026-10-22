# Conditional Stage B entry — prepared only, 2026-10-22

These files have been written and read statically. They have not been executed
by MATLAB, checked by MATLAB `checkcode`, or validated with a native solve.
They are not a statement that Stage A passed or Stage B is ready to launch.
The latest user instruction permits Stage B after successful Stage A; the
driver enforces the recorded Stage A evidence before native context creation.
Historical locks, stopped attempts and earlier resource proposals are retained.

## Current authority and clocks

Stage A now reads `config.authority_file` and `config.authority_sha256` through
`e036_stage_a_authority`. The file must be inside `run_root`. Its schema is
`e036-stage-a-authority-v1`, with `stage="A"`, `authority_id`, `run_root`,
`producer_hostname`, `allowed_labels`, `authorized_at_utc`,
`human_authorization_ref`, `max_compute_threads`, `global_deadline_utc`,
`per_job_wall_seconds` and `arm_wall_seconds`. UTC strings use whole seconds
and a trailing `Z`. An explicit JSON null global deadline removes the previous
cumulative deadline. There is no fallback to the expired deadline or old
1,200/600/1,800/3,600-second limits. Each job still has an explicit finite
positive timeout; each disabled arm also requires one. Threads remain at most
four. Numeric solver settings and scientific tolerances are unchanged.

Stage B uses the corresponding `e036-stage-b-authority-v1`, `stage="B"`, plus
`request`, `step_wall_seconds`, `stage_a_evidence_sha256` and
`implementation_review_ref`. Its independent process guard applies to one
window, including setup, admission, solve and I/O. The per-step cooperative
guard cannot interrupt a blocking MEX/CHOLMOD call; the window-level external
watchdog does. No automatic retry, recovery or trajectory replay is added.
The Stage B PS files are separate from the frozen Stage A launcher/watchdog.

## Driver and evidence input

```matlab
result = e036_stage_b_driver(config_file,config_sha256);
```

The config binds the same actual native snapshot, fresh build receipt,
CHOLMOD/MEX/function paths and hashes, ordered mesh, stored derived U0,
source manifest and provenance as Stage A. It additionally carries `request`,
`predecessor`, `source_commit`, `stage_a_evidence_file` and its SHA, and the
explicit Stage B authority file/hash. Every actual MATLAB helper and runtime
MATLAB source must occur in the source manifest. Paths are canonicalized on
Windows. A config must not carry `pairs`, `target` or `targets`.

`request` has only `cycle`, `substeps`, `role`: main c1/c83 steps 1–5, main
c20/c60 step 4, or tightening c83 step 4. The normal settings stay at inner
250/250, outer 1500, mechanical `1e-6` and joint/phase `4e-4`. The predefined
tightening case uses `1e-8` and `4e-6`; this is not a rescue after failure.

The evidence file schema is `e036-stage-a-evidence-v1`:

- `prepare` and `disabled`: each `{path,sha256}` for the actual driver JSON.
- `frozen`: four objects with `cycle` in 1/20/60/83, `native` and `comparison`,
  each a `{path,sha256}`. The native export bytes must still match the reported
  hash; comparison must report matched at `1e-10 + 1e-8*maxabsref`. Its recorded
  runtime bindings must match the current bindings.
- `supervisors`: ten `{role,label,path,sha256}` records, with roles `prepare`,
  `disabled`, `native_c1/c20/c60/c83`, and `comparison_c1/c20/c60/c83`.
  Each also supplies `{path,sha256}` references in `supervisor_attempt`,
  `watchdog_attempt`, `watchdog_finished`, and, for MATLAB jobs, `config`.
  Completion paths, hashes and labels must all be distinct. The driver links
  the actual attempt, authority, entry bytes and corresponding result/config;
  comparator jobs additionally bind the argv input/output and input hashes.
  Each must record completed, zero exit, stopped watchdog and unchanged global
  policy, with no failure. Repeating a successful receipt under another role
  does not qualify that role. A successful mock or launch receipt alone is
  not a replacement for a successful native job.

## Exact predecessor inputs

`predecessor` always has `kind`, `path`, `sha256`, `state_key`. The physical
key includes trajectory, nominal Umax, cycle, substep, actual displacement,
post-commit timing and GP order. Supported kinds are:

- `stored_u0`: only the already bound E011 derived common U0, version 0.
- `request28_post_commit`: the native snapshot schema with exact node/cell
  order, fields, cycle/substep and all three commit flags. Also requires
  `origin_file/origin_sha256`; origin schema `e036-predecessor-origin-v1`
  contains `source_sha256`, `producer_source_path`, the same `state_key` and
  `provenance_ref`. A transfer receipt without original source identification
  does not satisfy this input.
- `verified_window_step`: requires `proposal_file/proposal_sha256` and
  `completion_file/completion_sha256`, with exact verified native field-schema
  checkpoint and readback hashes. Tightening additionally requires
  `main_window_result_file/main_window_result_sha256`, proving that the exact
  c83s3 predecessor came from the completed main c83 window.

The importer preserves all four history channels. It rejects nonfinite old
slot 1 rather than filling or reinterpreting it, checks the existing fatigue
mapping and native field-derived active driver, then evaluates current native
residuals without solving. No returned proposal is committed during admission.
It persists the admitted preimage and returns only the exact read-back fields.
The window preserves its existing single commit after verified persistence.

## Remaining producer validation and data gaps

The new Stage B files need independent review and actual MATLAB checkcode,
interface, persistence and native validation under the explicit authority.
No Stage A completion bundle currently accompanies this source preparation.
The root executor must bind real receipt hashes; no pass placeholders may be
substituted. No per-window producer config is fabricated from missing results.

A local candidate c82s5 exists at
`local_archive/experiments/S04-E036/pidl_readiness_20261022/source_c0082_s005_post_commit.mat`.
Its transfer receipt reports SHA
`74cf5191419c485d2328722967e6d7ecaf2beca3df4d566230ef553170751918`
and 35,579,306 bytes, but does not identify its original producer path. This
preparation has not read its MAT arrays or established its admission. c20/c60s3
and derived U0 already have documented archive locations, but they still need
the new current-runtime admission. A missing or failed predecessor stops that
window; it does not authorize replacing fields or regenerating history.
