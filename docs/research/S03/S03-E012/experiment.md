---
storyline_id: S03
experiment_id: S03-E012
protocol_revision: v1
status: code_review_pending
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
