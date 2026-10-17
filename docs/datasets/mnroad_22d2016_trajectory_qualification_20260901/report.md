# MnROAD 22-D-2016 pre-intervention crack-trajectory qualification

Date: 2026-09-01  
Scope: non-wheel-path longitudinal cracking (NWP) in the Driving lane  
Status: `CONDITIONAL_GO_MANUAL_VECTORISATION_PILOT__NO_GO_MODEL_READY_TRAJECTORY`

## Decision

The public MnROAD material passes acquisition identity, maintenance censoring,
page completeness, and printed-grid registration for the pre-sealing period of
`22-D-2016`. It therefore supports a bounded manual-vectorisation pilot.

It does **not** yet qualify as a model-ready spatial-temporal crack trajectory.
Only one non-zero survey has a map-derived diagnostic comparison against the
summary workbook, and that comparison was not blind. The survey maps are
cumulative working sheets, later PDFs contain
marks from multiple survey dates, one map covers both Driving and Passing
lanes, and the required lane/colour/date conventions have not been confirmed by
MnROAD. No forecasting or PIDL/FEM training is authorised by this audit.

## Sources and identity lock

- Summary workbook:
  `/Users/wenxiaofang/Downloads/HMA Distress All export.xlsx`
  (`Export Worksheet`, rows 1482-1491 for `22-D-2016`).
- Survey manual:
  `/Users/wenxiaofang/Downloads/LTPP_DIM_052014.pdf`.
- Official portal:
  <https://infopave.fhwa.dot.gov/Mnroad/index>.
- Portal distress-map endpoint: `POST /MnROAD/getSurveyBar`, queried with
  `SECTION_ID=22-D-2016` on 2026-09-01.
- Intervention timeline endpoint: `POST /MnROAD/GetTimelineData`, queried on
  2026-09-01.

The eight downloaded public PDFs were used read-only from temporary storage.
Their filenames, sizes, and SHA-256 hashes are frozen in `evidence.json`.

## Qualification object

A legal natural-deterioration trajectory is defined as:

`Cell 22 -> Driving lane -> fixed 50-ft page/station -> survey date`,

terminated immediately before the first intervention capable of changing the
physical crack state or its observability.

The official timeline records crack sealing on 2019-10-24: "500 feet of
longitudinal crack seal, shoulder construction joint." The final eligible
pre-intervention observation is therefore 2019-10-23. No transition may cross
2019-10-24.

## Exact Excel-map chain

NWP length is the sum of low, moderate, and high NWP longitudinal-cracking
fields. Values are reported in the workbook's native unit; the maps and portal
timeline use feet, but MnROAD confirmation of workbook units remains required.

| Survey date | NWP low | NWP moderate | NWP high | NWP total | Public map | Eligibility |
|---|---:|---:|---:|---:|---|---|
| 2017-03-20 | 0 | 0 | 0 | 0 | yes | eligible |
| 2017-11-01 | - | - | - | - | yes | map-only; excluded from supervised transitions |
| 2018-03-14 | 0 | 0 | 0 | 0 | yes | eligible |
| 2018-04-27 | 0 | 45 | 0 | 45 | yes | eligible |
| 2018-08-23 | 5 | 45 | 0 | 50 | yes | eligible |
| 2019-03-22 | 267 | 45 | 0 | 312 | yes | eligible |
| 2019-04-16 | 378 | 45 | 0 | 423 | yes | eligible |
| 2019-10-23 | 379 | 45 | 0 | 424 | yes | eligible; final pre-sealing state |
| 2020-03-06 | 421 | 45 | 0 | 466 | no | post-intervention; excluded from natural chain |
| 2020-11-06 | 446 | 45 | 0 | 491 | no | post-intervention; excluded from natural chain |
| 2021-06-08 | 446 | 45 | 0 | 491 | no | post-intervention; excluded from natural chain |

The legal public chain has seven Excel-aligned states and six pre-intervention
intervals. The extra 2017-11-01 map cannot be used as a supervised state until
its missing summary record is recovered.

## Frozen gates and results

