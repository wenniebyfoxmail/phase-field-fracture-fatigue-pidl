# S09-E009 result figure set

## Scientific question

At the frozen update-500 endpoint on one 16-cycle synthetic development
trajectory, does the reviewed `A25` damage-anchor PINO arm repair the E008
damage-regime failure relative to exact replay, and what trade-offs accompany
its damage-component changes?

## Evidence source

- Run: `S09-E009-R001-four-arm-damage-separation`
- Producer commit: `bc1309c75a2309e8b5e0fa00d474605a333d0379`
- Packet manifest SHA256:
  `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`
- Completion receipt: `S09-E009-R001-completion-receipt.json`
- Exact numerical table: `S09-E009-R001-decision-table.csv`
- Exact decision record: `S09-E009-R001-decision-metrics.json`

The tracked files are compact copies from the verified retrieved run. The
complete logs and checkpoints remain in the local run archive.

## Reading order

1. Read `S09-E009-R001-decision-table.csv` for the authoritative update-500
   values and arm labels.
2. Inspect `S09-E009-R001-decision.png` for the same-arm comparison across the
   frozen damage, regime-ranking, physics and judgement axes.
3. Use the completion receipt and decision JSON for predicate traces,
   cross-arm eligibility, replay status and exact precision.

## What the figure shows

The figure compares all four frozen arms at the sole decision endpoint. It
makes visible that `A25` lowers growth MAE and near-stagnant false growth versus
replay while amplitude AUC remains 0.68, median spatial alignment is not
positive, and the equilibrium residual remains 2.70 times replay. It also
shows the large residual reduction from `A0` to `A25` under the matched anchor.

## Cross-figure interpretation

The numerical table, predicate trace and figure agree on
`COMPONENT_SIGNAL_OR_MIXED_TRADEOFF`. The damage-component gain is real within
this frozen development screen, but it does not satisfy the complete
relative-repair or confirmatory-nomination criteria. The target-support
diagnostic in the parent experiment folder motivates a new support-aware test;
it does not prove why E009 behaved this way.

## Allowed conclusion

At update 500 on this fixed synthetic development packet, `A25` improves the
reported growth and false-growth components relative to replay, while regime
ranking and spatial alignment remain unresolved and other objectives incur
measured costs.

## Blocked conclusion

This figure set cannot establish autonomous rollout, cross-trajectory or
cross-mesh generalisation, FEM truth, complete fracture-evolution PINO
validity, unique failure causation, architecture incapacity or real-road
applicability.
