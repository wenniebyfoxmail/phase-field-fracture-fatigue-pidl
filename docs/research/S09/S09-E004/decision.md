# S09-E004 decision

## Verdict

**Execution succeeded; the frozen scientific criterion failed.**

At the final matched update,

| Method | Development R |
|---|---:|
| Data only | 0.36286169 |
| Equilibrium informed | 0.61229706 |

The primary ratio was

`R_equilibrium / R_data = 1.68741168 > 0.95`, hence **FAIL**.

An independent float64 reconstruction from the retrieved final fields gave
`1.6874117017`.  The equilibrium-informed arm increased the selected
development displacement error by about 68.7% relative to the matched
data-only arm.  It was worse on c76, c82 and c83 separately.

## Physics diagnostic

The physics arm reduced the development free-force RMS ratio from about
25.4 times the affine comparator to about 2.59 times.  This is a substantial
residual reduction, but it neither satisfies equilibrium nor votes in the
primary decision.  The final field montage shows a smoother mid-plane
transition for the physics arm while the data-only field follows the exported
displacement jump more closely.  This is an observation, not a proved causal
mechanism.

## Evidence status

- Producer execution: succeeded in 45.78 s; peak CUDA allocation 535,286,272 B.
- Retrieval: all 11 output files match the newly generated remote SHA-256 and
  byte inventory.
- Remote archive: 11 files copied to
  `/mnt/data2/drtao/pidl_archives/S09-E004-R005_11fd75d_20261009T174900Z/output`.
- Independent Evidence Ready review: **PASS**.
- Original producer receipt defects are preserved: `run_id` is `output` and
  `retrieval` remains `pending`.  The tracked R005 receipt, command, remote
  root, PID and retrieval verification disambiguate the run and final state.

## Claim impact

The experiment establishes that the repository now has an executable
function-to-function, equilibrium-informed operator interface for
`(d_peak(.), Umax) -> u_peak(.)`.  Under this single seed, fixed grid, frozen
weight ramp and three reused development states, the equilibrium regularizer
traded lower force residual for worse displacement fit.

This does not reject PINO generally and does not test damage evolution,
autonomous rollout, unseen trajectory generalization, FEM physical truth or
real-road validity.  A next experiment must be a new, reviewed protocol; this
result does not authorize an unplanned weight retry.
