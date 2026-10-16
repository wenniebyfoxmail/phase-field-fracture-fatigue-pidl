# S03-E026-D01 — Beam4 last-query T1 error decomposition

2026-10-16 Europe/London; Storyline S03; protocol `T1-local-audit-v1`.
C1 diagnostic / controlled-experiment, posthoc viewed-development case.
Base20fbedd87f895abab05c6b1b9271cde29775e143; matching clean worktree
codex/crackmnist-tokenizer-mvp. User authorises local existing-profile/raw-image
comparison and Obsidian sync. No new model, source acquisition or old-score edit.

## Question, units and fixed scope

Explain the large B4-K2-Q50/T1 software-observable error: is the optical
30->40->50kN reversal reproducible and locally position-stable, or sensitive
to measurement support/correspondence? This cannot alone identify material
opening reversal, physical loading causation or the true local displacement.
Keep E015 half-depth definition: single fixed transect, median5 gray lines,
native first-frame pixels, shoulders|s|45..60, peak search|s|<=15, same QC.
Read only T1 stages1/2/3 of E020 cached profiles/deficits/strips and original
source photographs. Use E018 sanitised Beam4 geometry/H and E019 frozen FIT
translations plus CHECK records. No new registration or template matching.
Original_H is primary; background_aligned is an existing proxy counterfactual,
not accepted ground truth or a new preferred measurement. T1 CHECKa5 remains
excluded by first-frame screen, at most3/4 available; never fit using CHECK.

## Fixed diagnostic and comparator

Recompute unchanged half-depth from6 zero-position cached profiles, and all54
profiles (2arms×3stages×9 tangential offsets -2..2/.5). Check widths/edges/peak/
depth and deficits against existing E020 table/cache within1e-8px/gray (software
consistency tolerance, not physical precision). Stop on identity/validity/cache
mismatch. If any selected profile invalid, retain missingness; do not impute or
expand range. Source E020 code84c34422d52c7ff3f062add41a7bfe7537935861;
source E019 codeac56fdb6348f4cb3636271cee6b10e9cc5bb3212. E025 preserved.

Primary diagnostic: exact e_secant = d_history - d_next for equal10kN steps,
where d_history=w40-w30, d_next=w50-w40, before unchanged clip[0,120].
Show persistence w40 and secant2*w40-w30 versus w50; if clipping occurs report
both raw decomposition and mapped error. No new performance pass/fail cutoff:
this was selected after E025, so report effect sizes and finite-grid support,
not a statistical success. Visible dark edges and physical opening are not
alternative reference labels for this half-depth functional.

Position counterfactuals: same nominal t across3stages (9 per arm), versus
independent t30/t40/t50 (9^3=729 per arm). Report valid/total denominators,
all errors and sign-change counts, min/max; not confidence intervals or
independent observations. Never select offsets to reduce the old score.
No interpolation or continuous tolerance guarantee, no claim actual errors
fall within±2. Stage-zero bands describe connected half-depth intervals only;
disjoint/split/merge flags or their absence do not certify physical edges.

## Outcome map, budget and evidence

If cached measurement fails -> diagnose source/definition before interpretation.
If original reversal disappears with existing proxy alignment or allowable
counterfactuals -> corresponding limitation is position sensitivity, not proven
actual registration error. If reversal persists throughout tested combinations
-> reproducible, grid-robust optical trend reversal; causal/physical attribution
still unresolved. If interval/peak/depth changes accompany the width -> describe
measurement mechanism candidates using profiles/raw context, not physical proof.
Mixed findings select one smallest follow-up, not a new model or deleting T1.

One lightweight Mac numeric extraction/decomposition,60s wall/CPU budget,
freshS03-E026-D01-R001; rendererR002 from saved outputs plus three CRC-verified
existing JPEGs. Independent code review and synthetic checks before Run;
independent table/figure review afterward. Receipts record clean code, host/PID,
command/time/paths; no GPU/network. Old archives are read-only.

Figures, all named stages/no cherry picking:
1. Native pixel crops with original/aligned sampling locations, same display
   dimensions and gray0..255; plus cached registered raw-photo-derived strips
   (not untouched native pixels), same local coordinates/gray limits.
2. Median gray/deficit profiles and selected half-depth crossings for all3stages,
   original plus existing alignment; same axes/limits, no added smoothing.
3. Fixed-grid width and change/error response, both arms on shared scales.
4. Last-query trajectory/persistence/secant and all deterministic common/
   independent position errors, paired with exact algebraic decomposition.
README_analysis,54 measurement rows,4 stage-pair rows,1476 position rows,
corrections/CHECK support, selected cached arrays, summary and independent review.
No separate physical metrology verdict; case selected posthoc and remains development.

Registration status: prepared; no diagnostic executed at registration.
