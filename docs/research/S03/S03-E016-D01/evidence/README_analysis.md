# E016-D01 — boundary, location and repeat-view checks

2026-10-13. S03-E016-D01-R002; protocol development-v1; CPU offline
controlled-laboratory diagnostic. Independent reference status is PENDING.
User confirmed no human labels; public blind packet exists, zero annotations.
No Code/Evidence Ready, physical measurement or held-out forecasting claim.

## Question / source / exact outputs

Does the E015 fixed-camera image-width signal survive a distinct edge
definition and small location shifts? How much does repeat-view observation
variation obscure it? Reuse D01 Mendeley v4 DOI 10.17632/z3yc9z84tk.4, 14
fixed frames plus 18 moving frames = 32 unique state images. Source paths in
`repeatview_measurements.csv` and E012 acquisition receipt. CRC/size checked.
No new data, registration refit, physical calibration or model training.

Code `9aaa0de690eb662fafb946e61212e1aeea0ef52b`; R002 runtime 7.02 s.
R001 at `3a24a20968cca50b03e30c8ebda772dc72cfa788` stopped before results
because separated NumPy indexing transposed the 2x12 historical array. It is
preserved with failed receipt. The fix restores axis order, adds a regression
check and failure receipt handling, and uses fresh R002; no protocol changes.

`edge_method_agreement.csv` (168), `location_variants.csv` (840),
`repeatview_measurements.csv` (288), `variant_forecast_metrics.csv` (120),
`Beam*_checks.npz` and `summary.json` are authoritative. Centered replay is
numerically identical to E015 widths (tolerance 1e-7 px). Traces and variants
are not independent beams; no CI or population claim is inferred from them.

## Reading order / what the figures show

1. `edge_on_image_comparison_v2.png`: first/last fixed-stage pixels, rotated
   into transect coordinates, ID 6 in every beam (rule frozen before scoring).
   Blue marks saved half-depth crossings; orange dashed marks alternate
   gradient boundaries. Both are estimates of the CENTRAL sampled band, not
   traces along the full crack. Quantized gray display, no edge refitting.
   V1 is a preserved superseded layout with overlapping labels; use V2.
2. `edge_operator_comparison.png`: same six fixed examples, raw gray profiles
   and both boundary definitions; same axes. Gradient operator smooths sigma=1
   native pixel for derivatives, never consumes E015 edges/widths. Both share
   guided locations and grayscale, so this is method agreement, not truth.
3. `location_growth_comparison.png`: all stages, five coherent frozen center
   variants (centered, tangent +/-2, normal +/-2 native pixels). Shared 0..40
   px width axis. Shows stability of aggregate growth, not individual edges.
4. `variant_forecast_comparison.png`: exact equal-beam MAEs for ALL variants
   and same persistence/secant/half-secant rules. Every variant scored 96/96
   pair-transects. No variant chosen as the "best" replacement for E015.
5. `repeatview_width_comparison.png`: ALL supported moving-vs-fixed pairs,
   blue low / orange high nominal stops. Shared 0..60 px axes and identity
   line. Missing observations remain missing. See coverage below; this figure
   does not establish pure acquisition error or physical unchanged-state truth.

## Descriptive findings

| Beam | Median absolute width difference, gradient vs half-depth | Moving-fixed median absolute difference | Valid repeat-view widths | Common all-four-view stop-transects |
|---|---:|---:|---:|---:|
| 4 | 0.767 px | 4.904 px | 72/96 | 12/24 |
| 5 | 0.240 px | 2.151 px | 96/96 | 24/24 |
| 6 | 0.493 px | 3.304 px | 96/96 | 24/24 |

Alternate operator detects 168/168 profiles under its frozen diagnostic rule;
this is coverage, not accuracy. Median absolute boundary-location differences
are 0.383/0.158/0.279 pixels; width disagreement p90 2.248/0.465/0.717.
There is no independent reference that converts these into metrology errors.

