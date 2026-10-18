# S04 — PIDL/FEM mechanism closure

## 2026-10-05 claim impact: S04-E002-R003

The FEM c83 peak is nonstationary for the frozen projected PIDL413 objective (UV .04133148; box-damage .17479701; frozen screen1e-3). This narrows the interpretation of future supervised-to-physics departure; it cannot establish optimizer failure alone. History incompatibility is present, but cannot uniquely explain the total mismatch, especially the history-independent fixed-field UV residual. This supports a one-state counterfactual diagnostic only, not FEM invalidity, PINN incapacity, trajectory closure or a manuscript-level reproduction claim. Next gate: same-field weak-form/energy-gradient consistency and qualified FEM predecessor. Evidence: [S04-E002 decision](S04-E002/cross_residual_result.md).

## 2026-10-05 claim impact: S04-E003-R001

Original archived FEM free-UV weak residual and PIDL energy derivative agree (scaled vector difference1.108e-11, gate1e-9). The same rho_u .04133148 is present in both. Qualified FEM prior damage eliminates the cross-trajectory healing penalty; with both FEM histories, common-free damage box residual remains .058074. Frozen trial-coefficient damage gradient also agrees with the original weak residual at this inactive-penalty state (diagnostic). This excludes a same-field UV operator mismatch and narrows, but does not close, history attribution. Correct E002 predecessor unavailability: v1/native_q4 was missed, not absent. Next gate is teacher accuracy under a common residual/field contract; no training or trajectory claim. [Decision](S04-E003/decision.md).

## 2026-10-05 claim impact: S04-E006 teacher UV precision

FEM-seeded fixed-FEM-damage equilibrium reduces rho_u .04133148 to4.396e-11 with RMS UV correction/Us9.659e-6 and active relativeL2 correction0.06357%. Thus screen failure alone did not require large corrections in these norms for c83. Common-free damage stays .05807453; full coupled teacher remains unqualified. Next gate is phase/clipping/fatigue endpoint damage certification, not more UV precision or immediate training. Scoped evidence reviewPASS. [Decision](S04-E006/decision.md). Cross-cycle E005 is independently running.

## 2026-10-05 — hard-irreversibility interpretation corrected (S04-E007)

c76/c82/c83 native FEM endpoints pass the pre-frozen4e-4 nodal hard-KKT migration screen; their box-screen failures remain valid for the different feasible set. Original UV screens still fail and full teacher remains NOT_QUALIFIED. Follow-up E008 measures c76/c82 fixed-damage UV corrections; early/mid and within-cycle missing prior/oracle cannot be substituted by late peaks. See S04-E007/decision.md.

### 2026-10-05 — S04-E008 conditional UV precision, late peaks

Condor65 exit0, numerical a741da7,29tests PASS; c76/c82 fixed-damage UV solves4iterations each, rho_u≈4.7e-11. Active-driver relativeL2 corrections7.86%/18.56%, original-p99 9.33%/19.64%; c83 existing E006 much smaller. Only these three peaks show increase then decrease; no early-stage trend or causality claim. Hard KKT migration passes before/after, box fails, damage residuals increase slightly. Full teacher NOT_QUALIFIED. Evidence review PASS on supplied results; archived-array norm checks agree. [Decision](S04-E008/decision.md). Missing early/internal assets remain next gate, no new training.

### 2026-10-05 — S04-E009 restored early peaks

Original c20/c40 accepted fields fail the unchanged free-UV screen (rho_u0.7175/1.1879). Fixed-damage re-equilibration gives4.95e-11/4.87e-11, with active-driver corrections3.14%/9.02%. This excludes an exclusively late origin in sampled states, but does not locate onset or establish monotonicity. Own FEM priors and original MATLAB vectors admitted; separate replay lineage preserved. Hard-KKT passes, box fails; full teacher NOT_QUALIFIED. Evidence PASS on supplied records. [Decision](S04-E009/decision.md).

### 2026-10-05 — S04-E010 phase-resolved teacher residuals

