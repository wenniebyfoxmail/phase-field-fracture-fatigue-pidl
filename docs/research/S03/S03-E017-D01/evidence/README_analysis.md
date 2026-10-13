# E017-D01 isolated AI edge annotation: repeat reading and algorithm discrepancy

2026-10-13; controlled D01 laboratory images, AI-visual-development-v1.
This is AI-assisted selected-crop observation checking, NOT independent human
or physical metrology validation. No training or forecast rescoring.

## Question / source / information barrier

An algorithm-unexposed agent visually annotated all 30 anonymous E016-R002
task views. It did not inherit the parent conversation (`fork_turns=none`).
Only the 30 anonymous coordinate sheets, guide and task list were provided;
no algorithm profiles/edges/scores, loading identity or reveal key. The agent
attests it read every sheet and no project/memory/neighboring output. Platform
general research context and model pretraining could not be removed. This is
a procedural restriction and self-attestation, NOT a permission sandbox or
different-model/independent-sensor experiment. See B001 exposure/receipt.

All data are reused D01 v4 (DOI 10.17632/z3yc9z84tk.4) fixed-camera strips,
already selected by the upstream assisted observation workflow. Underlying
units: THREE beams, four transects each at first/last included states. The
24 unique tasks/6 duplicates are not 30 independent physical specimens. No
new image acquisitions, coordinate registration, detectors or model fitting.

Preparation `fa3fa3f`: public crops only, 30 raw 121x49 PNGs and fixed
nearest-neighbor readouts. The zero-based central row y=24 (25th row) and
x=0..120 pixel centers follow the separately locked visible-edge contract.
No intensity enhancement or candidate marks. Raw public packet/human UI
and the other chat's preparation remain unchanged.

AI annotation scope B001 outputs are frozen at commit
`fd4ac2e43259d513486c19e2e7afbdc1d8625eba` BEFORE reveal/algorithm joining.
The analyzer verifies exact bytes against Git before reading the private key.
Analysis at the same commit: R001 succeeded in 0.68 s. Later plotting changes
only clarify missing labels and use a non-misleading 0.5px repeat-plot scale;
V2 figures are rerendered from identical frozen numerical CSVs, no reannotation,
private-key reread or score recomputation. V1 figures preserved, not handed off.

## Frozen method / exact numerical evidence

`annotations.csv` and `exposure_note.md` remain the original agent response.
`unique_task_comparison.csv`, `duplicate_consistency.csv`, `summary.json` and
run receipt are authoritative. Reveal mapping remains LOCAL in E016's
`private_blind_key.json`, excluded from Git and blind-agent input.

Unique representative = lowest anonymous task ID per unique-key group,
REGARDLESS of confidence/visibility. No substitution of a clearer repeat.
Primary support requires representative visible and both stored operators
valid. Average |algorithm left - AI left| and |right - right| per task, then
mean tasks within beam, then equal mean of three beams. Report coverage /24.
Coordinate transform AI strip x -> normal offset x-60. Signed width difference
is algorithm minus AI. The AI's apparent central-row edges and the algorithms'
five-line-median profile definitions are different observation objects.
Consequently these are DISAGREEMENTS, not reference errors or accuracy scores.

## Findings

- 30/30 task responses: 20 visible, 10 uncertain, zero occluded; no forced
  conversion of ambiguous estimates to reference truth.
- Deduplicated primary support 16/24 (66.7%): Beam 4 6/8, Beam 5 6/8,
  Beam 6 4/8. All E017 comparisons use this SAME support for both algorithms;
  excluded eight tasks remain in tables/images/notes, never zero-filled.
- Equal-beam mean endpoint disagreement: half-depth **0.471043 px**,
  gradient **0.506944 px**. Per-beam means 0.447/0.397/0.569 and
  0.479/0.417/0.625 respectively. Do not rank operators from the ~0.036px
  difference; it is below AI's reporting granularity and lacks human-reference
  calibration, uncertainty/power or definition equivalence.
- Joint subjective-range overlap: half-depth 16/16, gradient 15/16; these are
  annotator plausible ranges, NOT confidence intervals or calibrated coverage.
- All six hidden-repeat pairs agree in quality (four visible/visible,
  two uncertain/uncertain). The four visible pairs have EXACTLY matching
  reported endpoints and widths; other two pairs have no valid repeat score.
  This is finite 0.5/1px, same-context repeat-reading agreement, not zero noise,
  infinite precision, perfect independent repeatability or reliability on Beam 6.

## Reading order / figure interpretation

1. `ai_algorithm_edge_overlay_v2.png`: fixed transect 6 first/last of EVERY
   beam, not selected by agreement. Purple point + plausible-range shade =
   AI visual estimate; blue half-depth / orange gradient = stored algorithms.
   Beam 6 examples are explicitly uncertain even when tentative points look
   close to algorithm marks; agreement does NOT resolve branch ambiguity.
2. `algorithm_ai_disagreement_v2.png`: all 24 unique tasks, shared scales,
   endpoint discrepancy above / width discrepancy below. `?` = uncertain,
   NOT scored, NOT zero. Per-beam visible support in titles. Numbers are exact
   table values and not pixel-level population accuracy.
3. `ai_duplicate_consistency_v2.png`: all six pairs, four scored at zero,
   two uncertain with no score. Y ticks reflect 0.5px reporting granularity;
   no misleading hundredth-pixel repeat precision. Same-context caveat in title.

QA: all three original figures inspected, repeat V1 automatic tiny scale
and clipped missing-task labels found; V2 fixed by rendering existing tables.
V2 discrepancy and repeat plots inspected again; V2 overlay preserves same
raw crop/markers/values as inspected V1. No blank panels, image row/coordinate
inversion or missing six-example images. All 30 input copies verified against
public raw PNGs, no key/candidate data copied into blind input.

## AI limitations / outcome / next test

1. One inherited-model AI annotator and one session. Visually similar repeated
   sheets may be recognized; the agent acknowledges possible memory effects.
   Four exact matches therefore do not estimate independent annotation noise.
2. Crops were preselected and centered by upstream workflow. The AI is isolated
   from candidate results, not from input-selection bias. Detection sensitivity,
   false-positive rate and all-crack topology are outside this sample.
3. Gray region boundaries depend on sampling/blur, rim/shadow, branching and
   spall. AI can plausibly draw the wrong physical object with high consistency.
   It lacks expertise adjudication, calibrated confidence and physical scale.
4. Central visible boundaries differ from median-profile half-depth/gradient
   edges. Differences combine definition, visual estimation, quantization and
   line aggregation; cannot uniquely assign them to algorithm error.
5. Eight unique tasks were uncertain, especially Beam 6 branches. Low visible
   discrepancy on remaining tasks does not validate all 24 or rescue missing
   reference coverage. No iid uncertainty estimate from this sample.
6. First/last references do NOT cover all eight next-stage prediction targets.
   E015's 52.4% result is unchanged, not independently validated by this run.

Allowed: AI blind visual reading completed; clear selected boundaries tend
to lie near the stored operator boundaries under coarse visual judgment, and
AI flags difficult cases rather than certifying them. Human-reference status
remains pending. Formal Code/Evidence Ready/physical-width/forecast claim absent.

Disposition: continue fixed-camera DEVELOPMENT; repair the reference definition
for branching/spall cases. Next smallest test: fresh-context reading of the
ambiguous/repeated cases to separate possible memory from repeatability, then
small expert-human adjudication. A fresh protocol is needed for every target
stage before any independent forecast scoring. Do not broaden models or adopt
AI labels as physical training truth from this agreement alone.