All coherent shifts preserve POSITIVE first-to-last median growth:
Beam 4 2.875..3.127, Beam 5 3.752..4.381, Beam 6 2.517..2.774 pixels.
Allowing first and last displacement variants to differ gives conservative
aggregate-growth envelopes 1.814/3.752/1.361 pixels, still positive within this
specific displacement set. This is not a distribution-free uncertainty bound.
Full pixel-shift sensitivity and edge irregularity remain; stage-wise growth
need not be monotonic in every variant or individual transect.

Secant equal-beam MAE is below persistence in ALL five variants, relative
reductions 50.350..69.835%; centered is unchanged at 52.408%. Do NOT select
tangent-minus2's 69.835% as a new accuracy headline. These are native image
observable losses with full matched-arm support, not absolute physical errors.

Real repeat-view observations: 264/288 widths valid. All 24 missing are Beam 4
outside-source support (moving1:12, moving2:8, moving3:4 across both stops).
Moving-vs-fixed paired widths 192/216; no zero filling. Difference p90 is
8.990/4.171/7.056 px. Existing first-reference registration routes give fixed
width median discrepancies only 0.0105/0.0012/0.0008 px, with p90 <=0.264.
Therefore simply swapping the stored global registration route does not
explain the much larger cross-camera discrepancy. Do not uniquely attribute
the discrepancy to a specific physical cause: resolution, pose, visibility,
local correspondence, camera observation and possible within-hold change are
confounded. Low/high groups are nominal load stops, not hard-synchronised
constant-state repeat acquisitions.

## Independent-reference status and blind packet

`blind_packet/index.html` is a standalone offline page, no external requests.
24 unique first/last tasks (IDs 3,6,9,12 in each beam), six hidden duplicates,
30 anonymous views; fixed shuffle seed 1613. No stage, beam, algorithm widths,
boundary suggestions or key in public packet. `private_blind_key.json` is
LOCAL ONLY, outside public folder and excluded from Git/handoff to annotators.

Annotator records visible dark-region boundaries and plausible ranges on the
central row, flags ambiguous branches/spall/shadow/occlusion, and reports prior
algorithm exposure. Duplicate agreement can later estimate intra-annotator
repeatability; different annotators are needed for inter-annotator agreement.
Central-row visible boundaries are not automatically identical to half-depth
of a five-line median profile; that observation-model distinction must remain
explicit in later comparisons. Sampled image grids are not physical mm truth.

Status: packet ready, independent annotator NOT assigned, 0 completed. A
finished packet is not an independent boundary-validation result. Human labels
must be returned and reviewed before reference-error scoring or a metrology
claim. UI JS syntax/tasks/leakage checks passed; desktop-browser interactions
were not live-tested, so do not call the full interface visually QA-passed.

## Allowed conclusion / blocked conclusion / next step

Allowed: E015's fixed-camera aggregate growth and history-baseline advantage
are not erased by the tested small location changes; distinct edge definitions
usually agree descriptively. Preserve that positive component finding. Real
repeat views have substantially greater spread, so keep fixed-camera state
trajectories separate from moving-view width estimates for now.

Blocked: independent edge truth validated; uncertainty calibrated; millimeter
width; all-camera fusion qualified; physical or road/fatigue forecasting;
held-out/generalisation success; a causal explanation of camera discrepancy.

Disposition: continue FIXED-camera diagnostic prediction; repair independent
reference and local camera correspondence. Next concrete action: a reviewer
who has not seen candidate boundary outputs completes the 30-view packet,
then assess duplicates, coverage and operator/reference discrepancy. Do not
expand temporal models or treat repeat cameras as extra time steps.

Visual QA: inspected five primary figures; no missing six-example panels or
flipped normal axes; identical widths/forecast aggregates checked numerically.
V2 fixes V1 label overlap, and both boundary markers occupy the central band.
All old E015 findings/thresholds remain unchanged. Obsidian stores the concise
decision, repository/archive stores full evidence.