One sealedStage0b trajectory, sixcycles20/40/60/76/82/83 ×s2/s4/s5, eachownacceptedprior. All18identity/operator/strictfeasibility pass;5archivedMATLAB bridges and13reconstructed-only labels retained. Original loading/peakUV fails alreadyatc20, allunloadUV passes, peakUVnonmonotonic. AllhardKKTmigration screensPASS versus allboxFAIL; different constraints/scales, no teacherpromotion. Condor67exit0,33testsPASS,archivednormsreproduced. EvidencePASS. [Decision](S04-E010/decision.md). Nextread-only gate: accepted-endpoint stopping semantics, no longrerun/training.

### 2026-10-06 — S04-E011 native stopping contract versus teacher gate

Hash-matched original Stage0b source reassembles UV equilibrium after the damage update and accepts on raw free-UV L2 plus the returned phase-Newton scalar at `4e-4`. Reusing the18E010 accepted-state vectors, all18 pass that reconstructed native expression, while all12 loading/peak states fail the later mass-dual `rho_u<=1e-3` teacher gate. Earlyc20, middlec60, latec82, and transitionc83 show the same contract mismatch; `rho_u/raw_uv_l2` is about4.17e3–4.44e3 for these sampled directions, not a universal conversion. The phase scalar precedes damage bounds and is not the E010 hard-KKT residual; the final native sum is posterior-reconstructed rather than separately archived. This resolves the apparent `converged=true` contradiction without granting teacher qualification. Quantitative attribution to the last damage change remains unavailable. Future mechanism checks default to early–middle–late plus within-cycle phase coverage. Independent evidence reviewPASS. Next: primary fixed-damage/frozen-fatigue UV-rebalanced derived-reference pilot at c82s4/c83s4 with read-only c82s5 control; keep native-fidelity as a separate secondary baseline. [Decision](S04-E011/decision.md), [review](S04-E011/evidence_review.md).

### 2026-10-08 — S04-E012 conditional UV-derived-reference adoption

The reviewed read-only runner independently reassembled the locked original and existing UV-rebalanced c82s4/c83s4 fields. Original `rho_u` values `1.3533453` and `0.04133148` fail; polished values `4.58098e-11` and `4.39641e-11` pass. All 596 essential UV values have zero error, fixed damage passes, and c83 prior/target/fatigue/strict-feasibility identity passes. c82 hard-KKT remains parent-reported, c83 hard-KKT is recomputed from locked inputs, and c82s5 remains a parent-JSON-only unloading control. Active-driver changes differ strongly: `18.5616%` at c82s4 versus `0.063566%` at c83s4, so the correction is state dependent and is not a universal late-stage escalation rule. Code Ready and Evidence review both PASS. Register c82s4/c83s4 only as fixed-damage/frozen-fatigue UV-rebalanced derived references; polished native phase/joint acceptance is not evaluated and `full_teacher=NOT_QUALIFIED`. Future checks retain the early–middle–late plus s2/s4/s5 default; E012 itself samples only two late states and one unloading control. [Decision](S04-E012/decision.md), [metrics](S04-E012/metrics.csv), [review](S04-E012/evidence_review.md).

### 2026-10-15 — S04-E019 localized residual preserves the inherited background

Frozen E017 backbone plus localized residual reaches full UVRMS.000703914/.000688588/.003238238 at c20/c60/c83; damage errors decrease78.39%/81.68%/2.01%, background errors decrease1.26%/1.48%/1.99% versus inherited baseline. All-three primary remains negative due to c83; background retention is a separate bounded component finding, not superiority to unrestricted background. c83 error is almost entirely in-core damage with late learning onset; draft a schedule-only fixed-budget repair. Producer6/6 admitted;61files verified and all18final UVmetrics independently reproduced, but strict Mac full replay rejects a reference-rho equality tolerance because of~1e-13 platform differences. Preserve that failure; external Evidence review pending. No new execution or teacher/trajectory promotion. [Decision](S04-E019/decision.md).

### 2026-10-15 — E019 bounded Evidence review and next repair design

Haofan Pro existing review accepts E019UV/component findings with explicit reference-rho numerical-portability exception; producer primaryFAIL and Mac strictINADMISSIBLE preserved. Artifact/pairing identities reviewed; no independentCUDA or18metric exact reproduction claimed. PLANPASS for3fresh delayed-decay candidates using archived E019localized controls; requires exact LR-update indexing, control identities and no unplanned repair branches. No producer launch authorised; teacher/trajectory/transfer boundaries unchanged. [Review](S04-E019/evidence_review.md).

