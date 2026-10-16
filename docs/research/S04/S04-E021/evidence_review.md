# Independent E021 bounded evidence audit

Verdict: BOUNDED EVIDENCE AUDIT PASS; no blocking mismatch found in the saved-UV comparison or the draft decision/next-step proposal. This is NOT a scientific-primary PASS, complete cross-platform replay PASS, producer-launch approval or predictive/physical qualification.

Scientific source98c620637b2b2ef06ec86983220a4e7f9f1053b7; saved-field analyzer4ca1e86f3c737c36edd765c0faaed8c55bdf53c8421578f39d04718d65562abe. Local read-only numerical audit only; no source edits, SSH, training, fit, parameter updates, new experiment or external message.

## Independent evidence checks

All66retrieved files independently rehashed against remote_final_manifest.json; sizes and SHA256 match,45560202bytes. Producer manifest reports9actualarchivecopies×3verified and aggregate3valid/zeromissing/zeroerrors; local verifier cannot independently re-queryremote storage. Producer complete matrix verdict remains COORDINATE_PRECONDITIONED_THREE_STATE_UV_SCREEN_FAIL, component flagsfalse.

Independently reconstructed nodal masses from raw Q4shape-function2×2Gauss integration using explicit2×2Jacobian determinants, rather than calling the analyzer/scoring helper. Independently reduced savedUV for3states×3models(backbone,E019,E021), full/damage/background and inside/outsidebackground. All27headline regionalvalues and18inside/outsideRMSvalues agree with analysis at1e-14absolute tolerance. Per-state rows, changes and damage-error fractions are in independent_result_check.json and independent_regional_support.csv. SavedE021−E019outsidewindowmaximumdifference is exactly0 for all3states.

c20: full−6.142079%, damage−6.919566%, background−0.176344%, insidebackground−1.642704%; finalfull.000660679469 passes.001.
c60: full+14.211898%, damage+16.198947%, background+1.546233%, insidebackground+13.704084%; finalfull.000786449687 passes.001 but regresses vsE019. “Absolutecriterionretained, E019fitnotpreserved” is correct; retaining a threshold is not preserving fitting accuracy.
c83: full−63.936596%, damage−64.246537%, background+1.344688%, insidebackground+6.823897%; finalfull.001167818974 fails.001. Damage accounts98.045223% of squarederror. “Coordinate-routeprogress with backgroundtradeoff and residualdamagebottleneck” is supported; a gradient-conflict mechanism is not established. c60bothregionsregress, so it must not be described as damagegainpaidforbybackgroundloss.

## Portability and visual checks

Independently replayed the parameter-free native metadata schedule:7425LRvalues differ from formalTorch2.7, firstupdate1129,maxabsolute7.589415207398531e-19. All3actualLRvectors exactly equal their expectedvectors and formalpreflightvector. Unmodified strictMacsummary0valid/3INADMISSIBLE with nativevector errors is preserved. AuditJSON has reference_rho as the only failedfinalmetric comparison in eachstate; other candidate numerical/flag matches do not mean scientificthresholdpasses. The reference-rho differences remain separately recorded. No tolerance was relaxed, and savedUV agreement must not be presented as completeportability.

Visually inspected both regional_comparison.png and regional_trajectories.png: correctstate/methodmapping, logaxeslabelled, full-only.001criterion shown, no blank/truncatedpanels or misleadingbestcheckpointselection. Backgroundchanges are smallabsolutevalues and plotted on appropriate localranges; interpret percentages alongside tables. Passive trajectories support the reported c83lateplateau/earlyc60improvement observations, not proof of convergence or fullnetworkcapacitylimits.

## Next proposal assessment

Sixexistingendpoints×E019/E021 with originalreferences/geometry/maps, nooptimizer/fit/update/newstate, is a bounded and appropriate nextdiagnostic. A massweightedlastfeatureGram plus bias/window/BCfactor, currentheadnormal-equationresidual crosschecked against autodiffgradient, regionalgradientnorm/cos with near-zero handling, and actualRSS<=2GiB can distinguish headoptimization, effectivefeature and tradeoff hypotheses without claiming fullJacobian/NTK/capacity. The proposal correctly avoids blindLR/extra10000updates, selecting per-statewinners or changing the usedthreshold. Actual implementation/memory checks and diagnostic evidence remain futurework; this review does not claim these mechanisms have been tested. Prepare only one subsequent repair after those observations, with fresh reviewed design/approval if training is proposed.


Local full review and independent CSV/JSON: /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/producer_execution_v2/analysis_review/results_v1
