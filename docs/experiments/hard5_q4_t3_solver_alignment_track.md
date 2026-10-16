# Hard-5 Q4/T3 solver alignment track

Question: which spatial operator, state-update and solution-control differences explain same-state FEM/PIDL disagreements? Scope: descriptive fixed-budget topology/algorithm comparison; no mesh-converged teacher or unique physical truth established.

Current result (2026-10-15): [CR-v3 displacement/constrained-damage closure](../research/S04/S04-E011/runs/coupled_repair_v3_result_20261015.md) passes4/4same-field joint residual criteria at c1/c83, without history commits or extra budget. c83 activeintegral collapses to~3%ofpriorDR, PIDL fixed-den gap grows to104.16%, correlation~.00664. Thus local numerical closure is achievable but does not yield PIDL agreement. Next unexecuted test is sequential substep/history-commit validation, first one fullc1; do not overwrite frozen production or promote teacher/physical claims.

Canonical paired production contract: [S04-E011](../research/S04/S04-E011/experiment.md). Frozen E003/E011 outputs retain their own verdicts and lineage. Common mesh nodes do not eliminate GP/state/algorithm distinctions.

Earlier sensitivity (2026-10-12): [c83 bounded-control sensitivity](../research/S04/S04-E011/runs/endpoint_q4_tight_20261012.md) from exact accepted s3 predecessor reproduced original20-round baseline, then exhausted10additional rounds. Fresh residualsum1.30639×baseline, absolute activefield gap to original Q4 PIDL c83step4141.99032×; no new converged endpoint. Historycommits0, native Q4 GP4 eta0; allhashes/statechecks and independentreviewPASS.

Earlier discriminator (2026-10-13): joint backtracking and sparse early-state comparison completed. [Terminal evidence](../research/S04/S04-E011/runs/endpoint_backtrack_grid_20261013.md) covers c1/20/60/76/82/83, 64 complete endpoints and105 trials, all independent review PASS. Earlier five states reduced active disagreement; c83 residual decreased11.9% while absolute disagreement increased18.0%, then stalled at seven rejected trials. All six missed4e-6, no converged teacher. Right-front damage/stiffness compensation localized from original outer20–30. Next unexecuted discriminator: saved c1/c83 phase projection/refresh residual floor and coupled trial-f tangent consistency; no automatic extra solve budget. Original trajectories/history remain frozen.

User-facing report: `/Users/wenxiaofang/obsidian/mesh对齐.md`; payloads remain external in `local_archive/experiments/S04-E011/runs/pf_s04e011_endpoint_q4_tight_0c21f70_20261012T170257Z`.


2026-10-13 follow-up: [saved-state phase/tangent audit](../research/S04/S04-E011/runs/phase_tangent_saved_state_20261013.md) completed. c1 remaining phase violation is concentrated in initial crack wake with f=1; c83 source-equivalent Picard derivative omits measurable trial-f chain term. Native pre-clamp/refresh attribution and exact next direction capture are prepared in the [new protocol](../research/S04/S04-E011/phase_projection_tangent_protocol_20261013.md), awaiting human approval for the final four-file Windows transfer under the newer user AGENTS rule. No new solve or history propagation yet.


2026-10-14: approved native v1 attempt stopped at pre-solve DOF row/column identity assertion. [Attempt](../research/S04/S04-E011/runs/phase_capture_v1_attempt_20261014.md). Four-state exact index/order proof confirms orientation-only bug. Revision2 fixes the comparison; native projection/tangent result remains pending final version transfer approval.


2026-10-15 terminal: [four-state native capture](../research/S04/S04-E011/runs/phase_capture_v2_result_20261015.md) completed, hashes/numerical review verified. c1-last cached residual misrepresents returned field; clipped endpoints retain1.06e-5/c1 and2.56e-5/c83 phase violations, raw-refresh incremental effect small here. Native Kdd trial-f chain omission measured; c83-last very small steps can descend beyond old1/64 minimum, with tiny progress. No history commit, repaired trajectory or teacher. Next unexecuted lever: genuinely constrained nodal damage solve plus fresh same-field stopping, c1 first then c83.


2026-10-15 preparation: [fixed-u constrained damage / fresh-stop protocol](../research/S04/S04-E011/constrained_damage_protocol_20261015.md). Prepare fresh-only and constrained arms at the four completed v2 capture states, c1 prerequisite then c83,250 phase calls/arm plus two shared admissions/state. No propagated history or coupled qualification. New six-file upload awaits exact-version approval; local independent review and Python/bundle checks do not mean native MATLAB execution.