### 2026-10-15 — S04-E020 delayed-decay preparation

New single-factor Experiment binds3archived E019localized controls and3fresh proposed candidates; actual update1–8000lr1e-3,8001–10000cosine to1e-5. Inherited initial states, full sampling streams, geometry, reference and producer runtime identities explicit; old E019source/failure verdicts unchanged. Nontraining real3statecontrol/reload/RNG/regions plus full3sampler replay and128checks pass. CodeReady material being prepared; no reviewed code permission or producer launch yet. [Protocol](S04-E020/experiment.md).

### 2026-10-15 — E020 independent Code Ready PASS

Human-selected Codexsubagent independently accepts exact671fba2 implementation,128nontraining checks,3real control reloads/regional recomputations,3complete sampled streams and33source-manifest entries. Actual LR, paired historical identity and fail-closed three-state scoring have no blocking issue. No candidate/CUDAtraining or scientific outcome; original E019verdict/portability exception unchanged. Concrete producer approval and live preflight still required. [Review](S04-E020/code_ready_review.md).

### 2026-10-15 — E020 delayed decay completed; retain E019 and diagnose optimisation

Three valid finalcandidates: full.000699737/.003487480/.003292717 for c20/c60/c83. VsE019localized c20 improves.59%, c60worsens406.47%, c83worsens1.68%; c20/c83background improves, c60backgroundworsens1.50%. All3exteriorUVarrays exactlyinherited; this does not ensure inside-windowbackgroundretention. ProducerprimaryFAIL/componentFalse;31files45027883bytesverified and independentUVmetricsagree. StrictMacfullreplayINADMISSIBLEonlyreference-rho baselineequality, exceptionpreserved. DelayedhighLRhold is not thegeneralrepair; c60samearchitecturefitsunderE019, so do not infercapacityfailure. Next: nontraining activation/gradient/last-hidden-feature-spectrum diagnostic across early/middle/transitionstates, then one targetedpreconditioning/representation test; no newtraining/sends. Evidence reviewpending. [Decision](S04-E020/decision.md), [Next diagnostic](S04-E020/next_diagnostic.md).

### 2026-10-15 — Three-state E020 endpoint diagnosis selects a bounded coordinate test

All9initial/E019/E020models at c20/c60/c83examined over86756nodes, no parameterupdate. c60E020last damage-ever-positiveunits3vs77(E019), feature relative rank4vs67, inputdamagegradient~24400times smaller; c83retains activefeatures/nonzerogradients and positive aggregate regionalgradientcosines. Successfulc20also sparse: endpoint collapse is not a universal explanation or capacity ceiling. Exploratory reduction cross-checks pass; independentreview pending. Choose S04-E021draft single bounded local-coordinate mapping vs original E019schedule, physicalwindow/BC/objective/frozenbackbone unchanged;6nontrainingtests and3real initialmap admissions pass. Runner/aggregator/independentCodeReady/producerapproval still pending; no newtraining/send. [Diagnostic](S04-E020/feature_diagnostic_decision.md), [Draft](S04-E021/experiment.md).

### 2026-10-15 — S04-E021 coordinate screen reaches Code Ready

Runner and aggregator complete for c20s4/c60s4/c83s4 against archived E019 localized controls, with original native cosine schedule, actual used LR vector, immutable PRE_UPDATE identities and fixed 10000-new-update budget. First exact source9b627979 was NO-GO for self-reported candidate strain/rho/BC; E021-only repair now independently recomputes every final metric at unchanged strict tolerances. Independent Codex re-review PASS binds `98c620637b2b2ef06ec86983220a4e7f9f1053b7`; 162 nontraining tests pass and the original coherent-hash tamper is rejected. Full/damage/background and inside/outside support comparisons stay separate; three-state full UV<=.001 remains primary. Historical E019/E020 sources, verdicts and strict cross-platform exceptions unchanged. No producer access or training. Next: prepare exact-source three-state production plan for human approval; Code Ready is not execution or scientific success. [Protocol](S04-E021/experiment.md), [Review](S04-E021/code_ready_review.md).

### 2026-10-15 — S04-E021 production package prepared for approval

