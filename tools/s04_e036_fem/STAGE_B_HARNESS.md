# S04-E036 Stage B reference windows — local preparation, 2026-10-22

This package prepares the F1 references in the isolated gap-attribution
worktree. The timing owner `01a1603e-8e80-7153-a753-d895b9edb7f5` owns Stage A.
No Stage A job is launched here. The current human instruction removes the
cumulative resource ceiling; it retains serial execution, at most four CPU
cores, finite per-job guards and no automatic scientific retry.

The MATLAB and PowerShell entries have not been run or checked by MATLAB
`checkcode` in this worktree. Twenty-three tiny Python serialization, hash, residual,
predecessor and path checks passed. Those tests perform no native assembly,
FEM solve or NN training. No FEM reference result is implied by preparation.

## Numerical scope and input states

The four main requests are c1 steps 1–5, c83 steps 1–5, c20 step 4 and c60
step 4. Four separately scheduled tightening jobs cover c1s2, c1s4, c83s2 and c83s4,
each once, using the exact accepted s1 or s3 checkpoint from its completed
main window. They measure reference sensitivity, not a numerical error bound;
a failed tightening is not followed by a third solve. Main settings are
mechanical `1e-6`, joint `4e-4`; tightening uses `1e-8`, `4e-6`. Inner caps stay
250/250 and outer cap 1500. The primary acceptance is the declared nodal box
problem with the unchanged native soft penalty kernel: exact `0 <= d <= 1`,
healing tolerance `1e-8`, active tolerance `1e-10`, history tolerance `1e-10`.
The 251 precrack damage nodes are prescribed to one and excluded from the
free phase residual. Existing native phase projection remains in place.

Every requested predecessor is read from actual stored native arrays,
checked for exact native mesh/BC/history identity, freshly evaluated without
a solve or repair, persisted and read back before entering the window.
A failure stops that request and preserves the incoming accepted state.
There is no cycle replay, missing-channel filling or recovery solve.

Known source inputs are:

| Requested window | Stored source | SHA256 |
|---|---|---|
| c1 | E011 derived `common_initial.mat`, version 0 | `59a0f81368d0c46a698f94fdfcb32158e96361714d7547f00deed996d4a7c181` |
| c83 | `c0082_s005_post_commit.mat` | `74cf5191419c485d2328722967e6d7ecaf2beca3df4d566230ef553170751918` |
| c20s4 | `c0020_s003_post_commit.mat` | `c242202960ae1da66d234d8646b12f69e6bab3bd4a119daa1811391e2efc5683` |
| c60s4 | `c0060_s003_post_commit.mat` | `56290564113df2653850ac45d574ade2a857a551eb8e9c0b5171c0e1df18fe96` |

These hashes identify inputs, not numerical admission. The c82s5 original
producer location is recorded in the earlier read-only preflight JSON at
`local_archive/pidl_cyclic_audit_20261021/e036_20261022_readonly_preflight.json`:
`C:\Users\xw436\OneDrive - University of Cambridge\griphfith\S04_E011_raw_outputs_ad749c8_20261005_backup_20261015\S04_E011_FEM_Q4_C120\request28_post_commit\c0082_s005_post_commit.mat`.
An origin JSON must bind that path, actual bytes, physical key and preflight
record; a transfer receipt alone is insufficient.

## Stage A reuse and source binding

`e036_stage_b_driver(config_file, config_sha256)` requires the actual Stage A
`e036-stage-a-evidence-v1` manifest and its SHA. It checks all ten original
supervisor, watchdog, authority, config/argv and output chains: prepare,
disabled transition, four frozen native exports and four comparisons. The
comparisons must pass at absolute `1e-10` plus relative `1e-8`; input and
output hashes must be connected. It does not accept a standalone pass flag.

`stage_a_root` is an explicit read-only source root, distinct from the new B
`run_root`. Original Stage A JSON and build receipts are not rewritten.
Runtime names and hashes must match; absolute paths may change only when
byte-identical native/build copies are relocated into B. All ten Fortran
sources and staged copies are checked via their original relative paths.
Fresh AMOR and AT1 MEX hashes remain bound to the original successful build;
installed kernel fallback is rejected. CHOLMOD keeps its reviewed external
path/hash. Every actual MATLAB helper and runtime MATLAB source is in the
new B manifest. This does not require unrelated Python controller/scorer
files to have the old whole-tree lock hash.

