---
storyline_id: S09
experiment_id: S09-E005
protocol_revision: v1-no-update-gradient-audit
status: code_preparation
primary_storyline: S09
related_experiments: [S09-E004]
---

# E004 data/physics gradient interaction audit

## Bounded question

At the exact S09-E004 common step-300 checkpoint, is the observed accuracy–
equilibrium trade-off associated with gradient scale imbalance, directional
conflict, or a nonzero residual floor in the exported FEM targets?

This Experiment performs backward passes but exactly zero optimizer updates.
It diagnoses the frozen E004 configuration and does not test a rescue method.

## Frozen identities

- Operator: `G_theta: (d_peak(.), Umax) -> u_peak(.)` on the fixed native Q4
  mesh, unchanged from E004.
- Physics objective: assembled free-DOF fixed-damage AMOR equilibrium residual,
  normalized by the state-specific affine-field residual.
- Training packet SHA-256:
  `b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed`.
- Common step-300 checkpoint SHA-256:
  `1fc1695a87c41cd4a373fa31535dc99be7d91ad01af9a1e11a2986d83af8029e`.
- States: all 16 frozen U0.115 training states in their locked cycle identity.
- Producer: Taobo GPUServer8 after independent Code Ready review.

## Measurements

For each state, compute the data and physics gradients separately and report:

1. global and encoder/local/coarse/decoder gradient norms, norm ratio and
   cosine similarity;
2. predicted first-order changes in both losses under the E004 initial weight,
   its first-assessment weight, equal gradient normalization and a
   data-anchored projected direction;
3. predicted-field and FEM-export free-force RMS relative to the same affine
   normalizer;
4. model-state and checkpoint hashes before and after the audit.

The linearized changes are explanatory derivatives per unit learning rate.
They are not optimizer updates or empirical training outcomes.

## Evidence criterion and interpretation

Evidence completeness passes only if all 16 states are finite, every declared
block is measured, both no-update identities match, and the exact frozen asset
hashes pass.  Scale imbalance is indicated by the measured norm ratios;
directional conflict is present statewise when cosine is negative.  The FEM
target residual is reported as a continuous diagnostic, without inventing a
post hoc threshold.

E005 can justify the design of a fresh, reviewed S09-E006 Pareto-rescue
Experiment.  It cannot change the E004 failure, demonstrate that a proposed
multi-objective optimizer works, establish exact equilibrium, or support crack
evolution/generalization claims.

## Required output

- `gradient_audit.json` with all statewise and blockwise measurements;
- compact `gradient_audit.csv`;
- producer receipt proving zero updates and hash identity;
- analysis table/figure, decision note and independent Evidence Ready review;
- one dated S09 claim-impact entry and Obsidian research-log update.

