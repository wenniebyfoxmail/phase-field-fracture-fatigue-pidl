# D4 target compatibility contract — 2026-10-20

**Run ID:** `HQ-ROAD-TARGET-COMPAT-001-R001`  
**Authority:** the user annotated the recommendation to run D4 with `go` on 2026-10-20.  
**Execution class:** one local, read-only, CPU run. No training, GPU, label mutation, remote compute, Road420 access or retry.

## Question

Can the published masks in the already-qualified CRACK500, CFD and GAPS384 development sources be represented by one scale-normalised centreline-band operator, or do they require source-specific renderers?

This is a label-operator audit. It does not test image-to-mask prediction, physical crack truth, field safety, independent-site generalisation or human-review utility.

## Frozen cohort

- CRACK500: the D1-locked 1,860 train crops, 341 validation crops and 200 full test images. The D1 parent exclusions remain in force. Crop parent is the group; each full test image is its own group.
- CFD: all 118 paired images and published `groundTruth.Boundaries` masks. Each image is one group.
- GAPS384: all 384 published image-mask pairs, with the two empty masks reported separately and excluded from nonempty renderer fitting. Site mapping is unavailable, so each image is one provisional group.

The source packages and hashes are frozen in `target_compat_data_lock.json`. Road420 has no command-line argument and must not be read.

## Frozen transform and split

1. Preserve the original mask bytes. Decode binary masks, then resize with nearest-neighbour interpolation so the shorter image side is 512 pixels while preserving aspect ratio.
2. Skeletonise each normalised nonempty mask. Compute foreground fraction, 8-connected component count, skeleton length, border contact and the distance-transform width distribution on the skeleton.
3. Render the skeleton at radii `0, 1, 2, 3, 4, 6, 8, 12, 16` normalised pixels and measure Dice against the normalised published mask.
4. Assign whole groups to `fit` or `eval` by the low bit of SHA-256(`20261020|source|group`). Radius fitting is group-weighted.
5. Select one radius per source on fit groups. Select one global radius by the unweighted mean of the three source-level fit means. Do not tune on eval groups.

## Prospective decision rule

For each source, the per-image best grid radius is the observable reconstruction ceiling. Empty masks are excluded from the ratios below.

- **Source renderer adequate:** held-out source-radius mean Dice is at least 90% of the held-out oracle-radius mean Dice, and held-out oracle mean Dice is at least 0.75.
- **Common renderer adequate:** the global-radius held-out mean Dice is at least 95% of the source-radius held-out mean Dice for every source.
- **Route A:** every source renderer and the common renderer are adequate, and the fixed visual audit reveals no object-semantic contradiction.
- **Route B:** every source renderer is adequate, but the common renderer is inadequate; the fixed visual audit still supports a shared visible centreline with source-specific width/rendering.
- **Stop:** any source renderer is inadequate, or the fixed visual audit shows broad-region, seam, patch-boundary or other object semantics that a centreline-width renderer cannot defend.

The 0.75 floor prevents a low reconstruction ceiling from making a relative ratio look successful. The 90% and 95% rules compare each simpler operator with an observed within-source ceiling rather than with D1–D3 model results. The visual audit may downgrade the numeric route; it cannot upgrade it.

## Fixed visual sample

For each source, select deterministically from held-out nonempty groups: the two lowest oracle reconstructions, the two largest source-versus-global improvements, the thinnest and thickest median-width examples, deduplicated and filled by SHA-256 order to eight items. Add an empty example where one exists. Display the source image with published mask, skeleton and rendered-mask overlays.

## Outputs and stop conditions

Required outputs are a receipt, complete per-mask CSV, source summary JSON, fixed selections, one panel per source, a cross-source summary figure, stdout/stderr and exit code. Stop without interpretation on identity mismatch, cohort mismatch, non-binary mask, group leakage, non-finite metric, output collision, wall time over two CPU hours or any Road420 access.

