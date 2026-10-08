---
storyline_id: S02
experiment_id: S02-E004
protocol_revision: v1.2
status: ready
started_at: 2026-10-08
closed_at:
primary_storyline: S02
related_storylines: [S01]
scientific_verdict:
---

# Small TIFF crack-tip measurement repeatability pilot

## Scientific question

Can a blinded operator reproduce a projected visible crack-tip measurement
from the Zenodo 10895431 TIFF images with error small enough to distinguish it
from the 1.401 mm persistence forecast error observed in S02-E003?

This experiment estimates same-image measurement repeatability. It does not
establish physical truth, independent-sensor accuracy, temporal forecasting,
or calibrated total uncertainty.

## Claim contract

- Claim tier / optional tag: C1 observation/measurement pilot.
- Estimand and comparison class: the 90th percentile of absolute paired
  differences between two blinded measurements of the same frame's projected
  visible crack length, in millimetres.
- Claim if primary gate passes: the declared TIFF/ImageJ-style protocol is
  repeatable enough for a larger measurement study and for an explicit
  observation-noise component bounded by this procedure.
- Claim if primary gate fails: stop image-model training and revise the
  landmark, visibility, or calibration protocol before acquiring more labels.
- Blocked conclusion regardless of outcome: unbiased crack truth, independent
  reference accuracy, 3-D crack length, future prediction, uncertainty
  decomposition, or transfer beyond the three pilot specimens.

## Reuse decision

- Searched: S02-E002 image-measurement contract, S02-E003 error scale, Zenodo
  10895431 central-directory and workbook audits, and the associated paper.
- Reused: physical-specimen independence, visibility status, separated
  reference metadata, and blinded repeated measurement.
- New code justification: a deterministic selector and packet builder is
  required to map irregular processed cycles to TIFF frames without exposing
  workbook crack lengths to the annotator.

## Frozen protocol

- Evidence identity: Zenodo 10895431 revision 12. Source ZIP identities are
  H01 `md5:1a067a54b75d7f780ac0cb577aebcfcb`, H05
  `md5:8ec3a330f59a7178ab6eb838899321db`, and V05
  `md5:1dc696bd097e7e00ac092619163068ec`.
- Specimens: the first released specimen in each condition group, fixed by ID
  rather than outcome: `H01-1`, `H05-1`, and `V05-1`.
- States: five processed rows per specimen at deterministic indices
  `round(k*(n-1)/4)` for `k=0..4`, using Python's integer arithmetic as
  implemented and checked for uniqueness.
- TIFF mapping: camera `_0` only. For each selected processed cycle, choose the
  TIFF with minimum absolute cycle difference; ties choose the earlier TIFF.
  Mapping validity follows the selected TIFF's nearest-neighbour cell in cycle
  space: when the processed cycle lies to the right of the selected TIFF, use
  half the interval to the next TIFF; when it lies to the left, use half the
  interval to the previous TIFF. At a sequence boundary, where the processed
  cycle lies outside the observed TIFF range, use one full adjacent interval.
  An exact cycle match has zero mapping difference. Any failure invalidates
  packet construction rather than dropping the state.
- Packet: 15 unique TIFFs. Round A is created first in a blind packet directory;
  the key, source identities, and canonical images are written to a separate
  sealed directory. Round B does not exist at that time. A separate completion
  mode validates all 15 Round A annotation rows and writes the completion time
  itself; callers cannot supply or override it. The runner refuses to create
  Round B until 24 hours after that sealed record. Each round uses HMAC tokens
  from a sealed random secret; the runner asserts that no token is reused across
  rounds. The operator receives only the requested round directory.
- Measurement object: projected visible crack length along the specimen axis
  from the fixed loading-line/left reference plane to the furthest visible
  crack tip. Calibrate millimetres from the stamped ruler in the same image.
  Record the reference-plane coordinate, tip coordinate, ruler calibration
  span, length, and visibility status (`resolved`, `ambiguous`, `not_visible`).
  For a resolved row, the recorded length must equal
  `abs(tip_x-reference_x) * ruler_span_mm / abs(ruler_end_x-ruler_start_x)`
  within `0.01 mm`; this is an entry-arithmetic validation tolerance, not a
  scientific acceptance threshold. All coordinates must lie within the image.
- Ambiguity rule: no forced numeric endpoint for `ambiguous` or `not_visible`.
  All calibration, endpoint, and length fields remain blank for such rows. The
  same visibility status in both rounds is required for a numeric pair.
- Necessary validity gates: the three 1-MiB central-directory tails match the
  frozen SHA-256 identities and expected entry counts; the twelve workbooks
  match the CRC-verified extraction receipt; all 15 source TIFFs pass central-directory
  uncompressed-size and CRC-32 checks; image dimensions are readable; packet
  key and blind manifests are one-to-one; no specimen, cycle, workbook length,
  or round-pair identity appears in blind filenames; both rounds are complete;
  at least 12/15 frames have paired `resolved` measurements; and no calibration
  field is missing for a resolved measurement.
- Primary criterion: among paired resolved frames, the empirical type-7 90th
  percentile of absolute Round-A minus Round-B length differences must be no
  greater than `1.4011204808349546 mm`, the frozen persistence macro MAE from
  S02-E003. Equality passes.
- Threshold rationale: repeat measurement disagreement at the upper pilot
  quantile must not exceed the entire error of the best transparent temporal
  predictor; otherwise image measurement noise can dominate the forecast
  comparison.
