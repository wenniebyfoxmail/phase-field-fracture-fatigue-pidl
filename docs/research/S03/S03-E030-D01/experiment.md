# S03-E030-D01 — fixed background centre half-depth profile comparison

2026-10-16; S03; protocol `T1-fixed-background-sampling-v1`; base d4dd8cc.
C2 optical-measurement diagnostic, controlled-experiment/viewed-development.
User authorises saving the three E029 primary positions BEFORE width access,
then comparing 30/40/50kN T1 profiles, widths and remaining conditional-query
error. No new independent specimen, physical reference or forecast validation.

## Frozen decision and information

Use exactly [fixed_positions.json](fixed_positions.json): E029 all17 affine
centre n/t vectors at all3stages, additive to the original-H centre. The file
is saved before E030 opens any width/profile/image. Researcher has seen earlier
E026/E028 widths/errors; this is NOT blind selection. No LOO, flags-clear,
best-anchor, offset search, registration, fit or alternative correction.

Single descriptive question: how does this ONE background-only estimate change
the existing half-depth observable and the remaining signed T1 Q50 error
relative to oldFIT? Primary output is signed error change, with stage-width
decomposition. No physical/scientific pass threshold: report decrease, increase
or unavailable without calling the entire route a success/failure.

Three fixed arms: original_H=(0,0), oldFIT from E019, fixed_background from E029.
Exactly9profiles from3existing E012 CRC/size-verified JPEGs (B4 stage1/2/3).
Use E018 safe geometry/H, original normal/centre, offsets -60:0.25:60,
five parallel lines at tangent -2,-1,0,1,2 and median; unchanged 1/32float32
bilinear, shoulder medians |s|>=45, core peak |s|<=15, half-depth crossings,
depth/noise/resolution/censoring QC. Unit native first-frame px, not physical mm.
Do not change width definition, old scores, E025 interface or any earlier file.

Check primary position/source identity before any image or width access.
Reproduce both original_H and oldFIT3widths plus query values against E026
nominal results to1e-8px software tolerance before interpreting new differences.
Mismatch stops interpretation; no adjustment to force agreement.
Invalid new measurements retain null/reason; do not move to a valid neighbour.
Both baseline3/3 and new3/3 coverage are reported, no unsupported zero fill.

For each available3stage arm: supplied nominal Q50, rawsecant=2*w40-w30,
prediction=clip(rawsecant,0,120), error=prediction-w50; also persistence=w40.
These are diagnostic recomputations, not overwriting any original score.
Separate prediction change (history widths) from reference change (w50).
Against oldFIT, delta_error=-delta_w30+2*delta_w40-delta_w50+delta_clip;
keep all terms. Stage increments distinguish retained down/up trend from change
of apparent optical trend, not physical narrowing/reopening or proven causality.

## Execution and minimum evidence

One Mac lightweight CPU R001,60s wall/CPU cap,3existing JPEGs, noGPU/network.
No training, acquisition, sealed target access, eight-case replay or tuning.
Code synthetic tests and independent read-only admission before image sampling;
review exact commit/protocol/position lock and data paths. Record identity,
command/host/PID/runtime/source receipts, hashes for the fixed external input
snapshot and oldscore files; verify oldscore content unchanged after execution.

Save9profile records/arrays,9measurements with QC,3query summaries, exact
decomposition and input/source identities. R002 saved-output-only renderer:
(1) all3stage deficits/half-levels/crossings for all3arms;
(2) width trajectories and supplied-Q50 residual comparison;
(3) same-scale original-image local strips and fixed sampling-band overlays,
plus stage contributions. All examples fixedT1/all3stages, no error ranking.
PNG/PDF/grayscale, figure-set README and same-stem notes; programmatic and
actual visual QA. Independent evidence calculation/visual review before closure.

If residual decreases: retain this candidate for subsequent measurement checks,
not declare correct physical coordinates or improved generalisation. If stays
similar/increases: record that this stable background estimator does not remove
the local mismatch; do not replace it by an error-minimising alternative.
Either outcome next separates background-transfer validity from optical-trend
modelling; no new model or width-definition change automatically follows.

Obsidian: reuse one existing task note, route/result milestones and oneRoadmap
status; canonical S03 track then frontier/navigation. Registration: prepared;
fixed position file saved, no E030 width sampling yet.
