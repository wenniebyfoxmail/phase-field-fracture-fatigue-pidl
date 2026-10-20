# D5 centreline-target proposal — design only

**Disposition:** `REVIEWABLE_DESIGN__NOT_EXECUTION_AUTHORITY`

## One question

Does replacing source-specific raw mask width with one scale-normalised centreline target materially improve cross-source crack localisation on the already-consumed CFD and GAPS384 development sources?

## Minimal comparator

- Reuse the D2 ResNet18-UNet family and ImageNet weight identity; one seed and one bounded run.
- Reuse the locked CRACK500 training/validation groups. Preserve all original masks; create the target on the fly from a skeleton and a prospectively fixed scale-normalised distance field.
- Do not add ensembles, domain adaptation, learned quality heads, calibration or a source renderer.
- CFD and GAPS384 are development evaluations. Road420 remains sealed and is not a D5 input.

## Evaluation before UQ

Report each source separately:

- centreline precision/recall/F1 at 1, 2 and 4 normalised pixels;
- reference component hit rate and catastrophic component omission;
- predicted-component excess and connectivity break diagnostics;
- strict raw-mask Dice only as a source-convention secondary metric;
- paired comparison with the frozen D1/D2 predictions on the same centreline metrics where artifacts permit.

No universal 0.75 Dice or 0.05 ranking threshold is proposed. The execution contract should freeze a practical base-measurement rule using the transformed-target validation ceiling and grouped paired uncertainty. The route only advances if improvement is consistent on both CFD and GAPS384 **and** the retained localisation/component error is usable in absolute terms. A directional improvement with near-zero localisation remains a stop.

## Falsifier

If a centreline-trained model still predicts broad background regions, omits most reference components or fails to improve both development sources, annotation width was not the binding mechanism. Stop further public-mask architecture/UQ sweeps and return to source acquisition or a differently scoped endpoint.

## Authority required

Before execution, freeze the exact target transform, validation ceiling, model snapshot, comparison artifacts, run budget, resource/host, output contract and first-stop rule, then obtain a new exact execution authorization. This document authorises no training or compute run.

