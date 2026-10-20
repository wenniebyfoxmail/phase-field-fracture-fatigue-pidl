# Result claim audit and route decision — HQ-ROAD-TARGET-COMPAT-001-R001

## Decision

`NO_GO_RAW_MASK_AND_FIXED_WIDTH_RENDERER__GO_TO_CENTERLINE_TARGET_DESIGN`

The run rejects one common fixed-width renderer and also rejects the tested one-fixed-width-per-source simplification. It does **not** reject public-data crack identification as a whole. The constructive route is to make a scale-normalised centreline or centreline-distance field the operational target and to stop requiring it to reproduce each source's published mask width.

This is a design decision, not authority to train the proposed centreline model. Road420 remains sealed.

## Execution and integrity

The approved local CPU run completed once in 80.71 seconds with exit code 0 and empty stderr. It used 2,903 locked masks: CRACK500 2,401, CFD 118 and GAPS384 384, including GAPS384's two empty references. Package hashes match the pre-run lock; the frozen audit script still matches snapshot `71a78dea3429a43983eaa51b77ba7957baf5c9962e07c437a2c60b3b2a736b55`. No training, GPU, remote compute, label mutation or Road420 access occurred.

An independent standard-library recomputation from the complete CSV reproduced the fitted radii, every decision-facing group mean and the final numeric decision to `1e-12`.

## Held-out geometry result

All masks were nearest-neighbour normalised to a 512-pixel short side. Groups were deterministically separated into fit and evaluation halves. Radii were chosen on fit groups only; means below are group-weighted held-out results.

| Source | Published masks | Median of image median widths | Fitted source radius | Oracle Dice | Source-radius Dice | Source/oracle retention | Global/source retention |
|---|---:|---:|---:|---:|---:|---:|---:|
| CRACK500 | 2,401 | 23.32 px | 8 px | 0.7980 | 0.6390 | 0.8007 | 0.5851 |
| CFD | 118 | 2.00 px | 1 px | 0.7433 | 0.7433 | 1.0000 | 1.0000 |
| GAPS384 | 384, 382 nonempty | 2.83 px | 1 px | 0.8097 | 0.7716 | 0.9530 | 1.0000 |

The equal-source global fit selects radius 1. CRACK500 needs a much broader radius and still has large within-source width variation: its image-level median width has a 10th–90th percentile range of 8.0–49.19 normalised pixels. A single CRACK500 radius loses 19.9% of its per-image oracle reconstruction, and the global radius loses another 41.5% relative to that source radius. The grouped bootstrap difference between CRACK500's source and global renderer is +0.2651 Dice, 95% interval `[+0.2283,+0.3012]`.

CRACK500 also has an internal representation shift: median normalised width is 25.18 px in train crops and 22.80 px in validation crops, but 6.00 px in the 200 full test images. Parent grouping prevents crop leakage; it does not make crop-scale and full-frame label width equivalent.

The frozen numeric rule therefore returns `STOP_CENTRELINE_WIDTH_RENDERER_NOT_ADEQUATE`. This is a stop for the tested fixed-width reconstruction family, not for a centreline target that deliberately discards source mask width.

## Fixed visual audit

The frozen held-out panels cover low oracle reconstruction, the largest source-versus-global gains, width extremes and GAPS384's empty case.

- CRACK500 visibly contains broad and locally variable crack regions as well as thin labels. A single dilation alternately underfills broad masks and overfills thin ones. The centreline generally follows the visible crack in the sampled panels.
- CFD masks are thin boundary traces. Their source radius equals the per-image oracle on every image. The mean 0.7433 falling 0.0067 below the pre-set 0.75 floor is a rasterisation/strict-overlap effect, not evidence of a different visible object in the frozen panel.
- GAPS384 is mostly thin, with occasional locally broad labels. Radius 1 retains 95.3% of its oracle performance. The selected empty image contains no rendered foreground.
- The panels do not show a prevalent lane-line, shadow, seam or broad-background target replacing the crack trace. They are a deterministic explanatory sample, not a prevalence estimate or annotation-repeatability study.

The visual review cannot rescue the formal fixed-width failure. It does explain why the next target should discard width rather than add a more complicated source-wide dilation.

## Criteria reflection

The D4 result confirms that the earlier criteria problem was about layer and estimand, not simply severity.

1. The CFD 0.75 oracle floor is too brittle for a two-pixel raster trace: the optimal frozen operator exactly matches the source-specific oracle but formally fails by 0.0067. This floor should not be reused as a scientific gate.
2. The CRACK500 failure is not a marginal threshold effect. Its source/oracle retention is 0.8007 against a frozen 0.90 rule, and the fixed panel shows both severe underfill and overfill. Lowering the rule would hide the width heterogeneity.
3. Raw-mask Dice mixes crack localisation with dataset-specific annotation width. The prior D1–D3 transfer failures cannot be attributed to width alone—the old/new models also had very low 2/4-pixel tolerant F1—but future base-measurement evaluation should separate centreline localisation, components and rendering convention.
4. File integrity, group separation, source-stratified reporting, independent recomputation and the Road420 seal remain appropriate. The exploratory `Dice>0` and fixed 0.05 ranking rules remain unsuitable as stand-alone capability gates.

## Reconciliation with the evidence ledger and prior audits

This result is consistent with the 31-row evidence ledger and the earlier data, statistics and evaluation audits:

- public masks support a finite published-label diagnostic, not physical crack width or safety;
- centreline/topology metrics are methodologically available, but no prior-art gap or novelty is claimed here;
- CRACK500 crop parents and GAPS384 image IDs are grouping proxies rather than independent road/site identities;
- no public-data curve establishes actual human-review or reacquisition benefit;
- an untouched source is spent only after a usable base measurement and a prospective decision rule exist.

The result narrows the D3 redirect: the incompatible element is published mask width. The frozen panels support a shared **operational visible-crack centreline hypothesis**, but one annotation per image cannot make that centreline physical truth or establish its repeatability.

## Constructive next route

Promote a modified Route A for one bounded comparator:

1. Transform each development mask to a skeleton and then to the same scale-normalised centreline-distance target. Preserve the original masks and report the transformation separately.
2. Reuse one pretrained segmentation architecture and one seed. Change only the target/loss required by the centreline representation; do not add UQ machinery.
3. Evaluate source-stratified centreline tolerance F1, component hit/omission and connectivity. Report 1/2/4 normalised-pixel sensitivity instead of choosing one favourable tolerance after the run.
4. Compare against the already-frozen raw-mask predictions on the same centreline metrics where possible. Require a consistent paired improvement and usable absolute component/localisation performance before any selective-acceptance study.
5. If base localisation remains poor on both CFD and GAPS384, stop the public-mask transfer thesis. If it becomes usable, freeze one simple uncertainty comparison on development sources before considering a fresh source.

The latent source-renderer route is demoted. A learned local-width renderer could fit mask conventions, but one mask per image cannot identify annotation width separately from model error. It should only be reconsidered if the scientific endpoint actually requires reproducing source masks; the present endpoint is crack localisation and selective inspection.

## Claim boundary

Supported: the three named public sources use materially different published-mask widths; the tested global and source-fixed width renderers are inadequate; a common centreline target is the next bounded design hypothesis.

Not supported: physical crack truth or width, independent-site generalisation, annotation repeatability, field safety, human-review utility, model performance of the proposed centreline route, or access to Road420.