- Missing-data rule: unresolved frames remain visibility evidence and do not
  receive invented values. Fewer than 12 numeric pairs makes the experiment
  inconclusive, not a repeatability pass.
- Explanatory diagnostics that cannot change the verdict: median absolute
  difference, mean signed difference, Bland-Altman limits, resolved fraction,
  visibility-status agreement, per-group pairs, and difference from the
  published workbook `a` after unblinding.
- Stop rule: do not train segmentation, keypoint, or forecast models if the
  packet is invalid or the repeatability gate fails. A pass opens only a larger
  annotation/reference study.
- Minimum required evidence: source-selection manifest and its digest, blind packet manifests,
  sealed HMAC key, member-level extraction receipt, two completed annotation tables, evaluator
  output, and independent evidence review.

### Conditional fields

- State capability / teacher or reference qualification: workbook `a` is a
  same-optical-pipeline ImageJ measurement and is diagnostic only after
  unblinding; it is not ground truth.
- Holdout unit / leakage firewall / independence axis: physical specimen is the
  independence unit. Repeat rounds estimate operator/procedure repeatability;
  frames are not counted as independent specimens.
- Uncertainty or deployment decision contract: only repeat measurement error
  under this procedure can be estimated. Physical heterogeneity, model
  uncertainty, 3-D curvature, invisible tips, and sensor drift remain separate.

### Frozen outcome map

```text
packet or measurement validity fails       -> inadmissible
valid packet, fewer than 12 numeric pairs   -> inconclusive
validity passes + primary passes            -> supports
validity passes + primary fails             -> negative
```

## Producer and Run readiness

- Authorised producer alias / hostname: local Mac for selective acquisition,
  packet construction, and annotation only; no training.
- Commit or immutable snapshot / dirty status: pending code review and commit.
- Runner / config / runtime:
  `scripts/s02_e004_build_tiff_repeatability_packet.py`; bundled Codex Python
  with `openpyxl` and Pillow; protocol v1.2. Frozen tail SHA-256 identities:
  H01 `bc13303f579536bd8bc08d8b1c805025dfe7fde5649392ec9480a4ddb7bdd959`,
  H05 `6f2236acd67dc7029a58d6767a6217737bb6044aada1931296d78c817cfe5668`,
  V05 `699238b96f07302e4a8656ace07b18007173d5a56fbf9460d52be09145d6dc56`.
- Output / archive / log / retrieval route:
  `local_archive/experiments/S02-E004/runs/S02-E004-R003/`.
- Ownership and process-safety constraints: source archives/workbooks are
  read-only; no full-archive extraction; no PIDL training on Mac.

## Amendments

### 2026-10-08 — v1.1 boundary-cycle mapping amendment

R001-A v1 failed before selecting or extracting any formal image because the
processed initial state at cycle 0 maps to the first H01-1 TIFF at cycle 1.
The v1 rule used half of the single forward interval at a sequence boundary,
giving a tolerance of 0.5 cycle and rejecting the 1-cycle acquisition offset.

Revision v1.1 uses one full adjacent interval only at the first or last TIFF;
the internal-state rule is unchanged. This is a data-index boundary repair. No
image measurement, workbook crack-length result, repeatability result, or
primary metric was observed or changed. R001-A remains failed and R002-A must
receive a new review and commit binding.

### 2026-10-08 — v1.2 cadence-transition mapping amendment

R002-A v1.1 failed before formal image extraction at H05-1 processed cycle
1050. The selected TIFF was cycle 1000. TIFF cadence changes there from 10 to
100 cycles; taking half the smaller two-sided interval incorrectly allowed only
5 cycles even though 1050 is the exact midpoint between 1000 and 1100.

Revision v1.2 defines the validity cell directionally toward the processed
cycle, which is the geometry used by nearest-neighbour selection. A value-blind
audit of all 15 frozen state indices confirmed that every mapping is inside its
directional cell. No image measurement, workbook crack length, repeatability
result, primary metric, or threshold was examined or changed. R001-A and
R002-A remain failed.

## Code review

- Reviewer task: v1, v1.1, and v1.2 passed independent read-only review
  recorded in `code_review_20261008.md`.
- Bound commit / runner / input identities / protocol revision: v1 was bound to
  commit `7e5d89e4f80740ffee1de1af53e7f9bc722c1d76`; v1.1 to commit
  `0bdb1dab6f3f9ca06e7c9735056e6ff751c69aa2`; v1.2 commit pending.
- Verdict: v1 `PASS`; v1.1 `PASS`; v1.2 `PASS` for R003-A.
- Blocking findings: v1 execution exposed the boundary mapping defect recorded
  in R001-A; the symmetric boundary-only v1.1 repair passed renewed review.

## Runs

| Run ID | Purpose | Execution | Retrieval | Receipt |
|---|---|---|---|---|
| S02-E004-R001-A | construct Round A under v1 | failed | pending | [S02-E004-R001-A.md](S02-E004-R001-A.md) |
| S02-E004-R002-A | construct Round A under v1.1 | failed | pending | [S02-E004-R002-A.md](S02-E004-R002-A.md) |
| S02-E004-R003-A | construct and complete Round A under v1.2 | prepared | pending | pending |
| S02-E004-R003-B | release and complete Round B after 24 h | prepared | pending | pending |

## Evidence review

Pending completed annotations.

## Scientific verdict

Pending.

## Claim impact

Pending. This pilot cannot change the S02-E003 forecast verdict.

## Next action

Complete v1.2 code review, bind the packet builder to a commit, then execute R003-A
once. Complete Round A before exposing Round B.
