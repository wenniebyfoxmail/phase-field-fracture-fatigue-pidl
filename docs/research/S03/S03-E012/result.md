# Minimal cycle-to-recorded-cracklength pilot: completed

## Semantics and grouping

The released dictionary defines cycles as load-cycle count and cracklength as
projected length calculated from DCPD via Johnson's formula. The pilot predicts
this recorded label in native controller units, not calibrated true geometry.
A scalar-to-mm mapping and unique specimen serial remain unverified.

All 342 admitted stages form 114 exact-cycle groups, each containing three
stages with exactly equal cracklength. All groups have three distinct recorded
force values in increasing stage order. They are different recorded loading
states, not independent fatigue histories. No tied labels were averaged or
inconsistent groups excluded. Full stage/group lineage is retained.

## Frozen temporal split and comparison

The first 68 groups are the early/train segment (66 scored transitions after
two warmup groups), followed by 23 development and 23 holdout target groups.
No cycle tie group crosses a split. No parameter fitting occurs in any segment.
Rolling one-step predictors use observed previous groups; later holdout origins
may use earlier holdout labels after observation. The next recorded cycle gap
is explicit offline conditioning information.

| Split | Scored transitions | Persistence MAE | Secant MAE | Secant/persistence MAE |
| --- | ---: | ---: | ---: | ---: |
| Early/train | 66 | 0.5366591 | 0.0839634 | 0.1564558 |
| Development | 23 | 0.5304325 | 0.0462540 | 0.0872006 |
| Holdout | 23 | 0.5308750 | 0.0669012 | 0.1260207 |

Holdout RMSE is 0.5407648 for persistence and 0.0922486 for secant. All errors
are in native recorded cracklength units. Holdout MAE is approximately 87.4%
lower for secant. This table rounds the authoritative Decimal metrics.

This completes the requested minimum scalar experiment. The descriptive gain
is conditional on recorded gaps in growth-triggered acquisition; it does not
establish prospective fixed-horizon skill, calibrated true-geometry error,
material/phase-field identification or independent-specimen/road validity.

## Evidence and next lever

Run: S03-E012-R001; reviewed/executed commit
`27664c5700db53dc50989a96b37f29b0506dd76c`. Both mode receipts report success
and clean status. A local independent preparation check preceded evaluation;
a separate Fraction/Decimal recomputation checked all predictions and metrics.
The PNG was visually inspected, then independently checked against its CSV.
External review returned `PASS_EVIDENCE_REVIEW` on 2026-10-12.

Evidence root:
`local_archive/experiments/S03-E012/runs/S03-E012-R001/`.
Prepare: stages.csv, groups.json, split_manifest.json, preparation_lock.json,
execution_receipt.json. Evaluate: predictions.csv, metrics.json, PNG/PDF,
README_analysis.md and receipt. `evidence_review.md` records exact bindings.

The next smallest comparator should distinguish the acquisition-triggered
increment prior from added cycle-history information: freeze a past-only
increment baseline in a separate experiment. Prospective fixed-cycle targets
require appropriate labels, not silent interpolation of this sparse archive.
The same-cycle three-load observations are retained as a useful later DIC-to-
mechanics axis, but spatial registration and inverse identifiability remain
separate work. No extra model arm was added after this pilot's scores.
