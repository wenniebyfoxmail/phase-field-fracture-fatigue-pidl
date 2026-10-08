---
storyline_id: S03
experiment_id: S03-E002
protocol_revision: v1
status: closed
started_at: 2026-10-08
closed_at: 2026-10-08
primary_storyline: S03
related_storylines: [S02]
scientific_verdict: inconclusive
---

# CrackMNIST current-state tokenizer MVP

## PIDL Experiment Gate

- **Mechanism question:** can the locked CrackMNIST-28/S data and labels pass
  through one reproducible `DIC -> latent token -> reconstruction/tip/SIF`
  pipeline without source leakage or label-semantic drift?
- **Claim changed if success:** tooling only: the current-state tokenizer
  pipeline is mechanically executable and ready for later scientific gates.
- **Claim changed if failure:** the implementation or data contract must be
  repaired before any tokenizer comparison; no model claim is permitted.
- **Cheaper diagnostic first:** reuse S03-E001's dataset/hash/lineage audit and
  completed tip/SIF evidence; run the new runner in audit mode plus unit tests
  before producer fitting.
- **Minimal output asset:** data audit, run receipt, finite checkpoint/history,
  test metrics, one reconstruction/probe figure set with README, and decision.
- **Code/producer alignment:** Mac performs audit/import/unit/forward sanity
  only. Any optimizer loop runs on the authorised Taobo GPU in a fresh run.
- **Success criteria:** every validity gate passes and the declared artifacts
  exist with finite values. No performance threshold is required in v1.
- **Failure criteria:** source/metadata identity failure, experiment overlap,
  broken label alignment, non-finite optimization/output, missing artifacts, or
  irreproducible fixed-seed execution.
- **Registry destination:** this Experiment, then one diagnostic row in
  `docs/pidl_experiment_inventory.md` after evidence review.
- **Decision:** implement and independently review; launch one fixed producer
  run only after Code Ready and Run Ready pass.

## Scientific question

Can a compact fixed-dimensional latent representation preserve enough of the
released current-state DIC field to support three mechanically complete output
paths: displacement reconstruction, one-pixel crack-tip localization, and
prediction of the provided `(KI, KII, T)` labels?

This experiment tests pipeline closure, not future-state sufficiency.

## Claim changed by success or failure

A success establishes only that the current-state representation workflow is
reproducible on the locked released data. It does not establish that the latent
state is physically sufficient, dynamically sufficient, superior to S03-E001,
or useful for future crack growth.

A failure is an implementation/data-contract failure. It cannot be interpreted
as evidence against scientific tokenization.

## Reuse decision

- **Searched:** S03-E001 protocol, runner, tests, decision, inventory entry,
  local CrackMNIST audit, official loader, and project registries.
- **Reused:** exact dataset and metadata locks; released experiment-side split;
  physical-field lineage definition; label/mask semantics; audit code patterns;
  Taobo producer and evidence-package conventions.
- **Not reused as a new claim:** S03-E001 performance gates and its frozen
  `NO_GO_CRACKMNIST_MECHANICS_CV` remain unchanged.
- **New code justification:** S03-E001 has tip and SIF heads but no explicit
  global latent bottleneck with DIC reconstruction. The new runner adds only
  the missing mechanical-closure path.

## Frozen protocol

### Data and holdout

- `crackmnist_28_S.h5`, MD5
  `26bb0aa814f2e3ed467879844222c46c`.
- Adjacent `experiments_metadata.json`, MD5
  `85b558aa217c2ad659b701946c399f58`.
- Use released splits unchanged: the two released training experiment-sides
  fit model and normalizers; released validation selects the best checkpoint by
  total validation loss; released test is evaluated once.
- S03-E001's strict lineage audit remains mandatory: eight contiguous,
  augmentation-distinct rows for every exact `(experiment-side, force, KI,
  KII, T)` physical-field tuple, with no physical-experiment overlap across
  released splits.
- Empty augmented tip masks remain valid for reconstruction/SIF and are omitted
  only from tip loss/metrics.

### Fixed model and fitting

- Flattened two-channel 28x28 standardized DIC input.
- Encoder `1568 -> 256 -> 32`; latent dimension is fixed at 32.
- Three heads: reconstruction `32 -> 256 -> 1568`, tip logits `32 -> 784`,
  and standardized SIF `32 -> 3`.
- Loss: `reconstruction_MSE + tip_CE + 0.5 * SIF_MSE`; tip CE is computed only
  for visible masks.
