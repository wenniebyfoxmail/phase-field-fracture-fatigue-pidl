# E035 independent review — 2026-10-17

Reviewer: independent team agent `/root/md01_early_review`. Read-only with
respect to production code, source data, E034 records and E035 R001 outputs.
Only this R004 review directory was written. No new photographs, fitting,
profile selection, additional offsets, training or other agents.

## Decision

No numerical or visual blocker. The complete frozen finite sets retain the
trend-vs-persistence advantage. This supports the bounded retrospective
position-sensitivity finding, not new forecasting validation or physical width
accuracy. Original E034 nominal scores remain the reported scores.

## Reproduction and numerical verification

Reproduce using:

```sh
cd /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp
/Users/wenxiaofang/miniconda3/bin/python3 /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E035-MD01/runs/S03-E035-MD01-R004/independent_check.py
```

The script refuses to overwrite its `independent_results.json`; preserve the
existing result or copy the script to another explicitly authorised fresh
review directory for a rerun. The result includes all 83 reconstructed profile
widths/crossings, all 50 independently calculated case scores and secondaries,
input/source/protected hashes, and summary checks. It imports only the separate
independent sampler and half-depth implementation, not the E035 measurement,
sampling or prediction functions.

- Admission bound to clean `9a60e9a`; R001 ran at clean `19ed022`, whose numerical
  runner and frozen lock are unchanged from the admitted snapshot.
- Background residuals and normal/tangent supports independently reconstructed
  from E034 saved registrations: normal 13.62730920890204 px; tangent
  1.9526942838456711 px. Every case's stage/offset association was checked.
- Actual unique profiles: 83, comprising 25/29/29 for stages 24/25/26; 83 valid.
  Independent family fixes stage24, independently varies only stages25/26.
- All three original files match cached official SHA256 and byte counts.
- Manual, quantised bilinear sampling from original source pixels reproduces
  all saved profiles exactly. Independent half-depth processing reproduces
  backgrounds, deficits, both crossings and widths exactly.
- All 50 forecasts, absolute errors, signed primary differences and all saved
  secondary changes reproduce exactly. Maximum absolute difference across
  every above check is **0**.
- Nominal profiles/backgrounds/deficits equal E034 arrays; nominal widths and
  scores reproduce the original E034 values, including delta
  -10.658018303487928 px.

| Fixed family | Cases valid / intended | Trend better | Ties / reversals / missing | Delta range, px |
|---|---:|---:|---:|---|
| Common three-stage offset | 25 / 25 | 25 | 0 / 0 / 0 | -12.118959811438124 to -7.033799185098445 |
| Independent later-stage offsets; stage24 fixed | 25 / 25 | 25 | 0 / 0 / 0 | -10.971547768488215 to -10.584100666521614 |

## Why the independent map has repeated rows

Every independent case satisfies target width > trend prediction > persistence
prediction. Hence delta = (target-trend)-(target-persistence) =
-(w25-w24), because neither predictor clips in these cases. Changing only target
position cancels out of this paired difference. This identity was verified
with maximum difference 0.

This does **not** make target width, target location or absolute error invariant.
Independent-family trend absolute error ranges from 0.8528418371833482 to
3.2267923944564174 px. The common family has four trend overshoots and its delta
has a wider range. A repeated delta row must not be presented as proof of
target-position accuracy or general position insensitivity.

## Old-byte protection: what was actually verified

The admitted producer compares nine old payload byte strings before and after
its run and reports success. During this independent review, all nine current
payload hashes remained unchanged. Five of these current files also exactly
match their independently retained, committed pre-E035 E034 evidence copies:
both history JSONs, target measurement JSON, final summary JSON and original v1
summary JSON. The two E034 nominal profile archives are additionally checked
array-for-array against E035 nominal samples.

The five JSON comparisons were also verified directly against `git show`
blobs from pre-E035 commit `e4401dc56d2d7a34b8d9d422e9f0c6fb42cca9ea`,
not only against current working-tree copies.

The reviewer did not separately witness the producer's pre-run filesystem
bytes for all nine files; do not call this an independent historical
filesystem attestation. Original v1 E034 R002 still records E=false; it is not
replaced by the v1.1 sensitivity result. Exact paths/hashes are in the JSON.

## Figure review

R003/analysis F01, F02, F03 colour and F02 grayscale were visually inspected.
No blocker: the two complete 5x5 matrices show negative-is-better with shared
signed colour limits and original-position outlines; all-point comparator
plots include equal-error and zero references; the original/source-support
view preserves native scale, fixed stage24 independent support, all anchor
alternatives and the background-transfer caveat. Run ID, development role,
origin/target, units and single-record/non-probability scope are visible.

The renderer reads saved numerical arrays and does not remeasure, align, rank
or choose offsets. No visual threshold adds a new scientific acceptance rule.

The final R003 `README_analysis.md` and F01 same-stem sidecar were also checked:
source/stage labels, all counts/ranges, target cancellation, the non-invariant
absolute errors and the finite/target-informed/background-transfer limitations
are accurately stated. The proposal for fixed small-batch stage windows is
explicitly future, not an execution or new source-access claim.

## Scientific boundary and useful next action

Fifty settings belong to one already-viewed controlled-experiment case, not
fifty independent observations. Target backgrounds inform the retrospective
stress set; they are not origin-time forecasting inputs. Supports and anchor
residuals are observed displacement disagreements, not calibrated error bounds,
confidence intervals or continuous robustness guarantees. Transferring these
background differences to the crack remains an explicit assumption.

The finite-set result is positive component progress: the original advantage
is not confined to the nominal point. Any further work should preserve the
original score and frozen definition, then separately test the remaining
position-correspondence assumptions or a new approved case. Do not select a
low-error position from this stress set or infer physical crack accuracy.
