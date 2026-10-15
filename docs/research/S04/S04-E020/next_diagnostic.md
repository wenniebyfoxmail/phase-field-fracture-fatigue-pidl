# Next bounded diagnostic after E020 — proposal, no new producer run

Purpose: distinguish failed optimisation/feature activation from unresolved local representation, using the existing c20s4/c60s4/c83s4 checkpoints. E019 fits c60 using the same architecture/window; therefore c60's E020 collapse cannot establish insufficient architecture capacity. c83 remains unresolved in both schedules. Keeping high LR until8000 is not a general repair. Preserve the original E019 controls and all frozen E020 verdicts; do not construct a per-state winner as a new scored method.

## Inputs and scope

Use exact qualified UV references, E017 backbones, reviewed deterministic zero-output initial residuals, and E019/E020 final localized checkpoints at all3states. Same mass weights, damage>.1/background complement, core/taper/exterior definitions. No fresh state/holdout, optimisation step, parameter update, producer process, extended budget, new seed or model fit. Diagnostic asset receipt must bind source/checkpoints and observed reductions. Mac inference/autodiff only, chunked with a2GiB memory cap; if that cap is not verified, stop rather than allocate a dense full Jacobian. Initial reconstructions are explicitly reconstruction, not saved intermediate training checkpoints.

## Measurements to prepare

1. Reproduce each saved UV and regional metrics before inspecting hidden features. Report layerwise TrainableReLU m values, preactivation signs, active fractions and near-constant/dead feature fractions, separately in damage and background. Use the recorded formula ReLU(m*z); no assumption that m is positive.
2. Stream the mass-weighted last-hidden-feature Gram matrix, with the window/BC output factor included, separately for damage and background. Report eigenvalue spectrum/effective-rank curves and feature norms; do not label this the full parameter-Jacobian or NTK condition number. No least-squares/ridge correction is fitted.
3. Accumulate gradients of the same full mass objective and its damage/background contributions over fixed chunks, without optimizer creation/step. Report layerwise norms and damage/background gradient cosine, including numerical-near-zero denominators explicitly. This separates weak/absent useful gradients from opposing regional directions; endpoint gradients cannot recover the earlier optimisation path.
4. Reuse fixed0/1000/...10000traces and saved correction-direction amplitude oracles. c60 E020 amplitude oracle remains.00348748025; c83.00328586513. Neither reaches.001. Residual amplitude alone is insufficient for these learned directions. Endpoint feature statistics cannot prove the representation ceiling.

## Decision and minimal repair

Retain E019 as the common comparator. If activation/feature collapse or extreme scale imbalance is observed, prepare one preconditioning/initialisation repair matching that measured failure, with original E019 schedule, unchanged architecture size/support/objective and10000new-update budget. Choose only one change after the diagnostic; freeze it before any new run. If useful features and gradients remain well represented but the local correction shape is unresolved, prepare a separate coordinate/feature representation discriminator rather than another blind LR sweep. Cover c20 early, c60 middle and c83 transition in either case; c60 must retain its existing.001 success, c83 must approach/pass.001, and background vs BOTH inherited/E019 controls stays separately reported.

This is the chosen next low-cost diagnostic plan, not a Code Ready implementation, confirmed causal finding or authorised training. Independent review and exact package approval are needed before a new producer experiment. No new external review sent.

## Execution 2026-10-15

The proposed9-model nontraining analysis is now completed; see feature_diagnostic_decision.md. c60E020endpoint collapse and c83nonzero-gradient/active-feature regime differ; do not generalise one explanation across states. Next chosen hypothesis is bounded teacher-residual local-coordinate preconditioning vs original E019, with physicalsupport/objective unchanged, drafted as S04-E021. Prototype and3real initial-map admissions completed; no newtraining/CodeReady or outbound approval implied.
