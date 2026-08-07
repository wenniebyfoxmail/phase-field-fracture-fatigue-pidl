# LTPP document-aware crack recognition amendment candidate

Status: `CANDIDATE__NOT_AUTHORIZED__NO_FIT`  
Date: 2026-08-07  
Parent track: `ltpp_geoforecast_crack_recognition_track.md`

## Mechanism question

Can explicit supervision for printed/form structures, together with crack
centerline and topology supervision, reduce B1's false-positive structure
segmentation while preserving crack recall on unseen sections?

## Claim that would change

If the frozen recognition gate passes, the result would qualify current-map
recognition on the existing 37-map, six-section carrier. It would not qualify
cross-date registration, physical crack width, future-map prediction, or
ordinary road-photo deployment.

If it fails, the result would strengthen the conclusion that the current
hand-drawn carrier is not sufficiently learnable for reliable recognition under
the existing section holdout, but it would not prove that all crack recognizers
fail universally.

## Proposed representation

Input: one grayscale scanned map, with no future information and no held-out
map information.

Outputs:

- crack occupancy;
- crack centerline;
- endpoint/junction heatmap;
- hard-negative semantic classes: grid/frame, boundary, handwriting,
  arrow/dimension, WIM/patch, hatching/X, other non-crack line;
- optional ambiguous/uncertain mask used only under the frozen missingness rule.

The centerline and endpoint targets must be derived from the new dated
hard-negative/geometry package before fitting. No pseudo-label from B0, B1, or
zero-shot SAM may be promoted to gold.

## Proposed model and loss

Use one small shared encoder with separate decoder heads for occupancy,
centerline, topology, and confounder classes. The architecture family must be
fixed before held-out evaluation. The planned loss is a fixed weighted sum of:

- binary cross-entropy or focal/Tversky for crack occupancy;
- Dice or focal loss for confounder classes;
- centerline loss;
- soft-clDice or an equivalent topology-preserving loss;
- endpoint/junction loss.

Exact architecture, weights, optimizer, epochs, seed, target rasterization,
and threshold must be written into the signed amendment before fitting.

## Split and safeguards

- retain the six complete-section LOSO folds;
- retain the frozen 37-map input set and original crack gold;
- use only training-section hard-negative labels for model fitting;
- freeze held-out hard-negative audit labels before any score is read;
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

Additionally report precision, recall, F1, and false-positive length separately
for every hard-negative class. Report crack-family and stroke-quality false
negatives, connected-component error, branch-count error, and topology-aware
clDice.

## Pre-fit gate

This candidate is not a training authorization. Before any fit, it requires:

1. completion and hash of the auxiliary hard-negative package;
2. external methodological review of the amendment;
3. final architecture and target-rasterization freeze;
4. no-fit preflight receipt;
5. explicit approval that the new representation is materially different from
   the completed B1 single-output Tiny U-Net.

