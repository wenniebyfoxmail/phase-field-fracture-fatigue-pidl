---
experiment_id: S09-E018
status: DESIGN_AND_LOCAL_IMPLEMENTATION_IN_PROGRESS
mode: scientific_validation_exploration
continuation_of: S09-E017
---

# S09-E018: amplitude-priority factorised follow-up

## Decision

E017 establishes that the factorised shape parameters move but that the decoded
damage-increment amplitude remains orders of magnitude below the FEM events.
The next decision is whether this is caused primarily by capacity of the
factorised readout, or by symmetric PCGrad cancelling the amplitude objective.

This is a continuation, not a new operator task. The mapping remains the
independent exposed-cycle transition

`(d_pre, history_pre, load path, mesh/material/BC) -> (d_peak, history_peak, u_peak)`.

## Direct observations from E017

- `F_AMP_SHAPE` had five scaled pairwise conflicts per update at updates 1, 16
  and 64; its amplitude loss changed only from 4.004 to 3.994 over 64 updates.
- At cycle 70, reference peak increment was 0.999 and total nodal increment
  mass 85.1. `F_AMP_SHAPE` produced 3.94e-5 and 0.334 respectively.
- `D_DIRECT` retained roughly 20 units of mass at every cycle, including
  near-stagnant cycles: a diffuse-background mode rather than localisation.
- No hard constraint was violated. Therefore the binding problem is objective
  geometry and amplitude calibration, not feasibility of the decoder.

## Mechanistic intervention

Compare two independently initialised factorised amplitude-plus-shape arms:

1. `F_AMP_SHAPE_PCG`: the E017 symmetric weighted PCGrad reference.
2. `F_AMP_SHAPE_A_PRIORITY`: same objective values, frozen scales, model,
   initial checkpoint, cycles and AdamW schedule; merge gives scaled amplitude
   gradient `A` protected priority. Secondary `S/R/P` gradients are combined
   with the existing conflict handling, then their aggregate is projected into
   the non-conflicting half-space of `A` before merging. Thus its first-order
   direction cannot oppose amplitude improvement.

This isolates the live alternative: if amplitude cancellation, rather than
readout incapacity, caused the collapse, the priority arm should reduce the
amplitude error and increase event mass at cycles 46/48/58/60/69/70 without
creating a broad background or hard-constraint violation. If it does not, the
small affine amplitude head or frozen representation is the limiting mechanism;
the next route becomes a representation/head redesign rather than loss tuning.

## Evidence and limits

Use the same 16 exposed cycles, beta=.25 native-Q4 AMOR equilibrium term,
64 updates/arm, fixed evaluation updates and one clean GPU admission. No new
FEM, holdout, rollout, coefficient scan, retry, resume or automatic selection.

At update 64 record the existing A/S/R/P vectors plus: per-cycle peak and
weighted mass of `Δd`, concentration/localisation, protected-amplitude descent
diagnostics, and `d_pre`, FEM `d_post`, predicted `d_post` fields. The field
figure has five columns per cycle: `d_pre`, FEM `Δd`, predicted `Δd`, FEM
`d_post`, predicted `d_post`. It must label cycles as independent transitions,
not a rollout.

This exploration is positive only if the protected arm achieves a material
amplitude/mass improvement on high-event cycles without a diffuse-background
increase and without constraint violations. It does not establish holdout
generalisation, full phase-field closure or a production PINO claim.
