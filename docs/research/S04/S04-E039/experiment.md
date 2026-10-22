# S04-E039 — phase-aware RPROP state inheritance

## Current workflow — 2026-10-22

Use the installed research-decision-core fixed-benchmark rule. The two existing
three-cycle arms below are the one task comparison; run each only as already
authorised, reuse completed outputs, then deliver the paired result. Do not add
historical reruns, smoke ladders, full regressions, per-commit/metadata review or
default post-result independent review. Documentation changes need only direct
consistency checks. Existing source snapshots, results, scientific criteria,
budget and execution permissions are unchanged; this amendment starts no run.

## Purpose

Test whether carrying the PyTorch RPROP per-parameter state between strictly
ascending substeps reduces numerical optimization cost in the existing explicit
cycle PIDL runner. This is a bounded optimizer-mechanics experiment; it does
not test physical-history sufficiency, fracture prediction, or road-level
generalisation.

## Frozen comparison

- Code base: clean commit `9c9c30fd` before this experiment.
- Network: 8 hidden layers, 400 neurons, seed 1, TrainableReLU, init coefficient 1.0.
- Material/PIDL settings: the runner's existing defaults; no Williams, Ansatz,
  symmetry, exact-BC, ψ hack, spatial αT, or adaptive sampling branches.
- Loading: `Umax=0.12`, factors `[0, 0.5, 1, 0.5, 0]`, three physical cycles
  (15 training substeps).
- RPROP cap: 1,000 updates per substep; same early-stopping tolerance in both arms.
- Fresh model directory and identical seed for each arm; no checkpoint resume.

Fixed producer command (run once per arm):

```bash
python SENS_tensile/run_explicit_cycle_umax.py 0.12 --n-cycles 3 \
  --epochs-rprop 1000 --rprop-state-mode <fresh_per_step|phase_aware>
```

## Arms

1. `fresh_per_step`: reconstruct RPROP at every training substep (historical
   behaviour).
2. `phase_aware`: reuse the same RPROP instance only when the next displacement
   is strictly larger than the previous one. Equal or decreasing displacement
   starts a new optimizer, so peak-to-unload and unload-to-reload boundaries are
   reset.

## Primary numerical readout

Compare total RPROP update count and wall time across the same 15 substeps. The
run is useful only if both arms complete the same substep sequence without a
launch or numerical failure. `rprop_state_vs_step.csv` records whether state was
reused and the post-step step-size range for the phase-aware arm.

## Interpretation boundary

Any reduction is evidence of a numerical warm-start effect under this short
trajectory. It is not evidence that RPROP state is a physical memory variable,
that the solution is more accurate, or that a full fatigue trajectory should
inherit state across unloading.
