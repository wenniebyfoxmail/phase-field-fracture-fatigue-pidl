# Independent evidence review — S01-E002 — 2026-10-11

## Scope and identity

This read-only review covers the S01-E002-R001 failure receipt, the successful
S01-E002-R002 evidence package, the exact confirmatory evaluation and the
decision figures. It does not alter thresholds, score choice, candidate rows or
the consumed holdout.

- Reviewed protocol source: commit `b347bc3ff67dc16710a676e0f176e33c119f5911`.
- Evidence ZIP SHA-256:
  `1d17b5c717147c16430ee34a6dac03a67ed8fc34b2d8a451ffea665d954e5983`.
- ZIP integrity: pass; 18/18 declared members present.
- Confirmatory evaluation SHA-256:
  `9e66d858487610f0a29b715d57a735556885da2e3fab66f40884b9920e0b7f7a`.
- Authorization chronology: pass. Model, validation result and selected score
  were hash-bound before confirmatory acquisition.
- Stop rule: pass. One formal training and one authorized confirmatory
  evaluation; no confirmatory tuning found.

## Findings

No evidence-integrity blocker was found. R001 failed before data preparation
and generated no scientific result. R002 is admissible for the bounded frozen
claim. Recalculation from the retrieved evaluation confirms:

- operating macro recall 0.113710 -> 0.183602, delta +0.069892;
- oracle macro recall 0.273723 -> 0.613172, delta +0.339449;
- primary gate fail and coverage gate pass;
- repaired oracle-to-budget capture ratio 0.299 versus baseline 0.415.

The training CSV peaks at epoch 23 and shows collapse from epoch 25, including
non-finite validation losses. The evaluated `best.pt` is the earlier retained
checkpoint with the declared hash, so this does not make the confirmatory result
inadmissible. It is a material stability limitation for future reuse and a
reason to keep the proposer frozen while testing the ranking repair.

The deterministic montage is consistent with the numerical result: the tiled
route recovers real cracks, but road markings and road-surface texture consume
ranking budget while some target-covering proposals remain below threshold.
This localises an actionable bottleneck but does not by itself prove a specific
cause.

## Verdict

`PASS_EVIDENCE_READY__NEGATIVE_PRIMARY__COVERAGE_COMPONENT_RETAINED`

The scientific verdict remains negative for S01-E002-v1. The useful result is
preserved: native-scale coverage is no longer the sole bottleneck, and the next
experiment should target tile-native ranking with a fresh evidence boundary.