- AdamW, learning rate `1e-3`, weight decay `1e-4`, batch size 256, 20 epochs,
  seed 17. No architecture, seed, dimension, weight, or epoch sweep.
- Input and SIF normalizers are fitted on released training experiments only.

### Validity gates

1. Dataset and metadata hashes match.
2. S03-E001 physical identity, split-overlap, lineage and label checks pass.
3. No test row contributes to fitting, normalization or checkpoint selection.
4. Every saved scalar, tensor and metric is finite.
5. Required artifacts and producer provenance exist.
6. Reporting remains `current-state tooling-only`; HDF5 row adjacency is never
   called chronology.

### Primary gate

`PASS_CURRENT_STATE_TOKENIZER_MVP` requires all validity gates and the complete
artifact set. Reconstruction, tip and SIF performance values are diagnostics
and have no v1 pass threshold.

### Secondary diagnostics

- standardized reconstruction MSE and original-unit MAE;
- lineage-averaged visible-tip Euclidean error;
- lineage-averaged KI/KII/T MAE in released units;
- train/validation loss curves;
- one mechanically selected median-error test lineage visualization.

### Stop rule

- Stop before fitting on any data/identity/lineage gate failure.
- Stop the producer run on non-finite loss, missing CUDA, wrong machine,
  provenance/storage failure, or output corruption.
- The formal command must pass the independently reviewed commit through
  `--reviewed-commit`; the runner requires `HEAD` to match it and requires the
  authorised Taobo hostname `GPUServer8`.
- Do not stop or tune because metrics are weak; complete and report them.
- Failure to recover source stage/cycle affects only a separate future-state
  branch and cannot be rescued inside this Experiment.

### Required evidence

- `data_audit.json`;
- `run_receipt.json` and exact command;
- `checkpoint.pt` and `history.csv`;
- `metrics.json` and `test_predictions.npz`;
- PNG/PDF figure set plus `README_analysis.md`;
- independent code review bound to commit/config/data/protocol v1;
- independent evidence review bound to the retrieved package;
- `decision.md`.

## Amendments

None. Any changed data semantics, split, latent dimension, architecture, loss
weights or performance gate requires a dated reviewed amendment.

## Code review

- **Reviewer task:** GPT Pro read-only review of the runner, tests and protocol,
  followed by a second review of the exact corrective patch.
- **Bound commit / runner / config / data lock / protocol revision:**
  `265b09e3c4395be1d1aeaefd09ae5617c5bdf3c9`;
  `scripts/crackmnist_tokenizer_mvp.py`; frozen 32-D/20-epoch/seed-17 v1;
  locked data and metadata hashes above.
- **Verdict:** `PASS_CODE_READY`.
- **Closed findings:** required figures now select visible-tip rows only; formal
  fitting requires exact reviewed `HEAD` and hostname `GPUServer8`; saved
  prediction arrays receive a pre-write finite scan.

## Runs

| Run ID | Purpose / arm / seed | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S03-E002-R001 | fixed current-state tokenizer MVP, seed 17 | succeeded on Taobo GPU 0 | verified local archive with matching hashes | `execution_status=succeeded`; `PASS_CURRENT_STATE_TOKENIZER_MVP` |

## Evidence review

- **Reviewer task:** GPT Pro read-only review of receipt, metrics, decision,
  transfer-integrity checks and visual QA.
- **Bound Run IDs:** S03-E002-R001.
- **Bound analysis package:**
  `$PROJECT/local_archive/experiments/S03-E002/runs/S03-E002-R001/archive/`.
- **Verdict:** `PASS_EVIDENCE_READY`.
- **Blocking findings:** none. The review explicitly retained diagnostic-only
  metrics, chronology/future blocking and S03-E001's frozen NO-GO.

## Scientific verdict

`inconclusive` for scientific performance. The separate experiment-level
pipeline decision is `PASS_CURRENT_STATE_TOKENIZER_MVP`: the fixed pipeline
closed with finite complete artifacts, but v1 had no scientific-performance
threshold and therefore cannot establish representation sufficiency.

## Claim impact

Tooling claim advanced: a reproducible locked-data `DIC -> 32-D latent ->
reconstruction/tip/SIF` path now exists. No scientific claim advanced. This
Experiment does not reopen S03-E001, future-state, RUL, phase-field or
road-transfer claims.

## Next action

Freeze this run as the v1 pipeline-closure reference. Do not tune it. Any
tokenizer comparison, identity-augmentation shortcut audit, phase-field link or
future-state task requires a separately frozen experiment; future prediction
remains blocked until source chronology is auditable.
