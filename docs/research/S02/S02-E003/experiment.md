---
storyline_id: S02
experiment_id: S02-E003
protocol_revision: v1
status: closed
started_at: 2026-10-08
closed_at: 2026-10-08
primary_storyline: S02
related_storylines: [S01]
scientific_verdict: negative
---

# Multi-specimen next-observation crack-length capability gate

## Scientific question

Before downloading about 34 GB of TIFF images or fitting a learned model, do
the eleven usable specimen trajectories in Zenodo 10895431 contain enough
origin-clean temporal signal for the simplest last-segment extrapolator to
beat persistence when predicting the next recorded ImageJ crack length?

This is a point-trajectory capability diagnostic. It does not test calibrated
observation uncertainty, image-based crack measurement, fixed-cycle-horizon
deployment, or transfer to roads.

## Claim contract

- Claim tier / optional tag: C3 controlled-experiment diagnostic.
- Estimand and comparison class: equal-specimen macro mean absolute error in
  metres for the next recorded crack-length observation, comparing causal
  last-segment secant extrapolation with persistence on identical origins.
- Claim if primary gate passes: this dataset merits a separately reviewed,
  specimen-disjoint learned point-forecast experiment.
- Claim if primary gate fails: stop model training on this release for this
  next-observation estimand; persistence remains the honest control.
- Blocked conclusion regardless of outcome: calibrated aleatoric or epistemic
  uncertainty; image-to-crack measurement validity; independent ground truth;
  fixed-cycle forecasting; material, laboratory, or road generalisation.

## Reuse decision

- Searched: S02-E001 comparators, S02-E002 trajectory rules, the Zenodo
  preflight scripts, and the published data-processing code.
- Reused: persistence, two-point secant, complete-specimen aggregation,
  origin-only input rules, and the CRC-verified Excel extraction.
- New code justification: a small read-only evaluator is required because no
  existing runner reads this workbook schema and emits specimen-macro evidence.

## Frozen protocol

- Evidence identity: Zenodo record 10895431, DOI
  `10.5281/zenodo.10895431`, revision 12 as retrieved on 2026-10-08. The twelve
  extracted Excel members and their CRC-32 values are fixed in
  `local_archive/open_data/zenodo_10895431_preflight_20261008/metadata/selective_excel_extraction_receipt.json`.
  `H05-4` is excluded before evaluation because it has no processed crack-length
  sheet. The remaining eleven specimens are all evaluated.
- Observation and target: `Ncycle` and measured crack length `a` from each
  processed-data sheet. The target for origin row `i` is `a[i+1]`; the issue
  time includes rows through `i` and the cycle of the next scheduled record
  `N[i+1]`. This is therefore conditional next-inspection prediction.
- Allowed inputs: only `N[0:i+1]`, `a[0:i+1]`, and `N[i+1]`.
- Forbidden inputs: reported `agrowth`, fitted crack length, future `a`,
  future-centred filters, `GCBT`, `GCBTmin`, `dGCBT`, any full-trajectory
  normalisation, and any TIFF information.
- Eligible origins: `i = 2, ..., n-2`, so at least three past observations and
  one future target exist. Every eligible origin is included.
- Comparator: persistence, `a_hat[i+1] = a[i]`.
- Challenger: last-segment secant,
  `a_hat[i+1] = a[i] + (a[i]-a[i-1])/(N[i]-N[i-1]) * (N[i+1]-N[i])`.
  No clipping, fitting, tuning, or group pooling is allowed.
- Necessary validity gates: all eleven frozen specimens are present; cycles are
  finite and strictly increasing; crack lengths are finite and nondecreasing;
  each specimen has at least four observations; predictions and errors are
  finite; both methods are scored on exactly the same origins.
- Primary criterion: compute MAE within each specimen, then take the unweighted
  mean across the eleven specimens. PASS only if
  `macro_MAE_secant < macro_MAE_persistence`. Equality fails.
- Threshold rationale: a complex learned route has no justification unless the
  simplest causal growth extrapolator beats the zero-change control. The zero
  improvement boundary is fixed before results and avoids an arbitrary effect
  size.
- Missing-data rule: any internal blank row, partial required row, or nonfinite
  required cell makes the validity gate fail; origins or specimens are not
  silently dropped. Fully blank spreadsheet rows after the final data row are
  ignored. The predeclared absence of the entire `H05-4` processed sheet is the
  only specimen exclusion.
- Minimal fatal-regression guards: the evaluator must pass analytic fixtures
  for constant, exactly linear, and accelerating trajectories before reading
  the workbooks.
- Explanatory diagnostics that cannot change the verdict: per-specimen MAE,
  group-macro MAE, number of specimen wins, horizon distribution, bias, and
  absolute-error quantiles.