Two-file Mac package (160346-byte incremental bundle +11845-byte dispatcher) binds reviewed science98c6206; deployment5406327 separately reviewed with6operationaltests. Base19-only reconstruction and all3realassetCLIchecks passed locally. Proposed sequential c20/c60/c83alpha.7seed7x10000 on GPU0 uses original nativeE019LR, all-stateCUDApreflight, immutablepairedcontrols, per-row exactdecoder/archive/LRverification and one-shotfailurestops. Finalaccount/destination/filehashes/fullcommands/script shown in local approval_request.md. No SSH/transfer/producerpreflight/training occurred. Await specific humanapproval; no scientificresult added. [Production preparation](S04-E021/producer_execution.md).

### 2026-10-15 — S04-E021 v1 stopped before training; shared-GPU proposal prepared

Userapproved exactv1 files and singlelaunch. Both remoteSHAchecks passed; dispatcher2290530 stopped22:11:07Z at initialresourceguard: GPU0had3existingCUDAcontexts despite21772MiBfree. No sciencecheckout, candidateupdates or comparativeE019errors; this is an executionblock, not a scientificnegative. Retrieved10files175450bytes withallSHAverified; no retries/interference. Prepare newv2sharingGPU0with >8GiBfree, same science98c6206/LR/statepairs/budget, freshroot and strictremainingchecks; changedpackage/action needs newapproval. [Execution record](S04-E021/producer_execution.md).

### 2026-10-16 — S04-E021 v2 admitted and started

Exact v2 transfer/launch explicitly approved; both remote file hashes match. Clean science98c6206 and33existing asset copies verified. All three formal runtime/CUDA/reference/map/initialization preflights passed, saved and zero-output UV differences all0.0. Dispatcher3081226 started09:47:55Z; c20 runner3084000 started09:49:46Z, with c60/c83 queued. Original E019 native10000LR profile archived before updates, no E020delayed schedule. Readonly heartbeat e021 every30minutes; no retry or budget change. Final E019 full/damage/background comparison remains pending; no scientific verdict. [Execution record](S04-E021/producer_execution.md).

## 2026-10-16 — E021 coordinate preconditioning: useful c83 gain, remaining three-state miss

E021v2 all3valid final10000-update rows; original primaryFAIL. E019-relative full changes c20−6.1421%,c60+14.2119%,c83−63.9366%; c83 final.00116782 still>.001. c20 improves all regions; c60 retains absolute threshold but not E019 fit. c60/c83 inside-background rises13.7041%/6.8239%, outside saved UV unchanged. Preserve useful coordinate route while addressing residual damage and middle-state regression. Independent bounded Q4/saved-field review complete; strict Mac nativeLR/reference-rho exceptions retained. No physical teacher/forecast qualification. [E021 decision](S04-E021/decision.md), [next diagnostic proposal, not run](S04-E021/next_step_proposal.md).

## 2026-10-16 — six endpoints select one final-activation discriminator

E019/E021×c20/c60/c83 read-onlydiagnosis and independent boundedreviewcomplete. c60E021inside-bg hiddenfeaturesallzero, bias-onlyshape and currentheadgradientcompetition; c83remainder not explained by necessary currentdamage/bgconflict or feature-rankloss alone. Preservecoordinatepreconditioninggains; nextproposal changes only localfinalhiddenTrainableReLU to fixedleak.01, keeping originalphysics/budget/objective. No newtraining/repairoutcome. [Decision](S04-E021/endpoint_diagnostic_decision.md).

## 2026-10-16 — E022 local final-hidden leak implementation ready

Only local hidden8 fixedleak.01 candidate/runner/strictaggregator implemented; E021direct and E019common three-state controls pinned, originalnativeLR/10000budget/physicsfreeze preserved. Sourcea540888 CodeReadyPASS,68nontrainingtests and3stateinitialUV/fullsamplerchecks complete. Restored mapderivation from exactsavedbackbonearray after firstadmissionrejected recomputedCPUfield. No training/repairresult or promotion. Next is concreteproducerplan/formalpreflight separately. [E022](S04-E022/experiment.md).

## 2026-10-16 — E022 exact production approval package prepared

Sciencea540888, deployment84a6cda; twofile bundle/dispatcher locallyverified andindependentlyreviewed. Three own-stateE021/E019pairedrows, proposedsharedGPU0>8GiB, all3formalnativeLR/runtime/zeroUVpreflights beforetraining, one-shotstoprules. No remoteactionsperformed; [exact approval plan](S04-E022/producer/approval_action.md) awaitsuserdecision.

