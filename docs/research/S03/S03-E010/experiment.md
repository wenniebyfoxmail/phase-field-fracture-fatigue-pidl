---
storyline_id: S03
experiment_id: S03-E010
protocol_revision: development-v1
status: development
started_at: 2026-10-11
primary_storyline: S03
---

# Local observation-token pipeline in canonical pixels

## Dataset-first route

S03-E006's archive possesses 27 verified IB images: three fixed ruler reference
planes and 24 state images (three beams x two stops x four views). Local
registration was previously qualified, but no independent crack mask/width
reference exists. S03-E009 confirms that metric-reference work is separable.
Use canonical pixels to test serialization now. This is C0 development
capability, controlled experiment, not a crack measurement/prediction test.

## Frozen MVP

Use every state image in S03-E006.SELECTION; reuse load_gray, register,
warp_image and ridge_response. Check exact input identity and existing
local-registration admission rules. No network, training or hyperparameter sweep.
Do not trust the generic global-overlap flag for close moving views; use
S03-E006's local-footprint registration checks.

Canonical plane: each beam's fixed ref1, working resolution <=2000 px.
Per-beam support: intersection of all eight registered state-view masks,
eroded by 20 working pixels. This joint support is offline characterization;
it is not a causal prediction-origin mask.

Divide the common-mask bounding box into a fixed 8x8 grid. Record coverage;
patches with <50% valid support are missing, with a separate validity mask and
zero placeholder. Four transparent descriptors per valid patch:
mean grayscale/255, grayscale SD/255, mean Sobel magnitude/255, mean existing
multiscale dark-ridge response. Native x/y positions accompany each patch.
Representations are image observables: stains, texture and shadows also respond.

Observation metadata: exact beam/stop/view/path and the published stop-label
categories (Beam 4: 10/50 kN; Beam 5: 10/60 kN; Beam 6: 10/40 kN).
These are nominal acquisition labels from S03-E005, not per-frame synchronized
load values. Keep timestamps in source paths; do not invent chronology.

Comparator/diagnostic: fixed-view patch vector at the same stop. Report mean
absolute descriptor difference for all 18 moving images and the three
fixed low/high pairs. No performance threshold or crack-growth interpretation.

Engineering acceptance: all 24 observations serialize and reload with source
identity, finite four-feature values and non-empty explicitly valid support.
Invalid registration stops computation; missing patches remain recorded.
Primary scientific verdict: development only; no new C1/C2/C3 accuracy claim.

Budget: one CPU diagnostic, 24 lightweight CV registrations; 10 minute cap.
Minimum evidence: three beam NPZs (tokens, masks, coordinates, metadata,
homographies), compact descriptor-difference CSV, all-beam overview, receipt
and README. No independent formal code/evidence readiness review is claimed.
Run S03-E010-R001; archive local_archive/experiments/S03-E010/runs/S03-E010-R001/.

Repair trigger: serialization/identity/coverage failure -> repair that component.
Large cross-view descriptor differences -> inspect photometric and representation
dependence before selecting any learned encoder. New validated accuracy or
transition claims require a separate reviewed protocol and qualified references.
