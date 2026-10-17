# Mendeley full-data exploration: figure reading guide

Question: can additional published displacement groups support reproducible crack-span measurements? Domain: controlled laboratory DIC; stage: exploration C1/C2, not a forecasting study. Sources: both complete, published-identity-checked archives at local_archive/open_data/mendeley_full_displacement_20261017, original156-row workbook and README.

Read in this order:

1. `candidate_field_overlays.png`: actual current PT fields at early/middle/late frames of both labelled codes plus one priority new code. Dashed vertical lines mark V1 projected support bounds, not qualified physical crack tips. Axes are PT pixels. Channel1 is consistent with uy-like fields, but the exact author coordinate/grid recipe is unqualified.
2. `candidate_trajectories_all19.png`: every group, V0 grey and V1 red, same pixel scale. Red bands show0.8/1/1.25 algorithm thresholds, not noise intervals. No temporal smoothing or forced monotonicity. Cycles come from filename/README and have unresolved export naming/phase semantics. Missing rows/tails remain missing.
3. `published_label_comparison.png`: all156 source reference rows across four separate sheets. The100/127 conversion and label-mm reading are provisional; differences are numeric agreement checks, not calibrated physical errors. Same DIC lineage prevents an independent-accuracy claim.
4. `priority_three_trajectories.png`: compact view of three simplest new edge-crack codes. Selection uses geometric simplicity, same conditions, clearer source naming and a bounded measurement diagnosis; it is not a selection on prediction performance. #2's28-stage PT tail is absent, not extrapolated.

All images live in the raw/output root; final selected priority and field-overlay PNGs are copied to the existing Obsidian task note. V0 and initial pre-chronological-summary files are retained separately. JSON/CSV outputs are authoritative, not interpolated chart readings.

Allowed: full source acquisition, measurable field discontinuities, candidate trajectory capability, a bounded rule repair and explicit source-quality gaps; advance to a small human repeat-measurement check. Blocked: physical metrology accuracy, independent specimen certification, online causality, historical predictive benefit, road transfer, or training readiness. OriginalE005 negative remains unchanged.

The packet contains25unique frames and5hidden repeats with a blank measurement template; it has not been annotated, sent or treated as ground truth. Four deterministic controls check smooth-field rejection, known synthetic jumps, missing-value handling and constant-shift invariance. They validate implementation behaviour, not physical calibration. No independent review of the new exploratory code is claimed.

Final material-only QA: all30images, source paths, item IDs and blank cells checked; operational measurement contract and remaining scale/Stage/length-definition gaps are in mendeley_measurement_handoff.md. Human annotation is explicitly pending. Figure sidecars point to the same outputs; no new computation, figure rendering, training or annotation was introduced by this QA.
