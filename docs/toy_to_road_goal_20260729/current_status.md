# Toy-to-road goal status

Updated: 2026-07-29 (Europe/London)

## Current verdict

The evidence package is valid and the four workstreams are integrated. The
Hard5 factorial is ready for **within-benchmark** leave-one-trajectory-out
training. It is not ready for a road-transfer claim.

## Track status

| Track | Current status | What is still required |
|---|---|---|
| Corrected scaling / Pi transfer | Diagnostic partial | Run the sealed F1b input as a fresh Windows-FEM solve and pass the field/event gates. |
| Multi-trajectory FEM | Accepted within Hard5 factorial | Acquire at least three road-like trajectories differing in defect, material state, or load history. |
| Markov / TCN / Transformer forecast | Signed 36-job matrix ready | Run the sealed matrix on an authenticated Taobo or CSD3 producer and evaluate held-out trajectories. |
| Real measurement / inverse interface | Interface accepted only | Ingest a registered real-road dataset through the versioned measurement adapters and evaluate identifiability. |

## Machine decision

- `valid=true`
- `within_benchmark_training_ready=true`
- `training_scope=within_benchmark_factorial`
- `road_training_ready=false`
- `road_validation_ready=false`

The active blockers are recorded in `current_gate_status.json`. Producer access
is an execution blocker, not scientific evidence and not a failed numerical
result.
