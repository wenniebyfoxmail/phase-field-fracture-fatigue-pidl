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

## Current implementation and authority entry

There is no active D5 execution card or Run ID. This proposal remains design-only and authorises no training, SSH, deployment, probe, transfer, review dispatch or compute run. D4's frozen records and consumed authority are unchanged.

D5 needs one bounded execution authorisation covering the scientific goal, allowed CRACK500/CFD/GAPS384 inputs, target/comparator and decision criteria, producer, total resource budget, scientific stop/retry limits and required result. That authorisation may be conditional on completing implementation, relevant tests, the chosen review channel where warranted, and successful admission; satisfying those mechanical conditions does not require another human approval.

Within that approved envelope, the agent will automatically:

- implement and repair in-scope code, run local tests and obtain any necessary focused re-review through the already chosen channel;
- discover and record actual compatible versions, verify environment/resource availability, and materialise exact commands, paths, Run ID, hashes and receipts;
- apply metadata-only or isolated dependency corrections with consistency checks, without restarting Code Ready or asking for repeated administrative approval;
- reserve a short mechanical recheck allowance inside the approved total budget before the first scientific attempt. A known pre-start resource wait is not a scientific failure or retry.

Human decision is required only if the authority envelope changes: Road420 or another protected/new source, a different producer, a larger total budget, changed target/comparator/scientific criterion, changed numerical or shared-system semantics, or a scientific retry not already allowed. Explicit human attempt/connection caps and scientific stop/no-retry rules remain controlling. Unknown or failed executions keep their receipts and are verified before any relaunch.

