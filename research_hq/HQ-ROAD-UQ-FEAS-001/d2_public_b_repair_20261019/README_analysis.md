# D2 repair-package visual reading guide

## `gaps384_overlay_audit.png`

**See:** twelve GAPS384 grayscale road images selected across the observed foreground-ratio range, with the published mask in red.

**Therefore:** the package supplies thin pixel-level curve labels suitable for a bounded segmentation-transfer diagnostic, and contains a range of crack visibility and label density.

**Does not show:** physical crack width, field-confirmed truth, site identity, natural prevalence or independence from sealed Road420.

## `d1_failure_panel.png`

**See:** fixed CFD examples from the frozen D1 result, selected by low/high `U_Z` and empty-prediction status. High-`U_Z` cases often have empty predictions; some low-`U_Z` cases remain partial or empty.

**Therefore:** a source-feature repair is testable, while label-width/target-definition mismatch remains unresolved. This supports changing only the encoder first.

**Does not show:** that pretrained ResNet18 will pass F1/F2. The panel is diagnostic evidence from the old run, not a new model result.
