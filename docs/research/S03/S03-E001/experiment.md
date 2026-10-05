---
storyline_id: S03
experiment_id: S03-E001
protocol_revision: v1
status: draft
started_at: 2026-10-05
closed_at:
primary_storyline: S03
related_storylines: [S02]
scientific_verdict:
---

# CrackMNIST mechanics-aware computer-vision feasibility pilot

## PIDL Experiment Gate

- **Mechanism question:** on a completely held-out physical fatigue experiment,
  does a DIC displacement field contain stable crack-tip and SIF information
  beyond a fixed spatial prior, the frozen energy-gradient heuristic, and a
  force-plus-specimen-metadata shortcut?
- **Claim changed if success:** permit only a bounded CrackMNIST observation-
  operator claim and a follow-up external-DIC replication.
- **Claim changed if failure:** stop neural expansion on this subset; retain the
  no-fit energy-localisation diagnostic only.
- **Cheaper diagnostic first:** dataset identity, physical-experiment grouping,
  augmentation-lineage recovery, one-pixel/empty-mask semantics, and the
  already completed fixed energy-gradient diagnostic.
- **Minimal output asset:** per-experiment table, two figures, run receipt and a
  GO/NO-GO decision.
- **Code/producer alignment:** Mac performs audit/tests only; formal fitting is
  a fresh attributable Taobo run with CUDA health and ownership preflight.
- **Success criteria:** the frozen conjunction below passes without post-result
  threshold changes.
- **Failure criteria:** any validity gate fails, or any member of the primary
  conjunction fails.
- **Registry destination:** this Experiment, then one compact update to the
  full experiment inventory; no research-frontier rewrite unless the storyline
  claim actually changes.
- **Decision:** diagnose first; launch one fixed small model only after Code
  Ready and Run Ready pass.

## Scientific question

Can released near-tip DIC displacement fields support physically held-out
crack-tip localisation and SIF estimation, with calibrated uncertainty, after
blocking all augmentations of a physical field and all rows of a physical
experiment together?

## Claim changed by success or failure

Success supports only a laboratory CrackMNIST observation-operator result:
within the four released AA2024 MT160 experiment-sides in the S subset, the DIC
field adds held-out information for the declared endpoints. Failure blocks
architecture expansion on this subset. Neither result establishes raw-image
vision, future crack growth, RUL, phase-field hidden-state recovery or road
transfer.

## Reuse decision

- **Searched:** `docs/pidl_experiment_inventory.md`, `docs/research_frontier.md`,
  `docs/research/S02`, `scripts/`, `tests/`, the local CrackMNIST audit and the
  official `dlr-wf/crackmnist` loader and split file.
- **Reused:** the exact plane-stress raw-gradient energy heuristic from
  `dic_energy_bridge_diagnostic_20260813`; repository Experiment/Run structure;
  Taobo producer rules.
- **New code justification:** no existing runner reconstructs released
  augmentation lineages, performs physical-experiment cross-fitting, measures
  incremental SIF information beyond the shortcut, or provides uncertainty and
  abstention evidence.

## Frozen protocol

### Data and identity lock

