# S09-E009 update-500 field visualisation

## Question

What do the frozen update-500 damage fields look like, and do the aggregate
component gains correspond to the correct crack-growth location and magnitude?

## Reconstruction and provenance

These figures are a read-only reconstruction from the verified E009
update-500 checkpoints and the same frozen 16-cycle E008 development packet.
The packet-manifest SHA256 is
`1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`.
The script performs no optimiser step. For every arm and cycle it also
recomputes the weighted mean damage increment and checks it against the frozen
`per_cycle_metrics.csv`; the maximum absolute difference is
`1.0842021724855044e-19`, below the `1e-12` replay tolerance. Exact checkpoint
and output hashes are recorded in `field_reconstruction_receipt.json`.

The plotted raster uses the nearest native mesh node only to display pixels.
All numerical comparisons use the original native-node fields. The common
physical colour scales must be used for magnitude comparisons. Per-panel
normalised views are explicitly labelled and show shape only.

## Reading the figures

### Cycle 69: strongest crack-growth transition

`S09-E009-R001-cycle69-four-arm-increments.png` compares the true and predicted
increment fields on a shared physical scale, then repeats each panel after
independent normalisation to expose spatial shape.

- FEM concentrates the increment in a very small crack-tip region, with a
  local maximum of `8.63e-1` and weighted mean `2.564e-4`.
- `R` and `S` approximately reproduce the global mean (`2.392e-4` and
  `2.424e-4`) but distribute it as a broad, smooth background/right-boundary
  pattern. Their within-cycle spatial correlations are only `0.050` and
  `0.053`.
- `A0` and `A25` suppress the broad positive increment. `A25` is more
  right-tip-biased in the shape-only view, but its weighted mean is
  `1.276e-5`, about 5% of the FEM mean, and its local maximum is `1.27e-4`
  versus `8.63e-1` for FEM. Its spatial correlation is `0.082`.

The cycle therefore separates two errors that a single scalar metric can
hide: `R/S` are closer in mean amplitude but spatially smeared; `A25` reduces
false broad growth and produces a more tip-biased pattern, but greatly
underestimates the local event.

### Cycle 73: final listed transition

`S09-E009-R001-A25-cycle73-final-fields.png` shows `d_pre`, FEM `d_peak`, A25
`d_peak`, the two increment fields, and signed increment error. The three total
damage fields look nearly identical because the persistent crack already
occupies most of the visible signal. The increment panels reveal the remaining
difference: FEM is nearly stagnant, with weighted mean `1.096e-6`, whereas A25
predicts `1.275e-5`, about 11.6 times larger. The spatial correlation is
`0.065`.

### Development sequence

`S09-E009-R001-A25-selected-cycle-peak-fields.png` compares FEM and A25 peak
fields for cycles 1, 21, 46, 58, 69 and 73. The accompanying GIF covers all 16
available cycle transitions. These are independent mappings from each cycle's
pre-state `s00` to its peak state `s04`; they are not an autoregressive rollout.

The stored packet contains only the operator input at `s00` and target/output
at `s04`. It does not contain model predictions for intermediate within-cycle
load states `s01`, `s02`, `s03` or `s05`. The animation is therefore a sequence
of selected cycle-to-peak transitions, not a movie of all loading steps.

## What this figure set means

The field views support the frozen `COMPONENT_SIGNAL_OR_MIXED_TRADEOFF`
decision. A25's aggregate false-growth improvement is visible as suppression
of the broad background increment, and the equilibrium term prevents the A0
physics-residual blow-up. The model still does not recover the concentrated
crack-tip amplitude or robust within-cycle spatial alignment. Whole-field
`d_peak` similarity cannot be used as evidence of successful crack-growth
prediction because it is dominated by the inherited `d_pre` field.

This is evidence from one 16-cycle synthetic development trajectory. It does
not establish rollout, cross-trajectory, cross-mesh, fresh-holdout or real-road
generalisation.
