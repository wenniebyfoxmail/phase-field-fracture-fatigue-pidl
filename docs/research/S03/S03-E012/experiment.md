---
storyline_id: S03
experiment_id: S03-E012
protocol_revision: v1
status: executed_evidence_review_pending
scientific_verdict: pending
---

# Minimal cycle-to-recorded-cracklength baseline pilot

Scope: controlled experiment, one released archive sequence; retrospective
conditional-gap prediction diagnostic. No trained model, physical material fit,
independent-specimen generalisation or prospective scheduling claim.

## Semantics and boundaries

Released timestep dictionary defines cycles as load cycles and cracklength as
projected length calculated from DCPD via Johnson's formula. Relative stage date
is elapsed acquisition time; time is described as a relative Unix timestamp.
Local first-stage metadata identifies Al2024-T3, L-T, MTS-PCQ0010. The released
description and original paper identify an MT160 AA2024-T3 experiment under
4.5--15 kN cyclic loading. A unique specimen serial is not yet established.
Paper: https://www.nature.com/articles/s41598-024-63915-x ; archived Zenodo
record: 11945905. Publication length context is mm, but serialized header scalar
units are not explicit. Use native controller cracklength units without conversion
or claiming metrological calibration. Forecast the recorded label, not a
validated true crack geometry or phase-field quantity.

Acquisition was crack-extension-triggered in the release description. The next
recorded cycle gap can therefore depend on growth. The pilot conditions on that
realized gap, which is available offline, not necessarily prospectively. Its
scores must not be presented as forecasts at predetermined cycle horizons,
inspection-policy utility or field deployment accuracy.

## Evidence and preparation

Same locked ZIP: 1,248,078,255 bytes; MD5 e671b804e29401e70043bc1e17f66dd1.
Reuse unchanged E011 parser, SHA256
757abe52c52d38538c92fd2dc33c3e6f142463eb2015910506954058afb86ce3.
Preparation reruns reviewed structural admission, then exports only seven
scalar fields from bounded headers. Budget at most two bounded reads/header;
no numerical DIC rows or connection bodies. One fresh prepare directory.

Group contiguous equal exact Decimal cycles. Within a tie require exactly equal
cracklength; otherwise stop, no averaging/exclusion. Retain all stage IDs and
latest acquisition date, treating origin as after that entire group's acquisition.
Group size is observed, not assumed from 342/114. Require at least ten groups.
Bind stages/groups/summary/split by a preparation lock; evaluate in a separate
fresh directory only after preparation consistency is verified.

## Frozen split and predictors, before export or scoring

Let G be group count. Split by target group index: train j<floor(.6G), dev
floor(.6G)<=j<floor(.8G), holdout thereafter. First two groups are secant warmup.
No tie group is divided across partitions. Transitions whose target enters a
new partition may use prior-group history from the preceding partition, as
available at the origin. Rolling one-step: earlier held-out readings may enter
later origins after they have been observed. No model fit or tuning occurs.

Target a_j at next strictly greater cycle N_j. Origin is group j-1. Allowed
inputs: last two admitted observations and recorded next cycle gap. No future
cracklength or field data in the predictors.
Persistence: a_hat=a_(j-1).
Secant: a_hat=a_(j-1)+(a_(j-1)-a_(j-2))*(N_j-N_(j-1))/(N_(j-1)-N_(j-2)).
No clipping, smoothing, monotonicity constraint or parameter selection.

## Criteria, evidence and repair

Primary descriptive metric: chronological holdout MAE ratio secant/persistence;
undefined if persistence MAE is zero. Report MAE/RMSE and counts per split,
exact predictions and horizon gaps. Pipeline completion is a C0 outcome;
baseline comparison is diagnostic performance on recorded labels, not validated
scientific superiority or uncertainty coverage. No performance acceptance
threshold is selected from observed scores. All other consistency/label/noise
requirements remain explicit limitations.

Preparation failure -> repair identity/grouping/semantics before scoring.
Successful pipeline -> retain grouping, coverage and scores even if secant loses;
select the next lever from gap distribution, label variation and baseline errors.
No extra model arm after observing results in this experiment.

Minimum evidence: stage table, exact groups and split, locked preparation,
predictions, metrics, both mode receipts, all-holdout target/prediction/error
figure with native units and conditional-gap label, visual QA, README_analysis,
independent evidence review and Storyline impact. Plot is generated from the
exact predictions CSV, with all chronological holdout targets, no chosen example.

Root: local_archive/experiments/S03-E012/runs/S03-E012-R001/prepare and evaluate.
No real E012 export or score has yet occurred.

## Numerical and lineage implementation clarification

Authoritative metrics are Decimal strings, not float JSON values. Working
precision covers twice the input decimal span plus 64 guard digits (minimum 50), with
an 8,192-digit arithmetic budget and adjusted exponent magnitude <=10,000.
Inputs outside this numerical capability fail; no success score is returned.
Prediction precision is chosen per origin from n0, n1, permitted target cycle
and the two past labels only. Current/future target labels cannot choose its
precision or representation. Target labels enter only subsequent error scoring.
Plots use floating representation only; nonfinite or nonzero-to-zero conversion
blocks figure completion while exact CSV/metric artifacts remain diagnostic.
Evaluation binds the preparation lock and every prepared artifact to the
successful preparation receipt and the unchanged runner/dependency identity.

## Code review history

Snapshot `3dc801869d3d7739f0877349c953df332a71bc36` received `REVISE_CODE`:
fixed 50-digit predictions lost increments for large precise labels, and float
loss arithmetic could turn nonzero errors or their squares into zero. The
revision implements the checked precision/domain policy above, exact-string
Decimal metrics and explicit plot representability failure. Full-mode synthetic
regressions cover labels 10^60+i, i^2*10^-400 and ordinary linear data; the
subfloat case preserves correct CSV/metrics and records figure completion
failure, not a successful pilot. A separate test checks RMSE of 10^-200 errors.
The real archive has not been prepared or scored.

Snapshot `9444f3b33ce650e7f38f54345381742eb24a0d9e` received `REVISE_CODE`
for intermediate cancellation and whole-sequence precision depending on future
labels. The revision uses twice-span guard precision per permitted origin input
set, fixes the prediction before target-based scoring, and adds complete-mode
regression B=10^100 with prediction 1e-100 plus later-label perturbation invariance.
The archived preparation tables remain uncreated pending renewed Code Ready.

## Actual pilot execution

Commit `27664c5700db53dc50989a96b37f29b0506dd76c` received `PASS_CODE_READY`.
Prepare mode succeeded at 2026-10-11T23:17:14Z (2026-10-12 local London date):
342 stages, 114 exact-cycle groups, exactly three stages/group and equal tied
labels. A separate read-only CSV/groupby, split and receipt/hash verification
passed before evaluate mode started at 2026-10-11T23:18:29Z.
Both mode receipts record the exact code identity and clean status.

Frozen early/dev/holdout target counts are 66/23/23, after two warmup groups.
Holdout native-unit MAE: persistence 0.5308750371, secant 0.0669012318;
MAE ratio 0.1260206774. Holdout RMSE: 0.5407647533 and 0.0922485740.
The complete figure and exact predictions exist and were visually inspected.
No model was trained or selected from these scores. Evidence review remains
pending; these are producer results for the bounded conditional-gap diagnostic.