## 2026-10-16 — E022 completed: restored pathways do not restore three-state UV fit

Approved exact two-file single launch completed all three formal rows; original aggregate 3/3 valid, primary FAIL. All65files/45604015bytes hash verified. Full UV c20/c60/c83=.000708697/.001154219/.001146135; c60 regresses46.763% vsE021 and67.621% vsE019, c83 improves1.8568% vsE021 but remains>.001. Background improves vsbackbone in allthree and vsE021 in c60/c83, but allthree worsen vsE019; exterior savedUV unchanged exactly. Leaky final features become nonzero without successful fitting; preserve negative result and useful earlier coordinate gains. Strict Mac LR/reference-rho portability failures unchanged. Next proposal is the same frozen-feature/output-head/region-gradient discriminator on E021/E022 six endpoints, before selecting one repair; no new training. [Decision](S04-E022/decision.md).

E022 independent bounded evidence review completed with no blockers: own Q4 mass and manual leaky tensor decoding reproduce saved-field conclusions. This does not override strict Mac INADMISSIBLE or the producer primary FAIL. [Review](S04-E022/evidence_review.md).

## 2026-10-16 — E021/E022 six endpoints: restored paths are insufficient; one head-scale proposal

E022-D001 read-only six-endpoint analysis and independent bounded review complete, 0fits/0updates. c60 background effective feature rank1→25, hidden gradient restored, current damage/background all-parameter cosine−.97239→+.81327; old hard-zero/current-conflict explanation is insufficient for its worse UV endpoint. c83 still has nonzero head residual but head-only attainable improvement is unquantified; do not claim head is the binding bottleneck or .001 is reachable. Earlyc20 remains a sentinel with current gradient conflict despite absolute pass. Select one **fixed initial full-mass RMS head reparameterization** discriminator on E022 architecture, with declared bias/zero/floor rules and same original three-state budget; proposal only. Original scientific and strict Mac failures preserved. [Diagnostic](S04-E022/endpoint_diagnostic_decision.md), [review](S04-E022/endpoint_diagnostic_review.md), [one proposal](S04-E022/head_scale_repair_proposal.md).

## 2026-10-16 — E023 fixed initial RMS head parameterization reaches Code Ready

One factor implemented on E022 architecture:284fixed full-mass physical-feature scales includingbias, derived before any update from commoninitializer only. Residual initialization/RNG/parameters, all3own-stateE022direct controls, E021/E019common controls, originalnative10000LR and fullsamplerstreams preserved. Root41nontrainingchecks and3realasset/CLI/gradient-coordinate calibrations passed; independent Codex CodeReadyPASS binds c4ceb5d, including independentRMSformula and nonzeroCPdecoder. Strictdecoder recomputes initialD and rejects coherentD/CP/hashforgery. No producerpreflight/training/physicalqualification; old primaryFAIL/strictMacexceptions unchanged. Next prepare exact-source three-state production package; no evidence yet this scale hypothesis improvesUV. [E023](S04-E023/experiment.md), [review](S04-E023/code_ready_review.md).

## 2026-10-16 — E023 production package prepared; transfer/start awaiting approval

Reviewed sciencec4ceb5d remains unchanged; separate deployment28f6aa8 binds a two-file package, fresh Taobo directory and conditional one-shot dispatcher. Fifteen localdeploymentchecks, minimal-base reconstruction/all3realvalidate-only calls and independent deployment review pass. All-state fixedD/nativeLR/pairing preflight, ownE022 controls, GPU0free>8192MiB sharing and fail-stop rules explicit. No SSH/transfer/producerpreflight/training or scientific gain. [Exact approval action](S04-E023/producer/approval_action.md), [execution record](S04-E023/producer_execution.md).

## 2026-10-17 — E023 exact approved production dispatched

After user approval and VPN restoration, targetabsence verified, two unchanged payloads transferred and remoteSHAchecked; dispatcher1104872 single launch14:50:41Z, clean reviewedc4source. Initialresources and87assetcopychecks passed; three-state formalpreflight underway, no scientificresult or candidate trainingconfirmed yet. Read-onlyhourlymonitor e023 active; no retries/newruns. [Execution record](S04-E023/producer_execution.md).

