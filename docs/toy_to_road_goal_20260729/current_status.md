# Toy-to-road goal status

Updated: 2026-07-31 (Europe/London)

Goal execution status: `ACTIVE_PARTIAL_EVIDENCE`. The user authorized the
Tunnelblick VPN, Taobo access was restored, and the sealed forecast matrix was
completed. The goal is not road-ready.

## Current verdict

The evidence contract is valid. Within-Hard5 factorial LOTO has now been run to
completion, but the temporal candidates do not beat the Markov graph control
under the locked promotion rule and the transition/reset task gates fail.

## Track status

| Track | Current status | What is still required |
|---|---|---|
| Corrected scaling / Pi transfer | Diagnostic partial | Run the sealed F1b input as a fresh Windows-MATLAB GRIPHFiTH solve and pass field/event gates. |
| Multi-trajectory FEM | Accepted within Hard5 factorial | Acquire at least three road-like trajectories differing in defect, material state, geometry or load history. |
| Markov / TCN / Transformer forecast | Completed negative result | No candidate promoted; transition warnings were all missed and reset propagation produced about 95x FEM active-support area. |
| Real measurement / inverse interface | Interface accepted; visual inventory found | Register and evaluate PaveTrack_PD under reconciled provenance, time, scale and cross-visit alignment; add mechanical and load/environment observations for state/RUL claims. |

## Machine decision

- `valid=true`
- `within_benchmark_training_ready=true`
- `training_scope=within_benchmark_factorial`
- `road_training_ready=false`
- `road_validation_ready=false`

Current blockers are recorded in `current_gate_status.json`. Forecast producer
access is no longer a blocker. `held_out_evaluation_completed=true` is kept
separate from `forecast_task_gate_passed=false`; a negative result is not an
unexecuted result.

## Remaining external boundary

- F1b is Windows-MATLAB/GRIPHFiTH specific; no fresh candidate output exists.
- The current four FEM trajectories share one Hard5 geometry, mesh, material
  family and Umax; they cannot count as independent roads.
- PaveTrack_PD provides 8,928 real image-mask pairs across 165 locations. A
  provenance-checked visual pilot sealed 24 observations from three long crack
  sequences, but the dataset has no physical pixel scale, timezone declaration,
  cross-visit registration or paired FWD/WIM/environment measurements. It has
  not passed the mechanical measurement handoff.

The integrated decision is recorded in `decision.md` as
`blocked_missing_evidence`.