| Gate | Frozen requirement | Evidence | Result |
|---|---|---|---|
| G1 Identity and censoring | Same cell/lane/date key; no transition across first relevant intervention | Seven exact Excel-map dates; cutoff 2019-10-24 | PASS |
| G2 PDF completeness | Every retained map is a valid, unencrypted 10-page PDF spanning 0-500 ft | 8/8 PDFs valid; 80/80 pages present; page 1 is 0-50 ft and page 10 is 450-500 ft; station chain 1234+80 to 1239+80 | PASS |
| G3 Printed-grid registration | All 60 same-page adjacent-date pairs solve; >=200 RANSAC inliers; per-pair median reprojection <=1.5 px; p95 <=3 px; transformed page-area ratio 0.80-1.20 | 60/60 solved; minimum 285 inliers; overall median 775; median reprojection 0.666 px; worst pair median 0.970 px; worst p95 2.363 px; area ratio 0.878-0.996 | PASS for coordinate carrier only |
| G4 Target semantic pilot | Target can be separated from printed grid, joints, other distress, and the other lane; map-derived length agrees with Excel within max(5 ft, 10%) | On 2018-04-27, a fixed green-ink/lane/orientation diagnostic recovered 43.0 ft versus Excel 45 ft (4.4% difference), after visual review of all 10 pages | DIAGNOSTIC PASS on one date only |
| G5 Full-chain scalar reconciliation | Blind, frozen extraction passes G4 tolerance on at least zero, onset, growth, and final pre-intervention dates, with explicit severity and lane labels | Not completed; later maps are cumulative multi-date sheets and colour/date semantics are not yet frozen | FAIL / BLOCKED |
| G6 Crack identity persistence | One annotator completes a frozen blind first pass plus a concealed repeat sample, then links crack identity chronologically without using future summaries | No intra-rater repeat or identity-agreement test | FAIL / BLOCKED |
| G7 Model-ready trajectory | G1-G6 pass and at least one independent section is held out | G5-G6 fail; one section alone cannot establish generalisable forecasting | NO-GO |

## Registration diagnostic

All PDFs were rendered at 120 dpi to 1020 x 1320 pixels. For each physical
50-ft page, ORB features were matched between adjacent exact survey dates; a
projective transform was estimated with a 3-pixel RANSAC threshold. The printed
grid and fixed page text dominate the matches, so this result establishes a
stable coordinate carrier, not crack recognition.

Summary for the 60 exact-date page pairs:

- solved: 60/60;
- minimum RANSAC inliers: 285;
- median RANSAC inliers: 775;
- median inlier ratio: 0.415;
- median reprojection error: 0.666 px;
- maximum pairwise median error: 0.970 px;
- maximum p95 error: 2.363 px;
- transformed page-area ratio range: 0.878-0.996.

## One-date semantic/length pilot

The 2018-04-27 map is the first Excel-aligned non-zero NWP state. A deliberately
simple diagnostic isolated green annotations in the Driving lane (the lane on
the 10-ft-shoulder side of the dashed lane divider), retained longitudinally
oriented components, and converted their summed axial extent using the printed
50-ft scale.

- map-derived NWP extent: 43.0 ft;
- workbook NWP extent: 45 ft;
- absolute difference: 2.0 ft;
- relative difference: 4.4%.

This is encouraging but not a blind full-chain validation. It uses one survey
colour and a lane region selected from the printed layout. It cannot be reused
unchanged on later cumulative sheets, where earlier marks have been copied or
rescanned in different colours and additional dates are written on the same
paper.

## Why the full trajectory is not yet qualified

1. The DIM instructs surveyors to bring copies of the most recent prior maps.
   The MnROAD PDFs visibly behave as cumulative working sheets rather than
   independent clean snapshots.
2. A Cell 22 map covers both lanes. The workbook has distinct `22-D-2016` and
   `22-P-2016` rows, so every vector must carry an explicit lane assignment.
3. Colour and handwriting change across surveys, and later scans contain dates,
   initials, sealing notes, and older marks. Pixel differencing alone would
   confuse observation process with physical crack growth.
4. The public set omits maps for post-2019 workbook rows. Those rows are also
   after the first relevant intervention and cannot extend the natural-growth
   chain.
5. MnROAD's modifications to the LTPP DIM, workbook units, colour/date
   convention, and treatment of sealed underlying cracks remain undocumented
   in the received package.

## Smallest decisive next qualification

Do not train a model. First create a frozen single-annotator packet for the
seven eligible dates and both lanes, but score `22-D-2016` only. The first pass
must hide Excel totals and later survey states. A preselected 20% of pages must
be duplicated under concealed IDs so the same annotator's repeatability can be
measured without requiring a second person.

The packet should require:

1. page and station identity (`0-50` through `450-500 ft`);
2. lane (`Driving`, `Passing`, shoulder, joint);
3. distress class (`NWP`, `WP`, construction joint, other);
4. severity and sealed/unsealed status;
5. survey-date ownership of each visible mark;
6. persistent crack ID, new extension, nucleation, disappearance, and
   `unresolvable` rather than forced identity;
7. explicit exclusion of transitions across 2019-10-24.

Promotion requires all of the following:

- map-derived NWP total agrees with Excel within max(5 ft, 10%) at the zero,
  onset, growth, and final pre-intervention states;
- the annotator's concealed repeat agrees on at least 80% of mapped NWP length
  by crack ID;
- median symmetric spatial distance between matched vectors is <=1 ft;
- no Driving/Passing-lane leakage;
- every unexplained mark is retained as `unresolvable`, not silently assigned;
- the protocol then passes on a second independent MnROAD section before any
  forecasting claim.

If these conditions pass, Cell 22 can become a real-world crack-observation
benchmark and a case study of initiation, extension, and nucleation. It still
will not, by itself, provide enough independent trajectories for a generalised
neural forecast model or a mechanics-identification claim.
