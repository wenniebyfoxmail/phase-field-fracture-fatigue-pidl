# D1 review amendment: transition-aware GNO

**Date:** 2026-08-26  
**Status:** `SUPERSEDED_BY_SECOND_REVIEW_FINAL_LOCK__NO_LAUNCH`  
**Reviewed task:** `01a03b5c-6ac8-79c2-ac18-5f5cc73ff389`

## Decision

The review's eight findings were checked against the implementation. Seven
required code or contract changes; the eighth required materially stronger
tests. The prior D1 objective is superseded before any producer run, so there
is no result comparability problem and no discarded training output.

This remains a data-only `GNO-data` experiment with zero physics loss.

The second independent review found that loss-value calibration did not
balance gradients and identified release/provenance, direct-dependency lock,
canonical-gate, forecast-population, strict-JSON and test-contract gaps. These
are resolved in
[`at1_fatigue_mesh_pino_d1_final_prelaunch_lock_20260826.md`](at1_fatigue_mesh_pino_d1_final_prelaunch_lock_20260826.md),
which is now canonical.

## Adopted corrections

1. **Loss balance.** Four channel errors are divided by training-fold residual
   scales and optimized with SmoothL1. Derived-active error receives its own
   training-fold one-cycle scale. Support uses
   `binary_cross_entropy_with_logits`. Finally, ordinary and
   transition-containing windows are divided by their separate mean
   training-only persistence losses. Thus 1:1 sampling also has approximately
   1:1 baseline optimization influence.
2. **Frozen dataset.** The runner now requires the exact `HASHES.sha256` SHA,
   exact manifest SHA, exact seven-file set and hashes, exact four trajectory
   IDs, unique files, manifest/filename/internal-NPZ ID agreement, and matching
   first-hit/confirmed metadata.
3. **Evaluation distribution.** The nine-row event-aligned primary stress test
   is retained and explicitly labelled retrospective. A secondary evaluation
   covers every legal held-out origin and reports natural-prevalence precision,
   recall, FPR, Brier score and fixed 10-bin ECE. It cannot tune the model or
   threshold.
4. **Producer/provenance.** Before reading data or creating output, the runner
   requires explicit Taobo producer ID, `drtao`, CUDA, selected GPU, RTX 4090,
   `/mnt/data2/drtao` data and `/mnt/data2/drtao/wennie` fresh output. It records
   hostname, git commit/branch/dirty state, Python/Torch/CUDA/device, code
   hashes and full arguments.
5. **Locked assets.** The NPZ now contains all nine predictions, nine FEM
   targets, logits, probabilities and all three three-frame input contexts.
6. **Reproducibility.** Python/NumPy/Torch/CUDA seeds and deterministic cuDNN
   settings are used. CUDA `index_add` graph aggregation is still not promised
   byte-identical, so the declared unit is the frozen three-seed distribution,
   not an identical same-seed replay claim.
7. **Capacity.** Model default width is 96 and both runner and tests require the
   exact 339,461 parameters.
8. **Contract tests.** Tests now cover exact capacity, stable loss, training-only
   statistics, true recurrent rollout, nine-row evaluation, complete NPZ,
   natural-distribution metrics, frozen hash failure, whole-trajectory holdout
   and Mac producer rejection.

## Read-only diagnostics

- Expanded local suite: `25 passed`.
- Both new Python modules compile and `git diff --check` passes.
- Exact frozen dataset hash set passes.
- All four archived first-hit labels are independently reproduced by the
  runner event predicate: hard5 c83, hard8 c86, soft5 c84, soft8 c83.
- One complete held-out-hard5 training-fold probe contained 12 transition and
  235 ordinary windows. After channel/active scaling, persistence field loss
  was 8.8577 versus 0.9658, a 9.17 ratio rather than the reviewed raw objective's
  roughly 900--2500 ratio. The locked bucket calibration maps both persistence
  baselines to 1.0 before transition BCE is added.

These are implementation diagnostics, not efficacy evidence.

## Remaining gate

No training is authorized. This document is historical after the second review;
use the final pre-launch lock for any later decision.
