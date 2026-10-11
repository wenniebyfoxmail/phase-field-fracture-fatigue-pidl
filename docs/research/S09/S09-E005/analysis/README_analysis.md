# S09-E005 analysis figures

## Scientific question

At the exact E004 common checkpoint, is the subsequent accuracy–equilibrium
trade-off more consistent with data/physics gradient scale imbalance,
directional conflict, or a large residual already present in the FEM target?

## Evidence source and reading order

Source: retrieved S09-E005-R001 `gradient_audit.json` and `receipt.json` from
execution commit `79f238e0cd2ddd7a31d994f79c6d05410fd8151a`.

Read `gradient_audit_decision.png` from the local analysis folder left to
right:

1. Panel A compares physics/data gradient norm ratios globally and by block.
2. Panel B shows gradient cosine; values below zero identify conflict.
3. Panel C compares the checkpoint prediction and FEM-export observed
   free-force residual with the affine reference.

Local figure set:
`local_archive/experiments/S09-E005/runs/S09-E005-R001/analysis/`.

## Cross-figure interpretation

The global physics gradient is 10,165–57,338 times the data gradient and has
positive cosine on all 16 states.  Encoder, local and coarse blocks have the
same pattern.  The decoder conflicts on 6/16 states, reaching cosine -0.816,
so conflict exists locally but does not dominate the global step-300 gradient.

At E004's initial weight 0.01, the weighted physics component is still
102–573 times the data-gradient norm; at the first assessment weight it is
166–935 times.  FEM-export observed residual is only 0.000086–0.0266 times the
affine residual, while the checkpoint prediction is 34.2–61.1 times affine.
The target does not show a large residual floor under this diagnostic.

Allowed conclusion: scale dominance is the leading measured mechanism at the
common checkpoint, with localized decoder conflict.  A new gradient-balanced,
data-anchored rescue is warranted for testing.  Blocked conclusions include a
causal proof of E004's entire training trajectory, successful multi-objective
training, exact equilibrium, crack evolution, generalization or real-road
validity.
