# S09-E004 reflection and solution-oriented next design

Date: 2026-10-11

## What the physics term actually was

The trained physics term was the fixed-damage mechanical equilibrium residual,
not the phase-field evolution equation.  For a predicted nodal displacement
field `u` and prescribed nodal damage `d`, the implementation:

1. evaluates Q4 strains at the same four Gauss points as the FEM export;
2. applies the AMOR tension/compression split;
3. degrades the tensile and deviatoric contribution by
   `g(d)=(1-d)^2+eta` while retaining compressive volumetric stress;
4. assembles the internal nodal force `r_u = integral(B^T sigma(u,d)) dOmega`;
5. penalizes the mean squared force on free displacement DOFs, normalized by
   the affine-boundary residual for that state.

Top and bottom displacement conditions are satisfied by construction.  AT1
phase and fatigue routines exist and were audited in E003, but were not used in
E004 training.  Therefore E004 did not impose damage evolution, irreversibility
KKT conditions or fatigue-history evolution.

## The learned function-to-function map

The map was

`G_theta: (d_peak(.), Umax) -> u_peak(.)`.

One sample is a complete 86,756-node damage field plus one peak-load scalar;
the output is the complete two-component nodal displacement field on the same
mesh.  Coordinates, connectivity, geometry and material are fixed context.
Nodes are discretization points inside one function sample, not independent
training samples.  This is a fixed-grid, damage-conditioned equilibrium
operator prototype.  It is not yet a crack-development operator and does not
demonstrate cross-grid operator consistency.

## Why one FAIL label is insufficient

The frozen E004 selection question remains valid: the chosen physics arm did
not improve final development displacement error by at least 5%.  That decision
must remain FAIL.  It should not erase the other verified outcomes.

| Evidence layer | E004 result | Meaning |
|---|---|---|
| Validity and execution | PASS | identities, split, boundary, matched arms, retrieval and reviews are valid |
| Operator interface | PASS | a whole damage field and load produce a whole nodal displacement field |
| Data learning | POSITIVE | data-only reached `R=0.36286`, substantially better than affine `R=1` |
| Physics channel | PARTIAL POSITIVE | free-force diagnostic fell from about 25.4 to 2.59 times affine, an approximately 89.8% reduction |
| Joint utility | NO-GO for this configuration | displacement `R` worsened from 0.36286 to 0.61230; primary ratio 1.68741 |
| Exact equilibrium | NOT ACHIEVED | the physics result remained about 2.59 times affine residual |
| Crack evolution/generalization | NOT TESTED | prescribed damage, one seed, fixed mesh, reused development states |

The scientific result is therefore a measured trade-off, not a total method
failure: the physics gradient was effective at its own objective but dominated
or conflicted with displacement fitting under the selected normalization,
weight ramp and optimizer trajectory.  Gradient dominance/conflict is a
hypothesis until directly measured.

## Result-definition framework for subsequent work

Use strict binary gates only for conditions that make evidence interpretable:
identity, state timing, no leakage, finite computation, hard boundaries,
matched budget, exact final-step scoring, retrieval and independent review.

Report model performance as a vector rather than one omnibus verdict:

1. displacement accuracy relative to affine and data-only;
2. free-force residual relative to affine, data-only and the FEM export;
3. per-state variation rather than aggregate alone;
4. training stability and gradient interaction;
5. generalization level: training, reused development, or untouched test;
6. evolution level: fixed damage, one-step damage, or autonomous rollout.

A predeclared primary criterion still decides whether a configuration is
selected for the next stage.  Secondary gains remain recorded as gains but do
not overturn that selection decision.  This prevents both moving the goalposts
and discarding useful mechanism evidence.

## Proposed next experiment: diagnose, then rescue the Pareto trade-off

Do not retry E004 weights post hoc.  Open a new S09-E005 protocol with two
sequential gates.

### Gate A: no-update gradient audit

At the exact common step-300 checkpoint, measure on the frozen 16 training
states:

- `||grad L_physics|| / ||grad L_data||` globally and by encoder/local/coarse/
  decoder blocks;
- cosine similarity between the two gradients;
- the native FEM-export residual relative to the same affine normalizer;
- one-step predicted change in both losses for the observed gradient mixture.

This distinguishes scale dominance, directional conflict and an inconsistent
residual floor without changing parameters.  It is the smallest direct test of
why a nominal weight as low as 0.016 already raised development `R` from about
0.44 to 0.95 at the first recorded physics assessment.

### Gate B: bounded Pareto rescue

Only after Gate A is reviewed, compare a small predeclared set of remedies from
the same common checkpoint and sample sequence.  Candidate remedies are:

- gradient-normalized physics weighting;
- projected/conflict-aware gradients when cosine similarity is negative;
- a displacement trust region or constrained optimization that reduces force
  residual without allowing large displacement degradation.

For early architecture development, use a loose, solution-oriented feasibility
target instead of demanding immediate joint superiority.  A provisional target
for review is: at least 50% residual reduction versus data-only while final
displacement `R` is no more than 10% worse than data-only on every development
state.  A stronger selection target can then require displacement improvement.
The exact thresholds and arms must be frozen and reviewed before observing new
training results.

Damage-evolution PINO should follow only after a satisfactory equilibrium
trade-off and after the old damage/history/fatigue state needed by the AT1
residual is available with exact timing semantics.
