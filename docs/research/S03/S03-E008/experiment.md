---
storyline_id: S03
experiment_id: S03-E008
protocol_revision: diagnostic-v1
status: development
started_at: 2026-10-11
primary_storyline: S03
---

# IB ruler crop failure audit and one-factor development repair

## Dataset-first observation

S03-E007's six fixed reference images have already been viewed. They are
development data in this experiment. Beam 6 ref2 visibly contains a long ruler,
whose upper edge appears above the frozen lower-half search region. The old
detector chose a lower line and estimated an 8 px period. The other five images
gave 15 or 19 px periods. The available signal therefore motivates testing the
crop before changing peak or fitting settings.

## Bounded purpose

C0 offline diagnostic, controlled-experiment domain: determine whether one
generic crop change repairs the observed detection bottleneck. Unit: image,
with images nested in three beams. No prediction origin or horizon applies.
Allowed inputs: the six released fixed ruler images and exact R001 CSV.
Target: reproducible indexed-peak coverage, not physical measurement accuracy.

Branch: `codex/crackmnist-tokenizer-mvp`; base:
`6b6713b820fd6ce7fd99877029ff28dfc760a3b1`.
Scope: this experiment's record, diagnostic script and development evidence.
Reuse the existing clean S03 worktree. S03-E007 runner and verdict are immutable.

## Predeclared comparison and budget

1. Reproduce S03-E007's baseline for all six images and check every original
   numerical field against the archived CSV before interpreting the repair.
2. Change only `BOTTOM_FRACTION` from `0.50` to `2/3`; leave line ranking,
   period range, peak settings, projective fit and the >=50 peak condition fixed.
3. Apply the same intervention to all six images once. Do not search fractions
   or add a second intervention in this diagnostic.
4. Inspect a ruler-band overlay for the failed case plus all-six coverage
   comparison and the failed case's autocorrelation before/after.

Engineering repair trigger: Beam 6 ref2 reaches >=50 indexed peaks while the
other five remain >=50 with finite monotone fits. This selects a candidate
for a new protocol; it cannot qualify millimetres or independent generalisation.
Internal LOMO errors are self-consistency diagnostics with detector-derived
indices, not independent physical-reference errors. An alias can fit well.

If the trigger misses, retain the measurements and choose the next lever from
the observed boundary/response decomposition; no automated retry or sweep.

## Evidence and next confirmation axis

Archive under `local_archive/experiments/S03-E008/runs/S03-E008-R001/`:
exact comparison CSV, response arrays, baseline-reproduction report, figures,
receipt, and analysis README. This is development diagnostic execution;
there is no formal claim-bearing run or independent Code/Evidence Ready PASS.

Inventory the released moving IB references from the existing ZIP manifest,
checking local presence without viewing or retrieving their pixels. Repeated
moving images of the same beams are a camera-transfer axis, not new independent
specimens. A future measurement claim needs known millimetre mark identities
and reference repeatability; unsafe-auto-report risk cannot be inferred from
tick counts or internal LOMO alone.

Scientific verdict: diagnostic only. Research disposition pending the one-factor
test. A formal selective-measurement protocol remains draft until its reference,
attainable threshold, non-empty coverage requirement and review are resolved.
