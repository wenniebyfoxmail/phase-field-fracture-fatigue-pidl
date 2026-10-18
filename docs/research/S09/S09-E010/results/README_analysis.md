# S09-E010 tracked result evidence

This directory contains the compact, claim-bearing evidence for
`S09-E010-R001-support-amplitude-three-arm`. Complete checkpoints and logs stay
under `local_archive/experiments/S09-E010/runs/`.

- `S09-E010-R001-decision.png` shows all 16 target/predicted amplitudes and the
  four protected `B25/A25` ratios.
- `decision_table.csv`, `decision_metrics.json`, and `completion_receipt.json`
  preserve the frozen update-500 arithmetic and execution identity.
- `per_cycle_metrics.csv` preserves every scheduled all-cycle evaluation.
- `field_visualisation/S09-E010-R001-cycle69-three-arm-increments.png` compares
  physical increment magnitude and independently normalised shape.
- `field_visualisation/S09-E010-R001-cycle73-final-fields.png` separates the
  inherited total crack from newly predicted damage.
- `field_visualisation/S09-E010-R001-all-selected-cycles-fields.gif` covers the
  16 stored `s00 -> s04` transitions. It is not a within-cycle load-step movie.
- `field_visualisation/field_reconstruction_receipt.json` binds checkpoints,
  packet identity, replay accuracy, display method, and output hashes.
- `cycle_separability/` contains the zero-step output/gradient SVD and the
  focused B25 pair-contrast amplitude-Jacobian audit.
- `../result_evidence_review_20261019.md` records the final independent
  `RESULT_EVIDENCE_READY_PASS`.

**See:** `B25` lowers false growth and preserves all protected metrics, while
all three arms retain the same amplitude AUC of 0.68.

**Therefore:** the balanced damage objectives produce a component-level repair
but no targeted growth-ranking signal; beta 0.25 remains important for keeping
the balanced arm's equilibrium residual controlled. The current head retains
local sensitivity for all eight wrong pair margins, while the present B25
descent worsens those eight margins, so the next minimal test is an explicit
cross-cycle ranking objective with the same head.

**Does not show:** rollout, fresh-holdout, cross-trajectory or real-road skill,
or a complete fracture-evolution PINO.

