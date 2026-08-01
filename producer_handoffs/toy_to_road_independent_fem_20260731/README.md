# Toy-to-Road Independent FEM Producer

This sealed handoff produces three independent single-axis synthetic FEM trajectories:
T1 varies the initial defect, T2 varies fracture material state,
and T3 varies physical loading history. The cases require strict serial
execution. Run exactly one case per launcher invocation and wait for it to
finish and validate before starting another.

The claim scope is synthetic whole-trajectory LOTO evidence only. Latent FEM
fields are not direct road sensors. This package authorizes no PIDL training
and no road validation. F1b remains a separate blocked diagnostic and is not a
parent or substitute for these cases.

## Immutable Inputs

The launcher requires:

- `SharedRepo`: a clean checkout at the exact full commit supplied with
  `-ExpectedSourceCommit`;
- `GripfithRoot`: clean GRIPHFiTH commit
  `355d4c83fefc2db88c32031a2dd2623b3de85c89` with the locked source and MEX
  bytes;
- `ParentRoot`: the root of
  `Hard5_eta0_5step_Umax_011_012_013_20260729`, containing `MANIFEST.csv` and
  the `u012` directory;
- `OutputParent`: an existing writable family output directory on a volume
  that supports hard links; and
- one `CaseId`: `T1_initial_defect`, `T2_material_state`, or
  `T3_loading_history`.

`SHA256SUMS.txt` uses repository-relative paths and hashes exact bytes. The
launcher verifies it before MATLAB, including LF-sensitive source bytes. It
also verifies every case/parent lock, required GRIPHFiTH source, the approved
AMOR and AT1-history-fatigue MEX binaries, the known F1b `initial.mexw64`
binary, CHOLMOD `cholmod2.mexw64`, and every consumed parent artifact.

## Safety Contract

There is no resume path. Checkpoint or resume environment input is rejected.
The selected Task 5 output root `<OutputParent>/<CaseId>` must not pre-exist,
even if empty. The launcher never deletes an output or terminates a process.
Any running MATLAB/FEM experiment blocks launch. A same-volume hard-link
preflight must pass and removes both probe names before continuing.

Each case starts from fresh hard recovery, uses five retained substeps, and
stops only at confirmed penetration or the c150 right-censor cap.
`RUN_RESULT.json` is the sole completion marker. Failed or incomplete roots
cannot be finalized, and no separate success marker is created.

`-PreflightOnly` executes every launcher gate, sets and reports the exact four
Task 5 environment variables, and returns before MATLAB invocation. The
internal fixture seam is accepted only together with `-PreflightOnly`, so test
configuration cannot launch MATLAB.

## Launch

First run the non-solving preflight from a clean sealed checkout:

```powershell
& .\producer_handoffs\toy_to_road_independent_fem_20260731\launch_toy_road_case.ps1 `
  -SharedRepo C:\q4diag\phase-field-fracture-fatigue-pidl-toy-road-producer `
  -GripfithRoot C:\q4diag\griphfith-f1b-355d4c83 `
  -ParentRoot 'C:\path\to\Hard5_eta0_5step_Umax_011_012_013_20260729' `
  -OutputParent C:\q4diag\toy_to_road_independent_fem_20260731 `
  -CaseId T1_initial_defect `
  -ExpectedSourceCommit <full-40-character-sealed-commit> `
  -PreflightOnly
```

Remove only `-PreflightOnly` to run that one selected case after reviewing the
preflight. If Windows policy requires an execution-policy bypass, apply it only
to the outer PowerShell caller; the sealed launcher does not embed a bypass.

On successful MATLAB return, the launcher checks the complete
`RUN_RESULT.json`, then starts a validation-only MATLAB process. The finalizer
deeply validates state0, mesh, every state shard, cycle index, event lifecycle,
case/source identities, and provenance before publishing deterministic
no-clobber `PRODUCER_PROVENANCE.json`, `VALIDATION_SUMMARY.json`, and a sorted
output `SHA256SUMS.txt`. Existing final outputs, missing files, unexpected
files, symlinks, case-colliding paths, and manifest tampering fail closed.
