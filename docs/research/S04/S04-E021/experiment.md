---
storyline_id: S04
experiment_id: S04-E021
protocol_revision: 20261015-draft-r1-coordinate-preconditioning
status: design-and-prototype-not-code-ready
---
# Bounded residual-coordinate preconditioning — proposed three-state discriminator

Question: can an input-coordinate reparameterisation help the local residual learn the required UV correction under the existing10000-update budget, retaining c20/c60 accuracy and background? Synthetic same-state supervised diagnostic, own c20s4/c60s4/c83s4 peak. Exact fixed-damage UV references, E017alpha.7backbones, frozen history/fatigue. One exposed trajectory/seed, no heldout/physical qualification. This design follows E020endpoint diagnostic; it is not a proven cause/repair. No producer launch, CodeReady approval or outgoing review.

## One factor relative to E019

Comparator: exact E019localized R002/R004/R006 archival controls. Candidate restores the ORIGINAL E019cosine schedule; E020hold schedule is not its control. Same8×283TrainableReLU residual architecture and parametercount, Xavier/zero-output initialization/seed7, alpha.7 and fullPCG64stream, original physical compactwindow/BCfactor/backbone, full massUVobjective,10000NEWupdates and final-step-only evaluation. Never resume E019/E020residual/optimizer or trainbackbone. Only local coordinate transform changes; separate local_center/local_scale buffers avoid modifying original physicalwindow geometry. No loss reweighting, support widening, extra branch or activation change.

For original physical core Q={damage>.1 AND lower<=xy<=upper}, define e_i=mass_i*||UV_FEM−UV_backbone||²; normalise e overQ. Let μ=Σq_i xy_i and σ_j²=Σq_i(x_ij−μ_j)². Candidate local coordinates=(xy−μ)/s, with s_j=min(s0_j,max(s0_j/4,3σ_j)). Constants3and4are a fixed bounded design choice, not optimised values or demonstrated optima; no sweep. Physicalwindow, its taper, BC and objective remain original. Restrict moments to core because tiny exterior errors can distort secondmoments; do not discard those errors from final full-domain scoring. coordinate_maps.json fixes exact3derivedmaps, sources, inherited residual digests and initial predictions.

This uses supervised FEM UVtargets already available to both methods, as one-time training preprocessing; label teacher_target_used=true and account for this preprocessing. It is not a deployable future-state coordinate estimator without target access. No predictive/generalisation claim from these three fits.

## Schedule, pairing and stopping requirements before Code Ready

Original E019actual updatek nominal profile: eta_min+(eta0−eta_min)/2*(1+cos(pi*(k−1)/10000)), eta0=.001,eta_min=.00001, k=1..10000. Preserve original literal optimizer.step→scheduler.step order; distinguish LR USED on update10000 from post-step schedulereta_min. Exact original recurrence/runtime replay and10000actualLRvector binding remain required implementation work, not established by this draft. Do not substitute E020's update-indexed8000hold schedule. Freeze actual vector, zero-initialresidual/physicalgeometry/sampler/backbone/reference identities, separate localmap buffers and source/runtime checks in the new runner/aggregator before independentreview.

Primary remains all3valid final fullmassUVRMS/abs(Us)<=.001. Compare full/damage/background vs BOTH inherited and E019historicalcontrol; component/background findings reported separately, no rescue of primary. Preserve c60's E019success via the same all-state criterion. Exterior invariance is a separate implementation check; inside-windowbackground must be measured. Feasibility: fixed-exterior bound below.001 is necessary only; coordinate change may alter learned direction but no guarantee of attainability. Do not revise thresholds from candidate results. No bestcheckpoint/seed/state selection or per-state mixture.

Nonfinite/source/asset/runtime/LR/map/gradient/BC/frozenbackbone/stream/parameterintegrity errors stop affectedrun/dispatcher; no retry/resume, extra steps, GPUfallback or changes after results. Missing=>inconclusive, invalid=>inadmissible, completevalid allpass=>bounded support, anyprimarymiss=>negative. No change to E019/E020verdicts or reference-rho tolerances. Cross-platform numerical exception assessed separately.

## Current concrete preparation

s04_e021_residual_coordinates.py implements pure boundedmap and separate-coordinate model prototype. Threeunitchecks: exterior errors excluded from map/max4zoom; initialprediction/parameteridentity/originalwindow unchanged and nonzeroresidual stillzero outside/atBC; nonfinite/zeroenergy rejection. Together with3diagnostic tests,6nontrainingchecks pass. Actual3states' full zero-output initialprediction maxdifference<=1.27e-15 from saved inherited UV; original residual parameterdigests unchanged. This validates prototype mechanics, not trainedcandidatefit or CodeReady. No full runner/exporter/aggregator implemented yet.

Next: implement exact original-schedule replay, map-aware runner/exporter/aggregator and paired audit, test nontraining wiring, then independent CodeReady. Any producer transfer/launch requires its concrete finalpackage and exact humanapproval. No new external message/file sent in this preparation.