- External dataset:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/crackmnist_20260813/crackmnist_28_S.h5`.
- Required MD5: `26bb0aa814f2e3ed467879844222c46c`.
- Metadata: adjacent `experiments_metadata.json`.
- The physical grouping key is metadata field `experiment`, not the side ID.
  Left and right observations from the same experiment are never independent
  specimens. In this S subset, the four present side IDs map to four distinct
  physical experiments.
- One physical-field lineage is the exact tuple `(experiment-side, force, KI,
  KII, T)`. The audit must find exactly eight rows, one contiguous block and
  eight distinct augmentation tuples per lineage.
- All rows from an outer held-out experiment remain absent from fitting,
  normalization, calibration and threshold selection.
- The released one-pixel mask uses value 255. An empty augmented mask means the
  tip was cropped out; it is excluded from localisation loss/accuracy but stays
  valid for SIF regression.

### Holdout and seeds

Sort the four released experiment-side IDs by integer HDF5 experiment ID. For
outer holdout position `h`, use position `(h+1) mod 4` as the calibration
experiment and the remaining two experiments for training. Execute all four
outer folds with seeds `17, 29, 41`. Rows are never randomly divided.

### Fixed model and tasks

Use one compact CNN only: three 3x3 convolution blocks, one 1x1 tip-heatmap
head, and one global SIF-residual head. No architecture or hyperparameter sweep
is permitted. Train 40 fixed epochs with AdamW (`lr=1e-3`, weight decay
`1e-4`, batch 256). Input normalization is fitted on the two training
experiments only.

The tip task uses spatial cross-entropy on visible one-pixel masks. The SIF
task predicts the residual over the frozen force-plus-metadata shortcut. The
loss is `tip_CE + 0.5 * residual_MSE`. Report KI, KII and T separately.

### Comparators

1. **Fixed spatial prior:** mean visible training-tip coordinate; no DIC input.
2. **Energy-gradient heuristic:** argmax of the already declared raw finite-
   difference positive-strain energy proxy with `E=70 GPa`, `nu=0.33`, plane
   stress. No smoothing or holdout tuning.
3. **Force + specimen metadata shortcut:** ridge (`alpha=1e-3`) on one row per
   physical-field lineage using log force, its square, R, orientation, side and
   declared low-order interactions. It predicts SIF only. The CNN SIF head
   predicts its residual, making the incremental comparison matched.

### Primary endpoint and gate

`GO_BOUNDED_CRACKMNIST_MECHANICS_CV` requires all three:

1. **Localisation:** the CNN median Euclidean tip error improves by at least
   10% over the better of fixed spatial prior and energy argmax in at least
   three of four held-out experiments, and the equal-experiment lineage-blocked
   95% bootstrap interval for gain has lower bound above zero.
2. **Incremental SIF:** mean normalized MAE across KI/KII/T improves by at
   least 10% over the force-plus-metadata shortcut in at least three of four
   held-out experiments, and the equal-experiment lineage-blocked 95% bootstrap
   interval for shortcut-minus-model MAE has lower bound above zero.
3. **Uncertainty/abstention:** for all three SIF targets, mean held-out coverage
   of calibration-experiment-scaled nominal 90% intervals is in `[0.80, 0.98]`;
   and in at least three of four held-out experiments, the 50%-coverage tip risk
   is no more than 80% of full-coverage risk and confidence detects `>3 px`
   failures with AUROC at least 0.65.

Any failed member gives `NO_GO_CRACKMNIST_MECHANICS_CV`. The thresholds may not
be relaxed after viewing results.

### Secondary diagnostics

- mean and median tip error per experiment;
- calibrated heatmap prediction-region coverage and pixel area;
- SIF 90% interval width as well as coverage;
- full risk-coverage curves and AURC;
- empty-mask counts and per-experiment lineage counts.

### Stop rule

Stop before training if the source hash, physical identity, split overlap,
lineage size/contiguity, augmentation uniqueness, or label convention fails.
After launch, stop only for non-finite loss, corrupted/missing data, loss of
producer ownership/provenance, or CUDA/storage failure. A scientifically weak
result is completed and recorded as NO-GO; it is not tuned away.

### Required evidence

- `data_audit.json`;
- exact command and producer receipt;
- 12 checkpoints and fixed-epoch histories (4 folds x 3 seeds);
- per-experiment metrics table;
- baseline-comparison and uncertainty/abstention figures with README;
- decision and five-sentence Olaf/Brian summary;
- independent code review bound to commit, runner, data lock and protocol v1;
- independent evidence review bound to the retrieved run.

## Amendments

None. Protocol v1 has not yet produced a Run.

## Code review

- **Reviewer task:** pending.
- **Bound commit / runner / config / data lock / protocol revision:** pending.
- **Verdict:** pending.
- **Blocking findings:** pending.

## Runs

| Run ID | Purpose / arm / seed | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S03-E001-R001 | four folds, fixed three-seed ensemble | prepared | pending | pending |

## Evidence review

- **Reviewer task:** pending.
- **Bound Run IDs:** S03-E001-R001.
- **Bound analysis package:** pending.
- **Verdict:** pending.
- **Blocking findings:** pending.

## Scientific verdict

`inconclusive` until the frozen producer run and evidence review close.

## Claim impact

No current Storyline claim changes at protocol freeze.

## Next action

Complete deterministic audit/tests and independent Code Ready review; then run
Taobo health/ownership/storage preflight before dispatch.
