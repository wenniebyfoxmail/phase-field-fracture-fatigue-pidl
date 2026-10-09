# S09-E004 analysis figures

## Scientific question

Does the frozen native-Q4 equilibrium term improve a matched graph operator for
the fixed-damage map `(d_peak(.), Umax) -> u_peak(.)` on three reused U0.12
development states?

## Evidence source and reading order

Source: retrieved S09-E004-R005 `metrics.json`, `history.csv` and
`final_fields.npz`, packet
`b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed`.
Read `decision.png` first, then `fields.png`.

1. `decision.png` shows the complete evaluated development trajectories, the
   final primary comparison, each state's relative displacement error and the
   non-voting residual diagnostic.
2. `fields.png` shows exported, data-only and equilibrium-informed vertical
   displacement for c76/c82/c83 on one coordinate frame and one colour scale.

## Interpretation

Data only finishes at `R=0.36286`; equilibrium informed finishes at
`R=0.61230`.  Their ratio is `1.68741`, so the frozen `<=0.95` criterion fails.
The physics arm lowers the residual from roughly 25.4 to 2.59 times affine but
does not reach equilibrium.  The montage is consistent with a smoother physics
solution and worse reproduction of the exported localized displacement jump.

Allowed conclusion: this equilibrium weight/interface is unfavorable for the
selected development displacement metric.  Blocked conclusions include a
general rejection of PINO, crack evolution, independent generalization, FEM
truth or real-road validity.  `fields.png` displays only `u_y`; the primary
metric includes both displacement components.

Local figure set:
`local_archive/experiments/S09-E004/runs/S09-E004-R005/analysis/`.
