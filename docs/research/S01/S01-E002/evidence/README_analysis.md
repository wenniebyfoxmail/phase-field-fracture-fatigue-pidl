# Analysis: S01-E002

## Scientific question

Does native-scale tiled proposal generation improve PaveTrack crack
localisation over the frozen full-frame route at one false positive per image,
and if the claim gate fails, which component now limits performance?

## Evidence identity

- Experiment: S01-E002, frozen protocol v1 at commit `b347bc3`.
- Runs: R001 execution failure before data preparation; R002 successful.
- Reference/comparator: frozen S01-E001-R008 full-frame proposer and hard-negative
  reranker.
- Analysis script: `scripts/pavetrack_tiled_cv/render_e002_evidence.py`.
- Scored source: retrieved `evaluation_test.json`, SHA-256
  `9e66d858487610f0a29b715d57a735556885da2e3fab66f40884b9920e0b7f7a`.
- Available fields: targets, baseline and tiled proposals, frozen proposal and
  reranker scores, per-location operating recall and oracle coverage.
- Missing fields: no independent field measurement of crack state and no
  evidence for temporal identity, mechanics, future prediction or transfer.

## Reading order

1. Start with `F01_decision.png` for the frozen primary and coverage gates.
2. Inspect `F02_error_montage.png` for deterministic examples of admitted false
   positives, recovered true positives and covered targets below the budget.
3. Use `location_metrics.csv` and `summary.json` for exact values and the case
   selection receipt.

## Figure guide

### F01 — Operating recall, oracle coverage and frozen gates

- Look for: the separation between operating recall and candidate-set oracle
  recall, especially at locations 577 and 956.
- Main numerical takeaway: primary delta +0.069892 fails +0.10; oracle delta
  +0.339449 passes +0.20.
- Supports: tiling materially repairs candidate coverage.
- Does not support: the full tiled-plus-frozen-reranker route meeting its v1
  claim or being ready for SAM2.

### F02 — Deterministic error montage

- Selection rule: the highest-scoring false positive from each zero-target
  location; the two highest-scoring true positives recovered over baseline from
  distinct locations; and the highest-scoring target-covering proposal below
  threshold from locations 577 and 220.
- Look for: road-marking and texture false positives competing with thin crack
  candidates for the fixed budget.
- Main numerical takeaway: valid crack proposals can lie immediately below the
  global threshold while visually plausible road texture receives higher scores.
- Supports: ranking and calibration are the next actionable bottleneck.
- Does not support: a unique causal attribution to reranker domain shift.

## Cross-figure interpretation

The figures agree that proposal availability and proposal ordering have
separated. The tiled model makes many more target-overlapping candidates
available, but the frozen full-frame-trained scoring route converts only 29.9%
of oracle coverage into operating recall. The baseline converts 41.5%. The
montage shows concrete errors consistent with this gap, while remaining
agnostic about whether retraining, calibration or visual ambiguity is causal.

## Gate result

- Validity gates: pass.
- Primary gate: fail, +0.069892 < +0.10.
- Decision visualization and displayed-case selection rule: present above.
- Secondary diagnostic: coverage gate passes, +0.339449 >= +0.20.
- Verdict: negative for the bounded v1 claim, with successful coverage repair.

## Allowed conclusion

Native-scale tiling materially improves candidate coverage on this fixed
PaveTrack holdout, but the frozen ranking route does not turn enough of that
coverage into detections at one false positive per image.

## Blocked conclusion

Do not claim general PaveTrack localisation validity, lower the v1 threshold,
tune on the consumed locations, invoke SAM2, or infer temporal crack growth,
mechanics or cross-network transfer.

## Storyline impact and next action

The S01 localisation bottleneck moves from proposal coverage to fixed-budget
ranking. Freeze the tiled proposer and test one tile-native hard-negative ranker
in a new experiment with a reviewed +0.05 practical-improvement gate and fresh
reserve locations.
