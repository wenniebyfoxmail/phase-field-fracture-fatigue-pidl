# Criteria review and next-route decision — 2026-10-19

**Status:** route decision and prospective design only. No new data access, label mutation, training, GPU run or Road420 access is authorized by this document.

## Decision

The criteria were not uniformly too high. They were applied at the wrong layers:

| Layer | Current rule | Review |
|---|---|---|
| Data integrity | official package, hashes, pairs, duplicates, licence and grouping | Appropriate and should remain. |
| Target compatibility | all labels broadly described as visible crack pixels | Too weak. It did not establish that CRACK500, CFD and GAPS encode the same object, centreline/region convention, width or ignore policy. |
| D1 nondegeneracy | at least 75% of nonempty images have `Dice>0`; empty/full predictions below 50% | Too permissive. D2 passed while mean Dice was 0.0139 and accepted risk was about 0.975. |
| D1 sorting | risk at 25% at least 0.05 below full risk | The fixed 0.05 is an arbitrary exploration heuristic. It can be too demanding for an incremental score, yet it can also pass when absolute accepted risk is unusable, as old/CFD showed. |
| Complex score | directionally better than `U_LC` | Suitable as a screening rule, but only after the base measurement is usable. |
| D2 `delta_min` | `max(0.05, 2×bootstrap SE)` | Defensible as a placeholder scientific effect size, but it lacks a measured inspection-cost basis. It should be derived prospectively from practical loss and repeatability, not lowered after observing results. |
| Road420 seal, source-stratified reporting, independent audit | hard requirements | Appropriate. These protect the only fresh-source evidence and prevent pooled or irreproducible conclusions. |

The matrix failure is not caused by a marginally high threshold. The repair increases strict error on both sources, decreases 2/4-pixel tolerant F1 on both, and leaves best accepted risk at 0.741–0.807 on CFD and at least 0.969 on GAPS. Relaxing a gate would relabel the same unusable outputs rather than create a useful capability.

## Revised decision ladder

### D4 — target and label-operator qualification, no training

Use only the already available development sources. Preserve every original mask. Quantify, source by source:

- foreground fraction, component count, skeleton length and width distribution;
- whether a skeleton plus a source-specific width/dilation operator can reconstruct the published mask;
- seam, shadow, patch boundary and broad-region inclusion on a fixed stratified visual sample;
- scale status and whether 2/4 pixels represent comparable physical or visual tolerance.

The output is a frozen label ontology and one of three decisions:

1. **Common target exists:** a centreline or scale-normalised band explains all sources well enough to define one measurement target -> modify the current route.
2. **Common latent evidence, different renderings:** visible crack evidence is shared but mask conventions differ -> use the new latent-renderer route.
3. **Different objects or unresolved reference:** no defensible common target -> stop this public-mask transfer thesis rather than add models.

The D4 pass threshold must be derived from within-source reconstruction ceilings and the fixed visual audit before any model result is viewed. It cannot be chosen to rescue D1–D3.

### D5 — base measurement feasibility before uncertainty

Replace `Dice>0` with evidence that tests actual measurement capability:

- source-stratified strict overlap plus centreline recall/connectivity and catastrophic component omission;
- an absolute performance floor derived from within-source validation/reconstruction ceilings;
- the normalised transfer gap between within-source and cross-source risk, with paired uncertainty;
- empty/sparse-reference false positives reported separately.

No uncertainty method advances while accepted predictions are still unusable in absolute terms. Development may show direction and uncertainty, but a scientific gate needs a prospectively justified absolute floor.

### D6 — selective acceptance only after D5

At a fixed review budget, compare simple low confidence against at most one justified added score. Require both:

- acceptable absolute risk in the retained queue; and
- a prospective minimum useful improvement over `U_LC`, derived from inspection cost or reference repeatability and supported by grouped uncertainty.

If no operational cost is available, report the result as exploratory ranking rather than inventing a universal 0.05 threshold. Calibration, ranking and conformal risk control remain separate claims.

### D7 — untouched-source confirmation

Road420 stays sealed until D4–D6 succeed on development sources. Its access requires a new exact run authorization and a frozen model, score, coverage, target representation and stop rule.

## Route A — modify the current method

Keep the original question—whether segmentation failures can be rejected under source shift—but change the order and representation.

1. Freeze a common operational target from D4, preferably centreline or scale-normalised crack band rather than raw source-specific mask width.
2. Use one strong pretrained segmentation baseline and one architecture only. Train/evaluate on grouped development data with the same target transform and source-stratified reporting.
3. Add topology/centreline diagnostics and a distance-map or topology-aware objective only if D4 shows these represent the same observable across sources.
4. Do not add ensembles, MC dropout, conformal sets or learned quality estimators until D5 establishes usable base measurement.
5. At D6 compare `U_LC` with one score tied to a measured failure mechanism, such as augmentation consistency for appearance instability. Drop it if it does not improve both absolute and relative retained risk.

This route is the lower-cost repair. Its falsifier is clear: if a frozen common target still leaves a large cross-source gap or broad-background predictions, representation/loss tuning is not the binding solution.

## Route B — new method: latent crack evidence with source-specific annotation renderers

Model the mechanism already exposed by the matrix:

`z = f_theta(x)`, `y_s ≈ R_phi_s(z) + e_s`.

- `f_theta` predicts a shared latent crack-evidence field, such as centreline probability plus distance-to-centreline.
- `R_phi_s` is a small source-specific renderer that maps the latent field to each dataset's published mask convention: width/dilation, uncertain boundary and ignore policy.
- The shared field is evaluated with source-neutral centreline/component criteria; rendered masks are evaluated only against their own source convention.
- Appearance uncertainty is measured on the latent field; annotation uncertainty is represented by renderer/width disagreement. These are not collapsed into one unexplained heatmap.

Predicted signatures:

- If annotation convention is the main bottleneck, source-specific rendering improves published-label agreement while the latent centreline remains consistent.
- If appearance/domain shift is dominant, the latent field itself fails on the held-out development source; add no label renderer complexity and redirect to domain adaptation or new acquisition.
- If neither a shared latent field nor source-specific rendering is stable, the public masks do not support the proposed common crack-identification claim.

This is a genuinely new methodological route relative to the completed backbone swap. It also carries more identifiability risk: with one mask per image, a latent centreline can become a convenient modelling assumption rather than physical truth. It therefore requires D4 evidence and must be described as a common operational representation, not true crack geometry.

## Recommendation

Proceed first with the bounded D4 no-training target audit. It is the cheapest experiment that can choose between Route A, Route B and stopping. If D4 supports a common centreline/band target, use Route A as the primary repair and keep Route B as a single strong comparator. If D4 shows shared visible evidence but irreducible source-specific rendering, promote Route B. Do not spend another GPU run on backbone/UQ variation before this decision.

The next executable package should therefore be `HQ-ROAD-TARGET-COMPAT-001`, CPU/read-only, existing CRACK500/CFD/GAPS only, no label mutation and no Road420. Its exact sample rule, transforms, ceiling-derived criterion, outputs and resource cap must be frozen and approved before execution.
