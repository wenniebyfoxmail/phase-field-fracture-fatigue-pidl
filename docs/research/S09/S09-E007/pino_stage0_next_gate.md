# Earliest defensible route from fixed damage to PINO

S09-E007 is deliberately the last fixed-damage selection test. If it passes,
S09-E008 should change the learned object rather than add another equilibrium
weight experiment.

## Proposed one-step operator

For cycle `n` and the next-cycle loading action, the first evolution operator is

\[
\mathcal T_\theta:
\bigl(d_n(\cdot),\bar\alpha_n(\cdot),f_n(\cdot),U_{n+1}\bigr)
\longmapsto
\bigl(d_{n+1}(\cdot),\bar\alpha_{n+1}(\cdot),u^{\mathrm{peak}}_{n+1}(\cdot)\bigr).
\]

The state must be a causal pre-cycle committed tuple. Same-cycle s4 damage or
history cannot be supplied as a predictor of itself. The first target is a
one-cycle transition; autonomous rollout is a later experiment.

## Physics ladder

1. Hard displacement boundary and fixed-mesh identity.
2. Peak mechanical equilibrium conditioned on predicted next damage.
3. Damage bounds and irreversibility `d_{n+1}>=d_n` as explicit constraints or
   projected outputs.
4. Fatigue-history monotonicity `alpha_bar_{n+1}>=alpha_bar_n` and the frozen
   Carrara degradation map.
5. Only after exact old/new substep semantics are available: AT1 phase-field
   stationarity/KKT residual for the next committed damage state.

These are separate objectives and validity checks. They should use constrained
or gradient-balanced optimization; a single raw weighted sum would repeat the
scale problem measured in S09-E005.

## Data gate before training

A complete trajectory must expose aligned pre-cycle committed state, next-cycle
committed targets, next-cycle peak displacement, native mesh/order, update timing,
and qualified producer identity. Split by complete Umax trajectory. Checkpoints
from one trajectory do not create an independent axis.

The minimal first experiment uses development trajectories only and keeps one
complete Umax trajectory sealed for confirmation. If no uncontaminated complete
trajectory exists, acquire one before making a transition-generalisation claim.
