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

## 2026-10-16 diagnostic result

Execution succeeded, local retrieval verified, independent11-test code review
and independent numerical evidence review complete. Original cached54 profiles
reproduce exactly; all valid and single bounded half-depth component.1476
counterfactual rows/4stage-pair rows independently rebuilt with maxdifference0.
R001 code991e5b0, wall.051481s CPU.042149s. Old scores and measurement unchanged.

At original t0, widths15.2524483 ->11.5099414 ->13.8340226px. Preceding
change-3.7425069 versus next change+2.3240812; secant signed error-6.0665881px
is exactly their difference, no clipping. Persistence signed error-2.3240812.
Width change is dominated by right half-depth crossing (-4.1336429 then
+3.1157177px), compared with left (-.3911360 then+.7916365px). Half-level
changes+.819608 then+.007261gray. No disjoint/split/merge stage indicator;
that does not identify a physical boundary or prove continuously correct edges.

Using existing FIT proxy sampling locations, widths16.3829098 ->16.1419709
->16.7876582px, secant error-.8866261; original~6.07px miss is therefore
strongly sample-location dependent, not safely explained as physical reversal.
This correction includes n and t shifts and remains unqualified at the crack.
T1 has3/4CHECK per stage (a5 first-frame excluded); background-to-crack transfer
has not been independently demonstrated.

Within common t±2 grid, original9/9 down-up, secant errors[-6.455148,-.709768].
Independent three-stage offsets:351/729 down-up and errors[-18.049038,+15.230186].
Aligned common5/9 and independent254/729; independent error range
[-17.660786,+17.771374]. All tested points valid, no clipping. These are
deterministic sensitivity combinations, not probabilities/independent specimens
or proof actual registration errors lie inside this grid.

Visual context: all three native crops put T1 near a bend/junction-like dark
band, and the raw-photo-derived strips show rapid width variation along t.
This is an image-context observation, not a new crack topology/physical label.
Existing alignment reduces the stage separation of the local response curves;
it does not certify a repaired physical-coordinate measurement.

Verdict: descriptive optical turn and position sensitivity supported; physical
attribution remains inconclusive. Disposition: repair local correspondence
qualification, not escalate temporal architecture or delete a viewed case.
Next smallest proposal: independently check stable near-crack background
correspondences around T1 and whether FIT translation transfers locally to the
sampling band, including both normal/tangent components; keep scoring and
operator fixed. Not executed, no new forecast score claimed.

Figures: R002 (7e4fea5) retained/superseded for bottom legend overlap; R003
(473cedd) only spacing and reading-guide repair, same numeric R001. Four figure
sets (PNG/PDF/grayscale) and README:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E026-D01/runs/S03-E026-D01-R003/analysis/README_analysis.md`.
Profile EDA before rendering:54rows×15fields, six arm/stage groups each9,
no missing fields; use all fixed-grid points rather than average-only summaries.
Final independent four-colour-figure/F04-grayscale and reading-guide review
complete, no blockers. R003 wall3.483624s CPU3.460569s; no numeric rerun.
All4colour PNGs strict300dpi checks pass, layout issues empty; owner and
reviewer actually opened final images. Diagnostic evidence complete; physical
attribution unresolved and proposed correspondence validation not executed.