2026-10-15 result: [fixed-u constrained damage/fresh-stop](../research/S04/S04-E011/runs/damage_repair_v1_result_20261015.md) completed4states8arms,40files468584478bytesverified. Constrained4/4phasepass using1–2updates; fresh-only0/4afterclip. c83-lastRu+14.75%, descriptive monitor+5.91%; pairedPIDL activefield gaps improve only modestly and integralgap worsens. Supports a bounded phase repair, not coupled/trajectory/teacher closure. Next: keep constrainedphase, re-equilibrateu and checkfreshsame-state residuals; unexecuted.


2026-10-15 next bounded discriminator prepared: [coupled repair](../research/S04/S04-E011/coupled_repair_protocol_20261015.md) starts from previous constrained endpoints, alternates fresh-return u and unchanged constrained d, tests both fresh residuals at identical u/d. Both c1 starts must pass before c83;20 blocks and250+250 native calls/case, no history commits. Local independent review/Python preparation only; nine-file upload and producer MATLAB checks remain pending approval.


2026-10-15 [coupled repair v1 admission failure](../research/S04/S04-E011/runs/coupled_repair_v1_attempt_20261015.md): approved9file upload/static/12selftests pass; stale predecessor path stops firstc1 before native residual,0states,history0.16files73957bytesverified. Original outputs separately migrated to verified backup; two accepted-s3 SHA match fresh remote checks. No coupled numerical verdict. Prepare locator-onlyv2 in freshroot with all-input preflight; new transfer approval pending.


2026-10-15 [coupled v2 I/O attempt](../research/S04/S04-E011/runs/coupled_repair_v2_attempt_20261015.md): approved9file/static/12selftests/14state hashes passed; mesh fileread fails in worker,0native states,16files75941bytesverified. SSH/Mac identicalinpSHA means no established mesh loss. Preparev3 all15data snapshots and same-worker import/MAT load prerequisite, no numeric changes, new approval pending. Owned stale readonly monitor memory issue separately repaired and freshRAM verified.


2026-10-15 CR-v3: exact9upload and15ordinarylocalinputs540736827bytes verified, attrs32. Static entrySAGROW comments block before launch; [two-file comment/hash repair](../research/S04/S04-E011/runs/coupled_repair_v3_static_annotation_20261015.md) prepared for exact replacement approval. All numerical code/data/budgets unchanged, no native result.


2026-10-15 [sequential c1/history preparation](../research/S04/S04-E011/c1_commit_protocol_20261015.md): original five-state regression prerequisite, shared exact recovery/predictorKK, repaired precommit old-state joint screen and single version advance.15file/8copy local package reviewed, no upload/native run;22Windows tests pending exact-version approval. Previous four-start numerical closure and c83 field divergence remain the latest computed results.


2026-10-16 [c1 sequence v1 attempt](../research/S04/S04-E011/runs/c1_commit_v1_attempt_20261016.md): approved15file transfer/8input staging passed; strict staticcheck stopped before all native fields and history commits.31file archive verified. Minimal v2 static repair prepared locally, new exact-version approval needed. Earlier numerical conclusions unchanged.


2026-10-16 [c1v2](../research/S04/S04-E011/runs/c1_commit_v2_attempt_20261016.md) passed staticchecks then stopped atbinarymanifest type before nativework/commits.31files156920132bytes verified; no numericalverdict. v3schema-only repair locally prepared, exactversion approvalpending; numerical protocol unchanged.


2026-10-16 [fullc1 v3 terminal](../research/S04/S04-E011/runs/c1_commit_v3_result_20261016.md): originals1/s2exactregressionspassed/singlecommits but freshC1036/21809>1. s3stopsatrawpointwisegate(5.0122e-10 vs1e-10),u/d~1e-12/history4.1e-12,9==9. Own-uQ4rawreplay explainsdifference, notphysicalfielddivergence;42filesverified. Acceptedversion2/proposed3uncommitted; repairedunexecuted. Preservegate/frozenproduction; nextoffline rawperturbation-bound design before any newapprovedproducer.


2026-10-16 [rawresponse r4 preparation](../research/S04/S04-E011/raw_admission_r4_20261016.md): oldrawpointwisegate did not account for permitted nodalperturbation response. Newprospective own-u consistencytau1e-10/analyticresponse budget retains allnonrawconditions and oldrawdiagnostics. v3missnotrescued;16filev4localprepared, exactapprovalpending before fullc1original→repairsequence.


