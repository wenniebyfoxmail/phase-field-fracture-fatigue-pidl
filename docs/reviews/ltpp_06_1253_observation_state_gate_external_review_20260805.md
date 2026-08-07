# External Review: LTPP 06-1253 Observation-State Gate

Date: 2026-08-05

Reviewer role: independent scientific-methods subagent, asked to design the gate without editing files or seeing future results.

## Recommended design

- Use only the first seven authorized primary surveys.
- Use four rolling-origin folds: surveys 1-3 predict 4, 1-4 predict 5, 1-5 predict 6, and 1-6 predict 7.
- Hide the complete `126 x 382` field at each forecast date; never split pixels randomly.
- Compare exactly persistence, a smooth nonmonotone transition model, and an irreversible latent-state model with a noisy observation layer.
- Fit every parameter using training dates only.
- Use foreground/background balanced MAE as the primary metric, with balanced CRPS, soft Dice, interval coverage, and interval width as safeguards.
- Use contiguous `6 x 10` spatial macrotiles for cluster bootstrap; do not treat pixels as independent samples.
- Require the latent model to improve median balanced MAE by at least 10% and median balanced CRPS by at least 5% against both baselines, win at least three of four folds, and avoid material fold-level regressions or uncertainty inflation.
- Return one fail-closed decision. Do not tune thresholds after seeing results.

## Adopted locally

- The complete rolling-origin split, metric family, macrotiling, thresholds, fail-closed decision, and forbidden-claim boundary are adopted.
- The smooth and latent models share the same fold-specific Student-t observation-noise family.
- Only `line_damage` is used. Area, climate, traffic, MON_DIS, FWD, and the 2012/2015 auxiliary surveys are excluded.

## Modified locally

The suggested high-dimensional probabilistic optimizer and three-initialization selection are replaced by deterministic low-capacity estimators. With only three to six training dates per fold, a per-pixel spike-and-slab optimizer would be weakly identified and could win through flexibility rather than state semantics.

- Smooth model: last local trend with a training-only shrinkage factor.
- Latent model: PAVA isotonic latent history plus a training-only nonnegative-drift scale.
- Observation uncertainty: one shared fold-specific Student-t noise estimate for all three models.

This modification makes the gate harder for the latent model and keeps the comparison focused on transition semantics. It does not turn the inferred latent field into physical ground truth.