## 2026-10-17 — E023 complete: c60 partial recovery, no c83 improvement over E022

Exactc4three-stateproduction finishes3valid, primaryFAIL;80files/33archivecopiesverified. FullUVc20/c60/c83=.000702665/.000890548/.001158720. c60improvesfull22.844%/damage24.307%vsE022 yetbackground+.156%, stillworseE021/E019; c83full+1.098%/damage+1.120%vsE022, so no newc83benefit. Exterior savedUVunchanged. Preserveusefulc60componentwithoutuniversalscaleadoptionorstatewinnerstitching. StrictMacINADMISSIBLE/mass-D-rhoportabilityfacts retained. Next proposedread-onlysixendpointphysical/scaledhead/regiongradientdiscriminator, no training. [Decision](S04-E023/decision.md).

Independent bounded E023Evidence review passed45headline/30support and3manualscaleddecodes, no blockers; originalprimaryFAIL and strictMacINADMISSIBLE retained. [Review](S04-E023/evidence_review.md).

## 2026-10-17 — E022/E023 physical/scaled endpoint diagnosis selects one tail-freeze proposal

Sixendpoints measured withoutfit/update, dualheadcoordinates correctlyincludeD/bias and reproduce oldE022. c60headphysicalresidual decreases but remainsnonzero; c83full/inside-backgroundheadresiduals increase despite morerelativespectraldirections. Both currentheadregions canlocallyimprove together, so earlierbackgroundregression is not establishedintrinsicconflict; oneexposedendpoint cannotidentifyAdamWcausalhistory. PreserveE023partialc60gain and alloldFAIL/strictMacexceptions. Propose onlyone futurefactor: first8000joint/last2000headonly, sameD/leak/target/nativeLR/sampler/10000budget, no resetmoments or extraheadfit. [Decision](S04-E023/endpoint_diagnostic_decision.md), [proposal](S04-E023/head_tail_repair_proposal.md). No newtraining.

E023-D001 finalboundedindependentreviewPASS:48dualhead/36gradientgrouprecords agree with511chunk actualforward/encode; no updates/fits/optimizer. One8000+2000proposal remainsunimplemented/unrun, oldscientificfailures unchanged. [Review](S04-E023/endpoint_diagnostic_review.md).

## 2026-10-17 — E024 staged head repair and application-driven evaluation revision

E024 implements8000joint+2000fixedhidden/headonly, preservesE023D/leak/native10000LR/sampler/target/initialization and correctownc20/c60/c83controls. ImmutableinitialPRE_UPDATE plus new8000snapshot/stageentry, finalactualoptimizerstates and strictmask/counter/moment/frozenweightchecks. Nontrainingphase/decoder/three-realstatefullsampler checks complete, exactCodeReadyPASS `231fe4b`; no producer transfer/training. Independent oldfull31/currentfocused18 coverage is distinguished in [review](S04-E024/code_ready_review.md).

User clarifies .001 was a historicalexperimental threshold, not a universalphysicalstandard: oldE019–E023verdicts remain, whileE024describes pairedfull/damageimprovement,background/inside-backgroundcost andactualwall/memory/storagecost. No inventedreplacementacceptance margins. PreserveE023c60componentgain independentlyofcrossing.001. Intendeduse isdamage/crack/fatigue; tolerance/fitness remainsUNDEFINED untilcoupledcorrectprior/history/errorpropagation/referenceprecision checks. [E024protocol](S04-E024/experiment.md), [applicationrequirements](S04-E024/application_accuracy_contract.md).

E024 production preparation v1 complete: exact231fe4b delta bundle and independent launcher, 120historicalassetcopies/39rowoutputs, allstatepreflight/ownE023DnativeLR/stagereceipts/stops/comparativeevaluation. Independent deploymentreviewa091ad7 PASS/22checks; cleanbundle reconstruction and3realvalidateonly pass. [Final action awaiting user approval](S04-E024/producer/approval_action.md). No SSH/transfer/producertraining.