2026-10-16 [c1 v4/r4 completed](../research/S04/S04-E011/runs/c1_commit_v4_r1_result_20261016.md): original five-step admission passes under prospective r4; legacy raw s3 still fails. Repaired five steps pass the PRE-COMMIT joint criterion under old history/lower, each with one durable version advance. Shared recovery: 34 phase calls, one reset. All 69 files / 1,353,725,620 bytes verified; producer 6794251. Repaired C = .165322/.392168/.887083/.813816/2.04e-6; s2 uses all 20 blocks. Original misses strict fresh closure at all five steps. Active weighted relative L2 difference is 79.41% at s2 and 16.50% at peak, although peak integral changes only −.2243%. All GP f=1: supports one-c1 numerical/state-transition consistency, not fatigue-degradation feedback, unique equilibrium, teacher or physical validity. Next unexecuted discriminator: same-predecessor s2 local solver sensitivity versus incoming-state propagation.


2026-10-16 [c1s2 controlled diagnostic](../research/S04/S04-E011/runs/s2_factorial_v1_result_20261016.md) completed: two exact restart anchors and four common-start solver × incoming lower/history cases, no history commits. All 48 files / 580,688,443 bytes verified, producer523f032. Same-predecessor solver active relativeL2 differences78.246%/78.238%; changing predecessor at fixed solver0.3281%/0.0270%. Symmetric decomposition L/P/warm-start bridge projections .903018/−.000312/.097295 are algebraic, not causal percentages; respective norms .905997/.001901/.122072 of archived gap. Squared gap99.47% in initial left crack wake. Original internal phase trialf≈2.17e-5, repaired alltrialf=1; all endpointsf=1. Original misses strict joint screen; repaired passes within19blocks for controls. Supports local composite solver/stop sensitivity at this c1s2, not two qualified equilibrium branches, physical/teacher/life claim. Earlier c1 f=1 statement applies to accepted endpoints only. Next unexecuted discriminator: isolate bounded damage versus fresh-stop/trial-f behavior at the same origin, retaining complete trial fields.


2026-10-16 [c1s2 D/S/F isolation](../research/S04/S04-E011/runs/s2_isolation_v1_r1_result_20261016.md) completed: all10 executed,7 declared-policy accepted, only110/111 strictC<=1 (.929612),3 bounded-budget inner misses retained. Same old O1 predecessor/common start/predictor, no history commits. Conditional active relL2: D atS0/F0 14.011%; S atD1/F0 80.668% (common000 denominator90.189%); F atD0/S0 8.805%; F underD1 exactly0. S squared-gap99.265% leftwake; 000 max-alpha trial(call27) dmin−161.896/alpha214/f2.17e-5 instead bottomright corner. S includes fresh+strictaccuracy,D is full constrained strategy,T1 includesinitialadmission; no bare-bound/pure-age/fullcubeShapley/physicalteacher claim. KeepD1S1/nativef. Producer6c2fceb,135files1679373763bytes verified,50tests/6nativeadmissions and independent terminal replay passed.


2026-10-16 [c1s2 refresh versus accuracy](../research/S04/S04-E011/runs/s2_refresh_accuracy_v1_result_20261016.md) completed: fixed D1/nativep2 and identical oldO1/commonstart/predictor; four R(refresh)×A(tolerance) cells accepted under ownpolicy, A0outer1 strictC15.65081 versus A1outer19 strictC.929612. R conditional active relativeL2=1.5526e-12/3.3482e-12; A both80.66797%; interaction/common00=2.3279e-12.40completeblocks cached/fresh phase norm difference≤2.1933e-15 with0thresholdcrossings, raw atfixedu independentofd. Two anchors exactly reproduce S2I100/110. Thus prior80.67% principally groupedthresholdA, notrefreshR, in this synthetic c1s2. A still groupsinneru/d,jointsum,outeru; noindividualtol/physicalteacher/multicycleclaim.89files1543190804bytes verified,44completepoints independently replayed;48tests/3figures/sidecars reviewed. Producerdd4fe3e, nohistorycommits, noaddedbudget/retry. KeepD1/nativef/freshstrictjoint; next unexecuted discriminator separates innerdamage and joint/outer-u accuracy. FrozenE003/E011 unchanged.