- Stop rule: if validity fails or the primary criterion fails, do not train a
  learned model and do not download all TIFFs for this forecasting estimand.
  A small image subset may still be acquired under a separate measurement
  experiment.
- Minimum required evidence: frozen row-level prediction table,
  specimen-level table, machine-readable summary, run receipt, and read-only
  evidence review.

### Conditional fields

- State capability / teacher or reference qualification: future `a` is a
  same-pipeline ImageJ measurement from the lateral DIC images, not an
  independent truth source.
- Holdout unit / leakage firewall / independence axis: the physical specimen is
  the independence unit. This no-fit baseline evaluates every specimen
  separately; future learned work must use complete-specimen holdout.
- Uncertainty or deployment decision contract: out of scope. The release has
  no repeat annotation, repeat acquisition, independent aligned sensor, or
  calibrated observation-error distribution.

### Frozen outcome map

```text
validity fails                         -> inadmissible
validity passes + primary passes       -> supports
validity passes + primary fails        -> negative
primary cannot be computed/identified  -> inconclusive
```

## Producer and Run readiness

- Authorised producer alias / hostname: local Mac for this read-only,
  non-training arithmetic diagnostic only. Any learned training must be a new
  reviewed experiment on an authorised producer, normally Taobo.
- Commit or immutable snapshot / dirty status: to be recorded in the run
  receipt; only experiment-owned files may be committed from the dirty shared
  checkout.
- Runner / config / runtime:
  `scripts/s02_e003_next_observation_baselines.py`; bundled Codex Python with
  `openpyxl`; protocol v1; the evaluator must receive the exact extraction
  receipt and verify each workbook's uncompressed size and CRC-32 before use.
- Output / archive / log / retrieval route:
  `local_archive/experiments/S02-E003/runs/S02-E003-R001/`.
- Ownership and process-safety constraints: no PIDL/GPU training on Mac; no
  CSD3 fallback; no modification of source workbooks.

## Amendments

None. Protocol v1 was frozen before opening baseline results.

## Code review

- Reviewer task: independent read-only review recorded in
  `code_review_20261008.md`.
- Bound commit / runner / config / data lock / protocol revision: final commit
  pending; runner SHA-256
  `399d40447860a62f42a4e5346eb7177ffbd60c7aafaf0425dc17c52d36f92cd2`,
  extraction-receipt SHA-256
  `ca7d10beeb963c5629f9537f82bb6bbd487bb1d53806dafe831a5c55177b90fc`,
  protocol v1 scientific contract reviewed at SHA-256
  `cdce6e7a31824bc7a259c8d1220c9844664fd4c9b8b88e29abd2a05f58b4cffc`.
- Verdict: `PASS` after one blocking round and one corrected re-review.
- Blocking findings: all resolved before execution; see the review record.

## Runs

| Run ID | Purpose / arm / seed | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S02-E003-R001 | deterministic persistence-versus-secant gate | succeeded | verified | [S02-E003-R001.md](S02-E003-R001.md) |

## Evidence review

- Reviewer task: independent read-only recomputation recorded in
  [evidence_review_20261008.md](evidence_review_20261008.md).
- Bound Run IDs: S02-E003-R001.
- Bound analysis package: archived `predictions.csv`, `specimen_metrics.csv`,
  `summary.json`, and the byte-identical tracked compact summary.
- Verdict: `PASS` for evidence integrity; frozen scientific verdict `negative`.
- Blocking findings: none. The primary criterion failed.

## Scientific verdict

`negative`

All eleven frozen specimens and 249 eligible origins passed the validity
checks. Persistence achieved an equal-specimen macro MAE of
`0.0014011204808349546 m`; last-segment secant achieved
`0.0028051460811423165 m`, an increase of `100.20734258846007%`. Secant won
on only `2/11` specimens and was worse in every condition-group macro result.
The predeclared criterion therefore failed.

## Claim impact

For this release and conditional next-recorded-observation estimand, the
simplest causal growth extrapolator does not beat persistence. The frozen stop
rule closes learned-model training and full-TIFF acquisition for this
forecasting estimand. This does not prove that the trajectories contain no
learnable signal.

The result does not reopen calibrated uncertainty, independent ground truth,
image measurement validity, fixed-cycle forecasting, or road/material
generalisation. A separately frozen small-image measurement experiment remains
allowed.

## Next action

If image work is pursued, open a separate measurement experiment that first
freezes TIFF-to-cycle alignment, a repeat blinded annotation protocol, and a
consensus/reference rule. Acquire a bounded image subset before any full
34-GB download. Do not train a forecast model under S02-E003.
