# Can MD03 research continue with missing definitions? — 2026-10-20

## Decision

**Yes: continue the questions that do not require those definitions, and keep
well-supported assumptions explicit. Do not invent the missing reference and
then claim agreement with it validates the method.** A reply is useful, not a
prerequisite for every crack-identification or image-geometry experiment.
This is a research-route analysis, not a newly executed experiment or relaxed
retrospective score. Old identification, half-depth and scores remain intact.

Original goal stays image observations → crack/state evolution. The present
question is which missing definitions affect which conclusions, not whether
every detail is complete. Reuse the measured facts in
[three-frame mapping](three_frame_reference_map_20261020.md); no rerun or new
source access is needed to make this decision.

## First-principles separation

Three different objects must not be collapsed:

1. Image features F(I_k): path/coverage/pixel thickness can be defined directly
   from each image. They need a clear observation rule, not the author's gauge
   endpoints. Speckle contamination still limits their crack interpretation;
   assuming coordinates does not improve segmentation accuracy.
2. A time/load association k→t→P: filename identity is a provenance assumption,
   while author-file time/unit/row connections have now been checked. It may
   be used conditionally without relabelling it a confirmed capture clock.
3. A gauge reading: a displacement/elongation signal depends on two material
   endpoints, projection, baseline and units. Even a known gauge crossing a
   crack can combine continuous elastic deformation with a displacement jump;
   it is not automatically pure crack opening. If endpoints are unknown, many
   spatial configurations can produce the same scalar signal. Signal fitting
   cannot uniquely establish which crack was crossed.

This is an identifiability argument, not a demand for perfect annotation.

## Which assumptions are useful?

| Missing item / working assumption | Permitted exploratory use | What it cannot establish |
|---|---|---|
|Published IMG suffix = PLA3/PLA5 photo number|Use the fixed three conditional time/load pairs, retain the actual matching rows and name the assumption|Certified physical image pairing, blind/future validation or a complete sequence join |
|DIC time unit is seconds|Relative ordering or interval ratios can use the time keys without needing seconds; state unit unknown|Capture timestamps, loading rates or seconds-to-failure unless independently confirmed |
|IMG_0003 is PLA3 reference frame|A named interpretation to ask the author about, not a fact|Original reference geometry or displacement zero |
|Ext4–7 are gauges crossing particular cracks|Can be posed as alternative hypothetical mechanisms, or tested synthetically with declared artificial endpoints|A real local opening target, independent label or pixel reference for our image band |
|Ext1–7 retain their recorded channel identity over time|Use the named elongation channels as anonymous auxiliary observations, subject to time-key quality|Spatial crack identification or equivalence of those channels to half-depth width |
|We define new virtual gauge endpoints from our images|A separate algorithm-defined observable with a fixed rule, coordinates and error analysis|Recovery of the authors' gauge setup or independent validation against assumed endpoints |

Do not pick a filename offset, gauge, sign or location because it minimises
the evaluated prediction error. If multiple provenance interpretations are
plausible, specify them from source constraints before evaluating and report
all, including unavailable joins. A finite scenario check is not a statistical
confidence interval and need not cover every possible wrong identity.

## A useful invariance: don't rerun an unchanged baseline

The candidate time keys430/645/860 have equal gaps215, as do the file indices
89/132/175 (gap43). Existing equal-step two-point extrapolation is

`y_hat3 = y2 + (y2-y1)*(t3-t2)/(t2-t1) = 2*y2-y1`.

Changing only a common time origin or time unit does not change this ratio.
Thus merely assigning seconds or shifting all three time labels by one common
offset would not change the saved hold/trend/separated predictions. Do not
spend another run on this as if it tested a new predictor. Independently
misassigned frames or nonuniform time associations are different problems;
they cannot be solved by a cosmetic change of time labels.

The conditional realised loads9.6445/12.9306/14.1595kN are valuable retrospective
loading context, not a licence to supply P3 to a predictor at frame132. A
load-conditioned forecast must distinguish a known loading schedule from a
later recorded load; otherwise it changes the information set and can leak
the future. This cannot be repaired by calling the load an assumption.

## Practical continuation while waiting

- Keep identification/image-geometry development separate from fixed-material-
  position opening measurement. Missing author gauge endpoints restrict the
  latter comparison, not every per-image geometry/prediction route.
- For MD03, retain the structure-sensitive control capability and explicitly
  conditional three-frame load context. The exposed three-frame 5.81% candidate-
  area result stays observer-space development; assumed endpoints or new labels
  cannot turn it into demonstrated physical crack prediction.
- Keep the7 DIC channels available as auxiliary state observations without
  forcing a spatial correspondence. Forecasting those channels is a possible
  explicitly labelled auxiliary task, not a silent replacement for crack
  evolution. It would need a defined target/comparator/information set before
  a new run. No training or new fit was requested or executed here.
- For a claim about real local opening accuracy, obtain located endpoints/
  reference image or an independent local opening reference. Park only that
  dependency. Do not hold the entire research programme or the independent
  D01 geometry route waiting for an email response.

The next computation should change a substantive modelling question and use
frozen observer/rules with persistence and simple extrapolation as controls,
not repeat metadata relabelling or assumed-ground-truth scoring. Design it
at the scale needed to distinguish observation variability from useful state
change; do not infer generalisation from this one exposed triplet. This note
does not launch that computation or open further images.

## Communication and records

[Combined author enquiry](author_enquiry_draft_20261020.md) is prepared locally,
not sent or saved in a mailbox. Contact verification and complete envelope/body
are available for human review. No external commitments. Existing Obsidian
owner note and its single Roadmap entry are updated; raw evidence remains in
the existing MD03 archives. This analysis changes prioritisation, not old scores.
