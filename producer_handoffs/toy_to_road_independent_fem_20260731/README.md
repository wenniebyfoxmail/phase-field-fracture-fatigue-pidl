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

## Qualification Status

This family is not currently authorized for execution. Production Q1 passed
from the reviewed pre-execution source, but Q2 parent validation published the
two blockers below and stopped before any solve. No passing Q2 evidence has
been sealed. The current state is `EvidenceLockUnsealed`, and
`QUALIFICATION_EVIDENCE_LOCK.json` is intentionally absent.

The locked parent is also missing authoritative native/GP damage-degradation
and active-driver evidence. Parent validation must report both
`blocked_missing_parent_damage_degradation_field` and
`blocked_missing_parent_active_field`, then stop before recovery, `System`,
Newton, or cycle 1. Neither `f_alpha_elem` nor an element-mean approximation
may be substituted for the active driver.

T1/T2/T3 remain fail-closed until canonical Q1 and Q2 receipts are bound by a
sealed qualification evidence lock. Once authorized, all three cases must use
the same qualification receipt, runtime-lock digest, and rebuilt
`initial.mexw64` SHA-256, in strict serial order with terminal validation
between cases.

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
  that supports hard links;
- `QualificationRoot`: a completed immutable qualification root containing a
  canonical family receipt bound to the sealed evidence lock; and
- one `CaseId`: `T1_initial_defect`, `T2_material_state`, or
  `T3_loading_history`.

`SHA256SUMS.txt` uses repository-relative paths and hashes exact bytes. The
launcher verifies it before MATLAB, including LF-sensitive source bytes. It
also verifies every case/parent lock, required GRIPHFiTH source, the approved
AMOR and AT1-history-fatigue MEX binaries, the known F1b `initial.mexw64`
binary, CHOLMOD `cholmod2.mexw64`, and every consumed parent artifact.

### Parent mesh identities

`PARENT_LOCK.mesh.content_sha256` is the legacy analysis-graph digest. It is
computed by hashing, in order, the ASCII key, NumPy dtype text, int64 shape,
and contiguous array bytes for `centroids`, `areas`, `connectivity`, and
`edge_index`. It is not the Task 4 mesh hash. `mesh.source_sha256` is the raw
analysis graph NPZ file digest.

`mesh.source_package_evidence_sha256` is computed from the ASCII VTK geometry
and topology only: normalize whitespace on each line from `DATASET` through
the line before `CELL_DATA` or `POINT_DATA`, append LF after each normalized
line, and hash those bytes. Its raw VTK source digest is separately locked.

The canonical Task 4 parent identity is
`4d01985bfe2e80afe7140ab1ead905ddce5843f8495a3558d2d4da3b237df5af`.
It is derived from the hash-gated `peak_load_c1.vtk` by hashing MATLAB
column-major `double(parent_node_coords(:))` bytes followed by column-major
`int64(connectivity(:))` bytes. The normalized VTK digest, raw VTK digest,
86756-node count, and 86408-element count all agree with the pre-existing
parent evidence; this additional identity does not replace physical authority.

### T1 mesh-transfer quality gate

T1 preserves the approved piecewise-affine x factors `1.25` on `x<=0` and
`0.75` on `x>0`. Its quality gate compares each mapped notch-tip incident-edge
length with the corresponding parent incident-edge length, using deterministic
connectivity-derived edge correspondence. Every mapped/parent ratio must be in
`[0.75, 1.25]` with tolerance `1e-12`; a zero-length parent edge fails before
division. Parent and mapped absolute `h/ell` minima and maxima remain exported
as audit evidence only and never drive this gate. The legacy
`local_h_over_ell_ratio_min/max` names mean mapped absolute incident-edge
`h/ell` and are retained only for compatibility.

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

## Commit receipt protocol

The source manifest deliberately excludes itself and contains no Git commit,
so sealing has no self-referential hash. After every covered edit, regenerate
`SHA256SUMS.txt` from exact LF-sensitive bytes, verify it in a fresh
byte-preserving copy, and commit the covered files plus manifest. A subsequent
evidence-report-only commit does not change the covered source set. Select the
final clean `HEAD` after those commits and pass that full hash as
`-ExpectedSourceCommit`.

The launcher verifies that exact commit and every exact normalized
relative-path-to-SHA256 mapping before execution. After strict validation of
the sole completion marker, it publishes `LAUNCH_RECEIPT.json` with
`FileMode.CreateNew`; the receipt records the verified commit, roots, locks,
and exact source, GRIPHFiTH, runtime, and parent mappings. The finalizer accepts
only that canonical no-clobber receipt inside the fresh output root and binds
the input snapshot and final provenance to it.

## Launch

Do not run the command below while the status is `EvidenceLockUnsealed` or
either Q2 parent-field blocker remains. Static preflight instructions and the
runtime/API evidence contract are in
`producer_handoffs/rebuilt_initial_mex_qualification_20260801/README.md`.

First run the non-solving preflight from a clean sealed checkout:

```powershell
& .\producer_handoffs\toy_to_road_independent_fem_20260731\launch_toy_road_case.ps1 `
  -SharedRepo C:\q4diag\phase-field-fracture-fatigue-pidl-toy-road-producer `
  -GripfithRoot C:\q4diag\griphfith-f1b-355d4c83 `
  -ParentRoot 'C:\path\to\Hard5_eta0_5step_Umax_011_012_013_20260729' `
  -OutputParent C:\q4diag\toy_to_road_independent_fem_20260731 `
  -QualificationRoot C:\q4diag\rebuilt_initial_mex_qualification_evidence `
  -CaseId T1_initial_defect `
  -ExpectedSourceCommit <full-40-character-sealed-commit> `
  -PreflightOnly
```

Remove only `-PreflightOnly` to run that one selected case after reviewing the
preflight. If Windows policy requires an execution-policy bypass, apply it only
to the outer PowerShell caller; the sealed launcher does not embed a bypass.

On successful MATLAB return, the launcher strictly checks the JSON boolean
`complete`, exact case, status, terminal reason/cycle, and canonical terminal
state path in `RUN_RESULT.json`, publishes `LAUNCH_RECEIPT.json` without
clobbering, then starts a validation-only MATLAB process. The finalizer
deeply validates state0, mesh, every state shard, cycle index, event lifecycle,
case/source identities, exact receipt path mappings, and provenance before
publishing deterministic
no-clobber `PRODUCER_PROVENANCE.json`, `VALIDATION_SUMMARY.json`, and a sorted
output `SHA256SUMS.txt`. Existing final outputs, missing files, unexpected
files, symlinks, case-colliding paths, and manifest tampering fail closed.
