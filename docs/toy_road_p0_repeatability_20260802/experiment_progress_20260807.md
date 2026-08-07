# Toy-Road Hard-5 P0 Experiment Progress

Recorded at: `2026-08-07T14:08:05+01:00` (Europe/London)

Status: `P0_PARENT_TERMINAL_VALIDATION_PASS`

## Goal

Establish the formal FEM parent baseline required before PIDL comparison and
the later toy-to-road trajectory family. The baseline is a synthetic FEM
transfer experiment, not real-road validation and not a field-calibrated RUL
claim.

The approved P0 target is:

- role: `P0_parent`;
- mesh: Option 1 native SENS mesh;
- recovery: hard zero-load recovery;
- residual stiffness: `eta=0`;
- loading: explicit five-substep cyclic cadence;
- `Umax=0.12`, `R=0`;
- no cycle jump, no resume, no line search;
- censor cap: c150;
- same-process physical c5/s4 fixed-point and KKT qualification;
- confirmed penetration only after the first hit remains present for three
  subsequent cycles.

After P0, the intended family order remains:

```text
P0 -> terminal validation
P0R -> terminal validation -> repeatability gate
T1 -> terminal validation
T2 -> terminal validation
T3 -> terminal validation
```

P0R, T1, T2 and T3 have not been launched by this task.

## Method

1. Use the rebuilt and qualified MATLAB R2025b runtime binaries, including
   rebuilt `initial`, `AMOR` and `AT1_HISTORY_FATIGUE` MEX files.
2. Build a fresh hard-recovered `state0`, clip damage to its physical range,
   and rebuild the FEM system from the recovered state.
3. Run the native five-substep Hard-recovery trajectory sequentially on the
   Option 1 mesh, preserving one native Q4/GP shard for every completed cycle.
4. At physical c5 peak substep 4, continue stagger iterations until both the
   native residual condition and
   `max(abs(d_k-d_(k-1))) <= 1e-3` hold.
5. Evaluate penetration at peak substep 4 using nodes with `x>=0.48` and
   `d>=0.95`; require a connected component of at least three nodes and three
   consecutive post-hit cycles before confirmation.
6. Close the package with an exact manifest, SHA-256 inventory, c5 receipt,
   event metadata and an independent terminal-package validation.

## Current Progress

The P0 solve completed successfully.

```text
first_hit_cycle: 70
confirmed_cycle: 73
terminal_cycle: 73
terminal_reason: confirmed_penetration
cycle shards: 73/73
```

The c5 same-process numerical gate passed after 45 stagger iterations:

```text
displacement residual:           4.6269644576006963e-6  <= 4e-4
projected phase KKT:             2.5981528424257050e-6  <= 4e-4
consecutive stagger damage delta:9.3807822065328228e-4  <= 1e-3
primal feasibility:              0                       <= 1e-12
```

Independent terminal validation returned:

```text
is_valid: true
terminal_cycle: 73
cycle_count: 73
identity_max_abs_error: 0
damage_history_min_delta: 0
alpha_history_min_delta: 0
```

All 84 entries in the package `SHA256SUMS.txt` were rehashed successfully.
Final MATLAB/FEM process count was zero.

## Result Locations

- Production run root:
  `C:\q4diag\toy-road-p0-production-d17efe6-run1`
- Closed output package:
  `C:\q4diag\toy-road-p0-production-d17efe6-run1\output`
- Terminal manifest SHA-256:
  `91b90c0b682a05908e20b31546ae29732c1fffd9a67418d9b386b6aa5d806893`
- c5 receipt SHA-256:
  `c17e883187d9af4a9ebe5b35630e80a266be6c2a8d1bcc790299b79f65c1ff1a`
- c73 shard SHA-256:
  `415264bfdc36c991853ddb04a734d6931068f902dd712edae1975a2b8338f30a`
- Independent validation log:
  `C:\q4diag\toy-road-p0-production-d17efe6-run1\P0_parent.independent-terminal-validation.log`

## Source And Repair History

- Numerical production source: `d17efe6118ded31d7085d08cd85fdb0d31c09659`
- Runtime receipt validator repair:
  `e4203e6935ff62a1bda8834db56e9a9c4af12d9d`
- Remote branch: `codex/toy-road-evidence-integration`
- Python protocol tests after repair: `130 passed`

The FEM solve returned normally at c73. The one-shot wrapper then rejected the
valid two-stage runtime receipt because the Python validator still used the
old eight-field schema. The repair accepts the approved production chain and
verifies its entrypoints, lock identities, upstream receipt path and SHA-256.
No FEM cycle was rerun. Event metadata was reconstructed by replaying the
locked event rule over c1-c73, and the existing finalizer independently
validated the resulting immutable package.

The older `decision.md` in this directory still describes the pre-execution
authorization state and is therefore stale with respect to this completed P0
result. Do not use that old status line to infer that P0 is unexecuted.

## Current Boundary

- P0: complete and terminal-validation PASS.
- P0R: not started; requires explicit authorization before execution.
- T1/T2/T3: not started and remain downstream of the P0/P0R repeatability gate.
- Do not start any MATLAB/FEM experiment while another experiment process is
  active.
- Do not alter or regenerate the P0 cycle shards.
- Do not claim historical active-field backward equivalence or real-road
  validation from this result.

## New-Agent Handover Prompt

```text
Take over the Toy-Road FEM family from the completed P0_parent baseline.

Repository/worktree:
C:\q4diag\phase-field-fracture-fatigue-pidl-toy-road-impl

Remote branch:
codex/toy-road-evidence-integration

Required validator baseline commit/ancestor:
e4203e6935ff62a1bda8834db56e9a9c4af12d9d

Read first:
docs/toy_road_p0_repeatability_20260802/experiment_progress_20260807.md

Validated P0 package:
C:\q4diag\toy-road-p0-production-d17efe6-run1\output

P0 result:
- Option 1 mesh, Hard-recovery, eta=0, five-step, Umax=0.12
- c5 fixed-point/KKT gate PASS at stagger 45
- first penetration hit c70
- confirmed penetration and terminal cycle c73
- 73/73 native cycle shards
- terminal manifest SHA-256
  91b90c0b682a05908e20b31546ae29732c1fffd9a67418d9b386b6aa5d806893

First verify, without modifying the package:
1. Git HEAD and clean worktree.
2. No MATLAB/FEM process is active.
3. VALIDATION_SUMMARY.json reports PASS for P0_parent c73.
4. The 84 SHA256SUMS entries match.
5. The independent validation log records is_valid=true.

Authorization boundary:
- Do not rerun or modify P0.
- Do not start P0R, T1, T2 or T3 without explicit user authorization.
- P0R is the next intended experiment and must use the same physics, mesh,
  loading, solver and qualified runtime in a fresh one-shot process/root.
- P0R must independently pass its own c5 and terminal gates before performing
  the P0/P0R repeatability comparison.
- Run only one computational experiment at a time.

Report concise verification status and identify the exact next authorization
needed. Do not infer production authorization from this handover document.
```
