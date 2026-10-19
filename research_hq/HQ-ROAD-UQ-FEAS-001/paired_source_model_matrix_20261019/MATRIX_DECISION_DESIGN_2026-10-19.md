# Paired source × model mechanism comparison — design

## Goal anchor

The programme asks whether crack-segmentation outputs can be accepted or rejected reliably under named public-source shifts. The frozen D1 result remains negative for scratch U-Net on CFD; the running D2 result tests a ResNet18-pretrained repair package on GAPS384. D2 changes both model package and B source, so the two diagonal results alone cannot attribute any difference to the repair.

## First-principles mechanism

For source `s`, an image and its published label follow `y_s = O_s(x, c_s) + e_s`: a latent crack-like state `x`, source/capture/annotation convention `c_s`, and reference error `e_s`. A predictor package `f_m` can fail because:

1. its representation does not transfer across `s`;
2. the new source is simply easier;
3. `O_s` changes the target width/location convention even when the feature is visible;
4. uncertainty ordering adds no information beyond simple confidence.

The smallest decision-scale comparison that distinguishes these live explanations is the complete paired matrix under one inference/scoring backend:

| Fixed checkpoint | CFD 118 | GAPS384 382 nonempty + 2 empty |
|---|---|---|
| D1 scratch U-Net | frozen D1 cell; reuse verdict and verify comparable recomputation | missing cell |
| D2 ResNet18UNet package | missing cell | frozen D2 cell after completion; reuse verdict and verify comparable recomputation |

Architecture and ImageNet initialization are treated as one repair package. This matrix does not attribute their effects separately.

## One bounded offline evidence package

- Reuse the frozen D1 and D2 CSV/result files as the authoritative diagonal verdicts.
- Run one no-training GPU inference batch to fill the two missing cells and to compute diagnostics absent from the diagonal outputs under the same native-pixel tiling backend.
- For each source/model cell report strict Dice/error, degeneracy, foreground overlap, 2-pixel and 4-pixel symmetric tolerance overlap, and risk–coverage for `U_LC`, `U_H` and A-validation-fitted `U_Z` at the same 25% acceptance budget.
- Keep CFD and GAPS source-stratified. Never pool them into one apparent sample size.
- Generate paired image panels using a frozen selection rule: largest three repair improvements, largest three repair degradations, and up to two cases where both predictions degenerate, separately per source. The panels explain disagreement and do not select the primary verdict.
- Report paired bootstrap intervals for new-minus-old strict error within each source as magnitude/uncertainty, not as a substitute for the frozen D1/D2 gates.

## Outcome map

- **Representation gain across sources:** strict error and degeneracy improve for the repair on both CFD and GAPS, with useful absolute risk and a score reducing accepted risk. Prepare a later untouched-source/review-budget scientific validation; do not open Road420 automatically.
- **New-source-only apparent gain:** GAPS improves but CFD does not. Attribute the diagonal change to source easiness/compatibility, not the repair; redirect to source/label compatibility.
- **Tolerance-only gain:** strict overlap remains poor while 2/4-pixel overlap rises materially. Treat annotation/location convention as the live mechanism; it explains but does not rescue the frozen strict gate.
- **Simple confidence wins:** retain the useful representation, drop complex UQ from the next route.
- **Absolute risk remains unusable:** do not present relative accepted-risk reduction as a deployable inspection system; stop blind backbone/seed sweeps and redirect.

## Authority boundary

The running `HQ-ROAD-UQ-FEAS-002-R001` is not modified. The paired matrix needs no training, new seed, new source or Road420 access, but its additional GPU inference is outside that frozen runner. Implementation may be prepared locally; execution requires one separate approval tied to the final evaluator snapshot, exact two checkpoints, CFD/GAPS identities, GPU budget and no-retry rule.

## Result pointer — 2026-10-19

The authorized unique run `HQ-ROAD-UQ-MATRIX-001-R001` completed with exit code 0, no retry, zero training steps and no Road420 access. The repair package increased strict mean error on both CFD and GAPS, decreased 2/4-pixel tolerant F1 on both, and did not create a useful absolute acceptance queue. Final disposition: redirect to target/source compatibility and stop blind backbone, seed and UQ-score expansion for this route. See `runs/HQ-ROAD-UQ-MATRIX-001-R001/03_RESULT_CLAIM_AUDIT_AND_FINAL_DECISION_2026-10-19.md`.
