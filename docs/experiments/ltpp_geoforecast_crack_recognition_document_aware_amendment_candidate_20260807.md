# LTPP document-aware crack recognition amendment candidate

Status: `CANDIDATE__HARD_REMOVAL_REJECTED__NO_FIT`
Date: 2026-08-07  
Parent track: `ltpp_geoforecast_crack_recognition_track.md`

## Mechanism question

Can a recognizer trained only against frozen adjudicated crack targets and
ordinary background use non-destructive, fixed document-structure cues to
reduce B1's false-positive structure segmentation while preserving crack
recall on unseen sections?

## Claim that would change

If the frozen recognition gate passes, the result would qualify current-map
recognition on the existing 37-map, six-section carrier. It would not qualify
cross-date registration, physical crack width, future-map prediction, or
ordinary road-photo deployment.

If it fails, the result would strengthen the conclusion that the current
hand-drawn carrier is not sufficiently learnable for reliable recognition under
the existing section holdout, but it would not prove that all crack recognizers
fail universally.

## Existing-label reuse boundary

The crack occupancy target remains the frozen adjudicated layer. No new crack
annotation is required. The 2026-08-10 target preview showed that existing
primary handwriting, boundary, and WIM proxies conflict too often with crack
gold to become semantic supervised truth. This amendment therefore does not
create semantic negative classes or a hard-negative output head. WIM is not a
recognition target.

## Proposed representation

Input: the unmodified grayscale scanned map, with no future information and no
held-out map information. A deterministic document-structure mask may be
supplied as a second input channel only if it never deletes or replaces pixels.

Outputs:

- crack occupancy;
- crack centerline;
- endpoint/junction heatmap.

There is no handwriting, grid, form, WIM, or other semantic negative output.
All unlabeled pixels remain ordinary background under the frozen crack target.

The centerline and endpoint targets are deterministically derived from the
frozen adjudicated crack geometry. No pseudo-label from B0, B1, or zero-shot
SAM may be promoted to gold.

## Proposed model and loss

Use one small shared encoder with decoder heads for occupancy, centerline, and
topology only. The architecture family must be fixed before held-out
evaluation. The planned loss is a fixed weighted sum of:

- binary cross-entropy or focal/Tversky for crack occupancy;
- centerline loss;
- soft-clDice or an equivalent topology-preserving loss;
- endpoint/junction loss.

Exact architecture, weights, optimizer, epochs, seed, target rasterization,
and threshold must be written into the signed amendment before fitting.

## Split and safeguards

- retain the six complete-section LOSO folds;
- retain the frozen 37-map input set and original crack gold;
- do not introduce semantic hard-negative labels or output heads;
- preserve the raw grayscale input; a document mask may be an auxiliary input
  channel but may not erase raw pixels;
- no threshold or component rule may be selected from held-out results;
- do not use dates, future maps, traffic, climate, maintenance, or the failed
  spatial-registration carrier;
- keep B0 and B1 results byte-for-byte unchanged.

## Primary and secondary outcomes

Keep the existing recognition gate unchanged:

- pooled centerline F1 at least `0.80`;
- pooled mean matched centerline distance at most `0.10 m`;
- pooled matched endpoint distance at most `0.20 m`;
- improvement over B0 in at least four of six sections;
- no section centerline recall below `0.70`;
- no post-freeze map, geometry, family, or confounder removal.

Additionally report false-positive length on the owner-audited handwriting,
form/grid, boundary, and WIM examples as diagnostic categories only. Report
crack-family and stroke-quality false negatives, connected-component error,
branch-count error, and topology-aware clDice.

The exact freeze must also define a map-level specificity sentinel for maps
with no adjudicated crack geometry. Such maps must report recognized crack
length and component count; the pass threshold must be fixed before fitting.
This is motivated by the owner review of `P002`, where the visible content is
text/form structure rather than a target crack.

## Pre-fit gate

This candidate is not a training authorization. Before any fit, it requires:

1. rejection of destructive preprocessing and freeze of the non-destructive
   input representation;
2. external methodological review of the amendment;
3. final architecture and target-rasterization freeze;
4. no-fit preflight receipt;
5. explicit approval that the new representation is materially different from
   the completed B1 single-output Tiny U-Net.

## Owner visual-review revisions

The 2026-08-10 owner review recorded four observations:

1. `P020` still misses one visible/adjudicated crack, so recall and continuity
   remain active risks even in the stronger example.
2. `P008` visibly converts handwriting/calculation into crack recognition
   output.
3. `P002` contains text/form content but no target crack; its B1 output is a
   specificity failure and should anchor the zero-crack-map sentinel.
4. WIM does not need semantic recognition and must not be a dedicated output
   class.

These revisions are adopted into the candidate. They do not authorize fit.

## 2026-08-10 preprocessing preservation gate

The owner selected adjudicated crack gold plus ordinary background and no
semantic negative head. Before fitting, the existing B0 `static_line_mask` was
tested as hard-removal preprocessing. It failed: pooled crack-target retention
was `69.06%`, 28 positive maps fell below the `95%` map floor, and `P020`
retained only `5.91%`. Hard removal is prohibited. See
`ltpp_geoforecast_document_preprocessing_preservation_result_20260810.md`.
