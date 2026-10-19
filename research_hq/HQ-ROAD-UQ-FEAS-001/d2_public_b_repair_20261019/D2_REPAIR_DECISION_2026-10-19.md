# D2 backbone-transfer repair decision — 2026-10-19

## Decision step

**Active D2 question:** can one isolated backbone-transfer repair be tested under the existing A-validation/B-transfer/selective-risk contract with an attributable result?

The earlier D2 substep, “audit one new public B and select one repair,” is complete. GAPS384 is the provisional new B and an official ImageNet-pretrained ResNet18 encoder is the single repair. This does not reverse the frozen `HQ-ROAD-UQ-FEAS-001-R001` NO-GO for the scratch U-Net on CRACK500→CFD.

## Uncertainty to remove

The D1 failure panel separates two problems: extreme feature shift, where high `U_Z` cases often produce empty predictions, and annotation-width mismatch, where some low-`U_Z` cases still produce partial or empty predictions. The proposed test asks only whether a pretrained encoder reduces the first problem enough to make published-label transfer and selective acceptance feasible. It cannot resolve physical crack truth or annotation-width validity.

## Minimum action and deliverables

1. Keep the frozen CRACK500 A train/validation/test splits, exclusions, loss, seed, optimizer, 40-epoch maximum, six-hour hard budget, A-validation checkpoint selection and `U_LC`/`U_H`/`U_Z` definitions.
2. Change only the model from the D1 scratch U-Net to `ResNet18UNet`, initialized from the hash-locked official torchvision ResNet18 ImageNet weights.
3. Replace viewed CFD as B with locally audited GAPS384. Score its 382 nonempty published masks as the primary cohort and report its two empty masks separately.
4. Produce the checkpoint, selection history, A metrics, B metrics, risk curves, failure list, environment/identity receipt and bounded result statement specified by `d2_runner.py`.

## Advance and turn conditions

- **Advance the repair candidate:** F1 and F2 both pass. This only qualifies a later protocol decision; it does not authorize Road420 access or establish field validity.
- **Retain `U_Z`:** its first-95 accepted risk must be strictly lower than `U_LC` at the same coverage. Otherwise retain the simpler score even if F1/F2 pass.
- **Turn back to data/label compatibility:** F1 fails again, especially through empty predictions or failures concentrated on visibly thin labels.
- **Stop this repair:** no validated checkpoint is produced within the budget, nonfinite values occur, any locked identity drifts, or GAPS384 inventory differs from 384/382/2.
- **Road420:** remains sealed. It is not an unseen-C resource for this repair package and no access is authorized.

## Current status

The data/weight lock, model, runner and no-training validation pass are prepared. A producer run has not been authorized for `HQ-ROAD-UQ-FEAS-002-R001`.