2026-10-17 E024 user-approved exacttwofile transfer succeeded, remote120assetcopiesverified, cleanreviewed231fe4b; single detached dispatcher1489681 at19:50:55UTC runningallstateformalpreflight. Trainingnotyetconfirmed, no scienceeffectclaim. Hourlye024silentmonitoractive, noautomaticretry/newexperiment. [Execution](S04-E024/producer_execution.md).

## 2026-10-17 — E024 completed comparison: no accuracy gain; pipeline cost increased

Original231fe4bproducer3valid/nointegrityerrors/completecomparison,86files140852341bytes/39truearchivecopiesverified. OwnE023full/damage/bg/inside-bg all12effectspositive; c60full+3.729%/damage+4.063%,c83full+.134%/damage+.134%, exterior0. Allhiddenweight/momentsandcounters frozencorrectly;0..8000tracesmatch. No precisionrepair or preservedinsidebackground. Recordedrowelapsed~11%less butwholepipeline3318vs2926s(+13.397%),rowpayload~3.09times; do notpromotespeedup. StrictMacnativeLR/stageLR/massD/rhoexceptionsretained, separatepinnedproducerD/LRsaved-statechecksandindependentreviewpass. .001legacyonly, noapplicationqualification. Nextonlyunexecutedrank-awarefixed8000featureoracleproposal, no training. [Decision](S04-E024/decision.md), [review](S04-E024/evidence_review.md). e024monitorpausedaftercompletion.

## 2026-10-17 — E024-D002 fixed8000 feature oracle separates two bottlenecks

Three same-state all-mass BC/window/D/bias-preserving direct-SVD diagnostics complete, code1f460aa4, independent pre-use6tests and result review. Rank279/284/254, .1/1/10numericalcutoffs fullyreported. c60fullrank optimumstill+2.182%vsE023, withremainingE024headgap; do notblameonlyoptimizer ornetworkglobalcapacity. c20/c83 realizeddamagegains−14.398%/−.856%vsE023 costbackground+.397%/+5.726% andinsidebg+3.776%/+26.328%. Originalmatmulwarningsretained; independentgesvd/dgemm/Q4/actualorder checksagree, nofalsephysical/nativeMacpromotion. NoCPwrites/neuralupdates/remoteactions. NextonlyunexecutedE023joint10000head diagnostic beforestableboundedcorrection, notearlyfreeze. [Decision](S04-E024/fixed_feature_decision.md), [review](S04-E024/fixed_feature_evidence_review.md).

## 2026-10-18 — E024-D008 background UV guard separates field preservation and physical cost

Same three E023 terminals/fixed D007 two directions/D/BC/window/fullmassUV/2% head norm; actual nonlinear weak-force plus full/background/inside-background UV acceptance. c20 retainsD007 benefit; c83 full/damage−.01749%/−.01725%, background−.02955%, insidebackground−.14954%, rho−.01976%; c60exactoriginalzero, no gain. Independent actualnetwork/AMOR/regions/mapmasks/sum-to-rho² audit passed; c60 gradient KKT supports zero optimum only in current convex2D proxy. Background strain/instantaneous elasticdriver stillworse c20/c83; no coupled damage/crack/fatigue or application qualification. Sourcea105bbbd, no neural update/CPwrite/history/fatigue/damage/remote action. Field atlas shows both red/blue changes with damage/window overlays; relative region preservation is not pointwise dominance. [Decision](S04-E024/background_guard_decision.md). Proposed next fullhead first-order feasible-direction diagnosis, no new correction/training. Old verdicts/strict portability failures retained; .001historical only.

## 2026-10-18 — E024-D009 full-head directions remove the old-plane first-order conflict

Fixed original E023three-state/D/BC/window/2%headnorm/historyfatigue diagnostic, sourcea7186d4f. c60old2D no resolvedUVdescent vsfullhead.958673 ofunconstraineddirectionalcapacity; allstates strictcommonUV/weak/backgroundUV and background/interior elasticdriver directions. This is localgradient capability, not actualerrorgain or finite2%feasibility. Independent27gradients/Q4/AMOR/identity/FD/geometry/figures reviewed; originalrho~47/58/52 unchanged and c20/c83full/damage driverpositive slopes remain. Preserve previous mixedresults; propose only oneextra orthogonalhead-direction axis tooldplane=>3D, with futureactualnonlinear checks, no correction/training now. [Decision](S04-E024/fullhead_cone_decision.md).
