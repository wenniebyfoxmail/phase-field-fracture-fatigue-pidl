# S09-E017 real-head-adapter implementation status

Date: 2026-10-20
Status: `IMPLEMENTATION_CANDIDATE_AWAITING_EXACT_REVIEW__NO_EXECUTION`

## Purpose

Implement the reviewed real-head-adapter design without changing the E017
mapping, three arms, beta `0.25` mechanical-equilibrium scope, 16 exposed
cycles, 64 updates per arm, no-retry rule or holdout boundary.

## Implemented

- Strict checkpoint inventory and conversion of the joint
  `Linear(width,3)` decoder into independently owned damage, `ux` and `uy`
  rows, reconstructed through one three-output `F.linear` call.
- One shared frozen hidden coordinate `h_i`; `D_DIRECT` and `F_AMP` expose
  `width+1` trainable scalars and `F_AMP_SHAPE` exposes `2*width+1`, with no
  shape bias.
- Pristine per-arm construction, cross-arm object/storage isolation, complete
  trainable/frozen/buffer inventories and frozen-state rehashing.
- Concrete decoded-field A/S/R/P losses, withheld F_AMP shape gradient,
  reviewed PCGrad order and one fresh float64 AdamW per arm.
- Separate operation-entered, optimiser-step-returned and durable-update-
  committed counters; write-once per-update evidence, independent first-failure
  receipt and non-self-referential inventory/retrieval verification.
- Fixed endpoint field arrays, A2/S6/R2/P4 evaluation rows, all-cycle
  reference/prediction/error panels with external colourbars, trajectory plot
  and `README_analysis.md` generation.
- A launch wrapper that checks execution authority before resolving scientific
  imports or examining packet/checkpoint paths. The tracked config remains
  disabled.

## Local verification

The focused suite completed with `122 passed in 2.29s`. It uses only hand-made
float64 tensors, synthetic checkpoint state and temporary output directories.
It exercises the actual adapter, autograd, PCGrad, AdamW, transactional writer,
metric evaluator and figure path. It does not instantiate the real Stage0A
scientific runtime or read the real packet, B25 checkpoint or FEM arrays.

Ruff, `py_compile`, canonical disabled-config resolution and
`git diff --check` pass. The disabled resolver reports zero scientific reads,
binding resolutions, model forwards, autograd collections, optimiser
constructions and optimiser steps.

## Pre-review self-audit correction

Before external submission, a counterexample audit found that the first
candidate counted a 16-cycle forward batch only after the batch returned and
did not persist the readout diagnostics required by the reviewed amendment.
The corrected candidate now counts every model-forward entry before the call,
including anchor and evaluation forwards; preserves pre-arm failures through
the independent writer; binds optimiser groups by parameter-object identity;
and persists readout norms/feature variance, hard-constraint audit, endpoint
profiles, per-arm wall/peak-memory/counters, exact resolved config and complete
metric/gradient JSONL streams. These are evidence-closure corrections, not
scientific results.

## Claim boundary

This is implementation evidence only. It does not show that any E017 arm
improves amplitude, localisation, reconstruction or equilibrium, and it does
not establish holdout generalisation, rollout stability, full phase-field
closure, operator capacity or real-road validity. A later bias-only amplitude
gain must be labelled global calibration unless `v_A` and the across-cycle
variance of `v_A^T h_bar` are both nonzero.

## Next gate

Create a dependency-closed archive bound to the exact candidate commit and ask
ChatGPT Pro on the Haofan account to review the actual source, tests, config,
manifest and commit identity. Do not enable the tracked config or perform a
scientific run from this candidate.