After Stage A evidence and actual runtime binding pass, before any B native
context/solve, the driver writes `stage_a_reuse_audit.json` with schema
`e036-stage-a-reuse-audit-v1`. It includes the preserved evidence object,
all actual function resolutions, adapter qualified/logical aliases and
hashes, original build receipt hash, new audit-source/config/manifest hashes,
`tasks_verified=10` and `stage_a_reexecuted=false`. This is a new read-only
validation record, not a modified Stage A artifact. The separate Python
`stage_a_reuse.py` wrapper binds the matching effective physics and Python
operator subset; a later B failure does not erase the completed A audit.

## Prepare one explicit job

Copy the verified Stage A native snapshot, fresh build, overlay and common
inputs into an independent B payload, keeping their paths relative to the
old root. Copy this worktree's `code/tools/s04_e036_fem` into the payload's
code root. Preserve the original build receipts unchanged. Include the
requested predecessor and its origin record, plus empty `logs` and `output`
directories. Do not copy or start a Stage A entry.

Create one `e036-stage-b-authority-v1` JSON per job. Required fields are:
`stage="B"`, unique `authority_id`, producer `run_root`, `producer_hostname`,
one `allowed_labels` entry, whole-second UTC `authorized_at_utc`,
`human_authorization_ref`, `implementation_review_ref`,
`max_compute_threads` (1–4), `global_deadline_utc=null`, finite positive
`per_job_wall_seconds`, `step_wall_seconds <= per_job_wall_seconds`,
`arm_wall_seconds=null`, exact `request` and actual
`stage_a_evidence_sha256`. There is no implicit 8 h, A 3 h or B 7 h ceiling.
A proposed anti-hang schedule is 4 h per five-step window, 1 h per step;
2 h per isolated endpoint/tightening job, 1 h per step. The root executor
records the chosen values before launch; timeout is a failure, not a retry.

The predecessor JSON has `kind`, producer-local `path`, `sha256`, `state_key`.
`stored_u0` binds the recorded common file. `request28_post_commit` also
needs `origin_file/origin_sha256` for schema `e036-predecessor-origin-v1`
(`source_sha256`, `producer_source_path`, `state_key`, `provenance_ref`).
`verified_window_step` binds its proposal and completion files/hashes;
tightening also binds `main_window_result_file/main_window_result_sha256`.

Once actual Stage A results and staged copies exist:

```sh
python tools/s04_e036_fem/prepare_stage_b_config.py \
  --stage-a-config ACTUAL_FROZEN_CONFIG.json \
  --stage-a-evidence ACTUAL_STAGE_A_EVIDENCE.json \
  --authority JOB_AUTHORITY.json --predecessor-spec JOB_PREDECESSOR.json \
  --payload LOCAL_MIRROR_OF_B_ROOT --label UNIQUE_JOB_LABEL
```

This writes the byte-bound manifest, config and MATLAB entry inside the local
payload. It refuses missing/mismatched bytes and reused attempt filenames.
It does not transfer or execute files. The separate supervisor command is:

```powershell
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File STAGE_B_LAUNCHER.ps1 `
  -Root B_ROOT -Label UNIQUE_JOB_LABEL -Entry B_ENTRY.m `
  -AuthorityFile JOB_AUTHORITY.json -AuthoritySha256 ACTUAL_SHA `
  -WatchdogFile STAGE_B_WATCHDOG.ps1 -WatchdogSha256 ACTUAL_SHA
```

The outer caller must capture this launcher process's stdout, stderr and
exit code too. Process-local `Bypass` changes no global policy. The watchdog
uses a fresh kill-on-close Job Object and owned process handles; it never
selects another user's process for termination. It refuses an already
running MATLAB process and records the actual thread/affinity settings.
Only one B job runs at a time. All preparation, native admission, solve,
persistence and watchdog times remain attributable.

## Export F1 and predecessor admission

After a window completes and its immutable files are retrieved:

```sh
python tools/s04_e036_fem/export_window.py \
  --run-result ACTUAL_stage_b_result.json --run-result-sha256 ACTUAL_SHA \
  --window RETRIEVED_WINDOW_DIRECTORY --predecessor EXACT_SOURCE.mat \
  --predecessor-npz EXISTING_FLOAT64_INPUT.npz --output NEW_EXPORT_DIRECTORY
