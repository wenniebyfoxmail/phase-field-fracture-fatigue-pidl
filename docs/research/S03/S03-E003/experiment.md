---
storyline_id: S03
experiment_id: S03-E003
protocol_revision: v1
status: planned
started_at: 2026-10-08
primary_storyline: S03
related_storylines: []
scientific_verdict: pending
---

# CrackMNIST augmentation-sensitivity audit

## PIDL Experiment Gate

- **Mechanism question:** across the eight released randomly augmented views of
  the same physical CrackMNIST lineage, how sensitive are the frozen S03-E002
  diagnostic errors to continuous augmentation amplitude and vertical flip?
- **Claim changed if success:** tooling/observation only: the frozen tokenizer's
  within-lineage augmentation associations become measured and auditable.
- **Claim changed if failure:** the released metadata/prediction join or the
  proposed estimand is not evaluable; no model-performance conclusion follows.
- **Cheaper diagnostic first:** reuse the verified S03-E002-R001 test prediction
  archive and released augmentation metadata. Do not train, infer again, or
  change the S03-E002 checkpoint.
- **Minimal output asset:** audit JSON, primary-estimand JSON, lineage contrasts,
  secondary metrics, one two-panel figure set with README, and decision note.
- **Registry destination:** this Experiment and exactly one diagnostic row in
  `docs/pidl_experiment_inventory.md` after independent evidence review.
- **Decision:** `PASS_PLAN_READY`; implement one deterministic post-hoc analysis.

## Five-question intake

1. **Question:** does diagnostic error vary systematically across the eight
   released augmented views of one physical state?
2. **Independent unit:** 743 physical lineages. The 5,944 rows are repeated
   views and are never treated as independent samples.
3. **Exposure:** released `shift_x_mm`, `shift_y_mm`, `rotation_deg`, and
   `vertical_flip`. There is no identity/unaugmented reference row.
4. **Outcome:** primary is row-level standardized reconstruction MSE. Original-
   unit reconstruction MAE, visible-tip-conditional error, visibility, and
   absolute SIF errors are secondary.
5. **Allowed conclusion:** association/sensitivity across released augmented
   views only. Identity degradation, causal effects, augmentation invariance,
   future/RUL prediction, dynamic or phase-field sufficiency, road transfer,
   and reversal of S03-E001 are blocked.

## Frozen inputs and source semantics

- HDF5:
  `$PROJECT/local_archive/open_data/crackmnist_20260813/crackmnist_28_S.h5`,
  MD5 `26bb0aa814f2e3ed467879844222c46c`.
- Predictions:
  `$PROJECT/local_archive/experiments/S03-E002/runs/S03-E002-R001/archive/test_predictions.npz`,
  SHA256 `e1371987d06c2e7e215dd8561947d0589fdfbc85d50657f3220d31186c939e58`.
- Upstream model/run is immutable S03-E002-R001, code
  `265b09e3c4395be1d1aeaefd09ae5617c5bdf3c9`, already Evidence Ready.
- Official loader semantics were checked at `dlr-wf/crackmnist` commit
  `df3564821cad725e74d26fc19e332afe74b8627c`: augmentation columns are
  `(shift_x_mm, shift_y_mm, rotation_deg, vertical_flip)`.
- Frozen nominal supports are 20 mm, 10 mm and 10 degrees. The analysis must
  stop rather than infer or reorder columns if these semantics cannot be
  verified.

## Primary estimand

For lineage `i` and view `j`, define

```text
y_ij = standardized reconstruction MSE
s_ij = sqrt(((shift_x/20)^2 + (shift_y/10)^2 + (rotation/10)^2) / 3)
f_ij = vertical_flip in {0,1}
y_ij = alpha_i + beta_s * s_ij + beta_f * f_ij + error_ij
```

Estimate `(beta_s, beta_f)` after demeaning outcome and both covariates within
lineage. Report 95% cluster-bootstrap intervals using 2,000 resamples of whole
lineages with seed `20261008`. Coefficient sign, size and significance do not
determine the audit PASS.

## Secondary diagnostics

- For each lineage, compare the lowest and highest *observed* `s` views and
  report the reconstruction-MSE difference and a lineage-bootstrap median CI.
- Four globally defined `s` quantile bins visualize mean lineage-centered
  reconstruction MSE; bin edges are not gates.
- Repeat the joint fixed-effect association descriptively for original-unit
  reconstruction MAE, absolute KI/KII/T error, tip visibility, and tip error
  conditional on visibility.
- Report per-lineage reconstruction error range and visible-view count.
- Never call the paired contrast unaugmented-versus-augmented.

## Validity, leakage, and independence gates

1. Prediction and HDF5 hashes match the frozen values.
2. `row_idx` is unique, test-only, in range, and joins one-to-one to
   `test_augs`.
3. Exactly 743 lineages and eight rows per lineage are recovered; rows sharing
   a lineage retain identical SIF truth.
4. All augmentation values are finite; flip is binary; all primary arrays are
   finite.
5. At least 90% of lineages have nonzero continuous-severity variation.
6. The demeaned joint primary design has rank two.
7. All uncertainty resamples whole lineages, never individual rows.
8. E003 results cannot select or modify the E002 checkpoint, model or
   normalizers.

## Operational decision gate

- `PASS_AUGMENTATION_AUDIT_MVP`: all validity gates pass and all required
  outputs are finite and present.
- `MIXED_DIAGNOSTIC`: reconstruction primary is valid, but a secondary outcome
  is evaluable in only 50% to 90% of lineages or has incomplete conditional
  coverage.
- `FAIL_AUDIT_MVP`: primary variation is below 50%, the join/identity/hash gate
  fails, the primary design is rank deficient, outputs are non-finite, rows are
  treated as independent, or an identity baseline is fabricated.

These are evaluability criteria, not scientific-performance thresholds.

## Stop rule

Stop before estimating or rendering if any strict input, join, lineage,
semantics, design-rank, or finiteness gate fails. Large, small, surprising or
non-significant sensitivities are results and are not stop conditions. No new
training is permitted in S03-E003.

## Required evidence

- `augmentation_audit.json`;
- `primary_estimand.json`;
- `lineage_contrasts.csv`;
- `secondary_metrics.json`;
- `figures/augmentation_sensitivity.{png,pdf}`;
- `README_analysis.md`;
- `decision.md`;
- independent code review bound to exact commit, inputs and v1 protocol;
- independent evidence review of the generated package.

## Planning review

- Reviewer: GPT Pro, conversation `6ac749ae-75cc-832f-b8fb-025ef1689cc9`.
- Verdict: `PASS_PLAN_READY`.
- Adopted: one primary joint lineage-fixed-effect model; whole-lineage
  bootstrap; visibility as a secondary outcome; no performance-size gate.
- Modified: lowest-versus-highest observed contrast and binned plots are
  secondary, not co-primary.
- Rejected: no identity subset, no row-level independence, no new training.

## Amendments

None. Any change to input identity, augmentation semantics, primary outcome,
severity definition, bootstrap unit, or operational gate requires a reviewed
amendment before results are viewed.
