# Independent pre-use S04-E023-D001 review

Verdict: PRE_USE_PASS. No blockers. Diagnostic source73f2fe459b9a62a0e8e4cbd0246f76f41c22d017, unchanged in plot-onlydescendant6724ea3; exactsource/protocol/lock/test/plot hashes in pre_use.json. Scope: actualexistingE022/E023 six endpoints, no fit/solve/parameterupdate/training/SSH/externalmessage. First fresh full-node c20E023 memoryprecheck, then only sixfixedpairs if successful, chunk256 and original2GiBRSSguard/tolerances.

## Mathematics and coordinate mapping

Actualforward correctly includesnonunitD onhiddenfeatures andbias and compares with actualmodel.correction_physical plus savedUV. PhysicalfeaturePhi includesBC/window/[h,1]/absUs; Bphys=DBnew, Hnew=DHD,Cnew=DC,Rnew=DR. Explicitalgebra/direct/actualautodiff checks inbothbases are correct. Physicalheadgradient is actualheadgradient dividedbyD; hiddenparametergradients remainunchanged under fixedDcoordinate map. Regionhead/all/hidden dotproducts correctly computed in eachbasis using clonedgradients, not mutatingmodel or storedactualgradients. Same loss/fullRMS inbothcoordinates, fullmassregionalcontributions distinct from conditionalRMS. Relative spectrum/cos/residual are descriptive, notheadoptimality/attainability/capacity proof or historicalAdamcausality.

Independently ran2syntheticunit checks:bothPASS. NonidentityD inclbias/negativelearnedcoeff physicalequivalence and identityD oldmeasure regression meaningful. Additionally independently compared allphysical all/hidden/head/per-layer gradientnorms/dots/cosines with equivalentfoldedphysicalheadmodel under differentchunks; allagree at1e-10relative/1e-12absolute. No optimizerstep and .grad/digest unchanged. Tests do not count physical-coordinateplots as a newphysicalvalidation claim.

## Evidence and portability scope

E022loader reuses frozen exactninefilecontrols/originalretrieval; E023loaderbinds trackedretrievaldigest,33rowfiles/11perstate, trustedsourcec4, fourbehaviorenvelopes, actual10000LR vs originalexpected/formal/ownE022, ownmap/backbone/sampler identities and formalD/gradientpreflight hashes. Actualtrainedscaledclass rebuilt andverified with producerD actualbuffers; Maccalibrationbitfail recorded, notsubstitutedMacD. SavedUV1e-12 andfullRMS1e-14 remainoriginal. OldE022physicalhead metrics regress against previousreviewedresults; no originalverdict or strictMacLR/mass/D/rho admission changed.

Memory: tensorgraphchunked, actualgrad viaautograd.grad, sourcechecks .gradNone/fullstate_digest unchanged; mappedgradients clonedbeforephysicaldivision. RSSguard reused aroundchunks/spectra; actualfullnodesixmemory still tobe verified, cannot infer fromtinytests. Onmismatch/nonfinite/RSSfailure stop, preservefailedreceipt, no changedtoleranceorautomaticretry.

## Plot and summary review

Plot-only6724ea3 scriptselects bothactual/physical headresidual andgradientcos curves consistently; physicalspectra use correctH. It reads completedsummary only, no modelweights/fit/update. SummaryCSV mixesphysical head/spectrum columns withactualgradientnorm/cos columns; rootwill explicitlylabel this inREADME/decision, authoritative longtables carrycoordinate. This avoids interpretinga smaller coordinate-dependentgradient as taskimprovement. Positiveactivationfraction remainspositiveoutput, notnonzero/derivativecoverage.

Resultreview stillrequired aftercompleteprecheck+sixoutputs andrenderedplots. No newrepairimplementation/training orcompleteMacportability admitted by thispre-usePASS.