```

`--predecessor-npz` is required for main windows and omitted for tightening.
The converter checks the saved native `Ru/Rd` vectors and their free-DOF
norms with the same box rule, exact proposal/checkpoint arrays, physical
keys, old source arrays, Gauss-point driver and one old-to-new fatigue
mapping. It verifies source hashes again after reading. It does not evaluate
a native kernel. The scorer separately reassembles from exported fields.

Each target has float64 `u,v,d,history,active_driver,f_solve,f_commit,
old_damage,old_history,old_active_driver`, physical and predecessor keys,
mesh/source/predecessor hashes, plus `s04_e036_target_admission_v1` with
concrete MAT evidence and the actual `solver_policy`. Existing four NPZ
predecessors receive `s04_e036_predecessor_admission_v1` only after exact
comparison to native admitted/read-back arrays. `targets.json` supplies the
scorer references. It also contains `as_predecessors[physical_slot]`, with a
separate standard predecessor NPZ/admission for every verified main F1 step.
Those files preserve the exact native checkpoint arrays and reuse its original
fresh final residual/readback evidence, with zero new native calls or commits.
D4 c1s2/c1s4/c83s2/c83s4 consume main c1s1/c1s3/c83s1/c83s3 respectively.
The original `targets` mapping remains exactly snapshot/admission pairs.
No accepted target or input admission is fabricated when
a source or native check is missing.

Here FEM `f_solve` is the coefficient from the final fresh residual assembly;
PIDL `f_solve` denotes the coefficient frozen in its last optimizer block.
FEM's last inner-return coefficient is separately retained in the raw audit
as `f_last_inner_return`. Do not interpret those as the same operational event.

## Predeclared node-solver oracle

The optional final `initial_fields` argument of `e036_run_window` is separate
from the immutable predecessor `lower/history`. Role `nodal_oracle` admits only
c1s2/c1s4/c83s2/c83s4, once per state, at the original `4e-4/1e-6` policy.
The predecessor is the exact preceding F1 checkpoint from a completed main
window. The candidate comes only from the predeclared D4 L+ `first_2000`
complete endpoint; missing or nonfinite L+ fields make this oracle unavailable.
No alternative initial guess is selected.

`prepare_oracle_candidate.py` binds both the original `fields.npz` and final
`completion.json`. It checks complete/readback flags, Lplus/legacy/1e-5,
2000 completed RPROP updates, zero history commits, physical state and exact
F1 predecessor SHA. It writes a MATLAB initial-fields packet containing only
u/d and provenance, never old damage/A/r. Float32 fields are embedded exactly
in float64; this preparation performs no clipping or solver operation.

```sh
python tools/s04_e036_fem/prepare_oracle_candidate.py \
  --fields ACTUAL_LPLUS_FIELDS.npz --completion ACTUAL_LPLUS_COMPLETION.json \
  --cycle 1 --substep 2 --predecessor-sha256 EXACT_F1_OLD_SHA \
  --producer-directory B_ROOT/inputs/oracle_c1s2 --output NEW_LOCAL_DIRECTORY
```

Use its `initial_fields_spec.json` with the config generator's
`--initial-fields-spec` argument. The oracle authority additionally binds
`initial_fields_sha256`, `initial_source_snapshot_sha256` and
`initial_source_completion_sha256`. No science is launched by either generator.

In MATLAB, `e036_initial_candidate` explicitly sets common displacement BC,
projects d to `[immutable old d,1]`, and sets the hard-crack nodes to one.
It saves all raw/projected u/d, changed counts, maximum and L2 changes in
`initial_candidate.mat`. The completed window row binds this file and the
declared input MAT/L+ field/completion hashes; export checks them against the
persisted input authority as well. It then starts the same native Newton/staggered solver
from those projected fields. The old F1 history remains untouched.
`e036_initial_candidate_selftest` has five tiny pure-array checks prepared
for MATLAB; it has not been executed locally.

The oracle export records its source completion/field hashes and independently
checks the recorded projection. It uses separate
`s04_e036_nodal_oracle_admission_v1` and `s04_e036_fem_oracle_targets_v1`
schemas so it cannot silently enter the ordinary F1 scorer. An oracle solve
is a node-solver result, never a NN score. Every accepted endpoint retains
the fresh same-state residual and exact persistence checks.
