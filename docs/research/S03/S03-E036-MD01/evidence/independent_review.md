# E036 independent review — 2026-10-17

Reviewer: `/root/md01_early_review`. Production code, scores, geometry, source
images and earlier records were read-only. Only this explicitly authorised
R005 review directory was written. No new source, target, position,
correspondence fit, repair, training or agent was introduced.

## Decision and actual result

No numerical or scientific-interpretation blocker. The scored subset contains
one positive continuation example; the batch primarily exposes measurement
availability and correspondence limits. It does not test slowing/reversal.

| Fixed window | History eligibility / target reference | Scored | Gain, persistence AE minus trend AE |
|---|---|---:|---:|
| W12, 12/13/14 | No credible first-history trace; target unopened | No | null |
| W15, 15/16/17 | No credible first-history trace; target unopened | No | null |
| W18, 18/19/20 | First width valid; later background correspondence unavailable; target unopened | No | null |
| W21, 21/22/23 | Both histories valid; fixed target reference valid | Yes | 4.490149111604083 px |

Overall common scoring is **1/4 = 25%**, conditional scoring among the one
history-eligible case is **1/1**. Three unscorable cases remain in the denominator;
they are not prediction failures and are not assigned zero errors. R remains
unknown for all three unopened targets.

Mean paired delta is -4.490149111604083 px **over the one common-scored case**.
It is not a four-case population estimate, proof that all four windows improve,
or evidence of stable superiority. The finite four windows are correlated
parts of one source trajectory, not four independent specimens.

## Independent numerical check

The reproducible `independent_check.py` in this directory imports the separate
independent quantised bilinear sampler and half-depth implementation, not the
producer's sampler, measurement, registration or prediction functions.
`independent_results.json` records every actual saved profile and case,
source/input hashes, chronology, missingness and independent summaries.

Run with the project Python from the matching worktree; outputs use exclusive
creation and will not overwrite this completed JSON. For a rerun, preserve the
result or copy the script to another explicitly authorised fresh directory.

Actual saved profiles were exactly four, all valid:

| Window / stage | Independent width, native reference px |
|---|---:|
| W18 / 18 | 5.34893038180641 |
| W21 / 21 | 10.452488435657946 |
| W21 / 22 | 14.94263754726203 |
| W21 / 23 | 19.798930821628097 |

Every saved profile was reconstructed independently from its original source
pixels at the original fixed geometry. Profiles, shoulder backgrounds, deficits,
both half-depth crossings, widths and the already-used first-history rough
peak refinement all agree with maximum absolute difference **0**. No new
positions were sampled. No invalid-stage profile was invented or measured.

Independent arithmetic also agrees exactly:

- W21 predictions: persistence 14.94263754726203 px; trend
  19.432786658866114 px; neither clips.
- W21 absolute errors: persistence 4.856293274366067 px; trend
  0.3661441627619837 px.
- Delta -4.490149111604083 px; gain 4.490149111604083 px.
- Historical increment 4.490149111604085 px; next increment
  4.856293274366067 px; exact stratum `growth_no_deceleration`.
- Eligibility, target attempted/reference, null predictions/errors/strata,
  counts, coverage, paired mean and all strata match independently.

There are zero **observed scored** slowing or reversal cases. This is absence
of representation, not evidence that the missing windows have no slowing or
that the predictor handles turning points.

## Information order and integrity

- Exact protocol/lock/code admission was completed before numerical use;
  the all-history target preflight amendment `0721a48` was independently
  reviewed. Execution receipts bind clean `7413b19`; frozen geometry is present
  in that execution commit and is unchanged in saved historical payloads.
- All four historical snapshots are byte-identical to their prediction twins;
  lock hashes match. Every saved-at timestamp precedes batch closure at
  **16:06:43.762204Z**. Closure precedes target phase startup and the only target
  acquisition, IMG_0391.JPG at **16:07:11.016772Z**.
- Source directory contains exactly the eight locked historical files and
  that one target. All nine SHA256/byte identities match the predeclared lock.
  IMG_0362.JPG, IMG_0371.JPG and IMG_0382.JPG remain absent in this experiment;
  none was opened by the reviewer.
- All **15 old result payload hashes** equal the values frozen in the E036
  pre-access lock, and remain unchanged during independent review. All current
  E036 numerical inputs likewise remain unchanged. These are exact payload
  checks, not a claim to have audited unrelated filesystem history.
- No old score, half-depth definition, profile, target or missingness verdict
  was revised to increase coverage.

## Visual geometry and W18 correspondence interpretation

The four first-history whole-frame previews and their single fixed-region
crops were inspected. W12/W15 do not establish a sufficiently identifiable
continuous trace for the declared profile task; no-trace is reasonable, but
does not establish physical absence or zero width. W18/W21 have identifiable
continuous traces. Stored y-midpoints equal the midpoint of the saved visible
trace endpoints, and normal directions follow the saved local tangent.
These remain observer-assisted AI choices, not human or physical truth.

W18's recorded four NCC scores are 0.3453952074, 0.4614996314,
0.2976358235 and 0.3460592330: all below the fixed 0.60 threshold; one peak is
also at a search boundary. Correspondence was therefore unavailable under the
frozen method. Those failed peak offsets are not known material displacement.
No fresh correspondence search or repair was performed by this reviewer.

First-history Step18 shows bare background near the chosen band; existing
Step19 shows newly present fixed plates and white adhesive. The F05 source
footprints show these overlap the original templates/search support. This
supports appearance/occlusion change as a plausible, controllable contributor,
not a unique quantified cause or proof of a particular true displacement.
Successful W21 background transfer is likewise an optical position proxy,
not calibrated material-point accuracy; its anchors lie above the measurement
band, so transfer to that band remains an assumption.

## Final figure and documentation review

Final R004/analysis F01–F05 colour and F02 grayscale were visually inspected.
The figures accurately retain all four windows, the three missing cases,
the one scored pair, fixed reference units, chronology, original profiles and
source imagery. Stage14/17/20 panels explicitly remain unopened. F05 labels
original template and zero-seeded search footprints, not successful matches.
No numerical or visual-encoding blocker was found.

README interpretation correctly distinguishes overall1/4 from conditional1/1,
one-case gain from stable batch success, and unavailable slowing/reversal
evidence. Its proposed new-version history-only correspondence repair uses
already seen18/19, retains the original line/definition/score, and leaves20
unopened pending a separately fixed and approved step; it is not reported as
executed.

Two minor documentation corrections were sent to the main agent and then
verified corrected in the final R004 assets: the README says **three missing
rows**, and sidecar provenance attributes original JPG display to **F03 and
F05**. Neither changes a figure, source, measurement or score. Final numerical
and visual review is complete with no outstanding correction.

## Claim and next-action boundary

This batch adds one independently reproduced directional gain while measuring
the current coverage bottleneck. Preserve both. Do not label all three missing
cases as model FAIL, fill their errors with zero, remove them from coverage,
or claim this batch tested deceleration/reversal performance.

A source-only, separately versioned18/19 correspondence repair is a reasonable
next bounded lever. It must not use unseen20 or target errors to choose
background, change the original crack line or retroactively replace E036's
1/4 coverage. Physical width accuracy, unseen-specimen/road generalisation and
statistical inference remain outside this result.
