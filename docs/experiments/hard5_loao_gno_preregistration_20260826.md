# Hard-5 leave-one-amplitude-out GNO preregistration

**Date:** 2026-08-26  
**Status:** `OWNER_AUTHORIZED__PRELAUNCH`  
**Authorization:** user said `go` for the new Hard-5-only retraining route.

## PIDL Experiment Gate

- Mechanism question: can a data-only native-mesh GNO trained on two Hard-5
  amplitudes reproduce the third amplitude's FEM archive transition and fields?
- Claim changed if success: supports an exploratory fast surrogate for the
  three processed Hard-5 GRIPHFiTH archives and enables matched FEM/PIDL/GNO
  field figures.
- Claim changed if failure: rejects this frozen Hard-5 LOAO GNO as a
  cross-amplitude surrogate; no retuning on the same three holdouts.
- Cheaper diagnostic first: passed. U0.11/U0.12/U0.13 have consecutive
  1–125/1–89/1–62 four-channel archives, 86,408 finite elements per cycle,
  identical connectivity and zero centroid difference.
- Minimal output asset: nine-job receipt table, fold/seed metrics,
  matched FEM/PIDL/GNO field NPZ and one decision note.
- Code/producer alignment: clean Mac release commit, Taobo only, two explicit
  GPUs, fresh run/archive roots and task-owned systemd services.
- Registry destination: this experiment document, the local case folder and
  one compact inventory row after completion.
- Decision: launch after code/hash tests and live CUDA/ownership preflight.

## Frozen data and split

Three complete Hard-5 eta0 five-step trajectories are used: U0.11, U0.12 and
U0.13. Each fold removes one complete amplitude before normalization, window
construction, gradient calibration and optimization. Known Umax is a protocol
input; cycle number, event distance and held-out event labels are prohibited
training inputs. Mapped PIDL assets are loaded only after training finishes.

The first-detect labels are c122/c83/c59. Confirmation c125/c86/c62 remains a
separate label. The matched PIDL comparison states are the already sealed
c121/c82/c55 states; these choices are frozen before results.

## Frozen model and matrix

The architecture and optimization are inherited unchanged from canonical D1:
context 3, recurrent rollout 3, width 96, 339,461 parameters, 3,000 AdamW
steps, transition-balanced sampling, training-fold gradient calibration and
transition weight 0.25. All weights start fresh. Three folds times seeds
1/2/3 gives nine jobs; seeds are optimization repeats.

## Frozen decision

The primary matched-field gate requires the seed-median GNO to have both lower
derived-active log-MAE and higher absolute FEM-p99 IoU than mapped PIDL in all
three folds. Retrospective event-centred transition recall must be at least 4/6
with at most 1/3 false warnings in at least two folds. The all-opportunity stop
gate retains the frozen D1 recall/FPR thresholds recorded in the JSON lock.

Failure of any primary clause makes the route negative. No threshold, loss,
mask, architecture or comparison cycle may be changed after results.

## Claim boundary

This is supervised imitation of processed/clipped GRIPHFiTH output:
`teacher_qualified=false`, `damage_fixed_point_gate=fail`, physics-loss weight
`0.0`, and `physical_validation=false`. Even a pass is not physical truth,
calibrated real-road warning, or a posterior result. Only three trajectories
exist, so the first complete matrix is exploratory.

## External planning provenance

The split and leakage rules adopt the earlier GPT Pro autonomous-transition
strategy: complete-trajectory leave-one-Umax-out, training events allowed only
for training amplitudes, and no failure-life normalization or heldout-informed
horizon. The earlier review explicitly deferred GNN work to a separately
preregistered branch; this document is that new branch.
